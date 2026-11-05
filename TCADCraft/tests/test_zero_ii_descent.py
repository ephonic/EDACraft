"""Zero avalanche amplitudes must retain source-free Newton globalization."""
import re
import numpy as np
import pytest
from test_newton_descent_fallback import cold_bar, independent_equations
from test_ii_field_floor import thin_result

COEFFICIENTS = [(0., 0., 0., 0.), (0., 2e5, 0., 3e5)]
REFERENCES = [(0., 0.), (5e18, 8e18)]


def zero_bar(axis=0, ptype=False, bias=.2, mode=0, coefficients=COEFFICIENTS[0],
             refs=REFERENCES[0], enabled=True, budget=60):
    sim = cold_bar(axis, ptype, bias, budget=budget)
    sim.set_ii_params(*coefficients)
    sim.set_ii_driving(mode)
    sim.set_ii_reference_density(*refs)
    sim.set_ii_enabled(enabled)
    return sim


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('mode', [0, 1])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
@pytest.mark.parametrize('refs', REFERENCES)
def test_zero_ii_matches_disabled_and_independent_equations(axis, ptype, bias, mode, coefficients, refs):
    disabled = zero_bar(axis, ptype, bias, mode, coefficients, refs, False).solve()
    enabled = zero_bar(axis, ptype, bias, mode, coefficients, refs, True).solve()
    assert enabled['converged'] and disabled['converged']
    independent_equations(enabled, axis, ptype, bias, False)
    assert np.array_equal(enabled['G_ii'], np.zeros(9))
    assert thin_result(enabled) == thin_result(disabled)
    # Zero source assembly can change cancellation in raw residuals near the
    # solution. Compare those diagnostics against their initial residual scale;
    # the returned state and physical audit above still require exact equality.
    a, b = enabled['nonlinear_history'], disabled['nonlinear_history']
    assert len(a) == len(b)
    for actual, expected in zip(a, b):
        assert actual.keys() == expected.keys()
        for key, value in actual.items():
            if isinstance(value, np.ndarray):
                reference = expected[key]
                assert value.shape == reference.shape and value.size > 0
                assert np.all(np.isfinite(value)) and np.all(value >= 0)
                scale = max(1., abs(float(reference[0]))) if key.startswith('raw_') else 1.
                np.testing.assert_allclose(value/scale, reference/scale, rtol=1e-12, atol=1e-14)
            else:
                assert value == expected[key]


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('mode', [0, 1])
@pytest.mark.parametrize('budget', [0, 1])
def test_zero_ii_insufficient_budget_remains_failure(axis, mode, budget):
    r = zero_bar(axis=axis, mode=mode, budget=budget).solve()
    assert not r['converged']
    assert all(np.all(np.isfinite(r[key])) for key in ('phi', 'n', 'p'))


@pytest.mark.parametrize('mode', [0, 1])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
def test_zero_ii_accepts_exponential_descent_fallback(mode, coefficients, monkeypatch, capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    r = zero_bar(mode=mode, coefficients=coefficients).solve()
    output = capfd.readouterr().out
    steps = re.findall(r'\[descent fallback\] policy=exponential scale=([^ ]+) alpha=([^\s]+)', output)
    assert r['converged']
    assert steps and any(float(alpha) > 0 for _, alpha in steps)
    independent_equations(r, 0, False, .2, False)
