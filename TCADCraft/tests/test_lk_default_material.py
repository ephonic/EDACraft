"""Default coupled-LK selection must preserve the equations it actually solves."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_energy, audit_transient_lk_error_control
from test_lk_material_field import stack_device
from test_lk_fixed_charge import check_history, widths
from test_fe_series_stack import stack
from test_transient_displacement import film


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('oxide', [.2, .5, 1.])
@pytest.mark.parametrize('cells', [8, 32])
def test_default_series_stack_matches_independent_voltage_partition(axis, oxide, cells):
    times = np.linspace(0., 1e-9, 41)
    top = -8*np.sin(2*np.pi*times/1e-9)
    sim, x, eps, mask = stack_device(times, top, oxide, cells, axis, enabled=None)
    states = sim.solve_transient()
    reference = stack(thickness_oxide=oxide*1e-9).solve_backward_euler(times, -top)
    for i, s in enumerate(states):
        assert s['valid'] and s['lk_coupled'] and s['lk_material_field']
        p = s['P'].reshape(-1, 3)[:, axis]
        np.testing.assert_allclose(p[mask != 0], reference['polarization_C_m2'][i], rtol=2e-11, atol=2e-12)
        np.testing.assert_allclose(s['electrode_charges_C'][1], reference['top_charge_C'][i], rtol=3e-11, atol=1e-25)
        np.testing.assert_allclose(eps*s['E'+'xyz'[axis]]+p,
                                   -s['electrode_charges_C'][1]/1e-13, rtol=1e-11, atol=2e-14)
        if i:
            np.testing.assert_allclose(s['electrode_total_currents_A'][1], reference['top_current_A'][i], rtol=1e-9, atol=2e-15)
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('pattern', ['positive', 'negative', 'neutral'])
@pytest.mark.parametrize('stretched', [False, True])
def test_default_fixed_charge_matches_independent_full_block(axis, pattern, stretched):
    sim, x, eps, mask, area = film(axis, 0, stretched, True)
    c = np.zeros(len(x))
    c[1:-1] = np.linspace(.3, 1.4, len(x)-2)*1e23
    if pattern == 'negative':
        c *= -1
    elif pattern == 'neutral':
        c[1:-1] *= np.array([1., -1., 1., -1., 1., -1., 1.])
        c[-2] -= np.dot(widths(x), c)/widths(x)[-2]
    sim.set_doping(c)
    sim.set_transient_lk_coupled(True)
    check_history(sim, x, eps, mask, area, c, axis)


FALLBACKS = ['mobility', 'generation', 'carrier', 'contact_carrier', 'endpoint_doping',
             'srh', 'fraction', 'edge', 'extra_contact', 'freeze_n', 'freeze_p', 'split', '2d', '3d']


def fallback_device(case, override=None):
    if case in ('2d', '3d'):
        from test_transient_lk_coupled import linear_multidimensional_case
        sim, *_ = linear_multidimensional_case(int(case[0]), False, False)
    else:
        sim, x, *_ = film(0, 0, True, True)
        sim.set_transient_lk_coupled(True)
        z = np.zeros(len(x)); o = np.ones(len(x))
        if case == 'mobility': sim.set_mobility(o*1e-8, z)
        elif case == 'generation': sim.set_optical_generation(o*1e10)
        elif case == 'carrier': sim.set_initial_guess(z, o*1e10, o*1e10)
        elif case == 'contact_carrier': sim.set_electron_bc({0: 1e10})
        elif case == 'endpoint_doping': sim.set_doping(o*1e20)
        elif case == 'srh': sim.set_recombination(o*1e-9, o*1e-9)
        elif case == 'fraction': sim.set_charge_volume_fraction(o*.5)
        elif case == 'edge': sim.set_edge_permittivity(*[o*1e-10 for _ in range(6)])
        elif case == 'extra_contact': sim.set_dirichlet_potential({0: 0., 4: 0., 8: -.01})
        elif case.startswith('freeze_'): getattr(sim, 'set_newton_'+case)(True)
        elif case == 'split': sim.set_transient_lk_coupled(False)
    if override is not None:
        sim.set_transient_lk_material_field(override)
    return sim


@pytest.mark.parametrize('case', FALLBACKS)
def test_ineligible_default_preserves_all_requested_equations(case):
    actual = fallback_device(case).solve_transient()
    expected = fallback_device(case, False).solve_transient()
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        assert not a['lk_material_field'] and a['valid'] == b['valid']
        assert a['electrode_charge_available'] == b['electrode_charge_available']
        for key in ('phi', 'P', 'n', 'p'):
            np.testing.assert_array_equal(a[key], b[key])
        if a['electrode_charge_available']:
            np.testing.assert_array_equal(a['electrode_charges_C'], b['electrode_charges_C'])
    if case in ('2d','3d'):
        forced=fallback_device(case, True).solve_transient()
        assert all(s['valid'] and s['lk_material_field'] for s in forced)
    else:
        with pytest.raises(ValueError, match='material-field LK'):
            fallback_device(case, True).solve_transient()


def test_explicit_override_is_sticky_but_automatic_selection_is_not():
    def device():
        sim, *_ = film(0, 0, True, True)
        sim.set_transient_lk_coupled(True)
        return sim
    sim = device()
    assert sim.solve_transient()[-1]['lk_material_field']
    sim.set_mobility(np.full(9, 1e-8), np.zeros(9))
    assert not sim.solve_transient()[-1]['lk_material_field']
    sim.set_mobility(np.zeros(9), np.zeros(9))
    assert sim.solve_transient()[-1]['lk_material_field']
    for requested in (False, True, False):
        sim.set_transient_lk_material_field(requested)
        states = sim.solve_transient()
        assert all(s['lk_material_field'] == requested for s in states)
        assert audit_transient_lk_energy(states)['valid']


def test_default_failure_rolls_back_and_retry_preserves_automatic_selection():
    sim, *_ = film(0, 0, True, True)
    sim.set_transient_lk_coupled(True)
    sim.set_nonlinear_history_enabled(True)
    sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]['valid'] and failed[-1]['lk_material_field']
    np.testing.assert_array_equal(failed[-1]['P'], failed[0]['P'])
    trial = sim.get_transient_attempt_history()[0]['trials'][0]
    assert trial['solver'] == 'lk_material_field_1d' and not trial['converged']
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, *_ = film(0, 0, True, True)
    fresh.set_transient_lk_coupled(True)
    for a, b in zip(retry, fresh.solve_transient()):
        for key in ('phi', 'P', 'electrode_charges_C'):
            np.testing.assert_array_equal(a[key], b[key])


def test_default_adaptive_coarse_and_halfsteps_match_forced_material_mode():
    def run(override):
        sim, *_ = film(0, 0, True, True)
        sim.set_transient_lk_coupled(True)
        if override: sim.set_transient_lk_material_field(True)
        sim.set_dirichlet_potential({0: 0., 8: -1.})
        sim.set_transient_lk_substepping(True)
        sim.set_transient_lk_error_control(True, rtol=1e-4, atol=1e-9, min_dt=1e-15, max_reject=30)
        sim.set_nonlinear_history_enabled(True)
        return sim.solve_transient(), sim.get_transient_attempt_history()
    states, attempts = run(False)
    expected, expected_attempts = run(True)
    assert len(states) == len(expected) and len(attempts) == len(expected_attempts)
    assert any(not g['accepted'] for g in attempts)
    for a, b in zip(states, expected):
        assert a['lk_material_field'] and a['valid']
        for key in ('phi', 'P', 'time_s', 'electrode_charges_C'):
            np.testing.assert_array_equal(a[key], b[key])
    assert audit_transient_lk_energy(states)['valid']
    assert audit_transient_lk_error_control(states)['valid']
    changed = deepcopy(states)
    changed[-1]['lk_material_field'] = False
    with pytest.raises(ValueError): audit_transient_lk_energy(changed)


@pytest.mark.parametrize('case_index', range(5))
def test_default_against_preserved_actual_sentaurus_stack(case_index):
    data = json.loads((Path(__file__).parent/'data/sentaurus_fe_oxide_stack.json').read_text())
    c = data['cases'][case_index]
    times = np.array(c['times_s']); top = -np.array(c['drive_voltage_V'])
    sim, _, _, mask = stack_device(times, top, c['oxide_nm'], 8, c['axis'], enabled=None)
    states = sim.solve_transient()
    assert all(s['valid'] and s['lk_material_field'] for s in states)
    axis = c['axis']; expected = c['reference']
    values = dict(polarization_C_m2=[s['P'].reshape(-1, 3)[3, axis] for s in states],
                  top_charge_C=[s['electrode_charges_C'][1] for s in states],
                  top_current_A=[0., *[s['electrode_total_currents_A'][1] for s in states[1:]]],
                  field_fe_V_m=[s['E'+'xyz'[axis]][3] for s in states],
                  field_oxide_V_m=[s['E'+'xyz'[axis]][-1] for s in states])
    errors = {k: float(np.max(np.abs(np.asarray(v)-expected[k]))/np.max(np.abs(expected[k])))
              for k, v in values.items()}
    assert all(e < 1e-3 for e in errors.values()) == c['comparison_passed']
    assert max(np.ptp(s['P'].reshape(-1, 3)[mask != 0, axis]) for s in states) < 1e-12
