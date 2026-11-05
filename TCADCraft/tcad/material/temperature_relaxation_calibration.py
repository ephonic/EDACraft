"""Temperature-dependent homogeneous MB relaxation from integral cooling times.

Density and lattice temperature are constant and energy-flux divergence and
postpulse electrical work must be negligible. Only tau0 and the carrier-T
exponent are identifiable here; lattice/density exponents are fixed to zero.
This numerical calibration never establishes measured material parameters.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.integrate import solve_ivp
from numpy.polynomial.legendre import leggauss
from .carrier_relaxation_calibration import CommercialDecayTrace
from .energy_relaxation import EnergyRelaxationPowerLaw


def _positive(v,name):
    a=np.asarray(v)
    if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a) or not 0<float(a)<np.inf:
        raise ValueError(name+' must be positive and finite')
    return float(a)


def predict_temperature_power_decay(times_s,initial_temperature_K,lattice_temperature_K,
                                    tau0_s,carrier_temperature_exponent,reference_temperature_K=300.):
    """Integrate the independently specified MB cooling ODE in scaled time."""
    t=np.asarray(times_s)
    if t.ndim!=1 or t.dtype.kind not in 'fiu' or not len(t) or not np.all(np.isfinite(t)):
        raise ValueError('ordered finite real time samples required')
    t=np.array(t,dtype=float,copy=True)
    if not np.all(np.isfinite(t)) or np.any(t<0) or np.any(np.diff(t)<=0):
        raise ValueError('strictly ordered nonnegative times required')
    T0=_positive(initial_temperature_K,'initial temperature');Tl=_positive(lattice_temperature_K,'lattice temperature')
    tau=_positive(tau0_s,'reference time');ref=_positive(reference_temperature_K,'reference temperature')
    exponent=np.asarray(carrier_temperature_exponent)
    if exponent.ndim or exponent.dtype.kind not in 'fiu' or not np.isfinite(exponent) or not np.isfinite(float(exponent)):
        raise ValueError('finite real temperature exponent required')
    b=float(exponent)
    if T0<=Tl:raise ValueError('strictly hot initial temperature required')
    if len(t)==1:return np.array([T0])
    scaled=(t-t[0])/tau
    if not np.all(np.isfinite(scaled)):raise ValueError('unrepresentable cooling interval')
    # Solve log(excess) to preserve positive excess during a long decay.
    def rhs(s,z):
        T=Tl+np.exp(z[0])
        with np.errstate(over='ignore',under='ignore',invalid='ignore'):
            rate=np.exp(-b*np.log(T/ref))
        if not np.isfinite(rate) or rate<=0:raise ValueError('unrepresentable relaxation rate')
        return [-rate]
    sol=solve_ivp(rhs,(0.,scaled[-1]),[np.log(T0-Tl)],t_eval=scaled,rtol=2e-11,atol=2e-12,method='DOP853')
    if not sol.success or sol.y.shape!=(1,len(t)):raise ValueError('cooling prediction did not converge')
    prediction=Tl+np.exp(sol.y[0])
    if not np.all(np.isfinite(prediction)):raise ValueError('nonfinite cooling prediction')
    return prediction


def calibrate_temperature_power_relaxation(traces,*,reference_temperature_K=300.,
        tau0_bounds_s=(1e-15,1e-10),exponent_bounds=(-4.,4.),minimum_signal_K=1.,
        maximum_fit_condition=1e4,training_relative_gate=.01,holdout_relative_gate=.01):
    """Fit integrated cooling times, then predict whole held-out traces.

    Integral coordinate z=log[(T-Tl)/(T0-Tl)] removes the equilibrium pole:
    dt/tau0 = integral(z,0) [(Tl+(T0-Tl)*exp(v))/Tref]^b dv.
    First temperatures are supplied initial conditions, not fitted amplitudes.
    Neither holdout slope nor holdout error influences the fitted parameters.
    """
    traces=tuple(traces)
    if not traces or any(type(t) is not CommercialDecayTrace for t in traces):
        raise ValueError('explicit homogeneous commercial decay traces required')
    ref=_positive(reference_temperature_K,'reference temperature')
    signal=_positive(minimum_signal_K,'minimum signal')
    condition_gate=_positive(maximum_fit_condition,'condition gate')
    train_gate=_positive(training_relative_gate,'training error gate')
    hold_gate=_positive(holdout_relative_gate,'holdout error gate')
    bounds=[]
    for v,name in ((tau0_bounds_s,'time'),(exponent_bounds,'exponent')):
        a=np.asarray(v)
        if a.shape!=(2,) or a.dtype.kind not in 'fiu' or not np.all(np.isfinite(a)):
            raise ValueError('ordered finite '+name+' bounds required')
        a=np.asarray(a,float)
        if not np.all(np.isfinite(a)) or a[0]>=a[1]:raise ValueError('ordered finite '+name+' bounds required')
        bounds.append(a)
    if bounds[0][0]<=0 or condition_gate<=1:raise ValueError('positive time bounds and condition gate >1 required')
    if len({t.case_id for t in traces})!=len(traces) or len({t.source_sha256 for t in traces})!=len(traces):
        raise ValueError('duplicate condition/source leakage')
    if len({t.material_model for t in traces})!=1:raise ValueError('material model changed')
    nodes,weights=leggauss(48);parameters={};holdouts=[];training=[]
    for t in traces:
        excess=t.temperatures_K-t.lattice_temperature_K
        if (excess[0]<signal or np.any(excess<=0) or np.any(np.diff(excess)>=0)
                or excess[-1]>.9*excess[0]):
            raise ValueError('resolved strictly monotone hot-carrier cooling required')
    for carrier in ('electrons','holes'):
        train=[t for t in traces if t.carrier==carrier and t.role=='calibration']
        held=[t for t in traces if t.carrier==carrier and t.role=='holdout']
        if not train or not held:raise ValueError('each carrier requires calibration and whole-condition holdout')
        prepared=[]
        for t in train:
            excess=t.temperatures_K-t.lattice_temperature_K
            width=-np.log(excess[1:]/excess[0])
            v=-.5*width[:,None]*(nodes[None,:]+1)
            logT=np.log((t.lattice_temperature_K+excess[0]*np.exp(v))/ref)
            dt=t.times_s[1:]-t.times_s[0]
            prepared.append((width,logT,dt))
        def residual(x):
            # Compare log durations; SI magnitudes do not dictate optimizer tolerance.
            return np.concatenate([x[0]+np.log(.5*width*(np.exp(x[1]*logT)@weights))-np.log(dt)
                for width,logT,dt in prepared])
        initial_tau=np.median([-(t.times_s[-1]-t.times_s[0])/
            np.log((t.temperatures_K[-1]-t.lattice_temperature_K)/(t.temperatures_K[0]-t.lattice_temperature_K)) for t in train])
        lower=[np.log(bounds[0][0]),bounds[1][0]];upper=[np.log(bounds[0][1]),bounds[1][1]]
        start=np.array([np.log(initial_tau),0.]);start=np.maximum(lower,np.minimum(upper,start))
        solved=least_squares(residual,start,bounds=(lower,upper),xtol=1e-12,ftol=1e-12,gtol=1e-12,
            diff_step=1e-5,max_nfev=200)
        scale=np.linalg.norm(solved.jac,axis=0)
        if not solved.success or np.any(solved.active_mask) or np.any(scale<=0) or not np.all(np.isfinite(scale)):
            raise ValueError('interior temperature-relaxation fit failed')
        singular=np.linalg.svd(solved.jac/scale,compute_uv=False)
        cond=float(singular[0]/singular[-1]) if singular[-1]>0 else np.inf
        if not np.isfinite(cond) or cond>condition_gate or np.linalg.matrix_rank(solved.jac)!=2:
            raise ValueError('temperature exponent and reference time are unidentifiable')
        tau=float(np.exp(solved.x[0]));b=float(solved.x[1]);law=EnergyRelaxationPowerLaw(ref,1e25,0.,b,0.)
        parameters[carrier]=dict(tau0_s=tau,carrier_temperature_exponent=b,reference_temperature_K=ref,
            lattice_temperature_exponent=0.,density_exponent=0.,normalized_fit_condition=cond,
            maximum_log_duration_residual=float(np.max(abs(solved.fun))),
            calibration_case_ids=[t.case_id for t in train],calibration_source_sha256=[t.source_sha256 for t in train],
            law=dict(zip(law.__dataclass_fields__,law.parameters())))
        for group,destination,gate in ((train,training,train_gate),(held,holdouts,hold_gate)):
            for t in group:
                predicted=predict_temperature_power_decay(t.times_s,t.temperatures_K[0],t.lattice_temperature_K,tau,b,ref)
                error=float(np.max(abs(predicted-t.temperatures_K))/(t.temperatures_K[0]-t.lattice_temperature_K))
                destination.append(dict(case_id=t.case_id,carrier=carrier,source_sha256=t.source_sha256,
                    supplied_initial_temperature_K=float(t.temperatures_K[0]),predicted_temperatures_K=predicted.tolist(),
                    maximum_peak_normalized_error=error,accepted=bool(error<=gate)))
    accepted=all(t['accepted'] for t in training+holdouts)
    return dict(parameters=parameters,training=training,holdouts=holdouts,fit_accepted=accepted,
        training_accepted=all(t['accepted'] for t in training),holdouts_accepted=all(t['accepted'] for t in holdouts),
        fitted_parameters=['tau0_s','carrier_temperature_exponent'],fixed_exponents=dict(lattice_temperature=0.,density=0.),
        reference_temperature_K=ref,holdout_initial_temperature_is_supplied=True,
        law='homogeneous constant-density MB dTc/dt=-(Tc-Tl)/(tau0*(Tc/Tref)^b)',
        commercial_temperature_decay_fit_only=True,provenance_authenticated=False,
        state_dependent_relaxation_calibrated=False,experimental_validated=False,
        physical_validated=False,spatial_transport_validated=False,complete_device_energy=False)
