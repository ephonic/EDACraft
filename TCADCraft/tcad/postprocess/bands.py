"""D1 band-diagram analyzer (plan0619.md §D1).

Reconstructs the conduction/valence band edges and quasi-Fermi levels from a
solved result, on a 1-D cutline along x (the transport direction).  The band
picture is the primary "why is this candidate good" explanatory artifact:

    Evac(x) = -phi(x)                  [eV]  (vacuum level; phi in V)
    Ec(x)   = Evac(x) - chi(x)         [eV]  (conduction band = vacuum - affinity)
    Ev(x)   = Ec(x) - Eg(x)            [eV]  (valence band)
    Efn(x)  = Ec(x) + VT * ln(n / Nc)  [eV]  (electron quasi-Fermi, Boltzmann)
    Efp(x)  = Ev(x) - VT * ln(p / Nv)  [eV]  (hole quasi-Fermi, Boltzmann)

``chi`` is now sampled onto the mesh by ``Device.sample_on_grid`` (M5 step 1),
so ``band_edges`` reads it from ``mesh.fields["chi"]``.  An optional ``device``
fallback re-samples ``chi``/``Eg`` from regions for meshes built before the
``chi`` field existed.

The 1-D cutline helper ``cutline_x_at_jk`` is shared with
``current.contact_current_1d`` (the same fixed-(j,k) x-line pattern), so both
the terminal-current and band-picture views see the same slice of the device.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# 1-D cutline helper (shared with current.contact_current_1d)
# ---------------------------------------------------------------------------

def cutline_x_at_jk(mesh, j: int = 0, k: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(x_coords, flat_indices)`` for the x-axis line at fixed (j, k).

    Node ordering is ``idx = i + nx*(j + ny*k)`` (``StructuredGrid.index``), so
    the x-line at fixed (j, k) is ``[i + nx*(j + ny*k) for i in range(nx)]``.
    Both arrays have length ``nx``.
    """
    nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
    if not (0 <= j < ny and 0 <= k < nz):
        raise IndexError(f"(j,k)=({j},{k}) out of mesh bounds ny={ny} nz={nz}")
    line = np.array([i + nx * (j + ny * k) for i in range(nx)], dtype=np.int64)
    # x-coordinate of each node on the line (node-ordered flat coords — §19).
    fx = mesh.flat_coords()[0]
    x = fx[line]
    return x, line


# ---------------------------------------------------------------------------
# Band edges (full 3-D fields)
# ---------------------------------------------------------------------------

@dataclass
class BandEdges:
    """Per-node band edges and quasi-Fermi levels [eV], flat arrays of length N."""
    Evac: np.ndarray   # vacuum level = -phi
    Ec: np.ndarray     # conduction band = Evac - chi
    Ev: np.ndarray     # valence band = Ec - Eg
    Efn: np.ndarray    # electron quasi-Fermi (Boltzmann)
    Efp: np.ndarray    # hole quasi-Fermi (Boltzmann)

    def as_dict(self) -> Dict[str, np.ndarray]:
        return {"Evac": self.Evac, "Ec": self.Ec, "Ev": self.Ev,
                "Efn": self.Efn, "Efp": self.Efp}


def _resolve_chi_eg(simulator, device=None) -> Tuple[np.ndarray, np.ndarray]:
    """Per-node chi [eV] and Eg [eV], from mesh fields or device fallback."""
    mesh = simulator.mesh
    n = mesh.npts()
    Eg = np.asarray(mesh.fields.get("Eg", np.full(n, 1.12)), dtype=float)
    if "chi" in mesh.fields:
        chi = np.asarray(mesh.fields["chi"], dtype=float)
    elif device is not None:
        # Re-sample chi from the device regions (fallback for pre-M5 meshes).
        chi = np.zeros(n, dtype=float)
        fx, fy, fz = mesh.flat_coords()  # node-ordered — §19
        for region in device.regions:
            mask = region.shape.contains(fx, fy, fz)
            chi[mask] = region.material.chi
    else:
        chi = np.full(n, 4.05, dtype=float)  # Si default
    return chi, Eg


def band_edges(simulator, result: Dict, device=None) -> BandEdges:
    """Reconstruct band edges + quasi-Fermi levels from a solved result.

    Parameters
    ----------
    simulator : Simulator
        Holds the mesh (for chi/Eg/Nc/Nv) and ``VT``.
    result : dict
        A single solve() result (phi, n, p).
    device : Device, optional
        Fallback for ``chi`` if the mesh lacks the field (pre-M5 meshes).
    """
    mesh = simulator.mesh
    VT = simulator.VT
    phi = np.asarray(result["phi"], dtype=float)        # [V]
    n = np.asarray(result["n"], dtype=float)            # [m^-3]
    p = np.asarray(result["p"], dtype=float)            # [m^-3]
    chi, Eg = _resolve_chi_eg(simulator, device)
    Nc = np.asarray(mesh.fields.get("Nc", np.full(mesh.npts(), 2.8e19)),
                    dtype=float) * 1e6                  # cm^-3 -> m^-3
    Nv = np.asarray(mesh.fields.get("Nv", np.full(mesh.npts(), 1.04e19)),
                    dtype=float) * 1e6

    Evac = -phi                                          # [eV]
    Ec = Evac - chi                                      # [eV]
    Ev = Ec - Eg                                         # [eV]
    # Boltzmann quasi-Fermi levels; clamp densities to avoid log(0).
    n_safe = np.maximum(n, 1e0)
    p_safe = np.maximum(p, 1e0)
    Efn = Ec + VT * np.log(n_safe / Nc)                  # [eV]
    Efp = Ev - VT * np.log(p_safe / Nv)                  # [eV]
    return BandEdges(Evac=Evac, Ec=Ec, Ev=Ev, Efn=Efn, Efp=Efp)


# ---------------------------------------------------------------------------
# 1-D band diagram (cutline)
# ---------------------------------------------------------------------------

@dataclass
class BandCutline:
    """1-D band diagram along x at fixed (j, k)."""
    x: np.ndarray       # [m]
    Evac: np.ndarray    # [eV]
    Ec: np.ndarray      # [eV]
    Ev: np.ndarray      # [eV]
    Efn: np.ndarray     # [eV]
    Efp: np.ndarray     # [eV]

    def as_dict(self) -> Dict[str, np.ndarray]:
        return {"x": self.x, "Evac": self.Evac, "Ec": self.Ec, "Ev": self.Ev,
                "Efn": self.Efn, "Efp": self.Efp}


def band_diagram_1d(simulator, result: Dict, j: int = 0, k: int = 0,
                    device=None) -> BandCutline:
    """1-D band diagram along the x cutline at fixed (j, k).

    Convenience wrapper around :func:`band_edges` + :func:`cutline_x_at_jk`
    returning the band edges restricted to one x-line (the transport
    direction), which is the standard "band diagram" plot.
    """
    x, line = cutline_x_at_jk(simulator.mesh, j, k)
    be = band_edges(simulator, result, device=device)
    return BandCutline(
        x=x,
        Evac=be.Evac[line], Ec=be.Ec[line], Ev=be.Ev[line],
        Efn=be.Efn[line], Efp=be.Efp[line],
    )
