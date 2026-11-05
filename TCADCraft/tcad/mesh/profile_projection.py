"""Conservative projection of an explicitly piecewise-linear 1-D profile.

Only the supplied representation is preserved. Sparse samples do not establish
the inventory of an unprovided full mesh. Project densities and material energy
densities separately; averaging temperatures does not conserve carrier energy.
"""
import numpy as np


def _vector(value, name):
    raw = np.asarray(value)
    if raw.ndim != 1 or raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):
        raise ValueError(name + ' must be a finite real vector')
    return np.array(raw, dtype=np.longdouble, copy=True)


def piecewise_linear_cell_averages(x_m, nodal_values, cell_edges_m):
    """Return owned longdouble cell averages over exactly the source support.

    Coordinates and edges must be strictly increasing, with identical support
    endpoints. Signed values are allowed. No extrapolation, renormalization or
    global-inventory fitting is performed. Integrals use local overlap lengths,
    avoiding subtraction of large cumulative integrals for narrow target cells.
    For constant cross-section extrusions, these are also volume averages.
    They are not a general 2-D/3-D mesh transfer or an energy-to-temperature codec.
    """
    x = _vector(x_m, 'source coordinates')
    y = _vector(nodal_values, 'nodal values')
    edges = _vector(cell_edges_m, 'target edges')
    if len(x) < 2 or y.shape != x.shape or len(edges) < 2:
        raise ValueError('aligned source samples and at least one target cell required')
    with np.errstate(over='ignore', invalid='ignore'):
        dx, widths = np.diff(x), np.diff(edges)
    if any(np.any(~np.isfinite(a)) or np.any(a <= 0) for a in (dx, widths)):
        raise ValueError('finite positive source and target intervals required')
    if not np.array_equal(x[[0, -1]], edges[[0, -1]]):
        raise ValueError('identical physical support endpoints required')
    result = np.empty(len(widths), dtype=np.longdouble)
    i = 0
    with np.errstate(over='ignore', invalid='ignore'):
        for j, width in enumerate(widths):
            left, end = edges[j], edges[j + 1]
            total = correction = np.longdouble(0)
            while left < end:
                right = min(end, x[i + 1])
                a = (left - x[i]) / dx[i]
                b = (right - x[i]) / dx[i]
                ya = (1 - a) * y[i] + a * y[i + 1]
                yb = (1 - b) * y[i] + b * y[i + 1]
                term = ((right - left) / width) * (ya / 2 + yb / 2)
                adjusted = term - correction
                following = total + adjusted
                correction = (following - total) - adjusted
                total = following
                left = right
                if right == x[i + 1] and i < len(dx) - 1:
                    i += 1
            result[j] = total
    if not np.all(np.isfinite(result)):
        raise ValueError('projected averages cannot be represented')
    return result
