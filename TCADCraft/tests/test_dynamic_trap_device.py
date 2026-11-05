"""Dynamic energy-resolved capture in native six-field device transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from test_three_temperature import case, BUDGET
from test_adaptive_three_temperature import OPTIONS
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.postprocess.spectral_trap_capture import reference_trap_capture
from tcad.physics.spectral_trap_capture import SpectralTrapState

Q=1.602176634e-19
FIELDS=('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K')
LAW='energy_resolved_local_detailed_balance'


def trap_case(*, count=1, contacts=False, voltage=0., nonuniform=False, mixed=False,
              generation=False, law=LAW, orchestration='native', Nt=3e23):
    base,old=case(count=count,uniform=not contacts,contacts=contacts,voltage=voltage,nonuniform=nonuniform)
    trap=np.full(count,Nt)
    if mixed:trap[0]=0.
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,
        dirichlet_V=base.bc,mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,
        Ec_J=base.Ec+.6*Q,Eh_J=base.Eh+.5*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=base.valleys['electrons'],valleys_p=base.valleys['holes'],
        thermionic_faces=base.thermionic_faces,particle_contacts=base.contacts,
        heat_bath_K=base.bath,terminal_groups=base.groups,
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        trap_density_m3=trap,trap_energy_J=.04*Q,capture_n_m3_s=3e-14,capture_p_m3_s=8e-15,
        trap_capture_law=law,residual_orchestration=orchestration,
        intercarrier_conductance_W_m3_K=1e15 if generation else 0.,
        pair_generation_rate_m3_s=1e35 if generation else 0.,
        pair_generation_kinetic_n_J=.025*Q,pair_generation_kinetic_p_J=.018*Q)
    old=replace(old,trap_fraction=np.full(count,.37))
    model.rhofix=Q*trap*old.trap_fraction
    return model,old


def assert_owned(device,state):
    raw=device.native_state()
    for k,f in [('n','n_m3'),('p','p_m3'),('trap_fraction','trap_fraction'),
                ('temperature_n','electron_temperature_K'),('temperature_p','hole_temperature_K'),
                ('temperature_l','temperature_K')]:
        np.testing.assert_array_equal(np.asarray(raw[k],getattr(state,f).dtype),getattr(state,f))


@pytest.mark.parametrize('options',[{},dict(count=2,mixed=True),dict(count=2,contacts=True,voltage=.002),
    dict(count=2,contacts=True,voltage=-.002,nonuniform=True,generation=True)])
def test_actual_coupled_step_conserves_all_reservoirs_and_trap_charge(options):
    model,old=trap_case(**options);new,r=model.step(old,2e-14,**BUDGET)
    assert r['independent_audit']['valid'] and r['dynamic_trap_device_coupled']
    assert not r['complete_device_energy'] and not r['physical_validated']
    assert np.max(abs(new.trap_fraction-old.trap_fraction))>1e-6
    if options.get('mixed'):assert new.trap_fraction[0]==old.trap_fraction[0]
    assert len(r['particle_residuals'])==3*model.nc
    assert abs(r['charge_balance_residual_C'])<=BUDGET['charge_atol_C']
    assert r['independent_audit']['max_trap_moment_scaled_error']<3e-10


def test_closed_six_unknown_backward_euler_matches_independent_DOS_root():
    model,old=trap_case();dt=2e-14;new,r=model.step(old,dt,**BUDGET)
    n0=float(old.n_m3[0]);p0=float(old.p_m3[0]);Nt=model.Nt[0];Et=model.Et[0]
    def reservoir(n,T,s):
        return reference_reservoir(n,T,(model.Ec if s=='electrons' else model.Eh)[0],model.valleys[s])
    u0=[reservoir(n0,360.,'electrons')['energy_density_J_m3'],
        reservoir(p0,260.,'holes')['energy_density_J_m3']]
    def residual(x):
        n,p=np.array([n0,p0])*np.exp(x[:2]);Tn,Tp,Tl=np.array([360.,260.,300.])*np.exp(x[2:5]);f=x[5]
        rn=reservoir(n,Tn,'electrons');rp=reservoir(p,Tp,'holes')
        ref=reference_trap_capture(SpectralTrapState(Tn,Tp,Tl,rn['chemical_potential_J'],rp['chemical_potential_J'],
            model.Ec[0],model.Eh[0],Nt,Et,model.cn[0],model.cp[0],f),*model.valleys.values())
        cn=dt*ref['net_capture_n_m3_s'];cp=dt*ref['net_capture_p_m3_s']
        en=-dt*ref['electron_energy_source_W_m3'];ep=-dt*ref['hole_energy_source_W_m3']
        un=rn['energy_density_J_m3'];up=rp['energy_density_J_m3']
        qn=dt*(un-reservoir(n,Tl,'electrons')['energy_density_J_m3'])/model.tau_n[0]
        qp=dt*(up-reservoir(p,Tl,'holes')['energy_density_J_m3'])/model.tau_p[0]
        heat=en+ep-Et*(cn-cp)
        return [(n-n0+cn)/n0,(p-p0+cp)/p0,(un-u0[0]+qn+en)/u0[0],
                (up-u0[1]+qp+ep)/u0[1],(model.capacity[0]*(Tl-300.)-qn-qp-heat)/(model.capacity[0]*300.),
                f-old.trap_fraction[0]-(cn-cp)/Nt]
    solved=root(residual,[0,0,0,0,0,.37],tol=1e-10)
    assert solved.success and max(abs(np.asarray(residual(solved.x))))<1e-12
    np.testing.assert_allclose([new.n_m3[0],new.p_m3[0]],np.array([n0,p0])*np.exp(solved.x[:2]),rtol=1e-10)
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
                              np.array([360.,260.,300.])*np.exp(solved.x[2:5]),rtol=0,atol=3e-6)
    assert abs(new.trap_fraction[0]-solved.x[5])<1e-10


def test_native_device_commits_occupancy_over_two_steps():
    model,old=trap_case();device=DeviceThreeTemperature(model,old);reference=old
    for _ in range(2):
        reference,_=model.step(reference,2e-14,**BUDGET)
        state,_=device.advance(2e-14,**BUDGET);assert_owned(device,state)
        for f in FIELDS:np.testing.assert_array_equal(getattr(state,f),getattr(reference,f))


@pytest.mark.parametrize('failure',['newton','audit','decode'])
def test_failed_dynamic_candidate_rolls_back_all_six_fields_and_retry(monkeypatch,failure):
    model,old=trap_case();device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',
                                        lambda *a,**k:dict(valid=False,reason='injected'))
        if failure=='decode':
            def reject(*a,**k):raise ValueError('injected')
            patch.setattr('tcad.solver.device_three_temperature.decode_three_temperature_output',reject)
        with pytest.raises((ValueError,RuntimeError)):device.advance(2e-14,**BUDGET,max_nfev=1 if failure=='newton' else 600)
    assert device.native_state()==saved;assert_owned(device,old)
    actual,_=device.advance(2e-14,**BUDGET);expected,_=DeviceThreeTemperature(model,old).advance(2e-14,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(actual,f),getattr(expected,f))


@pytest.mark.parametrize('damage',['capture','removed','heat','storage','entropy','moment','occupancy','scope','coverage'])
def test_independent_audit_rejects_forged_trap_or_frozen_occupancy(damage):
    model,old=trap_case();new,r=model.step(old,2e-14,**BUDGET);bad=deepcopy(r)
    if damage=='capture':bad['cell_trap_capture_counts']['electrons'][0]+=1e-4
    elif damage=='removed':bad['cell_trap_carrier_energy_removed_J']['holes'][0]+=1e-20
    elif damage=='heat':bad['cell_trap_lattice_heat_J'][0]+=1e-20
    elif damage=='storage':bad['energy_increments_J']['traps']+=1e-20
    elif damage=='entropy':bad['cell_trap_entropy_production_J_K'][0]+=1e-20
    elif damage=='moment':bad['cell_trap_moments'][0]['net_capture_n_m3_s']*=1.01
    elif damage=='occupancy':new=replace(new,trap_fraction=old.trap_fraction)
    elif damage=='scope':bad['dynamic_trap_device_coupled']=False
    else:bad['cell_trap_moments']=[]
    try: result=audit_three_temperature_energy(model,old,new,bad,**BUDGET)
    except ValueError:return
    assert not result['valid']


def test_audit_is_independent_of_native_operator_and_model_assembly(monkeypatch):
    model,old=trap_case();new,r=model.step(old,2e-14,**BUDGET)
    def forbidden(*a,**k):raise AssertionError('production function called')
    for f in ('_poisson','energies','carrier_reservoirs','split_face_transport','conduction'):
        monkeypatch.setattr(model,f,forbidden)
    monkeypatch.setattr('tcad.core._bindings.native_spectral_trap_capture_raw',forbidden)
    assert audit_three_temperature_energy(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('options',[dict(law='SRH'),dict(law=None),dict(orchestration='python'),dict(Nt=-1.)])
def test_opt_in_and_validated_native_configuration_required(options):
    with pytest.raises(ValueError):trap_case(**options)


@pytest.mark.parametrize('damage',['width','coefficient','nonfinite','gap','occupancy'])
def test_raw_schema_rejects_invalid_trap_inputs(damage):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=trap_case();c,f,vn,vp,p=pack_three_temperature_inputs(model,old,2e-14,**BUDGET)
    if damage=='width':p=p[:-1]
    elif damage=='coefficient':p[-1]=-1.
    elif damage=='nonfinite':p[-1]=np.nan
    elif damage=='gap':p[-3]=2*Q
    else:c[6]='0'
    with pytest.raises((ValueError,RuntimeError)):native_three_temperature_dispatch_raw(c,f,vn,vp,p,600)


def test_dynamic_adaptive_estimator_and_independent_path_ledger():
    model,old=trap_case();device=DeviceThreeTemperature(model,old)
    new,r=device.advance_adaptive(2e-14,**dict(OPTIONS,density_rtol=1e-4,temperature_atol_K=.1))
    attempt=r['attempts'][-1];full=attempt['states'][0]
    scale=OPTIONS['density_atol_m3']+1e-4*model.Nt*np.maximum(abs(old.trap_fraction),abs(new.trap_fraction))
    expected=float(max(model.Nt*abs(new.trap_fraction-full.trap_fraction)/scale))
    assert r['temporal_error_by_field']['occupied_trap_density_m3']==pytest.approx(expected,rel=1e-12)
    ledger=audit_three_temperature_trajectory(model,old,[r],final_state=new,**BUDGET)
    assert ledger['valid'] and 'traps' in ledger['energy_increments_J']
    assert abs(ledger['trap_particle_balance_residual'])<=2*BUDGET['particle_atol']
    assert_owned(device,new)


def test_dynamic_transient_and_empty_path_reconstruct_trap_endpoints():
    model,old=trap_case();device=DeviceThreeTemperature(model,old)
    empty=audit_three_temperature_trajectory(model,old,[],final_state=old,**BUDGET)
    assert empty['valid'] and empty['energy_increments_J']['traps']==0
    result=device.run_transient([0.,1e-15,3e-15],**dict(OPTIONS,initial_step_s=1e-15,maximum_step_s=1e-15))
    assert result['trajectory_energy_audit']['valid'];assert_owned(device,result['final_state'])
    assert result['final_state'].trap_fraction[0]!=old.trap_fraction[0]
