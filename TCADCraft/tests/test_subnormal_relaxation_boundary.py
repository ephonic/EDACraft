"""An unrepresentable time remains rejected at the lower float64 boundary."""
from dataclasses import replace
import numpy as np
import pytest
from test_subnormal_relaxation_audit import subnormal_case,BUDGET,DeviceThreeTemperature,audit_three_temperature_energy
from tcad.core._bindings import native_three_temperature_dispatch_raw
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs


@pytest.mark.parametrize('api',('public','native','independent_audit'))
def test_positive_real_time_rounding_to_zero_is_never_clipped_or_accepted(api):
    model,initial=subnormal_case();accepted,report=DeviceThreeTemperature(model,initial).advance(2e-14,**BUDGET)
    temperatures=dict(temperature_K=np.array([310.95]),electron_temperature_K=np.array([310.95]),hole_temperature_K=np.array([310.95]))
    old=replace(initial,**temperatures);new=replace(accepted,**temperatures)
    with pytest.raises(ValueError,match='range|relaxation'):
        if api=='public':DeviceThreeTemperature(model,old)
        elif api=='native':native_three_temperature_dispatch_raw(*pack_three_temperature_inputs(model,old,2e-14,**BUDGET),1)
        else:audit_three_temperature_energy(model,old,new,report,**BUDGET)
