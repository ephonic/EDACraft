"""Actual coupled FD transport with an authoritative signed energy state."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step
from tcad.postprocess.energy_coordinate_transport import audit_energy_coordinate_step


def transport_case(count=2,a=-20000,c=20000,contacts=False):
    model,old=case(count=count,uniform=not contacts,contacts=contacts,voltage=.002 if contacts else 0.)
    model.relaxation_laws=(Law(150,5e24,a,0,c),)*2
    if count==2 and not contacts:
        old=replace(old,n_m3=np.array([1.005e25,.995e25]),p_m3=np.array([1.005e25,.995e25]))
    return model,old


@pytest.mark.parametrize('count,a,c',[(1,-20000,20000),(2,-20000,20000),(2,0,0),(2,-.4,.3)])
def test_actual_two_steps_keep_signed_energy_and_independent_local_global_closure(count,a,c):
    model,initial=transport_case(count,a,c);state=initialize_energy_coordinates(model,initial)
    for dt in (2e-14,3e-14):
        old=state;state,r=energy_coordinate_step(model,old,dt,**BUDGET)
        v=audit_energy_coordinate_step(model,old,state,r,**BUDGET)
        assert v['valid'] and v['modeled_fixed_band_energy_closed'],v
        assert v['total_evaluations']<=600
        assert not r['native_device_session_integrated'] and not r['complete_device_energy'] and not r['physical_validated']
        if a==-20000:
            assert any(0<abs(Decimal(e))<Decimal('1e-70') for e in state.excess_J_m3)
        if count==2:
            raw=r['raw']['transport']
            assert np.max(abs(state.thermal.n_m3-old.thermal.n_m3)/old.thermal.n_m3)>1e-5
            for key in ('fn','fp','energy_n','energy_p'):assert max(map(abs,raw[key]))>0
        assert not state.thermal.n_m3.flags.writeable
    if count==1:
        assert state.thermal.temperature_K[0]==pytest.approx(302.9182948437794,abs=2e-6)
        assert state.thermal.electron_temperature_K[0]==state.thermal.temperature_K[0]
        assert state.thermal.hole_temperature_K[0]==state.thermal.temperature_K[0]


@pytest.fixture(scope='module')
def accepted():
    model,initial=transport_case();old=initialize_energy_coordinates(model,initial)
    new,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    return model,old,new,r


@pytest.mark.parametrize('damage',['erase_stiff_excess','exchange','storage','heat','particle','tau','flux','energy_flux','temperature',
    'scope','physical','device','extra_channel','budget','cell_phi','face_phi','transport_tau','unused_local','native_source'])
def test_independent_audit_rejects_forgery(accepted,damage):
    model,old,new,report=accepted;r=deepcopy(report)
    if damage=='erase_stiff_excess':
        e=list(new.excess_J_m3);e[2]='0';new=replace(new,excess_J_m3=tuple(e));r['raw']['excess'][2]='0'
    elif damage in ('exchange','storage','heat','particle','tau'):
        pos={'exchange':7,'storage':4,'heat':13,'particle':0,'tau':14}[damage]
        value=Decimal(r['raw']['ledger'][pos])
        r['raw']['ledger'][pos]=str(value*2 if damage=='tau' else value+Decimal('1' if damage=='particle' else '1e-10'))
    elif damage in ('flux','energy_flux'):r['raw']['transport']['fn' if damage=='flux' else 'energy_n'][0]+=1e18 if damage=='flux' else 1e-3
    elif damage=='temperature':r['raw']['transport']['temperature_n'][0]+=1
    elif damage=='cell_phi':r['raw']['local_cells'][14]='1'
    elif damage=='face_phi':r['raw']['local_faces'][6]='1'
    elif damage=='transport_tau':r['raw']['transport']['tau_n'][0]*=2
    elif damage=='unused_local':r['raw']['transport']['local']=[0.]
    elif damage=='native_source':r['raw']['local_cells'][27]='1'
    elif damage=='scope':r['scope']='complete_device'
    elif damage=='physical':r['physical_validated']=True
    elif damage=='device':r['native_device_session_integrated']=True
    elif damage=='extra_channel':r['photons']=0
    else:r['shared_max_nfev']=1
    if damage=='extra_channel':
        with pytest.raises(ValueError,match='coverage'):audit_energy_coordinate_step(model,old,new,r,**BUDGET)
    else:assert not audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


def test_audit_replay_calls_no_production_physics(accepted,monkeypatch):
    model,old,new,r=accepted
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('production physics called by independent audit')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    for name in ('_poisson','carrier_reservoirs','split_face_transport','energies','conduction'):
        monkeypatch.setattr(model,name,deny)
    assert audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('budget',[1,10,52,53])
def test_failure_does_not_mutate_state_and_retry_matches_fresh(budget):
    model,initial=transport_case();old=initialize_energy_coordinates(model,initial)
    saved=(old.thermal.n_m3.tobytes(),old.thermal.temperature_K.tobytes(),old.excess_J_m3,old.thermal.time_s)
    with pytest.raises(RuntimeError,match='budget'):energy_coordinate_step(model,old,2e-14,max_nfev=budget,**BUDGET)
    assert saved==(old.thermal.n_m3.tobytes(),old.thermal.temperature_K.tobytes(),old.excess_J_m3,old.thermal.time_s)
    retry,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    fresh,rr=energy_coordinate_step(model,initialize_energy_coordinates(model,initial),2e-14,**BUDGET)
    assert retry.excess_J_m3==fresh.excess_J_m3 and r==rr
    np.testing.assert_array_equal(retry.thermal.n_m3,fresh.thermal.n_m3)


@pytest.mark.parametrize('channel',['b','band','intercarrier','generation','configuration'])
def test_unsupported_channels_or_changed_configuration_are_explicitly_rejected(channel):
    model,initial=transport_case();old=initialize_energy_coordinates(model,initial)
    if channel=='b':model.relaxation_laws=(Law(150,5e24,-20000,1,20000),)*2
    elif channel=='band':model.band_temperature_slopes=(np.ones(2)*1e-25,np.zeros(2))
    elif channel=='intercarrier':model.intercarrier_conductance_W_m3_K=np.ones(2)
    elif channel=='generation':model.pair_generation_rate_m3_s=np.ones(2)
    else:model.mn=np.array(model.mn)*2
    with pytest.raises(ValueError):energy_coordinate_step(model,old,2e-14,**BUDGET)


@pytest.mark.parametrize('contacts',[False,True])
def test_moderate_path_matches_existing_general_solver(contacts):
    model,initial=case(contacts=contacts,voltage=.002 if contacts else 0.)
    old=initialize_energy_coordinates(model,initial)
    new,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    other,rr=model.step(initial,2e-14,**BUDGET)
    for key in ('temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_allclose(getattr(new.thermal,key),getattr(other,key),rtol=0,atol=2e-6)
    np.testing.assert_allclose(new.thermal.n_m3,other.n_m3,rtol=1e-11)
