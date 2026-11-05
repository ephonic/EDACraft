"""Implicit state-dependent exchange, independent law audit and safe retry."""
from copy import deepcopy
from dataclasses import FrozenInstanceError,replace
import numpy as np
import pytest
from scipy.optimize import root

from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.core._bindings import native_three_temperature_dispatch_raw,PyDeviceSimulator
from test_three_temperature import case,BUDGET
from test_device_three_temperature import assert_owned

LAWS=(Law(300.,1e25,.6,1.2,-.25),Law(300.,1e25,-.4,.8,.15))


def variable_case(**kwargs):
    model,state=case(**kwargs);model.relaxation_laws=LAWS
    return model,state


def direct_tau(model,state,label):
    k=0 if label=='electrons' else 1
    n=state.n_m3 if k==0 else state.p_m3
    Tc=state.electron_temperature_K if k==0 else state.hole_temperature_K
    tau=model.tau_n if k==0 else model.tau_p
    law=model.relaxation_laws[k]
    if law is None:return tau
    return tau*(state.temperature_K/law.reference_temperature_K)**law.lattice_temperature_exponent*\
        (Tc/law.reference_temperature_K)**law.carrier_temperature_exponent*\
        (n.astype(np.longdouble)/law.reference_density_m3)**law.density_exponent


@pytest.mark.parametrize('kwargs',[dict(),dict(contacts=True,voltage=.002),
    dict(contacts=True,voltage=-.002,density_scale=10),dict(nonuniform=True)])
def test_two_native_steps_recompute_law_at_new_state_and_close_each_reservoir(kwargs):
    model,old=variable_case(**kwargs);device=DeviceThreeTemperature(model,old)
    for _ in range(2):
        state,report=device.advance(2e-13,**BUDGET)
        assert report['independent_audit']['valid'] and report['modeled_device_energy_closed']
        assert report['relaxation_law']=='fixed_density_FD_energy_difference_over_state_dependent_tau'
        assert not report['physical_validated'] and not report['complete_device_energy']
        for label in ('electrons','holes'):
            np.testing.assert_allclose(report['cell_relaxation_time_s'][label],direct_tau(model,state,label),rtol=1e-12)
            assert np.max(abs(np.asarray(direct_tau(model,state,label))/direct_tau(model,old,label)-1))>1e-5
        assert_owned(device,state);old=state


def test_uniform_closed_step_matches_independent_coupled_FD_root_with_variable_tau():
    model,old=variable_case(count=1,uniform=True)
    new,report=model.step(old,2e-13,**BUDGET)
    def U(T,label):return reference_reservoir(old.n_m3[0],T,0.,model.valleys[label])['energy_density_J_m3']
    initial=[U(360.,'electrons'),U(260.,'holes')]
    def residual(T):
        candidate=replace(old,electron_temperature_K=[T[0]],hole_temperature_K=[T[1]],temperature_K=[T[2]])
        un,up=U(T[0],'electrons'),U(T[1],'holes')
        en=(un-U(T[2],'electrons'))*2e-13/float(direct_tau(model,candidate,'electrons')[0])
        ep=(up-U(T[2],'holes'))*2e-13/float(direct_tau(model,candidate,'holes')[0])
        return np.array([un-initial[0]+en,up-initial[1]+ep,model.capacity[0]*(T[2]-300.)-en-ep])/1e6
    solved=root(residual,[330.,275.,300.])
    assert solved.success and max(abs(residual(solved.x)))<1e-9
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
                               solved.x,rtol=0,atol=1e-6)
    assert report['independent_audit']['valid']


def test_explicit_reference_orchestration_matches_native_variable_law():
    model,old=variable_case(contacts=True,voltage=.002)
    control=deepcopy(model);control.residual_orchestration='python'
    actual,report=model.step(old,2e-13,**BUDGET)
    expected,reference=control.step(old,2e-13,**BUDGET)
    for field in ('electron_temperature_K','hole_temperature_K','temperature_K'):
        np.testing.assert_allclose(getattr(actual,field),getattr(expected,field),rtol=0,atol=1e-6)
    for field in ('n_m3','p_m3'):np.testing.assert_allclose(getattr(actual,field),getattr(expected,field),rtol=1e-10)
    assert report['independent_audit']['valid'] and reference['independent_audit']['valid']


def test_native_path_and_audit_do_not_call_python_law_evaluator(monkeypatch):
    model,old=variable_case()
    def forbidden(*a,**k):raise AssertionError('Python relaxation evaluator called by native production/audit')
    monkeypatch.setattr(Law,'evaluate',forbidden)
    state,report=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    assert report['independent_audit']['valid']


def test_constant_raw_schema_and_zero_exponents_reproduce_all_five_fields_exactly():
    model,old=case();zero=deepcopy(model);zero.relaxation_laws=(Law(),Law())
    plain=pack_three_temperature_inputs(model,old,2e-13,**BUDGET)
    extended=pack_three_temperature_inputs(zero,old,2e-13,**BUDGET)
    assert len(plain[-1])==7 and len(extended[-1])==17
    actual=native_three_temperature_dispatch_raw(*plain);expected=native_three_temperature_dispatch_raw(*extended)
    assert actual==expected


@pytest.mark.parametrize('damage',['exported_tau','frozen_tau','metadata','exchange','missing_tau'])
def test_independent_audit_rejects_wrong_tau_or_law_even_when_total_exchange_cancels(damage):
    model,old=variable_case();state,report=model.step(old,2e-13,**BUDGET);bad=deepcopy(report)
    if damage=='exported_tau':bad['cell_relaxation_time_s']['electrons'][0]*=1.01
    elif damage=='frozen_tau':bad['cell_relaxation_time_s']['electrons']=direct_tau(model,old,'electrons')
    elif damage=='metadata':bad['relaxation_law']='fixed_density_FD_energy_difference_over_tau'
    elif damage=='exchange':bad['cell_exchange_J']['electrons'][0]*=1.01
    else:del bad['cell_relaxation_time_s']
    if damage=='missing_tau':
        with pytest.raises(ValueError,match='relaxation'):audit_three_temperature_energy(model,old,state,bad,**BUDGET)
    else:assert not audit_three_temperature_energy(model,old,state,bad,**BUDGET)['valid']


@pytest.mark.parametrize('failure',['newton','audit'])
def test_device_rejection_preserves_all_fields_and_variable_law_retry_matches_fresh(monkeypatch,failure):
    model,old=variable_case();device=DeviceThreeTemperature(model,old);before=deepcopy(device.native_state())
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',
                                         lambda *a,**k:dict(valid=False,reason='injected'))
        with pytest.raises((RuntimeError,ValueError)):
            device.advance(2e-13,**BUDGET,max_nfev=1 if failure=='newton' else 600)
    assert device.native_state()==before
    state,_=device.advance(2e-13,**BUDGET)
    fresh,_=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    for field in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(state,field),getattr(fresh,field))


def test_immutable_device_configuration_detects_law_replacement_and_source_isolation():
    model,old=variable_case();device=DeviceThreeTemperature(model,old)
    model.relaxation_laws=(Law(),Law())
    assert device._model.relaxation_laws==LAWS
    with pytest.raises(FrozenInstanceError):LAWS[0].density_exponent=2.
    before=device.native_state();device._model.relaxation_laws=(Law(),Law())
    with pytest.raises(ValueError,match='immutable'):device.advance(2e-13,**BUDGET)
    assert device.native_state()==before


@pytest.mark.parametrize('index,value',[(7,0.),(8,-1.),(9,float('nan')),(12,0.),(13,float('inf'))])
def test_raw_invalid_law_parameters_leave_device_configuration_retryable(index,value):
    model,old=variable_case();args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET))
    bad=deepcopy(args);bad[-1][index]=value
    backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_three_temperature(*bad,0.)
    backend.configure_three_temperature(*args,0.)
    assert backend.three_temperature_state()['time_s']==0.


@pytest.mark.parametrize('field,value',[('reference_temperature_K',0.),('reference_density_m3',-1.),
    ('carrier_temperature_exponent',True),('density_exponent',float('nan')),('lattice_temperature_exponent',1j)])
def test_invalid_constitutive_parameters_rejected(field,value):
    with pytest.raises(ValueError):Law(**{field:value})


@pytest.mark.parametrize('exponent',[1e6,-1e6])
def test_unrepresentable_law_fails_without_clipping_or_advancing(exponent):
    model,old=case();model.relaxation_laws=(Law(carrier_temperature_exponent=exponent),None)
    with pytest.raises(ValueError,match='range'):DeviceThreeTemperature(model,old)
    with pytest.raises(ValueError,match='range'):model.relaxation_laws[0].evaluate(1e-13,1e25,360.,300.)


def test_structured_factory_forwards_laws_and_accepted_native_tau():
    from test_structured_three_temperature import structured_case
    source,old,options=structured_case()
    device=source.to_three_temperature(old,relaxation_law_n=LAWS[0],relaxation_law_p=LAWS[1],**options)
    state,report=device.advance(2e-13,**BUDGET)
    assert report['independent_audit']['valid'] and device.migration_report['audit']['valid']
    for label,raw in [('electrons','tau_n'),('holes','tau_p')]:
        np.testing.assert_allclose(report['cell_relaxation_time_s'][label],direct_tau(device._model,state,label),rtol=1e-12)
        np.testing.assert_array_equal(device.native_state()[raw],report['cell_relaxation_time_s'][label])


def test_nondefault_references_and_single_carrier_law_are_preserved_in_native_snapshot():
    model,old=case(count=1,uniform=True)
    model.relaxation_laws=(Law(350.,3e25,.7,-.4,.2),None)
    device=DeviceThreeTemperature(model,old)
    np.testing.assert_allclose(device.native_state()['tau_n'],direct_tau(model,old,'electrons'),rtol=1e-12)
    state,report=device.advance(2e-13,**BUDGET)
    np.testing.assert_allclose(report['cell_relaxation_time_s']['electrons'],direct_tau(model,state,'electrons'),rtol=1e-12)
    np.testing.assert_array_equal(report['cell_relaxation_time_s']['holes'],model.tau_p)
    assert report['independent_audit']['valid']


def test_arbitrary_relaxation_callback_is_rejected_before_native_orchestration():
    model,old=case();model.relaxation_laws=(lambda *a:1e-13,None)
    with pytest.raises(ValueError,match='callbacks'):DeviceThreeTemperature(model,old)
