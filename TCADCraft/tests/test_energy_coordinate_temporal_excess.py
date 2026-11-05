"""Real native error control below all exported temperature resolutions."""
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case
from test_adaptive_energy_coordinate import OPTIONS
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates
from tcad.solver.adaptive_energy_coordinate import AdaptiveStepError


def test_real_tiny_energy_alone_rejects_a_trial_with_identical_thermal_views():
    model,thermal=transport_case(1,0,0)
    thermal=replace(thermal,electron_temperature_K=thermal.temperature_K,hole_temperature_K=thermal.temperature_K)
    state=replace(initialize_energy_coordinates(model,thermal),excess_J_m3=('1e-120','-1e-120'))
    device=Device(model,state);old=device.state;before=device.native_state()
    options=dict(OPTIONS,excess_atol_J_m3=1e-124,max_retries=0)
    with pytest.raises(AdaptiveStepError) as caught:device.advance_adaptive(2e-13,**options)
    assert device.state is old and device.native_state()==before
    assert len(caught.value.attempts)==1
    trial=caught.value.attempts[0];assert trial['native_advance_calls']==3
    assert trial['normalized_error']>1
    for field,value in trial['field_errors'].items():
        assert value>1 if field.startswith('excess_') else value==0
    for candidate in trial['states']:
        for field in ('temperature_K','electron_temperature_K','hole_temperature_K'):
            np.testing.assert_array_equal(getattr(candidate.thermal,field),getattr(old.thermal,field))
    new,report=device.advance_adaptive(2e-13,**dict(options,excess_atol_J_m3=1e-120))
    assert 0<report['normalized_temporal_error']<1
    assert all(0<abs(Decimal(e))<Decimal('1e-120') for e in new.excess_J_m3)
