"""Radiation in signed-energy FD transport, including original negative a.

The direct-gap optical coefficients are controls, not silicon material data.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import numpy as np
import pytest
from test_radiative_device import radiative_case
from test_three_temperature import BUDGET
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step,_pack
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.energy_coordinate_transport import audit_energy_coordinate_step
from tcad.postprocess.energy_coordinate_trajectory import audit_energy_coordinate_trajectory

OUT=Path('docs/validation/energy_coordinate_radiative_20261022/accepted_records')


def radiation_case(kind):
    options={
        'emission':{},'absorption':dict(absorption=True,rate=1e10),
        'original_single':{},'original_transport':dict(count=2,source=True),
        'contact_sources':dict(count=2,contacts=True,voltage=.002,nonuniform=True,source=True),
    }[kind]
    model,initial=radiative_case(**options)
    if kind.startswith('original'):
        model.relaxation_laws=(Law(150.,5e24,-20000.,0.,20000.),)*2
    return model,initial


def encode(value):
    if hasattr(value,'excess_J_m3'):
        return dict(thermal=encode(value.thermal),excess_J_m3=value.excess_J_m3,
                    configuration_sha256=value.configuration_sha256)
    if hasattr(value,'n_m3'):
        return {k:encode(getattr(value,k)) for k in ('n_m3','p_m3','trap_fraction','temperature_K',
            'electron_temperature_K','hole_temperature_K','time_s')}
    if isinstance(value,np.ndarray):
        if value.dtype==np.dtype(np.longdouble):
            return [np.format_float_scientific(v,precision=35,unique=False) for v in value]
        return value.tolist()
    if isinstance(value,dict):return {k:encode(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encode(v) for v in value]
    if isinstance(value,np.generic):return value.item()
    return value


@pytest.fixture(scope='module',params=['emission','absorption','original_single','original_transport','contact_sources'])
def actual(request):
    kind=request.param;model,initial=radiation_case(kind)
    old=initialize_energy_coordinates(model,initial)
    new,report=energy_coordinate_step(model,old,1e-14,**BUDGET)
    OUT.mkdir(exist_ok=True)
    path=OUT/(kind+'.json');assert not path.exists()
    path.write_text(json.dumps(encode(dict(old=old,new=new,report=report)),indent=2)+'\n')
    return kind,model,old,new,report


def test_actual_radiation_conserves_each_reservoir_and_photon_port(actual):
    kind,model,old,new,r=actual;a=r['independent_audit']
    assert a['valid'] and a['modeled_fixed_band_energy_closed']
    assert a['radiative_material_calibrated'] is False
    assert a['radiative_entropy_production_J_K']>=0
    sign=-1 if kind=='absorption' else 1
    assert sign*a['radiative_photon_energy_J']>0
    assert sign*sum(a['reconstructed_radiative_recombined_pairs'])>0
    assert abs(sum(map(sum,a['reconstructed_radiative_carrier_source_J']))+a['radiative_photon_energy_J'])<1e-30
    assert not r['complete_device_energy'] and not r['physical_validated']
    if kind.startswith('original'):
        assert all(Decimal(v)!=0 for v in new.excess_J_m3)
        assert min(r['raw']['transport']['tau_n'])<1e-13
    if 'sources' in kind or kind=='original_transport':
        assert a['absorbed_generation_energy_J']>0
        assert max(a['intercarrier_temperature_rounding_bound_J'])>0


def test_independent_replay_uses_no_native_physics(actual,monkeypatch):
    kind,model,old,new,r=actual
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native physics used by independent photon audit')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    for name in ('radiative_parameters','pair_generation_parameters','carrier_reservoirs','energies','_poisson'):
        monkeypatch.setattr(model,name,deny)
    assert audit_energy_coordinate_step(model,old,new,r,**BUDGET)==r['independent_audit']


@pytest.mark.parametrize('damage',['photon','number','one_side','missing','zeroed','bath','rate','lattice','nan'])
def test_independent_audit_rejects_radiative_evidence_forgery(damage):
    saved=json.loads((OUT/'emission.json').read_text())
    # Share the actual module fixture rather than doing a new native solve.
    from tcad.solver.three_temperature import ThreeTemperatureState
    from tcad.solver.energy_coordinate_transport import EnergyCoordinateState
    def state(row):
        t=row['thermal'];t['n_m3']=np.array(t['n_m3'],np.longdouble);t['p_m3']=np.array(t['p_m3'],np.longdouble)
        return EnergyCoordinateState(ThreeTemperatureState(**t),tuple(row['excess_J_m3']),row['configuration_sha256'])
    model,_=radiation_case('emission');old=state(saved['old']);new=state(saved['new']);r=saved['report']
    moments=r['raw']['transport']['radiative_moments']
    if damage=='photon':moments[0][14]*=-1
    elif damage=='number':moments[0][4]*=-1
    elif damage=='one_side':moments[0][12]=0
    elif damage=='missing':del r['raw']['transport']['radiative_moments']
    elif damage=='zeroed':moments[0]=[0.]*19
    elif damage=='bath':model.photon_bath_temperature_K=np.array([3000.])
    elif damage=='rate':model.radiative_transition_rate_s=model.radiative_transition_rate_s*2
    elif damage=='lattice':r['raw']['local_cells'][31]='1e-20'
    else:moments[0][14]=float('nan')
    try:valid=audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']
    except ValueError:valid=False
    assert not valid


def test_nonstiff_coordinates_agree_with_existing_temperature_solver():
    model,initial=radiation_case('emission');old=initialize_energy_coordinates(model,initial)
    actual,r=energy_coordinate_step(model,old,1e-14,**BUDGET)
    expected,rr=model.step(initial,1e-14,**BUDGET)
    for field in ('electron_temperature_K','hole_temperature_K','temperature_K'):
        np.testing.assert_allclose(getattr(actual.thermal,field),getattr(expected,field),rtol=0,atol=2e-6)
    for field in ('n_m3','p_m3'):
        np.testing.assert_allclose(getattr(actual.thermal,field),getattr(expected,field),rtol=1e-12,atol=0)
    assert rr['independent_audit']['valid']


@pytest.mark.parametrize('damage',['bath_zero','rate_negative','short','extra','marker','gap'])
def test_native_schema_rejection_allows_retry(damage):
    from tcad.core._bindings import PyDeviceSimulator
    model,initial=radiation_case('emission');old=initialize_energy_coordinates(model,initial)
    packed,_=_pack(model,initial,1.,**BUDGET);bad=deepcopy(list(packed))
    if damage=='bath_zero':bad[5][-2]='0'
    elif damage=='rate_negative':bad[5][-1]='-1'
    elif damage=='short':bad[5].pop()
    elif damage=='extra':bad[5].append('0')
    elif damage=='marker':bad[5][10]='-2'
    else:bad[0][13]='0';bad[0][14]='0'
    backend=PyDeviceSimulator(1,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_energy_coordinate(*bad,old.excess_J_m3,0.)
    backend.configure_energy_coordinate(*packed,old.excess_J_m3,0.)
    assert backend.energy_coordinate_state()['time_s']==0.


def test_device_candidate_failure_rolls_back_then_retries(monkeypatch):
    model,initial=radiation_case('original_single');device=Device(model,initial)
    before=device.native_state();state=device.state;publish=device._publication
    def fail(*args):raise RuntimeError('controlled publication allocation failure')
    monkeypatch.setattr(device,'_publication',fail)
    with pytest.raises(RuntimeError,match='publication'):device.advance(1e-14,**BUDGET)
    assert device.state is state and device.native_state()==before
    monkeypatch.setattr(device,'_publication',publish)
    new,r=device.advance(1e-14,**BUDGET)
    assert r['independent_audit']['valid'] and new.thermal.time_s==1e-14


def test_complete_accepted_path_includes_independent_photon_ports():
    model,initial=radiation_case('original_transport');device=Device(model,initial);old=device.state
    options=dict(initial_step_s=1e-14,maximum_step_s=1e-14,minimum_step_s=1e-20,
        temperature_atol_K=1000.,temperature_rtol=0.,density_atol_m3=1e24,density_rtol=0.,
        excess_atol_J_m3=1e7,excess_rtol=0.,**BUDGET)
    result=device.run_transient([0.,1e-14,2e-14],**options)
    audit=result['trajectory_energy_audit']
    assert audit['valid'] and audit['accepted_native_substeps']==4
    assert audit['outward_energy_J']['photons']==audit['radiative_photon_energy_J']>0
    assert audit['radiative_recombined_pairs']>0 and audit['absorbed_generation_energy_J']>0
    assert min(audit['cell_generated_pairs'])>0
    np.testing.assert_allclose(audit['cell_net_pair_source'],
        np.array(audit['cell_generated_pairs'])-audit['cell_radiative_recombined_pairs'],rtol=1e-14,atol=1e-15)
    prior=json.loads((OUT/'trajectory.json').read_text())
    canonical=lambda value:json.loads(json.dumps(encode(value)))
    checkpoint=OUT/'trajectory_metadata.json';assert not checkpoint.exists()
    checkpoint.write_text(json.dumps(encode(dict(old=old,result=result,final=device.state)),indent=2)+'\n')
    assert canonical(old)==prior['old'] and canonical(device.state)==prior['final']
    assert canonical(result['interval_reports'])==prior['result']['interval_reports']
    assert audit['maximum_balance_error_J']<=audit['cumulative_energy_atol_J']
    assert audit_energy_coordinate_trajectory(model,old,result['interval_reports'],final_state=device.state,**BUDGET)==audit
    assert checkpoint.is_file()
