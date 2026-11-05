from fractions import Fraction
from .boltzmann_scaled_arithmetic import _tokens,_count
from .boltzmann_dyadic_codec import scaled_value_fraction
from .boltzmann_product_range import _vector,_binary113

def split_mb_capacity_arithmetic(wire):
    """Check framing and value grammar; the audit below checks the operation."""
    _tokens(wire, 16395)
    if len(wire) < 11 or tuple(wire[:2]) != ('mb_capacity_arithmetic_v1', '113'):
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


def audit_mb_capacity_arithmetic(operation, left, right, wire):
    """Verify the exact identity and the two-rounding quotient independently.

    The nonzero division remainder is authoritative saved evidence, never a
    state increment and never declared to be zero by a tolerance comparison.
    """
    value, rest = split_mb_capacity_arithmetic(wire)
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
