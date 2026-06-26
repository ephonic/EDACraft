# EarphoneSRAM256K — L5 dsl Specification

| Document ID | SRAM256K-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneSRAM256K |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
256 KB on-chip SRAM, APB4 slave, byte write enable.

### 1.2 Scope
RTL-ready DSL description of EarphoneSRAM256K.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `SRAM256K-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), plus verification intent `SRAM256K-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`) and latest evidence `SRAM256K-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `SRAM256K-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`), `SRAM256K-L5_DSL-TP-001` (`layer_L5_dsl/specs/05_dsl_test_plan.md`), and `SRAM256K-L5_DSL-TR-001` (`layer_L5_dsl/specs/05_dsl_test_report.md`) as inputs to `SRAM256K-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

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
| Dsl Class | EarphoneSRAM256K |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| clk | Input | 1 |
| paddr | Input | 32 |
| penable | Input | 1 |
| prdata | Output | 32 |
| pready | Output | 1 |
| psel | Input | 1 |
| pslverr | Output | 1 |
| pstrb | Input | 4 |
| pwdata | Input | 32 |
| pwrite | Input | 1 |
| rdata_reg | Reg | 32 |
| rst_n | Input | 1 |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
DSL simulation and cross-layer equivalence with L1/L2.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | DSL implementation matches reference model | rtlgen Simulator + LayerVerifier | All functional paths covered |

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
| D-01 | dsl.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
