"""Identify independent flux coefficients and check every spatial temperature."""
from copy import deepcopy
import hashlib
import numpy as np
import pytest
from tcad.postprocess.spatial_energy_transport import (KB,Q,fit_spatial_energy_flux,
 validate_spatial_profile,compare_temperature_profiles)


def profile(name,role,sign=1.,r=1.,hf=1.):
    x=np.linspace(0,1e-7,129);shape=1-(2*x/1e-7-1)**2
    p=dict(case_id=name,role=role,source_sha256=hashlib.sha256(name.encode()).hexdigest(),
           material_model='fixed-gap-test',units='SI',x_m=x)
    for key,value in [('Tn_K',600+shape),('Tp_K',600+.5*shape),('Tl_K',600+.2*shape),
         ('n_m3',np.full(len(x),1e21)),('p_m3',np.full(len(x),1e21)),
         ('mu_n_m2_Vs',np.full(len(x),.003)),('mu_p_m2_Vs',np.full(len(x),.002)),
         ('Fn_m2_s',np.full(len(x),sign*1e22)),('Fp_m2_s',np.full(len(x),-sign*1e22))]:p[key]=value
    for prefix,Tkey,nkey,mukey,Fkey in [('Sn','Tn_K','n_m3','mu_n_m2_Vs','Fn_m2_s'),('Sp','Tp_K','p_m3','mu_p_m2_Vs','Fp_m2_s')]:
        T=p[Tkey];p[prefix+'_W_m2']=2.5*r*(KB*T*p[Fkey]-hf*KB**2/Q*p[nkey]*p[mukey]*T*np.gradient(T,x,edge_order=2))
    return p


def test_identify_two_flux_coefficients_per_carrier_and_holdout():
    result=fit_spatial_energy_flux([profile('a','calibration'),profile('b','calibration',-1),profile('c','holdout',-.5)])
    assert result['holdouts_accepted']
    for fit in result['parameters'].values():
        assert fit['r']==pytest.approx(1.,rel=1e-12) and fit['hf']==pytest.approx(1.,rel=1e-12)
    assert result['experimental_validated'] is False and result['physical_validated'] is False


def test_bad_heldout_flux_does_not_change_parameters():
    data=[profile('a','calibration'),profile('b','holdout')];before=fit_spatial_energy_flux(data)
    data[1]['Sn_W_m2']*=.6
    after=fit_spatial_energy_flux(data)
    assert after['parameters']==before['parameters'] and not after['holdouts_accepted']


@pytest.mark.parametrize('kind',['source','material','missing_holdout','no_thermal_gradient','negative_coefficients'])
def test_leaking_or_unidentifiable_fits_rejected(kind):
    data=[profile('a','calibration'),profile('b','holdout')]
    if kind=='source':data[1]['source_sha256']=data[0]['source_sha256']
    if kind=='material':data[1]['material_model']='other'
    if kind=='missing_holdout':data=data[:1]
    if kind=='no_thermal_gradient':data[0]['Tn_K'][:]=600
    if kind=='negative_coefficients':data[0]['Sn_W_m2']*=-1
    with pytest.raises(ValueError):fit_spatial_energy_flux(data)


@pytest.mark.parametrize('key,value',[('units','cm'),('x_m',np.zeros(129)),
 ('Tn_K',np.full(129,np.nan)),('n_m3',np.full(129,-1)),('Sn_W_m2',np.ones(129,dtype=complex))])
def test_invalid_spatial_fields_rejected(key,value):
    p=profile('a','holdout');p[key]=value
    with pytest.raises(ValueError):validate_spatial_profile(p)


def test_profile_gate_uses_excursion_and_checks_nonpeak_error():
    p=profile('a','holdout');x=p['x_m'][1:-1:4]
    temperatures={k:np.interp(x,p['x_m'],p[k]) for k in ('Tn_K','Tp_K','Tl_K')}
    assert compare_temperature_profiles(x,temperatures,p,bath_K=600)['accepted']
    temperatures['Tn_K'][1]+=.2
    report=compare_temperature_profiles(x,temperatures,p,bath_K=600)
    assert not report['accepted'] and report['fields']['Tn_K']['budget_K']<.11


def test_unresolved_profile_not_silently_called_resolved():
    p=profile('a','holdout');p['Tp_K']=np.full(129,600.)
    temps={k:p[k] for k in ('Tn_K','Tp_K','Tl_K')}
    result=compare_temperature_profiles(p['x_m'],temps,p,bath_K=600)
    assert result['accepted'] and not result['all_three_temperatures_resolved']
