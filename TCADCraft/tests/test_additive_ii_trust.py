"""Additive avalanche Newton steps must advance both bias directions."""
import numpy as np
import pytest
from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('model', MODELS[:2])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
def test_additive_avalanche_both_biases_satisfy_independent_equations(axis, ptype, bias, model, coefficients):
    sim = avalanche_bar(axis, ptype, bias, 'additive', model, coefficients)
    assert sim.get_newton_log_density_update() == 'additive'
    r = sim.solve()
    assert r['converged']
    independent_balance(r, axis, ptype, bias, model, coefficients)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('model', MODELS[:2])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
@pytest.mark.parametrize('budget', [0, 1])
def test_reverse_additive_budget_is_honest_failure(axis, ptype, model, coefficients, budget):
    bias = .2 if ptype else -.2
    r = avalanche_bar(axis, ptype, bias, 'additive', model, coefficients, budget).solve()
    assert not r['converged']
    assert all(np.all(np.isfinite(r[key])) for key in ('phi', 'n', 'p'))


@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('model', MODELS[:2])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
def test_reverse_additive_uses_density_trust(ptype, model, coefficients, monkeypatch, capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    bias = .2 if ptype else -.2
    r = avalanche_bar(0, ptype, bias, 'additive', model, coefficients).solve()
    output = capfd.readouterr().out
    assert '[additive II trust]' in output
    assert r['converged']
    independent_balance(r, 0, ptype, bias, model, coefficients)
