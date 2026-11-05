"""Direct mpmath references for moderate, scaled WSe2 cancellation."""
import importlib.util
import math
from pathlib import Path
import sys

import pytest
from tcad.physics.contact import K_B_EV

spec = importlib.util.spec_from_file_location('wide_oracle', Path(__file__).with_name('test_wse2_wide_window.py'))
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
make, reference = oracle.make, oracle.reference


def notch_case(center, peak=1.):
    depth = 1e300
    ea = 2*K_B_EV*depth*math.exp(-center*center/2)*math.log(10.)
    return dict(temperature_reference_K=1., temperature_activation_eV=ea,
        notch_center_gate_V=center, notch_width_V=1., notch_depth_decades=depth,
        peak_current_A_per_um=peak)


CASES = [(f'notch_{center}_{peak}', notch_case(center, peak), 0., .5, 2.)
         for center in (37., 37.025, 37.05) for peak in (1e-300, 1., 1e300)]


def assert_current(model, gate, drain, temperature):
    expected = reference(model, gate, drain, temperature)
    assert math.isfinite(expected)
    assert model.current_A_per_um(gate, drain, temperature) == pytest.approx(
        expected, rel=5e-12, abs=2*math.ulp(expected))


@pytest.mark.parametrize('name,kwargs,gate,drain,temperature', CASES, ids=[c[0] for c in CASES])
def test_moderate_notch_compensation_is_independent_of_peak(name, kwargs, gate, drain, temperature):
    assert_current(make(**kwargs), gate, drain, temperature)


@pytest.mark.parametrize('center', [37.1, 37.15, 37.2])
@pytest.mark.parametrize('peak', [1e-300, 1., 1e300])
def test_neighboring_compensation_preserves_formula(center, peak):
    assert_current(make(**notch_case(center, peak)), 0., .5, 2.)


@pytest.mark.parametrize('power', [6, 10, 16])
@pytest.mark.parametrize('peak', [1e-300, 1., 1e300])
def test_moderate_temperature_and_drain_compensation(power, peak):
    model = make(temperature_reference_K=1.,
        temperature_activation_eV=2*K_B_EV*math.log(2.)*2.**power,
        drain_reference_V=1., drain_exponent=2.**power, peak_current_A_per_um=peak)
    assert_current(model, 0., .5, 2.)


@pytest.mark.parametrize('center', [37., 37.025, 37.05])
@pytest.mark.parametrize('tail', [.1, 1.])
def test_tail_and_notch_compensation_still_use_full_window(center, tail):
    model = make(**notch_case(center), right_tail_fraction=tail, skew=.3)
    assert_current(model, 0., .5, 2.)


@pytest.mark.parametrize('exponent', [31., 32., 33., 64.])
def test_smooth_physical_cases_across_precision_trigger(exponent):
    model = make(temperature_reference_K=1., temperature_activation_eV=2*K_B_EV*exponent)
    assert_current(model, math.sqrt(2*exponent), .5, 2.)


@pytest.mark.parametrize('peak', [math.ulp(0.), sys.float_info.max])
def test_compensated_current_at_output_range_boundaries(peak):
    assert_current(make(**notch_case(37.05, peak)), 0., .5, 2.)
