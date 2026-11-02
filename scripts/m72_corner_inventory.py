#!/usr/bin/env python3
"""Read-only SKY130HD corner and exact-route evidence inventory.
Creates NOT_VERIFIED template; never fabricates missing Liberty/RC corners.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--orfs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--suffix',default='exact_lq_singlecore_v2');a=p.parse_args()
 platform=a.orfs/'flow/platforms/sky130hd';flow=a.orfs/'flow'
 if not platform.is_dir() or a.out.exists():p.error('missing platform or output already exists')
 libs=sorted((platform/'lib').glob('sky130_fd_sc_hd__*.lib'))
 rc=platform/'rcx_patterns.rules';setrc=platform/'setRC.tcl'
 result={'schema':'msif-m72-corner-inventory-v1','status':'CORNER_DEPENDENCIES_NOT_VERIFIED','libraries':[], 'rc':{},'designs':{},'approval':'NOT_VERIFIED'}
 for lib in libs:
  txt=lib.read_text(errors='replace'); result['libraries'].append({'path':str(lib.resolve()),'sha256':sha(lib),'name':lib.name,'operating_conditions':re.findall(r'operating_conditions\s*\(\s*([^)]*)',txt)[:8]})
 for key,path in (('rcx_rules',rc),('layer_rc',setrc)):
  result['rc'][key]={'exists':path.is_file(),'path':str(path),'sha256':sha(path) if path.is_file() else None,'calibration':'NOT_VERIFIED'}
 for v in V:
  d=flow/'results/sky130hd'/f'msif_{v}'/f'msif_m72_{v}_{a.suffix}'
  files={k:d/n for k,n in (('odb','6_final.odb'),('spef','6_final.spef'),('sdc','6_1_fill.sdc'))}
  result['designs'][v]={k:({'path':str(path),'sha256':sha(path)} if path.is_file() else {'status':'MISSING','path':str(path)}) for k,path in files.items()}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(result['status']);return 0
if __name__=='__main__':sys.exit(main())
