#!/usr/bin/env python3
"""Research-only P5 side-by-side observations; never release signoff."""
import argparse,json,sys
from pathlib import Path
VARIANTS=('programmable','fixed','rom')
def compare(data):
    records={}
    for v in VARIANTS:
        e=data.get('variants',{}).get(v,{})
        if e.get('status')!='REPORTS_PRESENT_REVIEW_REQUIRED':
            raise ValueError(f'{v}: required final-stage evidence missing')
        t=e.get('timing_observations',{})
        # Values are accepted only as extracted observations, not as qualified PPA.
        records[v]={
            'final_artifact_hashes':e['artifacts'],
            'single_corner_timing_observations':t,
            'timing_basis':'TT research SDC 100 ns; no multi-corner qualification',
            'core_area_um2':None,
            'standard_cell_area_um2':None,
            'final_utilization_pct':None,
            'drc_evidence':e.get('route_drc_report',{}),
            'routed_drc_qualification':'NOT_VERIFIED',
            'power_watts_qualified':None,
            'power_activity_provenance':'NOT_VERIFIED',
            'memory_macro_area_um2':None,
            'memory_macro_qualification':'NOT_VERIFIED',
        }
    return {'schema':'msif-m72-p5-comparison-v1','status':'RESEARCH_COMPARISON_NOT_SIGNOFF','variants':records,'exact_lq_equivalence':'NOT_VERIFIED','multi_corner_sta':'NOT_VERIFIED','calibrated_power':'NOT_VERIFIED','g1_release':'NOT_VERIFIED'}
def main():
    a=argparse.ArgumentParser();a.add_argument('--ledger',required=True,type=Path);a.add_argument('--out',required=True,type=Path);args=a.parse_args()
    try: d=compare(json.loads(args.ledger.read_text()))
    except (ValueError,KeyError,OSError) as e: print(f'BLOCKED: {e}',file=sys.stderr);return 2
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':d['status'],'out':str(args.out)}));return 0
if __name__=='__main__':sys.exit(main())
