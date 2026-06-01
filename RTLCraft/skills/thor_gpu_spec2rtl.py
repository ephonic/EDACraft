"""
Thor-class GPGPU — Spec-to-RTL flow demonstration.

Architecture:
  - 2 SMs (Streaming Multiprocessors)
  - 4 warps per SM, 8-wide SIMD lanes per warp
  - Per-warp vector register file (8 regs × 8 lanes × 32b)
  - Per-SM shared instruction memory (32 entries)
  - Sticky round-robin warp scheduler (advances when warp idle/done/barrier)
  - Warp-level barrier synchronization
  - Global memory with round-robin SM arbiter

Flow:
  1. ArchDefinition  →  2. ArchSimulator (golden vectors)
  3. ArchSkeletonGenerator  →  4. DSL implementation
  5. Verilog emission  →  6. Testbench verification
"""

from rtlgen.arch_def import (
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, CycleContext,
)
from rtlgen.arch_sim import ArchSimulator
from rtlgen.arch_skel import ArchSkeletonGenerator
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Elif, Else, Switch, Mux, Cat, Rep, Const, ForGen

# =====================================================================
# Parameters
# =====================================================================
XLEN       = 32
NLANE      = 8
VLEN       = XLEN * NLANE   # 256
VREGS      = 8
NWARP      = 4
NSM        = 2
IMEM_DEPTH = 32
ACCW       = 64

OP_NOP     = 0x0
OP_VLOAD   = 0x1
OP_VSTORE  = 0x2
OP_VADD    = 0x3
OP_VMUL    = 0x4
OP_VMAC    = 0x5
OP_BARRIER = 0x6
OP_SLOAD   = 0x7
OP_DONE    = 0xF


# =====================================================================
# Behavioral helper: decode instruction fields
# =====================================================================
def decode_inst(inst: int):
    opcode = (inst >> 28) & 0xF
    rd     = (inst >> 24) & 0xF
    rs1    = (inst >> 20) & 0xF
    rs2    = (inst >> 16) & 0xF
    imm    = inst & 0xFFFF
    # sign-extend imm
    if imm & 0x8000:
        imm |= ~0xFFFF
    return opcode, rd, rs1, rs2, imm


# =====================================================================
# SM behavior (cycle-accurate behavioral model)
# =====================================================================
def sm_behavior(ctx: CycleContext):
    """Behavioral model for a single SM."""
    # Inputs
    clk      = ctx.get_input("clk", 0)
    rst_n    = ctx.get_input("rst_n", 1)
    start    = ctx.get_input("start", 0)
    imem_wr_en   = ctx.get_input("imem_wr_en", 0)
    imem_wr_addr = ctx.get_input("imem_wr_addr", 0)
    imem_wr_data = ctx.get_input("imem_wr_data", 0)
    mem_valid    = ctx.get_input("mem_valid", 0)
    mem_rdata    = ctx.get_input("mem_rdata", 0)
    mem_ready    = ctx.get_input("mem_ready", 1)

    # State (initialize on first access)
    warp_pc    = ctx.get_state("warp_pc",    [0] * NWARP)
    warp_state = ctx.get_state("warp_state", [0] * NWARP)
    warp_done  = ctx.get_state("warp_done",  [0] * NWARP)
    warp_acc   = ctx.get_state("warp_acc",   [0] * NWARP)
    barrier_mask = ctx.get_state("barrier_mask", [0] * NWARP)
    warp_sel   = ctx.get_state("warp_sel", 0)
    inst_reg   = ctx.get_state("inst_reg", 0)
    running    = ctx.get_state("running", 0)
    imem       = ctx.get_state("imem", [0] * IMEM_DEPTH)
    vrf        = ctx.get_state("vrf", [0] * (VREGS * NWARP))

    # --- IMEM write (combinational) ---
    if imem_wr_en:
        imem = list(imem)
        imem[imem_wr_addr % IMEM_DEPTH] = imem_wr_data
        ctx.set_state("imem", imem)

    # --- Sequential update (only on posedge clk) ---
    # In the behavior model we run every cycle; treat each call as posedge.
    if rst_n == 0:
        ctx.set_state("warp_sel", 0)
        ctx.set_state("inst_reg", 0)
        ctx.set_state("running", 0)
        ctx.set_state("warp_pc", [0] * NWARP)
        ctx.set_state("warp_state", [0] * NWARP)
        ctx.set_state("warp_done", [0] * NWARP)
        ctx.set_state("warp_acc", [0] * NWARP)
        ctx.set_state("barrier_mask", [0] * NWARP)
        ctx.set_output("mem_req", 0)
        ctx.set_output("mem_wen", 0)
        ctx.set_output("mem_addr", 0)
        ctx.set_output("mem_wdata", 0)
        ctx.set_output("sm_done", 0)
        ctx.set_output("debug_w0_acc0", 0)
        return

    # Copy mutable state
    warp_pc    = list(warp_pc)
    warp_state = list(warp_state)
    warp_done  = list(warp_done)
    warp_acc   = list(warp_acc)
    barrier_mask = list(barrier_mask)
    vrf        = list(vrf)

    # Start
    if start and not running:
        running = 1
        warp_pc    = [0] * NWARP
        warp_state = [0] * NWARP
        warp_done  = [0] * NWARP
        warp_acc   = [0] * NWARP
        barrier_mask = [0] * NWARP

    # Barrier release
    all_at_barrier_or_done = all(
        (barrier_mask[w] or warp_done[w]) for w in range(NWARP)
    )
    if all_at_barrier_or_done and not all(warp_done[w] for w in range(NWARP)):
        for w in range(NWARP):
            barrier_mask[w] = 0
            if warp_state[w] == 6:
                warp_state[w] = 0

    # Per-warp FSM
    w = warp_sel
    if 0 <= w < NWARP:
        st = warp_state[w]
        if st == 0:   # idle
            if running and not warp_done[w] and not barrier_mask[w]:
                warp_state[w] = 1
        elif st == 1: # fetch
            inst_reg = imem[warp_pc[w] % IMEM_DEPTH]
            warp_pc[w] = (warp_pc[w] + 1) % IMEM_DEPTH
            warp_state[w] = 2
        elif st == 2: # decode / execute
            opcode, rd, rs1, rs2, imm = decode_inst(inst_reg)
            if opcode == OP_NOP:
                warp_state[w] = 0
            elif opcode == OP_DONE:
                warp_done[w] = 1
                warp_state[w] = 0xF
            elif opcode in (OP_VLOAD, OP_VSTORE):
                warp_state[w] = 3
            elif opcode == OP_BARRIER:
                barrier_mask[w] = 1
                warp_state[w] = 6
            else:
                warp_state[w] = 4
        elif st == 3: # mem req
            warp_state[w] = 5
        elif st == 5: # mem wait
            if mem_valid and mem_ready:
                opcode, rd, rs1, rs2, imm = decode_inst(inst_reg)
                if opcode == OP_VLOAD:
                    vrf_base = w * VREGS
                    vrf[vrf_base + rd] = mem_rdata
                warp_state[w] = 0
        elif st == 4: # execute ALU
            opcode, rd, rs1, rs2, imm = decode_inst(inst_reg)
            vrf_base = w * VREGS
            if opcode == OP_VADD:
                vrf[vrf_base + rd] = (vrf[vrf_base + rs1] + vrf[vrf_base + rs2]) & ((1 << VLEN) - 1)
            elif opcode == OP_VMUL:
                vrf[vrf_base + rd] = (vrf[vrf_base + rs1] * vrf[vrf_base + rs2]) & ((1 << VLEN) - 1)
            elif opcode == OP_VMAC:
                # lane-0 MAC only for behavioral model simplicity
                a0 = vrf[vrf_base + rs1] & ((1 << XLEN) - 1)
                b0 = vrf[vrf_base + rs2] & ((1 << XLEN) - 1)
                warp_acc[w] = (warp_acc[w] + a0 * b0) & ((1 << ACCW) - 1)
            elif opcode == OP_SLOAD:
                # broadcast sign-extended imm to all 8 lanes
                lane_val = imm & ((1 << XLEN) - 1)
                vec = 0
                for lane in range(NLANE):
                    vec |= lane_val << (lane * XLEN)
                vrf[vrf_base + rd] = vec
            warp_state[w] = 0
        elif st == 0xF: # done
            pass

    # Scheduler: advance when current warp is idle/done/barrier
    warp_idle = [
        (warp_state[i] == 0) or (warp_state[i] == 0xF) or (warp_state[i] == 6)
        for i in range(NWARP)
    ]
    if warp_idle[w]:
        warp_sel = (warp_sel + 1) % NWARP

    # Memory request combinational
    mem_req_val = 0
    mem_wen_val = 0
    mem_addr_val = 0
    mem_wdata_val = 0
    for wcheck in range(NWARP):
        if warp_state[wcheck] == 3:
            _, rd_c, rs1_c, rs2_c, imm_c = decode_inst(inst_reg)
            mem_req_val = 1
            mem_addr_val = imm_c & 0xFFFFFFFF
            mem_wen_val = 1 if ((inst_reg >> 28) & 0xF) == OP_VSTORE else 0
            if mem_wen_val:
                vrf_base = wcheck * VREGS
                mem_wdata_val = vrf[vrf_base + rd_c]

    # Commit state
    ctx.set_state("warp_pc", warp_pc)
    ctx.set_state("warp_state", warp_state)
    ctx.set_state("warp_done", warp_done)
    ctx.set_state("warp_acc", warp_acc)
    ctx.set_state("barrier_mask", barrier_mask)
    ctx.set_state("warp_sel", warp_sel)
    ctx.set_state("inst_reg", inst_reg)
    ctx.set_state("running", running)
    ctx.set_state("vrf", vrf)

    # Outputs
    ctx.set_output("mem_req", mem_req_val)
    ctx.set_output("mem_wen", mem_wen_val)
    ctx.set_output("mem_addr", mem_addr_val)
    ctx.set_output("mem_wdata", mem_wdata_val)
    ctx.set_output("sm_done", all(warp_done))
    ctx.set_output("debug_w0_acc0", warp_acc[0] if warp_acc else 0)


# =====================================================================
# Memory Arbiter behavior
# =====================================================================
def arbiter_behavior(ctx: CycleContext):
    """Round-robin arbiter between 2 SMs."""
    clk   = ctx.get_input("clk", 0)
    rst_n = ctx.get_input("rst_n", 1)
    sm0_req = ctx.get_input("sm0_mem_req", 0)
    sm1_req = ctx.get_input("sm1_mem_req", 0)
    sm0_wen = ctx.get_input("sm0_mem_wen", 0)
    sm1_wen = ctx.get_input("sm1_mem_wen", 0)
    sm0_addr = ctx.get_input("sm0_mem_addr", 0)
    sm1_addr = ctx.get_input("sm1_mem_addr", 0)
    sm0_wdata = ctx.get_input("sm0_mem_wdata", 0)
    sm1_wdata = ctx.get_input("sm1_mem_wdata", 0)
    mem_ready = ctx.get_input("mem_ready", 1)
    mem_rdata = ctx.get_input("mem_rdata", 0)
    mem_valid = ctx.get_input("mem_valid", 0)

    rr_grant = ctx.get_state("rr_grant", 0)

    if rst_n == 0:
        ctx.set_state("rr_grant", 0)
        ctx.set_output("mem_req", 0)
        ctx.set_output("mem_wen", 0)
        ctx.set_output("mem_addr", 0)
        ctx.set_output("mem_wdata", 0)
        ctx.set_output("sm0_mem_valid", 0)
        ctx.set_output("sm1_mem_valid", 0)
        ctx.set_output("sm0_mem_rdata", 0)
        ctx.set_output("sm1_mem_rdata", 0)
        return

    any_req = sm0_req or sm1_req
    if any_req and mem_ready:
        rr_grant = 1 - rr_grant

    if rr_grant == 0:
        req = sm0_req
        wen = sm0_wen
        addr = sm0_addr
        wdata = sm0_wdata
    else:
        req = sm1_req
        wen = sm1_wen
        addr = sm1_addr
        wdata = sm1_wdata

    ctx.set_state("rr_grant", rr_grant)
    ctx.set_output("mem_req", req)
    ctx.set_output("mem_wen", wen)
    ctx.set_output("mem_addr", addr)
    ctx.set_output("mem_wdata", wdata)
    ctx.set_output("sm0_mem_valid", mem_valid if rr_grant == 0 else 0)
    ctx.set_output("sm1_mem_valid", mem_valid if rr_grant == 1 else 0)
    ctx.set_output("sm0_mem_rdata", mem_rdata if rr_grant == 0 else 0)
    ctx.set_output("sm1_mem_rdata", mem_rdata if rr_grant == 1 else 0)


# =====================================================================
# Thor GPGPU ArchDefinition
# =====================================================================
def build_thor_arch() -> ArchDefinition:
    arch = ArchDefinition(
        name="thor_gpu",
        description="Thor-class GPGPU: 2 SMs × 4 warps × 8 lanes",
        isa="simt",
    )

    # --- SM 0 ---
    sm0 = ProcessingElement(
        name="sm_0",
        pe_type="sm_wrapper",
        description="Streaming Multiprocessor 0",
        inputs=[
            PortDesc("clk", "input", 1, "clock"),
            PortDesc("rst_n", "input", 1, "active-low reset"),
            PortDesc("start", "input", 1, "kernel launch"),
            PortDesc("imem_wr_en", "input", 1, "instruction mem write enable"),
            PortDesc("imem_wr_addr", "input", 5, "instruction mem write addr"),
            PortDesc("imem_wr_data", "input", 32, "instruction mem write data"),
            PortDesc("mem_valid", "input", 1, "memory response valid"),
            PortDesc("mem_rdata", "input", VLEN, "memory read data"),
            PortDesc("mem_ready", "input", 1, "memory ready"),
        ],
        outputs=[
            PortDesc("mem_req", "output", 1, "memory request"),
            PortDesc("mem_wen", "output", 1, "memory write enable"),
            PortDesc("mem_addr", "output", 32, "memory address"),
            PortDesc("mem_wdata", "output", VLEN, "memory write data"),
            PortDesc("sm_done", "output", 1, "all warps done"),
            PortDesc("debug_w0_acc0", "output", ACCW, "warp0 accumulator debug"),
        ],
        state=[
            StateDesc("warp_pc", "list", "per-warp PC", [0]*NWARP, "reg", 32, NWARP),
            StateDesc("warp_state", "list", "per-warp FSM state", [0]*NWARP, "reg", 4, NWARP),
            StateDesc("warp_done", "list", "per-warp done flag", [0]*NWARP, "reg", 1, NWARP),
            StateDesc("warp_acc", "list", "per-warp MAC accumulator", [0]*NWARP, "reg", ACCW, NWARP),
            StateDesc("barrier_mask", "list", "per-warp barrier mask", [0]*NWARP, "reg", 1, NWARP),
            StateDesc("warp_sel", "int", "current warp select", 0, "reg", 2),
            StateDesc("inst_reg", "int", "fetched instruction", 0, "reg", 32),
            StateDesc("running", "int", "SM running flag", 0, "reg", 1),
            StateDesc("imem", "list", "instruction memory", [0]*IMEM_DEPTH, "memory", 32, IMEM_DEPTH),
            StateDesc("vrf", "list", "vector register file", [0]*(VREGS*NWARP), "regfile", VLEN, VREGS*NWARP),
        ],
        behavior=sm_behavior,
        latency=0,
        can_stall=False,
    )

    # --- SM 1 ---
    sm1 = ProcessingElement(
        name="sm_1",
        pe_type="sm_wrapper",
        description="Streaming Multiprocessor 1",
        inputs=sm0.inputs,
        outputs=sm0.outputs,
        state=sm0.state,
        behavior=sm_behavior,
        latency=0,
        can_stall=False,
    )

    # --- Memory Arbiter ---
    arb = ProcessingElement(
        name="mem_arbiter",
        pe_type="arbiter",
        description="Round-robin global memory arbiter",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst_n", "input", 1),
            PortDesc("sm0_mem_req", "input", 1),
            PortDesc("sm1_mem_req", "input", 1),
            PortDesc("sm0_mem_wen", "input", 1),
            PortDesc("sm1_mem_wen", "input", 1),
            PortDesc("sm0_mem_addr", "input", 32),
            PortDesc("sm1_mem_addr", "input", 32),
            PortDesc("sm0_mem_wdata", "input", VLEN),
            PortDesc("sm1_mem_wdata", "input", VLEN),
            PortDesc("mem_ready", "input", 1),
            PortDesc("mem_rdata", "input", VLEN),
            PortDesc("mem_valid", "input", 1),
        ],
        outputs=[
            PortDesc("mem_req", "output", 1),
            PortDesc("mem_wen", "output", 1),
            PortDesc("mem_addr", "output", 32),
            PortDesc("mem_wdata", "output", VLEN),
            PortDesc("sm0_mem_valid", "output", 1),
            PortDesc("sm1_mem_valid", "output", 1),
            PortDesc("sm0_mem_rdata", "output", VLEN),
            PortDesc("sm1_mem_rdata", "output", VLEN),
        ],
        state=[
            StateDesc("rr_grant", "int", "round-robin grant", 0, "reg", 1),
        ],
        behavior=arbiter_behavior,
        latency=0,
        can_stall=False,
    )

    arch.add_pe(sm0).add_pe(sm1).add_pe(arb)

    # --- Interconnects (SM → Arbiter) ---
    arch.add_interconnect(InterconnectSpec(
        src_pe="sm_0", dst_pe="mem_arbiter",
        signals=[
            PortDesc("mem_req", "output", 1),
            PortDesc("mem_wen", "output", 1),
            PortDesc("mem_addr", "output", 32),
            PortDesc("mem_wdata", "output", VLEN),
        ],
        flow_type="stream", delay_cycles=0,
    ))
    arch.add_interconnect(InterconnectSpec(
        src_pe="sm_1", dst_pe="mem_arbiter",
        signals=[
            PortDesc("mem_req", "output", 1),
            PortDesc("mem_wen", "output", 1),
            PortDesc("mem_addr", "output", 32),
            PortDesc("mem_wdata", "output", VLEN),
        ],
        flow_type="stream", delay_cycles=0,
    ))
    # Arbiter → SM responses
    arch.add_interconnect(InterconnectSpec(
        src_pe="mem_arbiter", dst_pe="sm_0",
        signals=[
            PortDesc("mem_valid", "output", 1),
            PortDesc("mem_rdata", "output", VLEN),
        ],
        flow_type="stream", delay_cycles=0,
    ))
    arch.add_interconnect(InterconnectSpec(
        src_pe="mem_arbiter", dst_pe="sm_1",
        signals=[
            PortDesc("mem_valid", "output", 1),
            PortDesc("mem_rdata", "output", VLEN),
        ],
        flow_type="stream", delay_cycles=0,
    ))

    return arch


class ThorSM(Module):
    """Complete DSL implementation of a Thor-class Streaming Multiprocessor."""

    def __init__(self, name="thor_sm"):
        super().__init__(name)

        # Ports (match skeleton)
        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.imem_wr_en   = Input(1, "imem_wr_en")
        self.imem_wr_addr = Input(5, "imem_wr_addr")
        self.imem_wr_data = Input(32, "imem_wr_data")

        self.mem_req   = Output(1, "mem_req")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.sm_done = Output(1, "sm_done")
        self.debug_w0_acc0 = Output(ACCW, "debug_w0_acc0")

        # State (match skeleton)
        self.warp_pc    = Array(32, NWARP, "warp_pc")
        self.warp_state = Array(4, NWARP, "warp_state")
        self.warp_done  = Array(1, NWARP, "warp_done")
        self.warp_acc   = Array(ACCW, NWARP, "warp_acc")
        self.barrier_mask = Array(1, NWARP, "barrier_mask")
        self.imem = Array(32, IMEM_DEPTH, "imem")
        self.vrf  = Array(VLEN, VREGS * NWARP, "vrf")

        self.warp_sel = Reg(2, "warp_sel")
        self.inst_reg = Reg(32, "inst_reg")
        self.running  = Reg(1, "running")

        # Instruction decode
        opcode = Wire(4, "opcode")
        rd     = Wire(4, "rd")
        rs1    = Wire(4, "rs1")
        rs2    = Wire(4, "rs2")
        imm    = Wire(16, "imm")

        with self.comb:
            opcode <<= self.inst_reg[31:28]
            rd     <<= self.inst_reg[27:24]
            rs1    <<= self.inst_reg[23:20]
            rs2    <<= self.inst_reg[19:16]
            imm    <<= self.inst_reg[15:0]

        # VRF indexing
        vrf_base = Wire(5, "vrf_base")
        vrf_rs1  = Wire(5, "vrf_rs1")
        vrf_rs2  = Wire(5, "vrf_rs2")
        vrf_rd   = Wire(5, "vrf_rd")

        with self.comb:
            vrf_base <<= self.warp_sel * Const(VREGS, 4)
            vrf_rs1  <<= vrf_base + rs1
            vrf_rs2  <<= vrf_base + rs2
            vrf_rd   <<= vrf_base + rd

        # Outputs
        with self.comb:
            self.sm_done <<= (self.warp_done[0] & self.warp_done[1] &
                              self.warp_done[2] & self.warp_done[3])
            self.debug_w0_acc0 <<= self.warp_acc[0]

        # Scheduler combinational
        next_warp = Wire(2, "next_warp")
        with self.comb:
            next_warp <<= self.warp_sel + 1

        # Warp idle tracking using Array (for ForGen compatibility)
        self.warp_idle_arr = Array(1, NWARP, "warp_idle_arr")
        current_warp_idle = Wire(1, "current_warp_idle")

        with self.comb:
            with ForGen('w', 0, NWARP) as w:
                self.warp_idle_arr[w] <<= ((self.warp_state[w] == 0) |
                                           (self.warp_state[w] == Const(0xF, 4)) |
                                           (self.warp_state[w] == 6))
            current_warp_idle <<= self.warp_idle_arr[self.warp_sel]

        all_at_barrier_or_done = Wire(1, "all_at_barrier_or_done")
        with self.comb:
            all_at_barrier_or_done <<= (
                (self.barrier_mask[0] | self.warp_done[0]) &
                (self.barrier_mask[1] | self.warp_done[1]) &
                (self.barrier_mask[2] | self.warp_done[2]) &
                (self.barrier_mask[3] | self.warp_done[3])
            )

        # Sequential logic
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.warp_sel <<= 0
                self.inst_reg <<= 0
                self.running  <<= 0
                with ForGen('w', 0, NWARP) as w:
                    self.warp_pc[w]    <<= 0
                    self.warp_state[w] <<= 0
                    self.warp_done[w]  <<= 0
                    self.warp_acc[w]   <<= 0
                    self.barrier_mask[w] <<= 0
            with Else():
                with If(self.imem_wr_en):
                    self.imem[self.imem_wr_addr] <<= self.imem_wr_data

                with If(self.start & ~self.running):
                    self.running <<= 1
                    with ForGen('w', 0, NWARP) as w:
                        self.warp_pc[w]    <<= 0
                        self.warp_state[w] <<= 0
                        self.warp_done[w]  <<= 0
                        self.warp_acc[w]   <<= 0
                        self.barrier_mask[w] <<= 0

                with If(all_at_barrier_or_done):
                    with ForGen('w', 0, NWARP) as w:
                        self.barrier_mask[w] <<= 0
                        with If(self.warp_state[w] == 6):
                            self.warp_state[w] <<= 0

                with ForGen('w', 0, NWARP) as w:
                    with If(self.warp_sel == w):
                        with Switch(self.warp_state[w]) as sw:
                            with sw.case(0):
                                with If(self.running & ~self.warp_done[w] & ~self.barrier_mask[w]):
                                    self.warp_state[w] <<= 1
                            with sw.case(1):
                                self.inst_reg <<= self.imem[self.warp_pc[w]]
                                self.warp_pc[w] <<= self.warp_pc[w] + 1
                                self.warp_state[w] <<= 2
                            with sw.case(2):
                                with If(opcode == OP_NOP):
                                    self.warp_state[w] <<= 0
                                with Elif(opcode == OP_DONE):
                                    self.warp_done[w] <<= 1
                                    self.warp_state[w] <<= Const(0xF, 4)
                                with Elif((opcode == OP_VLOAD) | (opcode == OP_VSTORE)):
                                    self.warp_state[w] <<= 3
                                with Elif(opcode == OP_BARRIER):
                                    self.barrier_mask[w] <<= 1
                                    self.warp_state[w] <<= 6
                                with Else():
                                    self.warp_state[w] <<= 4
                            with sw.case(3):
                                self.warp_state[w] <<= 5
                            with sw.case(5):
                                with If(self.mem_valid & self.mem_ready):
                                    with If(opcode == OP_VLOAD):
                                        self.vrf[vrf_rd] <<= self.mem_rdata
                                    self.warp_state[w] <<= 0
                                with Else():
                                    self.warp_state[w] <<= 5
                            with sw.case(4):
                                with If(opcode == OP_VADD):
                                    self.vrf[vrf_rd] <<= self.vrf[vrf_rs1] + self.vrf[vrf_rs2]
                                with If(opcode == OP_VMUL):
                                    self.vrf[vrf_rd] <<= self.vrf[vrf_rs1] * self.vrf[vrf_rs2]
                                with If(opcode == OP_VMAC):
                                    self.warp_acc[w] <<= self.warp_acc[w] + (
                                        self.vrf[vrf_rs1][1*XLEN-1:0*XLEN] *
                                        self.vrf[vrf_rs2][1*XLEN-1:0*XLEN]
                                    )
                                with If(opcode == OP_SLOAD):
                                    lane_val = Cat(Rep(imm[15], XLEN-16), imm)
                                    vec = Cat(*[lane_val for _ in range(NLANE)])
                                    self.vrf[vrf_rd] <<= vec
                                self.warp_state[w] <<= 0
                            with sw.case(Const(0xF, 4)):
                                self.warp_state[w] <<= Const(0xF, 4)

                with If(current_warp_idle):
                    self.warp_sel <<= next_warp

        # Memory interface combinational
        mem_req_c   = Wire(1, "mem_req_c")
        mem_wen_c   = Wire(1, "mem_wen_c")
        mem_addr_c  = Wire(32, "mem_addr_c")
        mem_wdata_c = Wire(VLEN, "mem_wdata_c")

        with self.comb:
            mem_req_c   <<= 0
            mem_wen_c   <<= 0
            mem_addr_c  <<= 0
            mem_wdata_c <<= 0
            with ForGen('w', 0, NWARP) as w:
                with If(self.warp_state[w] == 3):
                    mem_req_c <<= 1
                    mem_addr_c <<= Cat(Const(0, 16), imm)
                    mem_wen_c <<= (opcode == OP_VSTORE)
                    with If(opcode == OP_VSTORE):
                        mem_wdata_c <<= self.vrf[vrf_rd]
            self.mem_req   <<= mem_req_c
            self.mem_wen    <<= mem_wen_c
            self.mem_addr   <<= mem_addr_c
            self.mem_wdata  <<= mem_wdata_c


class ThorTop(Module):
    """Complete DSL implementation of Thor GPGPU top-level."""

    def __init__(self):
        super().__init__("thor_gpu_top")

        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.sm0_imem_wr_en   = Input(1, "sm0_imem_wr_en")
        self.sm0_imem_wr_addr = Input(5, "sm0_imem_wr_addr")
        self.sm0_imem_wr_data = Input(32, "sm0_imem_wr_data")
        self.sm1_imem_wr_en   = Input(1, "sm1_imem_wr_en")
        self.sm1_imem_wr_addr = Input(5, "sm1_imem_wr_addr")
        self.sm1_imem_wr_data = Input(32, "sm1_imem_wr_data")

        self.mem_req   = Output(1, "mem_req")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.all_done = Output(1, "all_done")
        self.sm0_w0_acc0 = Output(ACCW, "sm0_w0_acc0")
        self.sm1_w0_acc0 = Output(ACCW, "sm1_w0_acc0")

        sms = [ThorSM(f"sm_{i}") for i in range(NSM)]

        sm_mem_req   = [Wire(1, f"sm{i}_mem_req")   for i in range(NSM)]
        sm_mem_wen   = [Wire(1, f"sm{i}_mem_wen")   for i in range(NSM)]
        sm_mem_addr  = [Wire(32, f"sm{i}_mem_addr")  for i in range(NSM)]
        sm_mem_wdata = [Wire(VLEN, f"sm{i}_mem_wdata") for i in range(NSM)]
        sm_mem_rdata = [Wire(VLEN, f"sm{i}_mem_rdata") for i in range(NSM)]
        sm_mem_valid = [Wire(1, f"sm{i}_mem_valid") for i in range(NSM)]

        sm0_done = Wire(1, "sm0_done")
        sm1_done = Wire(1, "sm1_done")

        self.rr_grant = Reg(1, "rr_grant")
        any_req = Wire(1, "any_req")

        with self.comb:
            any_req <<= sm_mem_req[0] | sm_mem_req[1]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.rr_grant <<= 0
            with Else():
                with If(any_req & self.mem_ready):
                    self.rr_grant <<= self.rr_grant + 1

        with self.comb:
            self.mem_req   <<= Mux(self.rr_grant == 0, sm_mem_req[0],   sm_mem_req[1])
            self.mem_wen   <<= Mux(self.rr_grant == 0, sm_mem_wen[0],   sm_mem_wen[1])
            self.mem_addr  <<= Mux(self.rr_grant == 0, sm_mem_addr[0],  sm_mem_addr[1])
            self.mem_wdata <<= Mux(self.rr_grant == 0, sm_mem_wdata[0], sm_mem_wdata[1])

        for i in range(NSM):
            with self.comb:
                sm_mem_valid[i] <<= self.mem_valid & (self.rr_grant == i)
                sm_mem_rdata[i] <<= self.mem_rdata

        imem_ports = [
            (self.sm0_imem_wr_en, self.sm0_imem_wr_addr, self.sm0_imem_wr_data),
            (self.sm1_imem_wr_en, self.sm1_imem_wr_addr, self.sm1_imem_wr_data),
        ]
        done_ports = [sm0_done, sm1_done]
        debug_ports = [self.sm0_w0_acc0, self.sm1_w0_acc0]

        for i in range(NSM):
            self.instantiate(sms[i], f"sm_{i}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "start": self.start,
                "imem_wr_en":   imem_ports[i][0],
                "imem_wr_addr": imem_ports[i][1],
                "imem_wr_data": imem_ports[i][2],
                "mem_req":   sm_mem_req[i],
                "mem_wen":   sm_mem_wen[i],
                "mem_addr":  sm_mem_addr[i],
                "mem_wdata": sm_mem_wdata[i],
                "mem_valid": sm_mem_valid[i],
                "mem_rdata": sm_mem_rdata[i],
                "mem_ready": self.mem_ready,
                "sm_done": done_ports[i],
                "debug_w0_acc0": debug_ports[i],
            })

        with self.comb:
            self.all_done <<= sm0_done & sm1_done


print("ThorSM and ThorTop DSL modules defined.")


_TESTBENCH_SOURCE = """
`timescale 1ns / 1ps

module thor_gpu_top_tb;
    reg clk = 0;
    reg rst_n = 0;
    reg start = 0;
    reg sm0_imem_wr_en = 0;
    reg [4:0] sm0_imem_wr_addr = 0;
    reg [31:0] sm0_imem_wr_data = 0;
    reg sm1_imem_wr_en = 0;
    reg [4:0] sm1_imem_wr_addr = 0;
    reg [31:0] sm1_imem_wr_data = 0;
    wire mem_req;
    wire mem_wen;
    wire [31:0] mem_addr;
    wire [255:0] mem_wdata;
    reg mem_valid = 0;
    reg [255:0] mem_rdata = 0;
    reg mem_ready = 1;
    wire all_done;
    wire [63:0] sm0_w0_acc0;
    wire [63:0] sm1_w0_acc0;

    ThorTop dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .sm0_imem_wr_en(sm0_imem_wr_en),
        .sm0_imem_wr_addr(sm0_imem_wr_addr),
        .sm0_imem_wr_data(sm0_imem_wr_data),
        .sm1_imem_wr_en(sm1_imem_wr_en),
        .sm1_imem_wr_addr(sm1_imem_wr_addr),
        .sm1_imem_wr_data(sm1_imem_wr_data),
        .mem_req(mem_req), .mem_wen(mem_wen), .mem_addr(mem_addr),
        .mem_wdata(mem_wdata), .mem_valid(mem_valid),
        .mem_rdata(mem_rdata), .mem_ready(mem_ready),
        .all_done(all_done), .sm0_w0_acc0(sm0_w0_acc0), .sm1_w0_acc0(sm1_w0_acc0)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (mem_req && mem_ready) begin
            mem_valid <= 1;
            if (!mem_wen)
                mem_rdata <= {32'h1,32'h2,32'h3,32'h4,32'h5,32'h6,32'h7,32'h8};
        end else
            mem_valid <= 0;
    end

    function [31:0] inst_sload(input [3:0] rd, input [15:0] imm);
        inst_sload = {4'h7, rd, 4'h0, 4'h0, imm};
    endfunction
    function [31:0] inst_vadd(input [3:0] rd, input [3:0] rs1, input [3:0] rs2);
        inst_vadd = {4'h3, rd, rs1, rs2, 16'h0};
    endfunction
    function [31:0] inst_vmul(input [3:0] rd, input [3:0] rs1, input [3:0] rs2);
        inst_vmul = {4'h4, rd, rs1, rs2, 16'h0};
    endfunction
    function [31:0] inst_vmac(input [3:0] rd, input [3:0] rs1, input [3:0] rs2);
        inst_vmac = {4'h5, rd, rs1, rs2, 16'h0};
    endfunction
    function [31:0] inst_barrier; inst_barrier = {4'h6, 12'h0, 16'h0}; endfunction
    function [31:0] inst_done;    inst_done    = {4'hF, 12'h0, 16'h0}; endfunction

    task load_sm_inst(input sel, input [4:0] addr, input [31:0] data);
        begin
            @(posedge clk);
            if (sel == 0) begin
                sm0_imem_wr_en <= 1; sm0_imem_wr_addr <= addr; sm0_imem_wr_data <= data;
            end else begin
                sm1_imem_wr_en <= 1; sm1_imem_wr_addr <= addr; sm1_imem_wr_data <= data;
            end
            @(posedge clk);
            sm0_imem_wr_en <= 0; sm1_imem_wr_en <= 0;
        end
    endtask

    integer cycle;
    initial begin
        $display("=== Thor GPGPU Top Testbench ===");
        rst_n = 0; repeat(3) @(posedge clk);
        rst_n = 1; @(posedge clk);

        load_sm_inst(0, 0, inst_sload(4'd0, 16'd5));
        load_sm_inst(0, 1, inst_sload(4'd1, 16'd3));
        load_sm_inst(0, 2, inst_vadd(4'd2, 4'd0, 4'd1));
        load_sm_inst(0, 3, inst_vmul(4'd3, 4'd0, 4'd1));
        load_sm_inst(0, 4, inst_vmac(4'd4, 4'd0, 4'd1));
        load_sm_inst(0, 5, inst_barrier());
        load_sm_inst(0, 6, inst_sload(4'd0, 16'd7));
        load_sm_inst(0, 7, inst_sload(4'd1, 16'd2));
        load_sm_inst(0, 8, inst_vmac(4'd4, 4'd0, 4'd1));
        load_sm_inst(0, 9, inst_done());
        load_sm_inst(1, 0, inst_done());

        @(posedge clk); start <= 1; @(posedge clk); start <= 0;

        for (cycle = 0; cycle < 200; cycle = cycle + 1) begin
            @(posedge clk); #1;
            if (all_done) begin
                $display("Cycle %0d: all_done asserted!", cycle);
                $display("sm0_w0_acc0 = %0d (expected 29)", sm0_w0_acc0);
                if (sm0_w0_acc0 == 29)
                    $display("PASS: accumulator value correct");
                else
                    $display("FAIL: accumulator expected 29, got %0d", sm0_w0_acc0);
                $display("=== TEST COMPLETE ===");
                $finish;
            end
        end
        $display("TIMEOUT");
        $finish;
    end
endmodule
"""

if __name__ == "__main__":
    print("=" * 60)
    print("Thor GPGPU — Spec-to-RTL Flow Demonstration")
    print("=" * 60)

    # -----------------------------------------------------------------
    # Step 1: ArchDefinition
    # -----------------------------------------------------------------
    print("\n[Step 1] Building ArchDefinition...")
    arch = build_thor_arch()
    print(f"  Architecture: {arch.name}")
    print(f"  PEs: {[pe.name for pe in arch.processing_elements]}")
    print(f"  Interconnects: {len(arch.interconnects)}")

    # -----------------------------------------------------------------
    # Step 2: ArchSimulator (behavioral reference + golden vectors)
    # -----------------------------------------------------------------
    print("\n[Step 2] Running ArchSimulator with workload...")
    sim = ArchSimulator(arch)

    # Run reset cycle
    sim.run(num_cycles=3, init_inputs={"rst_n": 0, "clk": 0})

    # Load program into SM0 imem (cycle-accurate stimulus)
    sm0_prog = [
        (0, 0x70000005),  # SLOAD v0, 5
        (1, 0x71000003),  # SLOAD v1, 3
        (2, 0x32010000),  # VADD v2, v0, v1
        (3, 0x43010000),  # VMUL v3, v0, v1
        (4, 0x54010000),  # VMAC v4, v0, v1
        (5, 0x60000000),  # BARRIER
        (6, 0x70000007),  # SLOAD v0, 7
        (7, 0x71000002),  # SLOAD v1, 2
        (8, 0x54010000),  # VMAC v4, v0, v1
        (9, 0xF0000000),  # DONE
    ]
    for addr, data in sm0_prog:
        sim.run(num_cycles=1, init_inputs={
            "rst_n": 1, "mem_ready": 1,
            "sm_0.imem_wr_en": 1, "sm_0.imem_wr_addr": addr, "sm_0.imem_wr_data": data,
        })
    # Load SM1 simple program (DONE)
    sim.run(num_cycles=1, init_inputs={
        "rst_n": 1, "mem_ready": 1,
        "sm_1.imem_wr_en": 1, "sm_1.imem_wr_addr": 0, "sm_1.imem_wr_data": 0xF0000000,
    })

    # Start kernel
    sim.run(num_cycles=2, init_inputs={"rst_n": 1, "start": 1, "mem_ready": 1})

    # Run until completion or timeout
    for cycle in range(200):
        outputs = sim.step()
        done = sim._signals.get("sm_0.sm_done", 0) & sim._signals.get("sm_1.sm_done", 0)
        if done:
            acc0 = sim._signals.get("sm_0.debug_w0_acc0", 0)
            print(f"  Behavioral sim DONE at cycle {cycle}")
            print(f"  sm_0 debug_w0_acc0 = {acc0} (expected 29)")
            break
    else:
        print("  Behavioral sim TIMEOUT")

    report = sim._build_report()
    print(f"  Cycles: {report['total_cycles']}, IPC: {report['ipc']}, Retired: {report['total_retired']}")

    # -----------------------------------------------------------------
    # Step 3: ArchSkeletonGenerator
    # -----------------------------------------------------------------
    print("\n[Step 3] Generating DSL skeletons...")
    gen = ArchSkeletonGenerator()
    packages = gen.generate_all(arch)
    for name, pkg in packages.items():
        print(f"  {name}: pe_type={pkg.pe.pe_type}, golden_tests={len(pkg.golden_tests)}")

    # -----------------------------------------------------------------
    # Step 4: DSL implementation (ThorSM, ThorTop)
    # -----------------------------------------------------------------
    print("\n[Step 4] DSL modules already implemented in this file.")
    print("  - ThorSM: Streaming Multiprocessor")
    print("  - ThorTop: 2-SM top with round-robin arbiter")

    # -----------------------------------------------------------------
    # Step 5: Verilog emission
    # -----------------------------------------------------------------
    print("\n[Step 5] Emitting Verilog...")
    import os
    out_dir = "/tmp/skill_test/thor_gpu"
    os.makedirs(out_dir, exist_ok=True)

    from rtlgen.codegen import VerilogEmitter
    sm = ThorSM("thor_sm")
    top = ThorTop()
    emitter = VerilogEmitter(disable_cse=True)
    with open(f"{out_dir}/thor_sm.v", "w") as f:
        f.write(emitter.emit(sm))
    with open(f"{out_dir}/thor_gpu_top.v", "w") as f:
        f.write(emitter.emit(top))
    print(f"  Written to {out_dir}/thor_sm.v")
    print(f"  Written to {out_dir}/thor_gpu_top.v")

    # -----------------------------------------------------------------
    # Step 6: Functional verification (Python Simulator)
    # -----------------------------------------------------------------
    print("\n[Step 6] Running functional verification with Python Simulator...")
    from rtlgen.sim import Simulator

    top_sim = Simulator(top)
    top_sim.reset("rst_n", cycles=3)

    # Load SM0 program
    sm0_prog = [
        (0, 0x70000005), (1, 0x71000003), (2, 0x32010000), (3, 0x43010000),
        (4, 0x54010000), (5, 0x60000000), (6, 0x70000007), (7, 0x71000002),
        (8, 0x54010000), (9, 0xF0000000),
    ]
    for addr, data in sm0_prog:
        top_sim.set("sm0_imem_wr_en", 1)
        top_sim.set("sm0_imem_wr_addr", addr)
        top_sim.set("sm0_imem_wr_data", data)
        top_sim.step()
        top_sim.set("sm0_imem_wr_en", 0)
        top_sim.step()

    # Load SM1 program (DONE)
    top_sim.set("sm1_imem_wr_en", 1)
    top_sim.set("sm1_imem_wr_addr", 0)
    top_sim.set("sm1_imem_wr_data", 0xF0000000)
    top_sim.step()
    top_sim.set("sm1_imem_wr_en", 0)
    top_sim.step()

    # Start
    top_sim.set("start", 1)
    top_sim.step()
    top_sim.set("start", 0)

    # Run with memory model
    for cycle in range(200):
        top_sim.set("mem_valid", 0)
        top_sim.set("mem_rdata", 0)
        top_sim.set("mem_ready", 1)
        if top_sim.state["mem_req"] and not top_sim.state["mem_wen"]:
            top_sim.set("mem_valid", 1)
            top_sim.set("mem_rdata", 0x0102030405060708)
        top_sim.step()
        if top_sim.state["all_done"]:
            print(f"  Cycle {cycle}: all_done asserted!")
            print(f"  sm0_w0_acc0 = {top_sim.state['sm0_w0_acc0']} (expected 29)")
            if top_sim.state["sm0_w0_acc0"] == 29:
                print("  => VERIFICATION PASSED")
            else:
                print("  => VERIFICATION FAILED")
            break
    else:
        print("  TIMEOUT")
        print(f"  all_done={top_sim.state['all_done']} sm0_w0_acc0={top_sim.state['sm0_w0_acc0']}")

