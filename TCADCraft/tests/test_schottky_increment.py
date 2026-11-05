"""Independent physical roots for non-window and cutoff injection components."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def make(**kwargs):
    values = dict(barrier_height_eV=.8, effective_mass_ratio=.3, area_m2=1e-12,
                  tunneling_barrier_lowering_eV=.1)
    values.update(kwargs)
    return SchottkyContactModel(**values)


def reference(contact, voltage, temperature=300.):
    """Solve each complete branch, then subtract in high precision."""
    with localcontext() as ctx:
        ctx.prec = 800 if contact.series_resistance_ohm == 0. else 240
        d = Decimal.from_float
        thermal0 = d(K_B_EV) * d(temperature)
        thermal = thermal0 * d(contact.ideality_factor)
        prefactor = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                     * d(contact.richardson_multiplier) * d(contact.area_m2)
                     * d(temperature) ** 2)
        lowering = contact.tunneling_barrier_lowering_eV
        if contact.tunneling_cutoff_energy_eV is not None:
            available = max(1. - max(voltage, 0.) / contact.tunneling_cutoff_energy_eV, 0.)
            lowering *= available ** contact.tunneling_decay_exponent
        # Match the public float-valued effective barrier, without using any
        # production current, saturation, or increment helper.
        effective = max(contact.barrier_height_eV - lowering, 0.)

        def branch(barrier):
            saturation = prefactor * (-d(barrier) / thermal0).exp()
            if voltage == 0.:
                return Decimal(0)
            if contact.series_resistance_ohm == 0.:
                return saturation * ((d(voltage) / thermal).exp() - 1)
            sign = 1 if voltage > 0. else -1
            target = abs(d(voltage)); resistance = d(contact.series_resistance_ohm)
            limit = (d(contact.transport_saturation_current_A)
                     if sign > 0 and contact.transport_saturation_current_A is not None else None)
            lower = Decimal(0); upper = target / resistance
            if sign < 0:
                upper = min(upper, saturation)
            elif limit is not None:
                upper = min(upper, limit)
            current = Decimal(0)
            for _ in range(300):
                fraction = current / limit if limit is not None else Decimal(0)
                required = sign * thermal * (1 + sign * current / saturation).ln() + current * resistance / (1 - fraction)
                residual = required - target
                if residual == 0:
                    return sign * current
                if residual < 0:
                    lower = current
                else:
                    upper = current
                derivative = thermal / (saturation + sign * current) + resistance / (1 - fraction) ** 2
                candidate = current - residual / derivative
                if current and abs(candidate - current) < abs(current) * Decimal('1e-190'):
                    return sign * candidate
                if not lower < candidate < upper:
                    candidate = (lower + upper) / 2
                current = candidate
            raise AssertionError('independent branch solve did not converge')

        base = branch(contact.barrier_height_eV)
        total = branch(effective)
        return dict(thermionic_A=float(base), tunneling_increment_A=float(total - base), total_A=float(total))


def check(contact, voltage, temperature=300.):
    expected = reference(contact, voltage, temperature)
    result = contact.components(voltage, temperature)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=math.ulp(expected[name]) if expected[name] else 0.)
    assert result['total_A'] == contact.current(voltage, temperature, True)
    assert result['thermionic_A'] == contact.current(voltage, temperature, False)


@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-14, 1e-12, .1])
@pytest.mark.parametrize('voltage', [-1., -.05, .05, .2, 1.])
@pytest.mark.parametrize('resistance', [0., 1., 1000., 1e10])
def test_nonwindow_increment_matches_independent_roots(lowering, voltage, resistance):
    check(make(tunneling_barrier_lowering_eV=lowering, series_resistance_ohm=resistance), voltage)


@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-12, .1])
@pytest.mark.parametrize('voltage', [-.2, .05, .2, math.nextafter(.5, 0.), .5, .6])
@pytest.mark.parametrize('resistance', [0., 1000.])
def test_cutoff_increment_uses_actual_reduced_barrier(lowering, voltage, resistance):
    check(make(tunneling_barrier_lowering_eV=lowering, series_resistance_ohm=resistance,
               tunneling_cutoff_energy_eV=.5, tunneling_decay_exponent=.5,
               tunneling_window_center_eV=.1), voltage)


@pytest.mark.parametrize('resistance', [1000., 1e20, 1e40])
@pytest.mark.parametrize('voltage', [.1, 1., 10.])
def test_highfield_nearly_ohmic_increment_survives_equal_rounded_roots(resistance, voltage):
    contact = make(series_resistance_ohm=resistance, transport_saturation_current_A=1e-5,
                   tunneling_barrier_lowering_eV=math.ulp(.8))
    assert reference(contact, voltage)['tunneling_increment_A'] > 0.
    check(contact, voltage)


@pytest.mark.parametrize('temperature', [1e154, 1e200])
@pytest.mark.parametrize('voltage', [-.2, .2])
@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-12])
def test_unexportable_saturation_and_tiny_gain_keep_exportable_components(temperature, voltage, lowering):
    check(make(tunneling_barrier_lowering_eV=lowering), voltage, temperature)


@pytest.mark.parametrize('temperature', [200., 600.])
@pytest.mark.parametrize('ideality', [.5, 1.5])
@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('voltage', [-.2, .2])
def test_increment_uses_barrier_temperature_and_ideality_separately(temperature, ideality, resistance, voltage):
    check(make(tunneling_barrier_lowering_eV=math.ulp(.8), ideality_factor=ideality,
               series_resistance_ohm=resistance), voltage, temperature)


@pytest.mark.parametrize('parameters', [dict(tunneling_barrier_lowering_eV=0.),
    dict(barrier_height_eV=0.), dict(tunneling_barrier_lowering_eV=1e-20)])
@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('voltage', [-.2, .2])
def test_actual_zero_barrier_change_has_exact_zero_increment(parameters, resistance, voltage):
    contact = make(series_resistance_ohm=resistance, **parameters)
    check(contact, voltage)
    assert contact.components(voltage, 300.)['tunneling_increment_A'] == 0.


@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('area', [1e-300, 1e-313])
def test_increment_export_distinguishes_subnormal_from_nonzero_underflow(resistance, area):
    contact = make(area_m2=area, series_resistance_ohm=resistance,
                   tunneling_barrier_lowering_eV=math.ulp(.8))
    expected = reference(contact, .2)
    assert contact.current(.2, 300., True) != 0.
    if expected['tunneling_increment_A'] == 0.:
        with pytest.raises(ValueError, match='tunneling increment.*representable'):
            contact.components(.2, 300.)
    else:
        check(contact, .2)


@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('lowering', [0., .1])
def test_zero_bias_components_remain_exact(resistance, lowering):
    check(make(series_resistance_ohm=resistance, tunneling_barrier_lowering_eV=lowering), 0.)
