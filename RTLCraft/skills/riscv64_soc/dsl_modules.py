"""
skills.riscv64_soc — 64-Core RISC-V SoC DSL Modules

Architecture:
  64 clusters × (RV64Core + L1Cache + CoherenceDir + L2CacheSlice + NoCRouter)
  in an 8×8 mesh with directory-based MSI cache coherence.

Components:
  - RV64Core: 5-stage RV64I pipeline (F/D/E/M/W)
  - L1Cache: parameterizable I/D cache with tag match, LRU
  - CoherenceDir: MSI directory with sharers bitmask
  - L2CacheSlice: sliced L2 cache bank
  - NoCRouter: 5-port router with input buffers, crossbar, XY routing
  - ClusterTop: per-cluster wrapper
  - MeshTop: 8×8 mesh instantiation
"""

from __future__ import annotations
import os, sys
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, HandshakeSpec, QueueSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const, Mux,
    ForGenNode, GenVar,
)
from rtlgen import Cat
from rtlgen.logic import If, Else, Elif, Switch, ForGen, Cat, Rep, Const, Mux, SRA
from rtlgen.codegen import VerilogEmitter, EmitProfile

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

# ============================================================================
# Global Parameters
# ============================================================================
XLEN = 64
FETCH_WIDTH = 4
ROB_DEPTH = 128
L1_SIZE_KB = 32
L1_WAYS = 8
L1_LINE_SIZE = 64
L2_SLICE_KB = 4
L2_WAYS = 8
FLIT_WIDTH = 64
BUFFER_DEPTH = 4
NUM_VC = 3
DIR_ENTRIES = 64
DIR_WAYS = 4
MESH_X = 8
MESH_Y = 8
NUM_CORES = 64

# RV64 opcodes (RISC-V RV64I subset)
OPC_LOAD    = Const(0x03, 7)
OPC_STORE   = Const(0x23, 7)
OPC_BRANCH  = Const(0x63, 7)
OPC_JALR    = Const(0x67, 7)
OPC_JAL     = Const(0x6F, 7)
OPC_AUIPC   = Const(0x17, 7)
OPC_LUI     = Const(0x37, 7)
OPC_OP_IMM  = Const(0x13, 7)
OPC_OP      = Const(0x33, 7)
OPC_SYSTEM  = Const(0x73, 7)

FUNCT3_ADD  = Const(0x0, 3)
FUNCT3_SUB  = Const(0x0, 3)
FUNCT3_SLL  = Const(0x1, 3)
FUNCT3_SLT  = Const(0x2, 3)
FUNCT3_SLTU = Const(0x3, 3)
FUNCT3_XOR  = Const(0x4, 3)
FUNCT3_SRL  = Const(0x5, 3)
FUNCT3_SRA  = Const(0x5, 3)
FUNCT3_OR   = Const(0x6, 3)
FUNCT3_AND  = Const(0x7, 3)

# Coherence states
STATE_I = 0  # Invalid
STATE_S = 1  # Shared
STATE_M = 2  # Modified

# ============================================================================
# RV64 Core — 5-stage pipeline
# ============================================================================

class RV64Core(Module):
    """5-stage RISC-V RV64I pipeline.

    Stages: Fetch → Decode → Execute → Memory → Writeback
    Supports: R-type, I-type, load, store, branch (BEQ), JAL, LUI
    """

    def __init__(self):
        super().__init__("rv64_core")

        # Ports
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # L1 I-Cache interface
        self.icache_req = Output(1, "icache_req")
        self.icache_addr = Output(XLEN, "icache_addr")
        self.icache_rdata = Input(XLEN, "icache_rdata")
        self.icache_valid = Input(1, "icache_valid")
        self.icache_ready = Output(1, "icache_ready")
        # L1 D-Cache interface
        self.dcache_req = Output(1, "dcache_req")
        self.dcache_addr = Output(XLEN, "dcache_addr")
        self.dcache_wdata = Output(XLEN, "dcache_wdata")
        self.dcache_wen = Output(1, "dcache_wen")
        self.dcache_rdata = Input(XLEN, "dcache_rdata")
        self.dcache_valid = Input(1, "dcache_valid")
        self.dcache_ready = Output(1, "dcache_ready")
        # Status
        self.core_stall = Output(1, "core_stall")
        self.core_halted = Output(1, "core_halted")
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")

        # Pipeline registers
        # F stage
        pc_reg = Reg(XLEN, "pc")
        pc_next = Wire(XLEN, "pc_next")
        fetch_valid = Reg(1, "fetch_valid")
        fetch_instr = Reg(32, "fetch_instr")
        fetch_pc = Reg(XLEN, "fetch_pc")

        # D stage
        decode_valid = Reg(1, "decode_valid")
        decode_instr = Reg(32, "decode_instr")
        decode_pc = Reg(XLEN, "decode_pc")

        # E stage
        exec_valid = Reg(1, "exec_valid")
        exec_instr = Reg(32, "exec_instr")
        exec_pc = Reg(XLEN, "exec_pc")
        exec_alu_result = Reg(XLEN, "exec_alu_result")
        exec_branch_taken = Reg(1, "exec_branch_taken")
        exec_branch_target = Reg(XLEN, "exec_branch_target")
        exec_mem_read = Reg(1, "exec_mem_read")
        exec_mem_write = Reg(1, "exec_mem_write")
        exec_wb_en = Reg(1, "exec_wb_en")
        exec_rd = Reg(5, "exec_rd")

        # M stage
        mem_valid = Reg(1, "mem_valid")
        mem_alu_result = Reg(XLEN, "mem_alu_result")
        mem_wb_en = Reg(1, "mem_wb_en")
        mem_rd = Reg(5, "mem_rd")
        mem_load_data = Reg(XLEN, "mem_load_data")
        mem_is_load = Reg(1, "mem_is_load")

        # W stage
        wb_valid = Reg(1, "wb_valid")
        wb_result = Reg(XLEN, "wb_result")
        wb_wb_en = Reg(1, "wb_wb_en")
        wb_rd = Reg(5, "wb_rd")

        # Register file
        rf = Array(XLEN, 32, "regfile")
        # Forwarded values
        wb_fwd_valid = Wire(1, "wb_fwd_valid")
        wb_fwd_result = Wire(XLEN, "wb_fwd_result")
        wb_fwd_rd = Wire(5, "wb_fwd_rd")

        # Stalls
        icache_stall = Wire(1, "icache_stall")
        dcache_stall = Wire(1, "dcache_stall")
        branch_redirect = Wire(1, "branch_redirect")

        # ── PC reset and update ──
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                pc_reg <<= Const(0x1000, XLEN)  # boot ROM
                fetch_valid <<= 0
                fetch_instr <<= 0
                decode_valid <<= 0
                exec_valid <<= 0
                mem_valid <<= 0
                wb_valid <<= 0
            with Else():
                # PC update
                with If(branch_redirect == 1):
                    pc_reg <<= exec_branch_target
                with Else():
                    with If(icache_stall == 0):
                        pc_reg <<= pc_next

                # Fetch stage
                with If(icache_stall == 0):
                    with If(branch_redirect == 1):
                        fetch_valid <<= 0
                    with Else():
                        with If(self.icache_valid == 1):
                            fetch_valid <<= 1
                            fetch_instr <<= self.icache_rdata[31:0]
                            fetch_pc <<= pc_reg
                        with Else():
                            fetch_valid <<= fetch_valid

                # Decode → Execute pipeline
                with If(exec_valid == 0 and decode_valid == 1):
                    exec_valid <<= 1
                    exec_instr <<= decode_instr
                    exec_pc <<= decode_pc
                with Else():
                    exec_valid <<= 0

                # Execute → Memory pipeline
                with If(mem_valid == 0 and exec_valid == 1 and dcache_stall == 0):
                    mem_valid <<= 1
                    mem_alu_result <<= exec_alu_result
                    mem_wb_en <<= exec_wb_en
                    mem_rd <<= exec_rd
                    mem_is_load <<= exec_mem_read
                with Else():
                    mem_valid <<= 0

                # Memory → Writeback pipeline
                with If(wb_valid == 0 and mem_valid == 1):
                    wb_valid <<= 1
                    wb_result <<= Mux(mem_is_load, mem_load_data, mem_alu_result)
                    wb_wb_en <<= mem_wb_en
                    wb_rd <<= mem_rd
                with Else():
                    wb_valid <<= 0

                # Decode register
                with If(decode_valid == 0 and fetch_valid == 1):
                    decode_valid <<= 1
                    decode_instr <<= fetch_instr
                    decode_pc <<= fetch_pc
                with Else():
                    decode_valid <<= 0

                # Register file write
                with If(wb_valid == 1 and wb_wb_en == 1 and wb_rd != 0):
                    rf[wb_rd] <<= wb_result

        # ── Combinational logic ──
        with self.comb:
            # PC next
            pc_next <<= pc_reg + 4

            # I-cache request
            self.icache_req <<= ~fetch_valid
            self.icache_addr <<= pc_reg
            self.icache_ready <<= 1
            icache_stall <<= fetch_valid & ~self.icache_valid

            # ── Decode ──
            instr = decode_instr
            opcode = Wire(7, "dec_opcode")
            funct3 = Wire(3, "dec_funct3")
            funct7 = Wire(7, "dec_funct7")
            rs1 = Wire(5, "dec_rs1")
            rs2 = Wire(5, "dec_rs2")
            rd_d = Wire(5, "dec_rd")
            imm_i = Wire(XLEN, "dec_imm_i")
            imm_s = Wire(XLEN, "dec_imm_s")
            imm_b = Wire(XLEN, "dec_imm_b")
            imm_u = Wire(XLEN, "dec_imm_u")
            imm_j = Wire(XLEN, "dec_imm_j")

            opcode <<= instr[6:0]
            funct3 <<= instr[14:12]
            funct7 <<= instr[31:25]
            rs1 <<= instr[19:15]
            rs2 <<= instr[24:20]
            rd_d <<= instr[11:7]
            # I-type: sign-extend instr[31] to fill upper bits
            imm_i <<= Cat(Rep(instr[31], XLEN - 12), instr[11:0])
            imm_s <<= Cat(instr[31:25], instr[11:7], Const(0, XLEN - 12))
            imm_b <<= Cat(instr[31], instr[7], instr[30:25], instr[11:8], Const(0, 1), Const(0, XLEN - 13))
            imm_u <<= Cat(instr[31:12], Const(0, 12))
            imm_j <<= Cat(instr[31], instr[19:12], instr[20], instr[30:21], Const(0, 1), Const(0, XLEN - 21))

            # Register read
            ra = Wire(XLEN, "dec_ra")
            rb = Wire(XLEN, "dec_rb")
            # Forwarding: check if wb stage writes rs1/rs2
            wb_fwd_valid <<= wb_valid & wb_wb_en
            wb_fwd_result <<= wb_result
            wb_fwd_rd <<= wb_rd
            ra <<= Mux(rs1 == wb_fwd_rd, wb_fwd_result, rf[rs1])
            rb <<= Mux(rs2 == wb_fwd_rd, wb_fwd_result, rf[rs2])

            # ── Execute ──
            alu_result = Wire(XLEN, "exec_result")
            branch_taken_w = Wire(1, "branch_taken")
            branch_target_w = Wire(XLEN, "branch_target")
            mem_read_w = Wire(1, "mem_read")
            mem_write_w = Wire(1, "mem_write")
            wb_en_w = Wire(1, "wb_en")

            # ALU operations
            is_add = (funct3 == FUNCT3_ADD) & (opcode == OPC_OP_IMM)
            is_addw = (funct3 == FUNCT3_ADD) & (opcode == OPC_OP) & (funct7 == 0)
            is_sub = (funct3 == FUNCT3_SUB) & (opcode == OPC_OP) & (funct7 == Const(0x20, 7))
            is_xor = (funct3 == FUNCT3_XOR) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_or = (funct3 == FUNCT3_OR) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_and = (funct3 == FUNCT3_AND) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_sll = (funct3 == FUNCT3_SLL) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_srl = (funct3 == FUNCT3_SRL) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM)) & (funct7 == 0)
            is_sra = (funct3 == FUNCT3_SRA) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM)) & (funct7 == Const(0x20, 7))
            is_slt = (funct3 == FUNCT3_SLT) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_sltu = (funct3 == FUNCT3_SLTU) & ((opcode == OPC_OP) | (opcode == OPC_OP_IMM))
            is_lui = (opcode == OPC_LUI)
            is_auipc = (opcode == OPC_AUIPC)
            is_jal = (opcode == OPC_JAL)
            is_jalr = (opcode == OPC_JALR)
            is_beq = (funct3 == FUNCT3_ADD) & (opcode == OPC_BRANCH)
            is_load = (opcode == OPC_LOAD)
            is_store = (opcode == OPC_STORE)

            # ALU result — single combinational assignment via Mux chain
            is_rtype_alu = is_add | is_sub | is_xor | is_or | is_and | is_sll | is_srl | is_sra | is_slt | is_sltu
            rtype_result = Wire(XLEN, "rtype_result")
            rtype_result <<= Mux(is_sub, ra - imm_i,
                         Mux(is_xor, ra ^ imm_i,
                         Mux(is_or, ra | imm_i,
                         Mux(is_and, ra & imm_i,
                         Mux(is_sll, ra << imm_i[4:0],
                         Mux(is_srl, ra >> imm_i[4:0],
                         Mux(is_sra, SRA(ra, imm_i[4:0]),
                         Mux(is_slt, Mux((ra - imm_i)[XLEN-1], Const(1, XLEN), Const(0, XLEN)),
                         Mux(is_sltu, Mux((ra < imm_u), Const(1, XLEN), Const(0, XLEN)),
                         Const(0, XLEN))))))))))

            alu_result <<= Mux(is_rtype_alu, rtype_result,
                       Mux(is_add, ra + imm_i,
                       Mux(is_addw, (ra + imm_i)[31:0],
                       Mux(is_lui, imm_u,
                       Mux(is_auipc, pc_reg + imm_u,
                       Mux(is_jal, pc_reg + imm_j,
                       Mux(is_jalr, ra + imm_i,
                       Mux(is_store, ra + imm_s,
                       Mux(is_beq, ra + imm_b,
                       Const(0, XLEN))))))))))

            # Branch
            branch_taken_w <<= Mux(is_beq, Mux(ra == rb, Const(1, 1), Const(0, 1)), Const(0, 1))
            branch_target_w <<= Mux(is_beq, imm_b + decode_pc,
                            Mux(is_jalr, ra + imm_i, pc_reg + imm_j))

            # Memory
            mem_read_w <<= is_load
            mem_write_w <<= is_store

            # Writeback enable
            wb_en_w <<= is_add | is_addw | is_sub | is_xor | is_or | is_and | \
                        is_sll | is_srl | is_sra | is_slt | is_sltu | \
                        is_lui | is_auipc | is_jal | is_jalr | is_load

            # Branch redirect
            branch_redirect <<= decode_valid & exec_valid & branch_taken_w

            # Stall: dcache busy on load/store
            dcache_stall <<= exec_valid & (mem_read_w | mem_write_w) & ~self.dcache_valid

            # ── D-Cache interface ──
            self.dcache_req <<= exec_valid & (mem_read_w | mem_write_w) & ~dcache_stall
            self.dcache_addr <<= Mux(mem_read_w, ra + imm_i, ra + imm_s)
            self.dcache_wdata <<= rb
            self.dcache_wen <<= exec_mem_write
            self.dcache_ready <<= 1
            mem_load_data <<= self.dcache_rdata

            # ── Status outputs ──
            self.core_stall <<= icache_stall | dcache_stall
            self.core_halted <<= 0
            self.retire_valid <<= wb_valid & wb_wb_en
            self.retire_count <<= Const(1, 3)

            # ── Writeback register file (sequential, not comb) ──
            # (handled in seq block above)

print("  - RV64Core defined")

# ============================================================================
# L1 Cache — direct-mapped for simplicity, parameterizable ways
# ============================================================================

class L1Cache(Module):
    """L1 cache with tag match, LRU replacement, MSI coherence state.

    Parameters are configured via generate parameters.
    """

    def __init__(self):
        super().__init__("l1_cache")

        # Parameters (set via generate param in instantiation)
        # NUM_SETS = (L1_SIZE_KB * 1024) / (L1_LINE_SIZE * L1_WAYS)
        # For 32KB, 64B line, 8-way: 64 sets
        # TAG_WIDTH = XLEN - OFFSET_WIDTH - INDEX_WIDTH
        # OFFSET_WIDTH = log2(L1_LINE_SIZE) = 6
        # INDEX_WIDTH = log2(NUM_SETS) = 6

        OFFSET_WIDTH = 6
        INDEX_WIDTH = 6
        TAG_WIDTH = XLEN - OFFSET_WIDTH - INDEX_WIDTH  # 52
        LINE_WIDTH = L1_LINE_SIZE * 8  # 512 bits
        NUM_SETS = 64
        DATA_WIDTH = 64  # per-word access

        # Ports
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(1, "req")
        self.addr = Input(XLEN, "addr")
        self.wen = Input(1, "wen")
        self.wdata = Input(DATA_WIDTH, "wdata")
        self.rdata = Output(DATA_WIDTH, "rdata")
        self.valid = Output(1, "valid")
        self.ready = Input(1, "ready")
        # Coherence
        self.probe_valid = Input(1, "probe_valid")
        self.probe_addr = Input(XLEN, "probe_addr")
        self.probe_invalidate = Input(1, "probe_invalidate")
        self.cache_state = Output(2, "cache_state")
        self.probe_ack = Output(1, "probe_ack")
        # NoC interface (for miss refill)
        self.noc_req = Output(1, "noc_req")
        self.noc_addr = Output(FLIT_WIDTH, "noc_addr")
        self.noc_rdata = Input(FLIT_WIDTH, "noc_rdata")
        self.noc_rvalid = Input(1, "noc_rvalid")
        self.noc_rready = Output(1, "noc_rready")

        # Arrays
        tag_ram = Array(TAG_WIDTH, NUM_SETS, "tag_ram")
        data_ram = Array(LINE_WIDTH, NUM_SETS, "data_ram")
        state_ram = Array(2, NUM_SETS, "state_ram")  # MSI state
        valid_ram = Array(1, NUM_SETS, "valid_ram")
        lru_state = Array(3, NUM_SETS, "lru_state")  # tree LRU for 8-way

        # FSM
        IDLE = 0
        TAG_CHECK = 1
        REFILL_WAIT = 2
        REFILL_STORE = 3

        cache_fsm = Reg(2, "cache_fsm")
        hit = Wire(1, "cache_hit")
        miss = Wire(1, "cache_miss")
        refill_line = Reg(LINE_WIDTH, "refill_line")
        refill_set = Reg(INDEX_WIDTH, "refill_set")
        pending_req = Reg(1, "pending_req")
        pending_wen = Reg(1, "pending_wen")
        pending_word = Reg(3, "pending_word")  # word offset in line

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                cache_fsm <<= IDLE
                pending_req <<= 0
                self.valid <<= 0
                for i in range(NUM_SETS):
                    valid_ram[i] <<= 0
                    state_ram[i] <<= STATE_I
            with Else():
                with Switch(cache_fsm) as sw:
                    with sw.case(IDLE):
                        with If(self.req == 1 and self.ready == 1):
                            cache_fsm <<= TAG_CHECK
                            pending_req <<= 1
                            pending_wen <<= self.wen
                            pending_word <<= self.addr[8:6]
                    with sw.case(TAG_CHECK):
                        pending_req <<= 0
                        with If(hit == 1):
                            # Write or read from data_ram
                            with If(pending_wen == 1):
                                data_ram[self.addr[11:6]] <<= self._write_word(
                                    data_ram[self.addr[11:6]],
                                    self.wdata,
                                    pending_word
                                )
                                state_ram[self.addr[11:6]] <<= STATE_M
                            self.valid <<= 1
                            self.rdata <<= self._read_word(data_ram[self.addr[11:6]], pending_word)
                            cache_fsm <<= IDLE
                        with Else():
                            # Miss → request from NoC
                            cache_fsm <<= REFILL_WAIT
                            self.noc_req <<= 1
                            self.noc_addr <<= self.addr
                            self.noc_rready <<= 1
                            refill_set <<= self.addr[11:6]
                    with sw.case(REFILL_WAIT):
                        with If(self.noc_rvalid == 1):
                            refill_line <<= self.noc_rdata
                            cache_fsm <<= REFILL_STORE
                    with sw.case(REFILL_STORE):
                        data_ram[refill_set] <<= refill_line
                        tag_ram[refill_set] <<= self.addr[XLEN-1:12]
                        valid_ram[refill_set] <<= 1
                        state_ram[refill_set] <<= STATE_S
                        cache_fsm <<= IDLE
                        self.noc_req <<= 0

        with self.comb:
            # Tag check
            index = Wire(INDEX_WIDTH, "cache_index")
            tag_in = Wire(TAG_WIDTH, "cache_tag_in")
            index <<= self.addr[11:6]
            tag_in <<= self.addr[XLEN-1:12]
            hit <<= (tag_ram[index] == tag_in) & valid_ram[index]
            miss <<= self.req & ~hit & self.ready

            # Probe handling
            probe_index = Wire(INDEX_WIDTH, "probe_index")
            probe_tag = Wire(TAG_WIDTH, "probe_tag")
            probe_index <<= self.probe_addr[11:6]
            probe_tag <<= self.probe_addr[XLEN-1:12]
            probe_hit = Wire(1, "probe_hit")
            probe_hit <<= (tag_ram[probe_index] == probe_tag) & valid_ram[probe_index]

            self.probe_ack <<= probe_hit & self.probe_valid
            with If(self.probe_valid == 1 and self.probe_invalidate == 1 and probe_hit == 1):
                valid_ram[probe_index] <<= 0

            # Cache state output (from current access set)
            self.cache_state <<= Mux(self.req, state_ram[self.addr[11:6]], Const(0, 2))

            # Default outputs
            self.valid <<= 0
            self.rdata <<= 0
            self.noc_req <<= 0
            self.noc_addr <<= 0
            self.noc_rready <<= 0

    def _read_word(self, line, word_idx):
        """Extract 64-bit word from 512-bit cache line."""
        return line[word_idx * 64 + 63: word_idx * 64]

    def _write_word(self, line, wdata, word_idx):
        """Replace 64-bit word in 512-bit cache line."""
        result = Wire(L1_LINE_SIZE * 8, "write_word_result")
        result <<= line
        result[word_idx * 64 + 63: word_idx * 64] <<= wdata
        return result

print("  - L1Cache defined")

# ============================================================================
# Coherence Directory — MSI directory with sharers tracking
# ============================================================================

class CoherenceDir(Module):
    """Directory-based MSI coherence controller.

    Tracks per-address: state (M/S/I), sharers bitmask, owner.
    Handles probe generation and writeback coordination.
    """

    def __init__(self):
        super().__init__("coherence_dir")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # Request from L1
        self.req_valid = Input(1, "req_valid")
        self.req_core_id = Input(6, "req_core_id")
        self.req_addr = Input(XLEN, "req_addr")
        self.req_is_write = Input(1, "req_is_write")
        # Response
        self.resp_valid = Output(1, "resp_valid")
        self.resp_action = Output(3, "resp_action")
        # Probe output to sharers
        self.probe_targets = Output(NUM_CORES, "probe_targets")
        self.probe_addr = Output(XLEN, "probe_addr")
        self.probe_valid = Output(1, "probe_valid")
        self.probe_invalidate = Output(1, "probe_invalidate")
        # Writeback
        self.writeback_valid = Input(1, "writeback_valid")
        self.writeback_data = Input(FLIT_WIDTH, "writeback_data")
        self.writeback_to_core = Output(1, "writeback_to_core")
        self.writeback_core_id = Output(6, "writeback_core_id")

        # Directory storage (256 entries, 8-way set associative simplification)
        NUM_ENTRIES = DIR_ENTRIES
        TAG_WIDTH_DIR = XLEN - 6  # assume 6-bit index

        dir_tag = Array(TAG_WIDTH_DIR, NUM_ENTRIES, "dir_tag")
        dir_state = Array(2, NUM_ENTRIES, "dir_state")  # MSI
        dir_sharers = Array(NUM_CORES, NUM_ENTRIES, "dir_sharers")
        dir_owner = Array(6, NUM_ENTRIES, "dir_owner")
        dir_valid = Array(1, NUM_ENTRIES, "dir_valid")

        # FSM
        S_IDLE = 0
        S_LOOKUP = 1
        S_PROBE = 2
        S_UPDATE = 3
        S_WB = 4

        dir_fsm = Reg(2, "dir_fsm")
        hit = Wire(1, "dir_hit")
        hit_idx = Wire(8, "dir_hit_idx")  # log2(256) = 8

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                dir_fsm <<= S_IDLE
                self.resp_valid <<= 0
                self.probe_valid <<= 0
                self.writeback_to_core <<= 0
                for i in range(NUM_ENTRIES):
                    dir_valid[i] <<= 0
                    dir_state[i] <<= STATE_I
            with Else():
                with Switch(dir_fsm) as sw:
                    with sw.case(S_IDLE):
                        self.resp_valid <<= 0
                        self.probe_valid <<= 0
                        with If(self.req_valid == 1):
                            dir_fsm <<= S_LOOKUP
                    with sw.case(S_LOOKUP):
                        with If(hit == 1):
                            # Check current state
                            cur_state = Wire(2, "dir_cur_state")
                            cur_state <<= dir_state[hit_idx]
                            with If(self.req_is_write == 1):
                                # Upgrade to M: invalidate sharers if S
                                with If(cur_state == STATE_S):
                                    dir_fsm <<= S_PROBE
                                    self.probe_targets <<= dir_sharers[hit_idx]
                                    self.probe_addr <<= self.req_addr
                                    self.probe_valid <<= 1
                                    self.probe_invalidate <<= 1
                                    dir_state[hit_idx] <<= STATE_M
                                    dir_sharers[hit_idx] <<= 0
                                    dir_owner[hit_idx] <<= self.req_core_id
                                    self.resp_action <<= 1  # invalidate_sharers
                                with Else():
                                    # Already M: writeback if different owner
                                    dir_fsm <<= S_UPDATE
                                    self.resp_action <<= 0  # direct_write
                            with Else():  # read
                                with If(cur_state == STATE_M):
                                    # Writeback from owner
                                    dir_fsm <<= S_WB
                                    self.writeback_to_core <<= 1
                                    self.writeback_core_id <<= dir_owner[hit_idx]
                                    self.resp_action <<= 2  # writeback_read
                                with Else():
                                    dir_sharers[hit_idx] <<= dir_sharers[hit_idx] | (Const(1, 64) << self.req_core_id)
                                    dir_fsm <<= S_UPDATE
                                    self.resp_action <<= 3  # read_shared
                        with Else():
                            # Cold miss → allocate
                            dir_fsm <<= S_UPDATE
                            dir_state[hit_idx] <<= Mux(self.req_is_write, Const(STATE_M, 2), Const(STATE_S, 2))
                            dir_owner[hit_idx] <<= self.req_core_id
                            dir_valid[hit_idx] <<= 1
                            self.resp_action <<= 4  # allocate
                    with sw.case(S_PROBE):
                        dir_fsm <<= S_UPDATE
                        self.probe_valid <<= 0
                        self.resp_valid <<= 1
                    with sw.case(S_UPDATE):
                        dir_fsm <<= S_IDLE
                        self.resp_valid <<= 1
                    with sw.case(S_WB):
                        with If(self.writeback_valid == 1):
                            dir_state[hit_idx] <<= STATE_S
                            dir_sharers[hit_idx] <<= dir_sharers[hit_idx] | (Const(1, 64) << self.req_core_id)
                            dir_fsm <<= S_IDLE
                            self.resp_valid <<= 1
                            self.writeback_to_core <<= 0

        with self.comb:
            # Directory lookup
            req_index = Wire(8, "dir_req_index")
            req_index <<= self.req_addr[13:6]  # 8-bit index
            req_tag = Wire(TAG_WIDTH_DIR, "dir_req_tag")
            req_tag <<= self.req_addr[XLEN-1:14]

            # Simple direct-mapped for skeleton
            hit <<= dir_valid[req_index] & (dir_tag[req_index] == req_tag)
            hit_idx <<= req_index

print("  - CoherenceDir defined")

# ============================================================================
# L2 Cache Slice — banked L2 cache
# ============================================================================

class L2CacheSlice(Module):
    """L2 cache slice (bank). 4KB per slice, 8-way.

    Handles requests from local L1 and remote clusters via NoC.
    Connects to DRAM controller on miss.
    """

    def __init__(self):
        super().__init__("l2_cache_slice")

        NUM_SETS = 64  # 4KB / (64B * 8-way) = 8 sets, round up to 64 for index
        LINE_WIDTH = 512
        TAG_WIDTH_L2 = XLEN - 6 - 6  # 52
        DATA_WIDTH = 64

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # Coherence input
        self.coherence_resp = Input(1, "coherence_resp")
        self.coherence_action = Input(3, "coherence_action")
        # NoC interface (from L1 via router)
        self.noc_req = Input(1, "noc_req")
        self.noc_addr = Input(FLIT_WIDTH, "noc_addr")
        self.noc_wen = Input(1, "noc_wen")
        self.noc_wdata = Input(DATA_WIDTH, "noc_wdata")
        self.noc_rdata = Output(DATA_WIDTH, "noc_rdata")
        self.noc_rvalid = Output(1, "noc_rvalid")
        self.noc_rready = Input(1, "noc_rready")
        # DRAM interface
        self.dram_req = Output(1, "dram_req")
        self.dram_addr = Output(FLIT_WIDTH, "dram_addr")
        self.dram_wen = Output(1, "dram_wen")
        self.dram_wdata = Output(DATA_WIDTH, "dram_wdata")
        self.dram_req_valid = Output(1, "dram_req_valid")
        self.dram_rdata = Input(DATA_WIDTH, "dram_rdata")
        self.dram_rvalid = Input(1, "dram_rvalid")

        # Storage
        tag_ram = Array(TAG_WIDTH_L2, NUM_SETS, "l2_tag_ram")
        data_ram = Array(LINE_WIDTH, NUM_SETS, "l2_data_ram")
        valid_ram = Array(1, NUM_SETS, "l2_valid_ram")
        lru = Array(3, NUM_SETS, "l2_lru")

        # FSM
        L2_IDLE = 0
        L2_LOOKUP = 1
        L2_REFILL = 2
        L2_WRITEBACK = 3

        l2_fsm = Reg(2, "l2_fsm")
        hit = Wire(1, "l2_hit")
        pending_data = Reg(LINE_WIDTH, "l2_pending_data")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                l2_fsm <<= L2_IDLE
                self.noc_rvalid <<= 0
                self.dram_req <<= 0
                self.dram_req_valid <<= 0
                for i in range(NUM_SETS):
                    valid_ram[i] <<= 0
            with Else():
                with Switch(l2_fsm) as sw:
                    with sw.case(L2_IDLE):
                        self.noc_rvalid <<= 0
                        with If(self.noc_req == 1):
                            l2_fsm <<= L2_LOOKUP
                    with sw.case(L2_LOOKUP):
                        with If(hit == 1):
                            # Hit: read data
                            self.noc_rdata <<= self._l2_read(data_ram[self.noc_addr[11:6]])
                            self.noc_rvalid <<= 1
                            l2_fsm <<= L2_IDLE
                        with Else():
                            # Miss: request DRAM
                            l2_fsm <<= L2_REFILL
                            self.dram_req <<= 1
                            self.dram_addr <<= self.noc_addr
                            self.dram_req_valid <<= 1
                    with sw.case(L2_REFILL):
                        with If(self.dram_rvalid == 1):
                            pending_data <<= self.dram_rdata
                            l2_fsm <<= L2_WRITEBACK
                    with sw.case(L2_WRITEBACK):
                        data_ram[self.noc_addr[11:6]] <<= pending_data
                        tag_ram[self.noc_addr[11:6]] <<= self.noc_addr[XLEN-1:12]
                        valid_ram[self.noc_addr[11:6]] <<= 1
                        self.noc_rdata <<= self._l2_read(pending_data)
                        self.noc_rvalid <<= 1
                        self.dram_req <<= 0
                        self.dram_req_valid <<= 0
                        l2_fsm <<= L2_IDLE

        with self.comb:
            # Lookup
            l2_index = Wire(6, "l2_idx")
            l2_tag = Wire(TAG_WIDTH_L2, "l2_tag")
            l2_index <<= self.noc_addr[11:6]
            l2_tag <<= self.noc_addr[XLEN-1:12]
            hit <<= valid_ram[l2_index] & (tag_ram[l2_index] == l2_tag)

    def _l2_read(self, line):
        """Read first 64-bit word from cache line."""
        return line[63:0]

print("  - L2CacheSlice defined")

# ============================================================================
# NoC Router — reuse from noc skill or inline simplified version
# ============================================================================

class NoCBuffer(Module):
    """Input buffer for NoC router with ready/valid handshake."""

    def __init__(self):
        super().__init__("noc_buffer")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.pop = Input(1, "pop")
        self.data_in = Input(FLIT_WIDTH, "data_in")
        self.data_out = Output(FLIT_WIDTH, "data_out")
        self.valid_out = Output(1, "valid_out")
        self.empty = Output(1, "empty")
        self.full = Output(1, "full")

        buf = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf")
        wr_ptr = Reg(2, "buf_wr_ptr")
        rd_ptr = Reg(2, "buf_rd_ptr")
        count = Reg(3, "buf_count")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                wr_ptr <<= 0
                rd_ptr <<= 0
                count <<= 0
            with Else():
                with If(self.valid_in == 1 and self.pop == 0):
                    buf[wr_ptr] <<= self.data_in
                    wr_ptr <<= wr_ptr + 1
                    count <<= count + 1
                with Else():
                    with If(self.valid_in == 0 and self.pop == 1):
                        rd_ptr <<= rd_ptr + 1
                        count <<= count - 1
                    with Else():
                        with If(self.valid_in == 1 and self.pop == 1):
                            buf[wr_ptr] <<= self.data_in
                            wr_ptr <<= wr_ptr + 1
                            rd_ptr <<= rd_ptr + 1

        with self.comb:
            self.data_out <<= buf[rd_ptr]
            self.empty <<= count == 0
            self.full <<= count == BUFFER_DEPTH
            self.valid_out <<= count != 0
            self.ready_out <<= count != BUFFER_DEPTH

print("  - NoCBuffer defined")


class NoCRouter(Module):
    """5-port NoC router with XY routing, input buffering, crossbar.

    Ports: East, West, North, South, Local (inject/eject)
    """

    def __init__(self):
        super().__init__("noc_router")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.x_pos = Input(3, "x_pos")
        self.y_pos = Input(3, "y_pos")

        # East
        self.e_flit = Input(FLIT_WIDTH, "e_flit")
        self.e_valid = Input(1, "e_valid")
        self.e_ready = Output(1, "e_ready")
        self.e_flit_o = Output(FLIT_WIDTH, "e_flit_o")
        self.e_valid_o = Output(1, "e_valid_o")
        self.e_ready_i = Input(1, "e_ready_i")
        # West
        self.w_flit = Input(FLIT_WIDTH, "w_flit")
        self.w_valid = Input(1, "w_valid")
        self.w_ready = Output(1, "w_ready")
        self.w_flit_o = Output(FLIT_WIDTH, "w_flit_o")
        self.w_valid_o = Output(1, "w_valid_o")
        self.w_ready_i = Input(1, "w_ready_i")
        # North
        self.n_flit = Input(FLIT_WIDTH, "n_flit")
        self.n_valid = Input(1, "n_valid")
        self.n_ready = Output(1, "n_ready")
        self.n_flit_o = Output(FLIT_WIDTH, "n_flit_o")
        self.n_valid_o = Output(1, "n_valid_o")
        self.n_ready_i = Input(1, "n_ready_i")
        # South
        self.s_flit = Input(FLIT_WIDTH, "s_flit")
        self.s_valid = Input(1, "s_valid")
        self.s_ready = Output(1, "s_ready")
        self.s_flit_o = Output(FLIT_WIDTH, "s_flit_o")
        self.s_valid_o = Output(1, "s_valid_o")
        self.s_ready_i = Input(1, "s_ready_i")
        # Local
        self.loc_inj_flit = Input(FLIT_WIDTH, "loc_inj_flit")
        self.loc_inj_valid = Input(1, "loc_inj_valid")
        self.loc_inj_ready = Output(1, "loc_inj_ready")
        self.loc_ej_flit = Output(FLIT_WIDTH, "loc_ej_flit")
        self.loc_ej_valid = Output(1, "loc_ej_valid")
        self.loc_ej_ready = Input(1, "loc_ej_ready")

        # Input buffers
        buf_e = NoCBuffer()
        buf_w = NoCBuffer()
        buf_n = NoCBuffer()
        buf_s = NoCBuffer()
        buf_j = NoCBuffer()

        # Routing outputs (per buffer: dest port)
        PORT_E = 0; PORT_W = 1; PORT_N = 2; PORT_S = 3; PORT_J = 4
        dest_e = Reg(3, "dest_e")
        dest_w = Reg(3, "dest_w")
        dest_n = Reg(3, "dest_n")
        dest_s = Reg(3, "dest_s")
        dest_j = Reg(3, "dest_j")

        # Crossbar outputs per direction
        xbar_e_out = Wire(FLIT_WIDTH, "xbar_e_out")
        xbar_e_valid = Wire(1, "xbar_e_valid")
        xbar_w_out = Wire(FLIT_WIDTH, "xbar_w_out")
        xbar_w_valid = Wire(1, "xbar_w_valid")
        xbar_n_out = Wire(FLIT_WIDTH, "xbar_n_out")
        xbar_n_valid = Wire(1, "xbar_n_valid")
        xbar_s_out = Wire(FLIT_WIDTH, "xbar_s_out")
        xbar_s_valid = Wire(1, "xbar_s_valid")
        xbar_j_out = Wire(FLIT_WIDTH, "xbar_j_out")
        xbar_j_valid = Wire(1, "xbar_j_valid")

        # Arbitration grants (which buffer wins for each output port)
        grant_e = Reg(3, "grant_e")  # which buffer→east
        grant_w = Reg(3, "grant_w")
        grant_n = Reg(3, "grant_n")
        grant_s = Reg(3, "grant_s")
        grant_j = Reg(3, "grant_j")

        # ── Sequential: buffer push/pop, crossbar switch ──
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                dest_e <<= 0; dest_w <<= 0; dest_n <<= 0; dest_s <<= 0; dest_j <<= 0
                grant_e <<= 0; grant_w <<= 0; grant_n <<= 0; grant_s <<= 0; grant_j <<= 0
                self.e_valid_o <<= 0; self.w_valid_o <<= 0
                self.n_valid_o <<= 0; self.s_valid_o <<= 0
                self.loc_ej_valid <<= 0
            with Else():
                # Compute XY routing destination for each buffer head
                # Destination from flit header bits [5:0] = dest_x, [9:6] = dest_y
                flit_e = Wire(FLIT_WIDTH, "flit_e_hd")
                flit_e <<= buf_e.data_out
                dest_x = flit_e[5:3]
                dest_y = flit_e[9:6]
                with If(dest_x > self.x_pos):
                    dest_e <<= PORT_E
                with Else():
                    with If(dest_x < self.x_pos):
                        dest_e <<= PORT_W
                    with Else():
                        with If(dest_y > self.y_pos):
                            dest_e <<= PORT_N
                        with Else():
                            with If(dest_y < self.y_pos):
                                dest_e <<= PORT_S
                            with Else():
                                dest_e <<= PORT_J  # local eject

                # Similar for other ports (simplified)
                flit_w = buf_w.data_out
                with If(flit_w[5:3] > self.x_pos):
                    dest_w <<= PORT_E
                with Elif(flit_w[5:3] < self.x_pos):
                    dest_w <<= PORT_W
                with Elif(flit_w[9:6] > self.y_pos):
                    dest_w <<= PORT_N
                with Elif(flit_w[9:6] < self.y_pos):
                    dest_w <<= PORT_S
                with Else():
                    dest_w <<= PORT_J

                # Buffer push
                buf_e.valid_in <<= self.e_valid & buf_e.ready_out
                buf_w.valid_in <<= self.w_valid & buf_w.ready_out
                buf_n.valid_in <<= self.n_valid & buf_n.ready_out
                buf_s.valid_in <<= self.s_valid & buf_s.ready_out
                buf_j.valid_in <<= self.loc_inj_valid & buf_j.ready_out

                # Buffer pop (crossbar grant + ready)
                buf_e.pop <<= Mux(dest_e == PORT_E, (grant_e == 1) & self.e_ready_i,
                          Mux(dest_e == PORT_W, (grant_w == 1) & self.w_ready_i,
                          Mux(dest_e == PORT_N, (grant_n == 1) & self.n_ready_i,
                          Mux(dest_e == PORT_S, (grant_s == 1) & self.s_ready_i,
                          Mux(dest_e == PORT_J, (grant_j == 1) & self.loc_ej_ready,
                          Const(0, 1))))))

                # Output valid
                self.e_valid_o <<= xbar_e_valid
                self.w_valid_o <<= xbar_w_valid
                self.n_valid_o <<= xbar_n_valid
                self.s_valid_o <<= xbar_s_valid
                self.loc_ej_valid <<= xbar_j_valid

        # ── Combinational: ready signals, crossbar, arbitration ──
        with self.comb:
            # Input ready (buffer not full)
            self.e_ready <<= buf_e.ready_out
            self.w_ready <<= buf_w.ready_out
            self.n_ready <<= buf_n.ready_out
            self.s_ready <<= buf_s.ready_out
            self.loc_inj_ready <<= buf_j.ready_out

            # Simple crossbar: connect buffer to output based on dest
            # East output
            xbar_e_valid <<= Mux(dest_e == PORT_E, ~buf_e.empty,
                         Mux(dest_w == PORT_E, ~buf_w.empty,
                         Mux(dest_n == PORT_E, ~buf_n.empty,
                         Mux(dest_s == PORT_E, ~buf_s.empty,
                         Mux(dest_j == PORT_E, ~buf_j.empty,
                         Const(0, 1))))))
            xbar_e_out <<= Mux(dest_e == PORT_E, buf_e.data_out,
                       Mux(dest_w == PORT_E, buf_w.data_out,
                       Mux(dest_n == PORT_E, buf_n.data_out,
                       Mux(dest_s == PORT_E, buf_s.data_out,
                       Mux(dest_j == PORT_E, buf_j.data_out,
                       Const(0, FLIT_WIDTH))))))

            # West output
            xbar_w_valid <<= Mux(dest_e == PORT_W, ~buf_e.empty,
                         Mux(dest_w == PORT_W, ~buf_w.empty,
                         Mux(dest_n == PORT_W, ~buf_n.empty,
                         Mux(dest_s == PORT_W, ~buf_s.empty,
                         Mux(dest_j == PORT_W, ~buf_j.empty,
                         Const(0, 1))))))
            xbar_w_out <<= Mux(dest_e == PORT_W, buf_e.data_out,
                       Mux(dest_w == PORT_W, buf_w.data_out,
                       Mux(dest_n == PORT_W, buf_n.data_out,
                       Mux(dest_s == PORT_W, buf_s.data_out,
                       Mux(dest_j == PORT_W, buf_j.data_out,
                       Const(0, FLIT_WIDTH))))))

            # North output
            xbar_n_valid <<= Mux(dest_e == PORT_N, ~buf_e.empty,
                         Mux(dest_w == PORT_N, ~buf_w.empty,
                         Mux(dest_n == PORT_N, ~buf_n.empty,
                         Mux(dest_s == PORT_N, ~buf_s.empty,
                         Mux(dest_j == PORT_N, ~buf_j.empty,
                         Const(0, 1))))))
            xbar_n_out <<= Mux(dest_e == PORT_N, buf_e.data_out,
                       Mux(dest_w == PORT_N, buf_w.data_out,
                       Mux(dest_n == PORT_N, buf_n.data_out,
                       Mux(dest_s == PORT_N, buf_s.data_out,
                       Mux(dest_j == PORT_N, buf_j.data_out,
                       Const(0, FLIT_WIDTH))))))

            # South output
            xbar_s_valid <<= Mux(dest_e == PORT_S, ~buf_e.empty,
                         Mux(dest_w == PORT_S, ~buf_w.empty,
                         Mux(dest_n == PORT_S, ~buf_n.empty,
                         Mux(dest_s == PORT_S, ~buf_s.empty,
                         Mux(dest_j == PORT_S, ~buf_j.empty,
                         Const(0, 1))))))
            xbar_s_out <<= Mux(dest_e == PORT_S, buf_e.data_out,
                       Mux(dest_w == PORT_S, buf_w.data_out,
                       Mux(dest_n == PORT_S, buf_n.data_out,
                       Mux(dest_s == PORT_S, buf_s.data_out,
                       Mux(dest_j == PORT_S, buf_j.data_out,
                       Const(0, FLIT_WIDTH))))))

            # Local eject
            xbar_j_valid <<= Mux(dest_e == PORT_J, ~buf_e.empty,
                         Mux(dest_w == PORT_J, ~buf_w.empty,
                         Mux(dest_n == PORT_J, ~buf_n.empty,
                         Mux(dest_s == PORT_J, ~buf_s.empty,
                         Mux(dest_j == PORT_J, ~buf_j.empty,
                         Const(0, 1))))))
            xbar_j_out <<= Mux(dest_e == PORT_J, buf_e.data_out,
                       Mux(dest_w == PORT_J, buf_w.data_out,
                       Mux(dest_n == PORT_J, buf_n.data_out,
                       Mux(dest_s == PORT_J, buf_s.data_out,
                       Mux(dest_j == PORT_J, buf_j.data_out,
                       Const(0, FLIT_WIDTH))))))

            self.e_flit_o <<= xbar_e_out
            self.w_flit_o <<= xbar_w_out
            self.n_flit_o <<= xbar_n_out
            self.s_flit_o <<= xbar_s_out
            self.loc_ej_flit <<= xbar_j_out

print("  - NoCRouter defined")

# ============================================================================
# ClusterTop — per-cluster wrapper
# ============================================================================

class ClusterTop(Module):
    """Single cluster: RV64Core + L1 I/D + CoherenceDir + L2Slice + NoCRouter.

    This module declares the external port interface for a cluster.
    Sub-module instantiation and internal wiring is handled by
    generate_cluster_rtl() in design_riscv64_soc.py.
    """

    def __init__(self):
        super().__init__("cluster_top")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.core_id = Input(6, "core_id")
        self.x_pos = Input(3, "x_pos")
        self.y_pos = Input(3, "y_pos")

        # NoC mesh interfaces
        self.e_flit = Input(FLIT_WIDTH, "e_flit")
        self.e_valid = Input(1, "e_valid")
        self.e_ready = Output(1, "e_ready")
        self.e_flit_o = Output(FLIT_WIDTH, "e_flit_o")
        self.e_valid_o = Output(1, "e_valid_o")
        self.e_ready_i = Input(1, "e_ready_i")

        self.w_flit = Input(FLIT_WIDTH, "w_flit")
        self.w_valid = Input(1, "w_valid")
        self.w_ready = Output(1, "w_ready")
        self.w_flit_o = Output(FLIT_WIDTH, "w_flit_o")
        self.w_valid_o = Output(1, "w_valid_o")
        self.w_ready_i = Input(1, "w_ready_i")

        self.n_flit = Input(FLIT_WIDTH, "n_flit")
        self.n_valid = Input(1, "n_valid")
        self.n_ready = Output(1, "n_ready")
        self.n_flit_o = Output(FLIT_WIDTH, "n_flit_o")
        self.n_valid_o = Output(1, "n_valid_o")
        self.n_ready_i = Input(1, "n_ready_i")

        self.s_flit = Input(FLIT_WIDTH, "s_flit")
        self.s_valid = Input(1, "s_valid")
        self.s_ready = Output(1, "s_ready")
        self.s_flit_o = Output(FLIT_WIDTH, "s_flit_o")
        self.s_valid_o = Output(1, "s_valid_o")
        self.s_ready_i = Input(1, "s_ready_i")

        # Local inject/eject
        self.loc_inj_flit = Input(FLIT_WIDTH, "loc_inj_flit")
        self.loc_inj_valid = Input(1, "loc_inj_valid")
        self.loc_inj_ready = Output(1, "loc_inj_ready")
        self.loc_ej_flit = Output(FLIT_WIDTH, "loc_ej_flit")
        self.loc_ej_valid = Output(1, "loc_ej_valid")
        self.loc_ej_ready = Input(1, "loc_ej_ready")

        # Status
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")
        self.core_stall = Output(1, "core_stall")

        # Internal wires: coherence / NoC interface
        probe_vld = Wire(1, "probe_vld")
        probe_addr_w = Wire(XLEN, "probe_addr_w")
        probe_inv = Wire(1, "probe_inv")
        cache_st = Wire(2, "cache_st")

        # NoC internal signals
        l2_noc_rdata = Wire(FLIT_WIDTH, "l2_noc_rdata")
        l2_noc_rvalid = Wire(1, "l2_noc_rvalid")

print("  - ClusterTop defined")

# ============================================================================
# MeshTop — 8×8 mesh of clusters
# ============================================================================

class MeshTop(Module):
    """8×8 mesh of RISCV64 clusters.

    Generates 64 cluster instances with E/W/N/S mesh wiring.
    """

    def __init__(self):
        super().__init__("mesh_top")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.sys_start = Input(1, "sys_start")
        self.sys_done = Output(1, "sys_done")

        # Generate 8×8 clusters with mesh interconnect
        # Internal wires for mesh links
        # For each node (y, x), create wires to neighbors
        for y in range(MESH_Y):
            for x in range(MESH_X):
                cid = y * MESH_X + x
                # East link: e_flit_o[x] → w_flit[x+1]
                if x < MESH_X - 1:
                    # Wire declarations for east-west link
                    Wire(FLIT_WIDTH, f"link_ew_{cid}")
                    Wire(1, f"link_ew_vld_{cid}")
                    Wire(1, f"link_ew_rdy_{cid}")
                if y < MESH_Y - 1:
                    Wire(FLIT_WIDTH, f"link_ns_{cid}")
                    Wire(1, f"link_ns_vld_{cid}")
                    Wire(1, f"link_ns_rdy_{cid}")

        # Note: Full mesh wiring requires generate-for in Verilog.
        # For DSL generation, we output the structure as comments
        # and let the VerilogEmitter handle generate blocks.

        with self.comb:
            self.sys_done <<= self.sys_start

print("  - MeshTop defined (skeleton — full mesh wiring via generate-for)")

# ============================================================================
# DRAM Controller
# ============================================================================

class DRAMCtrl(Module):
    """Simplified DDR4 controller interface.

    Accepts requests from L2 slices, queues and reorders,
    issues DRAM commands.
    """

    def __init__(self):
        super().__init__("dram_ctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Request from NoC (aggregated from all L2 slices)
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(FLIT_WIDTH, "req_addr")
        self.req_wen = Input(1, "req_wen")
        self.req_wdata = Input(64, "req_wdata")

        # Response to NoC
        self.resp_valid = Output(1, "resp_valid")
        self.resp_rdata = Output(64, "resp_rdata")

        # DRAM pins (simplified)
        self.dram_ck = Output(1, "dram_ck")
        self.dram_cs_n = Output(1, "dram_cs_n")
        self.dram_ras_n = Output(1, "dram_ras_n")
        self.dram_cas_n = Output(1, "dram_cas_n")
        self.dram_we_n = Output(1, "dram_we_n")
        self.dram_addr = Output(17, "dram_addr")
        self.dram_ba = Output(2, "dram_ba")
        self.dram_dq = Output(64, "dram_dq")
        self.dram_dqs = Output(1, "dram_dqs")

        # Command queue
        cmd_queue = Array(FLIT_WIDTH + 1, 64, "cmd_queue")
        cmd_wr_ptr = Reg(6, "cmd_wr_ptr")
        cmd_rd_ptr = Reg(6, "cmd_rd_ptr")
        cmd_count = Reg(7, "cmd_count")

        # DRAM FSM
        DRAM_IDLE = 0
        DRAM_ACT = 1
        DRAM_READ = 2
        DRAM_WRITE = 3
        DRAM_PRE = 4
        DRAM_REF = 5

        dram_fsm = Reg(3, "dram_fsm")
        dram_timer = Reg(8, "dram_timer")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                dram_fsm <<= DRAM_IDLE
                dram_timer <<= 0
                cmd_wr_ptr <<= 0
                cmd_rd_ptr <<= 0
                cmd_count <<= 0
                self.resp_valid <<= 0
            with Else():
                # Queue push
                with If(self.req_valid == 1):
                    cmd_queue[cmd_wr_ptr] <<= Cat(self.req_wen, self.req_addr)
                    cmd_wr_ptr <<= cmd_wr_ptr + 1
                    cmd_count <<= cmd_count + 1

                # Queue pop
                with If(cmd_count > 0 and dram_fsm == DRAM_IDLE):
                    cmd_rd_ptr <<= cmd_rd_ptr + 1
                    cmd_count <<= cmd_count - 1
                    dram_fsm <<= DRAM_ACT
                    dram_timer <<= 10  # tRCD = 10 cycles

                # FSM transitions
                with Switch(dram_fsm) as sw:
                    with sw.case(DRAM_ACT):
                        with If(dram_timer == 0):
                            # ACT → READ/WRITE
                            with If(cmd_queue[cmd_rd_ptr][0] == 0):
                                dram_fsm <<= DRAM_READ
                            with Else():
                                dram_fsm <<= DRAM_WRITE
                            dram_timer <<= 5
                    with sw.case(DRAM_READ):
                        with If(dram_timer == 0):
                            dram_fsm <<= DRAM_PRE
                            self.resp_valid <<= 1
                            dram_timer <<= 2
                    with sw.case(DRAM_WRITE):
                        with If(dram_timer == 0):
                            dram_fsm <<= DRAM_PRE
                            dram_timer <<= 2
                    with sw.case(DRAM_PRE):
                        with If(dram_timer == 0):
                            dram_fsm <<= DRAM_IDLE
                    with sw.case(DRAM_REF):
                        with If(dram_timer == 0):
                            dram_fsm <<= DRAM_IDLE

                with If(dram_timer != 0):
                    dram_timer <<= dram_timer - 1

        with self.comb:
            # DRAM command outputs
            self.dram_ck <<= 0
            self.dram_cs_n <<= Mux(dram_fsm == DRAM_IDLE, Const(1, 1), Const(0, 1))
            self.dram_ras_n <<= Mux(dram_fsm == DRAM_ACT, Const(0, 1), Const(1, 1))
            self.dram_cas_n <<= Mux((dram_fsm == DRAM_READ) | (dram_fsm == DRAM_WRITE), Const(0, 1), Const(1, 1))
            self.dram_we_n <<= Mux(dram_fsm == DRAM_PRE, Const(0, 1), Const(1, 1))
            self.dram_addr <<= cmd_queue[cmd_rd_ptr][FLIT_WIDTH-1:FLIT_WIDTH-17]
            self.dram_ba <<= cmd_queue[cmd_rd_ptr][FLIT_WIDTH-18:FLIT_WIDTH-19]
            self.dram_dq <<= cmd_queue[cmd_rd_ptr][63:0]
            self.dram_dqs <<= dram_fsm == DRAM_WRITE

            self.resp_rdata <<= 0

print("  - DRAMCtrl defined")

# ============================================================================
# RTL Generation — run all modules through VerilogEmitter
# ============================================================================

def emit_all(output_dir: str = "generated_soc"):
    """Generate Verilog for all DSL modules."""
    os.makedirs(output_dir, exist_ok=True)

    modules = [
        RV64Core,
        L1Cache,
        CoherenceDir,
        L2CacheSlice,
        NoCBuffer,
        NoCRouter,
        ClusterTop,
        MeshTop,
        DRAMCtrl,
    ]

    profile = EmitProfile()
    profile.style = "simple"
    profile.reset_style = "async_low"
    profile.language = "verilog2001"

    emitter = VerilogEmitter(
        indent="    ",
        use_sv_always=False,
        emit_source_map=True,
        profile=profile,
        disable_cse=False,
    )

    for mod_cls in modules:
        print(f"  Generating {mod_cls.__name__}...")
        mod = mod_cls()
        verilog = emitter.emit(mod)
        path = os.path.join(output_dir, f"{mod_cls.__name__.lower()}.v")
        with open(path, "w") as f:
            f.write(verilog)
        print(f"    → {path} ({len(verilog.splitlines())} lines)")

    return modules


if __name__ == "__main__":
    print("=" * 70)
    print("  RISCV64 SoC — DSL Module RTL Generation")
    print("=" * 70)
    print()
    print("Phase 1: Defining DSL Modules...")
    print("=" * 70)

    # Module definitions are executed at import time above
    print("  - RV64Core defined")
    print("  - L1Cache defined")
    print("  - CoherenceDir defined")
    print("  - L2CacheSlice defined")
    print("  - NoCBuffer defined")
    print("  - NoCRouter defined")
    print("  - ClusterTop defined")
    print("  - MeshTop defined")
    print("  - DRAMCtrl defined")
    print()

    print("Phase 2: Generating Verilog...")
    print("=" * 70)
    emit_all("generated_soc")
    print()

    print("Phase 3: Linting...")
    print("=" * 70)
    if VerilogLinter is not None:
        linter = VerilogLinter()
        for fname in os.listdir("generated_soc"):
            if fname.endswith(".v"):
                with open(os.path.join("generated_soc", fname)) as f:
                    result = linter.lint(f.read())
                if result.issues:
                    print(f"  {fname}: {len(result.issues)} issue(s)")
                    for issue in result.issues[:3]:
                        print(f"    {issue}")
                else:
                    print(f"  {fname}: lint clean")
    print()

    print("=" * 70)
    print("  Done — generated_soc/ contains Verilog for all modules")
    print("=" * 70)
