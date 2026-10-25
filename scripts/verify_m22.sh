#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
python3 scripts/m22_verify.py --out build/m22 --seed 2026
printf '\nPASS M2.2 bounded GEMV arithmetic and sequential regression. FULL 16x64 FORMAL UNVERIFIED.\n'
