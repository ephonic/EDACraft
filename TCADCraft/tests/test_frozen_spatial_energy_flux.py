"""Independent analytic spatial flux controls, with no coefficient fitting."""
from copy import deepcopy
import hashlib
import numpy as np
import pytest
from tcad.postprocess.spatial_energy_transport import check_spatial_energy_flux,KB,Q

def sample(name='a'):
    x=np.linspace(0,1e-7,129);u=x/1e-7
    p=dict(case_id=name,role='holdout',source_sha256=hashlib.sha256(name.encode()).hexdigest(),
        material_model='analytic quadratic',units='SI',x_m=x,Tl_K=600+u*(1-u))
    for tag,Tkey,nkey,mukey,Fkey,Skey,r,hf in (
        ('n','Tn_K','n_m3','mu_n_m2_Vs','Fn_m2_s','Sn_W_m2',.8,1.2),
        ('p','Tp_K','p_m3','mu_p_m2_Vs','Fp_m2_s','Sp_W_m2',1.1,.7)):
        T=600+2*u*(1-u);gradient=2*(1-2*u)/1e-7
        p.update({Tkey:T,nkey:np.full(len(x),1e21),mukey:np.full(len(x),.003),
            Fkey:np.full(len(x),1e22 if tag=='n' else -1e22)})
        p[Skey]=2.5*r*(KB*T*p[Fkey]-hf*KB**2/Q*p[nkey]*p[mukey]*T*gradient)
    return p

COEFF={'electrons':dict(r=.8,hf=1.2),'holes':dict(r=1.1,hf=.7)}

def test_analytic_flux_uses_frozen_parameters_without_mutation():
    p=sample();before=deepcopy(p);coeff=deepcopy(COEFF)
    result=check_spatial_energy_flux([p],coeff,relative_gate=1e-10)
    assert result['accepted'] and result['parameters']==COEFF
    assert result['coefficients_fitted'] is False and result['provenance_authenticated'] is False
    for k in p:np.testing.assert_equal(p[k],before[k])
    assert coeff==COEFF

def test_local_nonpeak_flux_error_and_wrong_coefficients_are_rejected():
    p=sample();p['Sn_W_m2'][60]+=10*np.max(abs(p['Sn_W_m2']))
    result=check_spatial_energy_flux([p],COEFF)
    assert not result['accepted'] and result['parameters']==COEFF
    assert next(c for c in result['checks'] if c['carrier']=='holes')['accepted']
    assert not check_spatial_energy_flux([sample()],{c:dict(r=1.,hf=1.) for c in COEFF})['accepted']

def test_zero_signal_cannot_qualify_even_with_zero_error():
    p=sample()
    for k in ('Tn_K','Tp_K'):p[k][:]=600
    for k in ('Fn_m2_s','Fp_m2_s','Sn_W_m2','Sp_W_m2'):p[k][:]=0
    result=check_spatial_energy_flux([p],COEFF)
    assert not result['accepted'] and all(not c['resolved'] for c in result['checks'])

@pytest.mark.parametrize('value',[0.,-1.,np.nan,np.inf,True,1j,[1.]])
def test_bad_coefficients_rejected(value):
    coeff=deepcopy(COEFF);coeff['electrons']['hf']=value
    with pytest.raises(ValueError):check_spatial_energy_flux([sample()],coeff)

@pytest.mark.parametrize('kwargs',[dict(relative_gate=np.inf),dict(relative_gate=True),
    dict(minimum_peak_flux_W_m2=0.),dict(minimum_peak_flux_W_m2=np.nan)])
def test_bad_gates_rejected(kwargs):
    with pytest.raises(ValueError):check_spatial_energy_flux([sample()],COEFF,**kwargs)

@pytest.mark.parametrize('kind',['empty','duplicate_case','duplicate_source','material','missing_carrier'])
def test_ambiguous_inputs_rejected(kind):
    data=[sample(),sample('b')];coeff=deepcopy(COEFF)
    if kind=='empty':data=[]
    if kind=='duplicate_case':data[1]['case_id']=data[0]['case_id']
    if kind=='duplicate_source':data[1]['source_sha256']=data[0]['source_sha256']
    if kind=='material':data[1]['material_model']='other'
    if kind=='missing_carrier':del coeff['holes']
    with pytest.raises(ValueError):check_spatial_energy_flux(data,coeff)
