#!/usr/bin/env python3
"""P2b exact-netlist ORFS route launcher. Never treats route success as equivalence."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(root,orfs,out):
    ev=json.loads((root/'build/m71_liberty/m71_lq/evidence.json').read_text())
    if ev.get('qualification')!='bounded-mapped-gate-level-validation':raise ValueError('LQ qualification mismatch')
    if not (orfs/'flow/Makefile').is_file():raise ValueError('ORFS missing')
    # This option is supported on modern ORFS. Fail closed against older pinned Makefile.
    if not any('SYNTH_NETLIST_FILES' in f.read_text(errors='replace') for f in [orfs/'flow/Makefile', *(orfs/'flow/scripts').glob('*.mk')]):
        raise ValueError('pinned ORFS Makefile does not support SYNTH_NETLIST_FILES: check included files manually')
    out.mkdir(parents=True,exist_ok=False)
    data={}
    for v in V:
        inp=root/f'build/m71_liberty/m71_lq/msif_{v}_mapped.v'
        expected=ev['architectures'][v]['mapped_verilog_sha256']
        if not inp.is_file() or sha(inp)!=expected:raise ValueError('LQ hash mismatch '+v)
        conf=root/f'build/m72/{v}/config.mk'
        if not conf.is_file():raise ValueError('missing M7.2 config '+v)
        cfg=out/f'{v}.config.mk'
        cfg.write_text(conf.read_text()+f'\n# P2b: exact accepted mapped netlist; do NOT resynthesize RTL.\nexport SYNTH_NETLIST_FILES = {inp.resolve()}\n')
        data[v]={'accepted_sha256':expected,'input':str(inp.resolve()),'config':str(cfg.resolve()),'run':'NOT_EXECUTED','equivalence':'NOT_VERIFIED'}
    return data
def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a.add_argument('--orfs',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--execute',action='store_true');a.add_argument('--variant-suffix',default='exact_lq_v2');a.add_argument('--num-cores',type=int,default=1);n=a.parse_args()
    if not (1 <= n.num_cores <= 32): raise SystemExit('BLOCKED: num-cores out of range')
    out=n.out.resolve();root=n.root.resolve();orfs=n.orfs.resolve()
    try:
        data=prepare(root,orfs,out)
        if n.execute:
            for v in V:
                variant=f'msif_m72_{v}_{n.variant_suffix}'
                cmd=['make','-C',str(orfs/'flow'),f'DESIGN_CONFIG={data[v]["config"]}',f'FLOW_VARIANT={variant}',f'NUM_CORES={n.num_cores}','-j1']
                p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                (out/f'{v}.make.log').write_text(p.stdout)
                data[v]['make_exit_code']=p.returncode
                data[v]['make_log_sha256']=sha(out/f'{v}.make.log')
                data[v]['flow_variant']=variant
                data[v]['last_log_lines']=p.stdout.splitlines()[-12:]
                odb=orfs/f'flow/results/sky130hd/msif_{v}/{variant}/6_final.odb'
                data[v]['run']='FLOW_COMPLETE_NOT_EQUIVALENCE' if p.returncode==0 and odb.is_file() and odb.stat().st_size else 'BLOCKED'
                if data[v]['run']=='FLOW_COMPLETE_NOT_EQUIVALENCE':data[v]['final_odb_sha256']=sha(odb)
                if p.returncode or data[v]['run']=='BLOCKED':break
        obj={'schema':'msif-m72-exact-route-v1','status':'EXACT_ROUTE_PARTIAL_OR_RESEARCH_NOT_EQUIVALENCE','variants':data,'g1':'NOT_VERIFIED'}
        (out/'manifest.json').write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'status':obj['status'],'manifest':str(out/'manifest.json')}))
        return 2 if any(x['run']=='BLOCKED' for x in data.values()) else 0
    except (ValueError,OSError,KeyError) as e:
        print('BLOCKED:',e,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
