"""Synthetic fixtures test the contract; they are not experimental evidence."""
from copy import deepcopy
import numpy as np
import pytest
from test_carrier_temperature_experiment import dataset
from tcad.validation.carrier_temperature_experiment import qualify_carrier_temperature_experiment,compare_carrier_temperature_experiment

def inputs():
 d=dataset();d.update(condition_id='unseen',condition_role='holdout')
 p=dict(condition_id='unseen',coordinate_units='s',geometry_material_contacts=deepcopy(d['geometry_material_contacts']),
  configuration_sha256='c'*64,configuration_frozen_before_holdout=True,observables={k:
   dict(coordinates=[0.,1e-12,2e-12],values_K=[350.5,325.5,310.5]) for k in d['observables']})
 return d,p
def compare(d,p,**kw):
 return compare_carrier_temperature_experiment(d,p,**dict(dict(maximum_absolute_error_K=1.,maximum_standardized_error=1.,
  calibration_condition_ids=['trained'],calibration_source_sha256=['b'*64]),**kw))

def test_independent_comparison_reports_errors_and_never_certifies_provenance():
 d,p=inputs();r=compare(d,p)
 assert r['solver_prediction_compared'] and r['comparison_passed'] and len(r['fields'])==3
 assert not r['experimental_validated'] and not r['physical_validated'] and not r['provenance_authenticated']
 for f in r['fields'].values():assert f['maximum_absolute_error_K']==.5 and f['maximum_standardized_error']==.5

def test_linear_interpolation_on_physical_time_without_refitting():
 d,p=inputs()
 for q in p['observables'].values():q.update(coordinates=[0.,2e-12],values_K=[350.,310.])
 r=compare(d,p);assert not r['comparison_passed']
 assert r['fields']['electron_temperature_K']['predicted_at_measurement_K']==[350.,330.,310.]

@pytest.mark.parametrize('gate',['absolute','standardized'])
def test_both_error_gates_are_enforced(gate):
 d,p=inputs();r=compare(d,p,**{'maximum_'+('absolute_error_K' if gate=='absolute' else 'standardized_error'):.1})
 assert not r['comparison_passed'] and r['solver_prediction_compared']

def test_confidence_interval_uses_declared_factor_not_half_width_as_sigma():
 d,p=inputs()
 for q in d['observables'].values():q.update(uncertainty_kind='confidence_interval',coverage_factor=2.,confidence_level=.95)
 r=compare(d,p,maximum_standardized_error=.75)
 assert not r['comparison_passed']
 assert r['fields']['hole_temperature_K']['maximum_standardized_error']==1.

@pytest.mark.parametrize('value',[None,0.,-1.,float('nan'),True,[2.]])
def test_confidence_interval_without_resolved_coverage_is_not_ready(value):
 d,p=inputs();d['observables']['electron_temperature_K'].update(uncertainty_kind='confidence_interval',coverage_factor=value,confidence_level=.95)
 assert not qualify_carrier_temperature_experiment(d)['ready_for_three_temperature_acceptance']
 assert not compare(d,p)['solver_prediction_compared']

@pytest.mark.parametrize('damage',['id_leak','hash_leak','role','condition','units','device','frozen','hash','outside','missing','unordered','complex'])
def test_incompatible_prediction_or_holdout_rejected(damage):
 d,p=inputs()
 if damage=='id_leak':d['condition_id']='trained'
 if damage=='hash_leak':d['source_sha256']='b'*64
 if damage=='role':d['condition_role']='calibration'
 if damage=='condition':p['condition_id']='other'
 if damage=='units':p['coordinate_units']='ps'
 if damage=='device':p['geometry_material_contacts']={}
 if damage=='frozen':p['configuration_frozen_before_holdout']=False
 if damage=='hash':p['configuration_sha256']='invalid'
 if damage=='outside':p['observables']['hole_temperature_K']['coordinates'][0]=1e-15
 if damage=='missing':p['observables'].pop('hole_temperature_K')
 if damage=='unordered':p['observables']['hole_temperature_K']['coordinates'][1]=0.
 if damage=='complex':p['observables']['hole_temperature_K']['values_K'][1]=300+1j
 with pytest.raises(ValueError):compare(d,p)

@pytest.mark.parametrize('value',[0.,-1.,float('nan'),True,[1.]])
def test_invalid_gates_rejected(value):
 d,p=inputs()
 with pytest.raises(ValueError):compare(d,p,maximum_absolute_error_K=value)

def test_incomplete_real_observable_coverage_does_not_start_comparison():
 d,p=inputs();d['observables'].pop('hole_temperature_K');r=compare(d,p)
 assert not r['solver_prediction_compared'] and not r['comparison_passed']
