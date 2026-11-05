"""External work in stiff excess coordinates, independent roots and rollback."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from scipy.optimize import root
from test_isolated_relaxation import solver
from test_three_temperature import BUDGET
from tcad.solver.isolated_relaxation import IsolatedThreeTemperatureRelaxation
from tcad.postprocess.isolated_relaxation import audit_isolated_relaxation_step
from tcad.postprocess.fermi_spectral_energy import reference_reservoir


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('power',[(1e-5,0.,0.),(0.,1e-5,0.),(0.,0.,1e-5),(-1e-5,2e-5,-1e-5)])
def test_driven_reservoirs_close_independent_local_and_whole_path_energy(a,c,power):
    device,_,_=solver(a,c);saved=[]
    for dt in (2e-14,5e-14,9e-14):
        old=device.state;new,r=device.advance(dt,source_power_W=power,**BUDGET)
        assert device.native_state()==dict(state=new.raw(),time_s=new.time_s)
        audit=audit_isolated_relaxation_step(device.configuration,old,new,r,source_power_W=power,**BUDGET)
        assert audit['valid'] and not r['complete_device_energy'] and not r['physical_validated']
        saved.append(audit)
    with localcontext() as ctx:
        ctx.prec=90
        assert abs(sum(Decimal(r['endpoint_energy_residual_J']) for r in saved))<Decimal('1e-27')
    if a<0:assert 0<abs(Decimal(new.electron_excess_energy_J_m3))<Decimal('1e-70')


def test_moderate_driven_step_matches_independent_three_temperature_root():
    device,model,initial=solver(0.,0.);power=(1e-5,-2e-5,3e-5);dt=2e-14
    new,report=device.advance(dt,source_power_W=power,**BUDGET)
    def U(k,T):return reference_reservoir(1e25,float(T),0.,model.valleys[('electrons','holes')[k]])['energy_density_J_m3']
    un,up=U(0,360.),U(1,260.);V=model.vol[0]
    def residual(T):
        tn,tp,tl=T
        exn=dt/model.tau_n[0]*(U(0,tn)-U(0,tl))
        exp=dt/model.tau_p[0]*(U(1,tp)-U(1,tl))
        return [U(0,tn)-un+exn-dt*power[0]/V,U(1,tp)-up+exp-dt*power[1]/V,
                model.capacity[0]*(tl-300.)-exn-exp-dt*power[2]/V]
    answer=root(residual,[350.,265.,301.],tol=1e-10);assert answer.success
    assert abs(answer.x[2]-float(new.lattice_temperature_K))<2e-6
    for k,field in enumerate(('electron_excess_energy_J_m3','hole_excess_energy_J_m3')):
        assert abs(U(k,answer.x[k])-U(k,answer.x[2])-float(getattr(new,field)))<1e-5


@pytest.mark.parametrize('damage',['power','impulse','drop','order','model','scope','work_sign','double_work'])
def test_offline_auditor_requires_independent_source_contract(damage):
    device,_,_=solver();power=(1e-5,-2e-5,3e-5);old=device.state
    new,report=device.advance(2e-14,source_power_W=power,**BUDGET);r=deepcopy(report)
    if damage=='power':r['source_power_W'][0]*=2
    elif damage=='impulse':r['source_impulses_J'][0]='0'
    elif damage=='drop':del r['source_impulses_J']
    elif damage=='order':r['source_order'].reverse()
    elif damage=='model':r['source_model']='Joule heating'
    elif damage=='scope':r['scope']='isolated_single_cell_FD_energy_excess_BE'
    else:
        # Relabeling the report and source together cannot change caller's input.
        scale=-1 if damage=='work_sign' else 2
        r['source_power_W']=[v*scale for v in power]
        r['source_impulses_J']=[str(Decimal(v)*scale) for v in r['source_impulses_J']]
    try:check=audit_isolated_relaxation_step(device.configuration,old,new,r,source_power_W=power,**BUDGET)
    except (ValueError,KeyError):return
    assert not check['valid']


@pytest.mark.parametrize('power',[(1.,2.),(1.,2.,3.,4.),(float('nan'),0,0),(0,float('inf'),0),(True,0,0),(0,np.bool_(False),0)])
def test_invalid_source_leaves_native_state_and_clock_unchanged(power):
    device,_,_=solver();before=device.native_state()
    with pytest.raises(ValueError):device.advance(2e-14,source_power_W=power,**BUDGET)
    assert before==device.native_state()


@pytest.mark.parametrize('failure',['budget','audit','bracket','below_band'])
def test_driven_failure_rolls_back_then_retries(monkeypatch,failure):
    device,_,_=solver();before=device.native_state();power=(1e-5,0.,0.)
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.isolated_relaxation.audit_isolated_relaxation_step',lambda *a,**k:dict(valid=False))
        if failure=='bracket':power=(0,0,1e5)
        if failure=='below_band':
            device,_,_=solver(0.,0.);before=device.native_state();power=(-1.,1.,0.)
        with pytest.raises((RuntimeError,ValueError)):
            device.advance(2e-14,source_power_W=power,max_nfev=1 if failure=='budget' else 256,**BUDGET)
    assert before==device.native_state()
    actual,_=device.advance(2e-14,source_power_W=(1e-5,0.,0.),**BUDGET)
    fresh,_,_=solver(0.,0.) if failure=='below_band' else solver()
    expected,_=fresh.advance(2e-14,source_power_W=(1e-5,0.,0.),**BUDGET)
    assert actual==expected


def test_driven_heating_crosses_initial_envelope_only_with_explicit_frozen_bounds():
    _,model,old=solver(0.,0.);old=replace(old,electron_temperature_K=np.array([300.]),hole_temperature_K=np.array([300.]))
    narrow=IsolatedThreeTemperatureRelaxation(model,old)
    device=IsolatedThreeTemperatureRelaxation(model,old,temperature_bounds_K=(250.,800.))
    before=narrow.native_state()
    with pytest.raises(RuntimeError,match='bracketed'):narrow.advance(2e-14,source_power_W=(0.,0.,.02),**BUDGET)
    assert narrow.native_state()==before
    new,r=device.advance(2e-14,source_power_W=(0.,0.,.02),**BUDGET)
    assert 450<float(new.lattice_temperature_K)<800 and r['independent_audit']['valid']


@pytest.mark.parametrize('bounds',[(0,400),(260,300),(300,260),(False,500),(float('nan'),500),(250,500,600)])
def test_temperature_envelope_requires_positive_enclosing_bounds(bounds):
    _,model,old=solver()
    with pytest.raises(ValueError):IsolatedThreeTemperatureRelaxation(model,old,temperature_bounds_K=bounds)


def test_native_rejects_invalid_impulses_and_releases_prepare_slot():
    device,_,_=solver();before=device.native_state()
    for bad in [('1',),('nan','0','0'),('inf','0','0')]:
        with pytest.raises((ValueError,RuntimeError)):device._backend.prepare_isolated_relaxation(2e-14,source_impulses_J=bad,**BUDGET)
        assert device.native_state()==before
    device.advance(2e-14,source_power_W=(1e-5,0.,0.),**BUDGET)


def test_independent_auditor_checks_physical_carrier_energy_domain():
    device,_,_=solver();old=device.state;new,r=device.advance(2e-14,source_power_W=(1e-5,0.,0.),**BUDGET)
    invalid=replace(new,electron_excess_energy_J_m3='-1e30')
    with pytest.raises(ValueError,match='band minimum'):
        audit_isolated_relaxation_step(device.configuration,old,invalid,r,source_power_W=(1e-5,0.,0.),**BUDGET)
