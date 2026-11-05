"""Energy-aware local control, independent path replay and atomic adoption."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from test_device_energy_coordinate_transport import assert_owned
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.solver.adaptive_energy_coordinate import _energy_errors,AdaptiveStepError
from tcad.solver.transient_energy_coordinate import EnergyCoordinateTransientError
from tcad.postprocess.energy_coordinate_trajectory import audit_energy_coordinate_trajectory as audit

OPTIONS=dict(temperature_atol_K=1000.,temperature_rtol=0.,density_atol_m3=1e24,density_rtol=0.,
    excess_atol_J_m3=1e7,excess_rtol=0.,minimum_step_s=1e-20,**BUDGET)
TRANSIENT=dict(initial_step_s=2e-14,maximum_step_s=3e-14,**OPTIONS)


@pytest.fixture(scope='module',params=[(1,-20000,20000,False),(2,-20000,20000,False),(2,-.4,.3,True)])
def trajectory(request):
    count,a,c,contacts=request.param;model,initial=transport_case(count,a,c,contacts)
    device=Device(model,initial);old=device.state
    report=device.run_transient([0.,2e-14,5e-14],**TRANSIENT)
    return model,old,device,report


def test_real_trajectory_exact_clocks_owned_energy_and_cumulative_closure(trajectory):
    model,old,device,r=trajectory
    assert r['valid'] and r['whole_trajectory_atomic'] and r['native_advance_calls']==6
    assert r['accepted_native_substeps']==4 and r['accepted_intervals']==2
    assert [s.thermal.time_s for s in r['output_states']]==[0.,2e-14,5e-14]
    assert r['final_state'] is device.state and r['output_states'][0].excess_J_m3==old.excess_J_m3
    assert not r['output_times_s'].flags.writeable
    assert not r['physical_validated'] and not r['complete_device_energy'];assert_owned(device)
    ledger=audit(model,old,r['interval_reports'],final_state=device.state,**BUDGET)
    assert ledger==r['trajectory_energy_audit'] and ledger['valid']
    assert ledger['independently_reaudited_substeps']==4 and not ledger['temperature_view_used_as_energy']
    for interval in r['interval_reports']:
        assert len(interval['temporal_error_by_field'])==7
        assert interval['normalized_temporal_error']<=1
        assert interval['native_advance_calls']<=interval['maximum_native_advance_calls']
        for report in interval['substep_reports']:assert report['independent_audit']['total_evaluations']<=600
    if model.relaxation_laws[0].lattice_temperature_exponent==-20000:
        assert any(0<abs(Decimal(e))<Decimal('1e-70') for e in device.state.excess_J_m3)
    else:
        assert any(abs(v)>0 for v in ledger['outward_energy_J'].values())
        assert abs(ledger['source_work_J'])>0


def test_signed_energy_error_is_visible_when_all_temperature_views_are_identical(trajectory):
    _,old,_,r=trajectory;new=r['final_state'];e=list(new.excess_J_m3)
    e[0]='1e-120';coarse=replace(new,excess_J_m3=tuple(e));e[0]='1e-122';fine=replace(new,excess_J_m3=tuple(e))
    start=replace(new,excess_J_m3=('0',)*len(e))
    errors=_energy_errors(start,coarse,fine,1e-125,0.)
    assert errors['excess_n_J_m3']==pytest.approx(99000.)
    assert np.array_equal(coarse.thermal.electron_temperature_K,fine.thermal.electron_temperature_K)


@pytest.mark.parametrize('damage',['interval_scope','gap','missing_half','final_excess','ledger','cached_audit','discarded_trial'])
def test_independent_trajectory_rejects_path_forgery_and_ignores_untrusted_summaries(trajectory,damage):
    model,old,device,r=trajectory;intervals=deepcopy(r['interval_reports']);final=device.state
    if damage=='interval_scope':intervals[0]['scope']='complete_device'
    elif damage=='gap':intervals[1]['initial_state']=old
    elif damage=='missing_half':intervals[0]['substep_states']=intervals[0]['substep_states'][:1]
    elif damage=='final_excess':final=replace(final,excess_J_m3=('0',)*len(final.excess_J_m3))
    elif damage=='ledger':intervals[0]['substep_reports'][0]['raw']['ledger'][7]='1e-10'
    elif damage=='cached_audit':
        for interval in intervals:
            for report in interval['substep_reports']:report['independent_audit']={'valid':False}
    else:
        for interval in intervals:interval['attempts']=({'raw':'forged discarded candidate'},)
    if damage in ('cached_audit','discarded_trial'):
        assert audit(model,old,intervals,final_state=final,**BUDGET)['valid']
    else:
        with pytest.raises(ValueError):audit(model,old,intervals,final_state=final,**BUDGET)


def test_trajectory_replay_calls_no_native_or_production_physics(trajectory,monkeypatch):
    import tcad.core._bindings as native
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    model,old,device,r=trajectory
    def deny(*a,**k):raise AssertionError('production physics called')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    for name in ('_poisson','carrier_reservoirs','split_face_transport','energies','conduction'):monkeypatch.setattr(model,name,deny)
    assert audit(model,old,r['interval_reports'],final_state=device.state,**BUDGET)['valid']


@pytest.mark.parametrize('failure',['later_interval','cumulative','publication','interrupt'])
def test_whole_path_failure_retains_completed_diagnostics_and_caller_state(monkeypatch,failure):
    model,initial=transport_case(1,0,0);device=Device(model,initial);old=device.state;before=device.native_state()
    def allocation(*a,**k):raise MemoryError('injected result allocation')
    def interrupt(*a,**k):raise KeyboardInterrupt('injected publication interruption')
    opts=dict(TRANSIENT)
    with monkeypatch.context() as patch:
        if failure=='later_interval':opts['max_intervals']=1
        elif failure=='cumulative':patch.setattr('tcad.postprocess.energy_coordinate_trajectory.audit_energy_coordinate_trajectory',lambda *a,**k:dict(valid=False))
        elif failure=='publication':patch.setattr(device,'_trajectory_publication',allocation)
        else:patch.setattr(device,'_trajectory_publication',interrupt)
        with pytest.raises((EnergyCoordinateTransientError,KeyboardInterrupt)) as caught:device.run_transient([2e-14,5e-14],**opts)
    assert device.state is old and device.native_state()==before
    if failure!='interrupt':
        diagnostic=caught.value.diagnostics
        assert not diagnostic['published'] and len(diagnostic['interval_reports'])>=1
        assert diagnostic['failure_phase']==('integration' if failure=='later_interval' else 'cumulative_energy_audit' if failure=='cumulative' else 'result_construction')
    # A successful retry starts from the original native checkpoint.
    new,r=device.advance_adaptive(2e-14,**OPTIONS)
    fresh,rr=Device(model,initial).advance_adaptive(2e-14,**OPTIONS)
    assert new.excess_J_m3==fresh.excess_J_m3 and r['substep_reports']==rr['substep_reports'];assert_owned(device)


def test_real_temporal_rejection_shrinks_and_keeps_complete_trial_history():
    model,initial=transport_case(1,0,0);device=Device(model,initial)
    options=dict(OPTIONS,temperature_atol_K=.02,excess_atol_J_m3=100.)
    state,r=device.advance_adaptive(2e-13,**options)
    assert r['rejected_trials']>=1 and r['accepted_interval_s']<2e-13
    assert r['native_advance_calls']==sum(a['native_advance_calls'] for a in r['attempts'])
    assert any(a.get('normalized_error',0)>1 for a in r['attempts'][:-1])
    assert r['attempts'][-1]['accepted'] and state is device.state;assert_owned(device)


@pytest.mark.parametrize('damage',['budget','publication','minimum','clock'])
def test_adaptive_failure_does_not_adopt_any_trial(monkeypatch,damage):
    model,initial=transport_case(1,0,0)
    if damage=='clock':initial=replace(initial,time_s=1.)
    device=Device(model,initial);old=device.state;before=device.native_state();options=dict(OPTIONS,max_retries=0)
    dt=2e-14
    if damage=='budget':options['max_nfev']=1
    elif damage=='minimum':options.update(minimum_step_s=dt,temperature_atol_K=1e-15,excess_atol_J_m3=1e-20)
    elif damage=='clock':dt=1e-31
    else:
        def reject(*a,**k):raise MemoryError('injected adaptive publication failure')
        monkeypatch.setattr(device,'_publication',reject)
    with pytest.raises((AdaptiveStepError,ValueError,MemoryError)):device.advance_adaptive(dt,**options)
    assert device.state is old and device.native_state()==before


@pytest.mark.parametrize('name,value',[('excess_atol_J_m3',0),('excess_atol_J_m3',float('nan')),('excess_rtol',-1),
    ('max_retries',True),('max_nfev',0),('minimum_step_s',3e-14)])
def test_invalid_adaptive_contract_fails_before_native_advance(monkeypatch,name,value):
    model,initial=transport_case(1,0,0);device=Device(model,initial);old=device.state
    def deny(*a,**k):raise AssertionError('invalid request attempted a native advance')
    monkeypatch.setattr(Device,'advance',deny)
    with pytest.raises(ValueError):device.advance_adaptive(2e-14,**dict(OPTIONS,**{name:value}))
    assert device.state is old


def test_empty_path_and_output_resolution_contract():
    model,initial=transport_case(1,0,0);device=Device(model,initial)
    r=device.run_transient([0.],**TRANSIENT)
    assert r['accepted_intervals']==0 and r['trajectory_energy_audit']['valid']
    before=device.native_state();old=device.state
    for times in ([0.,0.],[-1.],[float('nan')],[1e-22]):
        with pytest.raises((ValueError,EnergyCoordinateTransientError)):device.run_transient(times,**TRANSIENT)
        assert device.state is old and device.native_state()==before
