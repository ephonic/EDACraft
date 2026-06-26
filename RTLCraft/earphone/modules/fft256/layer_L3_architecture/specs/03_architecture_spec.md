# EarphoneFFT256 — L3 architecture Specification

| Document ID | FFT256-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | EarphoneFFT256 |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Streaming 256-point FFT wrapper around the reusable FFT256Core datapath.

### 1.2 Scope
Micro-architectural decisions for EarphoneFFT256.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `FFT256-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `FFT256-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `FFT256-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `FFT256-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `FFT256-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `FFT256-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `FFT256-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

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
| Pipeline | streaming shell around a reusable FFT pipeline |
| Stages | input_stream, fft_core, output_stream |
| Points | 256 |
| Sample Width | 16 |
| Numeric Format | Q1.15 complex samples |
| Throughput | 1 complex sample per cycle after pipeline fill |
| Invariants | Transforms 256 complex input samples into 256 complex output samples., The wrapper preserves the streaming valid handshake on input and output., The reusable FFT256Core instance owns the butterfly pipeline state. |


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
