"""Pulse-width experiments preserve each plateau and validate before running."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.postprocess.fe_loops import run_pulse_width_sweep, ReliabilityStepError
from test_fe_measurement_protocols import IdealFE
from test_physical_step_commit import high_level


@pytest.mark.parametrize("name", ["V_pulse", "fe_thickness", "saturation_polarization",
                                  "max_iter", "tol"])
@pytest.mark.parametrize("value", [True, "0.1", [0.1], 1j, np.nan, np.inf])
def test_protocol_scalar_rejection_precedes_any_solve(name, value):
    sim = IdealFE()
    options = dict(V_pulse=1., fe_thickness=1e-8, pulse_widths=[.1],
                   saturation_polarization=.2)
    options[name] = value
    calls = []
    original_run = sim.run

    def run(**kwargs):
        calls.append(kwargs)
        return original_run(**kwargs)

    sim.run = run
    with pytest.raises(ValueError):
        run_pulse_width_sweep(sim, "gate", **options)
    assert calls == []
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("widths", [[True], ["0.1"], np.array([.1+1j]),
                                    np.array([.1], dtype=object)])
def test_width_array_is_validated_before_conversion(widths):
    sim = IdealFE()
    calls = []
    original_run = sim.run

    def run(**kwargs):
        calls.append(kwargs)
        return original_run(**kwargs)

    sim.run = run
    with pytest.raises(ValueError):
        run_pulse_width_sweep(sim, "gate", 1., 1e-8,
                             pulse_widths=widths, saturation_polarization=.2)
    assert calls == []


@pytest.mark.parametrize("reference", [True, [.2], "0.2"])
def test_inherited_reference_must_also_be_real_scalar(reference):
    sim = IdealFE()
    sim._fe_base_ps = reference
    calls = []
    sim.run = lambda **kwargs: calls.append(kwargs)
    with pytest.raises(ValueError, match="reference"):
        run_pulse_width_sweep(sim, "gate", 1., 1e-8, pulse_widths=[.1])
    assert calls == []


class PlateauPair(IdealFE):
    def __init__(self, positive=1., negative=.25, reuse=False):
        super().__init__(susceptibility=0.)
        self.positive, self.negative, self.reuse = positive, negative, reuse
        self.shared = {}

    def run(self, **kwargs):
        result = super().run(**kwargs)
        result["P"][:, 2] = self.positive if self.voltage > 0 else -self.negative
        if self.reuse:
            self.shared.clear()
            self.shared.update(result)
            return self.shared
        return result


@pytest.mark.parametrize("reuse", [False, True])
def test_each_plateau_is_captured_before_next_pulse(reuse):
    sim = PlateauPair(reuse=reuse)
    output = run_pulse_width_sweep(sim, "gate", 1., 1e-8, pulse_widths=[.1, .2],
                                   saturation_polarization=1.)
    np.testing.assert_allclose(output["Ps"], [.625, .625])
    np.testing.assert_allclose(output["memory_window"], [1.25, 1.25])
    np.testing.assert_allclose(output["program_polarization"], [1., 1.])
    np.testing.assert_allclose(output["erase_polarization"], [-.25, -.25])
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("voltage,positive,negative,reference,expected_ps,expected_window", [
    (1., 1e308, 1e308, 1e308, 1e308, 2.),
    (1e308, 1., .25, 1e308, .625, 1.25),
    (1e308, 5e-324, 5e-324, 1e308, 5e-324, 1e-323),
    (1., 0., 0., .2, 0., 0.),
    (8.868462055499348e307, .8881887315025601, .8881887315025601,
     .8763306607449259, .8881887315025601, np.finfo(float).max),
])
def test_finite_derived_metrics_do_not_overflow_intermediate_arithmetic(
        voltage, positive, negative, reference, expected_ps, expected_window):
    output = run_pulse_width_sweep(PlateauPair(positive, negative), "gate", voltage, 1e-8,
                                   pulse_widths=[.1], saturation_polarization=reference)
    np.testing.assert_allclose(output["Ps"], [expected_ps], rtol=3e-15, atol=0.)
    np.testing.assert_allclose(output["memory_window"], [expected_window], rtol=3e-15, atol=0.)


@pytest.mark.parametrize("voltage,plateau,reference", [
    (1e308, 1., 5e-324),
    (5e-324, 5e-324, 1e308),
])
def test_unrepresentable_metric_rejects_and_restores_whole_experiment(voltage, plateau, reference):
    sim = PlateauPair(plateau, plateau)
    before = deepcopy(sim.__dict__)
    with pytest.raises(ReliabilityStepError) as error:
        run_pulse_width_sweep(sim, "gate", voltage, 1e-8,
                             pulse_widths=[.1], saturation_polarization=reference)
    assert error.value.experiment_index == 0
    assert error.value.completed_experiments == 0
    assert error.value.experiment_rolled_back
    assert sim.memory == before["memory"]
    assert sim.voltage == before["voltage"]
    assert sim.dwell == before["dwell"]


def test_width_plan_is_owned_and_callback_cannot_change_next_candidate():
    widths = np.array([.1, .2])
    sim = PlateauPair()
    original_run = sim.run
    dwells = []

    def run(**kwargs):
        dwells.append(sim.dwell)
        widths[1] = -.5
        return original_run(**kwargs)

    sim.run = run
    output = run_pulse_width_sweep(sim, "gate", 1., 1e-8, pulse_widths=widths,
                                   saturation_polarization=1.)
    np.testing.assert_allclose(dwells, [.1, .1, .2, .2])
    np.testing.assert_allclose(output["pulse_widths"], [.1, .2])
    output["pulse_widths"][0] = .7
    assert widths[0] == .1


@pytest.mark.parametrize("widths,failed_index", [([.5], 0), ([.01, .5], 1)])
def test_native_metric_failure_restores_entry_even_after_completed_candidate(widths, failed_index):
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["valid"]
    before = deepcopy(sim.results)
    contacts = deepcopy(sim._contact_voltages)
    guess = deepcopy(sim._accepted_initial_guess)
    dwell = sim._fe_nls_dt
    with pytest.raises(ReliabilityStepError) as error:
        run_pulse_width_sweep(sim, "right", 4., 40e-9, pulse_widths=widths,
                             saturation_polarization=1e-309, max_iter=300, tol=1e-8)
    assert error.value.experiment_index == failed_index
    assert error.value.completed_experiments == failed_index
    assert error.value.experiment_rolled_back
    assert error.value.completed_segments == 1
    assert error.value.elapsed_time == pytest.approx(widths[failed_index])
    assert sim._contact_voltages == contacts
    assert sim._fe_nls_dt == dwell
    for actual, expected in zip(sim._accepted_initial_guess, guess):
        np.testing.assert_array_equal(actual, expected)
    for key in ("phi", "P"):
        np.testing.assert_array_equal(sim.results[key], before[key])
    # Check native charge/history as well as the Python result cache.
    retry = sim.run(max_iter=300, tol=1e-8, physical_step=False)
    for key in ("phi", "P"):
        np.testing.assert_allclose(retry[key], before[key], atol=1e-12)
