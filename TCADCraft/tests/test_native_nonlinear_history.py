"""Native nonlinear diagnostics must be measured, separated and opt-in."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator


def make_device(axis=0, budget=80):
    shape = [1, 1, 1]; shape[axis] = 9
    sim = PyDeviceSimulator(*shape, 1e-8, 1e-8, 1e-8)
    sim.set_permittivity(np.full(9, 11.7*8.854187817e-12))
    sim.set_mobility(np.zeros(9), np.zeros(9)); sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9, 1e16), np.full(9, 1e16)); sim.set_bandgap(np.full(9, 6.))
    sim.set_recombination(np.full(9, 1e100), np.full(9, 1e100))
    sim.set_dirichlet_potential({0: 0., 8: .2})
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_gummel_max_iter(budget); sim.set_tolerance(1e-12)
    return sim


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_gummel_history_contains_actual_update_and_equation_samples(axis):
    sim = make_device(axis)
    sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    assert result['converged']
    assert result['nonlinear_history_enabled']
    stage, = result['nonlinear_history']
    assert stage['solver'] == 'gummel' and stage['converged']
    assert len(stage['poisson_relative_l2']) == result['iterations'] >= 2
    assert stage['relative_phi_update'][0] > stage['relative_phi_update'][-1]
    assert np.all(np.isfinite(stage['poisson_relative_l2']))
    assert not np.shares_memory(stage['poisson_relative_l2'], stage['relative_phi_update'])
    assert stage['final_poisson_residual'] == result['poisson_residual']


def test_disabled_history_does_not_fabricate_a_final_residual_sequence():
    result = make_device().solve()
    assert not result['nonlinear_history_enabled'] and result['nonlinear_history'] == []
    assert 'iteration_residuals' not in result


@pytest.mark.parametrize('budget', [0, 1])
def test_failed_or_zero_budget_solve_keeps_its_real_stage(budget):
    sim = make_device(budget=budget)
    sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    stage, = result['nonlinear_history']
    assert stage['converged'] == result['converged']
    if budget == 0: assert not result['converged']
    assert len(stage['poisson_relative_l2']) == budget


def test_history_is_reset_between_calls_and_python_arrays_own_storage():
    sim = make_device(); sim.set_nonlinear_history_enabled(True)
    first = sim.solve(); saved = first['nonlinear_history'][0]['relative_phi_update'].copy()
    second = sim.solve()
    np.testing.assert_array_equal(first['nonlinear_history'][0]['relative_phi_update'], saved)
    assert len(first['nonlinear_history']) == len(second['nonlinear_history']) == 1
    sim.set_nonlinear_history_enabled(False)
    assert sim.solve()['nonlinear_history'] == []


def make_transport(axis=0, budget=80, primary=False, hybrid=False, generation=0.):
    shape = [1, 1, 1]; shape[axis] = 3
    sim = PyDeviceSimulator(*shape, 1e-7, 1e-7, 1e-7)
    sim.set_permittivity(np.full(3, 11.7*8.854187817e-12))
    sim.set_mobility(np.full(3, .1), np.full(3, .05))
    sim.set_doping(np.array([0., 1.5e18, 0.]))
    sim.set_effective_dos(np.full(3, 1e19), np.full(3, 1e19)); sim.set_bandgap(np.zeros(3))
    sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    sim.set_optical_generation(np.full(3, generation))
    sim.set_dirichlet_potential({0: 0., 2: 0.})
    sim.set_electron_bc({0: 1e19, 2: 1e19}); sim.set_hole_bc({0: 1e19, 2: 1e19})
    sim.set_initial_guess(np.zeros(3), 1e19*np.array([1., 1.6, 1.]), 1e19*np.array([1., 1.1, 1.]))
    sim.set_gummel_max_iter(budget); sim.set_tolerance(1e-11)
    sim.set_use_newton(hybrid or primary); sim.set_newton_primary(primary)
    return sim


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_newton_raw_block_residuals_match_independent_initial_equations(axis):
    sim = make_transport(axis, primary=True); sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    assert result['converged']
    stage, = result['nonlinear_history']
    assert stage['solver'] == 'newton' and stage['converged']
    assert len(stage['relative_block_max']) == result['iterations'] >= 2
    # Initial phi is zero: Poisson source q*(p-n+doping); SG reduces to
    # diffusion. The one free carrier row has integrated flux mu*VT*2*delta/h.
    assert stage['raw_phi_l2'][0] == pytest.approx(1.602176634e-19*3.5e18, rel=1e-12)
    assert stage['raw_n_l2'][0] == pytest.approx(.1*.02585*2*.6e19/1e-7, rel=1e-12)
    assert stage['raw_p_l2'][0] == pytest.approx(.05*.02585*2*.1e19/1e-7, rel=1e-12)
    blocks = np.array([stage[key] for key in ('raw_phi_l2', 'raw_n_l2', 'raw_p_l2')])
    np.testing.assert_allclose(stage['relative_block_max'], np.max(blocks/blocks[:, :1], axis=0), rtol=1e-14)
    assert stage['equilibrated_linf'][-1] < 1e-11


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_failed_hybrid_preserves_two_actual_stage_histories_and_rollback(axis):
    sim = make_transport(axis, budget=1, hybrid=True); sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    first, second = result['nonlinear_history']
    assert not result['converged']
    assert [first['solver'], second['solver']] == ['gummel', 'newton']
    assert not first['converged'] and not second['converged']
    assert len(first['poisson_relative_l2']) == len(second['relative_block_max']) == 1
    assert result['iterations'] == 2
    # Failed Newton candidate is rolled back. The returned state's final
    # Poisson audit matches the Gummel exit, not the last pre-trial sample.
    assert result['poisson_residual'] == first['final_poisson_residual']
    assert result['poisson_residual'] != first['poisson_relative_l2'][-1]


@pytest.mark.parametrize('budget', [1, 4, 8])
def test_optical_retries_retain_every_solver_invocation(budget):
    sim = make_transport(budget=budget, generation=1e28); sim.set_nonlinear_history_enabled(True)
    result = sim.solve(); stages = result['nonlinear_history']
    assert 1 <= len(stages) <= 3
    assert sum(len(s['poisson_relative_l2']) for s in stages) == result['iterations']
    assert all(s['solver'] == 'gummel' for s in stages)
    assert all(not s['converged'] for s in stages[:-1])
    assert stages[-1]['converged'] == result['converged']
    assert stages[0]['poisson_relative_l2'][0] > stages[-1]['poisson_relative_l2'][0]
    assert result['poisson_residual'] == stages[-1]['final_poisson_residual']
    if result['converged']:
        # Retry count depends on the residual scale. Verify the returned
        # physical state rather than requiring a specific number of retries.
        q, vt, dx, generation = 1.602176634e-19, .02585, 1e-7, 1e28
        d = np.diff(result['phi'])/vt
        bp = np.where(abs(d)<1e-12, 1., d/np.expm1(d))
        bm = np.where(abs(d)<1e-12, 1., -d/np.expm1(-d))
        n, p = result['n'], result['p']
        jn = q*.1*vt/dx*(n[1:]*bp-n[:-1]*bm)
        jp = q*.05*vt/dx*(p[:-1]*bp-p[1:]*bm)
        source = q*generation*dx
        assert abs(jn[1]-jn[0]+source)/max(abs(jn).sum(),source) < 1e-8
        assert abs(jp[1]-jp[0]-source)/max(abs(jp).sum(),source) < 1e-8


@pytest.mark.parametrize('primary', [False, True])
def test_zero_budget_has_empty_samples_without_invented_zeros(primary):
    sim = make_transport(budget=0, primary=primary); sim.set_nonlinear_history_enabled(True)
    result = sim.solve(); stage, = result['nonlinear_history']
    assert result['iterations'] == 0 and not result['converged']
    for key, value in stage.items():
        if isinstance(value, np.ndarray): assert value.size == 0


@pytest.mark.parametrize('bad', [0, 1, 'yes', None, np.nan, [], [True]])
def test_diagnostic_flag_requires_a_boolean(bad):
    with pytest.raises(ValueError): make_device().set_nonlinear_history_enabled(bad)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('path', ['gummel', 'newton', 'hybrid_failure', 'optical_retries', 'traps', 'quantum', 'fermi', 'fe'])
def test_diagnostic_reassembly_never_changes_fields_or_verdict(axis, path):
    def run(enabled):
        if path == 'fe':
            sim = make_device(axis)
            sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_model(0)
            sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), 2e8, 3e12)
            sim.set_ferroelectric_polar_axis(axis)
        else:
            sim = make_transport(axis, primary=path == 'newton', hybrid=path == 'hybrid_failure',
                budget=1 if path == 'hybrid_failure' else (8 if path == 'optical_retries' else 80),
                generation=1e28 if path == 'optical_retries' else 0.)
            if path == 'traps':
                sim.set_interface_traps(np.array([0, 1, 0], dtype=np.int8), 1e10, .1)
            if path == 'quantum': sim.set_quantum_enabled(True)
            if path == 'fermi': sim.set_statistics_type(1)
        sim.set_nonlinear_history_enabled(enabled)
        return sim.solve()
    plain, traced = run(False), run(True)
    for key in ('phi', 'n', 'p', 'Qn', 'Qp', 'Ex', 'Ey', 'Ez', 'P', 'Jn_x', 'Jn_y', 'Jn_z'):
        np.testing.assert_array_equal(plain[key], traced[key], err_msg=path+':'+key)
    for key in ('converged', 'iterations', 'poisson_residual', 'quantum_residual'):
        assert plain[key] == traced[key], path+':'+key
    assert plain['nonlinear_history'] == [] and traced['nonlinear_history']


def test_explicit_monotonicity_adapter_uses_one_measured_newton_stage():
    from tcad.validation.boundedness import MonotoneConvergenceTest
    sim = make_transport(primary=True); sim.set_nonlinear_history_enabled(True)
    result = sim.solve(); stage, = result['nonlinear_history']
    measured = dict(iteration_residuals=stage['relative_block_max'].copy(), converged=result['converged'])
    report = MonotoneConvergenceTest(runner=lambda sim: measured).run(object)
    assert report.passed, report.message
    assert not report.details['convergence_validated']
    measured['iteration_residuals'][2] = 2*measured['iteration_residuals'][1]
    assert not MonotoneConvergenceTest(runner=lambda sim: measured).run(object).passed


def test_high_level_history_option_forwards_to_native_without_coercion():
    from tcad.simulator import Simulator
    from types import SimpleNamespace
    recorded = []
    obj = Simulator.__new__(Simulator)
    obj._sim = SimpleNamespace(set_nonlinear_history_enabled=recorded.append)
    obj.set_nonlinear_history_enabled(True)
    assert recorded == [True]
