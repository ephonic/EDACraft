"""Resolve high-field injection gains against independent complete-current roots."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def make(gap_fraction, limit=1e-5, bulk_voltage=1., lowering=.1, window=True):
    return SchottkyContactModel(.8, .3, area_m2=1e-12,
        series_resistance_ohm=gap_fraction * bulk_voltage / limit,
        transport_saturation_current_A=limit, tunneling_barrier_lowering_eV=lowering,
        tunneling_window_center_eV=.1 if window else None, tunneling_window_width_eV=.025)


def saturation(contact, barrier, temperature):
    d = Decimal.from_float
    return (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
            * d(contact.richardson_multiplier) * d(contact.area_m2) * d(temperature) ** 2
            * (-d(barrier) / (d(K_B_EV) * d(temperature))).exp())


def physical_voltage(contact, gap_fraction, temperature=300.):
    """Construct bias from a real current below the limit, before float export."""
    with localcontext() as ctx:
        ctx.prec = 320
        d = Decimal.from_float
        current = d(contact.transport_saturation_current_A) * (1 - d(gap_fraction))
        thermal = d(K_B_EV) * d(temperature) * d(contact.ideality_factor)
        return float(thermal * (1 + current / saturation(contact, contact.barrier_height_eV, temperature)).ln()
                     + current * d(contact.series_resistance_ohm) / d(gap_fraction))


def reference(contact, voltage, temperature=300.):
    with localcontext() as ctx:
        ctx.prec = 320
        d = Decimal.from_float
        thermal = d(K_B_EV) * d(temperature) * d(contact.ideality_factor)
        resistance = d(contact.series_resistance_ohm)
        limit = d(contact.transport_saturation_current_A)
        target = d(voltage)

        def branch(barrier):
            sat = saturation(contact, barrier, temperature)
            lower = Decimal(0); upper = min(target / resistance, limit)
            current = Decimal(0)
            for _ in range(500):
                fraction = current / limit
                junction = thermal * (1 + current / sat).ln()
                residual = junction + current * resistance / (1 - fraction) - target
                if residual == 0:
                    return current, junction
                if residual < 0:
                    lower = current
                else:
                    upper = current
                derivative = thermal / (sat + current) + resistance / (1 - fraction) ** 2
                candidate = current - residual / derivative
                if current and abs(candidate - current) < current * Decimal('1e-240'):
                    return candidate, thermal * (1 + candidate / sat).ln()
                if not lower < candidate < upper:
                    candidate = (lower + upper) / 2
                current = candidate
            raise AssertionError('independent complete-current root did not converge')

        base, junction = branch(contact.barrier_height_eV)
        effective = max(contact.barrier_height_eV - contact.tunneling_barrier_lowering_eV, 0.)
        enhanced, _ = branch(effective)
        weight = Decimal(1)
        if contact.tunneling_window_center_eV is not None:
            weight /= 1 + ((junction - d(contact.tunneling_window_center_eV)) /
                           d(contact.tunneling_window_width_eV)).exp()
        increment = weight * (enhanced - base)
        return dict(thermionic_A=float(base), tunneling_increment_A=float(increment),
                    total_A=float(base + increment))


@pytest.mark.parametrize('gap_fraction', [1e-4, 1e-8, 1e-12, 1e-15])
@pytest.mark.parametrize('limit', [1e-5, 1e-100])
@pytest.mark.parametrize('bulk_voltage', [1., 10.])
@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-12, .1])
@pytest.mark.parametrize('window', [False, True])
def test_small_transport_gap_does_not_amplify_export_rounding(gap_fraction, limit, bulk_voltage, lowering, window):
    contact = make(gap_fraction, limit, bulk_voltage, lowering, window)
    voltage = physical_voltage(contact, gap_fraction)
    expected = reference(contact, voltage)
    assert expected['tunneling_increment_A'] > 0.
    result = contact.components(voltage, 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=math.ulp(expected[name]))
    assert contact.current(voltage, 300., True) == result['total_A']


@pytest.mark.parametrize('gap_fraction', [1e-8, 1e-12])
@pytest.mark.parametrize('temperature,ideality', [(200., .5), (600., 1.5)])
def test_transport_gap_respects_temperature_and_ideality(gap_fraction, temperature, ideality):
    from dataclasses import replace
    contact = replace(make(gap_fraction, lowering=math.ulp(.8)), ideality_factor=ideality)
    voltage = physical_voltage(contact, gap_fraction, temperature)
    expected = reference(contact, voltage, temperature)
    for name, actual in contact.components(voltage, temperature).items():
        assert actual == pytest.approx(expected[name], rel=5e-13, abs=math.ulp(expected[name]))


@pytest.mark.parametrize('gap_fraction', [math.nextafter(.01, 0.), .01,
                                        math.nextafter(.01, math.inf), .02])
@pytest.mark.parametrize('lowering', [math.ulp(.8), .1])
def test_physical_increment_is_consistent_across_gap_solver_transition(gap_fraction, lowering):
    contact = make(gap_fraction, lowering=lowering)
    voltage = physical_voltage(contact, gap_fraction)
    expected = reference(contact, voltage)
    for name, actual in contact.components(voltage, 300.).items():
        assert actual == pytest.approx(expected[name], rel=5e-13, abs=math.ulp(expected[name]))


def test_unexportable_root_inside_last_transport_interval_is_explicitly_rejected():
    # Keep the public strict transport-limit contract: returning the rounded
    # limit would imply a singular bulk voltage at the exported current.
    contact = SchottkyContactModel(.8, .3, series_resistance_ohm=1e-300,
                                  transport_saturation_current_A=1e-3)
    with pytest.raises(ValueError, match='representable bracket'):
        contact.current(1e300, 300.)
