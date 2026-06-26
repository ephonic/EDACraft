"""ThorGpuSM module package.

Public API:
    - sm_functional: L1 functional SM model.
    - OP_* opcode constants.
    - Architectural parameters (XLEN, NLANE, VLEN, VREGS, NWARP, IMEM_DEPTH, ACCW).
"""

from __future__ import annotations

from thor_gpu.modules.gpu_sm.layer_L1_behavior.src.behavior import (
    XLEN, NLANE, VLEN, VREGS, NWARP, IMEM_DEPTH, ACCW,
    OP_NOP, OP_VLOAD, OP_VSTORE, OP_VADD, OP_VMUL, OP_VMAC,
    OP_BARRIER, OP_SLOAD, OP_DONE,
    sm_functional,
)

__all__ = [
    "XLEN", "NLANE", "VLEN", "VREGS", "NWARP", "IMEM_DEPTH", "ACCW",
    "OP_NOP", "OP_VLOAD", "OP_VSTORE", "OP_VADD", "OP_VMUL", "OP_VMAC",
    "OP_BARRIER", "OP_SLOAD", "OP_DONE",
    "sm_functional",
]
