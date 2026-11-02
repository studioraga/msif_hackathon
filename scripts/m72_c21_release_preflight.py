#!/usr/bin/env python3
"""MSIF M7.2 evidence gate inventory. Read-only; never promotes missing signoff.

No external OpenROAD dependencies required; missing evidence becomes NOT_VERIFIED.
"""
import argparse
import hashlib
import json
from pathlib import Path

V = ('programmable','fixed','rom')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda:fh.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def inspect(root):
    root=Path(root)
    out={'schema':'msif-m72-c21-release-preflight-v1','status':'RELEASE_BLOCKED_REVIEW_REQUIRED',
         'release_authorized':False,'gates':{},'issues':[],'variants':{}}
    base=root/'build/m72'
    sources={
        'bounded_gls':base/'postroute-gls-run-c16/manifest.json',
        'tt_sta':base/'tt-research-run-c13b/manifest.json',
        'classified_area':base/'c19-classified-v1/manifest.json',
        'area_sdc_audit':base/'c20-area-sdc-live-v1.json',
    }
    data={}
    for name,path in sources.items():
        try: data[name]=json.loads(path.read_text());out['gates'][name]='EVIDENCE_PRESENT_NOT_SIGNOFF'
        except (OSError,ValueError):out['gates'][name]='NOT_VERIFIED';out['issues'].append('missing or malformed '+name)
    if 'bounded_gls' in data:
        m=data['bounded_gls']
        if m.get('status')!='BOUNDED_FINAL_GLS_ALL_PASS_NOT_EQUIVALENCE' or set(m.get('variants',{}))!=set(V):
            out['issues'].append('GLS incomplete or unexpected variant set')
        else:
            for v in V:
                rec=m['variants'][v]
                if rec.get('status')!='BOUNDED_FINAL_GLS_PASS_NOT_EQUIVALENCE' or rec.get('compile_exit')!=0 or rec.get('simulation_exit')!=0:
                    out['issues'].append('GLS failed '+v);continue
                log=base/'postroute-gls-run-c16'/f'{v}.simulate.log'
                if not log.is_file() or sha(log)!=rec.get('simulation_log_sha256') or f'PASS {v} 260 vectors' not in log.read_text(errors='replace'):
                    out['issues'].append('GLS log mismatch '+v)
                else: out['variants'].setdefault(v,{})['bounded_gls']='PASS_260_NOT_EQUIVALENCE'
    if 'tt_sta' in data:
        m=data['tt_sta']
        if m.get('status')!='TT_RESEARCH_EXECUTED_REVIEW_REQUIRED':out['issues'].append('TT run incomplete')
        for v in V:
            rec=m.get('results',{}).get(v,{})
            log=base/'tt-research-run-c13b'/f'{v}.log'
            if rec.get('status')!='STA_EXECUTED_REVIEW_REQUIRED' or not log.is_file() or sha(log)!=rec.get('log_sha256'):
                out['issues'].append('TT evidence mismatch '+v)
            else:out['variants'].setdefault(v,{})['tt_sta']='RESEARCH_REVIEW_REQUIRED'
    if 'classified_area' in data:
        m=data['classified_area']
        if m.get('status')!='CLASSIFICATION_REVIEW_REQUIRED':out['issues'].append('area run incomplete')
        for v in V:
            rec=m.get('variants',{}).get(v,{})
            report=base/'c19-classified-v1'/f'{v}.classified.txt'
            if rec.get('status')!='CLASSIFICATION_REVIEW_REQUIRED' or not report.is_file() or sha(report)!=rec.get('report_sha256'):
                out['issues'].append('classified area mismatch '+v)
            else: out['variants'].setdefault(v,{})['classified_area']='RESEARCH_REVIEW_REQUIRED'
    if 'area_sdc_audit' in data:
        m=data['area_sdc_audit']
        if m.get('status')!='AREA_RECONCILED_SDC_REVIEW_REQUIRED' or m.get('issues') or set(m.get('variants',{}))!=set(V):
            out['issues'].append('C20 SDC/area review incomplete')
        else:
            for v in V:
                r=m['variants'][v]
                if not r.get('sdc_review',{}).get('reset_input_delayed'):
                    out['issues'].append('unexpected reset constraint inventory '+v)
                out['variants'].setdefault(v,{})['sdc']='HASH_RECONCILED_RESET_REVIEW_REQUIRED'
    # These gates remain open without independent, reviewed proof receipts.
    out['gates'].update({'p2b_formal':'NOT_VERIFIED','p3_eco_equivalence':'NOT_VERIFIED',
                         'p4_global_tt_coverage':'NOT_VERIFIED','p4_ss_ff_rc':'NOT_VERIFIED',
                         'p5_activity_power':'NOT_VERIFIED','p5_qualified_ppa':'NOT_VERIFIED',
                         'g1_independent_approval':'NOT_VERIFIED'})
    return out

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    if a.out.exists():p.error('output exists; preserve prior evidence')
    result=inspect(a.root);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(result['status'],f"issues={len(result['issues'])}")
    return 0 if not result['issues'] else 2
if __name__=='__main__':raise SystemExit(main())
