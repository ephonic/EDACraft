"""Avalanche cutoff forwarding, returned sources and Newton residuals."""
import json
import os
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants
from test_native_nonlinear_history import make_transport
from test_transport_parameter_guard import resistor, same_solution


BAD = [-1., 0., np.nan, np.inf, -np.inf, True, np.bool_(False),
       '1e5', None, 1+2j, [], object()]
FLOORS = [2e5, 3.5e5, 6e5]
PHI = np.array([0., .025, .07])
N = 1e19*np.array([1., 1.6, 1.])
P = 1e19*np.array([1., 1.1, 1.])


def bar(axis=0, primary=False, budget=0):
    sim = make_transport(axis=axis, primary=primary, budget=budget)
    sim.set_dirichlet_potential({0: PHI[0], 2: PHI[-1]})
    sim.set_initial_guess(PHI, N, P)
    sim.set_ii_params(1e5, 2e5, 2e5, 3e5)
    sim.set_ii_enabled(True)
    sim.set_nonlinear_history_enabled(True)
    return sim


def edge_reference(phi, n, p, spacing=1e-7):
    q = float(native_constants()['elementary_charge_C'])
    delta = np.diff(phi)/.02585
    bp = delta/np.expm1(delta)
    bm = -delta/np.expm1(-delta)
    jn = q*.1*.02585/spacing*(n[:-1]*bm-n[1:]*bp)
    jp = q*.05*.02585/spacing*(p[:-1]*bp-p[1:]*bm)
    return jn, jp, bp, bm


def generation(phi, jn, jp, floor, spacing=1e-7):
    q = float(native_constants()['elementary_charge_C'])
    field = np.abs(np.diff(phi)/spacing)
    an = np.where(field >= floor, 1e5*np.exp(-2e5/field), 0.)
    ap = np.where(field >= floor, 2e5*np.exp(-3e5/field), 0.)
    half = .5*(an*np.abs(jn)+ap*np.abs(jp))/q
    return np.r_[half[0], half.sum(), half[-1]]


@pytest.mark.parametrize('public', [False, True])
@pytest.mark.parametrize('bad', BAD)
def test_invalid_floor_is_atomic(public, bad):
    owner, sim = resistor(public=public)
    _, pristine = resistor()
    api = owner if public else sim
    for backend in (sim, pristine):
        backend.set_ii_params(10., 0., 20., 0.)
        backend.set_ii_enabled(True)
        backend.set_ii_field_floor(1e5)
    before = repr(owner.configuration_snapshot()) if public else None
    with pytest.raises(ValueError, match='(field floor|E_floor)'):
        api.set_ii_field_floor(bad)
    assert api.get_ii_field_floor() == 1e5
    if public:
        assert repr(owner.configuration_snapshot()) == before
    same_solution(pristine, sim)


@pytest.mark.parametrize('public', [False, True])
@pytest.mark.parametrize('value', [1, 2., np.int64(3), np.float64(4), np.float32(5), np.uint64(6)])
def test_accepts_real_numeric_types(public, value):
    owner, sim = resistor(public=public)
    api = owner if public else sim
    assert api.get_ii_field_floor() == 1e5
    api.set_ii_field_floor(value)
    assert api.get_ii_field_floor() == float(value)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('floor', FLOORS)
def test_gummel_source_and_audit_match_independent_edges(axis, floor):
    sim = bar(axis)
    sim.set_ii_field_floor(floor)
    r = sim.solve()
    assert not r['converged']  # Zero iteration returned-state operator check.
    # Gummel can perform a final continuity polish even with zero outer
    # iterations. Reconstruct the operator at its actual returned state.
    phi, n, p = r['phi'], r['n'], r['p']
    jn, jp, bp, bm = edge_reference(phi, n, p)
    label = 'xyz'[axis]
    # The public Jn is conventional current, opposite to electron particle flux.
    np.testing.assert_allclose(r['Jn_'+label][:2], -jn, rtol=5e-13)
    np.testing.assert_allclose(r['Jp_'+label][:2], jp, rtol=5e-13)
    expected = generation(phi, jn, jp, floor)
    np.testing.assert_allclose(r['G_ii'], expected, rtol=5e-13, atol=0.)
    if floor == 6e5:
        assert not np.any(r['G_ii'])
    else:
        assert r['G_ii'][1] > 0
    audit = r['steady_equation_audit']
    assert audit['available']
    for carrier, mu, plus, minus, name in [(n, .1, bm, bp, 'electron'),
                                          (p, .05, bp, bm, 'hole')]:
        d = mu*.02585/1e-7
        diagonal = d*(minus[0]+plus[1])*carrier[1]
        neighbors = d*(plus[0]*carrier[0]+minus[1]*carrier[2])
        rhs = expected[1]*1e-7
        backward = abs(diagonal-neighbors-rhs)/(abs(diagonal)+abs(neighbors)+abs(rhs))
        assert audit[name+'_backward_error_linf'] == pytest.approx(backward, rel=2e-12, abs=2e-15)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('floor', FLOORS)
def test_newton_initial_residual_uses_configured_floor(axis, floor):
    sim = bar(axis, primary=True, budget=1)
    sim.set_ii_field_floor(floor)
    r = sim.solve()
    stage, = r['nonlinear_history']
    assert stage['solver'] == 'newton' and len(stage['raw_n_l2']) == 1
    jn, jp, _, _ = edge_reference(PHI, N, P)
    g = generation(PHI, jn, jp, floor)
    q = float(native_constants()['elementary_charge_C'])
    for current, name in [(jn,'n'), (jp,'p')]:
        expected = abs((current[1]-current[0])/q-g[1]*1e-7)
        assert stage['raw_'+name+'_l2'][0] == pytest.approx(expected, rel=2e-12)


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_cutoff_equality_is_active_and_next_float_is_inactive(axis):
    shape = [1, 1, 1]; shape[axis] = 3
    sim = PyDeviceSimulator(*shape, .125, .125, .125)
    sim.set_mobility(np.full(3,.1), np.full(3,.05))
    sim.set_initial_guess(np.array([0.,.25,.5]), np.full(3,1e19), np.full(3,1e19))
    sim.set_gummel_max_iter(0)
    sim.set_ii_enabled(True)
    sim.set_ii_params(1.,0.,1.,0.)
    sim.set_ii_field_floor(2.)
    active = sim.solve()
    assert np.all(active['G_ii'] > 0.)
    sim.set_ii_field_floor(np.nextafter(2., np.inf))
    assert not np.any(sim.solve()['G_ii'])


def thin_result(r):
    keys = ['phi','n','p','G_ii']+['J'+c+'_'+axis for c in 'np' for axis in 'xyz']
    return dict(arrays={key:np.asarray(r[key]).tolist() for key in keys},
                converged=bool(r['converged']),iterations=int(r['iterations']),
                audit=r['steady_equation_audit'])


def default_case(case):
    if case.startswith('bar_'):
        _, axis, primary = case.split('_')
        return bar(int(axis), bool(int(primary)), budget=1)
    _, sim = resistor()
    sim.set_ii_params(10.,0.,20.,0.); sim.set_ii_enabled(True)
    if case == 'resistor_newton':
        sim.set_use_newton(True);sim.set_newton_primary(True)
    return sim


# The old resistor_newton snapshot encoded non-convergence. Stage 366 replaces
# that one leaf with independent converged equations in test_ii_newton_merit.py.
DEFAULT_CASES = ['bar_'+str(axis)+'_'+str(primary) for axis in range(3) for primary in range(2)]+['resistor_gummel']


@pytest.mark.parametrize('case', DEFAULT_CASES)
def test_default_matches_frozen_parent_and_explicit_default(case):
    with open(os.environ['TCAD_II_FLOOR_BASELINE'], encoding='utf8') as f:
        baseline = json.load(f)['cases'][case]
    implicit, explicit = default_case(case), default_case(case)
    explicit.set_ii_field_floor(1e5)
    a,b = thin_result(implicit.solve()), thin_result(explicit.solve())
    assert a == b == baseline
    # The frozen parent stalls for this resistor's Newton initial guess,
    # including with avalanche disabled. Its exact behavior is preserved here;
    # only the Gummel case supplies a converged-solution qualification.
    if case == 'resistor_gummel':
        assert a['converged']


def test_public_recipe_replays_floor_and_rejection_does_not_record():
    a, _ = resistor(public=True);b, _ = resistor(public=True)
    a.set_ii_field_floor(3e5)
    recipe = a.configuration_snapshot()[-1]
    assert recipe == ('python','set_ii_field_floor',{'floor':3e5})
    before = repr(a.configuration_snapshot())
    with pytest.raises(ValueError):a.set_ii_field_floor(0.)
    assert repr(a.configuration_snapshot()) == before
    getattr(b, recipe[1])(**recipe[2])
    assert b.get_ii_field_floor() == a.get_ii_field_floor() == 3e5
    same_solution(a._sim,b._sim)


@pytest.mark.parametrize('primary', [False, True])
def test_disabled_ii_preserves_solution_with_nondefault_floor(primary):
    a,b = default_case('resistor_newton' if primary else 'resistor_gummel'),default_case('resistor_newton' if primary else 'resistor_gummel')
    for sim in (a,b):sim.set_ii_enabled(False)
    b.set_ii_field_floor(6e5)
    assert thin_result(a.solve()) == thin_result(b.solve())
