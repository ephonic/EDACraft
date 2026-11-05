"""Absolute charge/flux checks independent of peak waveform agreement."""
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
import pytest
from tcad.validation import audit_electrode_charge_balance,integrate_electrode_surface_charge


def audit(times=(0.,1.),q=((-.25,-.75),(-.5,-.5)),volume=(1.,1.),**overrides):
    options=dict(boundary_coverage_complete=True,converged=True,
        charge_scale_C=1.,charge_atol_C=0.,charge_rtol=0.)
    options.update(overrides)
    return audit_electrode_charge_balance(times,q,volume,**options)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('sign',[-1,1])
def test_analytic_planar_bulk_charge_and_polarized_contact_flux(axis,sign):
    # D(x)=rho*(x-L/2)+constant, with independent polarization at either face.
    eps=2e-10;area=3e-13;length=2e-8;rho=sign*2e4;d0=.02-rho*length/2
    p=np.zeros((2,3));p[:,axis]=[.01,.015]
    d=np.array([d0,d0+rho*length]);e=np.zeros_like(p);e[:,axis]=(d-p[:,axis])/eps
    normals=np.zeros_like(p);normals[:,axis]=[-1,1]
    q=[integrate_electrode_surface_charge(e[i:i+1],p[i:i+1],[eps],normals[i:i+1],[area])['surface_charge_C'] for i in range(2)]
    np.testing.assert_allclose(q,area*d*np.array([1.,-1.]),rtol=1e-14)
    result=audit([0.],[q],[rho*length*area],charge_scale_C=abs(rho*length*area),charge_rtol=1e-12)
    assert result['charge_balance_compatible'] and not result['physical_validated']


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('pattern',['positive','negative','neutral'])
def test_native_absolute_ports_and_surface_fields_pass(axis,pattern):
    from test_lk_fixed_charge import charged_device,widths
    from test_transient_displacement import QE
    sim,x,eps,mask,area,c=charged_device(axis,True,pattern);states=sim.solve_transient()
    fixed=QE*area*np.dot(widths(x),c);charges=[]
    for state in states:
        row=[]
        for node,sign in [(0,-1),(-1,1)]:
            field=[[state['E'+label][node] for label in 'xyz']]
            p=state['P'].reshape(-1,3)[node:node+1] if node==0 else state['P'].reshape(-1,3)[-1:]
            normal=np.zeros((1,3));normal[0,axis]=sign
            row.append(integrate_electrode_surface_charge(field,p,[eps[node]],normal,[area])['surface_charge_C'])
        np.testing.assert_allclose(row,state['electrode_charges_C'],atol=1e-28,rtol=1e-12)
        charges.append(row)
    result=audit([s['time_s'] for s in states],charges,np.full(len(states),fixed),
        converged=[s['valid'] for s in states],charge_scale_C=1e-16,charge_rtol=1e-10)
    assert result['charge_balance_compatible']


@pytest.mark.parametrize('baseline',[1.,1e100,1e308])
def test_missing_small_bulk_charge_is_not_hidden_by_terminal_peak(baseline):
    result=audit(q=((baseline,-baseline),(baseline,-baseline)),volume=(1e-20,1e-20),
        charge_scale_C=1e-20,charge_rtol=.01)
    assert not result['charge_balance_compatible']
    np.testing.assert_array_equal(result['charge_balance_residual_C'],1e-20)


def test_exact_sum_retains_cancellation_across_overflowing_partials():
    maximum=np.finfo(float).max
    q=[[maximum,maximum,-maximum,-maximum,1e-20]]
    assert audit([0.],q,[-1e-20])['charge_balance_compatible']
    bad=audit([0.],q,[0.])
    assert bad['charge_balance_residual_C'][0]==1e-20 and not bad['charge_balance_compatible']


def test_exact_budget_boundary_and_sample_ownership():
    result=audit(q=((-1.,0.),(-1.,.125)),charge_rtol=.125)
    np.testing.assert_array_equal(result['sample_compatible'],[True,True])
    bad=audit(q=((-1.,0.),(-1.,np.nextafter(.125,1.))),charge_rtol=.125)
    np.testing.assert_array_equal(bad['sample_compatible'],[True,False])
    result['sample_compatible'][:]=False
    assert audit()['charge_balance_compatible']


@pytest.mark.parametrize('times,q,volume',[
    ([],[],[]),([0.,0.],[[-1.,0.]]*2,[1.,1.]),([-1.],[[-1.,0.]],[1.]),
    ([1.,0.],[[-1.,0.]]*2,[1.,1.]),([[0.]],[[-1.,0.]],[1.]),
    ([0.],[-1.,0.],[1.]),([0.],[[-1.]],[1.]),([0.],[[-1.,0.]],1.),
    ([0.],[[-1.,0.]],[[1.]]),([0.],[[-1.,0.]],[1.,1.]),
    ([0.,1.],[[-1.,0.]],[1.,1.]),([0.],[[-1.,np.nan]],[1.]),
    ([0.],[[-1.,0.]],[np.inf]),([0.],[['-1','0']],[1.]),
    ([False],[[-1.,0.]],[1.]),([0.],[[-1.,0.]],[True])])
def test_invalid_absolute_charge_shapes_types_and_time_rejected(times,q,volume):
    with pytest.raises(ValueError):audit(times,q,volume)


@pytest.mark.parametrize('option,value',[
    ('boundary_coverage_complete',False),('boundary_coverage_complete',1),
    ('boundary_coverage_complete',[True]),('converged',1),('converged',[True,False]),
    ('converged',[True]),('converged',None),('charge_scale_C',0.),
    ('charge_scale_C',-1.),('charge_scale_C',True),('charge_atol_C',-1.),
    ('charge_atol_C',[0.]),('charge_atol_C',np.nan),('charge_rtol',1.),
    ('charge_rtol',-1.),('charge_rtol','0'),('charge_rtol',np.inf)])
def test_explicit_status_and_physical_budget_required(option,value):
    with pytest.raises(ValueError):audit(**{option:value})


def test_nonrepresentable_budget_and_residual_rejected():
    tiny=np.nextafter(0.,1.)
    with pytest.raises(ValueError):audit(charge_scale_C=tiny,charge_rtol=.25)
    with pytest.raises(ValueError):audit(q=[[1e308,1e308]],times=[0.],volume=[1e308])
    with pytest.raises(ValueError):audit(charge_scale_C=1e308,charge_atol_C=1e308,charge_rtol=.9)


@pytest.mark.parametrize('bad', ['field_shape','p_shape','eps_shape','area_shape','normal_shape',
    'negative_eps','zero_area','zero_normal','long_normal','nan','complex','boolean'])
def test_invalid_surface_input_rejected(bad):
    args=[np.array([[1.,0.,0.]]),np.zeros((1,3)),np.array([1.]),np.array([[-1.,0.,0.]]),np.array([1.])]
    if bad=='field_shape':args[0]=np.ones(3)
    elif bad=='p_shape':args[1]=np.ones((1,2))
    elif bad=='eps_shape':args[2]=1.
    elif bad=='area_shape':args[4]=1.
    elif bad=='normal_shape':args[3]=np.zeros(3)
    elif bad=='negative_eps':args[2][:]=-1.
    elif bad=='zero_area':args[4][:]=0.
    elif bad=='zero_normal':args[3][:]=0.
    elif bad=='long_normal':args[3][0,0]=-2.
    elif bad=='nan':args[0][0,0]=np.nan
    elif bad=='complex':args[1]=np.zeros((1,3),dtype=complex)
    else:args[4]=np.array([True])
    with pytest.raises(ValueError):integrate_electrode_surface_charge(*args)


def test_surface_oblique_multisample_orientation_and_exact_products():
    e=[[2.,3.,4.],[-3.,5.,1.]];p=[[.2,.3,.4],[-.1,.3,-.5]]
    eps=[2.,3.];normals=[[.6,.8,0.],[0.,0.,-1.]];area=[.25,.75]
    expected=-sum(Fraction(a)*sum((Fraction(ep)*Fraction(f)+Fraction(pc))*Fraction(n)
        for f,pc,n in zip(ei,pi,ni)) for ei,pi,ep,ni,a in zip(e,p,eps,normals,area))
    result=integrate_electrode_surface_charge(e,p,eps,normals,area)
    assert result['surface_charge_C']==float(expected)
    opposite=integrate_electrode_surface_charge(e,p,eps,-np.array(normals),area)
    assert opposite['surface_charge_C']==-result['surface_charge_C']
    # Preserve eps*E-P cancellation, even when eps*E alone overflows float64.
    maximum=np.finfo(float).max
    result=integrate_electrode_surface_charge([[maximum,0.,0.]],[[-maximum,0.,0.]],[2.],[[-1.,0.,0.]],[.5])
    assert result['surface_charge_C']==maximum/2
    with pytest.raises(ValueError):
        integrate_electrode_surface_charge([[1e-200,0.,0.]],[[0.,0.,0.]],[1e-200],[[-1.,0.,0.]],[1.])


def test_surface_partition_and_scaling_preserve_total_charge():
    whole=integrate_electrode_surface_charge([[1e6,0.,0.]],[[.01,0.,0.]],[1e-10],[[-1.,0.,0.]],[1e-13])
    split=integrate_electrode_surface_charge([[1e6,0.,0.]]*4,[[.01,0.,0.]]*4,[1e-10]*4,[[-1.,0.,0.]]*4,[.25e-13]*4)
    assert split['surface_charge_C']==whole['surface_charge_C']


_REFERENCE=json.loads((Path(__file__).parent/'data/sentaurus_electrode_charge.json').read_text())['cases']
@pytest.mark.parametrize('case',_REFERENCE,ids=lambda c:c['name'])
@pytest.mark.parametrize('source',['surface','raw'])
def test_actual_commercial_surface_charge_passes_and_raw_charge_remains_rejected(case,source):
    q=case['electrode_charges_C'] if source=='surface' else case['raw_electrode_charges_C']
    result=audit(case['time_s'],q,case['enclosed_charge_C'],charge_scale_C=case['charge_scale_C'],charge_rtol=.01)
    assert result['charge_balance_compatible']==(source=='surface')
    residual=max(abs(v) for v in result['charge_balance_residual_C'])/case['charge_scale_C']
    assert residual<.001 if source=='surface' else residual>.99
    assert not result['trajectory_validated'] and not result['physical_validated']


def test_actual_integrated_dose_is_not_replaced_by_nominal_geometry():
    cases={c['name']:c for c in _REFERENCE}
    for sign in ['positive','negative']:
        mismatch=[]
        for level,kind in [(32,'surface'),(64,'surface'),(128,'formal'),(256,'formal')]:
            c=cases[f'{sign}_{kind}_m{level}'];nominal=(1 if sign=='positive' else -1)*1.602176634e-17
            mismatch.append(abs(c['enclosed_charge_C'][0]/nominal-1.))
        assert all(a>b>0. for a,b in zip(mismatch[:-1],mismatch[1:]))
        assert mismatch[0]>.01 and mismatch[-1]<.01
