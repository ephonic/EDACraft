"""Independent Fraction audit for native scaled arithmetic and division tails."""
from fractions import Fraction
import re

from .boltzmann_product_range import _binary113, _vector


def _tokens(raw, maximum):
    if not isinstance(raw, (list, tuple)) or len(raw) > maximum:
        raise ValueError('bounded scaled wire required')
    if any(type(s) is not str or not 1 <= len(s) <= 64 for s in raw):
        raise ValueError('short scaled tokens required')


def _count(text, maximum):
    if re.fullmatch(r'0|[1-9][0-9]{0,4}', text) is None or int(text) > maximum:
        raise ValueError('canonical bounded scaled count required')
    return int(text)


def scaled_value_fraction(wire):
    """Decode the separate value format without a native/package call."""
    _tokens(wire, 8195)
    if len(wire) < 3 or tuple(wire[:2]) != ('mb_scaled_value_v1', '113'):
        raise ValueError('scaled value version/precision mismatch')
    n = _count(wire[2], 4096)
    if len(wire) != 3 + 2 * n:
        raise ValueError('scaled value coverage mismatch')
    total = Fraction()
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
        total += Fraction(c << e) if e >= 0 else Fraction(c, 1 << -e)
    return total


def split_mb_scaled_arithmetic(wire):
    """Check framing and value grammar; the audit below checks the operation."""
    _tokens(wire, 16395)
    if len(wire) < 11 or tuple(wire[:2]) != ('mb_scaled_arithmetic_v1', '113'):
        raise ValueError('scaled arithmetic version/precision mismatch')
    if wire[2] not in ('import', 'add', 'subtract', 'multiply', 'divide'):
        raise ValueError('unknown scaled arithmetic operation')
    size = _count(wire[3], 8195)
    if 4 + size >= len(wire):
        raise ValueError('scaled result coverage mismatch')
    value = list(wire[4:4 + size])
    rest_size = _count(wire[4 + size], 8195)
    rest = list(wire[5 + size:])
    if len(rest) != rest_size:
        raise ValueError('scaled remainder coverage mismatch')
    scaled_value_fraction(value)
    scaled_value_fraction(rest)
    if int(value[2]) + int(rest[2]) > 4096:
        raise ValueError('original combined evidence component budget exceeded')
    return value, rest


def audit_mb_scaled_arithmetic(operation, left, right, wire):
    """Verify the exact identity and the two-rounding quotient independently.

    The nonzero division remainder is authoritative saved evidence, never a
    state increment and never declared to be zero by a tolerance comparison.
    """
    value, rest = split_mb_scaled_arithmetic(wire)
    if operation != wire[2]:
        raise ValueError('scaled operation provenance mismatch')
    q, residual = scaled_value_fraction(value), scaled_value_fraction(rest)
    if operation == 'import':
        if right != [] and right != ():
            raise ValueError('scaled import must have no right input')
        expected = sum(_vector(left), Fraction())
        identity = q == expected and residual == 0
    else:
        a, b = scaled_value_fraction(left), scaled_value_fraction(right)
        if operation == 'add': expected = a + b
        elif operation == 'subtract': expected = a - b
        elif operation == 'multiply':
            if int(left[2]) * int(right[2]) > 65536:
                raise ValueError('original product pair budget exceeded')
            expected = a * b
        elif operation == 'divide':
            if not b:
                raise ValueError('scaled division by zero')
            first = _binary113(a / b)
            second = _binary113((a - b * first) / b)
            expected = first + second
        else:
            raise ValueError('unknown scaled arithmetic operation')
        identity = (a == b * q + residual) if operation == 'divide' else residual == 0
    if q != expected or not identity:
        raise ValueError('scaled exact integer identity or quotient mismatch')
    division_bound = operation != 'divide' or abs(residual) <= abs(a) / (1 << 226)
    if not division_bound:
        raise ValueError('two-rounding division error bound exceeded')
    return dict(scope='scaled_binary113_arithmetic_with_exact_remainder',
                operation=operation, exact_integer_identity=True,
                division_error_bound_checked=operation == 'divide',
                division_relative_residual_bound_bits=226 if operation == 'divide' else None,
                result_component_count=int(value[2]), remainder_component_count=int(rest[2]),
                remainder_is_zero=residual == 0,
                native_physics_used=False, physical_time_advanced=False,
                state_committed=False, physical_validated=False)
