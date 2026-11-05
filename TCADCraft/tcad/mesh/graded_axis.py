"""Cell-centred coordinate grading with exact exterior half-cell supports."""

from __future__ import annotations

import numpy as np


def graded_cell_centers(start, stop, cells, *, boundary_cell_width, reverse=False):
    """Return centres of geometrically graded intervals in ``[start, stop]``.

    The first two intervals have the requested width. The last two also have
    equal widths. Between them, widths follow one geometric progression,
    determined by the span. Thus a native zero-D exterior half cell reaches
    the physical boundary exactly. ``reverse=True`` pins the upper end.

    Adjacent layers can be joined without moving their interface by using
    the same interval width on its two sides. These are coordinate axes for
    the native cell-centred convention, not endpoint-based StructuredGrid
    axes or cut-cell volumes. Interior solver volumes remain dual volumes.

    At least four cells and a span greater than twice the pinned width are
    required. Coordinates must preserve the intended interval widths to
    relative accuracy 1e-9; excessive grading raises ValueError.
    """
    if (isinstance(cells, (bool, np.bool_))
            or not isinstance(cells, (int, np.integer)) or cells < 4):
        raise ValueError('cells must be an integer of at least four')
    if not isinstance(reverse, (bool, np.bool_)):
        raise ValueError('reverse must be boolean')
    scalars = (start, stop, boundary_cell_width)
    if any(np.iscomplexobj(v) or np.ndim(v) != 0
           or np.asarray(v).dtype.kind not in 'iuf'
           or isinstance(v, (bool, np.bool_)) for v in scalars):
        raise ValueError('bounds and boundary_cell_width must be real scalars')
    try:
        start, stop, width = map(float, scalars)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('bounds and boundary_cell_width must be real scalars') from exc
    with np.errstate(over='ignore', invalid='ignore'):
        span = stop - start
    if not (np.isfinite([start, stop, width, span]).all()
            and width > 0 and span > 0 and width < span / 2):
        raise ValueError('finite increasing bounds require 0 < width < span/2')

    # Repeated end exponents preserve both exterior half-cell locations.
    powers = np.r_[0., np.arange(cells - 2, dtype=float), float(cells - 3)]
    target = np.log(span) - np.log(width)

    def log_sum(log_ratio):
        terms = powers * log_ratio
        peak = terms.max()
        with np.errstate(under='ignore'):
            return peak + np.log(np.exp(terms - peak).sum())

    low, high = -750., 750.
    for _ in range(120):
        mid = (low + high) / 2
        if log_sum(mid) < target:
            low = mid
        else:
            high = mid
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        widths = np.exp(np.log(width) + powers * ((low + high) / 2))
        if reverse:
            widths = widths[::-1]
        faces = np.r_[start, start + np.cumsum(widths)]
        faces[-1] = stop
        centers = faces[:-1] + np.diff(faces) / 2
        gaps = np.diff(centers)
        supports = (centers[0] - gaps[0] / 2,
                    centers[-1] + gaps[-1] / 2)
    tolerance = 64 * float(np.finfo(float).eps) * max(abs(start), abs(stop), span)
    if (not np.isfinite(centers).all() or not np.all(widths > 0)
            or not np.all(np.diff(faces) > 0) or not np.all(gaps > 0)
            or not start < centers[0] < centers[-1] < stop
            or np.max(np.abs(np.asarray(supports) - [start, stop])) > tolerance):
        raise ValueError('graded coordinates are not representable at this scale')
    # Merely increasing centres can hide percent-level distortion of tiny
    # intervals near a large coordinate offset. Reconstruct their faces from
    # the returned coordinates, independently of the cumulative sum above.
    recovered = np.empty(cells + 1)
    recovered[0] = start
    for i, point in enumerate(centers):
        recovered[i + 1] = point + (point - recovered[i])
    if np.any(np.abs((np.diff(recovered) - widths) / widths) > 1e-9):
        raise ValueError('grading loses relative interval-width accuracy')
    return centers
