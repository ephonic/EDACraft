"""L1 BehaviorIR model for the EarphoneSIMD16 accelerator.

This module defines the cycle-unaware functional reference for the 16-lane
SIMD ALU: INT16 full-ALU operations and FP16 multiply-accumulate.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from earphone.modules.common.utils import _to_u32, _sign_extend


SIMD_OP_VADD = 0
SIMD_OP_VSUB = 1
SIMD_OP_VMUL = 2
SIMD_OP_VAND = 3
SIMD_OP_VOR = 4
SIMD_OP_VXOR = 5
SIMD_OP_VSLL = 6
SIMD_OP_VSRL = 7
SIMD_OP_VSRA = 8
SIMD_OP_VCMP_EQ = 9
SIMD_OP_VCMP_LT = 10

SIMD_FP_OP_VMAC = 0
SIMD_FP_OP_VMUL = 1


# Mapping from opcode value to human-readable name.
_INT16_OP_NAMES: Dict[int, str] = {
    SIMD_OP_VADD: "VADD",
    SIMD_OP_VSUB: "VSUB",
    SIMD_OP_VMUL: "VMUL",
    SIMD_OP_VAND: "VAND",
    SIMD_OP_VOR: "VOR",
    SIMD_OP_VXOR: "VXOR",
    SIMD_OP_VSLL: "VSLL",
    SIMD_OP_VSRL: "VSRL",
    SIMD_OP_VSRA: "VSRA",
    SIMD_OP_VCMP_EQ: "VCMP_EQ",
    SIMD_OP_VCMP_LT: "VCMP_LT",
}


def _fp16_to_f32(h: int) -> float:
    """Convert IEEE-754 FP16 (unsigned 16-bit pattern) to Python float."""
    h = h & 0xFFFF
    sign = (h >> 15) & 1
    exp = (h >> 10) & 0x1F
    mant = h & 0x3FF
    if exp == 0:
        if mant == 0:
            val = 0.0
        else:
            val = math.ldexp(mant / 1024.0, -14)
    elif exp == 0x1F:
        val = float('inf') if mant == 0 else float('nan')
    else:
        val = math.ldexp(1.0 + mant / 1024.0, exp - 15)
    return -val if sign else val


def _f32_to_fp16(f: float) -> int:
    """Convert Python float to IEEE-754 FP16, round-to-nearest-even."""
    if math.isnan(f):
        return 0x7E00
    if math.isinf(f):
        return 0xFC00 if f < 0 else 0x7C00
    if f == 0.0:
        return 0x0000
    sign = 0 if f >= 0 else 1
    f = abs(f)
    exp = math.floor(math.log2(f))
    if exp < -14:
        mant = round(f * 1024.0 * (2 ** 14))
        exp = 0
    elif exp > 15:
        return 0xFC00 if sign else 0x7C00
    else:
        mant = round((f / (2 ** exp) - 1.0) * 1024.0)
        if mant == 1024:
            mant = 0
            exp += 1
            if exp > 15:
                return 0xFC00 if sign else 0x7C00
        exp = exp + 15
    return (sign << 15) | (exp << 10) | (mant & 0x3FF)


def simd16_int16_functional(op: int, a: int, b: int, pred: int = 0xFFFF) -> int:
    """16-lane INT16 operation. Inputs/outputs are 256-bit packed vectors."""
    result = 0
    for lane in range(16):
        if not ((pred >> lane) & 1):
            continue
        av_u16 = (a >> (lane * 16)) & 0xFFFF
        bv_u16 = (b >> (lane * 16)) & 0xFFFF
        av = _sign_extend(av_u16, 16)
        bv = _sign_extend(bv_u16, 16)
        av_s16 = av_u16 - 0x10000 if av_u16 & 0x8000 else av_u16
        bv_s16 = bv_u16 - 0x10000 if bv_u16 & 0x8000 else bv_u16
        if op == SIMD_OP_VADD:
            rv = _to_u32(av + bv) & 0xFFFF
        elif op == SIMD_OP_VSUB:
            rv = _to_u32(av - bv) & 0xFFFF
        elif op == SIMD_OP_VMUL:
            rv = _to_u32(av * bv) & 0xFFFF
        elif op == SIMD_OP_VAND:
            rv = (av & bv) & 0xFFFF
        elif op == SIMD_OP_VOR:
            rv = (av | bv) & 0xFFFF
        elif op == SIMD_OP_VXOR:
            rv = (av ^ bv) & 0xFFFF
        elif op == SIMD_OP_VSLL:
            sh = bv & 0xF
            rv = (av << sh) & 0xFFFF
        elif op == SIMD_OP_VSRL:
            sh = bv & 0xF
            rv = (av & 0xFFFF) >> sh
        elif op == SIMD_OP_VSRA:
            sh = bv & 0xF
            rv = _to_u32(av_s16 >> sh) & 0xFFFF
        elif op == SIMD_OP_VCMP_EQ:
            rv = 0xFFFF if av == bv else 0
        elif op == SIMD_OP_VCMP_LT:
            rv = 0xFFFF if av_s16 < bv_s16 else 0
        else:
            rv = 0
        result |= rv << (lane * 16)
    return result


def simd16_fp16_mac_functional(a: int, b: int, c: int, pred: int = 0xFFFF) -> int:
    """16-lane FP16 multiply-accumulate: a*b + c."""
    result = 0
    for lane in range(16):
        if not ((pred >> lane) & 1):
            continue
        av = _fp16_to_f32((a >> (lane * 16)) & 0xFFFF)
        bv = _fp16_to_f32((b >> (lane * 16)) & 0xFFFF)
        cv = _fp16_to_f32((c >> (lane * 16)) & 0xFFFF)
        rv = _f32_to_fp16(av * bv + cv)
        result |= rv << (lane * 16)
    return result


def describe() -> Dict[str, Any]:
    """Return module metadata for document generation."""
    return {
        "name": "EarphoneSIMD16",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "16-lane INT16 ALU + FP16 MAC functional reference model.",
        "vector_width": 256,
        "lane_width": 16,
        "num_lanes": 16,
    }
