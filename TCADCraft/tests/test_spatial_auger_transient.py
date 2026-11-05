"""Manufactured contact-bearing Auger dynamics; no material calibration claim.

The reference eliminates both SG carrier rows with a common pair loss, then
uses nested scalar bisections for that loss and the physical Poisson equation.
It does not call native residuals/Jacobians or start from the native solution.
Small positive mobilities keep transport and recombination on comparable time
scales while retaining the existing constant Auger coefficients.
"""
import json

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants


QE = float(native_constants()["elementary_charge_C"])
EPS = 11.7 * 8.854187817e-12
VT = .025852
SCALE = 1e23


def bernoulli(x):
    if abs(x) < 1e-5:
        return 1 - x / 2 + x*x / 12 - x**4 / 720
    return x / np.expm1(x)


def pair_rate(n, p, ni, cn, cp, tau_n, tau_p):
    """Physical pair rate divided by SCALE, using dimensionless n and p."""
    product = n*p - ni*ni
    return (SCALE**2 * (cn*n + cp*p) * product
            + product / (tau_p*(n+ni) + tau_n*(p+ni)))


def reference_step(previous, h, x, boundary_phi, boundary_n, boundary_p,
                   doping, mu_n, mu_p, ni, cn, cp, tau_n, tau_p, generation):
    left, right = np.diff(x)
    width = (left + right) / 2
    geometric = (1 / left + 1 / right) / width
    kappa = QE * SCALE / (EPS * geometric)
    harmonic_phi = (boundary_phi[0] / left + boundary_phi[1] / right) / (1/left + 1/right)
    if h == 0:
        n, p = previous
        return np.array([harmonic_phi + kappa*(p-n+doping), n, p])

    # The Auger contribution to dF/dloss is bounded below by this positive
    # value; SRH adds a nonnegative derivative on the positive-density branch.
    assert h * SCALE**2 * ni**2 * (cn + cp) < .5

    def carriers(phi):
        delta = (boundary_phi - phi) / VT
        bpos = np.array([bernoulli(v) for v in delta])
        bneg = np.array([bernoulli(-v) for v in delta])
        edges = np.array([left, right])
        an = h * mu_n * VT / (edges * width)
        ap = h * mu_p * VT / (edges * width)
        numer_n = previous[0] + np.dot(an * bpos, boundary_n) + h * generation
        numer_p = previous[1] + np.dot(ap * bneg, boundary_p) + h * generation
        denom_n, denom_p = 1 + np.dot(an, bneg), 1 + np.dot(ap, bpos)

        def at_loss(loss):
            return (numer_n-loss)/denom_n, (numer_p-loss)/denom_p

        def defect(loss):
            n, p = at_loss(loss)
            return loss - h * pair_rate(n, p, ni, cn, cp, tau_n, tau_p)

        low, high = -1., min(numer_n, numer_p)
        for _ in range(50):
            if defect(low) < 0:
                break
            low *= 2
        else:
            raise AssertionError("pair-loss bracket not found")
        assert defect(high) > 0
        for _ in range(75):
            mid = (low + high) / 2
            if defect(mid) < 0:
                low = mid
            else:
                high = mid
        n, p = at_loss((low+high)/2)
        assert n > 0 and p > 0
        return n, p

    def residual(phi):
        n, p = carriers(phi)
        return phi - harmonic_phi - kappa * (p-n+doping)

    low, high = -.5, .5
    assert residual(low) < 0 < residual(high)
    for _ in range(75):
        mid = (low + high) / 2
        if residual(mid) < 0:
            low = mid
        else:
            high = mid
    phi = (low+high)/2
    return np.array([phi, *carriers(phi)])


@pytest.mark.parametrize("axis", range(3))
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("species", range(3))
@pytest.mark.parametrize("mode", ["decay", "generation", "mixed", "disabled"])
@pytest.mark.parametrize("polarity", [-1, 1])
def test_contact_auger_matches_independent_poisson_sg_be(axis, stretched, log_space,
                                                       species, mode, polarity):
    shape, spacing = [1, 1, 1], [1e-6, 1e-6, 1e-6]
    shape[axis], spacing[axis] = 3, 1e-8
    x = np.array([0., .7, 2.1] if stretched else [0., 1., 2.]) * spacing[axis]
    left, right = np.diff(x)
    width = (left+right)/2
    geometric = (1/left+1/right)/width
    dt = 2e-5
    mu_n = .15 / (dt * VT * geometric)
    mu_p = .55 * mu_n
    cn, cp = (0. if species == 1 else 2.8e-43), (0. if species == 0 else 9.9e-44)
    ni = 2. if mode == "generation" else .3
    tau_n, tau_p = (3*dt, 5*dt) if mode == "mixed" else (1e100, 1e100)
    generation = .15 / dt if mode == "mixed" else 0.
    doping = .15 * polarity
    phi_bc = polarity * np.array([-.003, .005])
    n0, p0 = np.array([1., 1.6, .8]), np.array([.9, 1.1, 1.1])
    if polarity < 0:
        n0, p0 = p0, n0
    bn, bp = n0[[0, 2]], p0[[0, 2]]
    sim = PyDeviceSimulator(*shape, *spacing)
    sim.set_quantum_enabled(False)
    [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions][axis](x)
    sim.set_permittivity(np.full(3, EPS))
    sim.set_mobility(np.full(3, mu_n), np.full(3, mu_p))
    sim.set_doping(SCALE * np.array([0., doping, 0.]))
    sim.set_effective_dos(np.full(3, SCALE*ni), np.full(3, SCALE*ni))
    sim.set_bandgap(np.zeros(3))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(3, tau_n), np.full(3, tau_p))
    sim.set_optical_generation(np.full(3, SCALE*generation))
    sim.set_auger_params(cn, cp)
    sim.set_auger_enabled(mode != "disabled")
    sim.set_dirichlet_potential({0: float(phi_bc[0]), 2: float(phi_bc[1])})
    sim.set_electron_bc({0: float(SCALE*bn[0]), 2: float(SCALE*bn[1])})
    sim.set_hole_bc({0: float(SCALE*bp[0]), 2: float(SCALE*bp[1])})
    sim.set_initial_guess(np.zeros(3), SCALE*n0, SCALE*p0)
    sim.set_newton_use_log_space(log_space)
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-18)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(2.5*dt)
    sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient()
    assert len(history) == 4
    actual_cn, actual_cp = (0., 0.) if mode == "disabled" else (cn, cp)
    reference_n, reference_p = n0[1], p0[1]
    previous_n, previous_p = n0.copy(), p0.copy()
    previous_charge = None
    max_error = max_balance = max_current_error = max_charge_defect = 0.
    signal = None
    area = np.prod([spacing[a] for a in range(3) if a != axis])
    volume = width * area
    for step, state in enumerate(history):
        assert state['valid'] and state['converged'] and not state['phi_frozen']
        assert not state['majority_frozen'] and state['charge_ledger_available']
        assert state['initial_state'] == (step == 0)
        h = 0. if step == 0 else state['time_s'] - history[step-1]['time_s']
        assert state['dt_s'] == pytest.approx(h, rel=1e-14)
        expected = reference_step((reference_n, reference_p), h, x, phi_bc, bn, bp,
                                  doping, mu_n, mu_p, ni, actual_cn, actual_cp,
                                  tau_n, tau_p, generation)
        if step == 1 and mode != 'disabled':
            no_auger = reference_step((reference_n, reference_p), h, x, phi_bc, bn, bp,
                                     doping, mu_n, mu_p, ni, 0., 0., tau_n, tau_p, generation)
            signal = float(np.max(abs(expected[1:] - no_auger[1:])))
            assert signal > 1e-3  # The oracle must detect an omitted Auger source.
        reference_n, reference_p = expected[1:]
        n, p, phi = state['n']/SCALE, state['p']/SCALE, state['phi']
        assert np.all(np.isfinite(n)) and np.all(np.isfinite(p)) and np.all(np.isfinite(phi))
        assert np.all(n > 0) and np.all(p > 0)
        np.testing.assert_array_equal(state['n'][[0, 2]], SCALE*bn)
        np.testing.assert_array_equal(state['p'][[0, 2]], SCALE*bp)
        np.testing.assert_array_equal(phi[[0, 2]], phi_bc)
        max_error = max(max_error, abs(phi[1]-expected[0])/VT,
                        abs(n[1]/reference_n-1), abs(p[1]/reference_p-1))
        delta = np.diff(phi)/VT
        bpos = np.array([bernoulli(v) for v in delta])
        bneg = np.array([bernoulli(-v) for v in delta])
        jn = QE*SCALE*mu_n*VT/np.diff(x) * (n[1:]*bpos - n[:-1]*bneg)
        jp = QE*SCALE*mu_p*VT/np.diff(x) * (p[:-1]*bpos - p[1:]*bneg)
        currents = area * np.array([(jn+jp)[0], -(jn+jp)[1]])
        current_scale = QE*SCALE*volume/dt
        max_current_error = max(max_current_error,
                                np.max(abs(np.asarray(state['terminal_currents_A'])-currents))/current_scale)
        charge = QE*SCALE*(p[1]-n[1])*volume
        assert abs(state['stored_charge_C']-charge)/(QE*SCALE*volume) < 1e-12
        if h:
            rate = pair_rate(n[1], p[1], ni, actual_cn, actual_cp, tau_n, tau_p)
            # Original unscaled BE equations, independently reconstructed.
            residual_n = n[1]-previous_n[1] - h*(jn[1]-jn[0])/(QE*SCALE*width) + h*(rate-generation)
            residual_p = p[1]-previous_p[1] + h*(jp[1]-jp[0])/(QE*SCALE*width) + h*(rate-generation)
            max_balance = max(max_balance, abs(residual_n), abs(residual_p))
            max_charge_defect = max(max_charge_defect,
                                   abs(charge-previous_charge-h*sum(currents))/(QE*SCALE*volume))
        previous_n, previous_p, previous_charge = n, p, charge
    assert history[-1]['time_s'] == pytest.approx(2.5*dt, rel=1e-14)
    attempts = sim.get_transient_attempt_history()
    assert len(attempts) == 3 and all(a['accepted'] for a in attempts)
    assert all(t['solver'] == 'newton' for a in attempts for t in a['trials'])
    assert max(max_error, max_balance, max_current_error, max_charge_defect) < 1e-8
    print(json.dumps(dict(test='spatial_auger', axis=axis, stretched=stretched,
                         log_space=log_space, species=species, mode=mode, polarity=polarity,
                         steps=3, max_error=float(max_error), max_balance=float(max_balance),
                         max_current_error=float(max_current_error),
                         max_charge_defect=float(max_charge_defect), signal=signal)))
