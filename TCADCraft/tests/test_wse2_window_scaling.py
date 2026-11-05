"""Direct Decimal formula references for thermal and drain window scaling."""
from decimal import Decimal, localcontext
import math
import sys

import pytest

from tcad.physics.contact import K_B_EV, WSe2TransportWindow


def make(**kwargs):
    values = dict(center_gate_V=0., width_V=1., peak_current_A_per_um=1.,
                  floor_current_A_per_um=math.ulp(0.))
    values.update(kwargs)
    return WSe2TransportWindow(**values)


def reference(window, drain, temperature):
    """Evaluate the declared formula directly, without production log helpers."""
    with localcontext() as ctx:
        ctx.prec = 1600
        ctx.Emax = 999999999
        ctx.Emin = -999999999
        d = Decimal.from_float
        exponent = d(window.temperature_activation_eV) / d(K_B_EV) * (
            1 / d(window.temperature_reference_K) - 1 / d(temperature))
        thermal = exponent.exp()
        drive = (Decimal(1) if window.drain_exponent == 0. else
                 (abs(d(drain)) / d(window.drain_reference_V)) ** d(window.drain_exponent))
        return dict(thermal=float(thermal), drain=float(drive),
            current=float(max(d(window.floor_current_A_per_um),
                              d(window.peak_current_A_per_um) * thermal * drive)))


# Keep thermal/drain factors independently outside float64 while their product
# with the peak remains representable. All values are numerical probes.
CASES = [
    ('thermal_above_clip', dict(peak_current_A_per_um=1e-300,
        temperature_activation_eV=40.), .5, 600.),
    ('thermal_below_clip', dict(peak_current_A_per_um=1e300,
        temperature_activation_eV=40.), .5, 200.),
    ('drain_power_overflow', dict(peak_current_A_per_um=1e-300,
        drain_exponent=2.), 1e200, 300.),
    ('drain_power_underflow', dict(peak_current_A_per_um=1e300,
        drain_exponent=2.), 1e-200, 300.),
    ('drain_ratio_overflow', dict(peak_current_A_per_um=1e-300,
        drain_reference_V=1e-300, drain_exponent=.5), 1e300, 300.),
    ('drain_ratio_underflow', dict(peak_current_A_per_um=1e300,
        drain_reference_V=1e300, drain_exponent=.5), 1e-300, 300.),
    ('temperature_reciprocal_overflow', dict(temperature_reference_K=1e-310,
        temperature_activation_eV=1e-312), .5, 2e-310),
    ('energy_quotient_overflow', dict(temperature_reference_K=1e308,
        temperature_activation_eV=1e308), .5, math.nextafter(1e308, math.inf)),
    ('thermal_drain_compensation', dict(temperature_activation_eV=40.,
        drain_exponent=2.), 1e-170, 600.),
    ('subnormal_peak_recovery', dict(peak_current_A_per_um=math.ulp(0.),
        drain_exponent=2.), 1e160, 300.),
    ('zero_bias', dict(peak_current_A_per_um=1e300), 0., 300.),
    ('minimum_bias', dict(peak_current_A_per_um=1e300), math.ulp(0.), 300.),
]


@pytest.mark.parametrize('name,kwargs,drain,temperature', CASES, ids=[c[0] for c in CASES])
def test_final_current_uses_complete_scaling(name, kwargs, drain, temperature):
    model = make(**kwargs)
    expected = reference(model, drain, temperature)['current']
    assert model.current_A_per_um(0., drain, temperature) == pytest.approx(
        expected, rel=5e-12, abs=2 * math.ulp(expected))


@pytest.mark.parametrize('temperature', [200., 300., 600., math.nextafter(300., math.inf)])
@pytest.mark.parametrize('activation', [0., .01, 1., 40.])
def test_temperature_factor_is_not_clipped(temperature, activation):
    model = make(temperature_activation_eV=activation)
    expected = reference(model, .5, temperature)['thermal']
    if expected == 0. or not math.isfinite(expected):
        with pytest.raises(ValueError, match='representable'):
            model.temperature_factor(temperature)
    else:
        assert model.temperature_factor(temperature) == pytest.approx(expected, rel=5e-12, abs=math.ulp(expected))


@pytest.mark.parametrize('drain', [0., math.ulp(0.), 1e-200, 1e-31, .5, 1e200, 1e300])
@pytest.mark.parametrize('power', [0., .5, 1., 2.])
def test_drain_factor_has_no_hidden_voltage_floor(drain, power):
    model = make(drain_exponent=power)
    expected = reference(model, drain, 300.)['drain']
    if drain > 0. and expected == 0. or not math.isfinite(expected):
        with pytest.raises(ValueError, match='representable'):
            model.drain_factor(drain)
    else:
        assert model.drain_factor(drain) == pytest.approx(expected, rel=5e-12, abs=math.ulp(expected))


@pytest.mark.parametrize('reference_voltage', [math.ulp(0.), 1e-300, .5, 1e300])
@pytest.mark.parametrize('direction', [0., math.inf])
def test_near_reference_drain_with_large_power(reference_voltage, direction):
    drain = math.nextafter(reference_voltage, direction)
    model = make(drain_reference_V=reference_voltage,
                 drain_exponent=1. if reference_voltage < sys.float_info.min else 1e10)
    expected = reference(model, drain, 300.)['current']
    assert model.current_A_per_um(0., drain, 300.) == pytest.approx(expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('drain', [0., 1e-300, .5, 1e300])
def test_drain_sign_symmetry(drain):
    model = make(drain_exponent=.5)
    assert model.current_A_per_um(0., drain, 300.) == model.current_A_per_um(0., -drain, 300.)


@pytest.mark.parametrize('temperature', [math.ulp(0.), 1e-300, 300., 1e308])
def test_exact_temperature_reference_survives_extreme_energy(temperature):
    model = make(temperature_reference_K=temperature, temperature_activation_eV=1e308)
    assert model.temperature_factor(temperature) == 1.
    assert model.current_A_per_um(0., .5, temperature) == 1.


@pytest.mark.parametrize('peak', [math.ulp(0.), 1e-300, 1., sys.float_info.max])
def test_neutral_scaling_preserves_peak_exactly(peak):
    assert make(peak_current_A_per_um=peak).current_A_per_um(0., .5, 300.) == peak


@pytest.mark.parametrize('kwargs,drain,temperature', [
    (dict(temperature_activation_eV=40.), .5, 600.),
    (dict(drain_exponent=2.), 1e200, 300.),
    (dict(peak_current_A_per_um=1e300, drain_exponent=2.), 1e100, 300.),
])
def test_unrepresentable_final_current_is_explicitly_rejected(kwargs, drain, temperature):
    with pytest.raises(ValueError, match='representable'):
        make(**kwargs).current_A_per_um(0., drain, temperature)


@pytest.mark.parametrize('gate,drain,temperature', [
    (math.nan, 0., 300.), (math.inf, .5, 300.), (0., math.nan, 300.),
    (0., math.inf, 300.), (0., 0., math.nan), (0., 0., math.inf),
    (0., 0., 0.), (0., 0., -1.),
])
def test_invalid_inputs_rejected_even_when_signal_is_zero(gate, drain, temperature):
    with pytest.raises(ValueError, match='finite|> 0'):
        make().current_A_per_um(gate, drain, temperature)


@pytest.mark.parametrize('temperature', [200., 300., 600.])
def test_explicit_floor_is_preserved(temperature):
    model = make(peak_current_A_per_um=1e-10, floor_current_A_per_um=1e-20,
                 temperature_activation_eV=40.)
    assert model.current_A_per_um(0., 0., temperature) == model.floor_current_A_per_um

