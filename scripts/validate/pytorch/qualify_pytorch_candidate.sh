#!/usr/bin/env bash
set -euo pipefail

CANDIDATE="${CANDIDATE_VENV:-/tmp/msif-pytorch-2.14.0-cu130}"

PY="$CANDIDATE/bin/python"

test -x "$PY"

echo "=================================================="
echo "PYTORCH CANDIDATE QUALIFICATION"
echo "=================================================="

echo
echo "=== PACKAGE ==="

"$PY" - <<'PY'
import torch

print("torch =", torch.__version__)
print("runtime_cuda =", torch.version.cuda)

assert torch.__version__.startswith("2.14.0")
assert torch.version.cuda == "13.0"

print("PACKAGE_GATE=PASS")
PY

echo
echo "=== NORMAL GPU EXECUTION ==="

"$PY" \
  scripts/validate/pytorch/validate_torch_blackwell.py

echo
echo "=== NO PTX JIT ==="

CUDA_DISABLE_PTX_JIT=1 \
"$PY" \
  scripts/validate/pytorch/validate_torch_blackwell.py

echo
echo "=== SM120 ARCH LIST ==="

"$PY" - <<'PY'
import torch

arches = torch.cuda.get_arch_list()

print(arches)

assert "sm_120" in arches

print("ARCH_GATE=PASS")
PY

echo
echo "=== EXTENSION ==="

rm -rf /tmp/msif-torch-extensions

CUDA_HOME=/usr/local/cuda-13.3 \
TORCH_CUDA_ARCH_LIST=12.0 \
TORCH_EXTENSIONS_DIR=/tmp/msif-torch-extensions \
"$PY" \
  scripts/validate/pytorch/validate_torch_cuda_extension.py

SO="$(
    find /tmp/msif-torch-extensions \
      -type f \
      -name '*.so' \
      | head -1
)"

test -n "$SO"
test -f "$SO"

echo "EXTENSION_SO=$SO"

echo
echo "=== CUBIN ==="

/usr/local/cuda-13.3/bin/cuobjdump \
    --list-elf \
    "$SO" \
    | tee /tmp/msif-sm120-cuobjdump.log

grep -q \
    'sm_120' \
    /tmp/msif-sm120-cuobjdump.log

echo "SM120_CUBIN_GATE=PASS"

echo
echo "=================================================="
echo "PYTORCH_CANDIDATE=ACCEPT"
echo "=================================================="
