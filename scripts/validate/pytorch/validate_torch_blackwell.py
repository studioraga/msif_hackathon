#!/usr/bin/env python3

from __future__ import annotations

import sys
import time

import torch


passes = 0
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    global passes

    if condition:
        print(f"[PASS] {message}")
        passes += 1
    else:
        print(f"[FAIL] {message}")
        failures.append(message)


print("Gemma 4 Developer Agent")
print("PyTorch Blackwell Qualification")
print("=" * 60)

print(f"python={sys.version}")
print(f"torch={torch.__version__}")
print(f"torch_cuda_runtime={torch.version.cuda}")

check(
    sys.version_info[:2] == (3, 12),
    "Python 3.12",
)

check(
    torch.__version__.startswith("2.14.0"),
    f"PyTorch 2.14.0 ({torch.__version__})",
)

check(
    torch.version.cuda is not None,
    f"CUDA-enabled PyTorch ({torch.version.cuda})",
)

check(
    torch.cuda.is_available(),
    "torch.cuda.is_available()",
)

if not torch.cuda.is_available():
    print(f"PASS={passes} FAIL={len(failures)}")
    print("RESULT=FAIL")
    raise SystemExit(1)

device = torch.device("cuda:0")

name = torch.cuda.get_device_name(device)
capability = torch.cuda.get_device_capability(device)
arch_list = torch.cuda.get_arch_list()

print(f"device_name={name}")
print(f"compute_capability={capability}")
print(f"arch_list={arch_list}")

check(
    "RTX 5060 Ti" in name,
    f"expected RTX 5060 Ti ({name})",
)

check(
    capability == (12, 0),
    f"compute capability 12.0 ({capability})",
)

check(
    "sm_120" in arch_list,
    f"native sm_120 listed ({arch_list})",
)

torch.manual_seed(1234)
torch.cuda.manual_seed_all(1234)

print()
print("=== ALLOCATION ===")

x = torch.arange(
    1_000_000,
    dtype=torch.float32,
    device=device,
)

torch.cuda.synchronize()

check(
    x.is_cuda,
    "CUDA tensor allocation",
)

check(
    x.device.type == "cuda",
    "tensor resides on CUDA device",
)

print()
print("=== ELEMENTWISE ===")

y = x * 2.0 + 1.0

torch.cuda.synchronize()

expected = x[:10].cpu() * 2.0 + 1.0
actual = y[:10].cpu()

check(
    torch.equal(actual, expected),
    "elementwise CUDA correctness",
)

print()
print("=== MATMUL ===")

a = torch.randn(
    (2048, 2048),
    dtype=torch.float16,
    device=device,
)

b = torch.randn(
    (2048, 2048),
    dtype=torch.float16,
    device=device,
)

torch.cuda.synchronize()

c = a @ b

torch.cuda.synchronize()

check(
    c.is_cuda,
    "matrix multiplication executed on CUDA",
)

check(
    bool(torch.isfinite(c).all().item()),
    "matrix multiplication finite output",
)

print()
print("=== CUDA EVENT TIMING ===")

start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)

for _ in range(3):
    _ = a @ b

torch.cuda.synchronize()

start.record()

for _ in range(10):
    c = a @ b

end.record()

torch.cuda.synchronize()

elapsed_ms = start.elapsed_time(end)

print(f"elapsed_10_matmuls_ms={elapsed_ms:.3f}")

check(
    elapsed_ms > 0.0,
    "CUDA event timing",
)

print()
print("=== MEMORY ===")

print(
    "allocated_bytes=",
    torch.cuda.memory_allocated(device),
)

print(
    "reserved_bytes=",
    torch.cuda.memory_reserved(device),
)

torch.cuda.synchronize()

print()
print("=" * 60)
print(f"PASS={passes} FAIL={len(failures)}")

if failures:
    for failure in failures:
        print(f"FAILED_CHECK={failure}")

    print("RESULT=FAIL")
    raise SystemExit(1)

print("RESULT=PASS")
