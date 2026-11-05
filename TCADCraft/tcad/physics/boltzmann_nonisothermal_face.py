"""Flat MB moments with independent endpoint lattice coordinates and capacities."""
from decimal import Decimal
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState,FIELDS,_fingerprint
from tcad.physics.boltzmann_affine_face import endpoint,encode

OP_NAMES=('kinetic_difference','kinetic_sum','density_difference','difference_times_sum','neighbor_kinetic_square',
    'square_times_leading_density_difference','leading_owner_inverse','owner_low_product','owner_inverse_correction',
    'leading_inverse_difference','owner_density_low_product','owner_inverse_difference_correction','neighbor_density_low_product',
    'neighbor_inverse_difference_correction','rational_difference','number','band_energy','kinetic_energy','energy')


def nonisothermal_mb_flat_face(owner,neighbor,geometry,*,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    from tcad.core._bindings import native_mb_nonisothermal_face_raw
    g=_numbers(geometry,(5,));limits=_numbers([number_atol_s,energy_atol_W],(2,))
    if min(limits)<=0 or face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):raise ValueError('positive affine face budgets and valid geometry kind required')
    a,_=endpoint(owner);b,_=endpoint(neighbor)
    if owner.time_s!=neighbor.time_s:raise ValueError('simultaneous affine endpoints required')
    if any(Decimal(a.frame[j])!=Decimal(b.frame[j]) for j in (5,6)):
        raise ValueError('nonisothermal face flat bands required')
    raw=native_mb_nonisothermal_face_raw(encode(owner),encode(neighbor),list(map(_decimal,g)));index=1
    def vector():
        nonlocal index
        n=Decimal(raw[index]);index+=1
        if n!=n.to_integral_value() or not 0<=n<=4096:raise ValueError('affine vector coverage invalid')
        n=int(n);v=raw[index:index+n];index+=n
        if len(v)!=n:raise ValueError('truncated affine vector')
        return v
    quotients=[vector(),vector()];thermal=[vector(),vector()];carriers=[]
    for _ in range(2):
        coeff=vector();norm=[vector() for _ in range(4)]
        ops=[dict(name=name,value=vector()) for name in OP_NAMES]
        carriers.append(dict(coefficients=coeff,normalization=norm,operations=ops,
            number_expansion=ops[15]['value'],energy_expansion=ops[18]['value']))
    if index!=len(raw):raise ValueError('affine face trailing output')
    report=dict(scope='flat_MB_nonisothermal_affine_face',execution_backend='native',precision_bits=113,face_kind=face_kind,
        alpha=raw[0],lattice_quotients=quotients,thermal_expansions=thermal,lattice_normalization='compensated_capacity_quotients',geometry=list(map(_decimal,g)),carriers=carriers,
        owner_sha256=_fingerprint(owner),neighbor_sha256=_fingerprint(neighbor),time_s=owner.time_s,
        inverse_density_model='first_order_inverse_density_difference',affine_endpoint_supported=True,lattice_heterogeneity_supported=True,lattice_flux_included=False,
        physical_time_advanced=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_nonisothermal_transport import audit_nonisothermal_mb_face
    check=audit_nonisothermal_mb_face(owner,neighbor,report,geometry=geometry,face_kind=face_kind,
        number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    if not check['valid']:raise ValueError('independent affine MB face audit failed')
    report['independent_audit']=check;return report
