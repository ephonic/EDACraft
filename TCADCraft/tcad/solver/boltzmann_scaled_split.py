"""Atomic affine-input split with native scaled collision and immutable output."""
from dataclasses import dataclass,asdict
import math

from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.physics.boltzmann_affine_face import encode
from tcad.solver.boltzmann_frozen_finite_volume import _fingerprint
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport
from tcad.solver.boltzmann_scaled_candidate import MBScaledCollisionCandidate,scaled_candidate_from_saved
from tcad.postprocess.boltzmann_scaled_split import audit_mb_scaled_split_interval


@dataclass(frozen=True)
class MBScaledFiniteVolumeState:
    collision: MBScaledCollisionCandidate
    time_s: float
    physical_clock: tuple

    def __post_init__(self):
        if type(self.collision) is not MBScaledCollisionCandidate:raise ValueError('immutable scaled collision required')
        if type(self.time_s) is not float or not math.isfinite(self.time_s) or self.time_s<0:raise ValueError('scaled physical clock required')
        clock=tuple(self.physical_clock)
        if any(type(x) is not str for x in clock):raise ValueError('scaled string clock required')
        object.__setattr__(self,'physical_clock',clock)


def advance_mb_scaled_split_interval(configurations,states,faces,dt_s,*,impulses_J=None,
                                      particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    """Return the whole audited transaction or raise without changing inputs.

    Input transport uses the existing affine path. Output retains the exact
    scaled collision increments. A subsequent scaled transport is unsupported.
    """
    states=tuple(states);configurations=tuple(configurations);faces=tuple(faces)
    if any(type(s) is MBScaledFiniteVolumeState for s in states):
        raise ValueError('scaled transport consumer not implemented; no scalar conversion permitted')
    dt,pa,ea,nfa,efa=map(float,_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,)))
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=len(states)<=256 or len(configurations)!=len(states):
        raise ValueError('one configuration per bounded scaled split cell required')
    start=states[0].time_s;end=start+dt
    if not math.isfinite(end) or not start<end or any(s.time_s!=start for s in states):raise ValueError('synchronized advancing scaled split clocks required')
    q=tuple((0.,0.,0.) for s in states) if impulses_J is None else tuple(tuple(_numbers(row,(3,))) for row in impulses_J)
    if len(q)!=len(states):raise ValueError('one explicit impulse triple per scaled split cell required')
    from tcad.core._scaled_mb import native_mb_scaled_powerlaw_raw
    intermediate,transport=advance_mb_nonisothermal_transport(states,faces,dt,particle_atol=pa,
        energy_atol_J=ea/2,number_atol_s=nfa,energy_atol_W=efa)
    final=[]
    for cfg,mid,impulse in zip(configurations,intermediate,q):
        endpoint=encode(mid);command=[*cfg.parameters,_decimal(dt),*map(_decimal,impulse)];clock=[_decimal(end)]
        wire=native_mb_scaled_powerlaw_raw(endpoint,command,clock)
        candidate,_=scaled_candidate_from_saved(endpoint,command,clock,wire)
        final.append(MBScaledFiniteVolumeState(candidate,end,candidate.start_clock))
    final=tuple(final)
    report=dict(scope='scaled_same_interval_Lie_split_flat_MB',execution_backend='native',precision_bits=113,
        method='transport_explicit_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='exact_scaled_auxiliary_then_project',dt_s=dt,physical_interval_s=[start,end],
        old_sha256=list(map(_fingerprint,states)),new_sha256=list(map(_fingerprint,final)),configuration_sha256=[c.sha256 for c in configurations],
        transported_states=list(map(asdict,intermediate)),transport=transport,physical_time_advanced=True,
        production_binding_integrated=True,state_commit_integrated=True,repeat_scaled_transport_supported=False,
        monolithic_coupled_BE=False,field_work_included=False,lattice_flux_included=False,complete_device_energy=False,physical_validated=False)
    check=audit_mb_scaled_split_interval(configurations,states,final,report,faces=faces,dt_s=dt,impulses_J=q,
        particle_atol=pa,energy_atol_J=ea,number_atol_s=nfa,energy_atol_W=efa)
    if not check['valid']:raise ValueError('independent scaled whole split audit failed: '+str(check))
    report['independent_audit']=check
    return final,report
