"""True-residual acceptance, physical parity and transaction-owned LU reuse."""
import copy
import itertools
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from test_sheet_coupled import X, Y, Z, BOUNDS, CASES, check_fluxes, assert_state_equal
from test_sheet_dielectric_contacts import trap


def device(method='reused_gmres', contact='linear', material='graphene', finite=True,
           scheme='diffusion_enhanced'):
    options={}
    if contact=='linear':options['contact_resistance_ohm_m']=.003
    if contact=='thermionic':options['thermionic_barrier_n_eV']=(.12,.15)
    if contact=='dirac':options['dirac_contact_offset_eV']=(-.02,.03)
    band=mos2_sheet(reference_eV=-.9) if material=='mos2' else graphene_sheet()
    return DielectricSheetDriftDiffusion(X,Y,Z,band,sheet_index=3,
        permittivity_F_m=5*8.8541878128e-12*(1+np.arange(48).reshape(6,2,4)/48),
        contact_z_bounds_m=BOUNDS if finite else None,electrostatic_backend='coupled',
        linear_solver=method,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
        sheet_permittivity_F=2e-20,doping_m2=np.linspace(-1e13,2e13,15).reshape(3,5),
        fixed_charge_C_m2=1e-7,transport_scheme=scheme,**options)


def transient(sim=None):
    sim=device() if sim is None else sim
    return SheetTransient(sim,initial_drive=dict(top_gate_voltage_V=.005),traps=trap(sim),
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)


@pytest.mark.parametrize('bad',(None,True,1,[],{},'gmres','Reused_GMRES'))
def test_invalid_method(bad):
    with pytest.raises(ValueError,match='linear_solver'):device(bad)


def test_requires_coupled_backend():
    with pytest.raises(ValueError,match='requires the coupled'):
        DielectricSheetDriftDiffusion(X,Y,Z,graphene_sheet(),sheet_index=3,
            permittivity_F_m=5e-11,linear_solver='reused_gmres',
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01)


@pytest.mark.parametrize('contact,material',CASES)
@pytest.mark.parametrize('finite,scheme',itertools.product((False,True),('midpoint','diffusion_enhanced')))
def test_dc_and_trap_be_match_direct_with_independent_flux_ledger(contact,material,finite,scheme):
    trajectories=[]
    for method in ('direct','reused_gmres'):
        sim=device(method,contact,material,finite,scheme)
        dc=sim.solve(top_gate_voltage_V=.012,bottom_gate_voltage_V=-.003,
            drain_voltage_V=.004,tolerance=1e-12,max_iter=120)
        assert dc['converged'];check_fluxes(sim,dc)
        run=transient(sim);states=[dc,run.state]
        for gate,drain in ((.025,.004),(-.01,-.004)):
            result=run.step(dt_s=2e-12,top_gate_voltage_V=gate,drain_voltage_V=drain,
                tolerance=1e-12,max_iter=120)
            assert result['accepted'];check_fluxes(sim,result)
            scale=max(max(map(abs,result['terminal_total_currents_A'].values())),1e-12)
            assert abs(result['terminal_total_current_sum_A'])<1e-8*scale
            states.append(result)
        for result in states:
            if method=='direct':assert 'linear_solver_diagnostics' not in result
            else:
                stats=result['linear_solver_diagnostics']
                assert stats['max_accepted_true_scaled_residual_linf']<=1e-14
                assert stats['absolute_tolerance']==1e-14
                for call in stats['attempts']:
                    assert len(call)<=2 and call[-1]['accepted']
        trajectories.append(states)
    for direct,iterative in zip(*trajectories):
        for key in ('phi_V','Fn_eV','Fp_eV','dielectric_phi_V','trap_occupancy'):
            if key in direct:np.testing.assert_allclose(iterative[key],direct[key],rtol=0.,atol=1e-10)
        for key in ('n_m2','p_m2'):
            np.testing.assert_allclose(iterative[key],direct[key],rtol=1e-9,atol=0.)
        for key,floor in (('contact_charge_C',1e-26),('terminal_currents_into_sheet_A',1e-15),
                          ('terminal_total_currents_A',1e-15)):
            if key in direct:
                for name in direct[key]:
                    np.testing.assert_allclose(iterative[key][name],direct[key][name],rtol=1e-8,atol=floor)


def test_deepcopy_owns_geometry_and_reuses_only_frozen_factor():
    sim=device();sim.solve(top_gate_voltage_V=.005,tolerance=1e-12)
    run=transient(sim);duplicate=copy.deepcopy(run)
    assert run._device._linear_factor is sim._linear_factor
    assert duplicate._device._linear_factor is run._device._linear_factor
    assert duplicate._device.dielectric._lff.data is not run._device.dielectric._lff.data
    sim.dielectric._lff.data[:]=0.
    result=run.step(dt_s=2e-12,top_gate_voltage_V=.015,drain_voltage_V=.003,tolerance=1e-12)
    assert result['accepted']
    assert result['linear_solver_diagnostics']['invalidated_initial_factor']
    assert not result['linear_solver_diagnostics']['reused_initial_factor']
    assert result['linear_solver_diagnostics']['factorizations']==1
    assert run._device._linear_factor.operator_key==('backward_euler',2e-12)
    following=run.step(dt_s=2e-12,top_gate_voltage_V=.016,tolerance=1e-12)
    assert following['linear_solver_diagnostics']['reused_initial_factor']
    assert following['linear_solver_diagnostics']['factorizations']==0
    result['linear_solver_diagnostics']['attempts'].clear()
    assert run.state['linear_solver_diagnostics']['attempts']


@pytest.mark.parametrize('failure',('stop_flag','nonfinite','false_success'))
def test_one_refresh_recovers_bad_attempt_and_commits_only_accepted_candidate(monkeypatch,failure):
    import tcad.solver._sheet_linear as linear
    run=transient();old=run._device._linear_factor;actual=linear.gmres;calls=[]
    def once(*args,**kwargs):
        x,info=actual(*args,**kwargs);calls.append(info)
        if len(calls)==1:
            if failure=='stop_flag':return x,1
            return np.full_like(x,np.nan) if failure=='nonfinite' else np.zeros_like(x),0
        return x,info
    monkeypatch.setattr(linear,'gmres',once)
    result=run.step(dt_s=2e-12,top_gate_voltage_V=.025,drain_voltage_V=.004,tolerance=1e-12)
    assert result['accepted'] and run._device._linear_factor is not old
    stats=result['linear_solver_diagnostics']
    assert stats['factorizations']==2 and stats['refreshes']==1
    assert stats['invalidated_initial_factor']
    assert not stats['attempts'][0][0]['accepted'] and stats['attempts'][0][1]['accepted']
    json.dumps(result['linear_solver_diagnostics'],allow_nan=False)
    if failure=='nonfinite':assert stats['attempts'][0][0]['true_scaled_residual_linf'] is None


@pytest.mark.parametrize('failure',('false_success','nonfinite','exception','factorization'))
def test_failed_linear_or_refresh_never_commits_history_or_factor(monkeypatch,failure):
    import tcad.solver._sheet_linear as linear
    run=transient();state=run.state;factor=run._device._linear_factor;calls=[]
    def broken(A,b,**kwargs):
        calls.append(1)
        if failure=='exception':raise RuntimeError('injected iterative exception')
        return np.full_like(b,np.nan) if failure=='nonfinite' else np.zeros_like(b),0
    monkeypatch.setattr(linear,'gmres',broken)
    if failure=='factorization':
        def singular(*a,**k):raise RuntimeError('injected refresh factorization exception')
        monkeypatch.setattr(linear,'splu',singular)
    with pytest.raises((FloatingPointError,RuntimeError)):
        run.step(dt_s=2e-12,top_gate_voltage_V=.025,drain_voltage_V=.004,tolerance=1e-12)
    assert len(calls)<=2 and run.time_s==0.
    assert run._device._linear_factor is factor
    assert_state_equal(run.state,state)


@pytest.mark.parametrize('copy_index',(1,2))
def test_nonlinear_rejection_and_result_copy_exception_rollback_cache(monkeypatch,copy_index):
    import tcad.solver._sheet_linear as linear
    import tcad.solver.sheet_transient as module
    run=transient();clean=copy.deepcopy(run);state=run.state;factor=run._device._linear_factor
    actual=linear.gmres;calls=[]
    def refresh(*a,**k):
        x,info=actual(*a,**k);calls.append(1)
        return x,1 if len(calls)==1 else info
    with monkeypatch.context() as m:
        m.setattr(linear,'gmres',refresh)
        rejected=run.step(dt_s=2e-12,top_gate_voltage_V=.2,drain_voltage_V=.04,
            max_iter=1,tolerance=1e-12)
    assert not rejected['accepted'] and run._device._linear_factor is factor
    assert rejected['linear_solver_diagnostics']['factorizations']>=1
    assert_state_equal(run.state,state)
    copier=copy.deepcopy
    allocations=[]
    def allocation(value,*args,**kwargs):
        if isinstance(value,dict) and value.get('accepted') and 'dt_s' in value:
            allocations.append(1)
            if len(allocations)==copy_index:
                raise MemoryError('injected post-solve public/history allocation')
        return copier(value,*args,**kwargs)
    with monkeypatch.context() as m:
        calls.clear();m.setattr(linear,'gmres',refresh);m.setattr(module.copy,'deepcopy',allocation)
        with pytest.raises(MemoryError):
            run.step(dt_s=2e-12,top_gate_voltage_V=.025,drain_voltage_V=.004,tolerance=1e-12)
    assert run.time_s==0. and run._device._linear_factor is factor
    assert_state_equal(run.state,state)
    retry=run.step(dt_s=2e-12,tolerance=1e-12)
    reference=clean.step(dt_s=2e-12,tolerance=1e-12)
    assert retry['accepted'];assert_state_equal(retry,reference)


@pytest.mark.parametrize('material',('graphene','mos2'))
def test_variable_time_step_matches_direct_and_reuses_only_same_storage_operator(material):
    histories=[]
    for method in ('direct','reused_gmres'):
        run=transient(device(method,material=material))
        states=[]
        for index,(dt,gate) in enumerate(((2e-12,.025),(2e-12,-.01),(1e-12,.015),(2e-12,.02))):
            old=run._device._linear_factor
            state=run.step(dt_s=dt,top_gate_voltage_V=gate,drain_voltage_V=.003,tolerance=1e-12,max_iter=120)
            assert state['accepted'];check_fluxes(run._device,state);states.append(state)
            if method=='reused_gmres':
                stats=state['linear_solver_diagnostics'];changed=index!=1
                assert stats['invalidated_initial_factor']==changed
                assert stats['reused_initial_factor']==(not changed)
                assert stats['factorizations']==int(changed)
                assert (run._device._linear_factor is old)==(not changed)
                assert run._device._linear_factor.operator_key==('backward_euler',dt)
        histories.append(states)
    for direct,iterative in zip(*histories):
        for key in ('phi_V','Fn_eV','Fp_eV','dielectric_phi_V','trap_occupancy'):
            np.testing.assert_allclose(iterative[key],direct[key],rtol=0.,atol=1e-10)
        for key in ('n_m2','p_m2'):
            np.testing.assert_allclose(iterative[key],direct[key],rtol=1e-9,atol=0.)


@pytest.mark.parametrize('failure',('factorization','nonlinear'))
def test_changed_time_step_failure_keeps_accepted_operator_and_retry_history(monkeypatch,failure):
    import tcad.solver._sheet_linear as linear
    run=transient();run.step(dt_s=2e-12,top_gate_voltage_V=.02,tolerance=1e-12)
    clean=copy.deepcopy(run);state=run.state;factor=run._device._linear_factor;time=run.time_s
    with monkeypatch.context() as m:
        if failure=='factorization':
            def broken(*a,**k):raise RuntimeError('injected new storage operator factorization failure')
            m.setattr(linear,'splu',broken)
            with pytest.raises(RuntimeError,match='new storage operator'):
                run.step(dt_s=1e-12,top_gate_voltage_V=.025,tolerance=1e-12)
        else:
            rejected=run.step(dt_s=1e-12,top_gate_voltage_V=.2,drain_voltage_V=.04,tolerance=1e-12,max_iter=1)
            assert not rejected['accepted'] and rejected['linear_solver_diagnostics']['invalidated_initial_factor']
    assert run.time_s==time and run._device._linear_factor is factor
    assert_state_equal(run.state,state)
    retry=run.step(dt_s=2e-12,tolerance=1e-12);reference=clean.step(dt_s=2e-12,tolerance=1e-12)
    assert retry['accepted'] and retry['linear_solver_diagnostics']['reused_initial_factor']
    assert retry['linear_solver_diagnostics']['factorizations']==0
    assert_state_equal(retry,reference)


def test_captured_large_phase2_jacobian_does_not_reject_a_valid_max_norm_solution():
    from scipy.sparse import csr_matrix
    from tcad.solver._sheet_linear import _ReusedGMRES
    with np.load(Path(__file__).parent/'data/sheet_phase2_linear_system.npz',allow_pickle=False) as data:
        A=csr_matrix((data['data'],data['indices'],data['indptr']),shape=tuple(data['shape']))
        b=data['b'];previous=data['original_rejected_x']
    # The captured old solve met the row-wise contract, but its L2 roundoff
    # floor just exceeded the old dimension-independent Krylov target.
    residual=A@previous-b
    assert np.max(abs(residual))<1e-14 and np.linalg.norm(residual)>1e-14
    context=_ReusedGMRES(None,1e-12);x=context.solve(A,b)
    assert np.all(np.isfinite(x)) and np.max(abs(A@x-b))<=1e-14
    stats=context.diagnostics()
    assert stats['linear_solves']==1 and stats['factorizations']==1
    assert all(c[-1]['info']==0 and c[-1]['accepted'] for c in stats['attempts'])


@pytest.mark.parametrize('correction_result',('valid','false_success','stop_flag','nonfinite'))
def test_rms_stop_requires_true_max_norm_and_verified_residual_correction(monkeypatch,correction_result):
    from scipy.sparse import eye
    import tcad.solver._sheet_linear as linear
    A=eye(16,format='csr');b=np.ones(16);actual=linear.gmres;calls=[]
    def controlled(matrix,rhs,**kwargs):
        calls.append(1)
        if len(calls)>2:return actual(matrix,rhs,**kwargs)
        kwargs['callback'](0.)
        if len(calls)==1:
            x=b.copy();x[0]+=2e-14
            return x,0
        if correction_result=='false_success':return np.zeros_like(rhs),0
        if correction_result=='nonfinite':return np.full_like(rhs,np.nan),0
        return rhs.copy(),1 if correction_result=='stop_flag' else 0
    monkeypatch.setattr(linear,'gmres',controlled)
    context=linear._ReusedGMRES(None,1e-12);x=context.solve(A,b);stats=context.diagnostics()
    assert np.max(abs(A@x-b))<=1e-14 and np.all(np.isfinite(x))
    assert stats['gmres_corrections']==1
    attempts=stats['attempts'][0];first=attempts[0]
    assert first['initial_true_scaled_residual_linf']>1e-14
    assert first['initial_true_scaled_residual_l2']<=first['gmres_absolute_l2_tolerance']
    assert first['correction'] is not None
    if correction_result=='valid':
        assert len(attempts)==1 and first['accepted'] and first['correction']['accepted']
        assert stats['factorizations']==1 and stats['refreshes']==0
    else:
        assert len(attempts)==2 and not first['accepted'] and not first['correction']['accepted']
        assert attempts[-1]['accepted'] and stats['factorizations']==2 and stats['refreshes']==1
    json.dumps(stats,allow_nan=False)
