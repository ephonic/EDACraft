"""L1 Functional Models — RISC-V 64 CPU pipeline stages."""
from __future__ import annotations
from typing import Callable, Dict, List, Tuple
from skills.cpu_riscv64 import *


def fetch_functional(**kwargs) -> Callable:
    """L1 Fetch: PC → I-Cache → instruction."""
    imem_depth = kwargs.get('imem_depth', 4096)
    def func(pc: int = 0, branch_taken: bool = False,
             branch_target: int = 0, icache_stall: bool = False,
             imem: List[int] = None) -> Dict:
        if imem is None: imem = [0] * imem_depth
        next_pc = branch_target if branch_taken else pc + 4
        inst = imem[(pc // 4) % imem_depth] if not icache_stall else 0x00000013  # NOP
        return {"inst": inst, "next_pc": next_pc & ~3, "valid": int(not icache_stall)}
    return func


def decode_functional(**kwargs) -> Callable:
    """L1 Decode: instruction → decoded fields + register read."""
    def func(inst: int = 0, rf_int: List[int] = None,
             rf_fp: List[float] = None) -> Dict:
        if rf_int is None: rf_int = [0] * NREGS
        if rf_fp is None: rf_fp = [0.0] * NREGS
        opcode, rd, funct3, rs1, rs2, funct7 = decode(inst)
        is_fp = (opcode == OP_FPU)
        rs1_val = rf_int[rs1] if not is_fp else rf_fp[rs1]
        rs2_val = rf_int[rs2] if not is_fp else rf_fp[rs2]
        return {
            "opcode": opcode, "rd": rd, "funct3": funct3,
            "rs1": rs1, "rs2": rs2, "funct7": funct7,
            "rs1_val": rs1_val, "rs2_val": rs2_val,
            "imm_i": imm_i(inst), "imm_s": imm_s(inst),
            "imm_b": imm_b(inst), "imm_u": imm_u(inst), "imm_j": imm_j(inst),
        }
    return func


def alu_functional(**kwargs) -> Callable:
    """L1 ALU: all integer arithmetic + logic operations."""
    xlen = kwargs.get('xlen', XLEN)
    def func(opcode: int = 0, funct3: int = 0, funct7: int = 0,
             rs1_val: int = 0, rs2_val: int = 0, imm: int = 0) -> Dict:
        is_ri = (opcode == OP_RI)
        b = rs2_val if opcode == OP_RR else imm
        result = 0; taken = None
        if opcode == OP_LUI: result = imm_u(imm)
        elif opcode == OP_AUIPC: result = imm_u(imm)
        elif opcode == OP_RI or opcode == OP_RR:
            if funct3 == 0:
                if funct7 == 0x20 and opcode == OP_RR: result = rs1_val - b  # SUB
                else: result = rs1_val + b                                   # ADD/ADDI
            elif funct3 == 1: result = rs1_val << (b & 0x3F)
            elif funct3 == 2:
                if funct7 == 0x20 and opcode == OP_RR: result = 1 if rs1_val < rs2_val else 0  # SLT
                else: result = 1 if rs1_val < b else 0
            elif funct3 == 3: result = 1 if (rs1_val & ((1<<xlen)-1)) < (b & ((1<<xlen)-1)) else 0
            elif funct3 == 4: result = rs1_val ^ b
            elif funct3 == 5:
                if funct7 == 0x20: result = rs1_val >> (b & 0x3F)  # SRA
                else: result = rs1_val >> (b & 0x3F)              # SRL
            elif funct3 == 6: result = rs1_val | b
            elif funct3 == 7: result = rs1_val & b
        elif opcode == OP_BRANCH:
            a, b = rs1_val, rs2_val
            if funct3 == BRANCH_BEQ:  taken = (a == b)
            elif funct3 == BRANCH_BNE: taken = (a != b)
            elif funct3 == BRANCH_BLT: taken = (a < b)
            elif funct3 == BRANCH_BGE: taken = (a >= b)
            elif funct3 == BRANCH_BLTU: taken = ((a & ((1<<xlen)-1)) < (b & ((1<<xlen)-1)))
            elif funct3 == BRANCH_BGEU: taken = ((a & ((1<<xlen)-1)) >= (b & ((1<<xlen)-1)))
        result = result & ((1 << xlen) - 1)
        return {"result": result, "taken": taken}
    return func


def fpu_functional(**kwargs) -> Callable:
    """L1 FPU: FADD, FSUB, FMUL, FDIV, FSQRT, FCVT."""
    def func(opcode: int = 0, funct7: int = 0, rs1_val: float = 0.0,
             rs2_val: float = 0.0) -> Dict:
        import struct, math
        result = 0.0
        f7_top = funct7 & 0x1F  # bits 31:27
        if f7_top == FUNC_FADD: result = rs1_val + rs2_val
        elif f7_top == FUNC_FSUB: result = rs1_val - rs2_val
        elif f7_top == FUNC_FMUL: result = rs1_val * rs2_val
        elif f7_top == FUNC_FDIV:
            result = rs1_val / rs2_val if rs2_val != 0 else float('inf')
        elif f7_top == FUNC_FSQRT:
            result = math.sqrt(rs1_val) if rs1_val >= 0 else 0.0
        bits = struct.pack('>d', result)
        return {"result": struct.unpack('>Q', bits)[0]}
    return func


def cache_functional(**kwargs) -> Callable:
    """L1 Cache: direct-mapped with tag/data/valid."""
    size = kwargs.get('size', ICACHE_SIZE)
    line_size = kwargs.get('line_size', CACHE_LINE)
    def func(addr: int = 0, req_valid: bool = False,
             tag_arr: List[int] = None, valid_arr: List[int] = None) -> Dict:
        n_lines = size // line_size
        if tag_arr is None: tag_arr = [0] * n_lines
        if valid_arr is None: valid_arr = [0] * n_lines
        idx = (addr // line_size) % n_lines
        tag = addr // (line_size * n_lines)
        hit = valid_arr[idx] and tag_arr[idx] == tag
        return {"hit": int(hit), "miss": int(req_valid and not hit)}
    return func


def bp_functional(**kwargs) -> Callable:
    """L1 Branch Predictor: gshare with PHT."""
    pht_size = kwargs.get('pht_size', BP_PHT_SIZE)
    def func(fetch_pc: int = 0, ghr: int = 0,
             pht: List[int] = None) -> Dict:
        if pht is None: pht = [2] * pht_size  # weakly taken
        idx = ((fetch_pc >> 2) ^ ghr) & (pht_size - 1)
        pred = pht[idx] >= 2  # taken if counter >= 2
        return {"pred_taken": int(pred), "pht_idx": idx}
    return func


FUNCTIONAL_MODELS = {
    "fetch": fetch_functional, "decode": decode_functional,
    "alu": alu_functional, "fpu": fpu_functional,
    "cache": cache_functional, "bp": bp_functional,
}
