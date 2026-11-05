"""Cumulative energy comes from the contiguous accepted path, never trials."""
from copy import deepcopy
from dataclasses import replace
from math import fsum
import numpy as np
import pytest

from test_adaptive_three_temperature import closed, OPTIONS
from test_three_temperature import case, BUDGET
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory

RUN = dict(OPTIONS, initial_step_s=1e-13, maximum_step_s=1e-13)


@pytest.fixture(scope='module')
def path():
    model, initial = closed(); device = DeviceThreeTemperature(model, initial)
    result = device.run_transient([0., 7.3e-14], **RUN)
    return model, result


def reaudit(path, **kw):
    model, r = path
    return audit_three_temperature_trajectory(model, r['initial_state'], r['interval_reports'],
        final_state=r['final_state'], **dict(BUDGET, **kw))


def test_closed_finite_capacity_path_has_endpoint_closure_and_excludes_real_rejections(path):
    model, r = path; a = r['trajectory_energy_audit']
    assert r['rejected_trials'] > 0 and r['native_advance_calls'] > r['accepted_native_substeps']
    assert a['valid'] and a == reaudit(path)
    assert a['independently_reaudited_substeps'] == r['accepted_native_substeps']
    assert a['cumulative_energy_atol_J'] == r['accepted_native_substeps']*BUDGET['energy_atol_J']
    assert a['cumulative_budget_policy'] == 'sum_of_per_substep_budgets'
    assert not a['discarded_trials_included'] and not a['complete_device_energy']
    assert not a['physical_validated'] and not a['experimental_validated'] and not a['global_temporal_error_bound']
    assert a['source_work_J'] == 0 and all(v == 0 for v in a['outward_energy_J'].values())
    assert a['energy_increments_J']['electrons'] < 0 < a['energy_increments_J']['lattice']
    assert a['carrier_exchange_to_lattice_J']['electrons'] > 0
    assert abs(fsum(a['endpoint_energy_increments_J'].values())) <= a['cumulative_energy_atol_J']
    assert max(map(abs, a['storage_telescoping_error_J'].values())) < 1e-27


def test_contact_path_accounts_for_all_material_ports_and_both_electrical_work_terms():
    model, initial = case(contacts=True, voltage=.002, count=2)
    d = DeviceThreeTemperature(model, initial)
    r = d.run_transient([initial.time_s+1e-17], **RUN)
    a = r['trajectory_energy_audit']
    assert a['valid'] and a['terminal_charge_C'].keys() == model.bc.keys()
    assert a['source_work_J'] != 0
    assert all(a['outward_energy_J'][s] != 0 for s in ('electrons','holes','lattice'))
    assert abs(a['endpoint_energy_residual_J']) <= a['cumulative_energy_atol_J']
    assert abs(a['electrical_work_residual_J']) <= a['cumulative_energy_atol_J']


def test_forged_attached_audit_and_poisoned_discarded_trials_are_not_used(path):
    model, r = path; intervals = deepcopy(r['interval_reports'])
    for interval in intervals:
        interval['attempts'] = ({'accepted':False, 'reports':({'source_work_J':1e100},)},)
        for report in interval['substep_reports']:
            report['independent_audit'] = {'valid':True, 'independently_reconstructed_ledger':{'source_work_J':1e100}}
    changed = dict(r, interval_reports=intervals)
    assert reaudit((model, changed)) == reaudit(path)


@pytest.mark.parametrize('corruption', ['duplicate', 'reorder', 'gap', 'final', 'density', 'trap', 'duration', 'halfcount'])
def test_path_coverage_and_five_field_continuity_cannot_be_forged(path, corruption):
    model, r = path; intervals = list(deepcopy(r['interval_reports'])); final = r['final_state']
    if corruption == 'duplicate':intervals.insert(1, intervals[0])
    elif corruption == 'reorder':intervals.reverse()
    elif corruption == 'gap':intervals.pop(0)
    elif corruption == 'final':final = r['initial_state']
    elif corruption == 'density':
        s = intervals[0]['initial_state']; intervals[0]['initial_state'] = replace(s, n_m3=s.n_m3*1.01)
    elif corruption == 'trap':
        s = intervals[0]['initial_state']; intervals[0]['initial_state'] = replace(s, trap_fraction=s.trap_fraction+.01)
    elif corruption == 'duration':intervals[0]['accepted_interval_s'] *= 2
    else:intervals[0]['substep_states'] = intervals[0]['substep_states'][:1]
    with pytest.raises(ValueError):
        audit_three_temperature_trajectory(model, r['initial_state'], intervals, final_state=final, **BUDGET)


def test_modified_accepted_report_is_rejected_even_with_forged_valid_summary(path):
    model, r = path; intervals = deepcopy(r['interval_reports'])
    report = intervals[0]['substep_reports'][0]
    report['source_work_J'] += 1e-20; report['independent_audit']['valid'] = True
    with pytest.raises(ValueError, match='independent accepted substep audit failed'):
        reaudit((model, dict(r, interval_reports=intervals)))


@pytest.mark.parametrize('value', [0., -1., np.inf, np.nan, True, [1e-27], 1j])
def test_explicit_cumulative_budget_must_be_positive_finite_scalar(path, value):
    with pytest.raises(ValueError):reaudit(path, cumulative_energy_atol_J=value)


def test_explicit_tighter_budget_and_empty_path_are_reported_without_relaxation(path):
    a = reaudit(path, cumulative_energy_atol_J=1e-27)
    assert a['valid'] and a['cumulative_budget_policy'] == 'explicit'
    a = reaudit(path, cumulative_energy_atol_J=1e-40)
    assert not a['valid'] and a['cumulative_energy_atol_J'] == 1e-40
    model, initial = closed(); d = DeviceThreeTemperature(model, initial)
    r = d.run_transient([initial.time_s], **RUN); a = r['trajectory_energy_audit']
    assert a['valid'] and a['accepted_native_substeps'] == 0
    assert a['energy_residual_J'] == a['endpoint_energy_residual_J'] == 0.
    assert all(v == 0 for v in a['energy_increments_J'].values())


def test_overflowed_cumulative_budget_is_rejected(path):
    with pytest.raises(ValueError, match='cumulative energy budget out of range'):
        reaudit(path, energy_atol_J=1e308)


@pytest.mark.parametrize('failure', ['reject', 'allocation'])
def test_final_cumulative_audit_failure_rolls_back_whole_native_session(monkeypatch, failure):
    model, initial = closed(); d = DeviceThreeTemperature(model, initial)
    before = deepcopy(d.native_state()); owned = d.state
    def fail(*a, **k):
        if failure == 'allocation':raise MemoryError('ledger allocation')
        return {'valid':False}
    monkeypatch.setattr('tcad.postprocess.three_temperature_trajectory.audit_three_temperature_trajectory', fail)
    with pytest.raises(ThreeTemperatureTransientError) as error:
        d.run_transient([0., 1e-15], **RUN)
    assert d.state is owned and d.native_state() == before
    assert len(error.value.diagnostics['interval_reports']) == 1
    assert not error.value.diagnostics['published']
