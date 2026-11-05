"""Overpopulated depleted states must advance within the original budget."""
import numpy as np
import pytest
from test_newton_tiny_population import near_equilibrium
from test_newton_zero_population import configured, carrier_matrix, MU, VT

TARGETS = [1e-30, 1e-100, 1e-250]
SEEDS = ['high', 'middle', 'low', 'relative']


def initial_value(target, seed):
    return {'high': .1, 'middle': 1e-8, 'low': 1e-19,
            'relative': target*1e12}[seed]


def depletion_fixture(axis, target, seed, species=0, budget=60):
    sim, generation = near_equilibrium(axis, target, 0.)
    value = initial_value(target, seed)
    n = np.array([0., target if species == 2 else value, 0.])
    p = np.array([0., target if species == 1 else value, 0.])
    sim.set_initial_guess(np.array([4., 2., 0.]), n, p)
    sim.set_gummel_max_iter(budget)
    return sim, generation


def multinode_fixture(axis, mesh, target, seed, species=0):
    sim, x, _ = configured(axis, mesh, 'srh', budget=60)
    sim.set_btbt_enabled(False)
    sim.set_bandgap(np.full(9, 25.))
    sim.set_recombination(np.full(9, 1e100), np.full(9, 1e100))
    generation = target*MU*VT/1e-18
    sim.set_optical_generation(np.full(9, generation))
    phi = 4*(1-x/x[-1]); width = (x[2:]-x[:-2])/2
    expected = [np.r_[0., np.linalg.solve(carrier_matrix(phi, x, sign),
                                        generation*width), 0.]
                for sign in [1, -1]]
    n = expected[0].copy() if species == 2 else np.full(9, initial_value(target, seed))
    p = expected[1].copy() if species == 1 else np.full(9, initial_value(target, seed))
    n[[0, -1]] = 0.; p[[0, -1]] = 0.
    sim.set_initial_guess(phi, n, p)
    return sim, x, expected, generation


def check_state(state, expected):
    assert state['converged']
    for key, density in zip(['n', 'p'], expected):
        np.testing.assert_allclose(state[key], density, rtol=2e-9, atol=0.)
    assert any(h['solver'] == 'newton' and h['converged']
               for h in state['nonlinear_history'])
    assert all(len(h['equilibrated_linf']) <= 60 for h in state['nonlinear_history'])


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('seed', SEEDS)
@pytest.mark.parametrize('species', range(3))
def test_overpopulated_tiny_steady_state(axis, target, seed, species):
    sim, _ = depletion_fixture(axis, target, seed, species)
    expected = np.array([0., target, 0.])
    check_state(sim.solve(), [expected, expected])


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('mesh', [0, 1])
@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('seed', ['high', 'middle'])
@pytest.mark.parametrize('species', range(3))
def test_nonuniform_multinode_depletion(axis, mesh, target, seed, species):
    sim, _, expected, _ = multinode_fixture(axis, mesh, target, seed, species)
    check_state(sim.solve(), expected)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('budget', [0, 1, 2])
def test_depletion_recovery_shares_original_budget(axis, budget):
    sim, _ = depletion_fixture(axis, 1e-250, 'middle', budget=budget)
    state = sim.solve()
    assert not state['converged']
    assert all(len(h['equilibrated_linf']) <= budget for h in state['nonlinear_history'])
