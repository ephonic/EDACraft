"""Actual complex native paths and cancelling-cell accounting fault injection."""
from copy import deepcopy
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from test_temperature_dependent_bands import band_case
from test_varshni_temperature_bands import configure
from test_auger_device import auger_case
from test_adaptive_three_temperature import OPTIONS
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.three_temperature_saved_path import audit_three_temperature_saved_path
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory


def factory(name):
    if name=='closed':return case(count=1,uniform=True)
    if name=='contact':return case(count=2,contacts=True,voltage=.002,nonuniform=True)
    if name in ('combined','varshni'):
        model,initial=band_case(complex=True,contacts=True,count=2)
        return (configure(model) if name=='varshni' else model),initial
    return auger_case(count=1,radiation=True,absorption=name=='absorption',impact=name=='impact')


@pytest.fixture(scope='module',params=['closed','contact','combined','varshni','absorption','impact'])
def saved(request):
    model,initial=factory(request.param);device=DeviceThreeTemperature(model,initial);steps=[]
    for dt in (2e-16,5e-16):
        old=device.state;new,report=device.advance(dt,**BUDGET);steps.append((old,new,report))
    result=audit_three_temperature_saved_path(model,initial,steps,final_state=device.state,**BUDGET)
    return model,initial,steps,device.state,result


def replay(saved,**kw):
    model,initial,steps,final,_=saved
    return audit_three_temperature_saved_path(model,initial,steps,final_state=final,**dict(BUDGET,**kw))


def test_every_native_saved_cell_and_reservoir_closes(saved):
    model,initial,steps,final,result=saved
    assert result['valid'] and result['cell_reservoir_path_valid']
    assert result['independently_reaudited_cell_reservoirs']
    assert set(result['cell_reservoir_energy_residuals_J'])==set(result['reservoir_energy_residuals_J'])
    assert all(len(row)==model.nc for row in result['cell_reservoir_energy_residuals_J'].values())
    for key,row in result['cell_reservoir_energy_residuals_J'].items():
        assert max(map(abs,row))<=result['cumulative_energy_atol_J']
        assert abs(sum(row)-result['reservoir_energy_residuals_J'][key])<1e-28
    assert result['maximum_cumulative_cell_particle_error']<=2*BUDGET['particle_atol']
    assert not result['complete_device_energy'] and not result['physical_validated']
    if model.trap_capture_law is not None:
        assert set(result['cell_particle_balance_residuals'])=={'electrons','holes','traps'}
        assert {'traps','photons','auger_internal'}<=set(result['cell_reservoir_energy_residuals_J'])


def test_saved_replay_ignores_attached_cell_ledgers_and_native_operators(saved,monkeypatch):
    model,initial,steps,final,result=saved;steps=deepcopy(steps)
    for old,new,report in steps:
        report['independent_audit']={'valid':True,'independently_reconstructed_cell_ledger':{'fake':[1e100]}}
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native operator called by independent path audit')
    for key in dir(native):
        if key.startswith('native_') and callable(getattr(native,key)):monkeypatch.setattr(native,key,deny)
    assert audit_three_temperature_saved_path(model,initial,steps,final_state=final,**BUDGET)==result


def test_empty_path_reports_explicit_zero_cell_balances(saved):
    model,initial,_,_,_=saved
    result=audit_three_temperature_saved_path(model,initial,[],final_state=initial,**BUDGET)
    assert result['valid'] and result['maximum_cumulative_cell_energy_error_J']==0
    assert result['maximum_cumulative_cell_particle_error']==0
    assert all(all(x==0 for x in row) for row in result['cell_reservoir_energy_residuals_J'].values())


@pytest.mark.parametrize('name',['closed','contact','varshni'])
def test_actual_adaptive_path_reaudits_cell_sources_and_endpoints(name):
    model,initial=factory(name);device=DeviceThreeTemperature(model,initial)
    result=device.run_transient([initial.time_s+7e-16],**dict(OPTIONS,
        initial_step_s=7e-16,maximum_step_s=7e-16))
    audit=result['trajectory_energy_audit']
    assert audit['valid'] and audit['cell_reservoir_path_valid']
    assert audit==audit_three_temperature_trajectory(model,initial,result['interval_reports'],
        final_state=device.state,**BUDGET)
    steps=[];previous=initial
    for interval in result['interval_reports']:
        for state,report in zip(interval['substep_states'],interval['substep_reports']):
            steps.append((previous,state,report));previous=state
    saved=audit_three_temperature_saved_path(model,initial,steps,final_state=previous,**BUDGET)
    for key in ('cell_reservoir_energy_residuals_J','cell_particle_balance_residuals',
                'cell_endpoint_energy_increments_J','cell_storage_telescoping_error_J'):
        assert audit[key]==saved[key]


@pytest.fixture(scope='module')
def coupled_path():
    model,initial=factory('varshni');device=DeviceThreeTemperature(model,initial)
    path=device.run_transient([7e-16],**dict(OPTIONS,initial_step_s=7e-16,maximum_step_s=7e-16))
    return model,initial,device.state,path


@pytest.mark.parametrize('kind',['transport','storage','particles','trap_particles','photon','auger'])
@pytest.mark.parametrize('api',['saved','adaptive'])
def test_opposite_cell_errors_cannot_hide_in_global_sums(monkeypatch,kind,api,coupled_path):
    model,initial,final,path=coupled_path
    # Native physics is run before injecting an independent-audit fault.
    import tcad.postprocess.three_temperature_energy as independent
    original=independent.audit_three_temperature_energy
    def altered(*a,**kw):
        result=original(*a,**kw);ledger=result['independently_reconstructed_cell_ledger']
        if kind=='transport':row=ledger['transport_energy_J']['electrons']
        elif kind=='storage':row=ledger['energy_increments_J']['lattice']
        elif kind=='particles':row=ledger['particle_transport']['electrons']
        elif kind=='trap_particles':row=ledger['occupied_trap_increment']
        elif kind=='photon':row=ledger['radiative_photon_energy_J']
        else:row=ledger['auger_carrier_energy_added_J']['electrons']
        amount=20*BUDGET['particle_atol'] if 'particles' in kind else 20*BUDGET['energy_atol_J']
        row[0]+=amount;row[1]-=amount
        return result
    target='tcad.postprocess.three_temperature_'+('saved_path' if api=='saved' else 'trajectory')
    monkeypatch.setattr(target+'.audit_three_temperature_energy',altered)
    if api=='saved':
        previous=initial;steps=[]
        for interval in path['interval_reports']:
            for state,report in zip(interval['substep_states'],interval['substep_reports']):
                steps.append((previous,state,report));previous=state
        result=audit_three_temperature_saved_path(model,initial,steps,final_state=final,**BUDGET)
    else:
        result=audit_three_temperature_trajectory(model,initial,path['interval_reports'],final_state=final,**BUDGET)
    assert not result['valid'] and not result['cell_reservoir_path_valid']
    assert not result['modeled_device_energy_closed']
    # The original global channels cannot see this spatially cancelling fault.
    assert max(map(abs,result['reservoir_energy_residuals_J'].values()))<=result['cumulative_energy_atol_J']
