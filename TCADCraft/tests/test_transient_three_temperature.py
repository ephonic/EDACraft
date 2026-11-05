"""Exact output clocks, whole-run rollback and the public Simulator entry."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import expm
from test_adaptive_three_temperature import closed, OPTIONS
from test_three_temperature import BUDGET, case
from test_device_three_temperature import assert_owned
from test_structured_three_temperature import structured_case
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError

RUN = dict(OPTIONS, initial_step_s=1e-13, maximum_step_s=1e-13)
FIELDS = ('n_m3', 'p_m3', 'temperature_K', 'electron_temperature_K', 'hole_temperature_K')


def test_exact_output_trajectory_matches_independent_finite_capacity_reservoir_solution():
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    times = np.array([0., 7.3e-14, 2.17e-13, 6e-13])
    result = device.run_transient(times, **RUN)
    k = 1.5*1e20*1.380649e-23/.03
    A = np.array([[-1/3e-13, 0, 1/3e-13], [0, -1/5e-13, 1/5e-13],
                  [k/3e-13, k/5e-13, -k/3e-13-k/5e-13]])
    assert result['valid'] and result['whole_trajectory_atomic'] and result['exact_output_clocks']
    assert not result['global_temporal_error_bound'] and not result['complete_device_energy']
    np.testing.assert_array_equal([s.time_s for s in result['output_states']], times)
    for s in result['output_states']:
        exact = expm(A*s.time_s)@np.array([540., 420., 300.])
        assert max(abs(np.array([s.electron_temperature_K[0], s.hole_temperature_K[0], s.temperature_K[0]])-exact)) < .8
    reports = result['interval_reports']
    assert result['native_advance_calls'] == sum(r['native_advance_calls'] for r in reports)
    assert result['accepted_native_substeps'] == 2*len(reports)
    assert result['rejected_trials'] > 0
    before = initial
    for r in reports:
        assert r['initial_state'].time_s == before.time_s
        assert all(a['independent_audit']['valid'] for a in r['substep_reports'])
        before = r['substep_states'][-1]
    assert before is device.state is result['final_state']
    assert_owned(device, device.state)
    times[:] = 0
    assert result['output_times_s'][-1] == 6e-13
    with pytest.raises(ValueError):result['output_times_s'].flags.writeable = True


@pytest.mark.parametrize('failure', ['limit', 'audit', 'metadata', 'newton'])
def test_late_failure_rolls_back_entire_trajectory_and_retains_diagnostic_prefix(monkeypatch, failure):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    before = deepcopy(device.native_state()); kw = dict(RUN)
    times = [0., 1e-15, 2e-15]
    if failure == 'limit':kw['max_intervals'] = 1
    else:
        original = DeviceThreeTemperature.advance_adaptive
        calls = []
        def late(self, *a, **k):
            calls.append(1)
            if len(calls) == 2:
                if failure == 'metadata':raise MemoryError('late report allocation failure')
                if failure == 'newton':k.update(max_nfev=1, max_retries=0)
                else:
                    with monkeypatch.context() as patch:
                        patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',
                                      lambda *a, **k: dict(valid=False, reason='late injected audit rejection'))
                        return original(self, *a, **dict(k, max_retries=0))
            return original(self, *a, **k)
        monkeypatch.setattr(DeviceThreeTemperature, 'advance_adaptive', late)
    with pytest.raises(ThreeTemperatureTransientError) as caught:
        device.run_transient(times, **kw)
    d = caught.value.diagnostics
    assert not d['published'] and len(d['interval_reports']) == 1
    assert [s.time_s for s in d['output_states']] == times[:2]
    assert d['failed_output_time_s'] == times[-1]
    if failure in ('audit', 'newton'):assert len(d['failed_interval_attempts']) == 1
    assert device.native_state() == before and device.state is not d['output_states'][-1]
    assert device.state.time_s == 0.
    monkeypatch.undo()
    result = device.run_transient(times, **RUN)
    assert_owned(device, result['final_state'])


@pytest.mark.parametrize('times', [[], [0., 0.], [1e-15, 0.], [-1e-15], [np.nan], [np.inf], [[0.]], [False], ['0']])
def test_invalid_output_contract_rejected_without_state_change(times):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    before = deepcopy(device.native_state())
    with pytest.raises(ValueError):device.run_transient(times, **RUN)
    assert device.native_state() == before


@pytest.mark.parametrize('kw', [{'initial_step_s':0}, {'initial_step_s':2e-13},
    {'maximum_step_s':True}, {'minimum_step_s':2e-13}, {'temperature_atol_K':0},
    {'density_rtol':False}, {'max_intervals':0}, {'max_intervals':True},
    {'max_retries':1.5}, {'max_nfev':0}, {'energy_atol_J':0}])
def test_invalid_step_contract_rejected_before_trials(kw):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    before = deepcopy(device.native_state())
    with pytest.raises(ValueError):device.run_transient([1e-15], **dict(RUN, **kw))
    assert device.native_state() == before


def test_subminimum_late_output_fails_without_epsilon_skip_or_budget_relaxation():
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    target = np.nextafter(1e-15, np.inf)
    with pytest.raises(ThreeTemperatureTransientError) as caught:
        device.run_transient([1e-15, target], **RUN)
    assert len(caught.value.diagnostics['interval_reports']) == 1
    assert device.state.time_s == 0.


def test_near_minimum_remainder_is_integrated_without_stranding_or_interpolation():
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    result = device.run_transient([1.5e-15], **dict(RUN, initial_step_s=1e-15,
        maximum_step_s=2e-15, minimum_step_s=8e-16))
    assert result['accepted_intervals'] == 1
    assert result['final_state'].time_s == 1.5e-15
    assert result['interval_reports'][0]['accepted_interval_s'] == 1.5e-15


def test_initial_only_and_resume_preserve_longdouble_and_fixed_step_interoperability():
    model, initial = case(count=1, uniform=True)
    n = np.array([np.longdouble('10000000000000000000000001')])
    initial = replace(initial, n_m3=n, p_m3=n)
    device = DeviceThreeTemperature(model, initial)
    empty = device.run_transient([initial.time_s], **RUN)
    assert empty['native_advance_calls'] == empty['accepted_intervals'] == 0
    result = device.run_transient([1e-16, 2e-16], **RUN)
    np.testing.assert_array_equal(result['final_state'].n_m3, n)
    state, _ = device.advance(1e-16, **BUDGET)
    resumed = device.run_transient([state.time_s, 5e-16], **RUN)
    assert resumed['initial_state'] is state
    np.testing.assert_array_equal(resumed['final_state'].p_m3, n)
    assert_owned(device, resumed['final_state'])


@pytest.mark.parametrize('contacts', [False, True])
def test_Simulator_entry_migrates_runs_and_returns_cell_history_without_mutating_nodal_source(contacts):
    source, initial, material = structured_case((3,1,1), contacts=contacts)
    before = deepcopy(source._sim.structured_three_temperature_seed())
    config = repr(source.configuration_snapshot())
    source.results = {'sentinel': np.array([9.])}
    result = source.run_three_temperature(initial, [initial.time_s, initial.time_s+1e-15,
        initial.time_s+2e-15], **dict(material, **RUN))
    assert result['Simulator_three_temperature_entry_integrated']
    assert result['migration_report']['audit']['valid']
    assert len(result['output_states']) == 3 and result['output_states'][0].n_m3.shape == (2,)
    assert not result['legacy_run_three_temperature_replaced']
    assert source._sim.structured_three_temperature_seed() == before
    assert repr(source.configuration_snapshot()) == config
    np.testing.assert_array_equal(source.results['sentinel'], [9.])
    assert not source._configuration_state_advanced
    for r in result['interval_reports']:
        for sub in r['substep_reports']:
            assert sub['device_mesh_mode'] == 'StructuredGrid_primal_cells'
            assert sub['legacy_StructuredGrid_three_temperature_integrated']
    assert_owned(result['device'], result['final_state'])


def test_failed_Simulator_entry_does_not_publish_partial_result():
    source, initial, material = structured_case((3,1,1), contacts=True)
    before = deepcopy(source._sim.structured_three_temperature_seed())
    with pytest.raises(ThreeTemperatureTransientError):
        source.run_three_temperature(initial, [initial.time_s+1e-15, initial.time_s+2e-15],
            **dict(material, **RUN, max_intervals=1))
    assert source._sim.structured_three_temperature_seed() == before and source.results is None
