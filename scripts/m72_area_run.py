#!/usr/bin/env python3
"""Load final OpenDB, export reproducible categorized physical area (not signoff)."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
V=('programmable','fixed','rom')
def main():
 a=argparse.ArgumentParser();a.add_argument('--flow',required=True,type=Path);a.add_argument('--out',required=True,type=Path);ns=a.parse_args()
 ns.out.mkdir(parents=True,exist_ok=True)
 hook=Path(__file__).with_name('m72_final_area.tcl').resolve()
 rows={}
 for v in V:
  odb=ns.flow/'results/sky130hd'/f'msif_{v}'/f'msif_m72_{v}_normalized_v2/6_final.odb'
  if not odb.is_file():print('BLOCKED missing',odb,file=sys.stderr);return 2
  tcl=ns.out/f'{v}.tcl';output=ns.out/f'{v}.area.txt'
  tcl.write_text(f'read_db {{{odb.resolve()}}}\nsource {{{hook}}}\n')
  env=dict(os.environ,MSIF_M72_AREA_OUT=str(output.resolve()))
  p=subprocess.run(['openroad','-exit',str(tcl)],env=env,capture_output=True,text=True)
  (ns.out/f'{v}.log').write_text(p.stdout+p.stderr)
  if p.returncode or not output.is_file():print('BLOCKED area export',v,p.returncode,file=sys.stderr);return 2
  values={}
  for line in output.read_text().splitlines():
   k,x=line.split('=',1);values[k]=float(x) if not k.endswith('.count') else int(x)
  rows[v]={'area_values':values,'odb_sha256':hashlib.sha256(odb.read_bytes()).hexdigest(),'qualification':'MEASURED_OPENDB_GEOMETRY_NOT_SIGNOFF'}
 (ns.out/'area-ledger.json').write_text(json.dumps({'status':'RESEARCH_AREA_NOT_SIGNOFF','variants':rows},indent=2)+'\n')
 print('RESEARCH_AREA_NOT_SIGNOFF',ns.out/'area-ledger.json');return 0
if __name__=='__main__':raise SystemExit(main())
