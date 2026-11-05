"""A segment is accepted only after its FE readout succeeds."""
from copy import deepcopy
from contextlib import contextmanager

import numpy as np
import pytest

from tcad.physics.reliability import CyclingDegradation, TrapKinetics
from tcad.postprocess import fe_loops
from test_physical_step_commit import high_level
from test_fefet_validation import _FakeFESimulator


@pytest.mark.parametrize("driver", ["retention", "endurance"])
@pytest.mark.parametrize("failure_read", [1, 2, 3, 4])
@pytest.mark.parametrize("with_traps", [False, True])
def test_native_failed_readout_restores_only_failed_segment(
        monkeypatch, driver, failure_read, with_traps):
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["valid"]
    trap = TrapKinetics(1e16, capture_tau=1., emission_tau=2.) if with_traps else None
    damage = CyclingDegradation(reference_field=1e8, wakeup_cycles=4.,
                                fatigue_cycles=100.) if driver == "endurance" else None
    original_run = sim.run
    original_transaction = sim.reliability_transaction
    original_read = fe_loops._read_axial_polarization
    physical_calls, reads, segments = 0, 0, 0
    entry = {}

    @contextmanager
    def transaction(*models, **kwargs):
        nonlocal segments, entry
        segments += 1
        if segments == failure_read:
            entry = {
                    "results": deepcopy(sim.results),
                    "contacts": deepcopy(sim._contact_voltages),
                    "guess": deepcopy(sim._accepted_initial_guess),
                    "dwell": sim._fe_nls_dt,
                    "trap": deepcopy(trap.__dict__) if trap else None,
                    "damage": deepcopy(damage.__dict__) if damage else None,
            }
        with original_transaction(*models, **kwargs):
            yield

    def run(**kwargs):
        nonlocal physical_calls
        if kwargs.get("physical_step", True):
            physical_calls += 1
        return original_run(**kwargs)

    def read(*args, **kwargs):
        nonlocal reads
        reads += 1
        if reads == failure_read:
            raise ValueError("injected FE quadrature failure")
        return original_read(*args, **kwargs)

    sim.run = run
    sim.reliability_transaction = transaction
    monkeypatch.setattr(fe_loops, "_read_axial_polarization", read)
    with pytest.raises(fe_loops.ReliabilityStepError) as error:
        if driver == "retention":
            fe_loops.run_retention(sim, "right", 4., n_steps=3, dt=.2,
                                  program_width=.2, trap_model=trap,
                                  max_iter=300, tol=1e-8)
        else:
            fe_loops.run_endurance(sim, "right", 4., 40e-9, n_cycles=2,
                                  pulse_width=.2, trap_model=trap,
                                  degradation_model=damage, max_iter=300, tol=1e-8)
    assert error.value.completed_segments == failure_read - 1
    assert error.value.elapsed_time == pytest.approx((failure_read - 1)*.2)
    assert physical_calls == failure_read
    assert sim._contact_voltages == entry["contacts"]
    assert sim._fe_nls_dt == entry["dwell"]
    for key in ("phi", "P"):
        np.testing.assert_array_equal(sim.results[key], entry["results"][key])
    for actual, expected in zip(sim._accepted_initial_guess, entry["guess"]):
        np.testing.assert_array_equal(actual, expected)
    for model, name in ((trap, "trap"), (damage, "damage")):
        if model is not None:
            assert model.__dict__.keys() == entry[name].keys()
            for key, expected in entry[name].items():
                np.testing.assert_equal(model.__dict__[key], expected)
    # A frozen re-solve also audits restored native FE and oxide-charge state.
    sim.run = original_run
    retry = sim.run(max_iter=300, tol=1e-8, physical_step=False)
    for key in ("phi", "P"):
        np.testing.assert_allclose(retry[key], entry["results"][key], atol=1e-12)


@pytest.mark.parametrize("driver", ["retention", "endurance"])
@pytest.mark.parametrize("invalid", ["axis", "volume", "shape"])
def test_invalid_readout_cannot_commit_first_program(driver, invalid):
    sim = _FakeFESimulator()
    sim.mesh.fields = deepcopy(sim.mesh.fields)
    if invalid == "axis":
        sim._fe_polar_axis = 1.5
    elif invalid == "volume":
        sim.mesh.fields["control_volume"] = np.zeros(sim.mesh.npts())
    else:
        original_run = sim.run
        def wrong_shape(**kwargs):
            result = original_run(**kwargs)
            result["P"] = result["P"].T
            return result
        sim.run = wrong_shape
    trap = TrapKinetics(1e16)
    damage = CyclingDegradation()
    with pytest.raises(fe_loops.ReliabilityStepError) as error:
        if driver == "retention":
            fe_loops.run_retention(sim, "gate", 1., n_steps=1, dt=.1,
                                  trap_model=trap)
        else:
            fe_loops.run_endurance(sim, "gate", 1., 1e-8, n_cycles=1,
                                  trap_model=trap, degradation_model=damage)
    assert error.value.completed_segments == 0
    assert error.value.elapsed_time == 0.
    assert sim.voltage == 0.
    assert sim.qot_history == []
    assert trap.occupancy is None
    assert damage.cycles == 0


def test_endurance_reads_program_before_reused_result_is_erased():
    sim = _FakeFESimulator()
    original_run = sim.run
    shared_result = {}

    def run(**kwargs):
        shared_result.clear()
        shared_result.update(original_run(**kwargs))
        shared_result["P"][:, 2] = 1. if sim.voltage > 0 else -.25
        return shared_result

    sim.run = run
    output = fe_loops.run_endurance(sim, "gate", 1., 1e-8, n_cycles=2,
                                   measure_every=1, Q_ot_max=0.)
    np.testing.assert_allclose(output["Ps"], [.625, .625])
    np.testing.assert_allclose(output["Pr"], [.375, .375])
    assert output["completed_segments"] == 4
