"""Bounded native MB particle/band energy transactions, separate from collisions."""
from dataclasses import dataclass
from decimal import Decimal
import math
import numpy as np
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal


@dataclass(frozen=True)
class MBParticleEnergyState:
    frame: tuple
    electron_excess: tuple
    hole_excess: tuple
    time_s: float
    origin_configuration_sha256: str

    def __post_init__(self):
        for field,lo,hi in (('frame',10,256),('electron_excess',1,4096),('hole_excess',1,4096)):
            raw=tuple(str(x) for x in getattr(self,field))
            if not lo<=len(raw)<=hi or any(not Decimal(x).is_finite() for x in raw):
                raise ValueError('finite bounded MB energy expansions required')
            object.__setattr__(self,field,raw)
        if isinstance(self.time_s,(bool,np.bool_)) or not math.isfinite(self.time_s) or self.time_s<0:
            raise ValueError('finite nonnegative MB clock required')


def expand_mb_relaxation_state(config,state):
    """Lossless storage adapter; the result is not accepted by the collision API."""
    if state.configuration_sha256!=config.sha256:raise ValueError('MB configuration mismatch')
    for valley in (config.valleys_n,config.valleys_p):
        if not valley or len(valley)%4 or any(Decimal(valley[j])!=Decimal(valley[3]) for j in range(3,len(valley),4)):
            raise ValueError('equal-offset MB valleys required')
    s=state.raw_state;p=config.parameters
    return MBParticleEnergyState((*s[:3],*p[:2],config.valleys_n[3],config.valleys_p[3],*p[12:14],s[3],*s[6:]),
                                 (s[4],),(s[5],),state.time_s,config.sha256)


def update_mb_particle_energy(old,densities,bands_J,*,energy_impulses_J=(0.,0.),energy_atol_J=1e-27):
    from tcad.core._bindings import native_boltzmann_particle_energy_raw
    n=_numbers(densities,(2,));e=_numbers(bands_J,(2,));q=_numbers(energy_impulses_J,(2,))
    a=_numbers([energy_atol_J],(1,))
    if a[0]<=0:raise ValueError('positive independent energy budget required')
    raw=native_boltzmann_particle_energy_raw(old.frame,old.electron_excess,old.hole_excess,list(map(_decimal,(*n,*e,*q))))
    if len(raw)<12:raise ValueError('MB particle energy output coverage mismatch')
    counts=[Decimal(x) for x in raw[4:6]]
    if any(x!=x.to_integral_value() or not 1<=x<=4096 for x in counts):raise ValueError('MB component counts invalid')
    cn,cp=map(int,counts)
    if len(raw)!=12+cn+cp:raise ValueError('MB particle energy output coverage mismatch')
    frame=(*raw[:2],*old.frame[2:5],*raw[2:4],*old.frame[7:])
    new=MBParticleEnergyState(frame,tuple(raw[6:6+cn]),tuple(raw[6+cn:6+cn+cp]),old.time_s,old.origin_configuration_sha256)
    report=dict(scope='equal_offset_MB_particle_band_energy_transaction',execution_backend='native',precision_bits=113,
                old_temperatures_K=raw[-6:-3],temperatures_K=raw[-3:],physical_time_advanced=False,
                origin_configuration_sha256=old.origin_configuration_sha256,energy_impulses_J=list(map(_decimal,q)),
                band_work_inferred=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_particle_energy import audit_mb_particle_energy
    audit=audit_mb_particle_energy(old,new,report,densities=densities,bands_J=bands_J,
                                  energy_impulses_J=energy_impulses_J,energy_atol_J=energy_atol_J)
    if not audit['valid']:raise ValueError('independent MB particle energy audit failed')
    report['independent_audit']=audit
    return new,report
