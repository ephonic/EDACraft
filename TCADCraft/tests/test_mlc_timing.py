"""Independent NLS dwell for program/reset/read, without numerical ramp time."""
import math

import numpy as np
import pytest

from tcad.postprocess.fe_loops import _ramp_contact_and_run, run_mlc_program_read_sweep
from test_fefet_validation import _FakeFESimulator
from test_physical_step_commit import high_level, PS


class TimedSim(_FakeFESimulator):
    def __init__(self):
        super().__init__()
        self._fe_nls_dt = .1
        self.dwell = .1
        self.accepted = []

    def set_ferroelectric_nls_dwell_time(self, dt):
        super().set_ferroelectric_nls_dwell_time(dt)
        self._fe_nls_dt = float(dt)

    def run(self, **kwargs):
        if kwargs.get("physical_step", True):
            self.accepted.append((self.voltage, self.dwell))
        return super().run(**kwargs)


def test_mlc_independent_phase_dwell_and_segment_count():
    sim = TimedSim()
    result = run_mlc_program_read_sweep(
        sim, "gate", [1., 2.], reset_voltage=-1., read_voltage=.2,
        program_width=.3, reset_width=.4, read_width=.05, max_ramp_step=.1)
    np.testing.assert_allclose(sim.accepted, [
        [-1., .4], [1., .3], [.2, .05], [-1., .4], [2., .3], [.2, .05]])
    assert result["elapsed_time"] == pytest.approx(1.5)
    assert result["completed_segments"] == 6
    assert result["completed_read_states"] == 2
    assert [s["phase"] for s in result["protocol_segments"]] == [
        "reset", "program", "read"] * 2
    assert result["timing_available"]
    assert result["timing_kind"] == "accepted_nls_dwell"


def test_mlc_inherited_width_is_resolved_once_before_read_changes_it():
    sim = TimedSim()
    result = run_mlc_program_read_sweep(sim, "gate", [1., 2.], read_width=.01)
    np.testing.assert_allclose(sim.accepted, [[1., .1], [0., .01], [2., .1], [0., .01]])
    assert result["elapsed_time"] == pytest.approx(.22)


def test_mlc_legacy_unknown_dwell_is_not_invented():
    result = run_mlc_program_read_sweep(_FakeFESimulator(), "gate", [1., 2.])
    assert result["elapsed_time"] is None
    assert not result["timing_available"]
    assert result["completed_segments"] == 4
    assert all(s["dwell_s"] is None for s in result["protocol_segments"])


@pytest.mark.parametrize("phase", ["program", "reset", "read"])
@pytest.mark.parametrize("width", [0., -1., np.nan, np.inf, True, [1e-3], "1e-3"])
def test_mlc_invalid_width_does_not_change_entry_state(phase, width):
    sim = TimedSim()
    with pytest.raises(ValueError):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], **{phase + "_width": width})
    assert sim.voltage == 0.
    assert sim._fe_nls_dt == .1
    assert sim.accepted == []


def test_mlc_total_dwell_overflow_is_rejected_before_programming():
    sim = TimedSim()
    with pytest.raises(ValueError, match="total MLC dwell"):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], program_width=1e308, read_width=1e308)
    assert sim.accepted == []


@pytest.mark.parametrize("model", [0, 1, 3])
def test_mlc_explicit_width_cannot_claim_non_nls_dynamics(model):
    sim = TimedSim()
    sim._fe_model_int = model
    with pytest.raises(ValueError, match="require the NLS model"):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], program_width=.2)
    assert sim.accepted == []


def test_mlc_width_requires_a_supported_dwell_setter():
    sim = _FakeFESimulator()
    sim.set_ferroelectric_nls_dwell_time = None
    with pytest.raises(TypeError, match="require set_ferroelectric_nls_dwell_time"):
        run_mlc_program_read_sweep(sim, "gate", [1., 2.], program_width=.2)
    assert sim.voltage == 0.


def test_mlc_rejected_ramp_restores_explicit_dwell_configuration():
    class RejectedSim(TimedSim):
        def run(self, **kwargs):
            result = super().run(**kwargs)
            if kwargs.get("physical_step", True):
                result["target_reached"] = False
            return result

    sim = RejectedSim()
    with pytest.raises(RuntimeError, match="not accepted"):
        _ramp_contact_and_run(sim, "gate", 1., .1, 300, 1e-8, 1, dwell_time=.2)
    assert sim._fe_nls_dt == .1
    assert sim.dwell == .1
    assert sim.voltage == 0.
    assert sim.accepted == []


def gummel_protocol_sim(monkeypatch):
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["converged"]
    monkeypatch.setattr(sim, "set_use_newton", lambda *_: None)
    monkeypatch.setattr(sim, "set_newton_log_space", lambda *_: None)
    return sim


@pytest.mark.parametrize("max_step", [.1, .5, 2.])
def test_mlc_native_dwell_matches_analytic_program_and_read(monkeypatch, max_step):
    sim = gummel_protocol_sim(monkeypatch)
    result = run_mlc_program_read_sweep(
        sim, "right", [4., 6.], read_voltage=2., program_width=.2, read_width=.05,
        max_ramp_step=max_step, max_iter=300, tol=1e-8)
    np.testing.assert_allclose(result["read_polarization"], [
        -PS*(1-math.exp(-.25)), -PS*(1-math.exp(-.5))], atol=1e-12)
    assert result["elapsed_time"] == pytest.approx(.5)
    assert result["completed_segments"] == 4
    assert sim._fe_nls_dt == .05


def test_mlc_native_reset_width_enters_signed_history(monkeypatch):
    sim = gummel_protocol_sim(monkeypatch)
    result = run_mlc_program_read_sweep(
        sim, "right", [4.], reset_voltage=-4., read_voltage=2.,
        reset_width=.4, program_width=.2, read_width=.05,
        max_ramp_step=.5, max_iter=300, tol=1e-8)
    after_reset = PS*(1-math.exp(-.4))
    expected = -PS+(after_reset+PS)*math.exp(-.25)
    np.testing.assert_allclose(result["read_polarization"], [expected], atol=1e-12)
    assert result["elapsed_time"] == pytest.approx(.65)
    assert result["completed_segments"] == 3


def test_mlc_failed_read_restores_program_dwell_and_history(monkeypatch):
    sim = gummel_protocol_sim(monkeypatch)

    def unavailable(*_):
        raise LookupError("read failed")

    with pytest.raises(LookupError, match="read failed"):
        run_mlc_program_read_sweep(
            sim, "right", [4., 6.], read_voltage=2., program_width=.2, read_width=.05,
            current_reader=unavailable, max_iter=300, tol=1e-8)
    assert sim._fe_nls_dt == .2
    assert sim._contact_voltages["right"] == 4.
    np.testing.assert_allclose(sim.results["P"][:, 0], -PS*(1-math.exp(-.2)), atol=1e-12)
    actual = _ramp_contact_and_run(sim, "right", 2., .5, 300, 1e-8, 0, dwell_time=.05)
    np.testing.assert_allclose(actual["P"][:, 0], -PS*(1-math.exp(-.25)), atol=1e-12)


def test_mlc_explicit_dwell_retry_is_consumed_once(monkeypatch):
    sim = gummel_protocol_sim(monkeypatch)
    original_run = sim.run
    attempts = []

    def reject_first(**kwargs):
        result = original_run(**kwargs)
        if kwargs.get("physical_step", True):
            attempts.append(result["P"].copy())
            if len(attempts) == 1:
                result["target_reached"] = False
        return result

    monkeypatch.setattr(sim, "run", reject_first)
    result = _ramp_contact_and_run(sim, "right", 4., .5, 300, 1e-8, 1, dwell_time=.2)
    assert len(attempts) == 2
    np.testing.assert_allclose(result["P"][:, 0], -PS*(1-math.exp(-.2)), atol=1e-12)
    np.testing.assert_allclose(attempts[0], attempts[1], atol=1e-12)
