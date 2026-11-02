#!/usr/bin/env bash
# Console-safe M7.2 gate: P0/P1 preflight by default; physical attempt only with explicit --execute.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${MSIF_ORFS:?Set path to reviewed pinned OpenROAD-flow-scripts checkout}"
: "${MSIF_M72_LICENSE_PVT_REVIEWED:?Set to YES only after license and PVT review}"
if [[ "$MSIF_M72_LICENSE_PVT_REVIEWED" != YES ]]; then
  echo 'BLOCKED: operator must attest library/process/license review' >&2; exit 1
fi
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s tests -q
python3 scripts/m71_lq_audit.py --build build/m71_liberty
python3 scripts/m72_physical.py --build build/m71_liberty --orfs "$MSIF_ORFS" \
  --out build/m72 --license-pvt-reviewed "$@"
