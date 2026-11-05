"""Expansion-preserving closed MB cell collision/source transactions."""
from decimal import Decimal
import math
import numpy as np
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState


def advance_mb_expanded_collision(config,old,dt_s,*,impulses_J=(0.,0.,0.),energy_atol_J=1e-27,max_nfev=256):
    from tcad.core._bindings import native_boltzmann_expanded_collision_raw
    a=_numbers([dt_s,energy_atol_J],(2,));q=_numbers(impulses_J,(3,))
    if np.any(a<=0) or not math.isfinite(old.time_s+float(dt_s)) or old.time_s+float(dt_s)<=old.time_s:
        raise ValueError('positive resolvable finite MB clock and energy budget required')
    p=config.parameters
    if any(Decimal(old.frame[j])!=Decimal(p[k]) for j,k in ((3,0),(4,1),(7,12),(8,13))):
        raise ValueError('MB collision capacity/volume/bounds configuration mismatch')
    for valley in (config.valleys_n,config.valleys_p):
        if not valley or len(valley)%4 or any(Decimal(valley[j])!=Decimal(valley[3]) for j in range(3,len(valley),4)):
            raise ValueError('equal-offset MB collision valleys required')
    raw=native_boltzmann_expanded_collision_raw(old.frame,old.electron_excess,old.hole_excess,
        [*p[2:12],_decimal(a[0])],list(map(_decimal,q)),max_nfev=max_nfev)
    count=len(old.electron_excess)+len(old.hole_excess)+3
    if len(raw)<11 or Decimal(raw[0])!=count:raise ValueError('MB collision lineage coverage mismatch')
    width=Decimal(raw[10])
    if width!=width.to_integral_value() or not 0<=width<=246:raise ValueError('MB lattice expansion coverage mismatch')
    lattice=raw[11:11+int(width)]
    rows=[];offset=11+int(width)
    for _ in range(count):
        head=raw[offset:offset+5]
        if len(head)!=5 or any(Decimal(x) not in (1,4) for x in head[3:]):raise ValueError('MB collision representation coverage mismatch')
        cn,cp=map(lambda x:int(Decimal(x)),head[3:]);offset+=5
        rows.append(dict(lattice_increment_density=head[0],exchange_densities=head[1:3],
            electron_excess=raw[offset:offset+cn],hole_excess=raw[offset+cn:offset+cn+cp]))
        offset+=cn+cp
    if offset!=len(raw):raise ValueError('MB collision lineage coverage mismatch')
    def flattened(field):return tuple(x for r in rows for x in r[field] if Decimal(x)!=0) or ('0',)
    new=MBParticleEnergyState((*old.frame,*lattice),flattened('electron_excess'),flattened('hole_excess'),
                              old.time_s+float(dt_s),old.origin_configuration_sha256)
    report=dict(scope='closed_equal_offset_MB_expanded_BE',execution_backend='native',precision_bits=113,
        configuration_sha256=config.sha256,origin_configuration_sha256=old.origin_configuration_sha256,
        dt_s=float(dt_s),impulses_J=list(map(_decimal,q)),old_temperatures_K=raw[4:7],temperatures_K=raw[7:10],
        log_relaxation_times_s=raw[2:4],residual_evaluations=int(Decimal(raw[1])),lineage_groups=rows,lattice_increment_expansion=lattice,
        complete_device_energy=False,physical_validated=False,device_statistics_selected=False,
        measured_ac_material_calibration=False,carrier_temperature_exponent_supported=0)
    from tcad.postprocess.boltzmann_expanded_collision import audit_mb_expanded_collision
    audit=audit_mb_expanded_collision(config,old,new,report,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J)
    if not audit['valid']:raise ValueError('independent expanded MB collision audit failed')
    report['independent_audit']=audit
    return new,report
