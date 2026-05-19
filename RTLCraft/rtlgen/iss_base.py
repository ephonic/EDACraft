"""
rtlgen.iss_base — Abstract Instruction Set Simulator Interface

Provides ISSBase, an abstract base class that any ISA simulator must
implement. This enables ISA_Model to work with arbitrary ISAs (RISC-V,
ARM, MIPS, x86, custom DSPs) without hardcoded knowledge of internal
structure.

Usage:
    class MyISS(ISSBase):
        @property
        def isa_name(self): return "my_isa"
        def fetch_instruction(self, pc): ...
        def step(self): ...
        def get_pc(self): ...
        def set_pc(self, pc): ...
        def get_register(self, idx): ...
        def set_register(self, idx, val): ...
        def get_halted(self): ...
        def reset(self): ...

    model = ISA_Model(iss=MyISS())
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# =====================================================================
# RISC-V ABI Register Names (used by RV32ISS.get_isa_metadata)
# =====================================================================

RV32_REG_NAMES = [
    "x0",  "x1",  "x2",  "x3",  "x4",  "x5",  "x6",  "x7",
    "x8",  "x9",  "x10", "x11", "x12", "x13", "x14", "x15",
    "x16", "x17", "x18", "x19", "x20", "x21", "x22", "x23",
    "x24", "x25", "x26", "x27", "x28", "x29", "x30", "x31",
]

RV32_REG_ABI = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
]


class ISSBase(ABC):
    """Abstract base class for Instruction Set Simulators.

    All ISA-specific simulators must inherit from this class and
    implement the abstract methods. This provides a uniform interface
    that the architecture framework (ISA_Model, ArchSimulator) can
    use without knowing ISA internals.

    Required abstract methods:
    - isa_name: string identifier for the ISA
    - fetch_instruction(pc): read instruction from memory
    - step(): execute one instruction
    - get_pc / set_pc: program counter access
    - get_register / set_register: register file access
    - get_halted: check if simulation is halted
    - reset: reset simulator state

    Optional override:
    - get_isa_metadata(): return ISA-specific metadata
    """

    @property
    @abstractmethod
    def isa_name(self) -> str:
        """ISA identifier, e.g. 'riscv_rv32i', 'armv7m', 'mips32', 'custom_dsp'."""

    @abstractmethod
    def fetch_instruction(self, pc: int) -> int:
        """Fetch instruction word from memory at pc."""

    @abstractmethod
    def step(self) -> str:
        """Execute one instruction, return mnemonic."""

    @abstractmethod
    def get_pc(self) -> int:
        """Get current program counter."""

    @abstractmethod
    def set_pc(self, pc: int):
        """Set program counter."""

    @abstractmethod
    def get_register(self, idx: int) -> int:
        """Get register value by index."""

    @abstractmethod
    def set_register(self, idx: int, val: int):
        """Set register value by index."""

    @abstractmethod
    def get_halted(self) -> bool:
        """Check if the simulator is halted."""

    @abstractmethod
    def reset(self):
        """Reset simulator state to initial condition."""

    def get_isa_metadata(self) -> dict:
        """Return ISA metadata for code generation and verification.

        Subclasses should override to provide:
        - reg_names: list of register names (e.g. ['x0', 'x1', ...])
        - reg_count: number of general-purpose registers
        - xlen: register width in bits (32 or 64)
        - privilege_levels: list of privilege mode names
        - encoding: instruction encoding format
        - csr_names / sysreg_names: CSR/system register names (if any)

        Default returns minimal info with just isa_name.
        """
        return {"isa": self.isa_name}

    def get_register_name(self, idx: int) -> str:
        """Get human-readable register name for index (optional)."""
        return f"r{idx}"

    def run(self, max_cycles: int = 10000, stop_at_pc: Optional[int] = None):
        """Run until halted, max_cycles reached, or pc == stop_at_pc.

        Subclasses can override for more efficient execution.
        """
        for _ in range(max_cycles):
            if self.get_halted():
                break
            if stop_at_pc is not None and self.get_pc() == stop_at_pc:
                break
            self.step()
