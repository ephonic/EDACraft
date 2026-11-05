"""Reject invalid protocols before the first physical operation."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.physics.reliability import CyclingDegradation, TrapKinetics
from tcad.postprocess.fe_loops import run_endurance, run_retention
from test_fefet_validation import _FakeFESimulator


BAD_SCALARS = [True, "0.1", [0.1], 1j, np.nan, np.inf]


def reject_before_run(driver, overrides):
    sim = _FakeFESimulator()
    trap = TrapKinetics(1e16)
    damage = CyclingDegradation()
    before_damage = deepcopy(damage.__dict__)
    calls = []
    original_run = sim.run

    def run(**kwargs):
        calls.append(kwargs)
        if len(calls) > 2:
            raise RuntimeError("invalid protocol attempted a third solve")
        return original_run(**kwargs)

    sim.run = run
    if driver == "retention":
        options = dict(V_program=1., n_steps=1, dt=.1, trap_model=trap)
        options.update(overrides)
        with pytest.raises(ValueError):
            run_retention(sim, "gate", **options)
    else:
        options = dict(V_pulse=1., fe_thickness=1e-8, n_cycles=1,
                       pulse_width=.1, trap_model=trap, degradation_model=damage)
        options.update(overrides)
        with pytest.raises(ValueError):
            run_endurance(sim, "gate", **options)
    assert calls == []
    assert sim.voltage == 0.
    assert sim.qot_history == []
    assert trap.occupancy is None
    assert damage.__dict__ == before_damage


@pytest.mark.parametrize("name", ["V_program", "dt", "program_width", "temperature", "tol"])
@pytest.mark.parametrize("value", BAD_SCALARS)
def test_retention_requires_real_protocol_scalars(name, value):
    reject_before_run("retention", {name: value})


@pytest.mark.parametrize("name", ["V_pulse", "fe_thickness", "pulse_width", "fatigue_Nc",
                                  "Q_ot_max", "temperature", "tol", "E_bd"])
@pytest.mark.parametrize("value", BAD_SCALARS)
def test_endurance_requires_real_protocol_scalars(name, value):
    options = {name: value}
    if name == "E_bd":
        options["legacy_breakdown_scaling"] = True
    reject_before_run("endurance", options)


@pytest.mark.parametrize("driver", ["retention", "endurance"])
@pytest.mark.parametrize("value", [True, 0, 1.5, "10"])
def test_solver_iteration_budget_is_preflighted(driver, value):
    reject_before_run(driver, {"max_iter": value})


@pytest.mark.parametrize("driver,options", [
    ("retention", {"dt": 0.}),
    ("retention", {"program_width": -1.}),
    ("retention", {"temperature": 0.}),
    ("retention", {"tol": 0.}),
    ("retention", {"dt": 1e308, "n_steps": 2}),
    ("retention", {"dt": 1e308, "program_width": 1e308}),
    ("retention", {"n_steps": 10**400}),
    ("endurance", {"tol": 0.}),
    ("endurance", {"pulse_width": 1e308}),
    ("endurance", {"V_pulse": 1e308, "fe_thickness": 1e-308}),
    ("endurance", {"n_cycles": 10**400}),
    ("endurance", {"n_cycles": np.int64(2**62), "pulse_width": 1e308}),
    ("endurance", {"V_pulse": 5e-324, "fe_thickness": 1e308}),
    ("endurance", {"legacy_breakdown_scaling": True, "E_bd": 1e-320}),
])
def test_derived_duration_and_stress_must_be_finite(driver, options):
    reject_before_run(driver, options)


@pytest.mark.parametrize("value", [1, "false", [False], None])
def test_legacy_breakdown_switch_requires_boolean(value):
    reject_before_run("endurance", {"legacy_breakdown_scaling": value})


def test_subnormal_legacy_fatigue_scale_has_finite_saturated_limit():
    output = run_endurance(_FakeFESimulator(), "gate", 1., 1e-8,
                           n_cycles=1, pulse_width=.1, fatigue_Nc=5e-324,
                           legacy_breakdown_scaling=True, E_bd=2e8, Q_ot_max=0.)
    # E/Ebd=.5 and saturated fatigue: half of the original plateau remains.
    np.testing.assert_allclose(output["Ps"], [.5])
    np.testing.assert_allclose(output["memory_window"], [.5])
    assert output["elapsed_time"] == pytest.approx(.2)


def test_small_fatigue_increment_is_not_lost_before_field_scaling():
    output = run_endurance(_FakeFESimulator(), "gate", 1., 1e-8,
                           n_cycles=1, pulse_width=.1, fatigue_Nc=1e18,
                           legacy_breakdown_scaling=True, E_bd=1e8/3e15, Q_ot_max=0.)
    # First-order fatigue=1/(.3e18), multiplied by E/Ebd=3e15: loss=.01.
    np.testing.assert_allclose(output["Ps"], [.99], rtol=0., atol=1e-15)


def test_disabled_legacy_scaling_does_not_use_legacy_field_parameter():
    output = run_endurance(_FakeFESimulator(), "gate", 1., 1e-8, n_cycles=1,
                           Q_ot_max=0., E_bd=np.nan, legacy_breakdown_scaling=np.bool_(False))
    assert output["valid"]
    assert output["legacy_breakdown_scaling"] is False


@pytest.mark.parametrize("voltage", [-1., 0., 1.])
def test_retention_accepts_signed_and_zero_program_voltage(voltage):
    output = run_retention(_FakeFESimulator(), "gate", np.float64(voltage),
                           n_steps=np.int64(2), dt=np.float64(.1),
                           max_iter=np.int64(5), tol=np.float64(1e-8))
    assert output["valid"]
    np.testing.assert_allclose(output["times"], [.1, .2])
    assert output["elapsed_time"] == pytest.approx(.3)
