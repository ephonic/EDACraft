"""Internal conductance: independently reconstructed ports and rounding cost."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import numpy as np
import pytest
from scipy.optimize import root
from test_energy_coordinate_transport import transport_case,BUDGET
from test_energy_coordinate_generation import generation_case
from test_device_energy_coordinate_transport import assert_owned
from tcad.core._bindings import PyDeviceSimulator,native_energy_coordinate_transport_raw
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step,_pack
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.energy_coordinate_transport import audit_energy_coordinate_step
from tcad.postprocess.energy_coordinate_trajectory import audit_energy_coordinate_trajectory
from tcad.postprocess.energy_coordinate_exchange import exchange_increments
from tcad.postprocess.fermi_spectral_energy import reference_reservoir


def exchange_case(count=1,a=0,c=0,contacts=False,generated=False,g=1e15):
    model,initial=(generation_case if generated else transport_case)(count,a,c,contacts)
    model.intercarrier_conductance_W_m3_K=np.full(count,g) if count==1 else np.array([0.,g])
    return model,initial


@pytest.fixture(scope='module')
def accepted():
    model,initial=exchange_case();old=initialize_energy_coordinates(model,initial)
    new,report=energy_coordinate_step(model,old,2e-14,**BUDGET)
    return model,old,new,report


@pytest.mark.parametrize('hot,generated',[('n',False),('p',False),('n',True)])
def test_actual_step_matches_independent_FD_coupled_backward_euler(accepted,hot,generated):
    if hot=='n' and not generated:model,old,new,r=accepted
    else:
        model,initial=exchange_case(generated=generated)
        if hot=='p':initial=replace(initial,electron_temperature_K=[260.],hole_temperature_K=[360.])
        old=initialize_energy_coordinates(model,initial);new,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    t=old.thermal;dt=r['dt_s'];rate=model.pair_generation_rate_m3_s[0]
    density=[float(v[0])+dt*rate for v in (t.n_m3,t.p_m3)]
    def u(n,T,label):return reference_reservoir(n,T,0.,model.valleys[label])['energy_density_J_m3']
    initial=[u(v[0],T[0],label) for v,T,label in ((t.n_m3,t.electron_temperature_K,'electrons'),(t.p_m3,t.hole_temperature_K,'holes'))]
    def rows(T):
        carrier=[u(n,T[s],label) for s,(n,label) in enumerate(zip(density,('electrons','holes')))]
        relaxed=[dt*(carrier[s]-u(n,T[2],label))/tau for s,(n,label,tau) in
                 enumerate(zip(density,('electrons','holes'),(model.tau_n[0],model.tau_p[0])))]
        transfer=dt*1e15*(T[0]-T[1]);qn=dt*rate*model.pair_generation_kinetic_n_J[0];qp=dt*rate*model.pair_generation_kinetic_p_J[0]
        return np.array([carrier[0]-initial[0]+relaxed[0]+transfer-qn,
                         carrier[1]-initial[1]+relaxed[1]-transfer-qp,
                         model.capacity[0]*(T[2]-t.temperature_K[0])-sum(relaxed)])/1e6
    solution=root(rows,[310.,310.,301.],tol=1e-10)
    assert solution.success and max(abs(rows(solution.x)))<1e-8
    np.testing.assert_allclose([new.thermal.electron_temperature_K[0],new.thermal.hole_temperature_K[0],new.thermal.temperature_K[0]],solution.x,rtol=0,atol=2e-6)
    audit=r['independent_audit'];x=audit['reconstructed_intercarrier_exchange_J'][0]
    assert np.sign(x)==(1 if hot=='n' else -1)
    assert audit['intercarrier_temperature_rounding_bound_J'][0]>0
    assert audit['source_work_J']==0
    if not generated:assert 'absorbed_generation_energy_J' not in audit
    json.dumps(r)


@pytest.mark.parametrize('damage',['sign','one_side','cancelled','lattice','count','coefficient','off','negative','nan','infinite'])
def test_independent_audit_rejects_internal_source_forgery(accepted,damage):
    original,old,new,report=accepted;model=deepcopy(original);r=deepcopy(report);cells=r['raw']['local_cells']
    if damage=='sign':cells[29]=str(-Decimal(cells[29]));cells[30]=str(-Decimal(cells[30]))
    elif damage=='one_side':cells[29]='0'
    elif damage=='cancelled':cells[29]=str(Decimal(cells[29])+Decimal('1e-20'));cells[30]=str(Decimal(cells[30])-Decimal('1e-20'))
    elif damage=='lattice':cells[31]='1e-20'
    elif damage=='count':cells[27]='1'
    elif damage=='coefficient':model.intercarrier_conductance_W_m3_K*=2
    elif damage=='off':model.intercarrier_conductance_W_m3_K[:]=0
    else:model.intercarrier_conductance_W_m3_K[:]=dict(negative=-1.,nan=np.nan,infinite=np.inf)[damage]
    try:valid=audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']
    except ValueError:valid=False
    assert not valid


@pytest.mark.parametrize('damage',['negative','nan','infinite','marker','short','extra','optical_marker'])
def test_native_exchange_schema_rejection_is_retryable(damage):
    model,initial=exchange_case();state=initialize_energy_coordinates(model,initial);packed,_=_pack(model,initial,1.,**BUDGET)
    bad=deepcopy(list(packed));laws=bad[5]
    if damage in ('negative','nan','infinite'):laws[-1]=dict(negative='-1',nan='nan',infinite='1e400')[damage]
    elif damage=='marker':laws[10]='0'
    elif damage=='short':laws.pop()
    elif damage=='extra':laws.append('0')
    else:laws[10]='-1'
    backend=PyDeviceSimulator(1,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_energy_coordinate(*bad,state.excess_J_m3,0.)
    backend.configure_energy_coordinate(*packed,state.excess_J_m3,0.)
    assert backend.energy_coordinate_state()['time_s']==0.


@pytest.mark.parametrize('count,a,c,contacts,generated',[(1,-20000,20000,False,False),(2,-20000,20000,False,True),(2,-.4,.3,True,True)])
def test_actual_owned_and_functional_exchange_agree(count,a,c,contacts,generated):
    model,initial=exchange_case(count,a,c,contacts,generated)
    old=initialize_energy_coordinates(model,initial);new,r=energy_coordinate_step(model,old,2e-14,**BUDGET)
    device=Device(model,old);actual,rr=device.advance(2e-14,**BUDGET);assert_owned(device)
    assert new.excess_J_m3==actual.excess_J_m3 and r['raw']==rr['raw']
    if count==2:assert rr['independent_audit']['reconstructed_intercarrier_exchange_J'][0]==0
    assert not rr['complete_device_energy'] and not rr['physical_validated']


@pytest.mark.parametrize('temperatures',[(300.,300.),(256.,512.),(360.,260.),(1.1,99999.)])
def test_rounding_allowance_encloses_all_temperature_cell_corners(temperatures):
    model,initial=exchange_case();state=replace(initial,electron_temperature_K=[temperatures[0]],hole_temperature_K=[temperatures[1]])
    x,bound=exchange_increments(model,state,2e-14);ld=np.longdouble
    ends=[]
    for value in temperatures:
        ends.append(((ld(np.nextafter(value,-np.inf))-ld(value))/2,(ld(np.nextafter(value,np.inf))-ld(value))/2))
    factor=ld(2e-14)*ld(model.vol[0])*ld(1e15)
    for n in ends[0]:
        for p in ends[1]:assert abs(factor*(n-p))<=bound[0]
    assert bound[0]>0 and np.isfinite(x[0])


def test_unresolved_tiny_energy_cannot_bypass_rounding_budget_and_retry():
    model,initial=exchange_case(g=1e30)
    initial=replace(initial,electron_temperature_K=initial.temperature_K,hole_temperature_K=initial.temperature_K)
    state=replace(initialize_energy_coordinates(model,initial),excess_J_m3=('1e-120','-1e-120'))
    device=Device(model,state);before=device.native_state();old=device.state
    with pytest.raises(ValueError,match='rounding.*budget'):device.advance(2e-14,**BUDGET)
    assert device.native_state()==before and device.state is old
    loose={**BUDGET,'energy_atol_J':1e-15}
    actual,r=device.advance(2e-14,**loose)
    assert all(Decimal(v)!=0 for v in actual.excess_J_m3)
    audit=r['independent_audit'];assert audit['reconstructed_intercarrier_exchange_J']==[0.]
    assert audit['intercarrier_temperature_rounding_bound_J'][0]>BUDGET['energy_atol_J']
    from tcad.postprocess.device_energy_coordinate_transport import audit_device_energy_coordinate_step
    assert not audit_device_energy_coordinate_step(model,state,actual,r,**BUDGET)['valid']


def test_exchange_configuration_cannot_change_after_initialization():
    model,initial=exchange_case();old=initialize_energy_coordinates(model,initial)
    model.intercarrier_conductance_W_m3_K*=2
    with pytest.raises(ValueError,match='configuration changed'):energy_coordinate_step(model,old,2e-14,**BUDGET)


def test_independent_exchange_audit_calls_no_native_physics(accepted,monkeypatch):
    model,old,new,r=accepted
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('production operator used by independent exchange replay')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(model,'pair_generation_parameters',deny)
    for name in ('carrier_reservoirs','energies','_poisson','split_face_transport'):monkeypatch.setattr(model,name,deny)
    assert audit_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


def test_explicit_zero_exchange_quadruple_packet_preserves_generation_result():
    model,initial=generation_case();old=initialize_energy_coordinates(model,initial);packed,_=_pack(model,initial,2e-14,**BUDGET)
    legacy=native_energy_coordinate_transport_raw(*packed,old.excess_J_m3)
    extended=deepcopy(list(packed));extended[5][10]='-2';extended[5].append('0')
    assert native_energy_coordinate_transport_raw(*extended,old.excess_J_m3)==legacy


def test_accepted_path_closes_each_reservoir_with_generation_and_exchange():
    model,initial=exchange_case(generated=True);device=Device(model,initial);old=device.state
    options=dict(initial_step_s=2e-14,maximum_step_s=3e-14,minimum_step_s=1e-20,
        temperature_atol_K=1000.,temperature_rtol=0.,density_atol_m3=1e24,density_rtol=0.,
        excess_atol_J_m3=1e7,excess_rtol=0.,**BUDGET)
    result=device.run_transient([0.,2e-14,5e-14],**options);ledger=result['trajectory_energy_audit']
    assert ledger['valid'] and ledger['accepted_native_substeps']==4
    assert ledger['intercarrier_exchange_electron_to_hole_J']>0
    assert ledger['absorbed_generation_energy_J']>0 and ledger['source_work_J']==0
    assert max(map(abs,ledger['reservoir_energy_residuals_J'].values()))+ledger['intercarrier_temperature_rounding_bound_J']<=ledger['cumulative_energy_atol_J']
    assert audit_energy_coordinate_trajectory(model,old,result['interval_reports'],final_state=device.state,**BUDGET)==ledger
