"""Audited BE step doubling of thermal views and authoritative signed energy."""
from decimal import Decimal,localcontext
import numpy as np
from .adaptive_three_temperature import AdaptiveStepError,_scalar,_field_errors

SCOPE='adaptive_fixed_band_energy_coordinate_local_error_control'


def _energy_errors(old,coarse,fine,absolute,relative):
    """Decimal differences retain sub-temperature-resolution carrier signals."""
    errors={}
    with localcontext() as context:
        context.prec=90
        atol=Decimal(str(absolute));rtol=Decimal(str(relative))
        for s,name in enumerate(('excess_n_J_m3','excess_p_J_m3')):
            values=[]
            for a,b,c in zip(old.excess_J_m3[s::2],coarse.excess_J_m3[s::2],fine.excess_J_m3[s::2]):
                start,full,half=map(Decimal,(a,b,c))
                values.append(abs(half-full)/(atol+rtol*abs(half-start)))
            errors[name]=float(max(values))
    return errors


def _integer(value,name,lower):
    a=np.asarray(value)
    if a.ndim or a.dtype.kind not in 'iu' or int(a)<lower:raise ValueError('integer '+name+' required')
    return int(a)


def advance_adaptive(device,dt_s,*,temperature_atol_K,temperature_rtol,density_atol_m3,density_rtol,
        excess_atol_J_m3,excess_rtol,minimum_step_s,charge_atol_C,particle_atol,energy_atol_J,
        max_retries=12,max_nfev=600):
    """Publish two audited half steps only after all seven field checks pass.

    Each carrier energy uses its own temporal change for relative scaling.
    max_nfev remains the shared seed/Newton limit per native advance; at most
    3*(max_retries+1) native advances are attempted. Retried/coarse candidates
    are diagnostic history and never contribute to accepted-path energy.
    No global temporal accuracy or missing-physics qualification is implied.
    """
    from .device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
    if type(device) is not Device:raise ValueError('native energy-coordinate device required')
    requested=_scalar(dt_s,'requested interval');minimum=_scalar(minimum_step_s,'minimum interval')
    ta=_scalar(temperature_atol_K,'temperature absolute tolerance');tr=_scalar(temperature_rtol,'temperature relative tolerance',zero=True)
    na=_scalar(density_atol_m3,'density absolute tolerance');nr=_scalar(density_rtol,'density relative tolerance',zero=True)
    ea=_scalar(excess_atol_J_m3,'excess energy absolute tolerance');er=_scalar(excess_rtol,'excess energy relative tolerance',zero=True)
    budgets={k:_scalar(v,k) for k,v in dict(charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J).items()}
    retries=_integer(max_retries,'retry count',0);budget=_integer(max_nfev,'evaluation budget',1)
    if minimum>requested:raise ValueError('minimum interval exceeds requested interval')
    attempts=[];calls=0
    with device._lock:
        device._check_configuration();device._check_owned_state();old=device.state;t0=old.thermal.time_s
        if not np.isfinite(t0+requested) or t0+requested<=t0:raise ValueError('requested interval cannot advance physical clock')
        proposal=requested
        for _ in range(retries+1):
            target=t0+proposal;actual=target-t0;midpoint=t0+actual/2
            if actual<minimum or not t0<midpoint<target:
                raise AdaptiveStepError('adaptive interval reached minimum or clock resolution',attempts)
            trial=dict(interval_s=actual,states=[],reports=[],accepted=False,native_advance_calls=0)
            attempts.append(trial)
            try:
                coarse=Device(device._model,old)
                calls+=1;trial['native_advance_calls']+=1
                full,r0=coarse.advance(actual,**budgets,max_nfev=budget)
                trial['states'].append(full);trial['reports'].append(r0)
                refined=Device(device._model,old)
                calls+=1;trial['native_advance_calls']+=1
                middle,r1=refined.advance(midpoint-t0,**budgets,max_nfev=budget)
                trial['states'].append(middle);trial['reports'].append(r1)
                calls+=1;trial['native_advance_calls']+=1
                new,r2=refined.advance(target-middle.thermal.time_s,**budgets,max_nfev=budget)
                trial['states'].append(new);trial['reports'].append(r2)
                if new.thermal.time_s!=target or full.thermal.time_s!=target:raise ValueError('trial clock mismatch')
                fields=_field_errors(old.thermal,full.thermal,new.thermal,ta,tr,na,nr)
                fields.update(_energy_errors(old,full,new,ea,er));error=max(fields.values())
                trial.update(normalized_error=error,field_errors=fields)
            except (ValueError,RuntimeError) as exc:
                trial.update(failure_type=type(exc).__name__,failure=str(exc));proposal=actual*.5
                continue
            if error<=1:
                trial['accepted']=True
                factor=2. if error==0 else float(np.clip(.85/np.sqrt(error),.2,2.))
                report=dict(valid=True,scope=SCOPE,initial_state=old,requested_interval_s=requested,
                    accepted_interval_s=actual,suggested_next_step_s=actual*factor,
                    normalized_temporal_error=error,temporal_error_by_field=fields,
                    rejected_trials=len(attempts)-1,native_advance_calls=calls,
                    accepted_native_substeps=2,substep_states=(middle,new),substep_reports=(r1,r2),attempts=tuple(attempts),
                    shared_max_nfev_per_advance=budget,maximum_native_advance_calls=3*(retries+1),
                    temperature_relative_scale='each field own temporal change',
                    excess_relative_scale='each carrier own signed-energy temporal change',
                    independent_substep_audits_passed=True,modeled_fixed_band_energy_closed=True,
                    complete_device_energy=False,physical_validated=False,experimental_validated=False,
                    global_temporal_error_bound=False,native_device_session_integrated=True,
                    device_state_owner='C++ DeviceSimulator',device_mesh_mode='explicit_cells',
                    device_transaction='independently_audited_trial_session_adoption')
                returned=device._publication(new,report)
                refined._check_owned_state();device._check_configuration();device._check_owned_state()
                if device.state is not old:raise ValueError('caller state changed during adaptive trial')
                device._backend,device._state=refined._backend,new
                return returned
            proposal=actual*float(np.clip(.85/np.sqrt(error),.2,.8))
        raise AdaptiveStepError('adaptive retry limit exhausted',attempts)
