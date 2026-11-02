#!/usr/bin/env python3
"""Read-only cross-ledger M7.2 evidence audit. Never promotes formal/P4/P5 signoff."""
import argparse
import hashlib
import json
from pathlib import Path

V = ('programmable', 'fixed', 'rom')

def check(root):
    def load(path):
        return json.loads((root / path).read_text())
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    probe=load('build/m72/formal-probe-v5-closure11a/manifest.json')
    pa=load('build/m72/formal-probe-audit-closure11a.json')
    eco=load('build/m72/eco-inventory-c11p1.json')
    corners=load('build/m72/corner-inventory-c11p1.json')
    route=load('build/m72/exact-route-singlecore-v2/manifest.json')
    result={'schema':'msif-m72-closure12-cross-ledger-v1', 'status':'EVIDENCE_CONSISTENT_NOT_SIGNOFF', 'g1':'NOT_VERIFIED','variants':{}, 'corner_views':[], 'issues':[]}
    for data,label in ((probe,'probe'),(pa,'probe audit'),(eco,'eco'),(route,'route')):
        if set(data.get('variants',{})) != set(V):
            result['issues'].append(f'{label}: missing/extra architectures')
    if set(corners.get('designs',{})) != set(V):
        result['issues'].append('corner: missing/extra architectures')
    for v in V:
        try:
            p=probe['variants'][v]; a=pa['variants'][v]; e=eco['variants'][v]; r=route['variants'][v]; c=corners['designs'][v]
            log=root/f'build/m72/formal-probe-v5-closure11a/{v}.log'
            assert log.is_file() and digest(log)==p['log_sha256']==a['log_sha256'], 'probe log SHA mismatch'
            assert log.stat().st_size==p['log_bytes'], 'probe log length mismatch'
            assert p['status']=='TIMEOUT_INCONCLUSIVE' and p['timed_out'] is True, 'unreviewed probe change'
            assert a['last_pass']=='EQUIV_INDUCT', 'last-pass change requires review'
            assert e['missing']==[], 'missing physical artifacts'
            assert e['files']['1_2_yosys.v']==r['accepted_sha256'], 'accepted mapped hash mismatch'
            assert e['files']['6_final.v']==e['files']['6_final_lec.v']==e['files']['4_after_rsz_lec.v'], 'final LEC mismatch'
            assert e['files']['6_final.odb']==r['final_odb_sha256']==c['odb']['sha256'], 'routed DB mismatch'
            assert e['files']['6_final.spef']==c['spef']['sha256'], 'SPEF mismatch'
            assert c['sdc'].get('sha256'), 'missing final SDC hash'
            result['variants'][v]={'formal':'TIMEOUT_INCONCLUSIVE','postroute_equivalence':'NOT_VERIFIED','physical_artifacts':'HASHES_CONSISTENT','final_verilog_sha256':e['files']['6_final.v'],'final_odb_sha256':e['files']['6_final.odb'],'spef_sha256':e['files']['6_final.spef'],'sdc_sha256':c['sdc']['sha256']}
        except (KeyError, AssertionError, OSError) as exc:
            result['issues'].append(f'{v}: {exc}')
    result['corner_views']=[x['name'] for x in corners.get('libraries',[])]
    result['rcx_present']=corners.get('rc',{}).get('rcx_rules',{}).get('exists') is True
    result['setrc_present']=corners.get('rc',{}).get('layer_rc',{}).get('exists') is True
    result['p4']='NOT_VERIFIED'
    result['p5']='NOT_VERIFIED'
    if result['issues']:result['status']='BLOCKED_EVIDENCE_MISMATCH'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('refusing to overwrite evidence')
    try: result=check(a.root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result={'schema':'msif-m72-closure12-cross-ledger-v1','status':'BLOCKED','issues':[str(exc)],'g1':'NOT_VERIFIED'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(result['status'])
    return 0 if result['status']=='EVIDENCE_CONSISTENT_NOT_SIGNOFF' else 2
if __name__=='__main__':raise SystemExit(main())
