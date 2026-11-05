"""Bounded nonzero a/c MB collision at full affine density, native root."""
from dataclasses import replace
from decimal import Decimal
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal
from tcad.physics.boltzmann_affine_face import encode
from tcad.solver.boltzmann_affine_collision import advance_mb_affine_collision


def advance_mb_affine_powerlaw(config,old,dt_s,*,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    from tcad.core._bindings import native_mb_affine_powerlaw_root_raw
    a=_numbers([dt_s,energy_atol_J],(2,));q=_numbers(impulses_J,(3,))
    if min(a)<=0:raise ValueError('positive powerlaw clock/budget required')
    raw=native_mb_affine_powerlaw_root_raw(encode(old),[*config.parameters,_decimal(a[0]),*map(_decimal,q)])
    count=Decimal(raw[3])
    if count!=count.to_integral_value() or not 1<=count<=256 or len(raw)!=4+4*int(count):raise ValueError('powerlaw root trace coverage')
    p=list(config.parameters);p[2:4]=raw[1:3]
    for j in (6,7,10,11):p[j]='0'
    effective=replace(config,parameters=tuple(p))
    new,inner=advance_mb_affine_collision(effective,old,dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J)
    report=dict(scope='bounded_powerlaw_affine_MB_collision_BE',execution_backend='native',precision_bits=113,
        configuration_sha256=config.sha256,old_sha256=inner['old_sha256'],new_sha256=inner['new_sha256'],
        dt_s=inner['dt_s'],impulses_J=inner['impulses_J'],root_temperature_K=raw[0],effective_tau_s=raw[1:3],
        root_trace=[dict(zip(('temperature_K','tau_n_s','tau_p_s','candidate_lattice_temperature_K'),raw[i:i+4])) for i in range(4,len(raw),4)],
        coefficient_model='binary113_log_head_plus_log1p_low',root_trace_is_diagnostic=True,collision=inner,
        physical_time_advanced=True,expanded_density_collision_supported=True,dynamic_lattice_supported=True,
        nonzero_ac_supported=True,extreme_stiffness_supported=False,same_interval_coupled_integrator_supported=False,
        device_statistics_selected=False,complete_device_energy=False,physical_validated=False)
    from tcad.postprocess.boltzmann_affine_powerlaw import audit_mb_affine_powerlaw
    check=audit_mb_affine_powerlaw(config,old,new,report,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J)
    if not check['valid']:raise ValueError('independent nonlinear affine collision audit failed: '+str(check))
    report['independent_audit']=check;return new,report
