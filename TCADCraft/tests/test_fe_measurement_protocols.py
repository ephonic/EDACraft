"""PUND signed increments, actual dwell and accepted measurements only."""
import math
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.postprocess.fe_loops import (run_pv_sweep, run_pe_sweep,
    run_pund_sequence, run_pulse_width_sweep)
from test_physical_step_commit import high_level
from test_fefet_validation import _FakeFESimulator


class IdealFE(_FakeFESimulator):
    def __init__(self, ps=.2, susceptibility=.03):
        super().__init__()
        self.memory = 0.
        self.ps = ps
        self.susceptibility = susceptibility

    def run(self, **kwargs):
        if kwargs.get("physical_step",True) and self.voltage != 0.:
            self.memory = self.ps*np.sign(self.voltage)
        result = super().run(**kwargs)
        result["P"][:,2] = self.memory + self.susceptibility*self.voltage
        return result


def test_pund_has_both_switching_and_nonswitching_pulse_pairs():
    out = run_pund_sequence(IdealFE(),"gate",2.,1e-8,n_points=10,
                           pre_pol_hold=1,pulse_width=.2,delay_time=0.)
    assert out["pulse_labels"] == ["preset","P","U","N","D"]
    assert out["P_switch_positive"] == pytest.approx(.4)
    assert out["P_switch_negative"] == pytest.approx(-.4)
    assert out["Pr"] == pytest.approx(.2)
    assert out["Ps"] == pytest.approx(.26)
    assert not out["terminal_charge_validated"]
    assert out["extraction_kind"] == "fe_state_increment_difference"


def test_reversible_polarization_does_not_become_switching_charge():
    out = run_pund_sequence(IdealFE(ps=0.),"gate",2.,1e-8,n_points=10,
                           pre_pol_hold=1,pulse_width=.2,delay_time=0.)
    assert out["Ps"] > 0.
    assert out["P_switch_positive"] == pytest.approx(0.,abs=1e-15)
    assert out["P_switch_negative"] == pytest.approx(0.,abs=1e-15)
    assert out["Pr"] == 0.


@pytest.mark.parametrize("subdivisions", [1, 3, 11])
def test_native_pund_five_pulse_closed_form_and_time(subdivisions):
    sim = high_level()
    out = run_pund_sequence(sim,"right",4.,40e-9,n_points=10*subdivisions,
                           pre_pol_hold=subdivisions,pulse_width=.2,delay_time=0.,
                           max_iter=300,tol=1e-8)
    a = math.exp(-.2)
    p = 0.
    plateau, increments = [], []
    for target in [.2,-.2,-.2,.2,.2]:
        next_p = target + (p-target)*a
        plateau.append(next_p); increments.append(next_p-p); p=next_p
    np.testing.assert_allclose(out["pulse_plateau_p"],plateau,atol=1e-12)
    np.testing.assert_allclose(out["pulse_zero_bias_p"],plateau,atol=1e-12)
    np.testing.assert_allclose(out["pulse_delta_p"],increments,atol=1e-12)
    assert out["P_switch_positive"] == pytest.approx(increments[1]-increments[2],abs=1e-12)
    assert out["P_switch_negative"] == pytest.approx(increments[3]-increments[4],abs=1e-12)
    assert out["elapsed_time"] == pytest.approx(1.)
    assert out["times"][0] == 0.
    assert out["times"][-1] == pytest.approx(1.)
    assert out["completed_segments"] == 5*subdivisions
    assert out["Pr"] == pytest.approx(.5*(abs(plateau[1])+abs(plateau[3])))


@pytest.mark.parametrize("resolution", [10, 80])
def test_explicit_edge_gap_durations_are_independent_of_resolution(resolution):
    out = run_pund_sequence(IdealFE(),"gate",2.,1e-8,n_points=resolution,
                           pre_pol_hold=3,pulse_width=.2,rise_time=.1,
                           fall_time=.1,delay_time=.3)
    assert out["elapsed_time"] == pytest.approx(3.5)
    assert np.sum(out["sample_durations"]) == pytest.approx(3.5)
    assert np.all(np.diff(out["times"]) >= 0.)
    assert np.all(out["sample_durations"][~out["physical_sample"]] == 0.)
    for lo,hi in out["phase_ranges"]:
        assert np.sum(out["sample_durations"][lo:hi]) == pytest.approx(.7)


@pytest.mark.parametrize("failure_call", [2, 3, 4, 5])
@pytest.mark.parametrize("failure_kind", ["invalid", "exception"])
def test_native_pund_rejection_restores_only_failed_segment(failure_call, failure_kind):
    sim = high_level()
    real_run = sim.run
    calls = 0
    entry = {}
    def injected(**kwargs):
        nonlocal calls, entry
        calls += 1
        if calls == failure_call:
            entry = {"results":deepcopy(sim.results),
                     "contacts":deepcopy(sim._contact_voltages),
                     "guess":deepcopy(sim._accepted_initial_guess)}
        result = real_run(**kwargs)
        if calls == failure_call:
            if failure_kind == "exception":
                raise RuntimeError("injected after native solve")
            result["valid"] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as error:
        run_pund_sequence(sim,"right",4.,40e-9,n_points=10,pre_pol_hold=1,
                           pulse_width=.2,delay_time=0.,max_iter=300,tol=1e-8)
    # Calls: initial helper, preset dwell, zero helper, P dwell, zero helper.
    completed = {2:0,3:1,4:1,5:2}[failure_call]
    assert error.value.completed_segments == completed
    assert error.value.elapsed_time == pytest.approx(completed*.2)
    # Contacts are restored to the transaction entry, before that update.
    # The injected callback observes the requested bias just after update.
    expected_bias = {2:0.,3:-4.,4:0.,5:4.}[failure_call]
    assert sim._contact_voltages["right"] == expected_bias
    np.testing.assert_array_equal(sim.results["P"],entry["results"]["P"])
    for actual,expected in zip(sim._accepted_initial_guess,entry["guess"]):
        np.testing.assert_array_equal(actual,expected)


@pytest.mark.parametrize("flag", ["valid","converged","target_reached","physical_step_accepted",
                                  "nan_P","missing_P","missing_phi"])
@pytest.mark.parametrize("driver", ["pv","pund","width"])
def test_all_measurement_drivers_reject_invalid_results(flag,driver):
    sim = IdealFE()
    real_run = sim.run
    def injected(**kwargs):
        result = real_run(**kwargs)
        if flag == "nan_P": result["P"][0,2] = np.nan
        elif flag.startswith("missing_"): del result[flag[8:]]
        else: result[flag] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError):
        if driver == "pv": run_pv_sweep(sim,"gate",2.,n_pts=2)
        elif driver == "pund":
            run_pund_sequence(sim,"gate",2.,1e-8,n_points=10,pre_pol_hold=1)
        else:
            run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=[.2],saturation_polarization=.2)
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("failure_call", [2, 4])
def test_native_pv_failure_restores_history_and_bias(failure_call):
    sim, reference = high_level(), high_level()
    real_run = sim.run
    calls = 0
    def injected(**kwargs):
        nonlocal calls
        calls += 1
        result = real_run(**kwargs)
        if calls == failure_call: result["valid"] = False
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as error:
        run_pv_sweep(sim,"right",4.,n_pts=2,dwell_time=.2,max_iter=300,tol=1e-8)
    for voltage in [0.,4.,0.,-4.,0.][:failure_call-1]:
        reference.set_ferroelectric_nls_dwell_time(.2)
        if reference.results is None: reference.set_contact("right",voltage)
        else: reference.update_contact("right",voltage)
        reference.run(max_iter=300,tol=1e-8)
    assert error.value.completed_segments == failure_call-1
    assert error.value.elapsed_time == pytest.approx((failure_call-1)*.2)
    np.testing.assert_array_equal(sim.results["P"],reference.results["P"])
    assert sim._contact_voltages == reference._contact_voltages


@pytest.mark.parametrize("kind", ["exception","wrong_size","nonbinary"])
def test_unavailable_breakdown_is_not_fabricated_as_zero(kind):
    sim = IdealFE()
    reads = []
    def state():
        reads.append(1)
        if len(reads)==2:
            if kind=="exception": raise RuntimeError("breakdown unavailable")
            if kind=="wrong_size": return np.zeros(2)
            return np.full(4,np.nan)
        return np.zeros(4)
    sim._sim = SimpleNamespace(breakdown_state=state)
    with pytest.raises(RuntimeError) as error:
        run_pv_sweep(sim,"gate",2.,n_pts=2,track_breakdown=True,dwell_time=.2)
    assert error.value.completed_segments == 1
    assert len(reads)==2
    assert sim.voltage == 0.
    assert sim.memory == 0.


def test_native_width_curve_matches_two_pulse_oracle_and_restores_state():
    sim = high_level()
    out = run_pulse_width_sweep(sim,"right",4.,40e-9,pulse_widths=[.1,.2,.5],
                               max_iter=300,tol=1e-8)
    a = np.exp(-np.array([.1,.2,.5]))
    expected_ps = .1*((1-a)+(1-a)**2)
    np.testing.assert_allclose(out["Ps"],expected_ps,atol=1e-12)
    np.testing.assert_allclose(out["memory_window"],8*expected_ps/.2,atol=1e-12)
    assert sim.results is None
    assert sim._contact_voltages["right"] == 0.
    assert sim._fe_nls_dt == .1


def test_width_order_duplicates_and_candidate_range_are_independent():
    sim = high_level(model="sentaurus_preisach")
    sim.run(max_iter=300,tol=1e-8)
    sim.update_contact("right",3.)
    sim.run(max_iter=300,tol=1e-8)
    original = sim.results["P"].copy()
    curves = []
    for widths in [[.1,.2,.5],[.5,.2,.1],[.2],[.2,.2]]:
        out = run_pulse_width_sweep(sim,"right",4.,40e-9,pulse_widths=widths,max_iter=300,tol=1e-8)
        curves.append(out)
        np.testing.assert_array_equal(sim.results["P"],original)
        assert sim._contact_voltages["right"] == 3.
    for key in ["Ps","memory_window"]:
        np.testing.assert_allclose(curves[0][key],curves[1][key][::-1],atol=1e-12)
        assert curves[0][key][1] == pytest.approx(curves[2][key][0],abs=1e-12)
        np.testing.assert_allclose(curves[3][key],curves[2][key][0],atol=1e-12)


@pytest.mark.parametrize("failure_call", [1,2])
def test_native_width_failure_restores_entire_experiment(failure_call):
    sim = high_level()
    sim.run(max_iter=300,tol=1e-8)
    before = sim.results["P"].copy()
    real_run = sim.run
    calls = 0
    def injected(**kwargs):
        nonlocal calls
        calls += 1
        result = real_run(**kwargs)
        if calls == failure_call: raise RuntimeError("reject width measurement")
        return result
    sim.run = injected
    with pytest.raises(RuntimeError) as error:
        run_pulse_width_sweep(sim,"right",4.,40e-9,pulse_widths=[.2],max_iter=300,tol=1e-8)
    assert error.value.experiment_rolled_back
    assert error.value.completed_experiments == 0
    np.testing.assert_array_equal(sim.results["P"],before)
    assert sim._contact_voltages["right"] == 0.


def test_width_reference_is_required_and_not_taken_from_sample_maximum():
    sim = IdealFE()
    with pytest.raises(ValueError,match="reference"):
        run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=[.1])
    assert sim.memory==0.
    a = run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=[.1],saturation_polarization=.2)
    b = run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=[.1],saturation_polarization=.4)
    np.testing.assert_allclose(a["memory_window"],2*b["memory_window"])


@pytest.mark.parametrize("parameter,value", [("n_points",True),("n_points",9),
    ("pre_pol_hold",0),("pre_pol_hold",1.5),("pulse_width",0.),
    ("rise_time",-1.),("fall_time",np.nan),("delay_time",np.inf),
    ("V_pulse",-1.),("fe_thickness",0.)])
def test_pund_invalid_inputs_fail_before_mutation(parameter,value):
    sim = IdealFE()
    options = {"V_pulse":2.,"fe_thickness":1e-8}
    options[parameter]=value
    with pytest.raises(ValueError): run_pund_sequence(sim,"gate",**options)
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("parameter,value", [
    ("V_pulse", True), ("pre_pol_V", "2."),
    ("fe_thickness", [1e-8]), ("pulse_width", np.array([.2])),
    ("rise_time", 1j), ("fall_time", [0.1, 0.2]),
    ("delay_time", "0.1"), ("max_iter", True), ("tol", np.array([1e-6])),
])
def test_pund_protocol_values_must_be_real_scalars(parameter, value):
    sim = IdealFE()
    options = {"V_pulse": 2., "fe_thickness": 1e-8}
    options[parameter] = value
    with pytest.raises(ValueError):
        run_pund_sequence(sim, "gate", **options)
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("driver,kwargs", [
    ("pv", {"Vmax": True}), ("pv", {"n_pts": 1.5}),
    ("pv", {"max_iter": True}), ("pv", {"tol": "1e-6"}),
    ("pv", {"dwell_time": [0.1]}),
    ("pe", {"Emax": "1e8"}), ("pe", {"fe_thickness": [1e-8]}),
    ("pe", {"max_iter": True}), ("pe", {"tol": np.nan}),
    ("breakdown", {"Vmax": [2.]}), ("breakdown", {"sigma_bd": True}),
])
def test_pv_pe_protocol_values_must_be_real_scalars(driver, kwargs):
    sim = IdealFE()
    if driver == "pv":
        options = {"Vmax": 2.}
    elif driver == "pe":
        options = {"Emax": 1e8, "fe_thickness": 1e-8}
    else:
        options = {"Vmax": 2.}
    options.update(kwargs)
    with pytest.raises(ValueError):
        if driver == "pv":
            run_pv_sweep(sim, "gate", **options)
        elif driver == "pe":
            run_pe_sweep(sim, "gate", **options)
        else:
            from tcad.postprocess.fe_loops import run_pv_sweep_with_breakdown
            run_pv_sweep_with_breakdown(sim, "gate", **options)
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("kwargs,configured_dwell", [
    ({"max_iter": True}, .1), ({"max_iter": 0}, .1),
    ({"tol": [1e-6]}, .1), ({"tol": 0.}, .1),
    ({}, True), ({}, 1e308),
])
def test_breakdown_wrapper_rejects_protocol_before_enabling(kwargs, configured_dwell):
    from tcad.postprocess.fe_loops import run_pv_sweep_with_breakdown
    sim = IdealFE()
    sim._fe_nls_dt = configured_dwell
    enabled = []
    sim.set_breakdown = lambda **options: enabled.append(options)
    with pytest.raises(ValueError):
        run_pv_sweep_with_breakdown(sim, "gate", 2., n_pts=2, **kwargs)
    assert enabled == []
    assert sim.memory == 0.
    assert sim.voltage == 0.


@pytest.mark.parametrize("widths", [[], [[.1,.2]], [.1,np.nan], [0.]])
def test_width_invalid_inputs_fail_before_mutation(widths):
    sim=IdealFE()
    with pytest.raises(ValueError):
        run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=widths,saturation_polarization=.2)
    assert sim.memory == 0.


@pytest.mark.parametrize("driver", ["pv","pund"])
@pytest.mark.parametrize("kind", ["axis","empty_mask"])
def test_invalid_polarization_measurement_restores_segment(driver,kind):
    sim = IdealFE()
    if kind=="axis": sim._fe_polar_axis = 9
    else: sim.mesh.fields={"fe_alpha":np.zeros(4)}
    with pytest.raises(RuntimeError):
        if driver=="pv": run_pv_sweep(sim,"gate",2.,n_pts=2)
        else: run_pund_sequence(sim,"gate",2.,1e-8,n_points=10,pre_pol_hold=1)
    assert sim.memory==0.


def test_readonly_transaction_restores_nested_commit_and_owned_model_state():
    sim = high_level()
    sim.run(max_iter=300,tol=1e-8)
    before = sim.results["P"].copy()
    with sim.reliability_transaction(commit=False):
        with sim.reliability_transaction():
            sim.update_contact("right",4.)
            assert sim.run(max_iter=300,tol=1e-8)["valid"]
    np.testing.assert_array_equal(sim.results["P"],before)
    assert sim._contact_voltages["right"] == 0.
    with pytest.raises(ValueError):
        with sim.reliability_transaction(commit="no"):
            pass


def test_pe_zero_thickness_is_rejected_before_mutation():
    sim=IdealFE()
    with pytest.raises(ValueError): run_pe_sweep(sim,"gate",1e8,0.)
    assert sim.voltage==0.


@pytest.mark.parametrize("driver", ["pv","pund","width"])
def test_total_duration_overflow_is_rejected_before_mutation(driver):
    sim=IdealFE()
    with pytest.raises(ValueError):
        if driver=="pv": run_pv_sweep(sim,"gate",2.,n_pts=2,dwell_time=1e308)
        elif driver=="pund": run_pund_sequence(sim,"gate",2.,1e-8,pulse_width=1e308)
        else:
            run_pulse_width_sweep(sim,"gate",2.,1e-8,pulse_widths=[1e308],saturation_polarization=.2)
    assert sim.voltage==0.


def test_pund_substep_underflow_is_rejected_before_mutation():
    sim=IdealFE()
    with pytest.raises(ValueError,match="underflows"):
        run_pund_sequence(sim,"gate",2.,1e-8,pulse_width=np.nextafter(0.,1.),pre_pol_hold=10)
    assert sim.voltage==0.
