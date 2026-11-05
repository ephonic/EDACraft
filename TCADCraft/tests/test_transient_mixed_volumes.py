"""Independent full-node FV transport through insulating layers and obstacles."""
from copy import deepcopy

import numpy as np
import pytest
from scipy.optimize import root

from test_transient_multidimensional_ledger import experiment, QE
from test_mobile_charge_scope import charge_audit
from test_transient_selfconsistent import VT, EPS


CASES = [
    ((5, 5, 1), 0, 1), ((5, 1, 5), 0, 2),
    ((5, 5, 1), 1, 0), ((1, 5, 5), 2, 1),
    ((4, 4, 3), 0, -1), ((3, 4, 4), 2, -1),
]
SCALE = 1e16


def mixed_device(case, stretched, log_space, coupled):
    shape, contact_axis, blocked_axis = case
    planes = [(contact_axis, False), (contact_axis, True)]
    sim, xyz, axes, widths, contacts, n, p = experiment(shape, planes, stretched)
    transverse = [a for a in range(3) if a != contact_axis]
    if blocked_axis >= 0:
        blocked = xyz[:, blocked_axis] < 2
    else:
        # An entire blocking surface plus an interior step: active face areas
        # change along the conducting direction, unlike an extruded channel.
        a, b = transverse
        blocked = (xyz[:, a] == 0) | ((xyz[:, a] == 1) &
                    (xyz[:, b] == 1) & (xyz[:, contact_axis] == 1))
    n[blocked] = p[blocked] = 0.
    mu_n = (~blocked) * (.07 + .003 * xyz.sum(axis=1))
    mu_p = (~blocked) * (.04 + .002 * xyz.sum(axis=1))
    generation = (~blocked) * (SCALE * 2e8 if coupled else 0.)
    tau = np.where(blocked | (not coupled), 1e100, 2e-10)
    sim.set_mobility(mu_n, mu_p)
    sim.set_optical_generation(generation)
    sim.set_recombination(tau, tau)
    sim.set_initial_guess(np.zeros(len(n)), n, p)
    sim.set_electron_bc({int(i): float(n[i]) for i in np.flatnonzero(contacts)})
    sim.set_hole_bc({int(i): float(p[i]) for i in np.flatnonzero(contacts)})
    sim.set_newton_freeze_phi(not coupled)
    sim.set_newton_use_log_space(log_space)
    sim.set_tolerance(1e-12)
    edges = []
    strides = [1, shape[0], shape[0] * shape[1]]
    for i, coord in enumerate(xyz):
        for axis in range(3):
            if coord[axis] + 1 < shape[axis]:
                j = i + strides[axis]
                distance = axes[axis][coord[axis] + 1] - axes[axis][coord[axis]]
                area = np.prod([widths[a][coord[a]] for a in range(3) if a != axis])
                edges.append((i, j, distance, area))
    i, j, distance, area = np.array(edges).T
    i = i.astype(int); j = j.astype(int)
    volume = np.prod([widths[a][xyz[:, a]] for a in range(3)], axis=0)
    return sim, dict(shape=shape, contacts=contacts, blocked=blocked,
        n=n / SCALE, p=p / SCALE, mu_n=mu_n, mu_p=mu_p,
        generation=generation / SCALE, tau=tau, i=i, j=j,
        distance=distance, area=area, volume=volume, coupled=coupled)


def bernoulli(x):
    # Independently evaluate B with its convergent origin series.
    small = np.abs(x) < 1e-4
    result = np.empty_like(x)
    u = x[small]
    result[small] = 1-u/2+u*u/12-u**4/720+u**6/30240
    result[~small] = x[~small] / np.expm1(x[~small])
    return result


def face_rates(spec, phi, n, p):
    i, j = spec['i'], spec['j']
    u = (phi[j] - phi[i]) / VT
    bp, bm = bernoulli(u), bernoulli(-u)
    rates = []
    for mobility, density, first, second in [
        (spec['mu_n'], n, bm, bp), (spec['mu_p'], p, bp, bm),
    ]:
        denominator = mobility[i] + mobility[j]
        mu = np.divide(2*mobility[i]*mobility[j], denominator,
                       out=np.zeros_like(denominator), where=denominator > 0)
        rates.append(mu * VT * spec['area'] / spec['distance'] *
                     (density[i]*first - density[j]*second))
    return rates


def reference_step(spec, previous, dt):
    n0, p0 = previous[1:]
    size = len(n0); i, j = spec['i'], spec['j']
    contacts, blocked = spec['contacts'], spec['blocked']
    fixed = contacts | blocked
    poisson = np.zeros((size, size))
    coefficients = EPS * spec['area'] / spec['distance']
    np.add.at(poisson, (i, i), coefficients)
    np.add.at(poisson, (j, j), coefficients)
    np.add.at(poisson, (i, j), -coefficients)
    np.add.at(poisson, (j, i), -coefficients)
    poisson /= (QE * SCALE * spec['volume'][:, None])
    poisson[contacts] = np.eye(size)[contacts] / VT

    def residual(x):
        phi, n, p = x.reshape(3, size)
        fp = poisson @ phi - (p - n)
        fp[contacts] = phi[contacts] / VT
        if not spec['coupled']:
            fp = phi / VT
        fn, fh = n - n0, p - p0
        if dt:
            rn, rp = face_rates(spec, phi, n, p)
            for f, rate in [(fn, rn), (fh, rp)]:
                np.add.at(f, i, dt * rate / spec['volume'][i])
                np.add.at(f, j, -dt * rate / spec['volume'][j])
            recombination = SCALE * (n*p-1) / (
                spec['tau'] * SCALE * (n+p+2))
            source = spec['generation'] - recombination
            fn -= dt * source; fh -= dt * source
        fn[fixed] = n[fixed] - spec['n'][fixed]
        fh[fixed] = p[fixed] - spec['p'][fixed]
        return np.r_[fp, fn, fh]

    initial = np.concatenate(previous)
    solved = root(residual, initial, tol=1e-10)
    assert np.max(np.abs(residual(solved.x))) < 1e-9, solved.message
    return tuple(solved.x.reshape(3, size))


def check_history(states, spec):
    expected = (np.zeros(len(spec['n'])), spec['n'].copy(), spec['p'].copy())
    max_density_error = max_phi_error = 0.
    for state in states:
        assert state['valid'] and state['converged']
        expected = reference_step(spec, expected, state['dt_s'])
        phi, n, p = expected
        error = max(np.max(np.abs(state['n']/SCALE-n)),
                    np.max(np.abs(state['p']/SCALE-p)))
        max_density_error = max(max_density_error, float(error))
        max_phi_error = max(max_phi_error, float(np.max(np.abs(state['phi']-phi))))
        np.testing.assert_allclose(state['n']/SCALE, n, rtol=2e-7, atol=1e-12)
        np.testing.assert_allclose(state['p']/SCALE, p, rtol=2e-7, atol=1e-12)
        np.testing.assert_allclose(state['phi'], phi, rtol=2e-7, atol=1e-11)
        assert state['charge_ledger_available']
        free = ~spec['contacts']
        q = QE * np.dot((state['p']-state['n'])[free], spec['volume'][free])
        assert state['stored_charge_C'] == pytest.approx(q, rel=2e-12, abs=1e-40)
        rn, rp = face_rates(spec, state['phi'], state['n']/SCALE, state['p']/SCALE)
        current = QE*SCALE*(-rn+rp)
        i, j = spec['i'], spec['j']
        left = spec['contacts'][i] & ~spec['contacts'][j]
        right = ~spec['contacts'][i] & spec['contacts'][j]
        expected_current = [current[left].sum(), -current[right].sum()]
        np.testing.assert_allclose(state['terminal_currents_A'], expected_current,
                                   rtol=2e-9, atol=1e-28)
    verdict = charge_audit(states)
    assert verdict.passed, verdict.message
    altered = deepcopy(states)
    altered[-1]['terminal_currents_A'] *= 1.2
    assert not charge_audit(altered).passed
    if spec['coupled']:
        assert np.max(np.abs(states[-1]['phi']-states[0]['phi'])) > 1e-8
    return dict(density_scaled_error=max_density_error, phi_absolute_error_V=max_phi_error,
                charge_audit=verdict.details)


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('coupled', [False, True])
def test_mixed_node_volumes_match_independent_poisson_sg_be(
        case, stretched, log_space, coupled):
    sim, spec = mixed_device(case, stretched, log_space, coupled)
    states = sim.solve_transient()
    assert len(states) == 4
    check_history(states, spec)
