"""Independent FD injection roots, particle/energy ports and owned transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.transient_three_temperature import ThreeTemperatureTransientError
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs,decode_three_temperature_output
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.core._bindings import native_three_temperature_dispatch_raw
from test_three_temperature import case,BUDGET
from test_adaptive_three_temperature import closed,OPTIONS
from test_device_three_temperature import assert_owned
from test_structured_three_temperature import structured_case

Q=1.602176634e-19;KB=1.380649e-23


def generated_case(rate=1e36,kn=1.5*KB*900,kp=1.5*KB*600,**kwargs):
    base,old=case(**kwargs)
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=base.Ec+.6*Q,Eh_J=base.Eh+.5*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=base.valleys['electrons'],valleys_p=base.valleys['holes'],
        thermionic_faces=base.thermionic_faces,particle_contacts=base.contacts,
        heat_bath_K=base.bath,terminal_groups=base.groups,
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        pair_generation_rate_m3_s=rate,pair_generation_kinetic_n_J=kn,pair_generation_kinetic_p_J=kp)
    return model,old


@pytest.mark.parametrize('scale',[1e-5,1.,10.])
def test_closed_generation_matches_independent_density_and_FD_energy_root(scale):
    rate=1e37*scale;dt=2e-13
    model,old=generated_case(rate=rate,count=1,uniform=True,density_scale=scale)
    new,report=model.step(old,dt,**BUDGET)
    density=old.n_m3[0]+np.longdouble(dt)*np.longdouble(rate)
    assert abs(new.n_m3[0]-density)*model.vol[0]<=BUDGET['particle_atol']
    np.testing.assert_array_equal(new.n_m3,new.p_m3)
    def u(n,t,s):return reference_reservoir(n,t,(model.Ec if s=='electrons' else model.Eh)[0],model.valleys[s])['energy_density_J_m3']
    un0=u(old.n_m3[0],old.electron_temperature_K[0],'electrons')
    up0=u(old.p_m3[0],old.hole_temperature_K[0],'holes')
    en=.6*Q+1.5*KB*900;ep=.5*Q+1.5*KB*600
    def rows(t):
        un,up=u(density,t[0],'electrons'),u(density,t[1],'holes')
        xn=dt*(un-u(density,t[2],'electrons'))/model.tau_n[0]
        xp=dt*(up-u(density,t[2],'holes'))/model.tau_p[0]
        return np.array([un-un0+xn-dt*rate*en,up-up0+xp-dt*rate*ep,
                         model.capacity[0]*(t[2]-old.temperature_K[0])-xn-xp])/max(1.,float(un0+up0))
    solution=root(rows,[350.,300.,300.],tol=1e-10)
    assert solution.success and max(abs(rows(solution.x)))<1e-8
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
                               solution.x,rtol=0.,atol=3e-6)
    assert report['absorbed_pair_energy_J']>1e-27 and report['independent_audit']['valid']
    assert report['source_work_J']==0. # electrical work remains a separate port
    np.testing.assert_allclose(report['cell_generated_pairs'],[dt*model.vol[0]*rate],rtol=1e-15)


@pytest.mark.parametrize('kwargs',[dict(contacts=True,voltage=.002),
    dict(contacts=True,voltage=-.002,density_scale=10),dict(nonuniform=True)])
def test_spatial_generation_with_transport_contacts_and_state_dependent_exchange(kwargs):
    from test_state_relaxation import LAWS
    model,old=generated_case(rate=[0.,1e36],**kwargs)
    model.intercarrier_conductance_W_m3_K=np.array([0.,1e15]);model.relaxation_laws=LAWS
    device=DeviceThreeTemperature(model,old)
    for _ in range(2):
        new,report=device.advance(2e-13,**BUDGET)
        assert_owned(device,new)
        assert report['cell_generated_pairs'][0]==0. and report['cell_generated_pairs'][1]>0.
        assert report['cell_intercarrier_exchange_J'][1]!=0.
        assert audit_three_temperature_energy(device._model,old,new,report,**BUDGET)['valid']
        old=new


def test_reference_orchestration_uses_native_pair_assembly():
    model,old=generated_case(count=1,uniform=True)
    new,report=model.step(old,2e-13,**BUDGET);model.residual_orchestration='python'
    other,given=model.step(old,2e-13,**BUDGET)
    for f in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_allclose(getattr(new,f),getattr(other,f),rtol=1e-10,atol=1e-8)
    np.testing.assert_allclose(report['cell_pair_generation_energy_J']['electrons'],
                               given['cell_pair_generation_energy_J']['electrons'],rtol=1e-12)


@pytest.mark.parametrize('damage',['missing','pairs','energy_n','energy_p','absorbed','law','lattice','double_gap','rate'])
def test_independent_audit_rejects_missing_or_double_counted_external_source(damage):
    model,old=generated_case(count=1,uniform=True)
    new,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    if damage=='missing':bad.pop('cell_pair_generation_energy_J')
    elif damage=='pairs':bad['cell_generated_pairs']*=2
    elif damage=='energy_n':bad['cell_pair_generation_energy_J']['electrons']*=2
    elif damage=='energy_p':bad['cell_pair_generation_energy_J']['holes']*=2
    elif damage=='absorbed':bad['absorbed_pair_energy_J']=0.
    elif damage=='law':bad['pair_generation_law']='unverified_absorption'
    elif damage=='lattice':bad['cell_exchange_J']['electrons']+=bad['cell_pair_generation_energy_J']['electrons']
    elif damage=='double_gap':bad['cell_pair_generation_energy_J']['electrons']+=bad['cell_generated_pairs']*1.1*Q
    else:model.pair_generation_rate_m3_s=np.zeros(1)
    try:accepted=audit_three_temperature_energy(model,old,new,bad,**BUDGET)['valid']
    except (ValueError,KeyError):accepted=False
    assert not accepted


@pytest.mark.parametrize('field,bad',[('rate',-1.),('rate',np.nan),('rate',np.inf),('rate',True),
    ('rate',1j),('rate','1'),('rate',[]),('rate',[1.,2.,3.]),('kn',-1e-20),('kp',np.nan)])
def test_invalid_prescribed_source_rejected(field,bad):
    with pytest.raises(ValueError):generated_case(**{field:bad})


def test_source_constructor_detaches_and_freezes_all_arrays():
    rate=np.array([0.,1e36]);kn=np.array([0.,1e-20]);kp=np.array([0.,2e-20])
    model,_=generated_case(rate=rate,kn=kn,kp=kp);rate[:]=kn[:]=kp[:]=0.
    for field,want in (('pair_generation_rate_m3_s',[0.,1e36]),
        ('pair_generation_kinetic_n_J',[0.,1e-20]),('pair_generation_kinetic_p_J',[0.,2e-20])):
        np.testing.assert_array_equal(getattr(model,field),want)
        with pytest.raises(ValueError):getattr(model,field).flags.writeable=True


@pytest.mark.parametrize('damage',['rate','kinetic','nan','infinite','marker','short','extra','nonpositive_photon'])
def test_raw_generation_schema_rejected(damage):
    model,old=generated_case(count=1,uniform=True)
    args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET));params=list(args[-1])
    if damage=='rate':params[19]=-1.
    elif damage=='kinetic':params[20]=-1e-20
    elif damage=='nan':params[21]=np.nan
    elif damage=='infinite':params[20]=np.inf
    elif damage=='marker':params[17]=0.
    elif damage=='short':params.pop()
    elif damage=='extra':params.extend([0.]*4)
    else:
        cells=list(args[0]);cells[13]=cells[14]='-1';args[0]=cells
    args[-1]=params
    with pytest.raises(ValueError):native_three_temperature_dispatch_raw(*args,600)


def test_zero_rate_preserves_previous_schema_and_state():
    base,old=case(count=1,uniform=True)
    # Explicit energies with the source off must not introduce a generation schema.
    base.pair_generation_kinetic_n_J=np.array([1e-20])
    assert len(pack_three_temperature_inputs(base,old,2e-13,**BUDGET)[-1])==7
    a,ar=base.step(old,2e-13,**BUDGET);base.pair_generation_kinetic_n_J=np.zeros(1)
    b,br=base.step(old,2e-13,**BUDGET)
    for f in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(a,f),getattr(b,f))
    assert ar['independent_audit']==br['independent_audit']
    assert 'absorbed_pair_energy_J' not in br


def test_native_decoder_rejects_unexpected_tail_instead_of_treating_it_as_exchange():
    model,old=generated_case(count=1,uniform=True)
    raw=native_three_temperature_dispatch_raw(*pack_three_temperature_inputs(model,old,2e-13,**BUDGET),600)
    raw['local'].append(0.)
    with pytest.raises(ValueError,match='coverage'):decode_three_temperature_output(model,old,raw,dt_s=2e-13,**BUDGET)


def test_independent_audit_uses_no_production_physics(monkeypatch):
    model,old=generated_case(count=1,uniform=True);new,report=model.step(old,2e-13,**BUDGET)
    def forbidden(*a,**k):raise AssertionError('production operator used')
    for name in ('_poisson','carrier_reservoirs','split_face_transport','conduction','energies','relaxation_times'):
        monkeypatch.setattr(model,name,forbidden)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']


def test_trajectory_external_source_ledger_and_whole_run_rollback():
    model,old=closed();model.pair_generation_rate_m3_s=np.array([1e32])
    model.pair_generation_kinetic_n_J=np.array([1.5*KB*900]);model.pair_generation_kinetic_p_J=np.array([1.5*KB*600])
    device=DeviceThreeTemperature(model,old);before=deepcopy(device.native_state())
    run=dict(OPTIONS,initial_step_s=1e-14,maximum_step_s=1e-14)
    with pytest.raises(ThreeTemperatureTransientError):device.run_transient([0.,1e-14,2e-14],**dict(run,max_intervals=1))
    assert before==device.native_state() and device.state.time_s==0.
    result=device.run_transient([0.,1e-14,2e-14],**run);ledger=result['trajectory_energy_audit']
    assert ledger['valid'] and ledger['absorbed_pair_energy_J']>0. and ledger['source_work_J']==0.
    assert ledger==audit_three_temperature_trajectory(device._model,old,result['interval_reports'],
        final_state=device.state,**BUDGET)
    np.testing.assert_allclose(ledger['generated_pairs'],1e32*2e-14*model.vol[0],rtol=1e-15)
    assert_owned(device,device.state)


def test_simulator_public_entry_forwards_constant_pair_source():
    source,old,options=structured_case(shape=(2,1,1),uniform=True)
    before=deepcopy(source._sim.structured_three_temperature_seed())
    result=source.run_three_temperature(old,[old.time_s,old.time_s+1e-15],
        **options,**{k:v for k,v in OPTIONS.items() if k not in BUDGET},
        initial_step_s=1e-15,maximum_step_s=1e-15,pair_generation_rate_m3_s=1e34,
        pair_generation_kinetic_n_J=1e-20,pair_generation_kinetic_p_J=2e-20)
    assert np.all(result['device']._model.pair_generation_rate_m3_s==1e34)
    assert result['trajectory_energy_audit']['absorbed_pair_energy_J']>0.
    assert before==source._sim.structured_three_temperature_seed()
