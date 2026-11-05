"""Repeated explicit flat MB transport with unchanged affine anchors."""
from decimal import Decimal
import math
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState,FIELDS,_fingerprint
from tcad.physics.boltzmann_affine_face import endpoint,encode,affine_mb_flat_face


def advance_mb_affine_transport(states,faces,dt_s,*,particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    from tcad.core._bindings import native_mb_fv_integrate_raw,native_mb_affine_cell_raw
    states=tuple(states);faces=tuple(faces);limits=_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,))
    if min(limits)<=0 or not 1<=len(states)<=256 or len(faces)>512:raise ValueError('positive bounded affine transport problem required')
    anchors=[endpoint(s) for s in states]
    if any(s.time_s!=states[0].time_s for s in states):raise ValueError('simultaneous affine cells required')
    end=states[0].time_s+float(dt_s)
    if not math.isfinite(end) or end<=states[0].time_s:raise ValueError('representable affine clock advance required')
    transfers=[];signed=[[[] for _ in range(4)] for _ in states];seen=set()
    for spec in faces:
        if not isinstance(spec,dict) or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):raise ValueError('explicit affine face specification required')
        i=spec['owner'];contact='reservoir' in spec;j=None if contact else spec['neighbor']
        if type(i) is not int or not 0<=i<len(states) or (not contact and (type(j) is not int or not 0<=j<len(states) or i==j)):
            raise ValueError('affine face index invalid')
        if not contact:
            edge=tuple(sorted((i,j)))
            if edge in seen:raise ValueError('duplicate affine internal face')
            seen.add(edge)
        other=spec['reservoir'] if contact else states[j]
        moment=affine_mb_flat_face(states[i],other,spec['geometry'],face_kind='contact' if contact else 'bulk',
            number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
        source=[moment['carriers'][k][key] for key in ('number_expansion','energy_expansion') for k in range(2)]
        integrated=[native_mb_fv_integrate_raw(v,_decimal(limits[0])) for v in source]
        transfers.append(dict(owner=i,neighbor=j,moment=moment,integrated=integrated))
        for k,raw in enumerate(integrated):
            signed[i][k].extend(('-'+x if not x.startswith('-') else x[1:]) for x in raw)
            if not contact:signed[j][k].extend(raw)
    new=[];cells=[]
    for i,(anchor,previous) in enumerate(anchors):
        raw=native_mb_affine_cell_raw(encode(states[i]),*signed[i]);index=0;changes=[]
        for old in previous:
            count=Decimal(raw[index]);index+=1
            if count!=count.to_integral_value() or not 0<=count<=4096:raise ValueError('affine cell increment coverage invalid')
            count=int(count);added=tuple(raw[index:index+count]);index+=count
            if len(added)!=count:raise ValueError('affine cell increment truncated')
            changes.append((*old,*added))
        if len(raw)!=index+3:raise ValueError('affine cell trailing output')
        new.append(MBFiniteVolumeState(anchor,*changes,end));cells.append(dict(temperatures_K=raw[index:]))
    report=dict(scope='repeated_flat_MB_affine_transport',execution_backend='native',precision_bits=113,
        dt_s=_decimal(limits[0]),old_sha256=[_fingerprint(s) for s in states],new_sha256=[_fingerprint(s) for s in new],
        transfers=transfers,cells=cells,time_s=end,physical_time_advanced=True,repeat_transport_supported=True,
        device_statistics_selected=False,field_work_inferred=False,lattice_flux_included=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_affine_transport import audit_mb_affine_transport
    check=audit_mb_affine_transport(states,new,report,faces=faces,dt_s=dt_s,particle_atol=particle_atol,
        energy_atol_J=energy_atol_J,number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    if not check['valid']:raise ValueError('independent affine MB transport audit failed')
    report['independent_audit']=check;return tuple(new),report
