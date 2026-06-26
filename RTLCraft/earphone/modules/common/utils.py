"""Shared bit/integer helpers used across Earphone module models.

These low-level utilities are layer-agnostic and are imported by L1 behavior
models, L2 cycle models, and L5 DSL generators alike.
"""

from __future__ import annotations


def _to_u32(v: int) -> int:
    """Return the low 32 bits of ``v`` as an unsigned value."""
    return v & 0xFFFFFFFF


def _to_s32(v: int) -> int:
    """Return ``v`` sign-extended to a signed 32-bit Python integer."""
    v = v & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def _sign_extend(v: int, width: int) -> int:
    """Sign-extend a ``width``-bit value to 32 bits and return as unsigned."""
    v = v & ((1 << width) - 1)
    if v & (1 << (width - 1)):
        v = v - (1 << width)
    return v & 0xFFFFFFFF


def _pack_u16_lanes(lanes: list) -> int:
    """Pack a list of 16-bit lane values into a 256-bit vector."""
    result = 0
    for i, lane in enumerate(lanes):
        result |= (lane & 0xFFFF) << (i * 16)
    return result


def _unpack_u16_lanes(vector: int, num_lanes: int = 16) -> list:
    """Unpack a 256-bit vector into a list of 16-bit unsigned lane values."""
    return [(vector >> (i * 16)) & 0xFFFF for i in range(num_lanes)]
