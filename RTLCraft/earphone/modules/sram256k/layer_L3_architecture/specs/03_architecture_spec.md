# EarphoneSRAM256K — L3 architecture Specification

| Document ID | SRAM256K-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | EarphoneSRAM256K |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Single-port 256 KB APB SRAM with byte write strobes.

### 1.2 Scope
Micro-architectural decisions for EarphoneSRAM256K.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `SRAM256K-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `SRAM256K-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `SRAM256K-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `SRAM256K-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `SRAM256K-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `SRAM256K-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `SRAM256K-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneSRAM256K as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Pipeline | single-cycle APB transfer with registered readback |
| Stages | apb_request, memory_access, readback |
| Depth Words | 65536 |
| Data Width | 32 |
| Byte Lanes | 4 |
| Read Latency Cycles | 1 |
| Write Latency Cycles | 1 |
| Invariants | Read data is returned through a registered prdata path., Write strobes merge new byte lanes with the existing memory word., The SRAM datapath only updates while an APB transfer is selected and enabled. |


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
