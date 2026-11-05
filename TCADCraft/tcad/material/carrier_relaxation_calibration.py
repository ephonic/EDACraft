"""Commercial homogeneous decay calibration, with whole conditions held out.

The temperature law assumes constant density, fixed lattice temperature and
negligible spatial energy-flux divergence. It identifies a numerical reference
time, not a measured material constant or a spatial energy-transport closure.
"""
from dataclasses import dataclass
import re
import numpy as np
from scipy.optimize import least_squares


def _real_array(value, name):
    a=np.asarray(value)
    if a.dtype.kind not in 'fiu' or a.ndim!=1 or not np.all(np.isfinite(a)):
        raise ValueError(name+' must be a finite real vector')
    a=np.array(a,dtype=float,copy=True);a.setflags(write=False)
    return a


@dataclass(frozen=True)
class CommercialDecayTrace:
    case_id: str
    carrier: str
    role: str
    times_s: object
    temperatures_K: object
    lattice_temperature_K: float
    source_sha256: str
    material_model: str

    def __post_init__(self):
        if not self.case_id or self.carrier not in ('electrons','holes') or self.role not in ('calibration','holdout'):
            raise ValueError('unique case, explicit carrier and calibration/holdout role required')
        if not isinstance(self.source_sha256,str) or not re.fullmatch('[0-9a-f]{64}',self.source_sha256):
            raise ValueError('original commercial export SHA256 required')
        if not isinstance(self.material_model,str) or not self.material_model:
            raise ValueError('material model identity required')
        tl=np.asarray(self.lattice_temperature_K)
        if tl.ndim or tl.dtype.kind not in 'fiu' or not np.isfinite(tl) or tl<=0:
            raise ValueError('positive real lattice temperature required')
        t=_real_array(self.times_s,'times');T=_real_array(self.temperatures_K,'temperatures')
        if len(t)<6 or T.shape!=t.shape or np.any(t<0) or np.any(np.diff(t)<=0) or np.any(T<=0):
            raise ValueError('six ordered nonnegative time/positive temperature pairs required')
        object.__setattr__(self,'times_s',t);object.__setattr__(self,'temperatures_K',T)
        object.__setattr__(self,'lattice_temperature_K',float(tl))


def calibrate_commercial_relaxation(traces, *, tau_bounds_s=(1e-15,1e-10),
                                   minimum_signal_K=.1, holdout_relative_gate=.01,
                                   training_relative_gate=.01):
    """Fit only calibration data; condition holdouts on their first sample.

    The holdout initial temperature is supplied as an initial condition. No
    held-out decay slope, amplitude adjustment or error is used by optimization.
    A failed holdout is returned explicitly and never called a validation.
    Every training trace must fit the constant-tau law within its own initial
    excess-normalized gate. Both carriers' training checks precede any holdout
    prediction; a failed training law raises instead of returning a calibrated
    flag that a caller checking only the holdouts could accept.
    """
    traces=tuple(traces)
    if not traces or any(not isinstance(t,CommercialDecayTrace) for t in traces):
        raise ValueError('commercial traces required')
    if len({t.case_id for t in traces})!=len(traces):raise ValueError('duplicate case identity')
    if len({t.source_sha256 for t in traces})!=len(traces):raise ValueError('duplicate source leaks conditions')
    if len({t.material_model for t in traces})!=1:raise ValueError('material model changed')
    bounds=_real_array(tau_bounds_s,'tau bounds')
    if bounds.shape!=(2,) or not 0<bounds[0]<bounds[1]:raise ValueError('ordered positive tau bounds required')
    for v in (minimum_signal_K,holdout_relative_gate,training_relative_gate):
        a=np.asarray(v)
        if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a) or a<=0:
            raise ValueError('positive signal and holdout gates required')
    fits={};validation=[];training_checks=[]
    for carrier in ('electrons','holes'):
        training=[t for t in traces if t.carrier==carrier and t.role=='calibration']
        held=[t for t in traces if t.carrier==carrier and t.role=='holdout']
        if not training or not held:raise ValueError('each carrier requires calibration and independent holdout')
        for trace in training+held:
            signal=trace.temperatures_K-trace.lattice_temperature_K
            if signal[0]<minimum_signal_K or np.any(signal<=0):
                raise ValueError('resolvable strictly positive hot-carrier decay required')
            if signal[-1]>=.9*signal[0]:raise ValueError('decay is not identifiable')
        # Independent amplitude per training curve; a single shared tau.
        starts=[float(t.temperatures_K[0]-t.lattice_temperature_K) for t in training]
        slopes=[-(t.times_s[-1]-t.times_s[0])/np.log((t.temperatures_K[-1]-t.lattice_temperature_K)/s)
                for t,s in zip(training,starts)]
        initial=np.r_[np.log(np.clip(np.median(slopes),bounds[0]*1.01,bounds[1]/1.01)),np.log(starts)]
        def residual(x):
            tau=np.exp(x[0])
            return np.concatenate([(np.exp(x[i+1])*np.exp(-(t.times_s-t.times_s[0])/tau)
                 -(t.temperatures_K-t.lattice_temperature_K))/starts[i] for i,t in enumerate(training)])
        fit=least_squares(residual,initial,bounds=(np.r_[np.log(bounds[0]),np.full(len(training),-40.)],
            np.r_[np.log(bounds[1]),np.full(len(training),40.)]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
        if not fit.success or np.any(fit.active_mask) or np.linalg.matrix_rank(fit.jac)!=len(initial):
            raise ValueError('relaxation fit did not identify an interior full-rank solution')
        tau=float(np.exp(fit.x[0]));fits[carrier]=dict(tau_s=tau,
            calibration_case_ids=[t.case_id for t in training],
            calibration_source_sha256=[t.source_sha256 for t in training],
            maximum_training_normalized_error=float(np.max(np.abs(fit.fun))))
        offset=0
        for t in training:
            error=float(np.max(np.abs(fit.fun[offset:offset+len(t.times_s)])))
            offset+=len(t.times_s)
            passed=bool(np.isfinite(error) and error<=training_relative_gate)
            training_checks.append(dict(case_id=t.case_id,carrier=carrier,source_sha256=t.source_sha256,
                maximum_peak_normalized_error=error,accepted=passed))
            if not passed:
                raise ValueError('calibration constant-tau decay exceeds training gate: '+t.case_id+' / '+carrier)
    # Finish both species' training admission before computing held-out curves.
    for carrier in ('electrons','holes'):
        tau=fits[carrier]['tau_s']
        held=[t for t in traces if t.carrier==carrier and t.role=='holdout']
        for t in held:
            amplitude=float(t.temperatures_K[0]-t.lattice_temperature_K)
            predicted=t.lattice_temperature_K+amplitude*np.exp(-(t.times_s-t.times_s[0])/tau)
            error=float(np.max(np.abs(predicted-t.temperatures_K))/amplitude)
            validation.append(dict(case_id=t.case_id,source_sha256=t.source_sha256,carrier=carrier,
                supplied_initial_temperature_K=float(t.temperatures_K[0]),predicted_temperatures_K=predicted.tolist(),
                maximum_peak_normalized_error=error,accepted=bool(error<=holdout_relative_gate)))
    return dict(parameters=fits,holdouts=validation,holdouts_accepted=all(v['accepted'] for v in validation),
        training_checks=training_checks,training_accepted=True,accepted=all(v['accepted'] for v in validation),
        commercial_relaxation_calibrated=True,experimental_validated=False,
        spatial_transport_validated=False,complete_device_energy=False,physical_validated=False,
        law='T(t)=Tl+[T(t0)-Tl]*exp[-(t-t0)/tau]; homogeneous constant-density MB limit',
        holdout_initial_temperature_is_supplied=True)
