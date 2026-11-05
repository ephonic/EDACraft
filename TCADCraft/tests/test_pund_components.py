"""Model PUND component diagnostics: false FE signals and independent references."""
from copy import deepcopy
import math

import numpy as np
import pytest

from tcad.postprocess import (audit_transient_pund_components, run_transient_pund,
                              extract_pund_terminal_charge)
from test_transient_pund import device, options
from test_transient_selfconsistent import central_cell, bernoulli, QE, EPS, VT
from test_transient_voltage_waveforms import scalar_driven_step
from test_terminal_trace import trace


def pair_reference(values):
    a, b = values["P"]-values["U"], values["N"]-values["D"]
    return {"positive": a, "negative": b, "magnitude": .5*(abs(a)+abs(b))}


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("dt", [.13e-10, .7e-10])
def test_classical_carrier_relaxation_is_not_polarization_switching(axis, log_space, dt):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True)
    clock, volts, windows = [0.], [0.], {}
    for label, amplitude in zip(("preset", "P", "U", "N", "D"), (-.002, .002, .002, -.002, -.002)):
        start = clock[-1]
        clock.extend([start+.3e-10, start+1.3e-10, start+1.7e-10, start+1.9e-10])
        volts.extend([amplitude, amplitude, 0., 0.])
        if label != "preset": windows[label] = (start, clock[-3])
    sim.set_transient_voltage_waveforms(clock, {2: volts})
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(clock[-1])
    history = sim.solve_transient()
    names = history[0]["electrode_names"]
    out = audit_transient_pund_components(history, windows, terminal=names[1], reference_terminal=names[0])
    expected_i, dielectric_i = [0.], [0.]
    previous_phi = previous_v = None
    for state in history:
        v = np.interp(state["time_s"], clock, volts)
        phi, nn, pp = scalar_driven_step(nn, pp, state["dt_s"], x, v)
        np.testing.assert_allclose(state["phi"], [0., phi, v], atol=1e-12, rtol=1e-8)
        if state["dt_s"]:
            u = (v-phi)/VT
            j = QE*VT*1e16/(x[2]-x[1])*(.1*(bernoulli(u)-nn*bernoulli(-u))
                  +.05*(pp*bernoulli(u)-bernoulli(-u)))
            # Full transverse area=1e-12 m2; upper-terminal sign is -J.
            expected_i.append(-1e-12*j)
            dielectric_i.append(1e-12*EPS*((v-previous_v)-(phi-previous_phi))/
                                ((x[2]-x[1])*state["dt_s"]))
            assert state["electrode_conduction_currents_A"][1] == pytest.approx(expected_i[-1], rel=1e-7, abs=1e-25)
        previous_phi, previous_v = phi, v
    expected_charge = {}
    times = np.array([s["time_s"] for s in history])
    for kind, currents in (("conduction", expected_i), ("dielectric", dielectric_i)):
        expected_charge[kind] = {}
        for label, (start, end) in windows.items():
            expected_charge[kind][label] = math.fsum(s["dt_s"]*currents[k]
                    for k, s in enumerate(history) if start < times[k] <= end)
        expected_pair = pair_reference(expected_charge[kind])
        for key, value in expected_pair.items():
            assert out["component_pair_charge_C"][kind][key] == pytest.approx(value, rel=1e-6, abs=1e-29)
    assert out["valid"] and out["component_balance_validated"]
    assert out["component_pair_charge_C"]["total"]["magnitude"] > 1e-25
    assert out["component_pair_charge_C"]["conduction"]["magnitude"] > 1e-25
    assert out["modeled_conduction_and_dielectric_removed_pair_charge_C"] == {"positive": 0., "negative": 0., "magnitude": 0.}
    assert not out["leakage_cancellation_validated"] and not out["physical_validated"]


@pytest.mark.parametrize("dt", [.11e-9, .7e-9])
def test_nls_direct_component_matches_gauss_polarization_increment(dt):
    out = run_transient_pund(device(), "right", "left", .01,
                **options(dt=dt), audit_components=True, electrode_area_m2=1.)
    states = {s["time_s"]: s for s in out["history"]}
    charge = {}
    for label, (start, end) in out["pulse_windows_s"].items():
        charge[label] = -(states[end]["P"][0]-states[start]["P"][0])
        assert out["component_reports"]["polarization"]["pulse_charge_C"][label] == pytest.approx(charge[label], rel=1e-11)
    expected = pair_reference(charge)
    assert out["modeled_conduction_and_dielectric_removed_pair_charge_C"] == pytest.approx(expected, rel=1e-11)
    assert out["component_pair_charge_C"]["conduction"]["magnitude"] == 0.
    assert out["component_pair_charge_C"]["dielectric"]["magnitude"] < 1e-15
    assert out["valid"] and out["component_balance_validated"]


@pytest.fixture
def native_output():
    return run_transient_pund(device(), "right", "left", .01, **options())


@pytest.mark.parametrize("field", ["total", "displacement", "conduction", "dielectric", "polarization"])
@pytest.mark.parametrize("electrode", [0, 1])
def test_forged_component_fails_interval_audit_at_every_electrode(native_output, field, electrode):
    history = deepcopy(native_output["history"])
    history[2][f"electrode_{field}_currents_A"][electrode] += 1e8
    out = audit_transient_pund_components(history, native_output["pulse_windows_s"], terminal="x_max", reference_terminal="x_min")
    assert not out["valid"] and not out["component_balance_validated"]
    assert out["max_component_relative_residual"] > 1e-8


@pytest.mark.parametrize("kind", ["conduction", "displacement", "dielectric", "polarization"])
@pytest.mark.parametrize("issue", ["missing", "nonfinite", "shape"])
def test_missing_or_invalid_components_are_not_inferred_from_total(native_output, kind, issue):
    history = deepcopy(native_output["history"])
    key = f"electrode_{kind}_currents_A"
    if issue == "missing": del history[2][key]
    elif issue == "nonfinite": history[2][key][0] = np.nan
    else: history[2][key] = [0.]
    with pytest.raises(ValueError):
        audit_transient_pund_components(history, native_output["pulse_windows_s"], terminal="x_max", reference_terminal="x_min")


@pytest.mark.parametrize("kwargs", [{"rtol": True}, {"rtol": 0.}, {"rtol": 1.}, {"rtol": [1e-8]},
    {"atol_A": -1.}, {"atol_A": np.inf}, {"atol_A": True}])
def test_invalid_audit_tolerances_rejected(native_output, kwargs):
    with pytest.raises(ValueError):
        audit_transient_pund_components(native_output["history"], native_output["pulse_windows_s"],
                                       terminal="x_max", reference_terminal="x_min", **kwargs)


@pytest.mark.parametrize("value", [1, "true", None])
def test_driver_component_audit_enable_requires_boolean(value):
    sim = device()
    with pytest.raises(ValueError):
        run_transient_pund(sim, "right", "left", .01, **options(), audit_components=value)
    assert sim.results is None and sim._transient_contact_waveforms is None


def test_direct_polarization_integral_survives_a_large_conduction_background(native_output):
    history = deepcopy(native_output["history"])
    factor = 1e-50
    for state in history[1:]:
        state["electrode_polarization_currents_A"] *= factor
        state["electrode_displacement_currents_A"] = (state["electrode_dielectric_currents_A"]
                                                       +state["electrode_polarization_currents_A"])
        v = state["electrode_voltages_V"][1]
        state["electrode_conduction_currents_A"] = np.array([-v, v])*1e100
        state["electrode_total_currents_A"] = (state["electrode_conduction_currents_A"]
                                                +state["electrode_displacement_currents_A"])
    out = audit_transient_pund_components(history, native_output["pulse_windows_s"], terminal="x_max", reference_terminal="x_min")
    original = audit_transient_pund_components(native_output["history"], native_output["pulse_windows_s"],
                                              terminal="x_max", reference_terminal="x_min")
    expected = {key: value*factor for key, value in original["component_pair_charge_C"]["polarization"].items()}
    assert out["modeled_conduction_and_dielectric_removed_pair_charge_C"] == pytest.approx(expected, rel=1e-12, abs=0.)
    assert out["component_pair_charge_C"]["polarization"]["magnitude"] > 0.
    assert out["valid"] and not out["physical_validated"]
    # Synthetic export stress, not a modeled device at this conduction scale.
    for state in history[1:]:
        if state["electrode_voltages_V"][1]:
            np.testing.assert_array_equal(state["electrode_total_currents_A"], state["electrode_conduction_currents_A"])


def small_external_pulses(charge, both=True):
    result = {}
    for label in ("P", "U", "N", "D"):
        sign = 1. if label in ("P", "U") else -1.
        current = sign*charge if label == "P" or (label == "N" and both) else 0.
        result[label] = dict(trace([0., 1.], sign, current), current_kind="total")
    return result


def test_subnormal_pund_magnitude_rounds_only_after_combining_both_polarities():
    out = extract_pund_terminal_charge(small_external_pulses(math.ulp(0.)),
                terminal="gate", reference_terminal="body", electrode_area_m2=1.)
    assert out["switching_charge_magnitude_C"] == math.ulp(0.)
    assert out["switching_polarization_magnitude_C_per_m2"] == math.ulp(0.)


def test_unrepresentable_nonzero_pund_magnitude_cannot_be_valid_zero():
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(small_external_pulses(math.ulp(0.), both=False),
                                    terminal="gate", reference_terminal="body")


@pytest.mark.parametrize("area", [1e200, 1e300])
def test_nonzero_area_normalized_pund_charge_cannot_underflow_to_valid_zero(area):
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(small_external_pulses(1e-200),
                terminal="gate", reference_terminal="body", electrode_area_m2=area)


@pytest.mark.parametrize("flag", [False, 1, None])
def test_unavailable_or_ambiguous_component_scope_is_rejected(native_output, flag):
    history = deepcopy(native_output["history"])
    history[2]["displacement_current_available"] = flag
    with pytest.raises(ValueError, match="scope"):
        audit_transient_pund_components(history, native_output["pulse_windows_s"], terminal="x_max", reference_terminal="x_min")


def test_overflowing_signed_pund_difference_raises_value_error():
    pulses = {}
    for label, sign, current in (("P", 1., 1e308), ("U", 1., -1e308),
                                 ("N", -1., -1e308), ("D", -1., 1e308)):
        pulses[label] = dict(trace([0., 1.], sign*1e-308, current), current_kind="total")
    with pytest.raises(ValueError, match="difference"):
        extract_pund_terminal_charge(pulses, terminal="gate", reference_terminal="body")
