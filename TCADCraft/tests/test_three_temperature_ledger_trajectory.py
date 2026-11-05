"""Cumulative replay must enforce channel coverage of every accepted substep."""
from copy import deepcopy
import pytest
from test_three_temperature import BUDGET
from test_three_temperature_trajectory_energy import path
from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory

@pytest.mark.parametrize('field',('energy_increments_J','cell_exchange_J',
    'cell_electrical_work_J','integrated_particle_flux_s'))
def test_extra_substep_channel_cannot_hide_behind_attached_valid_audit(path,field):
    model,result=path;intervals=deepcopy(result['interval_reports'])
    report=intervals[0]['substep_reports'][0]
    assert report['independent_audit']['valid']
    report[field]['unmodeled_reservoir']=0.
    with pytest.raises(ValueError,match=field+' channel coverage mismatch'):
        audit_three_temperature_trajectory(model,result['initial_state'],intervals,
            final_state=result['final_state'],**BUDGET)
