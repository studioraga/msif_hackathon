# Governance crosswalk to source snapshot v0.21.1

Source reference: uploaded governance archive, commit `ea95206`.

| Governance source code | Intended MSIF role | Current implementation |
|---|---|---|
| `src/portable_ai_governance/supply_chain/signing.py` | Ed25519 artifact sign / verify | Adapter directly imports and calls real functions |
| `src/portable_ai_governance/kernel/evidence.py` | HMAC-chained event evidence | Available upstream, not yet invoked in MSIF |
| `src/portable_ai_governance/multi_agent/` | Agent orchestration | Design-only mapping; not integrated |
| `src/portable_ai_governance/tool_agent/` | Bounded tool execution | Design-only mapping; not integrated |
| `src/portable_ai_governance/kernel/approvals.py` | Human authorization | Design-only mapping; not integrated |
| `src/portable_ai_governance/ai_security/` | Model provenance and AI evaluations | Design-only mapping; not integrated |
| `src/portable_ai_governance/compliance_risk/` | Risk posture and control mapping | Design-only mapping; not integrated |
| `src/portable_ai_governance/security_ops/` | Exceptions, monitoring and response | Design-only mapping; not integrated |

## Source documentation mappings

The upstream repository has root `README.md`, root `instruction.md`, `docs/Architecture.md`, `docs/Deployment.md`, `docs/Milestones.md`, `docs/Prerequisites.md`, `docs/Validation.md`, `docs/oneshot-deployment.md`, and milestone-prefixed documents. In particular:

- `docs/M10-Multi-Agent-Workflows.md`
- `docs/M2-Security-Control-Plane.md`
- `docs/M3-Supply-Chain.md`
- `docs/M4-AI-System-Security.md`
- `docs/M5-Compliance-Risk-Automation.md`
- `docs/M6-Bounded-Evidence-Analyst.md`
- `docs/M7-Tool-Using-Agent.md`
- `docs/M8-Approval-Controlled-Actions.md`
- `docs/M9-Security-Operations.md`
- `docs/Documentation-Audit-M21.1.md`

Preserve those real names in cross-repository references. Do not create duplicate aliases in the upstream repository or claim they are present. Inspect provenance, contract, failure behavior and test coverage before integrating additional functions.


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
