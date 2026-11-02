# Instruction

## M7.2 exact research operating sequence — 2 November 2026

The actual branch has research commits `01-p01` → `02-p2b` → `03-p3` → `04-p4` → `05-p5-area` → `06-p5-vcd` → `07-g1`; `08-docs` is the proposed final **documentation** freeze. Use the controller plus its exact adjacent JSON manifest; do not use invalid aliases such as `05-p5`. The current parent before Commit 08 is `3411e86f89095a149f03cd947399eb4cac6c3bb2`. Confirm protected M7.1-LQ tag and empty staged index, backup tracked/untracked and ignored EDA evidence separately, review files and hashes, run 110-test baseline and focused negative checks, and only after manual review stage exactly the approved group. Verify post-commit ancestry and path membership.

Read [Architecture](Architecture.md#m72-authoritative-research-architecture--reconciled-2-november-2026), [Milestones](Milestones.md#m72-branch-history-and-release-gates--2-november-2026), [Validation](Validation.md#m72-evidence-and-validation--2-november-2026) and [future Git decisions](M7.2-Future-Commit-and-Tags.md) before interpreting statuses. Research commits do not establish release acceptance. No automatic remote push, merge or tag.

Read `README.md` first, then run `scripts/node1_audit.sh` and `scripts/verify.sh`. Preserve emitted logs. Review limitations in `docs/Architecture.md`; study `docs/Governance-Crosswalk.md` before importing any additional PAG code. Use Git for review, but do not push without manual approval. Re-run the reproducible build after any compiler or model change.


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

## M2.1 invocation

From the repository root: `./scripts/verify_m21.sh`. Examine `build/m21/formal.log`, `build/m21/exhaustive.log`, and `build/m21/evidence.json` prior to committing. See [M2.1](M2.1-Formal-Equivalence.md).


> **M2.1 validation correction (2026-10-25):** For M2.1, execute the corrected verifier and inspect simulator errors, formal SAT success, Verilator lint and fresh evidence.

## M2.2 small-GEMV verification candidate

The bounded 2×4 GEMV arithmetic miter, generated RTL sequential tests, fail-closed Verilator lint, independent simulator checks, and evidence acceptance criteria are specified in [M2.2 — Small GEMV and Sequential Verification](M2.2-Small-GEMV-and-Sequential-Verification.md). On pages located within `docs/`, use the relative link `M2.2-Small-GEMV-and-Sequential-Verification.md`. Run `./scripts/verify_m22.sh` on Node1 only after M2.1 has been merged and revalidated. This milestone is not automatically accepted on source generation alone.


### M2.2 reset-testbench erratum (2026-10-25)
The first Node1 M2.2 simulation stopped at `async reset failed` because the testbench initialized active-low reset to zero without generating a falling edge. The corrected testbench initializes `rst_n=1`, then explicitly drives `rst_n=0` and waits for nonblocking assignments to settle before checking reset outputs. Repeat all three variant simulations and proof/lint gates; earlier M2.2 evidence is not acceptable. This is a testbench correction, not a change to the accepted M2.1 RTL compiler.

## M5.1 — PyTorch tensor import candidate

[M5.1 Instructions](M5.1-Quantized-Tensor-Ingestion.md) defines deterministic per-tensor signed INT4 quantization, row-major ordering, SHA-256 source provenance, explicit scale and fail-closed overflow. Execute `./scripts/verify_m51.sh` in addition to earlier milestone gates. This candidate is **not yet Node1-qualified** and does not imply production-model quantization accuracy, PDK PPA, or governance approval.


## M5.1 locked dependency qualification

See [PyTorch/NumPy environment qualification](M5.1-PyTorch-Environment-Qualification.md). `pyproject.toml` defines NumPy 2.5.4 and the explicit cu130 PyTorch 2.14.0 GPU group; `uv.lock` must be generated by `uv lock` and verified on Node1. Use `uv sync --locked --group gpu` and `./scripts/validate/pytorch/qualify_project_environment.sh` before `./scripts/verify_m51.sh`. `requirements.txt` is a core-only compatibility manifest and cannot certify CUDA. GPU, sm_120, PTX-JIT-disabled execution and compiled CUDA extension acceptance remain Node1-only gates.


## M7.1 synthesis comparison candidate

The next prototype gate is [M7.1 controlled A/B/C synthesis](M7.1-Controlled-Synthesis-Comparison.md) (see `docs/M7.1-Controlled-Synthesis-Comparison.md` from documents). Run `./scripts/verify_m71.sh` after all older milestone regressions. Generic cell counts and optional Liberty-mapped cell counts do not establish timing, routed area, power or release approval. PAG EvidenceLedger and human approval integration remain planned.


## M7.1-L — optional standard-cell Liberty mapping qualification (2026-10-26)

**Node1 order:** verify previous milestone gates → `./scripts/verify_m71.sh` (generic) → review Liberty source/license/PVT/hash → `python3 -m msif.cli build --out build/m71_liberty --m 2 --k 4 --seed 2026` → `python3 -m msif.cli verify --out build/m71_liberty` → `python3 scripts/m71_compare.py --build build/m71_liberty --liberty "$MSIF_LIB"` → inspect `m71_evidence.json` and mapping logs. See [Node1 Liberty walkthrough](M7.1-Liberty-Mapping-Qualification.md).

## M7.1-LQ Node1 bounded verification — 26 October 2026

**PASS:** mapped A/B/C standard-cell inventories and 260-vector gate-level regression per architecture on Node1 (746/690/746 mapped cells). See [canonical LQ evidence, incident history and limitations](M7.1-LQ-Mapped-Netlist-Verification.md). Full sequential formal proof, physical PPA and governed release authorization remain **NOT VERIFIED**. Continue with the document-first [M7.2/G1 engineering handoff](M7.2-G1-Engineering-Handoff.md); do not claim those milestones complete or production-qualified.


## M7.2 physical-flow implementation boundary — 26 October 2026

**M7.2 operator order:** review platform/license/PVT → confirm M7.1-LQ audit → P0/P1 preflight → SDC review → ORFS dry-run → opt-in P3 attempt → independent reports/STA/DRC checks → human review before Git closure. [Exact commands](M7.2-Physical-Design-Qualification.md).

## Node1 M7.2 execution state and evidence boundary

See [M7.2 physical runbook](M7.2-Physical-Design-Qualification.md) for the 28 October 2026 programmable-only completed exploratory route, unresolved P2b–P5, warnings and independent A/B/C audit. Do not represent the programmable Make exit 0 as release authorization.


## M7.2 P2b–P5 implementation continuation (28 October 2026)

This section is additive to the accepted P0/P1 baseline and does not authorize a commit, tag, or release.

```mermaid
flowchart TD
  L[Accepted M7.1-LQ A/B/C netlist + SHA-256 + 260-vector evidence] --> P2[P2b exact hash-pinned netlist preparation]
  P2 --> N[Compatibility-only signed declaration normalization or explicit no-op]
  N --> I[OpenROAD read_verilog / Liberty / LEF / OpenDB import]
  I --> E{Structural import and provenance pass?}
  E -->|No| X[BLOCKED]
  E -->|Yes| Q[Independent connectivity and sequential equivalence: NOT VERIFIED]
  B[Original M7.1 RTL and shared P0/P1 SDC] --> R[Exploratory ORFS RTL synthesis for A/B/C]
  R --> F[P3 floorplan + PDN + placement + CTS + detailed route]
  F --> T[P4 extracted SPEF and corner-labelled STA]
  T --> C[P5 comparable area/timing and qualified activity-based power]
  C --> D{Independent report reviews complete?}
  D -->|No| X
  Q --> D
  D -->|Yes| G[G1 authorization, independent separate gate]
```

### Implementation modules and status

- `scripts/m72_exact_lq_import.py`: hash-pin exact accepted `build/m71_liberty/m71_lq/msif_*_mapped.v` into isolated P2b candidates, preserve raw files, permit only reviewed signed-port compatibility transforms (including explicit no-op) and optionally test import into OpenDB; **does not implement post-import formal equivalence or a complete ORFS place-and-route handoff**.
- `scripts/m72/m72_normalize.py`: previously verified programmable declaration transform, now also emits a fail-closed identity/no-op receipt when no signed declarations exist. Prevents valid fixed/ROM structural netlists from being rejected solely due to absence of signed ports.
- `scripts/m72_report_review.py`: collects A/B/C final ODB/GDS/SPEF/SDC, detailed-route report and finish report, hashes artifacts, extracts labelled timing *observations*, and refuses missing evidence. A report-present result is explicitly not signoff.
- `scripts/m72_physical_audit.py`: retains a conservative three-architecture inventory with no signoff from existence alone.

### Node1 execution sequence

```bash
cd ~/dev/pub/ai-sys1/msif-hack/push/msif_hackathon
source .venv/bin/activate
export MSIF_ORFS="$HOME/eda/qualified-pdks/OpenROAD-flow-scripts"
export PYTHONPATH="$PWD/src:$PWD/scripts"
python3 -m unittest discover -s tests -v
PYTHONPATH="$PWD/scripts/m72" python3 -m unittest discover -s scripts/m72 -p 'test_m72_normalize.py' -v
python3 scripts/m72_exact_lq_import.py --orfs "$MSIF_ORFS" --out build/m72/p2b-exact-lq
# Only after reviewing the manifest and no stale output directory:
# python3 scripts/m72_exact_lq_import.py --orfs "$MSIF_ORFS" --out build/m72/p2b-exact-lq-execute --execute
# Independently perform the normalizer ORFS route on fixed and rom; use separate FLOW_VARIANTs.
python3 scripts/m72_report_review.py --flow "$MSIF_ORFS/flow" --out build/m72/p3p5-report-ledger.json
```

### Outstanding hard gates

- **P2b:** OpenDB import with matching accepted hashes is an *import experiment*. Cell-pin/bit-accurate structural preservation, sequential equivalence, and a fully integrated exact-LQ physical implementation remain separate, unimplemented closure gates.
- **P3:** A is routed experimentally; B/C must be routed. Independently review legal placement, PDN connectivity, detailed-route DRC, antenna checks, macro inclusion, and reproducible ODB/GDS against reports.
- **P4:** Timing reports from a single TT corner and relaxed research SDC cannot establish multi-corner signoff. Review all setup/hold paths, unconstrained endpoints, reset recovery/removal, RCX corner provenance and additional PVT views where available.
- **P5:** Report standard-cell (not die/core) area and distinguish core area, utilization, clock and I/O delay assumptions. Power without explicit VCD/SAIF/activity provenance is an estimate only. A/C arrays are not qualified SRAM/ROM macros.
- **G1:** Release approval and Node2 independent receipts remain `NOT_VERIFIED`.
