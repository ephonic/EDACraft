"""Identify tau0 and Tl/Tc/density exponents from homogeneous MB cooling.

Each trace has prescribed constant lattice temperature and carrier density.
No temperature derivatives, exchange-power surrogates or measurement error
bars are inferred. Full-rank excitation across conditions is mandatory.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from scipy.special import logsumexp
from numpy.polynomial.legendre import leggauss
from .carrier_relaxation_calibration import CommercialDecayTrace
from .temperature_relaxation_calibration import _positive,predict_temperature_power_decay
from .energy_relaxation import EnergyRelaxationPowerLaw


@dataclass(frozen=True)
class DensityResolvedDecayTrace(CommercialDecayTrace):
    density_m3: float

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.case_id,str):raise ValueError('string condition identity required')
        object.__setattr__(self,'density_m3',_positive(self.density_m3,'constant carrier density'))
        for name in ('times_s','temperatures_K'):
            values=getattr(self,name)
            if not np.all(np.isfinite(values)):raise ValueError('float64 trace representation required')
            object.__setattr__(self,name,np.frombuffer(values.tobytes(),dtype=float))
        _positive(self.lattice_temperature_K,'prescribed lattice temperature')


def _condition_partition(traces):
    """Keep an a/c excitation pair together across files and carrier species.

    A new initial carrier temperature or a new clock tests a different cooling
    trajectory at the same a/c condition. It cannot make that lattice/density
    pair an independent whole-condition holdout for the four-parameter fit.
    This checks supplied conditions, not the authenticity of their provenance.
    """
    groups={}
    for trace in traces:
        key=(trace.lattice_temperature_K,trace.density_m3)
        groups.setdefault(key,[]).append(trace)
    rows=[]
    for (lattice,density),group in sorted(groups.items()):
        roles={t.role for t in group}
        if len(roles)!=1:
            raise ValueError('lattice-temperature/density condition crosses calibration/holdout roles')
        rows.append(dict(lattice_temperature_K=lattice,density_m3=density,role=next(iter(roles)),
            case_ids=sorted(t.case_id for t in group),carriers=sorted({t.carrier for t in group})))
    return dict(condition_axes=['lattice_temperature_K','density_m3'],
        grouped_across_carriers=True,initial_temperature_and_clock_do_not_define_new_ac_condition=True,
        groups=rows)


def calibrate_multicondition_relaxation(traces,*,reference_temperature_K=300.,reference_density_m3=1e22,
        tau0_bounds_s=(1e-15,1e-10),exponent_bounds=(-4.,4.),minimum_signal_K=1.,
        maximum_fit_condition=1e3,training_relative_gate=.01,holdout_relative_gate=.01):
    """Fit four parameters using training traces; predict whole held conditions.

    log(dt)=log(tau0)+a*log(Tl/Tref)+c*log(n/nref)+log(I_b),
    I_b=integral(log(excess/excess0),0) (Tc/Tref)**b dz.
    Quadrature integrates log excess, removing the equilibrium pole. An analytic
    Jacobian checks four independent directions. Errors are scaled by each
    trace's own initial excess. Holdouts must lie inside the coordinate envelope
    of the training set; that envelope is not a proof of material applicability.
    Each supplied (Tl,density) pair belongs to exactly one role across both
    carriers. Replicates and new initial temperatures stay in the same role.
    """
    traces=tuple(traces)
    if not traces or any(type(t) is not DensityResolvedDecayTrace for t in traces):
        raise ValueError('density-resolved homogeneous traces required')
    ref=_positive(reference_temperature_K,'reference temperature');nr=_positive(reference_density_m3,'reference density')
    signal=_positive(minimum_signal_K,'minimum signal');condgate=_positive(maximum_fit_condition,'condition gate')
    gates=(_positive(training_relative_gate,'training gate'),_positive(holdout_relative_gate,'holdout gate'))
    if condgate<=1:raise ValueError('condition gate must exceed one')
    bounds=[]
    for values in (tau0_bounds_s,exponent_bounds):
        v=np.asarray(values)
        if v.shape!=(2,) or v.dtype.kind not in 'fiu' or not np.all(np.isfinite(v)):
            raise ValueError('finite ordered parameter bounds required')
        v=np.asarray(v,float)
        if not np.all(np.isfinite(v)) or v[0]>=v[1]:raise ValueError('finite ordered parameter bounds required')
        bounds.append(v)
    if bounds[0][0]<=0:raise ValueError('positive reference time bounds required')
    for key in ('case_id','source_sha256'):
        if len({getattr(t,key) for t in traces})!=len(traces):raise ValueError('duplicate condition/source leakage')
    if len({t.material_model for t in traces})!=1:raise ValueError('material identity changed')
    partition=_condition_partition(traces)
    for t in traces:
        excess=t.temperatures_K-t.lattice_temperature_K
        if excess[0]<signal or np.any(excess<=0) or np.any(np.diff(excess)>=0) or excess[-1]>.9*excess[0]:
            raise ValueError('resolved strictly monotone hot-carrier cooling required')
    nodes,weights=leggauss(48);parameters={};training=[];holdouts=[]
    lower=np.r_[np.log(bounds[0][0]),np.repeat(bounds[1][0],3)]
    upper=np.r_[np.log(bounds[0][1]),np.repeat(bounds[1][1],3)]
    for carrier in ('electrons','holes'):
        train=[t for t in traces if t.carrier==carrier and t.role=='calibration']
        held=[t for t in traces if t.carrier==carrier and t.role=='holdout']
        if not train or not held:raise ValueError('each carrier needs training and whole-condition holdouts')
        prepared=[]
        for t in train:
            excess=t.temperatures_K-t.lattice_temperature_K
            width=np.log(excess[0])-np.log(excess[1:])
            z=-.5*width[:,None]*(nodes[None,:]+1)
            logT=np.log(t.lattice_temperature_K+excess[0]*np.exp(z))-np.log(ref)
            prepared.append((width,logT,np.log(t.times_s[1:]-t.times_s[0]),
                np.log(t.lattice_temperature_K)-np.log(ref),np.log(t.density_m3)-np.log(nr)))
        def evaluate(x,jacobian=False):
            rows=[]
            for width,logT,logdt,logTl,logN in prepared:
                terms=x[2]*logT+np.log(weights)
                logsum=logsumexp(terms,axis=1)
                if jacobian:
                    db=np.sum(np.exp(terms-logsum[:,None])*logT,axis=1)
                    rows.append(np.column_stack((np.ones(len(width)),np.full(len(width),logTl),db,np.full(len(width),logN))))
                else:rows.append(x[0]+x[1]*logTl+x[3]*logN+np.log(.5*width)+logsum-logdt)
            return np.vstack(rows) if jacobian else np.concatenate(rows)
        def condition(J):
            scale=np.linalg.norm(J,axis=0)
            if np.any(scale<=0) or not np.all(np.isfinite(scale)) or np.linalg.matrix_rank(J)!=4:
                raise ValueError('four independent tau0/Tl/Tc/density directions required')
            value=float(np.linalg.cond(J/scale))
            if not np.isfinite(value) or value>condgate:raise ValueError('ill-conditioned four-parameter decay design')
            return value
        initial_tau=np.median([-(t.times_s[-1]-t.times_s[0])/
            np.log((t.temperatures_K[-1]-t.lattice_temperature_K)/(t.temperatures_K[0]-t.lattice_temperature_K)) for t in train])
        start=np.clip(np.r_[np.log(initial_tau),0.,0.,0.],lower,upper)
        condition(evaluate(start,True))
        solved=least_squares(evaluate,start,jac=lambda x:evaluate(x,True),bounds=(lower,upper),
            xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=200)
        if not solved.success or np.any(solved.active_mask) or np.any(solved.x-lower<1e-7) or np.any(upper-solved.x<1e-7):
            raise ValueError('interior four-parameter relaxation fit failed')
        cond=condition(solved.jac);logtau,a,b,c=map(float,solved.x);tau=float(np.exp(logtau))
        law=EnergyRelaxationPowerLaw(ref,nr,a,b,c)
        parameters[carrier]=dict(tau0_s=tau,lattice_temperature_exponent=a,carrier_temperature_exponent=b,
            density_exponent=c,reference_temperature_K=ref,reference_density_m3=nr,
            normalized_fit_condition=cond,maximum_log_duration_residual=float(np.max(abs(solved.fun))),
            calibration_case_ids=[t.case_id for t in train],calibration_source_sha256=[t.source_sha256 for t in train],
            law=dict(zip(law.__dataclass_fields__,law.parameters())))
        envelope=np.array([[min(t.lattice_temperature_K for t in train),max(t.lattice_temperature_K for t in train)],
            [min(t.density_m3 for t in train),max(t.density_m3 for t in train)],
            [min(min(t.temperatures_K) for t in train),max(max(t.temperatures_K) for t in train)]])
        for group,dest,gate in ((train,training,gates[0]),(held,holdouts,gates[1])):
            for t in group:
                logeffective=logtau+a*(np.log(t.lattice_temperature_K)-np.log(ref))+c*(np.log(t.density_m3)-np.log(nr))
                with np.errstate(over='ignore',under='ignore'):effective=float(np.exp(logeffective))
                _positive(effective,'condition reference time')
                predicted=predict_temperature_power_decay(t.times_s,t.temperatures_K[0],t.lattice_temperature_K,effective,b,ref)
                error=float(np.max(abs(predicted-t.temperatures_K))/(t.temperatures_K[0]-t.lattice_temperature_K))
                inside=bool(envelope[0,0]<=t.lattice_temperature_K<=envelope[0,1] and
                    envelope[1,0]<=t.density_m3<=envelope[1,1] and
                    envelope[2,0]<=min(t.temperatures_K) and max(t.temperatures_K)<=envelope[2,1])
                dest.append(dict(case_id=t.case_id,carrier=carrier,source_sha256=t.source_sha256,
                    supplied_initial_temperature_K=float(t.temperatures_K[0]),density_m3=t.density_m3,
                    predicted_temperatures_K=predicted.tolist(),inside_training_envelope=inside,
                    maximum_peak_normalized_error=error,accepted=bool(error<=gate and (inside or t.role=='calibration'))))
    return dict(parameters=parameters,training=training,holdouts=holdouts,
        fit_accepted=all(t['accepted'] for t in training+holdouts),training_accepted=all(t['accepted'] for t in training),
        holdouts_accepted=all(t['accepted'] for t in holdouts),fitted_parameters=['tau0_s','lattice_temperature_exponent','carrier_temperature_exponent','density_exponent'],
        law='homogeneous MB tau=tau0*(Tl/Tref)^a*(Tc/Tref)^b*(density/nref)^c',
        holdout_initial_temperature_is_supplied=True,provenance_authenticated=False,
        whole_condition_holdout_checked=True,whole_condition_partition=partition,
        uncertainty_intervals_computed=False,state_dependent_relaxation_calibrated=False,
        experimental_validated=False,physical_validated=False,spatial_transport_validated=False,complete_device_energy=False)
