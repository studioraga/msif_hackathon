#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
test -x "$PY" || { echo 'BLOCKED: project .venv missing; run uv sync --locked --group gpu' >&2; exit 2; }
command -v uv >/dev/null || { echo 'BLOCKED: uv missing' >&2; exit 2; }
uv lock --check
"$PY" -c 'import sys,numpy,torch; assert sys.version_info[:2]==(3,12); assert numpy.__version__=="2.5.4"; assert torch.__version__.split("+")[0]=="2.14.0"; assert torch.version.cuda=="13.0"; assert torch.cuda.is_available(); assert torch.cuda.get_device_capability(0)==(12,0); assert "sm_120" in torch.cuda.get_arch_list(); print("LOCKED_DEPENDENCIES=PASS")'
"$PY" scripts/validate/pytorch/validate_torch_blackwell.py
CUDA_DISABLE_PTX_JIT=1 "$PY" scripts/validate/pytorch/validate_torch_blackwell.py
: "${CUDA_HOME:=/usr/local/cuda-13.3}"
: "${TORCH_EXTENSIONS_DIR:=/tmp/msif-torch-extensions-project}"
export CUDA_HOME TORCH_EXTENSIONS_DIR TORCH_CUDA_ARCH_LIST=12.0
mkdir -p "$TORCH_EXTENSIONS_DIR"
"$PY" scripts/validate/pytorch/validate_torch_cuda_extension.py
CUDA_DISABLE_PTX_JIT=1 "$PY" scripts/validate/pytorch/validate_torch_cuda_extension.py
SO="$(find "$TORCH_EXTENSIONS_DIR" -type f -name '*.so' -print -quit)"
test -n "$SO" || { echo 'FAIL: CUDA extension .so missing'; exit 1; }
"$CUDA_HOME/bin/cuobjdump" --list-elf "$SO" | tee "$TORCH_EXTENSIONS_DIR/cuobjdump.log"
grep -q 'sm_120' "$TORCH_EXTENSIONS_DIR/cuobjdump.log" || { echo 'FAIL: native sm_120 cubin not found'; exit 1; }
echo 'PROJECT_PYTORCH_BLACKWELL=ACCEPT'
