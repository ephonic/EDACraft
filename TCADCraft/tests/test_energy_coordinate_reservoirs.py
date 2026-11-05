"""Accepted-path species and cell balances cannot hide in a cancelling total."""
from copy import deepcopy
import json
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from test_energy_coordinate_generation import generation_case
from test_energy_coordinate_exchange import exchange_case
from test_adaptive_energy_coordinate import TRANSIENT
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.energy_coordinate_trajectory import audit_energy_coordinate_trajectory as audit
import tcad.postprocess.energy_coordinate_trajectory as replay


CASES=[('zero_original_single',transport_case,1,-20000,20000,False),
       ('zero_original_transport',transport_case,2,-20000,20000,False),
       ('zero_contact',transport_case,2,-.4,.3,True),
       ('generated_transport',generation_case,2,0,0,False),
       ('generated_contact',generation_case,2,-.4,.3,True),
       ('coupled_generated',exchange_case,2,-20000,20000,False)]


@pytest.fixture(scope='module')
def paths():
    # A focused retry only needs the requested physical path. Preserve the
    # same construction and per-module cache for the full parameter suite.
    class Paths(dict):
        def __missing__(self,name):
            _,factory,count,a,c,contact=next(case for case in CASES if case[0]==name)
            kwargs={'generated':True} if factory is exchange_case else {}
            model,initial=factory(count,a,c,contact,**kwargs)
            device=Device(model,initial);old=device.state
            path=device.run_transient([0.,2e-14,5e-14],**TRANSIENT)
            self[name]=(model,old,device,path)
            return self[name]
    return Paths()


def checked(case,**kw):
    model,old,device,path=case
    return audit(model,old,path['interval_reports'],final_state=device.state,**dict(BUDGET,**kw))


@pytest.mark.parametrize('name',[c[0] for c in CASES])
def test_real_path_closes_every_cell_and_reservoir_without_changing_native_steps(paths,name):
    model,old,device,path=paths[name];ledger=checked(paths[name])
    assert ledger==path['trajectory_energy_audit'] and ledger['valid']
    assert ledger['independently_reintegrated_all_face_ports']
    assert ledger['accepted_native_substeps']==4 and path['native_advance_calls']==6
    assert set(ledger['reservoir_energy_residuals_J'])=={'electrons','holes','lattice'}
    bounds=np.array(ledger['cell_intercarrier_temperature_rounding_bound_J'])
    for label,values in ledger['cell_reservoir_energy_residuals_J'].items():
        assert len(values)==model.nc
        assert max(abs(np.array(values))+bounds)<=ledger['cumulative_energy_atol_J']
        assert sum(values)==pytest.approx(ledger['reservoir_energy_residuals_J'][label],abs=1e-42)
    if name.startswith('zero'):
        assert np.all(bounds==0) and 'generation_law' not in ledger
    elif name.startswith('generated'):
        assert np.all(bounds==0) and ledger['absorbed_generation_energy_J']>0
    else:
        # Original negative-a stiffness collapses the rounded views, even
        # though the authoritative signed energies and uncertainty survive.
        assert np.max(bounds)>0 and ledger['intercarrier_exchange_electron_to_hole_J']==0
        active=model.intercarrier_conductance_W_m3_K!=0
        np.testing.assert_array_equal(device.state.thermal.electron_temperature_K[active],device.state.thermal.hole_temperature_K[active])
    assert not ledger['physical_validated'] and not ledger['complete_device_energy']
    assert not ledger['experimental_validated'] and not ledger['global_temporal_error_bound']
    json.dumps(ledger)


@pytest.mark.parametrize('name',[c[0] for c in CASES])
def test_stricter_explicit_whole_path_budget_cannot_be_hidden_by_substep_passes(paths,name):
    base=checked(paths[name]);maximum=base['maximum_balance_error_J']
    assert maximum>0
    result=checked(paths[name],cumulative_energy_atol_J=maximum/2)
    assert not result['valid'] and not result['modeled_fixed_band_energy_closed']
    assert result['maximum_balance_error_J']==maximum
    assert result['per_substep_energy_atol_J']==BUDGET['energy_atol_J']


@pytest.mark.parametrize('channel',['electrons','holes','lattice','opposite_species'])
def test_cancelling_port_faults_are_detected_below_the_total_energy_ledger(paths,monkeypatch,channel):
    case=paths['zero_contact'];baseline=checked(case);original=replay._ports
    delta=np.longdouble('1e-23')
    def damaged(*a,**kw):
        outward,transport,work=original(*a,**kw)
        if channel=='opposite_species':
            work[0]=work[0].astype(np.longdouble)+delta
            work[1]=work[1].astype(np.longdouble)-delta
        else:
            transport[channel]=transport[channel].astype(np.longdouble)+[delta,-delta]
        return outward,transport,work
    monkeypatch.setattr(replay,'_ports',damaged)
    result=checked(case)
    # Fault injection affects only the new independent cell/species evidence.
    # Every old global/endpoint/telescoping quantity remains identical.
    for key in ('energy_residual_J','endpoint_energy_residual_J','storage_telescoping_error_J',
                'source_work_J','outward_energy_J','summed_substep_energy_residual_J'):
        assert result[key]==baseline[key]
    assert not result['valid'] and result['maximum_balance_error_J']>float(delta)
    if channel!='opposite_species':
        assert max(map(abs,result['reservoir_energy_residuals_J'].values()))<BUDGET['energy_atol_J']


@pytest.mark.parametrize('name',['zero_contact','coupled_generated'])
def test_replay_reconstructs_ports_without_native_operators_or_cached_evidence(paths,monkeypatch,name):
    case=paths[name];expected=checked(case);model,old,device,path=case
    intervals=deepcopy(path['interval_reports'])
    for interval in intervals:
        interval['attempts']=[{'invented_cached_energy_J':1e100}]
        for report in interval['substep_reports']:
            report['independent_audit']={'valid':True,'reconstructed_electrical_work_J':[[1e100]]}
    def deny(*a,**kw):raise AssertionError('production constitutive operator used by independent replay')
    import tcad.core._bindings as native
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    # Configuration packing is still allowed; physical replay must not call
    # the production EOS, face operators, energies or Poisson wrapper.
    for name in ('carrier_reservoirs','energies','_poisson','split_face_transport'):
        monkeypatch.setattr(model,name,deny)
    assert audit(model,old,intervals,final_state=device.state,**BUDGET)==expected


def test_empty_path_has_explicit_zero_cell_and_reservoir_balances():
    model,initial=transport_case(2,0,0);device=Device(model,initial)
    ledger=device.run_transient([0.],**TRANSIENT)['trajectory_energy_audit']
    assert ledger['valid'] and ledger['accepted_native_substeps']==0
    assert ledger['reservoir_energy_residuals_J']==dict(electrons=0.,holes=0.,lattice=0.)
    assert all(values==[0.,0.] for values in ledger['cell_reservoir_energy_residuals_J'].values())
    assert ledger['cell_intercarrier_temperature_rounding_bound_J']==[0.,0.]


from pathlib import Path
import importlib.util,sys
from test_energy_record_finite import encode_state,decode_state

PARTICLE_OUT=Path(__file__).resolve().parents[1]/'docs/validation/energy_particle_path_20261022'

def particle_parent():
    name='tcad.postprocess.frozen_particle_path_parent'
    spec=importlib.util.spec_from_file_location(name,PARTICLE_OUT/'before/tcad/postprocess/energy_coordinate_trajectory.py')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=previous
    return module


@pytest.mark.parametrize('name',[c[0] for c in CASES])
def test_cumulative_particles_replay_exact_native_paths_and_preserve_old_energy_fields(paths,name):
    model,old,device,path=paths[name];now=checked(paths[name]);parent=particle_parent()
    before=parent.audit_energy_coordinate_trajectory(model,old,path['interval_reports'],final_state=device.state,**BUDGET)
    assert {k:now[k] for k in before}==before
    assert now['particle_path_valid'] and now['independently_reintegrated_particle_ports']
    assert now['cumulative_particle_atol']==4*BUDGET['particle_atol']
    for key in ('cell_particle_balance_residuals','cell_particle_telescoping_errors'):
        assert set(now[key])=={'electrons','holes'}
        assert all(len(v)==model.nc for v in now[key].values())
    intervals=[]
    for interval in path['interval_reports']:
        intervals.append(dict(valid=True,scope=interval['scope'],initial_state=encode_state(interval['initial_state']),
            accepted_native_substeps=2,accepted_interval_s=interval['accepted_interval_s'],
            substep_states=[encode_state(s) for s in interval['substep_states']],substep_reports=interval['substep_reports']))
    directory=PARTICLE_OUT/'accepted_records';directory.mkdir(exist_ok=True)
    target=directory/(name+'.json')
    capture=dict(name=name,initial=encode_state(old),final=encode_state(device.state),
        intervals=intervals,audit=now,parent_audit=before,native_advance_calls=path['native_advance_calls'],
        accepted_native_substeps=path['accepted_native_substeps'])
    if target.exists():assert json.loads(target.read_text())==json.loads(json.dumps(capture,allow_nan=False))
    else:target.write_text(json.dumps(capture,indent=2,allow_nan=False)+'\n')


@pytest.mark.parametrize('label',['electrons','holes'])
@pytest.mark.parametrize('spatial',['cancelling','uniform'])
def test_particle_port_faults_cannot_hide_behind_unchanged_energy(paths,monkeypatch,label,spatial):
    model,old,device,path=paths['zero_contact'];baseline=checked(paths['zero_contact'])
    parent=particle_parent();original=replay._ports
    def damaged(*a,**kw):
        outward,transport,work=original(*a,**kw)
        delta=np.longdouble(8*BUDGET['particle_atol'])
        transport['particle_'+label]=transport['particle_'+label]+[delta,-delta if spatial=='cancelling' else delta]
        return outward,transport,work
    monkeypatch.setattr(replay,'_ports',damaged);monkeypatch.setattr(parent,'_ports',damaged)
    previous=parent.audit_energy_coordinate_trajectory(model,old,path['interval_reports'],final_state=device.state,**BUDGET)
    now=checked(paths['zero_contact'])
    assert previous['valid'] and {k:now[k] for k in previous if k not in ('valid','modeled_fixed_band_energy_closed')}=={
        k:v for k,v in previous.items() if k not in ('valid','modeled_fixed_band_energy_closed')}
    assert not now['valid'] and not now['particle_path_valid'] and not now['modeled_fixed_band_energy_closed']
    assert now['maximum_balance_error_J']==baseline['maximum_balance_error_J']
    if spatial=='cancelling':assert abs(now['particle_balance_residuals'][label])<now['cumulative_particle_atol']


@pytest.mark.parametrize('value',[0.,-1.,np.nan])
def test_explicit_particle_budget_is_validated_before_native_free_replay(paths,value):
    with pytest.raises(ValueError):checked(paths['zero_contact'],cumulative_particle_atol=value)


@pytest.mark.parametrize('value',[np.nan,np.inf])
def test_nonfinite_independent_particle_port_is_rejected(paths,monkeypatch,value):
    original=replay._ports
    def damaged(*a,**kw):
        outward,transport,work=original(*a,**kw);transport['particle_holes'][0]=value
        return outward,transport,work
    monkeypatch.setattr(replay,'_ports',damaged)
    with pytest.raises(ValueError,match='particle path'):checked(paths['zero_contact'])


def test_strict_cumulative_particle_budget_is_independent_of_energy_acceptance(paths):
    baseline=checked(paths['zero_contact']);error=baseline['maximum_cumulative_particle_error']
    assert error>0
    now=checked(paths['zero_contact'],cumulative_particle_atol=error/2)
    assert not now['valid'] and not now['particle_path_valid']
    assert now['maximum_balance_error_J']==baseline['maximum_balance_error_J']
    assert now['per_substep_particle_atol']==BUDGET['particle_atol']
