#!/usr/bin/env python3
"""Read-only, time-bounded Yosys diagnosis, preserving per-variant partial logs.

Runs existing reviewed .ys files unchanged. Does not make equivalence claims.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

VARIANTS = ('programmable', 'fixed', 'rom')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run_one(script, log, binary, timeout_s):
    started = time.monotonic()
    with log.open('wb') as out:
        proc = subprocess.Popen([binary, '-s', str(script)], stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            code = proc.wait(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            code = None
    return {'status': 'TIMEOUT_INCONCLUSIVE' if timed_out else 'EXECUTED_REVIEW_REQUIRED' if code == 0 else 'FAILED',
            'exit_code': code, 'timed_out': timed_out, 'elapsed_seconds': round(time.monotonic()-started, 3),
            'log_sha256': digest(log), 'log_bytes': log.stat().st_size}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plans', type=Path, required=True, help='Directory with existing generated *.ys')
    p.add_argument('--out', type=Path, required=True, help='New output directory')
    p.add_argument('--timeout', type=int, default=180, help='Per-architecture timeout in seconds')
    p.add_argument('--yosys', default='yosys')
    a=p.parse_args()
    if a.timeout < 1: p.error('timeout must be positive')
    if not a.plans.is_dir(): p.error('plans directory missing')
    if a.out.exists(): p.error('output directory already exists; evidence must never be overwritten')
    plans = {v:(a.plans/f'{v}.ys').resolve() for v in VARIANTS}
    for v,s in plans.items():
        if not s.is_file() or not s.stat().st_size: p.error(f'{v} script missing/empty: {s}')
    a.out.mkdir(parents=True)
    report={'schema':'msif-m72-formal-diagnostic-v1','status':'DIAGNOSTIC_NOT_FORMAL_PROOF',
            'timeout_seconds':a.timeout,'variants':{}}
    try:
        for v,script in plans.items():
            log=a.out/f'{v}.log'
            try:
                r=run_one(script,log,a.yosys,a.timeout)
            except (OSError,ValueError) as exc:
                r={'status':'LAUNCH_ERROR', 'error':str(exc)}
            r['script_sha256']=digest(script)
            report['variants'][v]=r
            (a.out/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
            print(f'{v}: {r["status"]} ({r.get("elapsed_seconds","-")}s)',flush=True)
    finally:
        (a.out/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return 0 if all(v['status']=='EXECUTED_REVIEW_REQUIRED' for v in report['variants'].values()) else 2
if __name__=='__main__': sys.exit(main())
