#!/usr/bin/env python3
"""Fail-closed P3/P4/P5 research report ledger, never signoff without review."""
import argparse,hashlib,json,re,sys
from pathlib import Path
V=('programmable','fixed','rom')
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def parse_finish(text):
    def value(name):
        match=re.search(r'^\s*'+re.escape(name)+r'\s+(-?\d+(?:\.\d+)?)\b',text,re.M)
        return float(match.group(1)) if match else None
    return {'wns_max_ns':value('wns max'),'tns_max_ns':value('tns max'),'worst_slack_max_ns':value('worst slack max'), 'setup_violations':value('setup violation count'),'hold_violations':value('hold violation count'),'max_slew_violations':value('max slew violation count'),'max_cap_violations':value('max cap violation count')}
def collect(flow,suffix):
    entries={}
    for v in V:
        rel=Path('sky130hd')/f'msif_{v}'/f'msif_m72_{v}_{suffix}'
        results=flow/'results'/rel;reports=flow/'reports'/rel
        required=[results/f'6_final.{ext}' for ext in ('odb','spef','sdc','gds')]+[reports/'6_finish.rpt']
        drc=reports/'5_route_drc.rpt'
        missing=[str(f) for f in required if not f.is_file() or f.stat().st_size==0]
        entry={'status':'BLOCKED_MISSING_EVIDENCE' if missing else 'REPORTS_PRESENT_REVIEW_REQUIRED','missing':missing,'artifacts':{f.name:sha(f) for f in required if f.is_file() and f.stat().st_size}}
        entry['route_drc_report'] = {'status':'PRESENT_UNREVIEWED' if drc.is_file() and drc.stat().st_size else 'NOT_EMITTED_BY_PINNED_FLOW', 'sha256':sha(drc) if drc.is_file() and drc.stat().st_size else None}
        if (reports/'6_finish.rpt').is_file():entry['timing_observations']=parse_finish((reports/'6_finish.rpt').read_text())
        entry.update({'p3_routing_audit':'REQUIRES_INDEPENDENT_DRC_REVIEW','p4_multi_corner_sta':'NOT_VERIFIED','p4_unconstrained_endpoints':'NOT_VERIFIED','p4_reset_recovery_removal':'NOT_VERIFIED','p5_power_activity':'NOT_VERIFIED','p5_macro_comparison':'OUT_OF_SCOPE'})
        entries[v]=entry
    return {'schema':'msif-m72-p3p5-report-ledger-v1','variants':entries,'status':'REPORTS_COLLECTED_NOT_SIGNOFF' if all(not e['missing'] for e in entries.values()) else 'BLOCKED_INCOMPLETE_REPORTS','physical_ppa_qualification':'NOT_VERIFIED','g1_release':'NOT_VERIFIED'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--flow',required=True,type=Path);ap.add_argument('--out',type=Path,default=Path('build/m72/p3p5-report-ledger.json'));ap.add_argument('--suffix',default='normalized_v2');a=ap.parse_args()
    d=collect(a.flow,a.suffix);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':d['status'],'output':str(a.out)}));return 0 if d['status']=='REPORTS_COLLECTED_NOT_SIGNOFF' else 2
if __name__=='__main__':sys.exit(main())
