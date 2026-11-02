#!/usr/bin/env python3
"""Fail-closed Node1 M7.2 physical facts and outstanding closure gates.

No inferred power, no inferred PVT signoff, no inferred exact-LQ routing.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

VARIANTS=('programmable','fixed','rom')
FINAL_DRC_KEY='detailedroute__route__drc_errors'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read_json(p): return json.loads(p.read_text())
def number(v):
    return v if isinstance(v,(int,float)) and not isinstance(v,bool) else None

def route_status(route):
    if not isinstance(route,dict) or FINAL_DRC_KEY not in route:
        return {'status':'NOT_VERIFIED','final_drc_count':None}
    count=number(route[FINAL_DRC_KEY])
    if count is None or count<0:
        return {'status':'BLOCKED_INVALID_FINAL_DRC','final_drc_count':count}
    ants=[route.get('detailedroute__antenna__violating__nets'),route.get('detailedroute__antenna__violating__pins')]
    if any(number(v) is None for v in ants):
        return {'status':'REVIEW_ANTENNA_NOT_RECORDED','final_drc_count':count}
    return {'status':'ROUTER_ZERO_REPORTED_VIOLATIONS_NOT_FOUNDRY_SIGNOFF' if count==0 and all(x==0 for x in ants) else 'BLOCKED_ROUTER_VIOLATIONS','final_drc_count':count,'antenna_net_violations':ants[0],'antenna_pin_violations':ants[1]}

def extract_area(report_json, report_log):
    # The ORFS metric schema distinguishes cell categories, unlike the textual 'Design area'.
    area_metrics={k:v for k,v in report_json.items() if 'area' in k and isinstance(v,(int,float))}
    m=re.findall(r'Design area\s+([0-9.]+)\s+um\^2\s+([0-9.]+)% utilization',report_log)
    last=m[-1] if m else None
    return {'area_metric_fields':area_metrics,'reported_design_area_um2':float(last[0]) if last else None,
            'reported_utilization_percent_rounded':float(last[1]) if last else None,
            'classification':'REQUIRES_OPENDB_CATEGORIZED_AREA_AND_REVIEW'}

def collect(flow, manifest=None):
    entries={}
    for v in VARIANTS:
        rel=Path('sky130hd')/f'msif_{v}'/f'msif_m72_{v}_normalized_v2'
        logs=flow/'logs'/rel; results=flow/'results'/rel
        required={'route_metrics':logs/'5_2_route.json','finish_metrics':logs/'6_report.json',
                  'finish_log':logs/'6_report.log','final_odb':results/'6_final.odb','spef':results/'6_final.spef',
                  'gds':results/'6_final.gds'}
        missing=[name for name,p in required.items() if not p.is_file() or p.stat().st_size==0]
        if missing:
            entries[v]={'status':'BLOCKED_MISSING_FILES','missing':missing};continue
        route=read_json(required['route_metrics']);finish=read_json(required['finish_metrics'])
        entries[v]={'status':'RESEARCH_EVIDENCE_REVIEW_REQUIRED','hashes':{k:sha(p) for k,p in required.items()},
                    'routing':route_status(route),'physical_area':extract_area(finish,required['finish_log'].read_text()),
                    'final_timing_metric_fields':{k:x for k,x in finish.items() if ('timing' in k and isinstance(x,(int,float)))},
                    'power':'PWR0_RESEARCH_ONLY','exact_mapped_route':'NOT_VERIFIED','pvt_signoff':'NOT_VERIFIED'}
    d={'schema':'msif-m72-closure-evidence-v1','variants':entries,
       'p2b':'NOT_VERIFIED','p3_foundry_signoff':'NOT_VERIFIED','p4_multi_corner':'NOT_VERIFIED',
       'p5_activity_qualified_power':'NOT_VERIFIED','memory_macro_equivalence':'NOT_VERIFIED','g1':'NOT_VERIFIED'}
    if manifest:
        m=read_json(manifest);d['external_qualification_manifest_sha256']=sha(manifest)
        req=('corners','power_activity','memory_macros','exact_mapped_physical')
        d['external_gates']={k: 'MANIFEST_PRESENT_REQUIRES_INDEPENDENT_REVIEW' if m.get(k) else 'NOT_VERIFIED' for k in req}
    d['status']='RESEARCH_EVIDENCE_COLLECTED_NOT_SIGNOFF' if all(e['status']=='RESEARCH_EVIDENCE_REVIEW_REQUIRED' for e in entries.values()) else 'BLOCKED_MISSING_EVIDENCE'
    return d

def main():
    a=argparse.ArgumentParser();a.add_argument('--flow',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--external-manifest',type=Path);ns=a.parse_args()
    try:d=collect(ns.flow,ns.external_manifest)
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as ex: print('BLOCKED:',ex,file=sys.stderr);return 2
    ns.out.parent.mkdir(parents=True,exist_ok=True);ns.out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':d['status'],'out':str(ns.out)}));return 0 if d['status'].startswith('RESEARCH_') else 2
if __name__=='__main__':raise SystemExit(main())
