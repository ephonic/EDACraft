"""Identify explicit local exchange laws, keeping material acceptance separate.

Observations must provide the same-density carrier energy difference and the
isolated signed carrier-to-lattice power density. Total device heating, SRH
lifetimes and temperature decay slopes are not interchangeable with these.
The supplied standard uncertainty is for log(abs(delta_u / power)); it must
already account for their covariance. State coordinates are conditioning data.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from .energy_relaxation import EnergyRelaxationPowerLaw


def _positive_scalar(value, name):
    a=np.asarray(value)
    if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a) or not 0<float(a)<np.inf:
        raise ValueError(name+' must be a positive finite real scalar')
    return float(a)


def _vector(value, name, *, positive=False):
    a=np.asarray(value)
    if a.ndim!=1 or a.dtype.kind not in 'fiu' or not np.all(np.isfinite(a)):
        raise ValueError(name+' must be a finite real vector')
    with np.errstate(over='ignore',under='ignore'):
        a=np.array(a,dtype=float,copy=True)
    if not np.all(np.isfinite(a)) or (positive and np.any(a<=0)):
        raise ValueError(name+' must be representable'+(' and positive' if positive else ''))
    # Immutable storage, including against setflags(write=True).
    return np.frombuffer(a.tobytes(),dtype=float)


@dataclass(frozen=True)
class RelaxationExchangeCondition:
    condition_id: str
    carrier: str
    role: str
    density_m3: object
    carrier_temperature_K: object
    lattice_temperature_K: object
    energy_difference_J_m3: object
    power_to_lattice_W_m3: object
    log_tau_standard_uncertainty: object
    source_sha256: str
    source_kind: str
    source_reference: str
    material_model: str
    energy_difference_definition: str = 'fixed_density_carrier_energy_minus_lattice_equilibrium'
    power_definition: str = 'isolated_carrier_to_lattice_relaxation'

    def __post_init__(self):
        for name in ('condition_id','source_reference','material_model'):
            if not isinstance(getattr(self,name),str) or not getattr(self,name).strip():
                raise ValueError(name+' identity required')
        if self.carrier not in ('electrons','holes') or self.role not in ('calibration','holdout'):
            raise ValueError('explicit carrier and whole-condition role required')
        if self.source_kind not in ('synthetic','commercial','measured'):
            raise ValueError('explicit source kind required')
        if not isinstance(self.source_sha256,str) or not re.fullmatch('[0-9a-f]{64}',self.source_sha256):
            raise ValueError('original observation source SHA256 required')
        if self.energy_difference_definition!='fixed_density_carrier_energy_minus_lattice_equilibrium':
            raise ValueError('same-density carrier energy difference required')
        if self.power_definition!='isolated_carrier_to_lattice_relaxation':
            raise ValueError('isolated relaxation power required; total heating is not an observation')
        names=('density_m3','carrier_temperature_K','lattice_temperature_K',
               'energy_difference_J_m3','power_to_lattice_W_m3','log_tau_standard_uncertainty')
        for name in names:
            object.__setattr__(self,name,_vector(getattr(self,name),name,
                positive=name not in ('energy_difference_J_m3','power_to_lattice_W_m3')))
        if not len(self.density_m3) or any(getattr(self,n).shape!=self.density_m3.shape for n in names):
            raise ValueError('nonempty aligned observations required')
        du=self.energy_difference_J_m3;power=self.power_to_lattice_W_m3
        dT=self.carrier_temperature_K-self.lattice_temperature_K
        if (np.any(du==0) or np.any(power==0) or np.any(dT==0)
                or np.any(np.sign(du)!=np.sign(power)) or np.any(np.sign(du)!=np.sign(dT))):
            raise ValueError('resolved thermodynamically signed exchange required')
        # Subtract logs instead of dividing very large/small dimensional values.
        log_tau=np.log(abs(du))-np.log(abs(power))
        with np.errstate(over='ignore',under='ignore'):
            tau=np.exp(log_tau)
        if not np.all(np.isfinite(tau)) or np.any(tau<=0):
            raise ValueError('observed effective time outside positive float64 range')


def load_relaxation_exchange_condition(path):
    """Read one complete condition from exact JSON bytes with explicit SI units.

    One file may contain both carriers, but cannot mix calibration and holdout.
    Hashing pins the observation bytes; it does not authenticate the claimed
    commercial run or measurement. No sorting, resampling or unit guessing.
    """
    raw=Path(path).read_bytes();data=json.loads(raw)
    units=dict(density='m^-3',temperature='K',energy_density='J/m^3',
               power_density='W/m^3',log_tau_uncertainty='1')
    if not isinstance(data,dict) or data.get('schema')!='tcad.local_relaxation_exchange.v1' or data.get('units')!=units:
        raise ValueError('explicit local exchange schema and exact SI units required')
    rows=data.get('carriers')
    if not isinstance(rows,list) or not rows:
        raise ValueError('nonempty carrier observation records required')
    fields={'carrier','density_m3','carrier_temperature_K','lattice_temperature_K',
            'energy_difference_J_m3','power_to_lattice_W_m3','log_tau_standard_uncertainty'}
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=fields:
            raise ValueError('complete carrier exchange fields required')
        result.append(RelaxationExchangeCondition(**row,condition_id=data['condition_id'],role=data['role'],
            source_kind=data['source_kind'],source_reference=data['source_reference'],
            material_model=data['material_model'],source_sha256=hashlib.sha256(raw).hexdigest()))
    if len({c.carrier for c in result})!=len(result):
        raise ValueError('duplicate carrier in condition export')
    return tuple(result)


def _condition_partition(conditions):
    """Keep every a/c excitation pair in one role across files and species.

    New Tc samples or exchange measurements at the same (Tl, density) do not
    establish a new whole-condition a/c holdout. One exported condition may
    contain several pairs; every supplied observation participates here.
    """
    groups={}
    for c in conditions:
        for lattice,density in zip(c.lattice_temperature_K,c.density_m3):
            groups.setdefault((float(lattice),float(density)),[]).append(c)
    rows=[]
    for (lattice,density),members in sorted(groups.items()):
        roles={c.role for c in members}
        if len(roles)!=1:
            raise ValueError('lattice-temperature/density condition crosses calibration/holdout roles')
        rows.append(dict(lattice_temperature_K=lattice,density_m3=density,role=next(iter(roles)),
            condition_ids=sorted({c.condition_id for c in members}),
            carriers=sorted({c.carrier for c in members}),observations=len(members)))
    return dict(condition_axes=['lattice_temperature_K','density_m3'],grouped_across_carriers=True,
        carrier_temperature_and_export_do_not_define_new_ac_condition=True,groups=rows)


def calibrate_energy_relaxation_power_law(conditions, *, reference_temperature_K=300.,
        reference_density_m3=1e25, tau0_bounds_s=(1e-15,1e-10), exponent_bound=10.,
        maximum_design_condition=1e6, standardized_error_gate=3., holdout_relative_gate=.05):
    """Weighted log-time regression with four identifiable parameters/carrier.

    Fit only calibration conditions. Sigma describes independent log-time
    errors at exact state coordinates; the covariance is conditional on that
    assumption, not a confidence interval for a full material/device model.
    A held-out condition must lie within the training coordinate envelope.
    Source provenance is recorded, not authenticated by supplied metadata.
    Even an accepted fit never sets commercial/experimental acceptance flags.
    Every supplied (Tl, density) pair must stay in one role across both carriers;
    changing Tc samples or export identity cannot create a new a/c condition.
    """
    conditions=tuple(conditions)
    if not conditions or any(type(c) is not RelaxationExchangeCondition for c in conditions):
        raise ValueError('explicit exchange observation conditions required')
    tref=_positive_scalar(reference_temperature_K,'reference temperature')
    nref=_positive_scalar(reference_density_m3,'reference density')
    bound=_positive_scalar(exponent_bound,'exponent bound')
    condition_gate=_positive_scalar(maximum_design_condition,'design condition gate')
    sigma_gate=_positive_scalar(standardized_error_gate,'standardized error gate')
    relative_gate=_positive_scalar(holdout_relative_gate,'holdout relative gate')
    bounds=_vector(tau0_bounds_s,'tau0 bounds',positive=True)
    if bounds.shape!=(2,) or bounds[0]>=bounds[1] or condition_gate<=1:
        raise ValueError('ordered reference-time bounds and design gate >1 required')
    if len({(c.carrier,c.condition_id) for c in conditions})!=len(conditions):
        raise ValueError('duplicate carrier condition identity')
    if len({c.material_model for c in conditions})!=1 or len({c.source_kind for c in conditions})!=1:
        raise ValueError('one material model and one source kind per fit required')
    # A single export may contain both carriers. Its role must remain whole.
    for key in ('condition_id','source_sha256'):
        roles={}
        for c in conditions:roles.setdefault(getattr(c,key),set()).add(c.role)
        if any(len(v)!=1 for v in roles.values()):
            raise ValueError('calibration/holdout leakage through '+key)
    partition=_condition_partition(conditions)

    def design(c):
        return np.column_stack((np.ones(len(c.density_m3)),
            np.log(c.lattice_temperature_K)-np.log(tref),
            np.log(c.carrier_temperature_K)-np.log(tref),
            np.log(c.density_m3)-np.log(nref)))

    parameters={};holdouts=[];training_accepted=True
    for carrier in ('electrons','holes'):
        train=[c for c in conditions if c.carrier==carrier and c.role=='calibration']
        held=[c for c in conditions if c.carrier==carrier and c.role=='holdout']
        if not train or not held:raise ValueError('each carrier requires training and independent whole-condition holdout')
        X=np.concatenate([design(c) for c in train])
        y=np.concatenate([np.log(abs(c.energy_difference_J_m3))-np.log(abs(c.power_to_lattice_W_m3)) for c in train])
        sigma=np.concatenate([c.log_tau_standard_uncertainty for c in train])
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            A=X/sigma[:,None];target=y/sigma
            scales=np.linalg.norm(A,axis=0)
        if (len(y)<=4 or not np.all(np.isfinite(A)) or not np.all(np.isfinite(target))
                or not np.all(np.isfinite(scales)) or np.any(scales<=0)):
            raise ValueError('overdetermined finite full-rank calibration design required')
        normalized=A/scales
        U,s,Vt=np.linalg.svd(normalized,full_matrices=False)
        rank=int(np.count_nonzero(s>s[0]*max(normalized.shape)*np.finfo(float).eps))
        cond=float(s[0]/s[-1]) if s[-1]>0 else float('inf')
        if rank!=4 or not np.isfinite(cond) or cond>condition_gate:
            raise ValueError('relaxation exponents are unidentifiable or ill-conditioned')
        beta=(Vt.T@((U.T@target)/s))/scales
        if (not np.all(np.isfinite(beta)) or not np.log(bounds[0])<beta[0]<np.log(bounds[1])
                or np.any(abs(beta[1:])>=bound)):
            raise ValueError('fit is outside open constitutive parameter bounds')
        # Covariance for supplied independent standard uncertainties; no residual rescaling.
        inverse=(Vt.T/s)/scales[:,None]
        covariance=inverse@inverse.T
        residual=(X@beta-y)/sigma
        train_error=float(np.max(abs(residual)))
        training_accepted &= train_error<=sigma_gate
        lower=X[:,1:].min(axis=0);upper=X[:,1:].max(axis=0)
        law=EnergyRelaxationPowerLaw(tref,nref,*beta[1:])
        parameters[carrier]=dict(tau0_s=float(np.exp(beta[0])),law=dict(zip(law.__dataclass_fields__,law.parameters())),
            log_parameter_order=['log_tau0_s','lattice_temperature_exponent','carrier_temperature_exponent','density_exponent'],
            conditional_log_parameter_covariance=covariance.tolist(),design_rank=rank,
            normalized_design_condition=cond,training_observations=len(y),
            maximum_training_standardized_error=train_error,training_accepted=bool(train_error<=sigma_gate),
            calibration_condition_ids=[c.condition_id for c in train],
            calibration_source_sha256=[c.source_sha256 for c in train],
            training_log_coordinate_envelope=[lower.tolist(),upper.tolist()])
        for c in held:
            Z=design(c);observed=np.log(abs(c.energy_difference_J_m3))-np.log(abs(c.power_to_lattice_W_m3))
            predicted=Z@beta
            with np.errstate(over='ignore',under='ignore',invalid='ignore'):
                effective=np.exp(predicted);relative=abs(np.expm1(predicted-observed))
            if not np.all(np.isfinite(effective)) or np.any(effective<=0) or not np.all(np.isfinite(relative)):
                raise ValueError('predicted held-out relaxation outside representable range')
            # Independent holdout: include the conditional fitted-parameter error.
            prediction_variance=np.einsum('ij,jk,ik->i',Z,covariance,Z)
            if not np.all(np.isfinite(prediction_variance)) or np.any(prediction_variance<0):
                raise ValueError('invalid conditional prediction covariance')
            predictive_sigma=np.hypot(c.log_tau_standard_uncertainty,np.sqrt(prediction_variance))
            error=float(np.max(abs(predicted-observed)/predictive_sigma))
            rel=float(np.max(relative))
            # Rounding tolerance is solely for identical decimal coordinates.
            envelope=bool(np.all(Z[:,1:]>=lower-1e-12) and np.all(Z[:,1:]<=upper+1e-12))
            holdouts.append(dict(condition_id=c.condition_id,carrier=carrier,source_sha256=c.source_sha256,
                predicted_tau_s=effective.tolist(),observed_tau_s=np.exp(observed).tolist(),
                predictive_log_tau_standard_uncertainty=predictive_sigma.tolist(),
                maximum_standardized_error=error,maximum_relative_error=rel,
                within_training_coordinate_envelope=envelope,
                accepted=bool(error<=sigma_gate and rel<=relative_gate and envelope)))
    accepted=bool(training_accepted and all(h['accepted'] for h in holdouts))
    return dict(parameters=parameters,holdouts=holdouts,fit_accepted=accepted,
        whole_condition_holdout_checked=True,whole_condition_partition=partition,
        training_accepted=bool(training_accepted),holdouts_accepted=all(h['accepted'] for h in holdouts),
        gates=dict(standardized_error=sigma_gate,holdout_relative=relative_gate,
                   maximum_normalized_design_condition=condition_gate),
        observation_sources=[dict(condition_id=c.condition_id,carrier=c.carrier,role=c.role,
            source_sha256=c.source_sha256,source_kind=c.source_kind,source_reference=c.source_reference,
            material_model=c.material_model) for c in conditions],
        law='tau0*(Tl/Tref)^a*(Tc/Tref)^b*(density/nref)^c',
        uncertainty_assumption='independent log-time standard errors; exact state coordinates; conditional covariance',
        provenance_authenticated=False,local_constitutive_fit_only=True,
        state_dependent_relaxation_calibrated=False,commercial_validated=False,
        experimental_validated=False,physical_validated=False,complete_device_energy=False)


def fitted_relaxation_configuration(result):
    """Export an accepted local fit to the explicit solver constructor keywords.

    This is configuration conversion, not an authentication/acceptance boundary.
    The caller retains responsibility for the supplied observational provenance.
    """
    if not isinstance(result,dict) or result.get('fit_accepted') is not True:
        raise ValueError('accepted local constitutive fit required for configuration export')
    configuration={}
    for carrier,suffix in (('electrons','n'),('holes','p')):
        p=result['parameters'][carrier]
        configuration['relaxation_time_'+suffix+'_s']=_positive_scalar(p['tau0_s'],'reference time')
        configuration['relaxation_law_'+suffix]=EnergyRelaxationPowerLaw(**p['law'])
    return configuration
