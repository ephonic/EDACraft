"""Device performance metrics extraction from simulation results."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from .current import contact_current_1d


def extract_transfer_characteristics(
    sweep_results: List[Dict],
    drain_contact: str = "drain",
    gate_contact: str = "gate",
) -> Dict[str, np.ndarray]:
    """Extract Id-Vg transfer characteristics from a voltage sweep.

    Parameters
    ----------
    sweep_results : list of dict
        Results from ``simulate_sweep``.
    drain_contact : str
        Name of the drain contact.
    gate_contact : str
        Name of the gate contact.

    Returns
    -------
    dict
        Keys: ``Vg`` (gate voltages), ``Ion`` (peak carrier density proxy),
        ``Vth`` (threshold voltage), ``SS`` (subthreshold swing in mV/dec),
        ``Ion_Ioff`` (on/off ratio).
    """
    Vg = np.array([r["_voltages"][gate_contact] for r in sweep_results])
    n_max = np.array([r["n"].max() for r in sweep_results])
    p_max = np.array([r["p"].max() for r in sweep_results])
    # Carrier density as proxy for drain current
    I_proxy = n_max

    # Threshold voltage: constant current method at 1e-3 of max
    I_on = I_proxy.max()
    I_th = 1e-3 * I_on
    vth_indices = np.where(I_proxy >= I_th)[0]
    Vth = float(Vg[vth_indices[0]]) if len(vth_indices) > 0 else float(Vg[-1])

    # Subthreshold swing: dVg / d(log10(I)) in subthreshold region
    I_off = I_proxy.min()
    if I_on > 0 and I_off > 0:
        log_I = np.log10(np.clip(I_proxy, max(I_off, 1.0), None))
        # Find subthreshold region: I between I_off and 0.1*I_on
        sub_mask = (I_proxy < 0.1 * I_on) & (I_proxy > I_off * 1.1)
        if sub_mask.sum() >= 2:
            Vg_sub = Vg[sub_mask]
            log_I_sub = log_I[sub_mask]
            # Linear fit: Vg = SS * log10(I) + offset
            coeffs = np.polyfit(log_I_sub, Vg_sub, 1)
            SS = abs(float(coeffs[0])) * 1e3  # mV/dec
        else:
            SS = float("nan")
        Ion_Ioff = float(I_on / max(I_off, 1.0))
    else:
        SS = float("nan")
        Ion_Ioff = float("nan")

    return {
        "Vg": Vg,
        "I_proxy": I_proxy,
        "Ion": float(I_on),
        "Ioff": float(I_off),
        "Vth": Vth,
        "SS": SS,
        "Ion_Ioff": Ion_Ioff,
    }


def _transfer_metrics_from_current(
    Vg: np.ndarray,
    I: np.ndarray,
) -> Dict:
    """Compute Ion/Ioff/SS/Vth/Ion_Ioff from a real current array [A].

    Shared backend for the current-based extractors.  ``I`` must be strictly
    positive (a terminal current magnitude); zero or negative samples are
    clamped to a floor so the log-space SS fit stays finite.  This mirrors the
    proxy-based logic in ``extract_transfer_characteristics`` so the two can be
    compared apples-to-apples.
    """
    I = np.asarray(I, dtype=float)
    I_floor = max(float(np.min(I[I > 0])) if np.any(I > 0) else 1e-30, 1e-30)
    I_safe = np.clip(I, I_floor, None)

    I_on = float(I_safe.max())
    I_off = float(I_safe.min())
    I_th = 1e-3 * I_on
    vth_indices = np.where(I_safe >= I_th)[0]
    Vth = float(Vg[vth_indices[0]]) if len(vth_indices) > 0 else float(Vg[-1])

    if I_on > 0 and I_off > 0:
        log_I = np.log10(I_safe)
        sub_mask = (I_safe < 0.1 * I_on) & (I_safe > I_off * 1.1)
        if sub_mask.sum() >= 2:
            Vg_sub = Vg[sub_mask]
            log_I_sub = log_I[sub_mask]
            coeffs = np.polyfit(log_I_sub, Vg_sub, 1)
            SS = abs(float(coeffs[0])) * 1e3  # mV/dec
        else:
            SS = float("nan")
        Ion_Ioff = float(I_on / max(I_off, 1e-30))
    else:
        SS = float("nan")
        Ion_Ioff = float("nan")

    return {
        "Vg": Vg,
        "Id": I_safe,
        "Ion": I_on,
        "Ioff": I_off,
        "Vth": Vth,
        "SS": SS,
        "Ion_Ioff": Ion_Ioff,
    }


def extract_transfer_characteristics_current(
    simulator,
    sweep_results: List[Dict],
    drain_contact: str = "drain",
    gate_contact: str = "gate",
    direction: str = "auto",
) -> Dict[str, np.ndarray]:
    """Extract Id-Vg from a sweep using the real drain terminal current [A].

    This is the credibility-correct replacement for
    ``extract_transfer_characteristics`` (which used ``n.max()`` as a current
    proxy — audit_recheck.md §3.1 #1, plan0619.md M1/B1).  The drain current
    is obtained by integrating the Scharfetter-Gummel edge flux adjacent to the
    drain contact (``current.contact_current_1d``), so Ion/Ioff/SS/Vth are now
    backed by an actual terminal current rather than a carrier-density peak.

    Parameters
    ----------
    simulator : Simulator
        The simulator that produced ``sweep_results`` (holds the mesh for
        contact masks, mobility fields, grid spacing, and VT).
    sweep_results : list of dict
        Results from ``simulate_sweep``.
    drain_contact : str
        Name of the drain contact whose terminal current is Id.
    gate_contact : str
        Name of the swept gate contact.
    direction : str
        Passed through to ``contact_current_1d`` (``"auto"`` detects the
        contact side from node position).

    Returns
    -------
    dict
        Keys: ``Vg``, ``Id`` (drain current magnitude [A]), ``Ion``, ``Ioff``,
        ``Vth``, ``SS`` (mV/dec), ``Ion_Ioff``.
    """
    Vg = np.array([r["_voltages"][gate_contact] for r in sweep_results])
    # Signed terminal current into the drain contact [A]; take magnitude for
    # log-space metric extraction (a transfer curve is |Id| vs Vg).
    Id_signed = np.array(
        [contact_current_1d(simulator, r, drain_contact, direction=direction)
         for r in sweep_results]
    )
    Id = np.abs(Id_signed)
    out = _transfer_metrics_from_current(Vg, Id)
    out["Id_signed"] = Id_signed
    return out


def compute_energy_delay(
    Vdd: float = 0.7,
    Cox: float = 1e-2,
    W: float = 20e-9,
    L: float = 12e-9,
    Ion: float = 1e24,
    Ioff: float = 1e10,
    Ion_is_current: bool = False,
) -> Dict[str, float]:
    """Estimate switching energy and delay from device parameters.

    Parameters
    ----------
    Vdd : float
        Supply voltage [V].
    Cox : float
        Gate oxide capacitance per unit area [F/m^2].
    W : float
        Device width [m].
    L : float
        Gate length [m].
    Ion : float
        On-state current. By default a carrier density [m^-3] proxy and the
        historical ``1e-19 * Ion * W * L`` estimate is used. If
        ``Ion_is_current=True``, ``Ion`` is treated as a real current [A].
    Ioff : float
        Off-state current/density (same convention as ``Ion``).
    Ion_is_current : bool
        If True, ``Ion``/``Ioff`` are real currents [A] and no density->current
        fudge factor is applied.

    Returns
    -------
    dict
        Keys: ``E_switch`` (switching energy [J]), ``tau_delay`` (intrinsic
        delay [s]), ``EDP`` (energy-delay product [J*s]), ``P_static``
        (static leakage power [W]).
    """
    C_gate = Cox * W * L
    E_switch = 0.5 * C_gate * Vdd * Vdd

    # Intrinsic delay: tau = C_gate * Vdd / I_on
    if Ion_is_current:
        I_on_est = float(Ion)
        I_off_est = float(Ioff)
    else:
        I_on_est = 1e-19 * Ion * W * L  # legacy density->current proxy
        I_off_est = 1e-19 * Ioff * W * L
    if I_on_est > 0:
        tau_delay = C_gate * Vdd / I_on_est
    else:
        tau_delay = float("inf")

    EDP = E_switch * tau_delay
    P_static = Vdd * I_off_est

    return {
        "E_switch": float(E_switch),
        "tau_delay": float(tau_delay),
        "EDP": float(EDP),
        "P_static": float(P_static),
        "C_gate": float(C_gate),
    }


def compare_devices(
    device_results: Dict[str, Dict],
    Vdd: float = 0.7,
) -> str:
    """Generate a comparison table of multiple device simulations.

    Parameters
    ----------
    device_results : dict
        Mapping device name -> transfer characteristics dict (from
        ``extract_transfer_characteristics``).
    Vdd : float
        Supply voltage for energy-delay calculation.

    Returns
    -------
    str
        Formatted markdown table comparing devices.
    """
    header = f"{'Device':<20} {'SS (mV/dec)':<14} {'Ion/Ioff':<14} {'Vth (V)':<10} {'Ion (m^-3)':<16}"
    sep = "-" * len(header)
    lines = [header, sep]

    for name, metrics in device_results.items():
        ss = f"{metrics['SS']:.1f}" if not np.isnan(metrics['SS']) else "N/A"
        lines.append(
            f"{name:<20} {ss:<14} {metrics['Ion_Ioff']:<14.2e} "
            f"{metrics['Vth']:<10.3f} {metrics['Ion']:<16.3e}"
        )

    return "\n".join(lines)
