"""Finite breakdown inputs, irreversible history and filament current contract."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_trap_parameter_guard import ROUTES, SIZE, dielectric
from test_zero_auger_transient import digest

MASK = np.array([1, 1, 0, 1, 1, 0, 1, 0, 1], dtype=np.int8)
THRESHOLDS = np.array([0., 6e4, 1.8e5, 6e5, 1.5e5, 0., 8e4, 4e5, 1e5])
SIGMA = 1e-5
RETRY_MASK = np.array([0, 0, 1, 0, 1, 1, 0, 1, 0], dtype=np.int8)
RETRY_THRESHOLDS = np.full(SIZE, 2e4)
RETRY_SIGMA = 3e-5
FIELDS = ['threshold_unmasked', 'threshold_middle', 'threshold_last', 'conductivity']
POSITIONS = [2, 4, 8]
MODES = ['enabled', 'disabled']
HISTORIES = ['intact', 'broken']
BAD = {'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf}


def check_step(sim, x, axis, voltage, history, enabled,
               mask=MASK, thresholds=THRESHOLDS, sigma=SIGMA):
    # The imposed voltage and geometry determine the field independently of
    # the native detector. Avoid equality thresholds in floating-point tests.
    field = -voltage/(x[-1]-x[0])
    predicted = history.copy()
    if enabled:
        predicted |= mask.astype(bool) & (thresholds > 0) & (abs(field) > thresholds)
    sim.set_dirichlet_potential({0: 0., SIZE-1: voltage})
    state = sim.solve()
    assert state['converged']
    np.testing.assert_array_equal(sim.breakdown_state(), predicted.astype(np.int8))
    np.testing.assert_allclose(state['phi'], voltage*(x-x[0])/(x[-1]-x[0]),
                               rtol=1e-9, atol=1e-14)
    expected = np.zeros(SIZE)
    if enabled and sigma > 0:
        # A newly detected filament is committed after acceptance and enters
        # transport/current/heat together on the next solve (native contract).
        active = (history[:-1] | history[1:]) & (mask[:-1].astype(bool) | mask[1:].astype(bool))
        expected[:-1] = active*sigma*field
    actual = state['Jleak_'+'xyz'[axis]]
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-15)
    for other in set(range(3))-{axis}:
        assert np.all(state['Jleak_'+'xyz'[other]] == 0.)
    return (state, sim.breakdown_state().copy()), predicted, float(np.max(abs(actual-expected)))


def fixture(route, mode, history):
    axis = ROUTES.index(route)
    sim, x = dielectric(route, axis, stretched=True)
    sim.set_breakdown_params(MASK.copy(), THRESHOLDS.copy(), SIGMA)
    sim.set_breakdown_enabled(True)
    predicted = np.zeros(SIZE, dtype=bool)
    if history == 'broken':
        _, predicted, _ = check_step(sim, x, axis, .02, predicted, True)
        assert predicted.sum() == 4
    else:
        _, predicted, _ = check_step(sim, x, axis, .004, predicted, True)
        assert not predicted.any()
    sim.set_breakdown_enabled(mode == 'enabled')
    return sim, x, axis, predicted


def cycle(sim, x, axis, mode, history, mask=MASK, thresholds=THRESHOLDS, sigma=SIGMA):
    states, errors = [], []
    for voltage in [.004, .02, .001, -.06, .004]:
        state, history, error = check_step(sim, x, axis, voltage, history, mode == 'enabled',
                                            mask, thresholds, sigma)
        states.append(state); errors.append(error)
    if mode == 'disabled':
        # Stored parameters/history must survive while disabled. Re-enable
        # explicitly to expose a hidden mutation, then restore the switch.
        sim.set_breakdown_enabled(True)
        for voltage in [.001, -.06, .004]:
            state, history, error = check_step(sim, x, axis, voltage, history, True,
                                                mask, thresholds, sigma)
            states.append(state); errors.append(error)
        sim.set_breakdown_enabled(False)
    return states, history, max(errors)


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='breakdown_finite_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_BREAKDOWN_FINITE_ORACLE')
    if path: assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('history', HISTORIES)
def test_irreversible_masked_breakdown_and_filament_current_match_independent_law(route, mode, history):
    sim, x, axis, predicted = fixture(route, mode, history)
    states, predicted, error = cycle(sim, x, axis, mode, predicted)
    assert predicted.sum() == 5 and not predicted[0]  # zero threshold disables detection
    reference(f'physical/{route}/{mode}/{history}', states)
    print(json.dumps(dict(test='breakdown_finite_physics', route=route, mode=mode,
                          history=history, max_error_A_m2=error)))


@pytest.mark.parametrize('field', ['thresholds', 'conductivity'])
def test_finite_signed_zero_and_extreme_acceptance_then_restore(field):
    actual, x, axis, ha = fixture('gummel', 'enabled', 'broken')
    control, _, _, hb = fixture('gummel', 'enabled', 'broken')
    maximum, minimum = float(np.finfo(float).max), float(np.nextafter(0., 1.))
    for value in [-maximum, maximum, -minimum, minimum, -0., 0.]:
        values = np.full(SIZE, value) if field == 'thresholds' else RETRY_THRESHOLDS.copy()
        sigma = value if field == 'conductivity' else RETRY_SIGMA
        actual.set_breakdown_params(RETRY_MASK.copy(), values, sigma)
        # Compatibility of finite inputs only; restore physical parameters
        # before solving with any extreme or signed value.
        actual.set_breakdown_params(MASK.copy(), THRESHOLDS.copy(), SIGMA)
    a, _, _ = cycle(actual, x, axis, 'enabled', ha)
    b, _, _ = cycle(control, x, axis, 'enabled', hb)
    assert digest(a) == digest(b)
    reference(f'finite/{field}', a)


def retry(sim):
    sim.set_breakdown_params(RETRY_MASK.copy(), RETRY_THRESHOLDS.copy(), RETRY_SIGMA)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
def test_valid_reconfiguration_preserves_irreversible_history_and_enable_switch(route, mode):
    actual, x, axis, ha = fixture(route, mode, 'broken')
    control, _, _, hb = fixture(route, mode, 'broken')
    before, ha, _ = cycle(actual, x, axis, mode, ha)
    same, hb, _ = cycle(control, x, axis, mode, hb)
    assert digest(before) == digest(same)
    retry(actual); retry(control)
    after, _, _ = cycle(actual, x, axis, mode, ha, RETRY_MASK, RETRY_THRESHOLDS, RETRY_SIGMA)
    same, _, _ = cycle(control, x, axis, mode, hb, RETRY_MASK, RETRY_THRESHOLDS, RETRY_SIGMA)
    assert digest(after) == digest(same) and digest(after) != digest(before)
    reference(f'control/{route}/{mode}', [before, after])


def child(route, mode, history, field, bad):
    actual, x, axis, ha = fixture(route, mode, history)
    control, _, _, hb = fixture(route, mode, history)
    saved = actual.breakdown_state().copy()
    values, sigma = RETRY_THRESHOLDS.copy(), RETRY_SIGMA
    if field < 3: values[POSITIONS[field]] = BAD[bad]
    else: sigma = BAD[bad]
    message = 'E_bd values must be finite' if field < 3 else 'sigma_bd must be finite'
    with pytest.raises(ValueError, match='^'+message+'$'):
        actual.set_breakdown_params(RETRY_MASK.copy(), values, sigma)
    np.testing.assert_array_equal(actual.breakdown_state(), saved)
    before, ha, _ = cycle(actual, x, axis, mode, ha)
    same, hb, _ = cycle(control, x, axis, mode, hb)
    assert digest(before) == digest(same)
    retry(actual); retry(control)
    after, _, _ = cycle(actual, x, axis, mode, ha, RETRY_MASK, RETRY_THRESHOLDS, RETRY_SIGMA)
    same, _, _ = cycle(control, x, axis, mode, hb, RETRY_MASK, RETRY_THRESHOLDS, RETRY_SIGMA)
    assert digest(after) == digest(same) and digest(after) != digest(before)
    return dict(route=route, mode=mode, history=history, field=field, bad=bad,
                sha256=digest([before, after]))


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('history', HISTORIES)
@pytest.mark.parametrize('field', range(len(FIELDS)), ids=FIELDS)
@pytest.mark.parametrize('bad', BAD)
def test_nonfinite_rejection_preserves_parameters_history_mask_and_switch(route, mode, history, field, bad):
    args = route, mode, history, field, bad
    code = ("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
            "from test_breakdown_parameter_finiteness import child\n"
            f"print(json.dumps(dict(test='breakdown_finite_atomic',**child(*{args!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                       capture_output=True, text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='breakdown_finite_child_exit', route=route, mode=mode,
                         history=history, field=field, bad=bad, returncode=r.returncode)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = [line for line in r.stdout.splitlines() if line.startswith('{"test": "breakdown_finite_atomic"')]
    assert len(rows) == 1
    print(rows[0])
