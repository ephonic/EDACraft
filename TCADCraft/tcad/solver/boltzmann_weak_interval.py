"""Opt-in native weak-collision full intervals with physical clock projection."""
from dataclasses import asdict, replace
from tcad.physics.native_boltzmann import _numbers
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_recomputed_transport import advance_mb_scaled_transport
from tcad.solver.boltzmann_weak_endpoint_collision import advance_mb_weak_endpoint_collision
from tcad.solver.boltzmann_recomputed_lattice_transport import apply_mb_recomputed_lattice_stage
from tcad.solver.boltzmann_accounted_rounding import round_mb_endpoints
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tcad.postprocess.boltzmann_weak_endpoint_collision import configuration
from tcad.postprocess.boltzmann_weak_interval import audit_mb_weak_endpoint_split, audit_mb_weak_conducting_split, audit_mb_weak_rounded_split

def advance_mb_weak_endpoint_split(configurations,states,faces,dt_s,*,impulses_J=None,
                            particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    configurations=tuple(configurations);states=tuple(states);faces=tuple(faces)
    dt,pa,ea,nfa,efa=map(float,_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,)))
    n=len(states)
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=n<=256 or len(configurations)!=n or any(type(s) is not MBScaledTransportState for s in states):
        raise ValueError('bounded typed complete endpoint split required')
    q=tuple((0.,0.,0.) for s in states) if impulses_J is None else tuple(tuple(map(float,_numbers(row,(3,)))) for row in impulses_J)
    if len(q)!=n:raise ValueError('one impulse triple per complete endpoint cell required')
    middle,transport=advance_mb_scaled_transport(states,faces,dt,particle_atol=pa,energy_atol_J=ea/2,number_atol_s=nfa,energy_atol_W=efa)
    auxiliary=[];collisions=[];final=[]
    for cfg,mid,impulse in zip(configurations,middle,q):
        child,report=advance_mb_weak_endpoint_collision(cfg,mid,dt,impulses_J=impulse,energy_atol_J=ea/(2*n))
        auxiliary.append(child);collisions.append(report)
        final.append(replace(child,time_s=mid.time_s,physical_clock=mid.physical_clock))
    final=tuple(final)
    report=dict(scope='weak_complete_endpoint_same_interval_Lie_split',execution_backend='native',precision_bits=113,
        method='full_density_scaled_transport_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='exact_scaled_auxiliary_then_project',dt_s=dt,physical_time_advanced=True,
        physical_interval_clock=[list(states[0].physical_clock),list(middle[0].physical_clock)],
        configuration_sha256=[configuration(c)[1] for c in configurations],old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,final)),
        transported_states=list(map(asdict,middle)),transport=transport,collision_states=list(map(asdict,auxiliary)),collisions=collisions,
        monolithic_coupled_BE=False,lattice_flux_included=False,field_work_included=False,complete_device_energy=False,physical_validated=False)
    check=audit_mb_weak_endpoint_split(configurations,states,final,report,faces=faces,dt_s=dt,impulses_J=q,
        particle_atol=pa,energy_atol_J=ea,number_atol_s=nfa,energy_atol_W=efa)
    if not check['valid']:raise ValueError('independent complete endpoint full split audit failed')
    report['independent_audit']=check;return final,report

def advance_mb_weak_conducting_split(configurations,states,faces,thermal_faces,dt_s,*,impulses_J=None,energy_atol_J=1e-27):
    configurations=tuple(configurations);states=tuple(states);faces=tuple(faces);thermal_faces=tuple(thermal_faces)
    dt,ea=map(float,_numbers([dt_s,energy_atol_J],(2,)))
    if min(dt,ea)<=0:raise ValueError('positive conducting split duration/budget required')
    middle,carrier=advance_mb_weak_endpoint_split(configurations,states,faces,dt,impulses_J=impulses_J,energy_atol_J=ea/2)
    new,lattice=apply_mb_recomputed_lattice_stage(middle,thermal_faces,dt,energy_atol_J=ea/2)
    report=dict(scope='weak_endpoint_transport_collision_Fourier_Lie_split',execution_backend='native',precision_bits=113,temporal_order=1,autonomous_operators_only=True,monolithic_coupled_BE=False,dt_s=dt,old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,new)),pre_lattice_states=list(map(asdict,middle)),carrier_split=carrier,lattice=lattice,physical_time_advanced=True,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_weak_conducting_split(configurations,states,new,report,faces=faces,thermal_faces=thermal_faces,dt_s=dt,impulses_J=impulses_J,energy_atol_J=ea)
    return new,report

def advance_mb_weak_rounded_split(configurations,states,faces,thermal_faces,dt_s,*,
                                      impulses_J=None,particle_atol=1e-9,energy_atol_J=1e-27):
    configurations=tuple(configurations);states=tuple(states);faces=tuple(faces);thermal_faces=tuple(thermal_faces)
    pa,ea=map(float,_numbers([particle_atol,energy_atol_J],(2,)))
    rounded,r=round_mb_endpoints(states,particle_atol=pa,energy_atol_J=ea/2)
    new,child=advance_mb_weak_conducting_split(configurations,rounded,faces,thermal_faces,dt_s,
        impulses_J=impulses_J,energy_atol_J=ea/2)
    report=dict(scope='accounted_weak_RN113_transport_collision_Fourier_Lie_split',execution_backend='native',precision_bits=113,
        temporal_order=1,dt_s=float(dt_s),old_sha256=list(map(_saved_fingerprint,states)),
        new_sha256=list(map(_saved_fingerprint,new)),rounded_states=list(map(asdict,rounded)),rounding=r,conducting=child,
        exact_recurrence_preserved=False,rounding_error_included=True,physical_time_advanced=True,
        lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_weak_rounded_split(configurations,states,new,report,faces=faces,
        thermal_faces=thermal_faces,dt_s=dt_s,impulses_J=impulses_J,particle_atol=pa,energy_atol_J=ea)
    return new,report

