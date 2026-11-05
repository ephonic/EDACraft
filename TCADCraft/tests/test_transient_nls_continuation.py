"""Native-owned Python continuation: parity, ownership, guards and exports."""
import copy
import gc
import itertools
import pickle
import sys
import weakref

import numpy as np
import pytest

from test_transient_nls_event_control import configured, independent, T, S, PS
from test_transient_preflight_history import assert_exact
from tcad.simulator import Simulator


def setup(dimension=2, logarithmic=False, adaptive=False, protocol=0):
    sim, meta = configured(dimension, logarithmic, protocol=protocol, enable=False)
    sim.set_tolerance(1e-16)
    if adaptive:
        sim.set_transient_nls_error_control(True, .5, PS/2, 1., .5, S, T/1024, 20)
    return sim, meta


@pytest.mark.parametrize('dimension,logarithmic,adaptive,protocol',
                         itertools.product((2, 3), (False, True), (False, True), (0, 1)))
def test_native_owned_trajectory_matches_legacy(dimension, logarithmic, adaptive, protocol):
    args = dimension, logarithmic, adaptive, protocol
    reference, _ = setup(*args)
    expected = reference.solve_transient()
    trace = reference.get_transient_attempt_history()
    sim, meta = setup(*args)
    state = sim.create_nls_continuation()
    assert state.status == 'not_started' and state.history == [] and state.trace == []
    assert state.advance() == 'complete'
    assert_exact(state.history, expected)
    assert_exact(state.trace, trace)
    assert sim.get_transient_attempt_history() == []
    assert all(s['valid'] for s in state.history)
    independent(state.history, meta)
    diagnostics = state.diagnostics
    assert diagnostics['allocation_failures'] == diagnostics['solver_failures'] == diagnostics['retries'] == 0
    assert state.advance(max_retries=0) == 'complete'
    assert_exact(state.history, expected)
    assert_exact(state.trace, trace)
    assert state.diagnostics == diagnostics


@pytest.mark.parametrize('value', [-1, True, False, np.bool_(True), 1.5, '1', None, float('inf')])
def test_retry_budget_rejected_before_advancement(value):
    sim, _ = setup()
    state = sim.create_nls_continuation()
    with pytest.raises(ValueError):
        state.advance(value)
    assert state.status == 'not_started' and state.history == [] and state.trace == []


def test_retry_budget_overflow_and_numpy_integer():
    sim, _ = setup()
    state = sim.create_nls_continuation()
    with pytest.raises(OverflowError):
        state.advance(1 << 128)
    assert state.status == 'not_started'
    assert state.advance(np.int64(0)) == 'complete'


@pytest.mark.parametrize('adaptive', [False, True])
def test_exports_are_copies_and_owner_lives_as_long_as_capsule(adaptive):
    sim, _ = setup(adaptive=adaptive)
    before = sys.getrefcount(sim)
    state = sim.create_nls_continuation()
    assert sys.getrefcount(sim) == before + 1
    del sim
    gc.collect()
    assert state.advance() == 'complete'
    saved, trace, diagnostics = state.history, state.trace, state.diagnostics
    damaged = state.history
    damaged[-1]['phi'][:] = 123
    damaged[-1]['P'][:] = -456
    damaged.clear()
    damaged = state.trace
    damaged[0]['trials'].clear()
    damaged.clear()
    state.diagnostics['status'] = 'damaged'
    assert state.advance() == 'complete'
    assert_exact(state.history, saved)
    assert_exact(state.trace, trace)
    assert state.diagnostics == diagnostics


@pytest.mark.parametrize('operation', [copy.copy, copy.deepcopy, pickle.dumps])
def test_capsule_cannot_be_cloned_or_serialized(operation):
    sim, _ = setup()
    state = sim.create_nls_continuation()
    with pytest.raises(TypeError):
        operation(state)
    assert state.advance() == 'complete'


@pytest.mark.parametrize('setting', ['tol', 'end', 'seed', 'controller'])
def test_changed_configuration_rejected_without_losing_accepted_state(setting):
    sim, _ = setup(adaptive=True)
    state = sim.create_nls_continuation()
    assert state.advance() == 'complete'
    saved, trace, diagnostics = state.history, state.trace, state.diagnostics
    if setting == 'tol':
        sim.set_tolerance(5e-17)
    elif setting == 'end':
        sim.set_transient_t_final(5*T)
    elif setting == 'seed':
        sim.set_initial_guess(saved[-1]['phi'], saved[-1]['n'], saved[-1]['p'])
    else:
        sim.set_transient_nls_error_control(True, .25, PS/2, 1., .5, S, T/1024, 20)
    with pytest.raises(ValueError):
        state.advance()
    assert_exact(state.history, saved)
    assert_exact(state.trace, trace)
    assert state.diagnostics == diagnostics


def test_unqualified_scope_preserves_unstarted_capsule():
    sim, _ = setup()
    sim.set_quantum_enabled(True)
    state = sim.create_nls_continuation()
    with pytest.raises(ValueError):
        state.advance()
    assert state.history == [] and state.status == 'not_started'
    sim.set_quantum_enabled(False)
    assert state.advance() == 'complete'


def test_solver_stop_retains_accepted_prefix_and_rejects_budget_workaround():
    sim, _ = setup(adaptive=True)
    sim.set_gummel_max_iter(1)
    state = sim.create_nls_continuation()
    assert state.advance(0) == 'solver_failure'
    saved = state.history
    assert len(saved) == 1 and saved[0]['valid'] and saved[0]['initial_state']
    assert state.diagnostics['solver_failures'] == 1
    assert state.advance(1) == 'solver_failure'
    assert state.diagnostics['solver_failures'] == 3 and state.diagnostics['retries'] == 1
    assert_exact(state.history, saved)
    sim.set_gummel_max_iter(100)
    with pytest.raises(ValueError):
        state.advance()
    assert_exact(state.history, saved)


def test_high_level_factory_prepares_once_and_capsule_survives_wrapper():
    backend, _ = setup(adaptive=True)
    expected = backend.solve_transient()
    backend, _ = setup(adaptive=True)
    owner = Simulator.__new__(Simulator)
    owner._sim = backend
    owner._apply_cut_cell = lambda: None
    ref = weakref.ref(owner)
    state = owner.create_nls_continuation()
    assert owner._configuration_state_advanced
    del backend, owner
    gc.collect()
    assert ref() is None
    assert state.advance() == 'complete'
    assert_exact(state.history, expected)
