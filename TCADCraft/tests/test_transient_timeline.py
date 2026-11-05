"""Native backward-Euler time, failure and charge-ledger regressions."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.validation.conservation import TransientConservationTest

QE = float(native_constants()["elementary_charge_C"])


def slab(dt=1e-10, final=2.5e-10, doped=False, perturb=True):
    size = 11
    sim = PyDeviceSimulator(size, 1, 1, 1e-6, 1e-6, 1e-6)
    sim.set_newton_freeze_phi(True)  # Explicit fixed-field diffusion benchmark.
    sim.set_permittivity(np.full(size, 8.854187817e-12 * 11.7))
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(np.full(size, 1e16 if doped else 0.0))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.zeros(size))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_thermal_voltage(.025852)
    sim.set_dirichlet_potential({0: 0.0, size - 1: 0.0})
    sim.set_electron_bc({0: 1e16, size - 1: 1e16})
    sim.set_hole_bc({0: 1e16, size - 1: 1e16})
    n = np.full(size, 1e16)
    if perturb:
        n[1:-1] += 5e15 * np.sin(np.arange(1, size - 1) * np.pi / (size - 1))
    sim.set_initial_guess(np.zeros(size), n, np.full(size, 1e16))
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(final)
    return sim, n


@pytest.mark.parametrize("dt,final,expected", [
    (1e-10, 0.0, [0.0]),
    (1e-10, 3e-10, [0.0, 1e-10, 2e-10, 3e-10]),
    (1e-10, 2.5e-10, [0.0, 1e-10, 2e-10, 2.5e-10]),
    (1e-10, 3e-11, [0.0, 3e-11]),
    (1e-10, 1e-9, list(np.arange(11) * 1e-10)),
])
def test_time_zero_is_initial_and_last_step_hits_requested_end(dt, final, expected):
    sim, initial = slab(dt=dt, final=final)
    history = sim.solve_transient()
    np.testing.assert_allclose([s["time_s"] for s in history], expected, rtol=1e-14, atol=1e-25)
    np.testing.assert_array_equal(history[0]["n"], initial)
    assert history[0]["initial_state"]
    assert all(s["converged"] and s["valid"] for s in history)
    assert history[-1]["time_s"] == final
    assert sum(s["dt_s"] for s in history) == pytest.approx(final, rel=1e-14)
    for state in history[1:]:
        assert not state["initial_state"]
        assert 0 < state["dt_s"] <= dt * (1 + 1e-14)
    assert np.all(np.diff([s["time_s"] for s in history]) > 0)


def test_failed_attempt_retains_accepted_time_and_state_then_retry_matches_fresh():
    sim, initial = slab()
    sim.set_gummel_max_iter(0)
    history = sim.solve_transient()
    assert len(history) == 2
    rejected = history[-1]
    assert not rejected["valid"] and not rejected["converged"]
    assert rejected["time_s"] == 0.0 and rejected["dt_s"] == 0.0
    assert rejected["attempted_time_s"] == pytest.approx(1e-10)
    np.testing.assert_array_equal(rejected["n"], initial)
    np.testing.assert_array_equal(rejected["phi"], history[0]["phi"])
    assert not TransientConservationTest(integration="backward_euler").run(lambda: history).passed
    sim.set_gummel_max_iter(80)
    retried = sim.solve_transient()
    fresh, _ = slab()
    baseline = fresh.solve_transient()
    for actual, expected in zip(retried, baseline):
        np.testing.assert_array_equal(actual["n"], expected["n"])
        assert actual["time_s"] == expected["time_s"]


def test_native_diffusion_has_a_closed_mobile_charge_ledger():
    sim, _ = slab()
    history = sim.solve_transient()
    assert all(s["charge_ledger_available"] for s in history)
    assert all(not s["majority_frozen"] for s in history)
    result = TransientConservationTest(integration="backward_euler",
        charge_atol_C=0.0, tolerance=1e-3).run(lambda: history)
    assert result.passed, result.message
    # Audit the public charge from node densities independently of the core
    # summation: the two contact nodes belong to external reservoirs.
    for state in history:
        expected = QE * np.sum(state["p"][1:-1] - state["n"][1:-1]) * 1e-18
        assert state["stored_charge_C"] == pytest.approx(expected, rel=1e-12)
        assert state["terminal_currents_A"][0] == pytest.approx(
            1e-12 * (state["Jn_x"][0] + state["Jp_x"][0]), rel=1e-12)
    history[-1]["terminal_currents_A"] *= 2
    assert not TransientConservationTest(integration="backward_euler",
        charge_atol_C=0.0, tolerance=1e-3).run(lambda: history).passed


@pytest.mark.parametrize("dt,final", [(1e-10, 2.5e-10), (5e-10, 2e-9), (7e-10, 2e-9)])
def test_diffusion_eigenmode_matches_exact_backward_euler_with_partial_step(dt, final):
    sim, initial = slab(dt=dt, final=final)
    history = sim.solve_transient()
    # A sine is an eigenvector of the independently known Dirichlet discrete
    # Laplacian. Its BE amplitude uses each *actual* dt, including the last.
    eigenvalue = 4 * .1 * .025852 * np.sin(np.pi / 20) ** 2 / 1e-12
    amplitude = initial - 1e16
    for state in history:
        amplitude = amplitude / (1 + eigenvalue * state["dt_s"])
        np.testing.assert_allclose(state["n"], 1e16 + amplitude, rtol=2e-7, atol=1.0)


def test_high_level_transient_preserves_time_and_invalid_status():
    from types import SimpleNamespace
    from tcad.simulator import Simulator

    low, _ = slab()
    # Exercise the actual public run method with the already-configured native
    # slab, without rebuilding a separate mesh/material experiment.
    host = SimpleNamespace(_sim=low, _apply_cut_cell=lambda: None)
    history = Simulator.run_transient(host, max_iter=0)
    assert not host.results["valid"]
    assert host.results["time_s"] == 0.0
    assert host.results["attempted_time_s"] == history[-1]["attempted_time_s"]


def test_high_level_fe_damping_cannot_be_silently_ignored():
    from tcad.simulator import Simulator

    with pytest.raises(ValueError, match="unavailable"):
        Simulator.set_transient(object(), 1e-9, 2e-9, fe_gamma=1e-8)


@pytest.mark.parametrize("gamma", [-1.0, np.nan, np.inf, True])
def test_fe_transient_gamma_rejects_nonfinite_negative_and_boolean(gamma):
    from tcad.simulator import Simulator

    sim, _ = slab()
    host = type("TransientHost", (), {"_sim": sim, "_apply_cut_cell": lambda self: None})()
    with pytest.raises(ValueError, match="gamma"):
        Simulator.set_transient(host, 1e-9, 1e-9, fe_gamma=gamma)


def test_nls_fe_transient_advances_once_per_accepted_step_and_exposes_p():
    sim, initial = slab(dt=1e-9, final=2e-9, perturb=False)
    sim.set_newton_freeze_phi(False)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(initial.size, dtype=np.int8), -1e8, 1e18)
    sim.set_ferroelectric_model(2)
    sim.set_ferroelectric_preisach(0.2, 1e8, 0.0)
    sim.set_ferroelectric_nls(1e-12, 0.0, 1e-12)
    potential = np.linspace(0.0, 0.1, initial.size)
    sim.set_initial_guess(potential, np.full(initial.size, 1e16), np.full(initial.size, 1e16))
    sim.set_dirichlet_potential({0: 0.0, initial.size - 1: 0.1})
    from tcad.simulator import Simulator
    host = type("TransientHost", (), {"_sim": sim, "_apply_cut_cell": lambda self: None})()
    Simulator.set_transient(host, 1e-9, 2e-9, fe_gamma=0.0)
    history = Simulator.run_transient(host)
    assert len(history) == 3
    assert all(state["P"].shape == (3 * initial.size,) for state in history)
    assert all(np.all(np.isfinite(state["P"])) for state in history)
    assert np.max(np.abs(history[-1]["P"])) > 0.0
    assert np.allclose(history[0]["P"], 0.0)


def test_transient_hfs_flux_matches_its_continuity_model():
    sim, _ = slab(perturb=False)
    potential = np.linspace(0.0, .1, 11)
    sim.set_initial_guess(potential, np.full(11, 1e16), np.full(11, 1e16))
    sim.set_dirichlet_potential({0: 0.0, 10: .1})
    sim.set_high_field_saturation(True, 1e3, 1e3, 2.0, 2.0, 1)
    state = sim.solve_transient()[-1]
    assert state["converged"]
    field = -1e4
    expected = QE * 1e16 * .1 * field / np.sqrt(2.0)
    np.testing.assert_allclose(state["Jn_x"][:-1], expected, rtol=1e-12)


@pytest.mark.parametrize("positions", [np.array([0, .2, .7, 1.4, 2.5, 4, 5.8, 7, 8.3, 9.4, 10])*1e-6])
def test_nonuniform_free_node_volumes_in_native_charge_ledger(positions):
    sim, _ = slab()
    sim.set_x_positions(positions)
    history = sim.solve_transient()
    assert all(state["converged"] for state in history)
    volumes = (positions[2:] - positions[:-2]) * .5 * 1e-12
    for state in history:
        charge = QE * np.dot(state["p"][1:-1] - state["n"][1:-1], volumes)
        assert state["stored_charge_C"] == pytest.approx(charge, rel=1e-12)
    verdict = TransientConservationTest(integration="backward_euler",
        charge_atol_C=0.0, tolerance=1e-3).run(lambda: history)
    assert verdict.passed, verdict.message


def test_two_dimensional_complete_contact_planes_have_closed_ledger():
    """The charge ledger must cover finite-volume 2-D slabs, not only 1-D."""
    nx, ny, nz = 5, 3, 1
    size = nx * ny * nz
    sim = PyDeviceSimulator(nx, ny, nz, 1e-6, 2e-6, 1e-6)
    sim.set_permittivity(np.full(size, 8.854187817e-12 * 11.7))
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.zeros(size))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_thermal_voltage(.025852)
    # Complete x-min/x-max carrier-contact planes; y faces remain insulating.
    contacts = {}
    for j in range(ny):
        contacts[j * nx] = 1e16
        contacts[j * nx + nx - 1] = 1e16
    sim.set_dirichlet_potential({idx: 0.0 for idx in contacts})
    sim.set_electron_bc(contacts)
    sim.set_hole_bc(contacts)
    sim.set_initial_guess(np.zeros(size), np.full(size, 1e16), np.full(size, 1e16))
    sim.set_transient_dt(1e-10)
    sim.set_transient_t_final(0.0)

    history = sim.solve_transient()
    assert len(history) == 1
    state = history[0]
    assert state["charge_ledger_available"]
    assert state["charge_ledger_scope"].startswith("mobile free-node")
    assert state["terminal_currents_A"].shape == (2,)
    expected = QE * np.sum(
        state["p"].reshape(ny, nx)[:, 1:-1] - state["n"].reshape(ny, nx)[:, 1:-1]
    ) * 1e-6 * 2e-6 * 1e-6
    assert state["stored_charge_C"] == pytest.approx(expected, rel=1e-12, abs=0.0)


def test_uniform_doping_keeps_both_carriers_and_closed_charge_ledger():
    sim, _ = slab(doped=True, perturb=False)
    history = sim.solve_transient()
    assert history[-1]["converged"]
    assert all(not s["majority_frozen"] for s in history)
    assert all(s["charge_ledger_available"] for s in history)
    assert all("stored_charge_C" in s for s in history)
    verdict = TransientConservationTest(integration="backward_euler").run(lambda: history)
    assert verdict.passed, verdict.message


def test_immobile_carrier_rows_do_not_claim_closed_charge_ledger():
    sim, _ = slab(final=0.0)
    mobility = np.full(11, .1)
    mobility[5] = 0.0
    sim.set_mobility(mobility, np.full(11, .05))
    assert not sim.solve_transient()[0]["charge_ledger_available"]


@pytest.mark.parametrize("setting", ["dt", "final"])
@pytest.mark.parametrize("value", [-1.0, np.nan, np.inf])
def test_invalid_time_configuration_raises(setting, value):
    sim, _ = slab()
    with pytest.raises(ValueError, match="transient"):
        if setting == "dt":
            sim.set_transient_dt(value)
        else:
            sim.set_transient_t_final(value)


def test_zero_dt_is_rejected():
    sim, _ = slab()
    with pytest.raises(ValueError):
        sim.set_transient_dt(0.0)


@pytest.mark.parametrize("tolerance", [0.0, -1.0, np.nan, np.inf])
def test_invalid_transient_tolerance_cannot_accept_a_step(tolerance):
    sim, _ = slab()
    with pytest.raises(ValueError, match="tolerance"):
        sim.set_tolerance(tolerance)
    reference, _ = slab()
    history, expected = sim.solve_transient(), reference.solve_transient()
    assert all(state["valid"] for state in history)
    assert len(history) == len(expected)
    for actual, wanted in zip(history, expected):
        for field in ("phi", "n", "p"):
            np.testing.assert_array_equal(actual[field], wanted[field])


@pytest.mark.parametrize("model", ["quantum", "thermal", "btbt", "ii",
                                   "breakdown", "traps", "oxide_traps", "mobility"])
def test_unimplemented_enabled_physics_is_not_silently_ignored(model):
    sim, _ = slab()
    if model == "ferroelectric":
        sim.set_ferroelectric_enabled(True)
    elif model == "quantum":
        sim.set_quantum_enabled(True)
    elif model == "thermal":
        sim.set_thermal_coupling_enabled(True)
    elif model == "btbt":
        sim.set_btbt_enabled(True)
    elif model == "ii":
        sim.set_ii_enabled(True)
    elif model == "breakdown":
        sim.set_breakdown_enabled(True)
    elif model == "traps":
        sim.set_interface_traps(np.ones(11, dtype=np.int8), 1e11, 0.0)
    elif model == "oxide_traps":
        sim.set_oxide_traps(np.full(11, 1e-4))
    else:
        sim.set_mobility_model(1)
    with pytest.raises(ValueError, match="not implemented"):
        sim.solve_transient()
