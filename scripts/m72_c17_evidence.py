#!/usr/bin/env python3
"""Cross-check immutable routed-GLS and TT evidence, never infer signoff."""
import argparse,hashlib,json,re,sys
from pathlib import Path
V=('programmable','fixed','rom')
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''): h.update(c)
 return h.hexdigest()
def audit(gls,tt):
 g=json.loads((gls/'manifest.json').read_text());t=json.loads((tt/'manifest.json').read_text())
 errors=[];rows={}
 for v in V:
  a=g.get('variants',{}).get(v,{}); b=t.get('results',{}).get(v,{})
  row={'gls':a.get('status'),'tt':b.get('status')};rows[v]=row
  if row['gls']!='BOUNDED_FINAL_GLS_PASS_NOT_EQUIVALENCE': errors.append(v+': GLS status')
  if row['tt']!='STA_EXECUTED_REVIEW_REQUIRED' or b.get('exit_code')!=0: errors.append(v+': TT status')
  for suffix,record in [('compile',a),('simulate',a)]:
   p=gls/f'{v}.{suffix}.log';key=('compile_log_sha256' if suffix=='compile' else 'simulation_log_sha256')
   if not p.is_file() or digest(p)!=record.get(key): errors.append(v+': '+suffix+' integrity')
  p=gls/f'{v}.simulate.log'
  if p.is_file() and len(re.findall(rf'(?m)^PASS {v} 260 vectors$',p.read_text()))!=1: errors.append(v+': PASS marker mismatch')
  if a.get('compile_exit')!=0 or a.get('simulation_exit')!=0:errors.append(v+': simulation exit')
  models=gls/f'{v}.routed.functional_models.v'; prov=gls/f'{v}.routed.functional_models.provenance.json'
  if not models.is_file() or digest(models)!=a.get('routed_models',{}).get('sha256'):errors.append(v+': models hash')
  if not prov.is_file() or digest(prov)!=a.get('routed_models',{}).get('provenance_sha256'):errors.append(v+': provenance hash')
  if prov.is_file():
   pr=json.loads(prov.read_text());row['routed_cell_types']=len(pr.get('mapped_cell_types',[]))
   if set(pr.get('mapped_cell_types',[]))!=set(a.get('final_cell_types',[])):errors.append(v+': cell-type coverage')
  for label,rec in a.get('inputs',{}).items():
   path=Path(rec['path'])
   if path.is_file() and digest(path)!=rec['sha256']:errors.append(v+': '+label+' drift')
  lg=tt/f'{v}.log'
  if not lg.is_file() or digest(lg)!=b.get('log_sha256'):errors.append(v+': STA log integrity')
 status='GLS_TT_EVIDENCE_CONSISTENT_NOT_SIGNOFF' if not errors else 'BLOCKED'
 return {'schema':'msif-m72-c17-evidence-v1','status':status,'issues':errors,'variants':rows,'formal_equivalence':'NOT_VERIFIED','eco_equivalence':'NOT_VERIFIED','multicorner_signoff':'NOT_VERIFIED','power_signoff':'NOT_VERIFIED','g1':'NOT_VERIFIED'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--gls',type=Path,required=True);p.add_argument('--tt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():p.error('output exists; preserve evidence')
 try:r=audit(a.gls,a.tt)
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as exc:r={'schema':'msif-m72-c17-evidence-v1','status':'BLOCKED','issues':[str(exc)]}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['status']);return 0 if r['status'].startswith('GLS_TT_') else 2
if __name__=='__main__':sys.exit(main())
