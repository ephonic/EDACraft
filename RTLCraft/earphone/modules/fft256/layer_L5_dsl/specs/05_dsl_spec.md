# EarphoneFFT256 — L5 dsl Specification

| Document ID | FFT256-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneFFT256 |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
256-point streaming FFT accelerator wrapper.

### 1.2 Scope
RTL-ready DSL description of EarphoneFFT256.

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
| DEC-01 | Implement EarphoneFFT256 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Dsl Class | EarphoneFFT256 |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| clk | Input | 1 |
| di_en | Input | 1 |
| di_im | Input | 16 |
| di_re | Input | 16 |
| do_en | Output | 1 |
| do_im | Output | 16 |
| do_re | Output | 16 |
| rst | Input | 1 |


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
