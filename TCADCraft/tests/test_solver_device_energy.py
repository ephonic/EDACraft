"""Use actual trajectories and deliberately inconsistent state/port reports."""
from copy import deepcopy

import pytest

from tcad.postprocess import audit_solver_device_energy, audit_complete_device_energy, solver_energy_history
from tcad.postprocess.device_energy import SOLVER_COMPONENTS

BUDGET = dict(charge_atol_C=2e-29, particle_atol=1e-10, energy_atol_J=1e-28)


@pytest.mark.parametrize('kind', ['closed', 'electrothermal', 'nonconvex', 'mimetic', 'thermionic'])
def test_independent_energy_audit_of_two_actual_steps(kind):
    moment = {}
    budget = BUDGET
    if kind == 'closed':
        from test_cut_cell_transport_energy import fixture
        model, state = fixture(quantum=True, traps=True, bath=True)
        budget = dict(charge_atol_C=1e-29, particle_atol=1e-9, energy_atol_J=2e-28)
    elif kind == 'thermionic':
        from test_thermionic_electrothermal import fixture, BUDGET as budget, MOMENT as moment
        model, state = fixture(contacts=True, traps=True, quantum=True)
    else:
        from test_electrothermal_cut_cell import fixture
        model, state = fixture(open_contacts=True, quantum=True, traps=True, nonconvex=kind == 'nonconvex')
        if kind == 'mimetic':
            from test_mimetic_electrothermal import model_from
            model = model_from(model)
    for _ in range(2):
        old = state
        state, report = model.step(old, 2e-12, **budget)
        result = audit_solver_device_energy(model, old, state, report, **budget, **moment)
        assert result['valid'] and result['modeled_energy_balance_validated']
        assert result['snapshots_valid'] and result['independent_audit']['valid']
        assert not result['complete_device_energy'] and not result['physical_validated']
        assert result['backend'] == 'python_cut_cell'


@pytest.fixture(scope='module')
def actual_step():
    from test_electrothermal_cut_cell import fixture
    model, old = fixture(open_contacts=True, quantum=True, traps=True)
    new, report = model.step(old, 2e-12, **BUDGET)
    return model, old, new, report


@pytest.mark.parametrize('field', ['source_work_J', 'outward_heat_J', 'outward_carrier_energy_J'])
def test_unchanged_storage_cannot_hide_corrupt_boundary_totals(actual_step, field):
    model, old, new, report = actual_step
    bad = deepcopy(report)
    bad[field] += 1e-22
    # A storage-only ledger is incapable of detecting this alteration.
    assert audit_complete_device_energy(solver_energy_history(bad), components=SOLVER_COMPONENTS,
                                        atol_J=BUDGET['energy_atol_J'])['valid']
    result = audit_solver_device_energy(model, old, new, bad, **BUDGET)
    assert not result['valid'] and not result['independent_audit']['valid']


@pytest.mark.parametrize('field', ['integrated_heat_flux_W', 'integrated_carrier_energy_flux_W',
                                   'integrated_electron_particle_flux_s', 'trap_electron_capture_rate_s'])
def test_face_flux_and_capture_tampering_rejected(actual_step, field):
    model, old, new, report = actual_step
    bad = deepcopy(report)
    bad[field] *= 1.1
    assert not audit_solver_device_energy(model, old, new, bad, **BUDGET)['valid']


def test_shifted_before_and_after_snapshots_require_independent_state_check(actual_step):
    model, old, new, report = actual_step
    bad = deepcopy(report)
    for key in ('energy_before_J', 'energy_after_J'):
        bad[key]['carrier_J'] += 1e-22
    result = audit_solver_device_energy(model, old, new, bad, **BUDGET)
    assert result['storage_audit']['valid'] and result['independent_audit']['valid']
    assert not result['valid'] and not result['snapshots_valid']


def test_matched_snapshot_and_increment_forgery_cannot_certify_balance(actual_step):
    model, old, new, report = actual_step
    bad = deepcopy(report)
    bad['energy_after_J']['quantum_J'] += 1e-22
    bad['energy_increments_J']['quantum_J'] += 1e-22
    result = audit_solver_device_energy(model, old, new, bad, **BUDGET)
    assert result['storage_audit']['valid']
    assert not result['valid'] and not result['independent_audit']['valid']


def test_positive_report_flag_cannot_override_bad_state(actual_step):
    model, old, new, report = actual_step
    changed = deepcopy(new)
    changed.temperature_K[:] *= 1.001
    assert report['valid']
    assert not audit_solver_device_energy(model, old, changed, report, **BUDGET)['valid']


def test_thermionic_requires_explicit_moment_budgets_and_checks_them():
    from test_thermionic_electrothermal import fixture, BUDGET as budget, MOMENT as moment
    model, old = fixture(contacts=True, traps=True)
    new, report = model.step(old, 2e-12, **budget)
    with pytest.raises(ValueError):
        audit_solver_device_energy(model, old, new, report, **budget)
    bad = deepcopy(report)
    bad['thermionic_interfaces']['electrons']['moments']['particle_flux_s'] *= 1.1
    assert not audit_solver_device_energy(model, old, new, bad, **budget, **moment)['valid']


def test_budget_and_model_contracts(actual_step):
    model, old, new, report = actual_step
    with pytest.raises(ValueError):
        audit_solver_device_energy(object(), old, new, report, **BUDGET)
    for value in (True, '1e-28', 0., -1.):
        with pytest.raises(ValueError):
            audit_solver_device_energy(model, old, new, report, **{**BUDGET, 'energy_atol_J': value})
