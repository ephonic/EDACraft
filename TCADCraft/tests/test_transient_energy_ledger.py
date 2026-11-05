"""Scoped composition checks for the transient energy-component ledger."""

from copy import deepcopy

import numpy as np
import pytest

import tcad.postprocess as postprocess
from test_transient_voltage_waveforms import driven_film


def test_linear_dielectric_component_and_source_work_are_reported_separately():
    sim, *_ = driven_film()
    history = sim.solve_transient()
    report = postprocess.audit_transient_energy_ledger(
        history, rtol=1e-10, require_source_work=True)
    assert report["valid"]
    assert report["energy_balance_validated"]
    assert report["energy_balance_scope"] == "linear_lossless_charge_free_dielectric"
    assert report["complete_device_energy"] is False
    assert report["component_presence"] == {
        "dielectric": True, "lk": False, "terminal_source_work": True,
    }
    assert report["component_reports"]["dielectric"]["energy_balance_validated"]
    assert report["terminal_source_work"]["current_kind"] == "total"
    assert report["physical_validated"] is False
    assert "carrier_dissipation" in report["missing_physics"]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_lk_component_does_not_claim_total_device_closure(axis):
    sim, *_ = driven_film(axis, model=0, fe=True)
    history = sim.solve_transient()
    report = postprocess.audit_transient_energy_ledger(history)
    assert report["valid"]
    assert report["component_presence"]["lk"]
    assert not report["component_presence"]["dielectric"]
    assert report["energy_balance_validated"] is False
    assert report["complete_device_energy"] is False
    assert report["component_reports"]["lk"]["lk_kinetics_validated"]


def test_missing_component_is_rejected_instead_of_being_zero_filled():
    sim, *_ = driven_film()
    history = sim.solve_transient()
    broken = deepcopy(history)
    broken[1]["dielectric_energy_available"] = False
    with pytest.raises(ValueError, match="consistent"):
        postprocess.audit_transient_energy_ledger(broken)


def test_missing_terminal_work_can_be_explicitly_allowed_but_is_reported():
    sim, *_ = driven_film()
    history = sim.solve_transient()
    broken = deepcopy(history)
    for state in broken:
        state["total_terminal_current_available"] = False
        state.pop("electrode_total_currents_A", None)
    report = postprocess.audit_transient_energy_ledger(broken)
    assert report["valid"]
    assert report["terminal_source_work"] is None
    assert report["component_presence"]["terminal_source_work"] is False
    with pytest.raises(ValueError, match="source work"):
        postprocess.audit_transient_energy_ledger(broken, require_source_work=True)


def test_invalid_error_budget_is_forwarded_to_component_audit():
    sim, *_ = driven_film()
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(sim.solve_transient(), rtol=1.)


def test_non_mapping_and_empty_histories_are_rejected():
    with pytest.raises(ValueError, match="initial state"):
        postprocess.audit_transient_energy_ledger([])
    with pytest.raises(ValueError, match="mappings"):
        postprocess.audit_transient_energy_ledger([{}, []])


def test_no_native_energy_scope_is_rejected():
    history = [{
        "dielectric_energy_available": False,
        "lk_energy_available": False,
    }] * 2
    with pytest.raises(ValueError, match="scope"):
        postprocess.audit_transient_energy_ledger(history)


def storage_history():
    """An independent two-joule change on a large static energy background."""
    common = dict(valid=True, converged=True, dielectric_energy_available=True,
                  dielectric_energy_scope="linear_lossless_charge_free_dielectric",
                  lk_energy_available=False, total_terminal_current_available=False)
    return [dict(common, time_s=0., dt_s=0., attempted_time_s=0., initial_state=True,
                 dielectric_energy_J=1e12, dielectric_energy_increment_available=False),
            dict(common, time_s=1., dt_s=1., attempted_time_s=1., initial_state=False,
                 dielectric_energy_J=1e12+2., dielectric_energy_increment_available=True,
                 dielectric_energy_increment_J=2.)]


@pytest.mark.parametrize("change", ["failed", "not_converged", "numeric_valid", "negative_energy",
    "initial_time", "initial_dt", "initial_attempt", "initial_flag", "initial_increment",
    "endpoint_initial", "numeric_initial", "endpoint_dt", "endpoint_time", "attempt",
    "nan_time", "missing_status", "missing_attempt"])
def test_storage_without_source_rejects_invalid_status_clock_and_energy(change):
    history = storage_history()
    initial, state = history
    if change == "failed": state["valid"] = False
    elif change == "not_converged": state["converged"] = False
    elif change == "numeric_valid": state["valid"] = 1
    elif change == "negative_energy": state["dielectric_energy_J"] = -1.
    elif change == "initial_time": initial["time_s"] = 1.
    elif change == "initial_dt": initial["dt_s"] = 1.
    elif change == "initial_attempt": initial["attempted_time_s"] = 1.
    elif change == "initial_flag": initial["initial_state"] = False
    elif change == "initial_increment": initial["dielectric_energy_increment_J"] = 0.
    elif change == "endpoint_initial": state["initial_state"] = True
    elif change == "numeric_initial": state["initial_state"] = 0
    elif change == "endpoint_dt": state["dt_s"] = 2.
    elif change == "endpoint_time": state["time_s"] = 0.
    elif change == "attempt": state["attempted_time_s"] = 2.
    elif change == "nan_time": state["time_s"] = np.nan
    elif change == "missing_status": del state["valid"]
    else: del state["attempted_time_s"]
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(history)


@pytest.mark.parametrize("rtol,atol", [(True, 0.), (0., 0.), (1., 0.), (np.nan, 0.),
    (np.inf, 0.), (1e-8, -1.), (1e-8, True), (1e-8, np.nan), (1e-8, np.inf)])
def test_storage_without_source_rejects_invalid_budgets(rtol, atol):
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(storage_history(), rtol=rtol, atol_J=atol)


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], np.array([False])])
def test_require_source_work_is_a_strict_boolean(value):
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(storage_history(), require_source_work=value)


def test_storage_increment_defect_cannot_hide_in_large_background():
    history = storage_history()
    assert postprocess.audit_transient_energy_ledger(history)["valid"]
    history[1]["dielectric_energy_increment_J"] = 2.02
    report = postprocess.audit_transient_energy_ledger(history)
    assert not report["valid"]
    assert not report["energy_balance_validated"]
    assert report["component_reports"]["dielectric"]["max_storage_relative_residual"] > .008


@pytest.mark.parametrize("change", ["missing_current", "nan_current", "wrong_shape", "voltage"])
def test_available_lk_source_work_cannot_be_silently_dropped(change):
    sim, *_ = driven_film(model=0, fe=True)
    history = sim.solve_transient()
    state = history[1]
    if change == "missing_current": del state["electrode_total_currents_A"]
    elif change == "nan_current": state["electrode_total_currents_A"][0] = np.nan
    elif change == "wrong_shape": state["electrode_total_currents_A"] = np.zeros(1)
    else: state["electrode_voltages_V"] = np.array([np.nan, 0.])
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(history)


@pytest.mark.parametrize("change", ["initial_interval", "partial_intervals", "mixed_scopes"])
def test_inconsistent_native_component_scopes_are_rejected(change):
    sim, *_ = driven_film(model=0, fe=True)
    history = sim.solve_transient()
    if change == "initial_interval": history[0]["total_terminal_current_available"] = True
    elif change == "partial_intervals": history[1]["total_terminal_current_available"] = False
    else:
        for state in history:
            state["dielectric_energy_available"] = True
    with pytest.raises(ValueError):
        postprocess.audit_transient_energy_ledger(history)


def test_storage_only_report_distinguishes_consistency_from_energy_closure():
    history = storage_history()
    report = postprocess.audit_transient_energy_ledger(history)
    component = report["component_reports"]["dielectric"]
    assert report["valid"] and component["storage_consistency_validated"]
    assert component["stored_energy_change_J"] == 2.
    assert component["max_storage_relative_residual"] == 0.
    np.testing.assert_array_equal(component["interval_storage_consistency_residuals_J"], [0.])
    assert component["interval_energy_balance_residuals_J"] is None
    assert component["energy_balance_residual_J"] is None
    assert not report["energy_balance_validated"]
    assert report["energy_balance_scope"] is None
    assert report["terminal_source_work"] is None


def test_storage_only_rounding_allowance_does_not_claim_subresolution_accuracy():
    history = storage_history()
    # Two snapshots resolve no change, while a native increment may be smaller
    # than their float64 spacing. Only consistency, never closure, is audited.
    history[1]["dielectric_energy_J"] = history[0]["dielectric_energy_J"]
    history[1]["dielectric_energy_increment_J"] = 1e-6
    report = postprocess.audit_transient_energy_ledger(history)
    assert report["valid"] and not report["energy_balance_validated"]
    assert report["component_reports"]["dielectric"]["stored_energy_change_J"] == 1e-6


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
def test_capacitor_storage_consistency_is_identical_with_or_without_source(axis, stretched):
    sim, x, epsilon, _, area = driven_film(axis, stretched=stretched, layered=True)
    history = sim.solve_transient()
    with_source = postprocess.audit_transient_energy_ledger(history)
    # Independent series-capacitor energy, with harmonic face permittivity.
    face = 2*epsilon[:-1]*epsilon[1:]/(epsilon[:-1]+epsilon[1:])
    capacitance = area/sum(np.diff(x)/face)
    for state in history:
        voltage = state["electrode_voltages_V"][1]
        assert state["dielectric_energy_J"] == pytest.approx(
            .5*capacitance*voltage**2, rel=1e-12, abs=0.)
        state["total_terminal_current_available"] = False
        state.pop("electrode_total_currents_A", None)
    storage_only = postprocess.audit_transient_energy_ledger(history)
    assert with_source["valid"] and storage_only["valid"]
    assert with_source["energy_balance_validated"] and not storage_only["energy_balance_validated"]
    full = with_source["component_reports"]["dielectric"]
    component = storage_only["component_reports"]["dielectric"]
    np.testing.assert_array_equal(full["interval_storage_consistency_residuals_J"],
                                  component["interval_storage_consistency_residuals_J"])
    assert full["max_storage_relative_residual"] == component["max_storage_relative_residual"]


def test_lk_without_terminals_retains_local_kinetics_validation_only():
    sim, *_ = driven_film(model=0, fe=True)
    history = sim.solve_transient()
    for state in history:
        state["total_terminal_current_available"] = False
    report = postprocess.audit_transient_energy_ledger(history, require_source_work=np.bool_(False))
    assert report["valid"] and report["component_reports"]["lk"]["lk_kinetics_validated"]
    assert report["terminal_source_work"] is None
    assert not report["energy_balance_validated"]
    with pytest.raises(ValueError, match="source work"):
        postprocess.audit_transient_energy_ledger(history, require_source_work=np.bool_(True))


def test_storage_absolute_noise_budget_is_explicit_and_increment_scaled():
    history = storage_history()
    history[1]["dielectric_energy_increment_J"] = 2.02
    rejected = postprocess.audit_transient_energy_ledger(history, atol_J=.01)
    accepted = postprocess.audit_transient_energy_ledger(history, atol_J=.02)
    assert not rejected["valid"] and accepted["valid"]
    assert not accepted["energy_balance_validated"]


@pytest.mark.parametrize("api", [postprocess.audit_transient_dielectric_energy,
                                postprocess.audit_transient_energy_ledger])
@pytest.mark.parametrize("initial", [False, True])
def test_direct_and_composed_dielectric_audits_reject_wrong_attempted_time(api, initial):
    sim, *_ = driven_film()
    history = sim.solve_transient()
    history[0 if initial else 1]["attempted_time_s"] = 99.
    with pytest.raises(ValueError):
        api(history)

