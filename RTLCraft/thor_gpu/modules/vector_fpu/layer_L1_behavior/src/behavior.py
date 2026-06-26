"""L1 BehaviorIR model for the ThorVectorFPU.

Cycle-unaware functional reference for the 8-lane IEEE-754 FP32 vector FPU.
Operations: FADD(0), FMUL(1), FMADD(2) = s1*s2 + s3. Per-lane active mask.
"""

from __future__ import annotations

from typing import Any, Dict

from thor_gpu.modules.common.utils import (
    _unpack_u32_lanes, _pack_u32_lanes, _fp32_to_f32_bits, _f32_bits_to_fp32,
)


FPU_ADD = 0
FPU_MUL = 1
FPU_FMADD = 2

FPU_FN_NAMES: Dict[int, str] = {FPU_ADD: "FADD", FPU_MUL: "FMUL", FPU_FMADD: "FMADD"}


def vfpu_lane(fn: int, s1: int, s2: int, s3: int = 0) -> int:
    """One FP32 lane operation. Operands are IEEE-754 binary32 bit patterns."""
    f1 = _f32_bits_to_fp32(s1)
    f2 = _f32_bits_to_fp32(s2)
    f3 = _f32_bits_to_fp32(s3)
    if fn == FPU_ADD:
        return _fp32_to_f32_bits(f1 + f2)
    if fn == FPU_MUL:
        return _fp32_to_f32_bits(f1 * f2)
    if fn == FPU_FMADD:
        return _fp32_to_f32_bits(f1 * f2 + f3)
    return 0


def vfpu_functional(fn: int, src1: int, src2: int, src3: int = 0,
                    active_mask: int = 0xFF) -> Dict[str, int]:
    """8-lane FP32 vector FPU. Returns ``{"result": <256-bit>, "result_mask": <8-bit>}``."""
    s1 = _unpack_u32_lanes(src1)
    s2 = _unpack_u32_lanes(src2)
    s3 = _unpack_u32_lanes(src3)
    out = []
    rmask = 0
    for lane in range(8):
        if not ((active_mask >> lane) & 1):
            out.append(0)
            continue
        out.append(vfpu_lane(fn, s1[lane], s2[lane], s3[lane]))
        rmask |= 1 << lane
    return {"result": _pack_u32_lanes(out), "result_mask": rmask}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorVectorFPU",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "8-lane IEEE-754 FP32 vector FPU functional reference (predicated per-lane).",
        "lane_width": 32,
        "num_lanes": 8,
        "vector_width": 256,
        "datatype": "FP32",
        "latency_cycles": 1,
        "functions": ", ".join(FPU_FN_NAMES.values()),
    }


__all__ = [
    "FPU_ADD", "FPU_MUL", "FPU_FMADD", "FPU_FN_NAMES",
    "vfpu_lane", "vfpu_functional", "describe",
]
