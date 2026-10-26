#!/usr/bin/env python3
"""M7.1-LQ mapped netlist export, strict inventory and gate-level regression.

Gate-level equivalence is *bounded vector-based*, not a universal proof.
Fails closed without explicit, qualified standard-cell simulation models.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from msif.governance import validate_manifest
from msif.simulation import create_testbench, test_vectors
from m71_cell_models import assemble

VARIANTS = ('programmable', 'fixed', 'rom')
SHA = re.compile(r'^[a-f0-9]{64}$')
BAD = re.compile(r'(?im)^\s*(?:ERROR:|FATAL:|FAIL\s|%Error)')

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def safe_path(p: Path) -> str:
    p = p.resolve(strict=True)
    if re.search(r'[\s;"\\]', str(p)):
        raise ValueError('Yosys path contains unsupported characters')
    return str(p)

def run(argv: list[str], log: Path, timeout: int = 300) -> str:
    try:
        cp = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        result = cp.stdout + cp.stderr
        log.write_text('COMMAND: ' + repr(argv) + '\n' + result)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.write_text('ERROR: ' + str(exc))
        raise RuntimeError('tool invocation failed: ' + str(log)) from exc
    if cp.returncode != 0 or BAD.search(result):
        raise RuntimeError('tool failed: ' + str(log))
    return result

def inventory(mapped: dict, library: dict, top: str) -> dict:
    modules = mapped.get('modules', {})
    lib_modules = library.get('modules', {})
    if top not in modules or not lib_modules:
        raise ValueError('missing top module or empty Liberty cell catalog')
    cells = modules[top].get('cells', {})
    if not cells:
        raise ValueError('mapped design contains no cells')
    counts: dict[str, int] = {}
    unknown: list[str] = []
    for cell in cells.values():
        typ = cell['type']
        counts[typ] = counts.get(typ, 0) + 1
        if typ not in lib_modules:
            unknown.append(typ)
    return {'total_cells': len(cells), 'cell_types': dict(sorted(counts.items())),
            'unknown_cells': sorted(set(unknown)), 'check': 'PASS' if not unknown else 'FAIL'}

def qualify(build: Path, liberty: Path, cell_models: Path | None, vectors: int) -> dict:
    if vectors < 1 or vectors > 1024:
        raise ValueError('vectors must be 1..1024')
    if not shutil.which('yosys'):
        raise RuntimeError('yosys is mandatory')
    if cell_models is None:
        raise RuntimeError('qualified gate-level cell models required (--cell-models); LQ cannot be approved')
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        raise RuntimeError('Icarus and vvp required for gate-level verification')
    lib = safe_path(liberty)
    models = safe_path(cell_models)
    validate_manifest(build)
    model = json.loads((build / 'model.json').read_text())
    out = build / 'm71_lq'
    out.mkdir(parents=True, exist_ok=True)
    report = out / 'evidence.json'
    report.unlink(missing_ok=True)
    library_json = out / 'liberty-cells.json'
    run(['yosys', '-Q', '-T', '-p', f'read_liberty -lib {lib}; write_json {safe_path(out)}' + '/liberty-cells.json'],out/'liberty-parse.log')
    catalog = json.loads(library_json.read_text())
    result = {'schema':'msif-m71-lq-v1','qualification':'bounded-mapped-gate-level-validation',
              'release_approval':'NOT_VERIFIED','full_formal_equivalence':'NOT_VERIFIED',
              'physical_ppa':'NOT_VERIFIED', 'liberty_sha256':digest(Path(lib)),
              'cell_models_sha256':digest(Path(models)), 'model_sha256':digest(build/'model.json'),
              'manifest_sha256':digest(build/'manifest.json'), 'yosys_version':run(['yosys','-V'],out/'yosys-version.log',30).strip().splitlines()[0],
              'architectures':{}}
    for variant in VARIANTS:
        top = f'msif_{variant}'
        rtl = Path(safe_path(build / f'{top}.sv'))
        mapped_v = out / f'{top}_mapped.v'
        mapped_j = out / f'{top}_mapped.json'
        log = out / f'{top}_map.log'
        program = (f'read_liberty -lib {lib}; read_verilog -sv {rtl}; hierarchy -check -top {top}; synth -top {top}; '
                   f'dfflibmap -liberty {lib}; abc -liberty {lib}; clean; check -assert; '
                   f'write_verilog -noattr -noexpr {mapped_v.resolve()}; write_json {mapped_j.resolve()}; stat -liberty {lib}')
        run(['yosys','-Q','-T','-p',program],log)
        inv = inventory(json.loads(mapped_j.read_text()), catalog, top)
        inv_file = out / f'{top}_inventory.json'
        inv_file.write_text(json.dumps(inv, indent=2, sort_keys=True)+'\n')
        if inv['check'] != 'PASS':
            raise RuntimeError('unrecognized cell(s) in mapped netlist: ' + str(inv['unknown_cells']))
        tb = out / f'{top}_gate_tb.sv'
        test_count = vectors + 4
        bench = create_testbench(model,test_vectors(model,vectors),variant)
        # Exercise a real asynchronous reset event between clock edges, then
        # verify out_valid and data recovery. This is still bounded regression.
        marker = f'  $display("PASS {variant} {test_count} vectors");'
        if marker not in bench:
            raise RuntimeError('unexpected testbench template: PASS marker missing')
        reset_checks = (
            "  @(negedge clk); #1; rst_n=0; #1;\n"
            "  if (out_valid !== 1'b0 || result !== '0) $fatal(1, \"async reset failed\");\n"
            "  @(negedge clk); rst_n=1;\n"
            "  @(posedge clk); #1;\n"
            "  if (out_valid !== 1'b0) $fatal(1, \"post-reset valid failed\");\n"
        )
        tb.write_text(bench.replace(marker, reset_checks + marker))
        # The baseline bundle was built from older ABC logs. Use actual mapped
        # Yosys JSON so every cell in this mapping has a functional definition.
        import os
        sky130_source = os.environ.get('SKY130_HD')
        if not sky130_source:
            raise RuntimeError('SKY130_HD is required for exact mapped-cell model coverage')
        exact_models = out / f'{top}_functional_models.v'
        model_record = assemble(json.loads(mapped_j.read_text()), top, Path(sky130_source), exact_models)
        binary = out / f'{top}_gate.vvp'
        run(['iverilog','-g2012','-s','tb','-o',str(binary),str(exact_models),str(mapped_v),str(tb)],out/f'{top}_compile.log')
        sim_log = out / f'{top}_simulate.log'
        simulation = run(['vvp',str(binary)],sim_log)
        if f'PASS {variant} {test_count} vectors' not in simulation:
            raise RuntimeError('missing gate-level test PASS marker')
        result['architectures'][variant] = {'rtl_sha256':digest(rtl),'mapped_verilog_sha256':digest(mapped_v),
                'mapped_json_sha256':digest(mapped_j),'cell_inventory_sha256':digest(inv_file),
                'mapping_log_sha256':digest(log),'simulation_log_sha256':digest(sim_log),
                'mapped_cell_count':inv['total_cells'],'inventory':'PASS',
                'actual_cell_models_sha256':model_record['model_sha256'],
                'gate_level_vectors':test_count,'gate_level_regression':'PASS'}
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build',default='build/m71_liberty',type=Path)
    ap.add_argument('--liberty',required=True,type=Path)
    ap.add_argument('--cell-models',type=Path,required=True)
    ap.add_argument('--vectors',type=int,default=256)
    args=ap.parse_args()
    try:
        print(json.dumps(qualify(args.build,args.liberty,args.cell_models,args.vectors),indent=2))
        print('PASS M7.1-LQ: strict inventory and bounded gate-level regression; FULL FORMAL UNVERIFIED')
    except (ValueError,RuntimeError,OSError,KeyError,json.JSONDecodeError) as exc:
        print('BLOCKED M7.1-LQ:',exc,file=sys.stderr)
        raise SystemExit(1)
if __name__=='__main__': main()
