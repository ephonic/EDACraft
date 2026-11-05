"""A valid gap closer than the central-probe limit still has a cooling root."""
from copy import deepcopy
import numpy as np
import pytest
from test_band_trial_domain import boundary_case,BUDGET,DeviceThreeTemperature
from test_band_domain_reference import independent_temperatures
from test_band_domain_transport import transport_case
from tcad.solver.cut_cell_transport import Q


def narrow_case(transport=False):
    model,old=transport_case(.8) if transport else boundary_case('gap')
    model.Ec=np.full(len(old.n_m3),5e-17*Q)
    model.Eh=model.Ec.copy()
    model._validate_state(old)
    return model,old


@pytest.mark.parametrize('transport',(False,True))
def test_admissible_cooling_root_survives_central_domain_exhaustion(transport):
    model,old=narrow_case(transport);device=DeviceThreeTemperature(model,old)
    new,report=device.advance(2e-13,**BUDGET)
    assert np.all(new.temperature_K<old.temperature_K)
    assert report['independent_audit']['valid']
    assert 16<=report['nonlinear_statistics'][2] and report['nonlinear_statistics'][0]<=600
    if transport:
        for s,f in (('electrons','n_m3'),('holes','p_m3')):
            assert np.max(abs(report['integrated_particle_flux_s'][s][model.internal]))>1e10
            assert np.max(abs(report['integrated_carrier_energy_flux_W'][s][model.internal]))>1e-12
            assert np.max(abs(getattr(new,f)/getattr(old,f)-1))>1e-5
    else:
        expected=independent_temperatures(model,old,2e-13)
        np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],expected,rtol=0,atol=3e-6)
    assert not report['complete_device_energy'] and not report['physical_validated']


@pytest.mark.parametrize('transport',(False,True))
@pytest.mark.parametrize('budget',(17,30,50))
def test_recovery_probes_consume_budget_and_failed_device_is_retryable(transport,budget):
    model,old=narrow_case(transport);device=DeviceThreeTemperature(model,old)
    accepted=device.state;before=deepcopy(device.native_state())
    with pytest.raises(RuntimeError,match='evaluation budget exhausted'):
        device.advance(2e-13,**BUDGET,max_nfev=budget)
    assert device.state is accepted and device.native_state()==before and device._pending_token is None
    a,report=device.advance(2e-13,**BUDGET)
    b,reference=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    for field in ('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(a,field),getattr(b,field))
    np.testing.assert_array_equal(report['nonlinear_statistics'],reference['nonlinear_statistics'])
