#!/usr/bin/env python3
"""M7.1 controlled three-architecture synthesis comparison. Never claims physical PPA."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

VARIANTS = ('programmable', 'fixed', 'rom')
ERROR = re.compile(r'(?im)^(?:\s*(?:ERROR:|FATAL:|FAIL(?:\s|:)|%Error|%Warning))')
ZERO_CHECK = 'Found and reported 0 problems.'

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(command, output, timeout=600):
    try:
        proc=subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        output.write_text('COMMAND: '+repr(command)+'\nERROR: '+str(exc)+'\n')
        raise RuntimeError(f'tool invocation failed; see {output}') from exc
    output.write_text('COMMAND: '+repr(command)+'\n'+proc.stdout+proc.stderr)
    if proc.returncode != 0 or ERROR.search(proc.stdout+proc.stderr):
        raise RuntimeError(f'tool returned error or diagnostic; see {output}')
    return proc.stdout+proc.stderr

def compare(out: Path, liberty: Path|None):
    # This is not an approved workflow; validate before starting a tool.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
    from msif.governance import validate_manifest
    validate_manifest(out)
    if not shutil.which('yosys'):
        raise RuntimeError('Yosys unavailable')
    if liberty is not None:
        liberty=liberty.resolve()
        if not liberty.is_file() or liberty.stat().st_size == 0:
            raise RuntimeError('Liberty file missing or empty')
        # Strongly restrict Yosys script injection and output corruption from pathname.
        if re.search(r'[\s;"\\]',str(liberty)):
            raise RuntimeError('Liberty path must not contain spaces or Yosys control characters')
    evidence_path=out/'m71_evidence.json'
    evidence_path.unlink(missing_ok=True)
    result={'schema':'msif-m71-evidence-v1','qualification':'generic-synthesis-comparison-only' if liberty is None else 'liberty-mapped-synthesis-comparison-only',
       'limitations':['No placement/routing or extracted parasitics','No qualified STA/operating corner','No switching-power measurement','No characterized physical SRAM/ROM macros','No release approval'],
       'inputs':{},'tools':{},'architectures':{}}
    result['tools']['yosys']=run(['yosys','-V'],out/'m71_yosys_version.log',30).strip().splitlines()[0]
    result['inputs']['manifest_sha256']=digest(out/'manifest.json')
    if liberty:
        result['inputs']['liberty_path']=str(liberty)
        result['inputs']['liberty_sha256']=digest(liberty)
    for variant in VARIANTS:
        rtl=out/f'msif_{variant}.sv'
        result['inputs'][f'{variant}_rtl_sha256']=digest(rtl)
        # Common sequence; mapping is always explicitly opt-in and uses the SAME liberty.
        program=f'read_verilog -sv {rtl.resolve()}; hierarchy -check -top msif_{variant}; proc; opt; synth -top msif_{variant}; check;'
        if liberty:
            program += f' dfflibmap -liberty {liberty}; abc -liberty {liberty}; check;'
        program += ' stat'+(f' -liberty {liberty}' if liberty else '')
        log=out/f'm71_{variant}.log'
        txt=run(['yosys','-Q','-T','-p',program],log)
        if ZERO_CHECK not in txt:
            raise RuntimeError(f'No zero-problem synthesis check for {variant}')
        numbers=re.findall(r'Number of cells:\s*(\d+)',txt)
        if not numbers:
            raise RuntimeError(f'No cell count in synthesis report for {variant}')
        result['architectures'][variant]={'cells_reported':int(numbers[-1]),'log_sha256':digest(log),'rtl_sha256':digest(rtl),'check':'PASS'}
    result['inputs']['model_sha256']=digest(out/'model.json')
    result['tools']['version_log_sha256']=digest(out/'m71_yosys_version.log')
    result['observations']={'rom_vs_programmable_equal_cell_count':result['architectures']['rom']['cells_reported']==result['architectures']['programmable']['cells_reported'],
      'mapped_area':'NOT_VERIFIED' if not liberty else 'LIBERTY_MAPPING_ONLY_NOT_PHYSICAL_AREA',
      'clock_period':'NOT_VERIFIED','energy_per_op':'NOT_VERIFIED','approval':'NOT_VERIFIED'}
    evidence_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--build',default='build/m71')
    a.add_argument('--liberty',type=Path,help='Optional exact, reviewed Liberty file; no download is performed')
    args=a.parse_args()
    try:
        print(json.dumps(compare(Path(args.build),args.liberty),indent=2))
        print('PASS M7.1: controlled synthesis comparison; physical PPA NOT VERIFIED')
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print('BLOCKED M7.1:',exc,file=sys.stderr)
        raise SystemExit(1)
if __name__=='__main__':
    main()
