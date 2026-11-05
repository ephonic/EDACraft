"""Representable output clocks may not strand subminimum physical time."""
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.solver.device_three_temperature import DeviceThreeTemperature

@pytest.mark.parametrize('start',[3.64e-12,3.65e-12,3.7e-12,3.03e-12])
def test_rounded_minimum_remainder_is_integrated_at_exact_clocks(start):
 model,_=case(count=1,uniform=True)
 old=ThreeTemperatureState([1e20],[1e20],[.3],[300.],start,[300.],[300.])
 device=DeviceThreeTemperature(model,old);end=float(np.nextafter(start+1e-14,np.inf));minimum=1e-18
 result=device.run_transient([end],initial_step_s=1e-14,maximum_step_s=1e-14,minimum_step_s=minimum,
  temperature_atol_K=.01,temperature_rtol=.002,density_atol_m3=1e6,density_rtol=1e-6,**BUDGET)
 assert device.state.time_s==end and result['trajectory_energy_audit']['valid']
 assert len(result['interval_reports'])==2
 previous=start
 for interval in result['interval_reports']:
  assert minimum<=interval['accepted_interval_s']<=1e-14
  for report in interval['substep_reports']:assert report['independent_audit']['valid']
  assert interval['initial_state'].time_s==previous
  previous=interval['substep_states'][-1].time_s
 assert previous==end
