"""Public conservation checks must not certify malformed DC/time-domain ledgers."""

import numpy as np
import pytest

from tcad.validation.conservation import ConservationTest, TransientConservationTest


INVALID_SCALARS = [None, np.nan, np.inf, np.array(1.0 + 9.0j),
                   "invalid", 2**2000]
INVALID_IDS = ["none", "nan", "infinite", "complex", "text", "overflow"]


def energy_state():
    return dict(converged=True, energy_initial=1.0, energy_final=1.0,
                energy_components_initial_J={"stored": 1.0},
                energy_components_final_J={"stored": 1.0},
                energy_components_supplied_J={"source": 0.0},
                energy_components_dissipated_J={"loss": 0.0})


@pytest.mark.parametrize("name", ["energy_initial", "energy_final",
                                  "energy_supplied", "energy_dissipated"])
@pytest.mark.parametrize("bad", INVALID_SCALARS, ids=INVALID_IDS)
def test_valid_components_cannot_hide_invalid_energy_total(name, bad):
    state = energy_state()
    state[name] = bad
    assert not ConservationTest(check_charge=False).run(lambda: state).passed


def charge_states():
    return [dict(converged=True, time_s=t, stored_charge_C=0.0,
                 stored_charge_components_C={"mobile": 0.0},
                 terminal_currents_A=[1.0, -1.0]) for t in (0.0, 1.0)]


@pytest.mark.parametrize("bad", INVALID_SCALARS + [[0.0, 0.0]],
                         ids=INVALID_IDS + ["nonscalar"])
def test_valid_components_cannot_hide_invalid_charge_total(bad):
    states = charge_states()
    states[-1]["stored_charge_C"] = bad
    assert not TransientConservationTest().run(lambda: states).passed


@pytest.mark.parametrize("currents", [
    np.array([1 + 2j, -1 + 0j]), np.array([1 + 0j, -1 + 0j]),
    [2**2000, 0], np.array([1 + 2j, -1 + 0j], dtype=object),
    [1.0, np.nan], [1.0, np.inf]],
    ids=["imaginary", "complex_dtype", "overflow", "object_complex", "nan", "inf"])
@pytest.mark.parametrize("transient", [False, True])
def test_invalid_terminal_currents_fail_as_validation_results(currents, transient):
    if transient:
        states = charge_states()
        states[-1]["terminal_currents_A"] = currents
        result = TransientConservationTest().run(lambda: states)
    else:
        result = ConservationTest(check_energy=False).run(
            lambda: dict(converged=True, terminal_currents_A=currents))
    assert not result.passed


@pytest.mark.parametrize("name", ["time_s", "stored_charge_components_C",
                                  "charge_density_C_per_m3", "cell_volumes_m3"])
def test_complex_transient_fields_cannot_drop_imaginary_parts(name):
    states = charge_states()
    if name == "stored_charge_components_C":
        states[-1][name] = {"mobile": np.array(0.0 + 2j)}
    elif name in ("charge_density_C_per_m3", "cell_volumes_m3"):
        for state in states:
            state.pop("stored_charge_C")
            state.pop("stored_charge_components_C")
            state.update(charge_density_C_per_m3=[0.0], cell_volumes_m3=[1.0])
        states[-1][name] = np.array([2j if name.startswith("charge") else 1 + 2j])
    else:
        states[-1][name] = np.array(1 + 2j)
    assert not TransientConservationTest().run(lambda: states).passed


@pytest.mark.parametrize("name", ["energy_components_initial_J", "entropy_production"])
def test_complex_energy_or_entropy_cannot_be_certified_as_real(name):
    state = energy_state()
    if name == "entropy_production":
        state[name] = np.array(1 + 2j)
    else:
        state[name] = {"stored": np.array(1 + 2j)}
    check = ConservationTest(check_charge=False, check_entropy=name == "entropy_production")
    assert not check.run(lambda: state).passed


@pytest.mark.parametrize("exponent", [-1074, -1060, -1022, -1000, -100, -20, 0])
@pytest.mark.parametrize("kind", ["steady", "energy", "transient"])
@pytest.mark.parametrize("balanced", [False, True])
def test_relative_balance_has_no_implicit_unit_dependent_floor(exponent, kind, balanced):
    # Powers of two keep this independent prescribed ledger exactly representable,
    # including the smallest IEEE-754 binary64 value. No solver is involved.
    value = float(np.ldexp(1.0, exponent))
    if kind == "steady":
        check = ConservationTest(check_energy=False, current_atol_A=0.0)
        state = dict(converged=True, terminal_currents_A=[value, -value if balanced else 0.0])
    elif kind == "energy":
        check = ConservationTest(check_charge=False)
        state = dict(converged=True, energy_initial=value,
                     energy_final=value if balanced else 0.0)
    else:
        check = TransientConservationTest(charge_atol_C=0.0)
        state = [dict(converged=True, time_s=t, stored_charge_C=t*value,
                      terminal_currents_A=[value if balanced else 0.0, 0.0])
                 for t in (0.0, 1.0)]
    result = check.run(lambda: state)
    assert result.passed == balanced
    metric = "energy_violation" if kind == "energy" else "charge_violation"
    assert result.details[metric] == (0.0 if balanced else 1.0)


def test_absent_totals_still_allow_complete_component_only_ledgers():
    state = energy_state()
    state.pop("energy_initial")
    state.pop("energy_final")
    assert ConservationTest(check_charge=False).run(lambda: state).passed
    states = charge_states()
    for snapshot in states:
        snapshot.pop("stored_charge_C")
    assert TransientConservationTest().run(lambda: states).passed


def test_explicit_absolute_current_budget_still_applies_to_subnormal_values():
    state = dict(converged=True, terminal_currents_A=[np.nextafter(0.0, 1.0), 0.0])
    assert ConservationTest(check_energy=False).run(lambda: state).passed
