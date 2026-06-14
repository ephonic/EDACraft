# EarphoneRV32 — L3 architecture Test Report — Verification Test Report

| Document ID | RV32-L3_ARCHITECTURE-TR-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-14 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Test Plan Reference | RV32-L3_ARCHITECTURE-TP-001 |
| Status      | Draft |

---

## 1. Executive Summary

### 1.1 Overall Result
NO TESTS

### 1.2 Key Metrics
| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Total Test Cases | 0 | 0 | OK |
| Passed | 0 | 0 | OK |
| Failed | 0 | 0 | OK |
| Blocked / Skipped | 0 | 0 | OK |
| Line Coverage | {{ target_line_cov }} | {{ achieved_line_cov }} | {{ status_line_cov }} |
| Functional Coverage | {{ target_func_cov }} | {{ achieved_func_cov }} | {{ status_func_cov }} |

### 1.3 Sign-Off Recommendation
Investigate failures before sign-off

---

## 2. Test Scope

### 2.1 DUT Information
| Attribute | Value |
|-----------|-------|
| DUT Name | EarphoneRV32 |
| DUT Version | {{ dut_version }} |
| RTL Commit | {{ rtl_commit }} |
| Testbench Commit | {{ tb_commit }} |

### 2.2 Scope Summary
{{ scope_summary }}

---

## 3. Test Environment

### 3.1 Hardware
| Item | Configuration |
|------|---------------|
| Host | {{ host }} |
| CPU | {{ cpu }} |
| Memory | {{ memory }} |

### 3.2 Software
| Item | Version |
|------|---------|
| Simulator | {{ simulator }} |
| Synthesis Tool | {{ synth_tool }} |
| Lint Tool | {{ lint_tool }} |
| Coverage Tool | {{ coverage_tool }} |
| OS | {{ os }} |

### 3.3 Testbench Configuration
{{ tb_config }}

---

## 4. Test Results Summary

### 4.1 Results by Test Suite
| Suite | Total | Passed | Failed | Skipped | Coverage |
|-------|-------|--------|--------|---------|----------|
| L3 architecture | 0 | 0 | 0 | 0 | N/A |

### 4.2 Results by Priority
| Priority | Total | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| P0 | 0 | 0 | 0 | 0 |
| P1 | {{ p1_total }} | {{ p1_pass }} | {{ p1_fail }} | {{ p1_skip }} |
| P2 | {{ p2_total }} | {{ p2_pass }} | {{ p2_fail }} | {{ p2_skip }} |

### 4.3 Results by Verification Level
| Level | Total | Passed | Failed | Skipped |
|-------|-------|--------|--------|---------|
| Unit | 0 | 0 | 0 | 0 |
| Integration | {{ int_total }} | {{ int_pass }} | {{ int_fail }} | {{ int_skip }} |
| System | {{ sys_total }} | {{ sys_pass }} | {{ sys_fail }} | {{ sys_skip }} |

---

## 5. Detailed Test Results

### 5.1 Passing Test Cases
| TC ID | Name | Duration | Notes |
|-------|------|----------|-------|
| {{ pass_tc_id }} | {{ pass_tc_name }} | {{ pass_tc_dur }} | {{ pass_tc_notes }} |

### 5.2 Failing Test Cases
| TC ID | Name | Severity | Root Cause | Owner | Status |
|-------|------|----------|------------|-------|--------|
| {{ fail_tc_id }} | {{ fail_tc_name }} | {{ fail_tc_sev }} | {{ fail_tc_root }} | {{ fail_tc_owner }} | {{ fail_tc_status }} |

### 5.3 Skipped / Blocked Test Cases
| TC ID | Name | Reason | Plan to Run |
|-------|------|--------|-------------|
| {{ skip_tc_id }} | {{ skip_tc_name }} | {{ skip_tc_reason }} | {{ skip_tc_plan }} |

---

## 6. Coverage Results

### 6.1 Code Coverage
| Type | Target | Achieved | Gap | Status |
|------|--------|----------|-----|--------|
| Line | {{ line_target }} | {{ line_achieved }} | {{ line_gap }} | {{ line_status }} |
| Branch | {{ branch_target }} | {{ branch_achieved }} | {{ branch_gap }} | {{ branch_status }} |
| FSM | {{ fsm_target }} | {{ fsm_achieved }} | {{ fsm_gap }} | {{ fsm_status }} |
| Toggle | {{ toggle_target }} | {{ toggle_achieved }} | {{ toggle_gap }} | {{ toggle_status }} |
| Expression | {{ expr_target }} | {{ expr_achieved }} | {{ expr_gap }} | {{ expr_status }} |

### 6.2 Functional Coverage
| Covergroup / Point | Target | Achieved | Gap | Status |
|--------------------|--------|----------|-----|--------|
| {{ fc_name }} | {{ fc_target }} | {{ fc_achieved }} | {{ fc_gap }} | {{ fc_status }} |

### 6.3 Coverage Exclusions
| Exclusion | Reason | Approved By |
|-----------|--------|-------------|
| {{ exclusion }} | {{ exclusion_reason }} | {{ exclusion_approver }} |

---

## 7. Issues and Bugs

### 7.1 Open Issues
| ID | Severity | Summary | Owner | ETA |
|----|----------|---------|-------|-----|
| {{ open_issue_id }} | {{ open_issue_sev }} | {{ open_issue_summary }} | {{ open_issue_owner }} | {{ open_issue_eta }} |

### 7.2 Closed Issues
| ID | Severity | Summary | Resolution |
|----|----------|---------|------------|
| {{ closed_issue_id }} | {{ closed_issue_sev }} | {{ closed_issue_summary }} | {{ closed_issue_resolution }} |

---

## 8. Waivers and Deviations

| ID | Description | Justification | Approved By |
|----|-------------|---------------|-------------|
| {{ waiver_id }} | {{ waiver_desc }} | {{ waiver_just }} | {{ waiver_approver }} |

---

## 9. Regression History

| Run ID | Date | Total | Pass | Fail | Skip | Duration | Result |
|--------|------|-------|------|------|------|----------|--------|
| {{ run_id }} | {{ run_date }} | {{ run_total }} | {{ run_pass }} | {{ run_fail }} | {{ run_skip }} | {{ run_dur }} | {{ run_result }} |

---

## 10. Conclusion

Layer L3 architecture tests completed: 0/0 passed in 0.16s.

---

## 11. Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Verification Lead | {{ verif_lead }} | {{ verif_lead_sig }} | {{ verif_lead_date }} |
| Design Lead | {{ design_lead }} | {{ design_lead_sig }} | {{ design_lead_date }} |
| System Architect | {{ sys_arch }} | {{ sys_arch_sig }} | {{ sys_arch_date }} |
| Project Manager | {{ pm }} | {{ pm_sig }} | {{ pm_date }} |

---

## 12. Appendices

### Appendix A: Test Logs
{{ test_logs }}

### Appendix B: Tool Command History
{{ tool_history }}

### Appendix C: Raw Coverage Reports
{{ raw_coverage }}

---

## 13. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial report. |
