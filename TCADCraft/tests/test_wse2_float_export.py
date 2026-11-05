"""Independent literal-formula checks at float64 output boundaries."""
import importlib.util
import math
from pathlib import Path
import sys

import mpmath as mp
import pytest
from tcad.physics.contact import K_B_EV

spec = importlib.util.spec_from_file_location('export_oracle', Path(__file__).with_name('test_wse2_wide_window.py'))
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
make = oracle.make
TINY, MAX = math.ulp(0.), sys.float_info.max


def expected(model, method, args):
    with mp.workdps(1900):
        m = mp.mpf
        if method == 'drain_factor':
            result = mp.power(abs(m(args[0]))/m(model.drain_reference_V), m(model.drain_exponent))
        elif method == 'temperature_factor':
            result = mp.exp(m(model.temperature_activation_eV)/m(K_B_EV)*(
                1/m(model.temperature_reference_K)-1/m(args[0])))
        else:
            gate = args[0]
            width = (model.left_width_V if gate < model.center_gate_V and model.left_width_V is not None
                     else model.right_width_V if gate >= model.center_gate_V and model.right_width_V is not None
                     else model.width_V)
            offset = m(gate)-m(model.center_gate_V)
            x = offset/m(width)
            lobe = mp.exp(-x*x/2)*max(1+m(model.skew)*x, 0)
            left = m(model.left_tail_fraction)/(1+mp.exp(offset/m(model.left_tail_smoothing_V or width)))
            right = m(model.right_tail_fraction)/(1+mp.exp(-offset/m(model.right_tail_smoothing_V or width)))
            tail = max(left, right)
            result = tail+(1-tail)*lobe
            if model.notch_depth_decades:
                nx = (m(gate)-m(model.notch_center_gate_V))/m(model.notch_width_V)
                result *= mp.power(10, -m(model.notch_depth_decades)*mp.exp(-nx*nx/2))
            if method == 'current_A_per_um':
                _, drain, temperature = args
                thermal = mp.exp(m(model.temperature_activation_eV)/m(K_B_EV)*(
                    1/m(model.temperature_reference_K)-1/m(temperature)))
                drive = mp.power(abs(m(drain))/m(model.drain_reference_V), m(model.drain_exponent))
                result = max(m(model.floor_current_A_per_um), m(model.peak_current_A_per_um)*result*thermal*drive)
        # float(mpf) can round the mantissa before scaling into subnormals.
        # Decimal text retains the side of the midpoint for one float conversion.
        return float(mp.nstr(result, n=1900))


def check(model, method, args, *, exact=False):
    ref = expected(model, method, args)
    if not math.isfinite(ref) or ref == 0.:
        with pytest.raises(ValueError, match='representable'):
            getattr(model, method)(*args)
    else:
        actual = getattr(model, method)(*args)
        assert math.isfinite(actual)
        assert actual == ref if exact else abs(actual-ref) <= 2*math.ulp(ref), (actual, ref)


CASES = [
    ('half_minimum', dict(drain_reference_V=2.), 'drain_factor', (TINY,)),
    ('below_half_minimum', dict(drain_reference_V=math.nextafter(2., math.inf)), 'drain_factor', (TINY,)),
    ('above_maximum', dict(drain_reference_V=math.nextafter(1., 0.)), 'drain_factor', (MAX,)),
    ('maximum_factor', dict(drain_reference_V=1.), 'drain_factor', (MAX,)),
    ('half_maximum_factor', dict(drain_reference_V=2.), 'drain_factor', (MAX,)),
    ('tail_below_half_minimum', dict(skew=-1., left_tail_fraction=TINY,
        left_tail_smoothing_V=MAX), 'gate_weight', (1.,)),
    ('current_above_maximum', dict(drain_reference_V=math.nextafter(1., 0.)), 'current_A_per_um', (0., MAX, 300.)),
    ('half_maximum_current', dict(peak_current_A_per_um=MAX, drain_reference_V=2.), 'current_A_per_um', (0., 1., 300.)),
    ('near_maximum_thermal', dict(temperature_reference_K=1.,
        temperature_activation_eV=2*K_B_EV*math.log(MAX)), 'temperature_factor', (2.,)),
]


@pytest.mark.parametrize('name,kwargs,method,args', CASES, ids=[c[0] for c in CASES])
def test_actual_old_export_failures(name, kwargs, method, args):
    check(make(**kwargs), method, args)


@pytest.mark.parametrize('reference', [math.nextafter(2., 0.), 2., math.nextafter(2., math.inf)])
@pytest.mark.parametrize('sign', [-1., 1.])
def test_linear_drain_half_minimum_neighbors(reference, sign):
    check(make(drain_reference_V=reference), 'drain_factor', (sign*TINY,))


@pytest.mark.parametrize('power,exponent', [(1.25, -860), (2.5, -430), (5., -215)])
@pytest.mark.parametrize('direction', [0., math.inf])
def test_nonlinear_drain_neighbors_of_half_minimum(power, exponent, direction):
    value = math.nextafter(math.ldexp(1., exponent), direction)
    check(make(drain_reference_V=1., drain_exponent=power), 'drain_factor', (value,))


@pytest.mark.parametrize('power,exponent', [(1.25, -860), (2.5, -430), (5., -215)])
def test_nonlinear_drain_exact_underflow_tie(power, exponent):
    check(make(drain_reference_V=1., drain_exponent=power), 'drain_factor', (math.ldexp(1., exponent),))


@pytest.mark.parametrize('reference', [math.nextafter(1., 0.), 1., math.nextafter(1., math.inf), 2.])
@pytest.mark.parametrize('method', ['drain_factor', 'current_A_per_um'])
def test_linear_drain_maximum_neighbors(reference, method):
    args = (MAX,) if method == 'drain_factor' else (0., MAX, 300.)
    check(make(drain_reference_V=reference), method, args)


@pytest.mark.parametrize('target', [math.log(MAX), math.log(TINY)-math.log(2.)])
@pytest.mark.parametrize('steps', [-2, -1, 0, 1, 2])
def test_thermal_output_boundary_neighbors(target, steps):
    energy = 2*K_B_EV*abs(target)
    for _ in range(abs(steps)):
        energy = math.nextafter(energy, math.inf if steps > 0 else 0.)
    model = make(temperature_activation_eV=energy, temperature_reference_K=1. if target > 0 else 2.)
    check(model, 'temperature_factor', (2. if target > 0 else 1.,))


@pytest.mark.parametrize('side', ['left', 'right'])
@pytest.mark.parametrize('smoothing', [1., 1e100, MAX])
def test_gate_tail_neighbors_of_underflow_tie(side, smoothing):
    check(make(skew=-1., **{side+'_tail_fraction': TINY,
        side+'_tail_smoothing_V': smoothing}), 'gate_weight', (1.,))


@pytest.mark.parametrize('peak', [1., 3., 5., 7.])
@pytest.mark.parametrize('power,exponent', [(1., -1074), (1.25, -860), (5., -215)])
def test_neutral_window_subnormal_rounding_ties(peak, power, exponent):
    reference = 2. if power == 1. else 1.
    check(make(peak_current_A_per_um=peak, drain_reference_V=reference,
        drain_exponent=power), 'current_A_per_um', (0., math.ldexp(1., exponent), 300.), exact=True)


@pytest.mark.parametrize('peak', [3., 5.])
@pytest.mark.parametrize('power,exponent', [(1., -1074), (1.25, -860), (5., -215)])
@pytest.mark.parametrize('direction', [0., math.inf])
def test_neutral_current_neighbors_of_rounding_ties(peak, power, exponent, direction):
    value = math.nextafter(math.ldexp(1., exponent), direction)
    reference = 2. if power == 1. else 1.
    check(make(peak_current_A_per_um=peak, drain_reference_V=reference,
        drain_exponent=power), 'current_A_per_um', (0., value, 300.), exact=True)


@pytest.mark.parametrize('peak', [3., 5.])
@pytest.mark.parametrize('side', ['left', 'right'])
def test_full_tail_current_preserves_side_of_rounding_tie(peak, side):
    check(make(peak_current_A_per_um=peak, skew=-1., **{side+'_tail_fraction': TINY,
        side+'_tail_smoothing_V': MAX}), 'current_A_per_um', (1., .5, 300.), exact=True)


@pytest.mark.parametrize('gate', [.01, 1., 2.])
def test_complete_non_neutral_window_near_maximum(gate):
    check(make(peak_current_A_per_um=MAX), 'current_A_per_um', (gate, .5, 300.))


def test_export_replay_ignores_callers_decimal_context():
    from decimal import Inexact, ROUND_UP, localcontext
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        check(make(drain_reference_V=1., drain_exponent=1.25), 'drain_factor', (math.ldexp(1., -860),))
        check(make(peak_current_A_per_um=MAX), 'current_A_per_um', (.01, .5, 300.))
