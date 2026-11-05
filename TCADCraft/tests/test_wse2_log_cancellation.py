"""Independent direct mpmath formulas for finite cancelling window logs."""
from decimal import Inexact, ROUND_CEILING, ROUND_FLOOR, localcontext
import importlib.util
import math
from pathlib import Path

import pytest

from tcad.physics.contact import K_B_EV

spec = importlib.util.spec_from_file_location('wide_oracle', Path(__file__).with_name('test_wse2_wide_window.py'))
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
make, reference = oracle.make, oracle.reference


CASES = [
    *[(f'skew_log_{power}_{peak}', dict(peak_current_A_per_um=peak,
        temperature_activation_eV=K_B_EV, temperature_reference_K=math.ldexp(1., -2*power),
        skew=math.ldexp(1., -power)), math.ldexp(1., power), .5,
        math.ldexp(1., 1-2*power)) for power in (10, 25, 100, 500) for peak in (1e-300, 1., 1e300)],
    *[(f'thermal_drain_{power}', dict(temperature_reference_K=1.,
        temperature_activation_eV=2*K_B_EV*math.log(2.)*2.**power,
        drain_reference_V=1., drain_exponent=2.**power), 0., .5, 2.) for power in (20, 40)],
    *[(f'thermal_notch_{depth}', dict(temperature_reference_K=1.,
        temperature_activation_eV=2*K_B_EV*math.log(10.)*depth,
        notch_center_gate_V=0., notch_depth_decades=depth), 0., .5, 2.) for depth in (1e6, 1e16)],
]


@pytest.mark.parametrize('name,kwargs,gate,drain,temperature', CASES, ids=[c[0] for c in CASES])
def test_cancelling_finite_logs_keep_actual_signal(name, kwargs, gate, drain, temperature):
    model = make(**kwargs)
    expected = reference(model, gate, drain, temperature)
    assert math.isfinite(expected)
    assert model.current_A_per_um(gate, drain, temperature) == pytest.approx(
        expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('power', [10, 25, 100, 500])
def test_lobe_cancellation_retains_exact_factor_two(power):
    model = make(temperature_activation_eV=K_B_EV,
        temperature_reference_K=math.ldexp(1., -2*power), skew=math.ldexp(1., -power))
    assert reference(model, math.ldexp(1., power), .5, math.ldexp(1., 1-2*power)) == 2.
    assert model.current_A_per_um(math.ldexp(1., power), .5, math.ldexp(1., 1-2*power)) == 2.


@pytest.mark.parametrize('setting', ['inexact_trap', 'floor', 'ceiling', 'small_range'])
@pytest.mark.parametrize('wide', [False, True])
def test_fallback_is_isolated_from_caller_decimal_context(setting, wide):
    model = (make(width_V=math.ulp(0.), right_tail_fraction=.5) if wide else
             make(temperature_activation_eV=K_B_EV, temperature_reference_K=2.**-50, skew=2.**-25))
    args = (1e308, .5, 300.) if wide else (2.**25, .5, 2.**-49)
    expected = .5 if wide else 2.
    with localcontext() as ctx:
        ctx.prec = 3
        if setting == 'inexact_trap':
            ctx.traps[Inexact] = True
        elif setting == 'floor':
            ctx.rounding = ROUND_FLOOR
        elif setting == 'ceiling':
            ctx.rounding = ROUND_CEILING
        else:
            ctx.Emax, ctx.Emin = 9, -9
        ctx.clear_flags()
        before = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin, dict(ctx.traps), dict(ctx.flags))
        assert model.current_A_per_um(*args) == expected
        assert (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin, dict(ctx.traps), dict(ctx.flags)) == before


@pytest.mark.parametrize('peak', [1e-300, 1., 1e300])
def test_finite_log_path_still_preserves_neutral_peak(peak):
    assert make(peak_current_A_per_um=peak).current_A_per_um(0., .5, 300.) == peak
