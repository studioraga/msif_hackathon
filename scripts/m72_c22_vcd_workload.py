#!/usr/bin/env python3
"""Re-simulate exact routed A/B/C with copied 260-vector TBs to capture VCD.
No power or signoff inference. SHA-check C16 model and accepted TB manifests.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def scan_vcd(path):
 # Parse only scalar/vector transition records and validate nonempty time/activity; no claims of power coverage.
 ids={};scope=[];times=set();transitions=0;unknown=0;top_inputs={};clock_toggles=0
 with path.open(errors='replace') as fh:
  definitions=True;input_ids={}
  for line in fh:
   s=line.strip()
   if definitions:
    if s.startswith('$scope '):scope.append(s.split()[2])
    elif s.startswith('$upscope '):
     if scope:scope.pop()
    elif s.startswith('$var '):
     q=s.split()
     if len(q)>=5:
      identifier=q[3];name=q[4];ids[identifier]='.'.join(scope+[name]);
      if len(scope)==1 and scope[0]=='tb' and name in ('clk','rst_n','in_valid','activations'):input_ids[identifier]=name
    elif '$enddefinitions' in s:definitions=False
    continue
   if s.startswith('#'):
    try:times.add(int(s[1:]))
    except ValueError:pass
   elif s and s[0] in '01xXzZ' and len(s)>1:
    value=s[0];identifier=s[1:]
    if identifier in ids:
     transitions+=1;unknown+=int(value in 'xXzZ')
     if identifier in input_ids:
      top_inputs.setdefault(input_ids[identifier],[]).append((max(times) if times else 0,value))
      if input_ids[identifier]=='clk':clock_toggles+=1
   elif s.startswith('b'):
    q=s.split()
    if len(q)==2 and q[1] in ids:
     transitions+=1;unknown+=int('x' in q[0].lower() or 'z' in q[0].lower())
     if q[1] in input_ids:top_inputs.setdefault(input_ids[q[1]],[]).append((max(times) if times else 0,q[0][1:]))
 return {'identifier_count':len(ids),'time_points':len(times),'end_time_ticks':max(times) if times else None,'transition_records':transitions,'unknown_records':unknown,'clock_records':clock_toggles,'inputs':top_inputs}
def run(root,flow,gls,out,execute=False):
 root,flow,gls,out=map(Path,(root,flow,gls,out))
 if out.exists():raise ValueError('output already exists; preserve evidence')
 out.mkdir(parents=True)
 manifest={'schema':'msif-m72-c22-vcd-v1','status':'BLOCKED','power':'NOT_VERIFIED','annotation_coverage':'NOT_VERIFIED','issues':[],'variants':{}}
 try:
  prev=json.loads((gls/'manifest.json').read_text());evidence=json.loads((root/'build/m71_liberty/m71_lq/evidence.json').read_text())
  if prev.get('status')!='BOUNDED_FINAL_GLS_ALL_PASS_NOT_EQUIVALENCE':raise ValueError('C16 GLS not passed')
  if set(prev['variants'])!=set(V):raise ValueError('incomplete C16 variants')
  traces={}
  for v in V:
   old=prev['variants'][v];top='msif_'+v
   final=flow/'results/sky130hd'/top/f'msif_m72_{v}_exact_lq_singlecore_v2'/'6_final.v'
   tb=root/'build/m71_liberty/m71_lq'/f'{top}_gate_tb.sv';models=gls/f'{v}.routed.functional_models.v'
   known={'final_netlist':final,'testbench':tb};
   for k,p in known.items():
    if not p.is_file() or sha(p)!=old['inputs'][k]['sha256']:raise ValueError(f'{v} {k} hash mismatch')
   if not models.is_file() or sha(models)!=old.get('selected_models_sha256'):raise ValueError(f'{v} routed models hash mismatch')
   if sha(tb)!=old['inputs']['testbench']['sha256']:raise ValueError('TB changed')
   if sha(root/'build/m71_liberty/m71_lq'/f'{top}_functional_models.v') != evidence['architectures'][v]['actual_cell_models_sha256']:raise ValueError('M71 baseline drift')
   source=tb.read_text();m=re.search(r'\bmodule\s+tb\s*;',source)
   if m is None or '$dumpfile' in source:raise ValueError('unexpected testbench source')
   vcd=out/f'{v}.vcd';insert=f'\ninitial begin $dumpfile("{vcd.resolve()}"); $dumpvars(0,tb); end\n';copy=out/f'{v}.activity_tb.sv';copy.write_text(source[:m.end()]+insert+source[m.end():]);entry={'status':'INPUTS_VERIFIED_NOT_EXECUTED','input_shas':{k:sha(p) for k,p in known.items()},'models_sha256':sha(models),'instrumented_tb_sha256':sha(copy)};manifest['variants'][v]=entry
   if not execute:continue
   binary=out/f'{v}.vvp';clog=out/f'{v}.compile.log';slog=out/f'{v}.simulate.log'
   with clog.open('wb') as f:c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(models),str(final),str(copy)],stdout=f,stderr=subprocess.STDOUT,timeout=180)
   entry['compile_rc']=c.returncode;entry['compile_log_sha256']=sha(clog)
   if c.returncode:entry['status']='COMPILE_FAILED';continue
   with slog.open('wb') as f:s=subprocess.run(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT,timeout=180)
   entry['simulate_rc']=s.returncode;entry['simulate_log_sha256']=sha(slog)
   if s.returncode or f'PASS {v} 260 vectors' not in slog.read_text(errors='replace') or not vcd.is_file() or vcd.stat().st_size==0:entry['status']='SIMULATION_FAILED';continue
   trace=scan_vcd(vcd);entry['waveform']={k:value for k,value in trace.items() if k!='inputs'};entry['vcd_sha256']=sha(vcd);entry['vcd_bytes']=vcd.stat().st_size
   if trace['time_points']<10 or trace['clock_records']<20 or trace['transition_records']<100:entry['status']='WAVEFORM_INSUFFICIENT';continue
   entry['status']='BOUNDED_VCD_CAPTURED_NOT_POWER';traces[v]=trace['inputs']
  states=[r['status'] for r in manifest['variants'].values()]
  if not execute:manifest['status']='INPUTS_VERIFIED_NOT_EXECUTED'
  elif len(traces)==3:
   # identical top-level clock/reset/valid/activation activity is a necessary matched workload condition.
   keys=('clk','rst_n','in_valid','activations')
   diffs=[k for k in keys if any(traces[v].get(k)!=traces[V[0]].get(k) for v in V[1:])]
   manifest['matched_inputs']=not diffs;manifest['input_trace_mismatches']=diffs
   manifest['status']='MATCHED_BOUNDED_VCD_CAPTURED_NOT_POWER' if not diffs else 'INPUT_WAVEFORMS_DIFFER_NOT_COMPARABLE'
  else:manifest['status']='BLOCKED_OR_INCONCLUSIVE'
 except (OSError,ValueError,KeyError,subprocess.TimeoutExpired,json.JSONDecodeError) as e:manifest['issues'].append(str(e))
 finally:(out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(manifest['status']);return 0 if manifest['status'] in ('MATCHED_BOUNDED_VCD_CAPTURED_NOT_POWER','INPUTS_VERIFIED_NOT_EXECUTED') else 2
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--flow',type=Path,required=True);p.add_argument('--gls',type=Path,default=Path('build/m72/postroute-gls-run-c16'));p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
 try:raise SystemExit(run(a.root,a.flow,a.gls,a.out,a.execute))
 except ValueError as e:p.error(str(e))
