"""Golden reference model for the fully pipelined FP16 activation/trig SFU."""

from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Callable

from .lut_generator import (
    COEFF_FRAC_BITS,
    COS_QUADRANT_TABLE,
    SIGMOID_TABLE,
    SIN_QUADRANT_TABLE,
    TANH_TABLE,
)


FP16_WIDTH = 16
Q12_FRAC_BITS = 12
Q12_ONE = 1 << Q12_FRAC_BITS
Q24_FRAC_BITS = 24
Q24_ONE = 1 << Q24_FRAC_BITS
COEFF_ONE = 1 << COEFF_FRAC_BITS

SIGMOID_MAX_Q12 = 8 * Q12_ONE
TANH_MAX_Q12 = 4 * Q12_ONE

HALF_PI_Q24 = int(round((math.pi / 2.0) * Q24_ONE))
PI_Q24 = int(round(math.pi * Q24_ONE))
TWO_PI_Q24 = int(round((2.0 * math.pi) * Q24_ONE))

TRIG_REDUCE_RECIP_SHIFT = 40
TRIG_REDUCE_RECIP = int(round((1 << TRIG_REDUCE_RECIP_SHIFT) / HALF_PI_Q24))
TRIG_NORMALIZE_SHIFT = 28
TRIG_NORMALIZE_RECIP = int(round((Q12_ONE << TRIG_NORMALIZE_SHIFT) / HALF_PI_Q24))

OP_RELU = 0
OP_SIGMOID = 1
OP_TANH = 2
OP_SIN = 3
OP_COS = 4

OP_NAMES = {
    OP_RELU: "relu",
    OP_SIGMOID: "sigmoid",
    OP_TANH: "tanh",
    OP_SIN: "sin",
    OP_COS: "cos",
}


@dataclass(frozen=True)
class Fp16Fields:
    sign: int
    exp: int
    frac: int

    @property
    def is_zero(self) -> bool:
        return self.exp == 0 and self.frac == 0

    @property
    def is_subnormal(self) -> bool:
        return self.exp == 0 and self.frac != 0

    @property
    def is_inf(self) -> bool:
        return self.exp == 0x1F and self.frac == 0

    @property
    def is_nan(self) -> bool:
        return self.exp == 0x1F and self.frac != 0


def fp16_to_float(bits: int) -> float:
    return struct.unpack(">e", int(bits & 0xFFFF).to_bytes(2, "big"))[0]


def float_to_fp16_bits(value: float) -> int:
    if math.isnan(value):
        return 0x7E00
    if math.isinf(value):
        return 0x7C00 if value > 0 else 0xFC00
    try:
        return int.from_bytes(struct.pack(">e", float(value)), "big")
    except OverflowError:
        return 0x7C00 if value > 0 else 0xFC00


def decode_fp16(bits: int) -> Fp16Fields:
    bits &= 0xFFFF
    return Fp16Fields(
        sign=(bits >> 15) & 1,
        exp=(bits >> 10) & 0x1F,
        frac=bits & 0x3FF,
    )


def _mask(width: int) -> int:
    return (1 << width) - 1


def q16_magnitude_to_fp16_bits(magnitude_q16: int) -> int:
    """Convert a non-negative Q0.16 magnitude in [0, 1] to FP16.

    This mirrors the intended hardware behavior: no floating helper, just
    leading-one based normalization plus truncation. Tiny values are emitted as
    subnormals, and values >= 1 clamp to exactly 1.0.
    """
    if magnitude_q16 <= 0:
        return 0
    if magnitude_q16 >= COEFF_ONE:
        return 0x3C00

    if magnitude_q16 < 4:
        frac = min(0x3FF, magnitude_q16 << 8)
        return frac

    top_bit = magnitude_q16.bit_length() - 1
    exp_field = top_bit - 1
    base = 1 << top_bit
    remainder = magnitude_q16 - base
    shift = top_bit - 10
    mant = (remainder >> shift) if shift >= 0 else (remainder << (-shift))
    mant &= 0x3FF
    return (exp_field << 10) | mant


def _apply_sign(bits: int, sign: int) -> int:
    bits &= 0xFFFF
    if bits & 0x7FFF:
        bits |= (sign & 1) << 15
    return bits


def fp16_abs_to_q12(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan or fields.is_inf:
        return 0
    if fields.exp == 0:
        return fields.frac
    mant = (1 << 10) | fields.frac
    shift = fields.exp - 13
    return mant << shift if shift >= 0 else mant >> (-shift)


def fp16_abs_to_q24(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan or fields.is_inf:
        return 0
    if fields.exp == 0:
        return fields.frac << (Q24_FRAC_BITS - 10)
    mant = (1 << 10) | fields.frac
    shift = fields.exp - 1
    return mant << shift


def _poly_eval_q16(coeffs: tuple[int, int, int], delta_q12: int) -> int:
    c0, c1, c2 = coeffs
    delta2_q12 = (delta_q12 * delta_q12) >> Q12_FRAC_BITS
    y_q16 = c0 + ((c1 * delta_q12) >> Q12_FRAC_BITS) + ((c2 * delta2_q12) >> Q12_FRAC_BITS)
    if y_q16 < 0:
        return 0
    if y_q16 > COEFF_ONE:
        return COEFF_ONE
    return y_q16


def _eval_table_abs_q12(x_q12: int, table) -> int:
    if x_q12 <= 0:
        return table.coeffs[0][0]
    step_q12 = int(round(table.step * Q12_ONE))
    seg = min(x_q12 // step_q12, table.segments - 1)
    delta_q12 = x_q12 - seg * step_q12
    return _poly_eval_q16(table.coeffs[seg], delta_q12)


def _trig_reduce_q24(angle_q24: int) -> tuple[int, int]:
    quadrant_est = (angle_q24 * TRIG_REDUCE_RECIP) >> TRIG_REDUCE_RECIP_SHIFT
    product_q24 = quadrant_est * HALF_PI_Q24
    if product_q24 > angle_q24:
        delta_q24 = angle_q24 + HALF_PI_Q24 - product_q24
        quadrant = (quadrant_est - 1) & 0x3
    else:
        diff_q24 = angle_q24 - product_q24
        if diff_q24 >= HALF_PI_Q24:
            delta_q24 = diff_q24 - HALF_PI_Q24
            quadrant = (quadrant_est + 1) & 0x3
        else:
            delta_q24 = diff_q24
            quadrant = quadrant_est & 0x3
    return quadrant, delta_q24


def _eval_trig_quadrant(delta_q24: int, *, use_cos_table: bool) -> int:
    t_q12 = (delta_q24 * TRIG_NORMALIZE_RECIP) >> TRIG_NORMALIZE_SHIFT
    if t_q12 >= Q12_ONE:
        return 0 if use_cos_table else COEFF_ONE
    table = COS_QUADRANT_TABLE if use_cos_table else SIN_QUADRANT_TABLE
    return _eval_table_abs_q12(t_q12, table)


def relu_fp16(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan:
        return 0x7E00
    if fields.sign:
        return 0
    return bits & 0xFFFF


def sigmoid_fp16(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan:
        return 0x7E00
    if fields.is_inf:
        return 0 if fields.sign else 0x3C00
    x_q12 = fp16_abs_to_q12(bits)
    if x_q12 >= SIGMOID_MAX_Q12:
        return 0 if fields.sign else 0x3C00
    y_q16 = _eval_table_abs_q12(x_q12, SIGMOID_TABLE)
    if fields.sign:
        y_q16 = COEFF_ONE - y_q16
    return q16_magnitude_to_fp16_bits(y_q16)


def tanh_fp16(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan:
        return 0x7E00
    if fields.is_inf:
        return 0xBC00 if fields.sign else 0x3C00
    x_q12 = fp16_abs_to_q12(bits)
    if x_q12 >= TANH_MAX_Q12:
        return 0xBC00 if fields.sign else 0x3C00
    y_q16 = _eval_table_abs_q12(x_q12, TANH_TABLE)
    return _apply_sign(q16_magnitude_to_fp16_bits(y_q16), fields.sign)


def sin_fp16(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan:
        return 0x7E00
    if fields.is_inf:
        return 0x7E00
    angle_q24 = fp16_abs_to_q24(bits)
    quadrant, delta_q24 = _trig_reduce_q24(angle_q24)
    sin_q16 = _eval_trig_quadrant(delta_q24, use_cos_table=False)
    cos_q16 = _eval_trig_quadrant(delta_q24, use_cos_table=True)
    if quadrant == 0:
        mag_q16, sign = sin_q16, fields.sign
    elif quadrant == 1:
        mag_q16, sign = cos_q16, fields.sign
    elif quadrant == 2:
        mag_q16, sign = sin_q16, 1 ^ fields.sign
    else:
        mag_q16, sign = cos_q16, 1 ^ fields.sign
    return _apply_sign(q16_magnitude_to_fp16_bits(mag_q16), sign)


def cos_fp16(bits: int) -> int:
    fields = decode_fp16(bits)
    if fields.is_nan:
        return 0x7E00
    if fields.is_inf:
        return 0x7E00
    angle_q24 = fp16_abs_to_q24(bits)
    quadrant, delta_q24 = _trig_reduce_q24(angle_q24)
    sin_q16 = _eval_trig_quadrant(delta_q24, use_cos_table=False)
    cos_q16 = _eval_trig_quadrant(delta_q24, use_cos_table=True)
    if quadrant == 0:
        mag_q16, sign = cos_q16, 0
    elif quadrant == 1:
        mag_q16, sign = sin_q16, 1
    elif quadrant == 2:
        mag_q16, sign = cos_q16, 1
    else:
        mag_q16, sign = sin_q16, 0
    return _apply_sign(q16_magnitude_to_fp16_bits(mag_q16), sign)


def eval_fp16_sfu_scalar(op: int, bits: int) -> int:
    if op == OP_RELU:
        return relu_fp16(bits)
    if op == OP_SIGMOID:
        return sigmoid_fp16(bits)
    if op == OP_TANH:
        return tanh_fp16(bits)
    if op == OP_SIN:
        return sin_fp16(bits)
    if op == OP_COS:
        return cos_fp16(bits)
    return 0x7E00


def describe() -> dict:
    return {
        "name": "Fp16ActivationTrigSfu",
        "function_set": ("relu", "sigmoid", "tanh", "sin", "cos"),
        "precision": "fp16",
        "approximation": "piecewise quadratic interpolation",
        "sigmoid_domain": "[0, 8], mirrored by sign symmetry",
        "tanh_domain": "[0, 4], mirrored by odd symmetry",
        "trig_domain": "quadrant reduction + [0, pi/2] interpolation",
        "sigmoid_segments": SIGMOID_TABLE.segments,
        "tanh_segments": TANH_TABLE.segments,
        "trig_segments": SIN_QUADRANT_TABLE.segments,
        "coeff_frac_bits": COEFF_FRAC_BITS,
    }


__all__ = [
    "COEFF_FRAC_BITS",
    "FP16_WIDTH",
    "OP_COS",
    "OP_NAMES",
    "OP_RELU",
    "OP_SIGMOID",
    "OP_SIN",
    "OP_TANH",
    "Q12_FRAC_BITS",
    "Q12_ONE",
    "Q24_FRAC_BITS",
    "Q24_ONE",
    "TANH_MAX_Q12",
    "SIGMOID_MAX_Q12",
    "decode_fp16",
    "describe",
    "eval_fp16_sfu_scalar",
    "float_to_fp16_bits",
    "fp16_abs_to_q12",
    "fp16_abs_to_q24",
    "fp16_to_float",
    "q16_magnitude_to_fp16_bits",
]
