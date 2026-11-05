"""Trap occupancy updates retain small first-order changes."""
from decimal import Decimal, localcontext
import math
import numpy as np
import pytest

from tcad.physics.reliability import TrapKinetics


def expected_occupancy(initial, target, rate, dt):
    with localcontext() as ctx:
        ctx.prec = 100
        x = Decimal(str(rate)) * Decimal(str(dt))
        return float(Decimal(str(target))
                     + (Decimal(str(initial)) - Decimal(str(target))) * (-x).exp())


@pytest.mark.parametrize("dt", [1e-20, 1e-18, 1e-16, 1e-14, 1e-12,
                                 1e-10, 1e-6, .1, 1., 700.])
@pytest.mark.parametrize("initial,target", [(1., .5), (0., .5)])
def test_trap_update_matches_decimal_for_small_and_large_exponents(dt, initial, target):
    model = TrapKinetics(1e16, capture_tau=1., emission_tau=1.,
                         neutral_occupancy=target)
    model.initialize(1, initial)
    model.advance(np.zeros(1), 0., dt)
    want = expected_occupancy(initial, target, 1., dt)
    assert model.occupancy[0] == pytest.approx(want, rel=3e-15, abs=math.ulp(want))
    assert 0. <= model.occupancy[0] <= 1.


@pytest.mark.parametrize("temperature", [100., 300., 900.])
@pytest.mark.parametrize("dt", [1e-20, 1e-16, 1e-12, 1e-6])
def test_subnormal_trap_increment_is_not_lost(temperature, dt):
    model = TrapKinetics(1e16, trap_energy=0., capture_tau=1., emission_tau=2.,
                         neutral_occupancy=.5)
    model.initialize(1, 1.)
    model.advance(np.zeros(1), 0., dt, temperature)
    # With phi=0 and trap energy=0, f_eq=.5 and rate=.75. Decimal predicts a
    # positive change even when the direct exp(-rate*dt) expression rounds to 1.
    want = expected_occupancy(1., .5, .75, dt)
    assert model.occupancy[0] == pytest.approx(want, rel=4e-15, abs=math.ulp(want))
    # A public float64 occupancy at exactly one cannot encode a decrement
    # smaller than its own ULP; assert once the change is representable.
    if dt >= 1e-14:
        assert model.occupancy[0] < 1.


def test_trap_update_still_commits_only_finite_bounded_candidate():
    model = TrapKinetics(1e16, field_acceleration=1e308)
    model.initialize(2, .8)
    before = model.occupancy.copy()
    with pytest.raises(ValueError):
        model.advance(np.zeros(2), np.array([np.inf, 0.]), 1.)
    np.testing.assert_array_equal(model.occupancy, before)
