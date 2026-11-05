"""Bounds and residual gates must use actual finite, successful measurements."""
from types import SimpleNamespace
import json
from pathlib import Path
import numpy as np
import pytest
from tcad.validation.boundedness import BoundednessTest, MonotoneConvergenceTest, PhysicalBoundsTest


def execute(check, result):
    class Simulator:
        def run(self, **kwargs): return result
    return check.run(Simulator)


def data():
    return dict(n=[1.,2.],p=[2.,3.],phi=[0.,1.],P=[0.,.1],
                Ex=[0.,1.],Ey=[0.,0.],Ez=[0.,0.],iteration_residuals=[1.,.1,.01],
                converged=True,valid=True)


def carriers_only():
    return BoundednessTest(check_potential_bounds=False,check_monotone_convergence=False,
                           check_ferroelectric_bounds=False)


@pytest.mark.parametrize('field',['n','p'])
@pytest.mark.parametrize('bad',[None,[np.nan,1.],[np.inf,1.],[],[True,False],['1','2']])
def test_carrier_bounds_reject_missing_or_invalid_measurements(field,bad):
    result=data()
    if bad is None: result.pop(field)
    else: result[field]=bad
    assert not execute(carriers_only(),SimpleNamespace(**result)).passed


@pytest.mark.parametrize('flag',['converged','valid'])
@pytest.mark.parametrize('value',[False,1,'true',None])
def test_supplied_failed_or_nonboolean_status_cannot_pass(flag,value):
    result=data();result[flag]=value
    assert not execute(carriers_only(),SimpleNamespace(**result)).passed


def test_default_bounds_cannot_guess_voltage_or_polarization_limits():
    assert not execute(BoundednessTest(),SimpleNamespace(**data())).passed


def test_requested_monotonicity_is_not_ignored_by_bounds():
    result=SimpleNamespace(iteration_residuals=[1.,2.],converged=True)
    check=BoundednessTest(check_positive_carriers=False,check_potential_bounds=False,
        check_ferroelectric_bounds=False,check_monotone_convergence=True)
    assert not execute(check,result).passed


@pytest.mark.parametrize('history',[None,[],[1.],[np.nan,0.],[1.,np.inf],[-1.,-2.],
                                   [[1.,.1]],[True,False],['1','0']])
def test_monotone_requires_finite_nonnegative_real_vector_history(history):
    result=SimpleNamespace(converged=True)
    if history is not None: result.iteration_residuals=history
    assert not execute(MonotoneConvergenceTest(),result).passed


@pytest.mark.parametrize('field',['n','p','Ex','Ey','Ez'])
@pytest.mark.parametrize('bad',[None,[np.nan,1.]])
def test_physical_bounds_require_all_carrier_and_field_measurements(field,bad):
    result=data()
    if bad is None:result.pop(field)
    else:result[field]=bad
    assert not execute(PhysicalBoundsTest(),SimpleNamespace(**result)).passed


@pytest.mark.parametrize('field',['n','p'])
@pytest.mark.parametrize('value',[-1.,0.,.5])
def test_physical_lower_carrier_bound_is_enforced(field,value):
    result=data();result[field]=[value,2.]
    assert not execute(PhysicalBoundsTest(min_carrier_density=1.),SimpleNamespace(**result)).passed


@pytest.mark.parametrize('check',[
    lambda:BoundednessTest(False,False,False,False),
    lambda:BoundednessTest(tolerance=np.nan),
    lambda:MonotoneConvergenceTest(tolerance=np.inf),
    lambda:PhysicalBoundsTest(min_carrier_density=2.,max_carrier_density=1.),
    lambda:PhysicalBoundsTest(max_electric_field=np.nan)])
def test_invalid_configuration_is_rejected(check):
    with pytest.raises(ValueError):check()


def bounded(**kwargs):
    config=dict(potential_bounds_V=(-1.,1.),polarization_limit_C_m2=.2,tolerance=0.)
    config.update(kwargs)
    return BoundednessTest(**config)


@pytest.mark.parametrize('as_mapping',[True,False])
def test_complete_measured_bounds_pass_without_claiming_physics_or_convergence(as_mapping):
    result=data()
    if not as_mapping:result=SimpleNamespace(**result)
    report=execute(bounded(),result)
    assert report.passed,report.message
    assert report.details['bounds_validated'] and report.details['residual_monotonicity_validated']
    assert not report.details['physical_validated'] and not report.details['convergence_validated']


@pytest.mark.parametrize('field',['n','p','phi','P'])
def test_pointwise_field_broadcasting_is_forbidden(field):
    result=data();result[field]=[0.]
    assert not execute(bounded(),result).passed


@pytest.mark.parametrize('field',['n','p'])
@pytest.mark.parametrize('tiny',[-1e-300,-5e-324])
def test_tiny_negative_density_is_not_hidden_by_other_nodes_or_large_upper_bound(field,tiny):
    result=data();result[field]=[tiny,1e300]
    assert not execute(carriers_only(),result).passed
    assert not execute(PhysicalBoundsTest(min_carrier_density=0.,max_carrier_density=1e300),result).passed


@pytest.mark.parametrize('low,high,phi,passed',[
    (-2.,-1.,[-2.,-1.],True),(-2.,-1.,[-2.01,-1.],False),
    (-1e308,1e308,[-1e308,1e308],True),(0.,0.,[0.,0.],True),
    (1e-300,1e300,[0.,1e300],False),(1e-300,1e300,[1e-300,1e300],True)])
def test_declared_potential_bounds_support_negative_bias_and_extreme_scales(low,high,phi,passed):
    check=BoundednessTest(False,True,False,False,tolerance=0.,potential_bounds_V=(low,high))
    assert execute(check,dict(phi=phi)).passed is passed


@pytest.mark.parametrize('field,delta,atol,passed',[
    ('n',-1e-20,0.,False),('n',-1e-20,1.01e-20,True),
    ('phi',1.001,0.,False),('phi',1.001,.002,True),
    ('P',.201,0.,False),('P',.201,.002,True)])
def test_absolute_budgets_are_explicit_and_have_field_units(field,delta,atol,passed):
    result=data();result[field]=[delta,delta]
    assert execute(bounded(atol={field:atol}),result).passed is passed


def test_relative_voltage_budget_cannot_be_used_as_density_negativity_budget():
    result=data();result['n']=[-1e-30,1e30]
    assert not execute(bounded(tolerance=.1),result).passed


@pytest.mark.parametrize('vector,limit,passed',[
    ([1.,1.,1.],1.4,False),([.3,.4,0.],.5000001,True),
    ([.3,.4,0.],.4999999,False),([3e-250,4e-250,0.],5.000001e-250,True),
    ([3e-250,4e-250,0.],4.999999e-250,False),([3e200,4e200,0.],5.000001e200,True)])
def test_vector_polarization_bounds_check_magnitude_without_squaring_overflow(vector,limit,passed):
    check=BoundednessTest(False,False,False,True,tolerance=0.,
        polarization_limit_C_m2=limit,polarization_component_axis=-1)
    assert execute(check,{'P':[vector,vector]}).passed is passed


@pytest.mark.parametrize('limit,passed',[(.2,True),([.2,.05],False),([.2,.1],True),([[.2],[.2]],False)])
def test_scalar_or_exact_shape_polarization_limits(limit,passed):
    assert execute(bounded(polarization_limit_C_m2=limit),data()).passed is passed


def test_lk_polarization_is_not_implicitly_capped_by_a_nominal_ps():
    check=BoundednessTest(False,False,False,True,polarization_limit_C_m2=2.)
    assert execute(check,{'P':[1.5,-1.5],'Ps':1.4}).passed


@pytest.mark.parametrize('history',[[1.,1.],[1e300,1e300],[0.,0.]])
def test_stagnant_residual_history_is_monotone_but_never_proves_convergence(history):
    report=execute(MonotoneConvergenceTest(),{'iteration_residuals':history})
    assert report.passed and report.details['residual_monotonicity_validated']
    assert not report.details['convergence_validated']


@pytest.mark.parametrize('history,tolerance,atol,passed',[
    ([1.,1.01],0.,0.,False),([1.,1.01],.02,0.,True),
    ([0.,5e-324],1e-6,0.,False),([0.,1e-30],0.,1e-29,True),
    ([1e308,1.01e308],.02,0.,True),([1e-300,1.01e-300],0.,0.,False)])
def test_residual_budget_has_no_implicit_floor_and_handles_large_values(history,tolerance,atol,passed):
    check=MonotoneConvergenceTest(tolerance,residual_atol=atol)
    assert execute(check,{'iteration_residuals':history}).passed is passed


@pytest.mark.parametrize('field',['n','p','Ex','Ey','Ez'])
def test_physical_bounds_reject_mismatched_shapes(field):
    result=data();result[field]=[1.]
    assert not execute(PhysicalBoundsTest(),result).passed


@pytest.mark.parametrize('component,limit,passed',[
    (3e200,5.2e200,True),(3e200,5e200,False),
    (3e-250,5.2e-250,True),(3e-250,5e-250,False),
    (1e308,1e308,False),(1e308,1.75e308,True),
    (1.79e308,1.79e308,False),(0.,0.,True)])
def test_electric_field_magnitude_is_stable_over_extreme_units(component,limit,passed):
    result=data()
    for field in ('Ex','Ey','Ez'): result[field]=[component,component]
    with np.errstate(all='raise'):
        report=execute(PhysicalBoundsTest(max_electric_field=limit),result)
    assert report.passed is passed,report.message
    if component==1.79e308:
        assert report.details['max_E'] is None and report.details['max_E_overflow']


@pytest.mark.parametrize('check',[
    lambda:BoundednessTest(potential_bounds_V=(1.,-1.)),
    lambda:BoundednessTest(potential_bounds_V=(True,1.)),
    lambda:BoundednessTest(potential_bounds_V=[0.,np.inf]),
    lambda:BoundednessTest(polarization_limit_C_m2=-1.),
    lambda:BoundednessTest(polarization_component_axis=True),
    lambda:BoundednessTest(atol={'undefined':0.}),
    lambda:BoundednessTest(atol={'phi':np.nan}),
    lambda:BoundednessTest(atol={'n':True}),
    lambda:BoundednessTest(check_potential_bounds=1),
    lambda:BoundednessTest(runner=1),
    lambda:BoundednessTest(residual_atol=-1.),
    lambda:MonotoneConvergenceTest(tolerance=True),
    lambda:MonotoneConvergenceTest(residual_atol=np.inf),
    lambda:PhysicalBoundsTest(min_carrier_density=-1.),
    lambda:PhysicalBoundsTest(max_carrier_density=True)])
def test_explicit_bounds_and_runner_configuration_are_validated(check):
    with pytest.raises(ValueError):check()


@pytest.mark.parametrize('axis',[-4,0,2])
def test_invalid_vector_axis_fails_without_guessing_layout(axis):
    check=BoundednessTest(False,False,False,True,polarization_limit_C_m2=1.,polarization_component_axis=axis)
    assert not execute(check,{'P':np.zeros((2,3))}).passed


def test_missing_declared_limits_does_not_execute_default_model():
    def forbidden(): pytest.fail('unconfigured bounds must not run')
    report=BoundednessTest().run(forbidden)
    assert not report.passed and report.details['unsupported']


def test_native_api_runner_and_framework_forwarding():
    from tcad.validation.framework import ValidationFramework
    class NativeAPI:
        def solve(self): return data()
    framework=ValidationFramework(NativeAPI)
    framework.add_boundedness_test(potential_bounds_V=(-1.,1.),polarization_limit_C_m2=.2,
        residual_atol=0.,runner=lambda sim:sim.solve())
    framework.add_monotone_convergence_test(runner=lambda sim:sim.solve())
    framework.add_physical_bounds_test(min_carrier_density=0.,runner=lambda sim:sim.solve())
    reports=framework.run_all()
    assert len(reports)==3 and all(report.passed for report in reports)


@pytest.mark.parametrize('check',[carriers_only,MonotoneConvergenceTest,PhysicalBoundsTest])
def test_solver_exceptions_do_not_pass(check):
    def broken(): raise RuntimeError('failed simulation')
    assert not check().run(broken).passed


def native_bounds_checks(axis,bias,corrupt=None):
    from tcad.core import PyDeviceSimulator
    count,length=9,8e-8
    shape,spacing=[1,1,1],[1e-8]*3;shape[axis]=count
    sim=PyDeviceSimulator(*shape,*spacing)
    sim.set_permittivity(np.full(count,8.854187817e-12*11.7))
    sim.set_mobility(np.zeros(count),np.zeros(count))
    sim.set_doping(np.zeros(count))
    sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16))
    sim.set_bandgap(np.full(count,6.))
    sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
    sim.set_dirichlet_potential({0:0.,count-1:bias})
    sim.set_electron_bc({0:1e16,count-1:1e16});sim.set_hole_bc({0:1e16,count-1:1e16})
    sim.set_initial_guess(np.linspace(0.,bias,count),np.full(count,1e16),np.full(count,1e16))
    sim.set_tolerance(1e-12);sim.set_gummel_max_iter(100)
    actual=sim.solve()
    assert actual['converged']
    np.testing.assert_allclose(actual['phi'],np.linspace(0.,bias,count),rtol=1e-12,atol=1e-14)
    for component,field in enumerate(('Ex','Ey','Ez')):
        np.testing.assert_allclose(actual[field],-bias/length if component==axis else 0.,rtol=1e-12,atol=1e-6)
    if corrupt=='phi':actual['phi'][count//2]=2.*max(abs(bias),1.)
    elif corrupt=='n':actual['n'][count//2]=-1e-300
    elif corrupt=='P':actual['P'][count//2,:]=.1
    elif corrupt=='E':actual[('Ex','Ey','Ez')[axis]][count//2]*=2.
    elif corrupt=='valid':actual['valid']=False
    bounds=BoundednessTest(check_monotone_convergence=False,potential_bounds_V=(min(0.,bias),max(0.,bias)),
        polarization_limit_C_m2=0.,polarization_component_axis=-1,runner=lambda sim:actual).run(object)
    # Interior zero-mobility nodes use the solver's insulating carrier floor;
    # the prescribed contact density is not a uniform bulk lower bound.
    physical=PhysicalBoundsTest(min_carrier_density=0.,max_carrier_density=1e16*(1.+1e-10),
        max_electric_field=abs(bias)/length*(1.+1e-10),runner=lambda sim:actual).run(object)
    monotone=MonotoneConvergenceTest(runner=lambda sim:actual).run(object)
    return dict(bounds=bounds,physical=physical,monotone=monotone)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('bias',[-.2,.2])
def test_native_three_axes_both_biases_pass_declared_bounds_but_cannot_invent_residual_history(axis,bias):
    reports=native_bounds_checks(axis,bias)
    for key in ('bounds','physical'):
        assert reports[key].passed,reports[key].message
    assert not reports['monotone'].passed and not reports['monotone'].details['convergence_validated']


@pytest.mark.parametrize('corrupt,bounds_pass,physical_pass',[
    ('phi',False,True),('n',False,False),('P',False,True),('E',True,False),('valid',False,False)])
def test_native_results_corrupted_after_solve_are_rejected_by_the_relevant_bounds(corrupt,bounds_pass,physical_pass):
    reports=native_bounds_checks(0,-.2,corrupt)
    assert reports['bounds'].passed is bounds_pass,reports['bounds'].message
    assert reports['physical'].passed is physical_pass,reports['physical'].message


COMMERCIAL=json.loads((Path(__file__).parent/'data/sentaurus_lk_dynamic.json').read_text())


@pytest.mark.parametrize('case',COMMERCIAL['cases'],ids=lambda c:f"{c['name']}-{c['max_step_normalized']}")
def test_existing_sentaurus_trajectories_obey_declared_lk_invariant_interval_and_detect_damage(case):
    # A caller-derived invariant interval for these cubic equations: at both
    # endpoints the LK field points inward for every applied field in the run.
    # This does not make .03 a universal Ps or material-validity threshold.
    limit=.03
    max_field=float(np.max(np.abs(case['voltage_V'])))/COMMERCIAL['length_m']
    assert case['alpha']*limit+case['beta']*limit**3 > max_field
    assert case['alpha']+3.*case['beta']*limit**2 > 0.
    measurement=dict(P=np.array(case['polarization_C_m2']),times_s=case['times_s'],valid=True)
    check=BoundednessTest(False,False,False,True,tolerance=0.,polarization_limit_C_m2=limit)
    report=execute(check,measurement)
    assert report.passed,report.message
    assert not report.details['physical_validated']
    measurement['P'][len(measurement['P'])//2]=1.01*limit
    assert not execute(check,measurement).passed
