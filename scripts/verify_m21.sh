#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 scripts/m21_verify.py --out build/m21
printf '\nPASS M2.1 scalar RTL exhaustive simulation + SAT proof. Full GEMV formal proof NOT VERIFIED.\n'
