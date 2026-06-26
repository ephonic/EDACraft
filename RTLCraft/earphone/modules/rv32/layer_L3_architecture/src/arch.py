"""L3 ArchitectureIR for the EarphoneRV32 core.

This layer captures micro-architectural decisions that sit between the
instruction-set semantics (L1/L2) and the structural implementation (L4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RV32Architecture:
    """Micro-architecture description of EarphoneRV32."""

    name: str = "EarphoneRV32"
    isa: str = "RV32IM"
    pipeline: str = "single-cycle scalar with iterative M-extension"
    stages: List[str] = field(default_factory=lambda: ["IF", "ID", "EX", "MEM", "WB"])
    multiplier: str = "iterative 32x32 multiply (MUL/MULH/...)"
    divider: str = "iterative 32-bit divider (DIV/REM/...)"
    branch_predictor: str = "static not-taken"
    dmem_width: int = 32
    imem_width: int = 32
    reset_pc: int = 0x1000


ARCH = RV32Architecture()
