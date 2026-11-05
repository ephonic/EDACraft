"""Accepted segment bookkeeping, rollback and independent history oracles."""
from copy import deepcopy
import math

import numpy as np
import pytest

from tcad.physics.reliability import CyclingDegradation, TrapKinetics
from tcad.physics.ferro_kinetics import FieldHistoryCyclingState
from tcad.postprocess.fe_loops import run_endurance, run_retention
from test_physical_step_commit import high_level, native, N
from test_fefet_validation import _FakeFESimulator


def traps():
    return TrapKinetics(1e16, capture_tau=1., emission_tau=2.)


def test_fatigue_accumulates_piecewise_exposure_without_healing():
    model = CyclingDegradation(reference_field=1., field_exponent=2.,
                               fatigue_cycles=100.)
    model.advance(10., 3.)
    earlier = model.fatigue_state
    model.advance(10., .1)
    expected = -math.expm1(-(10*9 + 10*.01)/100.)
    assert model.fatigue_state >= earlier
    assert model.fatigue_state == pytest.approx(expected, abs=1e-15)


def test_cycling_history_order_and_subdivision():
    segments = [(10., 3.), (20., -.2), (5., 1.5)]
    models = [CyclingDegradation(reference_field=1., fatigue_cycles=100.)
              for _ in range(3)]
    for duration, field in segments:
        models[0].advance(duration, field)
        for _ in range(10):
            models[1].advance(duration/10, field)
    for duration, field in reversed(segments):
        models[2].advance(duration, field)
    expected = -math.expm1(-sum(t*e**2 for t,e in segments)/100.)
    for model in models:
        assert model.fatigue_state == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 1e308])
def test_invalid_cycling_stress_does_not_mutate(value):
    model = CyclingDegradation(reference_field=1.)
    model.advance(2., 1.)
    state = deepcopy(model.__dict__)
    with pytest.raises(ValueError):
        model.advance(1., value)
    assert model.__dict__ == state


@pytest.mark.parametrize("temperature", [0., -1., np.nan, np.inf])
@pytest.mark.parametrize("initialized", [False, True])
def test_invalid_temperature_does_not_initialize_or_resize_traps(temperature, initialized):
    model = traps()
    if initialized:
        model.initialize(3, .8)
    before = deepcopy(model.occupancy)
    with pytest.raises(ValueError):
        model.advance(np.ones(4), 0., .1, temperature)
    if before is None:
        assert model.occupancy is None
    else:
        np.testing.assert_array_equal(model.occupancy, before)


@pytest.mark.parametrize("name", ["trap_energy", "activation_energy", "field_acceleration"])
def test_nonfinite_trap_parameters_are_rejected(name):
    with pytest.raises(ValueError):
        TrapKinetics(1e20, **{name: np.nan})


@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_native_checkpoint_restores_hidden_fe_history_and_charge(model):
    trial, reference = native(model=model), native(model=model)
    def pulse(sim, voltage):
        sim.set_dirichlet_potential({0:0., N-1:voltage})
        result = sim.solve()
        assert result["converged"]
        return result
    for voltage in [0., 4., -2., 1.]:
        pulse(trial, voltage); pulse(reference, voltage)
    trial.begin_reliability_transaction()
    trial.set_oxide_traps(np.full(N, 1e-3))
    trial.set_ferroelectric_preisach(.12, 8e7, 5e7)
    trial.set_ferroelectric_builtin_field(1e7)
    trial.set_ferroelectric_nls(.5, 0., .2)
    pulse(trial, -4.)
    trial.rollback_reliability_transaction()
    for voltage in [1., .5, -1., 2., -4., 4.]:
        actual, expected = pulse(trial, voltage), pulse(reference, voltage)
        for key in ("phi", "P"):
            np.testing.assert_allclose(actual[key], expected[key], atol=1e-12, rtol=1e-12)


def test_native_nested_transaction_commit_and_rollback():
    sim, reference = native(), native()
    for core in (sim, reference):
        assert core.solve()["converged"]
    sim.begin_reliability_transaction()
    sim.set_dirichlet_potential({0:0., N-1:4.})
    assert sim.solve()["converged"]
    sim.begin_reliability_transaction()
    sim.set_dirichlet_potential({0:0., N-1:-4.})
    assert sim.solve()["converged"]
    sim.commit_reliability_transaction()
    sim.rollback_reliability_transaction()
    np.testing.assert_allclose(sim.solve()["P"], reference.solve()["P"], atol=1e-12)
    for name in ("commit_reliability_transaction", "rollback_reliability_transaction"):
        with pytest.raises(RuntimeError, match="no active"):
            getattr(sim, name)()


@pytest.mark.parametrize("failure_call", [1, 2, 3, 4])
@pytest.mark.parametrize("failure_kind", ["invalid", "exception"])
def test_retention_failed_segment_restores_fe_traps_contacts_and_guesses(failure_call, failure_kind):
    sim, reference = high_level(), high_level()
    for core in (sim, reference):
        assert core.run(max_iter=300, tol=1e-8)["valid"]
    model, ref_model = traps(), traps()
    # Calls 1/2 program + frozen charge helper, 3/4 first retention hold.
    accepted = 0 if failure_call <= 2 else 1
    if accepted:
        # Independent direct program + trap update, with no hold appended.
        reference.set_ferroelectric_nls_dwell_time(.2)
        reference.update_contact("right", 4.)
        r = reference.run(max_iter=300, tol=1e-8)
        ref_model = traps()
        q = ref_model.advance(r["phi"], np.hypot(np.hypot(r["Ex"],r["Ey"]),r["Ez"]), .2)
        reference.set_oxide_traps(q)
        reference.run(max_iter=300, tol=1e-8, physical_step=False)
    before_p = reference.results["P"].copy()
    before_guess = deepcopy(reference._accepted_initial_guess)
    before_contacts = deepcopy(reference._contact_voltages)
    actual_run = sim.run
    calls = 0
    def injected(**kwargs):
        nonlocal calls
        calls += 1
        result = actual_run(**kwargs)
        if calls == failure_call:
            if failure_kind == "exception":
                raise RuntimeError("injected after native solve")
            result["valid"] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as failure:
        run_retention(sim, "right", 4., n_steps=2, dt=.1, program_width=.2,
                      trap_model=model, max_iter=300, tol=1e-8)
    assert failure.value.completed_segments == accepted
    assert failure.value.elapsed_time == pytest.approx(.2 * accepted)
    np.testing.assert_array_equal(sim.results["P"], before_p)
    assert sim._contact_voltages == before_contacts
    for actual, expected in zip(sim._accepted_initial_guess, before_guess):
        np.testing.assert_array_equal(actual, expected)
    if accepted:
        np.testing.assert_array_equal(model.occupancy, ref_model.occupancy)
    else:
        assert model.occupancy is None
    # Retry a physical pulse: no ghost dwell or residual oxide charge.
    sim.run = actual_run
    for core in (sim, reference):
        core.set_ferroelectric_nls_dwell_time(.1)
        core.update_contact("right", -2.)
    actual, expected = sim.run(max_iter=300,tol=1e-8), reference.run(max_iter=300,tol=1e-8)
    for key in ("phi", "P"):
        np.testing.assert_allclose(actual[key], expected[key], atol=1e-12, rtol=1e-12)


@pytest.mark.parametrize("model_class", [CyclingDegradation, FieldHistoryCyclingState])
@pytest.mark.parametrize("failure_call", [1, 2, 3, 4])
def test_endurance_failure_keeps_only_accepted_half_cycles(model_class, failure_call):
    sim = high_level()
    sim.run(max_iter=300,tol=1e-8)
    model = model_class(reference_field=1e8, wakeup_cycles=4., fatigue_cycles=100.)
    trap_model = traps()
    actual_run = sim.run
    calls = 0
    def injected(**kwargs):
        nonlocal calls
        calls += 1
        result = actual_run(**kwargs)
        if calls == failure_call:
            result["converged"] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as failure:
        run_endurance(sim,"right",4.,40e-9,n_cycles=2,measure_every=1,
                      trap_model=trap_model,degradation_model=model,
                      pulse_width=.2,max_iter=300,tol=1e-8)
    accepted = 0 if failure_call <= 2 else 1
    assert failure.value.completed_segments == accepted
    assert failure.value.elapsed_time == pytest.approx(.2 * accepted)
    assert model.cycles == accepted
    reference = model_class(reference_field=1e8,wakeup_cycles=4.,fatigue_cycles=100.)
    if accepted:
        reference.advance(1.,1e8)
    assert model.wakeup_state == pytest.approx(reference.wakeup_state)
    assert model.fatigue_state == pytest.approx(reference.fatigue_state)
    if not accepted:
        assert trap_model.occupancy is None
        assert sim._contact_voltages["right"] == 0.


def test_measurement_cadence_adds_no_pulses_or_damage():
    outputs = []
    for cadence in [1, 3]:
        sim = high_level()
        model = FieldHistoryCyclingState(reference_field=1e8,wakeup_cycles=4.,fatigue_cycles=100.)
        out = run_endurance(sim,"right",4.,40e-9,n_cycles=3,measure_every=cadence,
                            degradation_model=model,Q_ot_max=0.,pulse_width=.2,
                            max_iter=300,tol=1e-8)
        assert model.cycles == 6
        assert out["elapsed_time"] == pytest.approx(1.2)
        assert out["completed_segments"] == 6
        assert sim._fe_nls_dt == .2
        outputs.append((out,sim.results))
    for key in ("Ps", "Pr", "memory_window", "active_fraction"):
        assert outputs[0][0][key][-1] == pytest.approx(outputs[1][0][key][-1],abs=1e-12)
    np.testing.assert_allclose(outputs[0][1]["P"],outputs[1][1]["P"],atol=1e-12)


@pytest.mark.parametrize("kind", ["converged", "valid", "target_reached", "physical_step_accepted",
                                  "missing_phi", "nan_phi", "missing_P", "nan_P", "missing_Ex", "nan_Ez"])
def test_invalid_protocol_data_never_advance_traps(kind):
    sim, model = _FakeFESimulator(), traps()
    actual_run = sim.run
    def injected(**kwargs):
        result = actual_run(**kwargs)
        if kind.startswith("missing_"):
            del result[kind[8:]]
        elif kind.startswith("nan_"):
            result[kind[4:]].flat[0] = np.nan
        else:
            result[kind] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as failure:
        run_retention(sim,"gate",1.,n_steps=2,dt=.1,trap_model=model)
    assert failure.value.completed_segments == 0
    assert model.occupancy is None
    assert sim.qot_history == []


def test_endurance_dynamic_charge_helpers_do_not_add_dwell():
    sim = high_level()
    model = traps()
    out = run_endurance(sim,"right",4.,40e-9,n_cycles=1,measure_every=1,
                        trap_model=model,pulse_width=.2,max_iter=300,tol=1e-8)
    a = math.exp(-.2)
    # Uniform NLS tau=1: one negative and one positive target, exactly 2 dwells.
    expected = -.2*(1-a)*a + .2*(1-a)
    assert out["elapsed_time"] == pytest.approx(.4)
    np.testing.assert_allclose(sim.results["P"][:,0], expected, atol=1e-12)


def test_charge_helper_rejection_restores_committed_breakdown():
    sim = high_level()
    sim._sim.set_breakdown_enabled(True)
    sim._sim.set_breakdown_params(np.ones(N,dtype=np.int8),np.full(N,5e7),0.)
    assert sim.run(max_iter=300,tol=1e-8)["valid"]
    assert not np.any(sim._sim.breakdown_state())
    actual_run = sim.run
    saw_breakdown = []
    def injected(**kwargs):
        result = actual_run(**kwargs)
        saw_breakdown.append(np.count_nonzero(sim._sim.breakdown_state()))
        if not kwargs.get("physical_step", True):
            raise RuntimeError("reject trap-charge helper")
        return result
    sim.run = injected
    model = traps()
    with pytest.raises(RuntimeError):
        run_retention(sim,"right",4.,n_steps=1,dt=.1,
                      trap_model=model,max_iter=300,tol=1e-8)
    assert max(saw_breakdown) == N
    assert not np.any(sim._sim.breakdown_state())
    assert model.occupancy is None
    sim.run = actual_run
    sim.update_contact("right",4.)
    assert sim.run(max_iter=300,tol=1e-8)["valid"]
    assert np.count_nonzero(sim._sim.breakdown_state()) == N


def test_retention_constant_field_trap_trajectory_matches_closed_form():
    # Equal capture/emission tau makes the exact rate bias independent.
    sim = _FakeFESimulator()
    model = TrapKinetics(1e20,capture_tau=2.,emission_tau=2.)
    out = run_retention(sim,"gate",1.,n_steps=5,dt=.1,
                        program_width=.3,trap_model=model)
    f_program = 1/(1+math.exp(-1/(8.617333262e-5*300)))
    programmed = f_program + (.5-f_program)*math.exp(-.3/2)
    expected = .5 + (programmed-.5)*np.exp(-out["times"]/2)
    np.testing.assert_allclose(out["trap_occupancy"],expected,atol=1e-15)
    np.testing.assert_allclose(out["Q_ot"],-1.602176634e-19*1e20*(expected-.5),atol=1e-14)
    assert out["elapsed_time"] == pytest.approx(.8)


def test_failed_first_program_restores_uninitialized_state_and_retries_once():
    sim, reference = high_level(), high_level()
    original_contacts = deepcopy(sim._contact_voltages)
    actual_run = sim.run
    def rejected(**kwargs):
        result = actual_run(**kwargs)
        result["valid"] = False
        return result
    sim.run = rejected
    with pytest.raises(RuntimeError) as failure:
        run_retention(sim,"right",4.,n_steps=1,dt=.1,program_width=.2,
                      max_iter=300,tol=1e-8)
    assert failure.value.completed_segments == 0
    assert sim.results is None
    assert sim._accepted_initial_guess is None
    assert sim._contact_voltages == original_contacts
    sim.run = actual_run
    for core in (sim, reference):
        core.set_ferroelectric_nls_dwell_time(.2)
        core.set_contact("right",4.)
    actual = sim.run(max_iter=300,tol=1e-8)
    expected = reference.run(max_iter=300,tol=1e-8)
    np.testing.assert_allclose(actual["P"],expected["P"],atol=1e-12)


def test_transaction_restores_model_arrays_without_aliasing():
    sim = high_level()
    sim.run(max_iter=300,tol=1e-8)
    model = traps()
    model.initialize(N,.7)
    original = model.occupancy.copy()
    external_trial = None
    with pytest.raises(RuntimeError):
        with sim.reliability_transaction(model):
            external_trial = model.occupancy
            model.occupancy[:] = .1
            raise RuntimeError("reject candidate")
    external_trial[:] = .2
    np.testing.assert_array_equal(model.occupancy,original)


@pytest.mark.parametrize("count", [True, 1.5, np.nan])
def test_invalid_protocol_counts_fail_before_physical_state_changes(count):
    sim = _FakeFESimulator()
    with pytest.raises(ValueError):
        run_retention(sim,"gate",1.,n_steps=count)
    for name in ("n_cycles", "measure_every"):
        with pytest.raises(ValueError):
            run_endurance(sim,"gate",1.,1e-8,**{name:count})
    assert sim.voltage == 0.
    assert sim.qot_history == []
