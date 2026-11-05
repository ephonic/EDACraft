"""Check the entirely unconfigured LK integration default against independent physics."""
import ast
from copy import deepcopy
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_energy
from test_fe_series_stack import stack
from test_lk_fixed_charge import check_history, widths
from test_lk_material_field import stack_device
from test_fe_transient_feedback import dielectric
from test_transient_displacement import film


def without_policy_overrides(factory):
    """Keep the physical fixture; remove both explicit historical policy calls.

    This compiles a fresh factory, rather than changing a live simulator or
    replacing its methods. Assert that neither mode setter remains in its AST.
    """
    tree = ast.parse(inspect.getsource(factory))
    setters = {'set_transient_lk_material_field', 'set_transient_lk_coupled'}
    class Remove(ast.NodeTransformer):
        def visit_Expr(self, n):
            if isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr in setters:
                return ast.copy_location(ast.Pass(), n)
            return self.generic_visit(n)
    tree = Remove().visit(tree)
    assert not any(isinstance(n, ast.Attribute) and n.attr in setters for n in ast.walk(tree))
    namespace = dict(factory.__globals__)
    exec(compile(tree, '<physical fixture without policy overrides>', 'exec'), namespace)
    return namespace[factory.__name__]


auto_film = without_policy_overrides(film)
auto_stack = without_policy_overrides(stack_device)
auto_dielectric = without_policy_overrides(dielectric)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('oxide', [.2, .5, 1.])
@pytest.mark.parametrize('cells', [8, 32])
def test_no_mode_setters_matches_independent_series_voltage_partition(axis, oxide, cells):
    times = np.linspace(0., 1e-9, 41); top = -8*np.sin(2*np.pi*times/1e-9)
    sim, x, eps, mask = auto_stack(times, top, oxide, cells, axis)
    states = sim.solve_transient()
    ref = stack(thickness_oxide=oxide*1e-9).solve_backward_euler(times, -top)
    for i, s in enumerate(states):
        assert s['valid'] and s['lk_coupled'] and s['lk_material_field']
        p = s['P'].reshape(-1, 3)[:, axis]
        np.testing.assert_allclose(p[mask != 0], ref['polarization_C_m2'][i], rtol=2e-11, atol=2e-12)
        np.testing.assert_allclose(s['electrode_charges_C'][1], ref['top_charge_C'][i], rtol=3e-11, atol=1e-25)
        np.testing.assert_allclose(eps*s['E'+'xyz'[axis]]+p, -s['electrode_charges_C'][1]/1e-13, rtol=1e-11, atol=2e-14)
        if i:
            assert s['dt_s'] == pytest.approx(times[i]-times[i-1], rel=1e-13)
            np.testing.assert_allclose(s['electrode_total_currents_A'][1], ref['top_current_A'][i], rtol=1e-9, atol=2e-15)
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('sign', [-1, 0, 1])
def test_no_mode_setters_matches_independent_charged_full_block(axis, stretched, sign):
    sim, x, eps, mask, area = auto_film(axis, 0, stretched, True)
    c = np.zeros(len(x)); c[1:-1] = np.linspace(.3, 1.4, len(x)-2)*1e23
    if sign:
        c *= sign
    else:
        c[1:-1] *= np.array([1., -1., 1., -1., 1., -1., 1.])
        c[-2] -= np.dot(widths(x), c)/widths(x)[-2]
    sim.set_doping(c)
    states = check_history(sim, x, eps, mask, area, c, axis)
    assert all(s['lk_coupled'] and s['lk_material_field'] for s in states)


CASES = ['mobility', 'generation', 'carrier', 'contact_carrier', 'endpoint_doping', 'srh',
         'fraction', 'edge', 'extra_contact', 'freeze_n', 'freeze_p', '2d', '3d',
         'model1', 'model2', 'model3', 'coarse_nonmonotone', 'split_override', 'centered_override']


def fallback(case, explicit_split=False):
    if case in ('2d', '3d'):
        from test_transient_lk_coupled import linear_multidimensional_case
        sim, *_ = without_policy_overrides(linear_multidimensional_case)(int(case[0]), False, False)
    else:
        sim, x, *_ = auto_film(0, 0, True, True)
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
        elif case.startswith('model'): sim.set_ferroelectric_model(int(case[-1])); sim.set_ferroelectric_gamma(0.)
        elif case == 'coarse_nonmonotone': sim.set_transient_dt(2e-9); sim.set_transient_t_final(4e-9)
        elif case == 'split_override': sim.set_transient_lk_coupled(False)
        elif case == 'centered_override': sim.set_transient_lk_material_field(False)
    if explicit_split: sim.set_transient_lk_coupled(False)
    return sim


@pytest.mark.parametrize('case', CASES)
def test_ineligible_or_explicit_default_preserves_actual_split_equations(case):
    actual = fallback(case).solve_transient(); expected = fallback(case, True).solve_transient()
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        assert not a['lk_coupled'] and not a['lk_material_field']
        assert a['valid'] == b['valid'] and a['time_s'] == b['time_s']
        for key in ('phi', 'n', 'p', 'P'):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize('direction,expected', [(-1, True), (0, False), (1, False)])
def test_automatic_monotonicity_uses_the_exact_critical_step(direction, expected):
    # All critical coefficients are binary-exact; this checks both sides of
    # alpha+gamma/dt=0 without a decimal threshold ambiguity.
    critical = 2.**-30
    dt = critical if direction == 0 else np.nextafter(critical, 0. if direction < 0 else np.inf)
    sim, _ = auto_dielectric(dt=dt, final=dt, alpha=-2.**27, gamma=.125)
    states = sim.solve_transient()
    assert all(s['valid'] and s['lk_coupled'] == expected and s['lk_material_field'] == expected for s in states)
    assert states[-1]['time_s'] == dt and len(states) == 2
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('waveform', [False, True])
def test_short_actual_intervals_enable_automatic_coupling_without_changing_clock(waveform):
    final = 3e-10 if waveform else 1e-10
    sim, _ = auto_dielectric(dt=1e-7, final=final, voltage=0.)
    if waveform: sim.set_transient_voltage_waveforms([0., 1e-10, 2e-10, 3e-10], {8: [0., -.01, 0., .01]})
    states = sim.solve_transient()
    assert all(s['valid'] and s['lk_coupled'] and s['lk_material_field'] for s in states)
    expected = [0., 1e-10, 2e-10, 3e-10] if waveform else [0., 1e-10]
    np.testing.assert_array_equal([s['time_s'] for s in states], expected)


def test_automatic_integration_rechecks_carriers_and_sticky_overrides_on_each_run():
    sim, *_ = auto_film(0, 0, True, True)
    assert sim.solve_transient()[-1]['lk_coupled']
    sim.set_initial_guess(np.zeros(9), np.ones(9)*1e10, np.ones(9)*1e10)
    assert not sim.solve_transient()[-1]['lk_coupled']
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    assert sim.solve_transient()[-1]['lk_coupled']
    for requested in [False, True, False]:
        sim.set_transient_lk_coupled(requested)
        history = sim.solve_transient()
        assert all(s['lk_coupled'] == requested for s in history)
        assert audit_transient_lk_energy(history)['valid']


def test_automatic_failed_attempt_rolls_back_and_retries_without_latching_policy():
    sim, *_ = auto_film(0, 0, True, True)
    sim.set_nonlinear_history_enabled(True); sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]['valid'] and failed[-1]['lk_coupled'] and failed[-1]['lk_material_field']
    np.testing.assert_array_equal(failed[-1]['P'], failed[0]['P'])
    assert sim.get_transient_attempt_history()[0]['trials'][0]['solver'] == 'lk_material_field_1d'
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, *_ = auto_film(0, 0, True, True)
    for a, b in zip(retry, fresh.solve_transient()):
        for key in ('P', 'phi', 'time_s', 'electrode_charges_C'):
            np.testing.assert_array_equal(a[key], b[key])
    wrong = deepcopy(retry); wrong[-1]['lk_coupled'] = False
    with pytest.raises(ValueError): audit_transient_lk_energy(wrong)


def test_automatic_integration_does_not_reinterpret_explicit_controller_requirements():
    sim, *_ = auto_film(0, 0, True, True)
    sim.set_transient_lk_substepping(True)
    with pytest.raises(ValueError, match='requires enabled coupled LK'):
        sim.solve_transient()


@pytest.mark.parametrize('case_index', range(5))
def test_unconfigured_default_against_preserved_actual_sentaurus_stack(case_index):
    data = json.loads((Path(__file__).parent/'data/sentaurus_fe_oxide_stack.json').read_text())
    c = data['cases'][case_index]
    sim, _, _, mask = auto_stack(np.array(c['times_s']), -np.array(c['drive_voltage_V']), c['oxide_nm'], 8, c['axis'])
    states = sim.solve_transient(); axis = c['axis']; expected = c['reference']
    assert all(s['valid'] and s['lk_coupled'] and s['lk_material_field'] for s in states)
    actual = dict(polarization_C_m2=[s['P'].reshape(-1, 3)[3, axis] for s in states],
                  top_charge_C=[s['electrode_charges_C'][1] for s in states],
                  top_current_A=[0., *[s['electrode_total_currents_A'][1] for s in states[1:]]],
                  field_fe_V_m=[s['E'+'xyz'[axis]][3] for s in states],
                  field_oxide_V_m=[s['E'+'xyz'[axis]][-1] for s in states])
    errors = {k: float(np.max(np.abs(np.array(v)-expected[k]))/np.max(np.abs(expected[k]))) for k, v in actual.items()}
    assert all(e < 1e-3 for e in errors.values()) == c['comparison_passed']
    assert max(np.ptp(s['P'].reshape(-1, 3)[mask != 0, axis]) for s in states) < 1e-12
