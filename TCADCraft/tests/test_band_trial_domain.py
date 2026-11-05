"""Valid cooling roots adjacent to band-gap and storage-capacity boundaries."""
from dataclasses import replace
from copy import deepcopy
import numpy as np
import pytest
from test_temperature_dependent_bands import band_case
from test_three_temperature import BUDGET
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.cut_cell_transport import Q


def boundary_case(kind):
    model,old=band_case()
    old=replace(old,electron_temperature_K=np.array([260.]),hole_temperature_K=np.array([260.]))
    if kind=='gap':
        model.Ec=np.array([5e-11*Q]);model.Eh=np.array([5e-11*Q])
    else:
        beta=636.;T=300.;shape=T*(T+2*beta)/(T+beta)**2
        alpha=(model.capacity[0]-1e-7)/(2*old.n_m3[0]*shape)
        model.band_temperature_slopes=(np.zeros(1),np.zeros(1))
        model.band_varshni_alpha=(np.array([float(alpha)]),)*2
        model.band_varshni_beta=(np.array([beta]),)*2
    model._validate_state(old)
    return model,old


@pytest.mark.parametrize('kind',('gap','capacity'))
def test_valid_cooling_root_survives_constitutive_derivative_boundary(kind):
    model,old=boundary_case(kind);device=DeviceThreeTemperature(model,old)
    new,report=device.advance(2e-13,**BUDGET)
    assert new.temperature_K[0]<old.temperature_K[0]
    assert report['independent_audit']['valid']
    assert report['nonlinear_statistics'][2]>0
    assert report['nonlinear_statistics'][0]<=600
    assert not report['complete_device_energy'] and not report['physical_validated']
