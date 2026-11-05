"""Local quadratic reconstruction of one-dimensional finite-volume averages.

The polynomial in cell i is a[i] + b[i]*xi + c[i]*(xi**2 - 1/12),
where xi=(x-midpoint_i)/width_i. Every slope/curvature update therefore
preserves that cell's supplied average. This does not change a solver's
flux, Poisson, stored energy or initial state automatically.
"""
import numpy as np


def _vector(value, name):
    raw = np.asarray(value)
    if raw.ndim != 1 or raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):
        raise ValueError(name + ' must be a finite real vector')
    return np.array(raw, dtype=np.longdouble, copy=True)


def _minimum(a, b, c):
    value = min(a-b/2+c/6, a+b/2+c/6)
    if c > 0:
        stationary = -b/(2*c)
        if abs(stationary) < np.longdouble('.5'):
            value = min(value, a+b*stationary+c*(stationary**2-np.longdouble(1)/12))
    return value


def cell_average_quadratic_coefficients(cell_edges_m, cell_averages, *, lower_bound=None):
    """Return owned read-only longdouble (mean, linear, quadratic) coefficients.

    Three contiguous cell averages determine each polynomial, using one-sided
    stencils at the two ends. Nonuniform positive cell widths are supported.
    At least three cells are required; no extrapolated or ghost data are used.
    Optional scalar/per-cell lower bounds contract slope and curvature together
    about the unchanged mean, enforcing the bound over the WHOLE closed cell,
    including an interior quadratic minimum. An average below its bound is
    rejected rather than modified. No upper bound or monotonicity is implied.

    These are Cartesian/constant-cross-section volume averages. Reconstruct
    conserved particle and energy fields separately; a positive kinetic energy
    alone does not prove FD thermodynamic admissibility. A solver must still
    validate its EOS, contact/Poisson coupling and shared face conservation.
    """
    edges = _vector(cell_edges_m, 'cell edges')
    means = _vector(cell_averages, 'cell averages')
    if len(means) < 3 or len(edges) != len(means)+1:
        raise ValueError('at least three aligned cells required')
    with np.errstate(over='ignore', invalid='ignore'):
        widths = np.diff(edges)
    if np.any(~np.isfinite(widths)) or np.any(widths <= 0):
        raise ValueError('finite strictly increasing cell edges required')
    bound = None
    if lower_bound is not None:
        raw = np.asarray(lower_bound)
        if raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):
            raise ValueError('finite real scalar or per-cell lower bound required')
        try:
            bound = np.array(np.broadcast_to(raw, means.shape), dtype=np.longdouble, copy=True)
        except ValueError:
            raise ValueError('scalar or per-cell lower bound required') from None
        if np.any(means < bound):
            raise ValueError('cell average below lower bound')
    result = np.zeros((len(means), 3), dtype=np.longdouble)
    result[:, 0] = means
    eps = np.finfo(np.longdouble).eps
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        for i in range(len(means)):
            start = min(max(i-1, 0), len(means)-3)
            neighbors = [j for j in range(start, start+3) if j != i]
            rows = []
            for j in neighbors:
                # Subtract a nearby edge before introducing the midpoint.
                left = (edges[j]-edges[i])/widths[i]-np.longdouble('.5')
                right = (edges[j+1]-edges[i])/widths[i]-np.longdouble('.5')
                rows.append(((left+right)/2, (left*left+left*right+right*right)/3-np.longdouble(1)/12))
            a, b = rows[0]; c, d = rows[1]
            det = a*d-b*c
            if not np.isfinite(det) or abs(det) <= 64*eps*(abs(a*d)+abs(b*c)):
                raise ValueError('ill-conditioned quadratic reconstruction stencil')
            one, two = means[neighbors[0]]-means[i], means[neighbors[1]]-means[i]
            linear, quadratic = (one*d-b*two)/det, (a*two-one*c)/det
            if not np.isfinite(linear) or not np.isfinite(quadratic):
                raise ValueError('quadratic coefficients cannot be represented')
            if bound is not None:
                minimum = _minimum(means[i], linear, quadratic)
                if not np.isfinite(minimum):
                    raise ValueError('quadratic range cannot be represented')
                if minimum < bound[i]:
                    theta = (means[i]-bound[i])/(means[i]-minimum)
                    theta = min(np.longdouble(1), max(np.longdouble(0), theta))*(1-8*eps)
                    linear *= theta; quadratic *= theta
                    # Preserve the exact mean even in extreme rounding cases.
                    if _minimum(means[i], linear, quadratic) < bound[i]:
                        linear = quadratic = np.longdouble(0)
            result[i, 1:] = linear, quadratic
    result.setflags(write=False)
    return result


def evaluate_cell_quadratics(coefficients, xi):
    """Evaluate all cells at scalar or vector normalized positions in [-.5,.5].

    Scalar xi returns one value per cell; vector xi returns (cells, points).
    The normalized coordinate avoids global-coordinate cancellation and does
    not require the input/output geometry to be identical across cells.
    """
    raw = np.asarray(coefficients)
    if raw.ndim != 2 or raw.shape[1] != 3 or raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):
        raise ValueError('finite real (cells,3) coefficients required')
    coord = np.asarray(xi)
    if coord.ndim > 1 or coord.dtype.kind not in 'fiu' or not np.all(np.isfinite(coord)) or np.any(abs(coord) > .5):
        raise ValueError('finite scalar/vector cell coordinates in [-.5,.5] required')
    co = np.array(raw, dtype=np.longdouble, copy=True)
    x = np.array(coord, dtype=np.longdouble, copy=True)
    if coord.ndim:
        co = co[:, :, None]
    with np.errstate(over='ignore', invalid='ignore'):
        value = co[:, 0]+co[:, 1]*x+co[:, 2]*(x*x-np.longdouble(1)/12)
    if np.any(~np.isfinite(value)):
        raise ValueError('reconstructed values cannot be represented')
    return value
