"""Independent mpmath references for windows outside float64 log range."""
import math

import mpmath as mp
import pytest

from tcad.physics.contact import K_B_EV, WSe2TransportWindow


def make(**kwargs):
    values = dict(center_gate_V=0., width_V=1., peak_current_A_per_um=1.,
                  floor_current_A_per_um=math.ulp(0.))
    values.update(kwargs)
    return WSe2TransportWindow(**values)


def reference(model, gate, drain=.5, temperature=300., *, weight_only=False):
    # mpmath keeps an unbounded binary exponent. This reference evaluates
    # literal products, exp, sigmoid and powers, not production log helpers.
    with mp.workdps(1900):
        m = mp.mpf
        width = (model.left_width_V if gate < model.center_gate_V and model.left_width_V is not None
                 else model.right_width_V if gate >= model.center_gate_V and model.right_width_V is not None
                 else model.width_V)
        offset = m(gate)-m(model.center_gate_V)
        x = offset/m(width)
        lobe = mp.exp(-x*x/2)*max(1+m(model.skew)*x, 0)
        left = m(model.left_tail_fraction)/(1+mp.exp(offset/m(model.left_tail_smoothing_V or width)))
        right = m(model.right_tail_fraction)/(1+mp.exp(-offset/m(model.right_tail_smoothing_V or width)))
        tail = max(left, right)
        weight = tail+(1-tail)*lobe
        if model.notch_depth_decades:
            nx = (m(gate)-m(model.notch_center_gate_V))/m(model.notch_width_V)
            weight *= mp.power(10, -m(model.notch_depth_decades)*mp.exp(-nx*nx/2))
        if weight_only:
            return float(weight)
        if weight == 0 or drain == 0. and model.drain_exponent > 0.:
            return model.floor_current_A_per_um
        thermal = mp.exp(m(model.temperature_activation_eV)/m(K_B_EV)*(
            1/m(model.temperature_reference_K)-1/m(temperature)))
        drive = mp.power(abs(m(drain))/m(model.drain_reference_V), m(model.drain_exponent))
        return float(max(m(model.floor_current_A_per_um), m(model.peak_current_A_per_um)*weight*thermal*drive))


CASES = [
    ('squared_coordinate_floor', dict(), 1e200, .5, 300.),
    ('coordinate_overflow_floor', dict(width_V=math.ulp(0.)), 1e308, .5, 300.),
    ('deep_notch_floor', dict(notch_center_gate_V=0., notch_depth_decades=1e308), 0., .5, 300.),
    ('plateau_survives_coordinate', dict(width_V=math.ulp(0.), right_tail_fraction=.5), 1e308, .5, 300.),
    ('plateau_survives_square', dict(right_tail_fraction=.5), 1e200, .5, 300.),
    ('remote_notch_is_negligible', dict(notch_center_gate_V=1e308, notch_width_V=math.ulp(0.),
        notch_depth_decades=1e308), 0., .5, 300.),
    ('cold_activation_floor', dict(temperature_activation_eV=1e308), 0., .5, 1e-300),
    ('small_drain_power_floor', dict(drain_exponent=1e308), 0., 1e-300, 300.),
    ('zero_drain_extreme_gate', dict(width_V=math.ulp(0.)), 1e308, 0., 300.),
    ('zero_drain_extreme_heat', dict(temperature_activation_eV=1e308), 0., 0., 600.),
    ('zero_gate_extreme_heat', dict(skew=-1., temperature_activation_eV=1e308), 1., .5, 600.),
    ('opposed_superrange_logs', dict(temperature_reference_K=1e-307,
        temperature_activation_eV=.0019, notch_center_gate_V=0., notch_depth_decades=1e308), 0., .5, 300.),
    *[(f'exact_superrange_compensation_{peak}', dict(peak_current_A_per_um=peak,
        temperature_activation_eV=K_B_EV, temperature_reference_K=math.ldexp(1., -1026)),
        math.ldexp(1., 513), .5, math.ldexp(1., -1025)) for peak in (1e-300, 1., 1e300)],
]


@pytest.mark.parametrize('name,kwargs,gate,drain,temperature', CASES, ids=[c[0] for c in CASES])
def test_complete_current_uses_final_range(name, kwargs, gate, drain, temperature):
    model = make(**kwargs)
    expected = reference(model, gate, drain, temperature)
    assert math.isfinite(expected)
    assert model.current_A_per_um(gate, drain, temperature) == pytest.approx(
        expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('gate', [1e160, 1e200, 1e308, -1e160, -1e200, -1e308])
@pytest.mark.parametrize('width', [1., math.ulp(0.)])
def test_plateau_keeps_its_public_weight(gate, width):
    kwargs = dict(width_V=width, left_tail_fraction=.25, right_tail_fraction=.5)
    model = make(**kwargs)
    assert model.gate_weight(gate) == reference(model, gate, weight_only=True)
    assert model.current_A_per_um(gate, .5, 300.) == model.gate_weight(gate)


@pytest.mark.parametrize('kwargs,gate,drain,temperature', [
    (dict(temperature_activation_eV=1e308), 0., .5, 600.),
    (dict(drain_exponent=1e308), 0., 1e300, 300.),
    (dict(temperature_activation_eV=1e308, right_tail_fraction=.5), 1e200, .5, 600.),
])
def test_actual_final_overflow_still_rejected(kwargs, gate, drain, temperature):
    model = make(**kwargs)
    assert not math.isfinite(reference(model, gate, drain, temperature))
    with pytest.raises(ValueError, match='representable'):
        model.current_A_per_um(gate, drain, temperature)


@pytest.mark.parametrize('gate', [1e200, 1e308])
def test_nonzero_public_weight_underflow_is_rejected(gate):
    model = make()
    with pytest.raises(ValueError, match='representable'):
        model.gate_weight(gate)
    assert model.current_A_per_um(gate, .5, 300.) == model.floor_current_A_per_um


@pytest.mark.parametrize('gate,drain,temperature', [
    (math.nan, 0., 300.), (math.inf, 0., 300.), (0., 0., math.nan),
    (0., 0., math.inf), (0., 0., 0.), (0., math.nan, 300.),
])
def test_zero_path_still_validates_every_input(gate, drain, temperature):
    with pytest.raises(ValueError, match='finite|> 0'):
        make(width_V=math.ulp(0.)).current_A_per_um(gate, drain, temperature)


@pytest.mark.parametrize('temperature', [math.ulp(0.), 300., 1e308])
def test_zero_drain_with_zero_exponent_keeps_neutral_drive(temperature):
    model = make(drain_exponent=0., width_V=math.ulp(0.), right_tail_fraction=.5)
    assert model.current_A_per_um(1e308, 0., temperature) == .5

