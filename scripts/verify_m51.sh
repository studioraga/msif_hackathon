#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -c 'import torch; print("PyTorch:", torch.__version__)'
python3 -m unittest discover -s tests -v
python3 - <<'PY'
import json, tempfile
from pathlib import Path
import torch
from msif.tensor_import import build_from_tensor
from msif.governance import validate_manifest
p=Path('build/m51');p.mkdir(parents=True,exist_ok=True)
checkpoint=p/'fixture.pt'
torch.save({'model.weight':torch.tensor([[0.,.5,-.5,1.],[-1.,.25,-.25,0.]],dtype=torch.float32)},checkpoint)
a=build_from_tensor(checkpoint,.25,p/'a','model.weight')
b=build_from_tensor(checkpoint,.25,p/'b','model.weight')
assert a==b
for f in ('manifest.json','model.json','msif_programmable.sv','msif_fixed.sv','msif_rom.sv'):
    assert (p/'a'/f).read_bytes()==(p/'b'/f).read_bytes(), f
assert validate_manifest(p/'a') and validate_manifest(p/'b')
(p/'evidence.json').write_text(json.dumps({'schema':'msif-m51-evidence-v1','import':'PASS','repeatability':'PASS','manifest_integrity':'PASS','model_sha256':a['manifest']['model_sha256'],'source_sha256':a['provenance']['source_file_sha256'],'qualification':'synthetic-pytorch-tensor-only; not a production-model qualification'},indent=2)+'\n')
print('PASS: M5.1 deterministic PyTorch tensor import and RTL generation')
PY
python3 -m msif.cli verify --out build/m51/a
if command -v iverilog >/dev/null && command -v vvp >/dev/null; then
  python3 -m msif.cli sim --out build/m51/a --vectors 32
else
  echo 'BLOCKED: iverilog and vvp are mandatory for M5.1 qualification' >&2
  exit 2
fi
