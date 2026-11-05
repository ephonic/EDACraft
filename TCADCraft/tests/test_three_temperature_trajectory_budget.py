"""Public whole-path budgets reject atomically and retain useful final ledgers."""
from copy import deepcopy
import numpy as np
import pytest

from test_adaptive_three_temperature import closed
from test_device_three_temperature import assert_owned
from test_structured_three_temperature import structured_case
from test_three_temperature import BUDGET
from test_transient_three_temperature import RUN, FIELDS
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory


@pytest.fixture(scope='module')
def reference():
    model, initial = closed()
    result = DeviceThreeTemperature(model, initial).run_transient([0., 7.3e-14], **RUN)
    return model, initial, result


@pytest.mark.parametrize('budget', [None, 1e-27, 1e-20])
def test_explicit_budget_changes_only_final_gate_and_preserves_accepted_path(reference, budget):
    model, initial, expected = reference
    device = DeviceThreeTemperature(model, initial)
    actual = device.run_transient(expected['output_times_s'], cumulative_energy_atol_J=budget, **RUN)
    a = actual['trajectory_energy_audit']
    assert a == audit_three_temperature_trajectory(model, initial, actual['interval_reports'],
        final_state=actual['final_state'], cumulative_energy_atol_J=budget, **BUDGET)
    assert a['valid'] and a['per_substep_energy_atol_J'] == BUDGET['energy_atol_J']
    assert a['cumulative_budget_policy'] == ('explicit' if budget is not None else 'sum_of_per_substep_budgets')
    if budget is not None:assert a['cumulative_energy_atol_J'] == budget
    for key in ('native_advance_calls', 'accepted_intervals', 'rejected_trials'):
        assert actual[key] == expected[key]
    for left, right in zip(actual['output_states'], expected['output_states']):
        assert left.time_s == right.time_s
        for f in FIELDS:np.testing.assert_array_equal(getattr(left, f), getattr(right, f))
    numerical = {k:v for k,v in a.items() if k not in ('cumulative_budget_policy','cumulative_energy_atol_J')}
    assert numerical == {k:v for k,v in expected['trajectory_energy_audit'].items() if k not in ('cumulative_budget_policy','cumulative_energy_atol_J')}
    assert_owned(device, actual['final_state'])


def test_tight_cumulative_budget_rejects_completed_path_and_retry_publishes_once(reference):
    model, initial, expected = reference; device = DeviceThreeTemperature(model, initial)
    owned = device.state; before = deepcopy(device.native_state())
    with pytest.raises(ThreeTemperatureTransientError) as caught:
        device.run_transient(expected['output_times_s'], cumulative_energy_atol_J=1e-40, **RUN)
    d = caught.value.diagnostics; a = d['trajectory_energy_audit']
    assert d['failure_phase'] == 'cumulative_energy_audit' and not d['published']
    assert not a['valid'] and a['cumulative_energy_atol_J'] == 1e-40
    assert a['cumulative_budget_policy'] == 'explicit'
    assert a['per_substep_energy_atol_J'] == BUDGET['energy_atol_J']
    assert a == audit_three_temperature_trajectory(model, initial, d['interval_reports'],
        final_state=d['output_states'][-1], cumulative_energy_atol_J=1e-40, **BUDGET)
    assert d['completed_interval_native_calls'] == expected['native_advance_calls']
    assert d['output_states'][-1].time_s == expected['final_state'].time_s
    assert a['independently_reaudited_substeps'] == expected['accepted_native_substeps']
    assert not a['discarded_trials_included'] and expected['rejected_trials'] > 0
    assert device.state is owned and device.native_state() == before
    assert_owned(device, owned)
    result = device.run_transient(expected['output_times_s'], cumulative_energy_atol_J=1e-27, **RUN)
    assert result['valid'] and result['final_state'] is device.state
    assert_owned(device, result['final_state'])


INVALID = [0., -1e-27, np.nan, np.inf, -np.inf, True, '1e-27', [1e-27], 1j,
           np.longdouble('1e4000')]


@pytest.mark.parametrize('value', INVALID)
def test_invalid_device_budget_rejected_before_worker_or_trials(monkeypatch, value):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    owned = device.state; before = deepcopy(device.native_state())
    def forbidden(*a, **k):raise AssertionError('worker constructed for invalid budget')
    monkeypatch.setattr(DeviceThreeTemperature, '__init__', forbidden)
    with pytest.raises(ValueError, match='cumulative energy budget'):
        device.run_transient([1e-15], cumulative_energy_atol_J=value, **RUN)
    assert device.state is owned and device.native_state() == before


@pytest.mark.parametrize('value', INVALID)
def test_invalid_Simulator_budget_rejected_before_migration(monkeypatch, value):
    source, initial, material = structured_case((3,1,1), contacts=True)
    before = deepcopy(source._sim.structured_three_temperature_seed())
    def forbidden(*a, **k):raise AssertionError('migration attempted for invalid budget')
    monkeypatch.setattr(source, 'to_three_temperature', forbidden)
    with pytest.raises(ValueError, match='cumulative energy budget'):
        source.run_three_temperature(initial, [initial.time_s+1e-15],
            **dict(material, **RUN, cumulative_energy_atol_J=value))
    assert source._sim.structured_three_temperature_seed() == before and source.results is None


def test_budget_is_detached_before_mutable_caller_scalar_changes_in_report_hook():
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    budget = np.array(1e-27); calls = []
    def hook(report):
        calls.append(1); budget[...] = 0.
    device._decorate_report = hook
    r = device.run_transient([1e-15], cumulative_energy_atol_J=budget, **RUN)
    assert calls and budget == 0.
    assert r['trajectory_energy_audit']['cumulative_energy_atol_J'] == 1e-27
    assert_owned(device, r['final_state'])


def test_initial_only_tiny_positive_explicit_budget_needs_no_native_advance(monkeypatch):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    def forbidden(*a, **k):raise AssertionError('empty trajectory advanced')
    monkeypatch.setattr(DeviceThreeTemperature, 'advance_adaptive', forbidden)
    budget = np.nextafter(0., 1.)
    r = device.run_transient([initial.time_s], cumulative_energy_atol_J=budget, **RUN)
    a = r['trajectory_energy_audit']
    assert a['valid'] and a['cumulative_budget_policy'] == 'explicit'
    assert a['cumulative_energy_atol_J'] == budget and a['endpoint_energy_residual_J'] == 0.
    assert r['native_advance_calls'] == a['accepted_native_substeps'] == 0


@pytest.mark.parametrize('failure', ['integration', 'audit_allocation', 'prepublication', 'result_allocation'])
def test_failure_phase_and_available_final_ledger_are_retained_without_publication(monkeypatch, failure):
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    owned = device.state; before = deepcopy(device.native_state())
    expected_phase = dict(integration='integration', audit_allocation='cumulative_energy_audit',
        prepublication='prepublication_checks', result_allocation='result_construction')[failure]
    def fail(*a, **k):raise MemoryError(failure)
    if failure == 'integration':monkeypatch.setattr(DeviceThreeTemperature, 'advance_adaptive', fail)
    elif failure == 'audit_allocation':
        monkeypatch.setattr('tcad.postprocess.three_temperature_trajectory.audit_three_temperature_trajectory', fail)
    elif failure == 'prepublication':
        original = device._check_owned_state; calls = []
        def check():
            calls.append(1)
            if len(calls) == 2:fail()
            return original()
        monkeypatch.setattr(device, '_check_owned_state', check)
    else:
        def allocate(*a, **k):
            if k.get('scope') == 'atomic_native_three_temperature_trajectory':fail()
            return dict(*a, **k)
        monkeypatch.setattr('tcad.solver.transient_three_temperature.dict', allocate, raising=False)
    with pytest.raises(ThreeTemperatureTransientError) as caught:
        device.run_transient([0., 1e-15], cumulative_energy_atol_J=1e-27, **RUN)
    d = caught.value.diagnostics
    assert d['failure_phase'] == expected_phase and d['failure_type'] == 'MemoryError'
    assert not d['published'] and device.state is owned and device.native_state() == before
    if failure in ('prepublication','result_allocation'):
        assert d['trajectory_energy_audit']['valid']
        assert d['trajectory_energy_audit']['cumulative_energy_atol_J'] == 1e-27
    else:assert d['trajectory_energy_audit'] is None


@pytest.mark.parametrize('budget, accepted', [(1e-27, True), (1e-40, False)])
def test_Simulator_passes_budget_and_preserves_source_on_success_or_final_rejection(budget, accepted):
    source, initial, material = structured_case((3,1,1), contacts=True)
    before = deepcopy(source._sim.structured_three_temperature_seed())
    configuration = repr(source.configuration_snapshot())
    source.results = {'sentinel': np.array([9.])}
    kw = dict(material, **RUN, cumulative_energy_atol_J=budget)
    times = [initial.time_s, initial.time_s+1e-15]
    if accepted:
        r = source.run_three_temperature(initial, times, **kw)
        a = r['trajectory_energy_audit']
        assert r['migration_report']['audit']['valid'] and a['valid']
        assert_owned(r['device'], r['final_state'])
        # The returned device can continue with a different whole-path gate.
        resumed = r['device'].run_transient([r['final_state'].time_s+1e-15],
            cumulative_energy_atol_J=1e-26, **RUN)
        assert resumed['initial_state'] is r['final_state']
        assert resumed['trajectory_energy_audit']['cumulative_energy_atol_J'] == 1e-26
    else:
        with pytest.raises(ThreeTemperatureTransientError) as caught:
            source.run_three_temperature(initial, times, **kw)
        d = caught.value.diagnostics; a = d['trajectory_energy_audit']
        assert d['failure_phase'] == 'cumulative_energy_audit' and not d['published'] and not a['valid']
        assert d['output_states'][-1].time_s == times[-1]
    assert a['cumulative_energy_atol_J'] == budget and a['cumulative_budget_policy'] == 'explicit'
    assert a['per_substep_energy_atol_J'] == BUDGET['energy_atol_J']
    assert source._sim.structured_three_temperature_seed() == before
    assert repr(source.configuration_snapshot()) == configuration
    np.testing.assert_array_equal(source.results['sentinel'], [9.])
    assert not source._configuration_state_advanced
