#!/usr/bin/env python3
"""Read real Node1 logs; fail closed on missing/incorrect synthesis evidence."""
import argparse,json,re,hashlib,subprocess,shutil
from pathlib import Path
P=('programmable','fixed','rom')
def main():
    a=argparse.ArgumentParser();a.add_argument('--build',default='build/demo');a.add_argument('--out',default='build/demo/node1_evidence.json');args=a.parse_args()
    base=Path(args.build)
    from sys import path
    path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from msif.governance import validate_manifest
    validate_manifest(base)
    metrics={}
    for v in P:
        s=(base/f'sim_{v}.log').read_text()
        mt=re.search(r'^PASS '+v+r' (\d+) vectors$',s,re.M)
        if not mt:raise SystemExit('FAIL simulation evidence: '+v)
        log=(base/f'yosys_{v}.log').read_text()
        if 'Found and reported 0 problems.' not in log:raise SystemExit('FAIL Yosys check: '+v)
        matches=re.findall(r'Number of cells:\s+(\d+)',log)
        if not matches:raise SystemExit('FAIL missing cell count: '+v)
        metrics[v]={'simulation_vectors':int(mt.group(1)),'generic_cells':int(matches[-1]),'synthesis_check':'PASS'}
    tools={}
    for tool,cmd in [('yosys',['yosys','-V']),('iverilog',['iverilog','-V']),('verilator',['verilator','--version'])]:
        if not shutil.which(tool):
            tools[tool]='UNAVAILABLE_IN_REPORT_ENVIRONMENT'
            continue
        p=subprocess.run(cmd,text=True,capture_output=True)
        lines=(p.stdout or p.stderr).splitlines()
        tools[tool]=lines[0] if p.returncode==0 and lines else 'UNAVAILABLE'
    hashes={}
    for file in sorted(base.glob('*.log')):hashes[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    result={'schema':'msif-node1-generic-evidence-v1','qualification':'generic-simulation-and-synthesis-only','architectures':metrics,'tools':tools,'log_sha256':hashes,'observations':{'rom_vs_programmable_generic_cells_equal':metrics['rom']['generic_cells']==metrics['programmable']['generic_cells'],'technology_mapped_ppa':'NOT_VERIFIED','formal_equivalence':'NOT_VERIFIED','governance_approval':'NOT_VERIFIED'}}
    target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
