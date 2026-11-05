"""Cut-cell / immersed-boundary preprocessing for structured grids.

Computes edge-effective permittivity that accounts for material interfaces
cutting through grid edges at arbitrary positions.
"""

from __future__ import annotations
from collections.abc import Mapping
import math
from typing import Dict, Optional, List, Tuple
import numpy as np

from .structured_grid import StructuredGrid
from tcad.geometry.shapes import Shape
from .edge_intersections import SUPPORTED_EDGE_SHAPES, prepare_line_intervals


def _harmonic_mean(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    lo, hi = min(a, b), max(a, b)
    return lo / (0.5 + 0.5 * (lo / hi))


def _material_edge_integrator(shapes, eps, mat, material_permittivity):
    """Prepare constant-material primitive line integration; later regions win."""
    regions = []
    for shape, mid in shapes:
        if isinstance(mid, (bool, np.bool_)) or not isinstance(mid, (int, np.integer)) or mid < 0:
            raise ValueError('material ids must be nonnegative integers')
        regions.append((shape, mid, prepare_line_intervals(shape)))
    if material_permittivity is not None and not isinstance(material_permittivity, Mapping):
        raise ValueError('material_permittivity must map material ids to SI permittivity')
    values = {}
    for _, mid, _ in regions:
        samples = eps[mat == mid]
        if material_permittivity is None:
            if samples.size == 0:
                raise ValueError(f'unsampled material {mid} requires material_permittivity')
            value = samples[0]
        else:
            if mid not in material_permittivity:
                raise ValueError(f'missing material_permittivity for material {mid}')
            value = material_permittivity[mid]
        if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or np.iscomplexobj(value):
            raise ValueError('material permittivity must be a finite positive real scalar')
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError('material permittivity must be finite and positive')
        if samples.size and not np.all(samples == value):
            raise ValueError(f'material {mid} requires constant permittivity matching node data')
        values[mid] = value
    if not np.all(np.isin(mat, list(values))):
        raise ValueError('node material ids must belong to the supplied primitive geometry')

    def integrate(start, end, axis, first, last):
        # Split at every primitive entry/exit. Midpoints select the material
        # on each open interval, so endpoint ownership has zero line measure.
        lo, hi = start[axis], end[axis]
        if not np.all(np.isfinite([*start, *end])) or not lo < hi:
            raise ValueError('material edges require finite increasing coordinates')
        cuts = [lo, hi]
        candidates = []
        for shape, mid, intervals in regions:
            for segment in intervals(start, axis):
                if segment[0] < segment[1]:
                    candidates.append((segment, mid))
                    cuts.extend(x for x in segment if lo < x < hi)
        endpoints = np.array([start, end])
        ids = np.full(2, -1, dtype=np.int64)
        for shape, mid, _ in regions:
            inside = shape.contains(endpoints[:, 0], endpoints[:, 1], endpoints[:, 2])
            ids[inside] = mid
        if ids.tolist() != [first, last]:
            raise ValueError('node material ids disagree with primitive painter geometry')
        cuts = sorted(set(cuts))
        lengths, materials = [], []
        for a, b in zip(cuts[:-1], cuts[1:]):
            point = a + (b - a) * .5
            selected = None
            for segment, mid in candidates:
                if segment[0] <= point <= segment[1]:
                    selected = mid
            if selected is None:
                raise ValueError('primitive geometry leaves an uncovered edge interval')
            lengths.append((b - a) / (hi - lo))
            materials.append(values[selected])
        # Normalize by the smallest epsilon to avoid epsilon products and
        # reciprocals overflowing for otherwise representable coefficients.
        scale = min(materials)
        denominator = math.fsum(f * (scale / e) for f, e in zip(lengths, materials))
        with np.errstate(over='ignore', under='ignore'):
            result = float(np.float64(scale) / denominator)
        if not math.isfinite(result) or result <= 0:
            raise ValueError('effective edge permittivity is not representable')
        return result

    return integrate


def compute_edge_permittivity(
    grid: StructuredGrid,
    eps: np.ndarray,
    material_id: np.ndarray,
    shapes: Optional[List[Tuple[Shape, int]]] = None,
    n_samples: int = 5,
    *,
    material_permittivity: Optional[Mapping] = None,
) -> Dict[str, np.ndarray]:
    """
    Compute effective edge permittivity using distance-weighted harmonic averaging.

    In the legacy sampling fallback, for edges with different ``material_id``
    values, the code sub-samples ``n_samples`` points along the edge.  If
    ``shapes`` is provided, the material at each sub-sample is determined by
    ``shape.contains()``; otherwise a simple linear crossing at the midpoint
    is assumed (alpha = 0.5).

    The effective permittivity for an edge crossing an interface at fraction
    ``alpha`` (distance from first node divided by edge length) is

        eps_eff = 1 / (alpha/eps1 + (1-alpha)/eps2)

    With only ``Box``, ``Sphere``, axis-aligned ``Cylinder``, z-axis ``Cone``
    and simple z-extruded ``Prism`` regions, split at every geometric crossing
    and integrate every painted material interval along each edge,
    including layers absent from both edge
    endpoints. Later regions override earlier ones. This is a line coefficient
    correction, not cut-face areas, cut-cell charge/transport, or FE coupling.
    Concave prisms can contribute multiple disconnected intervals. Prism
    boundaries retain the geometry's existing Matplotlib Path membership.
    Other shape types retain the legacy first-crossing sampling approximation.
    Without geometry, use the node-based harmonic mean.

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
    material_permittivity : mapping, optional
        Constant absolute permittivity [F/m] by region id for supported primitives.
        Required for regions with no sampled node. If omitted, infer each
        material's value from its nodes; spatially varying values are rejected.
        Explicit values must agree with the node data. Other shapes currently
        do not use this mapping.

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
    mat_raw = np.asarray(material_id)
    if np.iscomplexobj(mat_raw) or not np.all(np.isfinite(mat_raw)):
        raise ValueError('material ids must be finite integers')
    mat = np.asarray(mat_raw, dtype=int).ravel()
    if eps.size != npts or mat.size != npts:
        raise ValueError('permittivity and material ids must match the grid size')
    if not np.all(mat == mat_raw.ravel()):
        raise ValueError('material ids must be integers')
    if not np.all(np.isfinite(eps)) or np.any(eps < 0):
        raise ValueError('node permittivity must be finite and nonnegative')
    if isinstance(n_samples, (bool, np.bool_)) or not isinstance(n_samples, (int, np.integer)) or n_samples < 2:
        raise ValueError('n_samples must be an integer of at least two')
    shapes = list(shapes) if shapes is not None else None
    exact_material = (_material_edge_integrator(shapes, eps, mat, material_permittivity)
                      if shapes and all(type(shape) in SUPPORTED_EDGE_SHAPES for shape, _ in shapes) else None)

    edge_eps = {
        "x_plus": np.zeros(npts, dtype=float),
        "x_minus": np.zeros(npts, dtype=float),
        "y_plus": np.zeros(npts, dtype=float),
        "y_minus": np.zeros(npts, dtype=float),
        "z_plus": np.zeros(npts, dtype=float),
        "z_minus": np.zeros(npts, dtype=float),
    }

    def _edge_eff(e1: float, e2: float, alpha: float) -> float:
        # alpha is the fraction of the edge occupied by material 1. At a
        # material-side node the interface may coincide with either endpoint:
        # alpha=0 means the edge is wholly material 2, while alpha=1 means it
        # is wholly material 1. Keep these limits consistent with the formula
        # below (the historical implementation had the two sides reversed).
        if alpha <= 0.0:
            return e2
        if alpha >= 1.0:
            return e1
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
                    if exact_material is not None:
                        start = np.array([grid.X[i, j, k], grid.Y[i, j, k], grid.Z[i, j, k]])
                        end = start.copy()
                        end[dim] = (grid.X, grid.Y, grid.Z)[dim][
                            i + (dim == 0), j + (dim == 1), k + (dim == 2)]
                        eff = exact_material(start, end, dim, mat[idx], mat[idx2])
                        edge_eps[plus_key][idx] = eff
                        edge_eps[minus_key][idx2] = eff
                        continue
                    if mat[idx] == mat[idx2]:
                        eff = _harmonic_mean(eps[idx], eps[idx2])
                        edge_eps[plus_key][idx] = eff
                        edge_eps[minus_key][idx2] = eff
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
