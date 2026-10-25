#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs
{ date -Is; uname -a; python3 --version
  for x in git python3 yosys iverilog vvp verilator openroad klayout ngspice openssl; do
    if command -v "$x" >/dev/null 2>&1; then printf 'FOUND %-10s %s\n' "$x" "$(command -v "$x")";
    else printf 'MISSING %s\n' "$x"; fi
  done
} | tee logs/node1_prerequisites.log
# The audit is informational: the strict verifier enforces required dependencies.
