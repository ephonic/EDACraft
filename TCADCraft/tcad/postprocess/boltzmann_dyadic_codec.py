"""Same strict scaled-value grammar, with one final Fraction normalization."""
from fractions import Fraction
import re
from .boltzmann_scaled_arithmetic import _tokens,_count

def scaled_value_fraction(wire):
    """Decode the separate value format without a native/package call."""
    _tokens(wire, 8195)
    if len(wire) < 3 or tuple(wire[:2]) != ('mb_scaled_value_v1', '113'):
        raise ValueError('scaled value version/precision mismatch')
    n = _count(wire[2], 4096)
    if len(wire) != 3 + 2 * n:
        raise ValueError('scaled value coverage mismatch')
    total = 0
    first = end = sign = None
    for raw, exponent in zip(wire[3::2], wire[4::2]):
        if re.fullmatch(r'-?0x[1-9a-f][0-9a-f]{0,28}', raw) is None:
            raise ValueError('canonical bounded hex coefficient required')
        if re.fullmatch(r'0|-?[1-9][0-9]{0,4}', exponent) is None:
            raise ValueError('canonical bounded explicit exponent required')
        c, e = int(raw, 16), int(exponent)
        bits = abs(c).bit_length()
        if not c & 1 or bits > 113 or abs(e) > 65536:
            raise ValueError('odd binary113 coefficient and bounded exponent required')
        if first is None:
            first, sign = e, c > 0
        elif e < end or (c > 0) != sign:
            raise ValueError('scaled components overlap, unordered or inconsistent sign')
        end = e + bits
        if end - first > 65536:
            raise ValueError('scaled integer span budget exceeded')
        total += c << (e-first)
    if first is None:return Fraction()
    return Fraction(total << first) if first >= 0 else Fraction(total,1 << -first)

