"""Rebuilt Python binding: independent classical Auger BE trajectories."""
import json

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator


@pytest.mark.parametrize("axis", range(3))
@pytest.mark.parametrize("species", range(3))
@pytest.mark.parametrize("mode", range(6))
def test_public_auger_be_trajectory(axis, species, mode):
    initial = 1e23
    ni = 1e24 if mode in (1, 2) else 1e19
    cn = 0. if species == 1 else 2.8e-43
    cp = 0. if species == 0 else 9.9e-44
    strength = 1e-4 if mode == 1 else (100. if mode in (0, 3) else 1.)
    dt = strength / ((cn + cp) * initial**2)
    tau = 3 / (2 * (cn + cp) * initial**2) if mode == 4 else 1e100
    generation = .2 * initial / dt if mode == 5 else 0.
    shape = [1, 1, 1]
    shape[axis] = 3
    sim = PyDeviceSimulator(*shape, 1e-6, 1e-6, 1e-6)
    sim.set_quantum_enabled(False)
    sim.set_permittivity(np.full(3, 11 * 8.854187817e-12))
    sim.set_mobility(np.full(3, .01), np.full(3, .02))
    sim.set_effective_dos(np.full(3, ni), np.full(3, ni))
    sim.set_bandgap(np.zeros(3))
    sim.set_recombination(np.full(3, tau), np.full(3, tau))
    sim.set_optical_generation(np.full(3, generation))
    sim.set_auger_params(cn, cp)
    sim.set_auger_enabled(mode != 3)
    sim.set_dirichlet_potential({0: 0., 1: 0., 2: 0.})
    sim.set_initial_guess(np.zeros(3), np.full(3, initial), np.full(3, initial))
    sim.set_newton_use_log_space(True)
    sim.set_gummel_max_iter(60)
    sim.set_tolerance(1e-18)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(2 * dt)
    sim.set_nonlinear_history_enabled(True)
    if mode == 2:
        sim.set_transient_electrical_error_control(True, 1e-8, .002, 1e12, dt * 1e-8, 30)
    history = sim.solve_transient()
    assert len(history) >= 3
    assert history[0]['initial_state'] and history[0]['time_s'] == 0.
    np.testing.assert_array_equal(history[0]['n'], np.full(3, initial))
    assert history[-1]['time_s'] == pytest.approx(2 * dt, rel=1e-14)
    expected = initial
    max_error = max_balance = 0.
    for prev, now in zip(history, history[1:]):
        assert now['valid'] and now['converged'] and not now['initial_state']
        h = now['time_s'] - prev['time_s']
        assert h > 0 and now['dt_s'] == pytest.approx(h, rel=1e-14)
        s = 0. if mode == 3 else h * (cn + cp) * expected**2
        b = h / (2 * tau) if mode == 4 else 0.
        ratio, g = ni / expected, h * generation / expected
        lo, hi = min(1., ratio), max(1. + g, ratio)
        # Independent reference is propagated from its own previous root.
        for _ in range(160):
            x = (lo + hi) / 2
            if x + s * x * (x*x - ratio*ratio) + b * (x-ratio) > 1 + g:
                hi = x
            else:
                lo = x
        expected *= (lo + hi) / 2
        n, p = now['n'], now['p']
        assert np.all(np.isfinite(n)) and np.all(np.isfinite(p))
        assert np.all(n > 0) and np.all(p > 0)
        max_error = max(max_error, np.max(abs(n/expected - 1)), np.max(abs(p/expected - 1)))
        rate = 0. if mode == 3 else (cn*n + cp*p) * (n*p - ni*ni)
        if mode == 4:
            rate += (n*p - ni*ni) / (tau * (n+p+2*ni))
        for key in ['n', 'p']:
            residual = (now[key] - prev[key] + h*(rate-generation)) / prev[key]
            max_balance = max(max_balance, np.max(abs(residual)))
    assert max_error < 1e-8 and max_balance < 1e-8
    attempts = sim.get_transient_attempt_history()
    assert attempts and all(t['solver'] == 'newton' for a in attempts for t in a['trials'])
    rejected = sum(not a['accepted'] for a in attempts)
    if mode == 2:
        assert len(history) > 3 and rejected > 0
    else:
        assert len(history) == 3 and rejected == 0
    print(json.dumps(dict(test='python_public_auger',axis=axis,species=species,mode=mode,
                         steps=len(history)-1,rejections=rejected,
                         max_error=float(max_error),max_balance=float(max_balance))))


@pytest.mark.parametrize('unsupported', ['fermi', 'ferroelectric', 'electron_blocked', 'both_blocked'])
def test_public_auger_scope_rejected_before_attempt(unsupported):
    sim = PyDeviceSimulator(3, 1, 1, 1e-6, 1e-6, 1e-6)
    sim.set_quantum_enabled(False)
    sim.set_auger_enabled(True)
    sim.set_mobility(np.full(3, .01), np.full(3, .01))
    sim.set_dirichlet_potential({0: 0., 1: 0., 2: 0.})
    sim.set_initial_guess(np.zeros(3), np.full(3, 1e23), np.full(3, 1e23))
    sim.set_nonlinear_history_enabled(True)
    if unsupported == 'fermi':
        sim.set_statistics_type(1)
    elif unsupported == 'ferroelectric':
        sim.set_ferroelectric_enabled(True)
        sim.set_ferroelectric_gamma(.1)  # Reach the Auger/FE guard with valid LK damping.
    else:
        sim.set_mobility(np.zeros(3), np.zeros(3) if unsupported == 'both_blocked' else np.full(3, .01))
    with pytest.raises(ValueError, match='Auger transient requires'):
        sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
