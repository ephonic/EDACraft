"""Conditional face audit from rounded classical, homogeneous node observations.

Node potentials/carriers and reported face force/mobility must be binary64
round-to-nearest observations. Their closed rounding cells are propagated with
directed Decimal arithmetic. This does not certify native transcendental errors
or reconstruct the nonlinear history. An interval crossing the cutoff never
qualifies. Nodal unmodified eGradQuasiFermi is not a modified face force.

Only a one-dimensional face, constant DOS, no quantum correction, positive
spacing/thermal voltage, QF at contacts, and CT beta 1 or 2 are supported. The
caller must establish those conditions and provenance independently.
"""
import math
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING


def _constant(value):
    if isinstance(value, bool) or not isinstance(value, (str, Decimal, int, float)):
        raise ValueError('expected a finite decimal constant')
    try:
        result = Decimal.from_float(value) if isinstance(value, float) else Decimal(value)
    except (ValueError, ArithmeticError) as exc:
        raise ValueError('invalid decimal constant') from exc
    if not result.is_finite():
        raise ValueError('nonfinite constant')
    return result


def binary64_rounding_cell(value):
    """Exact closed cell, including asymmetric spacing at powers of two.

    A closed cell conservatively includes both ties irrespective of evenness.
    Float extremes adjacent to infinity and non-float inputs are rejected.
    """
    if type(value) is not float or not math.isfinite(value):
        raise ValueError('expected a finite binary64 observation')
    adjacent = [math.nextafter(value, direction) for direction in (-math.inf, math.inf)]
    if not all(math.isfinite(x) for x in adjacent):
        raise ValueError('observation adjacent to infinity')
    with localcontext() as ctx:
        ctx.prec = 1100  # Exact midpoints even for the binary64 subnormal range.
        center = Decimal.from_float(value)
        return tuple((Decimal.from_float(x) + center) / 2 for x in adjacent)


class _Intervals:
    def __init__(self, precision):
        self.precision = precision

    def rounded(self, operation, upper):
        with localcontext() as ctx:
            ctx.prec = self.precision
            ctx.rounding = ROUND_CEILING if upper else ROUND_FLOOR
            return operation()

    def add(self, a, b):
        return (self.rounded(lambda: a[0] + b[0], False),
                self.rounded(lambda: a[1] + b[1], True))

    def sub(self, a, b):
        return (self.rounded(lambda: a[0] - b[1], False),
                self.rounded(lambda: a[1] - b[0], True))

    def mul(self, a, b):
        pairs = [(x, y) for x in a for y in b]
        return (min(self.rounded(lambda x=x, y=y: x*y, False) for x, y in pairs),
                max(self.rounded(lambda x=x, y=y: x*y, True) for x, y in pairs))

    def div(self, a, b):
        if b[0] <= 0:
            raise ValueError('division requires positive denominator interval')
        pairs = [(x, y) for x in a for y in b]
        return (min(self.rounded(lambda x=x, y=y: x/y, False) for x, y in pairs),
                max(self.rounded(lambda x=x, y=y: x/y, True) for x, y in pairs))

    def transcendental(self, a, name):
        if a[0] < 0 or (name == 'ln' and a[0] == 0):
            raise ValueError('invalid transcendental interval')
        # Decimal ln/sqrt are correctly rounded, nearest-even. Expand one ulp
        # explicitly; changing context.rounding alone would not direct ln.
        with localcontext() as ctx:
            ctx.prec = self.precision
            lo = getattr(a[0], name)().next_minus()
            hi = getattr(a[1], name)().next_plus()
            return lo, hi


def _overlap(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


def audit_hfs_gqf_face(*, potential_left, potential_right, carrier_left,
                       carrier_right, carrier, spacing, thermal_voltage,
                       reference_density, base_mobility, saturation_velocity,
                       beta, cutoff, reported_below_cutoff, reported_mobility,
                       reported_force=None, carrier_scale='1', mobility_scale='1',
                       precision=80):
    """Return force bounds, branch classification and conditional consistency.

    Constants (including float spacing/VT) are authoritative values. A float
    base_mobility is instead a rounded observation; Decimal/string is exact.
    Carrier/mobility unit scales are applied *after* forming observation cells.
    reported_below_cutoff is an independent snapshot flag or a separately
    justified inference from the exported mobility; it is never inferred from
    this audit's reconstructed force. Every required observation must be valid.

    The model requires carrier + RefDens > 1 SI throughout both observation
    cells; densities outside that scope are rejected rather than extrapolated
    to a commercial density-floor convention. RefDens can be zero for controls.
    """
    if carrier not in ('n', 'p') or type(beta) is not int or beta not in (1, 2):
        raise ValueError('carrier must be n/p and beta must be integer 1/2')
    if type(precision) is not int or not 50 <= precision <= 200:
        raise ValueError('precision must be an integer from 50 to 200')
    if type(reported_below_cutoff) is not bool:
        raise ValueError('an independent boolean branch observation is required')
    dx, vt, ref, vs, threshold, cs, ms = map(_constant, (
        spacing, thermal_voltage, reference_density, saturation_velocity,
        cutoff, carrier_scale, mobility_scale))
    if min(dx, vt, vs, threshold, cs, ms) <= 0 or ref < 0:
        raise ValueError('positive constants and nonnegative reference density required')
    ops = _Intervals(precision)
    exact = lambda x: (x, x)
    phi = [binary64_rounding_cell(x) for x in (potential_left, potential_right)]
    densities = [ops.mul(binary64_rounding_cell(x), exact(cs))
                 for x in (carrier_left, carrier_right)]
    if min(x[0] for x in densities) <= 0:
        raise ValueError('positive carrier observations required')
    shifted = [ops.add(x, exact(ref)) for x in densities]
    if min(x[0] for x in shifted) <= 1:
        raise ValueError('carrier plus reference is outside the supported floor-free regime')
    logs = [ops.transcendental(x, 'ln') for x in shifted]
    dlog = ops.mul(exact(vt), ops.sub(logs[1], logs[0]))
    dphi = ops.sub(phi[1], phi[0])
    signed = ops.sub(dphi, dlog) if carrier == 'n' else ops.add(dphi, dlog)
    magnitude = (Decimal(0) if signed[0] <= 0 <= signed[1] else min(x.copy_abs() for x in signed),
                 max(x.copy_abs() for x in signed))
    force = ops.div(magnitude, exact(dx))
    branch = ('below' if force[1] < threshold else
              'active' if force[0] >= threshold else 'indeterminate')
    branch_consistent = (None if branch == 'indeterminate' else
                         (branch == 'below') == reported_below_cutoff)
    base = (binary64_rounding_cell(base_mobility) if type(base_mobility) is float
            else exact(_constant(base_mobility)))
    if base[0] <= 0:
        raise ValueError('positive base mobility required')
    observed_mu = ops.mul(binary64_rounding_cell(reported_mobility), exact(ms))
    if observed_mu[0] <= 0:
        raise ValueError('positive reported mobility required')
    ratio = ops.div(ops.mul(base, force), exact(vs))
    power = ratio if beta == 1 else ops.mul(ratio, ratio)
    denom = ops.add(exact(Decimal(1)), power)
    if beta == 2:
        denom = ops.transcendental(denom, 'sqrt')
    active_mu = ops.div(base, denom)
    # Native CT ignores ratios <= 1e-12. Include both possibilities if needed.
    if ratio[0] <= Decimal('1e-12'):
        active_mu = (min(active_mu[0], base[0]), max(active_mu[1], base[1]))
    expected_mu = (base if branch == 'below' else active_mu if branch == 'active'
                   else (min(base[0], active_mu[0]), max(base[1], active_mu[1])))
    mobility_consistent = _overlap(observed_mu, expected_mu)
    force_consistent = (None if reported_force is None else
                        _overlap(binary64_rounding_cell(reported_force), force))
    qualified = (branch_consistent is True and mobility_consistent and
                 force_consistent is not False)
    return dict(force_V_m=[str(x) for x in force], branch=branch,
                branch_consistent=branch_consistent,
                expected_mobility_SI=[str(x) for x in expected_mu],
                mobility_consistent=mobility_consistent,
                reported_force_consistent=force_consistent,
                conditional_consistency=qualified, precision=precision,
                nonlinear_solution_or_commercial_alignment_qualified=False)
