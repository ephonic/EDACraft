"""ThorCommon shared utility package.

Public API:
    Bit/integer helpers for the 8-lane x 32-bit vector layout and matrix packers.
"""

from __future__ import annotations

from thor_gpu.modules.common.utils import (
    _to_u32,
    _to_s32,
    _sign_extend,
    _mask,
    _pack_u32_lanes,
    _unpack_u32_lanes,
    _pack_i8_matrix,
    _unpack_i8_matrix,
    _pack_i32_matrix,
    _unpack_i32_matrix,
    _fp32_to_f32_bits,
    _f32_bits_to_fp32,
)

__all__ = [
    "_to_u32",
    "_to_s32",
    "_sign_extend",
    "_mask",
    "_pack_u32_lanes",
    "_unpack_u32_lanes",
    "_pack_i8_matrix",
    "_unpack_i8_matrix",
    "_pack_i32_matrix",
    "_unpack_i32_matrix",
    "_fp32_to_f32_bits",
    "_f32_bits_to_fp32",
]
