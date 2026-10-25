#!/usr/bin/env bash
set -euo pipefail
# Explicit opt-in; modifies host packages. Inspect before executing.
if [[ "${1:-}" != "--install" ]]; then
  echo 'Dry run. On Ubuntu 24.04: sudo apt update && sudo apt install -y yosys iverilog verilator'
  echo 'Execute: ./scripts/install_node1_tools.sh --install'
  exit 0
fi
if ! command -v apt-get >/dev/null; then echo 'BLOCKED: requires Ubuntu/Debian apt'; exit 2; fi
sudo apt-get update
sudo apt-get install -y yosys iverilog verilator
for x in yosys iverilog vvp verilator; do command -v "$x" || { echo "BLOCKED: $x missing"; exit 2; }; done
