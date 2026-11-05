"""Measured transient attempts must survive rollback without adding dwell."""
import numpy as np
import pytest

from test_transient_timeline import slab
from test_transient_selfconsistent import central_cell
from test_transient_lk_error_control import controlled
from test_transient_voltage_waveforms import driven_film
from test_transient_nls_error_control import configured
from test_fe_transient_feedback import dielectric

COLUMNS = ('relative_block_max', 'raw_phi_l2', 'raw_n_l2', 'raw_p_l2',
           'scaled_merit_rms', 'equilibrated_linf')
MATERIAL_COLUMNS = ('voltage_residual_V', 'd_voltage_d_displacement_m2_F')


def trace_columns(trial):
    assert trial['solver'] in ('newton', 'lk_material_field_1d')
    return MATERIAL_COLUMNS if trial['solver'] == 'lk_material_field_1d' else COLUMNS


def make_case(path, axis=0):
    if path == 'fixed': return central_cell(1e19, False, axis, True)[0]
    if path == 'classical':
        sim = central_cell(1e19, False, axis, True)[0]
        sim.set_transient_electrical_error_control(True)
        return sim
    if path == 'nls': return configured(axis)[0]
    sim = driven_film(axis, model=0, fe=True, layered=True, dt=1e-7)[0]
    if path == 'lk_centered': sim.set_transient_lk_material_field(False)
    return controlled(sim, rtol=1e-3, atol=1e-8)


def assert_timeline(history, groups):
    retained = [t for g in groups for t in g['trials'] if t['retained']]
    committed = [s for s in history[1:] if s['valid']]
    assert len(retained) == len(committed)
    for trial, state in zip(retained, committed):
        assert trial['attempted_time_s'] == state['time_s']
        assert trial['dt_s'] == state['dt_s']
        assert len(trial[trace_columns(trial)[0]]) == state['iterations']
    assert sum(t['dt_s'] for t in retained) == pytest.approx(history[-1]['time_s'], rel=1e-14)
    for i, g in enumerate(groups):
        assert g['group_index'] == i
        assert g['dt_s'] == pytest.approx(g['attempted_time_s']-g['start_time_s'], rel=2e-14)
        for t in g['trials']:
            assert t['solver_called']
            columns = trace_columns(t)
            if t['solver'] == 'lk_material_field_1d':
                assert t['sample_scope'] == 'voltage_constraint_base_states'
                assert all(c not in t for c in COLUMNS)
                assert np.all(t['d_voltage_d_displacement_m2_F'] > 0.)
            else:
                assert t['sample_scope'] == 'outer_base_states_before_line_search'
                assert all(c not in t for c in MATERIAL_COLUMNS)
            assert len({len(t[c]) for c in columns}) == 1
            assert all(np.all(np.isfinite(t[c])) for c in columns)
            assert t['retained'] == (g['accepted'] and t['converged'] and t['role'] != 'coarse')
        if g['accepted']:
            assert g['status'] == g['stopping_reason'] == 'accepted'
        for control, field in [('polarization_control', 'polarization_error_ratio'),
                               ('electrical_control', 'electrical_error_ratio')]:
            if g['error_estimate_available'] and g[control]:
                assert g[field] >= 0. and g['exported_'+field] >= 0.
                if g['accepted']: assert max(g[field], g['exported_'+field]) <= 1.
            else: assert g[field] is g['exported_'+field] is None
        if g['error_control'] and g['error_estimate_available']:
            assert [t['role'] for t in g['trials']] == ['coarse', 'fine_first', 'fine_second']
            coarse, first, second = g['trials']
            assert coarse['start_time_s'] == first['start_time_s'] == g['start_time_s']
            assert coarse['attempted_time_s'] == second['attempted_time_s'] == g['attempted_time_s']
            assert first['attempted_time_s'] == second['start_time_s']
            assert all(t['converged'] for t in g['trials'])
        else:
            assert g['polarization_error_ratio'] is g['electrical_error_ratio'] is None


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('path', ['fixed', 'classical', 'lk', 'lk_centered', 'nls'])
def test_diagnostics_preserve_all_fields_schedule_and_controller_verdicts(path, axis):
    plain = make_case(path, axis); traced = make_case(path, axis)
    assert plain.get_transient_attempt_history() == traced.get_transient_attempt_history() == []
    traced.set_nonlinear_history_enabled(True)
    expected, actual = plain.solve_transient(), traced.solve_transient()
    assert plain.get_transient_attempt_history() == [] and len(expected) == len(actual)
    for left, right in zip(expected, actual):
        assert left.keys() == right.keys()
        for key in left:
            if isinstance(left[key], np.ndarray): np.testing.assert_array_equal(left[key], right[key], err_msg=key)
            else: assert left[key] == right[key], key
    groups = traced.get_transient_attempt_history()
    assert groups and all(s['valid'] for s in actual)
    assert_timeline(actual, groups)
    rejected = [g for g in groups if not g['accepted']]
    expected_solver = 'lk_material_field_1d' if path == 'lk' else 'newton'
    assert all(t['solver'] == expected_solver for g in groups for t in g['trials'])
    if path in ('lk', 'lk_centered'):
        assert rejected and all(g['stopping_reason'] == 'retry' for g in rejected)
        assert all(g['status'] == 'accuracy_limit' for g in rejected)
    for before, after in zip(groups, groups[1:]):
        if before['stopping_reason'] == 'retry':
            assert after['start_time_s'] == before['start_time_s']
            assert after['retry_index'] == before['retry_index']+1
            assert after['dt_s'] == pytest.approx(before['dt_s']/2, rel=1e-14)
        else: assert after['retry_index'] == 0


def test_first_residual_of_every_fixed_step_matches_independent_diffusion_equations():
    sim, _ = slab(); sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); groups = sim.get_transient_attempt_history()
    for previous, group in zip(history, groups):
        trial, = group['trials']
        # At the Newton base state, n=n_previous makes the BE storage term
        # zero. The actual cell-integrated SG equation is pure diffusion.
        nn = previous['n']; flux = .1*.025852/1e-6*(2*nn[1:-1]-nn[:-2]-nn[2:])
        assert trial['raw_n_l2'][0] == pytest.approx(np.linalg.norm(flux), rel=2e-13)
        assert trial['raw_phi_l2'][0] == 0.  # Explicit frozen-potential benchmark.
        assert trial['raw_n_l2'][0] > 1e18
        assert trial['relative_block_max'][0] == pytest.approx(1.)
        assert trial['equilibrated_linf'][-1] < 1e-10


@pytest.mark.parametrize('stop', ['max_reject', 'min_dt', 'solver_failure'])
def test_terminal_rejection_keeps_trials_but_no_committed_dwell(stop):
    sim = driven_film(0, model=0, fe=True, layered=True, dt=1e-7)[0]
    controlled(sim, atol=1e-10, max_reject=0 if stop != 'min_dt' else 20,
               min_dt=2.5e-10 if stop == 'min_dt' else 1e-15)
    if stop == 'solver_failure': sim.set_gummel_max_iter(0)
    sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); group, = sim.get_transient_attempt_history()
    assert not group['accepted'] and not history[-1]['valid']
    assert group['status'] == ('solver_failure' if stop == 'solver_failure' else 'accuracy_limit')
    assert group['stopping_reason'] == ('max_reject' if stop == 'solver_failure' else stop)
    assert len(group['trials']) == (1 if stop == 'solver_failure' else 3)
    assert_timeline(history, [group])
    if stop == 'solver_failure':
        assert not group['error_estimate_available']
        assert all(group['trials'][0][key].size == 0 for key in trace_columns(group['trials'][0]))
    for key in ('phi', 'n', 'p', 'P'):
        np.testing.assert_array_equal(history[0][key], history[-1][key])


@pytest.mark.parametrize('budget', [0, 1])
def test_failed_fixed_newton_invocation_retains_actual_samples(budget):
    sim, _ = slab(); sim.set_gummel_max_iter(budget); sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); group, = sim.get_transient_attempt_history()
    assert group['status'] == group['stopping_reason'] == 'solver_failure'
    assert not group['error_control'] and not group['accepted']
    trial, = group['trials']; assert not trial['converged'] and trial['solver_called']
    assert len(trial['raw_n_l2']) == budget
    assert_timeline(history, [group])


def test_unrepresentable_midpoint_records_a_proposal_without_fabricated_newton_call():
    tiny = np.nextafter(0., 1.)
    sim, _ = dielectric(voltage=0., alpha=1e8, dt=tiny, final=tiny)
    controlled(sim, min_dt=tiny, max_reject=0); sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); group, = sim.get_transient_attempt_history()
    assert group['status'] == group['stopping_reason'] == 'time_resolution'
    assert group['trials'] == [] and not group['error_estimate_available']
    assert_timeline(history, [group])


@pytest.mark.parametrize('case', ['zero_delta', 'quantized_delta'])
def test_unrepresentable_estimates_keep_three_successful_discarded_trials(case):
    voltage, alpha, atol = ((1e-280, 1e30, 1e-306) if case == 'zero_delta' else (1e-320, 1e8, 1e-320))
    sim, _ = dielectric(voltage=voltage, alpha=alpha, dt=1e-9, final=1e-9)
    controlled(sim, atol=atol); sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); group, = sim.get_transient_attempt_history()
    assert group['status'] == group['stopping_reason'] == 'unrepresentable_estimate'
    assert len(group['trials']) == 3 and all(t['converged'] for t in group['trials'])
    assert not group['error_estimate_available']
    assert_timeline(history, [group])


def test_arrays_are_owned_and_history_resets_on_disabled_zero_duration_and_invalid_runs():
    sim, _ = slab(); sim.set_nonlinear_history_enabled(True); sim.solve_transient()
    first = sim.get_transient_attempt_history(); original = first[0]['trials'][0]['raw_n_l2'].copy()
    first[0]['trials'][0]['raw_n_l2'][:] = -99.
    second = sim.get_transient_attempt_history()
    np.testing.assert_array_equal(second[0]['trials'][0]['raw_n_l2'], original)
    assert not np.shares_memory(second[0]['trials'][0]['raw_n_l2'], second[0]['trials'][0]['raw_p_l2'])
    sim.set_transient_t_final(0.); sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
    sim.set_transient_t_final(1e-10); sim.solve_transient()
    assert len(sim.get_transient_attempt_history()) == 1
    sim.set_quantum_enabled(True)
    with pytest.raises(ValueError): sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
    sim.set_quantum_enabled(False); sim.set_nonlinear_history_enabled(False); sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
    np.testing.assert_array_equal(second[0]['trials'][0]['raw_n_l2'], original)


def test_exhausted_solver_retries_preserve_all_proposals_and_empty_zero_budget_samples():
    sim = central_cell(1e19, False, 0, True)[0]
    sim.set_transient_electrical_error_control(True, max_reject=2)
    sim.set_gummel_max_iter(0); sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient(); groups = sim.get_transient_attempt_history()
    assert [g['retry_index'] for g in groups] == [0, 1, 2]
    assert [g['stopping_reason'] for g in groups] == ['retry', 'retry', 'max_reject']
    assert [g['dt_s'] for g in groups] == [1e-10, 5e-11, 2.5e-11]
    assert all(g['status'] == 'solver_failure' and g['start_time_s'] == 0. for g in groups)
    assert all(len(g['trials']) == 1 and g['trials'][0]['raw_n_l2'].size == 0 for g in groups)
    assert_timeline(history, groups)


def test_high_level_access_returns_native_owned_trace():
    from tcad.simulator import Simulator
    sim = Simulator.__new__(Simulator); sim._sim = slab()[0]
    sim.set_nonlinear_history_enabled(True); sim._sim.solve_transient()
    assert sim.get_transient_attempt_history()[0]['trials'][0]['solver_called']
