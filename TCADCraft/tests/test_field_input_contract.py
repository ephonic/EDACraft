"""Reject malformed persistent fields before mutating native solver inputs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_transient_selfconsistent import central_cell, reference_step
from test_zero_auger_transient import configured, digest, snapshot


ROUTES = ['gummel', 'newton', 'hybrid']
BAD = [('doping', 0, length) for length in [0, 2, 4]]
BAD += [('mobility', field, length) for field in [0, 1] for length in [0, 2, 4]]


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='field_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_FIELD_ORACLE')
    if path:assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


@pytest.mark.parametrize('polarity', [-1, 0, 1])
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
def test_valid_signed_doping_matches_independent_poisson_sg_be(polarity, axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True, polarity)
    sim.set_quantum_enabled(False)
    sim.set_nonlinear_history_enabled(True)
    sim.set_doping(np.array([0., polarity*.15e16, 0.]))
    result = snapshot(sim)
    assert len(result[0]) == 4
    max_error = 0.
    for state in result[0]:
        assert state['valid']
        phi, nn, pp = reference_step(nn, pp, state['dt_s'], x, 1e16, polarity*.15)
        np.testing.assert_allclose(state['phi'], [0., phi, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(state['n']/1e16, [1., nn, 1.], rtol=2e-8)
        np.testing.assert_allclose(state['p']/1e16, [1., pp, 1.], rtol=2e-8)
        max_error = max(max_error, abs(float(state['phi'][1])-phi), abs(float(state['n'][1])/1e16-nn), abs(float(state['p'][1])/1e16-pp))
    reference(f'doping/{polarity}/{axis}/{log_space}', result)
    print(json.dumps(dict(test='field_physics', polarity=polarity, axis=axis, log_space=log_space, max_normalized_error=max_error)))


@pytest.mark.parametrize('kind', ['classical', 'empty_blocked'])
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('budget', [0, 80])
def test_valid_positive_and_zero_mobility_preserves_every_export(kind, axis, log_space, budget):
    actual, expected = [configured(kind, axis, log_space, budget) for _ in range(2)]
    values = [np.full(3, .1), np.full(3, .05)] if kind == 'classical' else [np.zeros(3), np.zeros(3)]
    actual.set_mobility(np.full(3, .3), np.full(3, .2))
    actual.set_mobility(*values)
    a, b = snapshot(actual), snapshot(expected)
    assert digest(a) == digest(b)
    assert a[0][0]['valid']
    if budget:assert len(a[0]) == 4 and all(s['valid'] for s in a[0])
    elif kind == 'classical':assert not a[0][-1]['valid'] and a[0][-1]['time_s'] == 0.
    if kind == 'classical' and budget:
        changed = configured(kind, axis, log_space, budget)
        changed.set_mobility(np.full(3, .13), np.full(3, .07))
        assert digest(snapshot(changed)) != digest(b)
    reference(f'mobility/{kind}/{axis}/{log_space}/{budget}', a)


def fixture(route):
    axis = ROUTES.index(route)
    sim = configured('classical', axis, axis % 2 == 1)
    sim.set_use_newton(route != 'gummel')
    sim.set_newton_primary(route == 'newton')
    return sim


def observe(sim):
    transient = snapshot(sim)
    assert len(transient[0]) == 4 and all(s['valid'] for s in transient[0])
    steady = sim.solve()
    assert steady['converged']
    return transient, steady


def child(route, kind, field, length):
    actual, expected = fixture(route), fixture(route)
    if kind == 'doping':
        with pytest.raises(ValueError, match='^Doping size mismatch$'):
            actual.set_doping(np.full(length, -3e16))
    else:
        request = [np.full(3, .3), np.full(3, .2)]
        request[field] = np.full(length, .4)
        # On the baseline this assertion fails immediately after acceptance;
        # never solve using the malformed arrays that it has just stored.
        with pytest.raises(ValueError, match='^mobility size mismatch$'):
            actual.set_mobility(*request)
    a, b = observe(actual), observe(expected)
    assert digest(a) == digest(b)
    for sim in [actual, expected]:
        sim.set_doping(np.array([0., -.3e16, 0.]))
        sim.set_mobility(np.full(3, .13), np.full(3, .07))
    retry, control = observe(actual), observe(expected)
    assert digest(retry) == digest(control) and digest(retry) != digest(a)
    return dict(route=route, kind=kind, field=field, length=length, requests=1, sha256=digest([a, retry]))


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('kind,field,length', BAD)
def test_invalid_field_raises_preserves_both_solvers_and_allows_retry(route, kind, field, length):
    code = ("import json, resource; resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "from test_field_input_contract import child\n"
            f"print(json.dumps(dict(test='field_atomic', **child({route!r}, {kind!r}, {field!r}, {length!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    result = subprocess.run([sys.executable, '-B', '-c', code], env=env, capture_output=True,
                            text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='field_child_exit', route=route, kind=kind, field=field, length=length, returncode=result.returncode)))
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    rows = [line for line in result.stdout.splitlines() if line.startswith('{"test": "field_atomic"')]
    assert len(rows) == 1
    print(rows[0])
