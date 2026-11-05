"""Native collision and atomic Lie split for complete scaled MB endpoints."""
from dataclasses import asdict,replace
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState,advance_mb_scaled_transport
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tcad.postprocess.boltzmann_scaled_transport import scaled_value_fraction
from tcad.postprocess.boltzmann_endpoint_powerlaw import split_mb_endpoint_powerlaw,scaled_powerlaw_aggregates
from tcad.postprocess.boltzmann_endpoint_split import configuration,audit_mb_endpoint_collision,audit_mb_endpoint_split


def advance_mb_endpoint_collision(config,old,dt_s,*,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    from tcad.core._endpoint_mb import native_mb_endpoint_powerlaw_raw,native_mb_endpoint_apply_raw
    dt,ea=map(float,_numbers([dt_s,energy_atol_J],(2,)));q=tuple(map(float,_numbers(impulses_J,(3,))))
    if min(dt,ea)<=0 or type(old) is not MBScaledTransportState:raise ValueError('typed complete endpoint and positive collision duration/budget required')
    cfg,digest=configuration(config);command=[*cfg['parameters'],_decimal(dt),*map(_decimal,q)]
    raw=native_mb_endpoint_powerlaw_raw(old.endpoint,command,old.physical_clock)
    # Audit the saved root before invoking the arithmetic state materializer.
    from tcad.postprocess.boltzmann_endpoint_powerlaw import audit_mb_endpoint_powerlaw
    audit_mb_endpoint_powerlaw(old.endpoint,command,old.physical_clock,raw)
    parts=split_mb_endpoint_powerlaw(raw);v=scaled_powerlaw_aggregates(parts['proof'])
    endpoint=native_mb_endpoint_apply_raw(old.endpoint,*[v['aggregate.'+k] for k in ('L','un','up')])
    new=MBScaledTransportState(tuple(endpoint),float(scaled_value_fraction(parts['end'])),tuple(parts['end']))
    report=dict(scope='complete_endpoint_powerlaw_collision',execution_backend='native',precision_bits=113,
        configuration_sha256=digest,old_sha256=_saved_fingerprint(old),new_sha256=_saved_fingerprint(new),dt_s=dt,
        command=command,root_packet=raw,physical_time_advanced=True,complete_device_energy=False,physical_validated=False)
    check=audit_mb_endpoint_collision(config,old,new,report,dt_s=dt,impulses_J=q,energy_atol_J=ea)
    if not check['valid']:raise ValueError('independent complete endpoint collision audit failed')
    report['independent_audit']=check;return new,report


def advance_mb_endpoint_split(configurations,states,faces,dt_s,*,impulses_J=None,
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
        child,report=advance_mb_endpoint_collision(cfg,mid,dt,impulses_J=impulse,energy_atol_J=ea/(2*n))
        auxiliary.append(child);collisions.append(report)
        final.append(replace(child,time_s=mid.time_s,physical_clock=mid.physical_clock))
    final=tuple(final)
    report=dict(scope='complete_endpoint_same_interval_Lie_split',execution_backend='native',precision_bits=113,
        method='full_density_scaled_transport_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='exact_scaled_auxiliary_then_project',dt_s=dt,physical_time_advanced=True,
        physical_interval_clock=[list(states[0].physical_clock),list(middle[0].physical_clock)],
        configuration_sha256=[configuration(c)[1] for c in configurations],old_sha256=list(map(_saved_fingerprint,states)),new_sha256=list(map(_saved_fingerprint,final)),
        transported_states=list(map(asdict,middle)),transport=transport,collision_states=list(map(asdict,auxiliary)),collisions=collisions,
        monolithic_coupled_BE=False,lattice_flux_included=False,field_work_included=False,complete_device_energy=False,physical_validated=False)
    check=audit_mb_endpoint_split(configurations,states,final,report,faces=faces,dt_s=dt,impulses_J=q,
        particle_atol=pa,energy_atol_J=ea,number_atol_s=nfa,energy_atol_W=efa)
    if not check['valid']:raise ValueError('independent complete endpoint full split audit failed')
    report['independent_audit']=check;return final,report
