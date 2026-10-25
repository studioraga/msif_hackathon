# Architecture

## Processing boundary

1. Input model: deterministic JSON matrix of signed INT4 coefficients with signed INT32 biases.
2. M1 reference: exact signed INT8 activations and INT32 accumulation without overflow.
3. M5 compiler: canonical JSON plus RTL variants generated deterministically.
4. M2 variants: programmable initialized register weights, elaboration-fixed coefficients, and ROM-like initialized array.
5. Tests: exhaustive atomic pairs, fixture boundaries, manifest tamper detection; additional cycle simulation/formal tests remain required before claiming RTL equivalence.
6. M7-lite: optionally perform Yosys synthesis. The results are generic cells, not physical power/area/timing.
7. Governance: hash each built artifact; optionally use PAG Ed25519 signatures to authorize a bounded release.

## Deliberate limitations

No automatic Meta API calls; no actual model-directed optimizer, mask-ROM macro, quantized activation calibration, INT8 requantizer, transistor simulation, physical placement/routing, formal proof, FPGA or silicon. These are later extensions.

## Mathematical contract

$$y_i = b_i + \sum_{j=0}^{K-1} w_{ij}x_j$$

$$w_{ij}\in[-8,7],\quad x_j\in[-128,127],\quad y_i\in\mathbb{Z}_{32}$$

Biases are checked conservatively to avoid INT32 overflow. RTL ports emit INT32 values; round-to-nearest-even and saturating INT8 are **not yet implemented**, even though they are required by the full MSIF specification.

## GitHub-native milestone graph

```mermaid
gitGraph
    commit id: "M0 numerical contract"
    commit id: "M1 Python golden model"
    commit id: "M2 RTL variants"
    commit id: "M5 model compiler"
    branch m7-lite
    checkout m7-lite
    commit id: "M7 synthesis exploration"
    checkout main
    commit id: "Governance adapter"
```

The diagram represents a *planned logical milestone sequence*, not actual commits in a pushed Git repository.


## Node1 qualification correction — 25 October 2026

The initial `verify.sh` accepted successful Python tests while printing `SKIP` for unavailable Verilog simulation and synthesis tools. This did **not** satisfy M2 RTL equivalence or M7-lite synthesis acceptance. The revised script **fails closed** (exit code 2) when `iverilog`/`vvp` or `yosys` is missing, runs actual RTL test vectors against the Python oracle and archives per-variant simulation/synthesis logs under ignored `build/demo/`. The initial Node1 log showed `yosys`, `iverilog`, `verilator`, `openroad`, `klayout`, and `ngspice` missing; their installation is not established by the patch. Only Icarus and Yosys are hard requirements for the strict prototype gate. `scripts/install_node1_tools.sh` is dry-run by default; `--install` is an explicit host modification.

**Validity boundary:** Icarus simulations exercise deterministic boundary/random input vectors but are not exhaustive for 16×64 GEMV; formal equivalence, signed rounding/INT8 saturation, mapped Liberty area/STA, parasitics and physical DRC/LVS are not delivered. Generic Yosys `stat` must not be presented as PDK-based area/power/timing. Initial `programmable` weights are initialized registers, not software-loaded runtime-programmable memory; `rom` is an inferred array, not a qualified silicon ROM macro. Signing is optional for research, mandatory for any governed release.

**Traceability:** [README](../README.md) · [Prerequisites](Prerequisites.md) · [Validation](Validation.md) · [Architecture](Architecture.md) · [Milestones](Milestones.md) · [Governance Crosswalk](Governance-Crosswalk.md) · [Deployment](Deployment.md) · [Documentation Audit](Documentation-Audit.md) · [One-shot Deployment](oneshot-deployment.md). Original PAG document links in Governance Crosswalk retain the actual `M2-...` through `M10-...` filenames; no nonexistent aliases are promised.


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

## M2.1 proof boundary

An independently generated scalar arithmetic miter compares signed INT4×INT8 multiplication to a sign-extended four-term shift/add network. [Proof contract and limits](M2.1-Formal-Equivalence.md). This is not a full-matrix hardware proof.


> **M2.1 validation correction (2026-10-25):** M2.1 partitions Yosys-only `FORMAL` assertions from Icarus runtime checks to avoid event-trigger transient failures. Only scalar proof is in scope.

## M2.2 small-GEMV verification candidate

The bounded 2×4 GEMV arithmetic miter, generated RTL sequential tests, fail-closed Verilator lint, independent simulator checks, and evidence acceptance criteria are specified in [M2.2 — Small GEMV and Sequential Verification](M2.2-Small-GEMV-and-Sequential-Verification.md). On pages located within `docs/`, use the relative link `M2.2-Small-GEMV-and-Sequential-Verification.md`. Run `./scripts/verify_m22.sh` on Node1 only after M2.1 has been merged and revalidated. This milestone is not automatically accepted on source generation alone.


### M2.2 reset-testbench erratum (2026-10-25)
The first Node1 M2.2 simulation stopped at `async reset failed` because the testbench initialized active-low reset to zero without generating a falling edge. The corrected testbench initializes `rst_n=1`, then explicitly drives `rst_n=0` and waits for nonblocking assignments to settle before checking reset outputs. Repeat all three variant simulations and proof/lint gates; earlier M2.2 evidence is not acceptable. This is a testbench correction, not a change to the accepted M2.1 RTL compiler.
