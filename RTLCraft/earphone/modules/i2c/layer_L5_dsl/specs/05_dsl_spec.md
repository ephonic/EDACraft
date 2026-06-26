# EarphoneI2C — L5 dsl Specification

| Document ID | I2C-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneI2C |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Simplified APB I2C master controller.

### 1.2 Scope
RTL-ready DSL description of EarphoneI2C.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `I2C-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), plus verification intent `I2C-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`) and latest evidence `I2C-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `I2C-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`), `I2C-L5_DSL-TP-001` (`layer_L5_dsl/specs/05_dsl_test_plan.md`), and `I2C-L5_DSL-TR-001` (`layer_L5_dsl/specs/05_dsl_test_report.md`) as inputs to `I2C-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneI2C as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Dsl Class | EarphoneI2C |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| bit_cnt | Reg | 4 |
| clk | Input | 1 |
| ctrl | Reg | 32 |
| data | Reg | 32 |
| paddr | Input | 12 |
| penable | Input | 1 |
| prdata | Output | 32 |
| pready | Output | 1 |
| psel | Input | 1 |
| pwdata | Input | 32 |
| pwrite | Input | 1 |
| rst_n | Input | 1 |
| scl_i | Input | 1 |
| scl_o | Output | 1 |
| scl_oe | Output | 1 |
| scl_reg | Reg | 1 |
| sda_i | Input | 1 |
| sda_o | Output | 1 |
| sda_oe | Output | 1 |
| sda_reg | Reg | 1 |
| sent_data | Reg | 1 |
| shift | Reg | 9 |
| state | Reg | 4 |
| status | Reg | 32 |


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
