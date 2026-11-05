"""Independent face D, electrode charge and backward-Euler Ampere checks."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.postprocess import integrate_transient_terminal_history
from test_transient_selfconsistent import central_cell
from test_transient_multidimensional_ledger import CASES, experiment


EPS0 = 8.854187817e-12
QE = float(native_constants()["elementary_charge_C"])


def film(axis, model, stretched, layered=True):
    shape = [1, 1, 1]
    shape[axis] = 9
    spacings = [2e-7, 3e-7, 4e-7]
    spacings[axis] = 1e-8
    sim = PyDeviceSimulator(*shape, *spacings)
    sim.set_transient_lk_coupled(False)  # This fixture retains historical split equations.
    x = (np.array([0., .2, .7, 1.4, 2.5, 4., 5.8, 7., 8.]) if stretched
         else np.arange(9)) * 1e-8
    [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions][axis](x)
    eps = EPS0 * (10 + np.arange(9)) if layered else np.full(9, EPS0 * 20)
    mask = np.zeros(9, dtype=np.int8) if layered else np.ones(9, dtype=np.int8)
    if layered:
        mask[2:7] = 1
    sim.set_permittivity(eps)
    sim.set_mobility(np.zeros(9), np.zeros(9))
    sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9, 1e16), np.full(9, 1e16))
    sim.set_bandgap(np.full(9, 6.))
    sim.set_recombination(np.full(9, 1e100), np.full(9, 1e100))
    sim.set_dirichlet_potential({0: 0., 8: -.01})
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(mask, -1e8, 1e12)
    sim.set_ferroelectric_model(model)
    sim.set_ferroelectric_preisach(1e-6, 1e5, 0.)
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_nls(1e-9, 0., 1e-15)
    sim.set_ferroelectric_gamma(.1 if model == 0 else 0.)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-11)
    sim.set_transient_dt(1e-10)
    sim.set_transient_t_final(2.5e-10)
    area = np.prod([spacings[a] for a in range(3) if a != axis])
    return sim, x, eps, mask, area


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("model", [0, 1, 2, 3])
@pytest.mark.parametrize("stretched", [False, True])
def test_layered_fe_face_displacement_electrode_charge_and_total_current(axis, model, stretched):
    sim, x, eps, mask, area = film(axis, model, stretched)
    history = sim.solve_transient()
    assert len(history) == 4
    previous_d = None
    charge_integral = np.zeros(2)
    for state in history:
        assert state["valid"] and state["electrode_charge_available"]
        assert not state["charge_ledger_available"]  # Pure dielectric, zero mobility.
        assert state["electrostatic_flux_available"]
        assert state["electrode_names"] == ["xyz"[axis] + "_min", "xyz"[axis] + "_max"]
        np.testing.assert_array_equal(state["electrode_voltages_V"], [0., -.01])
        harmonic = 2 * eps[:-1] * eps[1:] / (eps[:-1] + eps[1:])
        polarization = mask * state["P"].reshape(-1, 3)[:, axis]
        bound = harmonic * (polarization[:-1] / eps[:-1] + polarization[1:] / eps[1:]) / 2
        electric = -harmonic * np.diff(state["phi"]) / np.diff(x)
        expected_d = electric + bound
        np.testing.assert_allclose(state["D_" + "xyz"[axis]][:-1], expected_d, rtol=1e-10, atol=1e-17)
        np.testing.assert_allclose(expected_d, expected_d[0], rtol=1e-10, atol=1e-17)
        charges = area * np.array([expected_d[0], -expected_d[-1]])
        np.testing.assert_allclose(state["electrode_charges_C"], charges, rtol=1e-10, atol=1e-30)
        if state["dt_s"]:
            expected_j = (expected_d - previous_d) / state["dt_s"]
            assert state["displacement_current_available"] and state["total_terminal_current_available"]
            np.testing.assert_allclose(state["Jdisp_" + "xyz"[axis]][:-1], expected_j,
                                       rtol=1e-8, atol=1e-7)
            np.testing.assert_array_equal(state["electrode_conduction_currents_A"], 0.)
            expected_i = area * np.array([expected_j[0], -expected_j[-1]])
            np.testing.assert_allclose(state["electrode_total_currents_A"], expected_i, rtol=1e-8, atol=1e-20)
            np.testing.assert_allclose(state["electrode_displacement_currents_A"], expected_i, rtol=1e-8, atol=1e-20)
            charge_integral += state["dt_s"] * state["electrode_total_currents_A"]
            assert abs(sum(state["electrode_total_currents_A"])) < 1e-10 * max(abs(expected_i)) + 1e-22
        else:
            assert not state["displacement_current_available"] and not state["total_terminal_current_available"]
            assert "electrode_total_currents_A" not in state and "Jdisp_x" not in state
        previous_d = expected_d
    np.testing.assert_allclose(charge_integral,
                               history[-1]["electrode_charges_C"] - history[0]["electrode_charges_C"],
                               rtol=1e-10, atol=1e-30)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_uniform_nls_total_current_matches_analytic_polarization_derivative(axis):
    sim, x, eps, _, area = film(axis, 2, False, layered=False)
    history = sim.solve_transient()
    previous_p = 0.
    for state in history:
        expected_p = 1e-6 * -np.expm1(-state["time_s"] / 1e-9)
        expected_d = eps[0] * .01 / x[-1] + expected_p
        np.testing.assert_allclose(state["electrode_charges_C"], [area * expected_d, -area * expected_d], rtol=1e-12)
        if state["dt_s"]:
            expected_i = area * (expected_p - previous_p) / state["dt_s"]
            np.testing.assert_allclose(state["electrode_total_currents_A"], [expected_i, -expected_i], rtol=1e-12)
        previous_p = expected_p


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("scale", [1e16, 1e24])
@pytest.mark.parametrize("log_space", [False, True])
def test_space_charge_conduction_and_displacement_obey_ampere(scale, log_space, axis):
    sim, x, _, _ = central_cell(scale, log_space, axis, True)
    history = sim.solve_transient()
    for previous, state in zip(history[:-1], history[1:]):
        assert state["total_terminal_current_available"]
        np.testing.assert_allclose(state["electrode_conduction_currents_A"], state["terminal_currents_A"], rtol=1e-12)
        derivative = (state["electrode_charges_C"] - previous["electrode_charges_C"]) / state["dt_s"]
        np.testing.assert_allclose(state["electrode_displacement_currents_A"], derivative, rtol=2e-8, atol=1e-25)
        total = state["electrode_total_currents_A"]
        assert abs(sum(total)) < 1e-7 * max(abs(state["electrode_conduction_currents_A"]))
        delta_q = state["stored_charge_C"] - previous["stored_charge_C"]
        assert delta_q == pytest.approx(-state["dt_s"] * sum(state["electrode_displacement_currents_A"]), rel=1e-7)


@pytest.mark.parametrize("shape,planes", CASES)
@pytest.mark.parametrize("stretched", [False, True])
def test_multidimensional_electrodes_satisfy_gauss_and_ampere(shape, planes, stretched):
    sim, coords, axes, widths, contacts, _, _ = experiment(shape, planes, stretched)
    sim.set_newton_freeze_phi(False)
    history = sim.solve_transient()
    volumes = np.prod(np.array([widths[a][coords[:, a]] for a in range(3)]), axis=0)
    for state in history:
        assert state["electrode_charge_available"] and state["valid"]
        expected_q = QE * np.dot(state["p"][~contacts] - state["n"][~contacts], volumes[~contacts])
        assert -sum(state["electrode_charges_C"]) == pytest.approx(expected_q, rel=1e-7, abs=1e-29)
        if state["dt_s"]:
            assert state["total_terminal_current_available"]
            total = state["electrode_total_currents_A"]
            conduction = state["electrode_conduction_currents_A"]
            np.testing.assert_allclose(conduction, state["terminal_currents_A"], rtol=1e-12, atol=1e-28)
            assert abs(sum(total)) < 1e-6 * max(abs(conduction)) + 1e-28


@pytest.mark.parametrize("invalid", ["frozen", "partial", "nonuniform_voltage", "fraction", "carrier_layout", "asymmetric_edges"])
def test_total_terminal_scope_does_not_claim_unsupported_electrodes(invalid):
    sim, *_ = central_cell(1e16, False, 0, False)
    if invalid == "frozen":
        sim.set_newton_freeze_phi(True)
    elif invalid == "partial":
        # An extra internal reference is not a complete outer electrode plane.
        sim.set_dirichlet_potential({1: .001})
    elif invalid == "nonuniform_voltage":
        sim, *_ = experiment((5, 4, 1), [(0, False), (0, True)], False)
        sim.set_newton_freeze_phi(False)
        sim.set_dirichlet_potential({5: .001})
    elif invalid == "fraction":
        sim.set_charge_volume_fraction(np.array([1., .5, 1.]))
    elif invalid == "carrier_layout":
        sim.set_electron_bc({1: 1e16})
    else:
        sim.set_edge_permittivity(np.full(3, EPS0 * 12), np.full(3, EPS0 * 13),
                                 np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3))
    history = sim.solve_transient()
    assert all(not state["total_terminal_current_available"] for state in history)
    assert all("electrode_total_currents_A" not in state for state in history)


def test_failed_attempt_cannot_export_a_displacement_current_interval():
    sim, *_ = central_cell(1e16, False, 0, True)
    sim.set_gummel_max_iter(0)
    initial, failed = sim.solve_transient()
    assert not failed["valid"] and failed["dt_s"] == 0.
    assert failed["electrode_charge_available"]
    np.testing.assert_array_equal(failed["electrode_charges_C"], initial["electrode_charges_C"])
    assert not failed["displacement_current_available"] and not failed["total_terminal_current_available"]
    assert "electrode_total_currents_A" not in failed
    with pytest.raises(ValueError, match="valid/converged"):
        integrate_transient_terminal_history([initial, failed])


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_reciprocal_edge_overrides_are_used_in_electrode_displacement(axis):
    sim, x, eps, mask, area = film(axis, 2, True)
    coefficient = 1.1 * 2 * eps[:-1] * eps[1:] / (eps[:-1] + eps[1:])
    arrays = [np.zeros(9) for _ in range(6)]
    arrays[2 * axis][:-1] = coefficient
    arrays[2 * axis + 1][1:] = coefficient
    sim.set_edge_permittivity(*arrays)
    for state in sim.solve_transient():
        assert state["valid"] and state["electrode_charge_available"]
        p = mask * state["P"].reshape(-1, 3)[:, axis]
        expected = coefficient * (-np.diff(state["phi"]) / np.diff(x) +
                                  .5 * (p[:-1] / eps[:-1] + p[1:] / eps[1:]))
        np.testing.assert_allclose(state["D_" + "xyz"[axis]][:-1], expected, rtol=1e-10, atol=1e-17)
        np.testing.assert_allclose(state["electrode_charges_C"], area * np.array([expected[0], -expected[-1]]),
                                   rtol=1e-10)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_native_be_history_integral_matches_analytic_nls_charge_and_source_work(axis):
    sim, _, _, _, area = film(axis, 2, False, layered=False)
    history = sim.solve_transient()
    result = integrate_transient_terminal_history(history)
    names = history[0]["electrode_names"]
    expected = area * 1e-6 * -np.expm1(-2.5e-10 / 1e-9)
    assert result["terminal_charge_C"][names[0]] == pytest.approx(expected, rel=1e-12)
    assert result["terminal_charge_C"][names[1]] == pytest.approx(-expected, rel=1e-12)
    assert result["supplied_energy_J"] == pytest.approx(.01 * expected, rel=1e-12)
    assert result["absorbed_energy_J"] == pytest.approx(.01 * expected, rel=1e-12)
    assert result["returned_energy_J"] == 0.
    assert result["integration_kind"] == "backward_euler_endpoint_voltage_and_current"
    assert not result["energy_balance_validated"] and not result["physical_validated"]
    conduction = integrate_transient_terminal_history(history, current_kind="conduction")
    assert conduction["supplied_energy_J"] == 0.


@pytest.mark.parametrize("change", ["failed", "missing_availability", "numeric_status", "scope",
    "backward_time", "wrong_dt", "nan_current", "complex_voltage", "duplicate_names",
    "reordered_names", "wrong_shape", "wrong_initial", "missing_current", "boolean_dt",
    "repeated_initial", "overflow"])
def test_native_history_integral_rejects_invalid_intervals(change):
    sim, *_ = film(0, 2, False, layered=False)
    history = sim.solve_transient()
    state = history[1]
    if change == "failed":
        state["valid"] = False
    elif change == "missing_availability":
        del state["total_terminal_current_available"]
    elif change == "numeric_status":
        state["converged"] = 1
    elif change == "scope":
        state["electrode_charge_available"] = False
    elif change == "backward_time":
        state["time_s"] = 0.
    elif change == "wrong_dt":
        state["dt_s"] *= 2
    elif change == "nan_current":
        state["electrode_total_currents_A"][0] = np.nan
    elif change == "complex_voltage":
        state["electrode_voltages_V"] = state["electrode_voltages_V"].astype(complex)
    elif change == "duplicate_names":
        state["electrode_names"] = ["x_min", "x_min"]
    elif change == "reordered_names":
        state["electrode_names"] = state["electrode_names"][::-1]
    elif change == "wrong_shape":
        state["electrode_total_currents_A"] = np.zeros(3)
    elif change == "wrong_initial":
        history[0]["dt_s"] = 1e-10
    elif change == "missing_current":
        del state["electrode_total_currents_A"]
    elif change == "boolean_dt":
        state["dt_s"] = True
    elif change == "repeated_initial":
        state["initial_state"] = True
    else:
        state["electrode_total_currents_A"][:] = 1e308
        state["electrode_voltages_V"][:] = 1e308
    with pytest.raises(ValueError):
        integrate_transient_terminal_history(history)
