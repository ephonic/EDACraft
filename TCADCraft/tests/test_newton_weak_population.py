"""Resolve generated populations below the additive coordinate density floor."""
import numpy as np
import pytest
from test_newton_tiny_population import near_equilibrium

TARGETS = [1e-30, 1e-100, 1e-250]
SEEDS = ['zero', 'subnormal', 'deep', 'relative']


def weak_fixture(axis, target, seed, species=0, budget=60):
    sim, generation = near_equilibrium(axis, target, 0.)
    value = {'zero': 0., 'subnormal': 5e-324, 'deep': 1e-300,
             'relative': target*1e-12}[seed]
    n = np.array([0., target if species == 2 else value, 0.])
    p = np.array([0., target if species == 1 else value, 0.])
    sim.set_initial_guess(np.array([4., 2., 0.]), n, p)
    sim.set_gummel_max_iter(budget)
    return sim, generation


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('seed', SEEDS)
@pytest.mark.parametrize('species', range(3))
def test_weak_generation_makes_physical_progress(axis, target, seed, species):
    sim, _ = weak_fixture(axis, target, seed, species)
    state = sim.solve()
    assert state['converged']
    for key in ['n', 'p']:
        np.testing.assert_allclose(state[key], [0., target, 0.], rtol=2e-9, atol=0.)
    history = state['nonlinear_history']
    assert any(h['solver'] == 'newton' and h['converged'] for h in history)
    assert all(len(h['equilibrated_linf']) <= 8 for h in history)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('seed', ['zero', 'deep'])
@pytest.mark.parametrize('budget', [0, 1, 2])
def test_unfinished_weak_startup_cannot_report_success(axis, seed, budget):
    sim, _ = weak_fixture(axis, 1e-100, seed, budget=budget)
    state = sim.solve()
    assert not state['converged']
    assert all(len(h['equilibrated_linf']) <= budget for h in state['nonlinear_history'])


@pytest.mark.parametrize('axis', range(3))
def test_true_zero_source_still_accepts_zero_population(axis):
    sim, _ = weak_fixture(axis, 1e-100, 'zero')
    sim.set_optical_generation(np.zeros(3))
    state = sim.solve()
    assert state['converged']
    np.testing.assert_array_equal(state['n'], np.zeros(3))
    np.testing.assert_array_equal(state['p'], np.zeros(3))
