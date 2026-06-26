# EarphoneRV32 — Module Design Specification

| Document ID | RV32-MOD-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Module ID   | RV32 |
| Status      | Draft |

---

## 1. Overview

### 1.1 Purpose
RV32IM 3-stage in-order RISC-V core with single-cycle MUL and iterative DIV/REM.

### 1.2 Features
| ID | Feature | Description |
|----|---------|-------------|
| F-01 | RV32IM ISA coverage | Implements RV32I base integer operations plus RV32M multiply/divide/remainder instructions. |
| F-02 | Low-power in-order microarchitecture | Uses a simple scalar pipeline, operand isolation, and iterative divide to reduce area and switching. |

### 1.3 Use Cases
Runs control firmware for the Smart Earphone SoC and services accelerator/peripheral orchestration.

### 1.4 Block Diagram

PC/fetch drives decode/execute, register-file read, ALU/branch/load-store logic, and an iterative M-extension unit before writeback and retire tracing.

```text
+-----------------------------------------------------------+
|                     EarphoneRV32                        |
|  +----------------+        +---------------------------+  |
|  | Fetch + Decode |------->| Execute + Writeback            |  |
|  +----------------+        +---------------------------+  |
+-----------------------------------------------------------+
```

---

## 2. References

| Document ID | Title | Version | Description |
|-------------|-------|---------|-------------|
| EARPHONE-SOC-SPEC | Smart Earphone SoC Design Specification | 0.1 | Top-level requirements, architecture, PPA targets, and roadmap. |

---

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| IR | Intermediate representation used for staged Spec2RTL lowering. |

---

## 4. Interface Definition

### 4.1 Port List

#### Clock and Reset
| Port Name | Width | Direction | Description |
|-----------|-------|-----------|-------------|
| clk | 1 | Input | System clock for fetch, execute, register file, and memory interface state. |
| rst_n | 1 | Input | Active-low reset; reset PC is 0x00001000. |

#### Functional Ports
| Port Name | Width | Direction | Protocol / Encoding | Description |
|-----------|-------|-----------|---------------------|-------------|
| imem_*, dmem_*, irq, retire_* | 1-32 | Input/Output | Harvard memory buses + retire trace | Instruction fetch, data memory request/response, local interrupt input, and verification retire outputs. |

### 4.2 Interface Timing

Instruction fetch requests are issued from the current PC. Data memory handshakes use request/grant/valid. M-extension divide/remainder operations stall the core until the iterative unit completes.

### 4.3 Protocol Compliance
| Protocol | Version | Compliance Level | Notes |
|----------|---------|------------------|-------|
| RV32IM + simple memory bus | RV32I/RV32M unprivileged subset | Project subset | No MMU/FPU; physical addressing only. FP16 work is delegated to SIMD16. |

---

## 5. Parameters and Configuration

| Parameter Name | Type | Default | Range | Description |
|----------------|------|---------|-------|-------------|
| XLEN / RESET_PC / DIV_ITERATIONS | integer constants | 32 / 0x1000 / 32 | fixed in v0.1 | Core width, reset entry point, and iterative divider latency. |

---

## 6. Functional Description

### 6.1 Theory of Operation
The core fetches 32-bit instructions, decodes operands and immediates, executes ALU/branch/load/store/M-extension operations, writes architectural results back to x1-x31, and keeps x0 hardwired to zero.

### 6.2 State Machine(s)

| State | Encoding | Description | Exit Conditions |
|-------|----------|-------------|-----------------|
| RESET / RUN / MULDIV_WAIT | implicit control state | Reset initializes PC/register state; RUN retires ordinary instructions; MULDIV_WAIT holds the pipeline for divide/remainder. | Reset release, instruction completion, or M-extension done. |

### 6.3 Data Path
PC -> instruction memory -> decode/register file -> ALU/LSU/muldiv -> writeback -> retire trace.

### 6.4 Error Handling
| Error Condition | Detection | Response | Reporting |
|-----------------|-----------|----------|-----------|
| Unsupported or unimplemented instruction encoding | Decode opcode/funct mismatch | Treat as safe no-op or halt for EBREAK depending on decoded instruction | Retire trace and L1/L5 tests. |

---

## 7. Microarchitecture

### 7.1 Major Sub-blocks
| Sub-block | Description | Interface |
|-----------|-------------|-----------|
| pc_unit, regfile, decoder, alu, muldiv_unit, load_store_unit | Major internal blocks declared in L4 StructuralIR. | PC, register operands, ALU controls, memory request/response, muldiv start/done/result. |

### 7.2 Pipeline Stages
| Stage | Latency | Description |
|-------|---------|-------------|
| IF / ID-EX / WB plus MULDIV_WAIT | 1 cycle for scalar ALU/MUL, 32 cycles for DIV/REM | Three-stage in-order control with multi-cycle hold during divide/remainder. |

### 7.3 Critical Path Considerations
ALU compare/add path and decode-to-writeback muxing; divider is iterative to avoid a long combinational path.

---

## 8. Timing

### 8.1 Clocking
| Clock Name | Frequency | Source | Notes |
|------------|-----------|--------|-------|
| clk | 48-160 MHz target | clk_sys | Earphone-class low-power system clock domain. |

### 8.2 Reset
| Reset Name | Type | Active Level | Description |
|------------|------|--------------|-------------|
| rst_n | asynchronous assert, synchronous release | active low | Resets architectural and control state to layer-specified defaults. |

### 8.3 Timing Diagrams

See L2 CycleIR test plan and cross-layer traces.

---

## 9. Registers

### 9.1 Register Summary
| Address Offset | Register Name | Width | Access | Reset Value | Description |
|----------------|---------------|-------|--------|-------------|-------------|
| N/A | pc, regs[32], pipeline control, muldiv state | 32-bit architectural state plus control bits | internal | pc=0x1000, x0-x31=0, control idle | Architectural register file, program counter, and M-extension state. |

### 9.2 Register Detail

#### pc, regs[32], pipeline control, muldiv state
| Bit | Field | Access | Reset | Description |
|-----|-------|--------|-------|-------------|
| N/A | N/A | N/A | N/A | No externally visible register field described at this level. |

---

## 10. Power Management

### 10.1 Power Domain
clk_sys CPU domain with stall-based clock-enable gating.

### 10.2 Clock Gating
| Clock Enable Signal | Controlled Logic | Idle Behavior |
|---------------------|------------------|---------------|
| core_clk_en | pipeline registers, writeback state, and operand isolation controls | held low during memory stalls and multi-cycle divide/remainder. |

### 10.3 Low-Power Modes
| Mode | Entry | Exit | Impact |
|------|-------|------|--------|
| idle | no active request or divide stall | new fetch, interrupt, or multicycle completion | reduced dynamic switching |

---

## 11. Verification Considerations

### 11.1 Verification Strategy
L1 behavior tests → L2 cycle tests → L3 DSL tests → L6 Verilog tests.

### 11.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional equivalence across layers | Cross-layer verification via LayerVerifier | 100% of ISA/protocol operations |

### 11.3 Assertions
| ID | Assertion | Severity | Description |
|----|-----------|----------|-------------|
| A-01 | x0 remains zero and DIV/REM by zero follows RV32M rules | error | Intent-driven tests and generated UVM/SVA artifacts cover RV32M divide-by-zero behavior. |

---

## 12. Design Constraints and Assumptions

### 12.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | RV32M divide-by-zero result and CPU active-power intent | EARP-RV32 constraints propagated through DesignScaffold |

### 12.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian data representation unless specified otherwise | Matches RV32/APB memory semantics in the Earphone SoC. |

---

## 13. Synthesis and Implementation Notes

### 13.1 Synthesis Target
| Item | Target |
|------|--------|
| Technology | 22nm / 28nm low-power CMOS target |
| Frequency | 48-160 MHz |
| Area Goal | <30k NAND2 equivalent for CPU core target |

### 13.2 Tool Settings
rtlgen VerilogEmitter, VerilogLinter, and optional downstream synthesis feedback.

---

## 14. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | behavior.py, cycle.py, arch.py, structure.py, dsl.py, emitter.py, tests, specs, earphone_rv32.v | Markdown, JSON, Python, Verilog | RTLCraft Agent |

---

## 15. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
