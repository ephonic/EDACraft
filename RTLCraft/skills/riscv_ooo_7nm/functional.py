"""Layer 1 — Functional models (pure behavior, no timing).

Each function takes keyword arguments and returns a dict of outputs.
These serve as the golden reference for L2 and L3 verification.
"""

from __future__ import annotations

from typing import Callable, Dict


def ooo_core_functional(**kwargs) -> Callable:
    """Top-level OoO core: models instruction flow through the pipeline.

    Inputs: inst_valid, inst[31:0], regfile[31:0][63:0]
    Outputs: result_valid, rd_addr, rd_data, pc_next
    """
    def core(instr: int = 0x13, rs1_val: int = 0, rs2_val: int = 0,
             pc: int = 0, valid: int = 1) -> Dict:
        if not valid:
            return {"result_valid": 0, "rd": 0, "rd_val": 0, "pc_next": pc + 4, "exception": 0}

        opcode = instr & 0x7f
        rd = (instr >> 7) & 0x1f
        funct3 = (instr >> 12) & 0x7
        funct7 = (instr >> 25) & 0x7f
        rs1 = (instr >> 15) & 0x1f
        rs2 = (instr >> 20) & 0x1f
        imm_i = (instr >> 20) & 0xfff
        if imm_i & 0x800:
            imm_i |= -0x1000
        imm_s = ((instr >> 7) & 0x1f) | ((instr >> 25) & 0x7f) << 5
        if imm_s & 0x800:
            imm_s |= -0x1000
        imm_b = ((instr >> 8) & 0xf) << 1 | ((instr >> 25) & 0x3f) << 5 | ((instr >> 7) & 0x1) << 11 | ((instr >> 31) & 0x1) << 12
        if imm_b & 0x1000:
            imm_b |= -0x2000
        imm_u = instr & 0xfffff000
        imm_j = ((instr >> 21) & 0x3ff) << 1 | ((instr >> 20) & 0x1) << 11 | ((instr >> 12) & 0xff) << 12 | ((instr >> 31) & 0x1) << 19
        if imm_j & 0x100000:
            imm_j |= -0x200000

        result_valid = 1
        rd_val = 0
        pc_next = pc + 4
        exception = 0
        mem_read = 0
        mem_write = 0
        mem_addr = 0
        mem_wdata = 0

        if opcode == 0x37:  # LUI
            rd_val = imm_u
        elif opcode == 0x17:  # AUIPC
            rd_val = pc + imm_u
        elif opcode == 0x6f:  # JAL
            rd_val = pc + 4
            pc_next = pc + imm_j
        elif opcode == 0x67:  # JALR
            rd_val = pc + 4
            pc_next = (rs1_val + imm_i) & ~1
        elif opcode == 0x63:  # BRANCH
            result_valid = 0
            taken = False
            if funct3 == 0: taken = rs1_val == rs2_val         # BEQ
            elif funct3 == 1: taken = rs1_val != rs2_val        # BNE
            elif funct3 == 4: taken = (rs1_val & 0x8000000000000000) > (rs2_val & 0x8000000000000000)  # BLT
            elif funct3 == 5: taken = (rs1_val & 0x8000000000000000) < (rs2_val & 0x8000000000000000)  # BGE
            elif funct3 == 6: taken = rs1_val < rs2_val          # BLTU
            elif funct3 == 7: taken = rs1_val >= rs2_val         # BGEU
            if taken:
                pc_next = pc + imm_b
        elif opcode == 0x03:  # LOAD
            mem_addr = rs1_val + imm_i
            mem_read = 1
            rd_val = 0  # placeholder, replaced by memory
        elif opcode == 0x23:  # STORE
            mem_addr = rs1_val + imm_s
            mem_write = 1
            mem_wdata = rs2_val
            result_valid = 0
        elif opcode == 0x13:  # OP-IMM
            if funct3 == 0: rd_val = rs1_val + imm_i           # ADDI
            elif funct3 == 1: rd_val = rs1_val << (imm_i & 0x3f)  # SLLI
            elif funct3 == 2: rd_val = rs1_val if (rs1_val >> 63) else 0 if (rs1_val < imm_i) else (rs1_val >> imm_i)  # SLTI (approx)
            elif funct3 == 3: rd_val = 1 if rs1_val < imm_i else 0  # SLTIU (simplified)
            elif funct3 == 4: rd_val = rs1_val ^ imm_i          # XORI
            elif funct3 == 5:
                if funct7 >> 6: rd_val = rs1_val >> (imm_i & 0x3f)  # SRAI
                else: rd_val = rs1_val >> (imm_i & 0x3f)           # SRLI (simplified for unsigned)
            elif funct3 == 6: rd_val = rs1_val | imm_i           # ORI
            elif funct3 == 7: rd_val = rs1_val & imm_i           # ANDI
        elif opcode == 0x33:  # OP
            if funct3 == 0:
                if funct7 >> 6: rd_val = rs1_val - rs2_val       # SUB
                else: rd_val = rs1_val + rs2_val                  # ADD
            elif funct3 == 1: rd_val = rs1_val << (rs2_val & 0x3f)  # SLL
            elif funct3 == 2: rd_val = 1 if rs1_val < rs2_val else 0  # SLT
            elif funct3 == 3: rd_val = 1 if (rs1_val & 0xffffffffffffffff) < (rs2_val & 0xffffffffffffffff) else 0  # SLTU
            elif funct3 == 4: rd_val = rs1_val ^ rs2_val          # XOR
            elif funct3 == 5:
                if funct7 >> 6: rd_val = rs1_val >> (rs2_val & 0x3f)  # SRA
                else: rd_val = rs1_val >> (rs2_val & 0x3f)           # SRL
            elif funct3 == 6: rd_val = rs1_val | rs2_val           # OR
            elif funct3 == 7: rd_val = rs1_val & rs2_val           # AND
        elif opcode == 0x1b:  # OP-IMM-32
            rs1_val_32 = rs1_val & 0xffffffff
            if funct3 == 0:
                rd_val = (rs1_val_32 + imm_i) & 0xffffffff
                if rd_val & 0x80000000: rd_val |= -0x100000000
        elif opcode == 0x3b:  # OP-32
            a, b = rs1_val & 0xffffffff, rs2_val & 0xffffffff
            if funct3 == 0:
                if funct7 >> 6: rd_val = (a - b) & 0xffffffff
                else: rd_val = (a + b) & 0xffffffff
                if rd_val & 0x80000000: rd_val |= -0x100000000
        elif opcode == 0x73:  # SYSTEM (ecall/ebreak/csrrw)
            if funct3 == 0:
                if imm_i == 0: exception = 11  # ECALL
                elif imm_i == 1: exception = 3  # EBREAK

        return {
            "result_valid": result_valid,
            "rd": rd,
            "rd_val": rd_val,
            "pc_next": pc_next,
            "exception": exception,
            "mem_read": mem_read,
            "mem_write": mem_write,
            "mem_addr": mem_addr,
            "mem_wdata": mem_wdata,
        }
    return core


def fetch_functional(**kwargs) -> Callable:
    """Instruction fetch: PC → I-cache → instruction stream."""
    def fetch(pc: int = 0, branch_taken: int = 0, branch_target: int = 0,
              redirect: int = 0, redirect_pc: int = 0,
              icache_stall: int = 0) -> Dict:
        if redirect:
            return {"pc_next": redirect_pc, "fetch_valid": 1}
        if branch_taken:
            return {"pc_next": branch_target, "fetch_valid": 1}
        if icache_stall:
            return {"pc_next": pc, "fetch_valid": 0}
        return {"pc_next": pc + 16, "fetch_valid": 1}  # 8-wide = 16 bytes = 4 instr
    return fetch


def bpredict_functional(**kwargs) -> Callable:
    """Branch predictor: gshare + BTB + RAS."""
    def predict(pc: int = 0, hist: int = 0, ras_ptr: int = 0,
                is_call: int = 0, is_return: int = 0) -> Dict:
        taken = ((pc ^ hist) & 0x1fff) > 0x1000  # simple gshare
        target = pc + 4
        if is_return:
            target = 0  # RAS will supply
        elif taken:
            target = pc + 8  # BTB target (simplified)
        return {"pred_taken": taken, "pred_target": target, "pred_valid": 1}
    return predict


def rename_functional(**kwargs) -> Callable:
    """Register renaming: architectural reg → physical reg."""
    def rename(arch_rs1: int = 0, arch_rs2: int = 0, arch_rd: int = 0,
               free_preg: int = 0, rat: int = 0) -> Dict:
        phys_rs1 = (rat >> (arch_rs1 * 8)) & 0xff
        phys_rs2 = (rat >> (arch_rs2 * 8)) & 0xff
        return {
            "phys_rs1": phys_rs1 if arch_rs1 != 0 else 0,
            "phys_rs2": phys_rs2 if arch_rs2 != 0 else 0,
            "phys_rd": free_preg,
            "new_rat_entry": (free_preg << (arch_rd * 8)),
        }
    return rename


def rob_functional(**kwargs) -> Callable:
    """Reorder buffer: track instruction completion and retirement."""
    def rob(pc: int = 0, rd: int = 0, pdst: int = 0,
            completed: int = 0, exception: int = 0,
            head: int = 0, tail: int = 0) -> Dict:
        committed = 0
        new_head = head
        if completed and not exception:
            committed = 1
            new_head = (head + 1) & 0xff
        return {
            "commit_valid": committed,
            "commit_pdst": pdst,
            "commit_rd": rd,
            "commit_pc": pc,
            "new_head": new_head,
            "full": ((tail + 1) & 0xff) == head,
            "empty": head == tail,
        }
    return rob
