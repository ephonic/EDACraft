"""Native five-field iteration, explicit reference, and immutable failed steps."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core import _bindings
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal,ThreeTemperatureState
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from test_three_temperature import case,BUDGET
from test_native_spectral import constructor_arguments


FIELDS=('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K')


@pytest.mark.parametrize('kwargs',[
    dict(),dict(contacts=True,voltage=.002),dict(contacts=True,voltage=-.002,density_scale=10.),
    dict(contacts=True,voltage=.002,density_scale=10.,count=4),dict(reverse=True),dict(nonuniform=True)])
def test_two_native_steps_match_explicit_reference_and_independent_audit(kwargs):
    model,state=case(**kwargs);control,reference=case(**kwargs);control.residual_orchestration='python'
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        reference,comparison=control.step(reference,2e-13,**BUDGET)
        assert report['native_residual_dispatch'] is True and report['residual_orchestration']=='native'
        assert comparison['native_residual_dispatch'] is False
        assert 1<report['nonlinear_statistics'][0]<=600
        assert report['nonlinear_statistics'][3]<=1
        assert audit_three_temperature_energy(model,old,state,report,**BUDGET)['valid']
        for key in FIELDS[:2]:np.testing.assert_allclose(getattr(state,key),getattr(reference,key),rtol=1e-10,atol=0)
        for key in FIELDS[2:]:np.testing.assert_allclose(getattr(state,key),getattr(reference,key),rtol=0,atol=1e-6)
        assert state.time_s>old.time_s and not state.n_m3.flags.writeable


def test_one_extension_call_with_python_production_and_callback_entries_disabled(monkeypatch):
    import tcad.physics.native_fermi_local as local
    import tcad.physics.native_spectral as face
    import tcad.physics.native_three_temperature as rows
    import tcad.solver.native_poisson as poisson
    model,old=case(contacts=True,voltage=.002,density_scale=10.)
    real=_bindings.native_three_temperature_dispatch_raw;calls=[]
    def observed(*args):calls.append(1);return real(*args)
    def forbidden(*args,**kwargs):raise AssertionError('Python production physics/callback used')
    monkeypatch.setattr(_bindings,'native_three_temperature_dispatch_raw',observed)
    for name in ('_poisson','energies','carrier_reservoirs','split_face_transport','conduction'):
        monkeypatch.setattr(model,name,forbidden)
    for name in ('native_fermi_newton_raw','native_fermi_reservoir_raw','native_hybrid_poisson_raw',
            'native_spectral_face_raw','native_three_temperature_local_raw','native_fermi_dispatch_raw'):
        monkeypatch.setattr(_bindings,name,forbidden)
    monkeypatch.setattr(local,'native_fermi_reservoirs',forbidden)
    monkeypatch.setattr(rows,'native_three_temperature_local',forbidden)
    monkeypatch.setattr(face,'native_spectral_face',forbidden)
    monkeypatch.setattr(poisson,'solve_native_state_poisson',forbidden)
    new,report=model.step(old,2e-13,**BUDGET)
    assert calls==[1] and report['independent_audit']['valid'] and new.time_s>0


@pytest.mark.parametrize('failure',['budget','native_exception','global_energy'])
def test_failed_native_step_preserves_all_state_and_retry_matches_fresh(failure,monkeypatch):
    import tcad.solver.native_three_temperature_dispatch as adapter
    model,old=case(count=1,uniform=True);saved=[getattr(old,k).tobytes() for k in FIELDS]
    def fail(*args):raise ValueError('forced native dispatch error')
    with monkeypatch.context() as patch:
        if failure=='native_exception':patch.setattr(_bindings,'native_three_temperature_dispatch_raw',fail)
        elif failure=='global_energy':
            real=adapter.native_three_temperature_step
            def corrupt(*args):
                output=real(*args);output[0]['poisson']['electrostatic_energy_J']+=1e-20;return output
            patch.setattr(adapter,'native_three_temperature_step',corrupt)
        with pytest.raises((ValueError,RuntimeError)):
            model.step(old,2e-13,max_nfev=1 if failure=='budget' else 600,**BUDGET)
    assert old.time_s==0 and saved==[getattr(old,k).tobytes() for k in FIELDS]
    state,report=model.step(old,2e-13,**BUDGET);fresh,_=case(count=1,uniform=True)
    expected,_=fresh.step(old,2e-13,**BUDGET)
    for key in FIELDS:np.testing.assert_array_equal(getattr(state,key),getattr(expected,key))
    assert report['independent_audit']['valid']


def test_native_boundary_preserves_density_bits_below_float64_spacing():
    model,old=case(contacts=True,voltage=.002,density_scale=10.)
    n=old.n_m3.copy();p=n.copy();n[0]+=np.spacing(n[0])
    assert n[0]!=p[0] and float(n[0])==float(p[0])
    old=ThreeTemperatureState(n,p,old.trap_fraction,old.temperature_K,0.,old.electron_temperature_K,old.hole_temperature_K)
    state,report=model.step(old,1e-30,**BUDGET)
    np.testing.assert_array_equal(state.n_m3,n);np.testing.assert_array_equal(state.p_m3,p)
    assert report['independent_audit']['valid']


@pytest.mark.parametrize('damage',['cell_width','face_width','parameter_width','n','trap','Tl','Tn','Tp',
    'capacity','conductivity','mobility','tau_n','tau_p','owner','fractional_owner','neighbor','mode','area',
    'half_distance','skew','bath_inside','emission_boundary','band_jump','missing_anchor','contact_voltage',
    'contact_temperature','empty_valleys','mass','nan','decimal','budget','fractional_budget','boolean_budget'])
def test_raw_dispatch_rejects_invalid_inputs(damage):
    model,old=case(contacts=True,voltage=.002)
    c,f,vn,vp,args=pack_three_temperature_inputs(model,old,2e-13,**BUDGET);budget=600
    base=22*int(model.internal[0]);edge=22*int(model.contact_faces[0])
    for key,index,value in [('n',3,'-1'),('trap',5,'1'),('Tl',10,'1'),('Tn',17,'1'),('Tp',18,'1e5'),
            ('capacity',11,'0'),('conductivity',12,'0'),('mobility',15,'0'),('tau_n',19,'0'),('tau_p',20,'-1')]:
        if damage==key:c[index]=value
    if damage=='cell_width':c.pop()
    elif damage=='face_width':f.pop()
    elif damage=='parameter_width':args.pop()
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
    elif damage=='mass':vn[0]=-1.
    elif damage=='nan':args[0]=float('nan')
    elif damage=='decimal':c[19]='1junk'
    elif damage=='budget':budget=0
    elif damage=='fractional_budget':budget=1.5
    elif damage=='boolean_budget':budget=True
    with pytest.raises((ValueError,RuntimeError)):
        _bindings.native_three_temperature_dispatch_raw(c,f,vn,vp,args,budget)


def test_newton_dimension_limit_rejected_before_geometry_assembly():
    with pytest.raises(ValueError,match='dense Newton limit'):
        _bindings.native_three_temperature_dispatch_raw(['1']*(21*205),['1']*22,[1,1,1,0],[1,1,1,0],[1]*7,600)


def test_missing_native_symbol_never_silently_falls_back(monkeypatch):
    mesh,_,kwargs=constructor_arguments();monkeypatch.delattr(_bindings,'native_three_temperature_dispatch_raw')
    with pytest.raises(ImportError):
        ThreeTemperatureElectrothermal(mesh,**kwargs,relaxation_time_n_s=1e-13,relaxation_time_p_s=4e-13)
    reference=ThreeTemperatureElectrothermal(mesh,**kwargs,relaxation_time_n_s=1e-13,
        relaxation_time_p_s=4e-13,residual_orchestration='python')
    assert reference.residual_orchestration=='python'


@pytest.mark.parametrize('damage',['residual_orchestration','native_residual_dispatch','local_conservation_backend'])
def test_independent_audit_rejects_false_dispatch_claim(damage):
    model,old=case(count=1,uniform=True);state,report=model.step(old,2e-13,**BUDGET)
    bad=deepcopy(report);bad[damage]='python' if damage!='native_residual_dispatch' else False
    assert not audit_three_temperature_energy(model,old,state,bad,**BUDGET)['valid']
