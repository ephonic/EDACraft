"""Nonlinear band work in actual native five-field dynamics and transactions."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import root
from test_temperature_dependent_bands import band_case
from test_smooth_temperature_bands import smooth_case
from test_three_temperature import BUDGET
from tcad.solver.cut_cell_transport import Q,_immutable_state_array
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.fermi_spectral_energy import reference_reservoir

def configure(model,sign=1.,beta=636.):
    model.band_varshni_alpha=tuple(_immutable_state_array(np.full(model.nc,sign*v*Q),float) for v in (2.365e-4,1.5e-4))
    model.band_varshni_beta=tuple(_immutable_state_array(np.full(model.nc,beta),float) for _ in range(2))
    return model

@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('beta',[0.,636.])
def test_closed_native_solution_matches_independent_nonlinear_root(sign,beta):
    model,old=band_case();configure(model,sign,beta);dt=2e-13
    new,r=model.step(old,dt,**BUDGET)
    n=float(old.n_m3[0]);p=float(old.p_m3[0]);V=model.vol[0]
    def edge(i,t):
        return (model.Ec,model.Eh)[i][0]+model.band_temperature_slopes[i][0]*(t-300)-model.band_varshni_alpha[i][0]*(t*t/(t+beta)-300**2/(300+beta))
    def U(i,t,tl):
        return reference_reservoir((n,p)[i],t,edge(i,tl),model.valleys[('electrons','holes')[i]])['energy_density_J_m3']
    def residual(t):
        tn,tp,tl=t;qn=dt*(U(0,tn,tl)-U(0,tl,tl))/1e-13;qp=dt*(U(1,tp,tl)-U(1,tl,tl))/4e-13
        wn=n*(edge(0,tl)-edge(0,300));wp=p*(edge(1,tl)-edge(1,300))
        return [U(0,tn,tl)-U(0,360,300)+qn-wn,U(1,tp,tl)-U(1,260,300)+qp-wp,1000*(tl-300)-qn-qp+wn+wp]
    solved=root(residual,[330,280,300],tol=1e-10)
    assert solved.success
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],solved.x,rtol=0,atol=3e-6)
    assert r['independent_audit']['valid'] and r['band_temperature_law']=='affine_plus_Varshni_lattice_temperature'
    for i,s in enumerate(('electrons','holes')):
        np.testing.assert_allclose(r['cell_band_work_from_lattice_J'][s],V*(n,p)[i]*(edge(i,new.temperature_K[0])-edge(i,300)),rtol=2e-7,atol=1e-34)
    assert not r['complete_device_energy'] and not r['temperature_dependent_band_entropy_closed']

@pytest.mark.parametrize('complex,contacts,count',[(False,True,2),(True,False,1),(True,True,2)])
def test_owned_steps_with_all_existing_sources_and_independent_replay(complex,contacts,count,monkeypatch):
    model,old=band_case(complex=complex,contacts=contacts,count=count);configure(model)
    device=DeviceThreeTemperature(model,old);steps=[]
    for _ in range(2):
        before=device.state;new,r=device.advance(1e-15 if complex else 2e-13,**BUDGET);steps.append((before,new,r))
        assert r['independent_audit']['valid']
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('production primitive forbidden')
    for mod in (public,native):
        for name in dir(mod):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(mod,name)):monkeypatch.setattr(mod,name,deny)
    monkeypatch.setattr(model,'band_edges',lambda t:(np.ones(count),np.ones(count)))
    monkeypatch.setattr(model,'band_derivatives',lambda t:(np.zeros(count),np.zeros(count)))
    for before,new,r in steps:assert audit_three_temperature_energy(model,before,new,r,**BUDGET)==r['independent_audit']

def test_smooth_nonlinear_bulk_gradients_without_thermionic_faces():
    model,old=smooth_case();configure(model)
    assert not model.thermionic_faces
    new,r=model.step(old,2e-13,**BUDGET)
    assert r['independent_audit']['valid'] and np.ptp(model.band_edges(new.temperature_K)[0])>0

@pytest.mark.parametrize('field',['band_varshni_alpha','band_varshni_beta'])
def test_nonlinear_material_discontinuities_rejected_in_both_layers(field):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=smooth_case();configure(model)
    arrays=list(getattr(model,field));a=arrays[0].copy();a[1]*=2;arrays[0]=_immutable_state_array(a,float);setattr(model,field,tuple(arrays))
    with pytest.raises(ValueError,match='discontinuit'):model.step(old,2e-13,**BUDGET)
    with pytest.raises(ValueError,match='discontinuit'):native_three_temperature_dispatch_raw(*pack_three_temperature_inputs(model,old,2e-13,**BUDGET),600)

@pytest.mark.parametrize('damage',['beta','alpha','truncated','count'])
def test_malformed_nonlinear_native_schema(damage):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=band_case();configure(model);args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET));p=args[-1]
    assert p[7]==-11
    if damage=='beta':p[-1]=-1
    if damage=='alpha':p[-3]=np.nan
    if damage=='truncated':p.pop()
    if damage=='count':p[8]=1e300
    with pytest.raises(ValueError):native_three_temperature_dispatch_raw(*args,600)

def test_failed_owned_step_rolls_back_then_retries_identically():
    model,old=band_case(complex=True);configure(model);device=DeviceThreeTemperature(model,old);saved=deepcopy(device.native_state())
    with pytest.raises(RuntimeError):device.advance(1e-15,**BUDGET,max_nfev=1)
    assert device.native_state()==saved
    a,_=device.advance(1e-15,**BUDGET);b,_=DeviceThreeTemperature(model,old).advance(1e-15,**BUDGET)
    for name in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K','trap_fraction'):np.testing.assert_array_equal(getattr(a,name),getattr(b,name))

def test_nonlinear_adaptive_trajectory_and_forged_affine_work_rejected():
    model,old=band_case(complex=True);configure(model);device=DeviceThreeTemperature(model,old)
    r=device.run_transient([0.,1e-15,2e-15],initial_step_s=1e-15,maximum_step_s=1e-15,minimum_step_s=1e-20,temperature_atol_K=.1,temperature_rtol=.02,density_atol_m3=1e10,density_rtol=.02,**BUDGET)
    assert r['trajectory_energy_audit']['valid']
    new,report=model.step(old,1e-15,**BUDGET);bad=deepcopy(report);bad['band_temperature_law']='affine_lattice_temperature'
    with pytest.raises(ValueError):audit_three_temperature_energy(model,old,new,bad,**BUDGET)

def test_nonlinear_capacity_and_negative_beta_rejected():
    model,old=band_case();configure(model)
    model.band_varshni_beta=(np.array([-1.]),np.array([636.]))
    with pytest.raises(ValueError):model.step(old,2e-13,**BUDGET)
    configure(model);model.band_varshni_alpha=(np.array([1e-20]),np.array([1e-20]))
    with pytest.raises(ValueError,match='capacity'):model.step(old,2e-13,**BUDGET)
