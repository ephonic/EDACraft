"""Zero mobile seeds must satisfy physical equations, including tiny SRH generation."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants

VT = .025852
NI = 1e3 * np.exp(-1.12 / (2 * 8.617333262e-5 * 300))
EPS = 11.7 * 8.854187817e-12
MU = 2e-18 / (2e-9 + 1e-30)


def bernoulli(v):
    return v / np.expm1(v) if abs(v) > 1e-7 else 1-v/2+v*v/12


def configured(axis, mesh, source, zero_species=0, budget=100):
    shape = [1, 1, 1]; shape[axis] = 9
    sim = PyDeviceSimulator(*shape, 1e-9, 1e-9, 1e-9)
    x = np.array([0., .35, 1.1, 1.8, 3., 4.5, 5.8, 7.1, 8.])*1e-9 if mesh else np.arange(9)*1e-9
    if mesh: getattr(sim, 'set_'+'xyz'[axis]+'_positions')(x)
    sim.set_quantum_enabled(False)
    sim.set_thermal_voltage(VT)
    sim.set_permittivity(np.full(9, EPS)); sim.set_doping(np.zeros(9))
    sim.set_mobility(np.full(9, 1e-9), np.full(9, 1e-9))
    sim.set_effective_dos(np.full(9, 1e3), np.full(9, 1e3))
    sim.set_bandgap(np.full(9, 1.12))
    sim.set_recombination(np.full(9, 1e-7), np.full(9, 1e-7))
    sim.set_dirichlet_potential({0: 4., 8: 0.})
    sim.set_electron_bc({0: 0., 8: 0.}); sim.set_hole_bc({0: 0., 8: 0.})
    n = np.zeros(9); p = np.zeros(9)
    if zero_species == 1: p[1:-1] = 1e-8
    if zero_species == 2: n[1:-1] = 1e-8
    seed = (4*(1-x/x[-1]), n, p)
    sim.set_initial_guess(*seed)
    sim.set_btbt_enabled(True); sim.set_btbt_use_nonlocal(source == 'nonlocal_export')
    sim.set_btbt_params(1e-4, 2e9, 2.)
    sim.set_btbt_continuity_scale(.1 if source == 'kane' else 0.)
    sim.set_btbt_nonlocal_params(.2, 32); sim.set_btbt_nonlocal_mass(.25)
    sim.set_use_newton(True); sim.set_newton_primary(True)
    sim.set_nonlinear_history_enabled(True)
    sim.set_gummel_max_iter(budget); sim.set_tolerance(1e-11)
    return sim, x, seed


def generation(phi, x):
    # Local quadratic interpolation at interior nodes, independent of the core.
    e = abs(np.gradient(phi, x, edge_order=2))
    e[0] = abs((phi[1]-phi[0])/(x[1]-x[0]))
    e[-1] = abs((phi[-1]-phi[-2])/(x[-1]-x[-2]))
    return 100*e*e*np.exp(-2e9/np.maximum(e, 1.))


def srh(n, p):
    return (n*p-NI*NI)/(1e-7*(n+p+2*NI))


def carrier_matrix(phi, x, sign):
    a = np.zeros((7, 7)); h = np.diff(x)
    for row, i in enumerate(range(1, 8)):
        for j, edge in [(i-1, i-1), (i+1, i)]:
            d = sign*(phi[j]-phi[i])/VT
            rate = MU*VT/h[edge]
            a[row, row] += rate*bernoulli(-d)
            if 0 < j < 8: a[row, j-1] -= rate*bernoulli(d)
    return a


def reference(x, source):
    # Fixed-point solution of two independent dense SG systems plus Poisson.
    # This deliberately does not use the native Newton assembly or solver.
    phi = 4*(1-x/x[-1]); n = np.zeros(9); p = np.zeros(9)
    width = (x[2:]-x[:-2])/2; h = np.diff(x)
    k = np.zeros((7, 7))
    for row in range(7):
        k[row, row] = EPS*(1/h[row]+1/h[row+1])
        if row: k[row, row-1] = -EPS/h[row]
        if row < 6: k[row, row+1] = -EPS/h[row+1]
    q = float(native_constants()['elementary_charge_C'])
    for _ in range(100):
        g = .1*generation(phi, x) if source == 'kane' else np.zeros(9)
        rhs = (g[1:-1]-srh(n, p)[1:-1])*width
        nn = np.r_[0., np.linalg.solve(carrier_matrix(phi, x, 1), rhs), 0.]
        pp = np.r_[0., np.linalg.solve(carrier_matrix(phi, x, -1), rhs), 0.]
        change = max(np.max(abs(nn[1:-1]-n[1:-1])/np.maximum(abs(nn[1:-1]), 1e-300)),
                     np.max(abs(pp[1:-1]-p[1:-1])/np.maximum(abs(pp[1:-1]), 1e-300)))
        n, p = nn, pp
        phi = 4*(1-x/x[-1]); phi[1:-1] += np.linalg.solve(k, q*(p-n)[1:-1]*width)
        if change < 1e-14: return phi, n, p
    raise AssertionError('independent fixed-point reference failed')


def errors(state, x, source):
    phi, n, p = [np.asarray(state[k], dtype=float) for k in ['phi', 'n', 'p']]
    expected = reference(x, source); width = (x[2:]-x[:-2])/2
    g = .1*generation(phi, x) if source == 'kane' else np.zeros(9)
    r = srh(n, p); defects = []
    for density, sign in [(n, 1), (p, -1)]:
        for i in range(1, 8):
            terms = []
            for j in [i-1, i+1]:
                d = sign*(phi[j]-phi[i])/VT
                terms.append(MU*VT/abs(x[j]-x[i])*(density[i]*bernoulli(-d)-density[j]*bernoulli(d))/width[i-1])
            defects.append(abs(sum(terms)+r[i]-g[i])/max(1e-300, abs(r[i]), abs(g[i]), *(abs(v) for v in terms)))
    currents = []
    for i in range(8):
        d = (phi[i+1]-phi[i])/VT; rate = MU*VT/(x[i+1]-x[i])
        currents.append(rate*(n[i+1]*bernoulli(d)-n[i]*bernoulli(-d)+p[i]*bernoulli(d)-p[i+1]*bernoulli(-d)))
    kcl = np.ptp(currents)/max(1e-300, np.max(abs(np.asarray(currents))))
    return dict(continuity_relative=max(defects), current_relative=float(kcl),
                potential_reference=float(np.max(abs(phi-expected[0]))),
                electron_reference=float(np.max(abs(n[1:-1]/expected[1][1:-1]-1))),
                hole_reference=float(np.max(abs(p[1:-1]/expected[2][1:-1]-1))))


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('mesh', [0, 1])
@pytest.mark.parametrize('source', ['srh', 'kane', 'nonlocal_export'])
@pytest.mark.parametrize('zero_species', [0, 1, 2])
def test_zero_population_newton_matches_independent_transport(axis, mesh, source, zero_species):
    sim, x, _ = configured(axis, mesh, source, zero_species)
    state = sim.solve()
    assert state['converged']
    assert any(s['solver'] == 'newton' and s['converged'] for s in state['nonlinear_history'])
    for key in ['n', 'p']:
        assert np.all(np.isfinite(state[key])) and np.all(state[key] >= 0)
        assert state[key][0] == state[key][-1] == 0
    assert max(errors(state, x, source).values()) < 2e-8


def test_guard_rejection_allows_zero_population_local_retry():
    # x-1D feedback is supported; the y-directed route remains guarded.
    sim, x, _ = configured(1, 0, 'nonlocal_export')
    sim.set_btbt_continuity_scale(.1)
    with pytest.raises(ValueError, match='Newton-primary nonlocal BTBT feedback is unsupported'):
        sim.solve()
    sim.set_btbt_use_nonlocal(False)
    state = sim.solve(); assert state['converged']
    assert max(errors(state, x, 'kane').values()) < 2e-8
    fresh, _, _ = configured(1, 0, 'kane')
    control = fresh.solve()
    for key in ['phi', 'n', 'p', 'G_btbt']:
        np.testing.assert_array_equal(state[key], control[key])


def test_zero_iteration_budget_does_not_claim_convergence():
    sim, _, _ = configured(0, 0, 'kane', budget=0)
    assert not sim.solve()['converged']
