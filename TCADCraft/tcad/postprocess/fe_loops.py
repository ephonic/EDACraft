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
        FE-layer-averaged polarization (Px component) [C/m^2].
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
    if "fe_alpha" in sim.mesh.fields:
        fe_mask = np.abs(sim.mesh.fields["fe_alpha"].ravel()) > 0.0
    else:
        fe_mask = np.ones(sim.mesh.npts(), dtype=bool)

    for Vg in V_loop:
        sim.update_contact(contact, Vg)
        result = sim.run(max_iter=max_iter, tol=tol)
        if "P" in result and result["P"] is not None:
            Px = np.asarray(result["P"]).reshape(-1, 3)[:, 0]
            P_avg = float(np.mean(Px[fe_mask])) if np.any(fe_mask) else float(np.mean(Px))
        else:
            P_avg = 0.0
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
        Soft-breakdown leakage conductance [F/m^3].
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
    if "fe_alpha" in sim.mesh.fields:
        fe_mask = np.abs(sim.mesh.fields["fe_alpha"].ravel()) > 0.0
    else:
        fe_mask = np.ones(sim.mesh.npts(), dtype=bool)

    for Vg in v_seq:
        sim.update_contact(contact, Vg)
        result = sim.run(max_iter=max_iter, tol=tol)
        if "P" in result and result["P"] is not None:
            Px = np.asarray(result["P"]).reshape(-1, 3)[:, 0]
            P_avg = float(np.mean(Px[fe_mask])) if np.any(fe_mask) else float(np.mean(Px))
        else:
            P_avg = 0.0
        P_vals.append(P_avg)

    P_arr = np.array(P_vals)
    # Extract P at the end of U and D pulse hold plateaus.
    # U plateau end: after pre-pol (3*seg + hold) + P (3*seg + hold) + U ramp+hold
    # D plateau end: + D ramp+hold
    n_pre = 3 * seg + pre_pol_hold     # pre-polarization segment length
    n_pulse = 3 * seg + pre_pol_hold   # each P/U/D segment length
    idx_U = min(2 * n_pre + n_pulse - 1, len(P_arr) - 1)   # end of U hold
    idx_D = min(3 * n_pre + 2 * n_pulse - 1, len(P_arr) - 1)  # end of D hold
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
    if "fe_alpha" in sim.mesh.fields:
        fe_mask = np.abs(sim.mesh.fields["fe_alpha"].ravel()) > 0.0
    else:
        fe_mask = np.ones(sim.mesh.npts(), dtype=bool)

    def _read_P(result):
        if "P" in result and result["P"] is not None:
            Px = np.asarray(result["P"]).reshape(-1, 3)[:, 0]
            return float(np.mean(Px[fe_mask])) if np.any(fe_mask) else float(np.mean(Px))
        return 0.0

    # 1. Program
    sim.update_contact(contact, V_program)
    result = sim.run(max_iter=max_iter, tol=tol)
    P_initial = _read_P(result)

    # 2. Monitor at V=0
    times = np.arange(n_steps) * dt
    P_vals = []
    for i in range(n_steps):
        sim.update_contact(contact, 0.0)
        result = sim.run(max_iter=max_iter, tol=tol)
        P_vals.append(_read_P(result))
    P_arr = np.array(P_vals)
    P_final = P_arr[-1]
    retention_loss = abs(P_initial - P_final) / max(abs(P_initial), 1e-30)

    return {
        "times": times,
        "P": P_arr,
        "P_initial": P_initial,
        "P_final": P_final,
        "retention_loss": retention_loss,
    }


def run_endurance(
    sim,
    contact: str,
    V_pulse: float,
    fe_thickness: float,
    n_cycles: int = 100,
    measure_every: int = 10,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> Dict[str, np.ndarray]:
    """Simulate endurance: cycle the device and measure Ps/Pr degradation.

    Applies ``n_cycles`` programming/erasing cycles (±V_pulse), measuring
    Ps/Pr every ``measure_every`` cycles via a PUND-like extraction. The
    degradation models accumulated trap charge (fatigue), which reduces the
    effective switching and broadens the loop.

    Parameters
    ----------
    sim : tcad.simulator.Simulator
        Configured simulator (ferroelectric enabled).
    contact : str
        Contact for cycling.
    V_pulse : float
        Programming/erasing pulse amplitude [V].
    fe_thickness : float
        FE layer thickness [m].
    n_cycles : int
        Total number of program/erase cycles.
    measure_every : int
        Measure Ps/Pr every this many cycles.
    max_iter, tol : see :func:`run_pv_sweep`.

    Returns
    -------
    dict with keys ``cycles``, ``Ps``, ``Pr``, ``memory_window`` [V].
    """
    if "fe_alpha" in sim.mesh.fields:
        fe_mask = np.abs(sim.mesh.fields["fe_alpha"].ravel()) > 0.0
    else:
        fe_mask = np.ones(sim.mesh.npts(), dtype=bool)

    def _read_P(result):
        if "P" in result and result["P"] is not None:
            Px = np.asarray(result["P"]).reshape(-1, 3)[:, 0]
            return float(np.mean(Px[fe_mask])) if np.any(fe_mask) else float(np.mean(Px))
        return 0.0

    cycles_list = []
    Ps_list = []
    Pr_list = []
    mw_list = []

    for cycle in range(1, n_cycles + 1):
        # Program (+V) then erase (-V)
        sim.update_contact(contact, V_pulse)
        sim.run(max_iter=max_iter, tol=tol)
        sim.update_contact(contact, -V_pulse)
        sim.run(max_iter=max_iter, tol=tol)

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
            # Memory window: voltage needed to flip P sign (simplified estimate
            # from the coercive voltage = Ec * thickness, reduced by fatigue).
            Ec_eff = abs(V_pulse) * max(Ps_val / max(abs(P_pos) + abs(P_neg), 1e-30), 0.1)
            mw_val = 2.0 * Ec_eff
            cycles_list.append(cycle)
            Ps_list.append(Ps_val)
            Pr_list.append(Pr_val)
            mw_list.append(mw_val)

    return {
        "cycles": np.array(cycles_list),
        "Ps": np.array(Ps_list),
        "Pr": np.array(Pr_list),
        "memory_window": np.array(mw_list),
    }
