"""Coefficient-table generation for the FP16 SFU.

The SFU uses second-order interpolation on compact domains:

- sigmoid: |x| in [0, 8], 32 segments
- tanh:    |x| in [0, 4], 32 segments
- sin/cos: t in [0, 1], 32 segments where angle = t * (pi/2)

Each segment is fitted from the endpoint/midpoint samples and emitted as
integer fixed-point coefficients for Horner-form evaluation:

    y ~= c0 + c1 * d + c2 * d^2

The tables are generated in Python so the RTL and the golden reference share
one exact source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable, Sequence


COEFF_FRAC_BITS = 16
COEFF_STORAGE_WIDTH = 18
SIGMOID_SEGMENTS = 32
TANH_SEGMENTS = 32
TRIG_SEGMENTS = 32


@dataclass(frozen=True)
class PolyTable:
    name: str
    domain_lo: float
    domain_hi: float
    segments: int
    coeff_frac_bits: int
    coeffs: tuple[tuple[int, int, int], ...]

    @property
    def step(self) -> float:
        return (self.domain_hi - self.domain_lo) / self.segments


def _fit_quadratic_segment(
    func: Callable[[float], float],
    lo: float,
    hi: float,
    *,
    frac_bits: int,
) -> tuple[int, int, int]:
    """Fit a quadratic on one segment from endpoint + midpoint samples."""
    mid = 0.5 * (lo + hi)
    seg_w = hi - lo

    y0 = func(lo)
    ym = func(mid)
    y1 = func(hi)

    delta_mid = ym - y0
    delta_hi = y1 - y0

    c2 = 2.0 * (delta_hi - 2.0 * delta_mid) / (seg_w * seg_w)
    c1 = (delta_hi - c2 * seg_w * seg_w) / seg_w
    c0 = y0

    scale = 1 << frac_bits
    return (
        int(round(c0 * scale)),
        int(round(c1 * scale)),
        int(round(c2 * scale)),
    )


def build_poly_table(
    name: str,
    func: Callable[[float], float],
    *,
    domain_lo: float,
    domain_hi: float,
    segments: int,
    frac_bits: int = COEFF_FRAC_BITS,
) -> PolyTable:
    step = (domain_hi - domain_lo) / segments
    coeffs = []
    for idx in range(segments):
        lo = domain_lo + idx * step
        hi = lo + step
        coeffs.append(_fit_quadratic_segment(func, lo, hi, frac_bits=frac_bits))
    return PolyTable(
        name=name,
        domain_lo=domain_lo,
        domain_hi=domain_hi,
        segments=segments,
        coeff_frac_bits=frac_bits,
        coeffs=tuple(coeffs),
    )


SIGMOID_TABLE = build_poly_table(
    "sigmoid",
    lambda x: 1.0 / (1.0 + math.exp(-x)),
    domain_lo=0.0,
    domain_hi=8.0,
    segments=SIGMOID_SEGMENTS,
)

TANH_TABLE = build_poly_table(
    "tanh",
    math.tanh,
    domain_lo=0.0,
    domain_hi=4.0,
    segments=TANH_SEGMENTS,
)

SIN_QUADRANT_TABLE = build_poly_table(
    "sin_quadrant",
    lambda t: math.sin((math.pi / 2.0) * t),
    domain_lo=0.0,
    domain_hi=1.0,
    segments=TRIG_SEGMENTS,
)

COS_QUADRANT_TABLE = build_poly_table(
    "cos_quadrant",
    lambda t: math.cos((math.pi / 2.0) * t),
    domain_lo=0.0,
    domain_hi=1.0,
    segments=TRIG_SEGMENTS,
)


ALL_TABLES: tuple[PolyTable, ...] = (
    SIGMOID_TABLE,
    TANH_TABLE,
    SIN_QUADRANT_TABLE,
    COS_QUADRANT_TABLE,
)


def flatten_coeffs(table: PolyTable, coeff_index: int) -> tuple[int, ...]:
    return tuple(segment[coeff_index] for segment in table.coeffs)


def pack_coeff_rows(
    table: PolyTable,
    *,
    coeff_width: int = COEFF_STORAGE_WIDTH,
) -> tuple[int, ...]:
    """Pack each `(c0, c1, c2)` row into one wide ROM word.

    This keeps the LUT bit count unchanged while reducing the number of storage
    objects the emitted RTL has to carry around.
    """

    mask = (1 << coeff_width) - 1
    packed = []
    for c0, c1, c2 in table.coeffs:
        packed.append(((c0 & mask) << (2 * coeff_width)) | ((c1 & mask) << coeff_width) | (c2 & mask))
    return tuple(packed)


def max_abs_coeff(table: PolyTable) -> tuple[int, int, int]:
    return tuple(max(abs(segment[i]) for segment in table.coeffs) for i in range(3))


__all__ = [
    "ALL_TABLES",
    "COEFF_FRAC_BITS",
    "COEFF_STORAGE_WIDTH",
    "COS_QUADRANT_TABLE",
    "PolyTable",
    "SIGMOID_SEGMENTS",
    "SIGMOID_TABLE",
    "SIN_QUADRANT_TABLE",
    "TANH_SEGMENTS",
    "TANH_TABLE",
    "TRIG_SEGMENTS",
    "build_poly_table",
    "flatten_coeffs",
    "max_abs_coeff",
    "pack_coeff_rows",
]
