"""Independent finite-volume row and terminal audits for 2-D/3-D Auger BE.

Unlike the scalar trajectory oracle, these checks validate the actual returned
state against the full graph equations, without claiming an independent
multidimensional trajectory solver or general device qualification.
"""
import json

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from test_spatial_auger_transient import QE, EPS, VT, SCALE, bernoulli, pair_rate


@pytest.mark.parametrize('shape', [(5, 4, 1), (5, 4, 3)])
@pytest.mark.parametrize('all_faces', [False, True])
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('mode', ['decay', 'generation', 'mixed', 'disabled'])
def test_multidimensional_auger_original_equations_and_terminal_charge(shape, all_faces,
                                                                      stretched, log_space, mode):
    size, dt = int(np.prod(shape)), 2e-5
    spacing = np.array([1e-8, 1.3e-8, .8e-8])
    positions = [np.arange(count)*length for count, length in zip(shape, spacing)]
    for x in positions:
        if stretched:
            x *= 1 + .1*np.arange(len(x))
    widths = []
    for x, length in zip(positions, spacing):
        edge = np.diff(x)
        widths.append(np.r_[edge[0], (edge[1:]+edge[:-1])/2, edge[-1]] if len(edge)
                      else np.array([length]))
    xyz = np.array([(i, j, k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    contacts = (xyz[:, 0] == 0) | (xyz[:, 0] == shape[0]-1)
    if all_faces:
        for axis in [1, 2]:
            if shape[axis] > 1:
                contacts |= (xyz[:, axis] == 0) | (xyz[:, axis] == shape[axis]-1)
    free = ~contacts
    volume = np.prod(np.array([widths[a][xyz[:, a]] for a in range(3)]), axis=0)
    eps = EPS * (1 + .12*xyz[:, 1] + .08*xyz[:, 2])
    doping = .08*np.cos(xyz[:, 0])
    ni = (2. if mode == 'generation' else .3) * (1 + .02*xyz[:, 1])
    mu_n, mu_p = 1.5e-11, .8e-11
    cn, cp = (0., 0.) if mode == 'disabled' else (2.8e-43, 9.9e-44)
    tau_n = (3*dt if mode == 'mixed' else 1e100) * (1 + .04*xyz[:, 1])
    tau_p = (5*dt if mode == 'mixed' else 1e100) * (1 + .03*xyz[:, 2])
    generation = (.15/dt if mode == 'mixed' else 0.) * (1 + .05*xyz[:, 0])
    n0 = 1 + .025*xyz[:, 1]**2 + .015*xyz[:, 2]
    p0 = 1 + .015*xyz[:, 1] + .02*xyz[:, 2]**2
    n0[free] += .5
    p0[free] += .15

    # Assemble a separate node-centred graph from geometry, without accessing
    # the native sparse matrix or row scaling. Each undirected edge is stored once.
    strides = [1, shape[0], shape[0]*shape[1]]
    edges = []
    poisson = np.zeros((size, size))
    for idx, coord in enumerate(xyz):
        for axis in range(3):
            if coord[axis]+1 >= shape[axis]:
                continue
            neighbor = idx + strides[axis]
            distance = positions[axis][coord[axis]+1] - positions[axis][coord[axis]]
            wu, wv = widths[axis][coord[axis]], widths[axis][coord[axis]+1]
            harmonic_eps = 2*eps[idx]*eps[neighbor]/(eps[idx]+eps[neighbor])
            for row, other, width in [(idx, neighbor, wu), (neighbor, idx, wv)]:
                coefficient = harmonic_eps/(distance*width)
                poisson[row, row] += coefficient
                poisson[row, other] -= coefficient
            area = volume[idx]/wu
            edges.append((idx, neighbor, axis, distance, wu, wv, area))
    poisson[contacts, :] = 0.
    poisson[contacts, contacts] = 1.

    sim = PyDeviceSimulator(*shape, *spacing)
    sim.set_quantum_enabled(False)
    for x, setter in zip(positions, [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions]):
        setter(x)
    sim.set_permittivity(eps)
    sim.set_mobility(np.full(size, mu_n), np.full(size, mu_p))
    sim.set_doping(SCALE*doping)
    sim.set_effective_dos(SCALE*ni, SCALE*ni)
    sim.set_bandgap(np.zeros(size))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(tau_n, tau_p)
    sim.set_optical_generation(SCALE*generation)
    sim.set_auger_params(2.8e-43, 9.9e-44)
    sim.set_auger_enabled(mode != 'disabled')
    sim.set_dirichlet_potential({int(i): 0. for i in np.flatnonzero(contacts)})
    sim.set_electron_bc({int(i): float(SCALE*n0[i]) for i in np.flatnonzero(contacts)})
    sim.set_hole_bc({int(i): float(SCALE*p0[i]) for i in np.flatnonzero(contacts)})
    sim.set_initial_guess(np.zeros(size), SCALE*n0, SCALE*p0)
    sim.set_newton_use_log_space(log_space)
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-18)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(2.5*dt)
    sim.set_nonlinear_history_enabled(True)
    history = sim.solve_transient()
    assert len(history) == 4
    previous_n, previous_p, previous_charge = n0, p0, None
    max_poisson = max_balance = max_current_error = max_charge_defect = 0.
    omitted_auger_signal = []
    for step, state in enumerate(history):
        assert state['valid'] and state['converged'] and state['charge_ledger_available']
        assert not state['phi_frozen'] and not state['majority_frozen']
        assert state['initial_state'] == (step == 0)
        n, p, phi = state['n']/SCALE, state['p']/SCALE, state['phi']
        assert np.all(np.isfinite(n)) and np.all(np.isfinite(p)) and np.all(np.isfinite(phi))
        assert np.all(n > 0) and np.all(p > 0)
        np.testing.assert_array_equal(state['n'][contacts], (SCALE*n0)[contacts])
        np.testing.assert_array_equal(state['p'][contacts], (SCALE*p0)[contacts])
        np.testing.assert_array_equal(phi[contacts], np.zeros(np.count_nonzero(contacts)))
        rhs = QE*SCALE*(p-n+doping)
        rhs[contacts] = 0.
        expected_phi = np.linalg.solve(poisson, rhs)
        max_poisson = max(max_poisson, np.max(abs(phi-expected_phi))/VT)
        divergence_n, divergence_p = np.zeros(size), np.zeros(size)
        # [x-min, x-max, y-min, y-max, z-min, z-max], excluding inactive planes.
        full_currents = np.zeros(6)
        for u, v, axis, distance, wu, wv, area in edges:
            delta = (phi[v]-phi[u])/VT
            bpos, bneg = bernoulli(delta), bernoulli(-delta)
            fn = mu_n*VT/distance * (n[u]*bneg-n[v]*bpos)
            fp = mu_p*VT/distance * (p[u]*bpos-p[v]*bneg)
            divergence_n[u] += fn/wu
            divergence_n[v] -= fn/wv
            divergence_p[u] += fp/wu
            divergence_p[v] -= fp/wv
            charge_current = QE*SCALE*area*(-fn+fp)
            if contacts[u] and free[v]:
                full_currents[2*axis] += charge_current
            if free[u] and contacts[v]:
                full_currents[2*axis+1] -= charge_current
        active_planes = [2*a+side for a in range(3) if shape[a]>1 and (a==0 or all_faces)
                         for side in range(2)]
        currents = full_currents[active_planes]
        charge_scale = QE*SCALE*np.sum(volume[free])
        max_current_error = max(max_current_error,
                                np.max(abs(state['terminal_currents_A']-currents))*dt/charge_scale)
        charge = QE*SCALE*np.dot((p-n)[free], volume[free])
        assert abs(state['stored_charge_C']-charge)/charge_scale < 1e-12
        h = 0. if step == 0 else state['time_s']-history[step-1]['time_s']
        assert state['dt_s'] == pytest.approx(h, rel=1e-14)
        if h:
            rate = pair_rate(n, p, ni, cn, cp, tau_n, tau_p)
            rn = n-previous_n + h*(divergence_n+rate-generation)
            rp = p-previous_p + h*(divergence_p+rate-generation)
            max_balance = max(max_balance, np.max(abs(rn[free])), np.max(abs(rp[free])))
            max_charge_defect = max(max_charge_defect,
                                   abs(charge-previous_charge-h*sum(currents))/charge_scale)
            if mode != 'disabled':
                auger = h*SCALE**2*(cn*n+cp*p)*(n*p-ni*ni)
                omitted_auger_signal.append(float(np.max(abs(auger[free]))))
        else:
            np.testing.assert_array_equal(state['n'], SCALE*n0)
            np.testing.assert_array_equal(state['p'], SCALE*p0)
        previous_n, previous_p, previous_charge = n, p, charge
    if omitted_auger_signal:
        assert min(omitted_auger_signal) > 1e-3
    assert history[-1]['time_s'] == pytest.approx(2.5*dt, rel=1e-14)
    attempts = sim.get_transient_attempt_history()
    assert len(attempts) == 3 and all(a['accepted'] for a in attempts)
    assert all(t['solver']=='newton' for a in attempts for t in a['trials'])
    assert max(max_poisson, max_balance, max_current_error, max_charge_defect) < 1e-8
    print(json.dumps(dict(test='multidimensional_auger', shape=shape, all_faces=all_faces,
                         stretched=stretched, log_space=log_space, mode=mode, free_nodes=int(sum(free)),
                         steps=3, max_poisson=float(max_poisson), max_balance=float(max_balance),
                         max_current_error=float(max_current_error), max_charge_defect=float(max_charge_defect),
                         minimum_omitted_auger_signal=min(omitted_auger_signal) if omitted_auger_signal else None)))
