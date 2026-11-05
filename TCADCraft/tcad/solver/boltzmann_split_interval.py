"""First-order autonomous Lie transport/collision split over one physical interval."""
from dataclasses import asdict,replace
import math
from tcad.physics.native_boltzmann import _numbers
from tcad.solver.boltzmann_frozen_finite_volume import _fingerprint
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport
from tcad.solver.boltzmann_affine_powerlaw import advance_mb_affine_powerlaw


def advance_mb_split_interval(configurations,states,faces,dt_s,*,impulses_J=None,
                              particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    """Apply T(dt) then C(dt), committing t+dt once. Inputs are immutable.

    Existing child APIs use advancing bookkeeping clocks. Their second clock
    is auxiliary: the returned final state changes only that clock to t+dt.
    Both autonomous operators approximate the same physical interval. Explicit
    impulses are per-interval amounts, applied once in collision. Contacts are
    evaluated at the input time. No time-dependent drive or monolithic BE claim.
    """
    states=tuple(states);configurations=tuple(configurations);faces=tuple(faces)
    dt,pa,ea,nfa,efa=map(float,_numbers([dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W],(5,)))
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=len(states)<=256 or len(configurations)!=len(states):
        raise ValueError('one configuration per bounded split cell required')
    start=states[0].time_s;end=start+dt;aux=end+dt
    if not math.isfinite(aux) or not start<end<aux or any(s.time_s!=start for s in states):
        raise ValueError('simultaneous representable physical and auxiliary split clocks required')
    q=tuple((0.,0.,0.) for _ in states) if impulses_J is None else tuple(tuple(_numbers(row,(3,))) for row in impulses_J)
    if len(q)!=len(states):raise ValueError('one explicit impulse triple per split cell required')
    intermediate,transport=advance_mb_nonisothermal_transport(states,faces,dt,particle_atol=pa,
        energy_atol_J=ea/2,number_atol_s=nfa,energy_atol_W=efa)
    final=[];collisions=[]
    for cfg,state,impulse in zip(configurations,intermediate,q):
        result,report=advance_mb_affine_powerlaw(cfg,state,dt,impulses_J=impulse,energy_atol_J=ea/(2*len(states)))
        final.append(replace(result,time_s=end));collisions.append(report)
    report=dict(scope='same_interval_Lie_split_flat_MB',execution_backend='native',precision_bits=113,
        method='transport_explicit_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='auxiliary_bookkeeping',physical_interval_s=[start,end],auxiliary_collision_end_s=aux,
        dt_s=float(dt),old_sha256=list(map(_fingerprint,states)),new_sha256=list(map(_fingerprint,final)),
        configuration_sha256=[c.sha256 for c in configurations],transported_states=[asdict(s) for s in intermediate],
        transport=transport,collisions=collisions,physical_time_advanced=True,same_interval_split_supported=True,
        monolithic_coupled_BE=False,field_work_included=False,lattice_flux_included=False,
        device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_split_interval import audit_mb_split_interval
    check=audit_mb_split_interval(configurations,states,tuple(final),report,faces=faces,dt_s=dt,
        impulses_J=q,particle_atol=pa,energy_atol_J=ea,number_atol_s=nfa,energy_atol_W=efa)
    if not check['valid']:raise ValueError('independent same-interval split audit failed: '+str(check))
    report['independent_audit']=check
    return tuple(final),report
