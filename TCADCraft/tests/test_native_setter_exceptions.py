"""Each native invalid-argument branch must survive the Python boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from test_trap_parameter_guard import dielectric, EPS, SIZE
from test_zero_auger_transient import configured, digest, snapshot


ARRAYS = {'permittivity': 1, 'optical_generation': 1, 'recombination': 2,
          'effective_dos': 2, 'bandgap': 1, 'ferroelectric_params': 1,
          'breakdown_params': 2}
SCALARS = {'btbt_continuity_scale': ['negative', 'nan', 'inf', 'ninf'],
           'btbt_nonlocal_params': ['nan', 'inf', 'ninf', 'points0', 'points1'],
           'btbt_nonlocal_mass': ['zero', 'negative', 'nan', 'inf', 'ninf']}
BAD = [(name, f'{field}:{length}') for name, count in ARRAYS.items()
       for field in range(count) for length in
       ([0, SIZE-1, SIZE+1] if name == 'breakdown_params' else [0, 2, 4])]
BAD += [(name, bad) for name, values in SCALARS.items() for bad in values]
NAMES = list(ARRAYS)+list(SCALARS)
VALID = [(name, axis) for name in NAMES for axis in
         ([0] if name.startswith('btbt_nonlocal') else range(3))]


def arguments(name, alternate=False):
    if name == 'permittivity':return [np.full(3, EPS*(2 if alternate else 1.2))]
    if name == 'optical_generation':return [np.full(3, 3e25 if alternate else 1e25)]
    if name == 'recombination':return [np.full(3, 5e-11 if alternate else 1e-10), np.full(3, 7e-11 if alternate else 2e-10)]
    if name == 'effective_dos':return [np.full(3, 3e16 if alternate else 1e16), np.full(3, 4e16 if alternate else 2e16)]
    if name == 'bandgap':return [np.full(3, .03 if alternate else .01)]
    if name == 'ferroelectric_params':return [np.ones(3, dtype=np.int8), 2e8 if alternate else 1e8, 3e12 if alternate else 1e12]
    if name == 'breakdown_params':return [np.ones(SIZE, dtype=np.int8), np.full(SIZE, 1e9 if alternate else 1e5), 9e-5 if alternate else 1e-5]
    if name == 'btbt_continuity_scale':return [.8 if alternate else .1]
    if name == 'btbt_nonlocal_params':return [.04 if alternate else .2, 64 if alternate else 32]
    if name == 'btbt_nonlocal_mass':return [.1 if alternate else .25]
    raise AssertionError(name)


def fixture(name, axis, alternate=False):
    if name == 'breakdown_params':
        sim, _ = dielectric('gummel', axis)
        sim.set_breakdown_enabled(True)
    elif name.startswith('btbt_nonlocal'):
        sim = PyDeviceSimulator(9, 1, 1, 1e-9, 1., 1.)
        sim.set_quantum_enabled(False)
        sim.set_mobility(np.full(9, 1e-9), np.full(9, 1e-9))
        sim.set_effective_dos(np.full(9, 1e3), np.full(9, 1e3))
        sim.set_bandgap(np.full(9, 1.12))
        sim.set_recombination(np.full(9, 1e-7), np.full(9, 1e-7))
        sim.set_dirichlet_potential({0: 4., 8: 0.})
        sim.set_electron_bc({0: 0., 8: 0.})
        sim.set_hole_bc({0: 0., 8: 0.})
        sim.set_initial_guess(np.linspace(4., 0., 9), np.zeros(9), np.zeros(9))
        sim.set_btbt_enabled(True)
        sim.set_btbt_use_nonlocal(True)
        sim.set_btbt_params(1e10, 2e9, 0.)
        sim.set_btbt_continuity_scale(0.)
        sim.set_btbt_nonlocal_params(.2, 32)
        sim.set_btbt_nonlocal_mass(.25)
        sim.set_gummel_max_iter(100)
        sim.set_tolerance(1e-11)
    else:
        sim = configured('coupled_lk' if name == 'ferroelectric_params' else 'classical', axis, True)
        if name not in ['ferroelectric_params', 'btbt_continuity_scale']:
            sim.set_recombination(np.full(3, 1e-10), np.full(3, 2e-10))
        if name == 'btbt_continuity_scale':
            sim.set_dirichlet_potential({0: 0., 2: -.05})
            sim.set_btbt_enabled(True)
            sim.set_btbt_params(1e18, 1e3, 0.)
    getattr(sim, 'set_'+name)(*arguments(name, alternate))
    return sim


def observe(sim, name):
    if name == 'breakdown_params':
        states = [sim.solve(), sim.solve()]
        assert all(s['converged'] for s in states)
        return states, sim.breakdown_state()
    if name.startswith('btbt_'):
        state = sim.solve()
        assert state['converged'] and np.max(state['G_btbt']) > 0.
        return state
    result = snapshot(sim)
    assert len(result[0]) == 4 and all(s['valid'] for s in result[0])
    if name == 'ferroelectric_params':
        return result, sim.get_ferroelectric_mask(), sim.get_ferroelectric_lk_parameters()
    return result


@pytest.mark.parametrize('name,axis', VALID)
def test_valid_setter_is_observable_and_preserves_parent_exports(name, axis):
    base = observe(fixture(name, axis), name)
    other = observe(fixture(name, axis, True), name)
    assert digest(base) != digest(other), (name, 'fixture does not expose parameter changes')
    key = f'{name}/{axis}'
    h = digest([base, other])
    print(json.dumps(dict(test='native_setter_reference', key=key, sha256=h)))
    oracle = os.environ.get('TCAD_NATIVE_SETTER_ORACLE')
    if oracle:assert json.loads(Path(oracle).read_text(encoding='utf8'))[key] == h


def child(name, bad):
    actual, expected = fixture(name, 0), fixture(name, 0)
    request = arguments(name, True)
    if name in ARRAYS:
        field, length = map(int, bad.split(':'))
        # Reject empty, short and long arrays independently for each field.
        request[field] = np.zeros(length, dtype=request[field].dtype)
        message = {'permittivity':'permittivity size mismatch', 'optical_generation':'optical generation size mismatch',
                   'recombination':'recombination lifetime size mismatch', 'effective_dos':'effective DOS size mismatch',
                   'bandgap':'bandgap size mismatch', 'ferroelectric_params':'fe_mask size mismatch',
                   'breakdown_params': 'bd_mask size mismatch' if field == 0 else 'E_bd size mismatch'}[name]
    elif name == 'btbt_nonlocal_params':
        if bad.startswith('points'):
            request[1] = int(bad[-1]);message = 'BTBT wkb_npts must be >= 2'
        else:
            request[0] = {'nan':np.nan, 'inf':np.inf, 'ninf':-np.inf}[bad]
            message = 'BTBT tunnel_path_frac must be finite'
    else:
        request[0] = {'zero':0., 'negative':-1., 'nan':np.nan, 'inf':np.inf, 'ninf':-np.inf}[bad]
        message = ('BTBT continuity scale must be finite and non-negative' if name == 'btbt_continuity_scale'
                   else 'BTBT nonlocal mass ratio must be finite and > 0')
    with pytest.raises(ValueError, match='^'+re.escape(message)+'$'):
        getattr(actual, 'set_'+name)(*request)
    a, b = observe(actual, name), observe(expected, name)
    assert digest(a) == digest(b)
    # FE and breakdown carry history across solves; advance both equally
    # before comparing a subsequent valid request.
    getattr(actual, 'set_'+name)(*arguments(name, True))
    getattr(expected, 'set_'+name)(*arguments(name, True))
    retry, control = observe(actual, name), observe(expected, name)
    assert digest(retry) == digest(control)
    return dict(name=name, bad=bad, requests=1, sha256=digest([a, retry]))


@pytest.mark.parametrize('name,bad', BAD)
def test_invalid_setter_raises_preserves_state_and_accepts_retry(name, bad):
    code = ("import json, resource; resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "from test_native_setter_exceptions import child\n"
            f"print(json.dumps(dict(test='native_setter_atomic', **child({name!r}, {bad!r}))))\n")
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
    result = subprocess.run([sys.executable, '-B', '-c', code], env=env, capture_output=True,
                            text=True, encoding='utf8', timeout=60)
    print(json.dumps(dict(test='native_setter_child_exit', name=name, bad=bad, returncode=result.returncode)))
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    rows = [line for line in result.stdout.splitlines() if line.startswith('{"test": "native_setter_atomic"')]
    assert len(rows) == 1
    print(rows[0])
