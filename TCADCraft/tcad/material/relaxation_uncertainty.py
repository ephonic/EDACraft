"""Local first-order propagation of fitted relaxation and state uncertainty.

This does not refit uncertain state coordinates or authenticate measurements.
Log-coordinate covariance is supplied explicitly; unknown errors are not zero.
The propagation rule is NIST TN 1297 Appendix A, equation A-3.
"""
import numpy as np
from .energy_relaxation import EnergyRelaxationPowerLaw
from .energy_relaxation_calibration import _positive_scalar,_vector


PARAMETER_ORDER=('log_tau0_s','lattice_temperature_exponent',
                 'carrier_temperature_exponent','density_exponent')
STATE_ORDER=('log_lattice_temperature_K','log_carrier_temperature_K','log_density_m3')


def _matrix(value,shape,name):
    a=np.asarray(value)
    if a.shape!=shape or a.dtype.kind not in 'fiu' or not np.all(np.isfinite(a)):
        raise ValueError(name+' requires finite real aligned covariance entries')
    a=np.array(a,dtype=float,copy=True)
    if not np.all(np.isfinite(a)):
        raise ValueError(name+' must be representable in float64')
    return a


def propagate_relaxation_uncertainty(result,carrier,*,density_m3,carrier_temperature_K,
        lattice_temperature_K,state_log_covariance,parameter_state_log_cross_covariance,
        coverage_multiplier=1.):
    """Propagate one carrier's conditional fit covariance at explicit states.

    State covariance has shape (N,3,3), in STATE_ORDER. Parameter/state cross
    covariance has shape (N,4,3), with rows in PARAMETER_ORDER. Explicit zero
    matrices assert exact states or independence; absent uncertainties are
    rejected. Each combined 7x7 covariance must be symmetric positive
    semidefinite. No covariance between different prediction points is inferred.

    The returned exp(log(tau) +/- k*u(log(tau))) band has no assigned coverage
    probability. It is a local first-order uncertainty band, not a confidence
    interval or full material-model uncertainty. State uncertainty is propagated
    through the fitted law; it does not correct the fit for errors in variables.
    """
    if not isinstance(result,dict) or result.get('fit_accepted') is not True:
        raise ValueError('accepted local constitutive fit required')
    if carrier not in ('electrons','holes'):
        raise ValueError('explicit electron or hole carrier required')
    k=_positive_scalar(coverage_multiplier,'coverage multiplier')
    try:
        p=result['parameters'][carrier]
        if tuple(p['log_parameter_order'])!=PARAMETER_ORDER:
            raise ValueError('known log-parameter covariance ordering required')
        law=EnergyRelaxationPowerLaw(**p['law'])
        tau0=_positive_scalar(p['tau0_s'],'reference relaxation time')
        C=_matrix(p['conditional_log_parameter_covariance'],(4,4),'parameter covariance')
    except (KeyError,TypeError) as error:
        raise ValueError('fit must provide its conditional log-parameter covariance and ordering') from error
    n=_vector(density_m3,'density',positive=True)
    Tc=_vector(carrier_temperature_K,'carrier temperature',positive=True)
    Tl=_vector(lattice_temperature_K,'lattice temperature',positive=True)
    if not len(n) or Tc.shape!=n.shape or Tl.shape!=n.shape:
        raise ValueError('nonempty aligned prediction states required')
    S=_matrix(state_log_covariance,(len(n),3,3),'state covariance')
    B=_matrix(parameter_state_log_cross_covariance,(len(n),4,3),'parameter/state cross covariance')
    logs=np.column_stack((np.log(Tl)-np.log(law.reference_temperature_K),
        np.log(Tc)-np.log(law.reference_temperature_K),np.log(n)-np.log(law.reference_density_m3)))
    X=np.column_stack((np.ones(len(n)),logs))
    beta=np.r_[np.log(tau0),law.lattice_temperature_exponent,
        law.carrier_temperature_exponent,law.density_exponent]
    logtau=X@beta;uncertainty=[];corrections=[]
    for i,x in enumerate(X):
        joint=np.block([[C,B[i]],[B[i].T,S[i]]])
        diagonal=np.diag(joint)
        if np.any(diagonal<0):raise ValueError('nonnegative covariance diagonal required')
        scale=np.sqrt(diagonal);active=scale>0
        if np.any(joint[~active]!=0) or np.any(joint[:,~active]!=0):
            raise ValueError('zero-variance coordinate cannot have nonzero covariance')
        normalized=joint[np.ix_(active,active)]
        if np.any(active):normalized=normalized/scale[active,None]/scale[None,active]
        if not np.all(np.isfinite(normalized)):
            raise ValueError('finite normalized covariance required')
        tol=64*np.finfo(float).eps*max(1,len(normalized))
        if not np.allclose(normalized,normalized.T,rtol=0,atol=tol):
            raise ValueError('symmetric joint covariance required')
        if len(normalized):
            eigen,vectors=np.linalg.eigh((normalized+normalized.T)/2)
            if np.min(eigen)<-tol:raise ValueError('positive semidefinite joint covariance required')
            sensitivity=np.r_[x,beta[1:]][active]*scale[active]
            sigma=float(np.linalg.norm((sensitivity@vectors)*np.sqrt(np.maximum(eigen,0))))
            corrections.append(int(np.count_nonzero(eigen<0)))
        else:sigma=0.;corrections.append(0)
        uncertainty.append(sigma)
    uncertainty=np.array(uncertainty)
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        tau=np.exp(logtau);band=np.exp(np.column_stack((logtau-k*uncertainty,logtau+k*uncertainty)))
    if not np.all(np.isfinite(band)) or np.any(band<=0) or not np.all(np.isfinite(tau)) or np.any(tau<=0):
        raise ValueError('predicted time or uncertainty band outside positive float64 range')
    envelope=_matrix(p['training_log_coordinate_envelope'],(2,3),'training coordinate envelope')
    if np.any(envelope[0]>envelope[1]):raise ValueError('ordered training coordinate envelope required')
    inside=np.all((logs>=envelope[0]-1e-12)&(logs<=envelope[1]+1e-12),axis=1)
    return dict(carrier=carrier,predicted_tau_s=tau.tolist(),
        log_tau_standard_uncertainty=uncertainty.tolist(),uncertainty_band_s=band.tolist(),
        coverage_multiplier=k,coverage_probability_assigned=False,
        within_training_coordinate_envelope=inside.tolist(),
        parameter_order=list(PARAMETER_ORDER),state_log_order=list(STATE_ORDER),
        method='first-order full joint covariance propagation in log coordinates',
        parameter_covariance='conditional covariance supplied by accepted local exchange fit',
        state_errors_in_variables_refitted=False,cross_point_covariance_computed=False,
        roundoff_negative_normalized_eigenvalues_corrected=corrections,
        uncertainty_source='explicit supplied state and parameter/state cross covariance; no inferred measurement errors',
        local_constitutive_prediction_only=True,provenance_authenticated=False,
        experimental_validated=False,physical_validated=False,complete_device_energy=False)
