# EarphoneAPBBridge — L5 dsl Specification

| Document ID | APB_BRIDGE-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | EarphoneAPBBridge |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Simple APB4 address decoder for 8 slave slots.

### 1.2 Scope
RTL-ready DSL description of EarphoneAPBBridge.

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
| DEC-01 | Implement EarphoneAPBBridge as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Dsl Class | EarphoneAPBBridge |

### Ports Table

| Port | Type | Width |
| --- | --- | --- |
| clk | Input | 1 |
| m_paddr | Input | 32 |
| m_penable | Input | 1 |
| m_prdata | Output | 32 |
| m_pready | Output | 1 |
| m_psel | Input | 1 |
| m_pslverr | Output | 1 |
| m_pstrb | Input | 4 |
| m_pwdata | Input | 32 |
| m_pwrite | Input | 1 |
| rst_n | Input | 1 |
| s_paddr | Output | 32 |
| s_penable | Output | 1 |
| s_prdata | Input | 32 |
| s_pready | Input | 8 |
| s_psel | Output | 8 |
| s_pslverr | Input | 8 |
| s_pstrb | Output | 4 |
| s_pwdata | Output | 32 |
| s_pwrite | Output | 1 |


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
