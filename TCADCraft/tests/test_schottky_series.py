"""Independent inversion oracles for series-resistance contact injection."""
from decimal import Decimal, localcontext
import math
import random

import pytest

from tcad.physics.contact import K_B_EV, SchottkyContactModel


def decimal_voltage(contact, current, temperature=300.):
    """Construct a known root using 800-digit arithmetic in the voltage law."""
    with localcontext() as ctx:
        ctx.prec = 800
        i = Decimal.from_float(current)
        saturation = Decimal.from_float(contact.saturation_current(temperature))
        thermal = (Decimal.from_float(K_B_EV) * Decimal.from_float(temperature)
                   * Decimal.from_float(contact.ideality_factor))
        bulk = i * Decimal.from_float(contact.series_resistance_ohm)
        if current > 0. and contact.transport_saturation_current_A is not None:
            bulk /= 1 - i / Decimal.from_float(contact.transport_saturation_current_A)
        return float(thermal * (1 + i / saturation).ln() + bulk)


@pytest.mark.parametrize('barrier', [0., .8, 2.])
@pytest.mark.parametrize('limit', [None, .001])
def test_zero_bias_is_exactly_zero_with_series_resistance(barrier, limit):
    contact = SchottkyContactModel(barrier, .3, area_m2=1e-12,
        series_resistance_ohm=1., transport_saturation_current_A=limit,
        tunneling_barrier_lowering_eV=.1)
    assert contact.current(0., 300.) == 0.
    assert contact.current(0., 300., True) == 0.
    assert all(value == 0. for value in contact.components(0., 300.).values())


@pytest.mark.parametrize('barrier', [0., .8, 2.])
@pytest.mark.parametrize('resistance', [1e-100, 1., 1e100])
@pytest.mark.parametrize('limit', [None, .001])
@pytest.mark.parametrize('expected', [1e-250, 1e-100, 1e-40, 1e-5])
def test_positive_known_roots_over_wide_dynamic_range(barrier, resistance, limit, expected):
    contact = SchottkyContactModel(barrier, .3, area_m2=1e-12,
        series_resistance_ohm=resistance, transport_saturation_current_A=limit)
    voltage = decimal_voltage(contact, expected)
    got = contact.current(voltage, 300.)
    assert got > 0.
    assert got == pytest.approx(expected, rel=2e-13, abs=0.)
    # Reconstruct the voltage independently, including the high-field term.
    assert decimal_voltage(contact, got) == pytest.approx(voltage, rel=3e-13, abs=0.)


@pytest.mark.parametrize('resistance', [1e-100, 1., 1e100])
@pytest.mark.parametrize('limit', [None, .001])
@pytest.mark.parametrize('fraction', [1e-200, 1e-40, .1, .9])
def test_reverse_known_roots_respect_sign_and_saturation(resistance, limit, fraction):
    contact = SchottkyContactModel(.8, .3, area_m2=1e-12,
        series_resistance_ohm=resistance, transport_saturation_current_A=limit)
    saturation = contact.saturation_current(300.)
    expected = -saturation * fraction
    got = contact.current(decimal_voltage(contact, expected), 300.)
    assert -saturation <= got < 0.
    assert got == pytest.approx(expected, rel=2e-13, abs=0.)


@pytest.mark.parametrize('resistance', [1e-300, 1., 1e300])
def test_large_brackets_do_not_overflow_midpoints(resistance):
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=resistance)
    expected = .01 if resistance < 1e100 else 1e-300
    assert contact.current(decimal_voltage(contact, expected), 300.) == pytest.approx(
        expected, rel=2e-13, abs=0.)


def test_unrepresentable_thermal_voltage_is_explicitly_rejected():
    contact = SchottkyContactModel(.8, .3, ideality_factor=math.ulp(0.),
                                  series_resistance_ohm=1.)
    with pytest.raises(ValueError, match='thermal voltage.*representable'):
        contact.current(.1, 300.)


def test_root_inside_unrepresentable_transport_gap_is_rejected():
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e-300,
                                  transport_saturation_current_A=1e-3)
    with pytest.raises(ValueError, match='representable bracket'):
        contact.current(1e300, 300.)


def test_nearly_ohmic_bound_is_rounded_outward():
    randomizer = random.Random(314159)
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e200)
    for _ in range(200):
        expected = randomizer.uniform(.1, 10.) * 1e-100
        voltage = decimal_voltage(contact, expected)
        assert contact.current(voltage, 300.) == pytest.approx(expected, rel=2e-13, abs=0.)
