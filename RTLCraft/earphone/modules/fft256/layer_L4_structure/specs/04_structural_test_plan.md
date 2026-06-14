# EarphoneFFT256 — L4 structure — Verification Test Plan

| Document ID | FFT256-L4_STRUCTURE-TP-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-14 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Verification test plan for the L4 structure of EarphoneFFT256.

### 1.2 Scope
<!-- Define the DUT(s), features, and verification levels covered. -->
Covers directed and cross-layer tests executed at L4 structure.

### 1.3 Out of Scope
Full SoC integration tests; see integration/ specs.

---

## 2. References

| Document ID | Title | Version |
|-------------|-------|---------|
| {{ ref_id }} | {{ ref_title }} | {{ ref_version }} |

---

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| {{ term }} | {{ definition }} |

---

## 4. Device Under Test (DUT)

| Attribute | Value |
|-----------|-------|
| DUT Name | EarphoneFFT256 |
| DUT Version | 0.1 |
| Hierarchy Path | {{ dut_hier }} |
| Specification Reference | {{ spec_ref }} |

---

## 5. Verification Strategy

### 5.1 Verification Approach
Run the layer-specific pytest suite under earphone/modules/fft256/L4_structure/tests and verify functional equivalence with adjacent layers where applicable.

### 5.2 Verification Levels
| Level | Objective | Method | Responsibility |
|-------|-----------|--------|----------------|
| Unit | Validate layer-local functional correctness | Python pytest + model simulation | RTLCraft Agent |
| Integration | Validate interaction with adjacent layers | Cross-layer equivalence checks | RTLCraft Agent |
| System | Validate SoC-level behavior | Full flow regression | System Architect |

### 5.3 Testbench Architecture
```text
+----------------+      +----------------+      +----------------+
|   {{ tb_agent_a }}    |<---->|      DUT       |<---->|   {{ tb_agent_b }}    |
+----------------+      +----------------+      +----------------+
         ^                       ^
         |                       |
         v                       v
+-----------------------------------------------------------+
|                    {{ tb_scoreboard }}                     |
+-----------------------------------------------------------+
```

### 5.4 Verification Methodology
| Method | Usage | Tools |
|--------|-------|-------|
| Constrained-random simulation | N/A | N/A |
| Directed tests | Core directed tests from test_*.py | pytest |
| Formal verification | SVA assertions generated from constraints | Verilog formal tools (future) |
| Emulation / FPGA prototyping | {{ emu_usage }} | {{ emu_tools }} |

---

## 6. Coverage Strategy

### 6.1 Code Coverage
| Coverage Type | Goal | Tool |
|---------------|------|------|
| Line coverage | 80% | pytest-cov |
| Branch coverage | 70% | pytest-cov |
| FSM coverage | {{ fsm_cov_goal }} | {{ fsm_cov_tool }} |
| Toggle coverage | {{ toggle_cov_goal }} | {{ toggle_cov_tool }} |
| Expression coverage | {{ expr_cov_goal }} | {{ expr_cov_tool }} |

### 6.2 Functional Coverage
| Coverage Point | Description | Goal |
|----------------|-------------|------|
| {{ fc_point }} | {{ fc_desc }} | {{ fc_goal }} |

### 6.3 Coverage Closure Criteria
{{ coverage_closure }}

---

## 7. Test Case Inventory

### 7.1 Test Case Summary
| TC ID | Name | Type | Priority | Objective | Status |
|-------|------|------|----------|-----------|--------|
| TC-001 | {{ tc_name_01 }} | {{ tc_type_01 }} | {{ tc_prio_01 }} | {{ tc_obj_01 }} | {{ tc_status_01 }} |

### 7.2 Detailed Test Cases

#### TC-001: {{ tc_name_01 }}
| Attribute | Description |
|-----------|-------------|
| Objective | {{ tc_obj_01 }} |
| Preconditions | {{ tc_pre_01 }} |
| Input stimulus | {{ tc_stim_01 }} |
| Expected result | {{ tc_exp_01 }} |
| Pass/Fail criteria | {{ tc_pass_01 }} |
| Coverage targeted | {{ tc_cov_01 }} |
| Dependencies | {{ tc_dep_01 }} |

---

## 8. Directed Test Cases

| TC ID | Scenario | Input | Expected Output | Priority |
|-------|----------|-------|-----------------|----------|
| D-01 | {{ dir_scenario_01 }} | {{ dir_input_01 }} | {{ dir_exp_01 }} | {{ dir_prio_01 }} |

---

## 9. Random and Constrained-Random Tests

| Test Name | Constraint Focus | Iterations | Seed Strategy | Regression Count |
|-----------|------------------|------------|---------------|------------------|
| {{ rand_test }} | {{ rand_focus }} | {{ rand_iter }} | {{ rand_seed }} | {{ rand_regress }} |

---

## 10. Corner Cases and Stress Tests

| TC ID | Scenario | Rationale |
|-------|----------|-----------|
| C-01 | {{ corner_scenario_01 }} | {{ corner_rationale_01 }} |

---

## 11. Regression Strategy

### 11.1 Regression Environments
| Environment | Tool | Frequency | Scope |
|-------------|------|-----------|-------|
| {{ regress_env }} | {{ regress_tool }} | {{ regress_freq }} | {{ regress_scope }} |

### 11.2 Regression Pass Criteria
{{ regress_pass_criteria }}

---

## 12. Defect Management

### 12.1 Severity Definitions
| Severity | Definition | Response Time |
|----------|------------|---------------|
| S0 - Blocker | {{ s0_def }} | {{ s0_time }} |
| S1 - Critical | {{ s1_def }} | {{ s1_time }} |
| S2 - Major | {{ s2_def }} | {{ s2_time }} |
| S3 - Minor | {{ s3_def }} | {{ s3_time }} |

### 12.2 Bug Tracking Process
{{ bug_tracking }}

---

## 13. Schedule and Milestones

| Milestone | Target Date | Deliverable | Owner |
|-----------|-------------|-------------|-------|
| {{ milestone }} | {{ milestone_date }} | {{ milestone_deliverable }} | {{ milestone_owner }} |

---

## 14. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| {{ risk }} | {{ risk_impact }} | {{ risk_likelihood }} | {{ risk_mitigation }} |

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
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
