"""M5.1: bounded, deterministic import of a 2D PyTorch tensor into MSIF INT4.

This is a per-tensor symmetric quantizer; it is not an ONNX Q/DQ importer.
No implicit clipping or calibration is performed.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from .core import canonical, check, sha, write_build


def load_tensor(path: str | Path, key: str | None = None):
    """Load .pt/.pth using torch weights_only=True (no arbitrary object unpickling)."""
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError('PyTorch is required for M5.1: install it in a separate venv') from exc
    path = Path(path)
    if path.suffix.lower() not in ('.pt', '.pth'):
        raise ValueError('Only .pt/.pth weights-only PyTorch checkpoints are supported')
    try:
        obj = torch.load(path, map_location='cpu', weights_only=True)
    except Exception as exc:
        raise ValueError('Cannot load weights-only tensor checkpoint') from exc
    if isinstance(obj, dict):
        if not key or key not in obj:
            raise ValueError('Explicit --tensor-key required for tensor dictionaries')
        obj = obj[key]
    elif key:
        raise ValueError('Tensor key supplied for a bare tensor')
    if not isinstance(obj, torch.Tensor) or obj.ndim != 2:
        raise ValueError('Expected a 2D torch.Tensor; no arbitrary Python objects')
    if obj.layout != torch.strided or obj.is_complex():
        raise ValueError('Unsupported tensor layout or complex dtype')
    if not obj.dtype.is_floating_point:
        raise ValueError('Expected floating-point tensor requiring explicit quantization')
    return obj.detach().to(dtype=torch.float64, device='cpu').contiguous().tolist()


def quantize_matrix(matrix, scale: float):
    """Round-to-nearest-even; reject non-finite data and any INT4 overflow."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be finite and > 0')
    if not isinstance(matrix, list) or not matrix or not all(isinstance(r, list) and r for r in matrix):
        raise ValueError('expected nonempty 2D matrix')
    k = len(matrix[0])
    if not 1 <= len(matrix) <= 256 or not 1 <= k <= 4096 or any(len(r) != k for r in matrix):
        raise ValueError('invalid or ragged shape')
    result = []
    for i, row in enumerate(matrix):
        converted = []
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'non-finite/non-numeric coefficient ({i},{j})')
            q = round(value / scale)  # Python round: ties to even
            if q < -8 or q > 7:
                raise ValueError(f'INT4 overflow at ({i},{j}): {q}; choose a larger scale; no clipping')
            converted.append(q)
        result.append(converted)
    return result


def import_tensor(path, scale, key=None, bias=None):
    path = Path(path)
    raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    matrix = load_tensor(path, key)
    weights = quantize_matrix(matrix, scale)
    m, k = len(weights), len(weights[0])
    if bias is None:
        bias = [0] * m
    if not isinstance(bias, list) or len(bias) != m or any(type(x) is not int for x in bias):
        raise ValueError('bias must be a list of signed INT32 integers of length M')
    model = {
        'format': 'msif-int4-v1', 'shape': [m, k], 'weights': weights, 'bias': bias,
        'numeric': {'weight': 'int4-twos-complement', 'activation': 'int8-twos-complement',
                    'accumulator': 'int32', 'overflow': 'reject'},
        'provenance': {
            'schema': 'msif-tensor-import-v1', 'source_file_sha256': raw_sha,
            'tensor_key': key, 'source_format': 'pytorch-weights-only',
            'tensor_shape': [m, k], 'layout': 'row-major-output-input',
            'quantizer': 'symmetric-per-tensor-int4-round-to-nearest-even-reject-overflow',
            'scale_hex': float(scale).hex(), 'zero_point': 0,
            'source_values_sha256': sha(matrix),
        },
    }
    check(model)
    return model


def build_from_tensor(path, scale, out, key=None, bias=None):
    model = import_tensor(path, scale, key, bias)
    manifest = write_build(model, out)
    # Existing manifest already hashes the complete model including provenance.
    return {'manifest': manifest, 'provenance': model['provenance']}
