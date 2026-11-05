"""Tiny positive populations need accurate log scaling and bounded startup."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator
from test_newton_zero_population import configured, errors, VT, MU, bernoulli

SEEDS = [5e-324, 1e-300, 1e-100, 1e-30, 1e-19]


def tiny_fixture(axis, mesh, source, species, value, budget=100):
    sim, x, seed = configured(axis, mesh, source, species, budget)
    n = np.full(9, value if species != 2 else 1e-8)
    p = np.full(9, value if species != 1 else 1e-8)
    n[[0, -1]] = 0.; p[[0, -1]] = 0.
    sim.set_initial_guess(seed[0], n, p)
    return sim, x


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('mesh', [0, 1])
@pytest.mark.parametrize('source', ['srh', 'kane', 'nonlocal_export'])
@pytest.mark.parametrize('species', [0, 1, 2])
@pytest.mark.parametrize('value', SEEDS)
def test_positive_tiny_seed_satisfies_independent_transport(axis, mesh, source, species, value):
    sim, x = tiny_fixture(axis, mesh, source, species, value)
    state = sim.solve()
    assert state['converged']
    assert any(s['solver'] == 'newton' and s['converged'] for s in state['nonlinear_history'])
    for key in ['n', 'p']:
        assert np.all(np.isfinite(state[key])) and np.all(state[key] >= 0)
        assert state[key][0] == state[key][-1] == 0.
    assert max(errors(state, x, source).values()) < 2e-8
    assert len(state['nonlinear_history'][-1]['equilibrated_linf']) <= 60


def near_equilibrium(axis, target, perturb):
    shape = [1, 1, 1]; shape[axis] = 3
    sim = PyDeviceSimulator(*shape, 1e-9, 1e-9, 1e-9)
    sim.set_quantum_enabled(False); sim.set_thermal_voltage(VT)
    sim.set_mobility(np.full(3, 1e-9), np.full(3, 1e-9))
    sim.set_doping(np.zeros(3)); sim.set_effective_dos(np.full(3, 1e3), np.full(3, 1e3))
    sim.set_bandgap(np.full(3, 25.))
    sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    g = target*MU*VT/1e-18*(bernoulli(2/VT)+bernoulli(-2/VT))
    sim.set_optical_generation(np.full(3, g))
    sim.set_dirichlet_potential({0: 4., 2: 0.})
    sim.set_electron_bc({0: 0., 2: 0.}); sim.set_hole_bc({0: 0., 2: 0.})
    density = np.array([0., target*(1+perturb), 0.])
    sim.set_initial_guess(np.array([4., 2., 0.]), density, density)
    sim.set_btbt_enabled(False); sim.set_use_newton(True); sim.set_newton_primary(True)
    sim.set_gummel_max_iter(60); sim.set_tolerance(1e-11); sim.set_nonlinear_history_enabled(True)
    return sim, g


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('target', [1e-30, 1e-100, 1e-250])
@pytest.mark.parametrize('perturb', [0., .01])
def test_tiny_physical_population_is_preserved_and_refined(axis, target, perturb):
    sim, _ = near_equilibrium(axis, target, perturb)
    state = sim.solve(); assert state['converged']
    np.testing.assert_allclose(state['n'], [0., target, 0.], rtol=2e-9, atol=0.)
    np.testing.assert_allclose(state['p'], [0., target, 0.], rtol=2e-9, atol=0.)
    assert len(state['nonlinear_history'][-1]['equilibrated_linf']) <= 8


@pytest.mark.parametrize('budget', [0, 1, 2])
def test_recovery_does_not_exceed_requested_budget(budget):
    sim, _ = tiny_fixture(0, 0, 'kane', 0, 1e-300, budget)
    state = sim.solve(); assert not state['converged']
    assert all(len(h['equilibrated_linf']) <= budget for h in state['nonlinear_history'])


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('mesh', [0, 1])
@pytest.mark.parametrize('source', ['srh', 'kane', 'nonlocal_export'])
def test_normal_population_control(axis, mesh, source):
    sim, x = tiny_fixture(axis, mesh, source, 0, 1.)
    state = sim.solve(); assert state['converged']
    assert max(errors(state, x, source).values()) < 2e-8
