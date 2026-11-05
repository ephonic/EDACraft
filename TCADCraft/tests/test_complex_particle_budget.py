"""General 3T particle budgets qualify real complex-source trajectories."""
from pathlib import Path
import importlib.util,json,sys
import numpy as np
import pytest
from test_three_temperature_cell_path import factory
from test_three_temperature import BUDGET
from test_adaptive_three_temperature import OPTIONS
from test_structured_three_temperature import structured_case
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.solver.device_three_temperature import DeviceThreeTemperature as Device
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.postprocess.three_temperature_saved_path import audit_three_temperature_saved_path as saved_audit
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory as trajectory_audit

OUT=Path(__file__).resolve().parents[1]/'docs/validation/complex_particle_budget_20261022'
RUN=dict(OPTIONS,initial_step_s=7e-16,maximum_step_s=7e-16)
FIELDS=('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K')


def normalized(value):
    if isinstance(value,ThreeTemperatureState):
        return dict(__three_temperature_state__=True,time_s=value.time_s,
            **{k:normalized(getattr(value,k)) for k in FIELDS})
    if isinstance(value,np.ndarray):return normalized(value.tolist())
    if isinstance(value,np.longdouble):return np.format_float_scientific(value,precision=35,unique=False)
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {str(k):normalized(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [normalized(v) for v in value]
    return value


def decode(value):
    if isinstance(value,dict):
        if value.get('__three_temperature_state__'):
            return ThreeTemperatureState(**{k:np.array(value[k],dtype=np.longdouble if k in ('n_m3','p_m3') else float)
                for k in FIELDS},time_s=value['time_s'])
        if {'n_m3','p_m3','lattice_K','electron_K','hole_K','trap_fraction','time_s'}==set(value):
            return ThreeTemperatureState(np.array(value['n_m3'],np.longdouble),np.array(value['p_m3'],np.longdouble),
                value['trap_fraction'],value['lattice_K'],value['time_s'],value['electron_K'],value['hole_K'])
        return {int(k) if k.lstrip('-').isdigit() else k:decode(v) for k,v in value.items()}
    if isinstance(value,list):return [decode(v) for v in value]
    return value


def parent(name):
    package='solver' if name=='transient_three_temperature' else 'postprocess'
    label='tcad.'+package+'._frozen_complex_particle_'+name
    if label in sys.modules:return sys.modules[label]
    spec=importlib.util.spec_from_file_location(label,OUT/'before/tcad'/package/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[label]=module
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=old
    if name in ('three_temperature_trajectory','three_temperature_saved_path'):
        module.audit_cell_reservoir_path=parent('three_temperature_cell_path').audit_cell_reservoir_path
    return module


def freeze_result(name,data):
    directory=OUT/'accepted_records';directory.mkdir(exist_ok=True)
    target=directory/(name+'.json');data=normalized(data)
    if target.exists():assert json.loads(target.read_text())==data
    else:target.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


@pytest.mark.parametrize('name',['contact','varshni'])
def test_real_particle_failure_retains_native_state_and_retry_matches_frozen_parent(name):
    frozen=json.loads((OUT/('frozen_'+name+'_adaptive.json')).read_text())
    budget=frozen['trajectory_energy_audit']['cumulative_cell_particle_atol']
    strict=frozen['trajectory_energy_audit']['maximum_cumulative_cell_particle_error']/2
    assert 0<strict<budget
    model,initial=factory(name);device=Device(model,initial);old=device.state
    before=device.native_state();calls=[];advance=Device.advance
    def counted(self,*a,**kw):
        state,report=advance(self,*a,**kw)
        calls.append(dict(time_s=state.time_s,dt_s=report['dt_s'],independently_audited=report['independent_audit']['valid']))
        return state,report
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Device,'advance',counted)
        with pytest.raises(ThreeTemperatureTransientError) as caught:
            device.run_transient([7e-16],**RUN,cumulative_particle_atol=strict)
        diagnostic=caught.value.diagnostics;audit=diagnostic['trajectory_energy_audit']
        assert not diagnostic['published'] and diagnostic['failure_phase']=='cumulative_energy_audit'
        assert 'conservation audit failed' in diagnostic['failure']
        assert not audit['valid'] and not audit['cell_particle_path_valid']
        assert audit['cumulative_particle_atol']==audit['cumulative_cell_particle_atol']==strict
        assert audit['maximum_cumulative_cell_particle_error']==2*strict
        assert audit['maximum_cumulative_cell_energy_error_J']<=audit['cumulative_energy_atol_J']
        energy_terms=[audit['energy_residual_J'],audit['endpoint_energy_residual_J'],audit['electrical_work_residual_J'],
            audit['energy_residual_J']-audit['summed_substep_energy_residual_J'],
            *audit['storage_telescoping_error_J'].values(),*audit['reservoir_energy_residuals_J'].values()]
        assert max(map(abs,energy_terms))<=audit['cumulative_energy_atol_J']
        assert device.state is old and device.native_state()==before
        assert len(calls)==diagnostic['completed_interval_native_calls']==frozen['native_advance_calls']
        assert all(c['independently_audited'] for c in calls)
        retry=device.run_transient([7e-16],**RUN,cumulative_particle_atol=budget)
        assert retry['valid'] and device.state is retry['final_state']
        legacy_device=Device(model,initial)
        with pytest.MonkeyPatch.context() as legacy_patch:
            legacy_patch.setattr('tcad.postprocess.three_temperature_trajectory.audit_three_temperature_trajectory',
                parent('three_temperature_trajectory').audit_three_temperature_trajectory)
            legacy=parent('transient_three_temperature').run_transient(legacy_device,[7e-16],**RUN)
    assert len(calls)==3*frozen['native_advance_calls'] and all(c['independently_audited'] for c in calls)
    assert retry['trajectory_energy_audit']['cumulative_particle_budget_policy']=='explicit'
    left=normalized(retry);right=normalized(legacy)
    left['trajectory_energy_audit']={k:v for k,v in left['trajectory_energy_audit'].items() if k in right['trajectory_energy_audit']}
    assert left==right and device.native_state()==legacy_device.native_state()
    # Replacing the whole-path bound cannot change per-step tolerances or physics.
    assert retry['trajectory_energy_audit']['per_substep_particle_atol']==BUDGET['particle_atol']
    if name=='varshni':
        assert {'traps','photons','auger_internal'}<=set(audit['cell_reservoir_energy_residuals_J'])
        assert 'traps' in audit['cell_particle_balance_residuals']
        assert audit['band_work_from_lattice_J'] and audit['generated_pairs']!=0
    freeze_result(name,dict(name=name,strict_particle_budget=strict,default_particle_budget=budget,
        strict_diagnostics=diagnostic,retry=retry,parent_default=legacy,native_before=before,
        native_after=device.native_state(),observed_native_calls=calls,
        caller_state_identity_and_native_snapshot_retained=True,all_parent_existing_result_fields_exact=True))


FROZEN=tuple(sorted(p.name for p in OUT.glob('frozen_*.json')))


@pytest.mark.parametrize('filename',FROZEN)
def test_frozen_independent_paths_preserve_defaults_and_enforce_particle_budget_without_native(monkeypatch,filename):
    data=decode(json.loads((OUT/filename).read_text()));name=filename.removeprefix('frozen_').split('_')[0]
    model,initial=factory(name)
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native physics called during independent saved replay')
    for key in dir(native):
        if key.startswith('native_') and callable(getattr(native,key)):monkeypatch.setattr(native,key,deny)
    if filename.endswith('_adaptive.json'):
        args=(model,data['initial_state'],data['interval_reports']);kw=dict(final_state=data['final_state'],**BUDGET)
        auditor=trajectory_audit;old_auditor=parent('three_temperature_trajectory').audit_three_temperature_trajectory
    else:
        steps=[(v['old'],v['new'],v['report']) for v in data['steps']]
        args=(model,data['initial'],steps);kw=dict(final_state=data['final'],**BUDGET)
        auditor=saved_audit;old_auditor=parent('three_temperature_saved_path').audit_three_temperature_saved_path
    actual=auditor(*args,**kw);previous=old_auditor(*args,**kw)
    assert previous=={k:v for k,v in actual.items() if k in previous}==data.get('audit',data.get('trajectory_energy_audit'))
    assert actual['valid'] and actual['cell_particle_path_valid']
    explicit=auditor(*args,**kw,cumulative_particle_atol=actual['cumulative_particle_atol'])
    assert explicit==dict(actual,cumulative_particle_budget_policy='explicit')
    error=actual['maximum_cumulative_particle_error']
    if error>0:
        failed=auditor(*args,**kw,cumulative_particle_atol=error/2)
        assert not failed['valid'] and not failed['cell_particle_path_valid']
        assert failed['maximum_cumulative_cell_energy_error_J']<=failed['cumulative_energy_atol_J']
        assert failed['maximum_cumulative_particle_error']==error
    assert set(actual['global_particle_balance_from_cells'])==set(actual['cell_particle_balance_residuals'])


INVALID=(0.,-1.,np.nan,np.inf,-np.inf,True,'1e-9',[1e-9],1j,np.longdouble('1e4000'))


@pytest.mark.parametrize('value',INVALID)
@pytest.mark.parametrize('api',['device','Simulator','trajectory','saved'])
def test_invalid_budget_rejected_before_state_checks_worker_migration_or_native(monkeypatch,value,api):
    def deny(*a,**kw):raise AssertionError('invalid cumulative particle budget reached state or worker')
    if api=='Simulator':
        source,initial,material=structured_case((3,1,1))
        monkeypatch.setattr(source,'to_three_temperature',deny)
        operation=lambda:source.run_three_temperature(initial,[initial.time_s],**dict(material,**RUN,cumulative_particle_atol=value))
    else:
        model,initial=factory('closed')
        if api=='device':
            device=Device(model,initial);monkeypatch.setattr(device,'_check_owned_state',deny)
            monkeypatch.setattr(Device,'__init__',deny)
            operation=lambda:device.run_transient([0.],**RUN,cumulative_particle_atol=value)
        else:
            monkeypatch.setattr(model,'_validate_state',deny)
            auditor=trajectory_audit if api=='trajectory' else saved_audit
            operation=lambda:auditor(model,initial,[],final_state=initial,**BUDGET,cumulative_particle_atol=value)
    with pytest.raises(ValueError,match='cumulative particle budget'):operation()


@pytest.mark.parametrize('value',[np.nextafter(0.,1.),np.float64(1e-10),np.array(1e-9)])
def test_empty_explicit_budget_has_zero_balances_without_advance(monkeypatch,value):
    model,initial=factory('closed');device=Device(model,initial)
    def deny(*a,**kw):raise AssertionError('empty path advanced')
    monkeypatch.setattr(Device,'advance',deny)
    result=device.run_transient([initial.time_s],**RUN,cumulative_particle_atol=value)
    audit=result['trajectory_energy_audit']
    assert result['valid'] and result['native_advance_calls']==0
    assert audit['maximum_cumulative_particle_error']==0 and audit['cell_particle_path_valid']
    assert audit['cumulative_particle_atol']==float(value)
    assert audit['cumulative_particle_budget_policy']=='explicit'
    saved=saved_audit(model,initial,[],final_state=initial,**BUDGET,cumulative_particle_atol=value)
    assert saved['valid'] and saved['maximum_cumulative_particle_error']==0


def test_Simulator_detaches_particle_budget_before_migration_and_forwards(monkeypatch):
    source,initial,material=structured_case((3,1,1));budget=np.array(1e-9);calls=[]
    class Migrated:
        migration_report={'sentinel':'migration'}
        def run_transient(self,times,**kw):
            calls.append(kw)
            assert kw['cumulative_particle_atol']==1e-9 and budget==0
            return {'valid':True}
    migrated=Migrated()
    def migrate(*a,**kw):budget[...] = 0.;return migrated
    monkeypatch.setattr(source,'to_three_temperature',migrate)
    result=source.run_three_temperature(initial,[initial.time_s],**dict(material,**RUN,cumulative_particle_atol=budget))
    assert len(calls)==1 and result['device'] is migrated and result['migration_report']==migrated.migration_report


def test_same_sign_cell_particle_residuals_cannot_hide_in_device_total():
    # Controlled independent-ledger fault: each cell passes, their sum fails.
    from types import SimpleNamespace
    from tcad.postprocess.three_temperature_cell_path import audit_cell_reservoir_path
    old=ThreeTemperatureState([1.,1.],[1.,1.],[0.,0.],[300.,300.],0.,[300.,300.],[300.,300.])
    model=SimpleNamespace(nc=2,vol=np.ones(2),trap_capture_law=None,radiative_law=None,auger_events=None)
    from tcad.postprocess import three_temperature_cell_path as module
    keys=('energy_increments_J','carrier_exchange_to_lattice_J','band_work_from_lattice_J',
        'trap_carrier_energy_removed_J','radiative_carrier_energy_removed_J','auger_carrier_energy_added_J',
        'transport_energy_J','carrier_electrical_work_J','pair_generation_energy_J','particle_increments',
        'particle_transport','trap_capture_counts')
    ledger={key:{s:[0.,0.] for s in ('electrons','holes','lattice')} for key in keys}
    ledger.update({key:[0.,0.] for key in ('intercarrier_exchange_J','trap_lattice_heat_J','generated_pairs',
        'radiative_recombined_pairs','auger_recombined_pairs')})
    ledger['particle_transport']['electrons']=[.75,.75]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module,'endpoint_cell_storage',lambda *a:{s:np.zeros(2) for s in ('electrons','holes','lattice')})
        audit=audit_cell_reservoir_path(model,old,old,[ledger],energy_budget_J=1.,particle_budget=1.)
    assert audit['maximum_cumulative_cell_particle_error']==.75
    assert audit['global_particle_balance_from_cells']['electrons']==1.5
    assert audit['maximum_cumulative_particle_error']==1.5
    assert not audit['cell_particle_path_valid'] and not audit['cell_reservoir_path_valid']
