"""HFS cutoff: atomic configuration, independent SG operators and defaults."""
import json
import os
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants
from test_native_nonlinear_history import make_transport
from test_transport_parameter_guard import resistor, same_solution
from test_ii_field_floor import PHI, N, P, thin_result

BAD = [-1., np.nan, np.inf, -np.inf, True, np.bool_(False), '1',
       None, 1+2j, [], object()]


def bar(axis=0, primary=False, driving=0):
    sim = make_transport(axis=axis, primary=primary, budget=1 if primary else 0)
    sim.set_dirichlet_potential({0: PHI[0], 2: PHI[-1]})
    sim.set_initial_guess(PHI, N, P)
    sim.set_high_field_saturation(True, 5e4, 4e4, 2., 1., driving)
    sim.set_nonlinear_history_enabled(True)
    return sim


def reference(phi, n, p, driving, cutoff, spacing=1e-7):
    vt = .02585
    q = float(native_constants()['elementary_charge_C'])
    delta = np.diff(phi)/vt
    bp, bm = delta/np.expm1(delta), -delta/np.expm1(-delta)
    mn, mp = [], []
    for carrier, mu, vsat, beta, sign, dest in [
            (n, .1, 5e4, 2., -1., mn), (p, .05, 4e4, 1., 1., mp)]:
        potential = phi if driving == 1 else phi+sign*vt*np.log(carrier/1e19)
        force = np.abs(np.diff(potential))/spacing
        active = np.where(force < cutoff, 0., force)
        dest.extend(mu/(1.+(mu*active/vsat)**beta)**(1./beta))
    dn, dp = np.array(mn)*vt/spacing, np.array(mp)*vt/spacing
    jn = q*dn*(n[1:]*bp-n[:-1]*bm)
    jp = q*dp*(p[:-1]*bp-p[1:]*bm)
    return jn, jp, dn, dp, bp, bm


@pytest.mark.parametrize('public', [False, True])
@pytest.mark.parametrize('bad', BAD)
def test_invalid_cutoff_is_atomic(public, bad):
    owner, sim = resistor(public=public)
    _, pristine = resistor()
    api = owner if public else sim
    for b in (sim, pristine):
        b.set_high_field_saturation(True, 5e4, 4e4, 2., 1., 1)
        b.set_hfs_low_field_cutoff(3e5)
    before = repr(owner.configuration_snapshot()) if public else None
    with pytest.raises(ValueError, match='low-field cutoff'):
        api.set_hfs_low_field_cutoff(bad)
    assert api.get_hfs_low_field_cutoff() == 3e5
    if public:
        assert repr(owner.configuration_snapshot()) == before
    same_solution(pristine, sim)


@pytest.mark.parametrize('public', [False, True])
@pytest.mark.parametrize('value', [0, 2., np.int64(3), np.float64(4), np.float32(5)])
def test_real_numeric_values_and_default(public, value):
    owner, sim = resistor(public=public)
    api = owner if public else sim
    assert api.get_hfs_low_field_cutoff() == 0.
    api.set_hfs_low_field_cutoff(value)
    assert api.get_hfs_low_field_cutoff() == float(value)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('cutoff', [0., 3e5, 1e6])
def test_returned_currents_and_gummel_audit(axis, driving, cutoff):
    sim = bar(axis, driving=driving)
    sim.set_hfs_low_field_cutoff(cutoff)
    r = sim.solve()
    assert not r['converged']  # Returned operator, not a converged solution.
    jn, jp, dn, dp, bp, bm = reference(r['phi'], r['n'], r['p'], driving, cutoff)
    label = 'xyz'[axis]
    np.testing.assert_allclose(r['Jn_'+label][:2], jn, rtol=5e-13)
    np.testing.assert_allclose(r['Jp_'+label][:2], jp, rtol=5e-13)
    audit = r['steady_equation_audit']
    assert audit['available']
    for carrier, diffusion, plus, minus, name in [
            (r['n'], dn, bm, bp, 'electron'), (r['p'], dp, bp, bm, 'hole')]:
        diagonal = (diffusion[0]*minus[0]+diffusion[1]*plus[1])*carrier[1]
        neighbors = diffusion[0]*plus[0]*carrier[0]+diffusion[1]*minus[1]*carrier[2]
        backward = abs(diagonal-neighbors)/(abs(diagonal)+abs(neighbors))
        assert audit[name+'_backward_error_linf'] == pytest.approx(backward, rel=2e-11, abs=2e-15)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('cutoff', [0., 3e5, 1e6])
def test_newton_initial_residual(axis, driving, cutoff):
    sim = bar(axis, primary=True, driving=driving)
    sim.set_hfs_low_field_cutoff(cutoff)
    r = sim.solve()
    stage, = r['nonlinear_history']
    assert stage['solver'] == 'newton' and len(stage['raw_n_l2']) == 1
    jn, jp, *_ = reference(PHI, N, P, driving, cutoff)
    q = float(native_constants()['elementary_charge_C'])
    for current, name in [(jn, 'n'), (jp, 'p')]:
        assert stage['raw_'+name+'_l2'][0] == pytest.approx(abs(np.diff(current)[0]/q), rel=2e-12)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
def test_equality_is_active_next_float_is_inactive(axis, driving):
    shape = [1, 1, 1]; shape[axis] = 3
    def solve(cutoff):
        sim = PyDeviceSimulator(*shape, .125, .125, .125)
        sim.set_mobility(np.full(3, .1), np.full(3, .05))
        # Pin every carrier node: a zero-budget Gummel solve without carrier
        # BCs otherwise initializes the returned density to its 1e6 floor.
        # log(carrier/DOS)=0 then makes the driving force exactly 2 V/m.
        sim.set_effective_dos(np.full(3, 1e19), np.full(3, 1e19))
        sim.set_electron_bc({i: 1e19 for i in range(3)})
        sim.set_hole_bc({i: 1e19 for i in range(3)})
        sim.set_initial_guess(np.array([0., .25, .5]), np.full(3, 1e19), np.full(3, 1e19))
        sim.set_gummel_max_iter(0)
        sim.set_high_field_saturation(True, 1., 1., 2., 1., driving)
        sim.set_hfs_low_field_cutoff(cutoff)
        return sim.solve()
    a, b = solve(2.), solve(np.nextafter(2., np.inf))
    for result in (a, b):
        np.testing.assert_array_equal(result['n'], np.full(3, 1e19))
        np.testing.assert_array_equal(result['p'], np.full(3, 1e19))
    label = 'xyz'[axis]
    for carrier, mu, beta in [('n', .1, 2.), ('p', .05, 1.)]:
        active = a['J'+carrier+'_'+label][:2]
        inactive = b['J'+carrier+'_'+label][:2]
        assert np.all(inactive != 0.)
        np.testing.assert_allclose(active/inactive, (1.+(mu*2.)**beta)**(-1./beta), rtol=5e-13)


CASES = [(axis, primary, driving, enabled) for axis in range(3)
         for primary in (False, True) for driving in (0, 1) for enabled in (False, True)]


def default_case(axis, primary, driving, enabled):
    sim = bar(axis, primary, driving)
    sim.set_high_field_saturation(enabled, 5e4, 4e4, 2., 1., driving)
    return sim


@pytest.mark.parametrize('axis,primary,driving,enabled', CASES)
def test_zero_matches_frozen_parent(axis, primary, driving, enabled):
    with open(os.environ['TCAD_HFS_CUTOFF_ORACLE'], encoding='utf8') as f:
        baseline = json.load(f)['cases'][str((axis, primary, driving, enabled))]
    a = default_case(axis, primary, driving, enabled)
    b = default_case(axis, primary, driving, enabled)
    b.set_hfs_low_field_cutoff(0.)
    assert thin_result(a.solve()) == thin_result(b.solve()) == baseline


@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('driving', [0, 1])
def test_converged_inactive_cutoff_matches_unsaturated(primary, driving):
    _, low = resistor(); _, cutoff = resistor()
    for sim in (low, cutoff):
        sim.set_use_newton(primary); sim.set_newton_primary(primary)
    cutoff.set_high_field_saturation(True, 5e4, 4e4, 2., 1., driving)
    cutoff.set_hfs_low_field_cutoff(1e9)
    same_solution(low, cutoff)


def test_public_configuration_replays_cutoff():
    a, _ = resistor(public=True); b, _ = resistor(public=True)
    a.set_hfs_low_field_cutoff(3e5)
    recipe = a.configuration_snapshot()[-1]
    assert recipe == ('python', 'set_hfs_low_field_cutoff', {'cutoff': 3e5})
    getattr(b, recipe[1])(**recipe[2])
    assert b.get_hfs_low_field_cutoff() == 3e5
    same_solution(a._sim, b._sim)
