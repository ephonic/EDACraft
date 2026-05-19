"""
skills.cpu.models — CPU Behavioral Models

RISC-V RV32I Instruction Set Simulator and CPU behavioral model.
Moved from rtlgen.processor_models to be domain-local to the CPU skill.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.core import BehavioralModule, Module, Input, Output
from rtlgen.iss_base import ISSBase, RV32_REG_NAMES, RV32_REG_ABI


# =====================================================================
# RISC-V RV32I Instruction Encodings (subset)
# =====================================================================

OPCODE_LOAD    = 0b0000011
OPCODE_STORE   = 0b0100011
OPCODE_IMM     = 0b0010011
OPCODE_REG     = 0b0110011
OPCODE_LUI     = 0b0110111
OPCODE_AUIPC   = 0b0010111
OPCODE_BRANCH  = 0b1100011
OPCODE_JAL     = 0b1101111
OPCODE_JALR    = 0b1100111
OPCODE_SYSTEM  = 0b1110011

FUNCT3_LB   = 0b000; FUNCT3_LH  = 0b001; FUNCT3_LW  = 0b010
FUNCT3_LBU  = 0b100; FUNCT3_LHU = 0b101
FUNCT3_SB   = 0b000; FUNCT3_SH  = 0b001; FUNCT3_SW  = 0b010
FUNCT3_ADDI = 0b000; FUNCT3_SLTI = 0b010; FUNCT3_XORI = 0b100
FUNCT3_ORI  = 0b110; FUNCT3_ANDI = 0b111
FUNCT3_SLLI = 0b001; FUNCT3_SRXI = 0b101
FUNCT3_ADD  = 0b000; FUNCT3_SUB  = 0b000; FUNCT3_SLL  = 0b001
FUNCT3_SLT  = 0b010; FUNCT3_XOR  = 0b100; FUNCT3_SRL  = 0b101
FUNCT3_OR   = 0b110; FUNCT3_AND  = 0b111
FUNCT3_BEQ  = 0b000; FUNCT3_BNE  = 0b001; FUNCT3_BLT  = 0b100
FUNCT3_BGE  = 0b101; FUNCT3_BLTU = 0b110; FUNCT3_BGEU = 0b111

FUNCT7_DEFAULT = 0b0000000
FUNCT7_SUB     = 0b0100000
FUNCT7_SRA     = 0b0100000
FUNCT7_SRAI    = 0b0100000


def _to_s32(v: int) -> int:
    v = v & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def _sign_extend(v: int, width: int) -> int:
    v = v & ((1 << width) - 1)
    if v & (1 << (width - 1)):
        v = v - (1 << width)
    return v & 0xFFFFFFFF


def _to_u32(v: int) -> int:
    return v & 0xFFFFFFFF


@dataclass
class RV32State:
    """RISC-V RV32I processor state."""
    regs: List[int] = field(default_factory=lambda: [0] * 32)
    pc: int = 0
    memory: Dict[int, int] = field(default_factory=dict)
    csr: Dict[int, int] = field(default_factory=dict)
    halted: bool = False
    cycle_count: int = 0

    def __post_init__(self):
        self.regs[0] = 0

    def load_byte(self, addr: int) -> int:
        return self.memory.get(addr, 0) & 0xFF

    def load_half(self, addr: int) -> int:
        return (self.load_byte(addr + 1) << 8) | self.load_byte(addr)

    def load_word(self, addr: int) -> int:
        b0 = self.load_byte(addr)
        b1 = self.load_byte(addr + 1)
        b2 = self.load_byte(addr + 2)
        b3 = self.load_byte(addr + 3)
        return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0

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

    def load_mem(self, addr: int, size: int) -> int:
        if size == 1:
            return self.load_byte(addr)
        if size == 2:
            return self.load_half(addr)
        if size == 4:
            return _to_s32(self.load_word(addr))
        return 0

    def store_mem(self, addr: int, val: int, size: int):
        if size == 1:
            self.store_byte(addr, val)
        elif size == 2:
            self.store_half(addr, val)
        elif size == 4:
            self.store_word(addr, val)


class RV32ISS(ISSBase):
    """RISC-V RV32I instruction set simulator.

    Supports RV32I base integer instruction subset.

    Usage:
        iss = RV32ISS()
        iss.load_program(machine_code_bytes, entry_point=0)
        iss.run(max_cycles=10000)
        print(iss.state.regs[10])  # a0 return value
    """

    def __init__(self):
        self.state = RV32State()
        self._trace: List[str] = []
        self._enable_trace = False

    def load_program(self, code: bytes, entry_point: int = 0):
        addr = entry_point
        for i in range(0, len(code), 4):
            chunk = code[i:i+4]
            if len(chunk) < 4:
                chunk = chunk + b'\x00' * (4 - len(chunk))
            word = struct.unpack('<I', chunk)[0]
            self.state.store_word(addr, word)
            addr += 4

    def load_program_words(self, words: List[int], entry_point: int = 0):
        addr = entry_point
        for w in words:
            self.state.store_word(addr, w)
            addr += 4

    def load_elf(self, elf_data: bytes):
        if elf_data[:4] != b'\x7fELF':
            raise ValueError("Not a valid ELF file")
        self.load_program(elf_data)

    def run(self, max_cycles: int = 10000, stop_at_pc: Optional[int] = None):
        for _ in range(max_cycles):
            if self.state.halted:
                break
            if stop_at_pc is not None and self.state.pc == stop_at_pc:
                break
            self.step()

    def step(self) -> str:
        state = self.state
        if state.halted:
            return "halted"

        pc = state.pc
        instr = state.load_word(pc)
        state.pc += 4
        state.cycle_count += 1

        mnemonic = self._execute(instr)

        if self._enable_trace:
            self._trace.append(f"pc={pc:#010x} instr={instr:#010x} {mnemonic}")

        return mnemonic

    def _execute(self, instr: int) -> str:
        s = self.state
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x7F
        funct7 = (instr >> 25) & 0x7F

        imm_i_signed = (instr >> 20)
        if imm_i_signed & 0x800:
            imm_i_signed = imm_i_signed - 0x10000

        if opcode == OPCODE_IMM:
            return self._exec_imm(s, rd, rs1, funct3, instr, imm_i_signed)
        elif opcode == OPCODE_REG:
            return self._exec_reg(s, rd, rs1, rs2, funct3, funct7)
        elif opcode == OPCODE_LOAD:
            return self._exec_load(s, rd, rs1, funct3, imm_i_signed)
        elif opcode == OPCODE_STORE:
            return self._exec_store(s, rs1, rs2, funct3, imm_i_signed)
        elif opcode == OPCODE_LUI:
            imm = instr & 0xFFFFF000
            s.regs[rd] = _to_u32(imm)
            s.regs[0] = 0
            return f"lui x{rd}, {imm:#x}"
        elif opcode == OPCODE_AUIPC:
            imm = instr & 0xFFFFF000
            s.regs[rd] = _to_u32(s.pc - 4 + imm)
            s.regs[0] = 0
            return f"auipc x{rd}, {imm:#x}"
        elif opcode == OPCODE_BRANCH:
            return self._exec_branch(s, rs1, rs2, funct3, instr)
        elif opcode == OPCODE_JAL:
            return self._exec_jal(s, rd, instr)
        elif opcode == OPCODE_JALR:
            return self._exec_jalr(s, rd, rs1, imm_i_signed)
        elif opcode == OPCODE_SYSTEM:
            if funct3 == 0 and rs2 == 0:
                if imm_i_signed == 0:
                    return "ecall"
                elif imm_i_signed == 1:
                    s.halted = True
                    return "ebreak"
            s.halted = True
            return f"system(funct3={funct3})"
        else:
            s.halted = True
            return f"unknown(opcode={opcode:#04x})"

    def _exec_imm(self, s, rd, rs1, funct3, instr, imm):
        val1 = s.regs[rs1]
        result = 0
        name = ""

        if funct3 == FUNCT3_ADDI:
            result = _to_u32(val1 + imm); name = f"addi x{rd}, x{rs1}, {imm}"
        elif funct3 == FUNCT3_SLTI:
            result = 1 if _to_s32(val1) < _to_s32(imm) else 0
            name = f"slti x{rd}, x{rs1}, {imm}"
        elif funct3 == FUNCT3_XORI:
            result = _to_u32(val1 ^ imm); name = f"xori x{rd}, x{rs1}, {imm}"
        elif funct3 == FUNCT3_ORI:
            result = _to_u32(val1 | imm); name = f"ori x{rd}, x{rs1}, {imm}"
        elif funct3 == FUNCT3_ANDI:
            result = _to_u32(val1 & imm); name = f"andi x{rd}, x{rs1}, {imm}"
        elif funct3 == FUNCT3_SLLI:
            shamt = (instr >> 20) & 0x1F
            result = _to_u32(val1 << shamt); name = f"slli x{rd}, x{rs1}, {shamt}"
        elif funct3 == FUNCT3_SRXI:
            shamt = (instr >> 20) & 0x1F
            funct7_val = (instr >> 25) & 0x7F
            if funct7_val == FUNCT7_SRAI:
                result = _to_s32(_to_s32(val1) >> shamt) & 0xFFFFFFFF
                name = f"srai x{rd}, x{rs1}, {shamt}"
            else:
                result = val1 >> shamt; name = f"srli x{rd}, x{rs1}, {shamt}"
        else:
            result = val1; name = f"imm_unknown x{rd}, x{rs1}"

        if rd != 0:
            s.regs[rd] = _to_u32(result)
        s.regs[0] = 0
        return name

    def _exec_reg(self, s, rd, rs1, rs2, funct3, funct7):
        val1 = s.regs[rs1]
        val2 = s.regs[rs2]
        result = 0
        name = ""

        if funct3 == FUNCT3_ADD and funct7 == FUNCT7_DEFAULT:
            result = _to_u32(val1 + val2); name = f"add x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_SUB and funct7 == FUNCT7_SUB:
            result = _to_u32(val1 - val2); name = f"sub x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_SLL and funct7 == FUNCT7_DEFAULT:
            result = _to_u32(val1 << (val2 & 0x1F)); name = f"sll x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_SLT and funct7 == FUNCT7_DEFAULT:
            result = 1 if _to_s32(val1) < _to_s32(val2) else 0
            name = f"slt x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_XOR and funct7 == FUNCT7_DEFAULT:
            result = _to_u32(val1 ^ val2); name = f"xor x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_SRL and funct7 == FUNCT7_DEFAULT:
            result = val1 >> (val2 & 0x1F); name = f"srl x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_SRL and funct7 == FUNCT7_SRA:
            result = _to_s32(_to_s32(val1) >> (val2 & 0x1F)) & 0xFFFFFFFF
            name = f"sra x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_OR and funct7 == FUNCT7_DEFAULT:
            result = _to_u32(val1 | val2); name = f"or x{rd}, x{rs1}, x{rs2}"
        elif funct3 == FUNCT3_AND and funct7 == FUNCT7_DEFAULT:
            result = _to_u32(val1 & val2); name = f"and x{rd}, x{rs1}, x{rs2}"
        else:
            result = val1; name = f"reg_unknown x{rd}, x{rs1}, x{rs2}"

        if rd != 0:
            s.regs[rd] = _to_u32(result)
        s.regs[0] = 0
        return name

    def _exec_load(self, s, rd, rs1, funct3, imm):
        addr = _to_u32(s.regs[rs1] + imm)
        size_map = {
            FUNCT3_LB: 1, FUNCT3_LH: 2, FUNCT3_LW: 4,
            FUNCT3_LBU: 1, FUNCT3_LHU: 2,
        }
        size = size_map.get(funct3, 4)
        val = s.load_mem(addr, size)

        if funct3 == FUNCT3_LB:
            val = _sign_extend(val, 8)
        elif funct3 == FUNCT3_LH:
            val = _sign_extend(val, 16)
        elif funct3 == FUNCT3_LBU:
            val = val & 0xFF
        elif funct3 == FUNCT3_LHU:
            val = val & 0xFFFF
        elif funct3 == FUNCT3_LW:
            val = _to_s32(val)

        if rd != 0:
            s.regs[rd] = val & 0xFFFFFFFF
        return f"load x{rd}, {imm}(x{rs1})"

    def _exec_store(self, s, rs1, rs2, funct3, imm):
        addr = _to_u32(s.regs[rs1] + imm)
        val = s.regs[rs2]
        size_map = {FUNCT3_SB: 1, FUNCT3_SH: 2, FUNCT3_SW: 4}
        size = size_map.get(funct3, 4)
        s.store_mem(addr, val, size)
        return f"store x{rs2}, {imm}(x{rs1})"

    def _exec_branch(self, s, rs1, rs2, funct3, instr):
        imm = _to_s32(((instr >> 31) << 12) | ((instr & 0x80) << 5) |
                       ((instr >> 20) & 0x7E0) | ((instr >> 7) & 0x1E))
        if imm & 0x1000:
            imm = imm - 0x2000
        target = s.pc - 4 + imm

        v1, v2 = s.regs[rs1], s.regs[rs2]
        taken = False
        cond_name = ""

        if funct3 == FUNCT3_BEQ:
            taken = (v1 == v2); cond_name = "beq"
        elif funct3 == FUNCT3_BNE:
            taken = (v1 != v2); cond_name = "bne"
        elif funct3 == FUNCT3_BLT:
            taken = (_to_s32(v1) < _to_s32(v2)); cond_name = "blt"
        elif funct3 == FUNCT3_BGE:
            taken = (_to_s32(v1) >= _to_s32(v2)); cond_name = "bge"
        elif funct3 == FUNCT3_BLTU:
            taken = (v1 < v2); cond_name = "bltu"
        elif funct3 == FUNCT3_BGEU:
            taken = (v1 >= v2); cond_name = "bgeu"

        if taken:
            s.pc = target
            return f"{cond_name} x{rs1}, x{rs2}, ->{target:#x}"
        return f"{cond_name} x{rs1}, x{rs2}, not taken"

    def _exec_jal(self, s, rd, instr):
        imm = _to_s32(((instr >> 31) << 20) | ((instr >> 20) & 0xFF800) |
                       ((instr >> 9) & 0x7FE) | ((instr >> 21) & 0x100000))
        target = s.pc - 4 + imm
        if rd != 0:
            s.regs[rd] = _to_u32(s.pc - 4)
        s.pc = target
        return f"jal x{rd}, {target:#x}"

    def _exec_jalr(self, s, rd, rs1, imm):
        target = _to_u32(s.regs[rs1] + imm) & 0xFFFFFFFE
        if rd != 0:
            s.regs[rd] = _to_u32(s.pc - 4)
        s.pc = target
        return f"jalr x{rd}, x{rs1}, {imm}"

    def set_reg(self, reg: int, val: int):
        self.state.regs[reg & 0x1F] = _to_u32(val)

    def get_reg(self, reg: int) -> int:
        return self.state.regs[reg & 0x1F]

    def set_mem_word(self, addr: int, val: int):
        self.state.store_word(addr, val)

    def get_mem_word(self, addr: int) -> int:
        return self.state.load_word(addr)

    def disassemble_single(self, instr: int) -> str:
        old_state = self.state
        self.state = RV32State()
        mnemonic = self._execute(instr)
        self.state = old_state
        return mnemonic

    def get_trace(self) -> List[str]:
        return list(self._trace)

    def enable_trace(self, on: bool = True):
        self._enable_trace = on

    @property
    def isa_name(self) -> str:
        return "riscv_rv32i"

    def fetch_instruction(self, pc: int) -> int:
        return self.state.load_word(pc)

    def get_pc(self) -> int:
        return self.state.pc

    def set_pc(self, pc: int):
        self.state.pc = pc

    def get_register(self, idx: int) -> int:
        return self.state.regs[idx & 0x1F]

    def set_register(self, idx: int, val: int):
        self.state.regs[idx & 0x1F] = _to_u32(val)
        self.state.regs[0] = 0

    def get_halted(self) -> bool:
        return self.state.halted

    def reset(self):
        self.state = RV32State()
        self._trace.clear()

    def get_isa_metadata(self) -> dict:
        return {
            "isa": self.isa_name,
            "reg_names": list(RV32_REG_NAMES),
            "reg_abi_names": list(RV32_REG_ABI),
            "reg_count": 32,
            "xlen": 32,
            "privilege_levels": ["M", "S", "U"],
            "encoding": "RISC-V",
            "instruction_width": 32,
        }

    def get_register_name(self, idx: int) -> str:
        idx = idx & 0x1F
        return f"{RV32_REG_NAMES[idx]} ({RV32_REG_ABI[idx]})"


class CPUModel:
    """CPU behavioral model container.

    Wraps an ISS for interaction with the RTLCraft ecosystem.

    Usage:
        cpu = CPUModel("riscv_cpu", isa="riscv_rv32i")
        cpu.iss.load_program(program_bytes)
        cpu.run(max_cycles=10000)
        print(cpu.get_status())
    """

    def __init__(self, name: str = "cpu", isa: str = "riscv_rv32i"):
        self.name = name
        self.isa = isa
        self.iss = RV32ISS()

    def load_program(self, code: bytes, entry_point: int = 0):
        self.iss.load_program(code, entry_point)

    def load_program_words(self, words: List[int], entry_point: int = 0):
        self.iss.load_program_words(words, entry_point)

    def run(self, max_cycles: int = 10000, stop_at_pc: Optional[int] = None):
        self.iss.run(max_cycles=max_cycles, stop_at_pc=stop_at_pc)

    def get_reg(self, reg: int) -> int:
        return self.iss.get_reg(reg)

    def set_reg(self, reg: int, val: int):
        self.iss.set_reg(reg, val)

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "isa": self.isa,
            "pc": self.iss.state.pc,
            "cycle_count": self.iss.state.cycle_count,
            "halted": self.iss.state.halted,
            "regs": dict(enumerate(self.iss.state.regs)),
        }


def _to_signed(val: int, width: int) -> int:
    mask = 1 << (width - 1)
    return (val & (mask - 1)) - (val & mask)


class BehavioralModelFactory:
    """Factory for creating behavioral models (CPU, GPGPU, ALU).

    Usage:
        factory = BehavioralModelFactory()
        cpu = factory.create_cpu("riscv_cpu")
        cpu.iss.load_program(program_bytes)
        cpu.iss.run(max_cycles=10000)

        gpu = factory.create_gpgpu("gpu", grid_dim=(4,1,1), block_dim=(32,1,1))
        gpu.load_kernel(my_kernel)
        gpu.run()
    """

    @staticmethod
    def create_cpu(name: str = "cpu", isa: str = "riscv_rv32i") -> CPUModel:
        return CPUModel(name, isa)

    @staticmethod
    def create_gpgpu(
        name: str = "gpu",
        grid_dim: Tuple[int, int, int] = (1, 1, 1),
        block_dim: Tuple[int, int, int] = (1, 1, 1),
    ) -> "GPGPUModel":
        from skills.gpgpu.models import GPGPUModel
        gpu = GPGPUModel(name)
        gpu.configure(grid_dim=grid_dim, block_dim=block_dim)
        return gpu

    @staticmethod
    def create_alu(
        name: str = "alu",
        width: int = 32,
        operations: Optional[Dict[str, Callable]] = None,
    ) -> "BehavioralModule":
        from rtlgen.core import BehavioralModule
        default_ops = {
            "add": lambda a, b: (a + b) & ((1 << width) - 1),
            "sub": lambda a, b: (a - b) & ((1 << width) - 1),
            "and": lambda a, b: a & b,
            "or":  lambda a, b: a | b,
            "xor": lambda a, b: a ^ b,
            "mul": lambda a, b: (a * b) & ((1 << width) - 1),
            "slt": lambda a, b: 1 if (_to_signed(a, width) < _to_signed(b, width)) else 0,
        }
        if operations:
            default_ops.update(operations)

        def alu_func(inputs: dict) -> dict:
            opcode = inputs.get("opcode", 0)
            op_names = list(default_ops.keys())
            if opcode < len(op_names):
                op = op_names[opcode]
                a = inputs.get("a", 0)
                b = inputs.get("b", 0)
                return {"result": default_ops[op](a, b)}
            return {"result": 0}

        return BehavioralModule(
            name=name,
            inputs=[("a", width), ("b", width), ("opcode", 4)],
            outputs=[("result", width)],
            func=alu_func,
        )
