"""IR drop analysis for power delivery networks (BSPDN, etc.)."""

from __future__ import annotations
from typing import Dict, Optional
import numpy as np


def compute_conductivity(
    n: np.ndarray,
    p: np.ndarray,
    mu_n: np.ndarray,
    mu_p: np.ndarray,
) -> np.ndarray:
    """Compute electrical conductivity from carrier densities and mobilities.

    sigma = q * (mu_n * n + mu_p * p)  [S/m]

    Parameters
    ----------
    n, p : np.ndarray
        Electron and hole concentrations [m^-3].
    mu_n, mu_p : np.ndarray
        Electron and hole mobilities [m^2/(V*s)].

    Returns
    -------
    np.ndarray
        Conductivity at each node [S/m].
    """
    q = 1.602176634e-19
    return q * (mu_n * n + mu_p * p)


def compute_resistive_network(
    mesh,
    conductivity: np.ndarray,
    dirichlet_bc: Dict[int, float],
    max_iter: int = 100,
    tol: float = 1e-8,
) -> np.ndarray:
    """Solve voltage distribution in a resistive network.

    Solves div(sigma * grad(V)) = 0 with Dirichlet BCs at contacts.
    This is the same discretization as the Poisson solver but with
    conductivity replacing permittivity.

    Parameters
    ----------
    mesh : StructuredGrid
        The simulation mesh.
    conductivity : np.ndarray
        Conductivity at each node [S/m].
    dirichlet_bc : dict
        Mapping of node index -> fixed voltage.
    max_iter : int
        Maximum Jacobi iterations.
    tol : float
        Convergence tolerance.

    Returns
    -------
    np.ndarray
        Voltage distribution at each node [V].
    """
    npts = mesh.npts()
    g = mesh.to_cxx_grid()
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    dx, dy, dz = g["dx"], g["dy"], g["dz"]

    # Initialize voltage: linear interpolation from Dirichlet nodes
    voltage = np.zeros(npts)
    for idx, val in dirichlet_bc.items():
        voltage[idx] = val

    # Jacobi iteration: V_i = sum(sigma_ij * V_j * A_ij) / sum(sigma_ij * A_ij)
    for iteration in range(max_iter):
        v_new = voltage.copy()
        max_delta = 0.0

        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    idx = i + nx * (j + ny * k)
                    if idx in dirichlet_bc:
                        continue

                    sigma_c = conductivity[idx]
                    if sigma_c < 1e-30:
                        continue

                    weighted_sum = 0.0
                    sigma_sum = 0.0

                    # x+ neighbor
                    if i + 1 < nx:
                        nbr = idx + 1
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dx * dx)
                        sigma_sum += sigma_edge / (dx * dx)

                    # x- neighbor
                    if i > 0:
                        nbr = idx - 1
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dx * dx)
                        sigma_sum += sigma_edge / (dx * dx)

                    # y+ neighbor
                    if j + 1 < ny:
                        nbr = idx + nx
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dy * dy)
                        sigma_sum += sigma_edge / (dy * dy)

                    # y- neighbor
                    if j > 0:
                        nbr = idx - nx
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dy * dy)
                        sigma_sum += sigma_edge / (dy * dy)

                    # z+ neighbor
                    if k + 1 < nz:
                        nbr = idx + nx * ny
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dz * dz)
                        sigma_sum += sigma_edge / (dz * dz)

                    # z- neighbor
                    if k > 0:
                        nbr = idx - nx * ny
                        sigma_edge = 2.0 * sigma_c * conductivity[nbr] / max(sigma_c + conductivity[nbr], 1e-30)
                        weighted_sum += sigma_edge * voltage[nbr] / (dz * dz)
                        sigma_sum += sigma_edge / (dz * dz)

                    if sigma_sum > 1e-30:
                        v_new[idx] = weighted_sum / sigma_sum
                        delta = abs(v_new[idx] - voltage[idx])
                        max_delta = max(max_delta, delta)

        voltage = v_new
        if max_delta < tol:
            break

    return voltage


def extract_ir_drop(
    simulator,
    results: Dict[str, np.ndarray],
    mu_n: Optional[np.ndarray] = None,
    mu_p: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute IR drop from simulation results.

    Uses the simulated carrier distribution to compute current density
    J = q(mu_n * n + mu_p * p) * E, then extracts the voltage drop
    along the dominant current path.

    Parameters
    ----------
    simulator : Simulator
        The simulator instance (provides mesh and mobility).
    results : dict
        Simulation results with phi, n, p, Ex, Ey, Ez.
    mu_n, mu_p : np.ndarray, optional
        Mobility arrays. If None, uses simulator defaults.

    Returns
    -------
    dict
        Contains max_ir_drop_mV, avg_ir_drop_mV, max_field_Vcm,
        equivalent_resistance_ohm.
    """
    npts = simulator.mesh.npts()
    n = results["n"]
    p = results["p"]
    Ex = results["Ex"]
    Ey = results["Ey"]
    Ez = results["Ez"]

    # Default mobilities (Si at 300K)
    if mu_n is None:
        mu_n = np.ones(npts) * 0.14  # m^2/(V*s)
    if mu_p is None:
        mu_p = np.ones(npts) * 0.045

    q = 1.602176634e-19
    sigma = q * (mu_n * n + mu_p * p)

    # Current density J = sigma * E
    Jx = sigma * Ex
    Jy = sigma * Ey
    Jz = sigma * Ez
    J_mag = np.sqrt(Jx**2 + Jy**2 + Jz**2)
    E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)

    # Voltage drop: max(phi) - min(phi) along the current path
    phi = results["phi"]
    ir_drop_v = float(np.max(phi) - np.min(phi))
    ir_drop_mv = ir_drop_v * 1000.0

    # Average IR drop (weighted by current density)
    if J_mag.sum() > 0:
        avg_ir_drop_mv = float(np.average(np.abs(phi - phi.mean()) * 1000, weights=J_mag))
    else:
        avg_ir_drop_mv = 0.0

    # Max electric field in V/cm
    max_field = float(np.max(E_mag)) / 100.0  # V/m -> V/cm

    # Equivalent resistance: R = V_drop / I_total
    # I_total = integral of |J| over cross-section (approximate)
    dx = simulator.mesh.to_cxx_grid()["dx"]
    cross_area = dx * dx  # approximate
    i_total = float(J_mag.max() * cross_area) if J_mag.max() > 0 else 1e-30
    eq_resistance = ir_drop_v / i_total if i_total > 0 else 0.0

    return {
        "max_ir_drop_mV": ir_drop_mv,
        "avg_ir_drop_mV": avg_ir_drop_mv,
        "max_field_Vcm": max_field,
        "equivalent_resistance_ohm": eq_resistance,
    }


def compute_pdn_efficiency(vdd: float, ir_drop: float) -> float:
    """Compute power delivery network efficiency.

    Efficiency = (Vdd - IR_drop) / Vdd * 100%

    Parameters
    ----------
    vdd : float
        Supply voltage [V].
    ir_drop : float
        IR drop [V].

    Returns
    -------
    float
        PDN efficiency in percent.
    """
    if vdd <= 0:
        return 0.0
    return float((vdd - abs(ir_drop)) / vdd * 100.0)


def analyze_bspdn(
    simulator,
    results: Dict[str, np.ndarray],
    vdd: float = 0.7,
    via_indices: Optional[np.ndarray] = None,
    rail_indices: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Analyze BSPDN-specific metrics.

    Parameters
    ----------
    simulator : Simulator
    results : dict
        Simulation results.
    vdd : float
        Supply voltage [V].
    via_indices : np.ndarray, optional
        Node indices of the backside via.
    rail_indices : np.ndarray, optional
        Node indices of the backside power rail.

    Returns
    -------
    dict
        IR drop metrics plus PDN efficiency.
    """
    metrics = extract_ir_drop(simulator, results)

    # PDN efficiency
    metrics["pdn_efficiency"] = compute_pdn_efficiency(vdd, metrics["max_ir_drop_mV"] / 1000.0)

    # Via resistance (if via indices provided)
    if via_indices is not None and len(via_indices) > 0:
        via_voltage = results["phi"][via_indices].mean()
        metrics["via_voltage_V"] = float(via_voltage)
        if rail_indices is not None and len(rail_indices) > 0:
            rail_voltage = results["phi"][rail_indices].mean()
            metrics["via_drop_mV"] = float(abs(via_voltage - rail_voltage) * 1000)

    return metrics
