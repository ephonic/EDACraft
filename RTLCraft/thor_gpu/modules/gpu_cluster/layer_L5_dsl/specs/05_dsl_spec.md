# ThorCluster — L5 dsl Specification

| Document ID | GPU_CLUSTER-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | ThorCluster |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
RTL-ready 2-SM cluster with round-robin L2 arbiter (cluster top).

### 1.2 Scope
RTL-ready DSL description of ThorCluster.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `GPU_CLUSTER-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`) as input to `GPU_CLUSTER-L5_DSL-001`.

---

## 3. Outputs to Next Layer

Emits `GPU_CLUSTER-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`) as input to `GPU_CLUSTER-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorCluster as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Dsl Class | ThorCluster |
| Ports | clk, rst_n, start, sm{0,1}_imem_wr_*, mem_* -> all_done, sm{0,1}_w0_acc0 |

### Ports

`clk, rst_n, start, sm{0,1}_imem_wr_*, mem_* -> all_done, sm{0,1}_w0_acc0`


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
| C-01 | Module specification compliance | Thor-GPGPU top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Two's-complement integer / IEEE-754 FP semantics | Matches the Thor GPGPU datapath |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | dsl.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
