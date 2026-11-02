#!/usr/bin/env python3
"""M7.2 research physical-flow preflight and opt-in OpenROAD Flow Scripts execution.

Never claims physical signoff, timing closure, macro equivalence or release approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# Support both CLI execution and importlib-based isolated test loading.
SCRIPTS_DIR = Path(__file__).resolve().parent
for module_dir in (ROOT / 'src', SCRIPTS_DIR):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
from msif.governance import validate_manifest
from m71_lq_audit import verify as audit_lq

VARIANTS = ('programmable', 'fixed', 'rom')
LIB_HASH = 'ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9'
PLATFORM_COMMIT = '64939f3717ad7c694199ba04cb98924b98022868'

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require_file(path: Path) -> Path:
    p = path.expanduser().resolve(strict=True)
    if not p.is_file() or p.stat().st_size == 0:
        raise ValueError(f'missing/empty file: {p}')
    return p

def get_commit(repo: Path) -> str:
    p = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=20)
    if p.returncode or not re.fullmatch(r'[0-9a-f]{40}', p.stdout.strip()):
        raise ValueError('cannot qualify OpenROAD source revision')
    return p.stdout.strip()

def check_rtl(build: Path) -> dict:
    validate_manifest(build)
    m = json.loads(require_file(build / 'model.json').read_text())
    if m.get('shape') != [2, 4]:
        raise ValueError('M7.2 research fixture is restricted to accepted 2x4 fixture')
    from msif.core import generate
    for v in VARIANTS:
        r = require_file(build / f'msif_{v}.sv')
        if r.read_text() != generate(m, v):
            raise ValueError(f'RTL does not match independent deterministic generator: {v}')
    return m

def sdc(clock_ns: float, io_delay_ns: float, uncertainty_ns: float, load_pf: float) -> str:
    if not (10 <= clock_ns <= 10000 and 0 <= io_delay_ns < clock_ns / 2 and
            0 <= uncertainty_ns < clock_ns / 4 and 0 < load_pf <= 1):
        raise ValueError('invalid or nonconservative SDC assumptions')
    return ('# Research-only constraint, identical for A/B/C; all numbers explicitly assumed.\n'
            f'create_clock -name core_clk -period {clock_ns:.3f} [get_ports clk]\n'
            f'set_clock_uncertainty {uncertainty_ns:.3f} [get_clocks core_clk]\n'
            f'set_input_delay {io_delay_ns:.3f} -clock core_clk [get_ports {{rst_n in_valid activations*}}]\n'
            f'set_output_delay {io_delay_ns:.3f} -clock core_clk [get_ports {{out_valid result*}}]\n'
            f'set_load {load_pf:.4f} [get_ports {{out_valid result*}}]\n'
            '# Reset treatment requires engineering review. Async reset is intentionally not false-pathed.\n')

def preflight(build: Path, orfs: Path, out: Path, *, clock_ns: float = 100, io_delay_ns: float = 5,
              uncertainty_ns: float = 1, load_pf: float = 0.01, expected_commit: str = PLATFORM_COMMIT,
              acknowledge_license: bool = False) -> dict:
    if not acknowledge_license:
        raise ValueError('operator must explicitly attest platform licensing/PVT review')
    for exe in ('openroad', 'yosys', 'make'):
        if not shutil.which(exe):
            raise ValueError(f'physical-flow tool missing from PATH: {exe}; qualify ORFS tool installation first')
    model = check_rtl(build)
    lq = audit_lq(build)
    if lq['result'] != 'PASS' or lq['vectors_per_architecture'] != [260] * 3:
        raise ValueError('previous LQ acceptance missing')
    orfs = orfs.expanduser().resolve(strict=True)
    flow = orfs / 'flow'
    platform = flow / 'platforms' / 'sky130hd'
    commit = get_commit(orfs)
    if commit != expected_commit:
        raise ValueError(f'ORFS revision mismatch: observed={commit} expected={expected_commit}')
    required = {
        'flow_makefile': flow / 'Makefile',
        'platform_config': platform / 'config.mk',
        'tech_lef': platform / 'lef' / 'sky130_fd_sc_hd.tlef',
        'cell_lef': platform / 'lef' / 'sky130_fd_sc_hd_merged.lef',
        'liberty': platform / 'lib' / 'sky130_fd_sc_hd__tt_025C_1v80.lib',
        'pdn': platform / 'pdn.tcl',
        'tapcell': platform / 'tapcell.tcl',
        'rcx_rules': platform / 'rcx_patterns.rules',
    }
    files = {key: {'path': str(require_file(val)), 'sha256': sha(val)} for key, val in required.items()}
    if files['liberty']['sha256'] != LIB_HASH:
        raise ValueError('SKY130 TT Liberty does not match reviewed LQ library SHA-256')
    # Validate RC and cell views from the *pinned platform config*, not guessed file names.
    conf = required['platform_config'].read_text()
    if not all(k in conf for k in ('TECH_LEF', 'SC_LEF', 'LIB_FILES', 'RCX_RULES')):
        # Some ORFS revisions use another extraction variable: do not silently accept it.
        raise ValueError('platform config missing required tech/RC declaration; review pinned RC setup')
    has_rc = any(p.is_file() for p in platform.rglob('*') if p.suffix.lower() in ('.rules', '.tcl', '.rc', '.spef') and ('rc' in p.name.lower() or 'setrc' in p.name.lower()))
    if not has_rc:
        raise ValueError('no potential RC setup files discovered; extraction not qualified')
    config = sdc(clock_ns, io_delay_ns, uncertainty_ns, load_pf)
    out.mkdir(parents=True, exist_ok=True)
    entries = {}
    for v in VARIANTS:
        run_dir = out / v
        run_dir.mkdir(parents=True, exist_ok=True)
        src = require_file(build / f'msif_{v}.sv')
        (run_dir / 'constraint.sdc').write_text(config)
        # Standard ORFS RTL-to-GDS entry point, NOT direct consumption of LQ mapped netlist.
        # ORFS independently maps RTL, therefore equivalence to LQ mapping is not claimed.
        mk = (f'export DESIGN_NAME = msif_{v}\n'
              'export PLATFORM = sky130hd\n'
              f'export VERILOG_FILES = {src}\n'
              f'export SDC_FILE = {(run_dir / "constraint.sdc").resolve()}\n'
              'export CORE_UTILIZATION = 25\n'
              'export CORE_ASPECT_RATIO = 1\n'
              'export CORE_MARGIN = 4\n'
              'export PLACE_DENSITY = 0.55\n')
        (run_dir / 'config.mk').write_text(mk)
        entries[v] = {'rtl_sha256': sha(src), 'sdc_sha256': sha(run_dir / 'constraint.sdc'),
                      'config_sha256': sha(run_dir / 'config.mk'),
                      'lq_mapped_verilog_sha256': sha(build / 'm71_lq' / f'msif_{v}_mapped.v'),
                      'constraint_file': str((run_dir / 'constraint.sdc').resolve()),
                      'design_config': str((run_dir / 'config.mk').resolve())}
    evidence = {'schema': 'msif-m72-preflight-v1', 'qualification': 'platform-constraints-readiness-only',
                'status': 'PASS_P0_P1_LQ_LINEAGE', 'orfs_revision': commit,
                'lq_audit': lq, 'process': 'sky130hd-TT-25C-1v80',
                'platform_files': files, 'variants': entries,
                'shared_assumptions': {'clock_period_ns': clock_ns, 'io_delay_ns': io_delay_ns,
                                       'uncertainty_ns': uncertainty_ns, 'load_pf': load_pf,
                                       'core_utilization_percent': 25, 'place_density': 0.55},
                'mapped_netlist_import': 'NOT_VERIFIED_ORFS_RESYNTHESIZES_RTL',
                'route': 'NOT_VERIFIED', 'extracted_timing': 'NOT_VERIFIED',
                'power': 'NOT_VERIFIED', 'physical_ppa': 'NOT_VERIFIED',
                'memory_macro_equivalence': 'NOT_VERIFIED', 'release_approval': 'NOT_VERIFIED'}
    (out / 'preflight.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    return evidence

def run_flow(preflight_result: dict, out: Path, orfs: Path, *, execute: bool, timeout: int) -> dict:
    if not shutil.which('make'):
        raise ValueError('make unavailable')
    flow = orfs.expanduser().resolve(strict=True) / 'flow'
    result = {'schema': 'msif-m72-flow-attempt-v1', 'execution': 'requested' if execute else 'static-plan-no-execution',
              'variants': {}, 'qualification': 'research-flow-attempt-only',
              'timing_closure': 'NOT_VERIFIED', 'physical_ppa_signoff': 'NOT_VERIFIED',
              'release_approval': 'NOT_VERIFIED'}
    for v in VARIANTS:
        config = Path(preflight_result['variants'][v]['design_config'])
        if not config.is_file() or not config.stat().st_size:
            raise ValueError(f'missing generated design config: {config}')
        constraint = Path(preflight_result['variants'][v]['constraint_file'])
        if not constraint.is_file() or not constraint.stat().st_size:
            raise ValueError(f'missing generated SDC: {constraint}')
        # Keep separate, uniquely named ORFS outputs for each architecture.
        cmd = ['make', '--no-print-directory', '-C', str(flow),
               f'DESIGN_CONFIG={config}', f'FLOW_VARIANT=msif_m72_{v}', '-j1']
        if not execute:
            # GNU make -n still runs recursive $(MAKE) recipes. ORFS uses these to
            # create stage intermediates, which causes false missing-target failures
            # (e.g. 2_1_floorplan.sdc). A safe dry-run must not invoke make at all.
            plan = out / v / 'orfs-plan.json'
            record = {
                'schema': 'msif-m72-static-plan-v1',
                'execution': 'NOT_EXECUTED',
                'verification': 'STATIC_INPUT_PLAN_ONLY',
                'make_argv': cmd,
                'design_config': str(config),
                'design_config_sha256': sha(config),
                'constraint_file': str(constraint),
                'constraint_sha256': sha(constraint),
                'mapped_lq_import': 'NOT_VERIFIED_ORFS_RESYNTHESIZES_RTL',
                'physical_ppa': 'NOT_VERIFIED',
                'required_future_stages': ['synthesis', 'floorplan', 'placement',
                                           'clock_tree', 'global_route', 'detailed_route',
                                           'extraction', 'sta', 'physical_report_audit'],
            }
            plan.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            result['variants'][v] = {
                'status': 'STATIC_PLAN_ONLY_NOT_EXECUTED',
                'plan': str(plan), 'plan_sha256': sha(plan),
                'tool_execution': 'NOT_PERFORMED',
            }
            continue
        log = out / v / 'orfs-execute.log'
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, check=False)
            log.write_text('COMMAND: ' + repr(cmd) + '\n' + p.stdout + '\n' + p.stderr)
            result['variants'][v] = {'exit_code': p.returncode, 'log_sha256': sha(log),
                                     'log': str(log),
                                     'status': 'FLOW_TOOL_EXIT_0_REPORTS_UNAUDITED'
                                     if p.returncode == 0 else 'BLOCKED'}
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.write_text('ERROR: ' + str(exc))
            result['variants'][v] = {'status': 'BLOCKED', 'log': str(log),
                                     'reason': str(exc)}
        if result['variants'][v]['status'] == 'BLOCKED':
            break
    (out / 'flow-attempt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    if len(result['variants']) != 3 or any(item['status'] == 'BLOCKED' for item in result['variants'].values()):
        raise RuntimeError('OpenROAD flow dry-run/execution blocked; inspect per-architecture log')
    return result

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, default=Path('build/m71_liberty'))
    p.add_argument('--orfs', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('build/m72'))
    p.add_argument('--license-pvt-reviewed', action='store_true')
    p.add_argument('--clock-ns', type=float, default=100)
    p.add_argument('--io-delay-ns', type=float, default=5)
    p.add_argument('--uncertainty-ns', type=float, default=1)
    p.add_argument('--load-pf', type=float, default=0.01)
    p.add_argument('--expected-orfs-commit', default=PLATFORM_COMMIT)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--timeout', type=int, default=7200)
    args = p.parse_args()
    try:
        if args.timeout <= 0:
            raise ValueError('timeout must be positive')
        if args.execute and args.dry_run:
            raise ValueError('select either dry-run or execute')
        result = preflight(args.build, args.orfs, args.out, clock_ns=args.clock_ns,
                           io_delay_ns=args.io_delay_ns, uncertainty_ns=args.uncertainty_ns,
                           load_pf=args.load_pf, expected_commit=args.expected_orfs_commit,
                           acknowledge_license=args.license_pvt_reviewed)
        print(json.dumps({'status': result['status'], 'preflight': str(args.out / 'preflight.json')}, indent=2))
        if args.execute or args.dry_run:
            flows = run_flow(result, args.out, args.orfs, execute=args.execute, timeout=args.timeout)
            print(json.dumps(flows, indent=2))
        print('PENDING: imported-LQ-netlist STA, placement metrics audit, routed timing, power, memory macros and G1 approval')
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
        print('BLOCKED M7.2:', exc, file=sys.stderr)
        raise SystemExit(1)
if __name__ == '__main__':
    main()
