#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${MSIF_LIB:?Provide verified SKY130 standard-cell Liberty path}"
: "${MSIF_CELL_MODELS:?Provide validated full SKY130 functional Verilog cell-model file}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -q
python3 -m msif.cli build --out build/m71_liberty --m 2 --k 4 --seed 2026
python3 -m msif.cli verify --out build/m71_liberty
python3 scripts/m71_compare.py --build build/m71_liberty --liberty "$MSIF_LIB"
python3 scripts/m71_lq.py --build build/m71_liberty --liberty "$MSIF_LIB" --cell-models "$MSIF_CELL_MODELS" --vectors 256
