"""Terminal trace and power entry points reject coercion-prone SI inputs."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.postprocess.terminal_trace import integrate_terminal_trace
from tcad.postprocess.fe_loops import run_power_measurement
from test_fefet_validation import _FakeFESimulator


def trace(times=None, currents=None, voltages=None):
    return {
        "times_s": np.array([0., 1.] if times is None else times),
        "valid": True,
        "terminal_currents_A": currents or {"a": [0., 1.], "b": [0., -1.]},
        "terminal_voltages_V": voltages or {"a": [0., 1.], "b": [0., 0.]},
    }


@pytest.mark.parametrize("name", ["times_s", "terminal_currents_A", "terminal_voltages_V"])
@pytest.mark.parametrize("kind", ["complex", "string", "bool", "object"])
def test_trace_rejects_float_coercion_for_physical_arrays(name, kind):
    data = trace()
    value = np.array([0., 1.])
    if kind == "complex":
        value = value.astype(complex) + 1j
    elif kind == "string":
        value = value.astype(str)
    elif kind == "bool":
        value = value.astype(bool)
    else:
        value = value.astype(object)
    if name == "times_s":
        data[name] = value
    else:
        data[name] = {"a": value, "b": value}
    with pytest.raises(ValueError):
        integrate_terminal_trace(data, current_kind="total")


@pytest.mark.parametrize("current_kind", [None, [], 1, np.array("total")])
def test_trace_current_kind_is_a_declared_string(current_kind):
    with pytest.raises(ValueError):
        integrate_terminal_trace(trace(), current_kind=current_kind)


@pytest.mark.parametrize("value", [True, "1e-9", [1e-9], 1j, np.nan, np.inf])
def test_power_entry_scalar_inputs_reject_before_solve(value):
    sim = _FakeFESimulator()
    calls = []
    original_run = sim.run
    sim.run = lambda **kwargs: (calls.append(kwargs), original_run(**kwargs))[1]
    with pytest.raises(ValueError):
        run_power_measurement(sim, "gate", value, pulse_width=.1,
                              current_reader=lambda *_: {"gate": 1e-6, "ground": -1e-6})
    assert calls == []
    assert sim.voltage == 0.
    assert sim.qot_history == []


@pytest.mark.parametrize("name,value", [
    ("pulse_width", True), ("pulse_width", "0.1"), ("pulse_width", [0.1]),
    ("cross_section_m2", True), ("cross_section_m2", "1e-12"),
    ("cross_section_m2", [1e-12]), ("max_iter", True), ("max_iter", 0),
    ("max_iter", 1.5), ("tol", "1e-8"), ("tol", [1e-8]), ("tol", 0.),
])
def test_power_entry_protocol_parameters_reject_before_solve(name, value):
    sim = _FakeFESimulator()
    options = {"current_reader": lambda *_: {"gate": 1e-6, "ground": -1e-6}}
    options[name] = value
    calls = []
    original_run = sim.run
    sim.run = lambda **kwargs: (calls.append(kwargs), original_run(**kwargs))[1]
    with pytest.raises(ValueError):
        run_power_measurement(sim, "gate", 1., **options)
    assert calls == []


@pytest.mark.parametrize("value", [True, "1e-6", [1e-6], 1j, np.nan, np.inf])
def test_power_callback_currents_are_strict_scalars(value):
    sim = _FakeFESimulator()
    before = deepcopy(sim.__dict__)
    with pytest.raises((ValueError, RuntimeError)):
        run_power_measurement(
            sim, "gate", 1., pulse_width=.1,
            current_reader=lambda *_: {"gate": value, "ground": -1e-6})
    assert sim.voltage == before["voltage"]
    assert sim.qot_history == before["qot_history"]


@pytest.mark.parametrize("value", [True, "0", [0], 1j, np.nan, np.inf])
def test_power_callback_voltages_are_strict_scalars(value):
    sim = _FakeFESimulator()
    def reader(*args):
        result = args[1]
        result["applied_contact_voltages"] = {"gate": value, "ground": 0.}
        return {"gate": 1e-6, "ground": -1e-6}
    with pytest.raises((ValueError, RuntimeError)):
        run_power_measurement(sim, "gate", 1., pulse_width=.1, current_reader=reader)
    assert sim.voltage == 0.


def test_power_callback_complex_result_cannot_commit_physical_pulse():
    sim = _FakeFESimulator()
    original = sim.run
    def run(**kwargs):
        result = original(**kwargs)
        result["phi"] = result["phi"].astype(complex) + 1j
        return result
    sim.run = run
    with pytest.raises(RuntimeError):
        run_power_measurement(sim, "gate", 1., pulse_width=.1,
                              current_reader=lambda *_: {"gate": 1e-6, "ground": -1e-6})
    assert sim.voltage == 0.
    assert sim.qot_history == []
