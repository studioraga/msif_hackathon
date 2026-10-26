# MSIF-AI — Governed Model-Specific Silicon Prototype

**Status:** Hackathon research prototype; not fabricated, not physically signed off. Independent companion to Portable Agentic AI Governance **v0.21.1** (snapshot commit `ea95206`).

## Scope and numerical contract

- M0: signed INT4 weights, signed INT8 activations, INT32 output, `y = Wx+b` (16×64 default), exact arithmetic.
- M1: deterministic golden model and all **4096** INT4×INT8 pairs tested.
- M2: programmable, fixed-coefficient and register-initialized ROM-style RTL variants, identical one-cycle valid response. The ROM variant is a behavioral/synthesis exploration, **not** a characterized mask-ROM macro.
- M5: deterministic matrix-to-SystemVerilog generator and content fingerprints.
- M7-lite: optional Yosys technology-independent synthesis; **no PDK-qualified power, area, routed timing or signoff**.
- Governance: manifest integrity verification and optional **actual PAG v0.21.1 Ed25519 signing adapter**, not a simulated signature.

## Quick start (Node1 Ubuntu 24.04)

```bash
./scripts/node1_audit.sh
./scripts/verify.sh
PYTHONPATH=src python3 -m msif.cli build --out build/demo
PYTHONPATH=src python3 -m msif.cli verify --out build/demo
```

## Governed artifact signing (optional)

Install the reviewed PAG snapshot into a separate Python environment or make its `src` importable. Provision an Ed25519 key pair *outside* the repository. Use the real PAG `generate_ed25519_keypair` operation if needed. Never commit private keys.

```bash
PYTHONPATH=src:/path/to/governance/src python3 -m msif.cli sign --out build/demo --private-key /secure/key.pem --public-key /secure/key.pub.pem
PYTHONPATH=src:/path/to/governance/src python3 -m msif.cli verify --out build/demo --pubkey /secure/key.pub.pem
```

No Git push, repository update, release or tapeout is performed by this package. Unsigned manifests are integrity-checked but are **not approved releases**.

## Documentation

Start with [Instruction](docs/Instruction.md), [Architecture](docs/Architecture.md), [Prerequisites](docs/Prerequisites.md), [Deployment](docs/Deployment.md), [Validation](docs/Validation.md), [Milestones](docs/Milestones.md), [Documentation Audit](docs/Documentation-Audit.md), [Governance Crosswalk](docs/Governance-Crosswalk.md), [One-shot Deployment](docs/oneshot-deployment.md).

The source specification is the supplied `Model-Specific-AISilicon-Architecture-and-Engineering(1).md`; it remains authoritative for the full 12-milestone research program, not a claim of completeness here.

## Audit and source specification

See [Repository Review](docs/Repository-Review.md) and the unmodified [MSIF Source Specification](docs/MSIF-Source-Specification.md).


## Node1 qualification correction — 25 October 2026

The initial `verify.sh` accepted successful Python tests while printing `SKIP` for unavailable Verilog simulation and synthesis tools. This did **not** satisfy M2 RTL equivalence or M7-lite synthesis acceptance. The revised script **fails closed** (exit code 2) when `iverilog`/`vvp` or `yosys` is missing, runs actual RTL test vectors against the Python oracle and archives per-variant simulation/synthesis logs under ignored `build/demo/`. The initial Node1 log showed `yosys`, `iverilog`, `verilator`, `openroad`, `klayout`, and `ngspice` missing; their installation is not established by the patch. Only Icarus and Yosys are hard requirements for the strict prototype gate. `scripts/install_node1_tools.sh` is dry-run by default; `--install` is an explicit host modification.

**Validity boundary:** Icarus simulations exercise deterministic boundary/random input vectors but are not exhaustive for 16×64 GEMV; formal equivalence, signed rounding/INT8 saturation, mapped Liberty area/STA, parasitics and physical DRC/LVS are not delivered. Generic Yosys `stat` must not be presented as PDK-based area/power/timing. Initial `programmable` weights are initialized registers, not software-loaded runtime-programmable memory; `rom` is an inferred array, not a qualified silicon ROM macro. Signing is optional for research, mandatory for any governed release.

**Traceability:** [README](README.md) · [Prerequisites](docs/Prerequisites.md) · [Validation](docs/Validation.md) · [Architecture](docs/Architecture.md) · [Milestones](docs/Milestones.md) · [Governance Crosswalk](docs/Governance-Crosswalk.md) · [Deployment](docs/Deployment.md) · [Documentation Audit](docs/Documentation-Audit.md) · [One-shot Deployment](docs/oneshot-deployment.md). Original PAG document links in Governance Crosswalk retain the actual `M2-...` through `M10-...` filenames; no nonexistent aliases are promised.


## Node1 observed qualification — October 25, 2026 (v0.1.1)

The user-supplied Node1 log confirms seven Python unit tests passed, all three RTL variants passed 28 deterministic vectors each, and Yosys 0.33 completed generic synthesis with zero `check` problems. Host tools: Icarus Verilog 12.0, Verilator 5.020 and Yosys 0.33. OpenROAD, KLayout and ngspice were not installed; they are not mandatory for the M7-lite generic synthesis gate.

| Variant | 28-vector Icarus | Yosys generic cells | Memory objects after synthesis |
|---|---|---:|---:|
| Programmable | PASS | 123,837 | 0 |
| Fixed-weight | PASS | 115,662 | 0 |
| ROM-style | PASS | 123,837 | 0 |

The fixed-weight variant has 8,175 (approximately 6.60%) fewer generic cells than the programmable baseline **for this particular fixture and synthesis flow**. The programmable and ROM-style variants map to identical generic cell counts, so the experiment does not yet differentiate a physical ROM or SRAM macro. These counts are *not* area, energy, timing, clock frequency, routed congestion or manufacturing evidence. The 28 full-matrix vectors are not an exhaustive proof.

`python3 scripts/node1_evidence.py --build build/demo` reads actual simulator/Yosys logs, requires PASS and zero Yosys `check` problems, and emits `build/demo/node1_evidence.json` with tool versions and log hashes. It fails if evidence is missing. This is a local evidence summary, **not** an approval or signature.

Baseline-freeze policy: freeze M0, M1 and the limited M2/M5/M7-lite implementation after reproducing the verification on Node1 and inspecting the local report. Keep formal proofs, technology-mapped PPA, real ROM macro, governance signature/approval and full source-model quantization as open gates. Existing milestones M3/M4/M6/M8–M11 are not completed.

## M2.1 formal verification candidate

See [M2.1 Formal Equivalence](docs/M2.1-Formal-Equivalence.md). Run `./scripts/verify_m21.sh` on Node1 for exhaustive scalar RTL simulation (4096 pairs) and a separate Yosys SAT assertion proof. A passing Node1 run is required before claiming this milestone; full GEMV equivalence and PDK timing remain unverified.


> **M2.1 validation correction (2026-10-25):** M2.1 correction: the first M2.1 run produced false-positive PASS evidence due to simulator ERROR messages; rerun corrected `scripts/verify_m21.sh` and inspect `docs/M2.1-Formal-Equivalence.md` before committing.

## M2.2 small-GEMV verification candidate

The bounded 2×4 GEMV arithmetic miter, generated RTL sequential tests, fail-closed Verilator lint, independent simulator checks, and evidence acceptance criteria are specified in [M2.2 — Small GEMV and Sequential Verification](docs/M2.2-Small-GEMV-and-Sequential-Verification.md). On pages located within `docs/`, use the relative link `M2.2-Small-GEMV-and-Sequential-Verification.md`. Run `./scripts/verify_m22.sh` on Node1 only after M2.1 has been merged and revalidated. This milestone is not automatically accepted on source generation alone.


### M2.2 reset-testbench erratum (2026-10-25)
The first Node1 M2.2 simulation stopped at `async reset failed` because the testbench initialized active-low reset to zero without generating a falling edge. The corrected testbench initializes `rst_n=1`, then explicitly drives `rst_n=0` and waits for nonblocking assignments to settle before checking reset outputs. Repeat all three variant simulations and proof/lint gates; earlier M2.2 evidence is not acceptable. This is a testbench correction, not a change to the accepted M2.1 RTL compiler.

## M5.1 — PyTorch tensor import candidate

[M5.1 Tensor Ingestion](docs/M5.1-Quantized-Tensor-Ingestion.md) defines deterministic per-tensor signed INT4 quantization, row-major ordering, SHA-256 source provenance, explicit scale and fail-closed overflow. Execute `./scripts/verify_m51.sh` in addition to earlier milestone gates. This candidate is **not yet Node1-qualified** and does not imply production-model quantization accuracy, PDK PPA, or governance approval.


## M5.1 PyTorch and NumPy dependency management (Node1)

**Authoritative dependency definition:** `pyproject.toml` plus committed `uv.lock`;
`requirements.txt` is a core-only pip compatibility file, not the GPU wheel lock.
Python 3.12 x86_64, NumPy 2.5.4 and GPU-group PyTorch 2.14.0 from the
explicit `pytorch-cu130` index are the tested *candidate selection*. The
project must not claim GPU admission until the locked `.venv` passes the
Blackwell sm_120 native-kernel, no-PTX-JIT, and custom-extension gates.

```bash
uv --version
uv lock                              # resolve and create uv.lock on networked Node1
uv sync --locked --group gpu         # reproducible .venv; refuses stale lock
uv run --locked --group gpu python -c 'import numpy, torch; print(numpy.__version__, torch.__version__, torch.version.cuda)'
./scripts/validate/pytorch/qualify_project_environment.sh
./scripts/verify_m51.sh
```

See `docs/M5.1-PyTorch-Environment-Qualification.md`. The external
`/tmp/msif-pytorch-2.14.0-cu130` qualification and all local evidence are
separate from the project lock. No GPU/CUDA validation was performed by
creating this dependency patch.
