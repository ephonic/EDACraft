"""Independent audit of the paused electron lineage, operations 6 through 19.

No state is emitted. This checks a saved arithmetic continuation and its fixed
tau lineage energy rows, not the nonlinear root or a complete physical step.
"""
from decimal import Decimal, localcontext
from fractions import Fraction

from .boltzmann_product_range import _binary113, _vector
from .boltzmann_scaled_arithmetic import (
    _count, _tokens, audit_mb_scaled_arithmetic, scaled_value_fraction,
    split_mb_scaled_arithmetic,
)


def _endpoint(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) > 25000:
        raise ValueError('bounded original endpoint required')
    groups = []
    j = 0
    for i in range(7):
        if j >= len(raw) or type(raw[j]) is not str or len(raw[j]) > 64:
            raise ValueError('original endpoint coverage mismatch')
        number = Fraction(Decimal(raw[j]))
        limit = 256 if i == 0 else 4096
        if number.denominator != 1 or not 0 <= number <= limit:
            raise ValueError('original endpoint vector count invalid')
        n = int(number)
        groups.append(_vector(raw[j + 1:j + 1 + n]))
        if len(groups[-1]) != n:
            raise ValueError('original endpoint vector coverage mismatch')
        j += n + 1
    if j != len(raw) or len(groups[0]) < 10:
        raise ValueError('original endpoint coverage mismatch')
    return groups


def _value(x):
    """Make an exact auditor operand, independently of the native radix packer."""
    if not x:
        return ['mb_scaled_value_v1', '113', '0']
    n = x.numerator
    e = -(x.denominator.bit_length() - 1)
    if x.denominator != 1 << -e:
        raise ValueError('dyadic audit operand required')
    sign = -1 if n < 0 else 1
    n = abs(n)
    parts = []
    while n:
        zeros = (n & -n).bit_length() - 1
        n >>= zeros
        e += zeros
        part = n & ((1 << 113) - 1)
        parts.extend([hex(sign * part), str(e)])
        n >>= 113
        e += 113
    return ['mb_scaled_value_v1', '113', str(len(parts) // 2), *parts]


def audit_mb_scaled_collision_tail(endpoint, command, saved_capacity, saved_dTl, wire):
    _tokens(wire, 20000)
    if len(wire) < 4 or tuple(wire[:4]) != ('mb_scaled_collision_tail_v1', '113', '9', '14'):
        raise ValueError('scaled collision tail coverage/version mismatch')
    f, en, ep, dn, dp, un, up = _endpoint(endpoint)
    c = _vector(command)
    if len(c) != 6 or min(c[:3]) <= 0:
        raise ValueError('positive saved fixed-tau commands required')
    alpha = _binary113(Fraction(3, 2) * _binary113(Fraction(Decimal('1.380649e-23'))))
    def quotients(values, divisor):
        result = Fraction()
        for x in values:
            first = _binary113(x / divisor)
            result += first + _binary113((x - divisor * first) / divisor)
        return result
    thermal = f[2] + quotients(f[9:], f[3])
    n = [f[0] + sum(dn, Fraction()), f[1] + sum(dp, Fraction())]
    kinetic = [alpha * thermal * f[0] + sum(en + un, Fraction()) - f[5] * sum(dn, Fraction()),
               alpha * thermal * f[1] + sum(ep + up, Fraction()) - f[6] * sum(dp, Fraction())]
    delta = [kinetic[k] - alpha * n[k] * thermal for k in range(2)]
    fractions = [_binary113(c[0] / _binary113(c[0] + c[k + 1])) for k in range(2)]
    trial = sum(_vector(saved_dTl), Fraction())
    capacity = sum(_vector(saved_capacity), Fraction())
    expected = [alpha * n[0], alpha * n[1], *fractions, f[3],
                -alpha * f[0], -alpha * f[1], delta[0], trial]
    if capacity != expected[0] or len(saved_capacity) * len(saved_dTl) > 65536:
        raise ValueError('saved original capacity mismatch or pair budget exceeded')
    j = 4
    payload = 0
    def take():
        nonlocal j
        if j >= len(wire):
            raise ValueError('scaled tail record missing')
        size = _count(wire[j], 16395)
        value = list(wire[j + 1:j + 1 + size])
        if len(value) != size:
            raise ValueError('scaled tail record truncated')
        j += 1 + size
        return value
    ctx = []
    for x in expected:
        raw = take()
        if scaled_value_fraction(raw) != x:
            raise ValueError('native tail normalization mismatch')
        ctx.append(raw)
        payload += int(raw[2])
    zero = _value(Fraction())
    v = []
    for i in range(14):
        operands = (
            lambda: ('multiply', ctx[0], ctx[8]),
            lambda: ('multiply', ctx[1], ctx[8]),
            lambda: ('subtract', ctx[7], v[0]),
            lambda: ('subtract', zero, v[1]),
            lambda: ('multiply', ctx[2], v[2]),
            lambda: ('multiply', ctx[3], v[3]),
            lambda: ('add', v[4], v[5]),
            lambda: ('divide', v[6], ctx[4]),
            lambda: ('multiply', ctx[5], v[7]),
            lambda: ('multiply', ctx[6], v[7]),
            lambda: ('subtract', zero, v[4]),
            lambda: ('subtract', zero, v[5]),
            lambda: ('add', v[8], v[10]),
            lambda: ('add', v[9], v[11]),
        )
        packet = take()
        audit_mb_scaled_arithmetic(*operands[i](), packet)
        value, rest = split_mb_scaled_arithmetic(packet)
        payload += int(value[2]) + int(rest[2])
        if payload > 4096:
            raise ValueError('original collision evidence budget exceeded')
        v.append(value)
    if j != len(wire):
        raise ValueError('unexpected scaled collision tail record')
    values = list(map(scaled_value_fraction, v))
    X = values[4:6]
    lattice = values[6]
    physical_alpha = Fraction(3, 2) * Fraction(Decimal('1.380649e-23'))
    physical_capacities = [physical_alpha * x for x in n]
    be = [f[4] * (X[k] - c[0] / c[k + 1] *
          ((delta[0] if k == 0 else 0) - X[k] - physical_capacities[k] * lattice / f[3]))
          for k in range(2)]
    scale = f[4] * (sum(map(abs, X)) + abs(lattice) *
                    (1 + sum(map(abs, physical_capacities)) / f[3]))
    groups = sum(x != 0 for x in delta) + sum(x != 0 for x in c[3:])
    budget = min(Fraction(1, 10**27) / max(1, groups), 4096 * Fraction(1, 1 << 112) * scale)
    carrier = [f[4] * (values[12 + k] + physical_alpha * f[k] * lattice / f[3]) for k in range(2)]
    energy = [carrier[0] + f[4] * X[0], carrier[1] + f[4] * X[1],
              f[4] * (lattice - sum(X)), sum(carrier) + f[4] * lattice]
    if any(abs(x) > budget for x in be + energy):
        raise ValueError('unapproximated fixed-tau lineage BE or energy gate failed')
    def text(x):
        with localcontext() as context:
            context.prec = 40
            return format(Decimal(x.numerator) / Decimal(x.denominator), '.12E')
    return dict(scope='paused_first_electron_lineage_scaled_operations_6_through_19',
                exact_native_operations_audited=14, evidence_components=payload,
                original_evidence_budget=4096, exact_original_product_retained=True,
                BE_residuals_J=list(map(text, be)), energy_residuals_J=list(map(text, energy)),
                unchanged_energy_budget_J=text(budget), fixed_tau_lineage_energy_gate_passed=True,
                division_remainder_retained=True, nonlinear_root_audited=False,
                full_collision_audited=False, state_committed=False,
                physical_time_advanced=False, physical_validated=False)
