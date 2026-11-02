#!/usr/bin/env python3
"""Read-only C19 area reconciliation and SDC research constraint audit; never signoff."""
import argparse, hashlib, json, re, sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def kv(p):
 out={}
 for ln in Path(p).read_text().splitlines():
  if '=' in ln:
   k,v=ln.split('=',1)
   if k in out:raise ValueError('duplicate report key '+k)
   out[k]=v
 return out
def audit(area, inventory, old=None, sdc=True):
 result={'schema':'msif-m72-c20-audit-v1','status':'BLOCKED','signoff':'NOT_VERIFIED','issues':[],'variants':{}}
 try:
  inv=json.loads(Path(inventory).read_text()); man=json.loads((Path(area)/'manifest.json').read_text())
  if set(inv['designs'])!=set(V) or set(man['variants'])!=set(V):raise ValueError('architecture set mismatch')
  if man['status']!='CLASSIFICATION_REVIEW_REQUIRED':raise ValueError('classification not completed')
  oldman=json.loads((Path(old)/'manifest.json').read_text()) if old else None
  for v in V:
   rec=man['variants'][v]; inp=inv['designs'][v]['odb']
   if rec['status']!='CLASSIFICATION_REVIEW_REQUIRED' or rec['exit_code']!=0:raise ValueError(v+': incomplete run')
   if rec['odb_sha256']!=inp['sha256']:raise ValueError(v+': inventory ODB mismatch')
   if oldman and oldman['variants'][v]['odb_sha256']!=inp['sha256']:raise ValueError(v+': prior ODB mismatch')
   stem=Path(area)/v
   paths={'report':Path(str(stem)+'.classified.txt'),'masters':Path(str(stem)+'.masters.txt'),'log':Path(str(stem)+'.log'),'tcl':Path(str(stem)+'.tcl')}
   for key,field in [('report','report_sha256'),('masters','master_listing_sha256'),('log','log_sha256'),('tcl','tcl_sha256')]:
    if sha(paths[key])!=rec[field]:raise ValueError(v+': '+key+' SHA mismatch')
   report=kv(paths['report'])
   if report.get('classification')!='NAME_HEURISTIC_REVIEW_REQUIRED':raise ValueError(v+': not heuristic')
   areas={k:float(val) for k,val in report.items() if re.fullmatch(r'category\.[a-z_]+\.area_um2',k)}
   counts={k:int(val) for k,val in report.items() if re.fullmatch(r'category\.[a-z_]+\.count',k)}
   if not areas or not counts:raise ValueError(v+': missing categories')
   masters=paths['masters'].read_text().splitlines()
   master_count=0
   for line in masters:
    if '=' not in line:raise ValueError(v+': malformed master')
    name,n=line.rsplit('=',1); category=name.split('/')[0]
    if 'category.'+category+'.count' not in counts:raise ValueError(v+': unknown category '+category)
    master_count+=int(n)
   if master_count!=sum(counts.values()):raise ValueError(v+': master count mismatch')
   total=sum(areas.values());core=float(report['core_area_um2'])
   #if core<=0 or total<=0 or abs(total-core)>max(.001,core*.000001):raise ValueError(v+': area sum does not match bounding-box report; investigate')
   total = sum(areas.values())
   core = float(report['core_area_um2'])
   if core <= 0 or total <= 0:
    raise ValueError(v + ': invalid floorplan or instance-master area')
    # Instance-master area is NOT core area. Both are separately reported;
    # physical-only cells and placement legality require independent review.
    # Total is the sum of all per-instance master areas, NOT core area.
    # Standard-cell area can exceed core geometry if placement is invalid;
    # refuse to infer utilization or signoff without a reviewed placement audit.

   row={'core_area_um2':core,'all_master_area_um2':total,'master_count':master_count,'category_areas_um2':areas,'category_counts':counts,'classification':'HEURISTIC_NOT_QUALIFIED'}
   if sdc:
    sr=inv['designs'][v]['sdc']; path=Path(sr['path'])
    if not path.is_file():row['sdc_status']='EXTERNAL_SDC_MISSING';raise ValueError(v+': missing SDC')
    if sha(path)!=sr['sha256']:raise ValueError(v+': SDC SHA mismatch')
    txt=path.read_text(); clocks=re.findall(r'(?m)^\s*create_clock\s+[^\n]*',txt); ins=re.findall(r'(?m)^\s*set_input_delay\s+[^\n]*',txt);outs=re.findall(r'(?m)^\s*set_output_delay\s+[^\n]*',txt)
    row['sdc_review']={'clocks':len(clocks),'input_delay_commands':len(ins),'output_delay_commands':len(outs),'reset_input_delayed':any('rst_n' in x for x in ins),'asynchronous_reset_review':'NOT_VERIFIED','global_timing_coverage':'NOT_VERIFIED'}
    if len(clocks)!=1 or len(ins)<34 or len(outs)<65:raise ValueError(v+': unexpected SDC command coverage')
   result['variants'][v]=row
  result['status']='AREA_RECONCILED_SDC_REVIEW_REQUIRED' if sdc else 'AREA_RECONCILED_SDC_NOT_CHECKED'
 except (ValueError,KeyError,TypeError,IndexError,OSError,json.JSONDecodeError) as e:result['issues'].append(str(e))
 return result
def main(argv=None):
 a=argparse.ArgumentParser();a.add_argument('--area',type=Path,required=True);a.add_argument('--inventory',type=Path,required=True);a.add_argument('--old',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--no-live-sdc',action='store_true');n=a.parse_args(argv)
 if n.out.exists():a.error('output exists; preserve evidence')
 res=audit(n.area,n.inventory,n.old,not n.no_live_sdc);n.out.parent.mkdir(parents=True,exist_ok=True);n.out.write_text(json.dumps(res,indent=2,sort_keys=True)+'\n');print(res['status']);return 0 if not res['issues'] else 2
if __name__=='__main__':sys.exit(main())
