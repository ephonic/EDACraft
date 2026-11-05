"""Original physical coordinates must bound interpolation before projection."""
from copy import deepcopy
import numpy as np
import pytest
from test_carrier_temperature_comparison import inputs,compare

FIELDS=('electron_temperature_K','hole_temperature_K','lattice_temperature_K')


def clocks(kind):
    if kind=='uint_upper':return np.array([0,1,2**53+1],dtype=np.uint64),np.array([0,2**53],dtype=np.uint64)
    if kind=='uint_lower':return np.array([2**53,2**53+2,2**53+4],dtype=np.uint64),np.array([2**53+1,2**53+4],dtype=np.uint64)
    if kind=='signed_upper':return np.array([0,1,2**53+1],dtype=np.int64),np.array([0,2**53],dtype=np.int64)
    if kind=='mixed_integer':return np.array([0,1,2**63],dtype=np.uint64),np.array([0,2**63-1],dtype=np.int64)
    if kind=='integer_vs_float':return np.array([0,1,2**53+1],dtype=np.uint64),np.array([0,2**53],dtype=float)
    if kind=='float_vs_integer':return np.array([2**53,2**53+2,2**53+4],dtype=float),np.array([2**53+1,2**53+4],dtype=np.uint64)
    if kind=='signed_lower':return np.array([-2**53-1,0,1],dtype=np.int64),np.array([-2**53,1],dtype=np.int64)
    if kind=='python_int_list':return [0,1,2**64-1],[0,2**64-2]
    if kind=='python_mixed_list':return [0,1,2**63+1],[0.,float(2**63)]
    if kind=='python_negative_list':return [-2**53-1,0.,1],[-2**53,1]
    if np.finfo(np.longdouble).eps>=np.finfo(float).eps:pytest.skip('no extended precision')
    near=np.longdouble(1)+np.finfo(np.longdouble).eps
    if kind=='extended_upper':return np.array([0,.5,near],dtype=np.longdouble),np.array([0,1],dtype=float)
    if kind=='extended_lower':return np.array([1,1.5,2],dtype=float),np.array([near,2],dtype=np.longdouble)
    raise AssertionError(kind)


@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('kind',['uint_upper','uint_lower','signed_upper','mixed_integer',
    'integer_vs_float','float_vs_integer','signed_lower','extended_upper','extended_lower',
    'python_int_list','python_mixed_list','python_negative_list'])
def test_point_outside_raw_bounds_cannot_round_onto_float64_endpoint(field,kind):
    d,p=inputs();target,predicted=clocks(kind)
    d['observables'][field].update(coordinates=target,values_K=[350.]*3)
    p['observables'][field].update(coordinates=predicted,values_K=[350.]*2)
    # This is precisely the gap: the projected endpoints appear in range.
    projected=np.asarray(target,float);bounds=np.asarray(predicted,float)
    assert projected[0]>=bounds[0] and projected[-1]<=bounds[-1]
    with pytest.raises(ValueError,match='outside prediction coordinate range'):compare(d,p)


@pytest.mark.parametrize('measured_dtype',[np.uint64,np.int64,np.float16,np.float32,np.float64,np.longdouble])
@pytest.mark.parametrize('predicted_dtype',[np.uint64,np.float64])
def test_compatible_mixed_numeric_axes_still_compare(measured_dtype,predicted_dtype):
    d,p=inputs()
    for field in FIELDS:
        d['observables'][field].update(coordinates=np.array([0,1,2],dtype=measured_dtype),values_K=[350.]*3)
        p['observables'][field].update(coordinates=np.array([0,2],dtype=predicted_dtype),values_K=[350.]*2)
    r=compare(d,p)
    assert r['comparison_passed'] and r['solver_prediction_compared']
    assert not r['experimental_validated'] and not r['physical_validated']


@pytest.mark.parametrize('boundary',['lower','upper'])
def test_genuinely_inside_point_may_round_to_endpoint(boundary):
    d,p=inputs()
    if boundary=='upper':target=[0,1,2**53];predicted=[0,2**53+1]
    else:target=[2**53+1,2**53+2,2**53+4];predicted=[2**53,2**53+4]
    for field in FIELDS:
        d['observables'][field].update(coordinates=np.array(target,dtype=np.uint64),values_K=[350.]*3)
        p['observables'][field].update(coordinates=np.array(predicted,dtype=np.uint64),values_K=[350.]*2)
    assert compare(d,p)['comparison_passed']


def test_invalid_raw_bound_is_rejected_before_interpolation(monkeypatch):
    d,p=inputs()
    for field in FIELDS:
        target,predicted=clocks('mixed_integer')
        d['observables'][field].update(coordinates=target,values_K=[350.]*3)
        p['observables'][field].update(coordinates=predicted,values_K=[350.]*2)
    def forbidden(*a,**kw):raise AssertionError('raw extrapolation reached interpolation')
    monkeypatch.setattr(np,'interp',forbidden)
    with pytest.raises(ValueError,match='outside prediction coordinate range'):compare(d,p)


def test_raw_coordinate_comparison_does_not_modify_input_buffers():
    d,p=inputs()
    for field in FIELDS:
        d['observables'][field]['coordinates']=np.array([0,1,2],dtype=np.uint64)
        p['observables'][field]['coordinates']=np.array([0,1,2],dtype=np.longdouble)
    before=deepcopy((d,p));compare(d,p)
    for original,after in zip(before,(d,p)):
        for field in FIELDS:
            a=original['observables'][field]['coordinates'];b=after['observables'][field]['coordinates']
            assert a.dtype==b.dtype and a.tobytes()==b.tobytes()
