"""Explicit coordinate-only transaction for the bounded closed MB cell."""
from decimal import Decimal
from tcad.solver.boltzmann_relaxation import MBRelaxationState
from tcad.physics.native_boltzmann import _numbers
from tcad.physics.native_fermi_local import _decimal


def rebase_mb_reference(config,old,reference_temperature_K,*,energy_atol_J=1e-27):
    from tcad.core._bindings import native_boltzmann_reference_rebase_raw
    if old.configuration_sha256!=config.sha256:raise ValueError('MB state/configuration mismatch')
    values=_numbers([reference_temperature_K,energy_atol_J],(2,))
    if values[1]<=0:raise ValueError('positive MB rebase energy budget required')
    raw=native_boltzmann_reference_rebase_raw(old.raw_state,config.parameters,config.valleys_n,config.valleys_p,_decimal(values[0]))
    width=len(old.raw_state)+4
    if len(raw)!=width+6:raise ValueError('MB reference rebase output coverage mismatch')
    new=MBRelaxationState(tuple(raw[:width]),old.time_s,config.sha256)
    report=dict(scope='equal_offset_MB_reference_rebase',configuration_sha256=config.sha256,execution_backend='native',
        precision_bits=113,old_temperatures_K=raw[width:width+3],temperatures_K=raw[width+3:],
        reference_temperature_K=new.raw_state[2],physical_time_advanced=False,complete_device_energy=False,
        physical_validated=False,device_statistics_selected=False)
    from tcad.postprocess.boltzmann_rebase import audit_mb_reference_rebase
    audit=audit_mb_reference_rebase(config,old,new,report,reference_temperature_K=reference_temperature_K,energy_atol_J=energy_atol_J)
    if not audit['valid']:raise ValueError('independent MB reference rebase audit failed')
    report['independent_audit']=audit
    return new,report
