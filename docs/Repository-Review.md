# Repository inspection and MSIF dependency determination

## Audited source archives

- `portable-agentic-ai-governance.tar(3).gz`: Git working-tree snapshot, `HEAD ea95206`, worktree clean at inspection, Python distribution version `0.21.1`, 64 files including tests and fixtures under `tests/` (not 64 distinct executable test cases).
- `Model-Specific-AISilicon-Architecture-and-Engineering(1).md`: source specification, revision 1.0, 22 October 2026, sections 1–15.

## What was actually tested

- The full PAG `pytest -q` invocation succeeded in the inspection container, with 214 test progress dots (actual underlying test total not separately counted by pytest's quiet output).
- The existing PAG Ed25519 key-generation, signing, and verification functions worked with an MSIF manifest and an ephemeral private key.
- MSIF golden-model exhaustive test, deterministic fixture test, manifest tamper test, variant-generation smoke test passed.

## Dependency status (separate requirement from observation)

| Requirement | Source implemented? | Runtime verified in inspection container? | Node1 verified? |
|---|---|---|---|
| Governance source, Python package | Yes | Yes, pytest passed | No |
| PAG Ed25519 sign/verify | Yes | Yes, integration smoke test | No |
| EvidenceLedger | Yes | Indirect tests only | No |
| MSIF golden reference | New companion implementation | Yes, Python tests | No |
| MSIF RTL emitters A/B/C | New companion implementation | Output generated only | No |
| Verilog cycle comparison | Not yet implemented | No | No |
| Yosys | Optional script present | Missing tool | No |
| OpenROAD and research PDK | Not included | No | No |
| Meta model API integration | Not included | No | No |
| Agent approval/release policy workflow | PAG capability exists | Not connected to MSIF | No |
| Node2 verification receipt | Upstream concept and tools | Not exercised on MSIF | No |

## Engineering caveats

All RTL candidates must undergo simulator-based comparison against the signed reference and formal checks before making equivalence claims. A behavioral initialized-register 'rom' does not model a qualified ASIC mask ROM. The supplied compiler is a deterministic static-weight emitter, not a graph-level ONNX compiler. Published MSIF M0–M11 acceptance criteria remain broader than this prototype. The governance repository's final M21 release is distinct from the documentation-only `ea95206` HEAD: the archived README names the release commit `e83ebf0`.

The upstream governance repository remains unchanged. No Git push was performed.


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
