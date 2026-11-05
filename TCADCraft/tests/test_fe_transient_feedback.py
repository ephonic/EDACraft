"""Independent LK cubic, NLS clock and Poisson feedback checks."""

import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator


def dielectric(model=0, dt=1e-10, final=2.5e-10, voltage=-.1,
               alpha=-1e8, beta=1e12, gamma=.1, mask=None, positions=None):
    size = 9
    sim = PyDeviceSimulator(size, 1, 1, 1e-8, 1., 1.)
    sim.set_transient_lk_coupled(False)  # This fixture explicitly tests the split integrator.
    x = np.arange(size) * 1e-8 if positions is None else positions
    if positions is not None:
        sim.set_x_positions(x)
    sim.set_permittivity(np.full(size, 8.854187817e-12 * 20))
    sim.set_mobility(np.zeros(size), np.zeros(size))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.full(size, 6.))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_dirichlet_potential({0: 0., size - 1: voltage})
    sim.set_electron_bc({0: 0., size - 1: 0.})
    sim.set_hole_bc({0: 0., size - 1: 0.})
    sim.set_initial_guess(voltage * x / x[-1], np.zeros(size), np.zeros(size))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(size, dtype=np.int8) if mask is None else mask,
                               alpha, beta)
    sim.set_ferroelectric_model(model)
    sim.set_ferroelectric_preisach(.01, 1e5, 0.)
    sim.set_ferroelectric_nls(1e-9, 0., 1e-15)
    sim.set_ferroelectric_gamma(gamma)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(final)
    return sim, x


@pytest.mark.parametrize("dt,final,alpha", [
    (1e-10, 2.5e-10, -1e8), (1e-7, 2.5e-7, -1e8), (1e-10, 2.5e-10, 1e8),
])
def test_lk_obeys_backward_euler_cubic_from_actual_initial_state(dt, final, alpha):
    gamma, beta = .1, 1e12
    sim, x = dielectric(dt=dt, final=final, alpha=alpha)
    history = sim.solve_transient()
    assert len(history) == 4 and all(s["valid"] for s in history)
    expected = 0.
    for state in history[1:]:
        rate = gamma / state["dt_s"]
        roots = np.roots([beta, 0., alpha + rate, -(rate * expected + .1 / x[-1])])
        candidates = [r.real for r in roots if abs(r.imag) < 1e-12 and r.real > 0.]
        assert len(candidates) == 1
        expected = candidates[0]
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], expected, rtol=1e-12)
        np.testing.assert_array_equal(state["P"].reshape(-1, 3)[:, 1:], 0.)
        assert not state["phi_frozen"] and not state["majority_frozen"]
    assert history[-1]["time_s"] == final


def test_lk_uses_nonuniform_edge_distances():
    positions = np.array([0., .2, .7, 1.4, 2.5, 4., 5.8, 7., 8.]) * 1e-8
    sim, _ = dielectric(final=1e-10, positions=positions)
    state = sim.solve_transient()[-1]
    assert state["valid"]
    np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0],
                               state["P"][0], rtol=1e-12)


@pytest.mark.parametrize("dt", [1e-10, 7e-10])
def test_nls_matches_relaxation_at_actual_time_including_short_final_step(dt):
    sim, _ = dielectric(model=2, dt=dt, final=2.5e-9, gamma=0.)
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    for state in history:
        expected = .01 * -np.expm1(-state["time_s"] / 1e-9)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], expected,
                                   rtol=1e-12, atol=1e-18)


def test_fe_bound_charge_changes_potential_and_satisfies_poisson():
    mask = np.zeros(9, dtype=np.int8)
    mask[2:7] = 1
    sim, x = dielectric(model=2, mask=mask, final=1e-10, gamma=0.)
    history = sim.solve_transient()
    state = history[-1]
    assert state["valid"] and not state["phi_frozen"]
    assert np.max(abs(state["phi"] - history[0]["phi"])) > 1e-4
    # Independent tridiagonal solve: bound charge enters the potential
    # equation with +div(P), including nodes outside the FE mask.
    eps, dx = 8.854187817e-12 * 20, x[1] - x[0]
    matrix = np.diag(np.full(7, -2 * eps / dx**2))
    matrix += np.diag(np.full(6, eps / dx**2), 1)
    matrix += np.diag(np.full(6, eps / dx**2), -1)
    polarization = state["P"].reshape(-1, 3)[:, 0]
    rhs = (polarization[2:] - polarization[:-2]) / (2 * dx)
    rhs[-1] -= eps / dx**2 * state["phi"][-1]
    np.testing.assert_allclose(state["phi"][1:-1], np.linalg.solve(matrix, rhs),
                               rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_initial_gauss_projection_preserves_existing_nonuniform_polarization(model):
    mask = np.zeros(9, dtype=np.int8)
    mask[2:7] = 1
    sim, x = dielectric(model=model, mask=mask, final=1e-10)
    previous = sim.solve_transient()[-1]
    assert previous["valid"] and np.max(abs(previous["P"])) > 0.
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_transient_t_final(0.)
    state, = sim.solve_transient()
    assert state["valid"] and state["time_s"] == state["dt_s"] == 0.
    np.testing.assert_array_equal(state["P"], previous["P"])
    np.testing.assert_allclose(state["phi"], previous["phi"], rtol=1e-10, atol=1e-12)
    eps, dx = 8.854187817e-12 * 20, x[1] - x[0]
    matrix = np.diag(np.full(7, -2 * eps / dx**2))
    matrix += np.diag(np.full(6, eps / dx**2), 1)
    matrix += np.diag(np.full(6, eps / dx**2), -1)
    polarization = state["P"].reshape(-1, 3)[:, 0]
    rhs = (polarization[2:] - polarization[:-2]) / (2 * dx)
    rhs[-1] -= eps / dx**2 * state["phi"][-1]
    np.testing.assert_allclose(state["phi"][1:-1], np.linalg.solve(matrix, rhs),
                               rtol=1e-10, atol=1e-12)


def test_fe_feedback_releases_majority_carrier_and_closes_mobile_ledger():
    from tcad.validation.conservation import TransientConservationTest
    mask = np.zeros(9, dtype=np.int8)
    mask[2:7] = 1
    sim, x = dielectric(model=2, mask=mask, final=2.5e-10, gamma=0.)
    sim.set_ferroelectric_preisach(1e-6, 1e5, 0.)
    sim.set_mobility(np.full(9, .1), np.full(9, .05))
    sim.set_doping(np.full(9, 1e16))
    sim.set_bandgap(np.zeros(9))
    sim.set_dirichlet_potential({0: 0., 8: -.001})
    sim.set_electron_bc({0: 2e16, 8: 2e16})
    sim.set_hole_bc({0: 1e16, 8: 1e16})
    sim.set_initial_guess(-.001 * x / x[-1], np.full(9, 2e16), np.full(9, 1e16))
    history = sim.solve_transient()
    assert all(s["valid"] and not s["majority_frozen"] for s in history)
    assert max(abs(history[-1]["n"] - history[0]["n"])) > 1e10
    verdict = TransientConservationTest(integration="backward_euler",
        charge_atol_C=0., tolerance=1e-3).run(lambda: history)
    assert verdict.passed, verdict.message


@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_failed_transient_restores_polarization_and_retry_matches_fresh(model):
    sim, _ = dielectric(model=model)
    sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]["valid"] and failed[-1]["time_s"] == 0.
    np.testing.assert_array_equal(failed[-1]["P"], failed[0]["P"])
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, _ = dielectric(model=model)
    direct = fresh.solve_transient()
    assert len(retry) == len(direct) and all(s["valid"] for s in retry)
    for actual, expected in zip(retry, direct):
        np.testing.assert_array_equal(actual["P"], expected["P"])
        np.testing.assert_array_equal(actual["phi"], expected["phi"])


@pytest.mark.parametrize("gamma", ["0.1", 1j, None, [], np.array([.1])])
def test_high_level_gamma_rejects_nonreal_scalars_consistently(gamma):
    from tcad.simulator import Simulator
    sim, _ = dielectric()
    host = type("Host", (), {"_sim": sim})()
    with pytest.raises(ValueError, match="gamma"):
        Simulator.set_transient(host, 1e-10, 1e-10, fe_gamma=gamma)


def test_lk_coarse_step_retains_metastable_branch_then_switches():
    dt, gamma, alpha, beta = 1e-7, .1, -1e8, 1e12
    sim, x = dielectric(dt=dt, final=dt, voltage=-.1)
    old = sim.solve_transient()[-1]["P"][0]
    assert old > 0.
    for voltage in (.001, .1):
        sim.set_dirichlet_potential({0: 0., 8: voltage})
        sim.set_initial_guess(voltage * x / x[-1], np.zeros(9), np.zeros(9))
        state = sim.solve_transient()[-1]
        assert state["valid"]
        roots = np.roots([beta, 0., alpha + gamma / dt,
                         -(gamma / dt * old - voltage / x[-1])])
        stable = [r.real for r in roots if abs(r.imag) < 1e-12 and
                  alpha + gamma / dt + 3 * beta * r.real**2 > 0.]
        expected = min(stable, key=lambda p: abs(p - old))
        assert state["P"][0] == pytest.approx(expected, rel=1e-12)
        if voltage == .001:
            assert expected > 0.
        else:
            assert expected < 0.
        old = state["P"][0]


def test_lk_imprint_and_extra_depolarization_enter_implicit_equation():
    sim, x = dielectric(final=1e-10)
    sim.set_ferroelectric_builtin_field(2e5)
    sim.set_ferroelectric_depol(30.)
    state = sim.solve_transient()[-1]
    assert state["valid"]
    roots = np.roots([1e12, 0., -1e8 + .1 / 1e-10 + 1 / (30 * 8.854187817e-12),
                     -(.1 / x[-1] - 2e5)])
    expected = next(r.real for r in roots if abs(r.imag) < 1e-12)
    np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], expected, rtol=1e-12)


@pytest.mark.parametrize("invalid", ["alpha", "beta_zero", "beta_nan", "imprint", "model", "initial"])
def test_invalid_fe_run_is_rejected_without_consuming_polarization(invalid):
    sim, x = dielectric(final=1e-10)
    reference, _ = dielectric(final=1e-10)
    before = sim.solve_transient()[-1]["P"]
    np.testing.assert_array_equal(reference.solve_transient()[-1]["P"], before)
    sim.set_transient_t_final(0.)
    if invalid == "alpha":
        with pytest.raises(ValueError, match="finite"):
            sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), np.nan, 1e12)
    elif invalid == "beta_nan":
        with pytest.raises(ValueError, match="finite"):
            sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), -1e8, np.nan)
    elif invalid == "beta_zero":
        sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), -1e8, 0.)
    elif invalid == "imprint":
        with pytest.raises(ValueError, match="finite"):
            sim.set_ferroelectric_builtin_field(np.nan)
    elif invalid == "model":
        sim.set_ferroelectric_model(4)
    else:
        with pytest.raises(ValueError):
            sim.set_initial_guess(np.full(9, np.nan), np.zeros(9), np.zeros(9))
    if invalid in ("beta_zero", "model"):
        with pytest.raises(ValueError):
            sim.solve_transient()
    sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_builtin_field(0.)
    sim.set_ferroelectric_model(0)
    sim.set_initial_guess(-.1 * x / x[-1], np.zeros(9), np.zeros(9))
    np.testing.assert_array_equal(sim.solve_transient()[0]["P"], before)
    sim.set_transient_t_final(1e-10)
    np.testing.assert_array_equal(sim.solve_transient()[-1]["P"],
                                  reference.solve_transient()[-1]["P"])


SENTAURUS = json.loads((Path(__file__).parent / "data" /
                       "sentaurus_preisach_history.json").read_text())


@pytest.mark.parametrize("case", SENTAURUS["cases"], ids=lambda c: c["name"])
def test_transient_preserves_nested_history_against_sentaurus(case):
    length = SENTAURUS["length_m"]
    sim, _ = dielectric(model=3, final=1e-10, gamma=0.,
                         positions=np.linspace(0., length, 9))
    scale = 2 * case["Ec"] / np.log((case["Ps"] + case["Pr"]) /
                                   (case["Ps"] - case["Pr"]))
    sim.set_ferroelectric_preisach(case["Ps"], case["Ec"], scale)
    for point in case["points"]:
        voltage = point["voltage_V"]
        sim.set_dirichlet_potential({0: voltage, 8: 0.})
        sim.set_initial_guess(np.linspace(voltage, 0., 9), np.zeros(9), np.zeros(9))
        state = sim.solve_transient()[-1]
        assert state["valid"]
        assert state["P"][12] == pytest.approx(point["polarization_C_per_m2"],
                                               rel=1e-6, abs=1e-9)
        # A snapshot-only call must not clear the appended turning-point stack.
        sim.set_transient_t_final(0.)
        np.testing.assert_array_equal(sim.solve_transient()[0]["P"], state["P"])
        sim.set_transient_t_final(1e-10)
