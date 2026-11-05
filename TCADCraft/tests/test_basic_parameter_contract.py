"""Physical scales and convergence tolerances must reject invalid scalars."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_field_input_contract import fixture, observe
from test_transient_selfconsistent import EPS, QE, VT, bernoulli, central_cell
from test_zero_auger_transient import configured, digest, snapshot


KB_EV = 8.617333262e-5
VALUES = {'temperature': [77., 300., 600.],
          'thermal_voltage': [.005, .025852, .05],
          'tolerance': [1e-9, 1e-11, 1e-13]}
BAD = {'zero': 0., 'negative_zero': -0., 'negative': -1.,
       'nan': np.nan, 'inf': np.inf, 'ninf': -np.inf}


def reference(key, value):
    h = digest(value)
    print(json.dumps(dict(test='basic_reference', key=key, sha256=h)))
    path = os.environ.get('TCAD_BASIC_ORACLE')
    if path:assert json.loads(Path(path).read_text(encoding='utf8'))[key] == h


def reference_step(nn, pp, dt, x, vt):
    """Scalar Poisson elimination plus backward-Euler SG at arbitrary VT."""
    left, right = np.diff(x)
    rate = (1/left+1/right)/((left+right)/2)
    kappa = QE*1e16/(EPS*rate)
    if not dt:return kappa*(pp-nn+.15), nn, pp
    an, ap = dt*.1*vt*rate, dt*.05*vt*rate
    def carriers(phi):
        u = phi/vt
        return ((nn+an*bernoulli(-u))/(1+an*bernoulli(u)),
                (pp+ap*bernoulli(u))/(1+ap*bernoulli(-u)))
    def residual(phi):
        n, p = carriers(phi)
        return phi-kappa*(p-n+.15)
    lo, hi = -10*vt, 10*vt
    assert residual(lo)<0<residual(hi)
    for _ in range(100):
        mid = (lo+hi)/2
        if residual(mid)<0:lo=mid
        else:hi=mid
    phi = (lo+hi)/2
    n, p = carriers(phi)
    return phi, n, p


VALID = [(name, value) for name, values in VALUES.items() for value in values]


@pytest.mark.parametrize('name,value', VALID)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
def test_positive_parameter_preserves_exports_and_matches_independent_reference(name, value, axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True)
    sim.set_quantum_enabled(False)
    sim.set_nonlinear_history_enabled(True)
    getattr(sim, 'set_'+name)(value)
    result = snapshot(sim)
    assert len(result[0]) == 4
    vt = KB_EV*value if name == 'temperature' else (value if name == 'thermal_voltage' else VT)
    phi_error = carrier_error = 0.
    for state in result[0]:
        assert state['valid']
        phi, nn, pp = reference_step(nn, pp, state['dt_s'], x, vt)
        np.testing.assert_allclose(state['phi'], [0., phi, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(state['n']/1e16, [1., nn, 1.], rtol=2e-8)
        np.testing.assert_allclose(state['p']/1e16, [1., pp, 1.], rtol=2e-8)
        phi_error = max(phi_error, abs(float(state['phi'][1])-phi))
        carrier_error = max(carrier_error, abs(float(state['n'][1])/1e16-nn), abs(float(state['p'][1])/1e16-pp))
    key = f'positive/{name}/{value}/{axis}/{log_space}'
    reference(key, result)
    print(json.dumps(dict(test='basic_physics', key=key, max_phi_error_V=phi_error,
                         max_scaled_carrier_error=carrier_error)))


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('order', ['temperature_last', 'voltage_last'])
def test_temperature_voltage_assignment_order_keeps_existing_coupling(order, axis, log_space):
    a, b = [configured('classical', axis, log_space) for _ in range(2)]
    a.set_temperature(450.)
    b.set_thermal_voltage(.012)
    b.set_temperature(450.)
    if order == 'voltage_last':
        a.set_thermal_voltage(.02)
        b.set_thermal_voltage(.02)
    aa, bb = snapshot(a), snapshot(b)
    assert all(s['valid'] for s in aa[0]) and digest(aa) == digest(bb)
    c = configured('classical', axis, log_space)
    c.set_temperature(450.)
    c.set_thermal_voltage(.013 if order == 'temperature_last' else .03)
    assert digest(snapshot(c)) != digest(aa)
    reference(f'order/{order}/{axis}/{log_space}', aa)


@pytest.mark.parametrize('name', list(VALUES))
def test_positive_float64_extremes_are_accepted_and_normal_settings_restored(name):
    actual, expected = [configured('classical', 0, True) for _ in range(2)]
    for value in [np.nextafter(0., 1.), np.finfo(np.float64).max]:
        getattr(actual, 'set_'+name)(float(value))
        # The setter domain does not promise solver qualification at extremes.
        actual.set_temperature(300.)
        actual.set_thermal_voltage(VT)
        actual.set_tolerance(1e-11)
    a, b = snapshot(actual), snapshot(expected)
    assert all(s['valid'] for s in a[0]) and digest(a) == digest(b)
    reference(f'extremes/{name}', a)


def guarded_fixture(route):
    sim = fixture(route)
    # Nonzero Eg and SRH expose temperature through ni independently of VT.
    sim.set_bandgap(np.full(3, .01))
    sim.set_recombination(np.full(3, 1e-10), np.full(3, 2e-10))
    return sim


def child(route, name, bad):
    actual, expected = guarded_fixture(route), guarded_fixture(route)
    message = {'temperature':'temperature must be finite and positive',
               'thermal_voltage':'thermal voltage must be finite and positive',
               'tolerance':'solver tolerance must be finite and positive'}[name]
    with pytest.raises(ValueError, match='^'+message+'$'):
        getattr(actual, 'set_'+name)(BAD[bad])
    a, b = observe(actual), observe(expected)
    assert digest(a) == digest(b)
    for sim in [actual, expected]:
        sim.set_temperature(450.)
        sim.set_thermal_voltage(.03)
        sim.set_tolerance(1e-12)
    retry, control = observe(actual), observe(expected)
    assert digest(retry) == digest(control) and digest(retry) != digest(a)
    return dict(route=route, name=name, bad=bad, requests=1, sha256=digest([a, retry]))


@pytest.mark.parametrize('route', ['gummel', 'newton'])
@pytest.mark.parametrize('name', list(VALUES))
@pytest.mark.parametrize('bad', list(BAD))
def test_invalid_parameter_raises_preserves_both_solvers_and_accepts_retry(route, name, bad):
    code = ("import json, resource; resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "from test_basic_parameter_contract import child\n"
            f"print(json.dumps(dict(test='basic_atomic', **child({route!r}, {name!r}, {bad!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, '-B', '-c', code], env=env, capture_output=True,
                       text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='basic_child_exit', route=route, name=name, bad=bad, returncode=r.returncode)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = [line for line in r.stdout.splitlines() if line.startswith('{"test": "basic_atomic"')]
    assert len(rows) == 1
    print(rows[0])
