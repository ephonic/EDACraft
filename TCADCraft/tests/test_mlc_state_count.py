"""Noise-floor censoring cannot establish additional observed MLC levels."""
from itertools import combinations

import numpy as np
import pytest

from tcad.postprocess.fe_loops import extract_mlc_memory_window, run_mlc_program_read_sweep
from test_fefet_validation import _FakeFESimulator


def test_all_censored_samples_have_no_observed_states_or_span():
    result = extract_mlc_memory_window([0., 1., 2.], [0., 1e-12, -1e-11], noise_floor=1e-9)
    assert result["n_states"] == 0
    assert result["n_states_including_censored"] == 1
    assert result["observed_memory_window_decades"] is None
    assert result["n_censored_samples"] == 3
    assert result["signed_window_censored"]
    assert not result["polarity_valid"]
    assert not result["physical_validated"]


def test_censored_floor_is_excluded_from_observed_state_count():
    result = extract_mlc_memory_window(
        [0., 1., 2., 3.], [0., 1e-12, -1e-8, 1e-6], noise_floor=1e-9)
    assert result["n_states"] == 2
    assert result["n_states_including_censored"] == 3
    assert result["memory_window_decades"] == pytest.approx(3.)
    assert result["observed_memory_window_decades"] == pytest.approx(2.)
    assert not result["polarity_valid"]


@pytest.mark.parametrize("currents,expected", [
    ([1e-6, 1e-6, 1e-6], 1),
    ([1e-6, -1e-6, 1e-5], 2),
    ([0., 0., 0.], 0),
])
def test_zero_separation_merges_duplicates_even_with_opposite_sign(currents, expected):
    result = extract_mlc_memory_window(
        [0., 1., 2.], currents, min_state_separation_decades=0., noise_floor=1e-9)
    assert result["n_states"] == expected


def test_exact_noise_floor_remains_measured_and_single_sample_span_is_zero():
    result = extract_mlc_memory_window([0., 1.], [0., 1e-9], noise_floor=1e-9)
    np.testing.assert_array_equal(result["censored_mask"], [True, False])
    assert result["n_states"] == 1
    assert result["observed_memory_window_decades"] == 0.


def test_uncensored_endpoints_allow_polarity_despite_internal_censoring():
    result = extract_mlc_memory_window([2., 0., 1.], [1e-6, 1e-8, 0.], noise_floor=1e-9)
    assert result["polarity_valid"]
    assert not result["signed_window_censored"]
    assert result["polarity"] == "normal"
    assert result["n_states"] == 2


def test_identical_program_voltages_do_not_establish_program_polarity():
    result = extract_mlc_memory_window([1., 1.], [1e-8, 1e-6])
    assert not result["polarity_valid"]


@pytest.mark.parametrize("separation", [0., .5, 1., 2.])
def test_observed_count_matches_independent_subset_oracle(separation):
    currents = np.array([0., 1e-11, 1e-8, 1e-8, 1e-7, 1e-6, -1e-5])
    observed_logs = np.log10(np.abs(currents[np.abs(currents) >= 1e-9]))
    maximum = 0
    for size in range(1, len(observed_logs)+1):
        for subset in combinations(observed_logs, size):
            ordered = sorted(subset)
            if all(b > a and b-a >= separation for a, b in zip(ordered, ordered[1:])):
                maximum = max(maximum, size)
    for order in (np.arange(7), np.arange(6, -1, -1), np.array([3, 0, 6, 1, 4, 2, 5])):
        result = extract_mlc_memory_window(
            np.arange(7)[order], currents[order], separation, noise_floor=1e-9)
        assert result["n_states"] == maximum


@pytest.mark.parametrize("parameter", ["noise_floor", "min_state_separation_decades"])
@pytest.mark.parametrize("value", [True, "0.1", [.1], [.1, .2], 1j, np.nan, np.inf])
def test_state_metric_parameters_require_finite_real_scalars(parameter, value):
    with pytest.raises(ValueError):
        extract_mlc_memory_window([0., 1.], [1e-8, 1e-6], **{parameter: value})


@pytest.mark.parametrize("kwargs", [
    {"min_state_separation_decades": True}, {"min_state_separation_decades": [.1]},
    {"current_noise_floor": True}, {"current_noise_floor": [1e-9]},
])
def test_bad_metric_configuration_is_rejected_before_programming(kwargs):
    sim = _FakeFESimulator()
    with pytest.raises(ValueError):
        run_mlc_program_read_sweep(
            sim, "gate", [1., 2.], current_reader=lambda *_: 1e-6, **kwargs)
    assert sim.voltage == 0.


def test_mlc_driver_reports_uncensored_count_and_preserves_readout_metadata():
    currents = iter([0., -1e-8, 1e-6])
    result = run_mlc_program_read_sweep(
        _FakeFESimulator(), "gate", [0., 1., 2.],
        current_reader=lambda *_: next(currents), current_noise_floor=1e-9)
    assert result["n_states"] == 2
    assert result["n_states_including_censored"] == 3
    assert result["n_censored_samples"] == 1
    np.testing.assert_array_equal(result["raw_read_currents"], [0., -1e-8, 1e-6])
    assert result["completed_read_states"] == 3
    assert result["valid"] and not result["physical_validated"]
