#!/usr/bin/env python3
"""P2b structural import experiment (NOT a qualified post-physical equivalence proof).

Hash-pin the accepted M7.1-LQ netlists, normalize only structural
port signedness and import them via OpenROAD's Liberty+LEF-backed reader.
Produces separate ODB per architecture, never modifies LQ evidence.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

VARIANTS = ('programmable', 'fixed', 'rom')
LIB_HASH = 'ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(root, out):
    from m72 import m72_normalize
    source = root / 'build/m71_liberty/m71_lq'
    evidence = json.loads((source / 'evidence.json').read_text())
    if evidence.get('qualification') != 'bounded-mapped-gate-level-validation' or evidence.get('liberty_sha256') != LIB_HASH:
        raise ValueError('invalid LQ qualification or Liberty lineage')
    out.mkdir(parents=True, exist_ok=False)
    results={}
    for v in VARIANTS:
        inp=source/f'msif_{v}_mapped.v'
        expected=evidence['architectures'][v]['mapped_verilog_sha256']
        if not inp.is_file() or sha(inp)!=expected: raise ValueError(f'LQ netlist integrity failed: {v}')
        raw=out/f'{v}.raw.v';raw.write_bytes(inp.read_bytes())
        converted=out/f'{v}.compat.v'
        receipt=m72_normalize.run(raw,converted)
        if sha(converted)!=receipt['normalized_sha256']:raise ValueError('normalization mismatch')
        results[v]={'raw_sha256':sha(raw),'accepted_lq_sha256':expected,'normalized_sha256':sha(converted),'normalization':receipt,'import':'NOT_EXECUTED'}
    return results

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--orfs',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('build/m72/p2b-exact-lq'));ap.add_argument('--execute',action='store_true'); a=ap.parse_args()
    try:
        root=a.root.resolve();orfs=a.orfs.resolve();out=a.out.resolve()
        if not (orfs/'flow/platforms/sky130hd/config.mk').is_file():raise ValueError('missing SKY130 HD platform')
        lib=orfs/'flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
        if sha(lib)!=LIB_HASH:raise ValueError('reviewed Liberty mismatch')
        results=prepare(root,out)
        if a.execute:
            for v in VARIANTS:
                tcl=out/f'{v}.import.tcl';tcl.write_text('set p $::env(MSIF_PDK_DIR)\nread_liberty $p/lib/sky130_fd_sc_hd__tt_025C_1v80.lib\nread_lef $p/lef/sky130_fd_sc_hd.tlef\nread_lef $p/lef/sky130_fd_sc_hd_merged.lef\nread_verilog $::env(MSIF_P2B_NETLIST)\nlink_design $::env(MSIF_P2B_TOP)\nwrite_db $::env(MSIF_P2B_ODB)\nputs "PASS_P2B_STRUCTURAL_IMPORT_ONLY"\n')
                env=dict(os.environ,MSIF_PDK_DIR=str(orfs/'flow/platforms/sky130hd'),MSIF_P2B_NETLIST=str(out/f'{v}.compat.v'),MSIF_P2B_TOP=f'msif_{v}',MSIF_P2B_ODB=str(out/f'{v}.odb'))
                q=subprocess.run(['openroad','-exit',str(tcl)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
                (out/f'{v}.import.log').write_text(q.stdout)
                odb=out/f'{v}.odb'
                if q.returncode or 'PASS_P2B_STRUCTURAL_IMPORT_ONLY' not in q.stdout or not odb.is_file() or not odb.stat().st_size:
                    results[v]['import']='BLOCKED';raise ValueError(f'OpenROAD import failed: {v}')
                results[v]['import']='STRUCTURAL_IMPORT_PASS_NOT_EQUIVALENCE';results[v]['odb_sha256']=sha(odb)
        result={'schema':'msif-m72-p2b-import-v1','variants':results,'accepted_m71_lq':'BOUNDED_GATE_REGRESSION','post_import_equivalence':'NOT_VERIFIED','physical_signoff':'NOT_VERIFIED','status':'STRUCTURAL_IMPORT_EXPERIMENT_PASS' if a.execute else 'HASH_PINNED_PLAN_ONLY'}
        (out/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'status':result['status'],'manifest':str(out/'manifest.json')},indent=2));return 0
    except (ValueError,OSError,KeyError,subprocess.TimeoutExpired) as ex:
        print(f'BLOCKED P2b: {ex}',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
