"""Explicit reset/program/read voltage waveforms, without memory-capacity claims."""
import math

import numpy as np

from tcad.postprocess.terminal_trace import _real_array, _real_scalar


def ferroelectric_program_read_protocol(program_voltages_V, *, reset_voltage_V,
        ramp_s, reset_hold_s, program_hold_s, read_hold_s, read_voltage_V=0.):
    """Build continuous pulses with a measured baseline after every reset.

    Each candidate gets reset/ramp/hold, baseline read, program/ramp/hold,
    and final read. All four ramps take ramp_s; both reads take read_hold_s.
    Voltages use the caller's declared drive convention. For a film with the
    bottom at zero, positive drive may require top=-drive; no axis is inferred.
    A reset pulse is an input, not proof of erasure. Candidate count is not
    measured state count, and no material or retention validation is implied.
    """
    candidates = _real_array(program_voltages_V, 'program_voltages_V')
    if candidates.ndim != 1 or not candidates.size:
        raise ValueError('program_voltages_V must be a nonempty one-dimensional sequence')
    reset = _real_scalar(reset_voltage_V, 'reset_voltage_V')
    read = _real_scalar(read_voltage_V, 'read_voltage_V')
    ramp, reset_hold, program_hold, read_hold = (
        _real_scalar(value, name, positive=True) for name, value in (
            ('ramp_s', ramp_s), ('reset_hold_s', reset_hold_s),
            ('program_hold_s', program_hold_s), ('read_hold_s', read_hold_s)))
    times, voltages, durations, events = [0.], [read], [], []

    def append(duration, voltage):
        durations.append(duration)
        try:
            end = math.fsum(durations)
        except OverflowError as exc:
            raise ValueError('protocol clock exceeds float64 range') from exc
        if not math.isfinite(end) or end <= times[-1]:
            raise ValueError('protocol interval is not representable on the float64 clock')
        times.append(end)
        voltages.append(float(voltage))

    for index, program in enumerate(candidates):
        append(ramp, reset)
        append(reset_hold, reset)
        append(ramp, read)
        append(read_hold, read)
        baseline_time = times[-1]
        append(ramp, program)
        append(program_hold, program)
        append(ramp, read)
        append(read_hold, read)
        events.append(dict(candidate_index=index, program_voltage_V=float(program),
                           baseline_read_time_s=baseline_time, program_read_time_s=times[-1]))
    return dict(times_s=times, drive_voltage_V=voltages, read_events=events,
        candidate_count=len(events), reset_voltage_V=reset, read_voltage_V=read,
        reset_effect_validated=False, measured_state_count=None, physical_validated=False)
