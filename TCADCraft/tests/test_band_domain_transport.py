"""Band-domain recovery in actual density-changing two-cell transport."""
from dataclasses import replace
import numpy as np
import pytest
from test_temperature_dependent_bands import band_case
from test_three_temperature import BUDGET
from tcad.solver.cut_cell_transport import Q
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy


def transport_case(mobility_ratio):
    model,old=band_case(count=2)
    model.Ec=np.full(2,5e-11*Q);model.Eh=np.full(2,5e-11*Q)
    model.mp=model.mp*mobility_ratio
    density=np.array([1.2e25,.8e25],dtype=np.longdouble)
    old=replace(old,n_m3=density,p_m3=density,electron_temperature_K=np.full(2,260.),hole_temperature_K=np.full(2,260.))
    model._validate_state(old)
    return model,old


@pytest.mark.parametrize('mobility_ratio',(1.,.8))
def test_cooling_with_nonzero_carrier_face_flux_and_density_changes(mobility_ratio):
    model,old=transport_case(mobility_ratio);device=DeviceThreeTemperature(model,old)
    new,report=device.advance(2e-13,**BUDGET)
    assert np.all(new.temperature_K<old.temperature_K)
    assert report['nonlinear_statistics'][2]>0
    assert report['independent_audit']['valid']
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)==report['independent_audit']
    for label,field in (('electrons','n_m3'),('holes','p_m3')):
        assert np.max(abs(getattr(new,field)/getattr(old,field)-1))>1e-5
        assert np.max(abs(report['integrated_particle_flux_s'][label][model.internal]))>1e10
        assert np.max(abs(report['integrated_carrier_energy_flux_W'][label][model.internal]))>1e-12
    assert not report['complete_device_energy'] and not report['physical_validated']
