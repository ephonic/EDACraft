"""Bounded exponential HFS/II acceptance using independent FV equations."""
import json
import os
import re
import numpy as np
import pytest
from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS
from test_ii_field_floor import thin_result
from test_newton_descent_fallback import cold_bar


CASES = [(ptype, bias, mi, ci) for ptype in [False, True] for bias in [-.2, .2]
         for mi in [2, 3] for ci in [0, 1]]


@pytest.mark.parametrize('axis', [1, 2])
@pytest.mark.parametrize('ptype,bias,mi,ci', CASES)
def test_exponential_hfs_other_axes_satisfy_independent_equations(axis, ptype, bias, mi, ci):
    result = avalanche_bar(axis, ptype, bias, 'exponential', MODELS[mi], COEFFICIENTS[ci]).solve()
    assert result['converged']
    independent_balance(result, axis, ptype, bias, MODELS[mi], COEFFICIENTS[ci])


@pytest.mark.parametrize('budget', [0, 1])
@pytest.mark.parametrize('ptype,bias,mi,ci', CASES)
def test_exponential_hfs_insufficient_budget_stays_failed_with_returned_audit(budget, ptype, bias, mi, ci):
    result = avalanche_bar(0, ptype, bias, 'exponential', MODELS[mi], COEFFICIENTS[ci], budget).solve(audit_newton=True)
    assert not result['converged']
    assert all(np.all(np.isfinite(result[key])) for key in ['phi', 'n', 'p', 'G_ii'])
    from hfs_audit_reference_373 import assert_avalanche_audit_rows
    assert_avalanche_audit_rows(result, ptype, bias, MODELS[mi], COEFFICIENTS[ci])


@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('mi', [2, 3])
def test_exponential_hfs_strong_source_respects_tighter_tolerance(ptype, mi):
    sim = avalanche_bar(0, ptype, .2, 'exponential', MODELS[mi], COEFFICIENTS[1])
    sim.set_tolerance(1e-10)
    result = sim.solve()
    assert result['converged']
    independent_balance(result, 0, ptype, .2, MODELS[mi], COEFFICIENTS[1], tolerance=1e-10)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype,bias,mi,ci', CASES)
def test_additive_hfs_preserves_exact_frozen_parent(axis, ptype, bias, mi, ci):
    with open(os.environ['TCAD_HFS_ADDITIVE_ORACLE'], encoding='utf8') as stream:
        rows = json.load(stream)
    expected = next(row for row in rows if row['policy'] == 'additive' and row['axis'] == axis
                    and row['ptype'] == ptype and row['bias'] == bias and row['model'] == mi and row['coeff'] == ci)
    result = avalanche_bar(axis, ptype, bias, 'additive', MODELS[mi], COEFFICIENTS[ci]).solve()
    assert thin_result(result) == expected['result']


@pytest.mark.parametrize('ptype', [False, True])
def test_exponential_hfs_takes_log_trust_and_accepted_step(ptype, monkeypatch, capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE', '1')
    result = avalanche_bar(0, ptype, .2, 'exponential', MODELS[3], COEFFICIENTS[1]).solve()
    output = capfd.readouterr().out
    assert '[exponential II trust]' in output
    steps = re.findall(r'\[ls\] alpha=([^\s]+)', output)
    assert any(0. < float(step) <= 1. for step in steps)
    assert result['converged']
    independent_balance(result, 0, ptype, .2, MODELS[3], COEFFICIENTS[1])


def test_default_density_update_matches_explicit_exponential_hfs():
    model = MODELS[3]
    implicit = cold_bar(0, False, .2, budget=60)
    mode, refs, hfs, driving, contacts, hfrefs = model
    implicit.set_ii_params(*COEFFICIENTS[1])
    implicit.set_ii_enabled(True)
    implicit.set_ii_driving(mode)
    implicit.set_ii_reference_density(*refs)
    implicit.set_high_field_saturation(hfs, 5e4, 4e4, 2., 1., driving)
    implicit.set_hfs_quasi_fermi_at_contacts(contacts)
    implicit.set_high_field_reference_density(*hfrefs)
    result = implicit.solve()
    explicit = avalanche_bar(0, False, .2, 'exponential', model, COEFFICIENTS[1]).solve()
    assert result['converged'] and thin_result(result) == thin_result(explicit)
    independent_balance(result, 0, False, .2, model, COEFFICIENTS[1])
