"""Continuous native drive: independent capacitor, FE and SG/BE references."""
import numpy as np
import pytest

from tcad.postprocess import integrate_transient_terminal_history
from test_transient_displacement import film
from test_transient_selfconsistent import central_cell, bernoulli, QE, EPS, VT
from test_physical_step_commit import high_level


CLOCK = np.array([0., .3, .8, 1.2, 1.9, 2.3, 3.]) * 1e-9
VOLTAGE = np.array([0., .02, .02, -.01, -.01, 0., 0.])


def driven_film(axis=0, model=2, stretched=False, layered=False, dt=.6e-9, fe=False):
    sim, x, eps, mask, area = film(axis, model, stretched, layered)
    sim.set_dirichlet_potential({0: 0., 8: 0.})
    sim.set_ferroelectric_enabled(fe)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(CLOCK[-1])
    sim.set_transient_voltage_waveforms(CLOCK, {8: VOLTAGE})
    return sim, x, eps, mask, area


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("layered", [False, True])
@pytest.mark.parametrize("dt", [.19e-9, .6e-9])
def test_capacitor_pulse_charge_current_knots_and_source_work(axis, stretched, layered, dt):
    sim, x, eps, _, area = driven_film(axis, stretched=stretched, layered=layered, dt=dt)
    history = sim.solve_transient()
    times = np.array([s["time_s"] for s in history])
    for knot in CLOCK:
        assert knot in times
    assert np.all(np.diff(times) > 0.) and np.max(np.diff(times)) <= dt * (1 + 1e-14)
    harmonic = 2 * eps[:-1] * eps[1:] / (eps[:-1] + eps[1:])
    series = np.cumsum(np.diff(x) / harmonic)
    capacitance = area / series[-1]
    prev_v = 0.
    work = 0.
    for state in history:
        assert state["valid"] and state["electrode_charge_available"]
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        np.testing.assert_allclose(state["phi"], voltage * np.r_[0., series / series[-1]], atol=1e-17)
        np.testing.assert_allclose(state["electrode_voltages_V"], [0., voltage], atol=1e-17)
        np.testing.assert_allclose(state["electrode_charges_C"], capacitance * np.array([-voltage, voltage]), atol=1e-32)
        if state["dt_s"]:
            dq = capacitance * (voltage - prev_v) * np.array([-1., 1.])
            np.testing.assert_allclose(state["electrode_charge_increments_C"], dq, atol=1e-32)
            np.testing.assert_allclose(state["electrode_total_currents_A"], dq / state["dt_s"], atol=1e-22)
            np.testing.assert_allclose(state["electrode_dielectric_currents_A"], dq / state["dt_s"], atol=1e-22)
            np.testing.assert_array_equal(state["electrode_polarization_currents_A"], 0.)
            work += voltage * dq[1]
        prev_v = voltage
    report = integrate_transient_terminal_history(history)
    np.testing.assert_allclose(list(report["terminal_charge_C"].values()), 0., atol=1e-31)
    assert report["supplied_energy_J"] == pytest.approx(work, rel=1e-12, abs=0.)
    # Endpoint BE quadrature has a known positive error for a lossless cycle.
    volts = np.interp(times, CLOCK, VOLTAGE)
    assert work == pytest.approx(.5 * capacitance * np.sum(np.diff(volts)**2), rel=1e-12, abs=0.)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_capacitor_work_quadrature_converges_under_time_refinement(axis):
    errors = []
    for level in range(4):
        sim, _, _, _, _ = driven_film(axis, dt=1e-9 / 2**level)
        sim.set_transient_t_final(2e-9)
        sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9], {8: [0., .02, 0.]})
        report = integrate_transient_terminal_history(sim.solve_transient())
        errors.append(report["supplied_energy_J"])
    np.testing.assert_allclose(np.array(errors[1:]) / errors[:-1], .5, rtol=1e-12)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("dt", [.19e-9, .6e-9])
def test_nls_uses_endpoint_drive_without_an_extra_dwell(axis, dt):
    sim, x, eps, _, area = driven_film(axis, dt=dt, fe=True)
    capacitance = area * eps[0] / x[-1]
    previous_p = previous_v = 0.
    for state in sim.solve_transient():
        assert state["valid"]
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        expected_p = previous_p
        if state["dt_s"] and voltage:
            target = -np.sign(voltage) * 1e-6
            expected_p += -np.expm1(-state["dt_s"] / 1e-9) * (target - previous_p)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], expected_p, rtol=1e-11, atol=1e-20)
        np.testing.assert_allclose(state["phi"], voltage * x / x[-1], atol=1e-17)
        if state["dt_s"]:
            polarity = np.array([-1., 1.])
            dielectric = capacitance * (voltage - previous_v) / state["dt_s"] * polarity
            polarization = -area * (expected_p - previous_p) / state["dt_s"] * polarity
            np.testing.assert_allclose(state["electrode_polarization_currents_A"], polarization, atol=1e-22)
            np.testing.assert_allclose(state["electrode_total_currents_A"], dielectric + polarization, atol=1e-22)
        previous_p, previous_v = expected_p, voltage


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_lk_implicit_cubic_uses_applied_endpoint_field(axis):
    sim, x, _, mask, _ = driven_film(axis, model=0, dt=.2e-9, fe=True)
    sim.set_ferroelectric_params(mask, 1e8, 1e12)
    previous_p = 0.
    for state in sim.solve_transient():
        assert state["valid"]
        if state["dt_s"]:
            rate = .1 / state["dt_s"]
            field = -np.interp(state["time_s"], CLOCK, VOLTAGE) / x[-1]
            roots = np.roots([1e12, 0., 1e8 + rate, -(rate * previous_p + field)])
            real_roots = roots[np.abs(roots.imag) < 1e-12].real
            assert len(real_roots) == 1
            previous_p = real_roots[0]
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], previous_p, rtol=1e-10, atol=1e-18)


def scalar_driven_step(nn, pp, dt, x, voltage):
    rates = 1 / (np.diff(x) * (x[-1] / 2))
    kappa = QE * 1e16 / (EPS * sum(rates))
    average = np.dot(rates, [0., voltage]) / sum(rates)
    if dt == 0.:
        return average + kappa * (pp - nn + .15), nn, pp

    def carriers(phi):
        u = (phi - np.array([0., voltage])) / VT
        bp = np.array([bernoulli(v) for v in u])
        bm = np.array([bernoulli(-v) for v in u])
        an, ap = dt * .1 * VT, dt * .05 * VT
        return ((nn + an * np.dot(rates, bm)) / (1 + an * np.dot(rates, bp)),
                (pp + ap * np.dot(rates, bp)) / (1 + ap * np.dot(rates, bm)))

    low, high = -10 * VT, 10 * VT
    for _ in range(100):
        phi = (low + high) / 2
        n, p = carriers(phi)
        if phi - average - kappa * (p - n + .15) < 0:
            low = phi
        else:
            high = phi
    phi = (low + high) / 2
    return phi, *carriers(phi)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_voltage_driven_carriers_match_independent_poisson_sg_be(axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True)
    clock = np.array([0., .6, 1.6, 2.5]) * 1e-10
    volts = np.array([0., .002, -.001, 0.])
    sim.set_transient_voltage_waveforms(clock, {2: volts})
    for state in sim.solve_transient():
        assert state["valid"]
        voltage = np.interp(state["time_s"], clock, volts)
        phi, nn, pp = scalar_driven_step(nn, pp, state["dt_s"], x, voltage)
        np.testing.assert_allclose(state["phi"], [0., phi, voltage], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(state["n"] / 1e16, [1., nn, 1.], rtol=2e-8)
        np.testing.assert_allclose(state["p"] / 1e16, [1., pp, 1.], rtol=2e-8)
        if state["dt_s"]:
            current = state["electrode_total_currents_A"]
            assert abs(sum(current)) < 1e-7 * max(abs(current)) + 1e-22


@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_rejected_pulse_rolls_back_voltage_and_fe_and_retry_matches_fresh(model):
    sim, *_ = driven_film(model=model, fe=True)
    sim.set_gummel_max_iter(0)
    initial, failed = sim.solve_transient()
    assert not failed["valid"] and failed["time_s"] == 0. and failed["dt_s"] == 0.
    assert failed["attempted_time_s"] == CLOCK[1]
    np.testing.assert_array_equal(failed["electrode_voltages_V"], [0., 0.])
    np.testing.assert_array_equal(failed["phi"], initial["phi"])
    np.testing.assert_array_equal(failed["P"], initial["P"])
    assert not failed["displacement_current_available"]
    sim.set_gummel_max_iter(80)
    fresh, *_ = driven_film(model=model, fe=True)
    actual, expected = sim.solve_transient(), fresh.solve_transient()
    for got, want in zip(actual, expected, strict=True):
        assert got["valid"]
        np.testing.assert_array_equal(got["phi"], want["phi"])
        np.testing.assert_array_equal(got["P"], want["P"])
    sim.clear_transient_voltage_waveforms()
    sim.set_ferroelectric_enabled(False)
    sim.set_ferroelectric_gamma(0.)
    for state in sim.solve_transient():
        np.testing.assert_array_equal(state["electrode_voltages_V"], [0., 0.])


INVALID = [([0.], {8: [0.]}), ([1., 2.], {8: [0., 1.]}),
           ([0., 0.], {8: [0., 1.]}), ([0., 2., 1.], {8: [0., 1., 2.]}),
           ([0., np.nan], {8: [0., 1.]}), ([0., 1.], {}),
           ([0., 1.], {8: [0.]}), ([0., 1.], {8: [0., np.inf]}),
           ([0., 1.], {1: [0., 1.]}), ([0., 1.], {-1: [0., 1.]}),
           ([0., 1.], {True: [0., 1.]}), ([0., 1.], {8: [0j, 1j]}),
           ([0., 1.], {8: [False, True]}), ([0., 1.], {8: ["0", "1"]})]


@pytest.mark.parametrize("times,profiles", INVALID)
def test_invalid_native_waveform_keeps_previous_configuration(times, profiles):
    sim, *_ = driven_film()
    with pytest.raises((ValueError, TypeError)):
        sim.set_transient_voltage_waveforms(times, profiles)
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    assert history[1]["electrode_voltages_V"][1] == pytest.approx(.02)


@pytest.mark.parametrize("reason", ["frozen", "coverage"])
def test_unsupported_drive_rejected_before_state_advances(reason):
    sim, *_ = driven_film()
    if reason == "frozen":
        sim.set_newton_freeze_phi(True)
    else:
        sim.set_transient_t_final(4e-9)
    with pytest.raises(ValueError, match="unfrozen|cover"):
        sim.solve_transient()
    sim.clear_transient_voltage_waveforms()
    sim.set_newton_freeze_phi(False)
    sim.set_transient_t_final(0.)
    state, = sim.solve_transient()
    np.testing.assert_array_equal(state["electrode_voltages_V"], [0., 0.])


def test_named_contact_waveforms_copy_inputs_refresh_offsets_and_preserve_dc():
    sim = high_level(initial_voltage=.123)
    sim._sim.set_ferroelectric_enabled(False)
    sim._sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_transient(dt=.6e-9, t_final=CLOCK[-1])
    clock, volts = CLOCK.copy(), VOLTAGE.copy()
    sim.set_transient_contact_waveforms(clock, {"right": volts})
    clock[:] = 0.
    volts[:] = 99.
    sim.set_contact("right", .456)
    for state in sim.run_transient(max_iter=80):
        assert state["valid"]
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        np.testing.assert_allclose(state["electrode_voltages_V"], [0., voltage], atol=1e-16)
    assert sim._contact_voltages["right"] == .456
    sim.clear_transient_contact_waveforms()
    sim.set_transient(dt=.6e-9, t_final=0.)
    state, = sim.run_transient(max_iter=80)
    np.testing.assert_array_equal(state["electrode_voltages_V"], [0., .456])


@pytest.mark.parametrize("profiles", [{}, {"missing": VOLTAGE}, {"right": [0.]},
                                       {"right": np.full(7, np.nan)}])
def test_invalid_named_waveform_does_not_replace_valid_drive(profiles):
    sim = high_level()
    sim._sim.set_ferroelectric_enabled(False)
    sim._sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_transient(dt=.6e-9, t_final=CLOCK[-1])
    sim.set_transient_contact_waveforms(CLOCK, {"right": VOLTAGE})
    with pytest.raises(ValueError):
        sim.set_transient_contact_waveforms(CLOCK, profiles)
    history = sim.run_transient(max_iter=80)
    assert history[1]["electrode_voltages_V"][1] == pytest.approx(.02)


def test_gate_alias_union_and_conflicting_shared_contacts():
    sim = high_level()
    sim._sim.set_ferroelectric_enabled(False)
    sim._sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.mesh.fields["contact_gate_r"] = sim.mesh.fields["contact_right"].copy()
    sim.mesh.fields["contact_gate"] = sim.mesh.fields["contact_right"].copy()
    sim.set_contact("gate", 0.)
    sim.set_contact("gate_r", 0.)
    sim.set_transient(dt=.6e-9, t_final=CLOCK[-1])
    sim.set_transient_contact_waveforms(CLOCK, {"gate": VOLTAGE, "gate_r": VOLTAGE})
    with pytest.raises(ValueError, match="conflicting"):
        sim.set_transient_contact_waveforms(CLOCK, {"gate": VOLTAGE, "gate_r": -VOLTAGE})
    history = sim.run_transient(max_iter=80)
    assert history[1]["electrode_voltages_V"][1] == pytest.approx(.02)


def test_contact_offsets_and_truncation_inside_last_waveform_segment():
    sim, *_ = driven_film()
    sim.set_dirichlet_potential({0: .03, 8: .123})
    sim.set_transient_t_final(1.5e-9)
    sim.set_transient_voltage_waveforms(CLOCK, {8: VOLTAGE - .123})
    history = sim.solve_transient()
    assert history[-1]["time_s"] == 1.5e-9
    for state in history:
        np.testing.assert_allclose(state["electrode_voltages_V"],
                                   [.03, np.interp(state["time_s"], CLOCK, VOLTAGE)], atol=1e-17)
    sim.clear_transient_voltage_waveforms()
    sim.set_transient_t_final(0.)
    state, = sim.solve_transient()
    np.testing.assert_array_equal(state["electrode_voltages_V"], [.03, .123])


def test_exception_restores_configured_contacts_without_committing_fe():
    sim, *_ = driven_film(fe=True)
    sim.set_dirichlet_potential({0: 0., 8: 1e308})
    sim.set_transient_t_final(.3e-9)
    sim.set_transient_voltage_waveforms([0., .3e-9], {8: [-1e308, 1e308]})
    with pytest.raises(ValueError, match="finite output range"):
        sim.solve_transient()
    # Cancellation at t=0 works only if the original DC map was restored.
    sim.set_transient_voltage_waveforms([0., .3e-9], {8: [-1e308, -1e308]})
    history = sim.solve_transient()
    for state in history:
        assert state["valid"]
        np.testing.assert_array_equal(state["electrode_voltages_V"], [0., 0.])
        np.testing.assert_array_equal(state["P"], 0.)
