"""Native implicit direct-gap radiation, photon ports and atomic transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from test_three_temperature import case,BUDGET
from test_adaptive_three_temperature import OPTIONS
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.physics.spectral_radiative import SpectralRadiativeState
from tcad.postprocess.spectral_radiative import reference_radiative_source
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory

Q=1.602176634e-19
LAW='matched_direct_gap_FD_Planck'
FIELDS=('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K')


def radiative_case(*,count=1,contacts=False,voltage=0.,nonuniform=False,traps=False,
                   source=False,absorption=False,rate=2e11,law=LAW,orchestration='native',valleys=None):
    base,old=case(count=count,contacts=contacts,voltage=voltage,nonuniform=nonuniform,uniform=not contacts)
    vn,vp=valleys or ((ThermionicValley('direct_n',1,.067,.067,.067),),
                      (ThermionicValley('direct_p',1,.45,.45,.45),))
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=base.Ec+.6*Q,Eh_J=base.Eh+.5*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=vn,valleys_p=vp,thermionic_faces=base.thermionic_faces,particle_contacts=base.contacts,
        heat_bath_K=base.bath,terminal_groups=base.groups,
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        trap_density_m3=3e23 if traps else 0.,trap_energy_J=.04*Q,
        capture_n_m3_s=3e-14 if traps else 0.,capture_p_m3_s=8e-15 if traps else 0.,
        trap_capture_law='energy_resolved_local_detailed_balance' if traps else None,
        intercarrier_conductance_W_m3_K=1e15 if source else 0.,
        pair_generation_rate_m3_s=1e34 if source else 0.,pair_generation_kinetic_n_J=.025*Q,
        pair_generation_kinetic_p_J=.018*Q,radiative_law=law,radiative_transition_rate_s=rate,
        photon_bath_temperature_K=3000. if absorption else 300.,residual_orchestration=orchestration)
    if absorption:old=replace(old,n_m3=np.full(count,1e21),p_m3=np.full(count,1e21))
    if traps:old=replace(old,trap_fraction=np.full(count,.37))
    model.rhofix=Q*(old.n_m3-old.p_m3+model.Nt*old.trap_fraction)
    return model,old


@pytest.mark.parametrize('options',[{},dict(traps=True),dict(absorption=True,rate=1e10),
 dict(count=2,contacts=True,voltage=.002,nonuniform=True,source=True,traps=True)])
def test_actual_implicit_device_step_and_photon_balance(options):
    model,old=radiative_case(**options);new,r=model.step(old,1e-14,**BUDGET)
    assert r['independent_audit']['valid'] and r['radiative_device_coupled']
    assert r['independent_audit']['max_radiative_moment_scaled_error']<3e-10
    assert r['outward_energy_J']['photons']==pytest.approx(sum(r['cell_radiative_photon_energy_J']),rel=2e-15)
    assert not r['complete_device_energy'] and not r['physical_validated']
    assert np.min(r['cell_radiative_entropy_production_J_K'])>=0
    if options.get('absorption'):
        assert np.sum(r['cell_radiative_recombined_pairs'])<0 and r['outward_energy_J']['photons']<0
        assert new.n_m3[0]>old.n_m3[0]
    elif not options.get('contacts'):
        assert np.sum(r['cell_radiative_recombined_pairs'])>0 and new.n_m3[0]<old.n_m3[0]


def test_closed_backward_euler_matches_independent_FD_radiative_root():
    model,old=radiative_case();dt=1e-14;new,r=model.step(old,dt,**BUDGET)
    def reservoir(n,T,s):return reference_reservoir(n,T,(model.Ec if s=='electrons' else model.Eh)[0],model.valleys[s])
    n0=float(old.n_m3[0]);p0=float(old.p_m3[0]);un0=reservoir(n0,360,'electrons')['energy_density_J_m3'];up0=reservoir(p0,260,'holes')['energy_density_J_m3']
    def residual(x):
        n,p=np.array([n0,p0])*np.exp(x[:2]);Tn,Tp,Tl=np.array([360.,260.,300.])*np.exp(x[2:])
        rn=reservoir(n,Tn,'electrons');rp=reservoir(p,Tp,'holes')
        ref=reference_radiative_source(SpectralRadiativeState(Tn,Tp,300.,rn['chemical_potential_J'],rp['chemical_potential_J'],
            model.Ec[0],model.Eh[0],.067,.45,1,2e11))
        pairs=dt*ref['net_recombination_rate_m3_s']
        qn=dt*(rn['energy_density_J_m3']-reservoir(n,Tl,'electrons')['energy_density_J_m3'])/model.tau_n[0]
        qp=dt*(rp['energy_density_J_m3']-reservoir(p,Tl,'holes')['energy_density_J_m3'])/model.tau_p[0]
        return [(n-n0+pairs)/n0,(p-p0+pairs)/p0,
            (rn['energy_density_J_m3']-un0+qn-dt*ref['electron_energy_source_W_m3'])/un0,
            (rp['energy_density_J_m3']-up0+qp-dt*ref['hole_energy_source_W_m3'])/up0,
            (model.capacity[0]*(Tl-300)-qn-qp)/(model.capacity[0]*300)]
    solved=root(residual,np.zeros(5),tol=1e-10)
    assert solved.success and max(abs(np.asarray(residual(solved.x))))<1e-12
    np.testing.assert_allclose([new.n_m3[0],new.p_m3[0]],np.array([n0,p0])*np.exp(solved.x[:2]),rtol=1e-10)
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
        np.array([360.,260.,300.])*np.exp(solved.x[2:]),rtol=0,atol=3e-6)


@pytest.mark.parametrize('failure',['newton','audit','decode'])
def test_native_transaction_failure_rolls_back_and_retry_matches_fresh(monkeypatch,failure):
    model,old=radiative_case(traps=True);device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',lambda *a,**k:dict(valid=False))
        if failure=='decode':
            def reject(*a,**k):raise ValueError('injected radiative decode')
            patch.setattr('tcad.solver.device_three_temperature.decode_three_temperature_output',reject)
        with pytest.raises((ValueError,RuntimeError)):device.advance(1e-14,**BUDGET,max_nfev=1 if failure=='newton' else 600)
    assert device.native_state()==saved
    actual,_=device.advance(1e-14,**BUDGET);expected,_=DeviceThreeTemperature(model,old).advance(1e-14,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(actual,f),getattr(expected,f))


@pytest.mark.parametrize('damage',['pairs','removed','photons','port','entropy','moment','scope','coverage','bath'])
def test_independent_audit_rejects_corrupted_radiative_deposit(damage):
    model,old=radiative_case();new,r=model.step(old,1e-14,**BUDGET);bad=deepcopy(r)
    if damage=='pairs':bad['cell_radiative_recombined_pairs'][0]+=1e-4
    elif damage=='removed':bad['cell_radiative_carrier_energy_removed_J']['electrons'][0]+=1e-20
    elif damage=='photons':bad['cell_radiative_photon_energy_J'][0]+=1e-20
    elif damage=='port':bad['outward_energy_J']['photons']+=1e-20
    elif damage=='entropy':bad['cell_radiative_entropy_production_J_K'][0]+=1e-20
    elif damage=='moment':bad['cell_radiative_moments'][0]['net_recombination_rate_m3_s']*=1.01
    elif damage=='scope':bad['radiative_device_coupled']=False
    elif damage=='bath':bad['photon_bath_law']='unknown'
    else:bad['cell_radiative_moments']=[]
    try:a=audit_three_temperature_energy(model,old,new,bad,**BUDGET)
    except ValueError:return
    assert not a['valid']


def test_reaudit_never_calls_production_sources_or_model_physics(monkeypatch):
    model,old=radiative_case(traps=True);new,r=model.step(old,1e-14,**BUDGET)
    def reject(*a,**k):raise AssertionError('production physics invoked')
    for f in ('_poisson','energies','carrier_reservoirs','split_face_transport'):monkeypatch.setattr(model,f,reject)
    monkeypatch.setattr('tcad.core._bindings.native_spectral_radiative_raw',reject)
    monkeypatch.setattr('tcad.core._bindings.native_three_temperature_dispatch_raw',reject)
    monkeypatch.setattr('tcad.core._bindings.native_spectral_trap_capture_raw',reject)
    assert audit_three_temperature_energy(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['law','no_opt_in','python','anisotropic','unequal_g','fractional_g','offset','multivalley','gap'])
def test_reject_incompatible_device_configuration(damage):
    options={}
    if damage=='law':options['law']='Bnp'
    elif damage=='no_opt_in':options['law']=None
    elif damage=='python':options['orchestration']='python'
    elif damage=='gap':
        model,old=radiative_case();model.Eh=-model.Ec.copy()
        with pytest.raises(ValueError):model._validate_state(old)
        return
    else:
        n=ThermionicValley('n',1,.067,.067,.067);p=ThermionicValley('p',1,.45,.45,.45)
        if damage=='anisotropic':n=replace(n,mass_tangent_1=.1,mass_tangent_2=.067*.067/.1)
        elif damage=='unequal_g':p=replace(p,degeneracy=2)
        elif damage=='fractional_g':n=replace(n,degeneracy=1.5)
        elif damage=='offset':n=replace(n,band_offset_owner_J=.1*Q,band_offset_neighbor_J=.1*Q)
        options['valleys']=((n,n) if damage=='multivalley' else (n,),(p,))
    with pytest.raises(ValueError):radiative_case(**options)


@pytest.mark.parametrize('traps',[False,True])
@pytest.mark.parametrize('damage',['width','temperature','coefficient','nonfinite','mass','degeneracy','offset','gap'])
def test_raw_schema_rejects_incompatible_inputs(traps,damage):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=radiative_case(traps=traps);c,f,vn,vp,p=pack_three_temperature_inputs(model,old,1e-14,**BUDGET)
    if damage=='width':p=p[:-1]
    elif damage=='temperature':p[-2]=0
    elif damage=='coefficient':p[-1]=-1
    elif damage=='nonfinite':p[-1]=np.nan
    elif damage=='mass':vn[1]*=2
    elif damage=='degeneracy':vp[2]=2
    elif damage=='offset':vn[3]=.1*Q
    else:c[14]=str(-2*Q)
    with pytest.raises((ValueError,RuntimeError)):native_three_temperature_dispatch_raw(c,f,vn,vp,p,600)


def test_zero_radiative_coefficient_matches_existing_device():
    model,old=radiative_case(rate=0.);base,_=radiative_case(rate=0.,law=None)
    a,r=model.step(old,1e-14,**BUDGET);b,_=base.step(old,1e-14,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(a,f),getattr(b,f))
    assert np.all(r['cell_radiative_recombined_pairs']==0) and r['outward_energy_J']['photons']==0


def test_adaptive_transient_reconstructs_photons_and_particle_balance():
    model,old=radiative_case();device=DeviceThreeTemperature(model,old)
    result=device.run_transient([0.,1e-15,2e-15],**dict(OPTIONS,initial_step_s=1e-15,maximum_step_s=1e-15))
    ledger=result['trajectory_energy_audit'];assert ledger['valid']
    assert ledger['radiative_photon_energy_J']>0 and ledger['radiative_recombined_pairs']>0
    assert max(abs(v) for v in ledger['particle_balance_residuals'].values())<ledger['cumulative_particle_atol']
    assert ledger==audit_three_temperature_trajectory(model,old,result['interval_reports'],final_state=device.state,**BUDGET)
    empty=audit_three_temperature_trajectory(model,old,[],final_state=old,**BUDGET)
    assert empty['valid'] and empty['radiative_photon_energy_J']==0


def test_device_material_reference_covariance():
    model,old=radiative_case();shifted,_=radiative_case();delta=-2*Q
    shifted.Ec=shifted.Ec+delta;shifted.Eh=shifted.Eh-delta
    a,ra=model.step(old,1e-14,**BUDGET);b,rb=shifted.step(old,1e-14,**BUDGET)
    for f in ('n_m3','p_m3'):np.testing.assert_allclose(getattr(a,f),getattr(b,f),rtol=1e-10)
    for f in ('temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_allclose(getattr(a,f),getattr(b,f),rtol=0,atol=3e-6)
    assert ra['outward_energy_J']['photons']==pytest.approx(rb['outward_energy_J']['photons'],rel=1e-8)


def test_failed_whole_path_cumulative_gate_preserves_accepted_device():
    from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
    model,old=radiative_case();device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with pytest.raises(ThreeTemperatureTransientError):
        device.run_transient([0.,1e-15],**dict(OPTIONS,initial_step_s=1e-15,maximum_step_s=1e-15,
            cumulative_energy_atol_J=1e-38))
    assert device.native_state()==saved and device.state.time_s==old.time_s
