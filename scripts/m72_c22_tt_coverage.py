#!/usr/bin/env python3
"""SHA-pinned TT-only global timing diagnostics, deliberately NOT signoff."""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(inventory,out,execute=False,openroad='openroad',timeout=300):
 inventory,out=Path(inventory),Path(out)
 if out.exists():raise ValueError('output exists: preserve evidence')
 out.mkdir(parents=True)
 record={'schema':'msif-m72-c22-tt-coverage-v1','status':'BLOCKED','signoff':'NOT_VERIFIED','corner':'TT_ONLY','issues':[],'variants':{}}
 try:
  data=json.loads(inventory.read_text());libs=[x for x in data['libraries'] if x['name']=='sky130_fd_sc_hd__tt_025C_1v80.lib']
  if len(libs)!=1 or set(data['designs'])!=set(V):raise ValueError('inventory missing variants or TT Liberty')
  lib=Path(libs[0]['path']); expected=libs[0]['sha256']
  if not lib.is_file() or sha(lib)!=expected:raise ValueError('TT Liberty SHA mismatch')
  binary=shutil.which(openroad) if execute else None
  if execute and not binary:raise ValueError('OpenROAD not found')
  for v in V:
   paths={key:Path(data['designs'][v][key]['path']) for key in ('odb','sdc','spef')}
   for key,p in paths.items():
    if not p.is_file() or sha(p)!=data['designs'][v][key]['sha256']:raise ValueError(f'{v} {key} SHA mismatch or missing')
   tcl=out/f'{v}.tcl';tcl.write_text('''read_liberty $::env(MSIF_LIB)\nread_db $::env(MSIF_ODB)\nread_sdc $::env(MSIF_SDC)\nread_spef $::env(MSIF_SPEF)\nputs "C22_BEGIN_SETUP"\ncheck_setup -verbose\nputs "C22_END_SETUP"\nputs "C22_BEGIN_GLOBAL_MAX"\nreport_wns -max -digits 4\nreport_tns -max -digits 4\nputs "C22_END_GLOBAL_MAX"\nputs "C22_BEGIN_GLOBAL_MIN"\nreport_wns -min -digits 4\nreport_tns -min -digits 4\nputs "C22_END_GLOBAL_MIN"\nputs "C22_BEGIN_PATHS"\nreport_checks -path_delay max -group_path_count 20\nreport_checks -path_delay min -group_path_count 20\nputs "C22_END_PATHS"\nputs "C22_BEGIN_ELECTRICAL"\nreport_check_types -max_slew -max_cap -max_fanout -violators\nputs "C22_END_ELECTRICAL"\nputs "C22_TT_DIAGNOSTICS_COMPLETE_NOT_SIGNOFF"\n''')
   entry={'status':'INPUTS_HASH_VERIFIED_NOT_EXECUTED','tcl_sha256':sha(tcl),'inputs':{k:{'sha256':sha(p),'path':str(p)} for k,p in paths.items()}}
   record['variants'][v]=entry
   if not execute:continue
   env=dict(os.environ,MSIF_LIB=str(lib),MSIF_ODB=str(paths['odb']),MSIF_SDC=str(paths['sdc']),MSIF_SPEF=str(paths['spef']))
   log=out/f'{v}.log'
   try:
    with log.open('wb') as f:r=subprocess.run([binary,'-exit',str(tcl.resolve())],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    txt=log.read_text(errors='replace');markers=['C22_BEGIN_SETUP','C22_END_SETUP','C22_BEGIN_GLOBAL_MAX','C22_END_GLOBAL_MAX','C22_BEGIN_GLOBAL_MIN','C22_END_GLOBAL_MIN','C22_BEGIN_PATHS','C22_END_PATHS','C22_BEGIN_ELECTRICAL','C22_END_ELECTRICAL','C22_TT_DIAGNOSTICS_COMPLETE_NOT_SIGNOFF']
    entry['exit_code']=r.returncode;entry['status']='GLOBAL_TT_REPORTS_EXECUTED_REVIEW_REQUIRED' if r.returncode==0 and all(m in txt for m in markers) and 'Error:' not in txt and '[ERROR' not in txt else 'BLOCKED'
   except subprocess.TimeoutExpired:entry['status']='TIMEOUT_INCONCLUSIVE'
   entry['log_sha256']=sha(log);entry['log_bytes']=log.stat().st_size
  statuses=[x['status'] for x in record['variants'].values()]
  record['status']='GLOBAL_TT_REPORTS_EXECUTED_REVIEW_REQUIRED' if execute and all(s=='GLOBAL_TT_REPORTS_EXECUTED_REVIEW_REQUIRED' for s in statuses) else 'TT_INPUTS_VERIFIED_NOT_EXECUTED' if not execute else 'BLOCKED_OR_INCONCLUSIVE'
 except (OSError,KeyError,ValueError) as e:record['issues'].append(str(e))
 finally:(out/'manifest.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 print(record['status']);return 0 if record['status'] in ('GLOBAL_TT_REPORTS_EXECUTED_REVIEW_REQUIRED','TT_INPUTS_VERIFIED_NOT_EXECUTED') else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--openroad',default='openroad');p.add_argument('--timeout',type=int,default=300);a=p.parse_args()
 if a.timeout<1:p.error('timeout positive required')
 try:raise SystemExit(run(a.inventory,a.out,a.execute,a.openroad,a.timeout))
 except ValueError as e:p.error(str(e))
