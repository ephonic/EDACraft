"""Independent law perturbations, reference invariance and correlated errors."""
from copy import deepcopy
import json
import numpy as np
import pytest
from test_energy_relaxation_calibration import observations,fit
from tcad.material.relaxation_uncertainty import propagate_relaxation_uncertainty as propagate


def inputs():
    result=fit(observations())
    kw=dict(density_m3=np.array([1e25,1.1e25]),carrier_temperature_K=np.array([320.,360.]),
        lattice_temperature_K=np.array([300.,310.]),state_log_covariance=np.zeros((2,3,3)),
        parameter_state_log_cross_covariance=np.zeros((2,4,3)))
    return result,kw


@pytest.mark.parametrize('carrier',['electrons','holes'])
def test_exact_states_reduce_to_existing_conditional_log_prediction(carrier):
    result,kw=inputs();p=result['parameters'][carrier];out=propagate(result,carrier,**kw)
    X=np.column_stack((np.ones(2),np.log(kw['lattice_temperature_K']/300),
        np.log(kw['carrier_temperature_K']/300),np.log(kw['density_m3']/1e25)))
    expected=np.sqrt(np.diag(X@np.asarray(p['conditional_log_parameter_covariance'])@X.T))
    np.testing.assert_allclose(out['log_tau_standard_uncertainty'],expected,rtol=1e-12)
    json.dumps(out,allow_nan=False)
    for key in ('coverage_probability_assigned','state_errors_in_variables_refitted',
            'provenance_authenticated','experimental_validated','physical_validated','complete_device_energy'):
        assert out[key] is False


def test_correlated_joint_propagation_matches_independent_central_law_perturbations():
    result,kw=inputs();p=result['parameters']['electrons']
    C=np.asarray(p['conditional_log_parameter_covariance'])
    R=np.array([[.1,.2,-.1],[.2,-.1,.3],[0.,.2,.1],[-.1,.1,.2]])
    B=C@R;S=R.T@C@R+np.diag([.0001,.0004,.0009])
    kw['state_log_covariance'][:]=S;kw['parameter_state_log_cross_covariance'][:]=B
    out=propagate(result,'electrons',**kw)
    root=np.linalg.cholesky(np.block([[C,B],[B.T,S]]))
    beta=np.r_[np.log(p['tau0_s']),[p['law'][k] for k in p['log_parameter_order'][1:]]]
    expected=[]
    for n,Tc,Tl in zip(kw['density_m3'],kw['carrier_temperature_K'],kw['lattice_temperature_K']):
        mean=np.r_[beta,np.log(Tl/300),np.log(Tc/300),np.log(n/1e25)]
        def independently_evaluate(z):return z[0]+sum(z[1+j]*z[4+j] for j in range(3))
        shifts=[(independently_evaluate(mean+v)-independently_evaluate(mean-v))/2 for v in root.T]
        expected.append(np.linalg.norm(shifts))
    np.testing.assert_allclose(out['log_tau_standard_uncertainty'],expected,rtol=1e-10)
    independent=deepcopy(kw);independent['parameter_state_log_cross_covariance'][:]=0
    assert not np.allclose(out['log_tau_standard_uncertainty'],propagate(result,'electrons',**independent)['log_tau_standard_uncertainty'],rtol=1e-5,atol=0)


def test_reference_reparameterization_preserves_prediction_and_joint_uncertainty():
    result,kw=inputs();p=result['parameters']['electrons'];C=np.asarray(p['conditional_log_parameter_covariance'])
    R=np.array([[.1,0.,0.],[0.,.2,0.],[0.,0.,.3],[.1,.1,.1]])
    B=C@R;kw['state_log_covariance'][:]=R.T@C@R+np.eye(3)*.0001
    kw['parameter_state_log_cross_covariance'][:]=B
    before=propagate(result,'electrons',**kw)
    result=deepcopy(result);p=result['parameters']['electrons']
    t=np.log(320/300);n=np.log(1.1);M=np.eye(4);M[0]=[1,t,t,n]
    beta=M@np.r_[np.log(p['tau0_s']),[p['law'][k] for k in p['log_parameter_order'][1:]]]
    p['tau0_s']=float(np.exp(beta[0]));p['law']['reference_temperature_K']=320.
    p['law']['reference_density_m3']=1.1e25
    p['conditional_log_parameter_covariance']=(M@C@M.T).tolist()
    p['training_log_coordinate_envelope']=(np.asarray(p['training_log_coordinate_envelope'])-[t,t,n]).tolist()
    kw['parameter_state_log_cross_covariance'][:]=M@B
    after=propagate(result,'electrons',**kw)
    for key in ('predicted_tau_s','log_tau_standard_uncertainty','uncertainty_band_s'):
        np.testing.assert_allclose(after[key],before[key],rtol=1e-11,atol=0)
    assert after['within_training_coordinate_envelope']==before['within_training_coordinate_envelope']


def test_perfect_parameter_state_anticorrelation_can_cancel_uncertainty():
    result,kw=inputs();p=result['parameters']['electrons'];p['conditional_log_parameter_covariance']=np.diag([.04,0,0,0]).tolist()
    a=p['law']['lattice_temperature_exponent']
    kw['state_log_covariance'][:,0,0]=.04/a**2
    kw['parameter_state_log_cross_covariance'][:,0,0]=-.04/a
    out=propagate(result,'electrons',**kw)
    np.testing.assert_allclose(out['log_tau_standard_uncertainty'],0,atol=1e-8)


def test_band_multiplier_changes_only_band_and_outside_envelope_stays_explicit():
    result,kw=inputs();kw['density_m3'][1]=2e25
    before=propagate(result,'electrons',**kw);after=propagate(result,'electrons',coverage_multiplier=2,**kw)
    assert before['predicted_tau_s']==after['predicted_tau_s']
    assert before['log_tau_standard_uncertainty']==after['log_tau_standard_uncertainty']
    assert after['within_training_coordinate_envelope']==[True,False]
    assert np.all(np.asarray(after['uncertainty_band_s'])[:,0]<np.asarray(before['uncertainty_band_s'])[:,0])
    assert np.all(np.asarray(after['uncertainty_band_s'])[:,1]>np.asarray(before['uncertainty_band_s'])[:,1])


@pytest.mark.parametrize('kind',['state_shape','cross_shape','asymmetry','negative_variance','indefinite',
    'zero_variance_cross','nan','bool','complex','missing_covariance','wrong_order','unaccepted','overflow'])
def test_invalid_or_unavailable_uncertainty_is_rejected(kind):
    result,kw=inputs();p=result['parameters']['electrons']
    if kind=='state_shape':kw['state_log_covariance']=np.eye(3)
    if kind=='cross_shape':kw['parameter_state_log_cross_covariance']=np.zeros((4,3))
    if kind=='asymmetry':kw['state_log_covariance'][:]=[[1,.2,0],[0,1,0],[0,0,1]]
    if kind=='negative_variance':kw['state_log_covariance'][:,0,0]=-.1
    if kind=='indefinite':kw['state_log_covariance'][:]=np.eye(3);kw['parameter_state_log_cross_covariance'][:]=1
    if kind=='zero_variance_cross':kw['state_log_covariance'][:,0,1]=.1
    if kind=='nan':kw['state_log_covariance'][:,0,0]=np.nan
    if kind=='bool':kw['state_log_covariance']=np.zeros((2,3,3),bool)
    if kind=='complex':kw['state_log_covariance']=np.zeros((2,3,3),complex)
    if kind=='missing_covariance':del p['conditional_log_parameter_covariance']
    if kind=='wrong_order':p['log_parameter_order']=list(reversed(p['log_parameter_order']))
    if kind=='unaccepted':result['fit_accepted']=False
    if kind=='overflow':kw['coverage_multiplier']=1e308
    with pytest.raises(ValueError):propagate(result,'electrons',**kw)


def test_input_objects_remain_unchanged():
    result,kw=inputs();before=json.dumps(result,sort_keys=True);saved={k:v.copy() for k,v in kw.items()}
    propagate(result,'electrons',**kw)
    assert json.dumps(result,sort_keys=True)==before
    for k,v in saved.items():np.testing.assert_array_equal(kw[k],v)
