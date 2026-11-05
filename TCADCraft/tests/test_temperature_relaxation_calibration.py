"""Analytic integral roots, independent whole-condition checks and bad inputs."""
from dataclasses import replace
import hashlib
import numpy as np
import pytest
from scipy.optimize import brentq
from tcad.material.carrier_relaxation_calibration import CommercialDecayTrace as Trace
from tcad.material.temperature_relaxation_calibration import (
    calibrate_temperature_power_relaxation as fit,predict_temperature_power_decay as predict)


def analytic(times,T0,Tl,tau,b):
    dt=times-times[0]
    if b==0:return Tl+(T0-Tl)*np.exp(-dt/tau)
    def duration(T):
        log=np.log((T0-Tl)/(T-Tl))
        if b==1:return tau/300.*(T0-T+Tl*log)
        if b==2:return tau/300.**2*(.5*(T0*T0-T*T)+Tl*(T0-T)+Tl*Tl*log)
        raise ValueError(b)
    return np.array([T0 if t==0 else brentq(lambda T:duration(T)-t,Tl+1e-9,T0,xtol=1e-11) for t in dt])


def traces():
    data=[]
    for carrier,tau,b in [('electrons',3e-13,1),('holes',2.5e-13,0)]:
        for i,(Tl,excess) in enumerate(((300.,140.),(300.,300.),(350.,180.),(300.,65.))):
            t=np.linspace(3e-14,1.03e-12,51);name=carrier+str(i)
            data.append(Trace(name,carrier,'calibration' if i<2 else 'holdout',t,
                analytic(t,Tl+excess,Tl,tau,b),Tl,hashlib.sha256(name.encode()).hexdigest(),'synthetic-MB'))
    return data


def test_two_parameter_recovery_against_analytic_integral_and_constant_limit():
    r=fit(traces());assert r['fit_accepted']
    for c,tau,b in [('electrons',3e-13,1),('holes',2.5e-13,0)]:
        p=r['parameters'][c]
        assert p['tau0_s']==pytest.approx(tau,rel=1e-8)
        assert p['carrier_temperature_exponent']==pytest.approx(b,abs=1e-8)
        assert p['density_exponent']==p['lattice_temperature_exponent']==0
    assert max(h['maximum_peak_normalized_error'] for h in r['holdouts'])<1e-8
    assert not r['experimental_validated'] and not r['physical_validated']
    assert not r['state_dependent_relaxation_calibrated'] and not r['spatial_transport_validated']


@pytest.mark.parametrize('b',[0,1,2])
def test_predictor_matches_independent_closed_form_integrals(b):
    times=np.linspace(2e-14,1.02e-12,101)
    np.testing.assert_allclose(predict(times,560.,300.,3e-13,b),analytic(times,560.,300.,3e-13,b),atol=1e-7,rtol=0)


def test_held_out_decay_cannot_change_parameters_and_failure_is_explicit():
    data=traces();before=fit(data);old=data[2]
    data[2]=replace(old,temperatures_K=analytic(old.times_s,530.,350.,1.6e-13,1))
    after=fit(data)
    assert before['parameters']==after['parameters']
    assert not after['fit_accepted'] and not after['holdouts_accepted']


def test_nondefault_reference_preserves_effective_law():
    r=fit(traces(),reference_temperature_K=340.);assert r['fit_accepted']
    assert r['parameters']['electrons']['tau0_s']==pytest.approx(3e-13*340/300,rel=1e-8)
    assert r['parameters']['electrons']['carrier_temperature_exponent']==pytest.approx(1.,abs=1e-8)


def test_wrong_training_law_is_not_accepted_by_loose_holdout_gate():
    data=traces();old=data[0];T=old.temperatures_K.copy();T[10:20]-=.5
    # Preserve monotonicity but introduce a non-power-law feature.
    data[0]=replace(old,temperatures_K=T)
    r=fit(data,training_relative_gate=1e-5,holdout_relative_gate=1.)
    assert not r['fit_accepted'] and not r['training_accepted']


@pytest.mark.parametrize('kind',['duplicate_case','duplicate_source','material','one_carrier','no_holdout',
    'no_signal','flat','not_monotone','bound_time','bound_exponent','condition'])
def test_bad_or_unidentifiable_fit_rejected(kind):
    data=traces();kw={}
    if kind=='duplicate_case':data[2]=replace(data[2],case_id=data[0].case_id)
    if kind=='duplicate_source':data[2]=replace(data[2],source_sha256=data[0].source_sha256)
    if kind=='material':data[0]=replace(data[0],material_model='changed')
    if kind=='one_carrier':data=[c for c in data if c.carrier=='electrons']
    if kind=='no_holdout':data=[c for c in data if c.role=='calibration']
    if kind=='no_signal':kw['minimum_signal_K']=1000.
    if kind=='flat':data[0]=replace(data[0],temperatures_K=np.full(51,440.))
    if kind=='not_monotone':
        T=data[0].temperatures_K.copy();T[20]=T[19]+1.;data[0]=replace(data[0],temperatures_K=T)
    if kind=='bound_time':kw['tau0_bounds_s']=(1e-15,1e-14)
    if kind=='bound_exponent':kw['exponent_bounds']=(-2.,.5)
    if kind=='condition':kw['maximum_fit_condition']=1.00001
    with pytest.raises(ValueError):fit(data,**kw)


@pytest.mark.parametrize('kw',[{'reference_temperature_K':True},{'minimum_signal_K':0},
    {'maximum_fit_condition':1},{'training_relative_gate':np.nan},{'holdout_relative_gate':False},
    {'tau0_bounds_s':(0,1e-12)},{'tau0_bounds_s':(1e-12,1e-13)},
    {'exponent_bounds':(0,np.inf)},{'exponent_bounds':(True,False)}])
def test_invalid_fit_configuration_rejected(kw):
    with pytest.raises(ValueError):fit(traces(),**kw)


@pytest.mark.parametrize('args',[([0,0,1],400,300,1e-13,1),([0,1],300,300,1e-13,1),
    ([0,1],400,300,True,1),([0,1],400,300,1e-13,True),
    ([0,1],400,300,1e-13,float('nan')),([0,1j],400,300,1e-13,1)])
def test_invalid_prediction_rejected(args):
    with pytest.raises(ValueError):predict(*args)


def test_training_arrays_are_not_rewritten():
    data=traces();old=[c.temperatures_K.tobytes() for c in data]
    fit(data);assert old==[c.temperatures_K.tobytes() for c in data]
