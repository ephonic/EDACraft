"""Independent capacitor, polynomial, PUND and native pulse-work references."""
from copy import deepcopy
import math

import numpy as np
import pytest

from tcad.postprocess import integrate_terminal_trace, extract_pund_terminal_charge
from tcad.postprocess.fe_loops import run_power_measurement
from tcad.validation.conservation import ConservationTest
from test_fe_measurement_protocols import IdealFE
from test_physical_step_commit import high_level
from test_conservation_balance import pn_device


def trace(times, voltage, current):
    times = np.asarray(times, dtype=float)
    current = np.broadcast_to(current, times.shape).copy()
    return {"times_s": times, "valid": True, "current_kind": "total",
            "terminal_voltages_V": {"gate": np.broadcast_to(voltage, times.shape).copy(),
                                    "body": np.zeros_like(times)},
            "terminal_currents_A": {"gate": current, "body": -current}}


@pytest.mark.parametrize("count", [2, 3, 17])
def test_linear_current_and_voltage_product_integral_is_quadratic(count):
    t = np.linspace(0., 1., count)
    out = integrate_terminal_trace(trace(t, t, t), current_kind="total")
    # V=I=t: integral(I)=1/2 and integral(V*I)=1/3; trapezoidal
    # integration of the endpoint power itself would give 1/2 for 2 samples.
    assert out["terminal_charge_C"]["gate"] == pytest.approx(.5, abs=1e-15)
    assert out["supplied_energy_J"] == pytest.approx(1/3, abs=1e-15)
    assert out["returned_energy_J"] == 0.
    assert out["net_terminal_charge_C"] == 0.
    assert not out["energy_balance_validated"]


def test_source_work_splits_both_internal_power_zero_crossings():
    # P(t)=(t-1/4)*(t-3/4). Signed integral=1/48, positive
    # integral=1/24, returned energy=1/48, despite both endpoint powers >0.
    out = integrate_terminal_trace(trace([0., 1.], [-.25, .75], [-.75, .25]),
                                   current_kind="total")
    assert out["supplied_energy_J"] == pytest.approx(1/48, abs=1e-15)
    assert out["absorbed_energy_J"] == pytest.approx(1/24, abs=1e-15)
    assert out["returned_energy_J"] == pytest.approx(1/48, abs=1e-15)


@pytest.mark.parametrize("charging", [True, False])
def test_linear_capacitor_charge_and_energy_reference(charging):
    capacitance, voltage, duration = 2e-15, 2., 4e-9
    t = np.array([0., .3*duration, duration])
    v = voltage*t/duration if charging else voltage*(1-t/duration)
    current = capacitance*voltage/duration*(1 if charging else -1)
    out = integrate_terminal_trace(trace(t, v, current), current_kind="total")
    sign = 1 if charging else -1
    assert out["terminal_charge_C"]["gate"] == pytest.approx(sign*capacitance*voltage, rel=1e-13, abs=0.)
    energy = .5*capacitance*voltage**2
    assert out["supplied_energy_J"] == pytest.approx(sign*energy, rel=1e-13, abs=0.)
    assert out["absorbed_energy_J"] == pytest.approx(energy if charging else 0., rel=1e-13, abs=0.)
    assert out["returned_energy_J"] == pytest.approx(0. if charging else energy, rel=1e-13, abs=0.)
    state = dict(valid=True, energy_initial=0. if charging else energy,
                 energy_final=energy if charging else 0., energy_dissipated=0.,
                 energy_supplied=out["supplied_energy_J"])
    assert ConservationTest(check_charge=False).run(lambda: state).passed
    # A real 1% work defect must still fail even after exact-charge discharge.
    state["energy_supplied"] *= .99
    assert not ConservationTest(check_charge=False).run(lambda: state).passed


@pytest.mark.parametrize("scale", [1e-30, 1e-15, 1.])
def test_energy_gate_uses_uncancelled_ledger_terms(scale):
    state = dict(valid=True, energy_initial=scale,
                 energy_supplied=-scale*(1+2e-16), energy_final=0.,
                 energy_dissipated=0.)
    check = ConservationTest(check_charge=False)
    assert check.run(lambda: state).passed
    state["energy_supplied"] = -scale*.99
    assert not check.run(lambda: state).passed


def test_multiterminal_source_work_and_gauge_invariance_for_KCL():
    data = trace([0., 1.], [1., 3.], [2., 4.])
    data["terminal_voltages_V"]["body"][:] = 1.
    out = integrate_terminal_trace(data, current_kind="total")
    assert out["supplied_energy_J"] == pytest.approx(10/3)
    # Both sources contribute. Changing the voltage reference cancels when
    # the supplied currents satisfy instantaneous total-terminal KCL.
    for values in data["terminal_voltages_V"].values():
        values += 5.
    shifted = integrate_terminal_trace(data, current_kind="total")
    assert shifted["supplied_energy_J"] == pytest.approx(out["supplied_energy_J"])


@pytest.mark.parametrize("change", ["duplicate_time", "backward_time", "one_sample", "time_nan",
    "time_overflow", "missing_status", "failed_status", "failed_sample", "numeric_status",
    "missing_currents", "current_shape", "current_nan", "voltage_shape", "missing_voltage",
    "one_terminal", "work_overflow", "charge_overflow"])
def test_invalid_or_incomplete_trace_cannot_return_energy(change):
    data = trace([0., 1., 2.], [0., 1., 2.], [1., 2., 3.])
    if change == "duplicate_time": data["times_s"][1] = 0.
    elif change == "backward_time": data["times_s"][1] = -1.
    elif change == "one_sample": data["times_s"] = np.array([0.])
    elif change == "time_nan": data["times_s"][1] = np.nan
    elif change == "time_overflow": data["times_s"] = np.array([-1e308, 0., 1e308])
    elif change == "missing_status": del data["valid"]
    elif change == "failed_status": data["valid"] = False
    elif change == "failed_sample": data["converged"] = [True, False, True]
    elif change == "numeric_status": data["valid"] = [1, 1, 1]
    elif change == "missing_currents": del data["terminal_currents_A"]
    elif change == "current_shape": data["terminal_currents_A"]["gate"] = [1., 2.]
    elif change == "current_nan": data["terminal_currents_A"]["gate"][1] = np.nan
    elif change == "voltage_shape": data["terminal_voltages_V"]["gate"] = 2.
    elif change == "missing_voltage": del data["terminal_voltages_V"]["body"]
    elif change == "one_terminal":
        del data["terminal_voltages_V"]["body"]; del data["terminal_currents_A"]["body"]
    elif change == "work_overflow": data["terminal_voltages_V"]["gate"][:] = 1e308
    elif change == "charge_overflow": data["terminal_currents_A"]["gate"][:] = 1e308
    with pytest.raises(ValueError):
        integrate_terminal_trace(data, current_kind="total")


@pytest.mark.parametrize("kind", [None, "density", "proxy"])
def test_current_components_must_be_declared(kind):
    with pytest.raises(ValueError):
        integrate_terminal_trace(trace([0., 1.], 1., 1.), current_kind=kind)


def pund_traces(switching_charge=8e-15):
    out = {}
    u = np.array([0., .25, .5, .75, 1.])
    shape = np.array([0., 1., 2., 1., 0.])
    width = 1e-6
    for index, label in enumerate(["P", "U", "N", "D"]):
        sign = 1 if label in ("P", "U") else -1
        v = sign*shape
        # The same leakage and reversible background appears in each pair.
        current = 1e-9*v + sign*1e-9*np.array([1., 1., 0., -1., -1.])
        if label in ("P", "N"):
            current += sign*switching_charge/width*shape
        out[label] = trace(index*2*width + u*width, v, current)
    return out


def extract(traces, **kwargs):
    return extract_pund_terminal_charge(traces, terminal="gate", reference_terminal="body", **kwargs)


def test_PUND_total_current_pairs_cancel_shared_background_and_keep_signs():
    out = extract(pund_traces(), electrode_area_m2=2e-14)
    assert out["switching_charge_positive_C"] == pytest.approx(8e-15, rel=1e-12, abs=0.)
    assert out["switching_charge_negative_C"] == pytest.approx(-8e-15, rel=1e-12, abs=0.)
    assert out["switching_polarization_positive_C_per_m2"] == pytest.approx(.4)
    assert out["switching_polarization_negative_C_per_m2"] == pytest.approx(-.4)
    assert out["terminal_current_integrated"]
    assert out["terminal_charge_validated"] is False
    assert out["physical_validated"] is False


def test_no_FE_switching_background_alone_does_not_produce_PUND_charge():
    out = extract(pund_traces(switching_charge=0.))
    assert abs(out["switching_charge_positive_C"]) < 1e-28
    assert abs(out["switching_charge_negative_C"]) < 1e-28
    assert "switching_polarization_positive_C_per_m2" not in out


def test_matched_PUND_waveforms_allow_different_sampling_grids():
    data = pund_traces()
    expected = extract(data)
    for label in ("U", "D"):
        old = data[label]
        t = old["times_s"]
        new_t = np.sort(np.r_[t, (t[:-1]+t[1:])/2])
        data[label] = trace(new_t, np.interp(new_t, t, old["terminal_voltages_V"]["gate"]),
                           np.interp(new_t, t, old["terminal_currents_A"]["gate"]))
    out = extract(data)
    assert out["switching_charge_positive_C"] == pytest.approx(expected["switching_charge_positive_C"], rel=1e-12, abs=0.)
    assert out["switching_charge_negative_C"] == pytest.approx(expected["switching_charge_negative_C"], rel=1e-12, abs=0.)


@pytest.mark.parametrize("change", ["missing_N", "conduction_only", "no_kind", "pulse_width",
    "pulse_shape", "other_source", "wrong_polarity", "zero_bias", "failed_sample"])
def test_PUND_rejects_incomplete_or_mismatched_measurements(change):
    data = pund_traces()
    if change == "missing_N": del data["N"]
    elif change == "conduction_only": data["P"]["current_kind"] = "conduction"
    elif change == "no_kind": del data["P"]["current_kind"]
    elif change == "pulse_width": data["U"]["times_s"] *= 2
    elif change == "pulse_shape": data["U"]["terminal_voltages_V"]["gate"][2] = 3.
    elif change == "other_source":
        for values in data["U"]["terminal_voltages_V"].values(): values += 3.
    elif change == "wrong_polarity": data["N"]["terminal_voltages_V"]["gate"] *= -1
    elif change == "zero_bias": data["P"]["terminal_voltages_V"]["gate"][:] = 0.
    else: data["D"]["valid"] = np.array([True, True, False, True, True])
    with pytest.raises(ValueError):
        extract(data)


@pytest.mark.parametrize("area", [0., -1., np.nan, np.inf, True])
def test_PUND_requires_physical_full_electrode_area(area):
    with pytest.raises(ValueError):
        extract(pund_traces(), electrode_area_m2=area)


class PowerFE(IdealFE):
    def __init__(self):
        super().__init__()
        self._contact_voltages = {"gate": 0., "body": 1.}
        self.currents = {"gate": 2e-9, "body": -2e-9}
        self.calls = 0

    def update_contact(self, name, voltage):
        super().update_contact(name, voltage)
        self._contact_voltages[name] = float(voltage)

    def run(self, **kwargs):
        self.calls += 1
        result = super().run(**kwargs)
        result["n"] = np.full(4, 1e25)
        result["applied_contact_voltages"] = deepcopy(self._contact_voltages)
        return result


def reader(sim, result):
    return sim.currents


@pytest.mark.parametrize("current", [2e-9, -2e-9])
def test_power_estimate_sums_all_sources_and_preserves_returned_energy(current):
    sim = PowerFE()
    sim.currents = {"gate": current, "body": -current}
    out = run_power_measurement(sim, "gate", 3., pulse_width=4e-9, current_reader=reader)
    assert out["energy"] == pytest.approx(2*current*4e-9, rel=1e-13, abs=0.)
    assert out["I_avg"] == current
    assert sim.dwell == 4e-9
    assert sim.calls == 1
    assert out["time_resolved"] is False
    assert out["full_operation_energy_available"] is False
    assert out["physical_validated"] is False
    assert out["current_kind"] == "user_supplied_unspecified_components"


@pytest.mark.parametrize("change", ["missing_currents", "missing_voltage", "nan_current",
    "density_array", "wrong_bias", "invalid_result", "reader_exception", "overflow"])
def test_power_rejection_rolls_back_pulse_instead_of_using_density_proxy(change):
    sim = PowerFE()
    saved = deepcopy(sim.__dict__)
    real_run = sim.run
    def injected(**kwargs):
        result = real_run(**kwargs)
        if change == "missing_voltage": del result["applied_contact_voltages"]
        elif change == "wrong_bias": result["applied_contact_voltages"]["gate"] = 2.
        elif change == "invalid_result": result["valid"] = False
        return result
    sim.run = injected
    def failing_reader(sim, result):
        if change == "reader_exception": raise RuntimeError("no current data")
        if change == "missing_currents": return {"gate": 2e-9}
        if change == "nan_current": return {"gate": np.nan, "body": 0.}
        if change == "density_array": return {"gate": np.ones(4), "body": 0.}
        if change == "overflow": return {"gate": 1e308, "body": 0.}
        return reader(sim, result)
    with pytest.raises(RuntimeError) as error:
        run_power_measurement(sim, "gate", 3., pulse_width=4e-9, current_reader=failing_reader)
    assert error.value.completed_segments == 0
    assert sim.memory == saved["memory"]
    assert sim.dwell == saved["dwell"]
    assert sim._contact_voltages == saved["_contact_voltages"]
    assert sim.calls == 0


@pytest.mark.parametrize("kwargs", [{}, {"cross_section_m2": 0.}, {"cross_section_m2": -1.},
    {"cross_section_m2": np.nan}, {"current_reader": 3},
    {"cross_section_m2": 1., "current_reader": reader}])
def test_power_requires_unambiguous_absolute_current_source_before_mutation(kwargs):
    sim = PowerFE()
    with pytest.raises(ValueError):
        run_power_measurement(sim, "gate", 3., **kwargs)
    assert sim.calls == 0
    assert sim.voltage == 0.


def test_native_PN_power_estimate_has_absolute_area_scaling():
    outputs = []
    for area in (1e-14, 2e-14):
        sim = pn_device()
        out = run_power_measurement(sim, "p_contact", .05, pulse_width=3e-9,
                                   cross_section_m2=area, max_iter=200, tol=1e-9)
        assert out["energy"] != 0.
        assert out["energy"] == pytest.approx(.05*out["I_avg"]*3e-9, rel=1e-12, abs=0.)
        assert out["current_kind"] == "conduction"
        assert out["time_resolved"] is False
        outputs.append(out)
    assert outputs[1]["energy"] == pytest.approx(2*outputs[0]["energy"], rel=1e-12, abs=0.)


def test_native_power_current_failure_restores_hidden_FE_memory_and_bias():
    sim, reference = high_level(), high_level()
    for item in (sim, reference):
        assert item.run(max_iter=300, tol=1e-8)["converged"]
    def unavailable(sim, result):
        raise RuntimeError("instrument unavailable")
    with pytest.raises(RuntimeError):
        run_power_measurement(sim, "right", 4., pulse_width=.2,
                              current_reader=unavailable, max_iter=300, tol=1e-8)
    assert sim._contact_voltages["right"] == 0.
    assert sim._fe_nls_dt == .1
    for voltage in (4., -4., 4.):
        sim.update_contact("right", voltage)
        reference.update_contact("right", voltage)
        np.testing.assert_allclose(sim.run(physical_step=True)["P"],
                                   reference.run(physical_step=True)["P"], atol=1e-12)
