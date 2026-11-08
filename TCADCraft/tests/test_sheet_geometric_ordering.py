"""Geometric ordering preserves original equations and transactional caches."""
import copy

import numpy as np
import pytest
from scipy.sparse import csr_matrix, eye
from scipy.sparse.linalg import splu

from tcad.solver._sheet_linear import _ReusedGMRES
from tcad.solver._sheet_ordering import _geometric_nd_permutation, _SymmetricPermutation, _PermutedLU
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.material import graphene_sheet
from test_sheet_reused_gmres import device, transient
from test_sheet_coupled import X, Y, Z, check_fluxes, assert_state_equal


def test_separator_is_last_and_duplicate_sheet_coordinates_stay_together():
    points=np.column_stack(np.unravel_index(np.arange(9*7*7),(9,7,7)))
    points=np.vstack((points,points[points[:,0]==4],points[points[:,0]==4]))
    original=points.copy()
    p=_geometric_nd_permutation(points)
    np.testing.assert_array_equal(np.sort(p),np.arange(len(points)))
    np.testing.assert_array_equal(p,_geometric_nd_permutation(points))
    np.testing.assert_array_equal(points,original)
    # The root selects a thin balanced z/y plane rather than the thick sheet.
    # Independently enumerate the root costs, then check the separator suffix.
    choices=[]
    for axis in range(3):
        values=np.unique(points[:,axis]);m=len(values)//2
        for value in values[max(1,m-1):min(len(values)-1,m+2)]:
            left=points[:,axis]<value;right=points[:,axis]>value
            nl,nr=left.sum(),right.sum()
            if min(nl,nr):
                sep=np.flatnonzero(~(left|right))
                choices.append((len(sep)*(len(points)/(2*min(nl,nr)))**2,sep))
    sep=min(choices,key=lambda item:item[0])[1]
    np.testing.assert_array_equal(p[-len(sep):],sep)


@pytest.mark.parametrize('bad',([],[[0,1]],[-1,0],[0,0],[0.,1.],[True,False],[0,2]))
def test_invalid_permutations_are_rejected(bad):
    with pytest.raises(ValueError,match='permutation'):
        _SymmetricPermutation(bad)


@pytest.mark.parametrize('bad',(np.empty((0,3)),np.ones((2,2)),[[0,1,np.nan]]))
def test_invalid_geometry_is_rejected(bad):
    with pytest.raises(ValueError,match='coordinates'):
        _geometric_nd_permutation(bad)


def test_permutation_is_immutable_shared_and_detached_from_input():
    source=np.array([2,0,1]);p=_SymmetricPermutation(source)
    source[:]=0
    np.testing.assert_array_equal(p.indices,[2,0,1])
    assert copy.deepcopy(p) is p
    assert p.key==_SymmetricPermutation([2,0,1]).key
    assert p.key!=_SymmetricPermutation([0,1,2]).key
    with pytest.raises(ValueError):p.indices[0]=0
    with pytest.raises(ValueError):p.indices.setflags(write=True)


@pytest.mark.parametrize('rhs_kind',('integer','vector','columns','complex'))
def test_nonsymmetric_inverse_permutation_matches_dense_solve(rhs_kind):
    rng=np.random.default_rng(511)
    dense=rng.normal(size=(17,17))*.01+np.eye(17)*2
    if rhs_kind=='complex':dense=dense.astype(complex)+np.eye(17)*.3j
    b=np.arange(17) if rhs_kind=='integer' else rng.normal(size=(17,3) if rhs_kind=='columns' else 17)
    if rhs_kind=='complex':b=b+.2j
    p=_SymmetricPermutation(rng.permutation(17));A=csr_matrix(dense)
    lu=_PermutedLU(splu(A[p.indices][:,p.indices].tocsc(),permc_spec='NATURAL'),p)
    np.testing.assert_allclose(lu.solve(b),np.linalg.solve(dense,b),rtol=1e-14,atol=1e-14)


def test_required_permutation_and_matrix_size_are_checked():
    with pytest.raises(ValueError,match='requires a geometry'):
        _ReusedGMRES(None,1e-12,ordering='GEOMETRIC_ND')
    with pytest.raises(ValueError,match='requires GEOMETRIC_ND'):
        _ReusedGMRES(None,1e-12,permutation=[0,1])
    context=_ReusedGMRES(None,1e-12,ordering='GEOMETRIC_ND',permutation=[0,1])
    with pytest.raises(ValueError,match='does not match'):
        context.solve(eye(3,format='csr'),np.ones(3))
    with pytest.raises(ValueError,match='requires reused_gmres'):
        DielectricSheetDriftDiffusion(X,Y,Z,graphene_sheet(),sheet_index=3,
            permittivity_F_m=5e-11,linear_ordering='GEOMETRIC_ND')


def test_cache_identity_includes_permutation_ordering_and_time_step():
    A=eye(8,format='csr');b=np.arange(8,dtype=float);key=('backward_euler',1e-12)
    first=_ReusedGMRES(None,1e-12,key,'GEOMETRIC_ND',np.arange(8)[::-1]);first.solve(A,b)
    old=first.factor
    assert copy.deepcopy(old) is old
    reused=_ReusedGMRES(old,1e-12,key,'GEOMETRIC_ND',np.arange(8)[::-1]);reused.solve(A,b)
    assert reused.reused_initial_factor and reused.factorizations==0
    for operator,ordering,p in ((key,'GEOMETRIC_ND',np.arange(8)),
            (('backward_euler',2e-12),'GEOMETRIC_ND',np.arange(8)[::-1]),(key,'COLAMD',None)):
        changed=_ReusedGMRES(old,1e-12,operator,ordering,p)
        assert changed.invalidated_initial_factor and not changed.reused_initial_factor
        np.testing.assert_allclose(changed.solve(A,b),b,rtol=0.,atol=1e-14)
        assert changed.factor is not old


@pytest.mark.parametrize('contact,material',(('linear','graphene'),('thermionic','mos2'),('dirac','graphene')))
def test_geometric_ordering_trap_pulse_matches_mmd_with_independent_flux_checks(contact,material):
    histories=[]
    for ordering in ('MMD_AT_PLUS_A','GEOMETRIC_ND'):
        sim=device(contact=contact,material=material);sim.linear_ordering=ordering
        run=transient(sim);states=[run.state]
        assert run.state['linear_solver_diagnostics']['factor_ordering']==ordering
        for i,(dt,gate) in enumerate(((2e-12,.025),(2e-12,-.01),(1e-12,.015))):
            state=run.step(dt_s=dt,top_gate_voltage_V=gate,drain_voltage_V=.003,
                tolerance=1e-12,max_iter=120)
            assert state['accepted'];check_fluxes(run._device,state)
            stats=state['linear_solver_diagnostics']
            assert stats['factor_ordering']==ordering
            assert stats['max_accepted_true_scaled_residual_linf']<=1e-14
            assert stats['factorizations']==int(i!=1)
            assert stats['reused_initial_factor']==(i==1)
            scale=max(max(map(abs,state['terminal_total_currents_A'].values())),1e-12)
            assert abs(state['terminal_total_current_sum_A'])<1e-8*scale
            states.append(state)
        histories.append(states)
    for a,b in zip(*histories):
        for key in ('phi_V','Fn_eV','Fp_eV','dielectric_phi_V','trap_occupancy'):
            np.testing.assert_allclose(a[key],b[key],rtol=0.,atol=1e-10)
        for key in ('n_m2','p_m2'):
            np.testing.assert_allclose(a[key],b[key],rtol=1e-9,atol=0.)
        for key,floor in (('contact_charge_C',1e-26),('terminal_total_currents_A',1e-15)):
            if key in a:
                for terminal in a[key]:
                    np.testing.assert_allclose(a[key][terminal],b[key][terminal],rtol=1e-8,atol=floor)


def test_failed_geometric_factorization_rolls_back_and_keeps_accepted_factor(monkeypatch):
    import tcad.solver._sheet_linear as linear
    run=transient();run.step(dt_s=2e-12,top_gate_voltage_V=.02,tolerance=1e-12)
    clean=copy.deepcopy(run);state=run.state;old=run._device._linear_factor;now=run.time_s
    run._device.linear_ordering='GEOMETRIC_ND'
    with monkeypatch.context() as m:
        def fail(*a,**k):raise MemoryError('injected geometric factorization failure')
        m.setattr(linear,'splu',fail)
        with pytest.raises(MemoryError,match='geometric factorization'):
            run.step(dt_s=2e-12,top_gate_voltage_V=.025,tolerance=1e-12)
    assert run._device._linear_factor is old and old.ordering=='COLAMD'
    assert run.time_s==now;assert_state_equal(run.state,state)
    run._device.linear_ordering='COLAMD'
    retry=run.step(dt_s=2e-12,tolerance=1e-12)
    expected=clean.step(dt_s=2e-12,tolerance=1e-12)
    assert retry['linear_solver_diagnostics']['factorizations']==0
    assert_state_equal(retry,expected)
