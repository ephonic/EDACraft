# EarphoneRV32 — L2 CycleIR Specification

| Document ID | RV32-L2_CYCLE-001 |
|-------------|--------------|
| Layer       | L2 CycleIR |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-14 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Provide a cycle-accurate reference model that tracks pipeline control signals while delegating functional execution to the L1 ISS.

### 1.2 Scope
Single-cycle scalar pipeline with multi-cycle M-extension operations.

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
| DEC-01 | Single-cycle scalar with iterative M-extension | Area/power optimized for earphone-class MCU | DIV/REM take variable cycles |

---

## 5. Detailed Description

### Tests

No dedicated L2 tests yet; cross-layer equivalence covers this layer.

### Model

| Property | Value |
| --- | --- |
| Pipeline | IF → ID → EX → MEM → WB |
| M-extension latency | Multi-cycle (iterative) |
| Branch predictor | Static not-taken |
| Stall/flush support | Yes |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests + cross-layer equivalence checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Instruction decode and execution correctness | Directed ISS tests | All RV32IM instructions exercised |

---

## 7. Constraints and Assumptions

### 7.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | RV32IM ISA compliance | Top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian byte ordering | Matches target bus architecture |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | cycle.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
