#!/usr/bin/env python3
"""P2b fail-closed checkpoint based on exact-route manifest; not formal equivalence."""
import argparse,json,hashlib,sys
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(m):
    states={}
    for name,v in m['variants'].items():
        p=Path(v['input']); expected=v['accepted_sha256']
        if not p.is_file() or digest(p)!=expected:raise ValueError('mapped source hash mismatch: '+name)
        state=v.get('run','NOT_EXECUTED')
        states[name]=state
        if state=='FLOW_COMPLETE_NOT_EQUIVALENCE' and not v.get('final_odb_sha256'):
            raise ValueError('complete run lacks ODB hash: '+name)
    return {'schema':'msif-m72-p2b-checkpoint-v1','states':states,
            'p2b_formal_equivalence':'NOT_VERIFIED','graph_continuity':'NOT_VERIFIED',
            'route_all_complete':all(v=='FLOW_COMPLETE_NOT_EQUIVALENCE' for v in states.values()),
            'status':'CHECKPOINT_NOT_EQUIVALENCE'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        result=audit(json.loads(a.manifest.read_text()))
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(result['status']);return 0 if result['route_all_complete'] else 2
    except (KeyError,ValueError,OSError) as e:print('BLOCKED:',e,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
