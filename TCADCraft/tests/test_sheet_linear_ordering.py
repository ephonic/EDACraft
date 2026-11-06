"""Ordering alternatives preserve physics, true residuals and cache ownership."""
import copy
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix, eye

from tcad.solver._sheet_linear import _ReusedGMRES
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.material import graphene_sheet
from test_sheet_reused_gmres import device, transient
from test_sheet_coupled import X, Y, Z, check_fluxes, assert_state_equal


@pytest.mark.parametrize('bad',(None,True,1,[],{},'mmd_at_plus_a','MMD_ATA','NATURAL'))
def test_ordering_rejects_invalid_values_before_allocating_geometry(bad):
    with pytest.raises(ValueError,match='linear_ordering'):
        DielectricSheetDriftDiffusion(X,Y,Z,graphene_sheet(),sheet_index=3,
            permittivity_F_m=5e-11,electrostatic_backend='coupled',
            linear_solver='reused_gmres',linear_ordering=bad)
    with pytest.raises(ValueError,match='linear_ordering'):
        _ReusedGMRES(None,1e-12,ordering=bad)


def test_nondefault_ordering_requires_explicit_iterative_backend():
    with pytest.raises(ValueError,match='requires reused_gmres'):
        DielectricSheetDriftDiffusion(X,Y,Z,graphene_sheet(),sheet_index=3,
            permittivity_F_m=5e-11,linear_ordering='MMD_AT_PLUS_A')


def test_ordering_change_invalidates_factor_without_mutating_published_cache():
    A=eye(8,format='csr');b=np.arange(8,dtype=float)
    first=_ReusedGMRES(None,1e-12,ordering='COLAMD');first.solve(A,b)
    old=first.factor
    second=_ReusedGMRES(old,1e-12,ordering='MMD_AT_PLUS_A')
    assert second.invalidated_initial_factor and not second.reused_initial_factor
    np.testing.assert_allclose(second.solve(A,b),b,rtol=0.,atol=1e-14)
    assert second.factor is not old and old.ordering=='COLAMD'
    assert second.factor.ordering=='MMD_AT_PLUS_A'
    reused=_ReusedGMRES(second.factor,1e-12,ordering='MMD_AT_PLUS_A')
    reused.solve(A,b)
    assert reused.reused_initial_factor and reused.factorizations==0


def test_constructor_routes_selected_ordering_to_the_owned_linear_session():
    sim=DielectricSheetDriftDiffusion(X,Y,Z,graphene_sheet(),sheet_index=3,
        permittivity_F_m=5e-11,electrostatic_backend='coupled',
        linear_solver='reused_gmres',linear_ordering='MMD_AT_PLUS_A',
        mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01)
    state=sim.solve(top_gate_voltage_V=.01,tolerance=1e-12)
    assert state['converged']
    assert state['linear_solver_diagnostics']['factor_ordering']=='MMD_AT_PLUS_A'
    assert sim._linear_factor.ordering=='MMD_AT_PLUS_A'


@pytest.mark.parametrize('contact,material',(('linear','graphene'),('thermionic','mos2'),('dirac','graphene')))
def test_orderings_preserve_trap_pulse_fluxes_and_variable_dt_cache(contact,material):
    histories=[]
    for ordering in ('COLAMD','MMD_AT_PLUS_A'):
        sim=device(contact=contact,material=material);sim.linear_ordering=ordering
        run=transient(sim);states=[run.state]
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


def test_failed_new_ordering_factorization_rolls_back_then_reuses_accepted_cache(monkeypatch):
    import tcad.solver._sheet_linear as linear
    run=transient();run.step(dt_s=2e-12,top_gate_voltage_V=.02,tolerance=1e-12)
    clean=copy.deepcopy(run);state=run.state;old=run._device._linear_factor;now=run.time_s
    run._device.linear_ordering='MMD_AT_PLUS_A'
    with monkeypatch.context() as m:
        def fail(*a,**k):raise MemoryError('injected ordering factorization failure')
        m.setattr(linear,'splu',fail)
        with pytest.raises(MemoryError,match='ordering factorization'):
            run.step(dt_s=2e-12,top_gate_voltage_V=.025,tolerance=1e-12)
    assert run._device._linear_factor is old and old.ordering=='COLAMD'
    assert run.time_s==now;assert_state_equal(run.state,state)
    run._device.linear_ordering='COLAMD'
    retry=run.step(dt_s=2e-12,tolerance=1e-12)
    expected=clean.step(dt_s=2e-12,tolerance=1e-12)
    assert retry['linear_solver_diagnostics']['factorizations']==0
    assert_state_equal(retry,expected)


@pytest.mark.parametrize('ordering',('COLAMD','MMD_AT_PLUS_A'))
def test_captured_phase2_system_passes_unchanged_true_residual_guard(ordering):
    with np.load(Path(__file__).parent/'data/sheet_phase2_linear_system.npz',allow_pickle=False) as f:
        A=csr_matrix((f['data'],f['indices'],f['indptr']),shape=tuple(f['shape']));b=f['b']
    context=_ReusedGMRES(None,1e-12,ordering=ordering)
    x=context.solve(A,b)
    assert np.all(np.isfinite(x)) and np.max(abs(A@x-b))<=1e-14
    stats=context.diagnostics()
    assert stats['factor_ordering']==ordering
    assert stats['absolute_tolerance']==1e-14
    assert all(call[-1]['accepted'] for call in stats['attempts'])
