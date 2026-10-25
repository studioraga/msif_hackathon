#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 -m msif.cli build --out build/demo
python3 -m msif.cli verify --out build/demo
# Strict gate: a passing Python suite cannot be confused with RTL qualification.
if ! command -v iverilog >/dev/null || ! command -v vvp >/dev/null; then
 echo 'BLOCKED M2: iverilog and vvp required. See docs/Prerequisites.md' >&2
 exit 2
fi
python3 -m msif.cli sim --out build/demo --vectors 24
if ! command -v yosys >/dev/null; then
 echo 'BLOCKED M7-lite: yosys required. See docs/Prerequisites.md' >&2
 exit 2
fi
python3 -m msif.cli synthesize --out build/demo
python3 scripts/node1_evidence.py --build build/demo
printf '\nPASS: Python + actual RTL simulation + Yosys generic synthesis.\n'
printf 'NOT VERIFIED: formal proof, mapped timing/PPA, OpenROAD, FPGA, release approval.\n'
