"""Opt-in RN113 reconditioning with exact saved perturbation accounting."""
from dataclasses import asdict
from tcad.physics.native_boltzmann import _numbers
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_recomputed_lattice_transport import advance_mb_recomputed_conducting_endpoint_split
from tcad.postprocess.boltzmann_accounted_rounding import (
    split_rounding,audit_mb_accounted_rounding,audit_mb_rounded_conducting_split,
)
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint


def round_mb_endpoints(states,*,particle_atol=1e-9,energy_atol_J=1e-27):
    from tcad.core import _accounted_rounding_mb as native
    states=tuple(states);pa,ea=map(float,_numbers([particle_atol,energy_atol_J],(2,)))
    if min(pa,ea)<=0 or not 1<=len(states)<=256 or any(type(s) is not MBScaledTransportState for s in states):
        raise ValueError('typed accounted rounding states and positive budgets required')
    raw=[native.endpoint(s.endpoint) for s in states]
    new=tuple(MBScaledTransportState(tuple(split_rounding(r)[0]),s.time_s,s.physical_clock) for s,r in zip(states,raw))
    report=dict(scope='explicit_accounted_RN113_endpoint_rounding',execution_backend='native',precision_bits=113,
        old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,new)),
        cells=raw,physical_time_advanced=False,exact_recurrence_preserved=False,
        coordinate_differences_exactly_saved=True,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_accounted_rounding(states,new,report,particle_atol=pa,energy_atol_J=ea)
    return new,report


def advance_mb_rounded_conducting_split(configurations,states,faces,thermal_faces,dt_s,*,
                                      impulses_J=None,particle_atol=1e-9,energy_atol_J=1e-27):
    configurations=tuple(configurations);states=tuple(states);faces=tuple(faces);thermal_faces=tuple(thermal_faces)
    pa,ea=map(float,_numbers([particle_atol,energy_atol_J],(2,)))
    rounded,r=round_mb_endpoints(states,particle_atol=pa,energy_atol_J=ea/2)
    new,child=advance_mb_recomputed_conducting_endpoint_split(configurations,rounded,faces,thermal_faces,dt_s,
        impulses_J=impulses_J,energy_atol_J=ea/2)
    report=dict(scope='accounted_RN113_transport_collision_Fourier_Lie_split',execution_backend='native',precision_bits=113,
        temporal_order=1,dt_s=float(dt_s),old_sha256=list(map(_saved_fingerprint,states)),
        new_sha256=list(map(_saved_fingerprint,new)),rounded_states=list(map(asdict,rounded)),rounding=r,conducting=child,
        exact_recurrence_preserved=False,rounding_error_included=True,physical_time_advanced=True,
        lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False)
    report['independent_audit']=audit_mb_rounded_conducting_split(configurations,states,new,report,faces=faces,
        thermal_faces=thermal_faces,dt_s=dt_s,impulses_J=impulses_J,particle_atol=pa,energy_atol_J=ea)
    return new,report
