#!/usr/bin/env python3
"""Fail-closed evidence inventory for M7.2 exploratory ORFS runs.

A reported ORFS run is never physical signoff or direct M7.1-LQ import.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

VARIANTS=('programmable','fixed','rom')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def audit_variant(flow, variant, run_id):
    base=Path(flow)
    rel=Path('sky130hd')/('msif_'+variant)/run_id
    out=base/'results'/rel; logs=base/'logs'/rel; reports=base/'reports'/rel
    required=['1_2_yosys.raw.v','1_2_yosys.v','1_2_yosys.normalization.json','1_synth.odb','2_floorplan.odb','3_place.odb','4_cts.odb','5_route.odb','6_final.odb','6_final.gds','6_final.spef','6_final.sdc']
    # Some pinned ORFS revisions write 3_place.odb as a stage alias; don't invent one.
    missing=[f for f in required if not (out/f).is_file() or (out/f).stat().st_size==0]
    evidence={'variant':variant,'run_id':run_id,'status':'BLOCKED' if missing else 'FLOW_ARTIFACTS_PRESENT_NOT_SIGNOFF', 'missing_artifacts':missing,'files':{},'qualification':'research-rtl-resynthesis-only','exact_lq_mapped_import':'NOT_VERIFIED','full_physical_signoff':'NOT_VERIFIED','governed_approval':'NOT_VERIFIED'}
    for filename in required:
        f=out/filename
        if f.is_file() and f.stat().st_size:evidence['files'][filename]={'bytes':f.stat().st_size,'sha256':sha(f)}
    rec=out/'1_2_yosys.normalization.json'
    if rec.is_file():
        try:
            d=json.loads(rec.read_text()); raw=out/'1_2_yosys.raw.v'; norm=out/'1_2_yosys.v'
            ok=d.get('schema')=='msif-m72-normalization-v1' and raw.is_file() and norm.is_file() and d.get('source_sha256')==sha(raw) and d.get('normalized_sha256')==sha(norm) and (bool(d.get('changed_lines')) or (d.get('normalization_action')=='NOOP_ALREADY_COMPATIBLE' and sha(raw)==sha(norm)))
            evidence['normalization_receipt']='PASS' if ok else 'FAIL'
            if not ok:evidence['status']='BLOCKED'
        except (OSError, ValueError, KeyError): evidence['normalization_receipt']='FAIL'; evidence['status']='BLOCKED'
    for filename in ['5_route_drc.rpt','6_finish.rpt']:
        f=reports/filename
        if f.is_file() and f.stat().st_size:evidence['files']['reports/'+filename]={'bytes':f.stat().st_size,'sha256':sha(f)}
    # These reports need engineering review; do not treat file existence as DRC or STA acceptance.
    evidence['routed_drc']='REQUIRES_REPORT_AUDIT'
    evidence['extracted_setup_hold']='REQUIRES_REPORT_AUDIT'
    evidence['reset_recovery_removal']='NOT_VERIFIED'
    evidence['power_activity']='NOT_VERIFIED'
    evidence['rcx_calibration']='NOT_VERIFIED'
    evidence['memory_macro_equivalence']='NOT_VERIFIED'
    return evidence

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--flow',required=True,type=Path);ap.add_argument('--out',default='build/m72/physical-evidence-audit.json',type=Path);ap.add_argument('--suffix',default='normalized_v2');args=ap.parse_args()
    runs={v:audit_variant(args.flow,v,f'msif_m72_{v}_{args.suffix}') for v in VARIANTS}
    status='FLOW_ARTIFACTS_PRESENT_NOT_SIGNOFF' if all(x['status']=='FLOW_ARTIFACTS_PRESENT_NOT_SIGNOFF' for x in runs.values()) else 'INCOMPLETE_RESEARCH_EVIDENCE'
    result={'schema':'msif-m72-physical-audit-v1','status':status,'variants':runs,'p2b_exact_mapped_lineage':'NOT_VERIFIED','p3_all_architectures':'NOT_VERIFIED','p4_signoff_sta':'NOT_VERIFIED','p5_comparable_ppa':'NOT_VERIFIED','g1_release_authorization':'NOT_VERIFIED'}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':status,'output':str(args.out),'variants':{v:r['status'] for v,r in runs.items()}},indent=2));return 0 if status=='FLOW_ARTIFACTS_PRESENT_NOT_SIGNOFF' else 2
if __name__=='__main__':sys.exit(main())
