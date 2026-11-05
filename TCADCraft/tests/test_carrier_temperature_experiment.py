"""Measured observable coverage cannot be replaced by commercial/phonon data."""
from copy import deepcopy
import pytest
from tcad.validation.carrier_temperature_experiment import qualify_carrier_temperature_experiment


def dataset():
    point=dict(provenance='measured',uncertainty_kind='standard_uncertainty',
               coordinates=[0.,1e-12,2e-12],values_K=[350.,325.,310.],uncertainty_K=[1.,1.,1.])
    return dict(source_kind='measured',source_sha256='a'*64,source_url='https://example.org/original',
      geometry_material_contacts={'material':'Si','length_m':1e-7},coordinate_units='s',
      whole_condition_roles=['calibration','holdout'],observables={k:deepcopy(point) for k in
        ('electron_temperature_K','hole_temperature_K','lattice_temperature_K')})


def test_qualified_evidence_is_not_solver_validation():
    report=qualify_carrier_temperature_experiment(dataset())
    assert report['ready_for_three_temperature_acceptance']
    assert not report['experimental_validated'] and not report['solver_prediction_compared']


def test_electron_optical_acoustic_three_baths_cannot_be_renamed():
    d=dataset();d['observables']['optical_phonon_temperature_K']=d['observables'].pop('hole_temperature_K')
    r=qualify_carrier_temperature_experiment(d)
    assert not r['ready_for_three_temperature_acceptance']
    assert not r['observable_coverage']['hole_temperature_K']


@pytest.mark.parametrize('kind',['commercial','digitized_uncertainty','no_holes','no_holdout','nonfinite',
 'negative_uncertainty','complex','bad_units','no_source','no_device'])
def test_missing_or_incompatible_measurement_evidence_rejected(kind):
    d=dataset();r=d['observables']['electron_temperature_K']
    if kind=='commercial':d['source_kind']='Sentaurus'
    if kind=='digitized_uncertainty':r['uncertainty_kind']='pixel_resolution'
    if kind=='no_holes':d['observables'].pop('hole_temperature_K')
    if kind=='no_holdout':d['whole_condition_roles']=['calibration']
    if kind=='nonfinite':r['values_K'][1]=float('nan')
    if kind=='negative_uncertainty':r['uncertainty_K'][1]=-1
    if kind=='complex':r['values_K'][1]=300+1j
    if kind=='bad_units':d['coordinate_units']='ps'
    if kind=='no_source':d['source_sha256']='bad'
    if kind=='no_device':d['geometry_material_contacts']={}
    assert not qualify_carrier_temperature_experiment(d)['ready_for_three_temperature_acceptance']
