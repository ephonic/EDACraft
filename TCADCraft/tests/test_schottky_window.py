"""Independent physical-current and sigmoid-window Decimal references."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def decimal_branch(contact, voltage, temperature, lowering):
    with localcontext() as ctx:
        ctx.prec = 160 if contact.series_resistance_ohm else 1200
        d = Decimal.from_float
        thermal = d(K_B_EV) * d(temperature) * d(contact.ideality_factor)
        # The production branch receives this float-valued effective barrier.
        barrier = max(contact.barrier_height_eV - lowering, 0.)
        saturation = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                      * d(contact.richardson_multiplier) * d(contact.area_m2)
                      * d(temperature) ** 2 * (-d(barrier) / (d(K_B_EV) * d(temperature))).exp())
        if contact.series_resistance_ohm == 0.:
            return saturation * ((d(voltage) / thermal).exp() - 1)
        assert contact.transport_saturation_current_A is None
        sign = 1 if voltage > 0. else -1
        target = abs(d(voltage)); resistance = d(contact.series_resistance_ohm)
        lower = Decimal(0); upper = target / resistance
        if sign < 0:
            upper = min(upper, saturation)
        magnitude = Decimal(0)
        for _ in range(160):
            residual = sign * thermal * (1 + sign * magnitude / saturation).ln() + magnitude * resistance - target
            if residual == 0:
                return sign * magnitude
            if residual < 0:
                lower = magnitude
            else:
                upper = magnitude
            derivative = thermal / (saturation + sign * magnitude) + resistance
            candidate = magnitude - residual / derivative
            if not lower < candidate < upper:
                candidate = (lower + upper) / 2
            if magnitude and abs(candidate - magnitude) < abs(magnitude) * Decimal('1e-80'):
                return sign * candidate
            magnitude = candidate
        raise AssertionError('independent Newton bracket did not converge')


def reference(contact, voltage, temperature):
    with localcontext() as ctx:
        ctx.prec = 1200
        d = Decimal.from_float
        base = decimal_branch(contact, voltage, temperature, 0.)
        enhanced = decimal_branch(contact, voltage, temperature, contact.tunneling_barrier_lowering_eV)
        junction = d(voltage) - base * d(contact.series_resistance_ohm)
        argument = (junction - d(contact.tunneling_window_center_eV)) / d(contact.tunneling_window_width_eV)
        weight = 1 / (1 + argument.exp())
        increment = (enhanced - base) * weight
        total = (1 - weight) * base + weight * enhanced
        return dict(thermionic_A=float(base), tunneling_increment_A=float(increment), total_A=float(total))


def make(**kwargs):
    values = dict(barrier_height_eV=.8, effective_mass_ratio=.3, area_m2=1e-12,
        tunneling_barrier_lowering_eV=.1, tunneling_window_center_eV=0.,
        tunneling_window_width_eV=.025)
    values.update(kwargs)
    return SchottkyContactModel(**values)


@pytest.mark.parametrize('barrier,lowering', [(20., 20.), (30., 30.), (40., 30.)])
@pytest.mark.parametrize('argument', [720., 800., 1000.])
def test_combination_can_fit_without_individually_representable_branches(barrier, lowering, argument):
    contact = make(barrier_height_eV=barrier, tunneling_barrier_lowering_eV=lowering,
                   tunneling_window_width_eV=20. / argument)
    expected = reference(contact, 20., 300.)['total_A']
    assert expected > 0. and math.isfinite(expected)
    assert contact.current(20., 300., True) == pytest.approx(expected, rel=5e-13, abs=0.)


@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('voltage', [-.2, .05, .2, .3])
@pytest.mark.parametrize('temperature', [200., 300., 600.])
def test_normal_window_matches_independent_physical_roots(resistance, voltage, temperature):
    contact = make(series_resistance_ohm=resistance, tunneling_window_center_eV=.15)
    expected = reference(contact, voltage, temperature)
    result = contact.components(voltage, temperature)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)
    assert contact.current(voltage, temperature, True) == result['total_A']


@pytest.mark.parametrize('resistance', [0., 1000.])
@pytest.mark.parametrize('argument', [50., 100., 500., 700.])
def test_increment_survives_when_rounded_total_equals_thermionic(resistance, argument):
    contact = make(series_resistance_ohm=resistance, tunneling_window_width_eV=.2 / argument)
    expected = reference(contact, .2, 300.)
    result = contact.components(.2, 300.)
    assert expected['tunneling_increment_A'] > 0.
    assert expected['total_A'] == expected['thermionic_A']
    assert result['tunneling_increment_A'] == pytest.approx(expected['tunneling_increment_A'],
        rel=5e-13, abs=math.ulp(expected['tunneling_increment_A']))


@pytest.mark.parametrize('argument', [40., 100., 500.])
def test_reverse_increment_has_correct_sign_without_subtraction_loss(argument):
    # Put the center on the positive side so a small reverse bias lies on
    # the near-one side; use a large mass ratio to keep both currents finite.
    contact = make(tunneling_window_center_eV=.1, tunneling_window_width_eV=.001,
                   richardson_multiplier=1e100)
    voltage = -.2 / argument
    expected = reference(contact, voltage, 300.)
    got = contact.components(voltage, 300.)
    assert got['tunneling_increment_A'] < 0.
    for name in got:
        assert got[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)


@pytest.mark.parametrize('voltage', [-1., 0., 1.])
def test_zero_lowering_is_exact_thermionic_limit(voltage):
    contact = make(tunneling_barrier_lowering_eV=0.)
    assert contact.current(voltage, 300., True) == contact.current(voltage, 300., False)
    assert contact.components(voltage, 300.)['tunneling_increment_A'] == 0.


@pytest.mark.parametrize('resistance', [0., 1000.])
def test_zero_bias_is_exact_with_window(resistance):
    contact = make(series_resistance_ohm=resistance)
    assert all(value == 0. for value in contact.components(0., 300.).values())


def test_unrepresentable_component_does_not_prevent_representable_total():
    contact = make(tunneling_window_width_eV=.0002)
    expected = reference(contact, .2, 300.)
    assert expected['tunneling_increment_A'] == 0.
    assert contact.current(.2, 300., True) == pytest.approx(expected['total_A'], rel=5e-13, abs=0.)
    with pytest.raises(ValueError, match='tunneling increment.*representable'):
        contact.components(.2, 300.)


@pytest.mark.parametrize('width', [math.ulp(0.), 1e-300])
def test_infinite_window_argument_does_not_create_clipped_tail(width):
    contact = make(tunneling_window_width_eV=width)
    assert contact.current(1e100, 1e154, True) == pytest.approx(
        contact.current(1e100, 1e154, False), rel=5e-13, abs=0.)


@pytest.mark.parametrize('parameters', [dict(area_m2=1e300),
    dict(barrier_height_eV=40., tunneling_barrier_lowering_eV=1.)])
def test_truly_unrepresentable_window_total_is_rejected(parameters):
    contact = make(**parameters)
    expected = reference(contact, 1., 300.)['total_A']
    assert expected == 0. or not math.isfinite(expected)
    with pytest.raises(ValueError, match='representable'):
        contact.current(1., 300., True)


@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-14, 1e-12])
@pytest.mark.parametrize('argument', [1., 100.])
@pytest.mark.parametrize('temperature', [300., 1e154])
def test_tiny_effective_barrier_change_preserves_increment(lowering, argument, temperature):
    contact = make(tunneling_barrier_lowering_eV=lowering,
                   tunneling_window_width_eV=.2 / argument)
    expected = reference(contact, .2, temperature)
    assert expected['tunneling_increment_A'] > 0.
    result = contact.components(.2, temperature)
    assert result['tunneling_increment_A'] == pytest.approx(expected['tunneling_increment_A'],
                                                           rel=5e-13, abs=0.)
