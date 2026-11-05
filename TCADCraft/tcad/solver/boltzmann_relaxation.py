"""Explicit closed MB cell, fixed densities/bands, equal offsets and b=0."""
from dataclasses import dataclass
from decimal import Decimal
import hashlib,json
import math
import numpy as np
from tcad.physics.native_boltzmann import _numbers,_valleys
from tcad.physics.native_fermi_local import _decimal
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw


@dataclass(frozen=True)
class MBRelaxationConfiguration:
    parameters: tuple
    valleys_n: tuple
    valleys_p: tuple

    def __post_init__(self):
        for field in ('parameters','valleys_n','valleys_p'):
            value=tuple(str(x) for x in getattr(self,field))
            if any(not Decimal(x).is_finite() for x in value):raise ValueError('finite MB configuration required')
            object.__setattr__(self,field,value)
        if len(self.parameters)!=14:raise ValueError('MB configuration parameter coverage mismatch')

    @property
    def sha256(self):
        return hashlib.sha256(json.dumps((self.parameters,self.valleys_n,self.valleys_p),separators=(',',':')).encode()).hexdigest()

    @classmethod
    def create(cls,capacity_J_m3_K,volume_m3,tau_n_s,tau_p_s,valleys_n,valleys_p,
               *,laws=(EnergyRelaxationPowerLaw(),EnergyRelaxationPowerLaw()),temperature_bounds=(2.,99999.)):
        scales=_numbers([capacity_J_m3_K,volume_m3,tau_n_s,tau_p_s],(4,))
        bounds=_numbers(temperature_bounds,(2,))
        if np.any(scales<=0) or not 1<bounds[0]<bounds[1]<1e5:raise ValueError('positive scales and open MB bounds required')
        if len(laws)!=2 or any(not isinstance(l,EnergyRelaxationPowerLaw) or l.carrier_temperature_exponent!=0 for l in laws):
            raise ValueError('two explicit relaxation laws with b=0 required')
        packed=[]
        for valleys in (valleys_n,valleys_p):
            vs,p=_valleys(valleys)
            if any(v.band_offset_owner_J!=vs[0].band_offset_owner_J for v in vs):raise ValueError('split valleys unsupported in MB relaxation')
            packed.append(tuple(p))
        params=[*scales]
        for law in laws:params.extend((law.reference_temperature_K,law.reference_density_m3,law.lattice_temperature_exponent,law.density_exponent))
        return cls(tuple(map(_decimal,(*params,*bounds))),*packed)


@dataclass(frozen=True)
class MBRelaxationState:
    raw_state: tuple
    time_s: float
    configuration_sha256: str

    def __post_init__(self):
        raw=tuple(str(x) for x in self.raw_state)
        if not 6<=len(raw)<=4097 or any(not Decimal(x).is_finite() for x in raw):raise ValueError('finite MB state and lattice expansion required')
        if isinstance(self.time_s,(bool,np.bool_)) or not math.isfinite(self.time_s) or self.time_s<0:raise ValueError('finite nonnegative MB clock required')
        object.__setattr__(self,'raw_state',raw)


def initialize_mb_relaxation(config,densities,reference_temperature_K,temperatures,*,time_s=0.):
    from tcad.core._bindings import native_boltzmann_relaxation_raw
    n=_numbers(densities,(2,));t=_numbers(temperatures,(3,));r=_numbers([reference_temperature_K,time_s],(2,))
    if r[1]<0:raise ValueError('nonnegative initial clock required')
    raw=native_boltzmann_relaxation_raw(list(map(_decimal,(*n,r[0],*t))),
        [*config.parameters,'1','1e-27','0','0','0'],config.valleys_n,config.valleys_p,True)
    return MBRelaxationState(tuple(raw),float(time_s),config.sha256)


def advance_mb_relaxation(config,old,dt_s,*,energy_atol_J=1e-27,impulses_J=(0.,0.,0.),max_nfev=256):
    from tcad.core._bindings import native_boltzmann_relaxation_raw
    if old.configuration_sha256!=config.sha256:raise ValueError('MB state/configuration mismatch')
    a=_numbers([dt_s,energy_atol_J],(2,));q=_numbers(impulses_J,(3,))
    if np.any(a<=0) or old.time_s+float(dt_s)<=old.time_s:raise ValueError('positive resolvable MB clock and budget required')
    raw=native_boltzmann_relaxation_raw(old.raw_state,[*config.parameters,*map(_decimal,(*a,*q))],
        config.valleys_n,config.valleys_p,max_nfev=max_nfev)
    width=len(old.raw_state)+1
    if len(raw)!=width+15:raise ValueError('MB relaxation output coverage mismatch')
    new=MBRelaxationState(tuple(raw[:width]),old.time_s+float(dt_s),config.sha256)
    values=raw[width:]
    report=dict(scope='closed_equal_offset_MB_energy_excess_BE',configuration_sha256=config.sha256,
        execution_backend='native',dt_s=float(dt_s),impulses_J=list(map(_decimal,q)),
        temperatures_K=values[:3],exchange_J=values[3:5],energy_increments_J=values[5:8],
        residuals_J=values[8:12],log_relaxation_times_s=values[12:14],residual_evaluations=int(Decimal(values[14])),
        complete_device_energy=False,physical_validated=False,measured_ac_material_calibration=False,
        device_statistics_selected=False,carrier_temperature_exponent_supported=0)
    from tcad.postprocess.boltzmann_relaxation import audit_mb_relaxation_step
    audit=audit_mb_relaxation_step(config,old,new,report,energy_atol_J=energy_atol_J,impulses_J=impulses_J)
    if not audit['valid']:raise ValueError('independent MB relaxation audit failed')
    report['independent_audit']=audit
    return new,report
