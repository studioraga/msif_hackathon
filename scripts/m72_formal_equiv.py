#!/usr/bin/env python3
"""Fail-closed Yosys RTL-to-gates induction experiment for MSIF M7.2.
An equiv_status -assert PASS is an induction proof only under Yosys's modeled semantics.
No proof is inferred from bounded vectors, and incomplete/timeout results block.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
V = ('programmable','fixed','rom')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(root,v,mapped,models):
    e=json.loads((root/'build/m71_liberty/m71_lq/evidence.json').read_text())
    assert e['qualification']=='bounded-mapped-gate-level-validation'
    rtl=root/f'build/m71_liberty/msif_{v}.sv'
    accepted=e['architectures'][v]
    for p,k in ((rtl,'rtl_sha256'),(models,'actual_cell_models_sha256')):
        assert p.is_file() and sha(p)==accepted[k],f'{v}: {k} mismatch'
    if mapped.resolve()==(root/f'build/m71_liberty/m71_lq/msif_{v}_mapped.v').resolve():
        assert sha(mapped)==accepted['mapped_verilog_sha256'],f'{v}: mapped hash mismatch'
    else:
        assert mapped.is_file() and mapped.stat().st_size>0
    return rtl

def yosys_script(rtl,mapped,models,top):
    # Reference and implementation share a single library model set.
    # proc is needed before equiv_make. Flatten after equivalence is generated
    # to prevent matching synthetic intermediate signals as false proof points.
    return '\n'.join([
      f'read_liberty -ignore_miss_func {models}',
      f'read_verilog -sv {rtl}', f'rename {top} msif_gold',
      f'read_verilog -sv {mapped}', f'rename {top} msif_gate',
      'proc',
      # Resolve constant-initialized coefficient arrays in A/C before miter.
      'memory_map',
      'opt_clean',
      # Do not run hierarchy -top on either design before equiv_make: it
      # prunes the other top module and destroys the miter input.
      # Check the combined miter only after equiv_make.

      'equiv_make msif_gold msif_gate msif_equiv',
      'hierarchy -check -top msif_equiv',
      'flatten', 'opt_clean',
      # SAT does not model async Liberty FFs; this is explicitly a sampled-clock abstraction.
      'async2sync',
      'opt_clean',
      'check -assert',
      'equiv_simple',
      'equiv_induct -seq 32',
      'equiv_status -assert',
      'stat', ''])

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--yosys',default='yosys');p.add_argument('--gate-dir',type=Path);a=p.parse_args()
    root=a.root.resolve(); out=a.out.resolve()
    if out.exists():print('BLOCKED: output exists',file=sys.stderr);return 2
    out.mkdir(parents=True)
    report={'schema':'msif-m72-formal-v3','status':'NOT_VERIFIED','proof_scope':'CLOCK_SAMPLED_ASYNC2SYNC_ABSTRACTION_NOT_FULL_ASYNC_RESET_PROOF','variants':{},'g1':'NOT_VERIFIED'}
    try:
      for v in V:
        mapped=(a.gate_dir/f'{v}.v') if a.gate_dir else root/f'build/m71_liberty/m71_lq/msif_{v}_mapped.v'
        mapped=mapped.resolve();models=(root/f'build/m71_liberty/m71_lq/msif_{v}_functional_models.v').resolve()
        rtl=check(root,v,mapped,models)
        # The M7.1-LQ preprocessed Verilog model contains UDP primitives
        # unsupported by Yosys's Verilog frontend. Read the pinned Liberty
        # instead, WITHOUT -lib (which would create black boxes).
        liberty=(root/'build/m71_liberty/m71_lq/evidence.json')
        e=json.loads(liberty.read_text())
        libpath=Path(os.environ.get('MSIF_M72_LIBERTY',
          os.path.expanduser('~/eda/qualified-pdks/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'))).resolve()
        if not libpath.is_file() or sha(libpath)!=e['liberty_sha256']:
          raise ValueError('missing or mismatched pinned SKY130HD TT Liberty')
        tcl=out/f'{v}.ys';tcl.write_text(yosys_script(rtl.resolve(),mapped,libpath,f'msif_{v}'))
        used=json.loads((root/f'build/m71_liberty/m71_lq/msif_{v}_mapped.json').read_text())['modules'][f'msif_{v}']['cells']
        used_types=sorted({c['type'] for c in used.values()})
        rec={'used_cell_types':used_types,'used_cell_count':len(used),'rtl_sha256':sha(rtl),'mapped_sha256':sha(mapped),'models_sha256':sha(models),'formal_liberty_sha256':sha(libpath),'formal_model_mode':'PINNED_LIBERTY_USED_CELLS_CLOCK_SAMPLED_ASYNC2SYNC_NON_SIGNOFF','script_sha256':sha(tcl),'status':'NOT_EXECUTED'}
        if a.execute:
          r=subprocess.run([a.yosys,'-s',str(tcl)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=1800)
          log=out/f'{v}.log';log.write_text(r.stdout);rec['log_sha256']=sha(log);rec['exit_code']=r.returncode
          rec['status']='CLOCK_SAMPLED_INDUCTION_REPORTED_REVIEW_REQUIRED' if r.returncode==0 and 'Equivalence successfully proven!' in r.stdout and not ('blackbox' in r.stdout.lower() or 'unproven' in r.stdout.lower()) else 'BLOCKED_OR_INCONCLUSIVE'
        report['variants'][v]=rec
    except (AssertionError,KeyError,OSError,subprocess.TimeoutExpired,ValueError) as ex:
      report['error']=str(ex)
    report['status']='ALL_CLOCK_SAMPLED_RUNS_REVIEW_REQUIRED' if len(report['variants'])==3 and all(x['status']=='CLOCK_SAMPLED_INDUCTION_REPORTED_REVIEW_REQUIRED' for x in report['variants'].values()) else 'NOT_VERIFIED'
    (out/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':report['status'],'manifest':str(out/'manifest.json')}))
    return 0 if not a.execute or report['status']=='ALL_CLOCK_SAMPLED_RUNS_REVIEW_REQUIRED' else 2
if __name__=='__main__':sys.exit(main())
