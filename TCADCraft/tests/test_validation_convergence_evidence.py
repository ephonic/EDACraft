"""Convergence requires measured errors, actual refinements and successful runs."""
from types import SimpleNamespace
import numpy as np
import pytest
from tcad.validation.convergence import GridConvergenceTest, TimeConvergenceTest, ParameterConvergenceTest
from tcad.validation import ValidationFramework


def test_unsupported_grid_builder_cannot_pass_without_reference():
    assert not GridConvergenceTest().run(lambda: object()).passed


@pytest.mark.parametrize('kind', ['grid', 'time', 'parameter'])
@pytest.mark.parametrize('values', [[], [3], [3,3,3], [3,9,5], [3,5,np.nan], [True,5,9]])
def test_bad_refinement_sequences_are_rejected(kind, values):
    with pytest.raises(ValueError):
        if kind == 'grid': GridConvergenceTest(mesh_sizes=values)
        if kind == 'time': TimeConvergenceTest(dt_values=values)
        if kind == 'parameter': ParameterConvergenceTest('a',values)


@pytest.mark.parametrize('kind', ['grid', 'time', 'parameter'])
@pytest.mark.parametrize('value', [0., -1., True, np.inf, np.nan, '0.1'])
def test_bad_tolerances_are_rejected(kind,value):
    with pytest.raises(ValueError):
        if kind == 'grid': GridConvergenceTest(tolerance=value)
        if kind == 'time': TimeConvergenceTest(tolerance=value)
        if kind == 'parameter': ParameterConvergenceTest('a',[1,2],tolerance=value)


def grid_check(errors=None, **kwargs):
    sizes=[5,9,17]
    if errors is None: errors=[1/16,1/64,1/256]
    def builder(nx,ny):
        return SimpleNamespace(run=lambda: dict(phi=[10.+errors[sizes.index(nx)]]))
    config=dict(mesh_sizes=sizes, reference=lambda n,result: {'phi':[10.]})
    config.update(kwargs)
    return GridConvergenceTest(**config).run(builder)


def test_true_error_converges_while_solution_norm_does_not_vanish():
    result=grid_check()
    assert result.passed
    np.testing.assert_allclose(result.details['pairwise_orders'],[2.,2.])
    assert result.details['grid_order_validated'] and not result.details['physical_validated']


@pytest.mark.parametrize('errors', [[1.,1.,1.],[1.,.01,.009],[1.,4.,16.],[0.,0.,0.]])
def test_flat_growing_wrong_or_unidentifiable_order_cannot_pass(errors):
    assert not grid_check(errors).passed


def test_each_order_is_checked_instead_of_a_cancelling_average():
    assert not grid_check([1.,.5,.0625]).passed # orders 1 and 3, mean 2


def test_actual_nonuniform_spacings_determine_order():
    result=grid_check([.3**2,.1**2,.02**2],spacing=lambda n: {5:.3,9:.1,17:.02}[n])
    assert result.passed
    np.testing.assert_allclose(result.details['pairwise_orders'],[2.,2.])


@pytest.mark.parametrize('bad', [{}, {'phi':[]},{'phi':[np.nan]},{'phi':[10.],'valid':False},{'phi':[[10.]]}])
def test_bad_grid_reference_cannot_pass(bad):
    assert not grid_check(reference=lambda n,r: bad).passed


def test_grid_cannot_be_its_own_reference():
    assert not grid_check(reference=lambda n,r:r).passed


@pytest.mark.parametrize('kind',['grid','time','parameter'])
def test_reused_simulator_is_rejected(kind):
    sim=SimpleNamespace(run=lambda:dict(phi=[1.]),run_transient=lambda **kw:dict(phi=[1.],time_s=1.))
    if kind=='grid':
        check=GridConvergenceTest(mesh_sizes=[5,9,17],reference=lambda n,r:dict(phi=[0.]))
    elif kind=='time': check=TimeConvergenceTest(dt_values=[.25,.125,.0625],t_final=1.)
    else: check=ParameterConvergenceTest('a',[1,2,3])
    assert not check.run(lambda **kw:sim).passed


@pytest.mark.parametrize('clock',[None, .5, [1.]])
def test_time_comparison_requires_actual_common_final_time(clock):
    def runner(sim,dt,t_final):
        result=dict(phi=[1.+dt])
        if clock is not None: result['time_s']=clock
        return result
    result=TimeConvergenceTest(dt_values=[.25,.125,.0625],t_final=1.,runner=runner).run(object)
    assert not result.passed


def test_time_runner_compares_endpoint_without_claiming_absolute_error_bound():
    result=TimeConvergenceTest(dt_values=[.25,.125,.0625],t_final=1.,tolerance=.1,
        runner=lambda s,dt,t:dict(phi=[1.+dt],time_s=t)).run(object)
    assert result.passed
    assert not result.details['global_temporal_error_validated']


def test_parameter_stability_does_not_certify_discretization_or_physics():
    result=ParameterConvergenceTest('a',[-2.,-1.,0.],runner=lambda sim:dict(phi=[1.])).run(lambda **kw:object())
    assert result.passed and result.details['parameter_stability_validated']
    assert not result.details['discretization_convergence_validated']
    assert not result.details['physical_validated']


def test_grid_runner_and_reference_are_exposed_by_framework():
    framework=ValidationFramework(lambda nx,ny:object())
    framework.add_grid_convergence_test(mesh_sizes=[5,9,17],runner=lambda s:dict(phi=[1.]),
        reference=lambda n,r:dict(phi=[1.-1/(n-1)**2]))
    assert framework.run_all()[0].passed


def native_poisson_check(reference_scale=1.):
    from tcad.core import PyDeviceSimulator
    length,amp,eps,q=1e-7,1e-3,8.854187817e-12*11.7,1.602176634e-19
    def builder(nx,ny):
        sim=PyDeviceSimulator(nx,1,1,length/(nx-1),1.,1.)
        x=np.linspace(0.,length,nx); k=2*np.pi/length
        sim.set_permittivity(np.full(nx,eps))
        sim.set_mobility(np.zeros(nx),np.zeros(nx))
        sim.set_doping(eps*k*k*amp/q*np.sin(k*x))
        sim.set_effective_dos(np.full(nx,1e16),np.full(nx,1e16))
        sim.set_bandgap(np.full(nx,6.))
        sim.set_recombination(np.full(nx,1e100),np.full(nx,1e100))
        sim.set_dirichlet_potential({0:0.,nx-1:0.})
        sim.set_electron_bc({0:0.,nx-1:0.}); sim.set_hole_bc({0:0.,nx-1:0.})
        sim.set_initial_guess(np.zeros(nx),np.zeros(nx),np.zeros(nx))
        sim.set_tolerance(1e-12); sim.set_gummel_max_iter(100)
        return sim
    def actual(sim):
        result=sim.solve()
        return dict(phi=result['phi'][1:-1],converged=result['converged'])
    result=GridConvergenceTest(mesh_sizes=[21,41,81],runner=actual,
        reference=lambda n,r:dict(phi=reference_scale*amp*np.sin(2*np.pi*np.linspace(0.,1.,n))[1:-1]),
        spacing=lambda n:length/(n-1),tolerance=.1).run(builder)
    return result


def test_native_poisson_sine_reference_validates_second_order():
    result=native_poisson_check()
    assert result.passed, result.message
    assert all(1.9<p<2.1 for p in result.details['pairwise_orders'])


def test_native_poisson_wrong_source_amplitude_is_rejected():
    assert not native_poisson_check(1.01).passed


@pytest.mark.parametrize('kwargs',[dict(mesh_sizes=[3.5,5,9]),dict(expected_order=0),
    dict(field=''),dict(runner=1),dict(reference=1),dict(spacing=1)])
def test_bad_grid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError): GridConvergenceTest(**kwargs)


@pytest.mark.parametrize('spacing',[lambda n:0.,lambda n:np.nan,lambda n:n])
def test_bad_actual_spacings_are_rejected(spacing):
    assert not grid_check(spacing=spacing).passed


@pytest.mark.parametrize('kind',['time','parameter'])
@pytest.mark.parametrize('bad',[{},dict(phi=[]),dict(phi=[np.inf]),dict(phi=[1.],valid=False)])
def test_bad_refinement_measurements_fail(kind,bad):
    if kind=='time':
        check=TimeConvergenceTest(dt_values=[.25,.125,.0625],t_final=1.,
            runner=lambda s,dt,t:dict(bad,time_s=t))
    else: check=ParameterConvergenceTest('a',[1,2,3],runner=lambda s:bad)
    assert not check.run(lambda **kw:object()).passed


def test_subnormal_reference_errors_can_identify_order_without_ratio_overflow():
    sizes=[5,9,17]
    check=GridConvergenceTest(mesh_sizes=sizes,
        runner=lambda s:dict(phi=[s]),reference=lambda n,r:dict(phi=[0.]))
    result=check.run(lambda nx,ny:[1e-300,2.5e-301,6.25e-302][sizes.index(nx)])
    assert result.passed


def test_zero_time_step_sensitivity_can_pass_without_claiming_an_order():
    result=TimeConvergenceTest(dt_values=[.25,.125,.0625],t_final=1.,
        runner=lambda s,dt,t:dict(phi=[0.],time_s=t)).run(object)
    assert result.passed and not result.details['temporal_order_validated']
