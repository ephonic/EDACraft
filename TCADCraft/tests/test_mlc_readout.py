"""MLC measurement rejection restores the programmed state, including NLS history."""
import math

import numpy as np
import pytest

from tcad.postprocess.fe_loops import (
    _ramp_contact_and_run, extract_mlc_memory_window, run_mlc_program_read_sweep,
)
from test_fefet_validation import _FakeFESimulator
from test_physical_step_commit import high_level, PS


@pytest.mark.parametrize("value", [
    np.nan, np.inf, True, 1j, [1e-6], [1e-6, 2e-6], "1e-6", 0.0,
])
def test_invalid_mlc_current_restores_program_state(value):
    sim = _FakeFESimulator()

    def reader(device, result):
        device.set_oxide_traps(123.0)
        return value

    with pytest.raises((ValueError, RuntimeError)):
        run_mlc_program_read_sweep(
            sim, "gate", [1.0, 2.0], read_voltage=0.0, current_reader=reader)
    assert sim.voltage == 1.0
    assert sim.qot_history == []


def test_mlc_reader_exception_restores_program_state():
    sim = _FakeFESimulator()

    def reader(device, result):
        device.set_oxide_traps(123.0)
        raise LookupError("read instrument unavailable")

    with pytest.raises(LookupError, match="unavailable"):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], current_reader=reader)
    assert sim.voltage == 1.
    assert sim.qot_history == []


def test_mlc_polarization_measurement_failure_restores_program_state():
    sim = _FakeFESimulator()

    def reader(device, result):
        result["P"][:] = np.nan
        return 1e-6

    with pytest.raises(ValueError):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], current_reader=reader)
    assert sim.voltage == 1.


def test_mlc_signed_raw_currents_and_explicit_zero_censoring():
    sim = _FakeFESimulator()
    currents = iter([-1e-9, -1e-6, 0.0])
    result = run_mlc_program_read_sweep(
        sim, "gate", [1., 2., 3.], current_reader=lambda *_: next(currents),
        current_noise_floor=1e-10)
    np.testing.assert_array_equal(result["raw_read_currents"], [-1e-9, -1e-6, 0.])
    np.testing.assert_allclose(result["read_currents"], [1e-9, 1e-6, 1e-10])
    np.testing.assert_array_equal(result["censored_mask"], [False, False, True])
    assert result["memory_window_decades"] == pytest.approx(4.)
    assert result["signed_window_decades"] == pytest.approx(-1.)
    assert result["valid"] and not result["physical_validated"]


@pytest.mark.parametrize("kwargs", [
    {"current_reader": 3},
    {"program_voltages": [1.], "current_reader": lambda *_: 1e-6},
])
def test_invalid_mlc_measurement_configuration_does_not_program(kwargs):
    sim = _FakeFESimulator()
    params = {"program_voltages": [1., 2.]}
    params.update(kwargs)
    with pytest.raises(ValueError):
        run_mlc_program_read_sweep(sim, "gate", **params)
    assert sim.voltage == 0.


def test_mlc_window_extreme_finite_currents_avoid_ratio_overflow():
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        result = extract_mlc_memory_window([0., 1.], [1e-300, 1e300])
    assert result["signed_window_decades"] == pytest.approx(600.)
    assert result["memory_window_decades"] == pytest.approx(600.)


def test_mlc_failed_readout_restores_native_nls_history(monkeypatch):
    sim, reference = high_level(), high_level()
    for device in (sim, reference):
        assert device.run(max_iter=300, tol=1e-8)["converged"]
    # This insulating zero-mobility fixture uses Gummel. Keep that solver
    # while exercising the production protocol and native history checkpoint.
    monkeypatch.setattr(sim, "set_use_newton", lambda *_: None)
    monkeypatch.setattr(sim, "set_newton_log_space", lambda *_: None)

    def reader(device, result):
        # A nonzero read voltage already consumed one dwell before extraction.
        assert device._contact_voltages["right"] == 2.
        raise LookupError("read instrument unavailable")

    with pytest.raises(LookupError, match="unavailable"):
        run_mlc_program_read_sweep(
            sim, "right", [4., 6.], read_voltage=2., current_reader=reader,
            max_ramp_step=.5, max_iter=300, tol=1e-8)
    programmed = _ramp_contact_and_run(reference, "right", 4., .5, 300, 1e-8, 0)
    assert sim._contact_voltages["right"] == 4.
    np.testing.assert_allclose(sim.results["P"], programmed["P"], atol=1e-12)
    np.testing.assert_allclose(sim.results["P"][:, 0], -PS*(1-math.exp(-.1)), atol=1e-12)
    actual = _ramp_contact_and_run(sim, "right", 2., .5, 300, 1e-8, 0)
    expected = _ramp_contact_and_run(reference, "right", 2., .5, 300, 1e-8, 0)
    np.testing.assert_allclose(actual["P"], expected["P"], atol=1e-12)
    np.testing.assert_allclose(actual["P"][:, 0], -PS*(1-math.exp(-.2)), atol=1e-12)
