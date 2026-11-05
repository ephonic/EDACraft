"""Native collision and atomic Lie split for complete scaled MB endpoints."""
from dataclasses import asdict,replace
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_recomputed_transport import advance_mb_scaled_transport
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tcad.postprocess.boltzmann_scaled_transport import scaled_value_fraction
from tcad.postprocess.boltzmann_weak_endpoint_powerlaw import split_mb_weak_endpoint_powerlaw,scaled_powerlaw_aggregates
from tcad.postprocess.boltzmann_weak_endpoint_collision import configuration,audit_mb_weak_endpoint_collision


def advance_mb_weak_endpoint_collision(config,old,dt_s,*,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    from tcad.core._weak_collision_mb import native_mb_weak_endpoint_powerlaw_raw,native_mb_recomputed_endpoint_apply_raw
    dt,ea=map(float,_numbers([dt_s,energy_atol_J],(2,)));q=tuple(map(float,_numbers(impulses_J,(3,))))
    if min(dt,ea)<=0 or type(old) is not MBScaledTransportState:raise ValueError('typed complete endpoint and positive collision duration/budget required')
    cfg,digest=configuration(config);command=[*cfg['parameters'],_decimal(dt),*map(_decimal,q)]
    raw=native_mb_weak_endpoint_powerlaw_raw(old.endpoint,command,old.physical_clock)
    # Audit the saved root before invoking the arithmetic state materializer.
    from tcad.postprocess.boltzmann_weak_endpoint_powerlaw import audit_mb_weak_endpoint_powerlaw
    audit_mb_weak_endpoint_powerlaw(old.endpoint,command,old.physical_clock,raw)
    parts=split_mb_weak_endpoint_powerlaw(raw);v=scaled_powerlaw_aggregates(parts['proof'])
    endpoint=native_mb_recomputed_endpoint_apply_raw(old.endpoint,*[v['aggregate.'+k] for k in ('L','un','up')])
    new=MBScaledTransportState(tuple(endpoint),float(scaled_value_fraction(parts['end'])),tuple(parts['end']))
    report=dict(scope='weak_complete_endpoint_powerlaw_collision',execution_backend='native',precision_bits=113,
        configuration_sha256=digest,old_sha256=_saved_fingerprint(old),new_sha256=_saved_fingerprint(new),dt_s=dt,
        command=command,root_packet=raw,physical_time_advanced=True,complete_device_energy=False,physical_validated=False)
    check=audit_mb_weak_endpoint_collision(config,old,new,report,dt_s=dt,impulses_J=q,energy_atol_J=ea)
    if not check['valid']:raise ValueError('independent complete endpoint collision audit failed')
    report['independent_audit']=check;return new,report

