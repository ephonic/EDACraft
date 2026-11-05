"""Native frozen Fourier operator and atomic three-operator MB Lie split."""
from dataclasses import asdict
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_recomputed_endpoint_split import advance_mb_recomputed_endpoint_split
from tcad.postprocess.boltzmann_recomputed_lattice_transport import (_topology,face_values,split_lattice_recomputed_cell,audit_mb_recomputed_lattice_stage,audit_mb_recomputed_conducting_endpoint_split)
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint


def apply_mb_recomputed_lattice_stage(states,faces,dt_s,*,energy_atol_J=1e-27):
    from tcad.core import _lattice_mb as face_native
    from tcad.core import _recomputed_lattice_mb as native
    states=tuple(states);faces=tuple(faces)
    dt,ea=map(float,_numbers([dt_s,energy_atol_J],(2,)))
    if min(dt,ea)<=0 or any(type(s) is not MBScaledTransportState for s in states):raise ValueError('typed lattice stage and positive exposure/budget required')
    topology=list(_topology(states,faces));proofs=[];signed=[[] for s in states]
    for f,(i,j,bath) in zip(faces,topology):
        g=list(map(_decimal,_numbers(f['geometry'],(5,))))
        if bath:
            temperature=_numbers([f['bath_temperature_K']],(1,))[0]
            raw=face_native.bath(states[i].endpoint,[*g,_decimal(temperature)])
        else:raw=face_native.face(states[i].endpoint,states[j].endpoint,g)
        proofs.append(raw);G,values,parts=face_values(raw);signed[i].append((-1,parts[4]))
        if not bath:signed[j].append((1,parts[4]))
    new=[];cells=[]
    for state,moments in zip(states,signed):
        command=['mb_lattice_transfers_v1','113',str(len(moments))]
        for sign,wire in moments:command.extend((str(sign),str(len(wire)),*wire))
        raw=native.cell(state.endpoint,command,[_decimal(dt)]);endpoint,v=split_lattice_recomputed_cell(raw)
        new.append(MBScaledTransportState(tuple(endpoint),state.time_s,state.physical_clock));cells.append(raw)
    new=tuple(new)
    report=dict(scope='complete_endpoint_recomputed_Fourier_stage',execution_backend='native',precision_bits=113,exposure_dt_s=dt,old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,new)),faces=proofs,cells=cells,physical_time_advanced=False,division_remainders_serialized=False,division_remainders_independently_recomputed=True,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_recomputed_lattice_stage(states,new,report,faces=faces,dt_s=dt,energy_atol_J=ea)
    return new,report


def advance_mb_recomputed_conducting_endpoint_split(configurations,states,faces,thermal_faces,dt_s,*,impulses_J=None,energy_atol_J=1e-27):
    configurations=tuple(configurations);states=tuple(states);faces=tuple(faces);thermal_faces=tuple(thermal_faces)
    dt,ea=map(float,_numbers([dt_s,energy_atol_J],(2,)))
    if min(dt,ea)<=0:raise ValueError('positive conducting split duration/budget required')
    middle,carrier=advance_mb_recomputed_endpoint_split(configurations,states,faces,dt,impulses_J=impulses_J,energy_atol_J=ea/2)
    new,lattice=apply_mb_recomputed_lattice_stage(middle,thermal_faces,dt,energy_atol_J=ea/2)
    report=dict(scope='complete_endpoint_transport_collision_recomputed_lattice_Lie_split',execution_backend='native',precision_bits=113,temporal_order=1,autonomous_operators_only=True,monolithic_coupled_BE=False,dt_s=dt,old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,new)),pre_lattice_states=list(map(asdict,middle)),carrier_split=carrier,lattice=lattice,physical_time_advanced=True,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_recomputed_conducting_endpoint_split(configurations,states,new,report,faces=faces,thermal_faces=thermal_faces,dt_s=dt,impulses_J=impulses_J,energy_atol_J=ea)
    return new,report
