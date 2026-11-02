#!/usr/bin/env python3
"""SHA-pinned exact_lq_singlecore_v2 final ODB area collector; research only."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--execute',action='store_true');p.add_argument('--openroad',default='openroad');p.add_argument('--timeout',type=int,default=300);a=p.parse_args(argv)
 if a.out.exists():p.error('output exists; preserve previous evidence')
 a.out.mkdir(parents=True)
 state={'schema':'msif-m72-exact-lq-area-v1','status':'BLOCKED','qualification':'RESEARCH_NOT_SIGNOFF','variants':{},'issues':[]}
 try:
  inv=json.loads(a.inventory.read_text());assert set(inv['designs'])==set(V),'incomplete corner inventory'
  hook=Path(__file__).with_name('m72_final_area.tcl').resolve(strict=True)
  binary=shutil.which(a.openroad) if a.execute else None
  if a.execute and binary is None:raise ValueError('OpenROAD executable missing')
  for v in V:
   record=inv['designs'][v]['odb'];odb=Path(record['path'])
   if not odb.is_file() or sha(odb)!=record['sha256']:raise ValueError(f'{v}: ODB absent or changed')
   # This is exact ODB from the existing SHA-bound corner inventory, never normalized_v2.
   if 'exact_lq_singlecore_v2' not in str(odb):raise ValueError(f'{v}: not an exact-LQ route')
   script=a.out/f'{v}.tcl';out=a.out/f'{v}.area.txt';log=a.out/f'{v}.log'
   script.write_text(f'read_db {{{odb.resolve()}}}\nsource {{{hook}}}\n')
   row={'odb_sha256':sha(odb),'tcl_sha256':sha(script),'status':'INPUTS_VERIFIED_NOT_EXECUTED'};state['variants'][v]=row
   if not a.execute:continue
   env=dict(os.environ,MSIF_M72_AREA_OUT=str(out.resolve()))
   with log.open('wb') as f:
    try:proc=subprocess.run([binary,'-exit',str(script.resolve())],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout)
    except subprocess.TimeoutExpired:row['status']='TIMEOUT';continue
   row['exit_code']=proc.returncode;row['log_sha256']=sha(log)
   if proc.returncode!=0 or not out.is_file() or out.stat().st_size==0:row['status']='BLOCKED';continue
   values={}
   for line in out.read_text().splitlines():
    k,sep,vlu=line.partition('=')
    if not sep or k in values:raise ValueError(f'{v}: malformed area report')
    values[k]=int(vlu) if k.endswith('.count') or k=='dbu_per_micron' else float(vlu)
   if values.get('core_area_um2',0)<=0 or not any(k.endswith('.area_um2') for k in values):raise ValueError(f'{v}: missing area fields')
   row.update(status='AREA_EXTRACTED_REVIEW_REQUIRED',area=values,report_sha256=sha(out))
  statuses=[d['status'] for d in state['variants'].values()]
  state['status']='AREA_EXTRACTED_REVIEW_REQUIRED' if a.execute and all(s=='AREA_EXTRACTED_REVIEW_REQUIRED' for s in statuses) else ('AREA_INPUTS_VERIFIED_NOT_EXECUTED' if not a.execute and len(statuses)==3 else 'BLOCKED')
 except (AssertionError,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:state['issues'].append(str(e))
 finally:(a.out/'manifest.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
 print(state['status']);return 0 if state['status'] in ('AREA_EXTRACTED_REVIEW_REQUIRED','AREA_INPUTS_VERIFIED_NOT_EXECUTED') else 2
if __name__=='__main__':sys.exit(main())
