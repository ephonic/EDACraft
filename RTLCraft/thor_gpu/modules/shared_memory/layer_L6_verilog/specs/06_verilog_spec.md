# ThorSharedMemory — L6 verilog Specification

| Document ID | SHARED_MEMORY-L6_VERILOG-001 |
|-------------|--------------|
| Layer       | L6 verilog |
| Module      | ThorSharedMemory |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Verilog emission wrapper for the Thor shared memory DSL contract.

### 1.2 Scope
Generated Verilog RTL and reports for ThorSharedMemory.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `SHARED_MEMORY-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`) as input to `SHARED_MEMORY-L6_VERILOG-001`.

---

## 3. Outputs to Next Layer

Emits the final RTL-generation contract `SHARED_MEMORY-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`) for module-level sign-off.

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorSharedMemory as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| File Name | thor_shared_memory.v |
| Dsl Class | ThorSharedMemory |
| Key Ports | addr, wdata, rdata, we, re |

---

## 6. Verification Considerations

### 6.1 Verification Strategy
Verilog generation and lint.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Generated RTL matches DSL semantics | VerilogEmitter + VerilogLinter | Module-level RTL coverage |

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
| D-01 | emitter.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
