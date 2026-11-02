#!/usr/bin/env python3
"""Read-only, SHA-bound TT-only OpenROAD STA experiment; NEVER signoff."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

VARIANTS = ('programmable', 'fixed', 'rom')
LIB_SHA = 'ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--openroad',default='openroad')
    p.add_argument('--timeout',type=int,default=300)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args(argv)
    if args.out.exists():p.error('output exists; preserve prior evidence')
    if args.timeout < 1:p.error('timeout must be positive')
    args.out.mkdir(parents=True)
    result={'schema':'msif-m72-tt-research-v1','status':'BLOCKED','signoff':'NOT_VERIFIED', 'multi_corner':'NOT_VERIFIED','results':{},'issues':[]}
    try:
        inventory=json.loads(args.inventory.read_text())
        if set(inventory.get('designs',{})) != set(VARIANTS):raise ValueError('incomplete design inventory')
        libraries=[x for x in inventory.get('libraries',[]) if x.get('name')=='sky130_fd_sc_hd__tt_025C_1v80.lib']
        if len(libraries)!=1:raise ValueError('exactly one pinned TT library required')
        lib=Path(libraries[0]['path']);
        if not lib.is_file() or sha(lib)!=LIB_SHA or libraries[0]['sha256']!=LIB_SHA:raise ValueError('TT Liberty hash mismatch')
        inputs={}
        for variant in VARIANTS:
            files={}
            for kind in ('odb','sdc','spef'):
                entry=inventory['designs'][variant][kind]
                path=Path(entry['path'])
                if not path.is_file() or path.stat().st_size==0 or sha(path)!=entry.get('sha256'):
                    raise ValueError(f'{variant} {kind}: missing or SHA mismatch: {path}')
                files[kind]=path.resolve()
            inputs[variant]=files
        binary=shutil.which(args.openroad) if args.execute else None
        if args.execute and not binary:raise ValueError(f'OpenROAD executable missing: {args.openroad}')
        for variant,files in inputs.items():
            entry={'status':'INPUTS_HASH_VERIFIED_NOT_EXECUTED', 'inputs':{k:{'path':str(v),'sha256':sha(v)} for k,v in files.items()},'liberty_sha256':LIB_SHA}
            result['results'][variant]=entry
            tcl=args.out/f'{variant}.tcl'
            tcl.write_text('''read_liberty $::env(MSIF_LIB)\nread_db $::env(MSIF_ODB)\nread_sdc $::env(MSIF_SDC)\nread_spef $::env(MSIF_SPEF)\nreport_checks -path_delay max -group_path_count 10\nreport_checks -path_delay min -group_path_count 10\nreport_check_types -max_slew -max_cap -max_fanout -violators\ncheck_setup\nputs "M72_TT_RESEARCH_EXECUTED_NOT_SIGNOFF"\n''')
            entry['script_sha256']=sha(tcl)
            if not args.execute:continue
            env=dict(os.environ,MSIF_LIB=str(lib.resolve()),MSIF_ODB=str(files['odb']),MSIF_SDC=str(files['sdc']),MSIF_SPEF=str(files['spef']))
            log=args.out/f'{variant}.log'
            try:
                with log.open('wb') as f:
                    proc=subprocess.run([binary,'-exit',str(tcl.resolve())],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=args.timeout,check=False)
                output=log.read_text(errors='replace')
                entry['exit_code']=proc.returncode
                entry['status']='STA_EXECUTED_REVIEW_REQUIRED' if proc.returncode==0 and 'M72_TT_RESEARCH_EXECUTED_NOT_SIGNOFF' in output else 'BLOCKED'
            except subprocess.TimeoutExpired:
                entry['status']='TIMEOUT_INCONCLUSIVE'
            entry['log_sha256']=sha(log)
            entry['log_bytes']=log.stat().st_size
        statuses=[e['status'] for e in result['results'].values()]
        result['status']='TT_RESEARCH_EXECUTED_REVIEW_REQUIRED' if args.execute and all(s=='STA_EXECUTED_REVIEW_REQUIRED' for s in statuses) else ('TT_INPUTS_VERIFIED_NOT_EXECUTED' if not args.execute else 'BLOCKED_OR_INCONCLUSIVE')
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        result['issues'].append(str(exc))
    finally:
        (args.out/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(result['status'])
    return 0 if result['status'] in ('TT_INPUTS_VERIFIED_NOT_EXECUTED','TT_RESEARCH_EXECUTED_REVIEW_REQUIRED') else 2

if __name__=='__main__':sys.exit(main())
