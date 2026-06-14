"""L1 BehaviorIR model for the EarphoneRV32 core.

This module implements a cycle-unaware RV32IM instruction-set simulator (ISS)
used as the golden reference for RTL verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# -----------------------------------------------------------------------------
# RV32IM opcodes and funct fields
# -----------------------------------------------------------------------------
OPCODE_LOAD = 0b0000011
OPCODE_STORE = 0b0100011
OPCODE_IMM = 0b0010011
OPCODE_REG = 0b0110011
OPCODE_LUI = 0b0110111
OPCODE_AUIPC = 0b0010111
OPCODE_BRANCH = 0b1100011
OPCODE_JAL = 0b1101111
OPCODE_JALR = 0b1100111
OPCODE_SYSTEM = 0b1110011

FUNCT3_LB = 0b000
FUNCT3_LH = 0b001
FUNCT3_LW = 0b010
FUNCT3_LBU = 0b100
FUNCT3_LHU = 0b101
FUNCT3_SB = 0b000
FUNCT3_SH = 0b001
FUNCT3_SW = 0b010
FUNCT3_ADDI = 0b000
FUNCT3_SLTI = 0b010
FUNCT3_XORI = 0b100
FUNCT3_ORI = 0b110
FUNCT3_ANDI = 0b111
FUNCT3_SLLI = 0b001
FUNCT3_SRXI = 0b101
FUNCT3_ADD = 0b000
FUNCT3_SUB = 0b000
FUNCT3_SLL = 0b001
FUNCT3_SLT = 0b010
FUNCT3_SLTU = 0b011
FUNCT3_XOR = 0b100
FUNCT3_SRL = 0b101
FUNCT3_SRA = 0b101
FUNCT3_OR = 0b110
FUNCT3_AND = 0b111
FUNCT3_BEQ = 0b000
FUNCT3_BNE = 0b001
FUNCT3_BLT = 0b100
FUNCT3_BGE = 0b101
FUNCT3_BLTU = 0b110
FUNCT3_BGEU = 0b111

FUNCT7_DEFAULT = 0b0000000
FUNCT7_SUB = 0b0100000
FUNCT7_SRA = 0b0100000
FUNCT7_SRAI = 0b0100000
FUNCT7_MULDIV = 0b0000001


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------
def _to_u32(v: int) -> int:
    return v & 0xFFFFFFFF


def _to_s32(v: int) -> int:
    v = v & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def _sign_extend(v: int, width: int) -> int:
    v = v & ((1 << width) - 1)
    if v & (1 << (width - 1)):
        v = v - (1 << width)
    return v & 0xFFFFFFFF


# -----------------------------------------------------------------------------
# Architectural state
# -----------------------------------------------------------------------------
@dataclass
class RV32IMState:
    """Architectural state for RV32IM functional model."""

    regs: List[int] = field(default_factory=lambda: [0] * 32)
    pc: int = 0x1000
    memory: Dict[int, int] = field(default_factory=dict)
    halted: bool = False

    def __post_init__(self) -> None:
        self.regs[0] = 0

    def load_byte(self, addr: int) -> int:
        return self.memory.get(addr, 0) & 0xFF

    def load_half(self, addr: int) -> int:
        return (self.load_byte(addr + 1) << 8) | self.load_byte(addr)

    def load_word(self, addr: int) -> int:
        return (
            (self.load_byte(addr + 3) << 24)
            | (self.load_byte(addr + 2) << 16)
            | (self.load_byte(addr + 1) << 8)
            | self.load_byte(addr)
        )

    def store_byte(self, addr: int, val: int):
        self.memory[addr] = val & 0xFF

    def store_half(self, addr: int, val: int):
        self.store_byte(addr, val & 0xFF)
        self.store_byte(addr + 1, (val >> 8) & 0xFF)

    def store_word(self, addr: int, val: int):
        self.store_byte(addr, val & 0xFF)
        self.store_byte(addr + 1, (val >> 8) & 0xFF)
        self.store_byte(addr + 2, (val >> 16) & 0xFF)
        self.store_byte(addr + 3, (val >> 24) & 0xFF)


# -----------------------------------------------------------------------------
# Instruction-set simulator
# -----------------------------------------------------------------------------
class RV32IM_ISS:
    """Functional (L1) model for the EarphoneRV32 core."""

    def __init__(self):
        self.state = RV32IMState()

    def reset(self, pc: int = 0x1000):
        self.state = RV32IMState(pc=pc)

    def load_program_words(self, words: List[int], entry_point: int = 0x1000):
        addr = entry_point
        for w in words:
            self.state.store_word(addr, w & 0xFFFFFFFF)
            addr += 4
        self.state.pc = entry_point

    def step(self) -> str:
        if self.state.halted:
            return "halted"
        pc = self.state.pc
        instr = self.state.load_word(pc)
        self.state.pc = _to_u32(pc + 4)
        return self._execute(instr, pc)

    def run(self, max_cycles: int = 10000):
        for _ in range(max_cycles):
            if self.state.halted:
                break
            self.step()

    def _execute(self, instr: int, pc: int) -> str:
        s = self.state
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F
        imm_i = _sign_extend(instr >> 20, 12)
        imm_s = _sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
        imm_b = _sign_extend(
            ((instr >> 31) << 12)
            | ((instr & 0x80) << 5)
            | ((instr >> 20) & 0x7E0)
            | ((instr >> 7) & 0x1E),
            13,
        )
        imm_u = instr & 0xFFFFF000
        imm_j = _sign_extend(
            ((instr >> 31) << 20)
            | ((instr >> 20) & 0xFF800)
            | ((instr >> 9) & 0x7FE)
            | ((instr >> 21) & 0x100000),
            21,
        )

        v1 = s.regs[rs1]
        v2 = s.regs[rs2]

        if opcode == OPCODE_IMM:
            result = 0
            if funct3 == FUNCT3_ADDI:
                result = _to_u32(v1 + imm_i)
            elif funct3 == FUNCT3_SLTI:
                result = 1 if _to_s32(v1) < _to_s32(imm_i) else 0
            elif funct3 == FUNCT3_XORI:
                result = _to_u32(v1 ^ imm_i)
            elif funct3 == FUNCT3_ORI:
                result = _to_u32(v1 | imm_i)
            elif funct3 == FUNCT3_ANDI:
                result = _to_u32(v1 & imm_i)
            elif funct3 == FUNCT3_SLLI:
                shamt = (instr >> 20) & 0x1F
                result = _to_u32(v1 << shamt)
            elif funct3 == FUNCT3_SRXI:
                shamt = (instr >> 20) & 0x1F
                if (instr >> 30) & 1:
                    result = _to_u32(_to_s32(v1) >> shamt)
                else:
                    result = v1 >> shamt
            if rd != 0:
                s.regs[rd] = result
            return f"imm op funct3={funct3}"

        elif opcode == OPCODE_REG:
            result = 0
            is_muldiv = funct7 == FUNCT7_MULDIV
            if is_muldiv:
                # RV32M extension
                if funct3 == 0b000:  # MUL
                    result = _to_u32(_to_s32(v1) * _to_s32(v2))
                elif funct3 == 0b001:  # MULH
                    result = _to_u32(((_to_s32(v1) * _to_s32(v2)) >> 32) & 0xFFFFFFFF)
                elif funct3 == 0b010:  # MULHSU
                    result = _to_u32(((_to_s32(v1) * (v2 & 0xFFFFFFFF)) >> 32) & 0xFFFFFFFF)
                elif funct3 == 0b011:  # MULHU
                    result = _to_u32(((v1 & 0xFFFFFFFF) * (v2 & 0xFFFFFFFF) >> 32) & 0xFFFFFFFF)
                elif funct3 == 0b100:  # DIV
                    if v2 == 0:
                        result = 0xFFFFFFFF
                    else:
                        result = _to_u32(int(_to_s32(v1) / _to_s32(v2)))
                elif funct3 == 0b101:  # DIVU
                    if v2 == 0:
                        result = 0xFFFFFFFF
                    else:
                        result = (v1 & 0xFFFFFFFF) // (v2 & 0xFFFFFFFF)
                elif funct3 == 0b110:  # REM
                    if v2 == 0:
                        result = v1
                    else:
                        result = _to_u32(_to_s32(v1) - int(_to_s32(v1) / _to_s32(v2)) * _to_s32(v2))
                elif funct3 == 0b111:  # REMU
                    if v2 == 0:
                        result = v1
                    else:
                        result = (v1 & 0xFFFFFFFF) % (v2 & 0xFFFFFFFF)
            else:
                if funct3 == FUNCT3_ADD:
                    result = _to_u32(v1 - v2) if funct7 == FUNCT7_SUB else _to_u32(v1 + v2)
                elif funct3 == FUNCT3_SLL:
                    result = _to_u32(v1 << (v2 & 0x1F))
                elif funct3 == FUNCT3_SLT:
                    result = 1 if _to_s32(v1) < _to_s32(v2) else 0
                elif funct3 == FUNCT3_XOR:
                    result = _to_u32(v1 ^ v2)
                elif funct3 == FUNCT3_SRL:
                    shamt = v2 & 0x1F
                    result = _to_u32(_to_s32(v1) >> shamt) if (instr >> 30) & 1 else v1 >> shamt
                elif funct3 == FUNCT3_OR:
                    result = _to_u32(v1 | v2)
                elif funct3 == FUNCT3_AND:
                    result = _to_u32(v1 & v2)
            if rd != 0:
                s.regs[rd] = _to_u32(result)
            return f"reg op funct3={funct3} muldiv={is_muldiv}"

        elif opcode == OPCODE_LOAD:
            addr = _to_u32(v1 + imm_i)
            val = 0
            if funct3 == FUNCT3_LB:
                val = _sign_extend(s.load_byte(addr), 8)
            elif funct3 == FUNCT3_LH:
                val = _sign_extend(s.load_half(addr), 16)
            elif funct3 == FUNCT3_LW:
                val = _to_s32(s.load_word(addr))
            elif funct3 == FUNCT3_LBU:
                val = s.load_byte(addr)
            elif funct3 == FUNCT3_LHU:
                val = s.load_half(addr)
            if rd != 0:
                s.regs[rd] = val & 0xFFFFFFFF
            return "load"

        elif opcode == OPCODE_STORE:
            addr = _to_u32(v1 + imm_s)
            val = v2
            if funct3 == FUNCT3_SB:
                s.store_byte(addr, val)
            elif funct3 == FUNCT3_SH:
                s.store_half(addr, val)
            elif funct3 == FUNCT3_SW:
                s.store_word(addr, val)
            return "store"

        elif opcode == OPCODE_LUI:
            if rd != 0:
                s.regs[rd] = imm_u
            return "lui"

        elif opcode == OPCODE_AUIPC:
            if rd != 0:
                s.regs[rd] = _to_u32(pc + imm_u)
            return "auipc"

        elif opcode == OPCODE_BRANCH:
            taken = False
            if funct3 == FUNCT3_BEQ:
                taken = v1 == v2
            elif funct3 == FUNCT3_BNE:
                taken = v1 != v2
            elif funct3 == FUNCT3_BLT:
                taken = _to_s32(v1) < _to_s32(v2)
            elif funct3 == FUNCT3_BGE:
                taken = _to_s32(v1) >= _to_s32(v2)
            elif funct3 == FUNCT3_BLTU:
                taken = (v1 & 0xFFFFFFFF) < (v2 & 0xFFFFFFFF)
            elif funct3 == FUNCT3_BGEU:
                taken = (v1 & 0xFFFFFFFF) >= (v2 & 0xFFFFFFFF)
            if taken:
                s.pc = _to_u32(pc + imm_b)
            return "branch"

        elif opcode == OPCODE_JAL:
            if rd != 0:
                s.regs[rd] = _to_u32(pc + 4)
            s.pc = _to_u32(pc + imm_j)
            return "jal"

        elif opcode == OPCODE_JALR:
            target = _to_u32(v1 + imm_i) & 0xFFFFFFFE
            if rd != 0:
                s.regs[rd] = _to_u32(pc + 4)
            s.pc = target
            return "jalr"

        elif opcode == OPCODE_SYSTEM:
            if funct3 == 0 and imm_i == 1:
                s.halted = True
                return "ebreak"
            return "system"

        else:
            s.halted = True
            return "unknown"
