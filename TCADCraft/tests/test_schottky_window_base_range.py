"""Independent series roots when a window's base current cannot be exported."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, RICHARDSON_M0, SchottkyContactModel


def make(**kwargs):
    values = dict(barrier_height_eV=30., effective_mass_ratio=.3, area_m2=1e-12,
                  series_resistance_ohm=1000., tunneling_barrier_lowering_eV=29.,
                  tunneling_window_center_eV=.1, tunneling_window_width_eV=.025)
    values.update(kwargs)
    return SchottkyContactModel(**values)


def reference(contact, voltage, temperature=300.):
    with localcontext() as ctx:
        ctx.prec = 800
        d = Decimal.from_float
        thermal0 = d(K_B_EV) * d(temperature)
        thermal = thermal0 * d(contact.ideality_factor)
        prefactor = (d(RICHARDSON_M0) * d(contact.effective_mass_ratio)
                     * d(contact.richardson_multiplier) * d(contact.area_m2) * d(temperature) ** 2)
        resistance = d(contact.series_resistance_ohm)
        sign = 1 if voltage > 0. else -1
        target = abs(d(voltage))
        limit = (d(contact.transport_saturation_current_A)
                 if sign > 0 and contact.transport_saturation_current_A is not None else None)

        def branch(barrier):
            saturation = prefactor * (-d(barrier) / thermal0).exp()
            lower = Decimal(0); upper = target / resistance
            if sign < 0:
                upper = min(upper, saturation)
            elif limit is not None:
                upper = min(upper, limit)
            magnitude = Decimal(0)
            for _ in range(600):
                fraction = magnitude / limit if limit is not None else Decimal(0)
                bulk = magnitude * resistance / (1 - fraction)
                required = sign * thermal * (1 + sign * magnitude / saturation).ln() + bulk
                residual = required - target
                if residual == 0:
                    break
                if residual < 0:
                    lower = magnitude
                else:
                    upper = magnitude
                derivative = thermal / (saturation + sign * magnitude) + resistance / (1 - fraction) ** 2
                candidate = magnitude - residual / derivative
                if magnitude and abs(candidate - magnitude) < magnitude * Decimal('1e-650'):
                    magnitude = candidate
                    break
                if not lower < candidate < upper:
                    candidate = (lower + upper) / 2
                magnitude = candidate
            else:
                raise AssertionError('independent branch root did not converge')
            junction = thermal * (1 + sign * magnitude / saturation).ln()
            return sign * magnitude, junction

        base, junction = branch(contact.barrier_height_eV)
        enhanced, _ = branch(max(contact.barrier_height_eV - contact.tunneling_barrier_lowering_eV, 0.))
        argument = (junction - d(contact.tunneling_window_center_eV)) / d(contact.tunneling_window_width_eV)
        weight = 1 / (1 + argument.exp())
        total = base + weight * (enhanced - base)
        return dict(thermionic_A=float(base), total_A=float(total), junction_V=float(junction),
                    base_log=float(abs(base).ln()), enhanced_log=float(abs(enhanced).ln()))


def check(contact, voltage, temperature=300.):
    expected = reference(contact, voltage, temperature)
    actual = contact.current(voltage, temperature, True)
    assert actual == pytest.approx(expected['total_A'], rel=5e-13, abs=math.ulp(expected['total_A']))
    if expected['thermionic_A'] == 0.:
        with pytest.raises(ValueError, match='representable'):
            contact.current(voltage, temperature, False)
        with pytest.raises(ValueError, match='representable'):
            contact.components(voltage, temperature)
    return expected


@pytest.mark.parametrize('resistance', [1., 1000., 1e100, 1e300])
@pytest.mark.parametrize('voltage', [-.2, .05, .2, 1.])
@pytest.mark.parametrize('width', [.025, 1.])
def test_underflowed_base_does_not_prevent_representable_window_total(resistance, voltage, width):
    contact = make(series_resistance_ohm=resistance, tunneling_window_width_eV=width)
    expected = check(contact, voltage)
    assert expected['thermionic_A'] == 0.
    assert expected['total_A'] != 0. and math.isfinite(expected['total_A'])


@pytest.mark.parametrize('temperature', [200., 600.])
@pytest.mark.parametrize('ideality', [.5, 1.5])
@pytest.mark.parametrize('voltage', [-.2, .2])
def test_underflowed_base_keeps_temperature_and_ideality(temperature, ideality, voltage):
    check(make(barrier_height_eV=60., tunneling_barrier_lowering_eV=59.,
               ideality_factor=ideality), voltage, temperature)


@pytest.mark.parametrize('voltage', [.1, 1., 10.])
@pytest.mark.parametrize('limit', [1e-5, 1e-20])
def test_enhanced_branch_keeps_highfield_bulk_voltage(voltage, limit):
    check(make(tunneling_barrier_lowering_eV=30., transport_saturation_current_A=limit), voltage)


@pytest.mark.parametrize('resistance', [1., 1e100])
@pytest.mark.parametrize('voltage', [-.2, .2])
def test_subnormal_base_uses_continuous_root_before_window_weight(resistance, voltage):
    check(make(barrier_height_eV=19.2, tunneling_barrier_lowering_eV=1.,
               series_resistance_ohm=resistance), voltage)


@pytest.mark.parametrize('voltage', [-.2, .2])
def test_unrepresentable_total_is_still_rejected(voltage):
    contact = make(tunneling_barrier_lowering_eV=.1)
    assert reference(contact, voltage)['total_A'] == 0.
    with pytest.raises(ValueError, match='representable'):
        contact.current(voltage, 300., True)
