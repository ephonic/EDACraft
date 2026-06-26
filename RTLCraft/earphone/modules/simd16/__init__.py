"""EarphoneSIMD16 module package.

Public API:
    - simd16_int16_functional, simd16_fp16_mac_functional: L1 functional models.
    - SIMD_OP_* opcode constants.
"""

from __future__ import annotations

from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
    SIMD_OP_VADD,
    SIMD_OP_VSUB,
    SIMD_OP_VMUL,
    SIMD_OP_VAND,
    SIMD_OP_VOR,
    SIMD_OP_VXOR,
    SIMD_OP_VSLL,
    SIMD_OP_VSRL,
    SIMD_OP_VSRA,
    SIMD_OP_VCMP_EQ,
    SIMD_OP_VCMP_LT,
    simd16_int16_functional,
    simd16_fp16_mac_functional,
)

__all__ = [
    "SIMD_OP_VADD",
    "SIMD_OP_VSUB",
    "SIMD_OP_VMUL",
    "SIMD_OP_VAND",
    "SIMD_OP_VOR",
    "SIMD_OP_VXOR",
    "SIMD_OP_VSLL",
    "SIMD_OP_VSRL",
    "SIMD_OP_VSRA",
    "SIMD_OP_VCMP_EQ",
    "SIMD_OP_VCMP_LT",
    "simd16_int16_functional",
    "simd16_fp16_mac_functional",
]
