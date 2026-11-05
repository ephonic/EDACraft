"""Same-sign local rows must not terminate a globally unbalanced Newton solve."""
from dataclasses import replace
import numpy as np
import pytest
from test_three_temperature import case, BUDGET
from tcad.solver.device_three_temperature import DeviceThreeTemperature


def distributed_heat_loss(orchestration='native'):
    model, old = case(count=8, uniform=True)
    model.residual_orchestration = orchestration
    # Four equal side-wall heat ports per cell; x end faces stay insulated.
    model.bath = {f: 300. for f, face in enumerate(model.mesh.faces)
                  if face.neighbor < 0 and face.area_vector_m2[0] == 0}
    temperature = np.full(8, 301.)
    old = replace(old, temperature_K=temperature,
                  electron_temperature_K=temperature, hole_temperature_K=temperature)
    dt = 2e-18
    initial_rows = np.zeros(8)
    for f in model.bath:
        initial_rows[model.mesh.faces[f].owner] += dt*model.area[f]*model.conductivity[model.mesh.faces[f].owner]/model.do[f]
    # The former max-row merit accepted the initial iterate immediately.
    assert np.max(initial_rows)/BUDGET['energy_atol_J'] < .25
    assert sum(initial_rows)/BUDGET['energy_atol_J'] > 1
    return model, old, dt


@pytest.mark.parametrize('orchestration', ['native', 'python'])
def test_global_budget_requires_another_iteration(orchestration):
    model, old, dt = distributed_heat_loss(orchestration)
    new, report = model.step(old, dt, **BUDGET)
    assert report['nonlinear_statistics'][0] > 1
    assert np.all(new.temperature_K < old.temperature_K)
    assert abs(report['energy_residual_J']) <= BUDGET['energy_atol_J']
    assert report['independent_audit']['valid']


def test_global_merit_budget_exhaustion_keeps_owned_state_retryable():
    model, old, dt = distributed_heat_loss()
    device = DeviceThreeTemperature(model, old)
    before = device.native_state()
    with pytest.raises(RuntimeError, match='budget'):
        device.advance(dt, max_nfev=1, **BUDGET)
    assert device.state is not None and device.state.time_s == old.time_s
    assert device.native_state() == before
    new, report = device.advance(dt, **BUDGET)
    assert new.time_s == dt and report['independent_audit']['valid']
