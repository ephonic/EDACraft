"""Classical avalanche generation must use the actual saturated SG current."""
import json
import os
import numpy as np
import pytest
from tcad.core import native_constants
from test_hfs_low_field_cutoff import bar as hfs_bar, reference
from test_ii_field_floor import PHI, N, P, generation, thin_result


def bar(axis=0, driving=1, cutoff=0., floor=1e5, primary=False):
    sim = hfs_bar(axis, primary, driving)
    sim.set_hfs_low_field_cutoff(cutoff)
    sim.set_ii_params(1e5, 2e5, 2e5, 3e5)
    sim.set_ii_field_floor(floor)
    sim.set_ii_enabled(True)
    return sim


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('cutoff', [0., 3e5, 1e6])
@pytest.mark.parametrize('floor', [1e5, 6e5])
def test_returned_generation_and_audit_use_actual_currents(axis, driving, cutoff, floor):
    r = bar(axis, driving, cutoff, floor).solve()
    assert not r['converged']  # Zero-budget returned operator, not a solved device.
    jn, jp, dn, dp, bp, bm = reference(r['phi'], r['n'], r['p'], driving, cutoff)
    label = 'xyz'[axis]
    np.testing.assert_allclose(r['Jn_'+label][:2], jn, rtol=5e-13)
    np.testing.assert_allclose(r['Jp_'+label][:2], jp, rtol=5e-13)
    expected = generation(r['phi'], jn, jp, floor)
    np.testing.assert_allclose(r['G_ii'], expected, rtol=5e-13, atol=0.)
    # Independently reconstruct generation a second way from the returned
    # conventional current arrays, without using reference mobilities.
    returned = generation(r['phi'], r['Jn_'+label][:2], r['Jp_'+label][:2], floor)
    np.testing.assert_allclose(r['G_ii'], returned, rtol=5e-13, atol=0.)
    audit = r['steady_equation_audit']; assert audit['available']
    for carrier, diffusion, plus, minus, name in [
            (r['n'], dn, bm, bp, 'electron'), (r['p'], dp, bp, bm, 'hole')]:
        diagonal = (diffusion[0]*minus[0]+diffusion[1]*plus[1])*carrier[1]
        neighbors = diffusion[0]*plus[0]*carrier[0]+diffusion[1]*minus[1]*carrier[2]
        rhs = expected[1]*1e-7
        backward = abs(diagonal-neighbors-rhs)/(abs(diagonal)+abs(neighbors)+abs(rhs))
        assert audit[name+'_backward_error_linf'] == pytest.approx(backward, rel=2e-11, abs=2e-15)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('cutoff', [0., 3e5, 1e6])
@pytest.mark.parametrize('floor', [1e5, 6e5])
def test_newton_source_residual_uses_saturated_current(axis, driving, cutoff, floor):
    r = bar(axis, driving, cutoff, floor, primary=True).solve()
    stage, = r['nonlinear_history']
    assert stage['solver']=='newton' and len(stage['raw_n_l2'])==1
    jn, jp, *_ = reference(PHI, N, P, driving, cutoff)
    g = generation(PHI, jn, jp, floor)
    q = float(native_constants()['elementary_charge_C'])
    # Jn is conventional electron current, opposite to the electron particle
    # flux used in the residual. Hole current already follows that convention.
    for current, name, sign in [(jn, 'n', -1.), (jp, 'p', 1.)]:
        expected = abs(sign*np.diff(current)[0]/q-g[1]*1e-7)
        assert stage['raw_'+name+'_l2'][0] == pytest.approx(expected, rel=2e-12)


OFF_CASES=[(axis,primary,mode) for axis in range(3) for primary in [False,True]
           for mode in ['ii_only','hfs_only','both_off','cutoff_inactive']]


def off_case(axis, primary, mode):
    sim=bar(axis, 1, 1e30 if mode=='cutoff_inactive' else 0., primary=primary)
    sim.set_high_field_saturation(mode in ['hfs_only','cutoff_inactive'],5e4,4e4,2.,1.,1)
    sim.set_ii_enabled(mode in ['ii_only','cutoff_inactive'])
    return sim


@pytest.mark.parametrize('axis,primary,mode', OFF_CASES)
def test_unaffected_paths_preserve_frozen_parent(axis, primary, mode):
    with open(os.environ['TCAD_HFS_II_CURRENT_ORACLE'],encoding='utf8') as f:
        expected=json.load(f)['cases'][str((axis,primary,mode))]
    assert thin_result(off_case(axis,primary,mode).solve())==expected
