"""Native nonlinear iterations, absolute stopping and FD transaction safety."""
import copy
import numpy as np
import pytest
from tcad.core._bindings import native_fermi_newton_raw
from tcad.postprocess.fermi_spectral_energy import audit_fermi_spectral_energy
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal
from test_fermi_spectral import fixture,BUDGET
from test_native_spectral import constructor_arguments


def test_native_Newton_solves_nonsymmetric_system_and_counts_every_callback():
    calls=[]
    def callback(x):
        calls.append(x)
        residual=np.array([x[0]**2+x[1]-5,x[0]+2*x[1]-4])
        return residual,float(max(abs(residual))/1e-12)
    x,stats,history=native_fermi_newton_raw(callback,[1.,1.5],[.01,.01],[10.,10.],200)
    np.testing.assert_allclose(x,[2.,1.],rtol=0,atol=1e-12)
    assert stats[0]==len(calls)<=200 and stats[1]>0 and stats[3]<=.25
    assert len(history)==3*stats[1]
    assert calls[-1]==x


def test_native_Newton_line_search_preserves_bounds_and_final_cache():
    calls=[]
    def callback(x):
        assert -5<x[0]<5
        calls.append(x[0]);r=np.array([np.exp(x[0])-2])
        return r,float(abs(r[0])/1e-12)
    x,stats,_=native_fermi_newton_raw(callback,[-4.],[-5.],[5.],400)
    assert abs(x[0]-np.log(2))<1e-12 and stats[2]>0 and calls[-1]==x[0]


@pytest.mark.parametrize('damage',['empty','size','bound','nan','budget','boolean','fractional',
    'nonfinite_residual','nonfinite_merit','negative_merit','residual_size','singular','false_convergence'])
def test_native_Newton_rejects_invalid_inputs_and_false_convergence(damage):
    initial=[0.];lower=[-2.];upper=[2.];budget=100
    callback=lambda x:([x[0]-1],abs(x[0]-1)/1e-12)
    if damage=='empty':initial=lower=upper=[]
    elif damage=='size':lower=[]
    elif damage=='bound':initial=[2.]
    elif damage=='nan':initial=[float('nan')]
    elif damage=='budget':budget=0
    elif damage=='boolean':budget=True
    elif damage=='fractional':budget=1.5
    elif damage=='nonfinite_residual':callback=lambda x:([float('inf')],1.)
    elif damage=='nonfinite_merit':callback=lambda x:([1.],float('nan'))
    elif damage=='negative_merit':callback=lambda x:([1.],-1.)
    elif damage=='residual_size':callback=lambda x:([1.,2.],1.)
    elif damage=='singular':callback=lambda x:([1.],1e8)
    else:callback=lambda x:([0.],1e8)
    with pytest.raises((ValueError,RuntimeError)):
        native_fermi_newton_raw(callback,initial,lower,upper,budget)


@pytest.mark.parametrize('fail_on',[1,2,4])
def test_native_callback_exception_identity_is_preserved(fail_on):
    error=LookupError('injected residual failure');calls=[]
    def callback(x):
        calls.append(x)
        if len(calls)==fail_on:raise error
        return [x[0]-1],abs(x[0]-1)/1e-12
    with pytest.raises(LookupError) as caught:
        native_fermi_newton_raw(callback,[0.],[-2.],[2.],100)
    assert caught.value is error and len(calls)==fail_on


def test_native_evaluation_budget_is_strict_including_Jacobian_probes():
    calls=[]
    def callback(x):
        calls.append(x);return [x[0]-1],1e8
    with pytest.raises(RuntimeError,match='budget exhausted'):
        native_fermi_newton_raw(callback,[0.],[-2.],[2.],2)
    assert len(calls)==2


@pytest.mark.parametrize('contacts,scale,voltage,count',[
    (False,1.,0.,2),(True,1.,0.,2),(True,1.,.002,2),(True,1.,-.002,2),
    (True,10.,.002,2),(True,10.,-.002,2),(True,10.,.002,4),(True,10.,-.002,4)])
def test_actual_native_iterations_advance_two_steps_and_pass_independent_audit(contacts,scale,voltage,count):
    native,state=fixture(contacts=contacts,density_scale=scale,voltage=voltage,count=count)
    control,reference=fixture(contacts=contacts,density_scale=scale,voltage=voltage,count=count)
    native.spectral_backend=native.local_backend=native.poisson_backend=native.nonlinear_backend='native'
    for _ in range(2):
        old=state
        state,report=native.step(old,2e-13,**BUDGET)
        reference,_=control.step(reference,2e-13,**BUDGET)
        assert audit_fermi_spectral_energy(native,old,state,report,**BUDGET)['valid']
        assert report['native_nonlinear_driver'] is True and report['residual_dispatch_backend']=='python'
        assert report['nonlinear_statistics']['residual_evaluations']==report['nfev']<=400
        assert report['nonlinear_statistics']['jacobian_probe_calls_included'] is True
        assert max(abs(state.n_m3/reference.n_m3-1))<1e-10
        assert max(abs(state.p_m3/reference.p_m3-1))<1e-10
        assert max(abs(state.temperature_K-reference.temperature_K))<1e-8
        assert state.time_s>old.time_s


def test_actual_native_driver_uses_no_SciPy_optimizer_or_Python_physics_fallback(monkeypatch):
    import tcad.solver.fermi_electrothermal as implementation
    import tcad.solver.cut_cell_poisson as poisson
    model,old=fixture(contacts=True,density_scale=10.,voltage=.002)
    model.spectral_backend=model.local_backend=model.poisson_backend=model.nonlinear_backend='native'
    def forbidden(*args,**kwargs):raise AssertionError('Python numerical fallback')
    with monkeypatch.context() as patch:
        for name in ('least_squares','spectral_face','fermi_reservoir'):patch.setattr(implementation,name,forbidden)
        patch.setattr(np.linalg,'solve',forbidden)
        patch.setattr(poisson,'solve_cut_cell_poisson',forbidden)
        new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


@pytest.mark.parametrize('failure',['budget','callback','final_gate'])
def test_failed_native_steps_do_not_modify_state_or_model(failure,monkeypatch):
    model,old=fixture(contacts=True,voltage=.002,density_scale=10.)
    model.spectral_backend=model.local_backend=model.poisson_backend=model.nonlinear_backend='native'
    names=('n_m3','p_m3','temperature_K','trap_fraction')
    saved=[getattr(old,k).tobytes() for k in names];model_time=old.time_s
    if failure=='callback':
        def fail(*args,**kwargs):raise LookupError('injected native-dispatch error')
        monkeypatch.setattr(model,'face_transport',fail)
    budgets=BUDGET.copy()
    if failure=='final_gate':budgets['energy_atol_J']=1e-40
    with pytest.raises((ValueError,RuntimeError,LookupError)):
        model.step(old,2e-13,max_nfev=1 if failure=='budget' else 400,**budgets)
    assert saved==[getattr(old,k).tobytes() for k in names] and old.time_s==model_time
    assert all(not getattr(old,k).flags.writeable for k in names)


@pytest.mark.parametrize('damage',['flag','backend','dispatch'])
def test_independent_audit_rejects_forged_execution_metadata(damage):
    model,old=fixture()
    model.spectral_backend=model.local_backend=model.poisson_backend=model.nonlinear_backend='native'
    new,report=model.step(old,2e-13,**BUDGET);bad=copy.deepcopy(report)
    key,value={'flag':('native_nonlinear_driver',False),'backend':('nonlinear_backend','python'),
        'dispatch':('residual_dispatch_backend','native')}[damage]
    bad[key]=value
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']


@pytest.mark.parametrize('backend',['invalid','missing_spectral','missing_local','missing_poisson','native'])
def test_constructor_validates_native_driver_dependencies(backend):
    mesh,old,kwargs=constructor_arguments()
    args=dict(spectral_backend='native',local_backend='native',poisson_backend='native',nonlinear_backend='native')
    if backend=='invalid':args['nonlinear_backend']='invalid'
    elif backend.startswith('missing_'):args[backend.removeprefix('missing_')+'_backend']='python'
    if backend=='native':
        model=FermiSpectralElectrothermal(mesh,**kwargs,**args)
        assert model.nonlinear_backend=='native'
    else:
        with pytest.raises(ValueError):FermiSpectralElectrothermal(mesh,**kwargs,**args)
