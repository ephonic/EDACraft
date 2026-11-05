"""Whole-path particle gates must qualify native state publication atomically."""
from pathlib import Path
import hashlib,importlib.util,json,sys
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from test_energy_coordinate_exchange import exchange_case
from test_adaptive_energy_coordinate import TRANSIENT
from test_energy_record_finite import encode_state
from tcad.solver.energy_coordinate_transport import EnergyCoordinateState
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.solver.transient_energy_coordinate import EnergyCoordinateTransientError

OUT=Path(__file__).resolve().parents[1]/'docs/validation/particle_transaction_20261022'
CASES=('zero_original_transport','zero_contact','coupled_generated')


def normalized(value):
    if isinstance(value,EnergyCoordinateState):return normalized(encode_state(value))
    if isinstance(value,np.ndarray):return normalized(value.tolist())
    if isinstance(value,np.longdouble):return np.format_float_scientific(value,precision=35,unique=False)
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {str(k):normalized(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalized(v) for v in value]
    return value


def parent():
    name='tcad.solver.frozen_particle_transaction_parent'
    spec=importlib.util.spec_from_file_location(name,OUT/'before/tcad/solver/transient_energy_coordinate.py')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=previous
    return module


def make_case(name):
    if name=='zero_original_transport':return transport_case(2,-20000,20000,False)
    if name=='zero_contact':return transport_case(2,-.4,.3,True)
    if name=='coupled_generated':return exchange_case(2,-20000,20000,False,generated=True)
    raise AssertionError(name)


@pytest.mark.parametrize('name',CASES)
def test_real_strict_particle_failure_rolls_back_then_explicit_retry_matches_parent(name):
    source=OUT/('frozen_'+name+'.json');frozen=json.loads(source.read_text())
    strict=frozen['audit']['maximum_cumulative_particle_error']/2
    assert 0<strict<4*BUDGET['particle_atol']
    model,initial=make_case(name);device=Device(model,initial);old=device.state
    native_before=device.native_state();calls=[];advance=Device.advance
    def counted(self,*args,**kwargs):
        state,report=advance(self,*args,**kwargs)
        calls.append(dict(dt_s=report['dt_s'],time_s=state.thermal.time_s,
            independently_audited=report['independent_audit']['valid']))
        return state,report
    def forbidden_publication(*a,**k):raise AssertionError('failed cumulative budget reached publication')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Device,'advance',counted)
        with pytest.MonkeyPatch.context() as publication:
            publication.setattr(device,'_trajectory_publication',forbidden_publication)
            with pytest.raises(EnergyCoordinateTransientError) as caught:
                device.run_transient([0.,2e-14,5e-14],**TRANSIENT,cumulative_particle_atol=strict)
        diagnostic=caught.value.diagnostics;ledger=diagnostic['trajectory_energy_audit']
        assert diagnostic['failure_phase']=='cumulative_energy_audit' and not diagnostic['published']
        assert diagnostic['completed_interval_native_calls']==len(calls)==6
        assert 'conservation audit failed' in diagnostic['failure']
        assert device.state is old and device.native_state()==native_before
        assert not ledger['valid'] and not ledger['particle_path_valid']
        assert ledger['cumulative_particle_atol']==strict
        assert ledger['maximum_cumulative_particle_error']==frozen['audit']['maximum_cumulative_particle_error']
        assert ledger['maximum_balance_error_J']<=ledger['cumulative_energy_atol_J']
        assert all(r['independent_audit']['valid'] for interval in diagnostic['interval_reports'] for r in interval['substep_reports'])
        assert all(interval['rejected_trials']==0 for interval in diagnostic['interval_reports'])
        retry=device.run_transient([0.,2e-14,5e-14],**TRANSIENT,cumulative_particle_atol=4*BUDGET['particle_atol'])
        assert retry['valid'] and retry['final_state'] is device.state and len(calls)==12
        assert retry['trajectory_energy_audit']['particle_path_valid']
        assert retry['trajectory_energy_audit']['cumulative_particle_budget_policy']=='explicit'
        legacy_device=Device(model,initial)
        legacy=parent().run_transient(legacy_device,[0.,2e-14,5e-14],**TRANSIENT)
        assert len(calls)==18 and all(c['independently_audited'] for c in calls)
    before=normalized(legacy);now=normalized(retry)
    before['trajectory_energy_audit']['cumulative_particle_budget_policy']='explicit'
    assert now==before and device.native_state()==legacy_device.native_state()
    assert retry['trajectory_energy_audit']==dict(frozen['audit'],cumulative_particle_budget_policy='explicit')
    if name!='zero_contact':assert any(0<abs(np.longdouble(v))<np.longdouble('1e-70') for v in device.state.excess_J_m3)
    data=normalized(dict(name=name,strict_particle_budget=strict,
        frozen_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        strict_diagnostics=diagnostic,native_before=native_before,retry=retry,parent_default=legacy,
        native_after=device.native_state(),observed_native_calls=calls,
        failed_caller_state_and_native_snapshot_unchanged=True,
        real_default_parent_compatibility_except_explicit_budget_policy=True))
    directory=OUT/'accepted_records';directory.mkdir(exist_ok=True)
    target=directory/(name+'.json')
    if target.exists():assert json.loads(target.read_text())==data
    else:target.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


@pytest.mark.parametrize('value',[0.,-1.,np.nan,np.inf,-np.inf,True,[1e-9],1j,'1e-9'])
def test_invalid_cumulative_particle_budget_fails_before_worker_or_native_steps(monkeypatch,value):
    model,initial=transport_case(1,0,0);device=Device(model,initial)
    old=device.state;before=device.native_state()
    def denied(*a,**k):raise AssertionError('invalid particle budget reached state inspection or advancement')
    monkeypatch.setattr(Device,'_check_owned_state',denied)
    monkeypatch.setattr(Device,'advance_adaptive',denied)
    with pytest.raises(ValueError,match='cumulative particle budget'):
        device.run_transient([0.,2e-14],**TRANSIENT,cumulative_particle_atol=value)
    assert device.state is old and device.native_state()==before


@pytest.mark.parametrize('value',[1e-25,np.float32(1e-9),np.longdouble('1e-9')])
def test_explicit_empty_path_particle_budget_does_not_advance_native_solver(monkeypatch,value):
    model,initial=transport_case(1,0,0);device=Device(model,initial);before=device.native_state()
    def denied(*a,**k):raise AssertionError('empty path attempted native advancement')
    monkeypatch.setattr(Device,'advance',denied)
    result=device.run_transient([0.],**TRANSIENT,cumulative_particle_atol=value,cumulative_energy_atol_J=1e-30)
    ledger=result['trajectory_energy_audit']
    assert result['native_advance_calls']==0 and device.native_state()==before
    assert ledger['valid'] and ledger['particle_path_valid']
    assert ledger['cumulative_particle_atol']==float(value) and ledger['cumulative_energy_atol_J']==1e-30
    assert ledger['cumulative_particle_budget_policy']==ledger['cumulative_budget_policy']=='explicit'
    assert ledger['maximum_cumulative_particle_error']==0
    for key in ('complete_device_energy','physical_validated','experimental_validated','global_temporal_error_bound'):
        assert result[key] is ledger[key] is False


def test_omitted_particle_budget_preserves_complete_parent_empty_result(monkeypatch):
    model,initial=transport_case(1,0,0);device=Device(model,initial);other=Device(model,initial)
    def denied(*a,**k):raise AssertionError('empty path attempted native advancement')
    monkeypatch.setattr(Device,'advance',denied)
    assert normalized(device.run_transient([0.],**TRANSIENT))==normalized(parent().run_transient(other,[0.],**TRANSIENT))
