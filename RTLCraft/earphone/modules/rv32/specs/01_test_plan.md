# EarphoneRV32 — Verification Test Plan

| Document ID | TP-EARPHONE-RV32-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-14 |
| Author      | RTLCraft Agent |
| Owner       | Earphone SoC Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Verify the EarphoneRV32 RV32IM core against its L1 ISS golden model, L3 DSL implementation, and generated Verilog.

### 1.2 Scope
<!-- Define the DUT(s), features, and verification levels covered. -->
{{ scope }}

### 1.3 Out of Scope
{{ out_of_scope }}

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
| DUT Name | EarphoneRV32 |
| DUT Version | 0.1 |
| Hierarchy Path | earphone.modules.rv32.src.dsl.EarphoneRV32 |
| Specification Reference | earphone/modules/rv32/specs/00_module_spec.md |

---

## 5. Verification Strategy

### 5.1 Verification Approach
{{ verification_approach }}

### 5.2 Verification Levels
| Level | Objective | Method | Responsibility |
|-------|-----------|--------|----------------|
| Unit | {{ unit_objective }} | {{ unit_method }} | {{ unit_owner }} |
| Integration | {{ int_objective }} | {{ int_method }} | {{ int_owner }} |
| System | {{ sys_objective }} | {{ sys_method }} | {{ sys_owner }} |

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
| Constrained-random simulation | {{ cr_usage }} | {{ cr_tools }} |
| Directed tests | {{ dir_usage }} | {{ dir_tools }} |
| Formal verification | {{ formal_usage }} | {{ formal_tools }} |
| Emulation / FPGA prototyping | {{ emu_usage }} | {{ emu_tools }} |

---

## 6. Coverage Strategy

### 6.1 Code Coverage
| Coverage Type | Goal | Tool |
|---------------|------|------|
| Line coverage | {{ line_cov_goal }} | {{ line_cov_tool }} |
| Branch coverage | {{ branch_cov_goal }} | {{ branch_cov_tool }} |
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
| TC-001 | RV32IM behavior parity | Directed | P0 | L1 ISS produces same architectural result as reference RISC-V execution for add/sub/load/store/branch/M-ext programs. | {{ tc_status_01 }} |

### 7.2 Detailed Test Cases

#### TC-001: RV32IM behavior parity
| Attribute | Description |
|-----------|-------------|
| Objective | L1 ISS produces same architectural result as reference RISC-V execution for add/sub/load/store/branch/M-ext programs. |
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

1. All priority-1 test cases pass: {{ p1_pass_criteria }}
2. Code coverage goals are met: {{ code_cov_criteria }}
3. Functional coverage goals are met: {{ func_cov_criteria }}
4. No open S0/S1 bugs: {{ bug_criteria }}
5. Regression is green for {{ regress_green_count }} consecutive runs.

---

## 16. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
