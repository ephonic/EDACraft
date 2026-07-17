"""Hysteresis analysis for NC-FET / FeFET characterization."""

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np


def extract_hysteresis(
    forward_results: List[Dict[str, np.ndarray]],
    backward_results: List[Dict[str, np.ndarray]],
    gate_contact_indices: np.ndarray,
    field: str = "phi",
) -> float:
    """Extract hysteresis window (in mV) from forward/backward voltage sweeps.

    Parameters
    ----------
    forward_results : list of dict
        Results from forward voltage sweep (e.g., Vg: 0 -> Vdd -> 0).
    backward_results : list of dict
        Results from backward voltage sweep (same voltage points, opposite direction).
    gate_contact_indices : np.ndarray
        Node indices belonging to the gate contact.
    field : str
        Field to compare. Default "phi" (potential).

    Returns
    -------
    float
        Hysteresis window in millivolts, computed as the maximum absolute
        difference in gate potential between forward and backward sweeps
        at matched voltage points.
    """
    if not forward_results or not backward_results:
        return 0.0

    # Gate potential proxy: average phi at gate contact nodes
    def gate_phi(results):
        gate_phis = []
        for r in results:
            phi_gate = r[field][gate_contact_indices].mean()
            gate_phis.append(phi_gate)
        return np.array(gate_phis)

    phi_fwd = gate_phi(forward_results)
    phi_bwd = gate_phi(backward_results)

    # Match by sweep index (assumes same voltage points in both directions)
    n_match = min(len(phi_fwd), len(phi_bwd))
    delta_phi = np.abs(phi_fwd[:n_match] - phi_bwd[:n_match])

    return float(np.max(delta_phi) * 1000.0)  # convert V -> mV


def classify_device(hysteresis_mv: float) -> str:
    """Classify device based on hysteresis window.

    Parameters
    ----------
    hysteresis_mv : float
        Hysteresis window in millivolts.

    Returns
    -------
    str
        "NC-FET" if hysteresis < 10 mV (negative capacitance regime),
        "FeFET" if hysteresis > 100 mV (ferroelectric memory regime),
        "intermediate" otherwise.
    """
    if hysteresis_mv < 10.0:
        return "NC-FET"
    elif hysteresis_mv > 100.0:
        return "FeFET"
    else:
        return "intermediate"


def extract_ss(results: List[Dict[str, np.ndarray]],
               gate_voltages: np.ndarray,
               drain_current_field: str = "n",
               gate_contact_indices: np.ndarray | None = None) -> float:
    """Extract subthreshold swing (SS) from a voltage sweep.

    SS = d(Vg) / d(log10(Id))  [mV/dec]

    Parameters
    ----------
    results : list of dict
        Simulation results at each gate voltage point.
    gate_voltages : np.ndarray
        Gate voltage values corresponding to each result.
    drain_current_field : str
        Field to use as drain current proxy (default "n" for max electron density).
    gate_contact_indices : np.ndarray, optional
        If provided, use average carrier density at gate contact.

    Returns
    -------
    float
        Minimum subthreshold swing in mV/decade.
    """
    if len(results) < 2:
        return 0.0

    # Extract current proxy
    currents = []
    for r in results:
        if gate_contact_indices is not None:
            i = r[drain_current_field][gate_contact_indices].mean()
        else:
            i = r[drain_current_field].max()
        currents.append(max(i, 1e-30))  # avoid log(0)

    currents = np.array(currents)
    log_i = np.log10(currents)

    # Compute local SS at each pair of adjacent points
    ss_values = []
    for k in range(len(gate_voltages) - 1):
        dv = abs(gate_voltages[k + 1] - gate_voltages[k])
        dlog = abs(log_i[k + 1] - log_i[k])
        if dlog > 1e-6:
            ss = dv / dlog * 1000.0  # mV/dec
            ss_values.append(ss)

    return float(min(ss_values)) if ss_values else 0.0
