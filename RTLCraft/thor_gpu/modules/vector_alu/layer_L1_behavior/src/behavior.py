"""L1 BehaviorIR model for the ThorVectorALU.

Cycle-unaware functional reference for the 8-lane INT32 vector ALU. Each lane
operates independently on a 32-bit slice of the 256-bit source vectors. Lanes
may be individually disabled via the 8-bit active mask.
"""

from __future__ import annotations

from typing import Any, Dict

from thor_gpu.modules.common.utils import (
    _to_u32,
    _to_s32,
    _unpack_u32_lanes,
    _pack_u32_lanes,
)


# Per-lane ALU function codes (match the Thor vALU reference).
ALU_ADD = 0
ALU_SLL = 1
ALU_XOR = 4
ALU_SRL = 5
ALU_OR = 6
ALU_AND = 7
ALU_SUB = 10
ALU_SLT = 12
ALU_SLTU = 14

ALU_FN_NAMES: Dict[int, str] = {
    ALU_ADD: "ADD",
    ALU_SLL: "SLL",
    ALU_XOR: "XOR",
    ALU_SRL: "SRL",
    ALU_OR: "OR",
    ALU_AND: "AND",
    ALU_SUB: "SUB",
    ALU_SLT: "SLT",
    ALU_SLTU: "SLTU",
}


def valu_lane(fn: int, s1: int, s2: int) -> int:
    """Execute one 32-bit lane operation. Inputs are unsigned 32-bit patterns."""
    u1 = _to_u32(s1)
    u2 = _to_u32(s2)
    si1 = _to_s32(s1)
    si2 = _to_s32(s2)
    if fn == ALU_ADD:
        return _to_u32(si1 + si2)
    if fn == ALU_SLL:
        return _to_u32(u1 << (u2 & 0x1F))
    if fn == ALU_XOR:
        return u1 ^ u2
    if fn == ALU_SRL:
        return u1 >> (u2 & 0x1F)
    if fn == ALU_OR:
        return u1 | u2
    if fn == ALU_AND:
        return u1 & u2
    if fn == ALU_SUB:
        return _to_u32(si1 - si2)
    if fn == ALU_SLT:
        return 1 if si1 < si2 else 0
    if fn == ALU_SLTU:
        return 1 if u1 < u2 else 0
    return 0


def valu_functional(fn: int, src1: int, src2: int, active_mask: int = 0xFF) -> Dict[str, int]:
    """8-lane INT32 vector ALU.

    Returns ``{"result": <256-bit>, "result_mask": <8-bit>}``. Disabled lanes
    produce zero and their result-mask bit is cleared.
    """
    s1 = _unpack_u32_lanes(src1)
    s2 = _unpack_u32_lanes(src2)
    out = []
    rmask = 0
    for lane in range(8):
        if not ((active_mask >> lane) & 1):
            out.append(0)
            continue
        out.append(valu_lane(fn, s1[lane], s2[lane]))
        rmask |= 1 << lane
    return {"result": _pack_u32_lanes(out), "result_mask": rmask}


def describe() -> Dict[str, Any]:
    """Return module metadata for document generation."""
    return {
        "name": "ThorVectorALU",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "8-lane INT32 vector ALU functional reference (predicated per-lane).",
        "lane_width": 32,
        "num_lanes": 8,
        "vector_width": 256,
        "latency_cycles": 1,
        "functions": ", ".join(ALU_FN_NAMES.values()),
    }


__all__ = [
    "ALU_ADD", "ALU_SLL", "ALU_XOR", "ALU_SRL", "ALU_OR", "ALU_AND",
    "ALU_SUB", "ALU_SLT", "ALU_SLTU", "ALU_FN_NAMES",
    "valu_lane", "valu_functional", "describe",
]
