# hetero_riscv4 — DSL Modules Index

Heterogeneous 4-core RISC-V SoC: 2 efficiency cores (3-stage RV64I) + 2 performance cores (5-stage RV64I)
in a 2×2 mesh NoC with directory-based MSI cache coherence.

---

## Module Summary

| # | Module | Role | Lines | Stages | Key Patterns |
|---|--------|------|-------|--------|-------------|
| 1 | NoCBuffer | FIFO input buffer for router ports | ~50 | 2 | fifo, valid_ready, credit_based_flow |
| 2 | EfficiencyCore | 3-stage RV64I CPU core | ~290 | F/E/W | riscv, alu, branch, load_store, forwarding |
| 3 | PerformanceCore | 5-stage RV64I CPU core | ~360 | F/D/E/M/W | riscv, alu, branch, load_store, forwarding, hazard |
| 4 | L1CacheSmall | 16KB 2-way L1 cache for eff cores | ~170 | FSM | cache, tag_lookup, hit_miss, lru, mesi |
| 5 | L1CacheBig | 64KB 8-way L1 cache for perf cores | ~160 | FSM | cache, tag_lookup, hit_miss, lru, mesi |
| 6 | CoherenceDir | MSI directory coherence controller for 4 cores | ~130 | FSM | coherence, directory, mesi, sharers, invalidation |
| 7 | NoCRouter | 5-port mesh NoC router with XY routing | ~380 | pipeline | noc_router, mesh, crossbar, arbitration, xy_routing |
| 8 | HeteroMeshTop | 2×2 mesh SoC top-level interconnect | ~1900 | hierarchy | mesh_noc, soc_integration, big_little_cluster |

---

## Detailed Module Descriptions

### 1. NoCBuffer

**Function:** Simple FIFO buffer for NoC router input ports with credit-based flow control.
Stores flits in a depth-4 array, manages read/write pointers and count registers for full/empty detection.
Supports push (valid_in & ready_out), pop, and simultaneous push+pop operations.
Outputs data_out from read pointer, generates ready_out when not full, valid_out when not empty,
and full/empty flags for upstream flow control.

**Interface:** clk, rst_n, valid_in, pop, data_in(64) → ready_out, data_out(64), valid_out, empty, full

**State:** buf_data[4][64], buf_count[3], buf_rd_ptr[2], buf_wr_ptr[2]

**Logic:** 1 comb block (data_out Mux, empty/full detection, ready/valid generation),
1 seq block (reset, push/pop pointer management, count update)

---

### 2. EfficiencyCore

**Function:** 3-stage RV64I in-order CPU pipeline (Fetch→Execute→Writeback).
Fetch stage requests instructions from I-Cache, latches 32-bit instruction and PC on cache valid.
Execute stage performs combined decode+ALU: extracts opcode/funct3/funct7/rs1/rs2/rd fields,
generates I/S/B/U/J-type immediates with sign extension, reads 32-entry register file with WB-stage forwarding,
computes R-type (ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU), I-type, LUI, AUIPC, JAL, JALR results via Mux chain.
Branch comparison (BEQ/BNE) with PC redirect on taken branches. D-Cache load/store address calculation.
Writeback stage writes ALU result or load data to register file. Supports ECALL for system calls.

**Interface:** clk, rst_n, icache_req/addr(64), icache_valid, icache_rdata(64),
dcache_req/addr(64)/wdata(64)/wen, dcache_valid, dcache_rdata(64), dcache_ready →
core_stall, core_halted, retire_valid, retire_count(3)

**State:** pc_reg(64), fetch_valid, fetch_instr(32), exec_valid, exec_instr(32), exec_pc(64),
wb_valid, wb_result(64), wb_wb_en, wb_rd(5), rf[32][64]

**Logic:** 1 comb block (decode, ALU Mux chain, branch compare, cache control, load extension),
1 seq block (pipeline registers F→E→W, PC update, regfile write)

**Sub-modules for fine-grained generation:**

#### 2a. EfficiencyCore — PCReg (program_counter)
**Function:** PC register initialized to 0x1000, advances by 4 each cycle when not stalled,
redirects to branch_target on taken branch or jump. Drives I-Cache address request.
Supports stall from I-Cache miss and D-Cache miss. Generates branch_redirect signal
to flush pipeline on control flow change.

**Keywords:** pc, program_counter, branch_redirect, icache_addr, advance_by_4, control_flow

#### 2b. EfficiencyCore — FetchStage (instruction_fetch)
**Function:** I-Cache request/response interface. Asserts icache_req when fetch pipeline slot is empty,
drives icache_addr from pc_reg. On icache_valid, latches 32-bit instruction from lower half of
64-bit cache line and captures current PC. Generates icache_stall when waiting for cache response.
Branch redirect clears fetch_valid to flush stale instructions.

**Keywords:** fetch, icache, instruction_latch, cache_stall, pipeline_flush, valid_handshake

#### 2c. EfficiencyCore — DecodeALU (decode_alu_execute)
**Function:** Combined decode+execute stage for 3-stage pipeline. Extracts opcode[6:0], funct3[14:12],
funct7[31:25] from 32-bit instruction. Generates all immediate types (I/S/B/U/J) with sign extension.
Reads register file rs1/rs2 with WB-stage forwarding bypass. Computes ALU operations via cascaded Mux:
ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU for R-type and I-type, LUI, AUIPC, JAL, JALR, BEQ, BNE.
Generates branch_taken from rs1/rs2 comparison, branch_target from PC+offset. D-Cache load/store
address = base+offset. Load data sign/zero extension (LB/LBU/LH/LHU/LW/LWU/LD).

**Keywords:** decode, opcode, immediate, alu, mux_chain, rtype, itype, branch_compare, forwarding,
load_store, sign_extend

#### 2d. EfficiencyCore — WritebackReg (writeback_regfile)
**Function:** Writeback stage captures ALU result and wb_en/wb_rd from execute stage.
Writes to 32-entry 64-bit register file when wb_valid & wb_en & rd!=0. Generates retire_valid
when instruction completes. Provides forwarding data (wb_result) to decode stage for rs1/rs2 bypass.
Drive core_stall, core_halted, retire_count status outputs.

**Keywords:** writeback, regfile, retire, forwarding, status, wb_en, register_write

---

### 3. PerformanceCore

**Function:** Full 5-stage RV64I in-order CPU pipeline (Fetch→Decode→Execute→Memory→Writeback).
Fetch requests 64-bit I-Cache line, latches 32-bit instruction with PC.
Decode extracts fields, generates immediates, performs branch comparison (BEQ/BNE/JAL/JALR)
with early branch resolution and PC redirect. Register read with 3-stage forwarding (EX/MEM/WB).
Execute stage has dedicated ALU Mux chain for R-type/I-type/LUI/AUIPC/JAL/JALR operations.
Memory stage handles D-Cache load/store with data width extension.
Writeback writes result to 32-entry register file.
Stall detection for I-Cache miss and D-Cache miss with pipeline freeze.
Branch redirect flushes all pipeline stages.

**Interface:** Same as EfficiencyCore (clk, rst_n, icache/dcache interfaces, status outputs)

**State:** pc_reg(64), 5 pipeline registers per stage (valid, instr/pc, ra/rb for EX, alu_result for MEM,
result for WB), rf[32][64]

**Logic:** 1 comb block (decode, ALU Mux chain, 3-stage forwarding, branch compare, load extension),
1 seq block (5-stage pipeline registers F→D→E→M→W, PC update, regfile write)

**Sub-modules for fine-grained generation:**

#### 3a. PerformanceCore — PCReg (program_counter)
**Function:** 64-bit PC register initialized to 0x1000, advances by 4 per cycle when core not stalled.
Redirects to branch_target on decode-stage branch resolution. Generates icache_addr for instruction fetch.
Stall signal freezes PC on I-Cache or D-Cache miss. Branch redirect clears all downstream pipeline valid bits.

**Keywords:** pc, program_counter, branch_redirect, icache_addr, advance_by_4, stall_freeze, control_flow

#### 3b. PerformanceCore — FetchStage (instruction_fetch)
**Function:** I-Cache request on fetch slot empty, addr from PC. Latches 32-bit instruction from
64-bit cache line lower half, captures PC into fetch_pc register. Generates icache_stall when
fetch_valid but no cache response. Branch redirect flushes fetch_valid. Pipeline advances on !stall.

**Keywords:** fetch, icache, instruction_latch, cache_stall, pipeline_flush, valid_handshake, pc_capture

#### 3c. PerformanceCore — DecodeStage (instruction_decode_branch)
**Function:** Decodes instruction fields (opcode, funct3, funct7, rs1, rs2, rd). Generates all 5 immediate
types with sign extension. Performs early branch comparison: BEQ (rs1==rs2), BNE (rs1!=rs2),
JAL (unconditional), JALR (ra+imm & ~1). Computes branch_target from PC+offset. Asserts branch_redirect
when decode_valid & branch_taken to flush all 5 pipeline stages. Register read with 3-stage forwarding
bypass from EX/MEM/WB results.

**Keywords:** decode, opcode, immediate, branch_compare, branch_target, early_branch, redirect,
register_read, forwarding_mux

#### 3d. PerformanceCore — ExecuteALU (execute_alu)
**Function:** Dedicated ALU stage with cascaded Mux chain. Computes R-type results (ADD/SUB/XOR/OR/AND/
SLL/SRL/SRA/SLT/SLTU) from pipeline-captured ra/rb. I-type ALU from ra+immediate. Generates final
exec_alu_result selecting between R-type, I-type, LUI(imm_u), AUIPC(pc+imm_u), JAL(pc+imm_j),
JALR(ra+imm_i), store(ra+imm_s), branch(pc+imm_b). Generates exec_wb_en for writeback-eligible
instructions. Drives D-Cache request address and write data for load/store.

**Keywords:** alu, execute, rtype, itype, mux_chain, add_sub_xor_shift, lui_auipc, jal_jalr,
wb_en, cache_addr

#### 3e. PerformanceCore — MemoryStage (load_store_memory)
**Function:** Memory stage captures ALU result, wb_en, rd, load flag from execute. On D-Cache response,
captures dcache_rdata as mem_load_data. Generates load data extension wires: LB(sign-extend byte),
LBU(zero-extend byte), LH(sign-extend half), LHU(zero-extend half), LW(sign-extend word),
LWU(zero-extend word), LD(full double). Selects wb_result from mem_is_load?load_data:alu_result.

**Keywords:** memory, load_store, dcache, sign_extend, zero_extend, lb_lh_lw_ld, memory_stage

#### 3f. PerformanceCore — WritebackReg (writeback_regfile)
**Function:** Writeback stage captures result and control from memory stage. Writes to rf[rd] when
wb_valid & wb_en & rd!=0. Generates retire_valid for performance monitoring. Provides 64-bit
forwarding data to decode stage. Drives core_stall, core_halted, retire_count status.

**Keywords:** writeback, regfile, retire, forwarding, register_write, status

#### 3g. PerformanceCore — HazardUnit (stall_hazard_detection)
**Function:** Detects I-Cache stall (fetch_valid & !icache_valid) and D-Cache stall
(exec_valid & mem_access & !dcache_valid). Combines into core_stall_w to freeze all pipeline stages.
Generates branch_redirect to flush pipeline on control flow change. Manages pipeline valid signal
propagation: each stage clears valid on redirect, advances on !stall.

**Keywords:** hazard, stall, icache_stall, dcache_stall, pipeline_freeze, branch_flush, valid_propagation

---

### 4. L1CacheSmall

**Function:** 16KB 2-way set-associative L1 cache for efficiency cores.
Parameters: 128 sets, 64B line, 51-bit tag. Dual-port data RAM (2 ways), dual-port tag RAM,
valid RAM, MSI state RAM, LRU bit per set.
4-state FSM: IDLE→CHECK(hit/miss)→REFILL(from NoC)→PROBE(coherence invalidation).
Tag comparison on both ways in parallel, hit selects data from matching way.
Miss triggers NoC refill request, stores returned line in LRU-selected way.
Coherence probe checks tag, invalidates matching entry on probe_invalidate.
LRU bit toggles on each refill for pseudo-LRU replacement.

**Interface:** clk, rst_n, req, addr(64), wdata(64), wen → valid, rdata(64), ready,
probe_addr(64), probe_valid, probe_invalidate → probe_ack,
noc_req, noc_addr(64), noc_rdata(64), noc_valid → cache_state(2)

**State:** data_ram0/1[128][512], tag_ram0/1[128][51], valid_ram0/1[128][1],
state_ram0/1[128][2], lru[128][1], cache_fsm[2], refill_set[7], refill_line[512]

**Logic:** 1 comb block (tag compare, hit detection, data select, probe check, LRU select),
1 seq block (FSM transitions, data write, tag update, valid update, LRU update)

---

### 5. L1CacheBig

**Function:** 64KB 8-way set-associative L1 cache for performance cores.
Parameters: 128 sets, 64B line, 51-bit tag. Similar FSM and interface as L1CacheSmall
but wider associativity for higher hit rate. 4-state FSM: IDLE→CHECK→REFILL→PROBE.
Hit selects data from matching way, miss triggers NoC refill with LRU replacement.
Coherence probe invalidation for MSI protocol.

**Interface:** Same as L1CacheSmall

**State:** data_ram0/1[128][512], tag_ram0/1[128][51], valid_ram0/1[128][1],
state_ram0/1[128][2], lru[128][1], cache_fsm[2]

**Logic:** Same structure as L1CacheSmall with scaled parameters

---

### 6. CoherenceDir

**Function:** Directory-based MSI coherence controller for 4-core system.
64-entry direct-mapped directory with tag, MSI state, 4-bit sharers bitmask, owner core_id.
5-state FSM: IDLE→LOOKUP→PROBE(sharers invalidate)→UPDATE→WB(writeback for M→S downgrade).
On shared read: adds requester to sharers, returns data. On exclusive write: invalidates current
owner, grants modified state. On M-state read request: triggers writeback to current owner,
then grants shared state. Generates probe_targets bitmask for snoop invalidation.
Generates writeback_to_core + writeback_core_id for M→S downgrade.

**Interface:** clk, rst_n, req_valid, req_core_id(6), req_addr(64), req_is_write →
resp_valid, resp_action(3), probe_targets(4), probe_addr(64), probe_valid, probe_invalidate,
writeback_valid, writeback_data(64) → writeback_to_core, writeback_core_id(6)

**State:** dir_tag[64][58], dir_state[64][2], dir_sharers[64][4], dir_owner[64][6],
dir_valid[64][1], dir_fsm[3]

**Logic:** 1 comb block (tag compare, hit detection, sharers decode),
1 seq block (5-state FSM, directory update, probe generation, writeback handling)

---

### 7. NoCRouter

**Function:** 5-port mesh NoC router (East/West/North/South/Local) with XY dimension-order routing.
Each input port has depth-4 FIFO buffer with read/write pointers and count.
Per-input routing: extracts dest_x[5:3] and dest_y[9:6] from flit header, compares with
current (x_pos, y_pos) coordinates to select output port (X-first, then Y).
Per-output arbitration: fixed priority (E>W>N>S>J) — each output independently grants to
highest-priority requesting input. Crossbar selects winning input data for each output.
Input popped when it wins grant on ANY output AND that output's downstream is ready.
Credit-based flow control: ready = !full on each input port.

**Interface:** clk, rst_n, x_pos(3), y_pos(3),
e/w/n/s_flit(64), e/w/n/s_valid, e/w/n/s_ready_i, loc_inj_flit(64), loc_inj_valid, loc_ej_ready →
e/w/n/s_ready, e/w/n/s_flit_o(64), e/w/n/s_valid_o,
loc_inj_ready, loc_ej_flit(64), loc_ej_valid

**State:** buf_e/w/n/s/j_data[4][64], buf_e/w/n/s/j_cnt[3], buf_e/w/n/s/j_rd[2], buf_e/w/n/s/j_wr[2]

**Logic:** 1 comb block (XY routing ×5, arbitration ×5, crossbar ×5, pop logic ×5, ready generation),
1 seq block (buffer push/pop, count update, output valid register)

**Sub-modules for fine-grained generation:**

#### 7a. NoCRouter — NoCBuffer (noc_buffer_fifo)
**Function:** Depth-4 FIFO with data array, count, read/write pointers. Push increments write pointer
and count when valid & !full. Pop increments read pointer and decrements count when !empty.
Generates full (count==4), empty (count==0) flags. Data read from buf_data[read_pointer].

**Keywords:** fifo, buffer, push_pop, read_write_pointer, count, full_empty, depth_4

#### 7b. NoCRouter — XYRouter (xy_routing_function)
**Function:** Dimension-order XY routing. Reads dest_x and dest_y from flit header bits [5:3] and [9:6].
Compares dest_x with current x_pos: if dest_x > x_pos route East, if dest_x < x_pos route West.
If x matches, compares dest_y with y_pos: if dest_y > y_pos route North, if dest_y < y_pos route South.
If both match, route to Local eject. Applied independently to each of 5 input buffers.

**Keywords:** xy_routing, dimension_order, coordinate_compare, port_selection, east_west_north_south

#### 7c. NoCRouter — CrossbarArb (crossbar_arbitration)
**Function:** Per-output fixed-priority arbiter. For each output port, collects requests from all
5 inputs whose XY routing decision matches that output. Priority order: E>W>N>S>J.
Selects winning input via cascaded Mux. Crossbar outputs data from winning buffer's read pointer.
Generates valid_out when grant != NONE. Independent arbitration per output port.

**Keywords:** crossbar, arbitration, fixed_priority, grant, mux_select, per_output, independent

#### 7d. NoCRouter — FlowCtrl (credit_flow_control)
**Function:** Credit-based flow control. Input ready = !full (count < depth). Push when upstream
valid & ready. Pop when input wins output grant AND downstream ready_i. Count update:
count <= count + push - pop. Output valid driven by crossbar valid signal.

**Keywords:** credit, flow_control, ready_valid, push_pop, backpressure, downstream_ready

---

### 8. HeteroMeshTop

**Function:** Complete 2×2 mesh SoC topology instantiating and connecting 13 submodules.
Layout: PerfCore0+L1Big0 at (0,0) — PerfCore1+L1Big1 at (1,0) connected horizontally,
EffCore0+L1Sm0 at (0,1) — EffCore1+L1Sm1 at (1,1) connected horizontally,
vertical connections between row 0 and row 1. Each cluster has CPU core + L1 cache + NoC router.
Coherence directory shared across all 4 cores. Wires all I-Cache, D-Cache, coherence probe,
and NoC interconnect signals between submodules. External retire observation ports for all 4 cores.

**Interface:** clk, rst_n → retire_valid/count[0:3] (8 outputs)

**Submodules:** 4 CPU cores + 4 L1 caches + 1 CoherenceDir + 4 NoCRouters = 13 instances

**Logic:** Pure structural instantiation with wire connections between submodules

---

## Sub-Module Index (for fine-grained retrieval)

| Parent | Sub-Module | Description |
|--------|-----------|-------------|
| EfficiencyCore | PCReg | Program counter with branch redirect and stall freeze |
| EfficiencyCore | FetchStage | I-Cache request/response and instruction latch |
| EfficiencyCore | DecodeALU | Instruction decode + ALU Mux chain + branch comparison |
| EfficiencyCore | WritebackReg | Register file writeback + retire + forwarding |
| PerformanceCore | PCReg | Program counter with branch redirect and stall freeze |
| PerformanceCore | FetchStage | I-Cache request/response and instruction latch |
| PerformanceCore | DecodeStage | Instruction decode + early branch + register forwarding |
| PerformanceCore | ExecuteALU | R/I-type ALU Mux chain + cache address calculation |
| PerformanceCore | MemoryStage | Load/store with sign/zero extension |
| PerformanceCore | WritebackReg | Register file writeback + retire + forwarding |
| PerformanceCore | HazardUnit | Stall detection + pipeline freeze + branch flush |
| NoCRouter | NoCBuffer | FIFO buffer with push/pop and full/empty detection |
| NoCRouter | XYRouter | Dimension-order XY routing from flit header |
| NoCRouter | CrossbarArb | Per-output fixed-priority arbiter + crossbar Mux |
| NoCRouter | FlowCtrl | Credit-based flow control with backpressure |
