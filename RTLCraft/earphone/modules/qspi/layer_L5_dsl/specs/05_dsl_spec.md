# EarphoneQSPI — L5 dsl Specification

| Document ID | QSPI-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneQSPI |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Simplified QSPI XIP read controller.

### 1.2 Scope
RTL-ready DSL description of EarphoneQSPI.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `QSPI-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), plus verification intent `QSPI-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`) and latest evidence `QSPI-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `QSPI-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`), `QSPI-L5_DSL-TP-001` (`layer_L5_dsl/specs/05_dsl_test_plan.md`), and `QSPI-L5_DSL-TR-001` (`layer_L5_dsl/specs/05_dsl_test_report.md`) as inputs to `QSPI-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneQSPI as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Dsl Class | EarphoneQSPI |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| addr | Input | 32 |
| addr_reg | Reg | 32 |
| clk | Input | 1 |
| counter | Reg | 4 |
| qspi_cs_n | Output | 1 |
| qspi_io_i | Input | 4 |
| qspi_io_o | Output | 4 |
| qspi_io_oe | Output | 4 |
| qspi_sck | Output | 1 |
| rdata | Output | 32 |
| ready | Output | 1 |
| req | Input | 1 |
| rst_n | Input | 1 |
| shift | Reg | 32 |
| state | Reg | 3 |


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
