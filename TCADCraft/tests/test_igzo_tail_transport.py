import math

import pytest

from tcad.material import (
    IgzoTailOccupancyTransport,
    igzo_tail_calibration,
    igzo_tail_calibrations,
    igzo_tail_transport,
)


def test_tail_transport_defaults_match_calibrated_shape():
    model = IgzoTailOccupancyTransport()

    assert model.factor(-1.0) == pytest.approx(0.15, rel=0.0, abs=1e-6)
    assert model.factor(4.0) == pytest.approx(1.0, rel=0.0, abs=1e-6)
    assert model.factor(model.center_voltage_V) == pytest.approx(0.575)
    assert model.factor(0.5) < model.factor(1.0) < model.factor(2.0)


def test_tail_transport_current_correction_is_explicit():
    model = IgzoTailOccupancyTransport(minimum_factor=0.2, center_voltage_V=1.0, width_V=0.2)
    raw = 1.0e-12

    assert model.corrected_current_A_per_um(raw, -2.0) == pytest.approx(0.2e-12)
    assert model.corrected_current_A_per_um(raw, 3.0) == pytest.approx(raw)


def test_tail_transport_high_gate_factor_is_explicit_selector():
    model = IgzoTailOccupancyTransport(
        minimum_factor=0.2,
        center_voltage_V=1.0,
        width_V=0.1,
        high_gate_factor=0.5,
    )

    assert model.factor(-1.0) == pytest.approx(0.2, abs=1e-6)
    assert model.factor(3.0) == pytest.approx(0.5, abs=1e-6)


def test_sentaurus_tail_selector_returns_accepted_t400_kernel():
    calibration = igzo_tail_calibration("igzo_t10_T400_vd0p1", require_accepted=True)
    model = calibration.transport()

    assert calibration.accepted
    assert calibration.high_gate_factor == pytest.approx(0.25)
    assert calibration.rmse_log_current_decades == pytest.approx(0.0527970082)
    assert model.factor(0.0) == pytest.approx(0.05, abs=1e-6)
    assert model.factor(4.0) == pytest.approx(0.25, abs=1e-6)


def test_sentaurus_tail_selector_marks_t250_as_floor_aware_acceptance():
    calibration = igzo_tail_calibration("igzo_t10_T250_vd0p1", require_accepted=True)
    model = calibration.transport()

    assert calibration.accepted
    assert calibration.acceptance_mode == "floor_aware_log_current"
    assert calibration.log_current_floor_A_per_um == pytest.approx(1.0e-36)
    assert calibration.rmse_log_current_decades == pytest.approx(0.0337893986)
    assert calibration.max_abs_log_current_error_decades == pytest.approx(0.0743968432)
    assert calibration.raw_max_abs_log_current_error_decades == pytest.approx(0.7105561319)
    assert model.factor(0.0) == pytest.approx(0.3001134947, rel=1e-6)
    assert model.factor(4.0) == pytest.approx(2.8, abs=1e-6)


def test_sentaurus_tail_selector_returns_t20_thick_channel_kernel():
    calibration = igzo_tail_calibration("igzo_t20_T300_vd0p1", require_accepted=True)
    model = calibration.transport()

    assert calibration.accepted
    assert calibration.acceptance_mode == "direct_log_current"
    assert calibration.rmse_log_current_decades == pytest.approx(0.0113268981)
    assert calibration.max_abs_log_current_error_decades == pytest.approx(0.0167287089)
    assert model.factor(0.0) == pytest.approx(0.15, abs=1e-6)
    assert model.factor(4.0) == pytest.approx(1.0, abs=1e-6)


def test_sentaurus_tail_selector_returns_t5_thin_channel_kernel():
    calibration = igzo_tail_calibration("igzo_t5_T300_vd0p1", require_accepted=True)
    model = calibration.transport()

    assert calibration.accepted
    assert calibration.acceptance_mode == "direct_log_current"
    assert calibration.rmse_log_current_decades == pytest.approx(0.0176132172)
    assert calibration.max_abs_log_current_error_decades == pytest.approx(0.0224585594)
    assert model.factor(0.0) == pytest.approx(0.15, abs=1e-6)
    assert model.factor(4.0) == pytest.approx(1.0, abs=1e-6)


def test_sentaurus_tail_selector_returns_vd5_high_drain_kernel():
    calibration = igzo_tail_calibration("igzo_t10_T300_vd5p0", require_accepted=True)
    model = calibration.transport()

    assert calibration.accepted
    assert calibration.acceptance_mode == "direct_log_current"
    assert calibration.rmse_log_current_decades == pytest.approx(0.0234048905)
    assert calibration.max_abs_log_current_error_decades == pytest.approx(0.0338311131)
    assert model.factor(0.0) == pytest.approx(0.1500031676, rel=1e-6)
    assert model.factor(4.0) == pytest.approx(1.0, abs=1e-6)


def test_sentaurus_tail_selector_rejects_unknown_branch_when_required():
    with pytest.raises(KeyError):
        igzo_tail_transport("igzo_missing_branch", require_accepted=True)


def test_sentaurus_tail_calibration_list_is_stable_and_all_accepted():
    calibrations = igzo_tail_calibrations(accepted_only=True)
    branches = [calibration.branch for calibration in calibrations]

    assert branches == sorted(branches)
    assert branches == [
        "igzo_t10_T250_vd0p1",
        "igzo_t10_T300_vd0p1",
        "igzo_t10_T300_vd5p0",
        "igzo_t10_T400_vd0p1",
        "igzo_t20_T300_vd0p1",
        "igzo_t5_T300_vd0p1",
    ]
    assert all(calibration.accepted for calibration in calibrations)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_factor": 0.0},
        {"high_gate_factor": 0.0},
        {"width_V": 0.0},
        {"width_V": -0.1},
        {"center_voltage_V": math.inf},
    ],
)
def test_tail_transport_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        IgzoTailOccupancyTransport(**kwargs)


def test_tail_transport_rejects_nonfinite_inputs():
    model = IgzoTailOccupancyTransport()
    with pytest.raises(ValueError):
        model.factor(math.nan)
    with pytest.raises(ValueError):
        model.corrected_current_A_per_um(math.inf, 1.0)
