# Thor-Class GPGPU Compute Cluster — Top-Level Design Specification

| Document ID | THOR-SOC-001 |
|-------------|--------------|
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Specify the top-level requirements, architecture, and verification strategy for a
Thor-class GPGPU **streaming-multiprocessor (SM) compute cluster** designed with RTLCraft's
document-driven 6-layer Spec2RTL flow.

### 1.2 Scope
**In scope**: SM compute fabric — warp scheduling, SIMT execution, vector ALU/FPU/tensor
core, load/store, shared memory, single SM, and a 2-SM cluster with a round-robin L2
arbiter. Each block is fully modeled across all 6 IR layers (L1 BehaviorIR … L6 Verilog).

**Out of scope** (v0.1): Grace host CPU, HBM3 memory controller, NVLink, multiple GPCs,
power domains/retention, and full RISC-V-vector ISA compatibility.

### 1.3 Intended Audience
- GPU architects and micro-architects
- RTL designers
- Verification engineers
- Project management

---

## 2. References

### 2.1 Internal References
| Document ID | Title | Description |
|-------------|-------|-------------|
| THOR-MOD-* | Per-module specs | `modules/<M>/specs/00_module_spec.md` for each block |
| RTLCRAFT-README | RTLCraft README | Spec2RTL methodology and framework |

---

## 3. Definitions and Abbreviations

| Term | Definition |
|------|------------|
| SM | Streaming Multiprocessor |
| Warp | Group of threads executed in lock-step (here: 8 lanes) |
| SIMT | Single-Instruction, Multiple-Threads |
| VRF | Vector Register File |
| MMA | Matrix-Multiply-Accumulate |
| IR | Intermediate representation (Spec2RTL layer) |
| GPC | Graphics Processing Cluster |

---

## 4. System Overview

### 4.1 High-Level Architecture
2 SMs sharing one global memory port through a round-robin L2 arbiter. Each SM contains a
sticky round-robin warp scheduler (4 warps), a SIMT core (fetch/decode/SIMT-stack), vector
ALU + FPU + tensor core datapaths, a vector LSU, per-SM shared memory, a VRF (8 regs ×
4 warps), and an IMEM (32 entries).

### 4.2 Key Features
| ID | Feature | Priority | Notes |
|----|---------|----------|-------|
| F-01 | Multi-SM cluster (2 SM) | Must | round-robin L2 arbiter |
| F-02 | 8-lane INT32 vector ALU | Must | predicated per-lane |
| F-03 | 8-lane FP32 vector FPU | Should | IEEE-754 single |
| F-04 | INT8 8×8×8 tensor core | Should | → INT32 accumulator |
| F-05 | Sticky-RR warp scheduler | Must | 4 warps/SM |
| F-06 | SIMT divergence stack | Should | push/pop reconvergence |
| F-07 | Warp barrier sync | Must | all-at-barrier release |

### 4.3 Target Application
Dense SIMT compute kernels, GEMM, INT8 inference, reductions.

---

## 5. Functional Description

### 5.1 Operating Modes
| Mode | Description | Entry | Exit |
|------|-------------|-------|------|
| Reset | All state cleared; warps IDLE | rst_n=0 | rst_n=1, start |
| Run | Scheduler dispatches warps; execution proceeds | start | all_done |
| Done | All SMs report sm_done/all_done | all warps DONE | reset |

### 5.2 Data Flow
`IMEM → decode → operands(VRF) → {vALU|vFPU|TC} → writeback → VRF`; loads/stores via LSU
and shared memory; global memory via the L2 arbiter.

### 5.3 Control Flow
Host loads each SM's IMEM before `start`. On `start`, warps leave IDLE and the scheduler
drives fetch→decode→exec/mem/barrier until each warp hits DONE.

---

## 6. Interface Definition

### 6.1 External Interfaces (cluster top)
| Interface | Protocol | Width | Direction | Description |
|-----------|----------|-------|-----------|-------------|
| clk | clock | 1 | in | core clock |
| rst_n | reset | 1 | in | active-low async reset |
| start | control | 1 | in | begin execution |
| sm_i_imem_wr_* | memory-wr | — | in | per-SM IMEM write port (en/addr/data) |
| mem_req/wen | mem | 1 | out | global memory request/write-enable |
| mem_addr | mem | 32 | out | global memory address |
| mem_wdata | mem | 256 | out | global memory write data |
| mem_valid | mem | 1 | in | global memory response valid |
| mem_rdata | mem | 256 | in | global memory read data |
| mem_ready | mem | 1 | in | global memory ready |
| all_done | status | 1 | out | all SMs done |

### 6.2 Internal Interfaces
| Source | Destination | Protocol | Description |
|--------|-------------|----------|-------------|
| WarpScheduler | SIMT Core | control | warp_sel, warp_pc |
| SIMT Core | vALU/vFPU/TC | datapath | operands + opcode |
| LSU | Global/L2 arbiter | req/resp | vector load/store |

---

## 7. Memory Map

| Base | End | Region | Description | Access |
|------|-----|--------|-------------|--------|
| 0x0000_0000 | 0x0000_FFFF | Global DRAM | host-visible backing store | RW |
| per-SM | — | SharedMemory | banked SRAM, SM-local | RW |

---

## 8. Clock, Reset, and Power

### 8.1 Clock Domains
| Clock | Frequency | Source | Description |
|-------|-----------|--------|-------------|
| clk | GPU core clock | external | single domain in v0.1 |

### 8.2 Reset Strategy
| Reset | Type | Active | Scope |
|-------|------|--------|-------|
| rst_n | async assert, sync release | low | whole cluster |

### 8.3 Power Domains
Single domain in v0.1. Idle-gating (clock enables) modeled on datapaths; power-gating deferred.

---

## 9. Performance Requirements

| ID | Requirement | Target | Unit | Method |
|----|-------------|--------|------|--------|
| P-01 | INT32 SIMD throughput | 16 | lanes/cycle | ALU/cluster tests |
| P-02 | Tensor throughput | 1024 | INT8 MACs/MMA | TC test |
| P-03 | Warp dispatch | 1 | warp/cycle | scheduler test |

---

## 10. Verification Strategy

### 10.1 Verification Approach
Layered: L1 functional unit tests → L2 cycle equivalence → L5 DSL simulation +
cross-layer checks → L6 Verilog lint. Per-module test plans and reports live in each
layer's `specs/` directory.

### 10.2 Verification Levels
| Level | Method | Owner | Exit |
|-------|--------|-------|------|
| Unit | pytest per layer | RTLCraft Agent | all directed tests pass |
| Integration | cluster top sim + cross-layer | RTLCraft Agent | L1==L2==L5 |
| System | full-kernel sim | System Architect | all_done observed |

---

## 11. Deliverables

| ID | Deliverable | Format | Owner | Due |
|----|-------------|--------|-------|-----|
| D-01 | design_spec.md | Markdown | RTLCraft Agent | 2026-06-17 |
| D-02 | per-module 6-layer models | Python | RTLCraft Agent | 2026-06-17 |
| D-03 | per-layer specs/plans/reports | Markdown | RTLCraft Agent | 2026-06-17 |
| D-04 | generated Verilog | Verilog | RTLCraft Agent | 2026-06-17 |

---

## 12. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
