"""Split NLS local control: independent face D, kinetics and continuous ODE."""
from copy import deepcopy
import math

import numpy as np
import pytest

from tcad.simulator import Simulator
from tcad.postprocess import audit_transient_nls_error_control, integrate_transient_terminal_history
from test_transient_displacement import film, EPS0
from test_transient_selfconsistent import central_cell, reference_step

PS, TAU, ACTIVATION, IMPRINT, DEPOL = 1e-5, 1e-9, 2e5, 1e4, 30.
CLOCK = np.array([0., .5, 1.8, 2.4, 3.7, 4.3])*1e-9
VOLTAGE = np.array([0., -.04, -.04, .035, .035, 0.])


def configured(axis=0, layered=False, **budgets):
    sim, x, eps, mask, area = film(axis, 2, True, layered)
    sim.set_dirichlet_potential({0: 0., 8: 0.})
    sim.set_transient_voltage_waveforms(CLOCK, {8: VOLTAGE})
    sim.set_transient_dt(1e-7); sim.set_transient_t_final(CLOCK[-1])
    sim.set_ferroelectric_preisach(PS, 1e5, 0.)
    sim.set_ferroelectric_nls(TAU, ACTIVATION, 1e-15)
    sim.set_ferroelectric_builtin_field(IMPRINT); sim.set_ferroelectric_depol(DEPOL)
    sim.set_tolerance(1e-12)
    sim.set_transient_nls_error_control(**budgets)
    return sim, x, eps, mask, area


def electrostatic(x, eps, polarization, voltage):
    """Solve constant face D and the integral voltage constraint directly."""
    face = 2*eps[:-1]*eps[1:]/(eps[:-1]+eps[1:])
    pface = .5*face*(polarization[:-1]/eps[:-1]+polarization[1:]/eps[1:])
    resistance = np.diff(x)/face
    displacement = (np.dot(pface, resistance)-voltage)/sum(resistance)
    return np.r_[0., np.cumsum((pface-displacement)*resistance)]


def kinetics(phi, old, x, mask, dt, *, ps=PS, tau=TAU, activation=ACTIVATION, imprint=IMPRINT, depol=DEPOL):
    selected = np.flatnonzero(mask)
    widths = np.r_[.5*(x[1]-x[0]), .5*(x[2:]-x[:-2]), .5*(x[-1]-x[-2])]
    fields = np.array([-(phi[min(i+1, len(x)-1)]-phi[max(i-1, 0)]) /
                       (x[min(i+1, len(x)-1)]-x[max(i-1, 0)]) for i in selected])
    previous = np.average(old[selected], weights=widths[selected])
    offset = imprint + (previous/(depol*EPS0) if depol else 0.)
    drive = np.average(fields, weights=widths[selected])-offset
    peak = max(np.max(abs(fields-offset)), abs(drive))
    target = ps if drive > 0. else (-ps if drive < 0. else previous)
    fraction = -math.expm1(-dt/tau*math.exp(-activation/peak)) if peak else 0.
    result = np.zeros(len(x)); result[selected] = previous+fraction*(target-previous)
    return result


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("layered", [False, True])
def test_coarse_and_committed_half_steps_match_independent_split_fields_and_kinetics(axis, layered):
    sim, x, eps, mask, _ = configured(axis, layered)
    h = sim.solve_transient(); old = np.zeros(len(x))
    assert all(s["valid"] for s in h)
    assert all(t in [s["time_s"] for s in h] for t in CLOCK)
    for i in range(1, len(h), 2):
        a, b = h[i:i+2]
        voltage = np.interp(b["time_s"], CLOCK, VOLTAGE)
        predicted = electrostatic(x, eps, old, voltage)
        pc = kinetics(predicted, old, x, mask, a["dt_s"]+b["dt_s"])
        np.testing.assert_allclose(b["nls_coarse_P_C_per_m2"].reshape(-1, 3)[:, axis], pc, rtol=1e-8, atol=1e-14)
        np.testing.assert_allclose(b["nls_coarse_phi_V"], electrostatic(x, eps, pc, voltage), rtol=1e-8, atol=1e-12)
        for s in (a, b):
            voltage = np.interp(s["time_s"], CLOCK, VOLTAGE)
            predicted = electrostatic(x, eps, old, voltage)
            old = kinetics(predicted, old, x, mask, s["dt_s"])
            np.testing.assert_allclose(s["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-14)
            np.testing.assert_allclose(s["phi"], electrostatic(x, eps, old, voltage), rtol=1e-8, atol=1e-12)
            assert not s["lk_coupled"] and s["lk_step_limit_s"] == 0.
            assert "electrical_error_scope" not in s and "lk_error_scope" not in s
    assert audit_transient_nls_error_control(h)["valid"]
    assert integrate_transient_terminal_history(h)["duration_s"] == CLOCK[-1]


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_active_carriers_and_uniform_nls_obey_independent_sg_gauss_and_split_kinetics(axis, log_space):
    sim, x, nn, pp = central_cell(1e19, log_space, axis, True, final=3e-10)
    sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_model(2)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_preisach(1e-6, 1e5, 0.)
    sim.set_ferroelectric_nls(TAU, 2e4, 1e-15); sim.set_ferroelectric_builtin_field(IMPRINT)
    sim.set_ferroelectric_polar_axis(axis); sim.set_transient_nls_error_control()
    h = sim.solve_transient(); old = np.zeros(3)
    assert all(s["valid"] for s in h)
    for i in range(1, len(h), 2):
        a, b = h[i:i+2]
        predicted = h[i-1]["phi"]
        coarse_p = kinetics(predicted, old, x, np.ones(3), a["dt_s"]+b["dt_s"], ps=1e-6, activation=2e4, depol=0.)
        phi_c, nc, pc = reference_step(nn, pp, a["dt_s"]+b["dt_s"], x, 1e19, .15)
        np.testing.assert_allclose(b["nls_coarse_P_C_per_m2"].reshape(-1, 3)[:, axis], coarse_p, rtol=1e-8, atol=1e-14)
        np.testing.assert_allclose(b["nls_coarse_phi_V"], [0., phi_c, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(b["nls_coarse_n_per_m3"]/1e19, [1., nc, 1.], rtol=2e-8)
        np.testing.assert_allclose(b["nls_coarse_p_per_m3"]/1e19, [1., pc, 1.], rtol=2e-8)
        for s in (a, b):
            old = kinetics(predicted, old, x, np.ones(3), s["dt_s"], ps=1e-6, activation=2e4, depol=0.)
            phi, nn, pp = reference_step(nn, pp, s["dt_s"], x, 1e19, .15)
            np.testing.assert_allclose(s["phi"], [0., phi, 0.], rtol=2e-8, atol=1e-12)
            np.testing.assert_allclose(s["n"]/1e19, [1., nn, 1.], rtol=2e-8)
            np.testing.assert_allclose(s["p"]/1e19, [1., pp, 1.], rtol=2e-8)
            np.testing.assert_allclose(s["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-14)
            predicted = s["phi"]
    assert audit_transient_nls_error_control(h)["valid"]


def continuous_reference(subdivisions=4096):
    """RK4 of continuously driven NLS with instantaneous extra depolarization."""
    times = [0.]; values = [0.]; value = 0.
    def rhs(t, p):
        field = -np.interp(t, CLOCK, VOLTAGE)/(8e-8)-IMPRINT-p/(DEPOL*EPS0)
        if not field: return 0.
        target = math.copysign(PS, field)
        return (target-p)/TAU*math.exp(-ACTIVATION/abs(field))
    for lo, hi in zip(CLOCK[:-1], CLOCK[1:]):
        step = (hi-lo)/subdivisions
        for j in range(subdivisions):
            t = lo+j*step
            a = rhs(t, value); b = rhs(t+step/2, value+step*a/2)
            c = rhs(t+step/2, value+step*b/2); d = rhs(t+step, value+step*c)
            value += step*(a+2*b+2*c+d)/6
            times.append(lo+(j+1)*step); values.append(value)
    return np.array(times), np.array(values)


def test_tighter_local_budgets_reduce_full_switching_error_against_continuous_ode():
    t, p = continuous_reference(); tf, pf = continuous_reference(8192)
    np.testing.assert_allclose(np.interp(t, tf, pf), p, rtol=0., atol=1e-13)
    errors = []; steps = []
    for relative in (.02, .002, .0002):
        sim, *_ = configured(rtol=relative, atol=relative*PS*.01, phi_atol=1.)
        h = sim.solve_transient()
        assert all(s["valid"] for s in h)
        times = np.array([s["time_s"] for s in h]); actual = np.array([s["P"][0] for s in h])
        errors.append(np.max(abs(actual-np.interp(times, t, p)))); steps.append(len(h)-1)
        assert audit_transient_nls_error_control(h)["valid"]
    assert steps[0] < steps[1] < steps[2]
    assert errors[1] < .6*errors[0] and errors[2] < .6*errors[1]


@pytest.mark.parametrize("failure", ["budget", "floor", "solver"])
def test_rejected_trials_restore_polarization_potential_carriers_and_drive(failure):
    sim, *_ = configured(rtol=1e-10, atol=1e-16, max_reject=0 if failure == "budget" else 20,
                         min_dt=4e-10 if failure == "floor" else 1e-15)
    if failure == "solver": sim.set_gummel_max_iter(0)
    h = sim.solve_transient()
    assert len(h) == 2 and not h[-1]["valid"]
    assert h[-1]["time_s"] == h[-1]["dt_s"] == 0.
    for key in ("P", "phi", "n", "p", "electrode_voltages_V"):
        np.testing.assert_array_equal(h[-1][key], h[0][key])
    assert h[-1]["nls_rejected_attempts"] >= 1
    sim.set_gummel_max_iter(80); sim.set_transient_nls_error_control()
    retry = sim.solve_transient(); fresh, *_ = configured(); expected = fresh.solve_transient()
    assert len(retry) == len(expected)
    for a, b in zip(retry, expected):
        for key in ("time_s", "dt_s", "P", "phi", "n", "p"):
            np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("mode", ["model0", "model1", "model3", "disabled", "classical", "LK", "substeps", "P_control", "LK_electrical", "phi", "n", "p"])
def test_incompatible_models_and_controllers_rejected_before_p_evolution(mode):
    sim, *_ = configured()
    if mode.startswith("model"): sim.set_ferroelectric_model(int(mode[-1]))
    elif mode == "disabled": sim.set_ferroelectric_enabled(False)
    elif mode == "classical": sim.set_transient_electrical_error_control(True)
    elif mode == "LK": sim.set_transient_lk_coupled(True)
    elif mode == "substeps": sim.set_transient_lk_substepping(True)
    elif mode == "P_control": sim.set_transient_lk_error_control(True)
    elif mode == "LK_electrical": sim.set_transient_lk_electrical_error_control(True)
    else: getattr(sim, "set_newton_freeze_"+mode)(True)
    with pytest.raises(ValueError, match="NLS error control requires"):
        sim.solve_transient()


def test_disabled_option_preserves_existing_split_trajectory():
    sim, *_ = configured(); sim.set_transient_nls_error_control(False)
    fresh, *_ = configured(); fresh.set_transient_nls_error_control(False)
    a, b = sim.solve_transient(), fresh.solve_transient()
    assert len(a) == len(b)
    for actual, expected in zip(a, b):
        assert "nls_error_scope" not in actual
        for key in ("P", "phi", "time_s", "dt_s"):
            np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("key", ["rtol", "atol", "phi_atol", "carrier_rtol", "carrier_atol", "min_dt"])
@pytest.mark.parametrize("bad", [True, 0., -1., float("inf"), float("nan"), "1", [1.]])
def test_native_and_public_budget_validation(key, bad):
    sim, *_ = configured(); host = type("Host", (), {"_sim": sim})()
    with pytest.raises(ValueError): sim.set_transient_nls_error_control(**{key: bad})
    with pytest.raises(ValueError): Simulator.set_transient_nls_error_control(host, **{key: bad})


@pytest.mark.parametrize("bad", [0, 1, "true", None, [], np.array([True])])
def test_strict_enable(bad):
    sim, *_ = configured()
    with pytest.raises(ValueError): sim.set_transient_nls_error_control(bad)


@pytest.mark.parametrize("kwargs", [{"rtol": 1.}, {"carrier_rtol": 1.}, {"max_reject": -1}, {"max_reject": True},
                                     {"max_reject": 1.5}, {"max_reject": 2**100}, {"min_dt": 1e-6}, {"min_dt": 1e-30}])
def test_ranges_and_retry_resolution(kwargs):
    sim, *_ = configured()
    with pytest.raises(ValueError):
        sim.set_transient_nls_error_control(**kwargs); sim.solve_transient()


@pytest.fixture(scope="module")
def accepted():
    sim, *_ = configured()
    return sim.solve_transient()


@pytest.mark.parametrize("defect", ["scope", "budget", "pair", "delta", "shape", "missing", "flag", "mix", "classical", "negative_polarization_allowed"])
def test_audit_scope_budget_and_polarization_estimate(accepted, defect):
    h = deepcopy(accepted)
    if defect == "negative_polarization_allowed":
        assert np.any(h[-1]["P"] < 0.)
        assert audit_transient_nls_error_control(h)["valid"]
        return
    if defect == "scope": h[1]["nls_error_scope"] = "fully_coupled"
    elif defect == "budget": h[2]["nls_polarization_atol_C_per_m2"] *= 2.
    elif defect == "pair": h[1]["nls_error_ratio"] += 1.
    elif defect == "delta": h[2]["nls_delta_P_C_per_m2"][0] += 1.
    elif defect == "shape": h[2]["nls_coarse_P_C_per_m2"] = np.zeros(3)
    elif defect == "missing": del h[2]["nls_coarse_P_C_per_m2"]
    elif defect == "flag": h[1]["nls_error_control"] = 1
    elif defect == "mix": h[1]["electrical_error_scope"] = "classical_electrical_step_doubling_BE"
    else: h[1]["electrical_error_control"] = True
    with pytest.raises(ValueError): audit_transient_nls_error_control(h)
