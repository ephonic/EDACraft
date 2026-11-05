"""Independent FD roots, heat-direction, device ownership and channel auditing."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.core._bindings import native_three_temperature_dispatch_raw
from test_three_temperature import case,BUDGET
from test_device_three_temperature import assert_owned
from test_adaptive_three_temperature import closed,OPTIONS
from test_structured_three_temperature import structured_case


def coupled_case(g=1e15,**kwargs):
    base,old=case(**kwargs)
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=base.Ec,Eh_J=base.Eh,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=base.valleys['electrons'],valleys_p=base.valleys['holes'],
        thermionic_faces=base.thermionic_faces,particle_contacts=base.contacts,
        heat_bath_K=base.bath,terminal_groups=base.groups,
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        intercarrier_conductance_W_m3_K=g)
    return model,old


@pytest.mark.parametrize('scale,hot',( (1e-5,'n'),(1.,'n'),(10.,'p')))
def test_closed_step_matches_independent_degenerate_FD_root(scale,hot):
    model,old=coupled_case(count=1,uniform=True,density_scale=scale)
    if hot=='p':old=replace(old,electron_temperature_K=[260.],hole_temperature_K=[360.])
    dt=2e-13
    def u(t,s):return reference_reservoir(old.n_m3[0],t,0.,model.valleys[s])['energy_density_J_m3']
    initial=(u(old.electron_temperature_K[0],'electrons'),u(old.hole_temperature_K[0],'holes'))
    def rows(t):
        un,up=u(t[0],'electrons'),u(t[1],'holes')
        en=dt*(un-u(t[2],'electrons'))/model.tau_n[0]
        ep=dt*(up-u(t[2],'holes'))/model.tau_p[0]
        eh=dt*1e15*(t[0]-t[1])
        return np.array([un-initial[0]+en+eh,up-initial[1]+ep-eh,
                         model.capacity[0]*(t[2]-old.temperature_K[0])-en-ep])/1e6
    solution=root(rows,[310.,310.,300.],tol=1e-10)
    assert solution.success and max(abs(rows(solution.x)))<1e-8
    new,report=model.step(old,dt,**BUDGET)
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
                               solution.x,rtol=0.,atol=2e-6)
    assert np.sign(report['cell_intercarrier_exchange_J'][0])==(1 if hot=='n' else -1)
    np.testing.assert_array_equal(new.n_m3,old.n_m3)
    np.testing.assert_array_equal(new.p_m3,old.p_m3)
    assert report['independent_audit']['valid']


@pytest.mark.parametrize('kwargs',[dict(contacts=True,voltage=.002),
    dict(contacts=True,voltage=-.002,density_scale=10),dict(nonuniform=True)])
def test_actual_device_two_steps_include_exchange_and_all_ports(kwargs):
    model,old=coupled_case(g=[0.,1e15],**kwargs);device=DeviceThreeTemperature(model,old)
    for _ in range(2):
        new,report=device.advance(2e-13,**BUDGET)
        assert_owned(device,new)
        assert report['cell_intercarrier_exchange_J'][0]==0.
        assert abs(report['cell_intercarrier_exchange_J'][1])>1e-26
        assert audit_three_temperature_energy(device._model,old,new,report,**BUDGET)['valid']
        assert not report['complete_device_energy'] and not report['physical_validated']
        old=new


def test_explicit_reference_orchestration_uses_native_exchange_assembly():
    model,old=coupled_case(contacts=True,voltage=.002)
    native,report=model.step(old,2e-13,**BUDGET)
    model.residual_orchestration='python'
    ref,given=model.step(old,2e-13,**BUDGET)
    for f in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_allclose(getattr(native,f),getattr(ref,f),rtol=1e-10,atol=1e-8)
    np.testing.assert_allclose(report['cell_intercarrier_exchange_J'],given['cell_intercarrier_exchange_J'],rtol=1e-10)


@pytest.mark.parametrize('damage',['sign','missing','law','nan','shape','lattice','coefficient'])
def test_independent_audit_rejects_false_channel_even_when_device_total_cancels(damage):
    model,old=coupled_case(count=1,uniform=True)
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    if damage=='sign':bad['cell_intercarrier_exchange_J'] *= -1
    elif damage=='missing':bad.pop('cell_intercarrier_exchange_J')
    elif damage=='law':bad['intercarrier_exchange_law']='unverified_microscopic_kernel'
    elif damage=='nan':bad['cell_intercarrier_exchange_J'][0]=np.nan
    elif damage=='shape':bad['cell_intercarrier_exchange_J']=np.zeros(2)
    elif damage=='lattice':bad['cell_exchange_J']['electrons'] += bad['cell_intercarrier_exchange_J']
    else:model.intercarrier_conductance_W_m3_K=np.zeros(1)
    try:accepted=audit_three_temperature_energy(model,old,new,bad,**BUDGET)['valid']
    except ValueError:accepted=False
    assert not accepted


@pytest.mark.parametrize('bad',[-1.,np.nan,np.inf,True,1j,'1',[],[1.,2.,3.]])
def test_invalid_coefficient_rejected_at_construction(bad):
    with pytest.raises(ValueError):coupled_case(g=bad)


def test_constructor_detaches_and_freezes_coefficient():
    given=np.array([1e15,2e15]);model,_=coupled_case(g=given);given[:]=0.
    np.testing.assert_array_equal(model.intercarrier_conductance_W_m3_K,[1e15,2e15])
    with pytest.raises(ValueError):model.intercarrier_conductance_W_m3_K.flags.writeable=True


@pytest.mark.parametrize('damage',['negative','nan','infinite','marker','short','extra'])
def test_raw_dispatch_rejects_invalid_coupling_schema(damage):
    model,old=coupled_case(count=1,uniform=True)
    args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET));params=list(args[-1])
    if damage=='negative':params[-1]=-1.
    elif damage=='nan':params[-1]=np.nan
    elif damage=='infinite':params[-1]=np.inf
    elif damage=='marker':params[17]=0.
    elif damage=='short':params.pop()
    else:params.append(0.)
    args[-1]=params
    with pytest.raises(ValueError):native_three_temperature_dispatch_raw(*args,600)


def test_zero_coupling_preserves_original_dispatch_schema_and_state_exactly():
    base,old=case(count=1,uniform=True)
    zero,_=coupled_case(g=0.,count=1,uniform=True)
    assert len(pack_three_temperature_inputs(zero,old,2e-13,**BUDGET)[-1])==7
    a,ar=base.step(old,2e-13,**BUDGET);b,br=zero.step(old,2e-13,**BUDGET)
    for f in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(a,f),getattr(b,f))
    assert ar['independent_audit']==br['independent_audit']
    assert not np.any(br['cell_intercarrier_exchange_J'])


def test_equal_temperature_has_no_spurious_exchange():
    model,old=coupled_case(count=1,uniform=True)
    old=replace(old,electron_temperature_K=old.temperature_K,hole_temperature_K=old.temperature_K)
    new,report=model.step(old,2e-13,**BUDGET)
    np.testing.assert_array_equal(new.electron_temperature_K,old.electron_temperature_K)
    assert not np.any(report['cell_intercarrier_exchange_J'])


def test_independent_audit_calls_no_production_operators(monkeypatch):
    model,old=coupled_case(count=1,uniform=True);new,report=model.step(old,2e-13,**BUDGET)
    def forbidden(*a,**k):raise AssertionError('production operator used')
    for name in ('_poisson','carrier_reservoirs','split_face_transport','conduction','energies','relaxation_times'):
        monkeypatch.setattr(model,name,forbidden)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']


def test_actual_transient_channel_ledger_and_failure_rollback():
    model,old=closed();model.intercarrier_conductance_W_m3_K=np.array([2e9])
    device=DeviceThreeTemperature(model,old)
    run=dict(OPTIONS,initial_step_s=1e-13,maximum_step_s=1e-13)
    before=deepcopy(device.native_state())
    with pytest.raises(ThreeTemperatureTransientError):device.run_transient([0.,1e-13,2e-13],**dict(run,max_intervals=1))
    assert before==device.native_state() and device.state.time_s==0.
    result=device.run_transient([0.,1e-13,2e-13],**run)
    ledger=result['trajectory_energy_audit']
    assert ledger['valid'] and ledger['intercarrier_exchange_electron_to_hole_J']>1e-25
    assert max(abs(v) for v in ledger['reservoir_energy_residuals_J'].values())<=ledger['cumulative_energy_atol_J']
    assert ledger==audit_three_temperature_trajectory(device._model,old,result['interval_reports'],
        final_state=device.state,**BUDGET)
    assert_owned(device,device.state)


def test_simulator_public_entry_inherits_explicit_constant_conductance():
    source,old,options=structured_case(shape=(2,1,1),uniform=True)
    before=deepcopy(source._sim.structured_three_temperature_seed())
    result=source.run_three_temperature(old,[old.time_s,old.time_s+1e-15],
        **options,**{k:v for k,v in OPTIONS.items() if k not in BUDGET},
        initial_step_s=1e-15,maximum_step_s=1e-15,intercarrier_conductance_W_m3_K=1e15)
    device=result['device']
    assert np.all(device._model.intercarrier_conductance_W_m3_K==1e15)
    assert result['trajectory_energy_audit']['valid']
    assert result['trajectory_energy_audit']['intercarrier_exchange_electron_to_hole_J']>0
    assert before==source._sim.structured_three_temperature_seed()


def test_nonzero_lattice_and_density_exponents_can_coexist_with_intercarrier_exchange():
    from test_state_relaxation import LAWS
    model,old=coupled_case(count=1,uniform=True);model.relaxation_laws=LAWS
    new,report=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    assert report['independent_audit']['valid'] and report['cell_intercarrier_exchange_J'][0]>0
    for s,tau in report['cell_relaxation_time_s'].items():
        assert tau[0] != (model.tau_n if s=='electrons' else model.tau_p)[0]
