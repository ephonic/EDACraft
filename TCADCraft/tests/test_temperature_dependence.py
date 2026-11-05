import numpy as np
import pytest

from tcad.material.temperature_dependence import TemperatureDependentMaterial, fit_power_temperature_law


def material():
    return TemperatureDependentMaterial('Si','Sentaurus Silicon.par; calibrated fixture',300.,1.17,.000473,636.,.14,2.3,150.,1.2,(250.,500.))


def test_temperature_laws_are_monotone_and_traceable():
    result=material().evaluate([300.,400.])
    assert result['bandgap_eV'][1] < result['bandgap_eV'][0]
    assert result['mobility_m2_Vs'][1] < result['mobility_m2_Vs'][0]
    assert result['conductivity_W_m_K'][1] < result['conductivity_W_m_K'][0]
    assert result['physical_validated'] is False and result['source']


def test_temperature_range_and_nonphysical_extrapolation_are_guarded():
    with pytest.raises(ValueError,match='calibrated range'): material().evaluate(700.)
    result=material().evaluate(700.,extrapolate=True)
    assert result['extrapolated']
    with pytest.raises(ValueError): material().evaluate([300.,float('nan')])


def test_power_fit_preserves_provenance_and_recovers_exponent():
    t=np.array([250.,300.,400.,500.]); y=2e-2*(t/300.)**-1.7
    fit=fit_power_temperature_law(t,y,source='measured wafer A',name='mobility')
    assert fit['exponent']==pytest.approx(1.7,rel=1e-12)
    assert fit['fit_rmse']<1e-15 and fit['source']=='measured wafer A'


def test_invalid_provenance_and_samples_rejected():
    with pytest.raises(ValueError): fit_power_temperature_law([300.,400.],[1.,1.],source='',name='x')
    with pytest.raises(ValueError): fit_power_temperature_law([300.,300.],[1.,2.],source='x',name='x')
