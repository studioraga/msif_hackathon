#!/usr/bin/env python3
"""Run C18 name-heuristic per-master classification on hash-pinned exact-LQ ODBs."""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
from m72_c18_area_audit import digest
V=('programmable','fixed','rom')
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--openroad',default='openroad');p.add_argument('--timeout',type=int,default=300);a=p.parse_args(argv)
 if a.out.exists():p.error('output exists; retain previous evidence')
 a.out.mkdir(parents=True)
 state={'schema':'msif-m72-c18-classified-area-v1','status':'BLOCKED','qualification':'RESEARCH_NOT_SIGNOFF','variants':{},'issues':[]}
 try:
  inv=json.loads(a.inventory.read_text()); assert set(inv['designs'])==set(V)
  hook=Path(__file__).with_name('m72_c18_classified_area.tcl').resolve(strict=True)
  exe=shutil.which(a.openroad) if a.execute else None
  if a.execute and exe is None:raise ValueError('OpenROAD not found')
  for v in V:
   rec=inv['designs'][v]['odb'];odb=Path(rec['path'])
   if 'exact_lq_singlecore_v2' not in str(odb) or not odb.is_file() or digest(odb)!=rec['sha256']:raise ValueError(v+': ODB missing, changed or not exact-LQ')
   out=a.out/(v+'.classified.txt');masters=a.out/(v+'.masters.txt');log=a.out/(v+'.log');tcl=a.out/(v+'.tcl')
   tcl.write_text(f'read_db {{{odb.resolve()}}}\nsource {{{hook}}}\n')
   row={'odb_sha256':digest(odb),'tcl_sha256':digest(tcl),'status':'INPUTS_VERIFIED_NOT_EXECUTED'};state['variants'][v]=row
   if not a.execute:continue
   env=dict(os.environ,MSIF_M72_AREA_OUT=str(out.resolve()),MSIF_M72_MASTERS_OUT=str(masters.resolve()))
   with log.open('wb') as f:
    try:r=subprocess.run([exe,'-exit',str(tcl.resolve())],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=a.timeout)
    except subprocess.TimeoutExpired:row['status']='TIMEOUT';continue
   row.update(exit_code=r.returncode,log_sha256=digest(log))
   if r.returncode!=0 or not out.is_file() or not masters.is_file() or 'M72_C18_AREA_CLASSIFIED_REVIEW_REQUIRED' not in log.read_text():row['status']='BLOCKED';continue
   lines=out.read_text()
   if 'classification=NAME_HEURISTIC_REVIEW_REQUIRED' not in lines or 'core_area_um2=' not in lines:raise ValueError(v+': invalid classification report')
   row.update(status='CLASSIFICATION_REVIEW_REQUIRED',report_sha256=digest(out),master_listing_sha256=digest(masters))
  statuses=[r['status'] for r in state['variants'].values()]
  if len(statuses)==3 and all(s=='CLASSIFICATION_REVIEW_REQUIRED' for s in statuses):state['status']='CLASSIFICATION_REVIEW_REQUIRED'
  elif not a.execute and len(statuses)==3:state['status']='AREA_INPUTS_VERIFIED_NOT_EXECUTED'
 except (OSError,ValueError,KeyError,AssertionError,TypeError,json.JSONDecodeError) as e:state['issues'].append(str(e))
 finally:(a.out/'manifest.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
 print(state['status']);return 0 if state['status'] in ('CLASSIFICATION_REVIEW_REQUIRED','AREA_INPUTS_VERIFIED_NOT_EXECUTED') else 2
if __name__=='__main__':sys.exit(main())
