"""No epsilon advance or invisible half step at a large absolute clock."""
from dataclasses import replace
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case
from test_adaptive_energy_coordinate import OPTIONS,TRANSIENT
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.solver.adaptive_energy_coordinate import AdaptiveStepError
from tcad.solver.transient_energy_coordinate import EnergyCoordinateTransientError


@pytest.mark.parametrize('mode',['no_clock_advance','no_half_clock','rounded_below_minimum','output_no_half_clock'])
def test_unrepresentable_or_subminimum_intervals_never_call_native_advance(monkeypatch,mode):
    model,initial=transport_case(1,0,0);initial=replace(initial,time_s=1.)
    device=Device(model,initial);old=device.state;before=device.native_state()
    def deny(*a,**k):raise AssertionError('clock-invalid request attempted native solve')
    monkeypatch.setattr(Device,'advance',deny)
    if mode=='no_clock_advance':
        with pytest.raises(ValueError,match='clock'):
            device.advance_adaptive(1e-31,**dict(OPTIONS,minimum_step_s=1e-35))
    elif mode=='no_half_clock':
        with pytest.raises(AdaptiveStepError,match='clock resolution') as caught:
            device.advance_adaptive(float(np.nextafter(1.,np.inf)-1.),**OPTIONS)
        assert caught.value.attempts==()
    elif mode=='rounded_below_minimum':
        assert (1.+1e-13)-1.<1e-13
        with pytest.raises(AdaptiveStepError,match='minimum'):
            device.advance_adaptive(1e-13,**dict(OPTIONS,minimum_step_s=1e-13))
    else:
        with pytest.raises(EnergyCoordinateTransientError) as caught:
            device.run_transient([float(np.nextafter(1.,np.inf))],**TRANSIENT)
        assert not caught.value.diagnostics['published']
    assert device.state is old and device.native_state()==before
