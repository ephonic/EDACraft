"""Independent Decimal roots for series-window junctions and small gains."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def reference(contact, voltage, temperature=300.):
    with localcontext() as ctx:
        ctx.prec = 180
        d = Decimal.from_float
        thermal0 = d(K_B_EV) * d(temperature)
        thermal = thermal0 * d(contact.ideality_factor)
        prefactor = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                     * d(contact.richardson_multiplier) * d(contact.area_m2) * d(temperature) ** 2)
        resistance = d(contact.series_resistance_ohm)
        sign = 1 if voltage > 0. else -1
        target = abs(d(voltage))
        limit = d(contact.transport_saturation_current_A) if contact.transport_saturation_current_A is not None else None

        def branch(barrier):
            saturation = prefactor * (-d(barrier) / thermal0).exp()
            lower = Decimal(0); upper = target / resistance
            if sign < 0:
                upper = min(upper, saturation)
            elif limit is not None:
                upper = min(upper, limit)
            magnitude = Decimal(0)
            for _ in range(220):
                fraction = magnitude / limit if sign > 0 and limit is not None else Decimal(0)
                bulk = magnitude * resistance / (1 - fraction)
                residual = sign * thermal * (1 + sign * magnitude / saturation).ln() + bulk - target
                if residual == 0:
                    return sign * magnitude, sign * thermal * (1 + sign * magnitude / saturation).ln()
                if residual < 0:
                    lower = magnitude
                else:
                    upper = magnitude
                derivative = thermal / (saturation + sign * magnitude) + resistance / (1 - fraction) ** 2
                candidate = magnitude - residual / derivative
                if magnitude and abs(candidate - magnitude) < abs(magnitude) * Decimal('1e-140'):
                    return sign * candidate, sign * thermal * (1 + sign * candidate / saturation).ln()
                if not lower < candidate < upper:
                    candidate = (lower + upper) / 2
                if magnitude and abs(candidate - magnitude) < abs(magnitude) * Decimal('1e-140'):
                    magnitude = candidate
                    return sign * magnitude, sign * thermal * (1 + sign * magnitude / saturation).ln()
                magnitude = candidate
            raise AssertionError('independent physical Newton solve did not converge')

        base, junction = branch(contact.barrier_height_eV)
        enhanced, _ = branch(max(contact.barrier_height_eV - contact.tunneling_barrier_lowering_eV, 0.))
        # branch() returns the magnitude of junction voltage; restore sign.
        junction *= sign
        argument = (junction - d(contact.tunneling_window_center_eV)) / d(contact.tunneling_window_width_eV)
        weight = 1 / (1 + argument.exp())
        increment = (enhanced - base) * weight
        return dict(thermionic_A=float(base), tunneling_increment_A=float(increment),
                    total_A=float(base + increment), junction_V=float(junction))


def make(**kwargs):
    values = dict(barrier_height_eV=.8, effective_mass_ratio=.3, area_m2=1e-12,
        series_resistance_ohm=1000., tunneling_barrier_lowering_eV=.1,
        tunneling_window_center_eV=.1, tunneling_window_width_eV=.025)
    values.update(kwargs)
    return SchottkyContactModel(**values)


@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-14, 1e-12, .1])
@pytest.mark.parametrize('voltage', [-.05, .05, .2])
@pytest.mark.parametrize('resistance', [1., 1000., 1e10])
def test_series_increment_matches_independent_roots(lowering, voltage, resistance):
    contact = make(tunneling_barrier_lowering_eV=lowering, series_resistance_ohm=resistance)
    expected = reference(contact, voltage)
    result = contact.components(voltage, 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)
    assert contact.current(voltage, 300., True) == result['total_A']


@pytest.mark.parametrize('resistance', [1e12, 1e20, 1e40])
@pytest.mark.parametrize('voltage', [.1, 1., 10.])
def test_nearly_ohmic_junction_preserves_window_increment(resistance, voltage):
    probe = make(series_resistance_ohm=resistance, tunneling_window_center_eV=0.)
    junction = reference(probe, voltage)['junction_V']
    contact = make(series_resistance_ohm=resistance, tunneling_window_center_eV=junction,
                   tunneling_window_width_eV=junction / 10.)
    expected = reference(contact, voltage)
    assert expected['tunneling_increment_A'] > 0.
    result = contact.components(voltage, 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)


@pytest.mark.parametrize('lowering', [math.ulp(.8), 1e-12, .1])
@pytest.mark.parametrize('voltage', [.1, 1., 10.])
def test_increment_includes_high_field_bulk_difference(lowering, voltage):
    contact = make(tunneling_barrier_lowering_eV=lowering,
                   transport_saturation_current_A=1e-5)
    expected = reference(contact, voltage)
    result = contact.components(voltage, 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)


@pytest.mark.parametrize('resistance', [math.ulp(0.), 1e-320])
def test_weighted_increment_can_fit_when_enhanced_root_exceeds_float(resistance):
    contact = make(barrier_height_eV=30., tunneling_barrier_lowering_eV=30.,
        series_resistance_ohm=resistance, tunneling_window_center_eV=0.,
        tunneling_window_width_eV=.025)
    expected = reference(contact, 20.)
    assert expected['total_A'] > 0. and math.isfinite(expected['total_A'])
    with pytest.raises(ValueError, match='representable'):
        contact._branch_current(20., 300., 0.)
    result = contact.components(20., 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)


@pytest.mark.parametrize('resistance', [1., 1000., 1e10])
@pytest.mark.parametrize('lowering', [math.ulp(.8), .1])
@pytest.mark.parametrize('voltage', [-.2, -1.])
@pytest.mark.parametrize('width', [.025, 1.])
def test_reverse_saturation_does_not_require_representable_current_deficit(resistance, lowering, voltage, width):
    contact = make(series_resistance_ohm=resistance, tunneling_barrier_lowering_eV=lowering,
                   tunneling_window_width_eV=width)
    expected = reference(contact, voltage)
    result = contact.components(voltage, 300.)
    for name in result:
        assert result[name] == pytest.approx(expected[name], rel=5e-13, abs=0.)
