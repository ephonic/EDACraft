"""Local P step-doubling control and independent physical BE references."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_energy, integrate_transient_terminal_history, audit_transient_lk_error_control
from tcad.simulator import Simulator
from test_fe_transient_feedback import dielectric
from test_transient_displacement import film
from test_transient_lk_coupled import simultaneous_film_step, carrier_reference, linear_multidimensional_case
from test_transient_selfconsistent import central_cell
from test_transient_voltage_waveforms import driven_film, CLOCK
from test_transient_lk_substepping import SWITCH_CLOCK, SWITCH_VOLTAGE, switching_reference
from test_physical_step_commit import high_level


def controlled(sim, rtol=1e-3, atol=1e-6, **kwargs):
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True)
    sim.set_transient_lk_error_control(True, rtol, atol, **kwargs)
    return sim


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("layered", [False, True])
def test_each_committed_halfstep_and_coarse_reference_match_independent_block_system(axis, layered):
    sim, x, eps, mask, _ = film(axis, 0, True, layered)
    sim.set_transient_lk_material_field(False)  # Explicit central-field reference below.
    sim.set_tolerance(1e-12); sim.set_transient_dt(1e-7); sim.set_transient_t_final(1.23e-9)
    history = controlled(sim).solve_transient()
    assert all(s["valid"] for s in history) and len(history) % 2 == 1
    old = np.zeros(len(x))
    for i in range(1, len(history), 2):
        a, b = history[i:i+2]
        macro_dt = a["dt_s"]+b["dt_s"]
        _, coarse = simultaneous_film_step(x, eps, mask, old, macro_dt, -.01)
        np.testing.assert_allclose(b["lk_coarse_P_C_per_m2"].reshape(-1, 3)[:, axis], coarse,
                                   rtol=1e-8, atol=1e-12)
        for state in (a, b):
            phi, old = simultaneous_film_step(x, eps, mask, old, state["dt_s"], -.01)
            np.testing.assert_allclose(state["phi"], phi, rtol=2e-9, atol=2e-11)
            np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], old, rtol=2e-8, atol=1e-12)
            assert state["lk_error_status"] == "accepted" and state["lk_error_ratio"] <= 1.
            assert state["lk_error_end_s"] == b["time_s"]
            assert state["lk_error_interval_s"] == pytest.approx(macro_dt)
        delta = b["lk_error_delta_P_C_per_m2"]
        denominator = b["lk_error_atol_C_per_m2"]+b["lk_error_rtol"]*np.maximum(abs(b["P"]), abs(b["lk_coarse_P_C_per_m2"]))
        assert b["lk_error_ratio"] == pytest.approx(np.max(abs(delta)/denominator), rel=2e-12)
    assert history[-1]["time_s"] == 1.23e-9
    assert audit_transient_lk_energy(history)["valid"]
    assert audit_transient_lk_error_control(history)["valid"]
    assert integrate_transient_terminal_history(history)["duration_s"] == 1.23e-9


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("log_space", [False, True])
def test_active_carrier_history_obeys_independent_sg_lk_gauss_reference(axis, log_space):
    scale=1e19
    sim, x, nn, pp = central_cell(scale, log_space, axis, True, final=1.23e-9)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_gamma(.1); sim.set_transient_dt(1e-7)
    sim.set_transient_lk_material_field(False)  # carrier_reference uses centred E.
    history=controlled(sim, atol=1e-9).solve_transient(); old=np.zeros(3)
    for state in history[1:]:
        assert state["valid"]
        phi, nn, pp, old = carrier_reference(nn, pp, old, state["dt_s"], x, scale, alpha=-1e8)
        np.testing.assert_allclose(state["phi"], [0., phi, 0.], rtol=1e-8, atol=1e-11)
        np.testing.assert_allclose(state["n"]/scale, [1., nn, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["p"]/scale, [1., pp, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-12)
    assert audit_transient_lk_energy(history)["valid"]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_waveform_knots_are_preserved_and_trial_rejections_do_not_add_dwell(axis):
    sim, *_=driven_film(axis, model=0, fe=True, layered=True, dt=1e-7)
    history=controlled(sim, rtol=1e-3, atol=1e-8).solve_transient()
    assert all(s["valid"] for s in history)
    times=np.array([s["time_s"] for s in history])
    assert np.all(np.diff(times)>0.) and all(t in times for t in CLOCK)
    assert sum(s["lk_rejected_attempts"] for s in history[2::2]) > 0
    assert sum(s["dt_s"] for s in history) == pytest.approx(CLOCK[-1], rel=2e-14)
    assert audit_transient_lk_energy(history)["valid"]
    assert integrate_transient_terminal_history(history)["duration_s"] == CLOCK[-1]


def test_tighter_local_tolerances_improve_full_switching_trace_against_continuous_rk4():
    ref_t, ref_p=switching_reference(8192, return_trace=True)
    errors=[]; steps=[]
    for rtol,atol in ((.01,1e-5),(.001,1e-6),(.0001,1e-7)):
        sim, *_=film(0,0,False,False)
        sim.set_dirichlet_potential({0:0.,8:0.})
        sim.set_transient_voltage_waveforms(SWITCH_CLOCK,{8:SWITCH_VOLTAGE})
        sim.set_transient_dt(1e-7); sim.set_transient_t_final(SWITCH_CLOCK[-1]); sim.set_tolerance(1e-12)
        history=controlled(sim,rtol,atol).solve_transient()
        assert all(s["valid"] for s in history)
        t=np.array([s["time_s"] for s in history]); p=np.array([s["P"][0] for s in history])
        # Check the full trace; the final saturated state alone hides switching error.
        errors.append(np.max(abs(p-np.interp(t,ref_t,ref_p)))); steps.append(len(history)-1)
        assert history[-1]["P"][0]<-.013
        assert audit_transient_lk_energy(history)["valid"]
    assert steps[0]<steps[1]<steps[2]
    assert errors[1]<.6*errors[0] and errors[2]<.6*errors[1]


@pytest.mark.parametrize("failure", ["budget", "min_dt", "solver"])
def test_rejection_exhaustion_restores_state_and_retry_matches_fresh(failure):
    sim, *_=driven_film(model=0,fe=True,layered=True,dt=1e-7)
    controlled(sim,atol=1e-10,max_reject=0 if failure=='budget' else 20,
               min_dt=2.5e-10 if failure=='min_dt' else 1e-15)
    if failure=='solver': sim.set_gummel_max_iter(0)
    failed=sim.solve_transient()
    assert not failed[-1]['valid'] and failed[-1]['dt_s']==0. and failed[-1]['time_s']==0.
    assert failed[-1]['lk_error_status']==('solver_failure' if failure=='solver' else 'accuracy_limit')
    assert failed[-1]['lk_rejected_attempts']>=1
    if failure in ('budget','min_dt'): assert failed[-1]['lk_rejected_attempts']==1
    for key in ('P','phi','n','p','electrode_voltages_V'):
        np.testing.assert_array_equal(failed[-1][key],failed[0][key])
    sim.set_gummel_max_iter(80); sim.set_transient_lk_error_control(True,atol=1e-8)
    retry=sim.solve_transient()
    fresh,*_=driven_film(model=0,fe=True,layered=True,dt=1e-7)
    direct=controlled(fresh,atol=1e-8).solve_transient()
    assert len(retry)==len(direct)
    for a,b in zip(retry,direct):
        for key in ('P','phi','n','p','time_s','dt_s'):
            np.testing.assert_array_equal(a[key],b[key])


def test_error_control_is_optional_and_disabling_restores_previous_algorithm():
    sim,_=dielectric(final=1e-10)
    controlled(sim); sim.set_transient_lk_error_control(False)
    result=sim.solve_transient()
    fresh,_=dielectric(final=1e-10); fresh.set_transient_lk_coupled(True); fresh.set_transient_lk_substepping(True)
    expected=fresh.solve_transient()
    assert len(result)==len(expected)
    for a,b in zip(result,expected): np.testing.assert_array_equal(a['P'],b['P'])
    assert 'lk_error_control' not in result[-1]


@pytest.mark.parametrize('invalid',[0,1,'true',None,[],np.array([True])])
def test_strict_boolean_enable(invalid):
    sim,_=dielectric(); host=type('Host',(),{'_sim':sim})()
    for action in (lambda:sim.set_transient_lk_error_control(invalid),lambda:Simulator.set_transient_lk_error_control(host,invalid)):
        with pytest.raises(ValueError,match='boolean'): action()


@pytest.mark.parametrize('name',['rtol','atol','min_dt'])
@pytest.mark.parametrize('invalid',[0.,-1.,np.nan,np.inf,True,'0.1',[.1],1+0j])
def test_strict_scalar_parameters(name,invalid):
    sim,_=dielectric()
    with pytest.raises(ValueError,match='requires'): sim.set_transient_lk_error_control(**{name:invalid})


@pytest.mark.parametrize('invalid',[-1,1.,True,'2',None,2**100])
def test_rejection_budget_is_nonnegative_integer(invalid):
    sim,_=dielectric()
    with pytest.raises(ValueError,match='integer'): sim.set_transient_lk_error_control(max_reject=invalid)


@pytest.mark.parametrize('case',['split','no_substep','min_dt','floor_resolution'])
def test_bad_mode_or_floor_rejected_before_consuming_p(case):
    sim,_=dielectric(final=1e-10)
    original=sim.solve_transient()[-1]['P'].copy()
    controlled(sim)
    if case=='split': sim.set_transient_lk_coupled(False)
    elif case=='no_substep': sim.set_transient_lk_substepping(False)
    elif case=='min_dt': sim.set_transient_lk_error_control(True,min_dt=1e-7)
    else: sim.set_transient_lk_error_control(True,min_dt=1e-30)
    with pytest.raises(ValueError,match='LK'): sim.solve_transient()
    sim.set_transient_lk_error_control(False); sim.set_transient_lk_coupled(False); sim.set_transient_lk_substepping(False)
    sim.set_transient_t_final(0.)
    np.testing.assert_array_equal(sim.solve_transient()[0]['P'],original)


def test_high_level_numpy_scalars():
    sim=high_level()
    sim.set_transient_lk_error_control(np.bool_(True),np.float64(.01),np.float64(1e-6),max_reject=np.int64(3))
    sim.set_transient_lk_error_control(False)


@pytest.mark.parametrize('dimensions',[2,3])
@pytest.mark.parametrize('partial',[False,True])
def test_multidimensional_halfsteps_match_independent_linear_four_block_reference(dimensions,partial):
    sim,count,base,boundary,mask,_=linear_multidimensional_case(dimensions,partial,True)
    history=controlled(sim,atol=1e-7).solve_transient()
    old=np.zeros((count,3))
    for state in history[1:]:
        assert state['valid']
        matrix=base.copy(); rhs=np.zeros(4*count); rate=.1/state['dt_s']
        for node,voltage in boundary.items(): rhs[node]=voltage
        for axis in range(3):
            block=slice((axis+1)*count,(axis+2)*count)
            matrix[block,block]=np.diag(np.where(mask,1e9+rate,1.))
            rhs[block]=rate*old[:,axis]*mask
        scales=np.max(abs(matrix),axis=1)
        result=np.linalg.solve(matrix/scales[:,None],rhs/scales)
        np.testing.assert_allclose(state['phi'],result[:count],rtol=1e-9,atol=5e-13)
        old=result[count:].reshape(3,count).T
        np.testing.assert_allclose(state['P'].reshape(count,3),old,rtol=1e-8,atol=5e-13)
    assert audit_transient_lk_energy(history)['valid']
    assert audit_transient_lk_error_control(history)['valid']


def test_near_monotonicity_boundary_reserves_a_splittable_last_interval():
    sim,_=dielectric(voltage=0.,dt=1e-7,final=2e-9)
    sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_substepping(True,np.nextafter(1.,0.))
    sim.set_transient_lk_error_control(True)
    history=sim.solve_transient()
    assert all(s['valid'] for s in history)
    assert np.all(np.diff([s['time_s'] for s in history])>0.) and history[-1]['time_s']==2e-9
    assert audit_transient_lk_error_control(history)['valid']


@pytest.mark.parametrize('invalid',[1.,2.])
def test_relative_tolerance_must_be_less_than_one(invalid):
    sim,_=dielectric()
    with pytest.raises(ValueError,match='requires'): sim.set_transient_lk_error_control(rtol=invalid)


@pytest.mark.parametrize('case',['flag','scope','mode','clock','params','ratio_pair','end','interval',
                                'coarse','delta','count','missing','availability','truncated'])
def test_error_audit_rejects_malformed_or_mixed_pairs(case):
    sim,_=dielectric(voltage=-.01,final=1e-10)
    history=deepcopy(controlled(sim).solve_transient())
    assert audit_transient_lk_error_control(history)['valid']
    if case=='flag': history[-1]['lk_error_control']=1
    elif case=='scope': history[-1]['lk_error_scope']='global'
    elif case=='mode': history[-1]['lk_substepping']=False
    elif case=='clock': history[-1]['time_s']*=2
    elif case=='params': history[-1]['lk_error_rtol']*=2
    elif case=='ratio_pair': history[-1]['lk_error_ratio']*=2
    elif case=='end': history[-1]['lk_error_end_s']*=2
    elif case=='interval': history[-1]['lk_error_interval_s']*=2
    elif case=='coarse': history[-1]['lk_coarse_P_C_per_m2'][0]+=.01
    elif case=='delta': history[-1]['lk_error_delta_P_C_per_m2'][0]+=.01
    elif case=='count': history[-1]['lk_rejected_attempts']=True
    elif case=='missing': history[-1].pop('lk_error_delta_P_C_per_m2')
    elif case=='availability': history[-1]['lk_error_estimate_available']=False
    else: history.pop()
    with pytest.raises(ValueError): audit_transient_lk_error_control(history)


def test_forged_zero_ratio_fails_independent_estimate_audit():
    sim,_=dielectric(voltage=-.01,final=1e-10)
    history=controlled(sim).solve_transient()
    for state in history[1:]: state['lk_error_ratio']=0.
    result=audit_transient_lk_error_control(history)
    assert not result['valid'] and not result['lk_local_error_control_validated']
    assert not result['global_temporal_error_validated'] and not result['physical_validated']


def test_unrepresentable_initial_midpoint_returns_uncommitted_failure():
    tiny=np.nextafter(0.,1.)
    sim,_=dielectric(voltage=0.,alpha=1e8,dt=tiny,final=tiny)
    controlled(sim,min_dt=tiny,max_reject=0)
    history=sim.solve_transient()
    assert len(history)==2 and not history[-1]['valid']
    assert history[-1]['lk_error_status']=='time_resolution' and history[-1]['time_s']==0.
    np.testing.assert_array_equal(history[-1]['P'],history[0]['P'])


def test_retry_floor_can_equal_the_exported_step_limit():
    sim,_=dielectric(voltage=0.,dt=1e-7,final=1e-9)
    history=controlled(sim,min_dt=5e-10).solve_transient()
    assert all(s['valid'] for s in history)
    assert history[0]['lk_step_limit_s']==5e-10
    assert audit_transient_lk_error_control(history)['valid']


def test_linear_lk_local_estimator_matches_closed_form_halfstep_difference():
    alpha,gamma,voltage=1e9,.1,.003
    sim,x=dielectric(alpha=alpha,beta=1e-6,voltage=voltage,dt=1e-9,final=1e-9)
    history=controlled(sim,rtol=1e-3,atol=1e-9).solve_transient()
    steady=-voltage/x[-1]/alpha
    for i in range(1,len(history),2):
        start=history[i-1]['P'][0]; state=history[i+1]
        h=state['lk_error_interval_s']; r=alpha*h/gamma
        difference=(steady-start)*r*r/(4*(1+r)*(1+r/2)**2)
        assert state['lk_error_delta_P_C_per_m2'][0]==pytest.approx(difference,rel=2e-9,abs=1e-35)
        exact=steady*(1-np.exp(-alpha*state['time_s']/gamma))
        assert abs(state['P'][0]-exact)<1e-6
    assert audit_transient_lk_error_control(history)['valid']


def test_failed_group_after_nonzero_accepted_history_preserves_physical_state():
    sim,_=dielectric(voltage=-.01,dt=1e-7,final=1e-7)
    sim.set_transient_lk_coupled(True); sim.set_transient_lk_substepping(True)
    written=sim.solve_transient()[-1]['P'].copy()
    sim.set_transient_voltage_waveforms(np.array([0.,1.,2.])*1e-9,{8:[0.,0.,.09]})
    sim.set_transient_t_final(2e-9); sim.set_transient_lk_error_control(True,atol=1e-10,max_reject=0)
    history=sim.solve_transient()
    assert len(history)>3 and all(s['valid'] for s in history[:-1]) and not history[-1]['valid']
    assert history[-1]['time_s']==1e-9 and history[-1]['attempted_time_s']>1e-9
    assert np.max(abs(history[-1]['P']))>1e-3
    np.testing.assert_array_equal(history[0]['P'],written)
    for key in ('P','phi','n','p','electrode_voltages_V'):
        np.testing.assert_array_equal(history[-1][key],history[-2][key])
    assert audit_transient_lk_energy(history[:-1])['valid']
    assert audit_transient_lk_error_control(history[:-1])['valid']
    sim.set_transient_lk_error_control(True,atol=1e-8,max_reject=20)
    retry=sim.solve_transient()
    np.testing.assert_array_equal(retry[0]['P'],history[-2]['P'])
    assert all(s['valid'] for s in retry) and retry[-1]['time_s']==2e-9


def test_unsplittable_voltage_knot_tail_preserves_previously_accepted_groups():
    knot=1e-9; final=np.nextafter(knot,np.inf)
    sim,_=dielectric(voltage=0.,dt=1e-7,final=final)
    sim.set_transient_voltage_waveforms([0.,knot,final],{8:[0.,0.,0.]})
    history=controlled(sim).solve_transient()
    assert all(s['valid'] for s in history[:-1]) and not history[-1]['valid']
    assert history[-1]['time_s']==knot and history[-1]['attempted_time_s']==final
    assert history[-1]['lk_error_status']=='time_resolution' and history[-1]['dt_s']==0.
    np.testing.assert_array_equal(history[-1]['P'],history[-2]['P'])
    assert audit_transient_lk_error_control(history[:-1])['valid']
