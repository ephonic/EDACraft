"""Source/material arrays: reject nonfinite requests before persistent writes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_field_input_contract import ROUTES, fixture as route_fixture, observe
from test_native_setter_exceptions import arguments
from test_transient_selfconsistent import EPS, QE, VT, bernoulli, central_cell
from test_zero_auger_transient import configured, digest, snapshot


NAMES = ['optical_generation', 'recombination', 'effective_dos', 'bandgap']
FIELDS = [(name, field) for name in NAMES for field in
          (range(2) if name in ['recombination', 'effective_dos'] else range(1))]
BAD = {'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf}
MESSAGES = {'optical_generation': 'optical generation values must be finite',
            'recombination': 'recombination lifetime values must be finite',
            'effective_dos': 'effective DOS values must be finite',
            'bandgap': 'bandgap values must be finite'}


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='source_finite_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_SOURCE_FINITE_ORACLE')
    if path:
        assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


def apply(sim, alternate=False):
    for name in NAMES:
        getattr(sim, 'set_'+name)(*arguments(name, alternate))


def fixture(route):
    sim = route_fixture(route)
    apply(sim)
    return sim


def reference_step(nn, pp, dt, x, generation, tn, tp, nc, nv, eg):
    """Independent 3-unknown finite-volume Poisson/SG/BE/SRH equations.

    Finite-difference Jacobian in float64; no native residual or Jacobian is
    called. The previous reference root, never the native state, is propagated.
    """
    left, right = np.diff(x)
    rate = (1/left + 1/right)/((left+right)/2)
    kappa = QE*1e16/(EPS*rate)
    if not dt:
        return kappa*(pp-nn+.15), nn, pp
    an, ap = dt*.1*VT*rate, dt*.05*VT*rate
    ni = np.sqrt(nc/1e16)*np.sqrt(nv/1e16)*np.exp(-eg/(2*8.617333262e-5*300.))

    def residual(y):
        u, n, p = y
        srh = (n*p-ni*ni)/(tp*(n+ni)+tn*(p+ni))
        source = dt*(srh-generation/1e16)
        return np.array([u-kappa/VT*(p-n+.15),
                         n-nn+an*(n*bernoulli(u)-bernoulli(-u))+source,
                         p-pp+ap*(p*bernoulli(-u)-bernoulli(u))+source])

    y = np.array([kappa/VT*(pp-nn+.15), nn, pp])
    for _ in range(40):
        r = residual(y)
        if np.max(abs(r)) < 2e-14:
            break
        jac = np.empty((3, 3))
        for j in range(3):
            h = 1e-5*max(1., abs(y[j]))
            delta = np.zeros(3); delta[j] = h
            jac[:, j] = (residual(y+delta)-residual(y-delta))/(2*h)
        step = np.linalg.solve(jac, -r)
        for power in range(30):
            trial = y + 2.**(-power)*step
            if min(trial[1:]) > 0 and np.max(abs(residual(trial))) < np.max(abs(r)):
                y = trial
                break
        else:
            raise AssertionError('independent reference line search failed')
    assert np.max(abs(residual(y))) < 2e-13
    return y[0]*VT, y[1], y[2]


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
def test_valid_sources_match_independent_poisson_sg_be_srh(name, axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True)
    sim.set_quantum_enabled(False); sim.set_nonlinear_history_enabled(True)
    apply(sim)
    getattr(sim, 'set_'+name)(*arguments(name, True))
    generation = float(arguments('optical_generation', name == 'optical_generation')[0][1])
    tn, tp = [float(a[1]) for a in arguments('recombination', name == 'recombination')]
    nc, nv = [float(a[1]) for a in arguments('effective_dos', name == 'effective_dos')]
    eg = float(arguments('bandgap', name == 'bandgap')[0][1])
    result = snapshot(sim)
    assert len(result[0]) == 4 and all(s['valid'] for s in result[0])
    phi_error = carrier_error = 0.
    for state in result[0]:
        phi, nn, pp = reference_step(nn, pp, state['dt_s'], x, generation, tn, tp, nc, nv, eg)
        np.testing.assert_allclose(state['phi'], [0., phi, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(state['n']/1e16, [1., nn, 1.], rtol=2e-8)
        np.testing.assert_allclose(state['p']/1e16, [1., pp, 1.], rtol=2e-8)
        phi_error = max(phi_error, abs(float(state['phi'][1])-phi))
        carrier_error = max(carrier_error, abs(float(state['n'][1])/1e16-nn), abs(float(state['p'][1])/1e16-pp))
    key = f'physical/{name}/{axis}/{log_space}'
    reference(key, result)
    print(json.dumps(dict(test='source_finite_physics', key=key,
                         max_phi_error_V=phi_error, max_scaled_carrier_error=carrier_error)))


@pytest.mark.parametrize('name,field', FIELDS)
def test_finite_extreme_signed_and_zero_setter_acceptance_then_restore(name, field):
    actual, expected = [configured('classical', 0, True) for _ in range(2)]
    apply(actual); apply(expected)
    maximum = float(np.finfo(float).max)
    minimum = float(np.nextafter(0., 1.))
    for value in [-maximum, maximum, -minimum, minimum, -0., 0.]:
        values = arguments(name)
        values[field] = np.full(3, value)
        getattr(actual, 'set_'+name)(*values)
        # Compatibility of setters only. Restore normal, physical inputs
        # before any solve; this does not qualify extreme or negative solves.
        apply(actual)
    a, b = snapshot(actual), snapshot(expected)
    assert all(s['valid'] for s in a[0]) and digest(a) == digest(b)
    reference(f'finite/{name}/{field}', a)


@pytest.mark.parametrize('route', ROUTES)
def test_valid_retry_fixture_observable(route):
    actual, expected = fixture(route), fixture(route)
    before, control = observe(actual), observe(expected)
    assert digest(before) == digest(control)
    apply(actual, True); apply(expected, True)
    after, control = observe(actual), observe(expected)
    assert digest(after) == digest(control) and digest(after) != digest(before)
    reference(f'control/{route}', [before, after])


def child(route, name, field, bad, position):
    actual, expected = fixture(route), fixture(route)
    values = arguments(name, True)
    values[field][position] = BAD[bad]
    with pytest.raises(ValueError, match='^'+MESSAGES[name]+'$'):
        getattr(actual, 'set_'+name)(*values)
    before, control = observe(actual), observe(expected)
    assert digest(before) == digest(control)
    apply(actual, True); apply(expected, True)
    after, control = observe(actual), observe(expected)
    assert digest(after) == digest(control) and digest(after) != digest(before)
    return dict(route=route, name=name, field=field, bad=bad, position=position,
                sha256=digest([before, after]))


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('name,field', FIELDS)
@pytest.mark.parametrize('bad', BAD)
@pytest.mark.parametrize('position', range(3))
def test_nonfinite_request_is_atomic_and_valid_retry_succeeds(route, name, field, bad, position):
    args = route, name, field, bad, position
    code = ("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
            "from test_source_material_finiteness import child\n"
            f"print(json.dumps(dict(test='source_finite_atomic',**child(*{args!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                       capture_output=True, text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='source_finite_child_exit', route=route, name=name,
                         field=field, bad=bad, position=position, returncode=r.returncode)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = [line for line in r.stdout.splitlines() if line.startswith('{"test": "source_finite_atomic"')]
    assert len(rows) == 1
    print(rows[0])
