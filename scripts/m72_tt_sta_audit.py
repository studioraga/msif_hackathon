#!/usr/bin/env python3
"""Audit captured TT research logs, without claiming timing signoff."""
import argparse, hashlib, json, re, sys
from pathlib import Path
VARIANTS = ('programmable','fixed','rom')
MARKER = 'M72_TT_RESEARCH_EXECUTED_NOT_SIGNOFF'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def audit(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    out={'schema':'msif-m72-tt-log-audit-v1','status':'BLOCKED','signoff':'NOT_VERIFIED','results':{},'issues':[]}
    if set(manifest.get('results',{}))!=set(VARIANTS):out['issues'].append('A/B/C coverage incomplete');return out
    for v in VARIANTS:
        record=manifest['results'][v]; path=directory/(v+'.log')
        if not path.is_file() or not path.stat().st_size:out['issues'].append(v+': missing log');continue
        content=path.read_text(errors='replace')
        lines=content.splitlines()
        matches=re.findall(r'([-+]?\d+(?:\.\d+)?)\s+slack \((MET|VIOLATED)\)',content)
        classes={key:[] for key in ('max','min')}
        current=None
        for line in lines:
            m=re.search(r'^Path Type:\s*(max|min)\s*$',line)
            if m:current=m.group(1)
            m=re.search(r'([-+]?\d+(?:\.\d+)?)\s+slack \((MET|VIOLATED)\)',line)
            if m and current:classes[current].append(float(m.group(1)))
        issues=[]
        if sha(path)!=record.get('log_sha256'):issues.append('log hash mismatch')
        if path.stat().st_size!=record.get('log_bytes'):issues.append('log size mismatch')
        if record.get('exit_code')!=0 or record.get('status')!='STA_EXECUTED_REVIEW_REQUIRED':issues.append('STA runner not successful')
        if content.count(MARKER)!=1:issues.append('missing or duplicate terminal marker')
        if re.search(r'(?im)^\s*(?:ERROR:|Error:|FATAL:)',content):issues.append('engine error')
        if not all(classes.values()):issues.append('missing setup/hold path reports')
        if any(label=='VIOLATED' for _,label in matches):issues.append('reported negative-slack violation')
        out['results'][v]={'status':'LOG_REVIEW_REQUIRED' if not issues else 'BLOCKED','log_sha256':sha(path), 'reported_path_min_slack':{k:min(values) if values else None for k,values in classes.items()},'reported_path_counts':{k:len(values) for k,values in classes.items()},'issues':issues}
        out['issues'] += [v+': '+i for i in issues]
    if not out['issues']:out['status']='TT_LOGS_CONSISTENT_REVIEW_REQUIRED'
    return out
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    if a.out.exists():p.error('output exists; preserve prior evidence')
    try:r=audit(a.run)
    except (OSError,ValueError,json.JSONDecodeError) as exc:r={'schema':'msif-m72-tt-log-audit-v1','status':'BLOCKED','signoff':'NOT_VERIFIED','issues':[str(exc)],'results':{}}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['status']);return 0 if r['status']=='TT_LOGS_CONSISTENT_REVIEW_REQUIRED' else 2
if __name__=='__main__':sys.exit(main())
