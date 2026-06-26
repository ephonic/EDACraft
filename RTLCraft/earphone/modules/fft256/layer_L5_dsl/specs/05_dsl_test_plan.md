# EarphoneFFT256 — L5 dsl — Verification Test Plan

| Document ID | FFT256-L5_DSL-TP-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Verification test plan for the L5 dsl of EarphoneFFT256.

### 1.2 Scope

Covers directed and cross-layer tests executed at L5 dsl.

### 1.3 Out of Scope
Full SoC integration tests; see integration/ specs.

---

## 2. References

| Document ID | Title | Version |
|-------------|-------|---------|
| FFT256-L5_DSL-001 | EarphoneFFT256 L5 dsl specification | 0.1 |

---

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| Layer contract | Machine-generated Markdown contract that is consumed by the next IR layer. |

---

## 4. Device Under Test (DUT)

| Attribute | Value |
|-----------|-------|
| DUT Name | EarphoneFFT256 |
| DUT Version | 0.1 |
| Hierarchy Path | earphone.modules.fft256.layer_L5_dsl |
| Specification Reference | layer_L5_dsl/specs/05_dsl_spec.md |

---

## 5. Verification Strategy

### 5.1 Verification Approach
Run the pytest cases listed in `layer_L5_dsl/specs/05_dsl_test_plan.md` under `earphone/modules/fft256/layer_L5_dsl/tests`, then publish PASS/FAIL evidence in `layer_L5_dsl/specs/05_dsl_test_report.md`. Test intent: Consumes approved outputs from `FFT256-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), plus verification intent `FFT256-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`) and latest evidence `FFT256-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`).

### 5.2 Verification Levels
| Level | Objective | Method | Responsibility |
|-------|-----------|--------|----------------|
| Unit | Validate layer-local functional correctness | Python pytest + model simulation | RTLCraft Agent |
| Integration | Validate interaction with adjacent layers | Cross-layer equivalence checks | RTLCraft Agent |
| System | Validate SoC-level behavior | Full flow regression | System Architect |

### 5.3 Testbench Architecture
```text
+----------------+      +----------------+      +----------------+
|   Previous-layer contract    |<---->|      DUT       |<---->|   Next-layer checker    |
+----------------+      +----------------+      +----------------+
         ^                       ^
         |                       |
         v                       v
+-----------------------------------------------------------+
|                    Layer pytest assertions and cross-layer equivalence checks                     |
+-----------------------------------------------------------+
```

### 5.4 Verification Methodology
| Method | Usage | Tools |
|--------|-------|-------|
| Constrained-random simulation | Not enabled until directed layer handoff is stable | Not enabled in current pilot |
| Directed tests | Core directed tests from test_*.py | pytest |
| Formal verification | SVA assertions generated from constraints | Verilog formal tools (future) |
| Emulation / FPGA prototyping | Not used in the Python-layer regression | None |

---

## 6. Coverage Strategy

### 6.1 Code Coverage
| Coverage Type | Goal | Tool |
|---------------|------|------|
| Line coverage | 80% | pytest-cov |
| Branch coverage | 70% | pytest-cov |
| FSM coverage | Covered by directed state-transition assertions where the layer has FSM state | pytest assertions |
| Toggle coverage | Covered at L6 Verilog when signal-level RTL is emitted | RTL simulator or formal tool |
| Expression coverage | Covered by directed branch and expression tests | pytest and downstream RTL coverage |

### 6.2 Functional Coverage
| Coverage Point | Description | Goal |
|----------------|-------------|------|
| L5 dsl contract coverage | Checks that L5 dsl preserves required inputs, outputs, and invariants. | All discovered directed tests pass |

### 6.3 Coverage Closure Criteria
Close L5 dsl when `layer_L5_dsl/specs/05_dsl_test_plan.md` has corresponding PASS evidence in `layer_L5_dsl/specs/05_dsl_test_report.md` and no blocker feedback remains.

---

## 7. Test Case Inventory

### 7.1 Test Case Summary
| TC ID | Name | Type | Priority | Objective | Status |
|-------|------|------|----------|-----------|--------|
| TC-001 | test_instantiation | Directed | P1 | Validate instantiation. | Planned |



Additional discovered test cases:

| TC ID | Name | Type | Priority | Objective | Status |
| --- | --- | --- | --- | --- | --- |
| FFT256-L5_DSL-TC-001 | test_instantiation | Directed | P1 | Validate instantiation. | Planned |
| FFT256-L5_DSL-TC-002 | test_simulator_reset | Directed | P1 | Validate simulator reset. | Planned |
| FFT256-L5_DSL-TC-003 | test_verilog_emit_non_empty | Directed | P1 | Validate verilog emit non empty. | Planned |

### 7.2 Detailed Test Cases

#### TC-001: test_instantiation
| Attribute | Description |
|-----------|-------------|
| Objective | Validate instantiation. |
| Preconditions | Layer model initialized |
| Input stimulus | Run pytest test case |
| Expected result | Test passes with no assertion failures |
| Pass/Fail criteria | Assertion passes |
| Coverage targeted | Functional coverage of the exercised feature |
| Dependencies | None |

---

## 8. Directed Test Cases

| TC ID | Scenario | Input | Expected Output | Priority |
|-------|----------|-------|-----------------|----------|
| D-01 | L5 dsl directed regression | Layer source, generated spec, and adjacent-layer contract artifacts | Layer-local behavior matches the contract and produces PASS evidence | P1 |

---

## 9. Random and Constrained-Random Tests

| Test Name | Constraint Focus | Iterations | Seed Strategy | Regression Count |
|-----------|------------------|------------|---------------|------------------|
| L5 dsl randomized smoke vectors | Future randomized contract perturbations | 0 in current pilot | record seed when enabled | 0 in current pilot |

---

## 10. Corner Cases and Stress Tests

| TC ID | Scenario | Rationale |
|-------|----------|-----------|
| C-01 | Reset, idle, and boundary protocol behavior | These states commonly reveal broken layer refinement. |

---

## 11. Regression Strategy

### 11.1 Regression Environments
| Environment | Tool | Frequency | Scope |
|-------------|------|-----------|-------|
| local-pytest | pytest | per flow run | EarphoneFFT256 L5 dsl |

### 11.2 Regression Pass Criteria
All layer tests pass and strict document feedback has zero blockers.

---

## 12. Defect Management

### 12.1 Severity Definitions
| Severity | Definition | Response Time |
|----------|------------|---------------|
| S0 - Blocker | Blocks layer handoff or invalidates an upstream contract. | Immediate repair before next layer generation |
| S1 - Critical | Breaks required behavior but has a bounded workaround. | Repair before sign-off |
| S2 - Major | Reduces coverage or traceability without breaking execution. | Repair before milestone closure |
| S3 - Minor | Documentation or polish issue without behavioral impact. | Repair during cleanup |

### 12.2 Bug Tracking Process
Issues are emitted into docgen_feedback.json with detected layer and upstream target layer.

---

## 13. Schedule and Milestones

| Milestone | Target Date | Deliverable | Owner |
|-----------|-------------|-------------|-------|
| L5 dsl handoff | 2026-06-18 | layer_L5_dsl/specs/05_dsl_spec.md, layer_L5_dsl/specs/05_dsl_test_plan.md, layer_L5_dsl/specs/05_dsl_test_report.md | RTLCraft Agent |

---

## 14. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Layer contract drift | Downstream code may satisfy stale or incomplete intent | Medium during migration | Strict placeholder checks, layer tests, and upstream feedback blockers |

---

## 15. Sign-Off Criteria

The verification phase is considered complete when:

1. All priority-1 test cases pass: 100%
2. Code coverage goals are met: Line coverage ≥ 80%
3. Functional coverage goals are met: All directed tests pass
4. No open S0/S1 bugs: No open S0/S1 bugs
5. Regression is green for 3 consecutive runs.

---

## 16. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
