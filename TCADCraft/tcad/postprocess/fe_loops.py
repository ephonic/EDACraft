"""Ferroelectric loop and PUND sequence drivers (P4.3).

These high-level helpers sweep a contact voltage over a bipolar loop (or a
PUND pulse train) and collect the ferroelectric polarization, so the raw
C++ solver can be exercised through the Python :class:`~tcad.simulator.Simulator`
API to produce P-V / P-E hysteresis loops and PUND extraction.

The drivers write the P-V testing principle into the tool (comments.docx
requested that the P-V testing method be encoded in the core code rather than
left to ad-hoc scripts).
"""

from __future__ import annotations
from contextlib import contextmanager
from collections.abc import Mapping
import os
import sys
from typing import Callable, Dict, List, Optional, Tuple
import warnings

import numpy as np

from .fe_readout import polarization_readout, _real_array, _weighted_polarization


@contextmanager
def _suppress_solver_stdio():
    """Temporarily silence low-level C/C++ stdout/stderr diagnostics.

    The MLC ramp helper intentionally retries intermediate non-converged points.
    C++ ``std::cout``/``std::cerr`` messages are written at the file-descriptor
    level before Python can decide whether the retry recovered, so suppress them
    inside this controlled retry loop and report only unrecovered failures.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    stdout_fd = os.dup(1)
    stderr_fd = os.dup(2)
    try:
        with open(os.devnull, "w", encoding="utf-8") as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(stdout_fd, 1)
        os.dup2(stderr_fd, 2)
        os.close(stdout_fd)
        os.close(stderr_fd)


def _fe_mask(sim) -> np.ndarray:
    """Return the configured FE domain, or material mask for a test double."""
    configured = getattr(sim, "_fe_node_mask", None)
    if configured is not None:
        mask = np.asarray(configured).ravel()
        if (mask.size != sim.mesh.npts() or not np.all(np.isfinite(mask))
                or not np.all((mask == 0) | (mask == 1))):
            raise ValueError("configured FE mask must contain one binary value per node")
        return mask.astype(bool)
    if "fe_alpha" in sim.mesh.fields:
        alpha = np.asarray(sim.mesh.fields["fe_alpha"], dtype=float).ravel()
        if alpha.size != sim.mesh.npts() or not np.all(np.isfinite(alpha)):
            raise ValueError("fe_alpha must contain one finite value per mesh node")
        return np.abs(alpha) > 0.0
    return np.ones(sim.mesh.npts(), dtype=bool)


def _require_real_scalar(value, name, *, positive=False, nonnegative=False):
    """Validate a protocol scalar before it can touch simulator state."""
    array = np.asarray(value)
    if (array.shape != () or array.dtype.kind not in "iuf"
            or isinstance(value, (bool, np.bool_)) or not np.isfinite(array)):
        raise ValueError(f"{name} must be a finite real scalar")
    value = float(array)
    if not np.isfinite(value):
        raise ValueError(f"{name} must be representable as a finite real scalar")
    if positive and value <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")
    if nonnegative and value < 0.0:
        raise ValueError(f"{name} must be finite and >= 0")
    return value


def _read_axial_polarization(sim, result, mask=None) -> float:
    """Read FE-volume-weighted polarization along the configured polar axis."""
    if "P" not in result or result["P"] is None:
        raise ValueError("polarization measurement requires result['P']")
    if mask is None:
        mask = _fe_mask(sim)
    readout = polarization_readout(
        result["P"], sim.mesh,
        polar_axis=getattr(sim, "_fe_polar_axis", 0), fe_mask=mask)
    result["fe_polarization_readout"] = readout
    return readout["mean_polarization"]


def _electric_field_magnitude(result, npts: int) -> np.ndarray:
    """Return |E|; missing/non-finite fields cannot drive trap kinetics."""
    components = []
    for name in ("Ex", "Ey", "Ez"):
        if name not in result:
            raise ValueError(f"dynamic trap coupling requires result['{name}']")
        value = np.asarray(result[name], dtype=float).ravel()
        if value.size != npts or not np.all(np.isfinite(value)):
            raise ValueError(f"result field {name} must contain {npts} finite values")
        components.append(value)
    return np.hypot(np.hypot(components[0], components[1]), components[2])


class ReliabilityStepError(RuntimeError):
    """A failed protocol segment, with only previously accepted progress."""

    def __init__(self, phase, completed_segments, elapsed_time, reason):
        self.phase = phase
        self.completed_segments = completed_segments
        self.elapsed_time = elapsed_time
        super().__init__(f"{phase} failed after {completed_segments} accepted "
                         f"segments ({elapsed_time:g} s): {reason}")


def _require_protocol_result(sim, result, physical_step=True):
    if not isinstance(result, Mapping):
        raise RuntimeError("electrical result must be a mapping")
    for name in ("converged", "valid", "target_reached"):
        # Legacy custom simulators may omit target metadata; convergence and
        # validity must always be explicit. Truthiness is not acceptance.
        flag = result.get(name, True if name == "target_reached" else None)
        if not isinstance(flag, (bool, np.bool_)) or not bool(flag):
            raise RuntimeError(f"electrical result['{name}'] must be boolean True")
    if "physical_step_accepted" in result:
        flag = result["physical_step_accepted"]
        if (not isinstance(flag, (bool, np.bool_))
                or bool(flag) != bool(physical_step)):
            raise RuntimeError("electrical result physical-step acceptance does not "
                               "match the requested segment")
    npts = sim.mesh.npts()
    for name, size in (("phi", npts), ("P", 3 * npts)):
        value = np.asarray(result.get(name, []))
        if (value.dtype.kind not in "iuf" or value.size != size
                or not np.all(np.isfinite(value))):
            raise RuntimeError(f"result['{name}'] must contain {size} finite real values")


def _reliability_step(sim, contact, voltage, dwell, max_iter, tol,
                      trap_model, temperature, phase, completed, elapsed,
                      degradation_model=None, stress_field=0.0, proxy_charge=None,
                      physical_step=True, result_validator=None):
    """One accepted physical segment plus a frozen-history charge re-solve."""
    if not hasattr(sim, "reliability_transaction"):
        raise TypeError("FE protocols require reliability_transaction()")
    try:
        with sim.reliability_transaction(trap_model, degradation_model):
            if dwell is not None and hasattr(sim, "set_ferroelectric_nls_dwell_time"):
                sim.set_ferroelectric_nls_dwell_time(dwell)
            if degradation_model is not None:
                fraction = degradation_model.advance(1.0, stress_field)
                _apply_cycling_state(sim, degradation_model, fraction)
            if proxy_charge is not None:
                sim.set_oxide_traps(proxy_charge)
            if hasattr(sim, "results") and sim.results is None:
                sim.set_contact(contact, voltage,
                                getattr(sim, "_contact_workfunctions", {}).get(contact))
            else:
                sim.update_contact(contact, voltage)
            result = sim.run(max_iter=max_iter, tol=tol, physical_step=physical_step)
            _require_protocol_result(sim, result, physical_step=physical_step)
            result, qot = _advance_traps(sim, result, trap_model, dwell, temperature)
            if qot is not None:
                result = sim.run(max_iter=max_iter, tol=tol, physical_step=False)
                _require_protocol_result(sim, result, physical_step=False)
            if result_validator is not None:
                result_validator(result)
            return result, qot
    except Exception as exc:
        raise ReliabilityStepError(phase, completed, elapsed, str(exc)) from exc


def _advance_traps(sim, result, trap_model, dt: float, temperature: float):
    """Advance an optional TrapKinetics state and feed Q_ot into Poisson."""
    if trap_model is None:
        return result, None
    _require_protocol_result(sim, result)
    if "phi" not in result or result["phi"] is None:
        raise ValueError("dynamic trap coupling requires result['phi']")
    phi = np.asarray(result["phi"], dtype=float).ravel()
    if phi.size == 0:
        raise ValueError("dynamic trap coupling requires non-empty result['phi']")
    field_mag = _electric_field_magnitude(result, phi.size)
    qot = trap_model.advance(phi, field_mag, dt, temperature)
    sim.set_oxide_traps(qot)
    return result, qot


def _apply_cycling_state(sim, degradation_model, active_fraction: float) -> None:
    """Feed M1 slow-state outputs back into the solver before the next
    electrical half-cycle.

    ``active_fraction`` rescales the switchable Preisach/NLS polarization while
    preserving the persistent play/NLS state (Simulator API).  The imprint
    state is converted to the solver's loop-shift convention: the solver's
    ``E_bi`` enters the material drive as ``E - E_bi``, so a physical imprint
    that stabilizes the polarity written by +V programming (M1
    ``imprint_state > 0``) corresponds to ``E_bi = -imprint_state``
    (imprint/Vc audit, 2026-09-18).
    """
    if hasattr(sim, "set_ferroelectric_active_fraction"):
        sim.set_ferroelectric_active_fraction(active_fraction)
    if (
        getattr(degradation_model, "imprint_field_max", 0.0) > 0.0
        and hasattr(sim, "set_ferroelectric_builtin_field")
    ):
        sim.set_ferroelectric_builtin_field(-degradation_model.imprint_field())


def _bipolar_voltage(Vmax: float, n_pts: int) -> np.ndarray:
    """Generate a full bipolar voltage sweep: 0 -> +Vmax -> 0 -> -Vmax -> 0.

    The sweep is piecewise-linear with ``n_pts`` points per segment. The return
    visits V=0 three times (start, mid, end), which is the standard shape for
    measuring a P-V hysteresis loop.
    """
    Vmax = _require_real_scalar(Vmax, "Vmax", positive=True)
    if (isinstance(n_pts, (bool, np.bool_))
            or not isinstance(n_pts, (int, np.integer)) or n_pts < 2):
        raise ValueError("n_pts must be an integer >= 2")
    seg = np.linspace(0.0, Vmax, n_pts)
    return np.concatenate([
        seg,                          # 0 -> +Vmax
        seg[::-1][1:],               # +Vmax -> 0
        -seg[1:],                    # 0 -> -Vmax
        -seg[::-1][1:],              # -Vmax -> 0
    ])


def _protocol_solver_parameters(max_iter, tol):
    if (isinstance(max_iter, (bool, np.bool_))
            or not isinstance(max_iter, (int, np.integer)) or max_iter < 1):
        raise ValueError("max_iter must be an integer >= 1")
    return _require_real_scalar(tol, "tol", positive=True)


def _protocol_duration(width, count):
    try:
        duration = width * count
    except OverflowError as exc:
        raise ValueError("total protocol duration must be finite") from exc
    return _require_real_scalar(duration, "total protocol duration", positive=True)


def _pv_solver_parameters(sim, max_iter, tol, dwell_time, sample_count):
    tol = _protocol_solver_parameters(max_iter, tol)
    dwell = getattr(sim, "_fe_nls_dt", 1e-6) if dwell_time is None else dwell_time
    dwell = _require_real_scalar(dwell, "dwell_time", positive=True)
    if not np.isfinite(dwell * sample_count):
        raise ValueError("total sweep duration must be finite")
    return tol, dwell


def run_pv_sweep(
    sim,
    contact: str,
    Vmax: float,
    n_pts: int = 26,
    max_iter: int = 50,
    tol: float = 1e-10,
    track_breakdown: bool = False,
    dwell_time: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    """Sweep a contact voltage over a bipolar loop and collect polarization.

    The simulator must already be configured (materials, contacts, ferroelectric
    model). An initial equilibrium result is reused when available. This function
    ramps ``contact`` through the bipolar sweep, reusing the previous solution
    as the initial guess (so the polarization carries path-dependent memory ->
    hysteresis), and records the FE-layer-averaged polarization at each point.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric must be enabled).
    contact : str
        Name of the contact to ramp (must have been set via ``set_contact``).
    Vmax : float
        Maximum voltage magnitude [V].
    n_pts : int
        Points per sweep segment.
    max_iter, tol : int, float
        Gummel solver control.
    track_breakdown : bool
        If True, read back ``sim._sim.breakdown_state()`` after each step and
        record the cumulative count of broken-down nodes. Requires
        ``sim.set_breakdown(True)`` to have been called beforehand.
    dwell_time : float, optional
        Physical dwell per requested sample. Defaults to configured NLS dwell,
        or 1 us for a custom simulator without that metadata. Numerical bias
        continuation does not add dwell. Failure restores the failed sample
        and raises ReliabilityStepError with accepted sample count/time.

    Returns
    -------
    voltages : np.ndarray
        The swept voltage sequence [V].
    P_avg : np.ndarray
        FE-layer-averaged polarization along the configured polar axis [C/m^2].
    last_result : dict
        The full result dict from the final solve (for inspection).
        If ``track_breakdown=True``, also contains ``"breakdown_count"``
        (cumulative broken-down node count per step).
    """
    V_loop = _bipolar_voltage(Vmax, n_pts)
    tol, dwell = _pv_solver_parameters(sim, max_iter, tol, dwell_time, len(V_loop))
    P_vals: List[float] = []
    bd_counts: List[int] = []
    result: Dict[str, np.ndarray] = {}
    # Identify FE nodes from the material field for averaging.
    fe_mask = _fe_mask(sim)
    bd_candidate = 0

    def validate_measurement(r):
        nonlocal bd_candidate
        _read_axial_polarization(sim, r, fe_mask)
        if track_breakdown:
            state = np.asarray(sim._sim.breakdown_state())
            if state.size != sim.mesh.npts() or not np.all(np.isin(state, [0, 1])):
                raise RuntimeError("breakdown state must contain one binary value per node")
            bd_candidate = int(np.count_nonzero(state))

    for i, Vg in enumerate(V_loop):
        result, _ = _reliability_step(
            sim, contact, Vg, dwell, max_iter, tol, None, 300.,
            f"pv_sample_{i+1}", i, i*dwell, result_validator=validate_measurement)
        P_avg = _read_axial_polarization(sim, result, fe_mask)
        P_vals.append(P_avg)
        if track_breakdown:
            bd_counts.append(bd_candidate)
    result["protocol_completed_segments"] = len(V_loop)
    result["protocol_elapsed_time"] = len(V_loop)*dwell
    result["physical_validated"] = False
    if track_breakdown:
        result["breakdown_count"] = np.array(bd_counts)
    return V_loop, np.array(P_vals), result


def run_pv_sweep_with_breakdown(
    sim,
    contact: str,
    Vmax: float,
    sigma_bd: float = 1.0e-2,
    n_pts: int = 26,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convenience wrapper: enable breakdown then run P-V sweep.

    Enables dielectric breakdown (M7b) with the given ``sigma_bd``, runs the
    bipolar P-V sweep, and returns the polarization plus a cumulative
    breakdown-count array so the P-V curve can be annotated with the bias
    point where breakdown first triggers. This addresses the comments.docx
    feedback that "the field exceeds the breakdown field but the result
    shows no breakdown" -- the breakdown now fires automatically inside
    ``DeviceSimulator::solve()`` and its effect is visible in the P-V curve.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric enabled, materials set).
    contact : str
        Contact to ramp.
    Vmax : float
        Maximum voltage [V].
    sigma_bd : float
        Post-breakdown filament conductivity [S/m].
    n_pts, max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    voltages : np.ndarray
    P_avg : np.ndarray
        FE-layer-averaged polarization [C/m^2].
    breakdown_count : np.ndarray
        Cumulative broken-down node count at each bias step.
    """
    V_loop = _bipolar_voltage(Vmax, n_pts)
    sigma_bd = _require_real_scalar(sigma_bd, "sigma_bd", nonnegative=True)
    tol, _ = _pv_solver_parameters(sim, max_iter, tol, None, len(V_loop))
    sim.set_breakdown(enabled=True, sigma_bd=sigma_bd)
    V, P, result = run_pv_sweep(sim, contact, Vmax, n_pts, max_iter, tol,
                                track_breakdown=True)
    bd = result["breakdown_count"]
    return V, P, bd


def run_pe_sweep(
    sim,
    contact: str,
    Emax: float,
    fe_thickness: float,
    n_pts: int = 26,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    """Sweep an electric field over a bipolar loop and collect P-E data.

    This is a convenience wrapper that converts a target field amplitude
    ``Emax`` [V/m] into a voltage amplitude ``Vmax = Emax * fe_thickness`` and
    delegates to :func:`run_pv_sweep`, then converts the returned voltages to
    fields.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator.
    contact : str
        Contact to ramp.
    Emax : float
        Maximum electric field [V/m].
    fe_thickness : float
        Ferroelectric layer thickness [m] (for V = E * d).
    n_pts, max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    E : np.ndarray
        Electric field [V/m] (= V / fe_thickness).
    P_avg : np.ndarray
        FE-layer-averaged polarization [C/m^2].
    last_result : dict
        Final result dict.
    """
    Emax = _require_real_scalar(Emax, "Emax", positive=True)
    fe_thickness = _require_real_scalar(fe_thickness, "fe_thickness", positive=True)
    Vmax = Emax * fe_thickness
    V_loop, P_avg, result = run_pv_sweep(sim, contact, Vmax, n_pts, max_iter, tol)
    E = V_loop / fe_thickness
    result["field_kind"] = "nominal_contact_voltage_over_fe_thickness"
    return E, P_avg, result


def run_pund_sequence(
    sim,
    contact: str,
    V_pulse: float,
    fe_thickness: float,
    n_points: int = 200,
    max_iter: int = 50,
    tol: float = 1e-10,
    pre_pol_V: Optional[float] = None,
    pre_pol_hold: int = 10,
    pulse_width: float = 1e-6,
    rise_time: float = 0.0,
    fall_time: float = 0.0,
    delay_time: float = 1e-6,
) -> Dict[str, np.ndarray]:
    """Preset then P/U/N/D, with explicit piecewise-constant physical durations.

    P/N are opposite-polarity switching pulses; U/D repeat the corresponding
    polarity. Paired FE state increments give signed model switching measures
    delta(P)-delta(U) and delta(N)-delta(D). These are not integrated terminal
    currents and do not subtract actual leakage or dielectric terminal charge.
    Ps is a plateau-magnitude diagnostic; Pr reads the zero-bias polarization
    after P and N. No saturation or experimental PUND accuracy is guaranteed.

    pulse_width is each plateau's duration, rise/fall_time each edge's duration,
    and delay_time each zero-bias gap's duration. n_points controls edge/gap
    subdivisions; pre_pol_hold subdivides each plateau without changing its
    duration. With zero edge time the bias change is instantaneous; numerical
    continuation is frozen. Zero-duration electrical helpers have repeated
    timestamps and physical_sample=False, so they consume no extra dwell.
    Each accepted segment survives subsequent failures; the failed segment is
    rolled back and ReliabilityStepError reports only accepted physical time.
    """
    V_pulse = _require_real_scalar(V_pulse, "V_pulse", positive=True)
    if pre_pol_V is None:
        pre_pol_V = V_pulse
    pre_pol_V = _require_real_scalar(pre_pol_V, "pre_pol_V", positive=True)
    fe_thickness = _require_real_scalar(fe_thickness, "fe_thickness", positive=True)
    pulse_width = _require_real_scalar(pulse_width, "pulse_width", positive=True)
    rise_time = _require_real_scalar(rise_time, "rise_time", nonnegative=True)
    fall_time = _require_real_scalar(fall_time, "fall_time", nonnegative=True)
    delay_time = _require_real_scalar(delay_time, "delay_time", nonnegative=True)
    for name, value, minimum in (("n_points",n_points,10),("pre_pol_hold",pre_pol_hold,1)):
        if (isinstance(value,(bool,np.bool_))
                or not isinstance(value,(int,np.integer)) or value < minimum):
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if (isinstance(max_iter, (bool, np.bool_))
            or not isinstance(max_iter, (int, np.integer)) or max_iter < 1):
        raise ValueError("max_iter must be an integer >= 1")
    tol = _require_real_scalar(tol, "tol", positive=True)
    seg = max(n_points//10, 1)
    if not np.isfinite(5*(float(pulse_width)+rise_time+fall_time+delay_time)):
        raise ValueError("total pulse sequence duration must be finite")
    for duration, subdivisions in ((pulse_width,pre_pol_hold),(rise_time,seg),
                                    (fall_time,seg),(delay_time,seg)):
        if duration > 0.0 and duration/subdivisions == 0.0:
            raise ValueError("physical segment duration underflows to zero")
    fe_mask = _fe_mask(sim)
    times, volts, polarizations, durations, physical = [], [], [], [], []
    elapsed, completed = 0.0, 0

    def step(voltage, duration, phase):
        nonlocal elapsed, completed
        commit = duration > 0.0
        result, _ = _reliability_step(
            sim,contact,voltage,duration if commit else None,max_iter,tol,
            None,300.,phase,completed,elapsed,physical_step=commit,
            result_validator=lambda r: _read_axial_polarization(sim,r,fe_mask))
        if commit:
            elapsed += duration
            completed += 1
        value = _read_axial_polarization(sim,result,fe_mask)
        times.append(elapsed); volts.append(voltage); polarizations.append(value)
        durations.append(duration); physical.append(commit)
        return value

    current = step(0.,0.,"pund_initial")
    labels = ["preset","P","U","N","D"]
    amplitudes = [-pre_pol_V,V_pulse,V_pulse,-V_pulse,-V_pulse]
    plateaus, zeros, increments, phase_ranges = [], [], [], []
    for label, amplitude in zip(labels,amplitudes):
        start_p = current
        start_index = len(times)
        if rise_time > 0.0:
            for i in range(1,seg+1):
                step(amplitude*i/seg,rise_time/seg,f"pund_{label}_rise_{i}")
        for i in range(pre_pol_hold):
            current = step(amplitude,pulse_width/pre_pol_hold,f"pund_{label}_hold_{i+1}")
        plateaus.append(current)
        increments.append(current-start_p)
        if fall_time > 0.0:
            for i in range(1,seg+1):
                current = step(amplitude*(1-i/seg),fall_time/seg,f"pund_{label}_fall_{i}")
        else:
            current = step(0.,0.,f"pund_{label}_return")
        if delay_time > 0.0:
            for i in range(seg):
                current = step(0.,delay_time/seg,f"pund_{label}_delay_{i+1}")
        zeros.append(current)
        phase_ranges.append((start_index,len(times)))
    positive = increments[1]-increments[2]
    negative = increments[3]-increments[4]
    return {
        "times":np.asarray(times),"voltages":np.asarray(volts),
        "P":np.asarray(polarizations),"sample_durations":np.asarray(durations),
        "physical_sample":np.asarray(physical,dtype=bool),
        "pulse_labels":labels,"phase_ranges":np.asarray(phase_ranges,dtype=int),
        "pulse_plateau_p":np.asarray(plateaus),"pulse_zero_bias_p":np.asarray(zeros),
        "pulse_delta_p":np.asarray(increments),
        "P_P":plateaus[1],"P_U":plateaus[2],"P_N":plateaus[3],"P_D":plateaus[4],
        "P_switch_positive":positive,"P_switch_negative":negative,
        "switching_polarization_magnitude":.5*(abs(positive)+abs(negative)),
        "Ps":.5*(abs(plateaus[1])+abs(plateaus[3])),
        "Pr":.5*(abs(zeros[1])+abs(zeros[3])),
        "valid":True,"completed_segments":completed,"elapsed_time":elapsed,
        "extraction_kind":"fe_state_increment_difference",
        "polarization_weighting":"FE_control_volume",
        "Ps_kind":"pulse_plateau_magnitude","Pr_kind":"zero_bias_fe_polarization",
        "terminal_charge_validated":False,"physical_validated":False,
    }


def run_retention(
    sim,
    contact: str,
    V_program: float,
    n_steps: int = 20,
    dt: float = 1e-6,
    max_iter: int = 50,
    tol: float = 1e-10,
    trap_model=None,
    temperature: float = 300.0,
    program_width: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """Simulate retention: polarize, then monitor P decay at V=0.

    1. Apply a programming pulse ``V_program`` to set the polarization.
    2. Remove the bias (V=0) and record the polarization at successive
       time points. The FE polarization may decay due to depolarization field
       and/or charge trapping (if oxide traps are enabled).

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric enabled).
    contact : str
        Contact for programming/read.
    V_program : float
        Programming pulse amplitude [V].
    n_steps : int
        Number of retention monitoring steps.
    dt : float
        Nominal time step [s] between monitoring points.
    max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    dict with keys ``times`` [s], ``P`` [C/m^2], ``P_initial``, ``P_final``,
    ``retention_loss`` (fraction of initial P lost).

    Each segment uses a scoped reliability transaction. Invalid electrical
    results raise ReliabilityStepError with accepted progress and restore the
    failed segment, including a failed FE-volume polarization readout. Trap
    charge uses one operator-split update and one frozen
    FE charge re-solve; this is not an iterated coupled FE/trap transient.
    ``temperature`` drives trap rates only; configure device temperature on
    Simulator separately.
    """
    if (isinstance(n_steps, (bool, np.bool_))
            or not isinstance(n_steps, (int, np.integer)) or n_steps < 1):
        raise ValueError("n_steps must be >= 1")
    n_steps = int(n_steps)
    dt = _require_real_scalar(dt, "retention dt", positive=True)
    if program_width is None:
        program_width = dt
    program_width = _require_real_scalar(program_width, "program_width", positive=True)
    temperature = _require_real_scalar(temperature, "temperature", positive=True)
    V_program = _require_real_scalar(V_program, "V_program")
    tol = _protocol_solver_parameters(max_iter, tol)
    hold_duration = _protocol_duration(dt, n_steps)
    elapsed_time = _require_real_scalar(program_width + hold_duration,
                                        "total retention duration", positive=True)
    times = (np.arange(n_steps, dtype=float) + 1) * dt
    fe_mask = _fe_mask(sim)

    P_sample = None

    def _measure_P(result):
        nonlocal P_sample
        P_sample = _read_axial_polarization(sim, result, fe_mask)

    result, _ = _reliability_step(
        sim, contact, V_program, program_width, max_iter, tol,
        trap_model, temperature, "retention_program", 0, 0.0,
        result_validator=_measure_P)
    P_initial = P_sample
    P_vals, qot_vals, occupancy_vals = [], [], []
    for i in range(n_steps):
        result, qot = _reliability_step(
            sim, contact, 0.0, dt, max_iter, tol, trap_model, temperature,
            f"retention_hold_{i+1}", i + 1, program_width + i * dt,
            result_validator=_measure_P)
        if qot is not None:
            qot_vals.append(float(np.mean(qot)))
            occupancy_vals.append(float(np.mean(trap_model.occupancy)))
        P_vals.append(P_sample)
    P_arr = np.array(P_vals)
    P_final = P_arr[-1]
    retention_loss = abs(P_initial - P_final) / max(abs(P_initial), 1e-30)

    output = {
        "valid": True,
        "completed_segments": n_steps + 1,
        "elapsed_time": elapsed_time,
        "transaction_scope": "fe_breakdown_charge_contacts_guesses_and_slow_models",
        "physical_validated": False,
        "times": times,
        "P": P_arr,
        "P_initial": P_initial,
        "P_final": P_final,
        "retention_loss": retention_loss,
        "polarization_weighting": "FE_control_volume",
    }
    if trap_model is not None:
        output["Q_ot"] = np.asarray(qot_vals)
        output["trap_occupancy"] = np.asarray(occupancy_vals)
    return output


def run_endurance(
    sim,
    contact: str,
    V_pulse: float,
    fe_thickness: float,
    n_cycles: int = 100,
    measure_every: int = 10,
    max_iter: int = 50,
    tol: float = 1e-10,
    fatigue_Nc: float = 1e6,
    Q_ot_max: float = 1.0e5,
    E_bd: float = 6.0e8,
    trap_model=None,
    degradation_model=None,
    pulse_width: float = 1.0e-6,
    temperature: float = 300.0,
    legacy_breakdown_scaling: bool = False,
) -> Dict[str, np.ndarray]:
    """Simulate endurance: cycle the device and measure Ps/Pr degradation.

    Applies ``n_cycles`` programming/erasing cycles (+/-V_pulse), sampling
    pulse-plateau polarization every ``measure_every`` cycles. Sampling adds
    no pulses. These are not zero-bias remanence or PUND measurements.
    ``memory_window`` is an uncalibrated polarization-ratio proxy. The first
    accepted cycle provides its baseline; there are no hidden conditioning
    pulses. A failed segment raises ReliabilityStepError and rolls back that
    segment, including its FE-volume polarization readout; previously accepted
    half-cycles remain committed. Each plateau is read before the next pulse.

    Without explicit state objects, the backwards-compatible trap proxy is:
        Q_ot(N) = Q_ot_max * (1 - exp(-N / Nc))
    Pass ``trap_model=TrapKinetics(...)`` to replace it with capture/emission
    dynamics, and ``degradation_model=CyclingDegradation(...)`` to evolve
    competing wake-up/fatigue populations and the switchable polarization.

    ``degradation_model=FieldHistoryCyclingState(...)`` (plan0918 M1) in
    addition accumulates a signed imprint state: the model advances once per
    half-cycle (program +E, erase -E; zero-field segments freeze), the
    switchable-polarization fraction and imprint are fed back into the solver
    before every half-cycle, and the returned ``imprint_field`` /
    ``imprint_loop_shift_V`` trajectories record the rigid loop translation
    (the shift that stabilizes the last-programmed polarity).

    Breakdown should normally be enabled on ``Simulator`` so its irreversible
    state, explicit filament current and Joule heat are used. The former
    empirical E/E_bd polarization scaling is available only through
    ``legacy_breakdown_scaling=True``.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric enabled).
    contact : str
        Contact for cycling.
    V_pulse : float
        Programming/erasing pulse amplitude [V].
    fe_thickness : float
        FE layer thickness [m] (used for field-dependent fatigue/breakdown).
    n_cycles : int
        Total number of program/erase cycles.
    measure_every : int
        Measure Ps/Pr every this many cycles.
    max_iter, tol : see :func:`run_pv_sweep`.
    fatigue_Nc : float
        Characteristic fatigue cycle count (wake-up->fatigue transition).
    Q_ot_max : float
        Maximum accumulated oxide trap charge [C/m^3].
    E_bd : float
        Breakdown field [V/m] for field-dependent lifetime.

    Returns
    -------
    dict with keys ``cycles``, ``Ps``, ``Pr``, ``memory_window`` [V],
    ``Q_ot`` (accumulated trap charge per cycle).
    """
    if (isinstance(n_cycles, (bool, np.bool_))
            or not isinstance(n_cycles, (int, np.integer)) or n_cycles < 1):
        raise ValueError("n_cycles must be >= 1")
    if (isinstance(measure_every, (bool, np.bool_))
            or not isinstance(measure_every, (int, np.integer)) or measure_every < 1):
        raise ValueError("measure_every must be >= 1")
    n_cycles, measure_every = int(n_cycles), int(measure_every)
    fatigue_Nc = _require_real_scalar(fatigue_Nc, "fatigue_Nc", positive=True)
    fe_thickness = _require_real_scalar(fe_thickness, "fe_thickness", positive=True)
    pulse_width = _require_real_scalar(pulse_width, "pulse_width", positive=True)
    V_pulse = _require_real_scalar(V_pulse, "V_pulse", positive=True)
    Q_ot_max = _require_real_scalar(Q_ot_max, "Q_ot_max", nonnegative=True)
    temperature = _require_real_scalar(temperature, "temperature", positive=True)
    tol = _protocol_solver_parameters(max_iter, tol)
    elapsed_time = _protocol_duration(pulse_width, 2 * n_cycles)
    E_cycle = _require_real_scalar(V_pulse / fe_thickness, "cycling field", positive=True)
    if not isinstance(legacy_breakdown_scaling, (bool, np.bool_)):
        raise ValueError("legacy_breakdown_scaling must be boolean")
    legacy_breakdown_scaling = bool(legacy_breakdown_scaling)
    if legacy_breakdown_scaling:
        E_bd = _require_real_scalar(E_bd, "legacy E_bd", positive=True)
        legacy_field_ratio = _require_real_scalar(E_cycle / E_bd, "legacy E/E_bd")
    fe_mask = _fe_mask(sim)

    P_sample = None

    def _measure_P(result):
        nonlocal P_sample
        P_sample = _read_axial_polarization(sim, result, fe_mask)

    # Read the existing program/erase plateaus. Extra measurement pulses
    # previously consumed FE dwell without entering trap/damage bookkeeping.
    Ps0 = None
    Vc0 = abs(V_pulse) * 0.5  # explicitly uncalibrated window proxy

    cycles_list = []
    Ps_list = []
    Pr_list = []
    mw_list = []
    qot_list = []
    active_fraction_list = []
    imprint_list = []
    trap_occupancy_list = []

    for cycle in range(1, n_cycles + 1):
        Q_ot = Q_ot_max * (-np.expm1(-cycle / fatigue_Nc))
        proxy_charge = Q_ot if trap_model is None else None
        r_program, _ = _reliability_step(
            sim, contact, V_pulse, pulse_width, max_iter, tol,
            trap_model, temperature, f"endurance_program_{cycle}",
            2 * (cycle - 1), 2 * (cycle - 1) * pulse_width,
            degradation_model, E_cycle, proxy_charge,
            result_validator=_measure_P)
        P_pos = P_sample
        r_erase, qot_dynamic = _reliability_step(
            sim, contact, -V_pulse, pulse_width, max_iter, tol,
            trap_model, temperature, f"endurance_erase_{cycle}",
            2 * cycle - 1, (2 * cycle - 1) * pulse_width,
            degradation_model, -E_cycle, result_validator=_measure_P)
        P_neg = P_sample
        active_fraction = (degradation_model.active_fraction
                           if degradation_model is not None else 1.0)
        if qot_dynamic is not None:
            Q_ot = float(np.mean(qot_dynamic))
        if Ps0 is None:
            Ps0 = 0.5 * (abs(P_pos) + abs(P_neg))
        if cycle % measure_every == 0 or cycle == n_cycles:
            Ps_val = 0.5 * (abs(P_pos) + abs(P_neg))
            Pr_val = 0.5 * (abs(P_pos) - abs(P_neg))

            # Fatigue model: accumulated trap charge
            # Field-dependent breakdown: higher field => earlier failure
            # Breakdown factor reduces Ps when E_cycle approaches/exceeds E_bd
            # Historical compatibility only. The default no longer invents a
            # polarization loss from E/E_bd: actual breakdown is represented
            # by the solver's irreversible conductive state and explicit
            # J_bd. Users reproducing old curves may opt into this proxy.
            breakdown_factor = 1.0
            if legacy_breakdown_scaling:
                fatigue_fraction = -np.expm1(-(cycle / fatigue_Nc) / 0.3)
                breakdown_factor = max(0.0, 1.0 - legacy_field_ratio * fatigue_fraction)

            # Effective Ps reduced by fatigue + breakdown
            Ps_eff = Ps_val * max(breakdown_factor, 0.01)

            # Memory window: 2 * Vc, where Vc degrades with cycling
            # (proportional to Ps_eff / Ps0 to capture fatigue)
            Vc_eff = Vc0 * max(Ps_eff / max(Ps0, 1e-30), 0.05)
            mw_val = 2.0 * Vc_eff

            cycles_list.append(cycle)
            Ps_list.append(Ps_eff)
            Pr_list.append(Pr_val * max(breakdown_factor, 0.01))
            mw_list.append(mw_val)
            qot_list.append(Q_ot)
            active_fraction_list.append(active_fraction)
            if hasattr(degradation_model, "imprint_state"):
                imprint_list.append(degradation_model.imprint_field())
            if trap_model is not None:
                trap_occupancy_list.append(float(np.mean(trap_model.occupancy)))

    output = {
        "valid": True,
        "completed_segments": 2 * n_cycles,
        "elapsed_time": elapsed_time,
        "measurement_extra_pulses": 0,
        "degradation_count_unit": "accepted_half_cycle",
        "transaction_scope": "fe_breakdown_charge_contacts_guesses_and_slow_models",
        "memory_window_kind": "uncalibrated_polarization_ratio_proxy",
        "polarization_metric_kind": "pulse_plateau_magnitudes_and_asymmetry",
        "polarization_weighting": "FE_control_volume",
        "legacy_breakdown_scaling": bool(legacy_breakdown_scaling),
        "physical_validated": False,
        "cycles": np.array(cycles_list),
        "Ps": np.array(Ps_list),
        "Pr": np.array(Pr_list),
        "memory_window": np.array(mw_list),
        "Q_ot": np.array(qot_list),
    }
    if degradation_model is not None:
        output["active_fraction"] = np.asarray(active_fraction_list)
        output["wakeup_state"] = float(degradation_model.wakeup_state)
        output["fatigue_state"] = float(degradation_model.fatigue_state)
        if hasattr(degradation_model, "imprint_state"):
            imprint_arr = np.asarray(imprint_list, dtype=float)
            output["imprint_field"] = imprint_arr
            output["imprint_loop_shift_V"] = -imprint_arr * fe_thickness
    if trap_model is not None:
        output["trap_occupancy"] = np.asarray(trap_occupancy_list)
    return output


def _pulse_width_window(voltage, plateau, reference):
    """Evaluate 2*V*plateau/reference without overflowing intermediate factors."""
    voltage_numerator, voltage_denominator = voltage.as_integer_ratio()
    plateau_numerator, plateau_denominator = plateau.as_integer_ratio()
    reference_numerator, reference_denominator = reference.as_integer_ratio()
    try:
        # Round once, including at the largest finite/subnormal boundary.
        window = ((2 * voltage_numerator * plateau_numerator * reference_denominator)
                  / (voltage_denominator * plateau_denominator * reference_numerator))
    except OverflowError as exc:
        raise ValueError("pulse-width memory window overflowed") from exc
    if plateau > 0 and window == 0:
        raise ValueError("pulse-width memory window underflowed")
    return _require_real_scalar(window, "pulse-width memory window", nonnegative=True)


def run_pulse_width_sweep(
    sim,
    contact: str,
    V_pulse: float,
    fe_thickness: float,
    pulse_widths: List[float] = None,
    max_iter: int = 50,
    tol: float = 1e-10,
    saturation_polarization: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """Isolated +/- pulse pairs from one initial device state for each width.

    Each experiment restores the entry FE/charge/breakdown/contact state even
    on success, so width ordering cannot change the curve. The diagnostic
    memory_window=2*|V_pulse|*plateau_magnitude/Ps_reference is an uncalibrated
    proxy, not an extracted threshold window or proof of saturation/speed.
    The reference must be explicit or come from the configured FE base Ps;
    normalizing by the largest sample would make results depend on the batch.
    Each signed plateau is captured inside its pulse transaction before the
    next pulse. A failed derived metric rejects the whole isolated experiment.
    """
    if pulse_widths is None:
        pulse_widths = np.logspace(-9, -4, 10).tolist()
    widths = _real_array(pulse_widths, "pulse_widths").copy()
    if widths.ndim != 1 or widths.size == 0 or not np.all(np.isfinite(widths)) or np.any(widths <= 0.):
        raise ValueError("pulse_widths must be a non-empty 1D array of finite positive values")
    if np.any(widths > np.finfo(float).max/2):
        raise ValueError("pulse pair duration must be finite")
    V_pulse = _require_real_scalar(V_pulse, "V_pulse", positive=True)
    fe_thickness = _require_real_scalar(fe_thickness, "fe_thickness", positive=True)
    tol = _protocol_solver_parameters(max_iter, tol)
    if saturation_polarization is None:
        saturation_polarization = getattr(sim,"_fe_base_ps",None)
    saturation_polarization = _require_real_scalar(saturation_polarization,
                                                  "saturation_polarization reference", positive=True)
    fe_mask = _fe_mask(sim)
    ps_values, windows, program_values, erase_values = [], [], [], []
    for i, width in enumerate(widths):
        measurement = {}

        def measure_program(result):
            measurement["program"] = _read_axial_polarization(sim, result, fe_mask)

        def measure_erase(result):
            measurement["erase"] = _read_axial_polarization(sim, result, fe_mask)
            plateau, _ = _weighted_polarization(
                np.abs([measurement["program"], measurement["erase"]]), np.ones(2), 2.)
            measurement["Ps"] = plateau
            measurement["window"] = _pulse_width_window(V_pulse, plateau, saturation_polarization)

        try:
            with sim.reliability_transaction(commit=False):
                _reliability_step(
                    sim,contact,V_pulse,width,max_iter,tol,None,300.,
                    f"width_{i+1}_program",0,0.,
                    result_validator=measure_program)
                _reliability_step(
                    sim,contact,-V_pulse,width,max_iter,tol,None,300.,
                    f"width_{i+1}_erase",1,width,
                    result_validator=measure_erase)
        except ReliabilityStepError as exc:
            exc.experiment_index = i
            exc.completed_experiments = i
            exc.experiment_rolled_back = True
            raise
        ps_values.append(measurement["Ps"])
        windows.append(measurement["window"])
        program_values.append(measurement["program"])
        erase_values.append(measurement["erase"])
    ps_arr = np.asarray(ps_values)
    return {
        "pulse_widths":widths,"Ps":ps_arr,
        "memory_window":np.asarray(windows),
        "program_polarization":np.asarray(program_values),
        "erase_polarization":np.asarray(erase_values),
        "saturation_polarization_reference":float(saturation_polarization),
        "memory_window_kind":"uncalibrated_plateau_ratio_proxy",
        "polarization_weighting":"FE_control_volume",
        "experiment_durations":2*widths,"completed_experiments":widths.size,
        "initial_state_policy":"restore_entry_state_for_each_width",
        "valid":True,"physical_validated":False,
    }


def _mlc_separation_parameter(value, name, positive=False):
    array = np.asarray(value)
    if (array.shape != () or array.dtype.kind not in "iuf"
            or not np.isfinite(array)):
        raise ValueError(f"{name} must be a finite real scalar")
    value = float(array)
    if not np.isfinite(value) or value < 0.0 or (positive and value == 0.0):
        bound = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be finite and {bound}")
    return value


def extract_mlc_memory_window(
    program_voltages,
    read_currents,
    min_state_separation_decades: float = 0.10,
    noise_floor: float | None = None,
) -> Dict[str, np.ndarray]:
    """Extract diagnostic MLC current spans and an uncensored level count.

    ``comment6.docx`` flagged a misleading "negative memory window" in the
    AlScN/MoS2 MLC exploration.  The sign is useful as a polarity diagnostic,
    but the externally reported MLC window is the *separation* between read
    states and must therefore be non-negative.  This helper reports both:

    - ``memory_window_decades``: full (max-min) log10 current span, always >= 0.
    - ``signed_window_decades``: high-program-current minus low-program-current
      log span.  Negative values indicate an inverted FE/channel polarity or an
      intentional p-type convention that should be documented.
    - ``n_states``: count of distinct uncensored read magnitudes separated by
      at least ``min_state_separation_decades``. Censored values contribute no
      measured level. A zero separation still merges identical magnitudes.

    The historical spans use the explicit noise floor where necessary;
    observed_memory_window_decades uses only uncensored samples (None if none).
    n_states_including_censored records the clipped-sample heuristic separately.
    polarity_valid is false if either endpoint is censored or all program
    voltages coincide. These diagnostics do not establish BER or physical MLC
    reliability; physical_validated remains false.
    """
    V = np.asarray(program_voltages, dtype=float).ravel()
    I = np.asarray(read_currents, dtype=float).ravel()
    if V.size != I.size:
        raise ValueError("program_voltages and read_currents must have same length")
    if V.size < 2:
        raise ValueError("at least two program/read states are required")
    if not np.all(np.isfinite(V)):
        raise ValueError("program_voltages must be finite")
    if not np.all(np.isfinite(I)):
        raise ValueError("read_currents must be finite")
    min_state_separation_decades = _mlc_separation_parameter(
        min_state_separation_decades, "min_state_separation_decades")
    if noise_floor is not None:
        noise_floor = _mlc_separation_parameter(noise_floor, "noise_floor", positive=True)
    raw_abs = np.abs(I)
    censored = raw_abs <= 0.0
    if np.any(censored) and noise_floor is None:
        raise ValueError(
            "read_currents contains zero; provide noise_floor so censored "
            "states are not silently replaced by the sample minimum"
        )
    floor = noise_floor if noise_floor is not None else 0.0
    I_safe = np.maximum(raw_abs, floor)
    censored |= raw_abs < floor
    if np.any(I_safe <= 0.0):
        raise ValueError("at least one positive current or a positive noise_floor is required")
    order_v = np.argsort(V)
    V_sorted = V[order_v]
    I_by_v = I_safe[order_v]
    signed = float(np.log10(I_by_v[-1]) - np.log10(I_by_v[0]))
    log_levels = np.sort(np.log10(I_safe))
    full_span = float(log_levels[-1] - log_levels[0])
    def separated_count(levels):
        levels = np.unique(levels)
        if levels.size == 0:
            return 0
        count = 1
        last = float(levels[0])
        for level in levels[1:]:
            if float(level) - last >= min_state_separation_decades:
                count += 1
                last = float(level)
        return count

    observed_log_levels = np.log10(raw_abs[~censored])
    n_states = separated_count(observed_log_levels)
    observed_span = (float(np.max(observed_log_levels) - np.min(observed_log_levels))
                     if observed_log_levels.size else None)
    endpoints_censored = bool(censored[order_v[0]] or censored[order_v[-1]])

    return {
        "program_voltages": V,
        "raw_read_currents": I.copy(),
        "read_currents": I_safe,
        "censored_mask": censored,
        "program_voltages_sorted": V_sorted,
        "read_currents_sorted_by_program": I_by_v,
        "memory_window_decades": full_span,
        "memory_window_kind": "noise_floor_clipped_log_current_span",
        "observed_memory_window_decades": observed_span,
        "signed_window_decades": signed,
        "signed_window_censored": endpoints_censored,
        "polarity": "normal" if signed >= 0.0 else "inverted",
        "polarity_valid": not endpoints_censored and bool(V_sorted[-1] > V_sorted[0]),
        "n_states": int(n_states),
        "n_states_including_censored": separated_count(log_levels),
        "n_censored_samples": int(np.count_nonzero(censored)),
        "state_count_kind": "uncensored_log_current_separation_heuristic",
        "physical_validated": False,
        "min_state_separation_decades": float(min_state_separation_decades),
    }


def _mlc_dwell_time(sim, width, name):
    if width is None:
        return None
    value = np.asarray(width)
    if (value.shape != () or value.dtype.kind not in "iuf"
            or not np.isfinite(value) or value <= 0.0):
        raise ValueError(f"{name} must be a finite positive real scalar")
    width = float(value)
    if not np.isfinite(width):
        raise ValueError(f"{name} must be representable as finite seconds")
    if not callable(getattr(sim, "set_ferroelectric_nls_dwell_time", None)):
        raise TypeError("MLC pulse widths require set_ferroelectric_nls_dwell_time()")
    if getattr(sim, "_fe_model_int", 2) != 2:
        raise ValueError("explicit MLC pulse widths currently require the NLS model")
    return width


def _ramp_contact_and_run(
    sim,
    contact: str,
    target_voltage: float,
    max_step: float,
    max_iter: int,
    tol: float,
    retries: int,
    dwell_time: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    if not hasattr(sim, "reliability_transaction"):
        raise TypeError("MLC ramps require reliability_transaction()")
    if not np.isfinite(target_voltage):
        raise ValueError("target voltage must be finite")
    if not np.isfinite(max_step) or max_step <= 0.0:
        raise ValueError("max_step must be finite and > 0")
    if (isinstance(retries, (bool, np.bool_))
            or not isinstance(retries, (int, np.integer)) or retries < 0):
        raise ValueError("retries must be an integer >= 0")
    dwell_time = _mlc_dwell_time(sim, dwell_time, "dwell_time")

    contacts = getattr(sim, "_contact_voltages", {})
    start_voltage = float(contacts.get(contact, getattr(sim, "voltage", 0.0)))
    delta = float(target_voltage) - start_voltage
    n_steps = max(1, int(np.ceil(abs(delta) / max_step)))
    result: Dict[str, np.ndarray] = {}

    def accepted(r, final_step):
        try:
            _require_protocol_result(sim, r, physical_step=final_step)
        except (TypeError, ValueError, RuntimeError):
            return False
        return True

    class RejectedAttempt(Exception):
        pass

    # A ramp is one protocol segment: intermediate contact changes and solver
    # guesses must all roll back if any point fails.  This prevents a failed
    # MLC candidate from contaminating the next candidate's FE/history state.
    with sim.reliability_transaction():
        for step, voltage in enumerate(np.linspace(start_voltage, float(target_voltage), n_steps + 1)[1:]):
            attempts = retries + 1
            for attempt in range(attempts):
                try:
                    # Rejecting a result must restore history before a retry,
                    # even if the underlying solver already changed its state.
                    with sim.reliability_transaction():
                        if step == n_steps - 1 and dwell_time is not None:
                            sim.set_ferroelectric_nls_dwell_time(dwell_time)
                        sim.update_contact(contact, float(voltage))
                        with warnings.catch_warnings(), _suppress_solver_stdio():
                            warnings.filterwarnings(
                                "ignore",
                                message=r"Solver did not converge; result marked valid=False.*",
                                category=RuntimeWarning,
                            )
                            result = sim.run(max_iter=max_iter, tol=tol, physical_step=step == n_steps - 1)
                        if not accepted(result, step == n_steps - 1):
                            raise RejectedAttempt
                except RejectedAttempt:
                    continue
                break
            else:
                raise RuntimeError(
                    f"{contact} ramp to {float(voltage):.6g} V was not accepted"
                )
    return result


def run_mlc_program_read_sweep(
    sim,
    contact: str,
    program_voltages,
    read_voltage: float = 0.0,
    reset_voltage: Optional[float] = None,
    max_ramp_step: float = 0.25,
    max_iter: int = 300,
    tol: float = 1.0e-6,
    retries: int = 2,
    current_reader: Optional[Callable[[object, Dict[str, np.ndarray]], float]] = None,
    min_state_separation_decades: float = 0.10,
    current_noise_floor: Optional[float] = None,
    *,
    program_width: Optional[float] = None,
    reset_width: Optional[float] = None,
    read_width: Optional[float] = None,
) -> Dict[str, np.ndarray]:
    """Run a robust FeFET MLC program-read sequence.

    The driver mirrors a Sentaurus-style quasistationary program/reset/read
    flow: every program, erase, and read transition is broken into bounded
    voltage increments and each intermediate point must converge before the
    next one is attempted.  This directly targets the AlScN thickness-scaling
    failure mode from ``comment6.docx`` where thick FE layers required large
    coercive voltages and direct multi-volt jumps drove the coupled
    FE/continuity solver into zero-pivot or limit-cycle states.

    If ``current_reader`` is supplied, it is called at each read point and the
    returned currents are post-processed by :func:`extract_mlc_memory_window`.
    Otherwise the helper records read-point axial FE polarization only.
    Every point requires explicit boolean convergence/validity and finite phi/P.
    Reported target/physical-step rejection also fails acceptance; numerical
    helpers need not accept a physical step. Rejected attempts roll back before
    retrying, and a failed ramp restores its entry state. Earlier completed
    program/reset/read ramps remain committed. Readout validation is part of
    the read ramp transaction: a failed current/polarization measurement
    restores the state after programming. Raw current signs are preserved;
    state separation uses magnitudes. Legacy custom simulators may
    omit target/physical-step flags, so acceptance is not physical validation.
    For NLS, program_width/reset_width/read_width independently set the final
    accepted dwell in seconds. None inherits the entry NLS dwell (resolved once
    for all phases). Intermediate ramp points and failed attempts add no dwell.
    Explicit widths for other built-in FE models are rejected. Legacy custom
    simulators without NLS dwell metadata retain their behavior and report
    elapsed_time=None. Segment records report accepted dwell, not a coupled
    transient waveform, numerical runtime, or full operation latency.
    """
    V_program = np.asarray(program_voltages, dtype=float).ravel()
    if V_program.size == 0:
        raise ValueError("program_voltages must contain at least one value")
    if not np.all(np.isfinite(V_program)):
        raise ValueError("program_voltages must be finite")
    if not np.isfinite(read_voltage):
        raise ValueError("read_voltage must be finite")
    if reset_voltage is not None and not np.isfinite(reset_voltage):
        raise ValueError("reset_voltage must be finite when supplied")
    if not np.isfinite(max_ramp_step) or max_ramp_step <= 0.0:
        raise ValueError("max_ramp_step must be finite and > 0")
    if (isinstance(max_iter, (bool, np.bool_))
            or not isinstance(max_iter, (int, np.integer)) or max_iter < 1):
        raise ValueError("max_iter must be an integer >= 1")
    if not np.isfinite(tol) or tol <= 0.0:
        raise ValueError("tol must be finite and > 0")
    if (isinstance(retries, (bool, np.bool_))
            or not isinstance(retries, (int, np.integer)) or retries < 0):
        raise ValueError("retries must be an integer >= 0")
    min_state_separation_decades = _mlc_separation_parameter(
        min_state_separation_decades, "min_state_separation_decades")
    if current_noise_floor is not None:
        current_noise_floor = _mlc_separation_parameter(
            current_noise_floor, "current_noise_floor", positive=True)
    if current_reader is not None:
        if not callable(current_reader):
            raise ValueError("current_reader must be callable")
        if V_program.size < 2:
            raise ValueError("current metrics require at least two program/read states")

    inherited_width = (getattr(sim, "_fe_nls_dt", None)
                       if getattr(sim, "_fe_model_int", 2) == 2 else None)
    widths = {
        phase: _mlc_dwell_time(sim, inherited_width if width is None else width,
                              f"{phase}_width")
        for phase, width in (("program", program_width), ("reset", reset_width),
                             ("read", read_width))
    }
    active_phases = ["program", "read"]
    if reset_voltage is not None:
        active_phases.insert(0, "reset")
    timing_available = all(widths[phase] is not None for phase in active_phases)
    if timing_available:
        total_dwell = sum(widths[phase] for phase in active_phases) * V_program.size
        if not np.isfinite(total_dwell):
            raise ValueError("total MLC dwell must be finite")

    if hasattr(sim, "set_use_newton"):
        sim.set_use_newton(True)
    if hasattr(sim, "set_newton_log_space"):
        sim.set_newton_log_space(True)

    fe_mask = _fe_mask(sim) if hasattr(sim, "mesh") else None
    read_results: List[Dict[str, np.ndarray]] = []
    read_currents: List[float] = []
    read_polarization: List[float] = []
    segments = []

    def record_segment(phase, index, voltage):
        segments.append({"phase": phase, "state_index": index,
                         "voltage_V": float(voltage), "dwell_s": widths[phase]})

    for index, Vp in enumerate(V_program):
        if reset_voltage is not None:
            _ramp_contact_and_run(
                sim, contact, float(reset_voltage), max_ramp_step,
                max_iter, tol, retries, dwell_time=widths["reset"],
            )
            record_segment("reset", index, reset_voltage)
        _ramp_contact_and_run(
            sim, contact, float(Vp), max_ramp_step, max_iter, tol, retries,
            dwell_time=widths["program"],
        )
        record_segment("program", index, Vp)
        # Measurement rejection must restore the accepted program state, even
        # if the read ramp has already changed polarization or breakdown.
        with sim.reliability_transaction():
            result = _ramp_contact_and_run(
                sim, contact, float(read_voltage), max_ramp_step,
                max_iter, tol, retries, dwell_time=widths["read"],
            )
            if current_reader is not None:
                value = np.asarray(current_reader(sim, result))
                if (value.shape != () or value.dtype.kind not in "iuf"
                        or not np.isfinite(value)):
                    raise RuntimeError("current_reader must return one finite real scalar current")
                current = float(value)
                if current == 0.0 and current_noise_floor is None:
                    raise ValueError("zero read current requires current_noise_floor")
            polarization = _read_axial_polarization(sim, result, fe_mask)
        record_segment("read", index, read_voltage)
        read_results.append(result)
        if current_reader is not None:
            read_currents.append(current)
        read_polarization.append(polarization)

    output: Dict[str, np.ndarray] = {
        "program_voltages": V_program,
        "read_voltage": float(read_voltage),
        "read_results": read_results,
        "read_polarization": np.asarray(read_polarization, dtype=float),
        "polarization_weighting": "FE_control_volume",
        "valid": True,
        "physical_validated": False,
        "completed_segments": len(segments),
        "completed_read_states": len(read_results),
        "elapsed_time": total_dwell if timing_available else None,
        "timing_available": timing_available,
        "timing_kind": "accepted_nls_dwell" if timing_available else "unavailable",
        "protocol_segments": segments,
        "phase_widths_s": widths,
    }
    if current_reader is not None:
        current_arr = np.asarray(read_currents, dtype=float)
        output["read_currents"] = current_arr
        output.update(extract_mlc_memory_window(
            V_program, current_arr, min_state_separation_decades,
            noise_floor=current_noise_floor,
        ))
    return output


def run_power_measurement(
    sim,
    contact: str,
    V_pulse: float,
    pulse_width: float = 1e-6,
    max_iter: int = 50,
    tol: float = 1e-10,
    *,
    cross_section_m2: Optional[float] = None,
    current_reader: Optional[Callable] = None,
) -> Dict:
    """Estimate signed source work assuming the final current holds throughout.

    This performs one accepted physical pulse of ``pulse_width`` and uses
    final-state current, not a time-resolved transient integral. Supply either
    the full area for the 1-D conduction-current extractor, or a callback
    ``current_reader(sim, result)`` returning all named terminal currents in A,
    positive into the device. All applied terminal voltages enter V*I; signs
    are preserved. No density proxy, implicit area or extraction fallback is
    allowed. Missing displacement/switching transients and stored energy mean
    this estimate cannot establish full operation energy or dissipation.

    Legacy energy/I_avg/power keys now denote signed source-work estimate [J],
    selected final terminal current [A], and total source power estimate [W].
    Use integrate_terminal_trace for an actual resolved SI current waveform.
    """
    from .terminal_trace import integrate_terminal_trace
    V_pulse = _require_real_scalar(V_pulse, "V_pulse")
    pulse_width = _require_real_scalar(pulse_width, "pulse_width", positive=True)
    tol = _protocol_solver_parameters(max_iter, tol)
    if (cross_section_m2 is None) == (current_reader is None):
        raise ValueError("supply either cross_section_m2 or current_reader in absolute A")
    if current_reader is not None and not callable(current_reader):
        raise ValueError("current_reader must be callable")
    if cross_section_m2 is not None:
        cross_section_m2 = _require_real_scalar(cross_section_m2,
                                                "cross_section_m2", positive=True)
        if sim.mesh.ny != 1 or sim.mesh.nz != 1:
            raise ValueError("default power extraction requires a 1-D mesh")
    captured = {}
    def validate_and_integrate(result):
        if current_reader is None:
            from .current import terminal_currents_1d
            currents = terminal_currents_1d(sim, result, cross_section_m2=cross_section_m2)
        else:
            currents = current_reader(sim, result)
        voltages = result.get("applied_contact_voltages")
        if (not isinstance(currents, Mapping) or not isinstance(voltages, Mapping)
                or len(currents) < 2 or set(currents) != set(voltages)
                or contact not in currents):
            raise ValueError("power extraction requires all applied named terminal currents and voltages")
        for values in (currents, voltages):
            for value in values.values():
                array = np.asarray(value)
                if (array.shape != () or array.dtype.kind not in "iuf"
                        or not np.all(np.isfinite(array))):
                    raise ValueError("power extraction requires finite scalar SI currents and voltages")
                scalar = float(array)
                if not np.isfinite(scalar):
                    raise ValueError("power extraction requires finite scalar SI currents and voltages")
        if float(voltages[contact]) != float(V_pulse):
            raise ValueError("power measurement did not reach the requested pulse voltage")
        trace = {
            "times_s": np.array([0., pulse_width]), "valid": True,
            "terminal_currents_A": {name: np.full(2, float(value)) for name, value in currents.items()},
            "terminal_voltages_V": {name: np.full(2, float(value)) for name, value in voltages.items()},
        }
        captured.update(integrate_terminal_trace(
            trace, current_kind="conduction" if current_reader is None else "total"))
        captured["terminal_currents_A"] = {name: float(value) for name, value in currents.items()}
        captured["terminal_voltages_V"] = {name: float(value) for name, value in voltages.items()}
    _reliability_step(sim, contact, V_pulse, pulse_width, max_iter, tol,
                      None, 300., "power_pulse", 0, 0.,
                      result_validator=validate_and_integrate)
    captured.update(
        energy=captured["supplied_energy_J"],
        supplied_energy_estimate_J=captured["supplied_energy_J"],
        I_avg=captured["terminal_currents_A"][contact],
        power=captured["mean_source_power_W"],
        pulse_width=float(pulse_width), V_pulse=float(V_pulse),
        measurement_kind="constant_final_current_pulse_estimate",
        time_resolved=False, full_operation_energy_available=False,
        current_source="native_1d_conduction" if current_reader is None else "explicit_current_reader_A",
        completed_segments=1, elapsed_time=float(pulse_width),
    )
    # A user callback supplies absolute currents but does not prove that it
    # includes displacement. Do not assert total-current completeness for it.
    if current_reader is not None:
        captured["current_kind"] = "user_supplied_unspecified_components"
    captured["integration_kind"] = "constant_final_current_pulse_estimate"
    return captured
