#!/usr/bin/env python3
"""Fail-closed analysis of closure11 formal probes. Never reports equivalence PASS."""
import argparse
import hashlib
import json
import re
from pathlib import Path

VARIANTS = ('programmable', 'fixed', 'rom')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(directory):
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 'msif-m72-formal-diagnostic-v1':
        raise ValueError('unexpected diagnostic schema')
    if set(manifest.get('variants', {})) != set(VARIANTS):
        raise ValueError('missing or unexpected architecture record')
    results = {}
    for variant in VARIANTS:
        record = manifest['variants'][variant]
        log = directory / f'{variant}.log'
        if not log.is_file() or log.stat().st_size == 0:
            raise ValueError(f'{variant}: log missing or empty')
        if sha(log) != record.get('log_sha256'):
            raise ValueError(f'{variant}: log digest mismatch')
        if log.stat().st_size != record.get('log_bytes'):
            raise ValueError(f'{variant}: log size mismatch')
        body = log.read_text(errors='replace')
        stages = re.findall(r'^\s*\d+\. Executing ([A-Z_]+) pass\.', body, re.M)
        simple_attempts = len(re.findall(r'Trying to prove \$equiv', body))
        proven = [int(x) for x in re.findall(r'Proved (\d+) previously unproven \$equiv cells', body)]
        results[variant] = {
            'status': record['status'], 'exit_code': record.get('exit_code'),
            'timed_out': record.get('timed_out'),
            'last_pass': stages[-1] if stages else 'UNKNOWN',
            'equiv_simple_attempts_observed': simple_attempts,
            'equiv_simple_proved_counts': proven,
            'log_sha256': sha(log),
            'interpretation': 'INCONCLUSIVE_NOT_EQUIVALENCE_PROOF'
        }
    return {'schema':'msif-m72-probe-audit-v1','qualification':'DIAGNOSTIC_ONLY_NOT_FORMAL_PROOF', 'variants':results}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--probe', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args=ap.parse_args()
    if args.out.exists(): ap.error('refusing to overwrite existing evidence')
    try: report=audit(args.probe)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f'BLOCKED: {e}')
        return 2
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2))
    return 0 # 0 means diagnostic audit complete, NOT proof
if __name__=='__main__': raise SystemExit(main())
