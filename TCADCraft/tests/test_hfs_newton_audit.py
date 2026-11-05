"""Optional HFS audit scores actual returned fields without changing solving."""
import json
import os
import numpy as np
import pytest
from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS
from test_newton_returned_audit import same_value, check_audit
from test_ii_field_floor import thin_result
from test_native_nonlinear_history import make_transport
from test_ii_driving import bar as operator_bar, HFREF
from test_hfs_contact_policy import N, P, PHI
from hfs_audit_reference_373 import reference_rows, check_rows, assert_avalanche_audit_rows


CASES = [(ptype, bias, mi, ci) for ptype in [False, True] for bias in [-.2, .2]
         for mi in [2, 3] for ci in [0, 1]]


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('policy', ['exponential', 'additive'])
@pytest.mark.parametrize('ptype,bias,mi,ci', CASES)
def test_hfs_audit_preserves_default_and_exact_parent(axis, policy, ptype, bias, mi, ci):
    model, coeff = MODELS[mi], COEFFICIENTS[ci]
    default = avalanche_bar(axis, ptype, bias, policy, model, coeff).solve()
    audited = avalanche_bar(axis, ptype, bias, policy, model, coeff).solve(audit_newton=True)
    assert default['converged'] and audited['converged']
    same_value({k: v for k, v in default.items() if k != 'steady_equation_audit'},
               {k: v for k, v in audited.items() if k != 'steady_equation_audit'})
    assert not default['steady_equation_audit']['available']
    with open(os.environ['TCAD_HFS_ADDITIVE_ORACLE'], encoding='utf8') as stream:
        rows = json.load(stream)
    parent = next(row for row in rows if row['policy'] == policy and row['axis'] == axis
                  and row['ptype'] == ptype and row['bias'] == bias and row['model'] == mi and row['coeff'] == ci)
    assert thin_result(default) == parent['result']
    assert assert_avalanche_audit_rows(audited, ptype, bias, model, coeff)['equations_pass']
    independent_balance(audited, axis, ptype, bias, model, coeff)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('policy', ['exponential', 'additive'])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('budget', [0, 1])
@pytest.mark.parametrize('reactions', [False, True])
def test_failed_hfs_primary_and_hybrid_audit_returned_fields(axis, policy, ptype, bias, primary, budget, reactions):
    sim = avalanche_bar(axis, ptype, bias, policy, MODELS[3], COEFFICIENTS[1], budget)
    sim.set_newton_primary(primary)
    light, auger = (1e24, (2.8e-43, 9.9e-44)) if reactions else (0., (0., 0.))
    sim.set_optical_generation(np.full(9, light))
    sim.set_auger_enabled(reactions)
    if reactions: sim.set_auger_params(*auger)
    result = sim.solve(audit_newton=True)
    assert not result['converged']
    assert_avalanche_audit_rows(result, ptype, bias, MODELS[3], COEFFICIENTS[1], optical=light, auger=auger)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('contacts', [False, True])
@pytest.mark.parametrize('ii_mode', [0, 1])
@pytest.mark.parametrize('cutoff', [0., 3e5, 1e6])
def test_hfs_audit_reconstructs_cutoff_contacts_and_reference_sources(axis, driving, contacts, ii_mode, cutoff):
    refs = (5e18, 8e18)
    sim = operator_bar(axis, True, refs, (True, driving, contacts), mode=ii_mode)
    sim.set_hfs_low_field_cutoff(cutoff)
    result = sim.solve(audit_newton=True)
    assert not result['converged']
    model = (ii_mode, refs, True, driving, contacts, HFREF)
    expected = reference_rows(result, model, COEFFICIENTS[1], spacing=1e-7,
                              vt=.02585, mobility=(.1, .05), dos=(1e19, 1e19), bandgap=6.,
                              doping=0., potential_bc=PHI[[0, -1]],
                              carrier_bc=(N[[0, -1]], P[[0, -1]]), lifetime=1e100, cutoff=cutoff)
    check_rows(result, expected)


@pytest.mark.parametrize('feature', ['fermi', 'btbt', 'freeze_phi',
                                    'freeze_n', 'freeze_p', 'Nc', 'Nv', 'Eg', 'immobile', 'traps'])
def test_hfs_combined_with_unsupported_physics_stays_unavailable(feature):
    sim = make_transport(primary=True, budget=0)
    sim.set_high_field_saturation(True, 5e4, 4e4, 2., 1., 0)
    if feature == 'quantum': sim.set_quantum_enabled(True)
    elif feature == 'fermi': sim.set_statistics_type(1)
    elif feature == 'btbt': sim.set_btbt_enabled(True)
    elif feature.startswith('freeze_'): getattr(sim, 'set_newton_'+feature)(True)
    elif feature in ('Nc', 'Nv'):
        nc = np.full(3, 1e19); nv = nc.copy(); (nc if feature == 'Nc' else nv)[1] *= 2
        sim.set_effective_dos(nc, nv)
    elif feature == 'Eg': sim.set_bandgap(np.array([0., .1, 0.]))
    elif feature == 'immobile': sim.set_mobility(np.zeros(3), np.full(3, .05))
    elif feature == 'traps': sim.set_interface_traps(np.ones(3, dtype=np.int8), 1e14, 0.)
    audit = sim.solve(audit_newton=True)['steady_equation_audit']
    assert not audit['available'] and audit['unavailable_reason'] == 'unsupported_newton_audit_physics'
    assert all(audit[key] is None for key in ['poisson_scaled_linf', 'electron_backward_error_linf',
               'hole_backward_error_linf', 'equation_gate', 'requested_update_tolerance', 'equations_pass'])


def test_hfs_audit_does_not_leak_across_calls():
    sim = avalanche_bar(model=MODELS[2])
    first = sim.solve(audit_newton=True)
    saved = dict(first['steady_equation_audit'])
    assert check_audit(first)['equations_pass']
    assert not sim.solve()['steady_equation_audit']['available']
    assert first['steady_equation_audit'] == saved


def test_public_run_forwards_hfs_audit():
    from test_transport_parameter_guard import resistor
    owner, sim = resistor(public=True)
    sim.set_use_newton(True); sim.set_newton_primary(True)
    sim.set_high_field_saturation(True, 5e4, 4e4, 2., 1., 1)
    sim.set_ii_params(*COEFFICIENTS[0]); sim.set_ii_enabled(True)
    result = owner.run(max_iter=60, tol=1e-8, audit_newton=True)
    assert result['converged'] and check_audit(result)['equations_pass']
    independent_balance(result, 0, False, .2, MODELS[2], COEFFICIENTS[0])


def test_previously_rejected_hfs_probe_has_returned_rows():
    sim = make_transport(primary=True, budget=0)
    sim.set_high_field_saturation(True, 5e4, 4e4, 2., 1., 1)
    result = sim.solve(audit_newton=True)
    assert not result['converged'] and not check_audit(result)['equations_pass']
