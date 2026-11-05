"""Real native trials: independent acceptance, clock/history ownership and rollback."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from tcad.solver.lattice_time import LatticeTimeStepper, LatticeStepRejected
from test_lattice_mobility_feedback import setup, heat_network, VT, EXTRUSION


def case(*, shape=None, axis=0, graded=False, bias=.08, model=1, feedback=True):
    native, axes, kappa, bath = setup(shape=shape, axis=axis, graded=graded, bias=bias,
                                       model=model, feedback=feedback)
    bbox = tuple((float(a[0]), float(a[-1]) if len(a) > 1 else float(a[0]+e))
                 for a, e in zip(axes, EXTRUSION))
    mesh = StructuredGrid(bbox, *map(len, axes), axes=axes)
    sim = Simulator(mesh)
    # Preserve the physical fixture's complete native configuration while
    # exercising the real high-level run/transaction API and recording layer.
    sim._sim.backend = native
    accepted = sim.run(max_iter=100, tol=1e-11)
    assert accepted['converged']
    size = mesh.npts()
    contract = dict(axes_m=axes, extrusion_m=EXTRUSION.copy(), conductivity_W_m_K=kappa,
        thermal_dirichlet_K=bath, base_mobility_n=np.full(size, .01),
        base_mobility_p=np.full(size, .005), doping_m3=np.zeros(size),
        mobility_model=('constant', 'arora', 'low_temp')[model],
        reference_temperature_K=300., reference_VT_V=VT, power_atol_W=1e-18,
        temperature_atol_K=2e-7, fixed_point_atol_K=1e-7, current_rtol=2e-7,
        current_atol_A_m2=1e-7)
    return sim, contract


def driver(sim, contract, **kwargs):
    initial = kwargs.pop('initial', np.full(sim.mesh.npts(), 300.))
    capacity = kwargs.pop('capacity', np.full(sim.mesh.npts(), 2e5))
    return LatticeTimeStepper(sim, initial, capacity, **{**contract, **kwargs})


def exact(a, b):
    if isinstance(a, np.ndarray):
        assert a.dtype == b.dtype
        np.testing.assert_array_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            exact(a[key], b[key])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            exact(x, y)
    else:
        assert a == b


def snapshot(sim):
    return deepcopy(dict(result=sim.results, guess=sim._accepted_initial_guess,
        contact=sim._accepted_contact_voltages, configuration=sim.configuration_snapshot(),
        advanced=sim._configuration_state_advanced, native=sim._sim._export_result()))


@pytest.mark.parametrize('shape,axis', [((5,1,1),0), ((1,5,1),1), ((1,1,5),2),
    ((5,3,1),0), ((1,5,3),1), ((3,1,5),2), ((3,3,3),0)])
@pytest.mark.parametrize('bias', [-.08, .08])
def test_continuous_steps_use_accepted_history_and_independent_heat_network(shape, axis, bias):
    sim, contract = case(shape=shape, axis=axis, graded=True, bias=bias)
    clock = driver(sim, contract)
    previous = clock.temperature_K
    for dt in (1e-8, 3e-8, 1e-7):
        start = clock.time_s
        report = clock.step(dt)
        assert report['accepted'] and report['power_audit']['valid'] and report['mobility_audit']['valid']
        assert report['complete_device_energy'] is False and report['physical_validated'] is False
        assert clock.time_s == start+dt
        exact(report['result']['thermal_ledger']['previous_temperature_K'], previous)
        expected = heat_network(report['result'], contract['axes_m'], contract['conductivity_W_m_K'],
            contract['thermal_dirichlet_K'], previous=previous,
            capacity=np.full(sim.mesh.npts(), 2e5), dt=report['dt_s'])
        np.testing.assert_allclose(clock.temperature_K, expected, rtol=0., atol=2e-7)
        previous = clock.temperature_K
    assert clock.accepted_steps == 3 and np.max(clock.temperature_K) > 300.


def test_unresolved_storage_rejection_rolls_back_every_owner_and_retry_matches_fresh():
    sim, contract = case()
    clock = driver(sim, contract)
    before = snapshot(sim)
    with pytest.raises(LatticeStepRejected, match='independent') as failure:
        clock.step(1e-22)
    attempt = failure.value.attempt
    assert attempt['result']['converged']
    assert not attempt['power_audit']['valid']
    assert clock.time_s == 0. and clock.accepted_steps == 0 and clock.last_report is None
    np.testing.assert_array_equal(clock.temperature_K, np.full(5, 300.))
    exact(snapshot(sim), before)
    retry = clock.step(1e-8)
    fresh, fresh_contract = case()
    expected = driver(fresh, fresh_contract).step(1e-8)
    exact(retry, expected)


def test_later_failure_retains_the_last_accepted_step(monkeypatch):
    sim, contract = case()
    clock = driver(sim, contract)
    first = clock.step(1e-8)
    state = snapshot(sim)
    entered = clock.temperature_K
    original = sim.run_lattice_step
    def corrupt(*args):
        result = original(*args)
        result['thermal_ledger']['storage_power_W'] += 1e-12
        return result
    monkeypatch.setattr(sim, 'run_lattice_step', corrupt)
    with pytest.raises(LatticeStepRejected):
        clock.step(2e-8)
    exact(snapshot(sim), state)
    exact(clock.last_report, first)
    exact(clock.temperature_K, entered)
    assert clock.time_s == 1e-8 and clock.accepted_steps == 1


@pytest.mark.parametrize('field', ['Jn_x', 'temperature', 'mobility', 'history', 'capacity', 'dt'])
def test_corrupt_candidate_is_rejected_and_cache_restored(field, monkeypatch):
    sim, contract = case()
    clock = driver(sim, contract)
    before = snapshot(sim)
    original = sim.run_lattice_step
    def corrupt(*args):
        r = original(*args)
        if field in ('Jn_x', 'temperature'):
            r[field][2] *= 1.1
        else:
            key = dict(mobility='mobility_n_m2_V_s', history='previous_temperature_K',
                       capacity='heat_capacity_J_m3_K', dt='dt_s')[field]
            if field == 'dt':
                r['thermal_ledger'][key] *= 2
            else:
                r['thermal_ledger'][key][2] *= 1.1
        return r
    monkeypatch.setattr(sim, 'run_lattice_step', corrupt)
    with pytest.raises(LatticeStepRejected):
        clock.step(1e-8)
    exact(snapshot(sim), before)
    assert clock.time_s == 0. and clock.accepted_steps == 0


@pytest.mark.parametrize('kind', ['solve', 'audit', 'configuration'])
def test_exceptions_restore_simulator_and_clock(kind, monkeypatch):
    sim, contract = case()
    clock = driver(sim, contract)
    before = snapshot(sim)
    if kind == 'solve':
        original = sim.run_lattice_step
        def explode(*args):
            original(*args)
            raise ArithmeticError('injected failure after native trial')
        monkeypatch.setattr(sim, 'run_lattice_step', explode)
        error = ArithmeticError
    elif kind == 'audit':
        import tcad.solver.lattice_time as module
        def explode(*args, **kwargs):
            raise ArithmeticError('injected audit failure')
        monkeypatch.setattr(module, 'audit_native_lattice_step', explode)
        error = ArithmeticError
    else:
        sim._sim.set_quantum_enabled(True)
        before = snapshot(sim)
        error = ValueError
    with pytest.raises(error):
        clock.step(1e-8)
    exact(snapshot(sim), before)
    assert clock.time_s == 0. and clock.accepted_steps == 0


def test_nonconvergence_is_rejected_with_candidate_and_restores_seed():
    sim, contract = case()
    sim.set_lattice_mobility_feedback(True, max_iter=1)
    clock = driver(sim, contract, initial=np.full(5, 400.))
    before = snapshot(sim)
    with pytest.raises(LatticeStepRejected, match='did not converge') as failure:
        clock.step(1e-7)
    assert not failure.value.attempt['result']['converged']
    exact(snapshot(sim), before)
    assert clock.time_s == 0.


def test_feedback_is_required_and_wrong_independent_contracts_cannot_pass():
    sim, contract = case(feedback=False)
    with pytest.raises(LatticeStepRejected, match='feedback'):
        driver(sim, contract).step(1e-8)
    sim.set_lattice_mobility_feedback(True)
    for changes in (dict(conductivity_W_m_K=np.full(5, .002)),
                    dict(doping_m3=np.full(5, 1e23)), dict(reference_temperature_K=301.),
                    dict(thermal_dirichlet_K={0: 301., 4: 300.})):
        before = snapshot(sim)
        with pytest.raises(LatticeStepRejected):
            driver(sim, contract, **changes).step(1e-8)
        exact(snapshot(sim), before)


def test_inputs_and_returned_reports_do_not_alias_accepted_state():
    sim, contract = case()
    fresh, other = case()
    initial, capacity = np.full(5, 300.), np.full(5, 2e5)
    clock = driver(sim, contract, initial=initial, capacity=capacity)
    control = driver(fresh, other)
    initial[:] = 900.; capacity[:] = 1.
    for key in ('base_mobility_n', 'base_mobility_p', 'doping_m3', 'conductivity_W_m_K'):
        contract[key][:] = 123.
    contract['axes_m'][0][:] = 2.
    contract['extrusion_m'][:] = 2.
    contract['thermal_dirichlet_K'][0] = 999.
    r = clock.step(1e-8)
    exact(r, control.step(1e-8))
    r['result']['temperature'][:] = 999.
    r['power_audit']['valid'] = False
    exposed = clock.temperature_K; exposed[:] = 999.
    cached = clock.last_report; cached['result']['temperature'][:] = 999.
    sim.results['temperature'][:] = 999.
    exact(clock.step(1e-8), control.step(1e-8))


@pytest.mark.parametrize('bad', [0., -1., float('nan'), float('inf'), True, 1j, '1e-8', [1e-8]])
def test_invalid_step_intervals_do_not_start_a_solve(bad, monkeypatch):
    sim, contract = case()
    clock = driver(sim, contract)
    def forbidden(*args):
        pytest.fail('invalid interval started a solve')
    monkeypatch.setattr(sim, 'run_lattice_step', forbidden)
    with pytest.raises(ValueError):
        clock.step(bad)
    assert clock.time_s == 0.


@pytest.mark.parametrize('time,dt', [(1., 1e-22), (1e308, 1e308)])
def test_unrepresentable_clock_endpoint_rejected(time, dt):
    sim, contract = case()
    clock = driver(sim, contract, initial_time_s=time)
    with pytest.raises(ValueError, match='representable'):
        clock.step(dt)
    assert clock.time_s == time


@pytest.mark.parametrize('changes', [dict(power_atol_W=0.), dict(power_atol_W=-1.),
    dict(current_rtol=-1.), dict(temperature_atol_K=True), dict(reference_VT_V=0.),
    dict(fixed_point_atol_K=float('nan')), dict(initial_time_s=-1.),
    dict(initial_time_s=True), dict(mobility_model='unknown'), dict(base_mobility_n=np.full(5,-1.)),
    dict(thermal_dirichlet_K={True:300.}), dict(thermal_dirichlet_K={6:300.}),
    dict(thermal_dirichlet_K={0:0.}), dict(thermal_dirichlet_K={}),
    dict(extrusion_m=[1e-7,1e-7,1e-7]), dict(conductivity_W_m_K=np.zeros(5)),
    dict(capacity=np.zeros(5)), dict(initial=np.ones((5,1))), dict(initial=np.full(5,300+1j))])
def test_invalid_external_contract_rejected_before_solving(changes):
    sim, contract = case()
    before = snapshot(sim)
    with pytest.raises(ValueError):
        driver(sim, contract, **changes)
    exact(snapshot(sim), before)


def test_mesh_replacement_requires_new_driver():
    sim, contract = case()
    clock = driver(sim, contract)
    sim.mesh = deepcopy(sim.mesh)
    with pytest.raises(ValueError, match='mesh changed'):
        clock.step(1e-8)


@pytest.mark.parametrize('commit_inner', [False, True])
def test_nested_native_cache_checkpoints_restore_exact_result(commit_inner):
    sim, contract = case()
    raw = sim._sim.backend
    accepted = raw._export_result()
    raw.begin_reliability_transaction()
    outer = raw.solve_lattice_step(np.full(5, 400.), np.full(5, 2e5), 1e-7)
    raw.begin_reliability_transaction()
    inner = raw.solve_lattice_step(np.full(5, 450.), np.full(5, 2e5), 1e-7)
    assert np.max(abs(inner['temperature']-outer['temperature'])) > 1.
    if commit_inner:
        raw.commit_reliability_transaction()
        exact(raw._export_result(), inner)
    else:
        raw.rollback_reliability_transaction()
        exact(raw._export_result(), outer)
    raw.rollback_reliability_transaction()
    exact(raw._export_result(), accepted)
    with pytest.raises(RuntimeError, match='no active'):
        raw.rollback_reliability_transaction()


def test_native_committed_cache_remains_queryable_and_empty_checkpoint_error_is_safe():
    sim, contract = case()
    raw = sim._sim.backend
    with pytest.raises(RuntimeError, match='no active'):
        raw.commit_reliability_transaction()
    raw.begin_reliability_transaction()
    trial = raw.solve_lattice_step(np.full(5, 400.), np.full(5, 2e5), 1e-7)
    raw.commit_reliability_transaction()
    exact(raw._export_result(), trial)
