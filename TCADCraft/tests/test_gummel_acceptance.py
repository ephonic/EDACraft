"""Returned-state equation audits, distinct from updates and energy closure."""
import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.simulator import simulate_device
from test_native_nonlinear_history import make_transport


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('generation', [0., 1e25])
@pytest.mark.parametrize('reaction', ['none', 'srh', 'srh_auger'])
def test_each_carrier_row_matches_independent_diffusion_and_reaction(axis, generation, reaction):
    sim = make_transport(axis, budget=0, generation=generation)
    tn, tp = (1e-9, 2e-9) if reaction != 'none' else (1e100, 1e100)
    sim.set_recombination(np.full(3, tn), np.full(3, tp))
    cn, cp = (2.8e-43, 9.9e-44) if reaction == 'srh_auger' else (0., 0.)
    if cn:
        sim.set_auger_enabled(True)
        sim.set_auger_params(cn, cp)
    result = sim.solve()
    audit = result['steady_equation_audit']
    assert audit['available'] and not result['converged']
    n, p = result['n'][1], result['p'][1]
    ni = 1e19
    den = tp*(n+ni)+tn*(p+ni)
    r = (n*p-ni*ni)/den + (cn*n+cp*p)*(n*p-ni*ni)
    derivatives = ((p*(tp*ni+tn*(p+ni))+tp*ni*ni)/den**2,
                   (n*(tn*ni+tp*(n+ni))+tn*ni*ni)/den**2)
    for name, density, mobility, dr in zip(
            ('electron', 'hole'), (n, p), (.1, .05), derivatives):
        # Native SRH Newton diagonal contributes to the backward-error scale;
        # its contribution cancels in the physical residual numerator.
        diffusion = mobility*.02585/1e-7
        rhs = (generation-r+dr*density)*1e-7
        diagonal = 2*diffusion+dr*1e-7
        applied = diagonal*density-2*diffusion*ni
        expected = abs(applied-rhs)/(abs(rhs)+abs(diagonal*density)+2*diffusion*ni)
        assert audit[name+'_backward_error_linf'] == pytest.approx(expected, rel=2e-13, abs=2e-16)
    assert audit['poisson_scaled_linf'] == pytest.approx(result['poisson_residual'], rel=1e-13)
    assert audit['equation_gate'] == 1e-8
    assert audit['requested_update_tolerance'] == 1e-11
    assert not audit['equations_pass']
    assert not audit['complete_device_energy'] and not audit['physical_validated']


def test_original_ten_iteration_example_is_still_rejected():
    with pytest.warns(RuntimeWarning, match='valid=False'):
        _, result = simulate_device(Device.pnjunction(L=1e-6, W=1e-6, H=1e-6),
            resolution=(.5e-6,)*3, quantum=False, max_iter=10, tol=1e-6)
    audit = result['steady_equation_audit']
    assert not result['converged'] and not result['valid'] and not result['target_reached']
    assert result['iterations'] == 10
    assert audit['available'] and not audit['equations_pass']
    assert audit['poisson_scaled_linf'] > audit['equation_gate']


@pytest.mark.parametrize('budget', [20, 50])
def test_sufficient_budget_accepts_only_after_all_three_rows_pass(budget):
    _, result = simulate_device(Device.pnjunction(L=1e-6, W=1e-6, H=1e-6),
        resolution=(.5e-6,)*3, quantum=False, max_iter=budget, tol=1e-6)
    audit = result['steady_equation_audit']
    assert result['converged'] and result['valid'] and audit['equations_pass']
    assert audit['requested_update_tolerance'] == 1e-6
    assert audit['equation_gate'] == pytest.approx(1e-4, rel=1e-15)
    assert max(audit[k] for k in ('poisson_scaled_linf', 'electron_backward_error_linf',
                                'hole_backward_error_linf')) < audit['equation_gate']


@pytest.mark.parametrize('hybrid,primary,quantum', [(True, False, False), (False, True, False), (False, False, True)])
def test_other_formulations_do_not_inherit_a_classical_gummel_audit(hybrid, primary, quantum):
    sim = make_transport(hybrid=hybrid, primary=primary)
    sim.set_quantum_enabled(quantum)
    audit = sim.solve()['steady_equation_audit']
    assert not audit['available']
    for name in ('poisson_scaled_linf', 'electron_backward_error_linf', 'hole_backward_error_linf',
                 'equation_gate', 'requested_update_tolerance', 'equations_pass'):
        assert audit[name] is None


def test_diagnostics_own_storage_and_do_not_leak_from_previous_call():
    sim = make_transport()
    first = sim.solve()['steady_equation_audit']
    saved = dict(first)
    sim.set_use_newton(True)
    second = sim.solve()['steady_equation_audit']
    assert first == saved and first['available'] and not second['available']


def test_failed_state_audit_uses_returned_floor_clipped_densities():
    sim = make_transport(budget=0)
    sim.set_mobility(np.zeros(3), np.zeros(3))
    sim.set_initial_guess(np.array([0., .1, 0.]), np.array([1e19, 0., 1e19]),
                          np.array([1e19, 0., 1e19]))
    result = sim.solve()
    assert result['n'][1] == result['p'][1] == 1e6
    # Zero-mobility native rows freeze at EPSILON; failure then exports
    # the density floor. Auditing that returned state must expose the change.
    expected = 1.
    audit = result['steady_equation_audit']
    assert audit['electron_backward_error_linf'] == pytest.approx(expected, abs=2e-16)
    assert audit['hole_backward_error_linf'] == pytest.approx(expected, abs=2e-16)
    assert not result['converged'] and not audit['equations_pass']
