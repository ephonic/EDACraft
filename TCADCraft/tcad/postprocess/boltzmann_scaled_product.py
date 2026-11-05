"""Independent rational replay of native explicit-exponent product evidence.

This validates intermediate arithmetic only. It does not convert the result
into an old scalar expansion, submit a state, or certify physical energy rows.
"""
from fractions import Fraction
import re

from .boltzmann_product_range import _vector


def audit_mb_scaled_product(left, right, wire):
    """Verify all bits, original input/pair limits and bounded output evidence."""
    a, b = _vector(left), _vector(right)
    if len(a) * len(b) > 65536:
        raise ValueError('original product pair budget exceeded')
    if not isinstance(wire, (list, tuple)) or not 6 <= len(wire) <= 8198:
        raise ValueError('bounded scaled product wire required')
    if any(type(s) is not str or len(s) > 64 for s in wire):
        raise ValueError('short scaled product tokens required')
    if wire[:2] != ['mb_scaled_product_v1', '113'] and tuple(wire[:2]) != ('mb_scaled_product_v1', '113'):
        raise ValueError('scaled product version/precision mismatch')
    if any(re.fullmatch(r'0|[1-9][0-9]{0,5}', s) is None for s in wire[2:6]):
        raise ValueError('canonical bounded counts required')
    n, m, pairs, count = map(int, wire[2:6])
    if (n, m, pairs) != (len(a), len(b), sum(x != 0 for x in a) * sum(x != 0 for x in b)):
        raise ValueError('scaled product input counts mismatch')
    if count > 4096 or len(wire) != 6 + 2 * count:
        raise ValueError('original component evidence budget exceeded or malformed wire')
    expected = sum(a, Fraction()) * sum(b, Fraction())
    total = Fraction()
    previous_end = None
    minimum = None
    for coefficient, exponent in zip(wire[6::2], wire[7::2]):
        if re.fullmatch(r'-?0x[1-9a-f][0-9a-f]{0,28}', coefficient) is None:
            raise ValueError('canonical bounded hex coefficient required')
        if re.fullmatch(r'0|-?[1-9][0-9]{0,5}', exponent) is None:
            raise ValueError('canonical bounded exponent required')
        c, e = int(coefficient, 16), int(exponent)
        bits = abs(c).bit_length()
        if bits > 113 or not c & 1 or abs(e) > 65536:
            raise ValueError('scaled coefficient/exponent budget exceeded')
        if expected == 0 or (c > 0) != (expected > 0):
            raise ValueError('scaled component sign mismatch')
        if previous_end is not None and e < previous_end:
            raise ValueError('scaled components overlap or are unordered')
        previous_end = e + bits
        minimum = e if minimum is None else minimum
        total += Fraction(c << e) if e >= 0 else Fraction(c, 1 << -e)
    if total != expected:
        raise ValueError('scaled product exact integer replay mismatch')
    if bool(count) != bool(expected):
        raise ValueError('scaled zero representation mismatch')
    return dict(scope='exact_scaled_binary113_intermediate_product',
                precision_bits=113, input_component_counts=[n, m],
                nonzero_pairs=pairs, output_component_count=count,
                minimum_exponent2=minimum, exact_integer_replay=True,
                native_physics_used=False, physical_time_advanced=False,
                physical_validated=False, state_committed=False)
