#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -v
command -v yosys >/dev/null || { echo 'BLOCKED: yosys required' >&2; exit 2; }
python3 -m msif.cli build --out build/m71 --m 2 --k 4 --seed 2026
python3 -m msif.cli verify --out build/m71
python3 scripts/m71_compare.py --build build/m71 "$@"
