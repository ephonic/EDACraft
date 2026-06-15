# RTLCraft Document-Driven Layered SoC Flow Audit - 2026-06-15

## Executive Summary

Current status: **partially aligned, not yet fully compliant** with the target of a document-driven, layered SoC design flow.

The repository has strong building blocks for the target flow:

- A clear 6-layer Earphone SoC directory structure under `earphone/modules/<module>/layer_L{1..6}_*/`.
- Real L1/L2/L5 implementations for the main pilot modules.
- Passing module-level tests: `60 passed`.
- Passing framework tests for document templates, contracts, and SpecIR-to-DSL: `63 passed`.
- A working legacy full-SoC command, `python earphone/design_earphone.py`, which reports `Overall: PASS`, emits 9 Verilog modules, runs constraint propagation, and records review artifacts.

However, the current flow is **not yet genuinely document-driven end to end**:

- The documented new entry point `python -m earphone.flow` fails at import time.
- `earphone/flow.py` still delegates full SoC closure to the legacy monolithic `design_earphone.py`.
- `docgen.py` mostly introspects code and writes Markdown. That is useful documentation automation, but it is closer to code-driven documentation than documentation-driven implementation.
- L3/L4/L6 layer tests are mostly absent, and some generated specs still contain fallback text such as `TBD` or `See DSL implementation`.
- Human approval/checkpoint semantics described in README/Tutorial are not enforced by the executable flow.

Recommendation: treat the current state as a **working legacy Spec2RTL demo plus a partially migrated layered documentation scaffold**, not yet as the authoritative document-driven SoC design flow.

## Design Goal Interpreted From README/Tutorial

The target flow is described as:

1. **Layered lowering**: SpecIR -> BehaviorIR -> CycleIR -> ArchitectureIR -> StructuralIR -> DSL -> Verilog.
2. **One module, one layer directory**: each IP owns its layer-local source, specs, tests, and reports.
3. **Documents as first-class inputs**: top-level specs drive module specs; module/layer specs drive implementations and tests.
4. **Human checkpoints**: agent prepares artifacts, human approves important transitions.
5. **Cross-layer verification**: behavior, cycle, DSL, and Verilog evidence should match or block progression.
6. **Traceability**: constraints, decisions, generated assertions/sequences, and reports should be reviewable.

The repo already documents these goals in `README.md`, `Tutorial.md`, and `earphone/design_spec.md`.

## Evidence Collected

Commands run during audit:

```bash
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft python -m earphone.flow
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft pytest earphone/modules -q
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft pytest tests/test_doc_templates.py tests/test_contract_framework.py tests/test_spec_to_dsl_flow.py -q
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft python earphone/design_earphone.py
```

Observed results:

- `python -m earphone.flow`: **FAIL**
  - ImportError: `cannot import name 'EarphoneRV32' from 'earphone.modules.rv32'`.
  - Cause: `earphone/flow.py` imports `RV32IM_ISS, EarphoneRV32`, but `earphone/modules/rv32/__init__.py` only exports `RV32IM_ISS`.
- `pytest earphone/modules -q`: **PASS**
  - `60 passed in 22.82s`.
- `pytest tests/test_doc_templates.py tests/test_contract_framework.py tests/test_spec_to_dsl_flow.py -q`: **PASS**
  - `63 passed in 11.96s`.
- `python earphone/design_earphone.py`: **PASS**
  - Scaffold compliance: `6/6 OK`.
  - L1 functional tests: `4/4 PASS`.
  - L3 DSL sim tests: `4/4 PASS`.
  - Cross-layer checks: `8/8 PASS`.
  - Intent-driven tests: `4/4 PASS`.
  - Verilog modules: `9/9 generated`.
  - Total Verilog lines: `2445`.
  - Total lint issues: `35`.

## What Is Working Well

### 1. Layered Module Skeleton Exists Across Main Blocks

The main Earphone modules have six source-layer files each:

- `rv32`
- `simd16`
- `fft256`
- `qspi`
- `i2c`
- `sram256k`
- `apb_bridge`

Each has `layer_L1_behavior`, `layer_L2_cycle`, `layer_L3_architecture`, `layer_L4_structure`, `layer_L5_dsl`, and `layer_L6_verilog` source directories. This matches the intended physical organization.

### 2. Real Functional/Cycle/DSL Coverage Exists

The module-level pytest suite exercises L1, L2, and L5 for most modules and passes completely. This is the strongest evidence that the refactor has real implementation substance, not just empty directories.

### 3. Legacy Full SoC Flow Is Operational

`earphone/design_earphone.py` runs the full demo and produces a coherent summary. It also:

- Generates constraint artifacts.
- Emits traceability reports.
- Generates FFT twiddle tables.
- Runs functional tests, DSL tests, cross-layer checks, intent-driven tests.
- Emits Verilog and lint summaries.

This means the project has a working executable baseline while the document-driven refactor continues.

### 4. Constraint/Intent Framework Is Meaningful

`earphone/constraints.py` defines a concrete six-layer path:

```text
SpecIR -> BehaviorIR -> CycleIR -> ArchitectureIR -> StructuralIR -> DSL -> Verilog
```

The legacy flow uses `DesignScaffold`, records design decisions, propagates constraints, emits SVA/UVM-style artifacts, and writes:

- `earphone/specs/09_constraint_traceability.md`
- `earphone/specs/10_design_issues.md`
- `earphone/specs/11_decision_log.md`

This is directionally aligned with industrial traceability.

### 5. Documentation Artifacts Are Broad

There are 149 generated module/layer spec and test report Markdown files under `earphone/modules`. The project has a strong review-artifact surface.

## Main Gaps And Risks

### P0 - New Document-Driven Entry Point Is Broken

`README.md` and `Tutorial.md` say to run:

```bash
python -m earphone.flow
```

But this fails immediately because `earphone.modules.rv32` does not export `EarphoneRV32`.

Impact:

- The official new document-driven entry point is not usable.
- Users are forced back to the legacy command.
- CI cannot rely on the documented flow.

Suggested fix:

- Export `EarphoneRV32` from `earphone/modules/rv32/__init__.py`, or import it directly from `earphone.modules.rv32.layer_L5_dsl.src.dsl` in `flow.py`.
- Add a regression test that invokes `python -m earphone.flow`.

### P0 - The New Flow Delegates To The Legacy Monolith

`earphone/flow.py` says it delegates to the legacy monolithic entry point for full SoC verification closure. Its actual Step 4 runs:

```python
[sys.executable, "-m", "earphone.design_earphone"]
```

Impact:

- The layered flow is not yet the authoritative orchestration.
- Full SoC integration still lives in a monolithic script.
- The new structure can drift from the working implementation.

Suggested fix:

- Move orchestration responsibilities from `design_earphone.py` into `flow.py` module-by-module.
- Keep `design_earphone.py` as a compatibility wrapper only after migration.
- Make `flow.py` discover modules and layers instead of hardcoding only RV32.

### P1 - Documentation Is Mostly Generated From Code, Not Driving Code

`docgen.py` introspects Python source, tests, `describe()` functions, and legacy DSL classes, then renders Markdown. This is valuable, but it reverses the stated design direction:

```text
current: code/tests -> docgen -> Markdown
target: Markdown/spec -> IR/contracts/tests/code -> reports
```

Impact:

- Specs can become descriptive snapshots rather than authoritative inputs.
- A wrong implementation can generate plausible documentation after the fact.
- Human approval of documents does not currently gate implementation changes.

Suggested fix:

- Introduce parsed, machine-checkable module/layer spec metadata, for example YAML front matter or JSON sidecars.
- Add a spec conformance checker: `specs/*.md` or sidecar -> expected ports/latency/PPA/contracts -> compare against L1/L2/L5/L6.
- Make `docgen.py` preserve user-authored requirements and append generated evidence, rather than overwrite or fully synthesize the document.

### P1 - Human Checkpoints Are Documented But Not Enforced

The top-level tutorial describes mandatory stop-and-approve checkpoints, but the executable flow runs straight through.

Impact:

- The process is not yet agent-human collaborative in the way the docs promise.
- High-impact defaults and architectural decisions are recorded, but not actually blocked pending approval.

Suggested fix:

- Add explicit gate state files, for example `earphone/specs/checkpoints/CP0_architecture.approved.json`.
- Make `flow.py` refuse to advance past gates unless approval artifacts exist.
- Record approver, timestamp, reviewed files, and hash of approved content.

### P1 - L3/L4/L6 Layer Tests Are Sparse Or Absent

The module pytest suite passes, but discovery shows no `test_*.py` files under L3 architecture, L4 structure, or L6 verilog layer test directories. Several directories contain only `__init__.py`.

Impact:

- Architecture and structure layers are documents/data, but not strongly checked.
- Verilog emitter wrappers are not tested layer-locally.
- The promise "every IR layer has its own test plan and test report" is only partially realized.

Suggested fix:

- Add L3 tests for architecture invariants: stage names, latency choices, reset PC, bus widths.
- Add L4 tests for structural connectivity: required subblocks, interface names, one-to-one port map sanity.
- Add L6 tests for emitter behavior: Verilog is emitted, module name is present, lint report is captured, generated file path is stable.
- Make empty test directories produce `NO TESTS` as a blocking result for sign-off layers, not a successful-looking report.

### P1 - Cross-Layer Verification Is Uneven

`design_earphone.py` reports 8/8 cross-layer checks, but several checks compare only a subset of layers:

- SRAM: L1 vs L3, with L2 treated as metadata/status.
- APB bridge: L1 vs L3.
- QSPI: L1 vs L2.
- I2C: L1 vs L2.
- FFT: L1 vs L3.

Impact:

- The reported "L1 == L2 == L3" contract is not uniformly enforced for every module.
- Missing layer comparisons can hide drift between cycle, DSL, and Verilog.

Suggested fix:

- Define per-module expected equivalence chain explicitly.
- Report skipped layer comparisons as `SKIP` with rationale, not as full cross-layer pass.
- Gradually require adjacent-layer checks: L1->L2, L2->L5, L5->L6.

### P2 - Generated Specs Still Contain Placeholder/Fallback Content

Examples found:

- Module specs contain `TBD` port and parameter rows.
- Several generated L3/L4 specs say `See DSL implementation for pipeline details` or `See DSL implementation for sub-block details`.

Impact:

- The documents are not yet complete enough to drive implementation.
- Reviewers must inspect DSL to learn key architecture facts, which weakens the layered abstraction.

Suggested fix:

- Fail doc generation or sign-off when `TBD`, `placeholder`, or `See DSL implementation` appears in required sections.
- Require each L3/L4 `describe()` to provide ports, pipeline, subblocks, interfaces, and invariants.

### P2 - README/Tutorial Are Not Fully Consistent With Implementation

README/Tutorial emphasize `python -m earphone.flow` as the new path, but `earphone/README.md` and `earphone/Tutorial.md` still present `python earphone/design_earphone.py` as the real full flow. The implementation confirms the latter is currently the working path.

Impact:

- New users may follow the newer command and fail.
- The project has two overlapping narratives: "new document-driven flow" and "legacy monolithic flow".

Suggested fix:

- Until `flow.py` is fixed, update docs to state: `design_earphone.py` is the working full flow; `flow.py` is the migration entry.
- Once `flow.py` works, invert this: make `flow.py` official and keep `design_earphone.py` as compatibility.

## Compliance Matrix

| Goal | Status | Evidence |
|------|--------|----------|
| Layered module directories | Mostly met | Seven modules have L1-L6 source files |
| L1/L2/L5 executable models | Mostly met | `pytest earphone/modules -q` passes 60 tests |
| New document-driven entry | Not met | `python -m earphone.flow` import failure |
| Full SoC executable closure | Met via legacy path | `python earphone/design_earphone.py` passes |
| Documents as first-class inputs | Partially met | Specs exist, but `docgen.py` is code-introspection driven |
| Cross-layer verification | Partially met | 8 checks pass, but not all are full adjacent-layer chains |
| Constraint traceability | Mostly met | Scaffold, reports, decisions, generated artifacts exist |
| Human approval checkpoints | Not met | No executable approval gate found |
| Per-layer tests/reports | Partially met | Reports exist; L3/L4/L6 local tests mostly absent |
| Verilog/lint artifact generation | Met | 9 modules emitted, 35 lint warnings reported |

## Framework Optimization Direction

The current problem is not just that templates contain stubs. The deeper issue is that the framework treats Markdown mostly as a rendered report, while the desired flow needs documents to become **layer contracts** that drive generation, verification, and feedback.

The recommended direction is to turn the flow into a closed loop:

```text
Previous layer approved contract
  -> current layer editable spec
  -> completeness gate
  -> code/test generation
  -> verification
  -> feedback classification
  -> document/code update
  -> approval gate
  -> next layer
```

### 1. Split Human Authored Spec From Generated Evidence

Each layer document should have two kinds of content:

- **Authoritative authored sections**: requirements, ports, timing, protocol, assumptions, invariants, PPA targets, decisions.
- **Generated evidence sections**: extracted implementation summary, test inventory, pass/fail report, lint report, traceability table.

`docgen.py` should no longer freely regenerate the whole document as if code is the source of truth. It should preserve authored sections and only refresh generated evidence blocks.

Recommended mechanism:

```markdown
<!-- BEGIN:AUTHORED requirements -->
Human/agent editable layer requirements.
<!-- END:AUTHORED requirements -->

<!-- BEGIN:GENERATED test_report -->
Regenerated by docgen.
<!-- END:GENERATED test_report -->
```

This prevents a rough implementation from overwriting or diluting the actual design intent.

### 2. Add Machine-Checkable Sidecars For Every Layer

Markdown is good for review, but generation and verification need structured data. Each layer should emit and consume a sidecar:

```text
layer_L<N>_<name>/specs/
  <NN>_<layer>_spec.md
  <NN>_<layer>_contract.json
  <NN>_<layer>_feedback.json
```

The contract sidecar should include:

- `schema_version`
- `module_name`
- `layer`
- `source_requirements`
- `ports`
- `state`
- `protocols`
- `timing`
- `ppa`
- `invariants`
- `assumptions`
- `derived_from`
- `traceability_ids`
- `approval_status`

The Markdown template should be rendered from this sidecar plus human-authored narrative, not from ad hoc placeholders.

### 3. Add A Completeness Gate Before Code Generation

A layer must not generate code if required fields are missing. The gate should fail on:

- `TBD`
- `placeholder`
- `See DSL implementation`
- empty port tables
- missing reset behavior
- missing latency/throughput assumptions
- missing verification intent
- missing upstream `derived_from`
- no tests for a required executable layer

Recommended CLI behavior:

```bash
python -m earphone.flow --module rv32 --to L3
```

Should execute:

```text
parse L2 contract
render/fill L3 contract draft
validate L3 completeness
if incomplete: stop and emit L3_feedback.json
if complete: generate arch.py + tests
run L3 tests
```

This turns stubs into blockers instead of allowing them to become accepted documentation.

### 4. Make Layer Generation Consume The Previous Layer Contract

Each layer generator should take the previous approved contract as input:

| Target Layer | Input | Generated Outputs | Required Verification |
|--------------|-------|-------------------|-----------------------|
| L1 BehaviorIR | L0/SpecIR contract | `behavior.py`, L1 tests | Functional directed tests |
| L2 CycleIR | L1 contract + behavior traces | `cycle.py`, latency tests | L1 vs L2 equivalence |
| L3 ArchitectureIR | L2 contract + timing/PPA targets | `arch.py`, arch invariant tests | architecture checks |
| L4 StructuralIR | L3 contract | `structure.py`, connectivity tests | subblock/interface checks |
| L5 DSL | L4 contract | `dsl.py`, simulator tests | L2/L4 vs L5 equivalence |
| L6 Verilog | L5 contract | `.v`, lint, RTL tests | DSL vs Verilog, lint, sim |

This replaces "write broad docs after implementation" with "generate the next implementation from the last approved layer".

### 5. Introduce A Layer Feedback Taxonomy

Feedback should be structured and actionable, not just free-form text. Reuse and extend `ConstraintFeedback` into layer feedback items:

```json
{
  "uid": "FB-RV32-L2-001",
  "module": "rv32",
  "source_layer": "CycleIR",
  "detected_at_layer": "DSL",
  "category": "contract_gap | code_bug | test_gap | ppa_miss | ambiguity",
  "severity": "blocker | warning | info",
  "message": "DIV latency not specified in L2 contract.",
  "suggested_actions": [
    "Update L2 timing.div_latency_cycles",
    "Regenerate L2 tests",
    "Regenerate L5 divider control"
  ],
  "target_files": [
    "earphone/modules/rv32/layer_L2_cycle/specs/02_cycle_contract.json"
  ]
}
```

The flow should use this feedback to decide whether to:

- patch the document contract,
- patch generated code,
- add or update tests,
- request human clarification,
- or block the layer transition.

### 6. Make Tests First-Class Layer Artifacts

For each layer, tests should be generated from the same contract that generates code.

Examples:

- Port table -> import/instantiation tests.
- Reset behavior -> reset-state tests.
- Protocol table -> valid/ready or APB transaction tests.
- Timing contract -> latency tests.
- Invariants -> assertions or pytest checks.
- PPA constraints -> static analyzer checks.

The test report should include both:

- tests discovered from files,
- tests expected by contract.

If expected tests are missing, the report should fail as `TEST_GAP`, not pass as `NO TESTS`.

### 7. Preserve Traceability IDs Through Code And Tests

Every requirement should carry a stable ID:

```text
REQ-RV32-DIV-001
REQ-RV32-RESET-001
REQ-SIMD16-VADD-001
```

Generated code and tests should reference those IDs in comments or metadata:

```python
# trace: REQ-RV32-DIV-001
def test_div_zero_behavior():
    ...
```

```verilog
// trace: REQ-SIMD16-VADD-001
assert property (...);
```

Then reports can answer:

- Which requirements have code?
- Which requirements have tests?
- Which requirements have Verilog/SVA evidence?
- Which requirements are unverified?

### 8. Add Approval State To The Flow

Each layer should have an explicit lifecycle:

```text
Draft -> Complete -> Generated -> Verified -> Approved -> Superseded
                                      |
                                   Blocked
```

The flow should not proceed from one layer to the next unless:

- the contract is complete,
- code generation succeeded,
- required tests passed,
- feedback has no blockers,
- and approval exists where required.

Approval can be represented as:

```text
layer_L3_architecture/specs/03_architecture_approval.json
```

Containing:

- approved contract hash,
- reviewer,
- timestamp,
- approved files,
- unresolved warnings accepted by reviewer.

### 9. Change `docgen.py` Into `docsync`

The current `docgen.py` should evolve into a bidirectional synchronizer:

```text
parse authored Markdown
  -> update contract JSON
  -> validate completeness
  -> render generated evidence blocks
  -> preserve authored sections
```

Suggested modules:

- `rtlgen/doc_contract.py`: Markdown/JSON contract schema.
- `rtlgen/doc_validate.py`: completeness and anti-stub checks.
- `rtlgen/layer_codegen.py`: contract-to-code generation.
- `rtlgen/layer_testgen.py`: contract-to-test generation.
- `rtlgen/layer_feedback.py`: feedback schema and merge logic.
- `earphone/flow.py`: project-specific orchestration.

### 10. Target End-State For `earphone.flow`

The desired `earphone.flow` should become a stage machine:

```bash
python -m earphone.flow --module rv32 --from L0 --to L6
python -m earphone.flow --module all --check
python -m earphone.flow --module qspi --repair-feedback FB-QSPI-L5-003
```

For each module and layer, it should:

1. Load previous approved contract.
2. Create or update current layer contract.
3. Validate document completeness.
4. Generate or update code.
5. Generate or update tests.
6. Run layer-local tests.
7. Run adjacent-layer equivalence.
8. Emit feedback.
9. Refresh generated evidence in Markdown.
10. Stop for approval when required.

This is the key shift from "documents are generated reports" to "documents are active contracts in the design loop".

## Recommended Next Actions

1. Fix `python -m earphone.flow` import failure and add a CI test for it.
2. Change `flow.py` from RV32-only to module discovery over `earphone/modules/*`.
3. Move full-SoC orchestration out of `design_earphone.py` into `flow.py`; leave a compatibility wrapper.
4. Add machine-checkable spec metadata and a spec-to-code conformance checker.
5. Add L3/L4/L6 layer-local tests and make no-test reports block sign-off where a layer is required.
6. Make cross-layer reporting explicit about which adjacent layer comparisons ran, passed, failed, or skipped.
7. Add checkpoint approval artifacts and enforce them in `flow.py`.
8. Add placeholder detection to doc generation/sign-off.

## Bottom Line

The codebase has made substantial progress toward the target architecture. It has real modules, real tests, a working SoC generation baseline, and a promising constraint traceability framework.

The main issue is process authority: today the **legacy executable flow is authoritative**, while the **document-driven layered flow is still a scaffold around it**. To meet the stated design goal, make `earphone/flow.py` the working orchestrator, make specs machine-checkable inputs, enforce human gates, and close the missing L3/L4/L6 verification gaps.

## Implementation Update - 2026-06-15

This pass moved the RV32 pilot from a document scaffold toward an executable document-driven chain:

- `python -m earphone.flow` now imports the RV32 package cleanly, runs strict RV32 document generation, executes all RV32 layer-local tests from L1 through L6, and then runs the legacy full-SoC closure flow.
- RV32 layer specs now explicitly consume the previous layer's spec, test plan, and test report, and emit their own spec, test plan, and test report as inputs to the next layer.
- RV32 test plans and reports are generated for every layer and are included in strict placeholder/stub validation. The generated RV32 docs currently scan clean for unfilled `{{ ... }}` placeholders, `TBD`, and stale "See DSL implementation" fallbacks.
- `specs/docgen_feedback.json` now records structured feedback with severity counts. Document-quality blockers, missing layer tests, and layer test failures are written with the detected layer and upstream feedback target.
- Added RV32 L2/L3/L4/L5/L6 layer tests and fixed L6 Verilog emission so per-layer reports contain real PASS evidence.

Current confirmation:

1. For the RV32 pilot, yes: documents are refined and passed layer by layer, and test plans/test reports are passed through the same L1-to-L6 chain.
2. For the RV32 pilot, yes: intermediate document or test issues can be emitted as structured feedback to the current or upstream layer through `docgen_feedback.json`; the existing `DesignScaffold` continues to provide constraint feedback for the legacy SoC closure path.

Remaining limitation:

- The above is fully implemented for RV32 as the migration pilot. The same strict document/test/report propagation and semantic feedback loop still needs to be generalized across SIMD16, FFT256, QSPI, I2C, SRAM, APB bridge, and top-level SoC orchestration.
- Feedback is currently structured and blocking, but automatic semantic repair across layers is still future work; the current behavior stops the flow and records where the repair should feed back.
