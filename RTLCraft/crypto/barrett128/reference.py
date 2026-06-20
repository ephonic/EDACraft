"""Golden reference model for the 128-bit Barrett modular multiplier.

Pure-Python, width-exact reference for ``r = (a * b) mod N`` where ``a, b`` are
128-bit unsigned values and ``N`` is a **full 128-bit modulus** (the Barrett
precondition ``2^127 <= N < 2^128`` must hold). Under this precondition the
Barrett constant ``m = floor(2^256 / N)`` is exactly 129 bits wide, which fixes
all datapath widths and makes the unit PPA-friendly (constant width, no
variable-latency normalization).

The Barrett reduction avoids division: it uses ``m`` to estimate the quotient of
the 256-bit product ``p = a*b`` divided by ``N``.

This module is the single source of truth for functional correctness. Both the
executable DSL module and every verification environment (directed vectors,
Python-UVM, generated SV/UVM reference model) compare against these functions.

Barrett reduction identity (k = 128, N full-width)::

    p  = a * b                         (256-bit, 0 <= p < 2^(2k))
    m  = floor(2^(2k) / N)             (precomputed, exactly 129-bit)
    q  = floor( floor(p / 2^(k-1)) * m / 2^(k+1) )   (quotient estimate)
    r  = p - q * N                     (0 <= r < 3*N, the residual)
    if r >= N: r -= N                  (at most two conditional subtractions)
    if r >= N: r -= N

With N full-width, the estimate ``q`` satisfies ``0 <= r < 3*N`` for all valid
inputs, so exactly two conditional subtractions normalize ``r`` into ``[0, N)``.
"""

from __future__ import annotations

K = 128                     # operand width
WIDTH = K                   # public operand width
PROD_WIDTH = 2 * K          # product width = 256
M_WIDTH = K + 1             # Barrett constant width = 129 (guaranteed for full-width N)


def is_valid_modulus(n: int) -> bool:
    """True iff ``n`` satisfies the Barrett full-width precondition."""
    return (1 << (K - 1)) <= n < (1 << K)


def barrett_constant(n: int) -> int:
    """Precompute the Barrett constant ``m = floor(2^256 / N)`` for modulus ``n``.

    Requires ``is_valid_modulus(n)`` (full 128-bit). The result is exactly
    129 bits wide under that precondition.
    """
    if not is_valid_modulus(n):
        raise ValueError(
            f"Barrett requires a full 128-bit modulus (2^127 <= N < 2^128); got {n}"
        )
    return (1 << (2 * K)) // n


def barrett_reduce(p: int, n: int, m: int) -> int:
    """Reduce a product ``p`` (0 <= p < 2^256) modulo ``n`` using Barrett.

    ``m`` is the Barrett constant from :func:`barrett_constant`.
    Returns ``p mod n`` in ``[0, n)``. Two conditional subtractions suffice.
    """
    q = ((p >> (K - 1)) * m) >> (K + 1)   # quotient estimate
    r = p - q * n                         # residual, 0 <= r < 3*N
    if r >= n:                            # at most two conditional subtractions
        r -= n
    if r >= n:
        r -= n
    return r


def modmul(a: int, b: int, n: int, m: int | None = None) -> int:
    """Compute ``(a * b) mod n`` via Barrett reduction.

    Operands ``a, b`` are masked to 128 bits. ``n`` must be a full 128-bit
    modulus. ``m`` defaults to the Barrett constant for ``n``.
    """
    mask = (1 << K) - 1
    a &= mask
    b &= mask
    if m is None:
        m = barrett_constant(n)
    p = a * b
    return barrett_reduce(p, n, m)


def describe() -> dict:
    return {
        "name": "BarrettModMul",
        "module": "barrett128",
        "function": "r = (a * b) mod N, 128-bit operands, fully-pipelined Barrett reduction",
        "operand_width": WIDTH,
        "product_width": PROD_WIDTH,
        "barrett_constant_width": M_WIDTH,
        "modulus_constraint": "2^127 <= N < 2^128 (full 128-bit modulus)",
        "multiplier_primitive": "16x16 single-cycle multiplier (DSP-friendly), 8x8 schoolbook",
        "algorithm": "Barrett reduction with precomputed m = floor(2^256 / N)",
        "max_conditional_subtractions": 2,
        "inputs": "a[128], b[128], n[128], m[129]",
        "outputs": "r[128]",
    }


__all__ = [
    "K", "WIDTH", "PROD_WIDTH", "M_WIDTH",
    "is_valid_modulus", "barrett_constant", "barrett_reduce", "modmul", "describe",
]
