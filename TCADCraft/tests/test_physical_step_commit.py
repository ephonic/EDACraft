"""Numerical voltage helpers consume no FE dwell or irreversible stress."""
import math

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator


N = 9
PS = 0.2


def native(model=2, newton=False):
    sim = PyDeviceSimulator(N, 1, 1, 40e-9/(N-1), 1, 1)
    sim.set_permittivity(np.full(N, 9*8.854187817e-12))
    sim.set_mobility(np.zeros(N), np.zeros(N))
    sim.set_doping(np.zeros(N))
    sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
    sim.set_bandgap(np.full(N, 6.0))
    sim.set_thermal_voltage(0.02585)
    sim.set_electron_bc({0:0., N-1:0.})
    sim.set_hole_bc({0:0., N-1:0.})
    sim.set_dirichlet_potential({0:0., N-1:0.})
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(N,dtype=np.int8), -5e8,1.25e10)
    sim.set_ferroelectric_model(model)
    sim.set_ferroelectric_preisach(PS,1e8,1e8)
    sim.set_ferroelectric_nls(1.,0.,.1)
    sim.set_use_newton(newton)
    sim.set_gummel_max_iter(300)
    sim.set_tolerance(1e-8)
    return sim


def high_level(initial_voltage=0., model="nls"):
    mesh = StructuredGrid(((0,40e-9),(0,1),(0,1)),N,1,1)
    mesh.fields.update({"doping":np.zeros(N), "mu_n":np.zeros(N),
                        "mu_p":np.zeros(N), "Eg":np.full(N,6.)})
    mesh.fields["contact_left"] = np.arange(N)==0
    mesh.fields["contact_right"] = np.arange(N)==N-1
    sim = Simulator(mesh)
    sim._sim.set_permittivity(np.full(N,9*8.854187817e-12))
    sim._sim.set_mobility(np.zeros(N),np.zeros(N))
    sim._sim.set_effective_dos(np.full(N,2.8e25),np.full(N,1.04e25))
    sim._sim.set_bandgap(np.full(N,6.))
    sim._sim.set_electron_bc({0:0.,N-1:0.})
    sim._sim.set_hole_bc({0:0.,N-1:0.})
    sim.set_ferroelectric(model=model,Ps=PS,Ec=1e8,Escale=1e8,
                          nls_tau0=1.,nls_E0=0.,nls_dt=.1,
                          polar_axis="x",fe_mask_override=np.ones(N,dtype=np.int8))
    sim.set_contact("left",0.)
    sim.set_contact("right",initial_voltage)
    return sim


def test_auto_continuation_consumes_one_nls_dwell():
    sim = high_level()
    assert sim.run(max_iter=300,tol=1e-8)["converged"]
    sim.update_contact("right",4.)
    result = sim.run(max_iter=300,tol=1e-8)
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)
    assert result["continuation_steps"] == 40
    assert result["continuation_helper_solves"] == 39
    assert result["physical_step_accepted"]


def test_initial_zero_bias_seed_consumes_no_dwell():
    sim = high_level(initial_voltage=4.)
    result = sim.run(max_iter=300,tol=1e-8)
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)
    assert result["continuation_helper_solves"] == 40


def test_explicit_pulses_each_consume_the_requested_dwell():
    sim = high_level(initial_voltage=4.)
    for pulse in range(1,4):
        result = sim.run(max_iter=300,tol=1e-8)
        assert result["converged"]
        np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1*pulse)),atol=1e-12)
    sim.set_ferroelectric_nls_dwell_time(.2)
    result = sim.run(max_iter=300,tol=1e-8)
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.5)),atol=1e-12)


def test_explicit_electrical_helper_does_not_advance_memory():
    sim = high_level(initial_voltage=4.)
    result = sim.run(max_iter=300,tol=1e-8,physical_step=False)
    assert result["converged"] and not result["physical_step_accepted"]
    np.testing.assert_array_equal(result["P"],0.)
    assert result["phi"][-1] == pytest.approx(4.)
    final = sim.run(max_iter=300,tol=1e-8)
    np.testing.assert_allclose(final["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


@pytest.mark.parametrize("model",[0,1,2,3])
@pytest.mark.parametrize("newton",[False,True])
def test_native_helpers_keep_p_and_hidden_branch_history(model,newton):
    tested, reference = native(model,newton),native(model,newton)
    for sim in (tested,reference):
        assert sim.solve()["converged"]
        sim.set_dirichlet_potential({0:0.,N-1:8.})
        first=sim.solve()
        assert first["converged"]
    before=first["P"].copy()
    tested.set_history_updates_enabled(False)
    for voltage in (-12.,12.,-4.):
        tested.set_dirichlet_potential({0:0.,N-1:voltage})
        helper=tested.solve()
        assert helper["converged"]
        np.testing.assert_array_equal(helper["P"],before)
        assert helper["phi"][-1] == pytest.approx(voltage)
    tested.set_history_updates_enabled(True)
    for sim in (tested,reference):
        sim.set_dirichlet_potential({0:0.,N-1:-8.})
    actual,expected = tested.solve(),reference.solve()
    assert actual["converged"] and expected["converged"]
    np.testing.assert_allclose(actual["P"],expected["P"],atol=1e-12,rtol=1e-12)


@pytest.mark.parametrize("newton",[False,True])
def test_frozen_memory_retains_bound_charge_in_electrical_solve(newton):
    sim=native(2,newton)
    mask=np.zeros(N,dtype=np.int8); mask[2:-2]=1
    sim.set_ferroelectric_params(mask,-5e8,1.25e10)
    assert sim.solve()["converged"]
    sim.set_dirichlet_potential({0:0.,N-1:8.})
    programmed=sim.solve()
    assert programmed["converged"]
    polarization=programmed["P"][:,0]
    assert np.max(np.abs(polarization))>1e-3
    # Independent charge-free continuum integral: D=eps*E+P is constant,
    # so dphi/dx=(P-D)/eps. Do not route the reference through another
    # Poisson assembly or the oxide-trap charge-sign convention.
    dx=40e-9/(N-1)
    eps=9*8.854187817e-12
    face_p=(polarization[:-1]+polarization[1:])/2
    displacement=(8*eps+np.sum(face_p)*dx)/(40e-9)
    expected=np.r_[0.,np.cumsum((face_p-displacement)*dx/eps)]
    sim.set_history_updates_enabled(False)
    sim.set_dirichlet_potential({0:0.,N-1:-8.})
    actual=sim.solve()
    assert actual["converged"]
    np.testing.assert_array_equal(actual["P"],programmed["P"])
    np.testing.assert_allclose(actual["phi"],expected,atol=1e-7,rtol=1e-7)
    assert np.max(np.abs(actual["phi"]-np.linspace(0,-8,N)))>1e-2


def test_failed_electrical_attempt_cannot_create_irreversible_breakdown():
    sim=native()
    sim.set_ferroelectric_enabled(False)
    sim.set_breakdown_enabled(True)
    sim.set_breakdown_params(np.ones(N,dtype=np.int8),np.full(N,1e7),1e-4)
    accepted = sim.solve()
    assert accepted["converged"]
    # Exhaust the solve budget while supplying a high-field trial iterate.
    # Its plausible field is not evidence that the equations were accepted.
    sim.set_gummel_max_iter(0)
    sim.set_dirichlet_potential({0:0.,N-1:8.})
    trial_phi = np.linspace(0,8,N)
    trial_phi[N//2] += 1.0  # Nonzero curvature violates charge-free Poisson.
    sim.set_initial_guess(trial_phi,accepted["n"],accepted["p"])
    for _ in range(3):
        failed=sim.solve()
        assert not failed["converged"]
        np.testing.assert_array_equal(sim.breakdown_state(),0)
    sim.set_gummel_max_iter(300)
    sim.set_initial_guess(accepted["phi"],accepted["n"],accepted["p"])
    assert sim.solve()["converged"]
    assert sim.breakdown_state().max()==1


def test_numerical_helpers_keep_existing_breakdown_and_do_not_add_damage():
    sim=native()
    sim.set_ferroelectric_enabled(False)
    sim.set_breakdown_enabled(True)
    mask=np.zeros(N,dtype=np.int8); mask[:4]=1
    sim.set_breakdown_params(mask,np.full(N,1e7),1e-4)
    assert sim.solve()["converged"]
    sim.set_history_updates_enabled(False)
    sim.set_dirichlet_potential({0:0.,N-1:8.})
    assert sim.solve()["converged"]
    np.testing.assert_array_equal(sim.breakdown_state(),0)
    sim.set_history_updates_enabled(True)
    assert sim.solve()["converged"]
    before=sim.breakdown_state().copy()
    assert before.max()==1
    sim.set_breakdown_params(np.ones(N,dtype=np.int8),np.full(N,1e7),1e-4)
    sim.set_history_updates_enabled(False)
    assert sim.solve()["converged"]
    np.testing.assert_array_equal(sim.breakdown_state(),before)


def test_queued_contact_updates_keep_original_continuation_start():
    sim=high_level()
    assert sim.run(max_iter=300,tol=1e-8)["converged"]
    sim.update_contact("right",2.)
    sim.update_contact("right",4.)
    assert sim._pending_contact_ramps["right"] == (0.,4.)
    result=sim.run(max_iter=300,tol=1e-8)
    assert result["continuation_steps"]==40
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


def test_mlc_voltage_helper_consumes_one_dwell_independent_of_max_step():
    from tcad.postprocess.fe_loops import _ramp_contact_and_run
    results=[]
    for max_step in (.1,.5,2.):
        sim=high_level()
        assert sim.run(max_iter=300,tol=1e-8)["converged"]
        result=_ramp_contact_and_run(sim,"right",4.,max_step,300,1e-8,2)
        results.append(result["P"])
        np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)
    np.testing.assert_allclose(results[0],results[-1],atol=1e-12)


@pytest.mark.parametrize("invalid_flag", ["target_reached", "physical_step_accepted"])
def test_mlc_rejected_final_result_restores_native_nls_history(monkeypatch, invalid_flag):
    from tcad.postprocess.fe_loops import _ramp_contact_and_run
    sim, reference = high_level(), high_level()
    for device in (sim, reference):
        assert device.run(max_iter=300, tol=1e-8)["converged"]
    initial_p = sim.results["P"].copy()
    original_run = sim.run

    def reject_final(**kwargs):
        result = original_run(**kwargs)
        if kwargs.get("physical_step", True):
            result[invalid_flag] = False
        return result

    with monkeypatch.context() as patch:
        patch.setattr(sim, "run", reject_final)
        with pytest.raises(RuntimeError, match="not accepted"):
            _ramp_contact_and_run(sim, "right", 4., .5, 300, 1e-8, 0)
    assert sim._contact_voltages["right"] == 0.
    np.testing.assert_array_equal(sim.results["P"], initial_p)
    actual = _ramp_contact_and_run(sim, "right", 4., .5, 300, 1e-8, 0)
    expected = _ramp_contact_and_run(reference, "right", 4., .5, 300, 1e-8, 0)
    np.testing.assert_allclose(actual["P"], expected["P"], atol=1e-12)
    np.testing.assert_allclose(actual["P"][:, 0], -PS*(1-math.exp(-.1)), atol=1e-12)


def test_mlc_retry_does_not_double_native_nls_dwell(monkeypatch):
    from tcad.postprocess.fe_loops import _ramp_contact_and_run
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["converged"]
    original_run = sim.run
    final_attempts = []

    def reject_first_final(**kwargs):
        result = original_run(**kwargs)
        if kwargs.get("physical_step", True):
            final_attempts.append(result["P"].copy())
            if len(final_attempts) == 1:
                result["target_reached"] = False
        return result

    monkeypatch.setattr(sim, "run", reject_first_final)
    result = _ramp_contact_and_run(sim, "right", 4., .5, 300, 1e-8, 1)
    assert len(final_attempts) == 2
    assert result["target_reached"] and result["physical_step_accepted"]
    np.testing.assert_allclose(result["P"][:, 0], -PS*(1-math.exp(-.1)), atol=1e-12)
    np.testing.assert_allclose(final_attempts[0], final_attempts[1], atol=1e-12)


def patched_device(monkeypatch):
    from types import SimpleNamespace
    import tcad.simulator as api
    sim=high_level()
    monkeypatch.setattr(api,"structured_mesh_from_device",lambda *_args,**_kwargs:sim.mesh)
    monkeypatch.setattr(api,"Simulator",lambda *_args,**_kwargs:sim)
    return api,sim,SimpleNamespace(contacts={"left":(None,0.),"right":(None,4.)})


def test_one_shot_outer_ramp_consumes_one_dwell(monkeypatch):
    api,sim,device=patched_device(monkeypatch)
    _,result=api.simulate_device(device,quantum=False,ramp_steps=9,max_iter=300,tol=1e-8)
    assert result["valid"]
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


def test_outer_sweep_commits_once_for_each_requested_pulse(monkeypatch):
    api,sim,device=patched_device(monkeypatch)
    _,results=api.simulate_sweep(device,{"right":np.array([4.,4.])},quantum=False,
                               ramp_steps=9,max_iter=300,tol=1e-8,verbose=False)
    for pulse,result in enumerate(results,1):
        assert result["valid"] and result["physical_step_accepted"]
        np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1*pulse)),atol=1e-12)


def test_failed_outer_ramp_preserves_full_requested_target(monkeypatch):
    api,sim,device=patched_device(monkeypatch)
    with pytest.warns(RuntimeWarning):
        _,failed=api.simulate_device(device,quantum=False,ramp_steps=9,max_iter=0,tol=1e-8)
    assert not failed["valid"] and not failed["physical_step_accepted"]
    assert failed["target_contact_voltages"]["right"]==4.
    assert sim._contact_voltages["right"]==4.
    assert sim._pending_contact_ramps["right"]==(0.,4.)
    recovered=sim.run(max_iter=300,tol=1e-8)
    assert recovered["valid"]
    np.testing.assert_allclose(recovered["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


def test_failed_outer_sweep_reports_attempted_and_requested_voltages(monkeypatch):
    api,sim,device=patched_device(monkeypatch)
    with pytest.warns(RuntimeWarning):
        _,results=api.simulate_sweep(device,{"right":np.array([4.])},quantum=False,
                                   ramp_steps=9,max_iter=0,tol=1e-8,verbose=False)
    failed=results[0]
    assert not failed["valid"]
    assert failed["_requested_voltages"]["right"]==4.
    assert failed["_voltages"]["right"]==.5
    assert sim._pending_contact_ramps["right"]==(0.,4.)


def test_exception_restores_target_and_native_history_update_mode():
    sim=high_level()
    assert sim.run(max_iter=300,tol=1e-8)["converged"]
    core=sim._sim
    class FailOnce:
        calls=0
        def __getattr__(self,name):
            return getattr(core,name)
        def solve(self):
            self.calls+=1
            if self.calls==3:
                raise RuntimeError("injected solver exception")
            return core.solve()
    sim._sim=FailOnce()
    sim.update_contact("right",4.)
    with pytest.raises(RuntimeError,match="injected"):
        sim.run(max_iter=300,tol=1e-8)
    assert sim._contact_voltages["right"]==4.
    # Call the native solver directly so a new high-level run cannot conceal
    # an accidentally retained frozen-history flag.
    result=core.solve()
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


def test_initial_preisach_seed_does_not_create_an_artificial_turning_point():
    sim=high_level(initial_voltage=4.,model="sentaurus_preisach")
    actual=sim.run(max_iter=300,tol=1e-8)
    reference=native(3)
    reference.set_dirichlet_potential({0:0.,N-1:4.})
    expected=reference.solve()
    assert actual["converged"] and expected["converged"]
    np.testing.assert_allclose(actual["P"],expected["P"],atol=1e-12)


def test_trap_charge_resolve_does_not_add_another_program_dwell():
    from tcad.postprocess.fe_loops import run_retention
    sim=high_level()
    assert sim.run(max_iter=300,tol=1e-8)["converged"]
    class ZeroChargeTrap:
        occupancy=np.zeros(N)
        durations=[]
        def advance(self,phi,field,dt,temperature):
            self.durations.append(dt)
            return np.zeros(N)
    traps=ZeroChargeTrap()
    result=run_retention(sim,"right",4.,n_steps=3,dt=.1,program_width=.2,
                         trap_model=traps,max_iter=300,tol=1e-8)
    expected=-PS*(1-math.exp(-.2))
    assert result["P_initial"]==pytest.approx(expected,abs=1e-12)
    np.testing.assert_allclose(result["P"],expected,atol=1e-12)
    assert traps.durations==[.2,.1,.1,.1]


def test_failed_continuation_preserves_target_and_no_physical_commit():
    sim=high_level()
    assert sim.run(max_iter=300,tol=1e-8)["converged"]
    before=sim.results["P"].copy()
    sim.update_contact("right",4.)
    with pytest.warns(RuntimeWarning):
        failed=sim.run(max_iter=0,tol=1e-8)
    assert not failed["valid"] and not failed["physical_step_accepted"]
    assert failed["continuation_steps_completed"]==0
    assert failed["applied_contact_voltages"]["right"]==pytest.approx(.1)
    assert failed["target_contact_voltages"]["right"]==4.
    assert sim._contact_voltages["right"]==4.
    assert sim._pending_contact_ramps["right"]==(0.,4.)
    np.testing.assert_array_equal(failed["P"],before)
    final=sim.run(max_iter=300,tol=1e-8)
    assert final["valid"] and final["target_reached"]
    np.testing.assert_allclose(final["P"][:,0],-PS*(1-math.exp(-.1)),atol=1e-12)


@pytest.mark.parametrize("physical_step",["False",1,None])
def test_physical_step_flag_must_be_boolean(physical_step):
    with pytest.raises(ValueError,match="boolean"):
        high_level().run(physical_step=physical_step)
