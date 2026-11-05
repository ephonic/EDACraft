"""Classical 1D additive avalanche with HFS retains full physical equations."""
import json
import os
import numpy as np
import pytest

from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS
from test_ii_field_floor import thin_result


QUALIFIED = [(ptype, bias, model, coefficients)
             for ptype in [False, True] for bias in [-.2, .2]
             for model in MODELS[2:] for coefficients in COEFFICIENTS
             if not (ptype and bias == .2 and model == MODELS[3] and coefficients == COEFFICIENTS[1])]


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype,bias,model,coefficients', QUALIFIED)
def test_hfs_additive_avalanche_converges_with_independent_equations(axis, ptype, bias, model, coefficients):
    r = avalanche_bar(axis, ptype, bias, 'additive', model, coefficients).solve()
    assert r['converged']
    independent_balance(r, axis, ptype, bias, model, coefficients)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('model', MODELS[2:])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
@pytest.mark.parametrize('budget', [0, 1])
def test_insufficient_hfs_budget_stays_failed_and_audit_scores_returned_fields(axis, ptype, bias, model, coefficients, budget):
    sim = avalanche_bar(axis, ptype, bias, 'additive', model, coefficients, budget)
    r = sim.solve(audit_newton=True)
    assert not r['converged']
    keys = ['phi', 'n', 'p', 'G_ii'] + ['J'+c+'_'+a for c in 'np' for a in 'xyz']
    assert all(np.all(np.isfinite(r[k])) for k in keys)
    from hfs_audit_reference_373 import assert_avalanche_audit_rows
    assert_avalanche_audit_rows(r, ptype, bias, model, coefficients)


@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('model', MODELS[2:])
def test_hfs_takes_relative_density_trust_and_still_satisfies_equations(ptype, bias, model, monkeypatch, capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    coefficients = COEFFICIENTS[0]
    r = avalanche_bar(0, ptype, bias, 'additive', model, coefficients).solve()
    output = capfd.readouterr().out
    assert '[additive II trust]' in output
    assert r['converged']
    independent_balance(r, 0, ptype, bias, model, coefficients)


@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('mi', [2, 3])
@pytest.mark.parametrize('ci', [0, 1])
def test_exponential_hfs_converges_with_independent_equations(ptype, bias, mi, ci):
    # Stage 372 explicitly replaces sixteen frozen failure comparisons.
    r = avalanche_bar(0, ptype, bias, 'exponential', MODELS[mi], COEFFICIENTS[ci]).solve()
    assert r['converged']
    independent_balance(r, 0, ptype, bias, MODELS[mi], COEFFICIENTS[ci])

def test_strong_reverse_n_gqf_takes_relative_density_trust(monkeypatch, capfd):
    import re
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    r = avalanche_bar(0, False, -.2, 'additive', MODELS[3], COEFFICIENTS[1]).solve()
    output = capfd.readouterr().out
    selected = re.findall(r'\[ls\] alpha=([^\s]+)', output)
    assert '[additive II trust]' in output
    assert selected and any(0. < float(a) <= 1. for a in selected)
    assert r['converged']
    independent_balance(r, 0, False, -.2, MODELS[3], COEFFICIENTS[1])


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_strong_positive_p_gqf_converges_with_independent_equations(axis):
    # Stage 371 replaces the three explicitly unresolved stage 370 cases
    # with full returned-state physical acceptance at the same tolerance.
    r = avalanche_bar(axis, True, .2, 'additive', MODELS[3], COEFFICIENTS[1]).solve()
    assert r['converged']
    independent_balance(r, axis, True, .2, MODELS[3], COEFFICIENTS[1])
