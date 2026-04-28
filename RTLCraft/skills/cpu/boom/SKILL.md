# BOOM-Style Out-of-Order RISC-V Processor (rtlgen)

This directory contains a **simplified, educational implementation** of a BOOM-style
out-of-order RISC-V processor core built with the `rtlgen` Python-to-Verilog framework.

> **Note**: This is a reference design for learning rtlgen and CPU microarchitecture.
> It is NOT a production-ready core. Key simplifications are listed below.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BOOMCore                                         │
├─────────────────┬───────────────────────────────────────────────────────────┤
│    Frontend     │              Backend (Out-of-Order Engine)                  │
├─────────────────┼──────────┬──────────┬──────────┬──────────┬───────────────┤
│                 │          │          │          │          │               │
│  FetchUnit  ────┼─► DecodeUnit    │ Rename   │  RS/IQ   │  ALU / MUL  │               │
│      │          │    │     │    │     │    │     │    │     │               │
│      ▼          │    ▼     │    ▼     │    ▼     │    ▼     │               │
│ BranchPredictor │          │  FreeList│          │  PhysicalRF│               │
│                 │          │  RMT     │          │          │               │
│                 │          │  BusyTbl │          │          │               │
│                 │          │    │     │          │    │     │               │
│                 │          │    ▼     │          │    ▼     │               │
│                 │          │   ROB ◄──┼──────────┼─── Writeback              │
│                 │          │          │          │    │     │               │
│                 │          │          │          │    ▼     │               │
│                 │          │          │          │   LSU ───┼──► Memory     │
│                 │          │          │          │          │               │
└─────────────────┴──────────┴──────────┴──────────┴──────────┴───────────────┘
```

### Pipeline Stages

1. **Fetch** (`FetchUnit`): Requests aligned fetch-packets from memory, consults
   branch predictor for next-PC.
2. **Decode** (`DecodeUnit`): Full RV32I decoder — extracts register fields, opcode,
   immediate, and generates control signals (is_load, is_store, is_branch, alu_op, etc.)
3. **Rename** (`RenameUnit`): Maps architectural registers to physical registers
   via the Rename Map Table (RMT). Allocates from a free list.
4. **Dispatch** (in `core.py`): Enqueues renamed instructions into the
   Reservation Station and ROB.
5. **Issue** (`ReservationStation`): Wakes up instructions when all source
   operands are ready, selects one for issue to an FU.
6. **Register Read** (`PhysicalRegFile`): Reads source operand values from the
   multi-ported physical register file.
7. **Execute** (`ALU`, `Multiplier`, `LSU`):
   - `ALU`: integer arithmetic, logic, shifts, branches
   - `Multiplier`: 3-cycle pipelined integer multiply
   - `LSU`: load/store unit with load queue, store queue, and store-to-load forwarding
8. **Writeback**: Results broadcast to the RS wakeup network and written to PRF.
9. **Commit** (`ReorderBuffer`): Instructions retire in-order, freeing old
   physical registers and updating architectural state.

---

## Module Catalog

| Module | File | Description |
|--------|------|-------------|
| `BOOMCore` | `core.py` | Top-level integration |
| `FetchUnit` | `frontend/fetch_unit.py` | Instruction fetch with BP interface |
| `BranchPredictor` | `frontend/branch_predictor.py` | BHT + BTB + RAS |
| `DecodeUnit` | `frontend/decode_unit.py` | Full RV32I instruction decoder |
| `RenameUnit` | `backend/rename.py` | RMT, Free List, Busy Table |
| `ReservationStation` | `backend/reservation_station.py` | Unified issue queue |
| `PhysicalRegFile` | `backend/physical_regfile.py` | Multi-ported register file |
| `ALU` | `backend/execution_units.py` | Integer ALU + branch resolution |
| `Multiplier` | `backend/execution_units.py` | 3-cycle pipelined multiplier |
| `LSU` | `backend/lsu.py` | Load/Store Unit with LQ/SQ |
| `ReorderBuffer` | `backend/reorder_buffer.py` | In-order commit buffer |

---

## Key Design Decisions

### 1. RV32I Decode Unit
The `DecodeUnit` fully decodes the RV32I base integer instruction set:
- **R-type**: ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND, MUL (M extension)
- **I-type**: ADDI, SLLI, SLTI, SLTIU, XORI, SRLI, SRAI, ORI, ANDI, LB, LH, LW, LBU, LHU, JALR
- **S-type**: SB, SH, SW
- **B-type**: BEQ, BNE, BLT, BGE, BLTU, BGEU
- **U-type**: LUI, AUIPC
- **J-type**: JAL

Control signals generated per instruction:
- `need_rs1/rs2/rd`, `use_imm`, `alu_op[3:0]`
- `is_load/store/branch/jump/alu/mul`
- `mem_size[1:0]`, `mem_signed`

### 2. Branch Predictor
- **BHT**: 64-entry table of 2-bit saturating counters
- **BTB**: 16-entry direct-mapped target cache
- **RAS**: 8-entry return address stack

### 3. Single Unified Reservation Station
Real BOOM uses separate issue queues per FU type. This version uses a single
unified RS to reduce code complexity while still demonstrating OoO issue.

### 4. Multi-Ported Physical Register File
- **6 read ports**: 2 operands × up to 3 issue lanes
- **4 write ports**: ALU, MUL, LSU, and one spare

### 5. Load/Store Unit
The LSU manages out-of-order memory accesses:
- **Load Queue (LQ)**: tracks in-flight loads, up to 8 entries
- **Store Queue (SQ)**: buffers stores until ROB commit, up to 8 entries
- **Store-to-load forwarding**: detects when a load matches an uncommitted store address
- **Memory arbitration**: committed stores have priority over loads
- **Sign/zero extension**: handles LB/LBU/LH/LHU/LW

### 6. ROB with In-Order Commit
The ROB is a circular buffer tracking in-flight instructions.
Each entry stores: physical destination, old physical destination, PC,
busy bit, and branch flag. Supports exception/mispredict flush.

---

## Running the Design

### Generate Verilog

```python
import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from skills.cpu.boom.core import BOOMCore
from rtlgen.codegen import VerilogEmitter

core = BOOMCore(
    xlen=32,
    fetch_width=2,
    rob_entries=16,
    rs_entries=8,
    num_pregs=64,
)

emitter = VerilogEmitter()
print(emitter.emit_design(core))
```

### Simulate (Simple Testbench)

```python
from rtlgen.sim import Simulator

sim = Simulator(core)
sim.reset('rst_n')

# Feed an ADDI instruction from "memory"
sim.set(core.mem_resp_valid, 1)
sim.set(core.mem_resp_data, 0x00500093)  # addi x1, x0, 5

for _ in range(20):
    sim.step()
```

---

## Simplifications vs. Real BOOM

| Feature | Real BOOM | This Version |
|---------|-----------|--------------|
| ISA | RV64GCB | RV32I subset + MUL |
| Fetch | GShare, TAGE, RAS | Simple BHT + BTB |
| Rename | Speculative RMT + snapshot | Single-cycle rename |
| Issue | Distributed IQs | Single unified RS |
| Load/Store | LSU with MSHRs, store queue, D-cache | Direct memory interface |
| FPU | Full IEEE-754 FMA, div/sqrt | Not implemented |
| MMU | Sv39, TLB, page walker | Not implemented |
| Cache | L1 I$/D$, inclusive L2 | Bypass to memory |
| Commit | 2+ instructions/cycle | Simplified width=1 issue |

---

## Future Extensions

- [ ] Add GShare or TAGE branch predictor
- [ ] Implement distributed issue queues (ALU / MEM / FP)
- [ ] Add D-cache with MSHRs
- [ ] Add CSR / exception handling (ecall, ebreak, interrupts)
- [ ] Add full RV64I support
- [ ] Add RISC-V formal verification properties
- [ ] Add multi-issue dispatch (currently RS only accepts width=1)
