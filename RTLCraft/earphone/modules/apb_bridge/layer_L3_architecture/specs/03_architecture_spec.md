# EarphoneAPBBridge — L3 architecture Specification

| Document ID | APB_BRIDGE-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | EarphoneAPBBridge |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
APB4 address decoder and response mux for eight peripheral slots.

### 1.2 Scope
Micro-architectural decisions for EarphoneAPBBridge.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `APB_BRIDGE-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `APB_BRIDGE-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `APB_BRIDGE-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `APB_BRIDGE-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `APB_BRIDGE-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `APB_BRIDGE-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `APB_BRIDGE-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneAPBBridge as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Pipeline | single-cycle combinational decode |
| Stages | decode, select_fanout, response_mux |
| Decode Field | m_paddr[29:22] |
| Slot Count | 8 |
| Slave Region Size Bytes | 4194304 |
| Host Protocol | APB4 master ingress to APB4 peripheral fanout |
| Timing | Decode is combinational; the selected slave determines pready and pslverr timing. |
| Invariants | Exactly one slave slot is selected for an in-range address., The selected slave's pready and pslverr status are returned to the master., All request fields are broadcast unchanged into the selected APB slot. |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests + cross-layer equivalence checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional correctness | Directed tests | All operations exercised |

---

## 7. Constraints and Assumptions

### 7.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | Module specification compliance | Top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian byte ordering | Matches target bus architecture |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | arch.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
