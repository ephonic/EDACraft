"""Saved paths keep real clocks and independently recompute all mechanisms."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from test_three_temperature import case, BUDGET
from test_temperature_dependent_bands import band_case
from test_varshni_temperature_bands import configure
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.three_temperature_saved_path import audit_three_temperature_saved_path


@pytest.fixture(scope='module', params=['closed', 'contact', 'combined'])
def path(request):
    if request.param == 'combined':
        model, initial = band_case(complex=True, contacts=True, count=2)
        configure(model)
    else:
        model, initial = case(count=1 if request.param == 'closed' else 2,
            uniform=request.param == 'closed', contacts=request.param == 'contact', voltage=.002)
    d = DeviceThreeTemperature(model, initial); steps = []
    for dt in (2e-16, 5e-16, 9e-16):
        old = d.state; new, report = d.advance(dt, **BUDGET)
        steps.append((old, new, report))
    return model, initial, steps, d.state


def audit(path, steps=None, **kw):
    m, initial, saved, final = path
    return audit_three_temperature_saved_path(m, initial, saved if steps is None else steps,
        final_state=final, **dict(BUDGET, **kw))


def test_nonuniform_accepted_path_has_independent_endpoint_and_every_reservoir(path, monkeypatch):
    m, initial, steps, final = path
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a, **k):raise AssertionError('native operator called by saved-path audit')
    for module in (public, native):
        for name in dir(module):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(module, name)):
                monkeypatch.setattr(module, name, deny)
    result = audit(path)
    assert result['valid'] and result['independently_reaudited_steps'] == 3
    assert result['final_time_s'] == final.time_s and result['initial_time_s'] == initial.time_s
    assert result['cumulative_energy_atol_J'] == 3*BUDGET['energy_atol_J']
    assert max(map(abs, result['storage_telescoping_error_J'].values())) < 1e-27
    assert not result['complete_device_energy'] and not result['global_temporal_error_bound']
    if m.auger_events is not None:
        assert {'electrons', 'holes', 'lattice', 'traps', 'photons', 'auger_internal'} == set(result['reservoir_energy_residuals_J'])
        assert result['absorbed_pair_energy_J'] > 0
        for key in ('band_work_from_lattice_J', 'trap_carrier_energy_removed_J',
                    'radiative_carrier_energy_removed_J', 'auger_carrier_energy_added_J'):
            assert any(v != 0 for v in result['mechanism_energy_terms_J'][key].values())


@pytest.mark.parametrize('damage', ['gap', 'reorder', 'duplicate', 'initial_density', 'final_temperature', 'clock'])
def test_actual_state_and_clock_continuity_is_required(path, damage):
    m, initial, original, final = path; steps = list(original)
    if damage == 'gap':steps.pop(1)
    elif damage == 'reorder':steps.reverse()
    elif damage == 'duplicate':steps.insert(1, steps[0])
    elif damage == 'initial_density':
        old, new, r = steps[1]; steps[1] = (replace(old, n_m3=old.n_m3*1.001), new, r)
    elif damage == 'final_temperature':
        old, new, r = steps[-1]; steps[-1] = (old, replace(new, temperature_K=new.temperature_K+.001), r)
    else:
        old, new, r = steps[0]; steps[0] = (old, replace(new, time_s=old.time_s), r)
    with pytest.raises(ValueError):audit(path, steps)


def test_attached_summary_cannot_replace_recomputed_physics(path):
    steps = deepcopy(path[2])
    for old, new, r in steps:r['independent_audit'] = {'valid': True, 'energy_residual_J': 1e100}
    assert audit(path, steps) == audit(path)
    steps[0][2]['source_work_J'] += 1e-18
    with pytest.raises(ValueError, match='independent saved step audit failed'):audit(path, steps)


@pytest.mark.parametrize('value', [0., -1., np.nan, np.inf, True, [1e-27]])
def test_cumulative_budget_is_an_explicit_positive_scalar(path, value):
    with pytest.raises(ValueError):audit(path, cumulative_energy_atol_J=value)


def test_stricter_cumulative_budget_rejects_without_modifying_local_budgets(path):
    r = audit(path, cumulative_energy_atol_J=1e-45)
    assert not r['valid'] and r['cumulative_energy_atol_J'] == 1e-45
    assert r['per_step_energy_atol_J'] == BUDGET['energy_atol_J']


def test_empty_saved_path_requires_the_same_initial_and_final_state(path):
    m, initial, _, final = path
    r = audit_three_temperature_saved_path(m, initial, [], final_state=initial, **BUDGET)
    assert r['valid'] and r['independently_reaudited_steps'] == 0
    assert r['endpoint_energy_residual_J'] == 0
    with pytest.raises(ValueError, match='final state mismatch'):
        audit_three_temperature_saved_path(m, initial, [], final_state=final, **BUDGET)
