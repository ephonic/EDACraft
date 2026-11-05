"""Exact-product and physical-current checks for the public Richardson constant."""
from decimal import Decimal, localcontext
import math
import sys

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


FACTORS = [math.ulp(0.), sys.float_info.min, 1e-300, .3, 1., 1e100, 1e300, sys.float_info.max]


def reference(mass, multiplier):
    with localcontext() as ctx:
        ctx.prec = 2400
        d = Decimal.from_float
        return float(d(RICHARDSON_M0) * d(mass) * d(multiplier))


def make(mass, multiplier, **kwargs):
    return SchottkyContactModel(.8, mass, richardson_multiplier=multiplier, **kwargs)


@pytest.mark.parametrize('mass', FACTORS)
@pytest.mark.parametrize('multiplier', FACTORS)
def test_constant_matches_independent_exact_product(mass, multiplier):
    contact = make(mass, multiplier)
    expected = reference(mass, multiplier)
    if expected == 0. or not math.isfinite(expected):
        with pytest.raises(ValueError, match='Richardson constant.*representable'):
            _ = contact.richardson_constant
    else:
        assert contact.richardson_constant == expected


# Probe both sides of the binary64 export boundaries, including subnormal
# ties. The reference multiplies exact float inputs before one final rounding.
BOUNDARIES = []
for mass, target in [(1., sys.float_info.max), (math.ulp(0.), .5),
                     (math.ulp(0.), 1.5), (1., sys.float_info.min)]:
    multiplier = target / RICHARDSON_M0
    BOUNDARIES.extend((mass, value) for value in [math.nextafter(multiplier, 0.), multiplier,
                                                math.nextafter(multiplier, math.inf)])


@pytest.mark.parametrize('mass,multiplier', BOUNDARIES)
def test_rounding_boundaries_do_not_create_infinity_or_false_zero(mass, multiplier):
    test_constant_matches_independent_exact_product(mass, multiplier)


@pytest.mark.parametrize('mass,multiplier,area', [
    (1e308, 1e-308, 1e-12), (1e-308, 1e308, 1e-12),
    (math.ulp(0.), 1e300, 1e-12),
    (1e300, 1e100, 1e-300), (1e-300, 1e-100, 1e300)])
@pytest.mark.parametrize('voltage', [-.2, .2])
def test_current_keeps_combined_factors_when_constant_export_fails(mass, multiplier, area, voltage):
    contact = make(mass, multiplier, area_m2=area)
    with localcontext() as ctx:
        ctx.prec = 2400
        d = Decimal.from_float
        constant = d(RICHARDSON_M0) * d(mass) * d(multiplier)
        thermal = d(K_B_EV) * d(300.)
        saturation = constant * d(area) * d(300.) ** 2 * (-d(.8) / thermal).exp()
        expected = float(saturation * ((d(voltage) / thermal).exp() - 1))
        assert contact.saturation_current(300.) == pytest.approx(float(saturation), rel=5e-13, abs=0.)
        assert contact.current(voltage, 300.) == pytest.approx(expected, rel=5e-13, abs=0.)
    exported = reference(mass, multiplier)
    if exported == 0. or not math.isfinite(exported):
        with pytest.raises(ValueError, match='Richardson constant.*representable'):
            _ = contact.richardson_constant
    else:
        assert contact.richardson_constant == exported


@pytest.mark.parametrize('mass,multiplier', [(1e308, 1e-308), (.3, 1.),
    (math.ulp(0.), sys.float_info.max), (sys.float_info.max, math.ulp(0.))])
def test_factor_order_is_invariant(mass, multiplier):
    assert make(mass, multiplier).richardson_constant == make(multiplier, mass).richardson_constant
