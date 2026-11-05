"""Bounded physical LK steps, independent BE equations and switching ODE."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_energy, integrate_transient_terminal_history
from tcad.simulator import Simulator
from test_fe_transient_feedback import dielectric
from test_transient_displacement import film
from test_transient_lk_coupled import simultaneous_film_step, carrier_reference
from test_transient_selfconsistent import central_cell
from test_transient_voltage_waveforms import driven_film, CLOCK, VOLTAGE
from test_physical_step_commit import high_level


SWITCH_CLOCK = np.array([0., 8., 10., 14., 16., 22., 24., 36.])*1e-9
SWITCH_VOLTAGE = np.array([-.08, -.08, 0., 0., .008, .008, .08, .08])


def switching_reference(steps_per_segment, *, return_trace=False):
    """Independent scalar RK4; uniform full-FE film has exactly uniform E.

    Continuation begins at P=0, retains the positive metastable well under
    a weak reversed field, then switches with the strong reversed field.
    """
    p = 0.; knots = [p]; trace_time = [0.]; trace_p = [p]
    for start, end, v0, v1 in zip(SWITCH_CLOCK[:-1], SWITCH_CLOCK[1:],
                                SWITCH_VOLTAGE[:-1], SWITCH_VOLTAGE[1:]):
        dt = (end-start)/steps_per_segment
        def rate(fraction, value):
            field = -(v0+(v1-v0)*fraction)/8e-8
            return (field+1e8*value-1e12*value**3)/.1
        for i in range(steps_per_segment):
            k1 = rate(i/steps_per_segment, p)
            k2 = rate((i+.5)/steps_per_segment, p+.5*dt*k1)
            k3 = rate((i+.5)/steps_per_segment, p+.5*dt*k2)
            k4 = rate((i+1)/steps_per_segment, p+dt*k3)
            p += dt*(k1+2*k2+2*k3+k4)/6
            if return_trace:
                trace_time.append(end if i+1 == steps_per_segment else start+(i+1)*dt)
                trace_p.append(p)
        knots.append(p)
    if return_trace:
        return np.array(trace_time), np.array(trace_p)
    return np.array(knots)


def switching_run(safety, axis=0):
    sim, *_ = film(axis, 0, False, False)
    sim.set_dirichlet_potential({0: 0., 8: 0.})
    sim.set_transient_voltage_waveforms(SWITCH_CLOCK, {8: SWITCH_VOLTAGE})
    sim.set_transient_dt(1e-7); sim.set_transient_t_final(SWITCH_CLOCK[-1])
    sim.set_tolerance(1e-12); sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_substepping(True, safety)
    return sim.solve_transient()


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_metastable_hold_then_switch_matches_continuous_ode_with_step_convergence(axis):
    reference = switching_reference(4096)
    np.testing.assert_allclose(reference, switching_reference(8192), rtol=0., atol=1e-13)
    assert reference[3] > .009 and reference[5] > .009 and reference[-1] < -.013
    errors = []
    for safety in (.5, .25, .125):
        history = switching_run(safety, axis)
        assert all(s["valid"] for s in history)
        p = np.array([s["P"].reshape(-1, 3)[:, axis] for s in history])
        np.testing.assert_allclose(p, np.repeat(p[:, :1], 9, axis=1), rtol=1e-9, atol=1e-12)
        lookup = {s["time_s"]: i for i, s in enumerate(history)}
        knots = np.array([p[lookup[t], 0] for t in SWITCH_CLOCK])
        assert knots[3] > .009 and knots[5] > .009 and knots[-1] < -.013
        errors.append(float(np.max(abs(knots-reference))))
        assert audit_transient_lk_energy(history)["valid"]
    assert errors[1] < .7*errors[0] and errors[2] < .7*errors[1]


def test_repeated_runs_continue_from_accepted_metastable_state():
    sim, _ = dielectric(voltage=-.08, dt=1e-7, final=12e-9)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True, .25)
    written = sim.solve_transient()[-1]["P"].copy()
    sim.set_dirichlet_potential({0: 0., 8: .008})
    held = sim.solve_transient()
    np.testing.assert_array_equal(held[0]["P"], written)
    assert np.min(held[-1]["P"].reshape(-1, 3)[:, 0]) > .009
    sim.set_dirichlet_potential({0: 0., 8: .08})
    switched = sim.solve_transient()
    np.testing.assert_array_equal(switched[0]["P"], held[-1]["P"])
    assert np.max(switched[-1]["P"].reshape(-1, 3)[:, 0]) < -.013
    assert audit_transient_lk_energy(held)["valid"] and audit_transient_lk_energy(switched)["valid"]


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_substeps_with_active_carriers_match_independent_sg_gauss_lk(axis, log_space):
    scale = 1e19
    sim, x, nn, pp = central_cell(scale, log_space, axis, True, final=1.23e-9)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_gamma(.1); sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_material_field(False)  # carrier_reference uses centred E.
    sim.set_transient_lk_substepping(True, .2); sim.set_transient_dt(1e-7)
    history = sim.solve_transient(); old_p = np.zeros(3)
    assert len(history) == 8
    for state in history[1:]:
        assert state["valid"] and not state["majority_frozen"] and not state["phi_frozen"]
        phi, nn, pp, old_p = carrier_reference(nn, pp, old_p, state["dt_s"], x, scale, alpha=-1e8)
        np.testing.assert_allclose(state["phi"], [0., phi, 0.], rtol=1e-8, atol=1e-11)
        np.testing.assert_allclose(state["n"]/scale, [1., nn, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["p"]/scale, [1., pp, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], old_p, rtol=1e-8, atol=1e-12)
    assert audit_transient_lk_energy(history)["valid"]


def test_failure_after_accepted_substeps_reports_covered_time_and_retry_continues():
    sim, *_ = driven_film(model=0, fe=True, layered=True, dt=1e-7)
    times = np.array([0., 1., 2.])*1e-9
    sim.set_transient_voltage_waveforms(times, {8: [0., 0., -.01]})
    sim.set_transient_t_final(2e-9)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True, .2)
    sim.set_gummel_max_iter(1)
    history = sim.solve_transient()
    assert all(s["valid"] for s in history[:-1]) and not history[-1]["valid"]
    assert history[-1]["time_s"] == 1e-9 and history[-1]["attempted_time_s"] > 1e-9
    assert history[-1]["dt_s"] == 0. and not history[-1]["lk_energy_increment_available"]
    for key in ("phi", "P", "n", "p", "electrode_voltages_V"):
        np.testing.assert_array_equal(history[-1][key], history[-2][key])
    assert audit_transient_lk_energy(history[:-1])["valid"]
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    np.testing.assert_array_equal(retry[0]["P"], history[-2]["P"])
    assert retry[0]["time_s"] == 0. and retry[-1]["time_s"] == 2e-9
    assert all(s["valid"] for s in retry)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("layered", [False, True])
@pytest.mark.parametrize("safety", [.5, .2])
def test_coarse_request_matches_independent_simultaneous_substeps(axis, layered, safety):
    sim, x, eps, mask, _ = film(axis, 0, True, layered)
    sim.set_transient_lk_material_field(False)  # Explicit central-field reference below.
    sim.set_tolerance(1e-12); sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_substepping(True, safety)
    sim.set_transient_dt(1e-7); sim.set_transient_t_final(1.23e-9)
    history = sim.solve_transient(); old = np.zeros(len(x))
    assert len(history) > 2 and history[-1]["time_s"] == 1.23e-9
    for state in history:
        assert state["valid"] and state["lk_coupled"] and state["lk_substepping"]
        assert state["lk_step_limit_s"] == pytest.approx(safety*1e-9)
        if state["initial_state"]:
            continue
        assert state["dt_s"] <= safety*1e-9*(1.+1e-13)
        phi, p = simultaneous_film_step(x, eps, mask, old, state["dt_s"], -.01)
        np.testing.assert_allclose(state["phi"], phi, rtol=2e-9, atol=2e-11)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], p, rtol=2e-8, atol=1e-12)
        old = p
    audit = audit_transient_lk_energy(history)
    assert audit["valid"] and audit["lk_substepping"] and not audit["energy_balance_validated"]
    port = integrate_transient_terminal_history(history)
    assert port["duration_s"] == 1.23e-9


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_waveform_knots_short_final_step_and_manual_fine_run_match(axis):
    bounded, *_ = driven_film(axis, model=0, fe=True, layered=True, dt=1e-7)
    explicit, *_ = driven_film(axis, model=0, fe=True, layered=True, dt=.2e-9)
    bounded.set_transient_lk_coupled(True); bounded.set_transient_lk_substepping(True, .2)
    explicit.set_transient_lk_coupled(True)
    actual, expected = bounded.solve_transient(), explicit.solve_transient()
    assert len(actual) == len(expected)
    clock = np.array([s["time_s"] for s in actual])
    assert np.all(np.diff(clock) > 0.)
    for knot in CLOCK:
        assert knot in clock
    for a, b in zip(actual, expected):
        for key in ("phi", "n", "p", "P", "time_s", "dt_s"):
            np.testing.assert_allclose(a[key], b[key], rtol=3e-12, atol=1e-18)
        assert a["valid"]
        np.testing.assert_allclose(a["electrode_voltages_V"],
                                   [0., np.interp(a["time_s"], CLOCK, VOLTAGE)], atol=1e-17)
    assert audit_transient_lk_energy(actual)["valid"]


@pytest.mark.parametrize("safety", [.5, .1, np.nextafter(1., 0.)])
def test_roundoff_tail_has_strict_clocks_and_native_monotone_steps(safety):
    sim, _ = dielectric(voltage=0., dt=1e-7, final=2e-9)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True, safety)
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    clock = np.array([s["time_s"] for s in history])
    assert np.all(np.diff(clock) > 0.) and clock[-1] == 2e-9
    assert np.sum([s["dt_s"] for s in history]) == pytest.approx(2e-9, rel=2e-15)
    assert audit_transient_lk_energy(history)["valid"]


@pytest.mark.parametrize("alpha", [0., 1e8])
def test_nonnegative_alpha_does_not_add_unnecessary_substeps(alpha):
    sim, _ = dielectric(voltage=-.01, alpha=alpha, dt=1e-7, final=2.5e-7)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True)
    history = sim.solve_transient()
    assert len(history) == 4 and all(s["valid"] for s in history)
    assert history[0]["lk_step_limit_s"] == 1e-7
    assert audit_transient_lk_energy(history)["valid"]


@pytest.mark.parametrize("case", ["split", "disabled", "nls", "unrepresentable"])
def test_bad_configuration_rejected_before_consuming_polarization(case):
    sim, _ = dielectric(final=1e-10)
    original = sim.solve_transient()[-1]["P"].copy()
    sim.set_transient_lk_substepping(True); sim.set_transient_lk_coupled(True)
    if case == "split":
        sim.set_transient_lk_coupled(False)
    elif case == "disabled":
        sim.set_ferroelectric_enabled(False); sim.set_ferroelectric_gamma(0.)
    elif case == "nls":
        sim.set_ferroelectric_model(2)
    else:
        sim.set_ferroelectric_gamma(1e-30)
    with pytest.raises(ValueError, match="LK substep"):
        sim.solve_transient()
    sim.set_transient_lk_substepping(False); sim.set_transient_lk_coupled(False)
    sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_model(0); sim.set_ferroelectric_gamma(.1)
    sim.set_transient_t_final(0.)
    np.testing.assert_array_equal(sim.solve_transient()[0]["P"], original)


def test_failed_substep_and_retry_preserve_state_and_voltage():
    sim, *_ = driven_film(model=0, fe=True, layered=True, dt=1e-7)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True, .2)
    sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]["valid"] and failed[-1]["dt_s"] == 0.
    assert failed[-1]["time_s"] == 0. and failed[-1]["attempted_time_s"] == pytest.approx(.2e-9)
    for key in ("phi", "P", "n", "p", "electrode_voltages_V"):
        np.testing.assert_array_equal(failed[0][key], failed[-1][key])
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, *_ = driven_film(model=0, fe=True, layered=True, dt=1e-7)
    fresh.set_transient_lk_coupled(True); fresh.set_transient_lk_substepping(True, .2)
    expected = fresh.solve_transient()
    assert len(retry) == len(expected)
    for a, b in zip(retry, expected):
        for key in ("phi", "n", "p", "P", "time_s", "dt_s"):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("invalid", [0, 1, "true", None, [], np.array([True])])
def test_native_and_high_level_enable_validation(invalid):
    sim, _ = dielectric()
    host = type("Host", (), {"_sim": sim})()
    for instance in (sim, host):
        method = sim.set_transient_lk_substepping if instance is sim else lambda *a: Simulator.set_transient_lk_substepping(host, *a)
        with pytest.raises(ValueError, match="boolean"):
            method(invalid)


@pytest.mark.parametrize("invalid", [0., 1., -1., np.nan, np.inf, True, "0.5", None, [0.5], 1+0j])
def test_native_and_high_level_safety_validation(invalid):
    sim, _ = dielectric()
    host = type("Host", (), {"_sim": sim})()
    with pytest.raises(ValueError, match="safety"):
        sim.set_transient_lk_substepping(True, invalid)
    with pytest.raises(ValueError, match="safety"):
        Simulator.set_transient_lk_substepping(host, True, invalid)


def test_high_level_and_numpy_scalar_parameters():
    sim = high_level()
    sim.set_transient_lk_coupled(np.bool_(True))
    sim.set_transient_lk_substepping(np.bool_(True), np.float64(.25))
    sim.set_transient_lk_substepping(False)


@pytest.mark.parametrize("case", ["flag", "mixed", "missing_limit", "changed_limit", "too_small", "uncoupled"])
def test_energy_audit_rejects_bad_substep_metadata(case):
    sim, _ = dielectric(dt=1e-7, final=1.2e-9, voltage=-.01)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True)
    history = deepcopy(sim.solve_transient())
    if case == "flag":
        history[-1]["lk_substepping"] = 1
    elif case == "mixed":
        history[-1]["lk_substepping"] = False
        history[-1]["lk_step_limit_s"] = 0.
    elif case == "missing_limit":
        history[-1].pop("lk_step_limit_s")
    elif case == "changed_limit":
        history[-1]["lk_step_limit_s"] *= 2
    elif case == "too_small":
        for s in history:
            s["lk_step_limit_s"] = 1e-12
    else:
        for s in history:
            s["lk_coupled"] = False
    with pytest.raises(ValueError):
        audit_transient_lk_energy(history)
