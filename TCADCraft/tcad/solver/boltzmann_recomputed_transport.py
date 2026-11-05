"""Audited native transport of complete scaled endpoints; collisions are separate."""
from dataclasses import dataclass,asdict,replace
import math
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.physics.boltzmann_affine_face import encode
from tcad.solver.boltzmann_scaled_split import MBScaledFiniteVolumeState
from tcad.postprocess.boltzmann_scaled_split import audit_mb_scaled_state,_clock,_saved_fingerprint
from tcad.postprocess.boltzmann_recomputed_transport import (
    point,scaled_value_fraction,audit_scaled_endpoint_import,moment_wire,split_cell,_wire,
    audit_mb_scaled_face,audit_mb_scaled_transport,
)


from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState

def advance_mb_scaled_transport(states,faces,dt_s,*,particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    from tcad.core._scaled_transport import native_mb_scaled_face_raw,native_mb_scaled_cell_raw
    states=tuple(states);faces=tuple(faces)
    dt,pa,ea,nfa,efa=map(float,_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,)))
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=len(states)<=256 or len(faces)>512 or any(type(s) is not MBScaledTransportState for s in states):
        raise ValueError('bounded typed scaled transport request required')
    start=states[0];end=start.time_s+dt
    if not math.isfinite(end) or end<=start.time_s or any(s.time_s!=start.time_s or s.physical_clock!=start.physical_clock for s in states):
        raise ValueError('synchronized advancing scaled clocks required')
    transfers=[];signed=[[] for s in states];seen=set()
    for f in faces:
        if not isinstance(f,dict) or set(f) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):raise ValueError('explicit scaled face topology required')
        i=f['owner'];contact='reservoir' in f;j=None if contact else f['neighbor']
        if type(i) is not int or not 0<=i<len(states) or (not contact and (type(j) is not int or not 0<=j<len(states) or i==j)):
            raise ValueError('scaled face index invalid')
        if not contact:
            edge=tuple(sorted((i,j)))
            if edge in seen:raise ValueError('duplicate scaled internal face')
            seen.add(edge)
        other=f['reservoir'] if contact else states[j]
        if type(other) is not MBScaledTransportState or other.physical_clock!=start.physical_clock or other.time_s!=start.time_s:
            raise ValueError('simultaneous scaled reservoir clock required')
        g=tuple(map(float,_numbers(f['geometry'],(5,))))
        if (g[2]>0)!= (not contact):raise ValueError('scaled bulk/contact geometry kind mismatch')
        raw=native_mb_scaled_face_raw(list(states[i].endpoint),list(other.endpoint),list(map(_decimal,g)))
        check=audit_mb_scaled_face(states[i].endpoint,other.endpoint,g,raw,face_kind='contact' if contact else 'bulk',number_atol_s=nfa,energy_atol_W=efa)
        transfers.append(dict(owner=i,neighbor=j,raw=raw,independent_audit=check))
        moments=moment_wire(raw);signed[i].append((-1,moments))
        if not contact:signed[j].append((1,moments))
    final=[];cells=[]
    for state,moments in zip(states,signed):
        command=['mb_scaled_transfers_v1','113',str(len(moments))]
        for sign,wire in moments:command.extend((str(sign),str(len(wire)),*wire))
        raw=native_mb_scaled_cell_raw(list(state.endpoint),command,[_decimal(dt)],list(state.physical_clock))
        endpoint,clock,v,ps,e=split_cell(raw)
        final.append(MBScaledTransportState(tuple(endpoint),float(scaled_value_fraction(clock)),tuple(clock)));cells.append(raw)
    report=dict(scope='full_density_scaled_MB_transport',execution_backend='native',precision_bits=113,
        model='full_density_rational_difference',old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,final)),
        dt_s=dt,transfers=transfers,cells=cells,physical_time_advanced=True,scaled_transport_supported=True,
        collision_included=False,lattice_flux_included=False,field_work_included=False,complete_device_energy=False,physical_validated=False)
    check=audit_mb_scaled_transport(states,final,report,faces=faces,dt_s=dt,particle_atol=pa,energy_atol_J=ea,number_atol_s=nfa,energy_atol_W=efa)
    if not check['valid']:raise ValueError('independent scaled transport audit failed: '+str(check))
    report['independent_audit']=check;return tuple(final),report
