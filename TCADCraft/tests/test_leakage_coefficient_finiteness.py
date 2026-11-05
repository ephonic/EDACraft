"""Leakage rejection preserves coefficients, masks, switches and FN polarity."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_initial_leakage_exceptions import LEAK_MASK, LEAK_PARAMS, POLAR_PARAMS
from test_trap_parameter_guard import ROUTES, SIZE, dielectric
from test_zero_auger_transient import digest


FIELDS = ['C_pf', 'B_pf', 'phi_t', 'C_fn', 'B_fn', 'phi_b', 'E_floor', 'sigma_cap']
MODES = ['symmetric', 'asymmetric', 'disabled']
VARIANTS = ['mixed', 'pf_only', 'fn_only', 'floor', 'capped', 'uncapped']
BAD = {'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf}
RETRY_MASK = np.array([0, 1, 0, 0, 0, 0, 1, 0, 0], dtype=np.int8)
RETRY_PARAMS = (7e-7, 60., .8, 9e-12, 9e4, .6, 2e3, 2e-5)


def parameters(variant):
    values = list(LEAK_PARAMS)
    if variant == 'pf_only': values[3] = 0.
    elif variant == 'fn_only': values[0] = 0.
    elif variant == 'floor': values[6] = 1e6
    elif variant == 'capped': values[7] = 1e-8
    elif variant == 'uncapped': values[7] = 0.
    else: assert variant == 'mixed'
    return values


def polarity_parameters(variant):
    if variant == 'pf_only':
        return 0., POLAR_PARAMS[1], 0., POLAR_PARAMS[3]
    return POLAR_PARAMS


def fixture(route, mode, variant='mixed'):
    axis = ROUTES.index(route)
    sim, x = dielectric(route, axis, stretched=True)
    sim.set_leakage(LEAK_MASK.copy(), *parameters(variant))
    if mode != 'symmetric': sim.set_leakage_fn_polarity(*polarity_parameters(variant))
    if mode == 'disabled': sim.set_leakage_enabled(False)
    return sim, x, axis


def check_current(state, x, axis, polarity, mode, values, mask, polar=POLAR_PARAMS):
    """Analytic PF/FN law on the constant field of a neutral dielectric.

    Compute the field from the imposed voltage and device length, without
    reading the native field, leakage coefficients or implementation helpers.
    """
    assert state['converged']
    field = -polarity*.02/(x[-1]-x[0])
    magnitude = abs(field)
    cpf, bpf, phit, cfn, bfn, phib, floor, cap = values
    if mode != 'symmetric':
        cfn, bfn = polar[:2] if field >= 0 else polar[2:]
    expected = np.zeros(SIZE)
    if mode != 'disabled' and magnitude > floor:
        sigma = cpf*np.exp(-bpf*np.sqrt(phit/magnitude))
        sigma += cfn*magnitude*np.exp(-bfn*phib**1.5/magnitude)
        if cap > 0: sigma = min(sigma, cap)
        active = mask[:-1].astype(bool) | mask[1:].astype(bool)
        expected[:-1] = active*sigma*field
    actual = state['Jleak_'+'xyz'[axis]]
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-15)
    np.testing.assert_allclose(state['phi'], polarity*.02*(x-x[0])/(x[-1]-x[0]), rtol=1e-9, atol=1e-14)
    for other in set(range(3))-{axis}:
        assert np.all(state['Jleak_'+'xyz'[other]] == 0.)
    return float(np.max(abs(actual-expected)))


def cycle(sim, x, axis, mode, values=LEAK_PARAMS, mask=LEAK_MASK):
    states = []
    for polarity in [-1, 1]:
        sim.set_dirichlet_potential({0: 0., SIZE-1: polarity*.02})
        state = sim.solve()
        check_current(state, x, axis, polarity, mode, values, mask)
        states.append(state)
    if mode == 'disabled':
        # Expose stored coefficients and the directional switch as well as
        # the disabled flag. Return with the original disabled flag restored.
        sim.set_leakage_enabled(True)
        states += cycle(sim, x, axis, 'asymmetric', values, mask)
        sim.set_leakage_enabled(False)
    return states


def retry(sim):
    # A successful legacy request intentionally resets FN polarity and
    # enables leakage. The rejected request must do neither of these.
    sim.set_leakage(RETRY_MASK.copy(), *RETRY_PARAMS)


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='leakage_finite_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_LEAKAGE_FINITE_ORACLE')
    if path:
        assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('variant', VARIANTS)
@pytest.mark.parametrize('polarity', [-1, 1])
def test_valid_pf_fn_floor_cap_and_switches_match_analytic_law(route, mode, variant, polarity):
    sim, x, axis = fixture(route, mode, variant)
    sim.set_dirichlet_potential({0: 0., SIZE-1: polarity*.02})
    state = sim.solve()
    error = check_current(state, x, axis, polarity, mode, parameters(variant), LEAK_MASK,
                          polarity_parameters(variant))
    if mode == 'disabled' or variant == 'floor':
        assert np.all(state['Jleak_'+'xyz'[axis]] == 0.)
    else:
        assert np.max(abs(state['Jleak_'+'xyz'[axis]])) > .001
    key = f'physical/{route}/{mode}/{variant}/{polarity}'
    reference(key, state)
    print(json.dumps(dict(test='leakage_finite_physics', key=key, max_error_A_m2=error)))


@pytest.mark.parametrize('field', range(len(FIELDS)), ids=FIELDS)
def test_finite_signed_zero_and_extreme_setter_acceptance_then_restore(field):
    actual, x, axis = fixture('gummel', 'asymmetric')
    expected, _, _ = fixture('gummel', 'asymmetric')
    maximum, minimum = float(np.finfo(float).max), float(np.nextafter(0., 1.))
    for value in [-maximum, maximum, -minimum, minimum, -0., 0.]:
        values = list(RETRY_PARAMS); values[field] = value
        actual.set_leakage(RETRY_MASK.copy(), *values)
        # Setter compatibility only: restore physical finite inputs and
        # FN polarity before solving, never solve with extreme/negative ones.
        actual.set_leakage(LEAK_MASK.copy(), *LEAK_PARAMS)
        actual.set_leakage_fn_polarity(*POLAR_PARAMS)
    a = cycle(actual, x, axis, 'asymmetric')
    b = cycle(expected, x, axis, 'asymmetric')
    assert digest(a) == digest(b)
    reference(f'finite/{FIELDS[field]}', a)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
def test_valid_retry_changes_mask_coefficients_and_resets_flags(route, mode):
    actual, x, axis = fixture(route, mode)
    expected, _, _ = fixture(route, mode)
    before, control = cycle(actual, x, axis, mode), cycle(expected, x, axis, mode)
    assert digest(before) == digest(control)
    retry(actual); retry(expected)
    after = cycle(actual, x, axis, 'symmetric', RETRY_PARAMS, RETRY_MASK)
    control = cycle(expected, x, axis, 'symmetric', RETRY_PARAMS, RETRY_MASK)
    assert digest(after) == digest(control) and digest(after) != digest(before)
    reference(f'control/{route}/{mode}', [before, after])


def child(route, mode, field, bad):
    actual, x, axis = fixture(route, mode)
    expected, _, _ = fixture(route, mode)
    values = list(RETRY_PARAMS); values[field] = BAD[bad]
    with pytest.raises(ValueError, match='^leakage parameters must be finite$'):
        actual.set_leakage(RETRY_MASK.copy(), *values)
    before, control = cycle(actual, x, axis, mode), cycle(expected, x, axis, mode)
    assert digest(before) == digest(control)
    retry(actual); retry(expected)
    after = cycle(actual, x, axis, 'symmetric', RETRY_PARAMS, RETRY_MASK)
    control = cycle(expected, x, axis, 'symmetric', RETRY_PARAMS, RETRY_MASK)
    assert digest(after) == digest(control) and digest(after) != digest(before)
    return dict(route=route, mode=mode, field=field, bad=bad, sha256=digest([before, after]))


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('field', range(len(FIELDS)), ids=FIELDS)
@pytest.mark.parametrize('bad', BAD)
def test_nonfinite_request_preserves_mask_parameters_enable_and_fn_polarity(route, mode, field, bad):
    args = route, mode, field, bad
    code = ("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
            "from test_leakage_coefficient_finiteness import child\n"
            f"print(json.dumps(dict(test='leakage_finite_atomic',**child(*{args!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                       capture_output=True, text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='leakage_finite_child_exit', route=route, mode=mode,
                         field=field, bad=bad, returncode=r.returncode)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = [line for line in r.stdout.splitlines() if line.startswith('{"test": "leakage_finite_atomic"')]
    assert len(rows) == 1
    print(rows[0])
