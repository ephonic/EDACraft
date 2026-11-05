"""Independent series electrostatics, dynamics, and actual spatial rejection."""
from copy import deepcopy
from decimal import Decimal,localcontext
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from tcad.physics.ferroelectric_stack import SeriesFerroelectricStack


def stack(**changes):
    values=dict(thickness_fe=20e-9,thickness_oxide=.5e-9,epsilon_fe=15*8.8542e-12,
        epsilon_oxide=3.9*8.8542e-12,alpha=-649519052.838329,beta=331387271.85629034,
        viscosity=.1,area=1e-13)
    values.update(changes);return SeriesFerroelectricStack(**values)


@pytest.mark.parametrize('tox',[0.,.2e-9,.5e-9,1e-9])
@pytest.mark.parametrize('p,v',[(0.,8.),(1.4,0.),(-.7,-8.),(.1,3.)])
def test_voltage_partition_against_100_digit_independent_series_charge(tox,p,v):
    s=stack(thickness_oxide=tox);out=s.electrostatics(p,v)
    with localcontext() as c:
        c.prec=100
        t,o,ef,eo,pol,vol=[Decimal.from_float(x) for x in
            (s.thickness_fe,tox,s.epsilon_fe,s.epsilon_oxide,p,v)]
        d=(vol+pol*t/ef)/(t/ef+o/eo)
        expected=dict(displacement_C_m2=d,field_fe_V_m=(d-pol)/ef,field_oxide_V_m=d/eo,
            voltage_fe_V=t*(d-pol)/ef,voltage_oxide_V=o*d/eo,
            top_charge_C=-d*Decimal.from_float(s.area))
    for key,ref in expected.items():
        assert float(out[key])==pytest.approx(float(ref),rel=2e-14,abs=1e-25)
    assert float(out['voltage_fe_V']+out['voltage_oxide_V'])==pytest.approx(v,abs=2e-14)


@pytest.mark.parametrize('name,value',[(k,0.) for k in
    ('thickness_fe','epsilon_fe','epsilon_oxide','beta','viscosity','area')]+
    [('thickness_oxide',-1.),('alpha',np.inf),('alpha',True),('thickness_fe',[1.]),
     ('epsilon_oxide',np.nan),('viscosity','0.1')])
def test_invalid_material_geometry_and_parameters(name,value):
    with pytest.raises(ValueError):stack(**{name:value})


@pytest.mark.parametrize('times,drive',[
    ([0.],[0.]),([1.,2.],[0.,1.]),([0.,0.],[0.,1.]),([0.,-1.],[0.,1.]),
    ([0.,np.inf],[0.,1.]),([0.,1.],[0.]),([[0.,1.]],[0.,1.]),([False,True],[0.,1.])])
def test_invalid_clocks_and_drives(times,drive):
    with pytest.raises(ValueError):stack().solve_backward_euler(times,drive)


def test_be_monotonicity_gate_and_initial_state_are_explicit():
    s=stack(thickness_oxide=0.)
    with pytest.raises(ValueError,match='positive alpha_eff'):
        s.solve_backward_euler([0.,1e-8],[0.,8.])
    result=s.solve_backward_euler([0.,1e-12],[0.,0.],initial_polarization=1.4)
    assert result['polarization_C_m2'][0]==1.4
    assert not result['physical_validated'] and not result['spatial_solver_validated']
    assert not result['initial_current_available']


def test_no_oxide_limit_matches_uniform_film_cubic_and_terminal_sign():
    s=stack(thickness_oxide=0.)
    t=np.linspace(0.,1e-9,101);v=np.full(len(t),8.);v[0]=0.
    result=s.solve_backward_euler(t,v)
    p=result['polarization_C_m2']
    residual=s.viscosity*np.diff(p)/np.diff(t)+s.alpha*p[1:]+s.beta*p[1:]**3-v[1:]/s.thickness_fe
    assert max(abs(residual))<1e-4
    np.testing.assert_allclose(result['field_fe_V_m'],v/s.thickness_fe,rtol=2e-15)
    assert result['top_charge_C'][-1]<0.
    assert np.dot(np.diff(t),result['top_current_A'][1:])==pytest.approx(
        result['top_charge_C'][-1]-result['top_charge_C'][0],rel=1e-14)


def test_series_feedback_changes_zero_bias_stability_and_be_refines_to_independent_ode():
    assert stack(thickness_oxide=.2e-9).effective_alpha<0.
    assert stack(thickness_oxide=1e-9).effective_alpha>0.
    s=stack(thickness_oxide=1e-9)
    # Eliminate D independently from the two physical layers; do not call
    # production electrostatics or use its reduced coefficients in the ODE.
    def rhs(t,y):
        d=(8.+y[0]*s.thickness_fe/s.epsilon_fe)/(s.thickness_fe/s.epsilon_fe+s.thickness_oxide/s.epsilon_oxide)
        e=(d-y[0])/s.epsilon_fe
        return [(e-s.alpha*y[0]-s.beta*y[0]**3)/s.viscosity]
    reference=solve_ivp(rhs,(0.,1e-9),[0.],method='DOP853',rtol=1e-12,atol=1e-14)
    assert reference.success
    errors=[]
    for steps in [20,40,80]:
        times=np.linspace(0.,1e-9,steps+1);voltage=np.full(steps+1,8.);voltage[0]=0.
        p=s.solve_backward_euler(times,voltage)['polarization_C_m2'][-1]
        errors.append(abs(p-reference.y[0,-1]))
    assert errors[2]<errors[1]<errors[0]
    assert .4<errors[1]/errors[0]<.6 and .4<errors[2]/errors[1]<.6


def uniform_history():
    s=stack();times=np.array([0.,1e-11,2e-11]);v=np.array([0.,1.,0.])
    r=s.solve_backward_euler(times,v);states=[]
    for i,t in enumerate(times):
        p=np.zeros((5,3));p[:3,0]=r['polarization_C_m2'][i]
        q=r['top_charge_C'][i]
        states.append(dict(time_s=t,valid=True,converged=True,electrode_charge_available=True,fe_mask=[1,1,1,0,0],P=p.ravel(),
            electrode_voltages_V=np.array([0.,-v[i]]),electrode_charges_C=np.array([-q,q])))
    return states


def audit(history):
    return stack().audit_uniform_history(history,polar_axis=0,reference_polarization=1.4,
        polarization_rtol=.01,charge_rtol=.01)


def test_uniform_target_acceptance_does_not_imply_physical_validation():
    report=audit(uniform_history());assert report['valid'] and not report['physical_validated']


@pytest.mark.parametrize('failure',['invalid','unconverged','spread','charge','clock','mask','P','ports','charge_unavailable','geometry'])
def test_uniform_target_gate_rejects_invalid_and_inconsistent_states(failure):
    history=deepcopy(uniform_history());state=history[-1]
    if failure=='invalid':state['valid']=False
    elif failure=='unconverged':state['converged']=False
    elif failure=='spread':state['P'][0]+=.1
    elif failure=='charge':state['electrode_charges_C'][1]+=1e-14
    elif failure=='clock':state['time_s']=0.
    elif failure=='mask':state['fe_mask']=[0]*5
    elif failure=='P':state['P'][0]=np.nan
    elif failure=='charge_unavailable':state['electrode_charge_available']=False
    elif failure=='geometry':state['fe_mask']=[1,1,1,1,0]
    else:state['electrode_voltages_V']=[0.]
    with pytest.raises(ValueError):audit(history)


def test_actual_converged_quad_checkerboard_is_rejected_for_uniform_stack():
    data=json.loads((Path(__file__).parent/'data/fe_series_spatial_failure.json').read_text())
    history=data['selected_history']
    assert all(s['valid'] and s['converged'] for s in history)
    assert data['original_sample_count']==577
    with pytest.raises(ValueError,match='uniform-film target'):audit(history)


@pytest.mark.parametrize('index',range(5))
def test_actual_sentaurus_series_stack_replay(index):
    data=json.loads((Path(__file__).parent/'data/sentaurus_fe_oxide_stack.json').read_text())
    case=data['cases'][index]
    s=SeriesFerroelectricStack(thickness_oxide=case['oxide_nm']*1e-9,**data['material'])
    actual=s.solve_backward_euler(case['times_s'],case['drive_voltage_V'])
    actual['interface_potential_V']=-actual['voltage_fe_V']
    errors=[]
    for key,values in case['reference'].items():
        ref=np.array(values)
        errors.append(max(abs(actual[key]-ref))/max(abs(ref)))
    # One finer commercial mesh fails the PREDECLARED budget. Preserve it
    # as a rejection fixture, never silently loosen the budget or drop it.
    accepted=all(error<1e-3 for error in errors)
    assert accepted==case['comparison_passed']==(index!=3)
    assert not actual['spatial_solver_validated'] and not data['physical_validated']
