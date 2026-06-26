# Thor-Class GPGPU SM Compute Cluster — Design Specification

**Project**: RTLCraft Spec2RTL design of a Thor-class GPGPU compute cluster
**Version**: 0.1
**Date**: 2026-06-17
**Design flow**: Spec2RTL 6-layer IR (L1 BehaviorIR → L2 CycleIR → L3 ArchitectureIR → L4 StructuralIR → L5 DSL → L6 Verilog) + Verilog output

---

## 1. Overview

This document defines a Thor-class General-Purpose GPU (GPGPU) **streaming-multiprocessor
(SM) compute cluster**, designed using RTLCraft's white-box Spec2RTL methodology with
mandatory cross-layer verification at every abstraction boundary.

The design is architecturally inspired by the NVIDIA Thor / Blackwell-class GPU compute
fabric and is concretely referenced against the RTLCraft `skills/gpgpu` library. The scope
of v0.1 is the **SM compute cluster**: instruction dispatch, warp scheduling, SIMT
execution, vector ALU/FPU/tensor-core datapaths, load/store, shared memory, and a
multi-SM cluster with a shared L2 round-robin arbiter.

### 1.1 Target Application
- Dense SIMT compute kernels (GEMM, element-wise FP32/INT32 vector ops, reductions)
- Tensor-core (INT8 matrix-multiply-accumulate) acceleration for inference workloads
- Warp-level barrier synchronization and inter-warp shared memory

### 1.2 Key Characteristics
| Item | Target |
|------|--------|
| Process target | 7nm-class high-performance CMOS (representative) |
| Core voltage | ~0.75–0.85 V |
| SM count (cluster) | 2 (NSM = 2) |
| Warps per SM | 4 (NWARP = 4) |
| Lanes per warp (SIMD width) | 8 (NLANE = 8) |
| Lane width | 32-bit (XLEN = 32) |
| Vector register width | 256-bit (VLEN = 256) |
| Tensor core | 8×8×8 INT8 → INT32 MMA |
| Clock domain | single `clk` (representative GPU core clock) |

---

## 2. Requirements Summary

| # | Requirement | Implementation |
|---|-------------|----------------|
| 1 | Multi-SM GPGPU compute cluster | **ThorCluster**: 2 SMs sharing one global memory port via a round-robin L2 arbiter |
| 2 | Warp-level SIMT execution | **WarpScheduler**: sticky round-robin scheduler over 4 warps; per-warp PC/FSM/barrier state |
| 3 | 8-lane INT32 vector ALU | **VectorALU**: per-lane ADD/SUB/AND/OR/XOR/SLL/SRL/SLT/SLTU with active-mask predication |
| 4 | 8-lane FP32 vector FPU | **VectorFPU**: per-lane FP32 add / mul / mul-add (IEEE-754 single) |
| 5 | INT8 tensor core | **TensorCore**: 8×8×8 INT8 × INT8 → INT32 matrix-multiply-accumulate |
| 6 | Vector load/store unit | **LSU**: vector load/store with memory request/response handshake |
| 7 | SIMT divergence support | **SIMTStack**: divergence push / reconvergence pop for conditional branches |
| 8 | Per-SM shared memory | **SharedMemory**: banked SRAM for inter-warp data sharing |
| 9 | Streaming Multiprocessor | **GpuSM**: integrates scheduler + core + LSU + shared memory + VRF + IMEM |
| 10 | Cluster interconnect | **GpuCluster**: 2× GpuSM + round-robin L2 arbiter + global memory interface |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Thor GPGPU Compute Cluster                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────────────── SM 0 ───────────────────────────┐    │
│   │  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │    │
│   │  │ WarpScheduler│──►│  SIMT Core   │──►│  Writeback    │   │    │
│   │  │ (4 warps,    │   │ Fetch/Decode │   │               │   │    │
│   │  │  sticky-RR)  │   │  +SIMTStack  │   │               │   │    │
│   │  └──────┬───────┘   └──┬─────┬─────┘   └───────────────┘   │    │
│   │         │              │     │                              │    │
│   │         │      ┌───────▼┐ ┌──▼────────┐                     │    │
│   │         │      │ vALU   │ │  vFPU     │   ┌───────────────┐  │    │
│   │         │      │ INT32  │ │  FP32     │   │  TensorCore   │  │    │
│   │         │      └────────┘ └───────────┘   │  8x8x8 INT8   │  │    │
│   │         │                                 └───────────────┘  │    │
│   │   ┌─────▼──────────┐   ┌──────────────────┐                  │    │
│   │   │ LSU (vec ld/st)│   │ SharedMemory     │   VRF (8×4)      │    │
│   │   └─────┬──────────┘   └──────────────────┘   IMEM (32)      │    │
│   └─────────┼────────────────────────────────────────────────────┘    │
│             │                                                         │
│   ┌─────────▼─────────── SM 1 (identical) ─────────────────────┐     │
│   │   ...                                                      │     │
│   └─────────┬──────────────────────────────────────────────────┘     │
│             │                                                         │
│             ▼                                                         │
│   ┌─────────────────────┐                                             │
│   │  L2 Round-Robin     │   ◄── global memory req/wen/addr/wdata     │
│   │  Arbiter (2 SMs)    │   ──► global memory valid/rdata/ready      │
│   └──────────┬──────────┘                                             │
│              │                                                        │
│              ▼  global memory interface (to host / HBM-like backing)  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Memory Hierarchy
| Level | Scope | Structure |
|-------|-------|-----------|
| Vector register file (VRF) | per warp | 8 vector registers × 256-bit, contiguous block per warp |
| Instruction memory (IMEM) | per SM | 32 × 32-bit, host-writable before `start` |
| Shared memory | per SM | banked SRAM, vector-word addressable |
| Global memory | cluster-wide | single port, arbitrated round-robin across the 2 SMs |

---

## 4. Spec2RTL 6-Layer Design Hierarchy

This design follows RTLCraft's mandatory **6-layer IR lowering + final Verilog output**, with
cross-layer consistency checks between adjacent layers.

| Stage | Layer / IR | File Location | Deliverable | Verification |
|-------|------------|---------------|-------------|--------------|
| 1 | **SpecIR** | `thor_gpu/specs/`, per-module `specs/` | Module specs (ports, function, timing, PPA goals) | Human review |
| 2 | **BehaviorIR (L1)** | `modules/<M>/layer_L1_behavior/` | Pure-Python functional models | `assert func() == expected` |
| 3 | **CycleIR (L2)** | `modules/<M>/layer_L2_cycle/` | Cycle-accurate Python models | `L2 == L1` via LayerVerifier |
| 4 | **ArchitectureIR (L3)** | `modules/<M>/layer_L3_architecture/` | Pipeline/operator/architecture plan | Metadata + invariant tests |
| 5 | **StructuralIR (L4)** | `modules/<M>/layer_L4_structure/` | Submodule decomposition + port maps | Connectivity checks |
| 6 | **DSL AST (L5)** | `modules/<M>/layer_L5_dsl/` | rtlgen `Module` classes | `Simulator` + cross-layer vs L1/L2 |
| 7 | **Verilog (L6)** | `modules/<M>/layer_L6_verilog/`, `verilog/` | Synthesizable `.v` + lint report | VerilogLinter |

### Cross-Layer Verification Contract
For every module:
```
L1 (functional)  ──►  L2 (cycle)  ──►  L5 (DSL)  ──►  Verilog
      ≡                    ≡               ≡
```
- `LayerVerifier.verify(...)` (or equivalent directed tests) must PASS before advancing.
- If mismatch: fix the lowest layer first.

---

## 5. Module Specifications

### 5.1 VectorALU — `ThorVectorALU`

**Purpose**: 8-lane INT32 vector ALU for the SIMT datapath. Per-lane predicated execution.

**Opcodes** (`alu_fn`, per-lane `s1 = src1`, `s2 = src2`):
| alu_fn | Operation |
|--------|-----------|
| 0 | ADD: s1 + s2 |
| 1 | SLL: s1 << (s2 & 0x1F) |
| 4 | XOR: s1 ^ s2 |
| 5 | SRL: (uint)s1 >> (s2 & 0x1F) |
| 6 | OR: s1 \| s2 |
| 7 | AND: s1 & s2 |
| 10 | SUB: s1 - s2 |
| 12 | SLT: (s1 < s2) ? 1 : 0 (signed) |
| 14 | SLTU: (uint)s1 < (uint)s2 ? 1 : 0 |

**Interfaces**: `src1/src2` (256-bit, 8×32), `active_mask` (8-bit), `alu_fn` (4-bit) → `result` (256-bit), `result_mask` (8-bit).
**Latency**: 1 cycle (registered).

---

### 5.2 VectorFPU — `ThorVectorFPU`

**Purpose**: 8-lane IEEE-754 FP32 vector FPU.

**Opcodes** (`fpu_fn`):
| fpu_fn | Operation |
|--------|-----------|
| 0 | FADD: s1 + s2 |
| 1 | FMUL: s1 * s2 |
| 2 | FMADD: s1 * s2 + s3 |

**Interfaces**: `src1/src2/src3` (256-bit), `active_mask` (8-bit), `fpu_fn` (2-bit) → `result` (256-bit).
**Latency**: 1 cycle (registered; full IEEE rounding modeled at L1/L2).

---

### 5.3 TensorCore — `ThorTensorCore`

**Purpose**: INT8 matrix-multiply-accumulate, 8×8×8: `C[8][8] += A[8][8] * B[8][8]`.

**Datapath**:
- A, B: 8×8 INT8 matrices (each operand = 64 bytes = 512 bits, packed row-major).
- C: 8×8 INT32 accumulator (2048 bits, packed row-major).
- Operation: `C[i][j] += sum_k A[i][k] * B[k][j]`, k = 0..7.

**Interfaces**: `a` (512-bit), `b` (512-bit), `c` (2048-bit), `start`, `acc_en` → `result` (2048-bit), `done`.
**Latency**: 1 cycle (combinational MAC modeled at L1; registered at L5).

---

### 5.4 WarpScheduler — `ThorWarpScheduler`

**Purpose**: schedule one warp per cycle across 4 warps using a **sticky round-robin** policy, and manage per-warp state + barrier synchronization.

**Scheduler rule**: `warp_sel` advances to `warp_sel + 1` only when the currently selected warp is idle (FSM IDLE / DONE / BARRIER); otherwise it stays, letting a busy warp progress.

**Per-warp state**: `warp_pc` (32-bit), `warp_state` (4-bit FSM), `warp_done` (1-bit), `barrier_mask` (1-bit), `warp_acc` (64-bit).

**Barrier**: `all_at_barrier = AND_w(barrier_mask[w] | warp_done[w])`; when true, all barriers clear and blocked warps resume.

**Interfaces**: `clk`, `rst_n`, `start`, per-warp `warp_idle` (4-bit), `warp_at_barrier` (4-bit), `warp_done_in` (4-bit) → `warp_sel` (2-bit), `warp_pc` (32-bit), `barrier_release` (1-bit), `sm_done` (1-bit).

---

### 5.5 SIMTStack — `ThorSIMTStack`

**Purpose**: manage SIMT divergence/reconvergence for conditional branches. On a divergent branch, push the not-taken mask and reconvergence PC; pop when the taken path converges.

**Interfaces**: `branch_pc` (32-bit), `reconverge_pc` (32-bit), `taken_mask` (8-bit), `active_mask` (8-bit), `push`, `pop`, `pop_q_empty` → `next_pc` (32-bit), `next_mask` (8-bit), `stack_depth`.

---

### 5.6 LSU — `ThorLSU`

**Purpose**: vector load/store unit. Issues a single memory transaction per vector instruction; handles request/response handshake.

**Interfaces**: `req_op` (1 = store, 0 = load), `addr` (32-bit), `wdata` (256-bit), `valid_in`, `mem_ready` → `mem_req`, `mem_wen`, `mem_addr` (32-bit), `mem_wdata` (256-bit); `mem_valid`, `mem_rdata` (256-bit) → `rdata` (256-bit), `done`.

---

### 5.7 SharedMemory — `ThorSharedMemory`

**Purpose**: per-SM banked SRAM for inter-warp data sharing. Single-port, 32-bit word, vector-word addressable (8 lanes mapped to 8 banks).

**Interfaces**: `we` (1-bit), `addr` (12-bit), `wdata` (256-bit), `re` (1-bit) → `rdata` (256-bit).

---

### 5.8 GpuSM — `ThorGpuSM`

**Purpose**: one streaming multiprocessor. Integrates the warp scheduler, IMEM, VRF, SIMT core (decode → ALU/FPU/TC), LSU, and shared memory. Executes the custom ISA.

**Per-warp FSM**: IDLE(0) → FETCH(1) → DECODE(2) → {EXEC(4) | MEM_REQ(3)→MEM_WAIT(5) | BARRIER(6)} → IDLE; DONE(0xF) terminal.

**Interfaces**: `clk`, `rst_n`, `start`, `imem_wr_*`, `mem_req/wen/addr/wdata` (out), `mem_valid/rdata/ready` (in), `sm_done`, `debug_w0_acc0`.

---

### 5.9 GpuCluster — `ThorCluster` (top)

**Purpose**: 2× GpuSM sharing one global memory port via a 1-bit round-robin arbiter.

**Interfaces**: `clk`, `rst_n`, `start`, per-SM `imem_wr_*`, global `mem_req/wen/addr/wdata` (out), `mem_valid/rdata/ready` (in), `all_done`, per-SM `w0_acc0` debug.

---

## 6. Instruction Set Architecture (ISA)

32-bit instruction encoding. Opcode in `inst[31:28]`.

| Opcode | Code | Fields (rd[27:24] rs1[23:20] rs2[19:16] imm[15:0]) | Semantics |
|--------|------|-----------------------------------------------------|-----------|
| NOP    | 0x0  | —                                                   | no-op |
| VLOAD  | 0x1  | rd, imm                                             | `vrf[rd] ← mem[imm]` |
| VSTORE | 0x2  | rd, imm                                             | `mem[imm] ← vrf[rd]` |
| VADD   | 0x3  | rd, rs1, rs2                                        | `vrf[rd] ← vrf[rs1] + vrf[rs2]` (8-lane) |
| VMUL   | 0x4  | rd, rs1, rs2                                        | `vrf[rd] ← vrf[rs1] * vrf[rs2]` (8-lane, low 32) |
| VMAC   | 0x5  | rs1, rs2                                            | `warp_acc[w] += lane0(vrf[rs1]) * lane0(vrf[rs2])` (64-bit) |
| BARRIER| 0x6  | —                                                   | set `barrier_mask[w]`, stall until all warps at barrier/done |
| SLOAD  | 0x7  | rd, imm                                             | broadcast sign-extended `imm` to all 8 lanes of `vrf[rd]` |
| DONE   | 0xF  | —                                                   | set `warp_done[w]`, freeze warp |

**VRF addressing**: `vrf_base = warp_sel * VREGS`; `vrf_index = vrf_base + reg`.

---

## 7. PPA Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Cluster SIMD throughput | 2 SMs × 8 lanes × INT32 op/cycle | 16 lanes/cycle INT32 |
| Tensor throughput | 1 MMA/SM, 8×8×8 INT8 MAC | 1024 INT8 MACs/MMA |
| Warp scheduler | 1 warp dispatched/cycle | sticky-RR over 4 warps |
| Global memory arbitration | round-robin, 1 outstanding/SM | fair across 2 SMs |
| Representative clock | GPU core clock | single domain in v0.1 |

### 7.1 PPA Optimization Strategy (6-Layer IR)

| IR Layer | PPA Focus | Key Decisions |
|----------|-----------|---------------|
| **SpecIR** | Requirements & budgets | Define throughput, lane count, SM count, arbitration policy |
| **BehaviorIR** | Functional golden | Validate algorithmic choices (INT8 MMA, FP32 rounding) without timing |
| **CycleIR** | Latency & throughput | Fix 1-cycle ALU/FPU, MMA latency, scheduler advancement rule |
| **ArchitectureIR** | Microarchitecture | Sticky-RR scheduler, flat per-warp VRF, lane-0 VMAC accumulator |
| **StructuralIR** | Decomposition | Isolate INT/FP/TC datapaths; separate scheduler from execution |
| **DSL/Verilog** | Implementation | Registered datapaths; combinational decode; clock-enable idle gating modeled |

---

## 8. Verification Plan

### 8.1 Layer-by-Layer Checks
| Layer | Method | Coverage |
|-------|--------|----------|
| L1 Functional | Python unit tests directed + constrained random | 100% opcode coverage for ALU/FPU/TC/scheduler |
| L2 Cycle | CycleContext simulation | All FSM transitions, barrier, scheduler advance |
| L5 DSL | `Simulator` + cross-layer equivalence | Bit-exact match with L1/L2 |
| Verilog | `VerilogEmitter` + `VerilogLinter` | Lint-clean, compiles |

### 8.2 Module-Specific Tests
- **VectorALU**: all `alu_fn` codes, signed/unsigned, per-lane predication.
- **VectorFPU**: FADD/FMUL/FMADD vs Python `struct` FP32 reference, rounding corners.
- **TensorCore**: identity matrix, all-ones, random INT8 vs numpy-free reference.
- **WarpScheduler**: sticky-RR advance rule, barrier release, sm_done.
- **SIMTStack**: push/pop, divergence mask, reconvergence PC.
- **LSU**: load then store handshake ordering.
- **SharedMemory**: write/read across banks.
- **GpuSM**: VADD/VMUL/VMAC/SLOAD/DONE micro-kernel; barrier across warps.
- **GpuCluster**: 2 SMs arbitrate global memory; `all_done`.

---

## 9. Implementation Roadmap

| Step | Task | Output | Checkpoint |
|------|------|--------|------------|
| 1 | Finalize `design_spec.md` (this doc) | `thor_gpu/design_spec.md` | Human review |
| 2 | Top-level + per-module SpecIR | `thor_gpu/specs/`, module `specs/` | Human review |
| 3 | L1 functional models + tests | `layer_L1_behavior/` | Unit tests PASS |
| 4 | L2 cycle-level models + tests | `layer_L2_cycle/` | L2 == L1 |
| 5 | L3/L4 architecture + structural | `layer_L3_*/`, `layer_L4_*/` | Metadata checks |
| 6 | L5 DSL implementation + tests | `layer_L5_dsl/` | L5 sim PASS, cross-layer |
| 7 | L6 Verilog generation + lint | `layer_L6_verilog/`, `verilog/` | Lint clean |
| 8 | Cluster top integration + verification | `top/`, `verilog/` | All tests PASS |

---

## 10. Open Questions / Decisions Log

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | Scope vs. full Thor SoC | SM compute cluster (2 SM + cluster); no Grace CPU / HBM / NVLink in v0.1 | 2026-06-17 |
| 2 | Reference vs. fresh code | Reference `skills/gpgpu`; write fresh self-contained 6-layer implementations | 2026-06-17 |
| 3 | Tensor core data type | INT8 × INT8 → INT32, 8×8×8 MMA | 2026-06-17 |
| 4 | Warp scheduler policy | Sticky round-robin (advance only when current warp idle) | 2026-06-17 |
| 5 | VMAC accumulator | 64-bit, lane-0 product only (matches Thor reference) | 2026-06-17 |
| 6 | FP rounding | IEEE-754 round-to-nearest-even at L1/L2; registered datapath at L5 | 2026-06-17 |

---

## 11. References

- RTLCraft `README.md` / `Tutorial.md` — Spec2RTL methodology and 6-layer IR flow.
- `earphone/design_spec.md` — pilot SoC spec (flow template).
- `skills/gpgpu/thor_gpu.py` — Thor-class GPGPU architectural reference.
- `skills/gpgpu/dsl_modules.py` — vALU `alu_fn` table and exec-unit port shapes.
- NVIDIA Blackwell / Thor architecture (public, representative inspiration).
