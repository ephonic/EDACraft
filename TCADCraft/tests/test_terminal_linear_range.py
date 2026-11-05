"""Independent scaled polynomial and exact charge references for SI traces."""
from fractions import Fraction
import math

import numpy as np
import pytest

from tcad.postprocess import integrate_terminal_trace, integrate_transient_terminal_history
from tcad.postprocess.terminal_trace import _finite_sum
from test_terminal_trace import trace


def exact_product(*values):
    result = Fraction(1)
    for value in values:
        result *= Fraction(float(value))
    return float(result)


@pytest.mark.parametrize("sign", [-1., 1.])
@pytest.mark.parametrize("voltage,current,duration", [
    (1e200, 1e200, 1e-200), (1e-200, 1e-200, 1e200),
    (1e-300, 1e-100, 1e200), (1e300, 1e100, 1e-100),
    (math.ulp(0.), 1e200, 1e100), (1., math.ulp(0.), 1e200),
])
def test_constant_trace_preserves_representable_charge_and_work(voltage, current, duration, sign):
    data = trace([0., duration], voltage, sign*current)
    # Common voltage isolates terminal energy transfer without requiring an
    # unrepresentably small/large mean net source power.
    data["terminal_voltages_V"]["body"][:] = voltage
    result = integrate_terminal_trace(data, current_kind="total")
    expected_q = exact_product(duration, sign*current)
    expected_w = exact_product(duration, voltage, sign*current)
    assert result["valid"]
    assert result["terminal_charge_C"]["gate"] == pytest.approx(expected_q, rel=1e-13, abs=0.)
    assert result["terminal_supplied_energy_J"]["gate"] == pytest.approx(expected_w, rel=1e-13, abs=0.)
    assert result["terminal_supplied_energy_J"]["body"] == pytest.approx(-expected_w, rel=1e-13, abs=0.)
    assert result["absorbed_energy_J"] == pytest.approx(abs(expected_w), rel=1e-13, abs=0.)
    assert result["returned_energy_J"] == pytest.approx(abs(expected_w), rel=1e-13, abs=0.)
    assert result["supplied_energy_J"] == result["mean_source_power_W"] == 0.


@pytest.mark.parametrize("scales", [(1e200, 1e200, 1e-200),
                                    (1e-200, 1e-200, 1e200),
                                    (1e-300, 1e-100, 1e200)])
@pytest.mark.parametrize("count", [2, 5, 17])
def test_two_power_zero_crossings_match_scaled_polynomial_integrals(scales, count):
    voltage, current, duration = scales
    u = np.linspace(0., 1., count)
    data = trace(duration*u, voltage*(u-.25), current*(u-.75))
    data["terminal_voltages_V"]["body"][:] = data["terminal_voltages_V"]["gate"]
    result = integrate_terminal_trace(data, current_kind="total")
    scale = exact_product(voltage, current, duration)
    # (u-1/4)*(u-3/4): signed=1/48, positive=1/24, negative=-1/48.
    assert result["terminal_supplied_energy_J"]["gate"] == pytest.approx(scale/48, rel=2e-12, abs=0.)
    assert result["terminal_absorbed_energy_J"]["gate"] == pytest.approx(scale/24, rel=2e-12, abs=0.)
    assert result["terminal_returned_energy_J"]["gate"] == pytest.approx(scale/48, rel=2e-12, abs=0.)
    assert result["terminal_charge_C"]["gate"] == pytest.approx(exact_product(-.25, current, duration),
                                                                 rel=2e-12, abs=0.)
    assert result["net_terminal_charge_C"] == result["supplied_energy_J"] == 0.


@pytest.mark.parametrize("count", [2, 3, 5])
def test_subnormal_interval_work_is_summed_before_final_rounding(count):
    data = trace(np.linspace(0., 1., count), math.ulp(0.), 1.)
    result = integrate_terminal_trace(data, current_kind="total")
    assert result["terminal_supplied_energy_J"]["gate"] == math.ulp(0.)
    assert result["absorbed_energy_J"] == math.ulp(0.)
    assert result["mean_source_power_W"] == math.ulp(0.)


def test_reversible_current_charge_sum_can_cancel_intermediate_overflow():
    data = trace(np.arange(6), 0., [1e308, 1e308, 1e308, -1e308, -1e308, -1e308])
    result = integrate_terminal_trace(data, current_kind="total")
    assert result["terminal_charge_C"] == {"gate": 0., "body": 0.}
    assert result["supplied_energy_J"] == 0.


@pytest.mark.parametrize("units", [1, 3, 5, 7])
def test_subnormal_duration_weight_is_not_rounded_before_large_power(units):
    duration = units*math.ulp(0.)
    data = trace([0., duration], 1., 1e300)
    result = integrate_terminal_trace(data, current_kind="total")
    expected = exact_product(duration, 1e300)
    assert result["terminal_charge_C"]["gate"] == expected
    assert result["terminal_supplied_energy_J"]["gate"] == expected
    assert result["mean_source_power_W"] == pytest.approx(1e300, rel=1e-15)


@pytest.mark.parametrize("values", [[1e308, 1e308, -1e308, -1e308, 1.],
                                   [1e308, 1., 1e308, -1e308, -1e308],
                                   [-1e308, -1e308, 1e308, 1e308, 1.]])
def test_finite_sum_retains_small_remainder_after_large_cancellation(values):
    assert _finite_sum(iter(values)) == 1.


def test_native_be_charge_cancellation_uses_the_same_finite_sum_fix():
    initial = dict(valid=True, converged=True, initial_state=True,
                   electrode_charge_available=True, electrode_names=["gate", "body"],
                   electrode_voltages_V=[0., 0.], time_s=0., dt_s=0.)
    history = [initial]
    for index, current in enumerate([1e308, 1e308, -1e308, -1e308], 1):
        history.append(dict(initial, initial_state=False, time_s=float(index), dt_s=1.,
                            total_terminal_current_available=True,
                            electrode_total_currents_A=[current, -current]))
    result = integrate_transient_terminal_history(history)
    assert result["terminal_charge_C"] == {"gate": 0., "body": 0.}
    assert result["supplied_energy_J"] == 0.
    assert not result["energy_balance_validated"]


@pytest.mark.parametrize("case", ["charge_overflow", "energy_overflow", "energy_underflow", "power_underflow"])
def test_unrepresentable_final_quantity_cannot_return_valid_zero(case):
    settings = {"charge_overflow": (0., 1e308, 2.),
                "energy_overflow": (1e308, 1e308, 1.),
                "energy_underflow": (1e-200, 1e-200, 1.),
                "power_underflow": (1e-200, 1e-200, 1e200)}
    voltage, current, duration = settings[case]
    with pytest.raises(ValueError):
        integrate_terminal_trace(trace([0., duration], voltage, current), current_kind="total")
