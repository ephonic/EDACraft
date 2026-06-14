# EarphoneSIMD16 — L5 dsl Specification

| Document ID | SIMD16-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneSIMD16 |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
16-lane SIMD accelerator.

### 1.2 Scope
RTL-ready DSL description of EarphoneSIMD16.

---

## 2. Inputs from Previous Layer

See previous layer specification for inputs.

---

## 3. Outputs to Next Layer

See next layer specification for outputs.

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneSIMD16 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Dsl Class | EarphoneSIMD16 |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| clk | Input | 1 |
| done | Output | 1 |
| fp_s0_a | Reg | 256 |
| fp_s0_b | Reg | 256 |
| fp_s0_c | Reg | 256 |
| fp_s0_pred | Reg | 16 |
| fp_s0_valid | Reg | 1 |
| fp_s1_a | Reg | 256 |
| fp_s1_b | Reg | 256 |
| fp_s1_c | Reg | 256 |
| fp_s1_pred | Reg | 16 |
| fp_s1_valid | Reg | 1 |
| fp_s2_result | Reg | 256 |
| fp_s2_valid | Reg | 1 |
| int_result | Reg | 256 |
| int_valid | Reg | 1 |
| mode | Input | 1 |
| op | Input | 5 |
| pred | Input | 16 |
| rst_n | Input | 1 |
| start | Input | 1 |
| vdst | Output | 256 |
| vsrc0 | Input | 256 |
| vsrc1 | Input | 256 |
| vsrc2 | Input | 256 |


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
| 0.1 | 2026-06-15 | RTLCraft Agent | Initial draft. |
