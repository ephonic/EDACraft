"""Signed charge and source-work integration of explicit SI terminal traces."""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
import math
import sys

import numpy as np


def _real_array(value, name):
    array = np.asarray(value)
    if array.dtype.kind not in "iuf":
        raise ValueError(f"{name} requires real numeric values")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} requires finite values")
    converted = array.astype(float, copy=False)
    if np.any((array != 0) & (converted == 0)) or not np.all(np.isfinite(converted)):
        raise ValueError(f"{name} cannot be represented as finite float64")
    return converted


def _real_scalar(value, name, *, positive=False):
    array = np.asarray(value)
    if (array.shape != () or array.dtype.kind not in "iuf"
            or not np.all(np.isfinite(array))):
        raise ValueError(f"{name} must be a finite real scalar")
    converted = float(array)
    if not np.isfinite(converted) or (positive and converted <= 0):
        bound = "finite and positive" if positive else "finite"
        raise ValueError(f"{name} must be {bound}")
    return converted


def _validated_trace(trace):
    if not isinstance(trace, Mapping):
        raise ValueError("terminal trace must be a mapping")
    times = _real_array(trace.get("times_s", []), "times_s")
    if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)):
        raise ValueError("times_s requires at least two finite samples")
    with np.errstate(over="ignore", invalid="ignore"):
        durations = np.diff(times)
        span = times[-1] - times[0]
    if (not np.all(np.isfinite(durations)) or np.any(durations <= 0)
            or not np.isfinite(span) or span <= 0):
        raise ValueError("trace times must be strictly increasing with finite duration")
    status_found = False
    for name in ("valid", "converged"):
        if name in trace:
            status_found = True
            status = np.asarray(trace[name])
            if (status.dtype.kind != "b" or status.shape not in ((), times.shape)
                    or not np.all(status)):
                raise ValueError(f"trace {name} must be True for every sample")
    if not status_found:
        raise ValueError("terminal trace requires explicit valid/converged status")
    currents, voltages = trace.get("terminal_currents_A"), trace.get("terminal_voltages_V")
    if (not isinstance(currents, Mapping) or not isinstance(voltages, Mapping)
            or len(currents) < 2 or set(currents) != set(voltages)
            or not all(isinstance(name, str) and name for name in currents)):
        raise ValueError("trace requires matching named current/voltage maps for at least two terminals")
    def fields(values, label):
        arrays = {name: _real_array(value, label) for name, value in values.items()}
        if any(value.shape != times.shape or not np.all(np.isfinite(value))
               for value in arrays.values()):
            raise ValueError(f"{label} requires one finite SI value per time and terminal")
        return arrays
    return times, durations, fields(currents, "terminal_currents_A"), fields(voltages, "terminal_voltages_V")


def _fraction_float(value):
    """Round a complete exact quantity once, rejecting lost nonzero output."""
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("terminal integral cannot be represented as finite float64") from exc
    if not math.isfinite(result) or (value != 0 and result == 0.):
        raise ValueError("terminal integral cannot be represented as finite nonzero float64")
    return result


def _finite_sum(values):
    values = tuple(values)  # Retain generators if fsum overflows before cancellation.
    if any(isinstance(value, Fraction) for value in values):
        return _fraction_float(sum((Fraction(value) for value in values), Fraction(0)))
    try:
        result = math.fsum(values)
    except OverflowError:
        if not all(math.isfinite(value) for value in values):
            raise ValueError("terminal integral overflowed")
        return _fraction_float(sum((Fraction(float(value)) for value in values), Fraction(0)))
    except ValueError as exc:
        raise ValueError("terminal integral overflowed") from exc
    if not math.isfinite(result):
        raise ValueError("terminal integral overflowed")
    return result


def _exact_source_work(v0, v1, i0, i1, duration):
    """Rare range fallback: retain exact signed pieces until final summation."""
    v0, v1, i0, i1, duration = map(Fraction, (v0, v1, i0, i1, duration))
    cuts = {Fraction(0), Fraction(1)}
    for first, last in ((v0, v1), (i0, i1)):
        if first*last < 0:
            cuts.add(-first/(last-first))
    cuts = sorted(cuts)
    a = v0*i0
    b = v0*(i1-i0) + i0*(v1-v0)
    c = (v1-v0)*(i1-i0)
    def primitive(u):
        return a*u + b*u*u/2 + c*u*u*u/3
    return [duration*(primitive(right)-primitive(left))
            for left, right in zip(cuts[:-1], cuts[1:])]


def _source_work(v0, v1, i0, i1, duration):
    """Exact integral of two linear interpolants, split at power sign changes."""
    if (v0 == v1 == 0.) or (i0 == i1 == 0.):
        return [0.]
    def exact():
        return _exact_source_work(v0, v1, i0, i1, duration)
    if any(0. < abs(value) < 2*sys.float_info.min for value in (v0, v1, i0, i1)):
        return exact()
    cuts = [0., 1.]
    for first, last in ((v0, v1), (i0, i1)):
        if first != 0 and last != 0 and np.signbit(first) != np.signbit(last):
            scale = max(abs(first), abs(last))
            cut = (abs(first)/scale)/(abs(first)/scale + abs(last)/scale)
            if not 0. < cut < 1.:
                return exact()
            cuts.append(cut)
    cuts = sorted(set(cuts))
    works = []
    for left, right in zip(cuts[:-1], cuts[1:]):
        # Two-point Gauss quadrature is exact for the quadratic V(t)*I(t).
        middle, half = (left+right)/2, (right-left)/2
        u0, u1 = middle-half/math.sqrt(3), middle+half/math.sqrt(3)
        if not left < u0 < u1 < right:
            return exact()
        va, vb = (1-u0)*v0+u0*v1, (1-u1)*v0+u1*v1
        ia, ib = (1-u0)*i0+u0*i1, (1-u1)*i0+u1*i1
        if va == 0. or vb == 0. or ia == 0. or ib == 0.:
            return exact()
        p0, p1 = va*ia, vb*ib
        if any(not math.isfinite(p) or abs(p) < sys.float_info.min for p in (p0, p1)):
            return exact()
        power = p0+p1
        interval_weight = duration*half
        if abs(interval_weight) < sys.float_info.min:
            return exact()
        work = interval_weight*power
        if (not math.isfinite(power) or not math.isfinite(work)
                or (power != 0. and abs(work) < sys.float_info.min)
                or np.signbit(p0) != np.signbit(p1)):
            return exact()
        works.append(work)
    return works


def integrate_terminal_trace(trace, *, current_kind):
    """Integrate current [A] and signed V*I work [J] over a terminal trace.

    Current is positive into the device. Declare ``current_kind='total'`` or
    ``'conduction'``; the latter omits displacement contributions. Samples
    define piecewise linear current and voltage, whose product is integrated
    exactly. Duplicate times and unresolved impulse charge are unsupported;
    this function cannot recover switching transients absent from the input.
    Source work is not dissipated energy or proof of a device energy balance.
    """
    if not isinstance(current_kind, str) or current_kind not in ("total", "conduction"):
        raise ValueError("current_kind must be 'total' or 'conduction'")
    times, durations, currents, voltages = _validated_trace(trace)
    charges, supplied, absorbed, returned = {}, {}, {}, {}
    for name, current in currents.items():
        voltage = voltages[name]
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            average = .5*current[:-1] + .5*current[1:]
            fast = durations*average
            small = (current != 0.) & (np.abs(current) < 2*sys.float_info.min)
            exact_charge = (~np.isfinite(fast) | small[:-1] | small[1:]
                            | ((average != 0.) & (np.abs(fast) < sys.float_info.min)))
        increments = list(fast)
        for index in np.flatnonzero(exact_charge):
            increments[index] = (Fraction(float(durations[index]))*
                (Fraction(float(current[index]))+Fraction(float(current[index+1])))/2)
        charges[name] = _finite_sum(increments)
        works = []
        for v0, v1, i0, i1, dt in zip(voltage[:-1], voltage[1:],
                                      current[:-1], current[1:], durations):
            works.extend(_source_work(float(v0), float(v1), float(i0), float(i1), float(dt)))
        supplied[name] = _finite_sum(works)
        absorbed[name] = _finite_sum(max(work, 0.) for work in works)
        returned[name] = _finite_sum(max(-work, 0.) for work in works)
    return _integral_report(charges, supplied, absorbed, returned,
                            float(times[-1]-times[0]), times.size, current_kind,
                            "piecewise_linear_voltage_and_current")


def _integral_report(charges, supplied, absorbed, returned, duration,
                     sample_count, current_kind, integration_kind):
    net_work = _finite_sum(supplied.values())
    power = net_work/duration
    if not np.isfinite(power) or (net_work != 0. and power == 0.):
        raise ValueError("mean terminal source power cannot be represented as finite nonzero float64")
    return {
        "terminal_charge_C": charges,
        "terminal_supplied_energy_J": supplied,
        "terminal_absorbed_energy_J": absorbed,
        "terminal_returned_energy_J": returned,
        "net_terminal_charge_C": _finite_sum(charges.values()),
        "supplied_energy_J": net_work,
        "absorbed_energy_J": _finite_sum(absorbed.values()),
        "returned_energy_J": _finite_sum(returned.values()),
        "mean_source_power_W": power,
        "duration_s": duration,
        "sample_count": sample_count,
        "current_kind": current_kind,
        "integration_kind": integration_kind,
        "valid": True,
        "charge_balance_validated": False,
        "energy_balance_validated": False,
        "physical_validated": False,
    }


def _scaled_product(numerators, denominators=()):
    """Multiply/divide SI factors without losing a representable final value."""
    mantissa, exponent = 1., 0
    for value in numerators:
        if value == 0.: return 0.
        part, power = math.frexp(value)
        mantissa *= part
        exponent += power
    for value in denominators:
        part, power = math.frexp(value)
        mantissa /= part
        exponent -= power
    try:
        result = math.ldexp(mantissa, exponent)
    except OverflowError as exc:
        raise ValueError("terminal integral cannot be represented as finite float64") from exc
    if not math.isfinite(result) or result == 0.:
        raise ValueError("terminal integral cannot be represented as finite nonzero float64")
    return result


def _be_source_work(v0, v1, charge, voltage_quadrature):
    """Work of a constant BE interval current, with explicit voltage shape."""
    if not math.isfinite(charge):
        raise ValueError("terminal charge integral overflowed")
    if voltage_quadrature == "endpoint":
        works = [_scaled_product((charge, v1))]
    else:
        scale = max(abs(v0), abs(v1))
        if v0 != 0. and v1 != 0. and np.signbit(v0) != np.signbit(v1):
            denominator = abs(v0)/scale + abs(v1)/scale
            # Signed triangles on either side of the voltage zero. Keep the
            # small endpoint squared in factors instead of rounding its
            # crossing-time fraction before multiplying by a large charge.
            works = [_scaled_product((.5, charge, value, abs(value)), (scale, denominator))
                     for value in (v0, v1)]
        elif scale:
            # Averaging subnormal voltages first can round to zero even when
            # the resulting work is representable after multiplication by Q.
            works = [_scaled_product((charge, scale, .5*(v0/scale + v1/scale)))]
        else:
            works = [0.]
    if not all(math.isfinite(work) for work in works):
        raise ValueError("terminal source work overflowed")
    return works


def integrate_transient_terminal_history(history, *, current_kind="total",
                                       voltage_quadrature="endpoint"):
    """Integrate native accepted BE intervals in C and signed source work in J.

    Native total current includes dielectric and FE polarization displacement.
    Current is held constant over its accepted BE interval. The default
    voltage_quadrature='endpoint' preserves the BE source-work convention.
    Choose 'linear' for continuous linear voltage between endpoints, splitting
    absorbed/returned work at internal voltage zero crossings. This is exact
    for linear lossless capacitors; nonlinear transport/FE still needs temporal
    convergence and does not gain a thermodynamic balance from this option.
    The t=0 state has no current interval. Reject failed/incomplete histories
    and unavailable electrode scope. This covers the returned interval only,
    not voltage jumps between separate runs, unresolved impulse charge, full
    energy balance or dissipated energy. Choose total, conduction, displacement,
    dielectric, or polarization for the corresponding native current component.
    Component source work does not establish a separate thermodynamic balance.
    """
    if not isinstance(current_kind, str) or current_kind not in (
            "total", "conduction", "displacement", "dielectric", "polarization"):
        raise ValueError("current_kind must name a native terminal current component")
    if not isinstance(voltage_quadrature, str) or voltage_quadrature not in ("endpoint", "linear"):
        raise ValueError("voltage_quadrature must be 'endpoint' or 'linear'")
    if not isinstance(history, (list, tuple)) or len(history) < 2:
        raise ValueError("transient history requires an initial state and accepted intervals")

    def flag(state, key):
        value = state.get(key)
        return isinstance(value, (bool, np.bool_)) and bool(value)

    names = None
    charges, supplied, absorbed, returned = {}, {}, {}, {}
    first_time = previous_time = previous_voltage = None
    for index, state in enumerate(history):
        if not isinstance(state, Mapping) or not flag(state, "valid") or not flag(state, "converged"):
            raise ValueError("transient history requires valid/converged states")
        if not flag(state, "electrode_charge_available"):
            raise ValueError("transient electrode scope is unavailable")
        labels = state.get("electrode_names")
        if (not isinstance(labels, (list, tuple)) or len(labels) < 2
                or any(not isinstance(name, str) or not name for name in labels)
                or len(set(labels)) != len(labels)):
            raise ValueError("transient electrodes require distinct names")
        if names is None:
            names = tuple(labels)
            for result in (charges, supplied, absorbed, returned):
                result.update({name: [] for name in names})
        if tuple(labels) != names:
            raise ValueError("transient electrode names/order must match across states")
        time = _real_scalar(state.get("time_s"), "time_s")
        dt = _real_scalar(state.get("dt_s"), "dt_s")
        voltage = _real_array(state.get("electrode_voltages_V"), "electrode_voltages_V")
        if voltage.shape != (len(names),):
            raise ValueError("transient voltage requires one value per electrode")
        if index == 0:
            if dt != 0 or time != 0 or not flag(state, "initial_state"):
                raise ValueError("transient history must start with its zero-time initial state")
            first_time = previous_time = time
            previous_voltage = voltage
            continue
        duration = time - previous_time
        if (not isinstance(state.get("initial_state"), (bool, np.bool_))
                or state["initial_state"]):
            raise ValueError("transient endpoints must not be initial states")
        if (not np.isfinite(duration) or duration <= 0 or dt <= 0
                or not np.isclose(dt, duration, rtol=1e-10, atol=0.)):
            raise ValueError("transient accepted dt must match strictly increasing times")
        if not flag(state, "total_terminal_current_available"):
            raise ValueError("transient terminal current scope is unavailable")
        current = _real_array(state.get("electrode_" + current_kind + "_currents_A"),
                              "electrode currents")
        if current.shape != voltage.shape:
            raise ValueError("transient current requires one value per electrode")
        for name, v0, v, i in zip(names, previous_voltage, voltage, current):
            charge = _scaled_product((dt, float(i)))
            works = _be_source_work(float(v0), float(v), charge, voltage_quadrature)
            charges[name].append(charge)
            supplied[name].extend(works)
            absorbed[name].extend(max(work, 0.) for work in works)
            returned[name].extend(max(-work, 0.) for work in works)
        previous_time = time
        previous_voltage = voltage
    for result in (charges, supplied, absorbed, returned):
        for name, increments in result.items():
            result[name] = _finite_sum(increments)
    result = _integral_report(charges, supplied, absorbed, returned,
                             previous_time - first_time, len(history), current_kind,
                             "backward_euler_endpoint_voltage_and_current" if voltage_quadrature == "endpoint"
                             else "linear_voltage_with_backward_euler_interval_current")
    result["voltage_quadrature"] = voltage_quadrature
    return result


def _validated_dielectric_storage(history):
    """Validate native storage independently of terminal-current availability."""
    if not isinstance(history, (list, tuple)) or len(history) < 2:
        raise ValueError("dielectric energy audit requires an initial state and accepted intervals")
    energies, increments = [], []
    previous_time = 0.
    for index, state in enumerate(history):
        if (not isinstance(state, Mapping)
                or not isinstance(state.get("dielectric_energy_available"), (bool, np.bool_))
                or not state["dielectric_energy_available"]
                or state.get("dielectric_energy_scope") != "linear_lossless_charge_free_dielectric"):
            raise ValueError("native linear lossless charge-free dielectric energy scope is unavailable")
        for key, expected in (("valid", True), ("converged", True),
                              ("initial_state", not bool(index)),
                              ("dielectric_energy_increment_available", bool(index))):
            flag = state.get(key)
            if not isinstance(flag, (bool, np.bool_)) or bool(flag) != expected:
                raise ValueError(f"dielectric energy requires explicit {key}={expected}")
        time = _real_scalar(state.get("time_s"), "time_s")
        dt = _real_scalar(state.get("dt_s"), "dt_s")
        attempted = _real_scalar(state.get("attempted_time_s"), "attempted_time_s")
        if not index:
            if time != 0. or dt != 0. or attempted != 0.:
                raise ValueError("dielectric energy history must start at its zero-time initial state")
            if "dielectric_energy_increment_J" in state:
                raise ValueError("initial state must not prescribe an energy increment")
        else:
            duration = time - previous_time
            if (not math.isfinite(duration) or duration <= 0. or dt <= 0.
                    or not np.isclose(dt, duration, rtol=1e-10, atol=0.) or attempted != time):
                raise ValueError("dielectric energy accepted clock and attempted endpoint must agree")
            increments.append(_real_scalar(state.get("dielectric_energy_increment_J"),
                                           "dielectric_energy_increment_J"))
        energy = _real_scalar(state.get("dielectric_energy_J"), "dielectric_energy_J")
        if energy < 0.:
            raise ValueError("dielectric stored energy must be nonnegative")
        energies.append(energy)
        previous_time = time
    return energies, increments


def _dielectric_storage_consistency(energies, increments, *, atol_J):
    """Use snapshot rounding as an absolute allowance, not a relative scale."""
    residuals, relative = [], []
    for old, new, increment in zip(energies, energies[1:], increments):
        change = _finite_sum([new, -old])
        residual = _finite_sum([-new, old, increment])
        rounding = 8 * np.finfo(float).eps * max(old, new)
        excess = max(abs(residual) - rounding - atol_J, 0.)
        scale = max(abs(increment), abs(change))
        error = excess / scale if scale else (0. if not excess else math.inf)
        residuals.append(residual)
        relative.append(error)
    return np.array(residuals), max(relative)


def audit_transient_dielectric_energy(history, *, rtol=1e-8, atol_J=0.):
    """Check independent native field-energy increments against source work.

    Scope is a linear lossless charge-free dielectric, without FE or carrier
    transport. Native flags establish this scope. Current is the accepted BE
    interval current; voltage is linear within each interval. Numerical energy
    closure is tested per interval using incremental energies, never normalized
    by a large static stored-energy background. Dissipation is zero by this
    explicit model assumption, not inferred from a source-work residual.
    Invalid/missing inputs raise ValueError; a finite balance defect returns
    valid=False and energy_balance_validated=False. physical_validated is false.
    """
    rtol = _real_scalar(rtol, "rtol", positive=True)
    atol_J = _real_scalar(atol_J, "atol_J")
    if rtol >= 1. or atol_J < 0.:
        raise ValueError("require 0 < rtol < 1 and nonnegative atol_J")
    energies, increments = _validated_dielectric_storage(history)
    result = integrate_transient_terminal_history(history, voltage_quadrature="linear")
    storage_residuals, storage_error = _dielectric_storage_consistency(
        energies, increments, atol_J=atol_J)
    residuals, relative = [], []
    accepted = storage_error <= rtol
    for previous, state, increment in zip(history, history[1:], increments):
        works = []
        current = _real_array(state["electrode_total_currents_A"], "electrode currents")
        for v0, v1, i in zip(previous["electrode_voltages_V"], state["electrode_voltages_V"], current):
            charge = _scaled_product((float(state["dt_s"]), float(i)))
            works.extend(_be_source_work(float(v0), float(v1), charge, "linear"))
        work = _finite_sum(works)
        residual = _finite_sum([work, -increment])
        scale = max(abs(work), abs(increment))
        excess = max(abs(residual) - atol_J, 0.)
        error = excess / scale if scale else (0. if not excess else math.inf)
        accepted = accepted and error <= rtol
        residuals.append(residual)
        relative.append(error)
    result.update(
        valid=bool(accepted), energy_balance_validated=bool(accepted),
        energy_balance_scope="linear_lossless_charge_free_dielectric",
        energy_initial_J=energies[0], energy_final_J=energies[-1],
        stored_energy_change_J=_finite_sum(increments), dissipated_energy_J=0.,
        energy_balance_residual_J=_finite_sum(residuals),
        interval_energy_balance_residuals_J=np.array(residuals),
        max_interval_relative_residual=max(relative),
        interval_storage_consistency_residuals_J=storage_residuals,
        max_storage_relative_residual=storage_error,
        energy_balance_rtol=rtol, energy_balance_atol_J=atol_J,
    )
    return result


def extract_pund_terminal_charge(pulse_traces, *, terminal, reference_terminal,
                                 electrode_area_m2=None):
    """P-U and N-D total-current integrals for matched, declared pulse windows.

    Each P/U/N/D trace has times_s and named voltage/current maps in SI and
    explicitly declares ``current_kind='total'``. Paired voltage waveforms at
    every terminal and pulse durations must match; sampling grids may differ.
    Integration covers exactly the supplied windows, which must capture the
    same part of each pulse. Area, if given, is the full measured electrode
    area, not FE volume. Trace integration alone does not establish leakage
    cancellation, FE origin or experimental/material validity.
    """
    labels = ("P", "U", "N", "D")
    if (not isinstance(pulse_traces, Mapping)
            or any(not isinstance(name, str) or not name for name in pulse_traces)
            or any(name not in pulse_traces for name in labels)):
        raise ValueError("PUND terminal extraction requires P, U, N and D traces")
    if electrode_area_m2 is not None:
        electrode_area_m2 = _real_scalar(electrode_area_m2, "electrode_area_m2", positive=True)
    if (not isinstance(terminal, str) or not terminal
            or not isinstance(reference_terminal, str) or not reference_terminal):
        raise ValueError("PUND terminals must be non-empty strings")
    results, arrays = {}, {}
    for label in labels:
        trace = pulse_traces[label]
        if not isinstance(trace, Mapping) or trace.get("current_kind") != "total":
            raise ValueError("PUND requires explicitly declared total terminal current")
        arrays[label] = _validated_trace(trace)
        results[label] = integrate_terminal_trace(trace, current_kind="total")
        times, _, currents, voltages = arrays[label]
        if terminal == reference_terminal or terminal not in currents or reference_terminal not in currents:
            raise ValueError("PUND terminal and reference must be distinct named trace terminals")
        bias = voltages[terminal]-voltages[reference_terminal]
        if not np.all(np.isfinite(bias)):
            raise ValueError("PUND terminal bias overflowed")
        positive = label in ("P", "U")
        if (positive and (np.any(bias < 0) or not np.any(bias > 0))) or (
                not positive and (np.any(bias > 0) or not np.any(bias < 0))):
            raise ValueError("P/U require positive and N/D negative pulse bias")
    for first, second in (("P", "U"), ("N", "D")):
        t0, _, c0, v0 = arrays[first]
        t1, _, c1, v1 = arrays[second]
        span0, span1 = float(t0[-1]-t0[0]), float(t1[-1]-t1[0])
        if set(c0) != set(c1) or not np.isclose(span0, span1, rtol=1e-10, atol=0.):
            raise ValueError("paired PUND terminal sets and window durations must match")
        # Relative normalized clocks support different absolute origins and
        # sample grids, without extrapolating outside either supplied window.
        u0, u1 = (t0-t0[0])/span0, (t1-t1[0])/span1
        points = np.union1d(u0, u1)
        for name in v0:
            if not np.allclose(np.interp(points, u0, v0[name]),
                               np.interp(points, u1, v1[name]), rtol=1e-10, atol=1e-12):
                raise ValueError("paired PUND voltage waveforms must match at every terminal")
    if set(arrays["P"][2]) != set(arrays["N"][2]):
        raise ValueError("all PUND pulses must contain the same terminals")
    return _pund_charge_report(results, terminal, reference_terminal, electrode_area_m2,
                               "matched_total_terminal_current_integrals")


def _pund_charge_report(results, terminal, reference_terminal, electrode_area_m2, kind):
    """Shared signed differences for externally sampled and native BE windows."""
    labels = ("P", "U", "N", "D")
    charges = {label: results[label]["terminal_charge_C"][terminal] for label in labels}
    positive, negative = charges["P"]-charges["U"], charges["N"]-charges["D"]
    if not all(np.isfinite(value) for value in (positive, negative)):
        raise ValueError("PUND charge difference overflowed")
    magnitude = _fraction_float((Fraction(abs(positive))+Fraction(abs(negative)))/2)
    if not all(np.isfinite(value) for value in (positive, negative, magnitude)):
        raise ValueError("PUND charge difference overflowed")
    output = {
        "pulse_charge_C": charges,
        "switching_charge_positive_C": positive,
        "switching_charge_negative_C": negative,
        "switching_charge_magnitude_C": magnitude,
        "pulse_integrals": results,
        "terminal": terminal, "reference_terminal": reference_terminal,
        "extraction_kind": kind,
        "valid": True, "terminal_current_integrated": True,
        "terminal_charge_validated": False,
        "physical_validated": False,
    }
    if electrode_area_m2 is not None:
        normalized = [_scaled_product((value,), (electrode_area_m2,))
                      for value in (positive, negative, magnitude)]
        output.update(electrode_area_m2=float(electrode_area_m2),
                      switching_polarization_positive_C_per_m2=float(normalized[0]),
                      switching_polarization_negative_C_per_m2=float(normalized[1]),
                      switching_polarization_magnitude_C_per_m2=float(normalized[2]))
    return output
