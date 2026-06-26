"""ThorVectorALU module package.

Public API:
    - valu_lane, valu_functional: L1 functional models.
    - ALU_* function-code constants.
"""

from __future__ import annotations

from thor_gpu.modules.vector_alu.layer_L1_behavior.src.behavior import (
    ALU_ADD, ALU_SLL, ALU_XOR, ALU_SRL, ALU_OR, ALU_AND, ALU_SUB, ALU_SLT, ALU_SLTU,
    ALU_FN_NAMES,
    valu_lane, valu_functional,
)

__all__ = [
    "ALU_ADD", "ALU_SLL", "ALU_XOR", "ALU_SRL", "ALU_OR", "ALU_AND",
    "ALU_SUB", "ALU_SLT", "ALU_SLTU", "ALU_FN_NAMES",
    "valu_lane", "valu_functional",
]
