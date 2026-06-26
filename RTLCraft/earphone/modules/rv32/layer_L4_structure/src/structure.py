"""L4 StructuralIR for the EarphoneRV32 core.

This layer defines the major sub-blocks and their interface contracts.  It is
intended to be used by the L5 DSL generator to instantiate and connect
components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class RV32Structure:
    """Structural decomposition of EarphoneRV32."""

    name: str = "EarphoneRV32"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock("pc_unit", "program counter generation and branch target", ["clk", "rst_n", "pc_next", "pc"]),
        SubBlock("regfile", "32-entry x 32-bit register file", ["clk", "rst_n", "rs1_addr", "rs2_addr", "rd_addr", "rd_wdata", "rs1_rdata", "rs2_rdata"]),
        SubBlock("decoder", "instruction decode and control signal generation", ["instr", "alu_op", "imm", "mem_op"]),
        SubBlock("alu", "arithmetic/logic operations and branch comparison", ["a", "b", "alu_op", "result", "zero", "lt", "ltu"]),
        SubBlock("muldiv_unit", "iterative M-extension multiply/divide", ["clk", "rst_n", "start", "done", "result"]),
        SubBlock("load_store_unit", "data memory interface", ["addr", "wdata", "mask", "we", "rdata", "valid"]),
    ])


STRUCTURE = RV32Structure()
