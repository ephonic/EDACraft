"""Actual native adaptive trials, independent reservoir dynamics and rollback."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import expm
from test_three_temperature import case,BUDGET
from test_device_three_temperature import assert_owned
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.adaptive_three_temperature import AdaptiveStepError

OPTIONS=dict(temperature_atol_K=.01,temperature_rtol=.002,density_atol_m3=1e6,
    density_rtol=1e-6,minimum_step_s=1e-18,**BUDGET)


def closed():
    model,_=case(count=1,uniform=True);model.rhofix=np.zeros(1)
    model.capacity=np.full(1,.03);model.tau_n=np.full(1,3e-13);model.tau_p=np.full(1,5e-13)
    state=ThreeTemperatureState([1e20],[1e20],[.3],[300.],0.,[540.],[420.])
    return model,state


def integrate(model,initial,atol,end=6e-13):
    device=DeviceThreeTemperature(model,initial);dt=end;calls=0;rejected=0
    while device.state.time_s<end:
        state,report=device.advance_adaptive(min(dt,end-device.state.time_s),**dict(OPTIONS,temperature_atol_K=atol))
        assert report['normalized_temporal_error']<=1
        assert report['independent_substep_audits_passed'] and not report['global_temporal_error_bound']
        assert len(report['substep_states'])==len(report['substep_reports'])==2
        assert_owned(device,state)
        dt=report['suggested_next_step_s'];calls+=report['native_advance_calls'];rejected+=report['rejected_trials']
        assert calls<3000
    return state,calls,rejected


def test_adaptive_three_reservoir_dynamics_converge_to_independent_matrix_exponential():
    model,initial=closed();end=6e-13
    # Independent MB three-reservoir solution with finite lattice capacity;
    # both carriers heat the lattice, no prescribed or infinite-capacity bath.
    k=1.5*1e20*1.380649e-23/.03;tn=3e-13;tp=5e-13
    A=np.array([[-1/tn,0,1/tn],[0,-1/tp,1/tp],[k/tn,k/tp,-k/tn-k/tp]])
    exact=expm(A*end)@np.array([540.,420.,300.])
    loose,lc,_=integrate(model,initial,.1,end);tight,tc,rejected=integrate(model,initial,.01,end)
    values=lambda s:np.array([s.electron_temperature_K[0],s.hole_temperature_K[0],s.temperature_K[0]])
    le=max(abs(values(loose)-exact));te=max(abs(values(tight)-exact))
    assert te<le*.65 and te<.8 and tc>lc and rejected>0
    fixed,_=DeviceThreeTemperature(model,initial).advance(end,**BUDGET)
    assert max(abs(values(fixed)-exact))>te*10
    assert tight.temperature_K[0]>310. and tight.time_s==end
    assert not np.shares_memory(tight.electron_temperature_K,initial.electron_temperature_K)


def test_rejected_accuracy_trial_never_publishes_coarse_state():
    model,initial=closed();device=DeviceThreeTemperature(model,initial);before=deepcopy(device.native_state())
    with pytest.raises(AdaptiveStepError) as caught:
        device.advance_adaptive(6e-13,**OPTIONS,max_retries=0)
    attempt=caught.value.attempts[0]
    assert not attempt['accepted'] and attempt['normalized_error']>1
    assert len(attempt['states'])==len(attempt['reports'])==3
    assert all(r['independent_audit']['valid'] for r in attempt['reports'])
    assert device.native_state()==before and device.state.time_s==0
    state,_=device.advance_adaptive(1e-15,**OPTIONS)
    assert_owned(device,state)


@pytest.mark.parametrize('failure',['audit','newton','partial_half'])
def test_failed_trials_keep_caller_unchanged_and_allow_a_clean_retry(monkeypatch,failure):
    model,initial=closed();device=DeviceThreeTemperature(model,initial);before=deepcopy(device.native_state())
    kw=dict(OPTIONS,max_retries=1)
    with monkeypatch.context() as patch:
        if failure=='audit':
            patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',lambda *a,**k:dict(valid=False,reason='injected'))
        elif failure=='newton':kw['max_nfev']=1
        else:
            original=DeviceThreeTemperature.advance;calls=[]
            def fail_half(self,*a,**k):
                calls.append(1)
                if len(calls)%2==0:raise RuntimeError('injected half-step failure')
                return original(self,*a,**k)
            patch.setattr(DeviceThreeTemperature,'advance',fail_half)
        with pytest.raises(AdaptiveStepError) as caught:device.advance_adaptive(2e-13,**kw)
    assert len(caught.value.attempts)==2
    assert all('failure' in t and not t['accepted'] for t in caught.value.attempts)
    if failure=='partial_half':assert all(len(t['states'])==1 for t in caught.value.attempts)
    assert device.native_state()==before
    state,_=device.advance_adaptive(1e-15,**OPTIONS)
    fresh,_=DeviceThreeTemperature(model,initial).advance_adaptive(1e-15,**OPTIONS)
    for key in ('n_m3','p_m3','electron_temperature_K','hole_temperature_K','temperature_K'):
        np.testing.assert_array_equal(getattr(state,key),getattr(fresh,key))


@pytest.mark.parametrize('adaptive',[False,True])
def test_report_decoration_failure_occurs_before_state_publication(monkeypatch,adaptive):
    model,initial=closed();device=DeviceThreeTemperature(model,initial);before=deepcopy(device.native_state())
    def fail(report):raise KeyError('injected metadata allocation failure')
    with monkeypatch.context() as patch:
        patch.setattr(device,'_decorate_report',fail)
        with pytest.raises(KeyError):
            if adaptive:device.advance_adaptive(1e-15,**OPTIONS)
            else:device.advance(1e-15,**BUDGET)
    assert device.native_state()==before and device.state.time_s==0
    state,_=device.advance(1e-15,**BUDGET);assert_owned(device,state)


def test_minimum_interval_is_not_a_license_to_accept_excess_error():
    model,initial=closed();device=DeviceThreeTemperature(model,initial)
    with pytest.raises(AdaptiveStepError):device.advance_adaptive(6e-13,**dict(OPTIONS,minimum_step_s=6e-13))
    assert device.state.time_s==0


def test_migrated_structured_device_preserves_context_for_adaptive_substeps():
    from test_structured_three_temperature import structured_case
    source,initial,options=structured_case((3,1,1),contacts=False)
    device=source.to_three_temperature(initial,**options)
    state,report=device.advance_adaptive(1e-15,**OPTIONS)
    assert report['device_mesh_mode']=='StructuredGrid_primal_cells'
    for r in report['substep_reports']:
        assert r['legacy_StructuredGrid_three_temperature_integrated'] and not r['legacy_run_three_temperature_replaced']
        assert 'legacy_StructuredGrid_three_temperature_conversion' not in r['missing_physics']
    assert_owned(device,state)


def test_adoption_preserves_density_low_bits_and_allows_subsequent_fixed_step():
    model,initial=case(count=1,uniform=True)
    n=np.array([np.longdouble('10000000000000000000000001')])
    initial=replace(initial,n_m3=n,p_m3=n)
    device=DeviceThreeTemperature(model,initial)
    state,report=device.advance_adaptive(1e-16,**OPTIONS)
    np.testing.assert_array_equal(state.n_m3,n);assert_owned(device,state)
    state,report=device.advance(1e-16,**BUDGET)
    np.testing.assert_array_equal(state.n_m3,n);assert_owned(device,state)


@pytest.mark.parametrize('kw',[{'temperature_atol_K':0},{'temperature_atol_K':True},{'temperature_rtol':-1},
    {'temperature_rtol':np.nan},{'density_atol_m3':0},{'density_rtol':False},{'minimum_step_s':0},
    {'max_retries':True},{'max_retries':1.5},{'max_retries':-1},{'max_nfev':0},{'energy_atol_J':0}])
def test_invalid_adaptive_contract_rejected_without_advancing(kw):
    model,initial=closed();device=DeviceThreeTemperature(model,initial);before=deepcopy(device.native_state())
    with pytest.raises(ValueError):device.advance_adaptive(1e-14,**dict(OPTIONS,**kw))
    assert device.native_state()==before


@pytest.mark.parametrize('dt',[True,0.,-1.,float('nan'),float('inf'),1e-20])
def test_invalid_or_subminimum_requested_time(dt):
    model,initial=closed();device=DeviceThreeTemperature(model,initial)
    with pytest.raises(ValueError):device.advance_adaptive(dt,**OPTIONS)
    assert device.state.time_s==0
