"""Shared bit/integer helpers used across Thor-GPGPU module models.

These low-level utilities are layer-agnostic and are imported by L1 behavior
models, L2 cycle models, and L5 DSL generators alike. They operate on the
Thor-GPGPU vector layout: 8 lanes × 32-bit, packed into a 256-bit integer
(lane i occupies bits [i*32 +: 32]).
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
    """Sign-extend a ``width``-bit value to a Python signed integer."""
    v = v & ((1 << width) - 1)
    if v & (1 << (width - 1)):
        v = v - (1 << width)
    return v


def _mask(width: int) -> int:
    """Return an unsigned ``width``-bit all-ones mask."""
    return (1 << width) - 1


def _pack_u32_lanes(lanes: list) -> int:
    """Pack a list of 32-bit lane values into a 256-bit vector (8 lanes)."""
    result = 0
    for i, lane in enumerate(lanes):
        result |= (lane & 0xFFFFFFFF) << (i * 32)
    return result


def _unpack_u32_lanes(vector: int, num_lanes: int = 8) -> list:
    """Unpack a 256-bit vector into a list of 32-bit unsigned lane values."""
    return [(vector >> (i * 32)) & 0xFFFFFFFF for i in range(num_lanes)]


def _pack_i8_matrix(matrix: list) -> int:
    """Pack an 8x8 INT8 matrix (row-major) into a 512-bit integer.

    Element [i][j] occupies bits [(i*8 + j) * 8 +: 8].
    """
    result = 0
    for i in range(8):
        for j in range(8):
            result |= (matrix[i][j] & 0xFF) << ((i * 8 + j) * 8)
    return result


def _unpack_i8_matrix(value: int) -> list:
    """Unpack a 512-bit integer into an 8x8 INT8 matrix (row-major, signed)."""
    matrix = [[0] * 8 for _ in range(8)]
    for i in range(8):
        for j in range(8):
            raw = (value >> ((i * 8 + j) * 8)) & 0xFF
            matrix[i][j] = raw - 0x100 if raw >= 0x80 else raw
    return matrix


def _pack_i32_matrix(matrix: list) -> int:
    """Pack an 8x8 INT32 matrix (row-major) into a 2048-bit integer."""
    result = 0
    for i in range(8):
        for j in range(8):
            result |= (matrix[i][j] & 0xFFFFFFFF) << ((i * 8 + j) * 32)
    return result


def _unpack_i32_matrix(value: int) -> list:
    """Unpack a 2048-bit integer into an 8x8 INT32 matrix (row-major, signed)."""
    matrix = [[0] * 8 for _ in range(8)]
    for i in range(8):
        for j in range(8):
            raw = (value >> ((i * 8 + j) * 32)) & 0xFFFFFFFF
            matrix[i][j] = raw - 0x100000000 if raw >= 0x80000000 else raw
    return matrix


def _fp32_to_f32_bits(f: float) -> int:
    """Convert a Python float to IEEE-754 binary32 bit pattern."""
    import struct
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _f32_bits_to_fp32(bits: int) -> float:
    """Convert an IEEE-754 binary32 bit pattern to a Python float."""
    import struct
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]
