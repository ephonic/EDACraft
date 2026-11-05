"""Protocol acceptance must use explicit booleans and real solver fields."""
from contextlib import contextmanager
from copy import deepcopy

import numpy as np
import pytest

from tcad.physics.reliability import CyclingDegradation, TrapKinetics
from tcad.postprocess import fe_loops
from test_fe_measurement_protocols import IdealFE
from test_physical_step_commit import high_level


DRIVERS = ["pv", "pund", "width", "retention", "endurance", "power", "mlc"]
BAD_RESULTS = [("flag", name, value)
               for name in ("converged", "valid", "target_reached", "physical_step_accepted")
               for value in (np.nan, "False", 1, np.array(True), None)]
BAD_RESULTS += [("missing", name, None) for name in ("converged", "valid")]
BAD_RESULTS += [("field", name, kind) for name in ("phi", "P")
                for kind in ("complex", "string", "bool")]
BAD_RESULTS += [("mapping", "result", value) for value in (None, [])]


def run_driver(driver, sim, trap=None, damage=None):
    if driver == "pv":
        return fe_loops.run_pv_sweep(sim, "gate", 1., n_pts=2)
    if driver == "pund":
        return fe_loops.run_pund_sequence(sim, "gate", 1., 1e-8,
                                          n_points=10, pre_pol_hold=1)
    if driver == "width":
        return fe_loops.run_pulse_width_sweep(sim, "gate", 1., 1e-8,
                                             pulse_widths=[.1], saturation_polarization=.2)
    if driver == "retention":
        return fe_loops.run_retention(sim, "gate", 1., n_steps=1, dt=.1,
                                      trap_model=trap)
    if driver == "endurance":
        return fe_loops.run_endurance(sim, "gate", 1., 1e-8, n_cycles=1,
                                      pulse_width=.1, trap_model=trap, degradation_model=damage)
    if driver == "power":
        return fe_loops.run_power_measurement(sim, "gate", 1., .1,
                   current_reader=lambda *_: {"gate": 1e-6, "ground": -1e-6})
    return fe_loops.run_mlc_program_read_sweep(sim, "gate", [1., 2.], retries=0,
                                              max_ramp_step=10., current_reader=lambda *_: 1e-6)


def complete_result(sim, result, physical_step):
    result.update(target_reached=np.bool_(True),
                  physical_step_accepted=np.bool_(physical_step),
                  applied_contact_voltages={"gate": sim.voltage, "ground": 0.})
    return result


@pytest.mark.parametrize("driver", DRIVERS)
@pytest.mark.parametrize("malformation", BAD_RESULTS)
def test_malformed_result_cannot_commit_protocol(driver, malformation):
    sim = IdealFE()
    trap, damage = TrapKinetics(1e16), CyclingDegradation()
    original_run = sim.run
    kind, name, value = malformation

    def injected(**kwargs):
        result = complete_result(sim, original_run(**kwargs), kwargs.get("physical_step", True))
        if kind == "flag":
            result[name] = value
        elif kind == "missing":
            result.pop(name)
        elif kind == "mapping":
            return value
        else:
            if value == "complex":
                result[name] = result[name].astype(complex) + 1j
            elif value == "string":
                result[name] = result[name].astype(str)
            else:
                result[name] = np.ones_like(result[name], dtype=bool)
        return result

    sim.run = injected
    with pytest.raises(RuntimeError):
        run_driver(driver, sim, trap, damage)
    assert sim.memory == 0.
    assert sim.voltage == 0.
    assert sim.qot_history == []
    assert trap.occupancy is None
    assert damage.cycles == 0


@pytest.mark.parametrize("driver", DRIVERS)
def test_real_results_and_numpy_boolean_flags_are_accepted(driver):
    sim = IdealFE()
    original_run = sim.run

    def run(**kwargs):
        result = complete_result(sim, original_run(**kwargs), kwargs.get("physical_step", True))
        result["converged"] = np.bool_(True)
        result["valid"] = np.bool_(True)
        return result

    sim.run = run
    run_driver(driver, sim)


def test_frozen_pund_initialization_cannot_report_physical_commit():
    sim = IdealFE()
    original_run = sim.run

    def run(**kwargs):
        result = complete_result(sim, original_run(**kwargs), True)
        return result

    sim.run = run
    with pytest.raises(fe_loops.ReliabilityStepError) as error:
        run_driver("pund", sim)
    assert error.value.completed_segments == 0
    assert error.value.elapsed_time == 0.
    assert sim.memory == 0.
    assert sim.voltage == 0.


def test_mlc_intermediate_ramp_cannot_report_physical_commit():
    sim = IdealFE()
    original_run = sim.run

    def run(**kwargs):
        return complete_result(sim, original_run(**kwargs), True)

    sim.run = run
    with pytest.raises(RuntimeError, match="not accepted"):
        fe_loops.run_mlc_program_read_sweep(sim, "gate", [1., 2.], retries=0,
                                           max_ramp_step=.5, current_reader=lambda *_: 1e-6)
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("failure_call", [2, 4])
@pytest.mark.parametrize("invalid", ["valid_nan", "missing_valid", "physical_true", "physical_nan"])
def test_native_rejected_charge_helper_restores_entire_segment(failure_call, invalid):
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["valid"]
    trap = TrapKinetics(1e16, capture_tau=1., emission_tau=2.)
    original_run, original_transaction = sim.run, sim.reliability_transaction
    calls, segments = 0, 0
    entry = {}

    @contextmanager
    def transaction(*models, **kwargs):
        nonlocal segments, entry
        segments += 1
        if segments == failure_call // 2:
            entry = dict(results=deepcopy(sim.results), contacts=deepcopy(sim._contact_voltages),
                         dwell=sim._fe_nls_dt, occupancy=deepcopy(trap.occupancy))
        with original_transaction(*models, **kwargs):
            yield

    def run(**kwargs):
        nonlocal calls
        calls += 1
        result = original_run(**kwargs)
        if calls == failure_call:
            assert kwargs["physical_step"] is False
            if invalid == "missing_valid":
                result.pop("valid")
            elif invalid == "valid_nan":
                result["valid"] = np.nan
            else:
                result["physical_step_accepted"] = True if invalid == "physical_true" else np.nan
        return result

    sim.run, sim.reliability_transaction = run, transaction
    with pytest.raises(fe_loops.ReliabilityStepError) as error:
        fe_loops.run_retention(sim, "right", 4., n_steps=1, dt=.2,
                              trap_model=trap, max_iter=300, tol=1e-8)
    accepted = failure_call // 2 - 1
    assert error.value.completed_segments == accepted
    assert error.value.elapsed_time == pytest.approx(.2 * accepted)
    assert sim._contact_voltages == entry["contacts"]
    assert sim._fe_nls_dt == entry["dwell"]
    np.testing.assert_equal(trap.occupancy, entry["occupancy"])
    for key in ("phi", "P"):
        np.testing.assert_array_equal(sim.results[key], entry["results"][key])
    retry = original_run(max_iter=300, tol=1e-8, physical_step=False)
    for key in ("phi", "P"):
        np.testing.assert_allclose(retry[key], entry["results"][key], atol=1e-12)
