"""Actual native affine-band dynamics, independent balances and transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from test_three_temperature import case,BUDGET
from test_auger_device import auger_case,FIELDS
from test_adaptive_three_temperature import OPTIONS
from tcad.solver.cut_cell_transport import Q,_immutable_state_array
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.fermi_spectral_energy import reference_reservoir


def band_case(*,complex=False,contacts=False,sign=-1.,count=1):
    if complex:
        model,old=auger_case(count=count,contacts=contacts,voltage=.002 if contacts else 0.,
            nonuniform=count==2,source=True,traps=True,radiation=True)
        # Frozen model coefficients are explicit prescribed numerical controls.
        model.band_temperature_slopes=tuple(_immutable_state_array(np.full(count,v*Q),float)
            for v in (sign*1e-5,sign*2e-5))
        return model,old
    base,old=case(count=count,contacts=contacts,voltage=.002 if contacts else 0.,uniform=not contacts)
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=base.Ec+.06*Q,Eh_J=base.Eh+.04*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=base.valleys['electrons'],valleys_p=base.valleys['holes'],
        thermionic_faces=tuple(map(int,base.internal)),particle_contacts=base.contacts,heat_bath_K=base.bath,
        terminal_groups=base.groups,relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        band_temperature_slope_n_J_K=sign*1e-5*Q,band_temperature_slope_p_J_K=sign*2e-5*Q)
    return model,old


@pytest.mark.parametrize('sign',[-1.,1.])
def test_closed_native_solution_matches_independent_three_reservoir_root(sign):
    model,old=band_case(sign=sign);dt=2e-13;new,r=model.step(old,dt,**BUDGET)
    n=float(old.n_m3[0]);p=float(old.p_m3[0])
    def U(T,Tl,s):
        edge=(.06 if s=='electrons' else .04)*Q+sign*(1e-5 if s=='electrons' else 2e-5)*Q*(Tl-300)
        return reference_reservoir(n if s=='electrons' else p,T,edge,model.valleys[s])['energy_density_J_m3']
    initial=[U(360.,300.,'electrons'),U(260.,300.,'holes')]
    def residual(T):
        Tn,Tp,Tl=T
        qn=dt*(U(Tn,Tl,'electrons')-U(Tl,Tl,'electrons'))/1e-13
        qp=dt*(U(Tp,Tl,'holes')-U(Tl,Tl,'holes'))/4e-13
        wn=n*sign*1e-5*Q*(Tl-300);wp=p*sign*2e-5*Q*(Tl-300)
        return [U(Tn,Tl,'electrons')-initial[0]+qn-wn,
                U(Tp,Tl,'holes')-initial[1]+qp-wp,1000*(Tl-300)-qn-qp+wn+wp]
    solved=root(residual,[330.,280.,300.],tol=1e-10)
    assert solved.success
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
        solved.x,atol=2e-6,rtol=0)
    assert abs(r['cell_band_work_from_lattice_J']['electrons'][0])>1e-25
    assert r['independent_audit']['valid'] and abs(r['energy_residual_J'])<=1e-27
    assert not r['complete_device_energy'] and not r['temperature_dependent_band_entropy_closed']


@pytest.mark.parametrize('complex,contacts,count',[(False,True,1),(False,True,2),(True,False,1),(True,True,2)])
def test_owned_device_two_steps_with_contacts_and_all_existing_sources(complex,contacts,count):
    model,old=band_case(complex=complex,contacts=contacts,count=count)
    device=DeviceThreeTemperature(model,old)
    for _ in range(2):
        before=device.state;new,r=device.advance(1e-15 if complex else 2e-13,**BUDGET)
        assert audit_three_temperature_energy(model,before,new,r,**BUDGET)['valid']
        assert sum(abs(v).sum() for v in r['cell_band_work_from_lattice_J'].values())>0
        if complex:
            assert r['dynamic_trap_device_coupled'] and r['radiative_device_coupled'] and r['auger_device_coupled']
            assert abs(sum(r['cell_generated_pairs']))>0
        device._check_owned_state()


def test_band_audit_uses_no_production_physics_or_band_evaluator(monkeypatch):
    model,old=band_case(complex=True,contacts=True,count=2);new,r=model.step(old,1e-15,**BUDGET)
    # Validation may check the configured law; only numerical references below
    # must remain independent of every production primitive.
    monkeypatch.setattr(model,'band_edges',lambda T:(np.ones(model.nc),np.ones(model.nc)))
    for name in ('_poisson','carrier_reservoirs','split_face_transport','conduction','energies'):
        monkeypatch.setattr(model,name,lambda *a,**k:(_ for _ in ()).throw(AssertionError('production physics')))
    assert audit_three_temperature_energy(model,old,new,r,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['sign','missing','coverage','law','entropy_claim','storage'])
def test_independent_audit_rejects_damaged_band_work(damage):
    model,old=band_case();new,r=model.step(old,2e-13,**BUDGET);bad=deepcopy(r)
    if damage=='sign':bad['cell_band_work_from_lattice_J']['electrons']*=-1
    if damage=='missing':del bad['cell_band_work_from_lattice_J']
    if damage=='coverage':del bad['cell_band_work_from_lattice_J']['holes']
    if damage=='law':bad['band_work_law']='fully_implicit_density'
    if damage=='entropy_claim':bad['temperature_dependent_band_entropy_closed']=True
    if damage=='storage':bad['energy_increments_J']['electrons']+=1e-20
    try:result=audit_three_temperature_energy(model,old,new,bad,**BUDGET)
    except ValueError:return
    assert not result['valid']


def test_failed_owned_step_is_atomic_and_retry_matches_fresh():
    model,old=band_case();device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with pytest.raises(RuntimeError):device.advance(2e-13,**BUDGET,max_nfev=1)
    assert device.native_state()==saved and device.state.time_s==0
    a,_=device.advance(2e-13,**BUDGET);b,_=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    for field in FIELDS:np.testing.assert_array_equal(getattr(a,field),getattr(b,field))


def test_adaptive_trajectory_closes_endpoint_storage_and_band_channels():
    model,old=band_case(complex=True);device=DeviceThreeTemperature(model,old)
    result=device.run_transient([0.,1e-15,2e-15],initial_step_s=1e-15,maximum_step_s=1e-15,
        minimum_step_s=1e-20,temperature_atol_K=.1,temperature_rtol=.02,density_atol_m3=1e10,
        density_rtol=.02,**BUDGET)
    assert result['trajectory_energy_audit']['valid']


@pytest.mark.parametrize('bad',[np.nan,True,1j,[1.,2.]])
def test_invalid_band_coefficients_rejected(bad):
    model,old=band_case();model.band_temperature_slopes=(bad,model.band_temperature_slopes[1])
    with pytest.raises((ValueError,TypeError)):model.step(old,2e-13,**BUDGET)


def test_missing_lattice_coordinate_negative_gap_and_negative_capacity_rejected():
    model,old=band_case()
    with pytest.raises(ValueError,match='lattice'):model.carrier_reservoirs(old.n_m3,old.p_m3,old.electron_temperature_K,old.hole_temperature_K)
    with pytest.raises(ValueError,match='gap'):model.band_edges([1e5])
    model.band_temperature_slopes=(np.array([-1e-20]),np.array([-1e-20]))
    with pytest.raises(ValueError,match='capacity'):model.step(old,2e-13,**BUDGET)


@pytest.mark.parametrize('damage',['count','reference','slope','inner_count','truncated'])
def test_malformed_native_band_wrapper_rejected(damage):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=band_case();args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET));p=args[-1]
    if damage=='count':p[8]=.5
    if damage=='reference':p[9]=0
    if damage=='slope':p[-1]=float('nan')
    if damage=='inner_count':p[8]=1e300
    if damage=='truncated':p.pop()
    with pytest.raises(ValueError):native_three_temperature_dispatch_raw(*args,600)
