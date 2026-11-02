#!/usr/bin/env python3
"""Run accepted M7.1 bounded vectors on exact-route Verilog, never claim LEC.

Uses accepted functional model; missing newly inserted cells fail compilation.
The model must be extended from actual SKY130 sources in a separately audited step.
"""
import argparse, hashlib, json, os, subprocess, sys, re
from m71_cell_models import assemble
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def routed_cell_types(final):
 text=Path(final).read_text(errors='replace')
 # ORFS write_verilog emits one SKY130 cell instance per line, optional parameters excluded.
 found=set(re.findall(r'(?m)^\s*(sky130_fd_sc_hd__[A-Za-z0-9_]+)\s+\\?[^\s(]+\s*\(',text))
 if not found:
  raise ValueError('no SKY130 instance types discovered in final Verilog')
 return sorted(found)

def check_source(source):
 source=Path(source).resolve(strict=True)
 if not (source/'cells').is_dir() or not (source/'models').is_dir():
  raise ValueError('SKY130_HD must contain cells/ and models/')
 return source

def run(root,flow,out,execute=False,sky130_hd=None):
 root,flow,out=Path(root).resolve(),Path(flow).resolve(),Path(out).resolve()
 if out.exists():raise ValueError('output exists: '+str(out))
 out.mkdir(parents=True)
 result={'schema':'msif-m72-postroute-gls-v1','status':'NOT_VERIFIED','functional_equivalence':'NOT_VERIFIED','g1':'NOT_VERIFIED','variants':{}}
 evidence=json.loads((root/'build/m71_liberty/m71_lq/evidence.json').read_text())
 if evidence.get('qualification')!='bounded-mapped-gate-level-validation':raise ValueError('unexpected baseline qualification')
 for v in V:
  top='msif_'+v
  baseline=root/'build/m71_liberty/m71_lq'
  final=flow/'results/sky130hd'/top/(f'msif_m72_{v}_exact_lq_singlecore_v2')/'6_final.v'
  tb=baseline/f'{top}_gate_tb.sv'; models=baseline/f'{top}_functional_models.v'
  rec={'status':'BLOCKED','inputs':{}}
  result['variants'][v]=rec
  try:
   if not all(p.is_file() and p.stat().st_size>0 for p in (final,tb,models)):raise ValueError('missing final netlist/testbench/functional models')
   if sha(models)!=evidence['architectures'][v]['actual_cell_models_sha256']:raise ValueError('baseline models hash drift')
   rec['inputs']={n:{'path':str(p),'sha256':sha(p)} for n,p in [('final_netlist',final),('testbench',tb),('functional_models',models)]}
   rec['status']='INPUTS_PRESENT_NOT_EXECUTED'
   rec['final_cell_types']=routed_cell_types(final)
   if execute:
    binary=out/f'{v}.vvp';clog=out/f'{v}.compile.log';slog=out/f'{v}.simulate.log'
    sim_models=models
    if sky130_hd is not None:
     source=check_source(sky130_hd)
     # This is the union of cells ACTUALLY used by the final netlist, not the M7.1 mapping.
     types=rec['final_cell_types']
     fake={'modules':{top:{'cells':{str(i):{'type':typ} for i,typ in enumerate(types)}}}}
     sim_models=out/f'{v}.routed.functional_models.v'
     provenance=assemble(fake,top,source,sim_models)
     rec['routed_models']={'sha256':sha(sim_models),'provenance_sha256':sha(out/f'{v}.routed.functional_models.provenance.json'),
                           'source_root':str(source),'cell_type_count':len(types)}
    rec['selected_models_sha256']=sha(sim_models)
    with clog.open('w') as f:
     c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(sim_models),str(final),str(tb)],stdout=f,stderr=subprocess.STDOUT,timeout=180)
    rec['compile_exit']=c.returncode;rec['compile_log_sha256']=sha(clog)
    if c.returncode:rec['status']='COMPILE_FAILED_REVIEW_MODELS_AND_FINAL_CELL_INVENTORY';continue
    with slog.open('w') as f:
     s=subprocess.run(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT,timeout=180)
    rec['simulation_exit']=s.returncode;rec['simulation_log_sha256']=sha(slog)
    text=slog.read_text(errors='replace')
    marker=f'PASS {v} 260 vectors'
    rec['status']='BOUNDED_FINAL_GLS_PASS_NOT_EQUIVALENCE' if s.returncode==0 and marker in text and 'FAIL' not in text else 'SIMULATION_FAILED'
  except (OSError,subprocess.TimeoutExpired,ValueError) as ex:rec['status']='BLOCKED';rec['error']=str(ex)
 result['status']='BOUNDED_FINAL_GLS_ALL_PASS_NOT_EQUIVALENCE' if all(x['status']=='BOUNDED_FINAL_GLS_PASS_NOT_EQUIVALENCE' for x in result['variants'].values()) else 'NOT_VERIFIED'
 (out/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(result['status']);return 0 if result['status']=='BOUNDED_FINAL_GLS_ALL_PASS_NOT_EQUIVALENCE' or (not execute and all(x['status']=='INPUTS_PRESENT_NOT_EXECUTED' for x in result['variants'].values())) else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sky130-hd',type=Path,default=None,help='verified upstream SKY130 HD source (cells/ and models/); required for final-cell model extension');p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--flow',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
 try:sys.exit(run(a.root,a.flow,a.out,a.execute,a.sky130_hd))
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print('BLOCKED:',e,file=sys.stderr);sys.exit(2)
