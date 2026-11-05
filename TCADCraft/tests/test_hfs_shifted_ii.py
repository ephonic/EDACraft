"""Independent physical acceptance of the strong positive p-type HFS/II bar."""
import re
import pytest
from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_strong_p_gqf_accepts_shifted_direction(axis, monkeypatch, capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    result = avalanche_bar(axis, True, .2, 'additive', MODELS[3], COEFFICIENTS[1]).solve()
    output = capfd.readouterr().out
    steps = re.findall(r'\[HFS shifted direction\] lambda=([^ ]+) alpha=([^ ]+)', output)
    assert any(float(lam) > 0. and 0. < float(alpha) <= 1. for lam, alpha in steps)
    assert result['converged']
    independent_balance(result, axis, True, .2, MODELS[3], COEFFICIENTS[1])


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_strong_p_gqf_respects_tighter_physical_tolerance(axis):
    sim = avalanche_bar(axis, True, .2, 'additive', MODELS[3], COEFFICIENTS[1])
    sim.set_tolerance(1e-10)
    result = sim.solve()
    assert result['converged']
    independent_balance(result, axis, True, .2, MODELS[3], COEFFICIENTS[1], tolerance=1e-10)
