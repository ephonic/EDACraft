"""Resolve small FE switching currents on top of a much larger static D."""

import numpy as np
import pytest

from tcad.postprocess import integrate_transient_terminal_history
from test_transient_displacement import film


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("dt", [1e-10, 1e-30, 1e-45])
@pytest.mark.parametrize("polarity", [-1, 1])
def test_nls_short_interval_current_retains_expm1_precision(axis, dt, polarity):
    sim, _, _, _, area = film(axis, 2, False, layered=False)
    sim.set_dirichlet_potential({0: 0., 8: -polarity * .01})
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(2.5 * dt)
    history = sim.solve_transient()
    previous_p = 0.
    for state in history[1:]:
        expected_p = polarity * 1e-6 * -np.expm1(-state["time_s"] / 1e-9)
        expected_j = (expected_p - previous_p) / state["dt_s"]
        expected_i = area * np.array([expected_j, -expected_j])
        assert state["valid"] and state["total_terminal_current_available"]
        np.testing.assert_allclose(state["electrode_total_currents_A"], expected_i, rtol=2e-12, atol=0.)
        np.testing.assert_allclose(state["electrode_polarization_currents_A"], expected_i, rtol=2e-12, atol=0.)
        np.testing.assert_array_equal(state["electrode_dielectric_currents_A"], 0.)
        np.testing.assert_allclose(state["electrode_charge_increments_C"], state["dt_s"] * expected_i,
                                   rtol=2e-12, atol=0.)
        previous_p = expected_p
    result = integrate_transient_terminal_history(history)
    expected_charge = area * polarity * 1e-6 * -np.expm1(-2.5 * dt / 1e-9)
    assert result["terminal_charge_C"][history[0]["electrode_names"][0]] == pytest.approx(
        expected_charge, rel=2e-12, abs=0.)
    assert result["supplied_energy_J"] == pytest.approx(polarity * .01 * expected_charge, rel=2e-12, abs=0.)
    for kind in ("displacement", "polarization"):
        component = integrate_transient_terminal_history(history, current_kind=kind)
        assert component["terminal_charge_C"][history[0]["electrode_names"][0]] == pytest.approx(
            expected_charge, rel=2e-12, abs=0.)
    dielectric = integrate_transient_terminal_history(history, current_kind="dielectric")
    assert dielectric["supplied_energy_J"] == 0.


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("ps", [1e-30, 1e-50])
@pytest.mark.parametrize("polarity", [-1, 1])
def test_small_switching_charge_survives_large_static_electrode_charge(axis, ps, polarity):
    sim, _, _, _, area = film(axis, 2, False, layered=False)
    sim.set_dirichlet_potential({0: 0., 8: -polarity * .01})
    sim.set_ferroelectric_preisach(ps, 1e5, 0.)
    history = sim.solve_transient()
    previous_p = 0.
    for state in history[1:]:
        expected_p = polarity * ps * -np.expm1(-state["time_s"] / 1e-9)
        expected_increment = area * np.array([expected_p - previous_p, previous_p - expected_p])
        expected_i = expected_increment / state["dt_s"]
        np.testing.assert_allclose(state["electrode_total_currents_A"], expected_i, rtol=2e-12, atol=0.)
        np.testing.assert_allclose(state["electrode_charge_increments_C"], expected_increment, rtol=2e-12, atol=0.)
        # The absolute charge cannot encode this addition in float64. Its
        # separately calculated increment must still be available in SI.
        np.testing.assert_array_equal(state["electrode_charges_C"], history[0]["electrode_charges_C"])
        previous_p = expected_p
    result = integrate_transient_terminal_history(history)
    expected_charge = area * polarity * ps * -np.expm1(-2.5e-10 / 1e-9)
    assert result["terminal_charge_C"][history[0]["electrode_names"][0]] == pytest.approx(
        expected_charge, rel=2e-12, abs=0.)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_layered_electric_and_polarization_current_components_match_independent_faces(axis):
    sim, x, eps, mask, area = film(axis, 2, True)
    history = sim.solve_transient()
    coefficient = 2 * eps[:-1] * eps[1:] / (eps[:-1] + eps[1:])
    for old, state in zip(history[:-1], history[1:]):
        delta_phi = state["phi"] - old["phi"]
        electric = -coefficient * np.diff(delta_phi) / np.diff(x) / state["dt_s"]
        delta_p = mask * (state["P"].reshape(-1, 3)[:, axis] - old["P"].reshape(-1, 3)[:, axis])
        polarization = coefficient * (delta_p[:-1] / eps[:-1] + delta_p[1:] / eps[1:]) / (2 * state["dt_s"])
        suffix = "xyz"[axis]
        np.testing.assert_allclose(state["Jdielectric_" + suffix][:-1], electric, rtol=1e-8, atol=1e-8)
        np.testing.assert_allclose(state["Jpolarization_" + suffix][:-1], polarization, rtol=1e-12, atol=1e-8)
        np.testing.assert_allclose(state["Jdisp_" + suffix][:-1], electric + polarization, rtol=1e-8, atol=1e-8)
        np.testing.assert_allclose(state["electrode_dielectric_currents_A"], area * np.array([electric[0], -electric[-1]]),
                                   rtol=1e-8, atol=1e-20)
        np.testing.assert_allclose(state["electrode_polarization_currents_A"], area * np.array([polarization[0], -polarization[-1]]),
                                   rtol=1e-12, atol=1e-20)
