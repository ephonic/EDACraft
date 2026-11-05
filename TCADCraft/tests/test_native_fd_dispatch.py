"""Native FD residual execution, independent audits and failed-step recovery."""
import copy
import numpy as np
import pytest
from tcad.core import _bindings
from tcad.solver.fermi_electrothermal import FermiSpectralElectrothermal,FermiSpectralState
from tcad.solver.native_fd_dispatch import pack_native_fd_inputs
from tcad.postprocess.fermi_spectral_energy import audit_fermi_spectral_energy
from test_fermi_spectral import fixture,BUDGET
from test_native_spectral import constructor_arguments


def native(model):
    model.spectral_backend=model.local_backend=model.poisson_backend=model.nonlinear_backend='native'
    model.residual_backend='native'
    return model


@pytest.mark.parametrize('contacts,scale,voltage,count',[
    (False,1.,0.,2),(True,1.,0.,2),(True,1.,.002,2),(True,1.,-.002,2),
    (True,10.,.002,2),(True,10.,-.002,2),(True,10.,.002,4),(True,10.,-.002,4)])
def test_native_residuals_advance_two_steps_and_match_previous_dispatch(contacts,scale,voltage,count):
    model,state=fixture(contacts=contacts,density_scale=scale,voltage=voltage,count=count);native(model)
    control,reference=fixture(contacts=contacts,density_scale=scale,voltage=voltage,count=count)
    control.spectral_backend=control.local_backend=control.poisson_backend=control.nonlinear_backend='native'
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        reference,_=control.step(reference,2e-13,**BUDGET)
        assert audit_fermi_spectral_energy(model,old,state,report,**BUDGET)['valid']
        assert report['residual_dispatch_backend']=='native' and report['native_nonlinear_driver']
        assert report['nfev']==report['nonlinear_statistics']['residual_evaluations']<=400
        assert max(abs(state.n_m3/reference.n_m3-1))<1e-10
        assert max(abs(state.p_m3/reference.p_m3-1))<1e-10
        assert max(abs(state.temperature_K-reference.temperature_K))<1e-8
        assert state.time_s>old.time_s and not state.n_m3.flags.writeable


def test_native_step_calls_one_extension_and_no_Python_production_physics(monkeypatch):
    import tcad.solver.fermi_electrothermal as solver
    import tcad.physics.native_fermi_local as local
    import tcad.physics.native_spectral as face
    import tcad.solver.native_poisson as poisson
    model,old=fixture(contacts=True,density_scale=10.,voltage=.002);native(model)
    real=_bindings.native_fermi_dispatch_raw;calls=[]
    def counted(*args):calls.append(1);return real(*args)
    def forbidden(*args,**kwargs):raise AssertionError('Python physics or optimizer dispatch')
    with monkeypatch.context() as patch:
        patch.setattr(_bindings,'native_fermi_dispatch_raw',counted)
        for name in ('energies','carrier_density_energy','face_transport','reservoirs','_poisson','conduction'):
            patch.setattr(model,name,forbidden)
        for name in ('native_fermi_newton_raw','native_fermi_reservoir_raw','native_spectral_face_raw',
                'native_fermi_local_raw','native_hybrid_poisson_raw'):patch.setattr(_bindings,name,forbidden)
        patch.setattr(solver,'least_squares',forbidden);patch.setattr(np.linalg,'solve',forbidden)
        patch.setattr(local,'native_fermi_reservoirs',forbidden);patch.setattr(local,'native_fermi_local',forbidden)
        patch.setattr(face,'native_spectral_face',forbidden);patch.setattr(poisson,'solve_native_state_poisson',forbidden)
        new,report=model.step(old,2e-13,**BUDGET)
    assert calls==[1] and report['nfev']>1
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']


@pytest.mark.parametrize('failure',['budget','global_energy'])
def test_failed_native_step_recovers_without_state_or_history_pollution(failure,monkeypatch):
    import tcad.solver.native_fd_dispatch as dispatch
    model,old=fixture(contacts=True,density_scale=10.,voltage=.002);native(model)
    fields=('n_m3','p_m3','trap_fraction','temperature_K')
    saved=[getattr(old,key).tobytes() for key in fields];time=old.time_s
    with monkeypatch.context() as patch:
        if failure=='global_energy':
            real=dispatch.native_fd_step
            def damaged(*args):
                output=real(*args);output[4]['electrostatic_energy_J']+=1e-20;return output
            patch.setattr(dispatch,'native_fd_step',damaged)
        with pytest.raises((ValueError,RuntimeError)):
            model.step(old,2e-13,max_nfev=1 if failure=='budget' else 400,**BUDGET)
    assert saved==[getattr(old,key).tobytes() for key in fields] and old.time_s==time
    new,report=model.step(old,2e-13,**BUDGET)
    assert audit_fermi_spectral_energy(model,old,new,report,**BUDGET)['valid']
    fresh,_=fixture(contacts=True,density_scale=10.,voltage=.002);native(fresh)
    expected,_=fresh.step(old,2e-13,**BUDGET)
    for key in fields:np.testing.assert_array_equal(getattr(new,key),getattr(expected,key))


def test_native_density_boundary_preserves_bits_below_float64_spacing():
    model,old=fixture(contacts=True,density_scale=10.,voltage=.002);native(model)
    n=old.n_m3.astype(np.longdouble);p=n.copy();n[0]+=np.spacing(n[0])
    assert n[0]!=p[0] and float(n[0])==float(p[0])
    state=FermiSpectralState(n,p,old.trap_fraction,old.temperature_K,old.time_s)
    new,report=model.step(state,1e-30,**BUDGET)
    np.testing.assert_array_equal(new.n_m3,n);np.testing.assert_array_equal(new.p_m3,p)
    assert audit_fermi_spectral_energy(model,state,new,report,**BUDGET)['valid']


@pytest.mark.parametrize('damage',['cells_size','faces_size','parameters_size','density','trap','temperature',
    'capacity','conductivity','mobility','owner','fractional_owner','neighbor','mode','area','half_distance',
    'skew','bath_inside','emission_boundary','band_jump','missing_anchor','contact_voltage','contact_temperature',
    'empty_valleys','bad_mass','nan','bad_decimal','budget','fractional_budget'])
def test_native_raw_dispatch_rejects_invalid_inputs(damage):
    model,old=fixture(contacts=True,voltage=.002)
    c,f,vn,vp,args=pack_native_fd_inputs(model,old,2e-13,**BUDGET);budget=400
    internal=int(model.internal[0]);boundary=int(model.contact_faces[0]);base=22*internal;edge=22*boundary
    if damage=='cells_size':c.pop()
    elif damage=='faces_size':f.pop()
    elif damage=='parameters_size':args.pop()
    elif damage=='density':c[3]='-1'
    elif damage=='trap':c[5]='1'
    elif damage=='temperature':c[10]='1'
    elif damage=='capacity':c[11]='0'
    elif damage=='conductivity':c[12]='0'
    elif damage=='mobility':c[15]='0'
    elif damage=='owner':f[0]='200'
    elif damage=='fractional_owner':f[0]='.5'
    elif damage=='neighbor':f[1]='-2'
    elif damage=='mode':f[base+19]='2'
    elif damage=='area':f[10]='1'
    elif damage=='half_distance':f[11]='1'
    elif damage=='skew':f[6]=str(float(f[6])+1e-9)
    elif damage=='bath_inside':f[base+13:base+15]=['1','350']
    elif damage=='emission_boundary':f[edge+19]='1'
    elif damage=='band_jump':f[base+19]='0'
    elif damage=='missing_anchor':f[8::22]=['0']*(len(f)//22);f[15::22]=['0']*(len(f)//22)
    elif damage=='contact_voltage':f[edge+8]='0'
    elif damage=='contact_temperature':f[edge+18]='0'
    elif damage=='empty_valleys':vn=[]
    elif damage=='bad_mass':vn[0]=-1.
    elif damage=='nan':args[0]=float('nan')
    elif damage=='bad_decimal':c[3]='1junk'
    elif damage=='budget':budget=0
    else:budget=1.5
    with pytest.raises((ValueError,RuntimeError)):_bindings.native_fermi_dispatch_raw(c,f,vn,vp,args,budget)


@pytest.mark.parametrize('backend',['invalid','missing_spectral','missing_local','missing_poisson','missing_nonlinear','native'])
def test_constructor_checks_dispatch_dependencies(backend):
    mesh,old,kwargs=constructor_arguments()
    args=dict(spectral_backend='native',local_backend='native',poisson_backend='native',
        nonlinear_backend='native',residual_backend='native')
    if backend=='invalid':args['residual_backend']='invalid'
    elif backend.startswith('missing_'):args[backend.removeprefix('missing_')+'_backend']='python'
    if backend=='native':
        model=FermiSpectralElectrothermal(mesh,**kwargs,**args)
        _,report=model.step(old,2e-13,**BUDGET)
        assert report['residual_dispatch_backend']=='native'
    else:
        with pytest.raises(ValueError):FermiSpectralElectrothermal(mesh,**kwargs,**args)


def test_constructor_does_not_silently_fall_back_if_dispatch_symbol_is_missing(monkeypatch):
    mesh,_,kwargs=constructor_arguments();monkeypatch.delattr(_bindings,'native_fermi_dispatch_raw')
    with pytest.raises(ImportError):FermiSpectralElectrothermal(mesh,**kwargs,spectral_backend='native',
        local_backend='native',poisson_backend='native',nonlinear_backend='native',residual_backend='native')


def test_independent_audit_rejects_false_dispatch_metadata():
    model,old=fixture();native(model);new,report=model.step(old,2e-13,**BUDGET)
    bad=copy.deepcopy(report);bad['residual_dispatch_backend']='python'
    assert not audit_fermi_spectral_energy(model,old,new,bad,**BUDGET)['valid']
