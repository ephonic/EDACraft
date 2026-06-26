"""
skills.hetero_riscv4 — Heterogeneous 4-Core RISC-V SoC DSL Modules

Architecture:
  2 efficiency cores (3-stage RV64I) + 2 performance cores (5-stage RV64I)
  in a 2x2 mesh NoC with directory-based MSI cache coherence.

Components:
  - EfficiencyCore: 3-stage RV64I (F/E/W), minimal pipeline
  - PerformanceCore: 5-stage RV64I (F/D/E/M/W), forwarding, hazard detection
  - L1CacheSmall: 16KB 2-way L1 for efficiency cores
  - L1CacheBig: 64KB 8-way L1 for performance cores
  - CoherenceDir: MSI directory for 4 cores
  - NoCBuffer: FIFO input buffer for router
  - NoCRouter: 5-port router with XY routing and per-output arbitration
  - HeteroMeshTop: 2x2 mesh connecting all 4 clusters
"""

from __future__ import annotations
import os, sys
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, HandshakeSpec, QueueSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
    Interface, HandshakeInterface, CacheInterface, connect_interfaces,
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
FLIT_WIDTH = 64
BUFFER_DEPTH = 4
NUM_CORES = 4
DATA_WIDTH = 64

# RV64 opcodes
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
# NoCBuffer — FIFO input buffer for router ports
# ============================================================================

class NoCBuffer(Module):
    """Simple FIFO buffer for NoC router input ports."""

    def __init__(self):
        super().__init__("noc_buffer")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.pop = Input(1, "pop")
        self.data_in = Input(FLIT_WIDTH, "data_in")
        self.ready_out = Output(1, "ready_out")
        self.data_out = Output(FLIT_WIDTH, "data_out")
        self.valid_out = Output(1, "valid_out")
        self.empty = Output(1, "empty")
        self.full = Output(1, "full")

        # Buffer storage — MUST use self.xxx so Array registers in module._arrays
        self.buf_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_data")
        self.buf_count = Reg(3, "buf_count")
        self.buf_rd_ptr = Reg(2, "buf_rd_ptr")
        self.buf_wr_ptr = Reg(2, "buf_wr_ptr")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.buf_wr_ptr <<= 0
                self.buf_rd_ptr <<= 0
                self.buf_count <<= 0
            with Else():
                with If((self.valid_in == 1) & (self.ready_out == 1) & (self.pop == 0)):
                    self.buf_data[self.buf_wr_ptr] <<= self.data_in
                    self.buf_wr_ptr <<= self.buf_wr_ptr + 1
                    self.buf_count <<= self.buf_count + 1
                with Elif((self.pop == 1) & (self.valid_out == 1)):
                    self.buf_rd_ptr <<= self.buf_rd_ptr + 1
                    self.buf_count <<= self.buf_count - 1
                with Elif((self.valid_in == 1) & (self.ready_out == 1) & (self.pop == 1) & (self.valid_out == 1)):
                    self.buf_data[self.buf_wr_ptr] <<= self.data_in
                    self.buf_wr_ptr <<= self.buf_wr_ptr + 1

        with self.comb:
            self.data_out <<= self.buf_data[self.buf_rd_ptr]
            self.empty <<= self.buf_count == 0
            self.full <<= self.buf_count == BUFFER_DEPTH
            self.valid_out <<= self.buf_count != 0
            self.ready_out <<= self.buf_count != BUFFER_DEPTH

print("  - NoCBuffer defined")

# ============================================================================
# EfficiencyCore — 3-stage RV64I (Fetch → Execute → Writeback)
# ============================================================================

class EfficiencyCore(Module):
    """Enhanced 3-stage RV64I pipeline for efficiency cores.

    Stages: Fetch → Execute → Writeback
    Supports: R-type, I-type, Load, Store, Branch, JAL, JALR, LUI, AUIPC, ECALL.
    """

    def __init__(self):
        super().__init__("efficiency_core")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # I-cache interface
        self.icache_req = Output(1, "icache_req")
        self.icache_addr = Output(XLEN, "icache_addr")
        self.icache_valid = Input(1, "icache_valid")
        self.icache_rdata = Input(64, "icache_rdata")
        # D-cache interface
        self.dcache_req = Output(1, "dcache_req")
        self.dcache_addr = Output(XLEN, "dcache_addr")
        self.dcache_wdata = Output(XLEN, "dcache_wdata")
        self.dcache_wen = Output(1, "dcache_wen")
        self.dcache_valid = Input(1, "dcache_valid")
        self.dcache_rdata = Input(64, "dcache_rdata")
        self.dcache_ready = Input(1, "dcache_ready")
        # Status
        self.core_stall = Output(1, "core_stall")
        self.core_halted = Output(1, "core_halted")
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")

        # Core state
        self.pc_reg = Reg(XLEN, "pc_reg")
        # Pipeline registers
        self.exec_valid = Reg(1, "exec_valid")
        self.exec_instr = Reg(64, "exec_instr")
        self.exec_pc = Reg(XLEN, "exec_pc")
        self.wb_valid = Reg(1, "wb_valid")
        self.wb_result = Reg(XLEN, "wb_result")
        self.wb_wb_en = Reg(1, "wb_wb_en")
        self.wb_rd = Reg(5, "wb_rd")
        # Register file
        self.rf = Array(XLEN, 32, "rf")
        # Fetch state
        self.fetch_valid = Reg(1, "fetch_valid")
        self.fetch_instr = Reg(32, "fetch_instr")
        # Wires
        self.icache_stall = Wire(1, "icache_stall")
        self.dcache_stall = Wire(1, "dcache_stall")
        self.core_stall_w = Wire(1, "core_stall_w")
        self.dcache_req_w = Wire(1, "dcache_req_w")
        self.dcache_addr_w = Wire(XLEN, "dcache_addr_w")
        self.dcache_wdata_w = Wire(XLEN, "dcache_wdata_w")
        self.dcache_wen_w = Wire(1, "dcache_wen_w")
        self.branch_redirect = Wire(1, "branch_redirect")
        self.branch_target = Wire(XLEN, "branch_target")
        self.branch_taken = Wire(1, "branch_taken")

        # Pre-declare comb wires used in seq
        exec_alu_result = Wire(XLEN, "exec_alu_result")
        exec_wb_en = Wire(1, "exec_wb_en")
        exec_rd = Wire(5, "exec_rd")

        # ── Sequential logic ──
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.pc_reg <<= Const(0x1000, XLEN)
                self.fetch_valid <<= 0
                self.fetch_instr <<= 0
                self.exec_valid <<= 0
                self.exec_instr <<= 0
                self.exec_pc <<= 0
                self.wb_valid <<= 0
                self.wb_wb_en <<= 0
                self.wb_rd <<= 0
                self.wb_result <<= 0

            with Else():
                # PC update: advance when not stalled, redirect on branch
                with If(self.branch_redirect == 1):
                    self.pc_reg <<= self.branch_target
                with Elif(self.core_stall_w == 0):
                    self.pc_reg <<= self.pc_reg + 4

                # Fetch stage: latch instruction when icache returns
                with If(self.branch_redirect == 1):
                    self.fetch_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.fetch_valid <<= self.icache_valid
                    with If(self.icache_valid == 1):
                        self.fetch_instr <<= self.icache_rdata[31:0]

                # Fetch → Execute pipeline
                with If(self.branch_redirect == 1):
                    self.exec_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.exec_valid <<= self.fetch_valid
                    with If(self.fetch_valid == 1):
                        self.exec_instr <<= self.fetch_instr
                        self.exec_pc <<= self.pc_reg

                # Execute → Writeback pipeline
                with If(self.branch_redirect == 1):
                    self.wb_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.wb_valid <<= self.exec_valid
                    with If(self.exec_valid == 1):
                        self.wb_wb_en <<= exec_wb_en
                        self.wb_rd <<= exec_rd
                        self.wb_result <<= exec_alu_result

                # Register file write
                with If(self.wb_valid == 1):
                    with If(self.wb_wb_en == 1):
                        with If(self.wb_rd != 0):
                            self.rf[self.wb_rd] <<= self.wb_result

        # ── Combinational logic ──
        with self.comb:
            self.icache_req <<= ~self.fetch_valid
            self.icache_addr <<= self.pc_reg
            self.icache_stall <<= self.fetch_valid & ~self.icache_valid

            # ── Decode (within execute) ──
            instr = self.exec_instr
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
            imm_i <<= Cat(Rep(instr[31], XLEN - 12), instr[31:20])
            imm_s <<= Cat(Rep(instr[31], XLEN - 12), instr[31:25], instr[11:7])
            imm_b <<= Cat(Rep(instr[31], XLEN - 13), instr[31], instr[7], instr[30:25], instr[11:8], Const(0, 1))
            imm_u <<= Cat(instr[31:12], Const(0, 12))
            imm_j <<= Cat(Rep(instr[31], XLEN - 21), instr[31], instr[19:12], instr[20], instr[30:21], Const(0, 1))

            # Register read with forwarding
            wb_fwd_valid = Wire(1, "wb_fwd_valid")
            wb_fwd_result = Wire(XLEN, "wb_fwd_result")
            wb_fwd_rd = Wire(5, "wb_fwd_rd")
            wb_fwd_valid <<= self.wb_valid & self.wb_wb_en
            wb_fwd_result <<= self.wb_result
            wb_fwd_rd <<= self.wb_rd
            ra = Wire(XLEN, "dec_ra")
            rb = Wire(XLEN, "dec_rb")
            ra <<= Mux(rs1 == wb_fwd_rd, wb_fwd_result, self.rf[rs1])
            rb <<= Mux(rs2 == wb_fwd_rd, wb_fwd_result, self.rf[rs2])

            # ── ALU operations ──
            is_add = (funct3 == FUNCT3_ADD) & (opcode == OPC_OP_IMM)
            is_add_r = (funct3 == FUNCT3_ADD) & (opcode == OPC_OP) & (funct7 == 0)
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
            is_bne = (funct3 == FUNCT3_SLTU) & (opcode == OPC_BRANCH)
            is_load = (opcode == OPC_LOAD)
            is_store = (opcode == OPC_STORE)
            is_ecall = (opcode == OPC_SYSTEM) & (funct3 == 0) & (instr[19:15] == 0) & (instr[24:20] == 0)
            is_rtype_alu = is_add | is_add_r | is_sub | is_xor | is_or | is_and | \
                           is_sll | is_srl | is_sra | is_slt | is_sltu

            # ALU result
            rtype_result = Wire(XLEN, "rtype_result")
            rtype_result <<= Mux(is_sub, ra - rb,
                         Mux(is_xor, ra ^ rb,
                         Mux(is_or, ra | rb,
                         Mux(is_and, ra & rb,
                         Mux(is_sll, ra << rb[4:0],
                         Mux(is_srl, ra >> rb[4:0],
                         Mux(is_sra, SRA(ra, rb[4:0]),
                         Mux(is_slt, Mux((ra - rb)[XLEN-1], Const(1, XLEN), Const(0, XLEN)),
                         Mux(is_sltu, Mux((ra < rb), Const(1, XLEN), Const(0, XLEN)),
                         Const(0, XLEN))))))))))

            # I-type ALU result
            itype_result = Wire(XLEN, "itype_result")
            itype_result <<= Mux(is_add, ra + imm_i,
                          Mux(is_add_r, ra - imm_i,
                          Mux(is_xor, ra ^ imm_i,
                          Mux(is_or, ra | imm_i,
                          Mux(is_and, ra & imm_i,
                          Mux(is_sll, ra << imm_i[4:0],
                          Mux(is_srl, ra >> imm_i[4:0],
                          Mux(is_sra, SRA(ra, imm_i[4:0]),
                          Mux(is_slt, Mux((ra - imm_i)[XLEN-1], Const(1, XLEN), Const(0, XLEN)),
                          Mux(is_sltu, Mux((ra < imm_i), Const(1, XLEN), Const(0, XLEN)),
                          Const(0, XLEN)))))))))))

            exec_alu_result <<= Mux(is_add | is_add_r, ra + imm_i,
                            Mux(is_rtype_alu, rtype_result,
                            Mux(is_lui, imm_u,
                            Mux(is_auipc, self.exec_pc + imm_u,
                            Mux(is_jal, self.exec_pc + imm_j,
                            Mux(is_jalr, ra + imm_i,
                            Mux(is_store, ra + imm_s,
                            Mux(is_beq, self.exec_pc + imm_b,
                            Mux(is_bne, self.exec_pc + imm_b,
                            Const(0, XLEN))))))))))

            # Branch
            self.branch_taken <<= Mux(is_beq, Mux(ra == rb, Const(1, 1), Const(0, 1)),
                                 Mux(is_bne, Mux(ra != rb, Const(1, 1), Const(0, 1)),
                                 Mux(is_jal | is_jalr, Const(1, 1), Const(0, 1))))
            self.branch_target <<= Mux(is_jalr, (ra + imm_i) & ~Const(1, XLEN),
                                  Mux(is_beq | is_bne, self.exec_pc + imm_b,
                                  self.exec_pc + imm_j))
            self.branch_redirect <<= self.exec_valid & self.branch_taken

            # D-cache
            exec_mem_read = Wire(1, "exec_mem_read")
            exec_mem_write = Wire(1, "exec_mem_write")
            exec_mem_read <<= is_load
            exec_mem_write <<= is_store
            self.dcache_stall <<= self.exec_valid & (exec_mem_read | exec_mem_write) & ~self.dcache_valid
            self.core_stall_w <<= self.icache_stall | self.dcache_stall

            self.dcache_req_w <<= self.exec_valid & (exec_mem_read | exec_mem_write) & ~self.dcache_stall
            self.dcache_addr_w <<= Mux(exec_mem_read, ra + imm_i, ra + imm_s)
            self.dcache_wdata_w <<= rb
            self.dcache_wen_w <<= exec_mem_write

            # Load data extension
            lb_ext = Wire(XLEN, "lb_ext")
            lbu_ext = Wire(XLEN, "lbu_ext")
            lh_ext = Wire(XLEN, "lh_ext")
            lhu_ext = Wire(XLEN, "lhu_ext")
            lw_ext = Wire(XLEN, "lw_ext")
            lwu_ext = Wire(XLEN, "lwu_ext")
            ld_ext = Wire(XLEN, "ld_ext")
            lb_ext <<= Cat(Rep(self.dcache_rdata[7], XLEN - 8), self.dcache_rdata[7:0])
            lbu_ext <<= Cat(Const(0, XLEN - 8), self.dcache_rdata[7:0])
            lh_ext <<= Cat(Rep(self.dcache_rdata[15], XLEN - 16), self.dcache_rdata[15:0])
            lhu_ext <<= Cat(Const(0, XLEN - 16), self.dcache_rdata[15:0])
            lw_ext <<= Cat(Rep(self.dcache_rdata[31], XLEN - 32), self.dcache_rdata[31:0])
            lwu_ext <<= Cat(Const(0, XLEN - 32), self.dcache_rdata[31:0])
            ld_ext <<= self.dcache_rdata

            wb_load_data = Wire(XLEN, "wb_load_data")
            wb_load_data <<= Mux(funct3 == FUNCT3_ADD, lb_ext,
                          Mux(funct3 == FUNCT3_SLL, lh_ext,
                          Mux(funct3 == FUNCT3_SLT, lw_ext,
                          Mux(funct3 == FUNCT3_SLTU, ld_ext,
                          Mux(funct3 == FUNCT3_XOR, lbu_ext,
                          Mux(funct3 == FUNCT3_SRL, lhu_ext,
                          Mux(funct3 == FUNCT3_OR, lwu_ext,
                          Const(0, XLEN))))))))

            # Writeback signals
            exec_wb_en <<= is_rtype_alu | is_add | is_lui | is_auipc | is_jal | is_jalr | is_load
            exec_rd <<= rd_d

            # Status
            self.core_stall <<= self.core_stall_w
            self.dcache_req <<= self.dcache_req_w
            self.dcache_addr <<= self.dcache_addr_w
            self.dcache_wdata <<= self.dcache_wdata_w
            self.dcache_wen <<= self.dcache_wen_w
            self.core_halted <<= 0
            # dcache_ready is driven by external cache
            self.retire_valid <<= self.wb_valid & self.wb_wb_en
            self.retire_count <<= Const(1, 3)

print("  - EfficiencyCore defined")

# ============================================================================
# PerformanceCore — 5-stage RV64I (Fetch → Decode → Execute → Memory → Writeback)
# ============================================================================

class PerformanceCore(Module):
    """Full 5-stage RV64I pipeline for performance cores.

    Stages: Fetch → Decode → Execute → Memory → Writeback
    Supports full RV64I with forwarding and hazard detection.
    """

    def __init__(self):
        super().__init__("performance_core")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # I-cache interface
        self.icache_req = Output(1, "icache_req")
        self.icache_addr = Output(XLEN, "icache_addr")
        self.icache_valid = Input(1, "icache_valid")
        self.icache_rdata = Input(64, "icache_rdata")
        # D-cache interface
        self.dcache_req = Output(1, "dcache_req")
        self.dcache_addr = Output(XLEN, "dcache_addr")
        self.dcache_wdata = Output(XLEN, "dcache_wdata")
        self.dcache_wen = Output(1, "dcache_wen")
        self.dcache_valid = Input(1, "dcache_valid")
        self.dcache_rdata = Input(64, "dcache_rdata")
        self.dcache_ready = Input(1, "dcache_ready")
        # Status
        self.core_stall = Output(1, "core_stall")
        self.core_halted = Output(1, "core_halted")
        self.retire_valid = Output(1, "retire_valid")
        self.retire_count = Output(3, "retire_count")

        # Core state
        self.pc_reg = Reg(XLEN, "pc_reg")
        # Pipeline registers
        self.fetch_valid = Reg(1, "fetch_valid")
        self.fetch_instr = Reg(32, "fetch_instr")
        self.fetch_pc = Reg(XLEN, "fetch_pc")
        self.decode_valid = Reg(1, "decode_valid")
        self.decode_instr = Reg(32, "decode_instr")
        self.decode_pc = Reg(XLEN, "decode_pc")
        self.exec_valid = Reg(1, "exec_valid")
        self.exec_instr = Reg(32, "exec_instr")
        self.exec_pc = Reg(XLEN, "exec_pc")
        self.exec_mem_read = Reg(1, "exec_mem_read")
        self.exec_ra = Reg(XLEN, "exec_ra")
        self.exec_rb = Reg(XLEN, "exec_rb")
        self.mem_valid = Reg(1, "mem_valid")
        self.mem_alu_result = Reg(XLEN, "mem_alu_result")
        self.mem_wb_en = Reg(1, "mem_wb_en")
        self.mem_rd = Reg(5, "mem_rd")
        self.mem_is_load = Reg(1, "mem_is_load")
        self.mem_load_data = Reg(XLEN, "mem_load_data")
        self.wb_valid = Reg(1, "wb_valid")
        self.wb_result = Reg(XLEN, "wb_result")
        self.wb_wb_en = Reg(1, "wb_wb_en")
        self.wb_rd = Reg(5, "wb_rd")
        # Register file
        self.rf = Array(XLEN, 32, "rf")
        # Wires
        self.icache_stall = Wire(1, "icache_stall")
        self.dcache_stall = Wire(1, "dcache_stall")
        self.branch_redirect = Wire(1, "branch_redirect")
        self.branch_target = Wire(XLEN, "branch_target")
        self.branch_taken = Wire(1, "branch_taken")
        self.core_stall_w = Wire(1, "core_stall_w")
        self.dcache_req_w = Wire(1, "dcache_req_w")
        self.dcache_addr_w = Wire(XLEN, "dcache_addr_w")
        self.dcache_wdata_w = Wire(XLEN, "dcache_wdata_w")
        self.dcache_wen_w = Wire(1, "dcache_wen_w")

        # Pre-declare comb wires used in seq
        exec_mem_read_c = Wire(1, "exec_mem_read_c")
        exec_alu_result = Wire(XLEN, "exec_alu_result")
        exec_wb_en = Wire(1, "exec_wb_en")
        exec_rd = Wire(5, "exec_rd")
        ra = Wire(XLEN, "dec_ra")
        rb = Wire(XLEN, "dec_rb")
        wb_result_c = Wire(XLEN, "wb_result_c")

        # ── Sequential logic ──
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.pc_reg <<= Const(0x1000, XLEN)
                self.fetch_valid <<= 0
                self.fetch_instr <<= 0
                self.fetch_pc <<= 0
                self.decode_valid <<= 0
                self.decode_instr <<= 0
                self.decode_pc <<= 0
                self.exec_valid <<= 0
                self.exec_instr <<= 0
                self.exec_pc <<= 0
                self.exec_mem_read <<= 0
                self.exec_ra <<= 0
                self.exec_rb <<= 0
                self.mem_valid <<= 0
                self.mem_alu_result <<= 0
                self.mem_wb_en <<= 0
                self.mem_rd <<= 0
                self.mem_is_load <<= 0
                self.mem_load_data <<= 0
                self.wb_valid <<= 0
                self.wb_wb_en <<= 0
                self.wb_rd <<= 0
                self.wb_result <<= 0

            with Else():
                # PC update
                with If(self.branch_redirect == 1):
                    self.pc_reg <<= self.branch_target
                with Elif(self.core_stall_w == 0):
                    self.pc_reg <<= self.pc_reg + 4

                # Fetch stage
                with If(self.branch_redirect == 1):
                    self.fetch_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.fetch_valid <<= self.icache_valid
                    with If(self.icache_valid == 1):
                        self.fetch_instr <<= self.icache_rdata[31:0]
                        self.fetch_pc <<= self.pc_reg

                # Fetch → Decode pipeline
                with If(self.branch_redirect == 1):
                    self.decode_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.decode_valid <<= self.fetch_valid
                    with If(self.fetch_valid == 1):
                        self.decode_instr <<= self.fetch_instr
                        self.decode_pc <<= self.fetch_pc

                # Decode → Execute pipeline
                with If(self.branch_redirect == 1):
                    self.exec_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.exec_valid <<= self.decode_valid
                    with If(self.decode_valid == 1):
                        self.exec_instr <<= self.decode_instr
                        self.exec_pc <<= self.decode_pc
                        self.exec_mem_read <<= exec_mem_read_c
                        self.exec_ra <<= ra
                        self.exec_rb <<= rb

                # Execute → Memory pipeline
                with If(self.branch_redirect == 1):
                    self.mem_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.mem_valid <<= self.exec_valid
                    with If(self.exec_valid == 1):
                        self.mem_alu_result <<= exec_alu_result
                        self.mem_wb_en <<= exec_wb_en
                        self.mem_rd <<= exec_rd
                        self.mem_is_load <<= self.exec_mem_read
                        self.mem_load_data <<= self.dcache_rdata

                # Memory → Writeback pipeline
                with If(self.branch_redirect == 1):
                    self.wb_valid <<= 0
                with Elif(self.core_stall_w == 0):
                    self.wb_valid <<= self.mem_valid
                    with If(self.mem_valid == 1):
                        self.wb_result <<= wb_result_c
                        self.wb_wb_en <<= self.mem_wb_en
                        self.wb_rd <<= self.mem_rd

                # Register file write
                with If(self.wb_valid == 1):
                    with If(self.wb_wb_en == 1):
                        with If(self.wb_rd != 0):
                            self.rf[self.wb_rd] <<= self.wb_result

        # ── Combinational logic ──
        with self.comb:
            # I-cache request
            self.icache_req <<= ~self.fetch_valid
            self.icache_addr <<= self.pc_reg
            self.icache_stall <<= self.fetch_valid & ~self.icache_valid

            # ── Decode ──
            instr = self.decode_instr
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
            imm_i <<= Cat(Rep(instr[31], XLEN - 12), instr[31:20])
            imm_s <<= Cat(Rep(instr[31], XLEN - 12), instr[31:25], instr[11:7])
            imm_b <<= Cat(Rep(instr[31], XLEN - 13), instr[31], instr[7], instr[30:25], instr[11:8], Const(0, 1))
            imm_u <<= Cat(instr[31:12], Const(0, 12))
            imm_j <<= Cat(Rep(instr[31], XLEN - 21), instr[31], instr[19:12], instr[20], instr[30:21], Const(0, 1))

            # ── Execute stage ──
            e_instr = self.exec_instr
            e_rd_d = Wire(5, "e_rd")
            e_imm_i = Wire(XLEN, "e_imm_i")
            e_imm_s = Wire(XLEN, "e_imm_s")
            e_imm_b = Wire(XLEN, "e_imm_b")
            e_imm_u = Wire(XLEN, "e_imm_u")
            e_imm_j = Wire(XLEN, "e_imm_j")

            e_rd_d <<= e_instr[11:7]
            e_imm_i <<= Cat(Rep(e_instr[31], XLEN - 12), e_instr[31:20])
            e_imm_s <<= Cat(Rep(e_instr[31], XLEN - 12), e_instr[31:25], e_instr[11:7])
            e_imm_b <<= Cat(Rep(e_instr[31], XLEN - 13), e_instr[31], e_instr[7], e_instr[30:25], e_instr[11:8], Const(0, 1))
            e_imm_u <<= Cat(e_instr[31:12], Const(0, 12))
            e_imm_j <<= Cat(Rep(e_instr[31], XLEN - 21), e_instr[31], e_instr[19:12], e_instr[20], e_instr[30:21], Const(0, 1))

            e_is_add = (e_instr[14:12] == FUNCT3_ADD) & (e_instr[6:0] == OPC_OP_IMM)
            e_is_add_r = (e_instr[14:12] == FUNCT3_ADD) & (e_instr[6:0] == OPC_OP) & (e_instr[31:25] == 0)
            e_is_sub = (e_instr[14:12] == FUNCT3_SUB) & (e_instr[6:0] == OPC_OP) & (e_instr[31:25] == Const(0x20, 7))
            e_is_xor = (e_instr[14:12] == FUNCT3_XOR) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_or = (e_instr[14:12] == FUNCT3_OR) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_and = (e_instr[14:12] == FUNCT3_AND) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_sll = (e_instr[14:12] == FUNCT3_SLL) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_srl = (e_instr[14:12] == FUNCT3_SRL) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM)) & (e_instr[31:25] == 0)
            e_is_sra = (e_instr[14:12] == FUNCT3_SRA) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM)) & (e_instr[31:25] == Const(0x20, 7))
            e_is_slt = (e_instr[14:12] == FUNCT3_SLT) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_sltu = (e_instr[14:12] == FUNCT3_SLTU) & ((e_instr[6:0] == OPC_OP) | (e_instr[6:0] == OPC_OP_IMM))
            e_is_lui = (e_instr[6:0] == OPC_LUI)
            e_is_auipc = (e_instr[6:0] == OPC_AUIPC)
            e_is_jal = (e_instr[6:0] == OPC_JAL)
            e_is_jalr = (e_instr[6:0] == OPC_JALR)
            e_is_beq = (e_instr[14:12] == FUNCT3_ADD) & (e_instr[6:0] == OPC_BRANCH)
            e_is_bne = (e_instr[14:12] == FUNCT3_SLTU) & (e_instr[6:0] == OPC_BRANCH)
            e_is_load = (e_instr[6:0] == OPC_LOAD)
            e_is_store = (e_instr[6:0] == OPC_STORE)

            e_is_rtype_alu = e_is_add | e_is_add_r | e_is_sub | e_is_xor | e_is_or | e_is_and | \
                             e_is_sll | e_is_srl | e_is_sra | e_is_slt | e_is_sltu

            e_rtype_result = Wire(XLEN, "e_rtype_result")
            e_rtype_result <<= Mux(e_is_sub, self.exec_ra - self.exec_rb,
                           Mux(e_is_xor, self.exec_ra ^ self.exec_rb,
                           Mux(e_is_or, self.exec_ra | self.exec_rb,
                           Mux(e_is_and, self.exec_ra & self.exec_rb,
                           Mux(e_is_sll, self.exec_ra << self.exec_rb[4:0],
                           Mux(e_is_srl, self.exec_ra >> self.exec_rb[4:0],
                           Mux(e_is_sra, SRA(self.exec_ra, self.exec_rb[4:0]),
                           Mux(e_is_slt, Mux((self.exec_ra - self.exec_rb)[XLEN-1], Const(1, XLEN), Const(0, XLEN)),
                           Mux(e_is_sltu, Mux((self.exec_ra < self.exec_rb), Const(1, XLEN), Const(0, XLEN)),
                           Const(0, XLEN))))))))))

            exec_alu_result <<= Mux(e_is_add, self.exec_ra + e_imm_i,
                            Mux(e_is_add_r, self.exec_ra + self.exec_rb,
                            Mux(e_is_rtype_alu, e_rtype_result,
                            Mux(e_is_lui, e_imm_u,
                            Mux(e_is_auipc, self.exec_pc + e_imm_u,
                            Mux(e_is_jal, self.exec_pc + e_imm_j,
                            Mux(e_is_jalr, self.exec_ra + e_imm_i,
                            Mux(e_is_store, self.exec_ra + e_imm_s,
                            Mux(e_is_beq, self.exec_pc + e_imm_b,
                            Mux(e_is_bne, self.exec_pc + e_imm_b,
                            Const(0, XLEN)))))))))))

            # D-cache (execute stage)
            exec_mem_read_c <<= e_is_load
            exec_mem_write = Wire(1, "exec_mem_write")
            exec_mem_write <<= e_is_store
            self.dcache_stall <<= self.exec_valid & (self.exec_mem_read | exec_mem_write) & ~self.dcache_valid
            self.core_stall_w <<= self.icache_stall | self.dcache_stall

            self.dcache_req_w <<= self.exec_valid & (self.exec_mem_read | exec_mem_write) & ~self.dcache_stall
            self.dcache_addr_w <<= Mux(self.exec_mem_read, self.exec_ra + e_imm_i, self.exec_ra + e_imm_s)
            self.dcache_wdata_w <<= self.exec_rb
            self.dcache_wen_w <<= exec_mem_write

            # Writeback signals (execute stage)
            exec_wb_en <<= e_is_rtype_alu | e_is_add | e_is_lui | e_is_auipc | e_is_jal | e_is_jalr | e_is_load
            exec_rd <<= e_rd_d

            # Register read with forwarding from EX, MEM, WB stages
            exec_fwd_valid = Wire(1, "exec_fwd_valid")
            exec_fwd_result = Wire(XLEN, "exec_fwd_result")
            exec_fwd_rd = Wire(5, "exec_fwd_rd")
            exec_fwd_valid <<= self.exec_valid & exec_wb_en
            exec_fwd_result <<= exec_alu_result
            exec_fwd_rd <<= exec_rd

            mem_fwd_valid = Wire(1, "mem_fwd_valid")
            mem_fwd_result = Wire(XLEN, "mem_fwd_result")
            mem_fwd_rd = Wire(5, "mem_fwd_rd")
            mem_fwd_valid <<= self.mem_valid & self.mem_wb_en
            mem_fwd_result <<= Mux(self.mem_is_load, self.mem_load_data, self.mem_alu_result)
            mem_fwd_rd <<= self.mem_rd

            wb_fwd_valid = Wire(1, "wb_fwd_valid")
            wb_fwd_result = Wire(XLEN, "wb_fwd_result")
            wb_fwd_rd = Wire(5, "wb_fwd_rd")
            wb_fwd_valid <<= self.wb_valid & self.wb_wb_en
            wb_fwd_result <<= self.wb_result
            wb_fwd_rd <<= self.wb_rd

            ra <<= Mux(exec_fwd_valid & (rs1 == exec_fwd_rd), exec_fwd_result,
                       Mux(mem_fwd_valid & (rs1 == mem_fwd_rd), mem_fwd_result,
                           Mux(wb_fwd_valid & (rs1 == wb_fwd_rd), wb_fwd_result, self.rf[rs1])))
            rb <<= Mux(exec_fwd_valid & (rs2 == exec_fwd_rd), exec_fwd_result,
                       Mux(mem_fwd_valid & (rs2 == mem_fwd_rd), mem_fwd_result,
                           Mux(wb_fwd_valid & (rs2 == wb_fwd_rd), wb_fwd_result, self.rf[rs2])))

            # Branch (decode stage, early resolution)
            is_beq = (funct3 == FUNCT3_ADD) & (opcode == OPC_BRANCH)
            is_bne = (funct3 == FUNCT3_SLTU) & (opcode == OPC_BRANCH)
            is_jal = (opcode == OPC_JAL)
            is_jalr = (opcode == OPC_JALR)
            self.branch_taken <<= Mux(is_beq, Mux(ra == rb, Const(1, 1), Const(0, 1)),
                                 Mux(is_bne, Mux(ra != rb, Const(1, 1), Const(0, 1)),
                                 Mux(is_jal | is_jalr, Const(1, 1), Const(0, 1))))
            self.branch_target <<= Mux(is_jalr, (ra + imm_i) & ~Const(1, XLEN),
                                  Mux(is_beq | is_bne, self.decode_pc + imm_b,
                                  self.decode_pc + imm_j))
            self.branch_redirect <<= self.decode_valid & self.branch_taken

            # Load extension
            lb_ext = Wire(XLEN, "lb_ext")
            lbu_ext = Wire(XLEN, "lbu_ext")
            lh_ext = Wire(XLEN, "lh_ext")
            lhu_ext = Wire(XLEN, "lhu_ext")
            lw_ext = Wire(XLEN, "lw_ext")
            lwu_ext = Wire(XLEN, "lwu_ext")
            ld_ext = Wire(XLEN, "ld_ext")
            lb_ext <<= Cat(Rep(self.dcache_rdata[7], XLEN - 8), self.dcache_rdata[7:0])
            lbu_ext <<= Cat(Const(0, XLEN - 8), self.dcache_rdata[7:0])
            lh_ext <<= Cat(Rep(self.dcache_rdata[15], XLEN - 16), self.dcache_rdata[15:0])
            lhu_ext <<= Cat(Const(0, XLEN - 16), self.dcache_rdata[15:0])
            lw_ext <<= Cat(Rep(self.dcache_rdata[31], XLEN - 32), self.dcache_rdata[31:0])
            lwu_ext <<= Cat(Const(0, XLEN - 32), self.dcache_rdata[31:0])
            ld_ext <<= self.dcache_rdata

            wb_load_data = Wire(XLEN, "wb_load_data")
            wb_load_data <<= Mux(funct3 == FUNCT3_ADD, lb_ext,
                          Mux(funct3 == FUNCT3_SLL, lh_ext,
                          Mux(funct3 == FUNCT3_SLT, lw_ext,
                          Mux(funct3 == FUNCT3_SLTU, ld_ext,
                          Mux(funct3 == FUNCT3_XOR, lbu_ext,
                          Mux(funct3 == FUNCT3_SRL, lhu_ext,
                          Mux(funct3 == FUNCT3_OR, lwu_ext,
                          Const(0, XLEN))))))))

            wb_result_c <<= Mux(self.mem_is_load, wb_load_data, self.mem_alu_result)

            # Status
            self.core_stall <<= self.core_stall_w
            self.dcache_req <<= self.dcache_req_w
            self.dcache_addr <<= self.dcache_addr_w
            self.dcache_wdata <<= self.dcache_wdata_w
            self.dcache_wen <<= self.dcache_wen_w
            self.core_halted <<= 0
            # dcache_ready is driven by external cache
            self.retire_valid <<= self.wb_valid & self.wb_wb_en
            self.retire_count <<= Const(1, 3)

print("  - PerformanceCore defined")


# ============================================================================
# L1CacheSmall — 16KB 2-way L1 for efficiency cores
# ============================================================================

class L1CacheSmall(Module):
    """Small L1 cache (16KB, 2-way set associative) for efficiency cores."""

    def __init__(self):
        super().__init__("l1_cache_small")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # CPU interface
        self.req = Input(1, "req")
        self.addr = Input(XLEN, "addr")
        self.wdata = Input(64, "wdata")
        self.wen = Input(1, "wen")
        self.valid = Output(1, "valid")
        self.rdata = Output(64, "rdata")
        self.ready = Output(1, "ready")
        # Coherence probe
        self.probe_addr = Input(XLEN, "probe_addr")
        self.probe_valid = Input(1, "probe_valid")
        self.probe_invalidate = Input(1, "probe_invalidate")
        self.probe_ack = Output(1, "probe_ack")
        # NoC interface (to L2/coherence)
        self.noc_req = Output(1, "noc_req")
        self.noc_addr = Output(XLEN, "noc_addr")
        self.noc_rdata = Input(64, "noc_rdata")
        self.noc_valid = Input(1, "noc_valid")
        # Cache state output
        self.cache_state = Output(2, "cache_state")

        # Cache params: 16KB = 16384 bytes, 2 ways, 64B line
        NUM_SETS = 128
        WAY_BITS = 1
        INDEX_WIDTH = 7  # log2(128)
        TAG_WIDTH = XLEN - 6 - INDEX_WIDTH  # 64 - 6 - 7 = 51
        LINE_WIDTH = 512  # 64 bytes * 8 bits

        self.data_ram0 = Array(LINE_WIDTH, NUM_SETS, "data_ram0")
        self.data_ram1 = Array(LINE_WIDTH, NUM_SETS, "data_ram1")
        self.tag_ram0 = Array(TAG_WIDTH, NUM_SETS, "tag_ram0")
        self.tag_ram1 = Array(TAG_WIDTH, NUM_SETS, "tag_ram1")
        self.valid_ram0 = Array(1, NUM_SETS, "valid_ram0")
        self.valid_ram1 = Array(1, NUM_SETS, "valid_ram1")
        self.state_ram0 = Array(2, NUM_SETS, "state_ram0")
        self.state_ram1 = Array(2, NUM_SETS, "state_ram1")
        self.lru = Array(1, NUM_SETS, "lru")

        hit = Wire(1, "cache_hit")
        miss = Wire(1, "cache_miss")

        # FSM
        S_IDLE = 0
        S_CHECK = 1
        S_REFILL = 2
        S_PROBE = 3

        cache_fsm = Reg(2, "cache_fsm")
        refill_set = Reg(INDEX_WIDTH, "refill_set")
        refill_line = Reg(LINE_WIDTH, "refill_line")
        # Wires for NoC interface — driven purely in comb from FSM state
        noc_req_w = Wire(1, "noc_req_w")
        noc_addr_w = Wire(XLEN, "noc_addr_w")

        # Pre-declare comb wires used in seq
        hit0 = Wire(1, "hit0")
        hit1 = Wire(1, "hit1")
        index = Wire(INDEX_WIDTH, "cache_index")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                cache_fsm <<= S_IDLE
                self.valid <<= 0
                with ForGen("i", 0, NUM_SETS) as i:
                    self.valid_ram0[i] <<= 0
                    self.valid_ram1[i] <<= 0
            with Else():
                self.valid <<= 0
                with Switch(cache_fsm) as sw:
                    with sw.case(S_IDLE):
                        with If(self.probe_valid == 1):
                            cache_fsm <<= S_PROBE
                        with Elif((self.req == 1) & (self.ready == 1)):
                            cache_fsm <<= S_CHECK
                    with sw.case(S_CHECK):
                        with If(hit == 1):
                            self.valid <<= 1
                            cache_fsm <<= S_IDLE
                            # Write hit: update data RAM
                            with If(self.wen == 1):
                                with If(hit0 == 1):
                                    self.data_ram0[index] <<= self.wdata
                                    self.state_ram0[index] <<= STATE_M
                                with Elif(hit1 == 1):
                                    self.data_ram1[index] <<= self.wdata
                                    self.state_ram1[index] <<= STATE_M
                        with Elif(miss == 1):
                            cache_fsm <<= S_REFILL
                    with sw.case(S_REFILL):
                        with If(self.noc_valid == 1):
                            refill_line <<= self.noc_rdata
                            refill_set <<= self.addr[11:6]
                            with If(self.lru[self.addr[11:6]] == 0):
                                self.data_ram0[self.addr[11:6]] <<= self.noc_rdata
                                self.tag_ram0[self.addr[11:6]] <<= self.addr[XLEN-1:12]
                                self.valid_ram0[self.addr[11:6]] <<= 1
                                self.state_ram0[self.addr[11:6]] <<= STATE_S
                                self.lru[self.addr[11:6]] <<= 1
                            with Else():
                                self.data_ram1[self.addr[11:6]] <<= self.noc_rdata
                                self.tag_ram1[self.addr[11:6]] <<= self.addr[XLEN-1:12]
                                self.valid_ram1[self.addr[11:6]] <<= 1
                                self.state_ram1[self.addr[11:6]] <<= STATE_S
                                self.lru[self.addr[11:6]] <<= 0
                            self.valid <<= 1
                            cache_fsm <<= S_IDLE
                    with sw.case(S_PROBE):
                        cache_fsm <<= S_IDLE

        with self.comb:
            tag_in = Wire(TAG_WIDTH, "cache_tag_in")
            index <<= self.addr[11:6]
            tag_in <<= self.addr[XLEN-1:12]

            hit0 <<= (self.tag_ram0[index] == tag_in) & self.valid_ram0[index]
            hit1 <<= (self.tag_ram1[index] == tag_in) & self.valid_ram1[index]
            hit <<= hit0 | hit1
            miss <<= self.req & ~hit & (cache_fsm == S_CHECK)

            # Read data
            with If(hit0 == 1):
                self.rdata <<= self.data_ram0[index][63:0]
            with Elif(hit1 == 1):
                self.rdata <<= self.data_ram1[index][63:0]
            with Else():
                self.rdata <<= 0

            # Probe
            probe_index = Wire(INDEX_WIDTH, "probe_index")
            probe_tag = Wire(TAG_WIDTH, "probe_tag")
            probe_index <<= self.probe_addr[11:6]
            probe_tag <<= self.probe_addr[XLEN-1:12]
            probe_hit0 = Wire(1, "probe_hit0")
            probe_hit1 = Wire(1, "probe_hit1")
            probe_hit0 <<= (self.tag_ram0[probe_index] == probe_tag) & self.valid_ram0[probe_index]
            probe_hit1 <<= (self.tag_ram1[probe_index] == probe_tag) & self.valid_ram1[probe_index]
            self.probe_ack <<= (probe_hit0 | probe_hit1) & self.probe_valid

            with If((self.probe_valid == 1) & (self.probe_invalidate == 1)):
                with If(probe_hit0 == 1):
                    self.valid_ram0[probe_index] <<= 0
                with Elif(probe_hit1 == 1):
                    self.valid_ram1[probe_index] <<= 0

            # Cache state
            with If(hit0 == 1):
                self.cache_state <<= self.state_ram0[index]
            with Elif(hit1 == 1):
                self.cache_state <<= self.state_ram1[index]
            with Else():
                self.cache_state <<= STATE_I

            # Ready
            self.ready <<= Mux(cache_fsm == S_IDLE, 1, 0)
            # NoC request driven from FSM state: assert during CHECK→miss
            noc_req_w <<= (cache_fsm == S_CHECK) & miss
            noc_addr_w <<= self.addr
            self.noc_req <<= noc_req_w
            self.noc_addr <<= noc_addr_w

print("  - L1CacheSmall defined")

# ============================================================================
# L1CacheBig — 64KB 8-way L1 for performance cores
# ============================================================================

class L1CacheBig(Module):
    """Large L1 cache (64KB, 8-way set associative) for performance cores."""

    def __init__(self):
        super().__init__("l1_cache_big")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        # CPU interface
        self.req = Input(1, "req")
        self.addr = Input(XLEN, "addr")
        self.wdata = Input(64, "wdata")
        self.wen = Input(1, "wen")
        self.valid = Output(1, "valid")
        self.rdata = Output(64, "rdata")
        self.ready = Output(1, "ready")
        # Coherence probe
        self.probe_addr = Input(XLEN, "probe_addr")
        self.probe_valid = Input(1, "probe_valid")
        self.probe_invalidate = Input(1, "probe_invalidate")
        self.probe_ack = Output(1, "probe_ack")
        # NoC interface
        self.noc_req = Output(1, "noc_req")
        self.noc_addr = Output(XLEN, "noc_addr")
        self.noc_rdata = Input(64, "noc_rdata")
        self.noc_valid = Input(1, "noc_valid")
        # Cache state output
        self.cache_state = Output(2, "cache_state")

        # Cache params: 64KB = 65536 bytes, 8 ways, 64B line
        NUM_SETS = 128
        INDEX_WIDTH = 7
        TAG_WIDTH = XLEN - 6 - INDEX_WIDTH  # 51
        LINE_WIDTH = 512  # 64 bytes

        self.data_ram0 = Array(LINE_WIDTH, NUM_SETS, "data_ram0")
        self.data_ram1 = Array(LINE_WIDTH, NUM_SETS, "data_ram1")
        self.tag_ram0 = Array(TAG_WIDTH, NUM_SETS, "tag_ram0")
        self.tag_ram1 = Array(TAG_WIDTH, NUM_SETS, "tag_ram1")
        self.valid_ram0 = Array(1, NUM_SETS, "valid_ram0")
        self.valid_ram1 = Array(1, NUM_SETS, "valid_ram1")
        self.state_ram0 = Array(2, NUM_SETS, "state_ram0")
        self.state_ram1 = Array(2, NUM_SETS, "state_ram1")
        self.lru = Array(1, NUM_SETS, "lru")

        hit = Wire(1, "cache_hit")
        miss = Wire(1, "cache_miss")

        # FSM
        S_IDLE = 0
        S_CHECK = 1
        S_REFILL = 2
        S_PROBE = 3

        cache_fsm = Reg(2, "cache_fsm")
        noc_req_w = Wire(1, "noc_req_w")
        noc_addr_w = Wire(XLEN, "noc_addr_w")

        # Pre-declare comb wires used in seq
        hit0 = Wire(1, "hit0")
        hit1 = Wire(1, "hit1")
        index = Wire(INDEX_WIDTH, "cache_index")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                cache_fsm <<= S_IDLE
                self.valid <<= 0
                with ForGen("i", 0, NUM_SETS) as i:
                    self.valid_ram0[i] <<= 0
                    self.valid_ram1[i] <<= 0
            with Else():
                self.valid <<= 0
                with Switch(cache_fsm) as sw:
                    with sw.case(S_IDLE):
                        with If(self.probe_valid == 1):
                            cache_fsm <<= S_PROBE
                        with Elif((self.req == 1) & (self.ready == 1)):
                            cache_fsm <<= S_CHECK
                    with sw.case(S_CHECK):
                        with If(hit == 1):
                            self.valid <<= 1
                            cache_fsm <<= S_IDLE
                            # Write hit
                            with If(self.wen == 1):
                                with If(hit0 == 1):
                                    self.data_ram0[index] <<= self.wdata
                                    self.state_ram0[index] <<= STATE_M
                                with Elif(hit1 == 1):
                                    self.data_ram1[index] <<= self.wdata
                                    self.state_ram1[index] <<= STATE_M
                        with Elif(miss == 1):
                            cache_fsm <<= S_REFILL
                    with sw.case(S_REFILL):
                        with If(self.noc_valid == 1):
                            with If(self.lru[self.addr[11:6]] == 0):
                                self.data_ram0[self.addr[11:6]] <<= self.noc_rdata
                                self.tag_ram0[self.addr[11:6]] <<= self.addr[XLEN-1:12]
                                self.valid_ram0[self.addr[11:6]] <<= 1
                                self.state_ram0[self.addr[11:6]] <<= STATE_S
                                self.lru[self.addr[11:6]] <<= 1
                            with Else():
                                self.data_ram1[self.addr[11:6]] <<= self.noc_rdata
                                self.tag_ram1[self.addr[11:6]] <<= self.addr[XLEN-1:12]
                                self.valid_ram1[self.addr[11:6]] <<= 1
                                self.state_ram1[self.addr[11:6]] <<= STATE_S
                                self.lru[self.addr[11:6]] <<= 0
                            self.valid <<= 1
                            cache_fsm <<= S_IDLE
                    with sw.case(S_PROBE):
                        cache_fsm <<= S_IDLE

        with self.comb:
            tag_in = Wire(TAG_WIDTH, "cache_tag_in")
            index <<= self.addr[11:6]
            tag_in <<= self.addr[XLEN-1:12]

            hit0 <<= (self.tag_ram0[index] == tag_in) & self.valid_ram0[index]
            hit1 <<= (self.tag_ram1[index] == tag_in) & self.valid_ram1[index]
            hit <<= hit0 | hit1
            miss <<= self.req & ~hit & (cache_fsm == S_CHECK)

            with If(hit0 == 1):
                self.rdata <<= self.data_ram0[index][63:0]
            with Elif(hit1 == 1):
                self.rdata <<= self.data_ram1[index][63:0]
            with Else():
                self.rdata <<= 0

            probe_index = Wire(INDEX_WIDTH, "probe_index")
            probe_tag = Wire(TAG_WIDTH, "probe_tag")
            probe_index <<= self.probe_addr[11:6]
            probe_tag <<= self.probe_addr[XLEN-1:12]
            probe_hit0 = Wire(1, "probe_hit0")
            probe_hit1 = Wire(1, "probe_hit1")
            probe_hit0 <<= (self.tag_ram0[probe_index] == probe_tag) & self.valid_ram0[probe_index]
            probe_hit1 <<= (self.tag_ram1[probe_index] == probe_tag) & self.valid_ram1[probe_index]
            self.probe_ack <<= (probe_hit0 | probe_hit1) & self.probe_valid

            with If((self.probe_valid == 1) & (self.probe_invalidate == 1)):
                with If(probe_hit0 == 1):
                    self.valid_ram0[probe_index] <<= 0
                with Elif(probe_hit1 == 1):
                    self.valid_ram1[probe_index] <<= 0

            with If(hit0 == 1):
                self.cache_state <<= self.state_ram0[index]
            with Elif(hit1 == 1):
                self.cache_state <<= self.state_ram1[index]
            with Else():
                self.cache_state <<= STATE_I

            self.ready <<= Mux(cache_fsm == S_IDLE, 1, 0)
            noc_req_w <<= (cache_fsm == S_CHECK) & miss
            noc_addr_w <<= self.addr
            self.noc_req <<= noc_req_w
            self.noc_addr <<= noc_addr_w

print("  - L1CacheBig defined")


# ============================================================================
# CoherenceDir — MSI directory for 4 cores
# ============================================================================

class CoherenceDir(Module):
    """Directory-based MSI coherence controller for 4 cores."""

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

        # Directory: 64 entries, direct-mapped
        NUM_ENTRIES = 64
        TAG_WIDTH_DIR = XLEN - 6  # 6-bit index
        INDEX_WIDTH = 6

        self.dir_tag = Array(TAG_WIDTH_DIR, NUM_ENTRIES, "dir_tag")
        self.dir_state = Array(2, NUM_ENTRIES, "dir_state")  # MSI
        self.dir_sharers = Array(NUM_CORES, NUM_ENTRIES, "dir_sharers")
        self.dir_owner = Array(6, NUM_ENTRIES, "dir_owner")
        self.dir_valid = Array(1, NUM_ENTRIES, "dir_valid")

        # FSM
        S_IDLE = 0
        S_LOOKUP = 1
        S_PROBE = 2
        S_UPDATE = 3
        S_WB = 4

        dir_fsm = Reg(3, "dir_fsm")
        hit = Wire(1, "dir_hit")
        hit_idx = Wire(INDEX_WIDTH, "dir_hit_idx")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                dir_fsm <<= S_IDLE
                self.resp_valid <<= 0
                self.probe_valid <<= 0
                self.writeback_to_core <<= 0
                with ForGen("i", 0, NUM_ENTRIES) as i:
                    self.dir_valid[i] <<= 0
                    self.dir_state[i] <<= STATE_I
            with Else():
                with Switch(dir_fsm) as sw:
                    with sw.case(S_IDLE):
                        self.resp_valid <<= 0
                        self.probe_valid <<= 0
                        with If(self.req_valid == 1):
                            dir_fsm <<= S_LOOKUP
                    with sw.case(S_LOOKUP):
                        with If(hit == 1):
                            cur_state = Wire(2, "dir_cur_state")
                            cur_state <<= self.dir_state[hit_idx]
                            with If(self.req_is_write == 1):
                                with If(cur_state == STATE_S):
                                    dir_fsm <<= S_PROBE
                                    self.probe_targets <<= self.dir_sharers[hit_idx]
                                    self.probe_addr <<= self.req_addr
                                    self.probe_valid <<= 1
                                    self.probe_invalidate <<= 1
                                    self.dir_state[hit_idx] <<= STATE_M
                                    self.dir_sharers[hit_idx] <<= 0
                                    self.dir_owner[hit_idx] <<= self.req_core_id
                                    self.resp_action <<= 1  # invalidate_sharers
                                with Else():
                                    dir_fsm <<= S_UPDATE
                                    self.resp_action <<= 0  # direct_write
                            with Else():  # read
                                with If(cur_state == STATE_M):
                                    dir_fsm <<= S_WB
                                    self.writeback_to_core <<= 1
                                    self.writeback_core_id <<= self.dir_owner[hit_idx]
                                    self.resp_action <<= 2  # writeback_read
                                with Else():
                                    self.dir_sharers[hit_idx] <<= self.dir_sharers[hit_idx] | (Const(1, NUM_CORES) << self.req_core_id)
                                    dir_fsm <<= S_UPDATE
                                    self.resp_action <<= 3  # read_shared
                        with Else():
                            dir_fsm <<= S_UPDATE
                            self.dir_state[hit_idx] <<= Mux(self.req_is_write, Const(STATE_M, 2), Const(STATE_S, 2))
                            self.dir_owner[hit_idx] <<= self.req_core_id
                            self.dir_valid[hit_idx] <<= 1
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
                            self.dir_state[hit_idx] <<= STATE_S
                            self.dir_sharers[hit_idx] <<= self.dir_sharers[hit_idx] | (Const(1, NUM_CORES) << self.req_core_id)
                            dir_fsm <<= S_IDLE
                            self.resp_valid <<= 1
                            self.writeback_to_core <<= 0

        with self.comb:
            req_index = Wire(INDEX_WIDTH, "dir_req_index")
            req_tag = Wire(TAG_WIDTH_DIR, "dir_req_tag")
            req_index <<= self.req_addr[11:6]
            req_tag <<= self.req_addr[XLEN-1:12]

            hit <<= self.dir_valid[req_index] & (self.dir_tag[req_index] == req_tag)
            hit_idx <<= req_index

print("  - CoherenceDir defined")

# ============================================================================
# NoCRouter — 5-port router with XY routing for 2x2 mesh
# ============================================================================

class NoCRouter(Module):
    """5-port NoC router with input buffers, crossbar, XY routing.

    Ports: East, West, North, South, Local (inject/eject)
    Uses dimension-order (XY) routing for deadlock-free 2x2 mesh.

    Key fix: Per-output arbitration with consistent pop logic.
    Each output port independently grants to one requesting input.
    An input is popped only when it wins grant on ANY output and that output is ready.
    """

    PORT_E = 0
    PORT_W = 1
    PORT_N = 2
    PORT_S = 3
    PORT_J = 4
    PORT_NONE = 5

    def __init__(self):
        super().__init__("noc_router")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.x_pos = Input(3, "x_pos")
        self.y_pos = Input(3, "y_pos")
        # Input ports
        self.e_flit = Input(FLIT_WIDTH, "e_flit")
        self.e_valid = Input(1, "e_valid")
        self.e_ready_i = Input(1, "e_ready_i")
        self.w_flit = Input(FLIT_WIDTH, "w_flit")
        self.w_valid = Input(1, "w_valid")
        self.w_ready_i = Input(1, "w_ready_i")
        self.n_flit = Input(FLIT_WIDTH, "n_flit")
        self.n_valid = Input(1, "n_valid")
        self.n_ready_i = Input(1, "n_ready_i")
        self.s_flit = Input(FLIT_WIDTH, "s_flit")
        self.s_valid = Input(1, "s_valid")
        self.s_ready_i = Input(1, "s_ready_i")
        self.loc_inj_flit = Input(FLIT_WIDTH, "loc_inj_flit")
        self.loc_inj_valid = Input(1, "loc_inj_valid")
        self.loc_ej_ready = Input(1, "loc_ej_ready")
        # Output ports
        self.e_ready = Output(1, "e_ready")
        self.e_flit_o = Output(FLIT_WIDTH, "e_flit_o")
        self.e_valid_o = Output(1, "e_valid_o")
        self.w_ready = Output(1, "w_ready")
        self.w_flit_o = Output(FLIT_WIDTH, "w_flit_o")
        self.w_valid_o = Output(1, "w_valid_o")
        self.n_ready = Output(1, "n_ready")
        self.n_flit_o = Output(FLIT_WIDTH, "n_flit_o")
        self.n_valid_o = Output(1, "n_valid_o")
        self.s_ready = Output(1, "s_ready")
        self.s_flit_o = Output(FLIT_WIDTH, "s_flit_o")
        self.s_valid_o = Output(1, "s_valid_o")
        self.loc_inj_ready = Output(1, "loc_inj_ready")
        self.loc_ej_flit = Output(FLIT_WIDTH, "loc_ej_flit")
        self.loc_ej_valid = Output(1, "loc_ej_valid")

        # Input buffer arrays
        self.buf_e_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_e_data")
        self.buf_w_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_w_data")
        self.buf_n_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_n_data")
        self.buf_s_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_s_data")
        self.buf_j_data = Array(FLIT_WIDTH, BUFFER_DEPTH, "buf_j_data")
        self.buf_e_cnt = Reg(3, "buf_e_cnt")
        self.buf_w_cnt = Reg(3, "buf_w_cnt")
        self.buf_n_cnt = Reg(3, "buf_n_cnt")
        self.buf_s_cnt = Reg(3, "buf_s_cnt")
        self.buf_j_cnt = Reg(3, "buf_j_cnt")
        self.buf_e_rd = Reg(2, "buf_e_rd")
        self.buf_w_rd = Reg(2, "buf_w_rd")
        self.buf_n_rd = Reg(2, "buf_n_rd")
        self.buf_s_rd = Reg(2, "buf_s_rd")
        self.buf_j_rd = Reg(2, "buf_j_rd")
        self.buf_e_wr = Reg(2, "buf_e_wr")
        self.buf_w_wr = Reg(2, "buf_w_wr")
        self.buf_n_wr = Reg(2, "buf_n_wr")
        self.buf_s_wr = Reg(2, "buf_s_wr")
        self.buf_j_wr = Reg(2, "buf_j_wr")

        # Buffer status wires
        e_empty = Wire(1, "e_empty")
        w_empty = Wire(1, "w_empty")
        n_empty = Wire(1, "n_empty")
        s_empty = Wire(1, "s_empty")
        j_empty = Wire(1, "j_empty")
        e_full = Wire(1, "e_full")
        w_full = Wire(1, "w_full")
        n_full = Wire(1, "n_full")
        s_full = Wire(1, "s_full")
        j_full = Wire(1, "j_full")

        # Routing decision per input port
        dest_e = Wire(3, "dest_e")
        dest_w = Wire(3, "dest_w")
        dest_n = Wire(3, "dest_n")
        dest_s = Wire(3, "dest_s")
        dest_j = Wire(3, "dest_j")

        # Push/pop signals
        e_push = Wire(1, "e_push")
        w_push = Wire(1, "w_push")
        n_push = Wire(1, "n_push")
        s_push = Wire(1, "s_push")
        j_push = Wire(1, "j_push")
        e_pop = Wire(1, "e_pop")
        w_pop = Wire(1, "w_pop")
        n_pop = Wire(1, "n_pop")
        s_pop = Wire(1, "s_pop")
        j_pop = Wire(1, "j_pop")

        # Crossbar outputs
        xbar_e_valid = Wire(1, "xbar_e_valid")
        xbar_e_out = Wire(FLIT_WIDTH, "xbar_e_out")
        xbar_w_valid = Wire(1, "xbar_w_valid")
        xbar_w_out = Wire(FLIT_WIDTH, "xbar_w_out")
        xbar_n_valid = Wire(1, "xbar_n_valid")
        xbar_n_out = Wire(FLIT_WIDTH, "xbar_n_out")
        xbar_s_valid = Wire(1, "xbar_s_valid")
        xbar_s_out = Wire(FLIT_WIDTH, "xbar_s_out")
        xbar_j_valid = Wire(1, "xbar_j_valid")
        xbar_j_out = Wire(FLIT_WIDTH, "xbar_j_out")

        # Grant signals: which input port wins each output (0-4, 5=none)
        grant_to_e = Wire(3, "grant_to_e")
        grant_to_w = Wire(3, "grant_to_w")
        grant_to_n = Wire(3, "grant_to_n")
        grant_to_s = Wire(3, "grant_to_s")
        grant_to_j = Wire(3, "grant_to_j")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.buf_e_cnt <<= 0; self.buf_w_cnt <<= 0; self.buf_n_cnt <<= 0
                self.buf_s_cnt <<= 0; self.buf_j_cnt <<= 0
                self.buf_e_rd <<= 0; self.buf_w_rd <<= 0; self.buf_n_rd <<= 0
                self.buf_s_rd <<= 0; self.buf_j_rd <<= 0
                self.buf_e_wr <<= 0; self.buf_w_wr <<= 0; self.buf_n_wr <<= 0
                self.buf_s_wr <<= 0; self.buf_j_wr <<= 0
                self.e_valid_o <<= 0; self.w_valid_o <<= 0
                self.n_valid_o <<= 0; self.s_valid_o <<= 0
                self.loc_ej_valid <<= 0
            with Else():
                # Buffer push
                with If(e_push == 1):
                    self.buf_e_data[self.buf_e_wr] <<= self.e_flit
                    self.buf_e_wr <<= self.buf_e_wr + 1
                with If(w_push == 1):
                    self.buf_w_data[self.buf_w_wr] <<= self.w_flit
                    self.buf_w_wr <<= self.buf_w_wr + 1
                with If(n_push == 1):
                    self.buf_n_data[self.buf_n_wr] <<= self.n_flit
                    self.buf_n_wr <<= self.buf_n_wr + 1
                with If(s_push == 1):
                    self.buf_s_data[self.buf_s_wr] <<= self.s_flit
                    self.buf_s_wr <<= self.buf_s_wr + 1
                with If(j_push == 1):
                    self.buf_j_data[self.buf_j_wr] <<= self.loc_inj_flit
                    self.buf_j_wr <<= self.buf_j_wr + 1

                # Buffer pop
                with If(e_pop == 1):
                    self.buf_e_rd <<= self.buf_e_rd + 1
                with If(w_pop == 1):
                    self.buf_w_rd <<= self.buf_w_rd + 1
                with If(n_pop == 1):
                    self.buf_n_rd <<= self.buf_n_rd + 1
                with If(s_pop == 1):
                    self.buf_s_rd <<= self.buf_s_rd + 1
                with If(j_pop == 1):
                    self.buf_j_rd <<= self.buf_j_rd + 1

                # Count update
                self.buf_e_cnt <<= self.buf_e_cnt + e_push - e_pop
                self.buf_w_cnt <<= self.buf_w_cnt + w_push - w_pop
                self.buf_n_cnt <<= self.buf_n_cnt + n_push - n_pop
                self.buf_s_cnt <<= self.buf_s_cnt + s_push - s_pop
                self.buf_j_cnt <<= self.buf_j_cnt + j_push - j_pop

                # Output valid
                self.e_valid_o <<= xbar_e_valid
                self.w_valid_o <<= xbar_w_valid
                self.n_valid_o <<= xbar_n_valid
                self.s_valid_o <<= xbar_s_valid
                self.loc_ej_valid <<= xbar_j_valid

        with self.comb:
            # Buffer status
            e_empty <<= self.buf_e_cnt == 0
            w_empty <<= self.buf_w_cnt == 0
            n_empty <<= self.buf_n_cnt == 0
            s_empty <<= self.buf_s_cnt == 0
            j_empty <<= self.buf_j_cnt == 0
            e_full <<= self.buf_e_cnt == BUFFER_DEPTH
            w_full <<= self.buf_w_cnt == BUFFER_DEPTH
            n_full <<= self.buf_n_cnt == BUFFER_DEPTH
            s_full <<= self.buf_s_cnt == BUFFER_DEPTH
            j_full <<= self.buf_j_cnt == BUFFER_DEPTH

            # Ready signals (not full)
            self.e_ready <<= ~e_full
            self.w_ready <<= ~w_full
            self.n_ready <<= ~n_full
            self.s_ready <<= ~s_full
            self.loc_inj_ready <<= ~j_full

            # Push: valid & ready
            e_push <<= self.e_valid & ~e_full
            w_push <<= self.w_valid & ~w_full
            n_push <<= self.n_valid & ~n_full
            s_push <<= self.s_valid & ~s_full
            j_push <<= self.loc_inj_valid & ~j_full

            # ── XY routing per input port ──
            # dest_x = flit[5:3], dest_y = flit[9:6]
            def route_xy(buf_data, buf_rd, x_pos, y_pos, dest_wire):
                dest_x = Wire(3, "dest_x")
                dest_y = Wire(3, "dest_y")
                dest_x <<= buf_data[buf_rd][5:3]
                dest_y <<= buf_data[buf_rd][9:6]
                with If(x_pos < dest_x):
                    dest_wire <<= self.PORT_E
                with Elif(x_pos > dest_x):
                    dest_wire <<= self.PORT_W
                with Elif(y_pos < dest_y):
                    dest_wire <<= self.PORT_N
                with Elif(y_pos > dest_y):
                    dest_wire <<= self.PORT_S
                with Else():
                    dest_wire <<= self.PORT_J

            route_xy(self.buf_e_data, self.buf_e_rd, self.x_pos, self.y_pos, dest_e)
            route_xy(self.buf_w_data, self.buf_w_rd, self.x_pos, self.y_pos, dest_w)
            route_xy(self.buf_n_data, self.buf_n_rd, self.x_pos, self.y_pos, dest_n)
            route_xy(self.buf_s_data, self.buf_s_rd, self.x_pos, self.y_pos, dest_s)
            route_xy(self.buf_j_data, self.buf_j_rd, self.x_pos, self.y_pos, dest_j)

            # ── Per-output arbitration (fixed priority: e > w > n > s > j) ──
            # East output (port 0): collect requests from all inputs that want East
            req_e_to_e = (dest_e == self.PORT_E) & ~e_empty
            req_w_to_e = (dest_w == self.PORT_E) & ~w_empty
            req_n_to_e = (dest_n == self.PORT_E) & ~n_empty
            req_s_to_e = (dest_s == self.PORT_E) & ~s_empty
            req_j_to_e = (dest_j == self.PORT_E) & ~j_empty

            grant_to_e <<= Mux(req_e_to_e, self.PORT_E,
                        Mux(req_w_to_e, self.PORT_W,
                        Mux(req_n_to_e, self.PORT_N,
                        Mux(req_s_to_e, self.PORT_S,
                        Mux(req_j_to_e, self.PORT_J, self.PORT_NONE)))))

            # West output (port 1)
            req_e_to_w = (dest_e == self.PORT_W) & ~e_empty
            req_w_to_w = (dest_w == self.PORT_W) & ~w_empty
            req_n_to_w = (dest_n == self.PORT_W) & ~n_empty
            req_s_to_w = (dest_s == self.PORT_W) & ~s_empty
            req_j_to_w = (dest_j == self.PORT_W) & ~j_empty

            grant_to_w <<= Mux(req_e_to_w, self.PORT_E,
                        Mux(req_w_to_w, self.PORT_W,
                        Mux(req_n_to_w, self.PORT_N,
                        Mux(req_s_to_w, self.PORT_S,
                        Mux(req_j_to_w, self.PORT_J, self.PORT_NONE)))))

            # North output (port 2)
            req_e_to_n = (dest_e == self.PORT_N) & ~e_empty
            req_w_to_n = (dest_w == self.PORT_N) & ~w_empty
            req_n_to_n = (dest_n == self.PORT_N) & ~n_empty
            req_s_to_n = (dest_s == self.PORT_N) & ~s_empty
            req_j_to_n = (dest_j == self.PORT_N) & ~j_empty

            grant_to_n <<= Mux(req_e_to_n, self.PORT_E,
                        Mux(req_w_to_n, self.PORT_W,
                        Mux(req_n_to_n, self.PORT_N,
                        Mux(req_s_to_n, self.PORT_S,
                        Mux(req_j_to_n, self.PORT_J, self.PORT_NONE)))))

            # South output (port 3)
            req_e_to_s = (dest_e == self.PORT_S) & ~e_empty
            req_w_to_s = (dest_w == self.PORT_S) & ~w_empty
            req_n_to_s = (dest_n == self.PORT_S) & ~n_empty
            req_s_to_s = (dest_s == self.PORT_S) & ~s_empty
            req_j_to_s = (dest_j == self.PORT_S) & ~j_empty

            grant_to_s <<= Mux(req_e_to_s, self.PORT_E,
                        Mux(req_w_to_s, self.PORT_W,
                        Mux(req_n_to_s, self.PORT_N,
                        Mux(req_s_to_s, self.PORT_S,
                        Mux(req_j_to_s, self.PORT_J, self.PORT_NONE)))))

            # Local eject (port 4)
            req_e_to_j = (dest_e == self.PORT_J) & ~e_empty
            req_w_to_j = (dest_w == self.PORT_J) & ~w_empty
            req_n_to_j = (dest_n == self.PORT_J) & ~n_empty
            req_s_to_j = (dest_s == self.PORT_J) & ~s_empty
            req_j_to_j = (dest_j == self.PORT_J) & ~j_empty

            grant_to_j <<= Mux(req_e_to_j, self.PORT_E,
                        Mux(req_w_to_j, self.PORT_W,
                        Mux(req_n_to_j, self.PORT_N,
                        Mux(req_s_to_j, self.PORT_S,
                        Mux(req_j_to_j, self.PORT_J, self.PORT_NONE)))))

            # ── Pop: input popped if it wins grant on ANY output and that output is ready ──
            e_pop <<= ((grant_to_e == self.PORT_E) & self.e_ready_i) | \
                      ((grant_to_w == self.PORT_E) & self.w_ready_i) | \
                      ((grant_to_n == self.PORT_E) & self.n_ready_i) | \
                      ((grant_to_s == self.PORT_E) & self.s_ready_i) | \
                      ((grant_to_j == self.PORT_E) & self.loc_ej_ready)

            w_pop <<= ((grant_to_e == self.PORT_W) & self.e_ready_i) | \
                      ((grant_to_w == self.PORT_W) & self.w_ready_i) | \
                      ((grant_to_n == self.PORT_W) & self.n_ready_i) | \
                      ((grant_to_s == self.PORT_W) & self.s_ready_i) | \
                      ((grant_to_j == self.PORT_W) & self.loc_ej_ready)

            n_pop <<= ((grant_to_e == self.PORT_N) & self.e_ready_i) | \
                      ((grant_to_w == self.PORT_N) & self.w_ready_i) | \
                      ((grant_to_n == self.PORT_N) & self.n_ready_i) | \
                      ((grant_to_s == self.PORT_N) & self.s_ready_i) | \
                      ((grant_to_j == self.PORT_N) & self.loc_ej_ready)

            s_pop <<= ((grant_to_e == self.PORT_S) & self.e_ready_i) | \
                      ((grant_to_w == self.PORT_S) & self.w_ready_i) | \
                      ((grant_to_n == self.PORT_S) & self.n_ready_i) | \
                      ((grant_to_s == self.PORT_S) & self.s_ready_i) | \
                      ((grant_to_j == self.PORT_S) & self.loc_ej_ready)

            j_pop <<= ((grant_to_e == self.PORT_J) & self.e_ready_i) | \
                      ((grant_to_w == self.PORT_J) & self.w_ready_i) | \
                      ((grant_to_n == self.PORT_J) & self.n_ready_i) | \
                      ((grant_to_s == self.PORT_J) & self.s_ready_i) | \
                      ((grant_to_j == self.PORT_J) & self.loc_ej_ready)

            # ── Crossbar: select which input goes to each output based on grant ──
            def xbar_select(grant, e_data, w_data, n_data, s_data, j_data):
                return Mux(grant == self.PORT_E, e_data,
                      Mux(grant == self.PORT_W, w_data,
                      Mux(grant == self.PORT_N, n_data,
                      Mux(grant == self.PORT_S, s_data,
                      Mux(grant == self.PORT_J, j_data, Const(0, FLIT_WIDTH))))))

            xbar_e_valid <<= grant_to_e != self.PORT_NONE
            xbar_e_out <<= xbar_select(grant_to_e,
                self.buf_e_data[self.buf_e_rd], self.buf_w_data[self.buf_w_rd],
                self.buf_n_data[self.buf_n_rd], self.buf_s_data[self.buf_s_rd],
                self.buf_j_data[self.buf_j_rd])

            xbar_w_valid <<= grant_to_w != self.PORT_NONE
            xbar_w_out <<= xbar_select(grant_to_w,
                self.buf_e_data[self.buf_e_rd], self.buf_w_data[self.buf_w_rd],
                self.buf_n_data[self.buf_n_rd], self.buf_s_data[self.buf_s_rd],
                self.buf_j_data[self.buf_j_rd])

            xbar_n_valid <<= grant_to_n != self.PORT_NONE
            xbar_n_out <<= xbar_select(grant_to_n,
                self.buf_e_data[self.buf_e_rd], self.buf_w_data[self.buf_w_rd],
                self.buf_n_data[self.buf_n_rd], self.buf_s_data[self.buf_s_rd],
                self.buf_j_data[self.buf_j_rd])

            xbar_s_valid <<= grant_to_s != self.PORT_NONE
            xbar_s_out <<= xbar_select(grant_to_s,
                self.buf_e_data[self.buf_e_rd], self.buf_w_data[self.buf_w_rd],
                self.buf_n_data[self.buf_n_rd], self.buf_s_data[self.buf_s_rd],
                self.buf_j_data[self.buf_j_rd])

            xbar_j_valid <<= grant_to_j != self.PORT_NONE
            xbar_j_out <<= xbar_select(grant_to_j,
                self.buf_e_data[self.buf_e_rd], self.buf_w_data[self.buf_w_rd],
                self.buf_n_data[self.buf_n_rd], self.buf_s_data[self.buf_s_rd],
                self.buf_j_data[self.buf_j_rd])

            self.e_flit_o <<= xbar_e_out
            self.w_flit_o <<= xbar_w_out
            self.n_flit_o <<= xbar_n_out
            self.s_flit_o <<= xbar_s_out
            self.loc_ej_flit <<= xbar_j_out

print("  - NoCRouter defined")


# ============================================================================
# HeteroMeshTop — 2x2 mesh connecting all 4 clusters
# ============================================================================

class HeteroMeshTop(Module):
    """Complete 2x2 mesh SoC topology for heterogeneous 4-core RISC-V system.

    Layout:
      [PerfCore0+L1Big0] (0,0)  ---  [PerfCore1+L1Big1] (1,0)
             |                                   |
      [EffCore0+L1Sm0] (0,1)  ---  [EffCore1+L1Sm1] (1,1)

    Submodules: 4 cores + 4 L1 caches + 1 CoherenceDir + 4 NoCRouters = 13 modules
    """

    def __init__(self):
        super().__init__("hetero_mesh_top")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # External retire/observation ports
        self.retire_valid_0 = Output(1, "retire_valid_0")
        self.retire_count_0 = Output(3, "retire_count_0")
        self.retire_valid_1 = Output(1, "retire_valid_1")
        self.retire_count_1 = Output(3, "retire_count_1")
        self.retire_valid_2 = Output(1, "retire_valid_2")
        self.retire_count_2 = Output(3, "retire_count_2")
        self.retire_valid_3 = Output(1, "retire_valid_3")
        self.retire_count_3 = Output(3, "retire_count_3")

        # =========================================================================
        # Instantiate 13 submodules
        # =========================================================================

        # ── 4 CPU cores ──
        perf_core_0 = PerformanceCore()
        perf_core_1 = PerformanceCore()
        eff_core_0 = EfficiencyCore()
        eff_core_1 = EfficiencyCore()

        # ── 4 L1 caches ──
        l1_big_0 = L1CacheBig()
        l1_big_1 = L1CacheBig()
        l1_sm_0 = L1CacheSmall()
        l1_sm_1 = L1CacheSmall()

        # ── Coherence Directory ──
        coh_dir = CoherenceDir()

        # ── 4 NoC Routers ──
        router_00 = NoCRouter()
        router_10 = NoCRouter()
        router_01 = NoCRouter()
        router_11 = NoCRouter()

        # =========================================================================
        # Cross-connect wires: Core <-> L1 Cache
        # =========================================================================

        # ── PerfCore0 <-> L1Big0 ──
        pc0_icache_req = Wire(1, "pc0_icache_req")
        pc0_icache_addr = Wire(XLEN, "pc0_icache_addr")
        pc0_icache_valid = Wire(1, "pc0_icache_valid")
        pc0_icache_rdata = Wire(64, "pc0_icache_rdata")
        pc0_dcache_req = Wire(1, "pc0_dcache_req")
        pc0_dcache_addr = Wire(XLEN, "pc0_dcache_addr")
        pc0_dcache_wdata = Wire(XLEN, "pc0_dcache_wdata")
        pc0_dcache_wen = Wire(1, "pc0_dcache_wen")
        pc0_dcache_valid = Wire(1, "pc0_dcache_valid")
        pc0_dcache_rdata = Wire(64, "pc0_dcache_rdata")
        pc0_dcache_ready = Wire(1, "pc0_dcache_ready")

        # ── PerfCore1 <-> L1Big1 ──
        pc1_icache_req = Wire(1, "pc1_icache_req")
        pc1_icache_addr = Wire(XLEN, "pc1_icache_addr")
        pc1_icache_valid = Wire(1, "pc1_icache_valid")
        pc1_icache_rdata = Wire(64, "pc1_icache_rdata")
        pc1_dcache_req = Wire(1, "pc1_dcache_req")
        pc1_dcache_addr = Wire(XLEN, "pc1_dcache_addr")
        pc1_dcache_wdata = Wire(XLEN, "pc1_dcache_wdata")
        pc1_dcache_wen = Wire(1, "pc1_dcache_wen")
        pc1_dcache_valid = Wire(1, "pc1_dcache_valid")
        pc1_dcache_rdata = Wire(64, "pc1_dcache_rdata")
        pc1_dcache_ready = Wire(1, "pc1_dcache_ready")

        # ── EffCore0 <-> L1Sm0 ──
        ec0_icache_req = Wire(1, "ec0_icache_req")
        ec0_icache_addr = Wire(XLEN, "ec0_icache_addr")
        ec0_icache_valid = Wire(1, "ec0_icache_valid")
        ec0_icache_rdata = Wire(64, "ec0_icache_rdata")
        ec0_dcache_req = Wire(1, "ec0_dcache_req")
        ec0_dcache_addr = Wire(XLEN, "ec0_dcache_addr")
        ec0_dcache_wdata = Wire(XLEN, "ec0_dcache_wdata")
        ec0_dcache_wen = Wire(1, "ec0_dcache_wen")
        ec0_dcache_valid = Wire(1, "ec0_dcache_valid")
        ec0_dcache_rdata = Wire(64, "ec0_dcache_rdata")
        ec0_dcache_ready = Wire(1, "ec0_dcache_ready")

        # ── EffCore1 <-> L1Sm1 ──
        ec1_icache_req = Wire(1, "ec1_icache_req")
        ec1_icache_addr = Wire(XLEN, "ec1_icache_addr")
        ec1_icache_valid = Wire(1, "ec1_icache_valid")
        ec1_icache_rdata = Wire(64, "ec1_icache_rdata")
        ec1_dcache_req = Wire(1, "ec1_dcache_req")
        ec1_dcache_addr = Wire(XLEN, "ec1_dcache_addr")
        ec1_dcache_wdata = Wire(XLEN, "ec1_dcache_wdata")
        ec1_dcache_wen = Wire(1, "ec1_dcache_wen")
        ec1_dcache_valid = Wire(1, "ec1_dcache_valid")
        ec1_dcache_rdata = Wire(64, "ec1_dcache_rdata")
        ec1_dcache_ready = Wire(1, "ec1_dcache_ready")

        # =========================================================================
        # Cross-connect wires: CoherenceDir <-> L1 Caches (probe signals)
        # =========================================================================
        probe_addr_0 = Wire(XLEN, "probe_addr_0")
        probe_valid_0 = Wire(1, "probe_valid_0")
        probe_inval_0 = Wire(1, "probe_inval_0")
        probe_ack_0 = Wire(1, "probe_ack_0")
        probe_addr_1 = Wire(XLEN, "probe_addr_1")
        probe_valid_1 = Wire(1, "probe_valid_1")
        probe_inval_1 = Wire(1, "probe_inval_1")
        probe_ack_1 = Wire(1, "probe_ack_1")
        probe_addr_2 = Wire(XLEN, "probe_addr_2")
        probe_valid_2 = Wire(1, "probe_valid_2")
        probe_inval_2 = Wire(1, "probe_inval_2")
        probe_ack_2 = Wire(1, "probe_ack_2")
        probe_addr_3 = Wire(XLEN, "probe_addr_3")
        probe_valid_3 = Wire(1, "probe_valid_3")
        probe_inval_3 = Wire(1, "probe_inval_3")
        probe_ack_3 = Wire(1, "probe_ack_3")

        # =========================================================================
        # Cross-connect wires: L1 Cache NoC <-> Router local ports
        # =========================================================================
        l1_0_noc_req = Wire(1, "l1_0_noc_req")
        l1_0_noc_addr = Wire(XLEN, "l1_0_noc_addr")
        l1_0_noc_rdata = Wire(64, "l1_0_noc_rdata")
        l1_0_noc_valid = Wire(1, "l1_0_noc_valid")
        l1_1_noc_req = Wire(1, "l1_1_noc_req")
        l1_1_noc_addr = Wire(XLEN, "l1_1_noc_addr")
        l1_1_noc_rdata = Wire(64, "l1_1_noc_rdata")
        l1_1_noc_valid = Wire(1, "l1_1_noc_valid")
        l1_2_noc_req = Wire(1, "l1_2_noc_req")
        l1_2_noc_addr = Wire(XLEN, "l1_2_noc_addr")
        l1_2_noc_rdata = Wire(64, "l1_2_noc_rdata")
        l1_2_noc_valid = Wire(1, "l1_2_noc_valid")
        l1_3_noc_req = Wire(1, "l1_3_noc_req")
        l1_3_noc_addr = Wire(XLEN, "l1_3_noc_addr")
        l1_3_noc_rdata = Wire(64, "l1_3_noc_rdata")
        l1_3_noc_valid = Wire(1, "l1_3_noc_valid")

        # Router interconnect wires (East/West/North/South between routers)
        r00e_flit = Wire(FLIT_WIDTH, "r00e_flit")
        r00e_valid = Wire(1, "r00e_valid")
        r00e_ready = Wire(1, "r00e_ready")
        r00s_flit = Wire(FLIT_WIDTH, "r00s_flit")
        r00s_valid = Wire(1, "r00s_valid")
        r00s_ready = Wire(1, "r00s_ready")
        r10s_flit = Wire(FLIT_WIDTH, "r10s_flit")
        r10s_valid = Wire(1, "r10s_valid")
        r10s_ready = Wire(1, "r10s_ready")
        r01e_flit = Wire(FLIT_WIDTH, "r01e_flit")
        r01e_valid = Wire(1, "r01e_valid")
        r01e_ready = Wire(1, "r01e_ready")

        # =========================================================================
        # Instantiate PerformanceCore 0 + L1CacheBig 0 at (0,0)
        # =========================================================================
        self.instantiate(perf_core_0, "perf_core_0", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "icache_req": pc0_icache_req,
            "icache_addr": pc0_icache_addr,
            "icache_valid": pc0_icache_valid,
            "icache_rdata": pc0_icache_rdata,
            "dcache_req": pc0_dcache_req,
            "dcache_addr": pc0_dcache_addr,
            "dcache_wdata": pc0_dcache_wdata,
            "dcache_wen": pc0_dcache_wen,
            "dcache_valid": pc0_dcache_valid,
            "dcache_rdata": pc0_dcache_rdata,
            "dcache_ready": pc0_dcache_ready,
            "core_stall": None,
            "core_halted": None,
            "retire_valid": self.retire_valid_0,
            "retire_count": self.retire_count_0,
        })
        self.instantiate(l1_big_0, "l1_big_0", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "req": pc0_icache_req | pc0_dcache_req,
            "addr": Mux(pc0_dcache_req, pc0_dcache_addr, pc0_icache_addr),
            "wdata": pc0_dcache_wdata,
            "wen": pc0_dcache_wen,
            "valid": pc0_icache_valid,
            "rdata": pc0_icache_rdata,
            "ready": pc0_dcache_ready,
            "probe_addr": probe_addr_0,
            "probe_valid": probe_valid_0,
            "probe_invalidate": probe_inval_0,
            "probe_ack": probe_ack_0,
            "noc_req": l1_0_noc_req,
            "noc_addr": l1_0_noc_addr,
            "noc_rdata": l1_0_noc_rdata,
            "noc_valid": l1_0_noc_valid,
            "cache_state": None,
        })

        # =========================================================================
        # Instantiate PerformanceCore 1 + L1CacheBig 1 at (1,0)
        # =========================================================================
        self.instantiate(perf_core_1, "perf_core_1", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "icache_req": pc1_icache_req,
            "icache_addr": pc1_icache_addr,
            "icache_valid": pc1_icache_valid,
            "icache_rdata": pc1_icache_rdata,
            "dcache_req": pc1_dcache_req,
            "dcache_addr": pc1_dcache_addr,
            "dcache_wdata": pc1_dcache_wdata,
            "dcache_wen": pc1_dcache_wen,
            "dcache_valid": pc1_dcache_valid,
            "dcache_rdata": pc1_dcache_rdata,
            "dcache_ready": pc1_dcache_ready,
            "core_stall": None,
            "core_halted": None,
            "retire_valid": self.retire_valid_1,
            "retire_count": self.retire_count_1,
        })
        self.instantiate(l1_big_1, "l1_big_1", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "req": pc1_icache_req | pc1_dcache_req,
            "addr": Mux(pc1_dcache_req, pc1_dcache_addr, pc1_icache_addr),
            "wdata": pc1_dcache_wdata,
            "wen": pc1_dcache_wen,
            "valid": pc1_icache_valid,
            "rdata": pc1_icache_rdata,
            "ready": pc1_dcache_ready,
            "probe_addr": probe_addr_1,
            "probe_valid": probe_valid_1,
            "probe_invalidate": probe_inval_1,
            "probe_ack": probe_ack_1,
            "noc_req": l1_1_noc_req,
            "noc_addr": l1_1_noc_addr,
            "noc_rdata": l1_1_noc_rdata,
            "noc_valid": l1_1_noc_valid,
            "cache_state": None,
        })

        # =========================================================================
        # Instantiate EfficiencyCore 0 + L1CacheSmall 0 at (0,1)
        # =========================================================================
        self.instantiate(eff_core_0, "eff_core_0", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "icache_req": ec0_icache_req,
            "icache_addr": ec0_icache_addr,
            "icache_valid": ec0_icache_valid,
            "icache_rdata": ec0_icache_rdata,
            "dcache_req": ec0_dcache_req,
            "dcache_addr": ec0_dcache_addr,
            "dcache_wdata": ec0_dcache_wdata,
            "dcache_wen": ec0_dcache_wen,
            "dcache_valid": ec0_dcache_valid,
            "dcache_rdata": ec0_dcache_rdata,
            "dcache_ready": ec0_dcache_ready,
            "core_stall": None,
            "core_halted": None,
            "retire_valid": self.retire_valid_2,
            "retire_count": self.retire_count_2,
        })
        self.instantiate(l1_sm_0, "l1_sm_0", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "req": ec0_icache_req | ec0_dcache_req,
            "addr": Mux(ec0_dcache_req, ec0_dcache_addr, ec0_icache_addr),
            "wdata": ec0_dcache_wdata,
            "wen": ec0_dcache_wen,
            "valid": ec0_icache_valid,
            "rdata": ec0_icache_rdata,
            "ready": ec0_dcache_ready,
            "probe_addr": probe_addr_2,
            "probe_valid": probe_valid_2,
            "probe_invalidate": probe_inval_2,
            "probe_ack": probe_ack_2,
            "noc_req": l1_2_noc_req,
            "noc_addr": l1_2_noc_addr,
            "noc_rdata": l1_2_noc_rdata,
            "noc_valid": l1_2_noc_valid,
            "cache_state": None,
        })

        # =========================================================================
        # Instantiate EfficiencyCore 1 + L1CacheSmall 1 at (1,1)
        # =========================================================================
        self.instantiate(eff_core_1, "eff_core_1", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "icache_req": ec1_icache_req,
            "icache_addr": ec1_icache_addr,
            "icache_valid": ec1_icache_valid,
            "icache_rdata": ec1_icache_rdata,
            "dcache_req": ec1_dcache_req,
            "dcache_addr": ec1_dcache_addr,
            "dcache_wdata": ec1_dcache_wdata,
            "dcache_wen": ec1_dcache_wen,
            "dcache_valid": ec1_dcache_valid,
            "dcache_rdata": ec1_dcache_rdata,
            "dcache_ready": ec1_dcache_ready,
            "core_stall": None,
            "core_halted": None,
            "retire_valid": self.retire_valid_3,
            "retire_count": self.retire_count_3,
        })
        self.instantiate(l1_sm_1, "l1_sm_1", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "req": ec1_icache_req | ec1_dcache_req,
            "addr": Mux(ec1_dcache_req, ec1_dcache_addr, ec1_icache_addr),
            "wdata": ec1_dcache_wdata,
            "wen": ec1_dcache_wen,
            "valid": ec1_icache_valid,
            "rdata": ec1_icache_rdata,
            "ready": ec1_dcache_ready,
            "probe_addr": probe_addr_3,
            "probe_valid": probe_valid_3,
            "probe_invalidate": probe_inval_3,
            "probe_ack": probe_ack_3,
            "noc_req": l1_3_noc_req,
            "noc_addr": l1_3_noc_addr,
            "noc_rdata": l1_3_noc_rdata,
            "noc_valid": l1_3_noc_valid,
            "cache_state": None,
        })

        # =========================================================================
        # Instantiate Coherence Directory
        # =========================================================================
        self.instantiate(coh_dir, "coh_dir", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "req_valid": l1_0_noc_req | l1_1_noc_req | l1_2_noc_req | l1_3_noc_req,
            "req_core_id": 0,
            "req_addr": l1_0_noc_addr,
            "req_is_write": 0,
            "resp_valid": None,
            "resp_action": None,
            "probe_targets": None,
            "probe_addr": probe_addr_0,
            "probe_valid": probe_valid_0,
            "probe_invalidate": probe_inval_0,
            "writeback_valid": 0,
            "writeback_data": 0,
            "writeback_to_core": None,
            "writeback_core_id": None,
        })

        # =========================================================================
        # Cross-connect: CoherenceDir broadcasts probe to all caches
        # =========================================================================
        with self.comb:
            probe_addr_1 <<= probe_addr_0
            probe_valid_1 <<= probe_valid_0
            probe_inval_1 <<= probe_inval_0
            probe_addr_2 <<= probe_addr_0
            probe_valid_2 <<= probe_valid_0
            probe_inval_2 <<= probe_inval_0
            probe_addr_3 <<= probe_addr_0
            probe_valid_3 <<= probe_valid_0
            probe_inval_3 <<= probe_inval_0

        # =========================================================================
        # Cross-connect: L1 NoC responses from router local ejection
        # =========================================================================
        with self.comb:
            l1_0_noc_rdata <<= router_00.loc_ej_flit[63:0]
            l1_0_noc_valid <<= router_00.loc_ej_valid
            l1_1_noc_rdata <<= router_10.loc_ej_flit[63:0]
            l1_1_noc_valid <<= router_10.loc_ej_valid
            l1_2_noc_rdata <<= router_01.loc_ej_flit[63:0]
            l1_2_noc_valid <<= router_01.loc_ej_valid
            l1_3_noc_rdata <<= router_11.loc_ej_flit[63:0]
            l1_3_noc_valid <<= router_11.loc_ej_valid

        # =========================================================================
        # Instantiate 4 NoC Routers with mesh interconnect
        # =========================================================================

        # Router (0,0) — PerfCore0 + L1Big0
        self.instantiate(router_00, "router_00", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "x_pos": Const(0, 3), "y_pos": Const(0, 3),
            # East → router (1,0)
            "e_flit": r00e_flit, "e_valid": r00e_valid, "e_ready_i": r00e_ready,
            # West → boundary
            "w_flit": Const(0, FLIT_WIDTH), "w_valid": 0, "w_ready_i": 0,
            # North → boundary
            "n_flit": Const(0, FLIT_WIDTH), "n_valid": 0, "n_ready_i": 0,
            # South → router (0,1)
            "s_flit": r00s_flit, "s_valid": r00s_valid, "s_ready_i": r00s_ready,
            # Local injection from L1Big0
            "loc_inj_flit": l1_0_noc_addr,
            "loc_inj_valid": l1_0_noc_req,
            "loc_ej_ready": 1,
            # Outputs
            "e_ready": None, "e_flit_o": None, "e_valid_o": None,
            "w_ready": None, "w_flit_o": None, "w_valid_o": None,
            "n_ready": None, "n_flit_o": None, "n_valid_o": None,
            "s_ready": None, "s_flit_o": None, "s_valid_o": None,
            "loc_inj_ready": None,
            "loc_ej_flit": None, "loc_ej_valid": None,
        })

        # Router (1,0) — PerfCore1 + L1Big1
        self.instantiate(router_10, "router_10", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "x_pos": Const(1, 3), "y_pos": Const(0, 3),
            # East → boundary
            "e_flit": Const(0, FLIT_WIDTH), "e_valid": 0, "e_ready_i": 0,
            # West → router (0,0)
            "w_flit": r00e_flit, "w_valid": r00e_valid, "w_ready_i": r00e_ready,
            # North → boundary
            "n_flit": Const(0, FLIT_WIDTH), "n_valid": 0, "n_ready_i": 0,
            # South → router (1,1)
            "s_flit": r10s_flit, "s_valid": r10s_valid, "s_ready_i": r10s_ready,
            # Local injection from L1Big1
            "loc_inj_flit": l1_1_noc_addr,
            "loc_inj_valid": l1_1_noc_req,
            "loc_ej_ready": 1,
            # Outputs
            "e_ready": None, "e_flit_o": None, "e_valid_o": None,
            "w_ready": r00e_ready, "w_flit_o": r00e_flit, "w_valid_o": r00e_valid,
            "n_ready": None, "n_flit_o": None, "n_valid_o": None,
            "s_ready": None, "s_flit_o": None, "s_valid_o": None,
            "loc_inj_ready": None,
            "loc_ej_flit": None, "loc_ej_valid": None,
        })

        # Router (0,1) — EffCore0 + L1Sm0
        self.instantiate(router_01, "router_01", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "x_pos": Const(0, 3), "y_pos": Const(1, 3),
            # East → router (1,1)
            "e_flit": r01e_flit, "e_valid": r01e_valid, "e_ready_i": r01e_ready,
            # West → boundary
            "w_flit": Const(0, FLIT_WIDTH), "w_valid": 0, "w_ready_i": 0,
            # North → router (0,0)
            "n_flit": r00s_flit, "n_valid": r00s_valid, "n_ready_i": r00s_ready,
            # South → boundary
            "s_flit": Const(0, FLIT_WIDTH), "s_valid": 0, "s_ready_i": 0,
            # Local injection from L1Sm0
            "loc_inj_flit": l1_2_noc_addr,
            "loc_inj_valid": l1_2_noc_req,
            "loc_ej_ready": 1,
            # Outputs
            "e_ready": None, "e_flit_o": None, "e_valid_o": None,
            "w_ready": None, "w_flit_o": None, "w_valid_o": None,
            "n_ready": r00s_ready, "n_flit_o": r00s_flit, "n_valid_o": r00s_valid,
            "s_ready": None, "s_flit_o": None, "s_valid_o": None,
            "loc_inj_ready": None,
            "loc_ej_flit": None, "loc_ej_valid": None,
        })

        # Router (1,1) — EffCore1 + L1Sm1
        self.instantiate(router_11, "router_11", port_map={
            "clk": self.clk, "rst_n": self.rst_n,
            "x_pos": Const(1, 3), "y_pos": Const(1, 3),
            # East → boundary
            "e_flit": Const(0, FLIT_WIDTH), "e_valid": 0, "e_ready_i": 0,
            # West → router (0,1)
            "w_flit": r01e_flit, "w_valid": r01e_valid, "w_ready_i": r01e_ready,
            # North → router (1,0)
            "n_flit": r10s_flit, "n_valid": r10s_valid, "n_ready_i": r10s_ready,
            # South → boundary
            "s_flit": Const(0, FLIT_WIDTH), "s_valid": 0, "s_ready_i": 0,
            # Local injection from L1Sm1
            "loc_inj_flit": l1_3_noc_addr,
            "loc_inj_valid": l1_3_noc_req,
            "loc_ej_ready": 1,
            # Outputs
            "e_ready": None, "e_flit_o": None, "e_valid_o": None,
            "w_ready": r01e_ready, "w_flit_o": r01e_flit, "w_valid_o": r01e_valid,
            "n_ready": r10s_ready, "n_flit_o": r10s_flit, "n_valid_o": r10s_valid,
            "s_ready": None, "s_flit_o": None, "s_valid_o": None,
            "loc_inj_ready": None,
            "loc_ej_flit": None, "loc_ej_valid": None,
        })

print("  - HeteroMeshTop defined")
print("  [skills.hetero_riscv4.dsl_modules] All modules loaded.")
