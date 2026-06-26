"""ThorVectorFPU module package.

Public API:
    - vfpu_lane, vfpu_functional: L1 functional models.
    - FPU_* function-code constants.
"""

from __future__ import annotations

from thor_gpu.modules.vector_fpu.layer_L1_behavior.src.behavior import (
    FPU_ADD, FPU_MUL, FPU_FMADD, FPU_FN_NAMES,
    vfpu_lane, vfpu_functional,
)

__all__ = [
    "FPU_ADD", "FPU_MUL", "FPU_FMADD", "FPU_FN_NAMES",
    "vfpu_lane", "vfpu_functional",
]
