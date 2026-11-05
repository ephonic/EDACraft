"""Transactional, independently audited BE step doubling for five fields."""
import numpy as np
from .three_temperature import ThreeTemperatureElectrothermal


class AdaptiveStepError(RuntimeError):
    """No trial qualified; the accepted device remains unchanged."""
    def __init__(self,message,attempts):
        super().__init__(message)
        self.attempts=tuple(attempts)


def _scalar(value,name,*,zero=False):
    a=np.asarray(value)
    if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a) or not np.isfinite(float(a)):
        raise ValueError(name+' must be a finite real scalar')
    x=float(a)
    if x<0 or (not zero and x==0):raise ValueError(name+' must be positive' if not zero else name+' must be nonnegative')
    return x


def _field_errors(old,coarse,fine,temperature_atol,temperature_rtol,density_atol,density_rtol):
    errors={}
    for field in ('electron_temperature_K','hole_temperature_K','temperature_K','n_m3','p_m3'):
        start=np.asarray(getattr(old,field),np.longdouble)
        full=np.asarray(getattr(coarse,field),np.longdouble);half=np.asarray(getattr(fine,field),np.longdouble)
        if field in ('n_m3','p_m3'):
            scale=np.longdouble(density_atol)+density_rtol*np.maximum(abs(start),abs(half))
        else:
            # Each carrier and lattice has its own temporal excursion, with no
            # absolute bath-temperature floor that hides a small third signal.
            scale=np.longdouble(temperature_atol)+temperature_rtol*abs(half-start)
        value=float(np.max(abs(half-full)/scale))
        errors[field]=value if np.isfinite(value) else float('inf')
    return errors


def advance_adaptive(device,dt_s,*,temperature_atol_K,temperature_rtol,density_atol_m3,density_rtol,
        minimum_step_s,charge_atol_C,particle_atol,energy_atol_J,max_retries=12,max_nfev=600):
    """Accept two audited half steps atomically, retaining rejected trials.

    The temporal estimator is |half-half - full| for first-order BE. All trials
    run in separate C++ sessions. Failed Newton, independent audit or temporal
    checks can shrink the step, and never advance the caller's accepted state.
    This controls local temporal discretization, not missing model physics.
    """
    from .device_three_temperature import DeviceThreeTemperature
    if not isinstance(device,DeviceThreeTemperature):raise ValueError('native three-temperature device required')
    requested=_scalar(dt_s,'requested interval');minimum=_scalar(minimum_step_s,'minimum interval')
    ta=_scalar(temperature_atol_K,'temperature absolute tolerance');tr=_scalar(temperature_rtol,'temperature relative tolerance',zero=True)
    na=_scalar(density_atol_m3,'density absolute tolerance');nr=_scalar(density_rtol,'density relative tolerance',zero=True)
    budgets={k:_scalar(v,k) for k,v in dict(charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J).items()}
    for value,name,lower in ((max_retries,'retry count',0),(max_nfev,'evaluation budget',1)):
        a=np.asarray(value)
        if a.ndim or a.dtype.kind not in 'iu' or int(a)<lower:raise ValueError('integer '+name+' required')
    if minimum>requested:raise ValueError('minimum interval exceeds requested interval')
    attempts=[];evaluations=0
    with device._lock:
        if device._pack_configuration()!=device._configuration:raise ValueError('device three-temperature configuration is immutable')
        device._check_owned_state();old=device.state
        if not np.isfinite(old.time_s+requested) or old.time_s+requested<=old.time_s:
            raise ValueError('requested physical interval cannot advance the clock')
        # Exclude the adapter backreference/lock; the session constructor takes
        # its own deep model snapshot and a detached copy of the current state.
        model=ThreeTemperatureElectrothermal.__new__(ThreeTemperatureElectrothermal)
        model.__dict__.update({k:v for k,v in device._model.__dict__.items() if k!='_device'})
        proposal=requested
        for attempt in range(int(max_retries)+1):
            target=old.time_s+proposal;actual=target-old.time_s
            if not np.isfinite(target) or actual<minimum*(1-1e-12) or not old.time_s<old.time_s+actual/2<target:
                raise AdaptiveStepError('adaptive interval reached minimum or clock resolution',attempts)
            trial=dict(interval_s=actual,states=[],reports=[],accepted=False)
            attempts.append(trial)
            try:
                coarse=DeviceThreeTemperature(model,old)
                evaluations+=1;full,full_report=coarse.advance(actual,**budgets,max_nfev=int(max_nfev))
                device._decorate_report(full_report)
                trial['states'].append(full);trial['reports'].append(full_report)
                refined=DeviceThreeTemperature(model,old)
                evaluations+=1;middle,r1=refined.advance(actual/2,**budgets,max_nfev=int(max_nfev))
                device._decorate_report(r1)
                trial['states'].append(middle);trial['reports'].append(r1)
                evaluations+=1;new,r2=refined.advance(target-middle.time_s,**budgets,max_nfev=int(max_nfev))
                device._decorate_report(r2)
                trial['states'].append(new);trial['reports'].append(r2)
                assert new.time_s==full.time_s==target
                fields=_field_errors(old,full,new,ta,tr,na,nr)
                if model.trap_capture_law is not None:
                    Nt=model.Nt.astype(np.longdouble)
                    scale=np.longdouble(na)+nr*Nt*np.maximum(abs(old.trap_fraction),abs(new.trap_fraction))
                    fields['occupied_trap_density_m3']=float(np.max(Nt*abs(
                        new.trap_fraction.astype(np.longdouble)-full.trap_fraction)/scale))
                error=max(fields.values())
                trial.update(normalized_error=error,field_errors=fields)
            except (ValueError,RuntimeError) as exc:
                trial.update(failure_type=type(exc).__name__,failure=str(exc))
                proposal=actual*.5
                continue
            if error<=1:
                trial['accepted']=True
                factor=2. if error==0 else float(np.clip(.85/np.sqrt(error),.2,2.))
                result=dict(valid=True,scope='adaptive_FD_three_temperature_local_error_control',
                    requested_interval_s=requested,accepted_interval_s=actual,
                    suggested_next_step_s=actual*factor,normalized_temporal_error=error,
                    temporal_error_by_field=fields,rejected_trials=len(attempts)-1,
                    native_advance_calls=evaluations,accepted_native_substeps=2,
                    substep_states=(middle,new),substep_reports=(r1,r2),attempts=tuple(attempts),
                    initial_state=old,independent_substep_audits_passed=True,
                    modeled_device_energy_closed=True,complete_device_energy=False,physical_validated=False,
                    experimental_validated=False,global_temporal_error_bound=False,
                    device_state_owner='C++ DeviceSimulator',device_mesh_mode=r2['device_mesh_mode'],
                    device_transaction='independently_audited_trial_session_adoption',
                    temperature_relative_scale='each field own temporal change')
                returned=(new,result)
                refined._check_owned_state()
                if device._pack_configuration()!=device._configuration:raise ValueError('device configuration changed during adaptive trial')
                # All simulations, audits and report allocations completed. The
                # accepted session/state are published together under the lock.
                device._backend,device._state=refined._backend,new
                return returned
            proposal=actual*float(np.clip(.85/np.sqrt(error),.2,.8))
        raise AdaptiveStepError('adaptive retry limit exhausted',attempts)
