"""Whole-trajectory transactions for the independently audited native solver."""
import numpy as np
from .adaptive_three_temperature import _scalar
from .three_temperature import ThreeTemperatureElectrothermal


class ThreeTemperatureTransientError(RuntimeError):
    """An isolated trajectory failed; no trajectory state was published.

    ``diagnostics`` retains completed intervals, failed adaptive trials, the
    failure phase and any completed cumulative ledger. Their states are
    diagnostic candidates, never caller-accepted history.
    """
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def run_transient(device, output_times_s, *, initial_step_s, maximum_step_s,
                  minimum_step_s, temperature_atol_K, temperature_rtol,
                  density_atol_m3, density_rtol, charge_atol_C, particle_atol,
                  energy_atol_J, cumulative_energy_atol_J=None, cumulative_particle_atol=None,
                  cumulative_charge_atol_C=None,
                  max_intervals=10000, max_retries=12, max_nfev=600):
    """Integrate to exact requested clocks and publish the final session once.

    Times are strictly increasing float64 absolute clocks, optionally starting
    at the current clock. No interpolation, epsilon skipping, or relaxation of
    the minimum interval is used. Subminimum/unresolvable output spacing fails
    the entire transaction. All accepted intervals and adaptive trials remain
    in the result, including the discarded full-step solutions.

    ``cumulative_energy_atol_J``, ``cumulative_particle_atol`` and
    ``cumulative_charge_atol_C`` optionally set
    separate positive finite whole-path conservation budgets, independently
    of the unchanged per-substep budgets.
    None retains the sum of accepted substep budgets (one for an empty path).
    The final independent audit must pass before publication. This gate does
    not request automatic refinement or bound the global temporal error.
    """
    from .device_three_temperature import DeviceThreeTemperature
    if not isinstance(device, DeviceThreeTemperature):
        raise ValueError('native three-temperature device required')
    times = np.asarray(output_times_s)
    if times.ndim != 1 or not times.size or times.dtype.kind not in 'fiu':
        raise ValueError('nonempty one-dimensional real output times required')
    times = np.array(times, dtype=float, copy=True)
    if np.any(~np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError('finite strictly increasing output clocks required')
    # Detached, bytes-backed storage cannot be changed during report hooks.
    times = np.frombuffer(times.tobytes(), dtype=float)
    first = _scalar(initial_step_s, 'initial interval')
    maximum = _scalar(maximum_step_s, 'maximum interval')
    minimum = _scalar(minimum_step_s, 'minimum interval')
    if not minimum <= first <= maximum:
        raise ValueError('minimum <= initial <= maximum interval required')
    options = dict(minimum_step_s=minimum,
        temperature_atol_K=_scalar(temperature_atol_K, 'temperature absolute tolerance'),
        temperature_rtol=_scalar(temperature_rtol, 'temperature relative tolerance', zero=True),
        density_atol_m3=_scalar(density_atol_m3, 'density absolute tolerance'),
        density_rtol=_scalar(density_rtol, 'density relative tolerance', zero=True),
        charge_atol_C=_scalar(charge_atol_C, 'charge budget'),
        particle_atol=_scalar(particle_atol, 'particle budget'),
        energy_atol_J=_scalar(energy_atol_J, 'energy budget'))
    for value, name, lower in ((max_intervals, 'interval limit', 1),
                              (max_retries, 'retry count', 0),
                              (max_nfev, 'evaluation budget', 1)):
        a = np.asarray(value)
        if a.ndim or a.dtype.kind not in 'iu' or int(a) < lower:
            raise ValueError('integer ' + name + ' required')
    options.update(max_retries=int(max_retries), max_nfev=int(max_nfev))
    cumulative = (None if cumulative_energy_atol_J is None else
                  _scalar(cumulative_energy_atol_J, 'cumulative energy budget'))
    cumulative_particle = (None if cumulative_particle_atol is None else
                           _scalar(cumulative_particle_atol, 'cumulative particle budget'))
    cumulative_charge = (None if cumulative_charge_atol_C is None else
                         _scalar(cumulative_charge_atol_C, 'cumulative charge budget'))
    with device._lock:
        if device._pack_configuration() != device._configuration:
            raise ValueError('device three-temperature configuration is immutable')
        device._check_owned_state()
        old = device.state
        if times[0] < old.time_s:
            raise ValueError('output clocks precede the accepted state')
        # Material snapshot excludes the native backreference and its lock.
        model = ThreeTemperatureElectrothermal.__new__(ThreeTemperatureElectrothermal)
        model.__dict__.update({k: v for k, v in device._model.__dict__.items() if k != '_device'})
        worker = DeviceThreeTemperature(model, old)
        worker._decorate_report = device._decorate_report
        outputs, intervals = [], []
        proposal = first
        ledger = None
        phase = 'integration'
        try:
            for target in times:
                target = float(target)
                while worker.state.time_s < target:
                    if len(intervals) >= int(max_intervals):
                        raise RuntimeError('trajectory interval limit exhausted')
                    remaining = target - worker.state.time_s
                    step = min(proposal, maximum, remaining)
                    # Do not strand a remainder below the prescribed minimum.
                    # Any enlarged proposal must still pass adaptive checks.
                    if 0 < target - (worker.state.time_s + step) < minimum:
                        if remaining <= maximum:
                            step = remaining
                        else:
                            endpoint = target - minimum
                            # Subtraction can round toward target, leaving a
                            # representable remainder strictly below minimum.
                            if target - endpoint < minimum:
                                endpoint = float(np.nextafter(endpoint, -np.inf))
                            step = endpoint - worker.state.time_s
                    if step < minimum:
                        raise RuntimeError('output spacing is below the minimum interval')
                    state, report = worker.advance_adaptive(step, **options)
                    if not old.time_s < state.time_s <= target:
                        raise RuntimeError('adaptive clock crossed a requested output')
                    intervals.append(report)
                    proposal = min(maximum, max(minimum, report['suggested_next_step_s']))
                if worker.state.time_s != target:
                    raise RuntimeError('requested output clock was not reached exactly')
                outputs.append(worker.state)
            from tcad.postprocess.three_temperature_trajectory import audit_three_temperature_trajectory
            phase = 'cumulative_energy_audit'
            ledger = audit_three_temperature_trajectory(worker._model, old, intervals,
                final_state=worker.state, charge_atol_C=options['charge_atol_C'],
                particle_atol=options['particle_atol'], energy_atol_J=options['energy_atol_J'],
                cumulative_energy_atol_J=cumulative, cumulative_particle_atol=cumulative_particle,
                cumulative_charge_atol_C=cumulative_charge)
            if not ledger['valid']:
                raise ValueError('independent cumulative trajectory conservation audit failed')
            phase = 'prepublication_checks'
            worker._check_owned_state()
            if device._pack_configuration() != device._configuration or device.state is not old:
                raise ValueError('caller configuration or state changed during trajectory')
            device._check_owned_state()
            phase = 'result_construction'
            result = dict(valid=True, scope='atomic_native_three_temperature_trajectory',
                initial_state=old, final_state=worker.state, output_times_s=times,
                output_states=tuple(outputs), interval_reports=tuple(intervals),
                accepted_intervals=len(intervals), accepted_native_substeps=2*len(intervals),
                native_advance_calls=sum(r['native_advance_calls'] for r in intervals),
                rejected_trials=sum(r['rejected_trials'] for r in intervals),
                exact_output_clocks=True, whole_trajectory_atomic=True,
                independent_substep_audits_passed=True, modeled_device_energy_closed=True,
                trajectory_energy_audit=ledger,
                complete_device_energy=False, physical_validated=False,
                experimental_validated=False, global_temporal_error_bound=False,
                legacy_run_three_temperature_replaced=False,
                device_state_owner='C++ DeviceSimulator')
        except Exception as exc:
            diagnostic = dict(initial_state=old, output_states=tuple(outputs),
                interval_reports=tuple(intervals), failed_output_time_s=target,
                failed_interval_attempts=getattr(exc, 'attempts', ()),
                failure_type=type(exc).__name__, failure=str(exc),
                failure_phase=phase, trajectory_energy_audit=ledger,
                completed_interval_native_calls=sum(r['native_advance_calls'] for r in intervals),
                published=False)
            raise ThreeTemperatureTransientError('three-temperature trajectory was not committed: ' + str(exc), diagnostic) from exc
        # Everything that can fail or allocate has completed before publication.
        device._backend, device._state = worker._backend, worker.state
        return result
