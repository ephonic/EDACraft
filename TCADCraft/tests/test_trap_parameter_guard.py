"""Native trap input atomicity, signed Poisson sources and zero-source scope."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from test_zero_auger_transient import KINDS, configured, digest, snapshot


ROUTES = ['gummel', 'newton', 'hybrid']
EPS = 20*8.854187817e-12
SIZE = 9


def dielectric(route, axis=0, stretched=False):
    shape = [1, 1, 1]
    shape[axis] = SIZE
    x = np.array([0., .3, .9, 1.8, 3., 4.7, 5.6, 7.2, 8.]) * 1e-8 if stretched else np.arange(SIZE)*1e-8
    sim = PyDeviceSimulator(*shape, 1e-8, 1e-8, 1e-8)
    [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions][axis](x)
    sim.set_quantum_enabled(False)
    sim.set_permittivity(np.full(SIZE, EPS))
    sim.set_mobility(np.zeros(SIZE), np.zeros(SIZE))
    sim.set_doping(np.zeros(SIZE))
    sim.set_effective_dos(np.full(SIZE, 1e16), np.full(SIZE, 1e16))
    sim.set_bandgap(np.full(SIZE, 6.))
    sim.set_recombination(np.full(SIZE, 1e100), np.full(SIZE, 1e100))
    sim.set_dirichlet_potential({0: 0., SIZE-1: .02})
    sim.set_electron_bc({0: 0., SIZE-1: 0.})
    sim.set_hole_bc({0: 0., SIZE-1: 0.})
    sim.set_initial_guess(np.zeros(SIZE), np.zeros(SIZE), np.zeros(SIZE))
    sim.set_use_newton(route != 'gummel')
    sim.set_newton_primary(route == 'newton')
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-11)
    return sim, x


def reference_poisson(x, charge):
    """Independent physical FV solve; Q_ot is C/m^3, not a carrier density."""
    matrix = np.zeros((SIZE, SIZE))
    rhs = charge.copy()
    matrix[0, 0] = matrix[-1, -1] = 1.
    rhs[0], rhs[-1] = 0., .02
    for i in range(1, SIZE-1):
        width = (x[i+1]-x[i-1])/2
        for j in [i-1, i+1]:
            coefficient = EPS / (abs(x[j]-x[i])*width)
            matrix[i, i] += coefficient
            matrix[i, j] -= coefficient
    return np.linalg.solve(matrix, rhs)


def check_oracle(kind, key, value):
    h = digest(value)
    print(json.dumps(dict(test='trap_reference', kind=kind, key=key, sha256=h)))
    path = os.environ.get('TCAD_TRAP_ORACLE')
    if path:
        assert json.loads(Path(path).read_text(encoding='utf8'))[kind+'/'+key] == h
    return h


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('sign', [-1, 1])
def test_signed_oxide_charge_clear_restore_matches_independent_poisson(route, axis, stretched, sign):
    sim, x = dielectric(route, axis, stretched)
    charge = sign*1e3*(.8+.05*np.arange(SIZE))
    states = []
    max_error = 0.
    for values in [charge, np.empty(0), charge, np.zeros(SIZE)]:
        sim.set_oxide_traps(values)
        sim.set_initial_guess(np.zeros(SIZE), np.zeros(SIZE), np.zeros(SIZE))
        state = sim.solve()
        assert state['converged'] and np.all(np.isfinite(state['phi']))
        physical_charge = values if len(values) else np.zeros(SIZE)
        expected = reference_poisson(x, physical_charge)
        np.testing.assert_allclose(state['phi'], expected, rtol=1e-8, atol=1e-12)
        max_error = max(max_error, float(np.max(abs(state['phi']-expected))))
        states.append(state)
    assert np.max(abs(states[0]['phi']-states[1]['phi'])) > 1e-4
    assert digest(states[0]) == digest(states[2])
    check_oracle('signed_cycle', f'{route}/{axis}/{stretched}/{sign}', states)
    print(json.dumps(dict(test='trap_poisson', route=route, axis=axis,
                         stretched=stretched, sign=sign, states=4, max_error_V=max_error)))


OXIDE_BAD = ['short', 'long', 'singleton'] + [f'{name}_{i}' for name in ['nan', 'inf', 'ninf'] for i in [0, 4, 8]]


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('bad', OXIDE_BAD)
def test_oxide_invalid_request_preserves_signed_charge(route, bad):
    actual, _ = dielectric(route)
    expected, _ = dielectric(route)
    for sim in [actual, expected]:
        sim.set_oxide_traps(np.linspace(-500., 1500., SIZE))
    if bad in ['short', 'long', 'singleton']:
        values = np.zeros({'short':SIZE-1, 'long':SIZE+1, 'singleton':1}[bad])
        message = 'oxide trap charge size mismatch'
    else:
        name, position = bad.split('_')
        values = np.full(SIZE, 5e3)
        values[int(position)] = {'nan':np.nan, 'inf':np.inf, 'ninf':-np.inf}[name]
        message = 'oxide trap charge must be finite'
    with pytest.raises(ValueError, match=message):
        actual.set_oxide_traps(values)
    a, b = actual.solve(), expected.solve()
    assert a['converged'] and b['converged']
    assert digest(a) == digest(b)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('bad', ['mask', 'density_negative', 'density_nan', 'density_inf',
                                 'density_ninf', 'energy_nan', 'energy_inf', 'energy_ninf'])
def test_interface_invalid_request_preserves_mask_density_and_energy(route, bad):
    actual, _ = dielectric(route)
    expected, _ = dielectric(route)
    for sim in [actual, expected]:
        sim.set_interface_traps(np.ones(SIZE, dtype=np.int8), 1e9, .1)
    mask, density, energy = np.zeros(SIZE, dtype=np.int8), 2e9, -.2
    if bad == 'mask':
        mask = np.ones(SIZE-1, dtype=np.int8)
        message = 'trap mask size mismatch'
    elif bad.startswith('density_'):
        density = {'negative':-1., 'nan':np.nan, 'inf':np.inf, 'ninf':-np.inf}[bad.split('_')[1]]
        message = 'interface trap density must be finite and nonnegative'
    else:
        energy = {'nan':np.nan, 'inf':np.inf, 'ninf':-np.inf}[bad.split('_')[1]]
        message = 'interface trap energy must be finite'
    if bad == 'mask':
        # Old bindings let the C++ size exception terminate Python. Isolate it
        # so the baseline still records every other missing input contract.
        code = ("from test_trap_parameter_guard import dielectric; import numpy as np, sys\n"
                f"s, _ = dielectric({route!r})\n"
                "try: s.set_interface_traps(np.ones(8, dtype=np.int8), 2e9, -.2)\n"
                "except ValueError: sys.exit(0)\n"
                "sys.exit(3)\n")
        env = dict(os.environ)
        env['PYTHONPATH'] = str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH', '')
        probe = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                               capture_output=True, text=True, encoding='utf8', timeout=30)
        assert probe.returncode == 0, (probe.returncode, probe.stderr)
    with pytest.raises(ValueError, match=message):
        actual.set_interface_traps(mask, density, energy)
    a, b = actual.solve(), expected.solve()
    assert a['converged'] and b['converged']
    assert digest(a) == digest(b)


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('budget', [0, 80])
def test_zero_oxide_charge_preserves_every_transient_export(kind, axis, log_space, budget):
    absent = configured(kind, axis, log_space, budget)
    expected = snapshot(absent)
    key = f'{kind}/{axis}/{log_space}/{budget}'
    h = check_oracle('absent_transient', key, expected)
    zero = configured(kind, axis, log_space, budget)
    zero.set_interface_traps(np.ones(3, dtype=np.int8), 0., .15)
    zero.set_oxide_traps(np.array([0., -0., 0.]))
    actual = snapshot(zero)
    assert digest(actual) == h
    if budget:
        assert len(actual[0]) == 4 and all(s['valid'] for s in actual[0])
    print(json.dumps(dict(test='trap_zero_equal', key=key, sha256=h)))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('sign', [-1, 1])
def test_any_nonzero_oxide_charge_is_rejected_then_zero_retry_matches_fresh(kind, sign):
    sim = configured(kind, 0, True)
    sim.set_oxide_traps(sign*np.array([0., 1e-300, 0.]))
    with pytest.raises(ValueError, match='traps, quantum, thermal'):
        sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
    sim.set_oxide_traps(np.zeros(3))
    actual = snapshot(sim)
    fresh = configured(kind, 0, True)
    expected = snapshot(fresh)
    assert all(s['valid'] for s in actual[0])
    assert digest(actual) == digest(expected)
