"""Isolate native setter exceptions and preserve valid solver/flux results."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_trap_parameter_guard import ROUTES, SIZE, dielectric
from test_zero_auger_transient import KINDS, configured, digest, snapshot


MODES = ['symmetric', 'asymmetric', 'disabled']
BAD_SEEDS = [f'{field}_{length}' for field in ['phi', 'n', 'p']
             for length in [0, 2, 4]] + ['all_empty']
LEAK_MASK = np.array([0, 0, 1, 0, 1, 0, 0, 0, 0], dtype=np.int8)
LEAK_PARAMS = (2e-7, 30., .4, 4e-12, 8e4, .5, 1e3, 1e-5)
POLAR_PARAMS = (7e-12, 1.3e5, 2e-12, 2.1e5)


def initial(kind, axis, budget):
    sim = configured(kind, axis, axis % 2 == 1, budget)
    if kind == 'empty_blocked':
        values = [np.array([0., .004, .01]), np.zeros(3), np.zeros(3)]
    else:
        phi = np.array([0., -.004, -.01]) if kind in ['split_lk', 'coupled_lk', 'nls'] else np.array([0., -.003, 0.])
        values = [phi, 1e16*np.array([1., 1.4, 1.]), 1e16*np.array([1., 1.2, 1.])]
    sim.set_initial_guess(*values)
    return sim, values


def leakage(route, axis, polarity, mode):
    sim, x = dielectric(route, axis)
    sim.set_dirichlet_potential({0: 0., SIZE-1: polarity*.02})
    sim.set_leakage(LEAK_MASK.copy(), *LEAK_PARAMS)
    if mode != 'symmetric':
        sim.set_leakage_fn_polarity(*POLAR_PARAMS)
    if mode == 'disabled':
        sim.set_leakage_enabled(False)
    return sim, x


def check_current(state, x, axis, polarity, mode):
    assert state['converged']
    field = -polarity*.02/(x[-1]-x[0])
    magnitude = abs(field)
    cpf, bpf, phit, cfn, bfn, phib, floor, cap = LEAK_PARAMS
    if mode != 'symmetric':
        cfn, bfn = POLAR_PARAMS[:2] if field >= 0 else POLAR_PARAMS[2:]
    sigma = cpf*np.exp(-bpf*np.sqrt(phit/magnitude))
    sigma += cfn*magnitude*np.exp(-bfn*phib**1.5/magnitude)
    expected = np.zeros(SIZE)
    active = LEAK_MASK[:-1].astype(bool) | LEAK_MASK[1:].astype(bool)
    if mode != 'disabled':
        expected[:-1] = active*min(sigma, cap)*field
        assert np.max(abs(expected)) > .01
    actual = state['Jleak_'+'xyz'[axis]]
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-15)
    for other in set(range(3))-{axis}:
        assert np.all(state['Jleak_'+'xyz'[other]] == 0.)
    return float(np.max(abs(actual-expected)))


def reference(kind, key, value):
    h = digest(value)
    print(json.dumps(dict(test='setter_reference', kind=kind, key=key, sha256=h)))
    path = os.environ.get('TCAD_SETTER_ORACLE')
    if path:
        assert json.loads(Path(path).read_text(encoding='utf8'))[kind+'/'+key] == h
    return h


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('budget', [0, 80])
def test_valid_initial_guess_clear_restore_keeps_every_export(kind, axis, budget):
    sim, values = initial(kind, axis, budget)
    expected = snapshot(sim)
    fresh, _ = initial(kind, axis, budget)
    fresh.clear_initial_guess()
    fresh.set_initial_guess(*values)
    actual = snapshot(fresh)
    assert digest(actual) == digest(expected)
    if budget:
        assert len(actual[0]) == 4 and all(s['valid'] for s in actual[0])
    reference('initial', f'{kind}/{axis}/{budget}', expected)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('polarity', [-1, 1])
@pytest.mark.parametrize('mode', MODES)
def test_valid_leakage_matches_independent_pf_fn_law(route, axis, polarity, mode):
    sim, x = leakage(route, axis, polarity, mode)
    state = sim.solve()
    error = check_current(state, x, axis, polarity, mode)
    reference('leakage', f'{route}/{axis}/{polarity}/{mode}', state)
    print(json.dumps(dict(test='setter_flux', route=route, axis=axis,
                         polarity=polarity, mode=mode, max_error_A_m2=error)))


def child_initial(axis, bad):
    actual, _ = initial('classical', axis, 0)
    fresh, _ = initial('classical', axis, 0)
    request = [np.full(3, -.008), np.full(3, 2e16), np.full(3, 3e16)]
    if bad == 'all_empty':
        request = [np.empty(0) for _ in range(3)]
    else:
        field, length = bad.split('_')
        request[['phi', 'n', 'p'].index(field)] = np.zeros(int(length))
    with pytest.raises(ValueError, match='^initial guess size mismatch$'):
        actual.set_initial_guess(*request)
    a, b = snapshot(actual), snapshot(fresh)
    assert digest(a) == digest(b)
    assert a[0][0]['n'][1] == 1.4e16 and a[0][0]['p'][1] == 1.2e16
    # A subsequent valid request must still be usable after the rejected one.
    recovered, values = initial('classical', axis, 80)
    actual.set_initial_guess(*values)
    actual.set_gummel_max_iter(80)
    retry, expected = snapshot(actual), snapshot(recovered)
    assert all(s['valid'] for s in retry[0]) and digest(retry) == digest(expected)
    return dict(requests=1, sha256=digest([a, retry]))


def child_leakage(route, axis, polarity, mode):
    results = []
    for length in [0, SIZE-1, SIZE+1]:
        actual, x = leakage(route, axis, polarity, mode)
        fresh, _ = leakage(route, axis, polarity, mode)
        with pytest.raises(ValueError, match='^leakage mask size mismatch$'):
            actual.set_leakage(np.ones(length, dtype=np.int8), .09, 80., .7,
                               9e-5, 1e5, .9, 9e5, 9e-4)
        a, b = actual.solve(), fresh.solve()
        check_current(a, x, axis, polarity, mode)
        assert digest(a) == digest(b)
        if mode == 'disabled':
            # Re-enable to expose preserved parameters as well as the switch.
            actual.set_leakage_enabled(True)
            fresh.set_leakage_enabled(True)
            a, b = actual.solve(), fresh.solve()
            check_current(a, x, axis, polarity, 'asymmetric')
            assert digest(a) == digest(b)
        results.append(a)
    return dict(requests=3, sha256=digest(results))


def isolated(kind, arguments):
    code = ("import json, resource; resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "from test_initial_leakage_exceptions import child_initial, child_leakage\n"
            f"value = {{'initial': child_initial, 'leakage': child_leakage}}[{kind!r}](*{arguments!r})\n"
            "print(json.dumps(dict(test='setter_child_result', **value)))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                            capture_output=True, text=True, encoding='utf8', timeout=45)
    print(json.dumps(dict(test='setter_child_exit', kind=kind, key=arguments,
                         returncode=result.returncode)))
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    rows = [json.loads(line[line.index('{"test": "setter_child_result"'):])
            for line in result.stdout.splitlines() if '{"test": "setter_child_result"' in line]
    assert len(rows) == 1
    print(json.dumps(dict(test='setter_atomic', kind=kind, key=arguments, **{k:v for k,v in rows[0].items() if k != 'test'})))


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('bad', BAD_SEEDS)
def test_invalid_initial_guess_raises_and_preserves_seed(axis, bad):
    isolated('initial', [axis, bad])


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('polarity', [-1, 1])
@pytest.mark.parametrize('mode', MODES)
def test_invalid_leakage_mask_raises_and_preserves_model(route, axis, polarity, mode):
    isolated('leakage', [route, axis, polarity, mode])
