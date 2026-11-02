#!/usr/bin/env python3
"""Bind ORFS pre/post-ECO exports to hashes. Presence is not equivalence."""
import argparse, hashlib, json, sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(flow,variant_suffix):
 d={}
 for v in V:
  base=flow/'results'/'sky130hd'/f'msif_{v}'/f'msif_m72_{v}_{variant_suffix}'
  names=('1_2_yosys.v','1_synth_lec.v','4_before_rsz_lec.v','4_after_rsz_lec.v','6_final_lec.v','6_final.v','6_final.odb','6_final.spef')
  missing=[n for n in names if not (base/n).is_file() or not (base/n).stat().st_size]
  d[v]={'files':{n:sha(base/n) for n in names if n not in missing},'missing':missing,'post_route_equivalence':'NOT_VERIFIED'}
 return {'schema':'msif-m72-eco-inventory-v1','status':'INVENTORY_PRESENT_NOT_EQUIVALENCE' if all(not x['missing'] for x in d.values()) else 'BLOCKED','variants':d}
def main():
 p=argparse.ArgumentParser();p.add_argument('--flow',type=Path,required=True);p.add_argument('--variant-suffix',default='exact_lq_singlecore_v2');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():p.error('output already exists')
 r=audit(a.flow,a.variant_suffix);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['status']);return 0 if r['status'].startswith('INVENTORY_') else 2
if __name__=='__main__':sys.exit(main())
