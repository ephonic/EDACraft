"""Independent closed-form cooling roots and confounded-design rejection."""
from dataclasses import replace
import hashlib
import numpy as np
import pytest
from test_temperature_relaxation_calibration import analytic
from tcad.material.multicondition_relaxation_calibration import (
    DensityResolvedDecayTrace as Trace,calibrate_multicondition_relaxation as fit)
from tcad.material.energy_relaxation_calibration import fitted_relaxation_configuration


def traces():
    result=[]
    for carrier,tau,a,b,c in [('electrons',3e-13,.6,1,-.2),('holes',2.5e-13,-.4,2,.3)]:
        for i,(Tl,n,excess) in enumerate(((300.,2e21,270.),(300.,1e22,380.),
                (400.,2e21,450.),(400.,1e22,260.),(350.,5e21,220.))):
            times=np.linspace(2e-14,8.2e-13,31);name=carrier+str(i)
            effective=tau*(Tl/300.)**a*(n/1e22)**c
            result.append(Trace(name,carrier,'holdout' if i==4 else 'calibration',times,
                analytic(times,Tl+excess,Tl,effective,b),Tl,
                hashlib.sha256(name.encode()).hexdigest(),'analytic numerical control',n))
    return result


def test_four_parameter_recovery_uses_independent_analytic_integrals():
    result=fit(traces());assert result['fit_accepted']
    for carrier,tau,a,b,c in [('electrons',3e-13,.6,1,-.2),('holes',2.5e-13,-.4,2,.3)]:
        p=result['parameters'][carrier]
        assert p['tau0_s']==pytest.approx(tau,rel=1e-7)
        for key,expected in [('lattice_temperature_exponent',a),('carrier_temperature_exponent',b),('density_exponent',c)]:
            assert p[key]==pytest.approx(expected,abs=1e-7)
        assert p['normalized_fit_condition']<1000
    assert max(h['maximum_peak_normalized_error'] for h in result['holdouts'])<1e-8
    assert not result['physical_validated'] and not result['experimental_validated']
    assert not result['state_dependent_relaxation_calibrated'] and not result['provenance_authenticated']
    configuration=fitted_relaxation_configuration(result)
    p=result['parameters']['electrons'];law=configuration['relaxation_law_n']
    assert float(law.evaluate(p['tau0_s'],5e21,500.,350.))==pytest.approx(3e-13*(350/300)**.6*(500/300)*(5e21/1e22)**-.2,rel=1e-7)


def test_heldout_perturbation_changes_acceptance_without_changing_fitted_parameters():
    data=traces();before=fit(data);t=data[4]
    data[4]=replace(t,temperatures_K=analytic(t.times_s,570.,350.,1e-13,1))
    after=fit(data)
    assert before['parameters']==after['parameters']
    assert not after['holdouts_accepted'] and not after['fit_accepted']


@pytest.mark.parametrize('coordinate',['lattice','density','carrier'])
def test_outside_training_envelope_never_qualifies_a_good_prediction(coordinate):
    data=traces();t=data[4];Tl=350.;n=5e21;excess=220.
    if coordinate=='lattice':Tl=450.
    if coordinate=='density':n=2e22
    if coordinate=='carrier':excess=700.
    effective=3e-13*(Tl/300)**.6*(n/1e22)**-.2
    data[4]=replace(t,lattice_temperature_K=Tl,density_m3=n,
        temperatures_K=analytic(t.times_s,Tl+excess,Tl,effective,1))
    result=fit(data);h=result['holdouts'][0]
    assert h['maximum_peak_normalized_error']<1e-8
    assert not h['inside_training_envelope'] and not h['accepted'] and not result['fit_accepted']


def test_reference_change_preserves_entire_state_law():
    result=fit(traces(),reference_temperature_K=340.,reference_density_m3=4e21)
    assert result['fit_accepted']
    assert result['parameters']['electrons']['tau0_s']==pytest.approx(3e-13*(340/300)**1.6*(4e21/1e22)**-.2,rel=1e-7)
    assert result['parameters']['holes']['tau0_s']==pytest.approx(2.5e-13*(340/300)**1.6*(4e21/1e22)**.3,rel=1e-7)


@pytest.mark.parametrize('kind',['constant_Tl','constant_density','correlated','almost_correlated'])
def test_rank_deficient_or_ill_conditioned_excitations_are_rejected(kind):
    data=traces()
    for i,t in enumerate(data):
        if t.role!='calibration':continue
        if kind=='constant_Tl':data[i]=replace(t,lattice_temperature_K=300.)
        if kind=='constant_density':data[i]=replace(t,density_m3=1e22)
        if kind in ('correlated','almost_correlated'):
            perturb=1e-10*(i%2) if kind=='almost_correlated' else 0.
            data[i]=replace(t,density_m3=1e22*(t.lattice_temperature_K/300.)**2*(1+perturb))
    with pytest.raises(ValueError):fit(data)


@pytest.mark.parametrize('kind',['duplicate_case','duplicate_source','material','missing_carrier','missing_holdout',
    'no_signal','nonmonotone','tau_bound','exponent_bound','condition'])
def test_bad_input_and_failed_identification_are_explicit(kind):
    data=traces();kw={}
    if kind=='duplicate_case':data[4]=replace(data[4],case_id=data[0].case_id)
    if kind=='duplicate_source':data[4]=replace(data[4],source_sha256=data[0].source_sha256)
    if kind=='material':data[0]=replace(data[0],material_model='other')
    if kind=='missing_carrier':data=[t for t in data if t.carrier=='electrons']
    if kind=='missing_holdout':data=[t for t in data if t.role=='calibration']
    if kind=='no_signal':kw['minimum_signal_K']=1000.
    if kind=='nonmonotone':
        T=data[0].temperatures_K.copy();T[15]=T[14]+1;data[0]=replace(data[0],temperatures_K=T)
    if kind=='tau_bound':kw['tau0_bounds_s']=(1e-15,1e-14)
    if kind=='exponent_bound':kw['exponent_bounds']=(-.5,.5)
    if kind=='condition':kw['maximum_fit_condition']=1.0001
    with pytest.raises(ValueError):fit(data,**kw)


@pytest.mark.parametrize('kw',[{'reference_temperature_K':True},{'reference_density_m3':0},
    {'maximum_fit_condition':1},{'training_relative_gate':float('nan')},{'holdout_relative_gate':False},
    {'tau0_bounds_s':(0,1e-12)},{'tau0_bounds_s':(1e-12,1e-13)},
    {'exponent_bounds':(0,float('inf'))},{'exponent_bounds':(True,False)}])
def test_invalid_configuration(kw):
    with pytest.raises(ValueError):fit(traces(),**kw)


@pytest.mark.parametrize('density',[True,0,-1,float('inf'),[1e22],1j])
def test_density_must_be_a_positive_real_scalar(density):
    with pytest.raises(ValueError):replace(traces()[0],density_m3=density)


def test_trace_has_immutable_detached_array_storage():
    t=traces()[0];values=t.temperatures_K.copy();copy=replace(t,temperatures_K=values)
    values[0]+=10;assert copy.temperatures_K[0]==t.temperatures_K[0]
    with pytest.raises(ValueError):copy.temperatures_K.setflags(write=True)
    with pytest.raises(ValueError):copy.times_s.setflags(write=True)


def test_non_power_training_cannot_hide_behind_loose_holdout_gate():
    data=traces();T=data[0].temperatures_K.copy();T[10:15]-=.4
    data[0]=replace(data[0],temperatures_K=T)
    result=fit(data,training_relative_gate=1e-5,holdout_relative_gate=1.)
    assert not result['training_accepted'] and not result['fit_accepted']
