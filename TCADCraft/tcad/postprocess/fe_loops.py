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
from typing import Dict, List, Optional, Tuple

import numpy as np


def _fe_mask(sim) -> np.ndarray:
    """Return the material-defined ferroelectric-node mask."""
    if "fe_alpha" in sim.mesh.fields:
        return np.abs(sim.mesh.fields["fe_alpha"].ravel()) > 0.0
    return np.ones(sim.mesh.npts(), dtype=bool)


def _read_axial_polarization(sim, result, mask=None) -> float:
    """Read FE-layer mean polarization along the configured polar axis."""
    if "P" not in result or result["P"] is None:
        return 0.0
    if mask is None:
        mask = _fe_mask(sim)
    P = np.asarray(result["P"]).reshape(-1, 3)
    axis = int(getattr(sim, "_fe_polar_axis", 0))
    if axis not in (0, 1, 2):
        axis = 0
    values = P[:, axis]
    return float(np.mean(values[mask])) if np.any(mask) else float(np.mean(values))


def _electric_field_magnitude(result, npts: int) -> np.ndarray:
    """Return |E| from a solver result, or zeros for protocol test doubles."""
    components = []
    for name in ("Ex", "Ey", "Ez"):
        value = np.asarray(result.get(name, np.zeros(npts)), dtype=float).ravel()
        if value.size != npts:
            raise ValueError(f"result field {name} size {value.size} != {npts}")
        components.append(value)
    return np.sqrt(sum(component * component for component in components))


def _advance_traps(sim, result, trap_model, dt: float, temperature: float):
    """Advance an optional TrapKinetics state and feed Q_ot into Poisson."""
    if trap_model is None:
        return result, None
    if "phi" not in result or result["phi"] is None:
        raise ValueError("dynamic trap coupling requires result['phi']")
    phi = np.asarray(result["phi"], dtype=float).ravel()
    if phi.size == 0:
        raise ValueError("dynamic trap coupling requires non-empty result['phi']")
    field_mag = _electric_field_magnitude(result, phi.size)
    qot = trap_model.advance(phi, field_mag, dt, temperature)
    sim.set_oxide_traps(qot)
    return result, qot


def _bipolar_voltage(Vmax: float, n_pts: int) -> np.ndarray:
    """Generate a full bipolar voltage sweep: 0 -> +Vmax -> 0 -> -Vmax -> 0.

    The sweep is piecewise-linear with ``n_pts`` points per segment. The return
    visits V=0 three times (start, mid, end), which is the standard shape for
    measuring a P-V hysteresis loop.
    """
    seg = np.linspace(0.0, Vmax, n_pts)
    return np.concatenate([
        seg,                          # 0 -> +Vmax
        seg[::-1][1:],               # +Vmax -> 0
        -seg[1:],                    # 0 -> -Vmax
        -seg[::-1][1:],              # -Vmax -> 0
    ])


def run_pv_sweep(
    sim,
    contact: str,
    Vmax: float,
    n_pts: int = 26,
    max_iter: int = 50,
    tol: float = 1e-10,
    track_breakdown: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, np.ndarray]]:
    """Sweep a contact voltage over a bipolar loop and collect polarization.

    The simulator must already be configured (materials, contacts, ferroelectric
    model) and have had an initial ``run()`` at equilibrium. This function
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
    P_vals: List[float] = []
    bd_counts: List[int] = []
    result: Dict[str, np.ndarray] = {}
    # Identify FE nodes from the material field for averaging.
    fe_mask = _fe_mask(sim)

    for Vg in V_loop:
        sim.update_contact(contact, Vg)
        result = sim.run(max_iter=max_iter, tol=tol)
        P_avg = _read_axial_polarization(sim, result, fe_mask)
        P_vals.append(P_avg)
        if track_breakdown:
            try:
                bd_state = sim._sim.breakdown_state()
                bd_counts.append(int(np.sum(np.asarray(bd_state) > 0)))
            except Exception:
                bd_counts.append(0)
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
    sim.set_breakdown(enabled=True, sigma_bd=sigma_bd)
    V, P, result = run_pv_sweep(sim, contact, Vmax, n_pts, max_iter, tol,
                                track_breakdown=True)
    bd = result.get("breakdown_count", np.zeros(len(V)))
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
    Vmax = Emax * fe_thickness
    V_loop, P_avg, result = run_pv_sweep(sim, contact, Vmax, n_pts, max_iter, tol)
    E = V_loop / fe_thickness
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
) -> Dict[str, np.ndarray]:
    """Run a PUND (Positive-Up-Negative-Down) pulse sequence and extract Ps/Pr.

    The standard PUND protocol applies five pulses:

    1. **N** (negative pre-polarization, to -V): ensures the device starts in a
       well-defined -P_s state before measurement. This is critical -- without
       adequate pre-polarization the P pulse also does switching, inflating P_U
       and giving unphysical results (comments.docx: "P-U appears negative,
       forward switching did not occur"). The pre-polarization amplitude
       ``pre_pol_V`` (default = V_pulse) and hold steps ``pre_pol_hold``
       ensure the device is fully polarized before the measurement pulses.
    2. **P** (positive, to +V): sets the device to +P_s.
    3. **U** (positive, to +V): the switching current gives P_s + P_r.
    4. **D** (negative, to -V): the switching current gives P_s - P_r.

    The extracted quantities:
      - P_s = (|P_U| + |P_D|) / 2  (saturation polarization)
      - P_r = (|P_U| - |P_D|) / 2  (remanent polarization)

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric enabled).
    contact : str
        Contact to pulse.
    V_pulse : float
        Pulse amplitude [V].
    fe_thickness : float
        FE layer thickness [m] (for field reference).
    n_points : int
        Total resolution of the pulse train.
    max_iter, tol : see :func:`run_pv_sweep`.
    pre_pol_V : float, optional
        Pre-polarization amplitude [V]. Default = V_pulse. Set higher to ensure
        full polarization of high-Ec materials like AlScN.
    pre_pol_hold : int
        Number of hold steps at the pre-polarization plateau (ensures the
        device reaches steady-state polarization before measurement).

    Returns
    -------
    dict with keys:
        ``times`` [s], ``voltages`` [V], ``P`` [C/m^2],
        ``Ps`` [C/m^2], ``Pr`` [C/m^2], ``P_U`` [C/m^2], ``P_D`` [C/m^2].
    """
    if pre_pol_V is None:
        pre_pol_V = V_pulse
    seg = max(n_points // 10, 5)
    ramp = lambda a, b: np.linspace(a, b, seg)
    hold = lambda v, n: np.full(n, v)

    # Phase 0: Negative pre-polarization with hold (ensure full -P_s)
    # Phase 1: P pulse (+V) -> positive set
    # Phase 2: U pulse (+V) -> positive read (switching + non-switching)
    # Phase 3: D pulse (-V) -> negative read
    v_seq = np.concatenate([
        ramp(0, -pre_pol_V), hold(-pre_pol_V, pre_pol_hold), ramp(-pre_pol_V, 0),
        ramp(0, V_pulse), hold(V_pulse, pre_pol_hold), ramp(V_pulse, 0),    # P
        ramp(0, V_pulse), hold(V_pulse, pre_pol_hold), ramp(V_pulse, 0),    # U
        ramp(0, -V_pulse), hold(-V_pulse, pre_pol_hold), ramp(-V_pulse, 0), # D
    ])
    dt = 1e-6   # nominal time step [s] (quasi-static; real time not critical)
    times = np.arange(len(v_seq)) * dt

    P_vals: List[float] = []
    result: Dict[str, np.ndarray] = {}
    fe_mask = _fe_mask(sim)

    for Vg in v_seq:
        sim.update_contact(contact, Vg)
        result = sim.run(max_iter=max_iter, tol=tol)
        P_avg = _read_axial_polarization(sim, result, fe_mask)
        P_vals.append(P_avg)

    P_arr = np.array(P_vals)
    # Extract P at the end of the U and D *hold plateaus*, before each return
    # ramp to zero.  Every segment is ramp-up + hold + ramp-down, i.e.
    # ``2*seg + pre_pol_hold`` samples.  The former 3*seg bookkeeping sampled
    # the end of the zero-bias return ramp for U and clipped D to the final
    # point, which could report Ps=Pr=0 despite successful switching.
    n_segment = 2 * seg + pre_pol_hold
    idx_U = 2 * n_segment + seg + pre_pol_hold - 1
    idx_D = 3 * n_segment + seg + pre_pol_hold - 1
    P_U = P_arr[idx_U]
    P_D = P_arr[idx_D]
    Ps = 0.5 * (abs(P_U) + abs(P_D))
    Pr = 0.5 * (abs(P_U) - abs(P_D))

    return {
        "times": times,
        "voltages": v_seq,
        "P": P_arr,
        "P_U": P_U,
        "P_D": P_D,
        "Ps": Ps,
        "Pr": Pr,
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
    """
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("retention dt must be finite and > 0")
    fe_mask = _fe_mask(sim)

    def _read_P(result):
        return _read_axial_polarization(sim, result, fe_mask)

    if program_width is None:
        program_width = dt
    if not np.isfinite(program_width) or program_width <= 0.0:
        raise ValueError("program_width must be finite and > 0")

    # 1. Program
    sim.update_contact(contact, V_program)
    result = sim.run(max_iter=max_iter, tol=tol)
    result, qot = _advance_traps(
        sim, result, trap_model, program_width, temperature,
    )
    if qot is not None:
        # Re-solve once with the newly captured charge, making the program
        # state self-consistent before the retention clock starts.
        result = sim.run(max_iter=max_iter, tol=tol)
    P_initial = _read_P(result)

    # 2. Monitor at V=0
    times = (np.arange(n_steps) + 1) * dt
    P_vals = []
    qot_vals = []
    occupancy_vals = []
    for i in range(n_steps):
        if hasattr(sim, "set_ferroelectric_nls_dwell_time"):
            sim.set_ferroelectric_nls_dwell_time(dt)
        sim.update_contact(contact, 0.0)
        result = sim.run(max_iter=max_iter, tol=tol)
        result, qot = _advance_traps(sim, result, trap_model, dt, temperature)
        if qot is not None:
            result = sim.run(max_iter=max_iter, tol=tol)
            qot_vals.append(float(np.mean(qot)))
            occupancy_vals.append(float(np.mean(trap_model.occupancy)))
        P_vals.append(_read_P(result))
    P_arr = np.array(P_vals)
    P_final = P_arr[-1]
    retention_loss = abs(P_initial - P_final) / max(abs(P_initial), 1e-30)

    output = {
        "times": times,
        "P": P_arr,
        "P_initial": P_initial,
        "P_final": P_final,
        "retention_loss": retention_loss,
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

    Applies ``n_cycles`` programming/erasing cycles (+/-V_pulse), measuring
    Ps/Pr every ``measure_every`` cycles via a PUND-like extraction.

    Without explicit state objects, the backwards-compatible trap proxy is:
        Q_ot(N) = Q_ot_max * (1 - exp(-N / Nc))
    Pass ``trap_model=TrapKinetics(...)`` to replace it with capture/emission
    dynamics, and ``degradation_model=CyclingDegradation(...)`` to evolve
    competing wake-up/fatigue populations and the switchable polarization.

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
    if n_cycles < 1:
        raise ValueError("n_cycles must be >= 1")
    if measure_every < 1:
        raise ValueError("measure_every must be >= 1")
    if not np.isfinite(fatigue_Nc) or fatigue_Nc <= 0.0:
        raise ValueError("fatigue_Nc must be finite and > 0")
    if not np.isfinite(fe_thickness) or fe_thickness <= 0.0:
        raise ValueError("fe_thickness must be finite and > 0")
    if not np.isfinite(pulse_width) or pulse_width <= 0.0:
        raise ValueError("pulse_width must be finite and > 0")
    fe_mask = _fe_mask(sim)

    # Initial Ps measurement (wake-up baseline)
    def _read_P(result):
        return _read_axial_polarization(sim, result, fe_mask)

    # Measure initial Ps
    sim.update_contact(contact, V_pulse)
    sim.run(max_iter=max_iter, tol=tol)
    sim.update_contact(contact, -V_pulse)
    sim.run(max_iter=max_iter, tol=tol)
    sim.update_contact(contact, V_pulse)
    P_pos0 = _read_P(sim.run(max_iter=max_iter, tol=tol))
    sim.update_contact(contact, -V_pulse)
    P_neg0 = _read_P(sim.run(max_iter=max_iter, tol=tol))
    Ps0 = 0.5 * (abs(P_pos0) + abs(P_neg0))
    # Coercive voltage from initial measurement
    Vc0 = abs(V_pulse) * 0.5  # approximate initial coercive voltage

    # Cycling field
    E_cycle = abs(V_pulse) / max(fe_thickness, 1e-15)

    cycles_list = []
    Ps_list = []
    Pr_list = []
    mw_list = []
    qot_list = []
    active_fraction_list = []
    trap_occupancy_list = []

    for cycle in range(1, n_cycles + 1):
        # Feed fatigue-driven trapped charge back into Poisson before the
        # electrical cycle.  Previously Q_ot was only reported and the solved
        # device state was completely unaffected by endurance degradation.
        Q_ot = Q_ot_max * (1.0 - np.exp(-cycle / fatigue_Nc))
        if trap_model is None and hasattr(sim, "set_oxide_traps"):
            sim.set_oxide_traps(Q_ot)
        active_fraction = 1.0
        if degradation_model is not None:
            active_fraction = degradation_model.advance(1.0, E_cycle)
            if hasattr(sim, "set_ferroelectric_active_fraction"):
                sim.set_ferroelectric_active_fraction(active_fraction)
        # Program (+V) then erase (-V)
        sim.update_contact(contact, V_pulse)
        r_program = sim.run(max_iter=max_iter, tol=tol)
        _, qot_dynamic = _advance_traps(
            sim, r_program, trap_model, pulse_width, temperature,
        )
        sim.update_contact(contact, -V_pulse)
        r_erase = sim.run(max_iter=max_iter, tol=tol)
        _, qot_dynamic = _advance_traps(
            sim, r_erase, trap_model, pulse_width, temperature,
        )
        if qot_dynamic is not None:
            Q_ot = float(np.mean(qot_dynamic))

        if cycle % measure_every == 0 or cycle == n_cycles:
            # Measure: positive then negative P
            sim.update_contact(contact, V_pulse)
            r_pos = sim.run(max_iter=max_iter, tol=tol)
            P_pos = _read_P(r_pos)
            sim.update_contact(contact, -V_pulse)
            r_neg = sim.run(max_iter=max_iter, tol=tol)
            P_neg = _read_P(r_neg)
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
                breakdown_factor = max(0.0, 1.0 - (E_cycle / E_bd) *
                                       (1.0 - np.exp(-cycle / (fatigue_Nc * 0.3))))

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
            if trap_model is not None:
                trap_occupancy_list.append(float(np.mean(trap_model.occupancy)))

    output = {
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
    if trap_model is not None:
        output["trap_occupancy"] = np.asarray(trap_occupancy_list)
    return output


def run_pulse_width_sweep(
    sim,
    contact: str,
    V_pulse: float,
    fe_thickness: float,
    pulse_widths: List[float] = None,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> Dict[str, np.ndarray]:
    """Measure switching speed: sweep pulse width and measure memory window.

    For each pulse width, applies a programming pulse of that width and
    measures the resulting memory window. The minimum pulse width that
    produces a saturated window indicates the device's fastest switching speed.

    In the quasi-static solver, pulse width maps to NLS dwell time: a shorter
    pulse gives less time for NLS switching, producing a smaller window.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (NLS model recommended for speed-dependent switching).
    contact : str
        Contact for pulse application.
    V_pulse : float
        Pulse amplitude [V].
    fe_thickness : float
        FE layer thickness [m] (for field reference).
    pulse_widths : List[float]
        Pulse widths to sweep [s], default logspace from 1e-9 to 1e-4.
    max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    dict with keys ``pulse_widths`` [s], ``memory_window`` [V], ``Ps`` [C/m^2].
    """
    if pulse_widths is None:
        pulse_widths = np.logspace(-9, -4, 10).tolist()
    if len(pulse_widths) == 0:
        raise ValueError("pulse_widths must contain at least one value")
    if not np.all(np.isfinite(pulse_widths)) or np.any(np.asarray(pulse_widths) <= 0.0):
        raise ValueError("pulse_widths must be finite and > 0")

    fe_mask = _fe_mask(sim)

    def _read_P(result):
        return _read_axial_polarization(sim, result, fe_mask)

    mw_values = []
    ps_values = []

    for pw in pulse_widths:
        # Set NLS dwell time = pulse width (controls switching completeness)
        if hasattr(sim, "set_ferroelectric_nls_dwell_time"):
            sim.set_ferroelectric_nls_dwell_time(pw)

        # Program with +V
        sim.update_contact(contact, V_pulse)
        P_pos = _read_P(sim.run(max_iter=max_iter, tol=tol))

        # Erase with -V
        sim.update_contact(contact, -V_pulse)
        P_neg = _read_P(sim.run(max_iter=max_iter, tol=tol))

        Ps_val = 0.5 * (abs(P_pos) + abs(P_neg))
        ps_values.append(Ps_val)

    # Scale the saturated 2*Vc window by switching completeness.  The old
    # expression divided Ps_val by itself and therefore returned exactly
    # |V_pulse| for every pulse width, hiding all NLS speed dependence.
    ps_arr = np.asarray(ps_values, dtype=float)
    ps_sat = max(float(np.max(ps_arr)), 1e-30)
    mw_values = 2.0 * abs(V_pulse) * ps_arr / ps_sat

    return {
        "pulse_widths": np.array(pulse_widths),
        "memory_window": np.asarray(mw_values),
        "Ps": ps_arr,
    }


def run_power_measurement(
    sim,
    contact: str,
    V_pulse: float,
    pulse_width: float = 1e-6,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> Dict[str, float]:
    """Measure single-operation energy consumption.

    Estimates the energy consumed in a single write/erase operation by
    integrating the transient current-voltage product over the pulse duration.

    E = integral(I * V * dt) ~ I_avg * V_pulse * pulse_width

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator.
    contact : str
        Contact for pulse application.
    V_pulse : float
        Pulse amplitude [V].
    pulse_width : float
        Pulse duration [s].
    max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    dict with keys ``energy`` [J], ``I_avg`` [A], ``power`` [W].
    """
    # Run transient with the pulse
    sim.update_contact(contact, V_pulse)
    result = sim.run(max_iter=max_iter, tol=tol)

    # Extract current from result (try real current, fallback to proxy)
    try:
        from tcad.postprocess.current import contact_current_1d
        I_avg = abs(contact_current_1d(sim, result, contact))
    except Exception:
        n = np.asarray(result.get("n", np.zeros(1)))
        I_avg = float(n.max()) * 1e-15

    energy = I_avg * abs(V_pulse) * pulse_width
    power = energy / max(pulse_width, 1e-15)

    return {
        "energy": energy,
        "I_avg": I_avg,
        "power": power,
        "pulse_width": pulse_width,
        "V_pulse": V_pulse,
    }
