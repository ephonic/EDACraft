"""Constant-tau collision/source transaction for authoritative affine MB cells."""
from dataclasses import replace
from decimal import Decimal
import math
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.physics.boltzmann_affine_face import endpoint,encode
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState,_fingerprint

OP_NAMES=('numerator','leading_quotient','division_residual','correction_quotient','trial_lattice','trial_dTl',
    'electron_capacity_product','hole_capacity_product','electron_pre_exchange','hole_pre_exchange',
    'electron_exchange','hole_exchange','lattice_change','committed_dTl','electron_rebase','hole_rebase',
    'electron_physical_change','hole_physical_change','electron_stored_change','hole_stored_change')


def advance_mb_affine_collision(config,old,dt_s,*,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    from tcad.core._bindings import native_mb_affine_collision_raw
    a=_numbers([dt_s,energy_atol_J],(2,));q=_numbers(impulses_J,(3,));anchor,change=endpoint(old);p=config.parameters
    end=old.time_s+float(dt_s)
    if min(a)<=0 or not math.isfinite(end) or end<=old.time_s:raise ValueError('positive resolvable collision clock/budget required')
    if any(Decimal(p[j])!=0 for j in (6,7,10,11)):raise ValueError('affine collision currently requires a=c=0 constant tau')
    if any(Decimal(anchor.frame[j])!=Decimal(p[k]) for j,k in ((3,0),(4,1),(7,12),(8,13))):raise ValueError('affine collision capacity/volume/bounds configuration mismatch')
    for valley in (config.valleys_n,config.valleys_p):
        if not valley or len(valley)%4 or any(Decimal(valley[j])!=Decimal(valley[3]) for j in range(3,len(valley),4)):raise ValueError('equal-offset MB valleys required')
    raw=native_mb_affine_collision_raw(encode(old),[_decimal(a[0]),p[2],p[3],*map(_decimal,q)]);index=1
    def vector():
        nonlocal index
        n=Decimal(raw[index]);index+=1
        if n!=n.to_integral_value() or not 0<=n<=4096:raise ValueError('affine collision vector coverage')
        n=int(n);v=raw[index:index+n];index+=n
        if len(v)!=n:raise ValueError('truncated affine collision vector')
        return v
    R=vector();quot=vector();thermal=vector();n=[vector() for _ in range(2)];K=[vector() for _ in range(2)]
    C=[vector() for _ in range(2)];delta=[vector() for _ in range(2)];capacity=[vector() for _ in range(2)];D=vector();sources=[vector() for _ in range(3)]
    count=Decimal(raw[index]);index+=1
    if count!=count.to_integral_value() or not 0<=count<=4096:raise ValueError('affine collision lineage coverage')
    rows=[]
    for _ in range(int(count)):
        kind,source=raw[index:index+2];index+=2
        values=vector()
        rows.append(dict(kind=int(Decimal(kind)),source=bool(Decimal(source)),input_expansion=values,operations=[dict(name=k,value=vector()) for k in OP_NAMES]))
    L=vector();un=vector();up=vector()
    if len(raw)!=index+3:raise ValueError('affine collision output coverage')
    newanchor=replace(anchor,frame=(*anchor.frame,*L))
    new=MBFiniteVolumeState(newanchor,change[0],change[1],(*change[2],*un),(*change[3],*up),end)
    report=dict(scope='constant_tau_affine_MB_collision_BE',execution_backend='native',precision_bits=113,
        configuration_sha256=config.sha256,old_sha256=_fingerprint(old),new_sha256=_fingerprint(new),dt_s=_decimal(a[0]),
        impulses_J=list(map(_decimal,q)),alpha=raw[0],exchange_fractions=R,lattice_quotients=quot,thermal_expansion=thermal,
        densities=n,kinetic=K,capacities=C,excess=delta,capacity_ratios=capacity,denominator=D,source_densities=sources,
        lineage_groups=rows,lattice_increment_expansion=L,carrier_stored_increments=[un,up],temperatures_K=raw[index:],
        quotient_model='one_residual_correction',response_groups='exact_linear_input_expansions',physical_time_advanced=True,expanded_density_collision_supported=True,
        dynamic_lattice_supported=True,constant_tau_only=True,device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_affine_collision import audit_mb_affine_collision
    check=audit_mb_affine_collision(config,old,new,report,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J)
    if not check['valid']:raise ValueError('independent affine collision audit failed: '+str(check))
    report['independent_audit']=check;return new,report
