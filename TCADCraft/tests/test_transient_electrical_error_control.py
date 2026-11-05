"""Joint local error control: independent SG/Poisson/LK and exact diffusion."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.simulator import Simulator
from tcad.postprocess import (audit_transient_lk_electrical_error_control,
                              audit_transient_lk_energy)
from test_transient_lk_error_control import controlled
from test_transient_lk_coupled import carrier_reference, simultaneous_film_step
from test_transient_selfconsistent import central_cell, VT
from test_transient_displacement import film
from test_transient_voltage_waveforms import driven_film, CLOCK, VOLTAGE


def active(axis=0, log_space=False, **budgets):
    sim, x, nn, pp = central_cell(1e19, log_space, axis, True, final=3e-10)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_gamma(.1); sim.set_transient_dt(1e-7)
    controlled(sim, atol=1e-4)
    sim.set_transient_lk_electrical_error_control(**budgets)
    return sim, x, nn, pp


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_joint_control_matches_independent_coarse_and_accepted_sg_lk_steps(axis, log_space):
    sim, x, nn, pp = active(axis, log_space, phi_atol=2e-6, carrier_rtol=2e-4, carrier_atol=1e10)
    sim.set_transient_lk_material_field(False)  # The scalar/coarse reference uses centred E.
    history = sim.solve_transient(); old = np.zeros(3)
    assert all(s["valid"] for s in history)
    for i in range(1, len(history), 2):
        a, b = history[i:i+2]
        phi_c, nc, pc, pol_c = carrier_reference(nn, pp, old, a["dt_s"]+b["dt_s"], x, 1e19, alpha=-1e8)
        np.testing.assert_allclose(b["lk_coarse_phi_V"], [0., phi_c, 0.], rtol=1e-8, atol=1e-11)
        np.testing.assert_allclose(b["lk_coarse_n_per_m3"]/1e19, [1., nc, 1.], rtol=1e-8)
        np.testing.assert_allclose(b["lk_coarse_p_per_m3"]/1e19, [1., pc, 1.], rtol=1e-8)
        np.testing.assert_allclose(b["lk_coarse_P_C_per_m2"].reshape(-1, 3)[:, axis], pol_c, rtol=1e-8, atol=1e-12)
        for s in (a, b):
            phi, nn, pp, old = carrier_reference(nn, pp, old, s["dt_s"], x, 1e19, alpha=-1e8)
            np.testing.assert_allclose(s["phi"], [0., phi, 0.], rtol=1e-8, atol=1e-11)
            np.testing.assert_allclose(s["n"]/1e19, [1., nn, 1.], rtol=1e-8)
            np.testing.assert_allclose(s["p"]/1e19, [1., pp, 1.], rtol=1e-8)
            np.testing.assert_allclose(s["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-12)
    assert history[-1]["time_s"] == 3e-10
    verdict = audit_transient_lk_electrical_error_control(history)
    assert verdict["valid"] and verdict["max_joint_error_ratio"] <= 1.
    assert not verdict["global_temporal_error_validated"]
    assert audit_transient_lk_energy(history)["valid"]


def neutral(axis, rtol=None):
    sim, x, *_ = active(axis)
    sim.set_doping(np.zeros(3))
    sim.set_mobility(np.full(3, .1), np.full(3, .1))
    sim.set_initial_guess(np.zeros(3), 1e19*np.array([1., 1.6, 1.]), 1e19*np.array([1., 1.6, 1.]))
    if rtol is None:
        sim.set_transient_lk_electrical_error_control(False)
    else:
        sim.set_transient_lk_electrical_error_control(carrier_rtol=rtol, carrier_atol=1e10)
    return sim, x


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_carrier_control_reduces_trace_error_when_polarization_estimator_is_negligible(axis):
    errors = []; steps = []
    for relative in (None, 1e-3, 1e-4):
        sim, x = neutral(axis, relative)
        history = sim.solve_transient()
        assert all(s["valid"] for s in history)
        rate = .1*VT*(1/np.diff(x)).sum()/(.5*(x[-1]-x[0]))
        t = np.array([s["time_s"] for s in history])
        density = np.array([s["n"][1]/1e19 for s in history])
        exact = 1.+.6*np.exp(-rate*t)
        errors.append(float(np.max(abs(density-exact)))); steps.append(len(history)-1)
        for s in history:
            # The exact charge-neutral solution has phi=P=0; quad Newton
            # leaves tiny roundoff. It must remain far below either budget.
            np.testing.assert_allclose(s["P"], 0., rtol=0., atol=1e-28)
            np.testing.assert_allclose(s["phi"], 0., rtol=0., atol=1e-28)
            assert s["lk_error_ratio"] < 1e-20
        if relative is not None:
            assert audit_transient_lk_electrical_error_control(history)["valid"]
            assert sum(s["lk_rejected_attempts"] for s in history[2::2]) > 0
    assert steps[0] < steps[1] < steps[2]
    assert errors[1] < .5*errors[0] and errors[2] < .5*errors[1]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_voltage_budget_controls_layered_waveform_with_zero_carriers(axis):
    sim, x, eps, mask, _ = driven_film(axis, model=0, fe=True, stretched=True, layered=True, dt=1e-7)
    sim.set_transient_lk_material_field(False)  # Explicit central-field reference below.
    controlled(sim, atol=1e-2)
    sim.set_transient_lk_electrical_error_control(phi_atol=1e-6)
    history = sim.solve_transient(); old = np.zeros(len(x))
    assert all(s["valid"] for s in history)
    assert all(t in [s["time_s"] for s in history] for t in CLOCK)
    assert sum(s["lk_rejected_attempts"] for s in history[2::2]) > 0
    for s in history[1:]:
        phi, old = simultaneous_film_step(x, eps, mask, old, s["dt_s"], np.interp(s["time_s"], CLOCK, VOLTAGE))
        np.testing.assert_allclose(s["phi"], phi, rtol=2e-9, atol=2e-11)
    assert audit_transient_lk_electrical_error_control(history)["valid"]


@pytest.mark.parametrize("failure", ["budget", "floor", "solver"])
def test_electrical_rejection_rolls_back_whole_group_and_retry_matches_fresh(failure):
    sim, *_ = active(phi_atol=1e-12, carrier_rtol=1e-8)
    controlled(sim, atol=1e-4, max_reject=0 if failure == "budget" else 20,
               min_dt=2e-10 if failure == "floor" else 1e-15)
    if failure == "solver":
        sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert len(failed) == 2 and not failed[-1]["valid"]
    assert failed[-1]["time_s"] == failed[-1]["dt_s"] == 0.
    for key in ("phi", "n", "p", "P"):
        np.testing.assert_array_equal(failed[-1][key], failed[0][key])
    if failure != "solver":
        assert failed[-1]["lk_error_ratio"] < 1. < failed[-1]["lk_electrical_error_ratio"]
    sim.set_gummel_max_iter(100)
    controlled(sim, atol=1e-4)
    sim.set_transient_lk_electrical_error_control()
    retried = sim.solve_transient(); fresh, *_ = active()
    expected = fresh.solve_transient()
    assert len(retried) == len(expected)
    for actual, baseline in zip(retried, expected):
        for key in ("phi", "n", "p", "P"):
            np.testing.assert_array_equal(actual[key], baseline[key])


def test_missing_p_control_rejected_before_state_changes():
    sim, *_ = active()
    controlled(sim).set_transient_lk_error_control(False)
    with pytest.raises(ValueError, match="requires LK polarization"):
        sim.solve_transient()
    controlled(sim, atol=1e-4)
    expected, *_ = active()
    for a, b in zip(sim.solve_transient(), expected.solve_transient()):
        np.testing.assert_array_equal(a["P"], b["P"])


def test_disabling_electrical_control_preserves_existing_p_only_trajectory():
    sim, x, eps, mask, _ = film(0, 0, True, True)
    controlled(sim)
    sim.set_transient_lk_electrical_error_control(np.bool_(True))
    sim.set_transient_lk_electrical_error_control(False)
    fresh, *_ = film(0, 0, True, True)
    expected = controlled(fresh).solve_transient()
    actual = sim.solve_transient()
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        assert "lk_electrical_error_scope" not in a
        for key in ("time_s", "dt_s", "phi", "n", "p", "P"):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("relative", [1., 2.])
def test_relative_carrier_budget_is_strictly_below_one(relative):
    sim, *_ = active()
    with pytest.raises(ValueError):
        sim.set_transient_lk_electrical_error_control(carrier_rtol=relative)


@pytest.mark.parametrize("key", ["phi_atol", "carrier_atol", "carrier_rtol"])
@pytest.mark.parametrize("bad", [True, 0., -1., float("inf"), float("nan"), "1", [1.]])
def test_native_and_public_budget_validation(key, bad):
    sim, *_ = active()
    host = type("Host", (), {"_sim": sim})()
    for target in (sim, host):
        method = (target.set_transient_lk_electrical_error_control if target is sim
                  else lambda **kw: Simulator.set_transient_lk_electrical_error_control(target, **kw))
        with pytest.raises(ValueError):
            method(**{key: bad})


@pytest.mark.parametrize("bad", [0, 1, "true", None, [], np.array([True])])
def test_strict_enable_type(bad):
    sim, *_ = active()
    with pytest.raises(ValueError, match="boolean"):
        sim.set_transient_lk_electrical_error_control(bad)


@pytest.fixture(scope="module")
def audited_history():
    sim, *_ = active()
    return sim.solve_transient()


@pytest.mark.parametrize("case", ["flag", "scope", "changed_budget", "ratio_mismatch", "initial_ratio",
    "first_half_trial", "missing_trial", "bad_shape", "negative_carrier", "nonfinite", "bad_delta"])
def test_auditor_rejects_malformed_or_inconsistent_estimates(audited_history, case):
    h = deepcopy(audited_history)
    if case == "flag": h[1]["lk_electrical_error_control"] = 1
    elif case == "scope": h[1]["lk_electrical_error_scope"] = "global"
    elif case == "changed_budget": h[-1]["lk_phi_atol_V"] *= 2
    elif case == "ratio_mismatch": h[1]["lk_electrical_error_ratio"] *= 2
    elif case == "initial_ratio": h[0]["lk_electrical_error_ratio"] = 1.
    elif case == "first_half_trial": h[1]["lk_coarse_phi_V"] = np.zeros(3)
    elif case == "missing_trial": del h[2]["lk_coarse_phi_V"]
    elif case == "bad_shape": h[2]["lk_coarse_n_per_m3"] = np.zeros(2)
    elif case == "negative_carrier": h[2]["n"][1] = -1.
    elif case == "nonfinite": h[2]["lk_delta_p_per_m3"][1] = np.inf
    elif case == "bad_delta": h[2]["lk_delta_phi_V"][1] += 1.
    with pytest.raises(ValueError):
        audit_transient_lk_electrical_error_control(h)


def test_auditor_detects_finite_excess_and_incorrect_shared_norm(audited_history):
    for defect in (0.5, 2.):
        h = deepcopy(audited_history)
        h[1]["lk_electrical_error_ratio"] = h[2]["lk_electrical_error_ratio"] = defect
        assert not audit_transient_lk_electrical_error_control(h)["valid"]
