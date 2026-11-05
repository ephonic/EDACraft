"""Converged cold avalanche bars checked against independent FV equations."""
import os
import json
import numpy as np
import pytest
from tcad.core import native_constants
from test_newton_descent_fallback import cold_bar, H, VT
from test_ii_field_floor import thin_result

# II driving, II references, HFS enabled/driving/contact policy, HFS references.
MODELS = [
    (0, (0., 0.), False, 1, True, (0., 0.)),
    (1, (5e18, 8e18), False, 1, True, (0., 0.)),
    (0, (0., 0.), True, 1, True, (0., 0.)),
    (1, (5e18, 8e18), True, 0, False, (3e18, 4e18)),
]
COEFFICIENTS = [(10., 0., 20., 0.), (1e5, 2e5, 2e5, 3e5)]


def avalanche_bar(axis=0, ptype=False, bias=.2, policy='exponential',
                  model=MODELS[0], coefficients=COEFFICIENTS[0], budget=60):
    sim = cold_bar(axis, ptype, bias, budget=budget)
    mode, refs, hfs, driving, contacts, hfrefs = model
    sim.set_newton_log_density_update(policy)
    sim.set_ii_params(*coefficients)
    sim.set_ii_enabled(True)
    sim.set_ii_driving(mode)
    sim.set_ii_reference_density(*refs)
    sim.set_high_field_saturation(hfs, 5e4, 4e4, 2., 1., driving)
    sim.set_hfs_quasi_fermi_at_contacts(contacts)
    sim.set_high_field_reference_density(*hfrefs)
    return sim


def independent_balance(result, axis, ptype, bias, model, coefficients, tolerance=1e-8):
    phi, n, p = (np.asarray(result[key]) for key in ('phi', 'n', 'p'))
    assert np.all(np.isfinite(np.r_[phi, n, p]))
    assert np.all(n > 0) and np.all(p > 0)
    np.testing.assert_allclose(phi[[0, 8]], [bias, 0.], rtol=0., atol=1e-12)
    np.testing.assert_allclose(n[[0, 8]], 1e5 if ptype else 1e21, rtol=1e-10)
    np.testing.assert_allclose(p[[0, 8]], 1e21 if ptype else 1e5, rtol=1e-10)
    mode, refs, hfs, driving, contacts, hfrefs = model
    q = float(native_constants()['elementary_charge_C'])
    delta = np.diff(phi)/VT
    assert np.min(np.abs(delta)) > 1e-6
    bp = delta/np.expm1(delta); bm = -delta/np.expm1(-delta)
    forces = [np.abs(np.diff(phi))/H]*2
    if hfs and driving == 0:
        forces = [np.abs(np.diff(phi) + sign*VT*np.diff(np.log(c+ref)))/H
                  for c, ref, sign in [(n, hfrefs[0], -1.), (p, hfrefs[1], 1.)]]
        if not contacts:
            for force in forces: force[[0, 7]] = np.abs(np.diff(phi))[[0, 7]]/H
    dn = np.full(8, .1*VT/H); dp = np.full(8, .035*VT/H)
    if hfs:
        dn /= np.sqrt(1.+(.1*forces[0]/5e4)**2)
        dp /= 1.+.035*forces[1]/4e4
    jn = q*dn*(n[1:]*bp-n[:-1]*bm)
    jp = q*dp*(p[:-1]*bp-p[1:]*bm)
    label = 'xyz'[axis]
    np.testing.assert_allclose(result['Jn_'+label][:-1], jn, rtol=2e-11, atol=1e-8)
    np.testing.assert_allclose(result['Jp_'+label][:-1], jp, rtol=2e-11, atol=1e-8)
    assert np.ptp(jn+jp)/np.max(np.abs(jn+jp)) < tolerance
    edge = np.zeros(8)
    for c, ref, sign, a, b, current in [
        (n, refs[0], -1., *coefficients[:2], jn),
        (p, refs[1], 1., *coefficients[2:], jp),
    ]:
        force = np.abs(np.diff(phi) + (sign*VT*np.diff(np.log(c+ref)) if mode else 0.))/H
        alpha = np.zeros(8); active = force >= 1e5
        alpha[active] = a*np.exp(-b/force[active])
        edge += alpha*np.abs(current)/q
    generation = np.zeros(9);generation[:-1] += .5*edge;generation[1:] += .5*edge
    assert np.max(generation) > 0.
    np.testing.assert_allclose(result['G_ii'], generation, rtol=2e-11, atol=0.)
    eps = 8.854187817e-12*11.7;doping = -1e21 if ptype else 1e21
    diagonal = 2*eps/H**2*phi[1:-1]
    neighbors = eps/H**2*(phi[:-2]+phi[2:])
    charge = q*(n[1:-1]-p[1:-1]-doping)
    assert np.max(np.abs(diagonal-neighbors+charge)/(
        np.abs(diagonal)+np.abs(neighbors)+q*(n[1:-1]+p[1:-1]+abs(doping)))) < tolerance
    ni = np.sqrt(2.8e25*1.04e25)*np.exp(-1.12/(2*8.617333262e-5*300))
    srh = (n[1:-1]*p[1:-1]-ni**2)/(1e-7*(n[1:-1]+p[1:-1]+2*ni))
    source = (srh-generation[1:-1])*H
    for c, d, plus, minus in [(n, dn, bm, bp), (p, dp, bp, bm)]:
        diagonal = (d[:-1]*minus[:-1]+d[1:]*plus[1:])*c[1:-1]
        neighbors = d[:-1]*plus[:-1]*c[:-2]+d[1:]*minus[1:]*c[2:]
        assert np.max(np.abs(diagonal-neighbors+source)/(
            np.abs(diagonal)+np.abs(neighbors)+np.abs(source))) < tolerance


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('policy,ptype,bias', [
    ('exponential', False, -.2), ('exponential', False, .2),
    ('exponential', True, -.2), ('exponential', True, .2),
    ('additive', False, .2), ('additive', True, -.2),
])
@pytest.mark.parametrize('model', MODELS[:2])
def test_cold_avalanche_converges_and_satisfies_equations(axis, ptype, bias, policy, model):
    # The broader HFS/high-generation/reversed additive exploration is retained
    # in stage 366 artifacts; those cases have not acquired convergence status.
    coefficients = COEFFICIENTS[0]
    result = avalanche_bar(axis, ptype, bias, policy, model, coefficients).solve()
    assert result['converged']
    independent_balance(result, axis, ptype, bias, model, coefficients)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('budget', [0, 1])
@pytest.mark.parametrize('policy', ['exponential', 'additive'])
def test_insufficient_avalanche_budget_is_honest_failure(axis, budget, policy):
    r = avalanche_bar(axis=axis, policy=policy, budget=budget).solve()
    assert not r['converged']
    assert all(np.all(np.isfinite(r[key])) for key in ('phi', 'n', 'p'))


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('policy', ['exponential', 'additive'])
def test_disabled_or_zero_ii_preserves_frozen_parent(axis, ptype, bias, policy):
    with open(os.environ['TCAD_II_NEWTON_ORACLE'], encoding='utf8') as f:
        expected = json.load(f)[str((axis, ptype, bias, policy))]
    # Stage 367 replaces the exponential zero-II failure snapshots with
    # closed-II equivalence and independent equations in test_zero_ii_descent.
    # Disabled II and the unchanged additive policy keep their frozen states.
    for zero in ([False, True] if policy == 'additive' else [False]):
        sim = cold_bar(axis, ptype, bias)
        sim.set_newton_log_density_update(policy)
        if zero:
            sim.set_ii_params(0., 0., 0., 0.);sim.set_ii_enabled(True)
        assert thin_result(sim.solve()) == expected[str(zero)]


@pytest.mark.parametrize('tolerance', [None, 1e-8])
def test_original_stall_and_explicit_default_have_same_converged_state(tolerance):
    # Replaces the old frozen snapshot of a failed II-enabled Newton solve.
    from test_transport_parameter_guard import resistor
    states = []
    for explicit in [False, True]:
        _, sim = resistor()
        sim.set_use_newton(True);sim.set_newton_primary(True)
        if tolerance is not None:sim.set_tolerance(tolerance)
        sim.set_ii_params(*COEFFICIENTS[0]);sim.set_ii_enabled(True)
        if explicit:sim.set_ii_field_floor(1e5)
        r = sim.solve();assert r['converged']
        independent_balance(r, 0, False, .2, MODELS[0], COEFFICIENTS[0],
                            1e-6 if tolerance is None else tolerance)
        states.append(thin_result(r))
    assert states[0] == states[1]
