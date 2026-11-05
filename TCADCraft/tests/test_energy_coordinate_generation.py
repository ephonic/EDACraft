"""Declared pair injection: native species balances and independent ports."""
from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from scipy.optimize import root
from test_energy_coordinate_transport import transport_case,BUDGET
from test_device_energy_coordinate_transport import assert_owned
from tcad.core._bindings import PyDeviceSimulator
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step,_pack
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.energy_coordinate_transport import audit_energy_coordinate_step
from tcad.postprocess.energy_coordinate_trajectory import audit_energy_coordinate_trajectory
from tcad.postprocess.fermi_spectral_energy import reference_reservoir


def generation_case(count=1,a=0,c=0,contacts=False):
    model,initial=transport_case(count,a,c,contacts)
    model.pair_generation_rate_m3_s=np.array([1e35] if count==1 else [0.,2e35])
    model.pair_generation_kinetic_n_J=np.full(count,1e-19)
    model.pair_generation_kinetic_p_J=np.full(count,2e-19)
    return model,initial


@pytest.fixture(scope='module')
def accepted():
    model,initial=generation_case()
    old=initialize_energy_coordinates(model,initial)
    new,report=energy_coordinate_step(model,old,2e-14,**BUDGET)
    return model,old,new,report


def test_actual_one_cell_matches_independent_FD_backward_euler(accepted):
    model,old,new,report=accepted;t=old.thermal;dt=report['dt_s'];rate=model.pair_generation_rate_m3_s[0]
    n=float(t.n_m3[0])+dt*rate;p=float(t.p_m3[0])+dt*rate
    def u(density,T,label):return reference_reservoir(density,T,0.,model.valleys[label])['energy_density_J_m3']
    before=(u(t.n_m3[0],t.electron_temperature_K[0],'electrons'),u(t.p_m3[0],t.hole_temperature_K[0],'holes'))
    def rows(T):
        un=u(n,T[0],'electrons');up=u(p,T[1],'holes')
        en=dt*(un-u(n,T[2],'electrons'))/model.tau_n[0]
        ep=dt*(up-u(p,T[2],'holes'))/model.tau_p[0]
        return np.array([un-before[0]+en-dt*rate*1e-19,up-before[1]+ep-dt*rate*2e-19,
                         model.capacity[0]*(T[2]-t.temperature_K[0])-en-ep])/1e6
    solution=root(rows,[350.,265.,301.],tol=1e-10)
    assert solution.success and max(abs(rows(solution.x)))<1e-8
    np.testing.assert_allclose([new.thermal.electron_temperature_K[0],new.thermal.hole_temperature_K[0],new.thermal.temperature_K[0]],
                              solution.x,rtol=0,atol=2e-6)
    # Compare the analytic density in the declared integrated-particle budget.
    # A float64 relative threshold below the allowed Newton error is unrelated
    # to the configured physical budget. Keep the temperature/root checks above.
    for actual,previous in ((new.thermal.n_m3,t.n_m3),(new.thermal.p_m3,t.p_m3)):
        expected=previous.astype(np.longdouble)+np.longdouble(dt)*np.longdouble(rate)
        assert max(abs(model.vol.astype(np.longdouble)*(actual-expected)))<=BUDGET['particle_atol']
    checked=report['independent_audit'];assert checked['valid']
    assert checked['absorbed_generation_energy_J']==pytest.approx(dt*model.vol[0]*rate*3e-19,rel=1e-15)
    assert checked['source_work_J']==0
    json.dumps(report)  # Public reports must remain serializable.


@pytest.mark.parametrize('damage',['electron_count','hole_count','electron_energy','hole_energy','cancelled_energy',
                                    'lattice_energy','band_work','rate','partition','turn_off'])
def test_species_and_port_audit_rejects_forgery(accepted,damage):
    original,old,new,report=accepted;model=deepcopy(original);r=deepcopy(report);cells=r['raw']['local_cells']
    if damage in ('electron_count','hole_count'):cells[27+(damage=='hole_count')]='1'
    elif damage in ('electron_energy','hole_energy'):cells[29+(damage=='hole_energy')]='1e-20'
    elif damage=='cancelled_energy':cells[29]='1e-20';cells[30]='-1e-20'
    elif damage=='lattice_energy':cells[31]='1e-20'
    elif damage=='band_work':cells[32]='1e-20'
    elif damage=='rate':model.pair_generation_rate_m3_s*=2
    elif damage=='partition':model.pair_generation_kinetic_n_J*=2;model.pair_generation_kinetic_p_J*=.5
    else:model.pair_generation_rate_m3_s[:]=0
    assert not audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


def test_independent_generation_audit_uses_no_production_physics(accepted,monkeypatch):
    model,old,new,r=accepted
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('production physics reached by independent pair-source audit')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(model,'pair_generation_parameters',deny)
    for name in ('carrier_reservoirs','energies','_poisson','split_face_transport'):
        monkeypatch.setattr(model,name,deny)
    assert audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['marker','short','extra','negative','nan','infinite','zero_energy','negative_energy'])
def test_raw_source_schema_rejection_leaves_native_configuration_retryable(damage):
    model,initial=generation_case();state=initialize_energy_coordinates(model,initial)
    packed,_=_pack(model,initial,1.,**BUDGET);bad=deepcopy(list(packed));laws=bad[5]
    if damage=='marker':laws[10]='0'
    elif damage=='short':laws.pop()
    elif damage=='extra':laws.append('0')
    elif damage=='negative':laws[11]='-1'
    elif damage=='nan':laws[11]='nan'
    elif damage=='infinite':laws[11]='1e400'
    elif damage=='zero_energy':laws[12]=laws[13]='0'
    else:laws[12]=laws[13]='-1e-19'
    backend=PyDeviceSimulator(1,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_energy_coordinate(*bad,state.excess_J_m3,0.)
    backend.configure_energy_coordinate(*packed,state.excess_J_m3,0.)
    assert backend.energy_coordinate_state()['time_s']==0.


@pytest.mark.parametrize('count,a,c,contacts',[(1,-20000,20000,False),(2,-20000,20000,False),(2,-.4,.3,True)])
def test_actual_transport_generation_matches_owned_device(count,a,c,contacts):
    model,initial=generation_case(count,a,c,contacts);old=initialize_energy_coordinates(model,initial)
    new,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    device=Device(model,old);actual,rr=device.advance(2e-14,**BUDGET);assert_owned(device)
    assert new.excess_J_m3==actual.excess_J_m3 and r['raw']==rr['raw']
    assert rr['independent_audit']['absorbed_generation_energy_J']>0
    if count==2:assert rr['independent_audit']['reconstructed_generated_pairs'][0]==0
    assert not rr['complete_device_energy'] and not rr['physical_validated']


def test_rejected_candidate_preserves_owned_state_and_retry():
    model,initial=generation_case();device=Device(model,initial);before=device.native_state();old=device.state
    with pytest.raises(RuntimeError,match='budget'):device.advance(2e-14,max_nfev=1,**BUDGET)
    assert device.native_state()==before and device.state is old
    actual,r=device.advance(2e-14,**BUDGET);expected,rr=Device(model,initial).advance(2e-14,**BUDGET)
    assert actual.excess_J_m3==expected.excess_J_m3 and r==rr


def test_source_configuration_is_immutable_after_initialization():
    model,initial=generation_case();state=initialize_energy_coordinates(model,initial)
    model.pair_generation_kinetic_n_J*=2
    with pytest.raises(ValueError,match='configuration changed'):energy_coordinate_step(model,state,2e-14,**BUDGET)


def test_explicit_zero_source_packet_matches_legacy_raw_result_exactly():
    from tcad.core._bindings import native_energy_coordinate_transport_raw
    model,initial=transport_case(1,0,0);state=initialize_energy_coordinates(model,initial)
    packed,_=_pack(model,initial,2e-14,**BUDGET)
    legacy=native_energy_coordinate_transport_raw(*packed,state.excess_J_m3)
    extended=deepcopy(list(packed));extended[5].extend(['-1','0','1e-19','2e-19'])
    assert native_energy_coordinate_transport_raw(*extended,state.excess_J_m3)==legacy


def test_accepted_path_counts_only_half_steps_and_absorbed_source():
    model,initial=generation_case();device=Device(model,initial);old=device.state
    options=dict(initial_step_s=2e-14,maximum_step_s=3e-14,minimum_step_s=1e-20,
        temperature_atol_K=1000.,temperature_rtol=0.,density_atol_m3=1e24,density_rtol=0.,
        excess_atol_J_m3=1e7,excess_rtol=0.,**BUDGET)
    result=device.run_transient([0.,2e-14,5e-14],**options)
    ledger=result['trajectory_energy_audit'];assert ledger['valid'] and ledger['accepted_native_substeps']==4
    expected=5e-14*model.vol[0]*model.pair_generation_rate_m3_s[0]
    assert ledger['generated_pairs']==pytest.approx(expected,rel=1e-15)
    assert ledger['absorbed_generation_energy_J']==pytest.approx(expected*3e-19,rel=1e-15)
    assert ledger['source_work_J']==0
    assert abs(ledger['endpoint_energy_residual_J'])<=ledger['cumulative_energy_atol_J']
    replay=audit_energy_coordinate_trajectory(model,old,result['interval_reports'],final_state=device.state,**BUDGET)
    assert replay==ledger
