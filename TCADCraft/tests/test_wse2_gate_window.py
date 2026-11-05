"""Direct high precision references for complete WSe2 gate windows."""
from decimal import Decimal, localcontext
import math

import pytest

from tcad.physics.contact import K_B_EV, WSe2TransportWindow


def make(**kwargs):
    values = dict(center_gate_V=0., width_V=1., peak_current_A_per_um=1.,
                  floor_current_A_per_um=math.ulp(0.))
    values.update(kwargs)
    return WSe2TransportWindow(**values)


def reference(model, gate, drain=.5, temperature=300.):
    """Use the literal window formula, retaining complements in Decimal."""
    with localcontext() as ctx:
        ctx.prec = 1600
        ctx.Emax = 999999999
        ctx.Emin = -999999999
        d = Decimal.from_float
        width = (model.left_width_V if gate < model.center_gate_V and model.left_width_V is not None
                 else model.right_width_V if gate >= model.center_gate_V and model.right_width_V is not None
                 else model.width_V)
        offset = d(gate) - d(model.center_gate_V)
        x = offset / d(width)
        lobe = (-x*x/2).exp() * max(1 + d(model.skew)*x, Decimal(0))
        def sigmoid(z):
            return 1 / (1 + (-z).exp())
        left = d(model.left_tail_fraction) * sigmoid(-offset / d(model.left_tail_smoothing_V or width))
        right = d(model.right_tail_fraction) * sigmoid(offset / d(model.right_tail_smoothing_V or width))
        tail = max(left, right)
        weight = tail + (1-tail)*lobe
        if model.notch_depth_decades:
            nx = (d(gate) - d(model.notch_center_gate_V))/d(model.notch_width_V)
            depth = d(model.notch_depth_decades) * (-nx*nx/2).exp()
            weight *= Decimal(10) ** (-depth)
        thermal = (d(model.temperature_activation_eV) / d(K_B_EV) * (
            1/d(model.temperature_reference_K) - 1/d(temperature))).exp()
        drive = (Decimal(1) if model.drain_exponent == 0. else
                 (abs(d(drain))/d(model.drain_reference_V)) ** d(model.drain_exponent))
        return dict(weight=float(weight), exact_zero=weight.is_zero(),
                    current=float(max(d(model.floor_current_A_per_um),
                                      d(model.peak_current_A_per_um)*weight*thermal*drive)))


CASES = [
    ('gaussian_underflow', dict(peak_current_A_per_um=1e300), 40., .5, 300.),
    ('thermal_restores_gaussian', dict(temperature_activation_eV=40.), 40., .5, 600.),
    ('clipped_sigmoid', dict(width_V=.1, right_tail_fraction=.5,
        right_tail_smoothing_V=1., peak_current_A_per_um=1e30), -50., .5, 300.),
    ('sigmoid_underflow', dict(width_V=10., right_tail_fraction=.5,
        right_tail_smoothing_V=1., peak_current_A_per_um=1e300), -800., .5, 300.),
    ('notch_underflow', dict(peak_current_A_per_um=1e300, notch_center_gate_V=0.,
        notch_depth_decades=400.), 0., .5, 300.),
    ('coordinate_overflow', dict(center_gate_V=-1e308, width_V=1e308), 1e308, .5, 300.),
    ('skew_product_overflow', dict(skew=1e308), 2., .5, 300.),
    ('skew_cancellation', dict(skew=-math.nextafter(math.nextafter(1., 0.), 0.),
        peak_current_A_per_um=1e30), math.nextafter(1., math.inf), .5, 300.),
    ('tail_complement', dict(width_V=50., skew=1e100, right_tail_fraction=1.,
        right_tail_smoothing_V=1.), 50., .5, 300.),
    ('notch_coordinate_overflow', dict(center_gate_V=-1e308, notch_center_gate_V=1e308,
        notch_width_V=1e308, notch_depth_decades=10.), -1e308, .5, 300.),
    ('left_clipped_sigmoid', dict(width_V=.1, left_tail_fraction=.5,
        left_tail_smoothing_V=1., peak_current_A_per_um=1e30), 50., .5, 300.),
    ('subnormal_weight_rounding', dict(peak_current_A_per_um=1e300), 38.5, .5, 300.),
]


@pytest.mark.parametrize('name,kwargs,gate,drain,temperature', CASES, ids=[c[0] for c in CASES])
def test_complete_current_recovers_gate_scaling(name, kwargs, gate, drain, temperature):
    model = make(**kwargs)
    expected = reference(model, gate, drain, temperature)['current']
    assert model.current_A_per_um(gate, drain, temperature) == pytest.approx(
        expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('gate', [-40., -10., -1., 0., 1., 10., 40.])
@pytest.mark.parametrize('kwargs', [dict(), dict(skew=.5), dict(left_width_V=2., right_width_V=.5),
    dict(left_tail_fraction=.3, right_tail_fraction=.8),
    dict(notch_center_gate_V=0., notch_width_V=2., notch_depth_decades=400.)])
def test_public_weight_matches_formula_or_rejects_nonzero_underflow(gate, kwargs):
    model = make(**kwargs)
    expected = reference(model, gate)
    if expected['weight'] == 0. and not expected['exact_zero']:
        with pytest.raises(ValueError, match='representable'):
            model.gate_weight(gate)
    else:
        assert model.gate_weight(gate) == pytest.approx(expected['weight'], rel=5e-12,
                                                       abs=math.ulp(expected['weight']))


@pytest.mark.parametrize('gate', [-800., -50., -40., 0., 40., 50., 800.])
@pytest.mark.parametrize('fraction', [math.ulp(0.), .5, 1.])
def test_tail_and_its_complement_survive_scaling(gate, fraction):
    model = make(width_V=10., right_tail_fraction=fraction, right_tail_smoothing_V=1.,
                 skew=1e100, peak_current_A_per_um=1e200)
    expected = reference(model, gate)['current']
    assert model.current_A_per_um(gate, .5, 300.) == pytest.approx(
        expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('gate', [-40., -2., 0., 2., 40.])
@pytest.mark.parametrize('depth', [0., 3., 400.])
def test_reflection_swaps_asymmetric_widths_tails_and_skew(gate, depth):
    first = make(left_width_V=2., right_width_V=.5, left_tail_fraction=.3,
        right_tail_fraction=.8, left_tail_smoothing_V=.7, right_tail_smoothing_V=.2,
        skew=.5, notch_center_gate_V=.5, notch_depth_decades=depth)
    reflected = make(left_width_V=.5, right_width_V=2., left_tail_fraction=.8,
        right_tail_fraction=.3, left_tail_smoothing_V=.2, right_tail_smoothing_V=.7,
        skew=-.5, notch_center_gate_V=-.5, notch_depth_decades=depth)
    assert first.current_A_per_um(gate, .5, 300.) == reflected.current_A_per_um(-gate, .5, 300.)


@pytest.mark.parametrize('gate,skew', [(1., -1.), (2., -1.), (-1., 1.), (-2., 1.)])
def test_clipped_skew_without_tails_is_exact_zero(gate, skew):
    model = make(skew=skew, peak_current_A_per_um=1e300, temperature_activation_eV=40.)
    assert model.gate_weight(gate) == 0.
    assert model.current_A_per_um(gate, .5, 600.) == model.floor_current_A_per_um


@pytest.mark.parametrize('gate', [math.nan, math.inf, -math.inf])
def test_invalid_gate_is_rejected_before_zero_drain_shortcut(gate):
    model = make()
    with pytest.raises(ValueError, match='finite'):
        model.gate_weight(gate)
    with pytest.raises(ValueError, match='finite'):
        model.current_A_per_um(gate, 0., 300.)


@pytest.mark.parametrize('kwargs,gate', [
    (dict(width_V=math.ulp(0.)), 1e308),
    (dict(), 1e200),
    (dict(notch_center_gate_V=0., notch_depth_decades=1e308), 0.),
])
def test_internal_logarithm_overflow_can_still_return_explicit_floor(kwargs, gate):
    model = make(**kwargs)
    assert model.current_A_per_um(gate, .5, 300.) == model.floor_current_A_per_um
    with pytest.raises(ValueError, match='representable'):
        model.gate_weight(gate)
