"""Cumulative charge must close independently of particle and energy budgets."""
from copy import deepcopy
from pathlib import Path
import importlib.util,json,sys
import numpy as np
import pytest
from test_complex_particle_budget import decode,normalized,factory,BUDGET,RUN
from test_structured_three_temperature import structured_case
from tcad.solver.device_three_temperature import DeviceThreeTemperature as Device
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.postprocess.three_temperature_saved_path import audit_three_temperature_saved_path as saved_audit
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory as trajectory_audit
from tcad.solver.cut_cell_transport import Q

OUT=Path(__file__).resolve().parents[1]/'docs/validation/three_temperature_charge_path_20261022'
FROZEN=tuple(sorted(p.name for p in OUT.glob('frozen_*.json')))


def parent(name):
    package='solver' if name=='transient_three_temperature' else 'postprocess'
    label='tcad.'+package+'._frozen_charge_path_'+name
    if label in sys.modules:return sys.modules[label]
    spec=importlib.util.spec_from_file_location(label,OUT/'before/tcad'/package/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[label]=module
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=old
    return module


def path_case(filename):
    data=decode(json.loads((OUT/filename).read_text()));name=filename.removeprefix('frozen_').split('_')[0]
    model,_=factory(name)
    if filename.endswith('_adaptive.json'):
        return model,data['initial_state'],data['interval_reports'],data['final_state'],trajectory_audit,'three_temperature_trajectory'
    steps=[(s['old'],s['new'],s['report']) for s in data['steps']]
    return model,data['initial'],steps,data['final'],saved_audit,'three_temperature_saved_path'


def deny_native(patch):
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native operator used during independent saved replay')
    for key in dir(native):
        if key.startswith('native_') and callable(getattr(native,key)):patch.setattr(native,key,deny)


@pytest.mark.parametrize('filename',FROZEN)
def test_frozen_paths_close_cell_global_trap_storage_and_terminal_charge(filename,monkeypatch):
    model,initial,path,final,auditor,module=path_case(filename);deny_native(monkeypatch)
    result=auditor(model,initial,path,final_state=final,**BUDGET)
    previous=getattr(parent(module),auditor.__name__)(model,initial,path,final_state=final,**BUDGET)
    assert previous=={k:v for k,v in result.items() if k in previous}
    assert result['valid'] and result['charge_path_valid']
    assert result['independently_reconstructed_cumulative_charge']
    assert result['maximum_cumulative_charge_error_C']<=result['cumulative_charge_atol_C']
    assert len(result['cell_charge_balance_residuals_C'])==model.nc
    assert set(result['cumulative_terminal_charge_C'])==set(model.bc)
    explicit=auditor(model,initial,path,final_state=final,**BUDGET,cumulative_charge_atol_C=result['cumulative_charge_atol_C'])
    assert explicit==dict(result,cumulative_charge_budget_policy='explicit')
    error=result['maximum_cumulative_charge_error_C']
    if error>0:
        strict=auditor(model,initial,path,final_state=final,**BUDGET,cumulative_charge_atol_C=error/2)
        assert not strict['valid'] and not strict['charge_path_valid'] and strict['cell_particle_path_valid']
        assert strict['maximum_cumulative_cell_energy_error_J']<=strict['cumulative_energy_atol_J']


@pytest.mark.parametrize('api',['adaptive','saved'])
@pytest.mark.parametrize('damage',['terminal_KCL','cell_transport','charge_storage','trap_storage'])
def test_parent_charge_omissions_are_rejected_with_other_budgets_still_passing(monkeypatch,api,damage):
    model,initial,intervals,final,_,_=path_case('frozen_varshni_adaptive.json')
    steps=[];previous=initial
    for interval in intervals:
        for state,report in zip(interval['substep_states'],interval['substep_reports']):
            steps.append((previous,state,report));previous=state
    path=intervals if api=='adaptive' else steps
    auditor=trajectory_audit if api=='adaptive' else saved_audit
    module_name='three_temperature_trajectory' if api=='adaptive' else 'three_temperature_saved_path'
    module=__import__('tcad.postprocess.'+module_name,fromlist=['*'])
    original=module.audit_three_temperature_energy;old=parent(module_name)
    count=len(steps);budget=count*BUDGET['charge_atol_C'];delta=.8*BUDGET['particle_atol']
    def altered(*args,**kw):
        result=original(*args,**kw)
        assert result['valid']
        cells=result['independently_reconstructed_cell_ledger']
        if damage=='terminal_KCL':result['independently_reconstructed_ledger']['terminal_charge_C'][next(iter(model.bc))]+=4*budget
        elif damage=='cell_transport':
            cells['particle_transport']['electrons'][0]-=delta
            cells['particle_transport']['holes'][0]+=delta
        elif damage=='charge_storage':
            cells['particle_increments']['electrons'][0]-=delta
            cells['particle_increments']['holes'][0]+=delta
        else:
            cells['occupied_trap_increment'][0]+=delta
            cells['particle_increments']['holes'][0]-=delta
        return result
    monkeypatch.setattr(module,'audit_three_temperature_energy',altered)
    monkeypatch.setattr(old,'audit_three_temperature_energy',altered)
    deny_native(monkeypatch)
    previous=getattr(old,auditor.__name__)(model,initial,path,final_state=final,**BUDGET)
    assert previous['valid'] and previous['cell_particle_path_valid']
    checked=auditor(model,initial,path,final_state=final,**BUDGET)
    assert not checked['valid'] and not checked['charge_path_valid']
    assert checked['cell_particle_path_valid']
    assert checked['maximum_cumulative_cell_energy_error_J']<=checked['cumulative_energy_atol_J']
    assert checked['maximum_cumulative_charge_error_C']>budget


def test_actual_charge_budget_failure_rolls_back_and_retry_matches_parent():
    model,initial,path,final,_,_=path_case('frozen_contact_adaptive.json')
    baseline=trajectory_audit(model,initial,path,final_state=final,**BUDGET)
    strict=baseline['maximum_cumulative_charge_error_C']/2;budget=baseline['cumulative_charge_atol_C']
    assert 0<strict<budget
    device=Device(model,initial);old=device.state;before=device.native_state();calls=[];advance=Device.advance
    def counted(self,*a,**kw):
        state,report=advance(self,*a,**kw)
        calls.append(dict(time_s=state.time_s,dt_s=report['dt_s'],independently_audited=report['independent_audit']['valid']))
        return state,report
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Device,'advance',counted)
        with pytest.raises(ThreeTemperatureTransientError) as caught:
            device.run_transient([7e-16],**RUN,cumulative_charge_atol_C=strict)
        diagnostic=caught.value.diagnostics;audit=diagnostic['trajectory_energy_audit']
        assert not diagnostic['published'] and diagnostic['failure_phase']=='cumulative_energy_audit'
        assert not audit['valid'] and not audit['charge_path_valid'] and audit['cell_particle_path_valid']
        assert audit['maximum_cumulative_charge_error_C']==baseline['maximum_cumulative_charge_error_C']
        assert audit['maximum_cumulative_cell_energy_error_J']<=audit['cumulative_energy_atol_J']
        assert device.state is old and device.native_state()==before
        assert diagnostic['completed_interval_native_calls']==len(calls)==15
        retry=device.run_transient([7e-16],**RUN,cumulative_charge_atol_C=budget)
        assert retry['valid'] and retry['final_state'] is device.state
        legacy_device=Device(model,initial)
        with pytest.MonkeyPatch.context() as legacy_patch:
            legacy_patch.setattr('tcad.postprocess.three_temperature_trajectory.audit_three_temperature_trajectory',
                parent('three_temperature_trajectory').audit_three_temperature_trajectory)
            legacy=parent('transient_three_temperature').run_transient(legacy_device,[7e-16],**RUN)
    left=normalized(retry);right=normalized(legacy)
    left['trajectory_energy_audit']={k:v for k,v in left['trajectory_energy_audit'].items() if k in right['trajectory_energy_audit']}
    assert left==right and device.native_state()==legacy_device.native_state()
    assert len(calls)==45 and all(c['independently_audited'] for c in calls)
    record=normalized(dict(strict_charge_budget_C=strict,default_charge_budget_C=budget,strict_diagnostics=diagnostic,
        retry=retry,parent_default=legacy,native_before=before,native_after=device.native_state(),observed_native_calls=calls,
        caller_state_identity_and_native_snapshot_retained=True,parent_existing_physical_result_exact=True))
    directory=OUT/'accepted_records';directory.mkdir(exist_ok=True);target=directory/'contact.json'
    if target.exists():assert json.loads(target.read_text())==record
    else:target.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')


INVALID=(0.,-1.,np.nan,np.inf,-np.inf,True,'1e-30',[1e-30],1j,np.longdouble('1e4000'))


@pytest.mark.parametrize('value',INVALID)
@pytest.mark.parametrize('api',['device','Simulator','adaptive','saved'])
def test_invalid_cumulative_charge_rejects_before_state_or_worker(monkeypatch,value,api):
    def deny(*a,**kw):raise AssertionError('invalid charge budget reached state validation or migration')
    if api=='Simulator':
        source,initial,material=structured_case((3,1,1));monkeypatch.setattr(source,'to_three_temperature',deny)
        operation=lambda:source.run_three_temperature(initial,[initial.time_s],**dict(material,**RUN,cumulative_charge_atol_C=value))
    else:
        model,initial=factory('closed')
        if api=='device':
            device=Device(model,initial);monkeypatch.setattr(device,'_check_owned_state',deny)
            monkeypatch.setattr(Device,'__init__',deny)
            operation=lambda:device.run_transient([0.],**RUN,cumulative_charge_atol_C=value)
        else:
            monkeypatch.setattr(model,'_validate_state',deny)
            auditor=trajectory_audit if api=='adaptive' else saved_audit
            operation=lambda:auditor(model,initial,[],final_state=initial,**BUDGET,cumulative_charge_atol_C=value)
    with pytest.raises(ValueError,match='cumulative charge budget'):operation()


@pytest.mark.parametrize('budget',[np.nextafter(0.,1.),np.float64(1e-30),np.array(1e-29)])
def test_empty_charge_path_has_zero_storage_ports_and_residuals(monkeypatch,budget):
    model,initial=factory('closed');device=Device(model,initial)
    def deny(*a,**kw):raise AssertionError('empty charge path advanced')
    monkeypatch.setattr(Device,'advance',deny)
    result=device.run_transient([initial.time_s],**RUN,cumulative_charge_atol_C=budget)
    audit=result['trajectory_energy_audit']
    assert result['valid'] and result['native_advance_calls']==0
    assert audit['charge_path_valid'] and audit['maximum_cumulative_charge_error_C']==0
    assert audit['cumulative_charge_atol_C']==float(budget) and audit['cumulative_charge_budget_policy']=='explicit'
    saved=saved_audit(model,initial,[],final_state=initial,**BUDGET,cumulative_charge_atol_C=budget)
    assert saved['valid'] and saved['maximum_cumulative_charge_error_C']==0


def test_Simulator_detaches_and_forwards_charge_budget_before_migration(monkeypatch):
    source,initial,material=structured_case((3,1,1));budget=np.array(1e-30);calls=[]
    class Migrated:
        migration_report={'sentinel':'migration'}
        def run_transient(self,times,**kw):
            calls.append(kw);assert kw['cumulative_charge_atol_C']==1e-30 and budget==0
            return {'valid':True}
    migrated=Migrated()
    def migrate(*a,**kw):budget[...] = 0.;return migrated
    monkeypatch.setattr(source,'to_three_temperature',migrate)
    result=source.run_three_temperature(initial,[initial.time_s],**dict(material,**RUN,cumulative_charge_atol_C=budget))
    assert len(calls)==1 and result['device'] is migrated
