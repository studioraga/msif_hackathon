#!/usr/bin/env python3
"""Audit immutable closure17 exact-LQ reports; never infer functional area/signoff."""
import argparse, hashlib, json, math, re
from pathlib import Path
V=('programmable','fixed','rom')
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(root, inventory):
 result={'schema':'msif-m72-c18-area-audit-v1','status':'BLOCKED','issues':[], 'architectures':{}, 'qualification':'RESEARCH_NOT_SIGNOFF'}
 try:
  data=json.loads((root/'manifest.json').read_text()); inv=json.loads(inventory.read_text())
  if data.get('status')!='AREA_EXTRACTED_REVIEW_REQUIRED' or set(data.get('variants',{}))!=set(V) or set(inv.get('designs',{}))!=set(V):raise ValueError('missing or invalid A/B/C manifest')
  for v in V:
   row=data['variants'][v]; evidence={}
   for suffix,key in (('.area.txt','report_sha256'),('.log','log_sha256'),('.tcl','tcl_sha256')):
    p=root/(v+suffix)
    if not p.is_file() or digest(p)!=row.get(key):raise ValueError(f'{v}: changed or absent {suffix}')
   if row.get('exit_code')!=0 or row.get('status')!='AREA_EXTRACTED_REVIEW_REQUIRED':raise ValueError(f'{v}: execution not successful')
   pinned=inv['designs'][v]['odb'];evidence['odb_sha256']=row['odb_sha256']
   if row['odb_sha256']!=pinned['sha256']:raise ValueError(f'{v}: ODB pin mismatch')
   report={}
   for line in (root/(v+'.area.txt')).read_text().splitlines():
    key,sep,raw=line.partition('=')
    if not sep or key in report:raise ValueError(f'{v}: invalid or duplicate report key')
    val=float(raw)
    if not math.isfinite(val) or val<0:raise ValueError(f'{v}: invalid numeric area')
    report[key]=val
   if set(report)!=set(row.get('area',{})):raise ValueError(f'{v}: report/manifest mismatch')
   for key,val in report.items():
    if not math.isclose(val,row['area'][key],rel_tol=1e-10,abs_tol=1e-8):raise ValueError(f'{v}: value mismatch {key}')
   categories=[k for k in report if re.fullmatch(r'category\.[^.]+\.area_um2',k)]
   total=sum(report[k] for k in categories);core=report.get('core_area_um2',0)
   if core<=0 or total<=0:raise ValueError(f'{v}: empty area')
   evidence.update(core_area_um2=core,all_instance_master_area_um2=total,instance_area_over_core=total/core,raw_other_um2=report.get('category.other.area_um2',0),raw_other_not_functional_area=True)
   result['architectures'][v]=evidence
  result['status']='AREA_RECEIPTS_INTACT_CLASSIFICATION_PENDING'
 except (OSError,ValueError,KeyError,TypeError, json.JSONDecodeError) as e:result['issues'].append(str(e))
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--area',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():p.error('refusing to overwrite audit evidence')
 r=check(a.area,a.inventory);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['status']);return 0 if not r['issues'] else 2
if __name__=='__main__':raise SystemExit(main())
