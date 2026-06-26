"""Cut-cell / immersed-boundary preprocessing for structured grids.

Computes edge-effective permittivity that accounts for material interfaces
cutting through grid edges at arbitrary positions.
"""

from __future__ import annotations
from typing import Dict, Optional, List, Tuple
import numpy as np

from .structured_grid import StructuredGrid
from tcad.geometry.shapes import Shape


def _harmonic_mean(a: float, b: float) -> float:
    s = a + b
    return 2.0 * a * b / s if s > 0 else 0.0


def compute_edge_permittivity(
    grid: StructuredGrid,
    eps: np.ndarray,
    material_id: np.ndarray,
    shapes: Optional[List[Tuple[Shape, int]]] = None,
    n_samples: int = 5,
) -> Dict[str, np.ndarray]:
    """
    Compute effective edge permittivity using distance-weighted harmonic averaging.

    For each grid edge where the two endpoints have different ``material_id``
    values, the code sub-samples ``n_samples`` points along the edge.  If
    ``shapes`` is provided, the material at each sub-sample is determined by
    ``shape.contains()``; otherwise a simple linear crossing at the midpoint
    is assumed (alpha = 0.5).

    The effective permittivity for an edge crossing an interface at fraction
    ``alpha`` (distance from first node divided by edge length) is

        eps_eff = 1 / (alpha/eps1 + (1-alpha)/eps2)

    When both endpoints share the same material, the ordinary harmonic average
    is returned.

    Parameters
    ----------
    grid : StructuredGrid
    eps : np.ndarray, shape (npts,)
        Permittivity at each node.
    material_id : np.ndarray, shape (npts,)
        Integer material identifier at each node.
    shapes : list of (Shape, int), optional
        Geometry definitions used for accurate sub-sample material detection.
        If omitted, alpha = 0.5 is used for all mixed-material edges.
    n_samples : int
        Number of sub-samples per edge for interface detection.

    Returns
    -------
    dict with keys ``x_plus``, ``x_minus``, ``y_plus``, ``y_minus``,
    ``z_plus``, ``z_minus``.  Each value is a float64 array of length
    ``npts``.  Zero entries indicate "not set" (solver falls back to
    harmonic average).
    """
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    npts = grid.npts()
    eps = np.asarray(eps, dtype=float).ravel()
    mat = np.asarray(material_id, dtype=int).ravel()

    edge_eps = {
        "x_plus": np.zeros(npts, dtype=float),
        "x_minus": np.zeros(npts, dtype=float),
        "y_plus": np.zeros(npts, dtype=float),
        "y_minus": np.zeros(npts, dtype=float),
        "z_plus": np.zeros(npts, dtype=float),
        "z_minus": np.zeros(npts, dtype=float),
    }

    def _edge_eff(e1: float, e2: float, alpha: float) -> float:
        if alpha <= 0.0:
            return e1
        if alpha >= 1.0:
            return e2
        return 1.0 / (alpha / e1 + (1.0 - alpha) / e2)

    def _detect_alpha(x_pts, y_pts, z_pts, mat_first):
        """Return approximate interface crossing fraction (0..1)."""
        if shapes is None or n_samples < 2:
            return 0.5
        # Vectorized contains check for all shapes
        mats = np.full(len(x_pts), -1, dtype=int)
        for shape, mid in shapes:
            mask = shape.contains(x_pts, y_pts, z_pts)
            mats[mask] = mid
        # Find where material changes from mat_first
        if mats[0] != mat_first:
            return 0.0
        change = np.where(mats != mat_first)[0]
        if len(change) == 0:
            return 1.0
        idx = change[0]
        if idx == 0:
            return 0.0
        # Linear interpolation between idx-1 and idx
        return (idx - 1) / (n_samples - 1)

    # Helper to avoid massive code duplication
    def _process_edges(dim, stride, coord_arr, plus_key, minus_key):
        """Process edges along a given dimension."""
        nxlim = nx if dim != 0 else nx - 1
        nylim = ny if dim != 1 else ny - 1
        nzlim = nz if dim != 2 else nz - 1

        for k in range(nzlim):
            for j in range(nylim):
                for i in range(nxlim):
                    idx = grid.index(i, j, k)
                    idx2 = idx + stride
                    if mat[idx] == mat[idx2]:
                        edge_eps[plus_key][idx] = _harmonic_mean(eps[idx], eps[idx2])
                        continue

                    # Sub-sample along the edge
                    c1 = coord_arr[i, j, k]
                    if dim == 0:
                        c2 = coord_arr[i + 1, j, k]
                        pts = np.linspace(c1, c2, n_samples)
                        xs, ys, zs = pts, np.full_like(pts, grid.Y[i, j, k]), np.full_like(pts, grid.Z[i, j, k])
                    elif dim == 1:
                        c2 = coord_arr[i, j + 1, k]
                        pts = np.linspace(c1, c2, n_samples)
                        xs, ys, zs = np.full_like(pts, grid.X[i, j, k]), pts, np.full_like(pts, grid.Z[i, j, k])
                    else:
                        c2 = coord_arr[i, j, k + 1]
                        pts = np.linspace(c1, c2, n_samples)
                        xs, ys, zs = np.full_like(pts, grid.X[i, j, k]), np.full_like(pts, grid.Y[i, j, k]), pts

                    alpha = _detect_alpha(xs, ys, zs, mat[idx])
                    eff = _edge_eff(eps[idx], eps[idx2], alpha)
                    edge_eps[plus_key][idx] = eff
                    edge_eps[minus_key][idx2] = eff

    _process_edges(0, 1, grid.X, "x_plus", "x_minus")
    _process_edges(1, nx, grid.Y, "y_plus", "y_minus")
    _process_edges(2, nx * ny, grid.Z, "z_plus", "z_minus")

    return edge_eps
