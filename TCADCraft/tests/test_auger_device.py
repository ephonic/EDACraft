"""Native implicit direct-gap radiation, photon ports and atomic transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from test_three_temperature import case,BUDGET
from test_adaptive_three_temperature import OPTIONS
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.physics.spectral_auger import AugerEvent,SpectralAugerState,LAW as AUGER_LAW
from tcad.postprocess.spectral_auger import reference_auger_source
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory

Q=1.602176634e-19
LAW='matched_direct_gap_FD_Planck'
FIELDS=('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K')


def auger_case(*,count=1,contacts=False,voltage=0.,nonuniform=False,traps=False,
                   source=False,absorption=False,rate=2e11,law=LAW,orchestration='native',valleys=None,
                   radiation=False,events='default',channel='mixed',weight=2e37,impact=False):
    if events=='default':events=tuple((AugerEvent('eeh',((.9,0,0),(1,0,0),(0,0,0)),weight),
        AugerEvent('hhe',((0,.9,0),(0,1,0),(0,0,0)),.3*weight)) if channel=='mixed' else
        (AugerEvent(channel,((.9,0,0),(1,0,0),(0,0,0)),weight),) for _ in range(count))
    base,old=case(count=count,contacts=contacts,voltage=voltage,nonuniform=nonuniform,uniform=not contacts)
    vn,vp=valleys or ((ThermionicValley('direct_n',1,.067,.067,.067),),
                      (ThermionicValley('direct_p',1,.45,.45,.45),))
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=base.Ec+.06*Q,Eh_J=base.Eh+.04*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=vn,valleys_p=vp,thermionic_faces=base.thermionic_faces,particle_contacts=base.contacts,
        heat_bath_K=base.bath,terminal_groups=base.groups,
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        trap_density_m3=3e23 if traps else 0.,trap_energy_J=.04*Q,
        capture_n_m3_s=3e-14 if traps else 0.,capture_p_m3_s=8e-15 if traps else 0.,
        trap_capture_law='energy_resolved_local_detailed_balance' if traps else None,
        intercarrier_conductance_W_m3_K=1e15 if source else 0.,
        pair_generation_rate_m3_s=1e34 if source else 0.,pair_generation_kinetic_n_J=.025*Q,
        pair_generation_kinetic_p_J=.018*Q,radiative_law=law if radiation else None,radiative_transition_rate_s=rate if radiation else 0.,
        auger_events=events,
        photon_bath_temperature_K=3000. if absorption else 300.,residual_orchestration=orchestration)
    if absorption:old=replace(old,n_m3=np.full(count,1e21),p_m3=np.full(count,1e21))
    if impact:old=replace(old,n_m3=np.full(count,1e21),p_m3=np.full(count,1e21),
        electron_temperature_K=np.full(count,2500.),hole_temperature_K=np.full(count,2500.))
    if traps:old=replace(old,trap_fraction=np.full(count,.37))
    model.rhofix=Q*(old.n_m3-old.p_m3+model.Nt*old.trap_fraction)
    return model,old




@pytest.mark.parametrize('options',[{},dict(channel='eeh'),dict(channel='hhe'),dict(impact=True),
 dict(traps=True),dict(radiation=True),dict(count=2,contacts=True,voltage=.002,nonuniform=True,source=True,traps=True,radiation=True)])
def test_implicit_collision_step_closes_both_carrier_rows(options):
    model,old=auger_case(**options);new,r=model.step(old,1e-14,**BUDGET)
    assert r['auger_device_coupled'] and r['independent_audit']['valid']
    assert r['independent_audit']['max_auger_moment_scaled_error']<3e-10
    assert set(r['outward_energy_J'])=={'electrons','holes','lattice'}|({'photons'} if options.get('radiation') else set())
    assert np.all(r['cell_auger_carrier_energy_added_J']['electrons']==-r['cell_auger_carrier_energy_added_J']['holes'])
    assert np.min(r['cell_auger_entropy_production_J_K'])>=0
    assert not r['auger_material_calibrated'] and not r['auger_continuum_kernel_integrated'] and not r['complete_device_energy']
    if not options.get('contacts'):
        sign=-1 if options.get('impact') else 1
        assert sign*sum(r['cell_auger_recombined_pairs'])>0
        assert sign*(old.n_m3[0]-new.n_m3[0])>0
    if options.get('channel')=='hhe':assert r['cell_auger_carrier_energy_added_J']['holes'][0]>0
    if options.get('channel')=='eeh':assert r['cell_auger_carrier_energy_added_J']['electrons'][0]>0


def test_closed_backward_euler_matches_independent_Decimal_collision_root():
    model,old=auger_case();dt=1e-14;new,r=model.step(old,dt,**BUDGET)
    def reservoir(n,T,s):return reference_reservoir(n,T,(model.Ec if s=='electrons' else model.Eh)[0],model.valleys[s])
    n0=float(old.n_m3[0]);p0=float(old.p_m3[0]);un0=reservoir(n0,360,'electrons')['energy_density_J_m3'];up0=reservoir(p0,260,'holes')['energy_density_J_m3']
    def residual(x):
        n,p=np.array([n0,p0])*np.exp(x[:2]);Tn,Tp,Tl=np.array([360.,260.,300.])*np.exp(x[2:])
        rn=reservoir(n,Tn,'electrons');rp=reservoir(p,Tp,'holes')
        ref=reference_auger_source(SpectralAugerState(Tn,Tp,rn['chemical_potential_J'],rp['chemical_potential_J'],
            model.Ec[0],model.Eh[0],.067,.45),model.auger_events[0])
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
def test_device_failure_rolls_back_then_retries_exactly(monkeypatch,failure):
    model,old=auger_case(traps=True,radiation=True);device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',lambda *a,**k:dict(valid=False))
        if failure=='decode':
            def reject(*a,**k):raise ValueError('injected Auger decode')
            patch.setattr('tcad.solver.device_three_temperature.decode_three_temperature_output',reject)
        with pytest.raises((ValueError,RuntimeError)):device.advance(1e-14,**BUDGET,max_nfev=1 if failure=='newton' else 600)
    assert device.native_state()==saved
    a,_=device.advance(1e-14,**BUDGET);b,_=DeviceThreeTemperature(model,old).advance(1e-14,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(a,f),getattr(b,f))


@pytest.mark.parametrize('damage',['pairs','energy','entropy','moment','event','coupled','material','continuum','coverage','port','extra_channel'])
def test_independent_audit_rejects_corrupted_collision_accounting(damage):
    model,old=auger_case();new,r=model.step(old,1e-14,**BUDGET);bad=deepcopy(r)
    if damage=='pairs':bad['cell_auger_recombined_pairs'][0]+=1e-4
    elif damage=='energy':
        bad['cell_auger_carrier_energy_added_J']['electrons'][0]+=1e-20
        bad['cell_auger_carrier_energy_added_J']['holes'][0]-=1e-20
    elif damage=='entropy':bad['cell_auger_entropy_production_J_K'][0]+=1e-20
    elif damage=='moment':bad['cell_auger_moments'][0]['net_recombination_rate_m3_s']*=1.01
    elif damage=='event':bad['cell_auger_moments'][0]['event_moments'][0]['kinetic_4_J']*=1.01
    elif damage=='coupled':bad['auger_device_coupled']=False
    elif damage=='material':bad['auger_material_calibrated']=True
    elif damage=='continuum':bad['auger_continuum_kernel_integrated']=True
    elif damage=='coverage':bad['cell_auger_moments']=[]
    elif damage=='port':bad['outward_energy_J']['auger']=0.
    else:bad['cell_auger_carrier_energy_added_J']['lattice']=np.zeros(1)
    try:a=audit_three_temperature_energy(model,old,new,bad,**BUDGET)
    except ValueError:return
    assert not a['valid']


def test_reaudit_calls_no_native_sources_dispatch_or_model_physics(monkeypatch):
    model,old=auger_case(traps=True,radiation=True);new,r=model.step(old,1e-14,**BUDGET)
    def reject(*a,**k):raise AssertionError('production physics invoked')
    for f in ('_poisson','energies','carrier_reservoirs','split_face_transport'):monkeypatch.setattr(model,f,reject)
    for f in ('native_spectral_auger_raw','native_spectral_radiative_raw','native_three_temperature_dispatch_raw','native_spectral_trap_capture_raw'):
        monkeypatch.setattr('tcad.core._bindings.'+f,reject)
    assert audit_three_temperature_energy(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['empty','coverage','flat','callback','duplicate','forbidden','python','anisotropic','multivalley','offset','gap','weight_range'])
def test_public_configuration_rejects_unsupported_collision_tables(damage):
    options={}
    event=AugerEvent('eeh',((1,0,0),(3,0,0),(0,0,0)),1e37)
    if damage=='empty':options['events']=((),)
    elif damage=='coverage':options['events']=((event,),(event,))
    elif damage=='flat':options['events']=(event,)
    elif damage=='callback':options['events']=((lambda:None,),)
    elif damage=='duplicate':options['events']=((event,event),)
    elif damage=='forbidden':options['events']=((AugerEvent('eeh',((1,0,0),(-1,0,0),(0,0,0)),1e37),),)
    elif damage=='weight_range':options['events']=((replace(event,weight_m3_s=np.longdouble('1e400')),),)
    elif damage=='python':options['orchestration']='python'
    elif damage=='gap':
        model,old=auger_case();model.Eh=-model.Ec.copy()
        with pytest.raises(ValueError):model._validate_state(old)
        return
    else:
        n=ThermionicValley('n',1,.067,.067,.067);p=ThermionicValley('p',1,.45,.45,.45)
        if damage=='anisotropic':n=replace(n,mass_tangent_1=.1,mass_tangent_2=.067*.067/.1)
        elif damage=='offset':n=replace(n,band_offset_owner_J=.01*Q,band_offset_neighbor_J=.01*Q)
        options['valleys']=((n,n) if damage=='multivalley' else (n,),(p,))
    with pytest.raises(ValueError):auger_case(**options)


@pytest.mark.parametrize('traps,radiation',[(False,False),(True,False),(False,True),(True,True)])
@pytest.mark.parametrize('damage',['width','count','channel','weight','nonfinite','duplicate','forbidden','mass','gap','coefficient'])
def test_raw_native_schema_rejects_malformed_event_tables(traps,radiation,damage):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=auger_case(traps=traps,radiation=radiation);c,f,vn,vp,p=pack_three_temperature_inputs(model,old,1e-14,**BUDGET)
    if damage=='width':p=p[:-1]
    elif damage=='count':p[27]=1.5
    elif damage=='channel':p[28]=2
    elif damage=='weight':p[29]=-1
    elif damage=='nonfinite':p[-1]=np.nan
    elif damage=='duplicate':p[39:50]=p[28:39]
    elif damage=='forbidden':p[30:39]=[1,0,0,-1,0,0,0,0,0]
    elif damage=='mass':vn[1]*=2
    elif damage=='gap':c[14]=str(-2*Q)
    else:p[18]=-1
    with pytest.raises((ValueError,RuntimeError)):native_three_temperature_dispatch_raw(c,f,vn,vp,p,600)


def test_zero_weight_exactly_matches_device_without_collisions():
    model,old=auger_case(weight=0.,traps=True,radiation=True);base,_=auger_case(events=None,traps=True,radiation=True)
    a,r=model.step(old,1e-14,**BUDGET);b,_=base.step(old,1e-14,**BUDGET)
    for f in FIELDS:np.testing.assert_array_equal(getattr(a,f),getattr(b,f))
    assert np.all(r['cell_auger_recombined_pairs']==0)


def test_adaptive_accepted_path_particle_energy_ledgers_and_empty_path():
    model,old=auger_case();device=DeviceThreeTemperature(model,old)
    result=device.run_transient([0.,1e-15,2e-15],**dict(OPTIONS,initial_step_s=1e-15,maximum_step_s=1e-15))
    ledger=result['trajectory_energy_audit'];assert ledger['valid'] and ledger['auger_device_coupled']
    assert ledger['auger_recombined_pairs']>0 and ledger['auger_carrier_energy_added_J']['electrons']>0
    assert ledger['reservoir_energy_residuals_J']['auger_internal']==0
    assert max(abs(v) for v in ledger['particle_balance_residuals'].values())<ledger['cumulative_particle_atol']
    assert ledger==audit_three_temperature_trajectory(model,old,result['interval_reports'],final_state=device.state,**BUDGET)
    empty=audit_three_temperature_trajectory(model,old,[],final_state=old,**BUDGET)
    assert empty['valid'] and empty['auger_recombined_pairs']==0


def test_whole_path_gate_failure_rolls_back_device():
    from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
    model,old=auger_case();device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with pytest.raises(ThreeTemperatureTransientError):
        device.run_transient([0.,1e-15],**dict(OPTIONS,initial_step_s=1e-15,maximum_step_s=1e-15,cumulative_energy_atol_J=1e-38))
    assert device.native_state()==saved and device.state.time_s==old.time_s
