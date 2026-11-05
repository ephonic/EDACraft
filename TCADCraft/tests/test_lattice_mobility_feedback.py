"""Actual DeviceSimulator feedback, independent heat networks and retry isolation."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import native_constants

from test_native_steady_thermal import fixture, EXTRUSION
from tcad.postprocess.native_thermal import (
    audit_native_steady_thermal, audit_native_lattice_step, audit_native_lattice_mobility)

POWER_BUDGET = dict(extrusion_m=EXTRUSION, power_atol_W=1e-18, temperature_atol_K=2e-7)
VT = 8.617333262e-5*300.


def setup(*, axis=0, graded=False, feedback=True, model=1, bias=.08, shape=None):
    sim, axes, kappa, bath = fixture(axis=axis, shape=shape, graded=graded, variable=False, bias=bias)
    sim.set_temperature(300.)
    sim.set_mobility_model(model)
    sim.set_use_newton(True)
    sim.set_newton_use_log_space(True)
    sim.set_newton_use_log_damping(True)
    sim.set_lattice_mobility_feedback(feedback, 120, 1e-7, .5)
    return sim, axes, kappa, bath


def mobility_audit(result, axes, model='arora', doping=None):
    size = len(result['phi'])
    return audit_native_lattice_mobility(result, axes, np.full(size, .01), np.full(size, .005),
        np.zeros(size) if doping is None else doping, model, 300., VT,
        fixed_point_atol_K=1e-7, current_rtol=2e-7, current_atol_A_m2=1e-7,
        elementary_charge_C=float(native_constants()['elementary_charge_C']))


def heat_network(result, axes, kappa, bath, *, previous=None, capacity=None, dt=None):
    """Dimensional FV matrix assembled independently of native ledger fields."""
    nx, ny, nz = map(len, axes)
    size = nx*ny*nz
    widths = [np.array([e]) if len(a) == 1 else np.r_[np.diff(a)[0],
        (np.diff(a)[:-1]+np.diff(a)[1:])/2, np.diff(a)[-1]] for a, e in zip(axes, EXTRUSION)]
    volume = np.array([widths[0][i]*widths[1][j]*widths[2][k]
                       for k in range(nz) for j in range(ny) for i in range(nx)])
    matrix = np.zeros((size, size))
    source = np.zeros(size)
    for node in range(size):
        coordinate = (node % nx, (node//nx) % ny, node//(nx*ny))
        for axis, stride in enumerate((1, nx, nx*ny)):
            index = coordinate[axis]
            if index+1 == len(axes[axis]):
                continue
            neighbor = node+stride
            area = np.prod([widths[b][coordinate[b]] for b in range(3) if b != axis])
            d = axes[axis][index+1]-axes[axis][index]
            current = result['Jn_'+'xyz'[axis]][node]+result['Jp_'+'xyz'[axis]][node]
            edge_power = abs(current*(result['phi'][node]-result['phi'][neighbor]))*area
            source[node] += edge_power/2
            source[neighbor] += edge_power/2
            conductance = 2/(1/kappa[node]+1/kappa[neighbor])*area/d
            matrix[node, node] += conductance
            matrix[node, neighbor] -= conductance
            matrix[neighbor, node] -= conductance
            matrix[neighbor, neighbor] += conductance
    rhs = source.copy()
    if dt is not None:
        rate = capacity*volume/dt
        matrix += np.diag(rate)
        rhs += rate*previous
    for node, temperature in bath.items():
        matrix[node] = 0.
        matrix[node, node] = 1.
        rhs[node] = temperature
    return np.linalg.solve(matrix, rhs)


@pytest.mark.parametrize('model,name', [(1, 'arora'), (2, 'low_temp')])
@pytest.mark.parametrize('axis', [0, 1, 2])
def test_reference_temperature_model_currents_match_continuity(model, name, axis):
    sim, axes, kappa, bath = setup(axis=axis, feedback=False, model=model)
    result = sim.solve()
    assert result['converged']
    assert mobility_audit(result, axes, name)['valid']
    assert audit_native_steady_thermal(result, axes, kappa, bath, **POWER_BUDGET)['valid']


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('graded', [False, True])
def test_actual_feedback_changes_current_and_matches_heat_network(axis, graded):
    cold, axes, kappa, bath = setup(axis=axis, graded=graded, feedback=False)
    one_way = cold.solve()
    sim, axes, kappa, bath = setup(axis=axis, graded=graded)
    result = sim.solve()
    assert result['converged']
    assert result['thermal_ledger']['feedback_iterations'] > 1
    assert result['thermal_ledger']['current_projected'] is False
    assert mobility_audit(result, axes)['valid']
    assert audit_native_steady_thermal(result, axes, kappa, bath, **POWER_BUDGET)['valid']
    np.testing.assert_allclose(result['temperature'], heat_network(result, axes, kappa, bath), rtol=0., atol=2e-7)
    direction = 'xyz'[axis]
    old = one_way['Jn_'+direction][0]+one_way['Jp_'+direction][0]
    new = result['Jn_'+direction][0]+result['Jp_'+direction][0]
    assert abs(new/old-1) > 1e-3
    assert abs(new) < abs(old)


@pytest.mark.parametrize('bias', [-.08, 0., .08])
def test_feedback_sign_and_zero_bias(bias):
    sim, axes, kappa, bath = setup(bias=bias)
    result = sim.solve()
    assert result['converged']
    assert mobility_audit(result, axes)['valid']
    if bias == 0.:
        np.testing.assert_allclose(result['temperature'], 300., rtol=0., atol=1e-10)
        assert abs(result['thermal_ledger']['source_power_W']) < 1e-25


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_BE_continuous_steps_pass_independent_storage_and_bath_audit(axis):
    sim, axes, kappa, bath = setup(axis=axis, graded=True)
    previous = np.full(len(kappa), 300.)
    capacity = np.linspace(1e5, 3e5, len(kappa))
    for dt in (2e-8, 5e-8, 1e-7):
        result = sim.solve_lattice_step(previous, capacity, dt)
        assert result['converged']
        assert mobility_audit(result, axes)['valid']
        audit = audit_native_lattice_step(result, axes, kappa, bath, previous, capacity, dt, **POWER_BUDGET)
        assert audit['valid']
        assert audit['storage_power_W'] > 0
        expected = heat_network(result, axes, kappa, bath, previous=previous, capacity=capacity, dt=dt)
        np.testing.assert_allclose(result['temperature'], expected, rtol=0., atol=2e-7)
        assert max(result['temperature']) > max(previous)
        previous = result['temperature'].copy()
    # BE state is scoped to one call; subsequent DC has no stale capacity.
    assert sim.solve()['thermal_ledger']['transient_storage'] is False


def test_changed_bath_accounts_for_pinned_node_storage():
    sim, axes, kappa, bath = setup(bias=0.)
    previous = np.full(5, 310.)
    capacity = np.full(5, 2e5)
    result = sim.solve_lattice_step(previous, capacity, 1e-7)
    assert result['converged']
    audit = audit_native_lattice_step(result, axes, kappa, bath, previous, capacity, 1e-7, **POWER_BUDGET)
    assert audit['valid']
    assert audit['storage_power_W'] < 0
    assert result['thermal_ledger']['node_storage_power_W'][0] < 0
    assert result['thermal_ledger']['bath_heat_W'][0] > 0


@pytest.mark.parametrize('transient', [False, True])
def test_failed_outer_iteration_rolls_back_and_retry_matches_fresh(transient):
    sim, axes, kappa, bath = setup()
    sim.set_lattice_mobility_feedback(True, 1, 1e-7, .5)
    previous = np.full(5, 300.)
    capacity = np.full(5, 2e5)
    invoke = lambda s: s.solve_lattice_step(previous, capacity, 1e-7) if transient else s.solve()
    bad = invoke(sim)
    assert not bad['converged'] and not bad['thermal_ledger']['available']
    sim.set_lattice_mobility_feedback(True, 120, 1e-7, .5)
    retry = invoke(sim)
    fresh, *_ = setup()
    control = invoke(fresh)
    assert retry['converged'] and control['converged']
    for name in ('phi', 'n', 'p', 'temperature', 'Jn_x', 'Jp_x'):
        np.testing.assert_array_equal(retry[name], control[name])


@pytest.mark.parametrize('field', ['storage_power_W', 'dt_s', 'node_storage_power_W',
                                  'previous_temperature_K', 'heat_capacity_J_m3_K'])
def test_forged_storage_is_rejected(field):
    sim, axes, kappa, bath = setup()
    previous = np.full(5, 300.)
    capacity = np.full(5, 2e5)
    result = sim.solve_lattice_step(previous, capacity, 1e-7)
    bad = deepcopy(result)
    bad['thermal_ledger'][field] *= 1.1
    assert not audit_native_lattice_step(bad, axes, kappa, bath, previous, capacity, 1e-7, **POWER_BUDGET)['valid']
    with pytest.raises(ValueError, match='history/capacity'):
        audit_native_steady_thermal(result, axes, kappa, bath, **POWER_BUDGET)


@pytest.mark.parametrize('field', ['mobility_n_m2_V_s', 'mobility_p_m2_V_s',
                                  'mobility_temperature_K', 'feedback_residual_K', 'carrier_reference_VT_V'])
def test_forged_feedback_metadata_is_rejected(field):
    sim, axes, *_ = setup()
    result = sim.solve()
    bad = deepcopy(result)
    bad['thermal_ledger'][field] *= 1.1
    assert not mobility_audit(bad, axes)['valid']


@pytest.mark.parametrize('value', [0., -1., float('nan'), float('inf')])
@pytest.mark.parametrize('argument', ['previous', 'capacity', 'dt'])
def test_invalid_step_inputs_are_rejected_without_poisoning_next_solve(value, argument):
    sim, *_ = setup()
    previous, capacity, dt = np.full(5, 300.), np.full(5, 2e5), 1e-7
    if argument == 'previous': previous[2] = value
    if argument == 'capacity': capacity[2] = value
    if argument == 'dt': dt = value
    with pytest.raises(ValueError):
        sim.solve_lattice_step(previous, capacity, dt)
    assert sim.solve()['converged']


@pytest.mark.parametrize('controls', [(0, 1e-7, .5), (True, 1e-7, .5), (2.5, 1e-7, .5),
    (10, 0., .5), (10, float('nan'), .5), (10, 1e-7, 0.), (10, 1e-7, 1.1)])
def test_invalid_feedback_controls(controls):
    sim, *_ = setup()
    with pytest.raises(ValueError):
        sim.set_lattice_mobility_feedback(True, *controls)


def test_unsupported_physics_and_disabled_heat_reject_instead_of_falling_back():
    sim, *_ = setup()
    sim.set_quantum_enabled(True)
    with pytest.raises(ValueError, match='classical'):
        sim.solve()
    sim.set_quantum_enabled(False)
    sim.set_thermal_coupling_enabled(False)
    with pytest.raises(ValueError, match='thermal coupling'):
        sim.solve()
    with pytest.raises(ValueError, match='thermal coupling'):
        sim.solve_lattice_step(np.full(5, 300.), np.full(5, 2e5), 1e-7)


@pytest.mark.parametrize('shape', [(3, 3, 1), (3, 3, 3)])
def test_multidimensional_feedback_and_storage(shape):
    sim, axes, kappa, bath = setup(shape=shape)
    previous = np.full(len(kappa), 300.)
    capacity = np.full(len(kappa), 2e5)
    result = sim.solve_lattice_step(previous, capacity, 1e-7)
    assert result['converged']
    assert mobility_audit(result, axes)['valid']
    assert audit_native_lattice_step(result, axes, kappa, bath, previous, capacity, 1e-7, **POWER_BUDGET)['valid']
    np.testing.assert_allclose(result['temperature'],
        heat_network(result, axes, kappa, bath, previous=previous, capacity=capacity, dt=1e-7), rtol=0., atol=2e-7)


@pytest.mark.parametrize('doping', [-1e22, 1e22])
@pytest.mark.parametrize('model,name', [(1, 'arora'), (2, 'low_temp')])
def test_signed_dopants_produce_finite_consistent_model_currents(doping, model, name):
    sim, axes, kappa, bath = setup(feedback=False, model=model, bias=.02)
    n = (doping+np.sqrt(doping*doping+4e42))/2
    p = 1e42/n
    potential = np.linspace(0., .02, 5)
    sim.set_doping(np.full(5, doping))
    sim.set_electron_bc({0: n, 4: n})
    sim.set_hole_bc({0: p, 4: p})
    sim.set_initial_guess(potential, np.full(5, n), np.full(5, p))
    result = sim.solve()
    assert result['converged']
    assert mobility_audit(result, axes, name, np.full(5, doping))['valid']
    assert audit_native_steady_thermal(result, axes, kappa, bath, **POWER_BUDGET)['valid']


def test_constant_mobility_feedback_matches_one_way_control():
    cold, axes, *_ = setup(feedback=False, model=0)
    hot, *_ = setup(model=0)
    before, after = cold.solve(), hot.solve()
    assert before['converged'] and after['converged']
    assert mobility_audit(after, axes, 'constant')['valid']
    for field in ('phi', 'n', 'p', 'temperature', 'Jn_x', 'Jp_x'):
        np.testing.assert_allclose(before[field], after[field], rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize('bad', [np.full(5, 300.+1j), np.ones((5, 1)), ['300']*5, np.ones(4)])
def test_nonreal_or_wrong_shape_history_rejected(bad):
    sim, *_ = setup()
    with pytest.raises(ValueError):
        sim.solve_lattice_step(bad, np.full(5, 2e5), 1e-7)


def test_float64_unresolved_storage_cannot_be_certified_by_native_flags():
    sim, axes, kappa, bath = setup(feedback=False)
    previous = np.full(5, 300.)
    capacity = np.full(5, 2e5)
    dt = 1e-22
    result = sim.solve_lattice_step(previous, capacity, dt)
    assert result['converged']
    # Native quad arithmetic can resolve a change the public float64 state
    # cannot. A successful internal linear solve must not bypass the audit.
    assert not audit_native_lattice_step(result, axes, kappa, bath, previous, capacity, dt, **POWER_BUDGET)['valid']


def test_high_level_temperature_recipe_feedback_clone_and_lattice_step():
    from test_configuration_inheritance import setup as configured_device
    from tcad.simulator import Simulator
    _, _, source = configured_device()
    hot = Simulator(source.mesh, temperature=350.)
    hot.set_material_from_mesh()
    hot.set_contact('low', 0.)
    hot.set_contact('high', .01)
    hot.set_thermal_coupling(True, np.full(hot.mesh.npts(), .001), 350.)
    hot.set_mobility_model('arora')
    hot.set_lattice_mobility_feedback(True)
    result = hot.run(max_iter=100, tol=1e-10)
    assert result['converged']
    assert result['thermal_ledger']['carrier_reference_temperature_K'] == 350.
    clone = hot.clone_on_mesh(hot.mesh)
    recipe = clone.configuration_snapshot()
    assert any(c[1] == 'set_lattice_mobility_feedback' for c in recipe)
    entered_recipe = repr(hot.configuration_snapshot())
    step = hot.run_lattice_step(result['temperature'], np.full(hot.mesh.npts(), 2e5), 1e-7)
    assert step['converged'] and hot.results is step
    assert repr(hot.configuration_snapshot()) == entered_recipe
    hot.set_lattice_mobility_feedback(True, max_iter=1)
    accepted = hot.results
    failed = hot.run_lattice_step(np.full(hot.mesh.npts(), 400.), np.full(hot.mesh.npts(), 2e5), 1e-7)
    assert not failed['converged'] and hot.results is accepted


def test_carrier_transient_rejects_feedback_even_if_heat_was_disabled():
    sim, *_ = setup(model=0)
    sim.set_thermal_coupling_enabled(False)
    sim.set_transient_enabled(True)
    sim.set_transient_dt(1e-9)
    sim.set_transient_t_final(1e-9)
    with pytest.raises(ValueError, match='transient'):
        sim.solve_transient()


@pytest.mark.parametrize('model', [1, 2])
def test_model_preserves_zero_mobility_insulator(model):
    sim, axes, kappa, bath = setup(model=model)
    sim.set_mobility(np.zeros(5), np.zeros(5))
    sim.set_electron_bc({0: 0., 4: 0.})
    sim.set_hole_bc({0: 0., 4: 0.})
    sim.set_initial_guess(np.linspace(0., .08, 5), np.zeros(5), np.zeros(5))
    result = sim.solve()
    assert result['converged']
    for carrier in 'np':
        assert not np.any(result['thermal_ledger']['mobility_'+carrier+'_m2_V_s'])
        assert not np.any(result['J'+carrier+'_x'])
    np.testing.assert_allclose(result['temperature'], 300., rtol=0., atol=1e-10)
    assert audit_native_steady_thermal(result, axes, kappa, bath, **POWER_BUDGET)['valid']
