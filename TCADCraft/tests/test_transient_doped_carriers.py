"""Doping must not discard a carrier continuity equation in transient mode."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.validation.conservation import TransientConservationTest


DT = 1e-10
VT = .025852
QE = float(native_constants()["elementary_charge_C"])


def doped_slab(carrier, scale, log_space, *, contacts=True, stretched=False):
    size = 11
    sim = PyDeviceSimulator(size, 1, 1, 1e-6, 1e-6, 1e-6)
    sim.set_newton_freeze_phi(True)  # These analytic references assume fixed E.
    sim.set_permittivity(np.full(size, 8.854187817e-12 * 11.7))
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(np.full(size, scale if carrier == "electron" else -scale))
    sim.set_effective_dos(np.full(size, scale), np.full(size, scale))
    sim.set_bandgap(np.zeros(size))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_newton_use_log_space(log_space)
    sim.set_dirichlet_potential({0: 0., size - 1: 0.})
    n = np.full(size, 2 * scale if carrier == "electron" else scale)
    p = np.full(size, 2 * scale if carrier == "hole" else scale)
    if contacts:
        sim.set_electron_bc({0: n[0], size - 1: n[-1]})
        sim.set_hole_bc({0: p[0], size - 1: p[-1]})
    x = np.arange(size) * 1e-6
    if stretched:
        x *= 1 + .1 * np.arange(size)
        sim.set_x_positions(x)
    sim.set_initial_guess(np.zeros(size), n, p)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    sim.set_transient_dt(DT)
    sim.set_transient_t_final(2.5 * DT)
    return sim, x, n, p


@pytest.mark.parametrize("carrier", ["electron", "hole"])
@pytest.mark.parametrize("scale", [1e16, 1e24])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("stretched", [False, True])
def test_doped_majority_diffuses_with_independent_be_solution(carrier, scale, log_space, stretched):
    sim, x, n, p = doped_slab(carrier, scale, log_space, stretched=stretched)
    initial = n if carrier == "electron" else p
    initial[1:-1] += .3 * scale * np.sin(np.pi * np.arange(1, 10) / 10)
    sim.set_initial_guess(np.zeros(11), n, p)
    history = sim.solve_transient()
    widths = np.r_[x[1] - x[0], (x[2:] - x[:-2]) / 2, x[-1] - x[-2]]
    diffusivity = (.1 if carrier == "electron" else .05) * VT
    operator = np.zeros((11, 11))
    for idx in range(1, 10):
        for neighbor in (idx - 1, idx + 1):
            rate = diffusivity / (abs(x[neighbor] - x[idx]) * widths[idx])
            operator[idx, idx] += rate
            operator[idx, neighbor] -= rate
    expected = initial.copy()
    assert len(history) == 4
    for state in history:
        assert state["valid"] and state["phi_frozen"]
        np.testing.assert_array_equal(state["phi"], np.zeros(11))
        expected = np.linalg.solve(np.eye(11) + state["dt_s"] * operator, expected)
        np.testing.assert_allclose(state["n" if carrier == "electron" else "p"], expected, rtol=2e-8)
        np.testing.assert_allclose(state["p" if carrier == "electron" else "n"], scale, rtol=1e-12)
        charge = QE * np.dot(state["p"][1:-1] - state["n"][1:-1], widths[1:-1] * 1e-12)
        if state["charge_ledger_available"]:
            assert state["stored_charge_C"] == pytest.approx(charge, rel=1e-12)
    assert all(not state["majority_frozen"] and state["charge_ledger_available"] for state in history)
    verdict = TransientConservationTest(integration="backward_euler", charge_atol_C=0.,
                                       tolerance=1e-5).run(lambda: history)
    assert verdict.passed, verdict.message


@pytest.mark.parametrize("carrier", ["electron", "hole"])
@pytest.mark.parametrize("scale", [1e16, 1e24])
@pytest.mark.parametrize("log_space", [False, True])
def test_uniform_optical_generation_creates_equal_electron_hole_pairs(carrier, scale, log_space):
    # Insulating carrier faces isolate generation from reservoir diffusion.
    sim, _, n, p = doped_slab(carrier, scale, log_space, contacts=False)
    generation = .1 * scale / DT
    sim.set_optical_generation(np.full(11, generation))
    history = sim.solve_transient()
    assert len(history) == 4
    for state in history:
        assert state["valid"]
        np.testing.assert_array_equal(state["phi"], np.zeros(11))
        np.testing.assert_allclose(state["n"], n + generation * state["time_s"], rtol=2e-9)
        np.testing.assert_allclose(state["p"], p + generation * state["time_s"], rtol=2e-9)
        np.testing.assert_allclose(state["p"] - state["n"], p - n, rtol=2e-9)
    assert all(not state["majority_frozen"] for state in history)


@pytest.mark.parametrize("carrier", ["electron", "hole"])
@pytest.mark.parametrize("scale", [1e16, 1e24])
@pytest.mark.parametrize("log_space", [False, True])
def test_uniform_srh_removes_equal_pairs_and_matches_nonlinear_be_root(carrier, scale, log_space):
    sim, _, n, p = doped_slab(carrier, scale, log_space, contacts=False)
    tau_n, tau_p = 2 * DT, 3 * DT
    sim.set_recombination(np.full(11, tau_n), np.full(11, tau_p))
    history = sim.solve_transient()
    nn, pp = n[0] / scale, p[0] / scale
    assert len(history) == 4
    for state in history:
        assert state["valid"]
        np.testing.assert_array_equal(state["phi"], np.zeros(11))
        if state["dt_s"]:
            dt = state["dt_s"]
            # Solve d/dt = [(n-d)(p-d)-ni^2] /
            # [tau_p(n-d+ni)+tau_n(p-d+ni)] with ni/scale=1.
            a = 1 + (tau_n + tau_p) / dt
            b = nn + pp + tau_p / dt * (nn + 1) + tau_n / dt * (pp + 1)
            c = nn * pp - 1
            loss = 2 * c / (b + np.sqrt(b * b - 4 * a * c))
            nn -= loss
            pp -= loss
        np.testing.assert_allclose(state["n"], nn * scale, rtol=2e-9)
        np.testing.assert_allclose(state["p"], pp * scale, rtol=2e-9)
        np.testing.assert_allclose(state["p"] - state["n"], p - n, rtol=2e-9)
    assert all(not state["majority_frozen"] for state in history)


@pytest.mark.parametrize("carrier", ["electron", "hole"])
@pytest.mark.parametrize("log_space", [False, True])
def test_srh_minority_accuracy_survives_sixteen_decades_of_density_range(carrier, log_space):
    sim, _, _, _ = doped_slab(carrier, 1e24, log_space, contacts=False)
    n0, p0 = (1e24, 5e8) if carrier == "electron" else (5e8, 1e24)
    sim.set_effective_dos(np.full(11, 1e16), np.full(11, 1e16))
    sim.set_initial_guess(np.zeros(11), np.full(11, n0), np.full(11, p0))
    tau_n, tau_p = 2 * DT, 3 * DT
    sim.set_recombination(np.full(11, tau_n), np.full(11, tau_p))
    history = sim.solve_transient()
    nn, pp = np.longdouble(n0), np.longdouble(p0)
    assert len(history) == 4
    for state in history:
        assert state["valid"] and not state["majority_frozen"]
        dt = state["dt_s"]
        if dt:
            a = 1 + (tau_n + tau_p) / dt
            b = nn + pp + tau_p / dt * (nn + 1e16) + tau_n / dt * (pp + 1e16)
            c = nn * pp - np.longdouble(1e16) ** 2
            loss = 2 * c / (b + np.sqrt(b * b - 4 * a * c))
            nn -= loss
            pp -= loss
        np.testing.assert_allclose(state["n"], float(nn), rtol=2e-9)
        np.testing.assert_allclose(state["p"], float(pp), rtol=2e-9)
