"""Finite qualification budgets and independently excited spatial temperatures."""
from copy import deepcopy
import numpy as np
import pytest
from test_spatial_energy_transport import profile
from tcad.postprocess.spatial_energy_transport import compare_temperature_profiles,validate_spatial_profile


def inputs():
    p=profile('independent','holdout');x=np.linspace(1e-9,99e-9,17)
    temperatures={k:np.interp(x,p['x_m'],p[k]) for k in ('Tn_K','Tp_K','Tl_K')}
    return x,temperatures,p


@pytest.mark.parametrize('key',['bath_K','atol_K','peak_rtol','minimum_signal_K'])
@pytest.mark.parametrize('value',[np.inf,np.nan,True,[.1],1j,0.,-1.])
def test_nonfinite_nonscalar_and_nonpositive_contracts_cannot_qualify(key,value):
    x,t,p=inputs()
    options=dict(bath_K=600.);options[key]=value
    with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,**options)


def test_infinite_tolerance_cannot_accept_an_arbitrarily_wrong_profile():
    x,t,p=inputs();t['Tn_K']+=1e4
    assert not compare_temperature_profiles(x,t,p,bath_K=600.)['accepted']
    with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,bath_K=600.,atol_K=np.inf)


@pytest.mark.parametrize('missing',['Tn_K','Tp_K','Tl_K'])
def test_strict_qualification_rejects_an_unexcited_field_even_with_exact_prediction(missing):
    x,t,p=inputs();p[missing]=np.full(len(p['x_m']),600.);t[missing][:]=600.
    before=deepcopy(p)
    ordinary=compare_temperature_profiles(x,t,p,bath_K=600.)
    strict=compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=True)
    assert ordinary['accepted'] and ordinary['all_temperature_errors_within_budget']
    assert not strict['accepted'] and strict['all_temperature_errors_within_budget']
    assert strict['resolution_required'] and not strict['all_three_temperatures_resolved']
    assert not strict['physical_validated'] and not strict['provenance_authenticated']
    for k in p:np.testing.assert_equal(p[k],before[k])


def test_each_field_keeps_its_own_peak_excursion_and_all_cell_errors_are_checked():
    x,t,p=inputs()
    result=compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=True)
    assert result['accepted'] and result['all_three_temperatures_resolved']
    assert [result['fields'][k]['budget_K'] for k in ('Tn_K','Tp_K','Tl_K')]==pytest.approx([.101,.051,.021])
    t['Tl_K'][1]+=.03
    result=compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=True)
    assert not result['accepted'] and result['fields']['Tn_K']['accepted'] and result['fields']['Tp_K']['accepted']
    assert not result['fields']['Tl_K']['accepted']


@pytest.mark.parametrize('value',[1,0,'yes',None,[True]])
def test_resolution_policy_requires_an_explicit_boolean(value):
    x,t,p=inputs()
    with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,bath_K=600.,require_resolved=value)


def test_finite_scalar_gates_cannot_overflow_into_an_infinite_derived_budget():
    x,t,p=inputs();p['Tn_K']+=2e100;t['Tn_K']+=2e100
    with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,bath_K=600.,peak_rtol=1e300)


@pytest.mark.skipif(np.finfo(np.longdouble).max<=np.finfo(float).max,reason='extended range unavailable')
@pytest.mark.parametrize('kind',['scalar','reference_vector','native_vector'])
def test_extended_finite_inputs_must_not_overflow_during_float64_conversion(kind):
    x,t,p=inputs();large=np.longdouble('1e400')
    if kind=='scalar':
        with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,bath_K=600.,atol_K=large)
    elif kind=='reference_vector':
        p['Tn_K']=np.full(len(p['x_m']),large,dtype=np.longdouble)
        with pytest.raises(ValueError):validate_spatial_profile(p)
    else:
        t['Tn_K']=np.full(len(x),large,dtype=np.longdouble)
        with pytest.raises(ValueError):compare_temperature_profiles(x,t,p,bath_K=600.)
