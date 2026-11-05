"""Classical adaptive BE: independent equations, exact solution and rollback."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.simulator import Simulator
from tcad.postprocess import (audit_transient_electrical_error_control,
                              integrate_transient_terminal_history,
                              audit_transient_dielectric_energy)
from tcad.validation.conservation import TransientConservationTest
from test_transient_selfconsistent import central_cell, reference_step, VT
from test_transient_voltage_waveforms import driven_film, scalar_driven_step, CLOCK


def adaptive(sim, **kwargs):
    sim.set_transient_electrical_error_control(True, **kwargs)
    return sim


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("scale", [1e16, 1e24])
def test_coarse_and_each_half_step_match_independent_poisson_sg_be(axis, log_space, stretched, scale):
    sim, x, nn, pp = central_cell(scale, log_space, axis, stretched)
    h = adaptive(sim, min_dt=1e-22).solve_transient()
    assert all(s["valid"] for s in h) and len(h) % 2 == 1
    phi0, _, _ = reference_step(nn, pp, 0., x, scale, .15)
    np.testing.assert_allclose(h[0]["phi"], [0., phi0, 0.], rtol=1e-10, atol=1e-12)
    for i in range(1, len(h), 2):
        a, b = h[i:i+2]
        pc, nc, hc = reference_step(nn, pp, a["dt_s"]+b["dt_s"], x, scale, .15)
        np.testing.assert_allclose(b["electrical_coarse_phi_V"], [0., pc, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(b["electrical_coarse_n_per_m3"]/scale, [1., nc, 1.], rtol=2e-8)
        np.testing.assert_allclose(b["electrical_coarse_p_per_m3"]/scale, [1., hc, 1.], rtol=2e-8)
        for s in (a, b):
            phi, nn, pp = reference_step(nn, pp, s["dt_s"], x, scale, .15)
            np.testing.assert_allclose(s["phi"], [0., phi, 0.], rtol=2e-8, atol=1e-12)
            np.testing.assert_allclose(s["n"]/scale, [1., nn, 1.], rtol=2e-8)
            np.testing.assert_allclose(s["p"]/scale, [1., pp, 1.], rtol=2e-8)
            assert not s["lk_coupled"] and not s["lk_substepping"]
            assert s["lk_step_limit_s"] == 0.
            assert "lk_error_scope" not in s and "lk_electrical_error_scope" not in s
    verdict = audit_transient_electrical_error_control(h)
    assert verdict["valid"] and verdict["max_error_ratio"] <= 1.
    assert not verdict["global_temporal_error_validated"]
    charge = TransientConservationTest(integration="backward_euler", charge_atol_C=0., tolerance=1e-5).run(lambda: h)
    assert charge.passed, charge.message


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_driven_carriers_preserve_knots_and_independent_forcing(axis, log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, axis, True)
    clock = np.array([0., .6, 1.6, 2.5])*1e-10
    volts = np.array([0., .002, -.001, 0.])
    sim.set_transient_voltage_waveforms(clock, {2: volts}); sim.set_transient_dt(1e-8)
    h = adaptive(sim).solve_transient()
    assert all(s["valid"] for s in h)
    assert all(t in [s["time_s"] for s in h] for t in clock)
    for i in range(1, len(h), 2):
        a, b = h[i:i+2]
        vc = np.interp(b["time_s"], clock, volts)
        pc, nc, hc = scalar_driven_step(nn, pp, a["dt_s"]+b["dt_s"], x, vc)
        np.testing.assert_allclose(b["electrical_coarse_phi_V"], [0., pc, vc], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(b["electrical_coarse_n_per_m3"]/1e16, [1., nc, 1.], rtol=2e-8)
        np.testing.assert_allclose(b["electrical_coarse_p_per_m3"]/1e16, [1., hc, 1.], rtol=2e-8)
        for s in (a, b):
            v = np.interp(s["time_s"], clock, volts)
            phi, nn, pp = scalar_driven_step(nn, pp, s["dt_s"], x, v)
            np.testing.assert_allclose(s["phi"], [0., phi, v], rtol=2e-8, atol=1e-12)
            np.testing.assert_allclose(s["n"]/1e16, [1., nn, 1.], rtol=2e-8)
            np.testing.assert_allclose(s["p"]/1e16, [1., pp, 1.], rtol=2e-8)
    assert audit_transient_electrical_error_control(h)["valid"]
    report = integrate_transient_terminal_history(h)
    assert report["duration_s"] == clock[-1]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_charge_free_capacitor_keeps_real_interval_ledgers(axis):
    sim, *_ = driven_film(axis, stretched=True, layered=True, dt=1e-8)
    h = adaptive(sim).solve_transient()
    assert all(s["valid"] for s in h)
    assert all(t in [s["time_s"] for s in h] for t in CLOCK)
    assert audit_transient_electrical_error_control(h)["valid"]
    assert audit_transient_dielectric_energy(h)["valid"]
    assert integrate_transient_terminal_history(h)["duration_s"] == CLOCK[-1]


def neutral(axis=0, relative=None):
    sim, x, *_ = central_cell(1e19, False, axis, True, final=3e-10)
    sim.set_transient_dt(3e-10)
    sim.set_doping(np.zeros(3)); sim.set_mobility(np.full(3, .1), np.full(3, .1))
    initial = 1e19*np.array([1., 1.6, 1.])
    sim.set_initial_guess(np.zeros(3), initial, initial)
    if relative is not None:
        adaptive(sim, carrier_rtol=relative)
    return sim, x


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_tighter_local_budgets_reduce_trace_error_against_exact_diffusion(axis):
    errors = []; steps = []
    for relative in (None, 1e-3, 1e-4):
        sim, x = neutral(axis, relative); h = sim.solve_transient()
        assert all(s["valid"] for s in h)
        rate = .1*VT*(1/np.diff(x)).sum()/(.5*(x[-1]-x[0]))
        time = np.array([s["time_s"] for s in h])
        exact = 1.+.6*np.exp(-rate*time)
        actual = np.array([s["n"][1]/1e19 for s in h])
        errors.append(np.max(abs(actual-exact))); steps.append(len(h)-1)
        if relative is not None:
            assert audit_transient_electrical_error_control(h)["valid"]
    assert steps[0] < steps[1] < steps[2]
    assert errors[1] < .5*errors[0] and errors[2] < .5*errors[1]


@pytest.mark.parametrize("failure", ["budget", "floor", "solver"])
def test_whole_group_rollback_then_retry_matches_fresh(failure):
    sim, x, *_ = central_cell(1e19, False, 0, True, final=3e-10)
    sim.set_transient_dt(3e-10)
    adaptive(sim, phi_atol=1e-12, carrier_rtol=1e-8,
             max_reject=0 if failure == "budget" else 20, min_dt=1e-10 if failure == "floor" else 1e-15)
    if failure == "solver": sim.set_gummel_max_iter(0)
    h = sim.solve_transient()
    assert len(h) == 2 and not h[-1]["valid"]
    assert h[-1]["time_s"] == h[-1]["dt_s"] == 0.
    for key in ("phi", "n", "p", "electrode_voltages_V"):
        np.testing.assert_array_equal(h[-1][key], h[0][key])
    assert h[-1]["electrical_rejected_attempts"] >= 1
    if failure != "solver": assert h[-1]["electrical_error_ratio"] > 1.
    sim.set_gummel_max_iter(100); adaptive(sim)
    fresh, *_ = central_cell(1e19, False, 0, True, final=3e-10)
    fresh.set_transient_dt(3e-10); adaptive(fresh)
    actual, expected = sim.solve_transient(), fresh.solve_transient()
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        for key in ("time_s", "dt_s", "phi", "n", "p"):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("option", ["phi", "n", "p", "FE", "LK", "substeps", "P_control", "LK_electrical"])
def test_incompatible_modes_are_rejected_before_progress(option):
    sim, *_ = central_cell(1e19, False, 0, True)
    adaptive(sim)
    if option in ("phi", "n", "p"):
        getattr(sim, "set_newton_freeze_"+option)(True)
    elif option == "FE": sim.set_ferroelectric_enabled(True)
    elif option == "LK": sim.set_transient_lk_coupled(True)
    elif option == "substeps": sim.set_transient_lk_substepping(True)
    elif option == "P_control": sim.set_transient_lk_error_control(True)
    else: sim.set_transient_lk_electrical_error_control(True)
    with pytest.raises(ValueError, match="classical electrical error control"):
        sim.solve_transient()


def test_disabled_controller_preserves_fixed_step_history():
    sim, *_ = central_cell(1e19, True, 1, True)
    adaptive(sim); sim.set_transient_electrical_error_control(False)
    fresh, *_ = central_cell(1e19, True, 1, True)
    actual, expected = sim.solve_transient(), fresh.solve_transient()
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        assert "electrical_error_scope" not in a
        for key in ("time_s", "dt_s", "phi", "n", "p"):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("key", ["phi_atol", "carrier_atol", "carrier_rtol", "min_dt"])
@pytest.mark.parametrize("bad", [True, 0., -1., float("inf"), float("nan"), "1", [1.]])
def test_native_and_public_reject_invalid_budgets(key, bad):
    sim, *_ = neutral()
    host = type("Host", (), {"_sim": sim})()
    with pytest.raises(ValueError): sim.set_transient_electrical_error_control(**{key: bad})
    with pytest.raises(ValueError): Simulator.set_transient_electrical_error_control(host, **{key: bad})


@pytest.mark.parametrize("bad", [True, -1, 1.5, "2", 2**100])
def test_retry_budget_requires_nonnegative_size_integer(bad):
    sim, *_ = neutral()
    with pytest.raises(ValueError): sim.set_transient_electrical_error_control(max_reject=bad)


@pytest.mark.parametrize("bad", [0, 1, "true", None, [], np.array([True])])
def test_enable_requires_boolean(bad):
    sim, *_ = neutral()
    with pytest.raises(ValueError): sim.set_transient_electrical_error_control(bad)


@pytest.mark.parametrize("setting", [{"carrier_rtol": 1.}, {"min_dt": 1e-9}, {"min_dt": 1e-30}])
def test_budget_range_and_timeline_resolution(setting):
    sim, *_ = neutral()
    with pytest.raises(ValueError):
        adaptive(sim, **setting).solve_transient()


@pytest.fixture(scope="module")
def accepted():
    sim, *_ = neutral(relative=1e-3)
    return sim.solve_transient()


@pytest.mark.parametrize("defect", ["flag", "scope", "mixed", "frozen", "initial", "estimate", "budget", "clock",
    "attempted", "end", "interval", "count", "first_trial", "missing", "shape", "negative", "nonfinite", "delta", "pair",
    "lk_limit", "p_control", "lk_electrical", "polarization"])
def test_auditor_rejects_invalid_provenance(accepted, defect):
    h = deepcopy(accepted)
    if defect == "flag": h[1]["electrical_error_control"] = 1
    elif defect == "scope": h[1]["electrical_error_scope"] = "global"
    elif defect == "mixed": h[1]["lk_error_scope"] = "lk_polarization_step_doubling_BE"
    elif defect == "frozen": h[1]["phi_frozen"] = True
    elif defect == "initial": h[0]["electrical_error_ratio"] = 1.
    elif defect == "estimate": h[2]["electrical_error_estimate_available"] = False
    elif defect == "budget": h[-1]["electrical_phi_atol_V"] *= 2.
    elif defect == "clock": h[1]["time_s"] = 0.
    elif defect == "attempted": h[1]["attempted_time_s"] = 0.
    elif defect == "end": h[1]["electrical_error_end_s"] *= 2.
    elif defect == "interval": h[1]["electrical_error_interval_s"] *= 2.
    elif defect == "count": h[1]["electrical_rejected_attempts"] = True
    elif defect == "first_trial": h[1]["electrical_coarse_phi_V"] = np.zeros(3)
    elif defect == "missing": del h[2]["electrical_coarse_phi_V"]
    elif defect == "shape": h[2]["electrical_delta_n_per_m3"] = np.zeros(2)
    elif defect == "negative": h[2]["p"][1] = -1.
    elif defect == "nonfinite": h[2]["electrical_delta_p_per_m3"][1] = np.inf
    elif defect == "delta": h[2]["electrical_delta_phi_V"][1] += 1.
    elif defect == "lk_limit": h[1]["lk_step_limit_s"] = 1e-10
    elif defect == "p_control": h[1]["lk_error_control"] = True
    elif defect == "lk_electrical": h[1]["lk_electrical_error_control"] = True
    elif defect == "polarization": h[1]["P"] = np.zeros(3)
    else: h[1]["electrical_error_ratio"] += 1.
    with pytest.raises(ValueError): audit_transient_electrical_error_control(h)


def test_auditor_flags_finite_norm_mismatch_and_excess(accepted):
    for ratio in (.5, 2.):
        h = deepcopy(accepted)
        h[1]["electrical_error_ratio"] = h[2]["electrical_error_ratio"] = ratio
        assert not audit_transient_electrical_error_control(h)["valid"]
