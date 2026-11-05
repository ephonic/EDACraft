"""Reject a nonuniform commercial field even when point traces agree."""
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.validation import audit_uniform_ferroelectric_reference as audit


def arguments(**overrides):
    args=dict(positions_m=np.array([[0.,0.],[1e-8,0.],[0.,1e-7],[1e-8,1e-7]]),
        polarization_C_m2=np.tile([.2,0.,0.],(4,1)),time_s=1e-9,
        polarization_scale_C_m2=1.4,spread_atol_C_m2=1e-6,spread_rtol=0.)
    args.update(overrides);return args


@pytest.mark.parametrize('dimension',[1,2,3])
@pytest.mark.parametrize('component',[0,1,2])
def test_explicit_spatial_samples_and_all_vector_components(dimension,component):
    x=np.arange(4*dimension,dtype=float).reshape(4,dimension)*1e-9
    p=np.zeros((4,3));p[:,component]=.4
    result=audit(**arguments(positions_m=x,polarization_C_m2=p))
    assert result['uniform_reference_compatible']
    assert not result['physical_validated'] and not result['trajectory_validated']
    assert result['sampled_coordinate_dimension']==dimension
    p[0,component]+=.002
    assert not audit(**arguments(positions_m=x,polarization_C_m2=p))['uniform_reference_compatible']
    np.testing.assert_array_equal(result['polarization_spread_C_m2'],np.zeros(3))


def test_zero_mean_and_one_matching_point_cannot_hide_nonuniformity():
    p=np.zeros((4,3));p[:,0]=[0.,1.4,-1.4,0.]
    result=audit(**arguments(polarization_C_m2=p))
    assert p[:,0].mean()==0. and not result['uniform_reference_compatible']
    assert result['max_polarization_spread_C_m2']==2.8


def test_budget_is_declared_absolute_plus_fixed_reference_scale():
    p=np.zeros((4,3));p[0,2]=.002
    for relative,passed in [(0.,False),(.002,True)]:
        out=audit(**arguments(polarization_C_m2=p,spread_rtol=relative,spread_atol_C_m2=.0001))
        assert out['uniform_reference_compatible']==passed
        assert out['spread_budget_C_m2']==pytest.approx(.0001+relative*1.4)
    p[:]=3.
    assert audit(**arguments(polarization_C_m2=p,spread_rtol=0.,spread_atol_C_m2=0.))['uniform_reference_compatible']


@pytest.mark.parametrize('key,value',[
    ('positions_m',[0.,1.]),('positions_m',np.zeros((1,2))),('positions_m',np.zeros((4,4))),
    ('positions_m',np.zeros((4,2))),('positions_m',[[0.,0.],[np.inf,1.]]),
    ('positions_m',[[False],[True]]),('polarization_C_m2',np.zeros((4,2))),
    ('polarization_C_m2',np.zeros((3,3))),('polarization_C_m2',np.full((4,3),np.nan)),
    ('polarization_C_m2',[['.2',0.,0.]]*4),('time_s',-1.),('time_s',True),
    ('time_s',[0.]),('time_s',np.inf),('polarization_scale_C_m2',0.),
    ('polarization_scale_C_m2',False),('spread_atol_C_m2',-1.),('spread_atol_C_m2',True),
    ('spread_rtol',-1.),('spread_rtol',1.),('spread_rtol',np.nan),('spread_rtol','0.1')])
def test_malformed_spatial_evidence_and_budgets_are_rejected(key,value):
    with pytest.raises(ValueError):audit(**arguments(**{key:value}))


@pytest.mark.parametrize('case',['extent','spread','budget','budget_underflow'])
def test_range_errors_are_not_silently_exported(case,monkeypatch):
    args=arguments()
    if case=='extent':args['positions_m'][0,0]=-1e308;args['positions_m'][1,0]=1e308
    elif case=='spread':args['polarization_C_m2'][0,0]=-1e308;args['polarization_C_m2'][1,0]=1e308
    elif case=='budget':args.update(polarization_scale_C_m2=1e308,spread_atol_C_m2=1e308,spread_rtol=.9)
    else:args.update(polarization_scale_C_m2=1e-300,spread_atol_C_m2=0.,spread_rtol=1e-300)
    with pytest.raises(ValueError,match='range'):audit(**args)
    if case=='budget_underflow':
        # Some platforms implement longdouble as float64. Its intermediate
        # product can already be zero before the float64 export check.
        monkeypatch.setattr(np,'longdouble',np.float64)
        with pytest.raises(ValueError,match='range'):audit(**args)


@pytest.mark.parametrize('case_index',range(10))
def test_actual_commercial_fields_preserve_uniform_reference_acceptance(case_index):
    data=json.loads((Path(__file__).parent/'data/sentaurus_spatial_fields.json').read_text())
    c=data['cases'][case_index]
    result=audit(c['positions_m'],c['polarization_C_m2'],time_s=c['time_s'],
        polarization_scale_C_m2=1.4,spread_atol_C_m2=1e-6,spread_rtol=0.)
    assert result['uniform_reference_compatible']==c['uniform_reference_compatible']
    if c['name']=='long_hold_rejected_x_0.5nm_m2':
        assert c['point_trace_passed'] and not result['uniform_reference_compatible']
    if c['name']=='long_hold_rejected_x_1nm_m2':
        assert result['polarization_min_C_m2'][0]<-1. and result['polarization_max_C_m2'][0]>1.
