#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path

import torch
from torch.utils.cpp_extension import load_inline


print("MSIF Developer Agent")
print("PyTorch CUDA Extension / sm_120 Qualification")
print("=" * 64)

print("python =", sys.version)
print("torch =", torch.__version__)
print("torch runtime CUDA =", torch.version.cuda)
print("device =", torch.cuda.get_device_name(0))
print("capability =", torch.cuda.get_device_capability(0))

assert torch.cuda.is_available()
assert torch.cuda.get_device_capability(0) == (12, 0)

os.environ.setdefault(
    "CUDA_HOME",
    "/usr/local/cuda-13.3",
)

os.environ.setdefault(
    "TORCH_CUDA_ARCH_LIST",
    "12.0",
)

os.environ.setdefault(
    "MAX_JOBS",
    "8",
)

cpp_source = r"""
#include <torch/extension.h>

torch::Tensor add_one_cuda(torch::Tensor x);
"""

cuda_source = r"""
#include <torch/extension.h>
#include <cuda.h>
#include <cuda_runtime.h>

__global__ void add_one_kernel(
    float* data,
    long long n
) {
    long long idx =
        static_cast<long long>(blockIdx.x) * blockDim.x
        + threadIdx.x;

    if (idx < n) {
        data[idx] += 1.0f;
    }
}

torch::Tensor add_one_cuda(torch::Tensor x) {
    TORCH_CHECK(
        x.is_cuda(),
        "input must be CUDA"
    );

    TORCH_CHECK(
        x.scalar_type() == torch::kFloat32,
        "input must be float32"
    );

    auto y = x.contiguous().clone();

    const auto n = y.numel();

    constexpr int threads = 256;

    const int blocks =
        static_cast<int>(
            (n + threads - 1) / threads
        );

    add_one_kernel<<<blocks, threads>>>(
        y.data_ptr<float>(),
        static_cast<long long>(n)
    );

    const cudaError_t err =
        cudaGetLastError();

    TORCH_CHECK(
        err == cudaSuccess,
        cudaGetErrorString(err)
    );

    return y;
}
"""

build_dir = Path(
    os.environ.get(
        "TORCH_EXTENSIONS_DIR",
        "/tmp/msif-torch-extensions",
    )
)

build_dir.mkdir(
    parents=True,
    exist_ok=True,
)

module = load_inline(
    name="msif_sm120_extension",
    cpp_sources=[cpp_source],
    cuda_sources=[cuda_source],
    functions=["add_one_cuda"],
    with_cuda=True,
    extra_cuda_cflags=[
        "-O2",
    ],
    verbose=True,
)

print()
print("EXTENSION_FILE=", module.__file__)

x = torch.arange(
    4096,
    dtype=torch.float32,
    device="cuda",
)

y = module.add_one_cuda(x)

torch.cuda.synchronize()

expected = x + 1.0

assert torch.equal(
    y.cpu(),
    expected.cpu(),
)

print("EXTENSION_CORRECTNESS=PASS")
print("RESULT=PASS")
