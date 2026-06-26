"""NDR (Negative Differential Resistance) tunnel diode postprocessing."""

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np


def extract_btb_current(
    results: Dict[str, np.ndarray],
    mesh,
    A_kane: float = 3.1e21,
    B_kane: float = 2.0e7,
    D: int = 2,
) -> float:
    """Extract BTBT generation current from simulation results.

    Same approach as TFET: integrate Kane's BTBT generation rate over volume.
    """
    Ex = results.get("Ex", np.zeros(mesh.npts()))
    Ey = results.get("Ey", np.zeros(mesh.npts()))
    Ez = results.get("Ez", np.zeros(mesh.npts()))

    E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)

    E_safe = np.maximum(E_mag, 1e4)
    G_btb = A_kane * E_safe**D * np.exp(-B_kane / E_safe)
    G_btb[E_mag < 1e4] = 0.0

    dx = mesh.to_cxx_grid()["dx"]
    dy = mesh.to_cxx_grid()["dy"]
    dz = mesh.to_cxx_grid()["dz"]
    dV = dx * dy * dz

    G_btb_m = G_btb * 1e6

    total_G = G_btb_m.sum() * dV

    q = 1.602176634e-19
    return float(q * total_G)


def extract_ndr_metrics(
    sweep_results: List[Dict[str, np.ndarray]],
    contact_name: str = "cathode",
) -> Dict[str, float]:
    """Extract NDR tunnel diode metrics from a voltage sweep.

    Parameters
    ----------
    sweep_results : list of dict
        Results from sequential simulations with increasing forward bias.
    contact_name : str
        Name of the biased contact (typically "cathode").

    Returns
    -------
    dict
        Keys: Vp (peak voltage), Ip (peak current proxy),
        Vv (valley voltage), Iv (valley current proxy),
        PVR (peak-valley ratio = Ip/Iv),
        V_ndr_start, V_ndr_end (NDR region voltage bounds).
    """
    V = np.array([r["_voltages"][contact_name] for r in sweep_results])
    # Use max electron density as current proxy
    I = np.array([r["n"].max() for r in sweep_results])

    I_safe = np.maximum(I, 1e-30)

    # Find peak: maximum current
    peak_idx = int(np.argmax(I_safe))
    Vp = float(V[peak_idx])
    Ip = float(I_safe[peak_idx])

    # Find valley: minimum current after the peak
    if peak_idx < len(V) - 1:
        post_peak = I_safe[peak_idx + 1:]
        valley_offset = int(np.argmin(post_peak))
        valley_idx = peak_idx + 1 + valley_offset
        Vv = float(V[valley_idx])
        Iv = float(I_safe[valley_idx])
    else:
        Vv = float(V[-1])
        Iv = float(I_safe[-1])

    # Peak-valley ratio
    PVR = Ip / max(Iv, 1e-30)

    # NDR region: where dI/dV < 0
    dIdV = np.diff(I_safe) / np.maximum(np.diff(V), 1e-12)
    ndr_mask = dIdV < 0
    ndr_indices = np.where(ndr_mask)[0]

    if len(ndr_indices) > 0:
        V_ndr_start = float(V[ndr_indices[0]])
        V_ndr_end = float(V[ndr_indices[-1] + 1])
    else:
        V_ndr_start = float("nan")
        V_ndr_end = float("nan")

    return {
        "Vp": Vp,
        "Ip": Ip,
        "Vv": Vv,
        "Iv": Iv,
        "PVR": PVR,
        "V_ndr_start": V_ndr_start,
        "V_ndr_end": V_ndr_end,
        "has_ndr": V_ndr_start != V_ndr_start or (V_ndr_end > V_ndr_start),
    }


def plot_ndr_curve(
    sweep_results: List[Dict[str, np.ndarray]],
    contact_name: str = "cathode",
    ax=None,
):
    """Plot I-V curve with NDR region highlighted.

    Parameters
    ----------
    sweep_results : list of dict
        Results from sequential simulations.
    contact_name : str
        Name of the biased contact.
    ax : matplotlib Axes, optional
        Axes to plot on. Creates new figure if None.
    """
    import matplotlib.pyplot as plt

    V = np.array([r["_voltages"][contact_name] for r in sweep_results])
    I = np.array([r["n"].max() for r in sweep_results])

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(V, I, "b-o", markersize=3, label="I-V")

    # Highlight NDR region
    metrics = extract_ndr_metrics(sweep_results, contact_name)
    if metrics["has_ndr"] and not np.isnan(metrics["V_ndr_start"]):
        mask = (V >= metrics["V_ndr_start"]) & (V <= metrics["V_ndr_end"])
        ax.plot(V[mask], I[mask], "r-o", markersize=4, linewidth=2, label="NDR region")

    # Mark peak and valley
    ax.plot(metrics["Vp"], metrics["Ip"], "g^", markersize=10, label=f"Peak (Vp={metrics['Vp']:.3f}V)")
    ax.plot(metrics["Vv"], metrics["Iv"], "rv", markersize=10, label=f"Valley (Vv={metrics['Vv']:.3f}V)")

    ax.set_xlabel("Voltage (V)")
    ax.set_ylabel("Current proxy (n_max [m$^{-3}$])")
    ax.set_title("Tunnel Diode I-V Characteristic")
    ax.legend()
    ax.grid(True, alpha=0.3)

    return ax
