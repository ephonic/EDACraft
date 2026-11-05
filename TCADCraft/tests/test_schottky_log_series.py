"""Series roots constructed from independent physical factors in Decimal."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def physical_voltage(contact, current, temperature, include=False):
    with localcontext() as ctx:
        ctx.prec = 1400
        d = Decimal.from_float
        i = current if isinstance(current, Decimal) else d(current)
        thermal = d(K_B_EV) * d(temperature)
        barrier = d(contact.barrier_height_eV)
        if include:
            barrier = max(barrier - d(contact.tunneling_barrier_lowering_eV), Decimal(0))
        saturation = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                      * d(contact.richardson_multiplier) * d(contact.area_m2)
                      * d(temperature) ** 2 * (-barrier / thermal).exp())
        bulk = i * d(contact.series_resistance_ohm)
        if i > 0 and contact.transport_saturation_current_A is not None:
            bulk /= 1 - i / d(contact.transport_saturation_current_A)
        return float(thermal * d(contact.ideality_factor) * (1 + i / saturation).ln() + bulk)


def physical_current(contact, voltage, temperature, initial):
    """Newton oracle for the actual rounded API voltage, without transport limit."""
    assert contact.transport_saturation_current_A is None
    with localcontext() as ctx:
        ctx.prec = 1400
        d = Decimal.from_float
        thermal = d(K_B_EV) * d(temperature)
        saturation = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                      * d(contact.richardson_multiplier) * d(contact.area_m2)
                      * d(temperature) ** 2 * (-d(contact.barrier_height_eV) / thermal).exp())
        thermal *= d(contact.ideality_factor)
        current = d(initial)
        for _ in range(4):
            residual = (thermal * (1 + current / saturation).ln()
                        + current * d(contact.series_resistance_ohm) - d(voltage))
            derivative = thermal / (saturation + current) + d(contact.series_resistance_ohm)
            current -= residual / derivative
        return float(current)


@pytest.mark.parametrize('temperature', [200., 300., 600.])
@pytest.mark.parametrize('resistance', [1e-100, 1., 1e100])
@pytest.mark.parametrize('limit', [None, .001])
@pytest.mark.parametrize('expected', [1e-250, 1e-40, 1e-5])
def test_forward_root_with_underflowed_saturation(temperature, resistance, limit, expected):
    contact = SchottkyContactModel(40., .3, area_m2=1e-12,
        series_resistance_ohm=resistance, transport_saturation_current_A=limit)
    with pytest.raises(ValueError, match='saturation current.*representable'):
        contact.saturation_current(temperature)
    voltage = physical_voltage(contact, expected, temperature)
    got = contact.current(voltage, temperature)
    assert got == pytest.approx(expected, rel=5e-13, abs=0.)
    assert physical_voltage(contact, got, temperature) == pytest.approx(voltage, rel=5e-13, abs=0.)


@pytest.mark.parametrize('temperature', [1e154, 1e300])
@pytest.mark.parametrize('resistance', [1e-320, 1., 1e100])
@pytest.mark.parametrize('expected', [-1e100, -.01, -1e-100, 1e-100, .01, 1e100])
def test_both_directions_with_overflowed_saturation(temperature, resistance, expected):
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=resistance)
    with pytest.raises(ValueError, match='saturation current.*representable'):
        contact.saturation_current(temperature)
    voltage = physical_voltage(contact, expected, temperature)
    if voltage == 0.:
        # The constructed physical bias itself can fall below float64. The
        # public API receives exact zero and must then return zero current.
        assert contact.current(voltage, temperature) == 0.
        return
    if abs(voltage) < float.fromhex('0x1.0p-1022'):
        # Subnormal voltage export can shift the root by more than 5e-13.
        # Compare against the physical root of the actual input voltage.
        expected = physical_current(contact, voltage, temperature, expected)
    got = contact.current(voltage, temperature)
    assert got == pytest.approx(expected, rel=5e-13, abs=0.)
    assert physical_voltage(contact, got, temperature) == pytest.approx(voltage, rel=5e-13, abs=0.)


@pytest.mark.parametrize('voltage', [-.1, -100.])
@pytest.mark.parametrize('resistance', [1., 1e300])
def test_truly_unrepresentable_reverse_root_is_rejected(voltage, resistance):
    contact = SchottkyContactModel(40., .3, series_resistance_ohm=resistance)
    with pytest.raises(ValueError, match='nonzero diode current.*representable'):
        contact.current(voltage, 300.)


@pytest.mark.parametrize('factor', [.1, .49, .51, .9, 1.1, 1.9])
@pytest.mark.parametrize('sign', [-1, 1])
def test_subnormal_root_rounds_at_zero_boundary(factor, sign):
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e300)
    with localcontext() as ctx:
        ctx.prec = 1400
        real_current = Decimal.from_float(math.ulp(0.)) * Decimal.from_float(factor) * sign
    voltage = physical_voltage(contact, real_current, 300.)
    expected = float(real_current)
    if expected == 0.:
        with pytest.raises(ValueError, match='nonzero diode current.*representable'):
            contact.current(voltage, 300.)
    else:
        got = contact.current(voltage, 300.)
        assert got * sign > 0.
        assert abs(got - expected) <= math.ulp(expected)
        if abs(expected) == math.ulp(0.):
            assert got == expected


@pytest.mark.parametrize('expected', [1e-100, 1e-10, 1e-5])
@pytest.mark.parametrize('ideality', [.5, 1., 2.])
def test_enhanced_series_branch_keeps_log_saturation(expected, ideality):
    contact = SchottkyContactModel(41., .3, area_m2=1e-12,
        series_resistance_ohm=1e5, ideality_factor=ideality,
        tunneling_barrier_lowering_eV=1.)
    voltage = physical_voltage(contact, expected, 300., True)
    assert contact.current(voltage, 300., True) == pytest.approx(expected, rel=5e-13, abs=0.)


@pytest.mark.parametrize('resistance', [1e-320, 1e-310, 1e-300])
@pytest.mark.parametrize('sign', [-1, 1])
def test_tiny_terminal_voltage_does_not_create_false_residual_plateau(resistance, sign):
    temperature = 1e300
    voltage = sign * math.ulp(0.)
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=resistance)
    expected = physical_current(contact, voltage, temperature, sign * 1e-14)
    assert contact.current(voltage, temperature) == pytest.approx(expected, rel=5e-13, abs=0.)


@pytest.mark.parametrize('voltage', [-1e100, 1e100])
def test_unrepresentable_root_is_rejected_in_both_directions(voltage):
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e-300)
    # Even the maximum finite current cannot supply this voltage: the
    # independent physical voltage at that bound is below 1e9 V.
    assert abs(physical_voltage(contact, math.copysign(float.fromhex('0x1.fffffffffffffp1023'), voltage),
                                1e300)) < 1e9
    with pytest.raises(ValueError, match='representable bracket'):
        contact.current(voltage, 1e300)


@pytest.mark.parametrize('factor', [.49, .51])
def test_zero_rounding_boundary_includes_transport_denominator(factor):
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e300,
                                  transport_saturation_current_A=2 * math.ulp(0.))
    with localcontext() as ctx:
        ctx.prec = 1400
        real_current = Decimal.from_float(math.ulp(0.)) * Decimal.from_float(factor)
    voltage = physical_voltage(contact, real_current, 300.)
    if factor < .5:
        with pytest.raises(ValueError, match='nonzero diode current.*representable'):
            contact.current(voltage, 300.)
    else:
        assert contact.current(voltage, 300.) == math.ulp(0.)
