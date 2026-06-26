"""L1 BehaviorIR model for the ThorTensorCore.

Cycle-unaware functional reference for the 8x8x8 INT8 matrix-multiply-accumulate
unit: ``C[i][j] += sum_k A[i][k] * B[k][j]`` for k=0..7.

Operands are packed bit-integers:
  - A, B: 512-bit (8x8 INT8, row-major, element [i][j] at bits [(i*8+j)*8 +: 8])
  - C/result: 2048-bit (8x8 INT32, row-major, element [i][j] at bits [(i*8+j)*32 +: 32])
"""

from __future__ import annotations

from typing import Any, Dict

from thor_gpu.modules.common.utils import (
    _unpack_i8_matrix, _pack_i32_matrix, _unpack_i32_matrix,
)


def tc_mma_reference(a: int, b: int, c: int = 0, acc_en: int = 1) -> Dict[str, int]:
    """8x8x8 INT8->INT32 matrix-multiply-accumulate.

    If ``acc_en`` is 1, ``result = A*B + C``; otherwise ``result = A*B``.
    Returns ``{"result": <2048-bit>}``.
    """
    A = _unpack_i8_matrix(a)
    B = _unpack_i8_matrix(b)
    C = _unpack_i32_matrix(c) if acc_en else [[0] * 8 for _ in range(8)]
    out = [[0] * 8 for _ in range(8)]
    for i in range(8):
        for j in range(8):
            acc = C[i][j]
            for k in range(8):
                acc += A[i][k] * B[k][j]
            out[i][j] = acc & 0xFFFFFFFF
    return {"result": _pack_i32_matrix(out)}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorTensorCore",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "8x8x8 INT8->INT32 matrix-multiply-accumulate functional reference.",
        "m": 8, "n": 8, "k": 8,
        "a_dtype": "INT8", "b_dtype": "INT8", "c_dtype": "INT32",
        "a_width": 512, "b_width": 512, "c_width": 2048,
        "macs_per_mma": 512,
    }


__all__ = ["tc_mma_reference", "describe"]
