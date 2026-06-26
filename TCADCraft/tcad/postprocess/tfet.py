"""TFET-specific postprocessing and analysis."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


def extract_btb_tbt_current(
    results: Dict[str, np.ndarray],
    mesh,
    A_kane: float = 3.1e21,
    B_kane: float = 2.0e7,
    D: int = 2,
) -> float:
    """Extract BTBT generation current from simulation results.

    Computes the total BTBT generation rate integrated over the device:
        G_BTBT = A * |E|^D * exp(-B / |E|)
        I_BTBT = q * integral(G_BTBT * dV)

    Parameters
    ----------
    results : dict
        Simulation results with Ex, Ey, Ez fields.
    mesh : StructuredGrid
        The simulation mesh for volume element calculation.
    A_kane : float
        Kane A coefficient [cm^-3 s^-1 V^-D].
    B_kane : float
        Kane B coefficient [V/m].
    D : int
        Kane exponent (2 for direct tunneling).

    Returns
    -------
    float
        Total BTBT current [A/m] (per unit width for 2D, total for 3D).
    """
    Ex = results.get("Ex", np.zeros(mesh.npts()))
    Ey = results.get("Ey", np.zeros(mesh.npts()))
    Ez = results.get("Ez", np.zeros(mesh.npts()))

    E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)

    # Kane's model: G = A * |E|^D * exp(-B / |E|) [cm^-3 s^-1]
    # Avoid division by zero
    E_safe = np.maximum(E_mag, 1e4)  # minimum field to avoid exp(-inf)
    G_btb = A_kane * E_safe**D * np.exp(-B_kane / E_safe)  # cm^-3 s^-1
    G_btb[E_mag < 1e4] = 0.0  # zero BTBT for negligible fields

    # Integrate over volume: each cell has volume = dx * dy * dz
    dx = mesh.to_cxx_grid()["dx"]
    dy = mesh.to_cxx_grid()["dy"]
    dz = mesh.to_cxx_grid()["dz"]
    dV = dx * dy * dz  # m^3

    # Convert G from cm^-3 s^-1 to m^-3 s^-1
    G_btb_m = G_btb * 1e6

    # Total BTBT generation rate
    total_G = G_btb_m.sum() * dV  # s^-1

    q = 1.602176634e-19
    return float(q * total_G)


def extract_tfet_metrics(
    sweep_results: List[Dict[str, np.ndarray]],
    gate_contact: str = "gate",
    Vdd: float = 0.5,
) -> Dict[str, float]:
    """Extract TFET-specific performance metrics from a Vg sweep.

    Parameters
    ----------
    sweep_results : list of dict
        Results from simulate_sweep with Vg values.
    gate_contact : str
        Name of the gate contact.
    Vdd : float
        Supply voltage [V].

    Returns
    -------
    dict
        TFET metrics: point_SS (minimum point SS), avg_SS (average SS over
        decade), V_on (turn-on voltage), I_on (current at Vdd), I_off
        (current at Vg=0), energy_per_switch.
    """
    Vg = np.array([r["_voltages"][gate_contact] for r in sweep_results])
    # Use max electron density as current proxy (since we don't have terminal current)
    I_proxy = np.array([r["n"].max() for r in sweep_results])

    # Clamp to avoid log(0)
    I_safe = np.maximum(I_proxy, 1e-30)

    # Point SS at each Vg: dVg / d(log10(I))
    point_ss = np.full_like(Vg, np.nan)
    for k in range(len(Vg) - 1):
        dV = abs(Vg[k + 1] - Vg[k])
        dlog = abs(np.log10(I_safe[k + 1]) - np.log10(I_safe[k]))
        if dlog > 1e-6:
            ss = dV / dlog * 1000.0  # mV/dec
            point_ss[k] = ss

    # Minimum point SS (best subthreshold behavior)
    valid_ss = point_ss[~np.isnan(point_ss)]
    min_ss = float(valid_ss.min()) if len(valid_ss) > 0 else float("nan")

    # Average SS over 3 decades (from I_off to I_off * 1000)
    I_off = float(I_safe[Vg <= 0].max()) if (Vg <= 0).any() else float(I_safe[0])
    I_on = float(I_safe[-1])  # current at highest Vg

    # Energy per switch: 0.5 * C_ox * Vdd^2 (approximate)
    # For a typical TFET: C_ox ~ 1e-2 F/m^2, W*L ~ (20nm)^2
    C_ox = 1e-2  # F/m^2 (typical for 1.5nm EOT)
    area = 20e-9 * 20e-9
    E_switch = 0.5 * C_ox * area * Vdd * Vdd

    # Turn-on voltage: Vg where current reaches 1% of I_on
    I_threshold = 0.01 * I_on
    v_on_indices = np.where(I_safe >= I_threshold)[0]
    V_on = float(Vg[v_on_indices[0]]) if len(v_on_indices) > 0 else float(Vg[-1])

    # I_on/I_off ratio
    Ion_Ioff = float(I_on / max(I_off, 1e-30))

    return {
        "min_SS": min_ss,
        "avg_point_SS": float(np.nanmean(valid_ss)) if len(valid_ss) > 0 else float("nan"),
        "V_on": V_on,
        "I_on": I_on,
        "I_off": I_off,
        "Ion_Ioff": Ion_Ioff,
        "E_switch": E_switch,
        "Vdd": Vdd,
    }


def compare_tfet_vs_mosfet(
    tfet_metrics: Dict[str, float],
    mosfet_metrics: Dict[str, float],
    Vdd_tfet: float = 0.3,
    Vdd_mosfet: float = 0.7,
) -> str:
    """Generate a comparison table between TFET and MOSFET.

    Parameters
    ----------
    tfet_metrics : dict
        Output from extract_tfet_metrics for TFET.
    mosfet_metrics : dict
        Output from extract_tfet_metrics for MOSFET (reuse function).
    Vdd_tfet : float
        TFET supply voltage [V].
    Vdd_mosfet : float
        MOSFET supply voltage [V].

    Returns
    -------
    str
        Formatted comparison table.
    """
    lines = [
        "| Metric              | TFET (Vdd=%.2fV) | MOSFET (Vdd=%.2fV) | Advantage |"
        % (Vdd_tfet, Vdd_mosfet),
        "|---------------------|-----------------|---------------------|-----------|",
    ]

    # Min SS
    tfet_ss = tfet_metrics.get("min_SS", float("nan"))
    mosfet_ss = mosfet_metrics.get("min_SS", float("nan"))
    ss_line = f"| min SS (mV/dec)     | {tfet_ss:.1f}{' ' if not np.isnan(tfet_ss) else 'N/A'} | {mosfet_ss:.1f}{' ' if not np.isnan(mosfet_ss) else 'N/A'} |"
    if not np.isnan(tfet_ss) and not np.isnan(mosfet_ss):
        ss_line += f" {'TFET' if tfet_ss < mosfet_ss else 'MOSFET'} |"
    else:
        ss_line += " - |"
    lines.append(ss_line)

    # I_on/I_off
    tfet_ratio = tfet_metrics.get("Ion_Ioff", 0)
    mosfet_ratio = mosfet_metrics.get("Ion_Ioff", 0)
    lines.append(
        f"| Ion/Ioff            | {tfet_ratio:.2e} | {mosfet_ratio:.2e} | "
        f"{'TFET' if tfet_ratio > mosfet_ratio else 'MOSFET'} |"
    )

    # Energy per switch
    tfet_E = tfet_metrics.get("E_switch", 0)
    mosfet_E = mosfet_metrics.get("E_switch", 0)
    energy_ratio = tfet_E / max(mosfet_E, 1e-30)
    lines.append(
        f"| E_switch (J)        | {tfet_E:.2e} | {mosfet_E:.2e} | "
        f"{'TFET %.1fx' % (mosfet_E/max(tfet_E,1e-30)) if energy_ratio < 1 else 'MOSFET'} |"
    )

    # V_on (turn-on voltage)
    tfet_von = tfet_metrics.get("V_on", 0)
    mosfet_von = mosfet_metrics.get("V_on", 0)
    lines.append(
        f"| V_on (V)            | {tfet_von:.3f} | {mosfet_von:.3f} | "
        f"{'TFET' if abs(tfet_von) < abs(mosfet_von) else 'MOSFET'} |"
    )

    return "\n".join(lines)
