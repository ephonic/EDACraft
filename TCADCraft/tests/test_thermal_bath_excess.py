"""Maintained thermal boundaries: genuine energy exchange and transactional audits."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from scipy.optimize import root
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.postprocess.lattice_excess import audit_lattice_excess_step
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.core._bindings import PyDeviceSimulator
from test_lattice_excess import lattice_case,BUDGET,VALLEYS


def bath_case(a=-20000.,c=20000.,count=2,graded=False,temperatures=(298.,304.)):
    model,initial=lattice_case(a,c,count,graded)
    left=min((i for i,f in enumerate(model.mesh.faces) if f.neighbor<0),key=lambda i:model.mesh.faces[i].centroid_m[0])
    right=max((i for i,f in enumerate(model.mesh.faces) if f.neighbor<0),key=lambda i:model.mesh.faces[i].centroid_m[0])
    model.bath={left:temperatures[0],right:temperatures[1]}
    return model,initial


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('count,graded',[(2,False),(2,True),(4,True)])
def test_baths_close_actual_three_step_device_storage_source_and_boundary_work(a,c,count,graded):
    model,initial=bath_case(a,c,count,graded);d=LatticeCoupledExcessRelaxation(model,initial)
    power=np.zeros((count,3));power[0,0]=1e-5;power[-1,2]=-1e-5
    for dt in (2e-14,5e-14,9e-14):
        old=d.state;new,r=d.advance(dt,source_power_W=power,**BUDGET)
        a=audit_lattice_excess_step(d.configuration,old,new,r,source_power_W=power,**BUDGET)
        assert a['valid'] and not a['native_operators_used']
        assert all(Decimal(v)>=0 for v in a['boundary_conduction_entropy_J_K'])
        assert max(abs(Decimal(v)) for v in a['independent_boundary_energy_impulses_J'])>Decimal('1e-22')
        assert d.native_state()==dict(state=new.raw(),time_s=new.time_s)
        assert not r['complete_device_energy'] and not r['general_carrier_transport_integrated']


@pytest.mark.parametrize('T,sign',[(298.,1),(304.,-1)])
def test_sign_convention_distinguishes_heating_and_cooling(T,sign):
    model,initial=bath_case(0.,0.,temperatures=(T,T));d=LatticeCoupledExcessRelaxation(model,initial)
    new,r=d.advance(2e-14,**BUDGET)
    assert sign*Decimal(r['independent_audit']['net_outward_boundary_energy_J'])>0
    closed,initial=lattice_case(0.,0.);adiabatic=LatticeCoupledExcessRelaxation(closed,initial);other,_=adiabatic.advance(2e-14,**BUDGET)
    assert sign*(sum(float(c.lattice_temperature_K) for c in other.cells)-sum(float(c.lattice_temperature_K) for c in new.cells))>.1


def test_moderate_bath_solution_matches_general_native_driver():
    from tcad.solver.device_three_temperature import DeviceThreeTemperature
    model,initial=bath_case(-.4,.3);d=LatticeCoupledExcessRelaxation(model,initial)
    general=DeviceThreeTemperature(model,initial)
    new,r=d.advance(2e-14,**BUDGET);expected,_=general.advance(2e-14,**BUDGET)
    np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],expected.temperature_K,atol=2e-6,rtol=0)


def test_forced_bath_solution_matches_independent_all_temperature_equations():
    model,initial=bath_case(0.,0.,graded=True);d=LatticeCoupledExcessRelaxation(model,initial)
    power=np.array([[1e-5,0.,2e-5],[0.,-1e-5,-2e-5]]);h=2e-14
    new,r=d.advance(h,source_power_W=power,**BUDGET)
    def U(T):return reference_reservoir(1e25,float(T),0.,VALLEYS)['energy_density_J_m3']
    original=np.array([[U(T) for T in row] for row in zip(initial.electron_temperature_K,initial.hole_temperature_K)])
    def residual(x):
        T=x.reshape(2,3);conduction=np.zeros(2);rows=[]
        for f in model.internal:
            face=model.mesh.faces[f];i,j=face.owner,face.neighbor
            I=h*model.area[f]/(model.do[f]/model.conductivity[i]+model.dn[f]/model.conductivity[j])*(T[i,2]-T[j,2])
            conduction[i]+=I;conduction[j]-=I
        for f,Tbath in model.bath.items():
            i=model.mesh.faces[f].owner
            conduction[i]+=h*model.area[f]*model.conductivity[i]/model.do[f]*(T[i,2]-Tbath)
        for i in range(2):
            exchange=np.array([h/tau*(U(T[i,k])-U(T[i,2])) for k,tau in enumerate((model.tau_n[i],model.tau_p[i]))])
            rows.extend(U(T[i,k])-original[i,k]+exchange[k]-h*power[i,k]/model.vol[i] for k in range(2))
            rows.append(model.capacity[i]*(T[i,2]-initial.temperature_K[i])-sum(exchange)+(conduction[i]-h*power[i,2])/model.vol[i])
        return rows
    answer=root(residual,np.array([[350.,265.,300.],[351.,266.,302.]]).ravel(),tol=1e-10)
    assert answer.success
    np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],answer.x.reshape(2,3)[:,2],atol=2e-6,rtol=0)


@pytest.fixture(scope='module')
def accepted():
    model,initial=bath_case();d=LatticeCoupledExcessRelaxation(model,initial);old=d.state
    new,r=d.advance(2e-14,**BUDGET)
    return d.configuration,old,new,r


@pytest.mark.parametrize('damage',['zero','sign','drop','extra','cell','entropy_sign','scope','claim','clock','geometry','bath_temperature'])
def test_independent_audit_rejects_forged_boundary_contract(accepted,damage):
    config,old,new,r=accepted;r=deepcopy(r)
    if damage=='zero':r['boundary_energy_impulses_J'][0]='0'
    elif damage=='sign':r['boundary_energy_impulses_J'][0]=str(-Decimal(r['boundary_energy_impulses_J'][0]))
    elif damage=='drop':r['boundary_energy_impulses_J']=[]
    elif damage=='extra':r['boundary_energy_impulses_J'].append('0')
    elif damage=='cell':r['cell_energy_residuals_J'][0][2]='1e-17'
    elif damage=='entropy_sign':r['bath_energy_sign']='positive_inward'
    elif damage=='scope':r['scope']='carrier_blocked_lattice_Fourier_FD_excess_BE'
    elif damage=='claim':r['complete_device_energy']=True
    elif damage=='clock':r['dt_s']*=2
    else:
        rows=list(config.baths);row=list(rows[0]);row[2 if damage=='geometry' else 5]='0';rows[0]=tuple(row)
        config=replace(config,baths=tuple(rows))
    try:a=audit_lattice_excess_step(config,old,new,r,**BUDGET)
    except (ValueError,KeyError):return
    assert not a['valid']


@pytest.mark.parametrize('damage',['internal','negative','zero','nan','bool','bad_index'])
def test_invalid_baths_rejected_before_native_configuration(damage):
    model,initial=bath_case();f=next(iter(model.bath))
    if damage=='internal':model.bath={int(model.internal[0]):300.}
    elif damage=='bad_index':model.bath={100000:300.}
    else:model.bath={f:dict(negative=-1.,zero=0.,nan=float('nan'),bool=True)[damage]}
    with pytest.raises(ValueError):LatticeCoupledExcessRelaxation(model,initial)


@pytest.mark.parametrize('damage',['width','owner','fractional','conductance','temperature','nonfinite'])
def test_invalid_native_bath_install_is_retryable(damage):
    model,initial=bath_case();d=LatticeCoupledExcessRelaxation(model,initial);c=d.configuration
    raw=[v for cell in c.cells for v in (*cell.initial_densities_m3,cell.initial_temperatures_K[2],*cell.initial_temperatures_K[:2])]
    args=[v for cell in c.cells for v in cell.parameters];baths=c.packed_baths();bad=baths.copy()
    if damage=='width':bad.pop()
    elif damage=='owner':bad[0]='2'
    elif damage=='fractional':bad[0]='.5'
    elif damage=='conductance':bad[1]='-1'
    elif damage=='temperature':bad[2]='0'
    else:bad[2]='nan'
    b=PyDeviceSimulator(2,1,1,1.,1.,1.)
    with pytest.raises((RuntimeError,ValueError)):b.configure_lattice_excess(raw,args,c.packed_faces(),*c.cells[0].packed_valleys(),baths=bad)
    b.configure_lattice_excess(raw,args,c.packed_faces(),*c.cells[0].packed_valleys(),baths=baths)
    assert b.isolated_relaxation_state()==d.native_state()


@pytest.mark.parametrize('failure',['budget','audit','decode','interrupt','bracket'])
def test_failed_bath_step_preserves_state_clock_and_retry(monkeypatch,failure):
    model,initial=bath_case();d=LatticeCoupledExcessRelaxation(model,initial);before=d.native_state();old=d.state
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.lattice_excess.audit_lattice_excess_step',lambda *a,**k:dict(valid=False))
        if failure in ('decode','interrupt'):
            def fail(*a,**k):raise (KeyboardInterrupt if failure=='interrupt' else ValueError)('injected')
            patch.setattr(d,'_decode_candidate',fail)
        with pytest.raises((RuntimeError,ValueError,KeyboardInterrupt)):
            d.advance(2e-14,source_power_W=np.full((2,3),1e5) if failure=='bracket' else None,
                max_nfev=1 if failure=='budget' else 600,**BUDGET)
    assert d.state is old and d.native_state()==before
    actual,_=d.advance(2e-14,**BUDGET);fresh=LatticeCoupledExcessRelaxation(model,initial);expected,_=fresh.advance(2e-14,**BUDGET)
    assert actual==expected


def test_bath_configuration_frozen_and_adiabatic_report_cannot_invent_a_boundary():
    model,initial=bath_case();d=LatticeCoupledExcessRelaxation(model,initial);old=d.state
    model.bath.clear();new,r=d.advance(2e-14,**BUDGET)
    assert len(d.configuration.baths)==2 and r['independent_audit']['valid']
    closed,initial=lattice_case();other=LatticeCoupledExcessRelaxation(closed,initial);before=other.state
    after,report=other.advance(2e-14,**BUDGET);report['boundary_energy_impulses_J']=['0']
    with pytest.raises(ValueError):audit_lattice_excess_step(other.configuration,before,after,report,**BUDGET)
