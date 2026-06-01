"""
skills/cpu_riscv64 — RISC-V 64-bit CPU with FPU (12nm, 2GHz target).

Architecture:
  - RV64IMAFD (integer + multiply/divide + atomic + float + double)
  - 7-stage in-order pipeline: F → D → I → E → M → W → C
  - Single-issue, in-order
  - FPU with FADD, FMUL, FMA, FCVT, FSQRT (4-8 cycle latency)
  - L1 I-cache 32KB, L1 D-cache 32KB
  - Gshare branch predictor (4KB PHT)
  - Targeting 12nm CMOS, 2GHz (500ps period)

Pipeline stages:
  F: Fetch — PCGen → I-Cache → Instruction Buffer
  D: Decode — instruction decode, register read
  I: Issue — scoreboard check, operand collection
  E: Execute — ALU/FPU/MUL/DIV (multi-cycle)
  M: Memory — D-Cache access (load/store)
  W: Writeback — result write to register file
  C: Commit — instruction retirement
"""
from __future__ import annotations

XLEN = 64
FLEN = 64      # double-precision FP
VLEN = 128     # vector (for future)
NREGS = 32     # architectural registers

# Pipeline latencies (in cycles)
L_ACCESS = 1   # cache access
L_MUL = 3      # integer multiply
L_DIV = 8      # integer divide
L_FADD = 4     # FP add
L_FMUL = 5     # FP multiply
L_FMA = 6      # FP multiply-accumulate
L_FCVT = 4     # FP convert
L_FSQRT = 12   # FP sqrt

# Cache parameters
ICACHE_SIZE = 32768   # 32KB
DCACHE_SIZE = 32768   # 32KB
CACHE_LINE = 64       # bytes
ICACHE_WAYS = 4       # 4-way set-associative
DCACHE_WAYS = 4
ICACHE_LATENCY = 2    # cycles
DCACHE_LATENCY = 2

# Branch predictor
BP_PHT_SIZE = 4096    # 4KB PHT
BP_BTB_SIZE = 256     # BTB entries
BP_RAS_DEPTH = 8      # return address stack

# PPA targets (12nm)
TARGET_FREQ_MHZ = 2000
TARGET_PERIOD_PS = 500
TECH_NODE = "12nm"
AREA_BUDGET = 200000  # NAND2 equivalent gates

# RISC-V opcodes
OP_LUI    = 0x37
OP_AUIPC  = 0x17
OP_JAL    = 0x6F
OP_JALR   = 0x67
OP_BRANCH = 0x63
OP_LOAD   = 0x03
OP_STORE  = 0x23
OP_RI     = 0x13  # register-immediate
OP_RR     = 0x33  # register-register
OP_FENCE  = 0x0F
OP_SYSTEM = 0x73
OP_FPU    = 0x53  # FP operations

# FPU function codes (funct7)
FUNC_FADD  = 0x00
FUNC_FSUB  = 0x01
FUNC_FMUL  = 0x02
FUNC_FDIV  = 0x03
FUNC_FSQRT = 0x0B  # sqrt.s
FUNC_FCVT  = 0x14  # FCVT integer<->FP

# Funct3 for branches
BRANCH_BEQ  = 0
BRANCH_BNE  = 1
BRANCH_BLT  = 4
BRANCH_BGE  = 5
BRANCH_BLTU = 6
BRANCH_BGEU = 7


def decode(inst: int):
    """Full RISC-V instruction decode."""
    opcode = inst & 0x7F
    rd = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    rs2 = (inst >> 20) & 0x1F
    funct7 = (inst >> 25) & 0x7F
    return opcode, rd, funct3, rs1, rs2, funct7


def sext(val: int, bits: int) -> int:
    """Sign-extend value from bits width to XLEN."""
    if val & (1 << (bits - 1)):
        return val | (~0 << bits)
    return val


def imm_i(inst: int) -> int:
    return sext(inst >> 20, 12)

def imm_s(inst: int) -> int:
    return sext(((inst >> 25) << 5) | ((inst >> 7) & 0x1F), 12)

def imm_b(inst: int) -> int:
    return sext(
        ((inst >> 31) << 12) | (((inst >> 7) & 1) << 11) |
        (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1), 13)

def imm_u(inst: int) -> int:
    return inst & 0xFFFFFFFFFFFFF000

def imm_j(inst: int) -> int:
    return sext(
        ((inst >> 31) << 20) | (((inst >> 12) & 0xFF) << 12) |
        (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1), 21)
