"""Native PUND: independent capacitor and exponential NLS charge references."""
import math

import numpy as np
import pytest

from tcad.postprocess import run_transient_pund, extract_transient_pund_charge, PUNDTransientError
from test_physical_step_commit import high_level, PS


def device(fe=True):
    sim = high_level()
    sim._sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim._sim.set_ferroelectric_enabled(fe)
    sim._sim.set_ferroelectric_nls(1e-9, 0., 1e-15)
    return sim


def options(**overrides):
    result = dict(pulse_width=1e-9, rise_time=.3e-9, fall_time=.4e-9,
                  delay_time=.2e-9, dt=.17e-9, max_iter=80, tol=1e-10)
    result.update(overrides)
    return result


@pytest.mark.parametrize("dt", [.11e-9, .7e-9, 2e-9])
@pytest.mark.parametrize("delay", [0., .2e-9])
def test_linear_capacitor_pund_cancels_repeat_charge_and_closes_full_cycle(dt, delay):
    sim = device(fe=False)
    out = run_transient_pund(sim, "right", "left", .01, **options(dt=dt, delay_time=delay))
    cap = 9*8.854187817e-12/40e-9
    for label in ("P", "U", "N", "D"):
        expected = cap*.01*(1 if label in ("P", "U") else -1)
        assert out["pulse_charge_C"][label] == pytest.approx(expected, rel=1e-12)
    assert out["switching_charge_magnitude_C"] < cap*.01*1e-12
    assert abs(out["sequence_integral"]["supplied_energy_J"]) < cap*.01**2*1e-12
    assert abs(out["sequence_integral"]["terminal_charge_C"]["x_max"]) < cap*.01*1e-12
    assert out["history"][0]["time_s"] == 0.
    np.testing.assert_allclose(out["history"][-1]["time_s"], 5*(1e-9+.3e-9+.4e-9+delay), rtol=1e-15)
    assert out["terminal_current_integrated"] and not out["leakage_cancellation_validated"]
    assert not out["physical_validated"] and not out["energy_balance_validated"]
    assert sim._transient_contact_waveforms is None
    assert sim._contact_voltages == {"left": 0., "right": 0.}


@pytest.mark.parametrize("dt", [.11e-9, .7e-9])
@pytest.mark.parametrize("delay", [0., .2e-9])
def test_nls_integrated_charge_matches_exponential_and_gauss_reference(dt, delay):
    sim = device()
    out = run_transient_pund(sim, "right", "left", .01,
                             electrode_area_m2=1., **options(dt=dt, delay_time=delay))
    cap = 9*8.854187817e-12/40e-9
    ps = [0.]
    for state in out["history"][1:]:
        voltage = np.interp(state["time_s"], out["waveform_times_s"], out["waveform_voltages_V"])
        p = ps[-1]
        if voltage != 0.:
            target = -np.sign(voltage)*PS
            p = target+(p-target)*math.exp(-state["dt_s"]/1e-9)
        ps.append(p)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], p, atol=1e-13)
    times = [s["time_s"] for s in out["history"]]
    expected = {}
    for label, (start, end) in out["pulse_windows_s"].items():
        a, b = times.index(start), times.index(end)
        v = .01*(1 if label in ("P", "U") else -1)
        expected[label] = cap*v-(ps[b]-ps[a])
        assert out["pulse_charge_C"][label] == pytest.approx(expected[label], rel=1e-11)
    assert out["switching_charge_positive_C"] == pytest.approx(expected["P"]-expected["U"], rel=1e-11)
    assert out["switching_charge_negative_C"] == pytest.approx(expected["N"]-expected["D"], rel=1e-11)
    assert out["switching_polarization_positive_C_per_m2"] == out["switching_charge_positive_C"]
    assert out["extraction_kind"] == "matched_native_backward_euler_terminal_integrals"


@pytest.mark.parametrize("field,value", [("rise_time", 0.), ("fall_time", 0.),
    ("pulse_width", True), ("dt", [1e-9]), ("delay_time", -1.), ("fe_gamma", -1.),
    ("max_iter", 0), ("tol", np.nan), ("electrode_area_m2", 0.),
    ("pulse_width", 1e308), ("rise_time", math.ulp(0.))])
def test_invalid_protocol_rejected_before_configuration_or_state_mutation(field, value):
    sim = device()
    with pytest.raises(ValueError):
        run_transient_pund(sim, "right", "left", .01, **options(**{field: value}))
    assert sim._transient_contact_waveforms is None
    assert sim.results is None


@pytest.mark.parametrize("contact,reference", [("missing", "left"), ("right", "right"), (True, "left")])
def test_unknown_or_ambiguous_contacts_are_rejected(contact, reference):
    with pytest.raises(ValueError):
        run_transient_pund(device(), contact, reference, .01, **options())


def test_previous_waveform_restored_on_success():
    sim = device(fe=False)
    previous = ([0., 1e-9], {"right": np.array([0., .1])})
    sim.set_transient_contact_waveforms(*previous)
    run_transient_pund(sim, "right", "left", .01, **options())
    np.testing.assert_array_equal(sim._transient_contact_waveforms[0], previous[0])
    np.testing.assert_array_equal(sim._transient_contact_waveforms[1]["right"], previous[1]["right"])


def test_incomplete_native_history_raises_and_restores_waveform_with_accepted_prefix():
    sim = device()
    original = sim.run_transient
    def incomplete(**kwargs):
        return original(max_iter=0, tol=kwargs["tol"])
    sim.run_transient = incomplete
    with pytest.raises(PUNDTransientError) as exc:
        run_transient_pund(sim, "right", "left", .01, **options())
    assert len(exc.value.accepted_history) == 1
    assert exc.value.elapsed_time_s == exc.value.accepted_history[-1]["time_s"]
    assert sim._transient_contact_waveforms is None
    sim.run_transient = original
    retry = run_transient_pund(sim, "right", "left", .01, **options())
    reference = run_transient_pund(device(), "right", "left", .01, **options())
    for first, second in zip(retry["history"], reference["history"]):
        np.testing.assert_array_equal(first["P"], second["P"])
        np.testing.assert_array_equal(first["phi"], second["phi"])


@pytest.mark.parametrize("mu", [1e-4, .1])
def test_native_ohmic_conduction_and_capacitive_repeat_charge_are_paired(mu):
    sim = device(fe=False)
    density = 1e16
    sim._sim.set_mobility(np.full(9, mu), np.full(9, 2*mu))
    sim._sim.set_initial_guess(np.zeros(9), np.full(9, density), np.full(9, density))
    sim._sim.set_electron_bc({0: density, 8: density})
    sim._sim.set_hole_bc({0: density, 8: density})
    out = run_transient_pund(sim, "right", "left", .01, **options())
    conductance = sim.elementary_charge_C*density*3*mu/40e-9
    cap = 9*8.854187817e-12/40e-9
    previous = out["history"][0]
    for state in out["history"][1:]:
        voltage = state["electrode_voltages_V"][1]
        assert state["electrode_conduction_currents_A"][1] == pytest.approx(conductance*voltage, rel=1e-9, abs=1e-16)
        dielectric = cap*(voltage-previous["electrode_voltages_V"][1])/state["dt_s"]
        assert state["electrode_total_currents_A"][1] == pytest.approx(conductance*voltage+dielectric, rel=1e-9, abs=1e-15)
        previous = state
    for label, (start, end) in out["pulse_windows_s"].items():
        expected_leak = conductance*math.fsum(s["dt_s"]*s["electrode_voltages_V"][1]
                           for s in out["history"] if start < s["time_s"] <= end)
        expected = expected_leak+cap*.01*(1 if label in ("P", "U") else -1)
        assert out["pulse_charge_C"][label] == pytest.approx(expected, rel=1e-9)
    assert out["switching_charge_magnitude_C"] < abs(out["pulse_charge_C"]["P"])*1e-9
    assert not out["leakage_cancellation_validated"]


@pytest.mark.parametrize("issue", ["empty", "interior", "same_plane", "nonfinite", "nonbinary"])
def test_contact_face_mapping_is_verified_before_drive(issue):
    sim = device()
    if issue == "same_plane": sim.mesh.fields["contact_right"] = sim.mesh.fields["contact_left"].copy()
    elif issue == "nonfinite": sim.mesh.fields["contact_right"] = np.full(9, np.nan)
    elif issue == "nonbinary": sim.mesh.fields["contact_right"] = np.full(9, .5)
    else:
        sim.mesh.fields["contact_right"][:] = False
        if issue == "interior": sim.mesh.fields["contact_right"][4] = True
    with pytest.raises(ValueError):
        run_transient_pund(sim, "right", "left", .01, **options())
    assert sim._transient_contact_waveforms is None and sim.results is None


def test_unresolvable_pulse_amplitude_is_rejected_before_drive():
    sim = device()
    sim._contact_voltages["left"] = 1e100
    with pytest.raises(ValueError, match="resolved"):
        run_transient_pund(sim, "right", "left", .01, **options())
    assert sim._transient_contact_waveforms is None and sim.results is None


@pytest.mark.parametrize("issue", ["off_grid", "overlap", "missing", "duration", "reference", "failed"])
def test_native_extraction_rejects_ambiguous_or_incomplete_windows(issue):
    sim = device(fe=False)
    out = run_transient_pund(sim, "right", "left", .01, **options())
    windows = dict(out["pulse_windows_s"])
    history = [dict(s) for s in out["history"]]
    reference = "x_min"
    if issue == "off_grid": windows["P"] = (windows["P"][0]+1e-15, windows["P"][1])
    elif issue == "overlap": windows["U"] = windows["P"]
    elif issue == "missing": del windows["D"]
    elif issue == "duration": windows["U"] = (windows["U"][0], history[-1]["time_s"])
    elif issue == "reference": reference = "x_max"
    else: history[-1]["valid"] = False
    with pytest.raises(ValueError):
        extract_transient_pund_charge(history, windows, terminal="x_max", reference_terminal=reference)
