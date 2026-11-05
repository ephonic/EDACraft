"""Native expanded-energy flat-band MB bulk/contact moments; no state update."""
from decimal import Decimal
from dataclasses import asdict
import hashlib,json
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal


def expanded_mb_flat_face(owner,neighbor,geometry,*,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    from tcad.core._bindings import native_boltzmann_expanded_flat_face_raw
    g=_numbers(geometry,(5,));limits=_numbers([number_atol_s,energy_atol_W],(2,))
    if min(limits)<=0 or face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):
        raise ValueError('positive independent budgets and bulk/contact geometry required')
    if owner.time_s!=neighbor.time_s:raise ValueError('simultaneous MB endpoint states required')
    a,b=owner.frame,neighbor.frame
    if (a[2],a[3],a[9:])!=(b[2],b[3],b[9:]) or any(Decimal(a[j])!=Decimal(b[j]) for j in (5,6)):
        raise ValueError('flat band and identical lattice coordinates required')
    raw=native_boltzmann_expanded_flat_face_raw(a,owner.electron_excess,owner.hole_excess,b,neighbor.electron_excess,neighbor.hole_excess,list(map(_decimal,g)))
    index=0
    def integer():
        nonlocal index
        x=Decimal(raw[index]);index+=1
        if x!=x.to_integral_value() or not 0<=x<=4096:raise ValueError('MB flat face coverage invalid')
        return int(x)
    def vector():
        nonlocal index
        n=integer();v=raw[index:index+n];index+=n
        if len(v)!=n:raise ValueError('MB flat face truncated expansion')
        return v
    inverse=raw[index];index+=1;thermal=vector();carriers=[]
    for _ in range(2):
        coefficients=vector();normalization=[vector() for _ in range(4)];rows=[]
        for _ in range(integer()):rows.append(dict(kind=integer(),factors=vector(),value=vector()))
        carriers.append(dict(coefficients=coefficients,normalization=normalization,terms=rows,
            number_expansion=[x for r in rows if r['kind']<2 for x in r['value']],
            energy_expansion=[x for r in rows if r['kind']>=2 for x in r['value']]))
    if index!=len(raw):raise ValueError('MB flat face trailing output')
    fingerprint=lambda state:hashlib.sha256(json.dumps(asdict(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    report=dict(scope='uniform_DOS_flat_band_common_lattice_MB_expanded_face',face_kind=face_kind,
        execution_backend='native',precision_bits=113,geometry=list(map(_decimal,g)),inverse_Cv=inverse,
        thermal_expansion=thermal,carriers=carriers,owner_sha256=fingerprint(owner),neighbor_sha256=fingerprint(neighbor),
        time_s=owner.time_s,physical_time_advanced=False,device_statistics_selected=False,
        field_work_inferred=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_expanded_flat_face import audit_expanded_mb_flat_face
    audit=audit_expanded_mb_flat_face(owner,neighbor,report,geometry=geometry,face_kind=face_kind,
        number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    if not audit['valid']:raise ValueError('independent MB expanded flat face audit failed')
    report['independent_audit']=audit
    return report
