"""Numerical acceptance controls only: no physical measurements are supplied."""
from copy import deepcopy
import numpy as np
import pytest
from test_carrier_temperature_comparison import inputs,compare
from tcad.validation.carrier_temperature_experiment import qualify_carrier_temperature_experiment

FIELDS=('electron_temperature_K','hole_temperature_K','lattice_temperature_K')


def axes(kind):
    if kind=='uint_descending':return np.array([2,1,0],dtype=np.uint64)
    if kind=='uint_interior_outside':return np.array([1,0,2],dtype=np.uint64)
    if kind=='signed_wrap':return np.array([2**63-1,-2**63,-2**63+2048],dtype=np.int64)
    if kind=='float64_collapse':return np.array([2**53,2**53+1,2**53+2],dtype=np.uint64)
    if kind=='duplicate':return np.array([0,1,1],dtype=np.uint64)
    if kind=='interval_overflow':return np.array([-1e308,1e308,1.5e308])
    raise AssertionError(kind)


@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('kind',['uint_descending','uint_interior_outside','signed_wrap',
    'float64_collapse','duplicate','interval_overflow'])
def test_invalid_measured_clock_stops_before_any_interpolation(field,kind,monkeypatch):
    d,p=inputs();d['observables'][field]['coordinates']=axes(kind)
    def forbidden(*a,**kw):raise AssertionError('unqualified data reached interpolation')
    monkeypatch.setattr(np,'interp',forbidden)
    report=compare(d,p)
    assert not report['qualification']['observable_coverage'][field]
    assert not report['solver_prediction_compared'] and not report['comparison_passed']


@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('kind',['uint_descending','uint_interior_outside','signed_wrap',
    'float64_collapse','duplicate','interval_overflow'])
def test_invalid_predicted_clock_is_rejected(field,kind):
    d,p=inputs();p['observables'][field]['coordinates']=axes(kind)
    with pytest.raises(ValueError,match='invalid prediction'):compare(d,p)


@pytest.mark.parametrize('dtype',[np.uint32,np.uint64,np.int32,np.int64,np.float32,np.float64])
def test_ordered_integer_and_float_axes_preserve_all_three_errors(dtype):
    d,p=inputs()
    for field in FIELDS:
        d['observables'][field]['coordinates']=np.array([0,1,2],dtype=dtype)
        p['observables'][field]['coordinates']=np.array([0,2],dtype=dtype)
        p['observables'][field]['values_K']=[350.,310.]
    r=compare(d,p,maximum_absolute_error_K=6.,maximum_standardized_error=6.)
    assert r['comparison_passed']
    for field in FIELDS:
        assert r['fields'][field]['predicted_at_measurement_K']==[350.,330.,310.]
        assert r['fields'][field]['signed_errors_K']==[0.,5.,0.]
    assert not r['experimental_validated'] and not r['physical_validated']


def test_valid_signed_axis_with_difference_overflow_remains_valid():
    d,p=inputs();clock=np.array([-2**63,0,2**63-1],dtype=np.int64)
    for field in FIELDS:
        d['observables'][field]['coordinates']=clock
        p['observables'][field]['coordinates']=clock
        p['observables'][field]['values_K']=d['observables'][field]['values_K']
    assert compare(d,p)['comparison_passed']


@pytest.mark.parametrize('factor,sigma',[(1e300,1e-300),(1e-300,1e300)])
def test_unrepresentable_ci_standard_uncertainty_fails_qualification(factor,sigma):
    d,p=inputs();d['observables']['hole_temperature_K'].update(
        uncertainty_kind='confidence_interval',coverage_factor=factor,confidence_level=.95,
        uncertainty_K=[sigma]*3)
    r=compare(d,p)
    assert not r['qualification']['ready_for_three_temperature_acceptance']
    assert not r['solver_prediction_compared']


def wide(value):
    if np.finfo(np.longdouble).maxexp<=np.finfo(np.float64).maxexp:
        pytest.skip('platform has no extended exponent representation')
    return np.longdouble(value)


@pytest.mark.parametrize('field',FIELDS)
@pytest.mark.parametrize('quantity,value',[
    ('coordinates','1e400'),('coordinates','1e-400'),
    ('values_K','1e400'),('values_K','1e-400'),
    ('uncertainty_K','1e400'),('uncertainty_K','1e-400')])
def test_extended_measurements_must_survive_float64_conversion(field,quantity,value):
    d,p=inputs();a=np.array(d['observables'][field][quantity],dtype=np.longdouble)
    a[0]=wide(value);d['observables'][field][quantity]=a
    assert not compare(d,p)['solver_prediction_compared']


@pytest.mark.parametrize('quantity,value',[
    ('coordinates','1e400'),('coordinates','1e-400'),
    ('values_K','1e400'),('values_K','1e-400')])
def test_extended_prediction_must_survive_float64_conversion(quantity,value):
    d,p=inputs();a=np.array(p['observables'][FIELDS[0]][quantity],dtype=np.longdouble)
    a[0]=wide(value);p['observables'][FIELDS[0]][quantity]=a
    with pytest.raises(ValueError,match='invalid prediction'):compare(d,p)


@pytest.mark.parametrize('quantity,value',[
    ('coverage_factor','1e400'),('coverage_factor','1e-400'),('confidence_level','1e-400')])
def test_extended_confidence_definition_must_be_representable(quantity,value):
    d,p=inputs();q=d['observables'][FIELDS[0]]
    q.update(uncertainty_kind='confidence_interval',coverage_factor=2.,confidence_level=.95)
    q[quantity]=wide(value)
    r=compare(d,p)
    assert not r['solver_prediction_compared']
    assert FIELDS[0]+':confidence_interval_definition_missing' in r['qualification']['reasons']


def test_confidence_level_rounding_to_one_is_not_qualified():
    if np.finfo(np.longdouble).eps>=np.finfo(float).eps:pytest.skip('no extended precision')
    d,p=inputs();d['observables'][FIELDS[0]].update(uncertainty_kind='confidence_interval',
        coverage_factor=2.,confidence_level=np.longdouble(1)-np.finfo(np.longdouble).eps)
    assert not compare(d,p)['solver_prediction_compared']


def test_no_extrapolation_at_an_interior_unsigned_point():
    d,p=inputs()
    for field in FIELDS:
        d['observables'][field].update(coordinates=np.array([1,0,2],dtype=np.uint64),
            values_K=[350.,350.,310.])
        p['observables'][field].update(coordinates=[1.,2.],values_K=[350.,310.])
    r=compare(d,p)
    assert not r['solver_prediction_compared'] and not r['comparison_passed']


def test_interpolation_overflow_cannot_reach_error_gates():
    d,p=inputs()
    for field in FIELDS:
        d['observables'][field]['coordinates']=[0.,1e-320,2e-320]
        p['observables'][field].update(coordinates=[0.,2e-320],values_K=[350.,310.])
    with pytest.raises(ValueError,match='unrepresentable temperature interpolation'):compare(d,p)


def test_qualification_and_comparison_do_not_rewrite_inputs():
    d,p=inputs();before=deepcopy((d,p))
    assert qualify_carrier_temperature_experiment(d)['ready_for_three_temperature_acceptance']
    compare(d,p)
    assert (d,p)==before
