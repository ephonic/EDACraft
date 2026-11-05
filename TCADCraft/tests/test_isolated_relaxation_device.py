"""Device-owned excess coordinates, strict mode boundaries and rollback."""
from copy import deepcopy
from dataclasses import replace
import pytest
from test_isolated_relaxation import solver
from test_three_temperature import BUDGET,case
from tcad.core._bindings import PyDeviceSimulator
from tcad.solver.isolated_relaxation import IsolatedThreeTemperatureRelaxation
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs


def assert_owned(device):
    assert device.native_state()==dict(state=device.state.raw(),time_s=device.state.time_s)


def configure(backend,device):
    config=device.configuration
    backend.configure_isolated_relaxation([*config.initial_densities_m3,
        config.initial_temperatures_K[2],*config.initial_temperatures_K[:2]],
        config.parameters,*config.packed_valleys(),config.initial_time_s)


@pytest.mark.parametrize('a,c',[(-20000,20000),(20000,-20000),(0,0)])
def test_native_device_owns_three_original_steps_without_free_raw_callback(monkeypatch,a,c):
    def deny(*a,**k):raise AssertionError('free isolated kernel callback forbidden')
    monkeypatch.setattr('tcad.core._bindings.native_isolated_relaxation_raw',deny)
    device,_,_=solver(a,c);assert_owned(device)
    for dt in (2e-14,5e-14,9e-14):
        new,report=device.advance(dt,**BUDGET);assert_owned(device)
        assert report['state_owner']=='C++ DeviceSimulator::isolated_relaxation'
        assert report['main_DeviceSimulator_scoped_isolated_relaxation_integrated']
        assert not report['main_DeviceSimulator_integrated']
        assert report['independent_audit']['valid']
    copy=device.native_state();copy['state'][2]='1'
    assert_owned(device)


@pytest.mark.parametrize('failure',['budget','initial_audit','step_audit','decode','interrupt'])
def test_failed_candidate_rolls_back_native_state_clock_and_allows_identical_retry(monkeypatch,failure):
    device,_,_=solver();old=device.state;before=device.native_state()
    def reject(*a,**k):raise KeyboardInterrupt('injected')
    with monkeypatch.context() as patch:
        if failure in ('initial_audit','step_audit'):
            which='initial' if failure=='initial_audit' else 'step'
            patch.setattr('tcad.postprocess.isolated_relaxation.audit_isolated_relaxation_'+which,
                lambda *a,**k:dict(valid=False))
        elif failure=='decode':patch.setattr(device,'_decode_candidate',lambda *a:(_ for _ in ()).throw(ValueError('decode')))
        elif failure=='interrupt':patch.setattr(device,'_decode_candidate',reject)
        with pytest.raises((ValueError,RuntimeError,KeyboardInterrupt)):
            device.advance(2e-14,max_nfev=1 if failure=='budget' else 256,**BUDGET)
    assert device.state is old and device.native_state()==before
    actual,report=device.advance(2e-14,**BUDGET);fresh,_,_=solver();expected,_=fresh.advance(2e-14,**BUDGET)
    assert actual==expected and report['independent_audit']['valid'];assert_owned(device)


def test_native_candidate_tokens_freeze_configuration_and_exclude_stale_commits():
    device,_,_=solver();native=device._backend;before=native.isolated_relaxation_state()
    with pytest.raises(RuntimeError,match='immutable'):configure(native,device)
    first,token=native.prepare_isolated_relaxation(2e-14,**BUDGET)
    assert native.isolated_relaxation_state()==before
    with pytest.raises(RuntimeError,match='pending'):native.prepare_isolated_relaxation(2e-14,**BUDGET)
    with pytest.raises(RuntimeError,match='stale'):native.commit_isolated_relaxation(token+1)
    native.discard_isolated_relaxation(token)
    with pytest.raises(RuntimeError,match='stale'):native.commit_isolated_relaxation(token)
    second,token2=native.prepare_isolated_relaxation(2e-14,**BUDGET)
    assert first==second and token2>token
    with pytest.raises(RuntimeError,match='stale'):native.discard_isolated_relaxation(token)
    native.commit_isolated_relaxation(token2)
    assert native.isolated_relaxation_state()==dict(state=[*before['state'][:2],*second[:3]],time_s=2e-14)
    # Bypassing the public audited commit cannot silently desynchronize its cache.
    with pytest.raises(ValueError,match='accepted state mismatch'):device.advance(2e-14,**BUDGET)


@pytest.mark.parametrize('direction',['isolated_first','general_first'])
def test_general_and_isolated_modes_are_mutually_exclusive(direction):
    isolated,model,old=solver();native=PyDeviceSimulator(1,1,1,1.,1.,1.)
    packed=pack_three_temperature_inputs(model,old,1.,2e-28,1e-9,1e-27)
    if direction=='isolated_first':
        configure(native,isolated)
        with pytest.raises(RuntimeError,match='already configured'):native.configure_three_temperature(*packed,0.)
        with pytest.raises(RuntimeError):native.three_temperature_result()
    else:
        native.configure_three_temperature(*packed,0.)
        with pytest.raises(RuntimeError,match='another mode'):configure(native,isolated)


@pytest.mark.parametrize('method',['solve','structured_three_temperature_seed','begin_reliability_transaction'])
def test_legacy_entry_points_reject_explicit_excess_state_without_mutating_it(method):
    device,_,_=solver();before=device.native_state()
    with pytest.raises((ValueError,RuntimeError)):getattr(device._backend,method)()
    assert device.native_state()==before
    device.advance(2e-14,**BUDGET);assert_owned(device)


def test_reliability_transaction_blocks_configuration_and_releases_cleanly():
    device,_,_=solver();native=PyDeviceSimulator(1,1,1,1.,1.,1.)
    native.begin_reliability_transaction()
    with pytest.raises(RuntimeError,match='reliability transaction'):configure(native,device)
    native.rollback_reliability_transaction();configure(native,device)
    assert native.isolated_relaxation_state()==device.native_state()


@pytest.mark.parametrize('damage',['count','clock','coefficient','dimensions'])
def test_invalid_configuration_is_not_partially_installed(damage):
    device,_,_=solver();native=PyDeviceSimulator(2 if damage=='count' else 1,1,1,1.,1.,1.)
    config=device.configuration;args=list(config.parameters)
    initial=[*config.initial_densities_m3,config.initial_temperatures_K[2],*config.initial_temperatures_K[:2]]
    if damage=='coefficient':args[0]='-1'
    if damage=='dimensions':args.pop()
    with pytest.raises(ValueError):native.configure_isolated_relaxation(initial,args,*config.packed_valleys(),-1. if damage=='clock' else 0.)
    with pytest.raises(RuntimeError,match='not configured'):native.isolated_relaxation_state()
    if damage!='count':configure(native,device);assert native.isolated_relaxation_state()==device.native_state()


@pytest.mark.parametrize('budget',[True,0,-1,1.5])
def test_invalid_prepare_budget_does_not_create_hidden_candidate(budget):
    device,_,_=solver();before=device.native_state()
    with pytest.raises(ValueError):device.advance(2e-14,max_nfev=budget,**BUDGET)
    assert device.native_state()==before
    device.advance(2e-14,**BUDGET);assert_owned(device)


def test_actual_clock_interval_is_shared_with_native_at_nonzero_start():
    _,model,old=solver(0,0);old=replace(old,time_s=1.)
    device=IsolatedThreeTemperatureRelaxation(model,old)
    new,report=device.advance(2e-14,**BUDGET)
    assert report['dt_s']==new.time_s-1. and report['dt_s']!=2e-14;assert_owned(device)
    before=device.native_state()
    with pytest.raises(ValueError,match='clock'):device.advance(1e-30,**BUDGET)
    assert device.native_state()==before


@pytest.mark.parametrize('key,value',[('state_owner','Python'),('state_transaction','commit-before-audit'),
    ('main_DeviceSimulator_scoped_isolated_relaxation_integrated',False)])
def test_offline_audit_rejects_corrupted_native_ownership_claims(key,value):
    from tcad.postprocess.isolated_relaxation import audit_isolated_relaxation_step
    device,_,_=solver();old=device.state;new,report=device.advance(2e-14,**BUDGET)
    report[key]=value
    with pytest.raises(ValueError,match='ownership metadata'):audit_isolated_relaxation_step(device.configuration,old,new,report,**BUDGET)
