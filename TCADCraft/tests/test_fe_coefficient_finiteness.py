"""FE coefficient rejection, owned history and independent uniform LK dynamics."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_transient_displacement import film, EPS0
from test_zero_auger_transient import digest, snapshot

MODES = ['split', 'centered', 'material', 'disabled']
FIELDS = ['alpha', 'beta', 'builtin']
BAD = {'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf}
SIZE = 9
ALPHA, BETA, BUILTIN = -1e8, 1e12, 2e5
RETRY_ALPHA, RETRY_BETA, RETRY_BUILTIN = 2e8, 3e12, -1e5
MASK = np.array([0, 0, 1, 1, 1, 1, 1, 0, 0], dtype=np.int8)
RETRY_MASK = np.array([0, 1, 1, 0, 1, 0, 1, 1, 0], dtype=np.int8)


def disabled_mode(sim, enabled):
    sim.set_ferroelectric_enabled(enabled)
    sim.set_ferroelectric_gamma(.1 if enabled else 0.)
    sim.set_transient_lk_coupled(enabled)
    sim.set_transient_lk_material_field(enabled)


def fixture(axis, mode, history='pristine', uniform=False, polar_axis=None,
            alpha=ALPHA, beta=BETA, builtin=BUILTIN):
    sim, x, eps, _, area = film(axis, 0, False, False)
    sim.set_quantum_enabled(False)
    sim.set_ferroelectric_params(np.ones(SIZE, dtype=np.int8) if uniform else MASK.copy(), alpha, beta)
    sim.set_ferroelectric_builtin_field(builtin)
    sim.set_ferroelectric_polar_axis(axis if polar_axis is None else polar_axis)
    sim.set_transient_lk_coupled(mode != 'split')
    sim.set_transient_lk_material_field(mode in ['material', 'disabled'])
    if history == 'seeded':
        p = np.zeros((SIZE, 3)); p[MASK != 0, axis] = np.linspace(-2e-4, 3e-4, 5)
        sim.set_ferroelectric_history(p)
    if mode == 'disabled': disabled_mode(sim, False)
    return sim, x, area


def configuration(sim):
    return sim.get_ferroelectric_mask(), sim.get_ferroelectric_lk_parameters(), sim.get_ferroelectric_history()


def observe(sim, mode):
    states, attempts = snapshot(sim)
    assert len(states) == 4 and all(s['valid'] for s in states)
    result = [states, attempts, configuration(sim)]
    if mode == 'disabled':
        disabled_mode(sim, True)
        states, attempts = snapshot(sim)
        assert len(states) == 4 and all(s['valid'] for s in states)
        result += [states, attempts, configuration(sim)]
        disabled_mode(sim, False)
    return result


def retry(sim):
    sim.set_ferroelectric_params(RETRY_MASK.copy(), RETRY_ALPHA, RETRY_BETA)
    sim.set_ferroelectric_builtin_field(RETRY_BUILTIN)


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='fe_finite_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_FE_FINITE_ORACLE')
    if path: assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('mode', MODES[:3])
@pytest.mark.parametrize('alpha,beta', [(1e8, 1e12), (-1e8, 3e12)])
@pytest.mark.parametrize('builtin', [-2e5, 0., 2e5])
@pytest.mark.parametrize('cross_axis', [False, True])
def test_uniform_vector_lk_matches_independent_backward_euler_cubic(axis, mode, alpha, beta, builtin, cross_axis):
    polar_axis = (axis+1)%3 if cross_axis else axis
    sim, x, area = fixture(axis, mode, uniform=True, polar_axis=polar_axis,
                           alpha=alpha, beta=beta, builtin=builtin)
    states, attempts = snapshot(sim)
    assert len(states) == 4 and all(s['valid'] for s in states)
    field = np.zeros(3); field[axis] = .01/(x[-1]-x[0]); field[polar_axis] -= builtin
    expected = np.zeros(3); error = 0.
    for state in states:
        if state['dt_s']:
            rate = .1/state['dt_s']
            # Every cubic is strictly increasing: alpha+gamma/dt > 0.
            assert alpha+rate > 0
            for c in range(3):
                roots = np.roots([beta, 0., alpha+rate, -(rate*expected[c]+field[c])])
                real = [v.real for v in roots if abs(v.imag) < 1e-12]
                assert len(real) == 1
                expected[c] = real[0]
        target = np.tile(expected, (SIZE, 1))
        actual = state['P'].reshape(SIZE, 3)
        np.testing.assert_allclose(actual, target, rtol=1e-9, atol=2e-13)
        np.testing.assert_allclose(state['phi'], -.01*x/x[-1], rtol=1e-10, atol=2e-13)
        d = 20*EPS0*.01/(x[-1]-x[0])+expected[axis]
        np.testing.assert_allclose(state['electrode_charges_C'], area*np.array([d, -d]),
                                   rtol=1e-9, atol=2e-26)
        error = max(error, float(np.max(abs(actual-target))))
    key = f'physical/{axis}/{mode}/{alpha}/{builtin}/{cross_axis}'
    reference(key, [states, attempts, configuration(sim)])
    print(json.dumps(dict(test='fe_finite_physics', key=key, max_p_error_C_m2=error)))


@pytest.mark.parametrize('field', FIELDS)
def test_finite_signed_zero_and_extreme_setter_acceptance_then_restore(field):
    actual, _, _ = fixture(0, 'material', 'seeded')
    control, _, _ = fixture(0, 'material', 'seeded')
    maximum, minimum = float(np.finfo(float).max), float(np.nextafter(0., 1.))
    for value in [-maximum, maximum, -minimum, minimum, -0., 0.]:
        if field == 'builtin': actual.set_ferroelectric_builtin_field(value)
        else:
            actual.set_ferroelectric_params(RETRY_MASK.copy(), value if field == 'alpha' else RETRY_ALPHA,
                                             value if field == 'beta' else RETRY_BETA)
        # Accept finite values as before, then restore a physical setup before
        # any solve. This does not qualify negative beta or extreme materials.
        actual.set_ferroelectric_params(MASK.copy(), ALPHA, BETA)
        actual.set_ferroelectric_builtin_field(BUILTIN)
    a, b = observe(actual, 'material'), observe(control, 'material')
    assert digest(a) == digest(b)
    reference(f'finite/{field}', a)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('mode', MODES)
def test_valid_replacement_changes_coefficients_mask_and_preserves_history(axis, mode):
    actual, _, _ = fixture(axis, mode, 'seeded')
    control, _, _ = fixture(axis, mode, 'seeded')
    before, same = observe(actual, mode), observe(control, mode)
    assert digest(before) == digest(same)
    history = actual.get_ferroelectric_history().copy()
    retry(actual); retry(control)
    np.testing.assert_array_equal(actual.get_ferroelectric_history(), history)
    after, same = observe(actual, mode), observe(control, mode)
    assert digest(after) == digest(same) and digest(after) != digest(before)
    reference(f'control/{axis}/{mode}', [before, after])


def child(axis, mode, history, field, bad):
    actual, _, _ = fixture(axis, mode, history)
    saved = digest(configuration(actual))
    message = 'FE builtin field must be finite' if field == 'builtin' else 'FE alpha and beta must be finite'
    with pytest.raises(ValueError, match='^'+message+'$'):
        if field == 'builtin': actual.set_ferroelectric_builtin_field(BAD[bad])
        else:
            actual.set_ferroelectric_params(RETRY_MASK.copy(), BAD[bad] if field == 'alpha' else RETRY_ALPHA,
                                             BAD[bad] if field == 'beta' else RETRY_BETA)
    assert digest(configuration(actual)) == saved
    control, _, _ = fixture(axis, mode, history)
    before, same = observe(actual, mode), observe(control, mode)
    assert digest(before) == digest(same)
    retained = actual.get_ferroelectric_history().copy()
    retry(actual); retry(control)
    np.testing.assert_array_equal(actual.get_ferroelectric_history(), retained)
    after, same = observe(actual, mode), observe(control, mode)
    assert digest(after) == digest(same) and digest(after) != digest(before)
    return dict(axis=axis, mode=mode, history=history, field=field, bad=bad,
                sha256=digest([before, after]))


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('history', ['pristine', 'seeded'])
@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('bad', BAD)
def test_nonfinite_rejection_preserves_coefficients_mask_history_and_enable(axis, mode, history, field, bad):
    args = axis, mode, history, field, bad
    code = ("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
            "from test_fe_coefficient_finiteness import child\n"
            f"print(json.dumps(dict(test='fe_finite_atomic',**child(*{args!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                       capture_output=True, text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='fe_finite_child_exit', axis=axis, mode=mode,
                         history=history, field=field, bad=bad, returncode=r.returncode)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = [line for line in r.stdout.splitlines() if line.startswith('{"test": "fe_finite_atomic"')]
    assert len(rows) == 1
    print(rows[0])
