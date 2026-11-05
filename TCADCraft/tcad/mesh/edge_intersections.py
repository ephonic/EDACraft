"""Coordinate-line intervals for supported material primitives.

These are intersections with a complete coordinate line. They do not describe
cut-face areas, volumes, transport stencils or material-side electric fields.
"""
import math

import numpy as np

from tcad.geometry.shapes import Box, Sphere, Cylinder, Cone, Prism


SUPPORTED_EDGE_SHAPES = (Box, Sphere, Cylinder, Cone, Prism)


def prepare_line_intervals(shape):
    """Return all occupied intervals, including disconnected concave chords.

    Prism classification retains its existing Matplotlib Path boundary policy.
    Only finite simple polygons without holes are accepted. Cone currently has
    the same z-axis restriction as its geometry implementation.
    """
    if type(shape) is Cone:
        return _cone_intervals(shape)
    if type(shape) is Prism:
        return _prism_intervals(shape)
    interval = prepare_line_interval(shape)

    def intervals(point, axis):
        segment = interval(point, axis)
        return [] if segment is None else [segment]

    return intervals


def _cone_intervals(shape):
    if shape.axis != 'z':
        raise ValueError('cone edge integration currently requires the z axis')
    values = [shape.c1, shape.c2, shape.zmin, shape.zmax, shape.rmin, shape.rmax]
    if (any(isinstance(v, (bool, np.bool_)) for v in values)
            or not np.all(np.isfinite(values)) or shape.zmin >= shape.zmax
            or min(shape.rmin, shape.rmax) < 0 or max(shape.rmin, shape.rmax) <= 0):
        raise ValueError('cone requires finite centers, positive span and nonnegative radii')
    bounds = np.asarray(shape.bbox(), dtype=float)
    if not np.all(np.isfinite(bounds)) or np.any(bounds[:, 1] <= bounds[:, 0]):
        raise ValueError('cone bounding spans must be finite and positive')

    def intervals(point, axis):
        if axis == 2:
            distance = math.hypot(float(point[0]) - shape.c1, float(point[1]) - shape.c2)
            if distance > max(shape.rmin, shape.rmax):
                return []
            if distance <= min(shape.rmin, shape.rmax):
                return [(shape.zmin, shape.zmax)]
            t = (distance - shape.rmin) / (shape.rmax - shape.rmin)
            crossing = (1 - t) * shape.zmin + t * shape.zmax
            return ([(crossing, shape.zmax)] if shape.rmax > shape.rmin
                    else [(shape.zmin, crossing)])
        if not shape.zmin <= point[2] <= shape.zmax:
            return []
        t = (point[2] - shape.zmin) / (shape.zmax - shape.zmin)
        radius = (1 - t) * shape.rmin + t * shape.rmax
        center = (shape.c1, shape.c2)
        offset = abs(float(point[1 - axis]) - center[1 - axis])
        if offset > radius:
            return []
        if radius == 0:
            return [(center[axis], center[axis])]
        distance = offset / radius
        half = radius * math.sqrt((1 - distance) * (1 + distance))
        return [(center[axis] - half, center[axis] + half)]

    return intervals


def _prism_intervals(shape):
    vertices = np.asarray(shape.vertices, dtype=float)
    if (vertices.ndim != 2 or vertices.shape[1] != 2 or len(vertices) < 3
            or not np.all(np.isfinite(vertices))):
        raise ValueError('prism requires at least three finite 2D vertices')
    if np.array_equal(vertices[0], vertices[-1]):
        vertices = vertices[:-1]
    bounds = np.asarray(shape.bbox(), dtype=float)
    spans = bounds[:, 1] - bounds[:, 0]
    if (len(vertices) < 3 or not np.all(np.isfinite(bounds))
            or not np.all(np.isfinite(spans)) or np.any(spans <= 0)):
        raise ValueError('prism requires finite positive bounding spans')
    if not np.array_equal(shape._path.vertices, shape.vertices):
        raise ValueError('prism vertices disagree with its cached containment path')
    # Normalize validation coordinates to avoid dimensional cross products
    # overflowing. No tolerance is used to erase thin physical features.
    v = (vertices - bounds[:2, 0]) / spans[:2]
    if len({tuple(p) for p in v}) != len(v):
        raise ValueError('prism polygon must have distinct vertices')

    def orient(a, b, c):
        u, w = b - a, c - a
        return u[0] * w[1] - u[1] * w[0]

    def on_segment(a, b, p):
        return np.all(np.minimum(a, b) <= p) and np.all(p <= np.maximum(a, b))

    edges = list(zip(v, np.roll(v, -1, axis=0)))
    for i, (a, b) in enumerate(edges):
        # Adjacent collinear reversal also overlaps and is not a simple ring.
        c = v[(i + 2) % len(v)]
        if orient(a, b, c) == 0 and (on_segment(a, b, c) or on_segment(b, c, a)):
            raise ValueError('prism polygon has overlapping adjacent edges')
        for j in range(i + 1, len(edges)):
            if j == i + 1 or (i == 0 and j == len(edges) - 1):
                continue
            c, d = edges[j]
            o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
            crosses = ((o1 < 0 < o2 or o2 < 0 < o1)
                       and (o3 < 0 < o4 or o4 < 0 < o3))
            touches = any(o == 0 and on_segment(p, q, r) for o, p, q, r in
                          [(o1, a, b, c), (o2, a, b, d), (o3, c, d, a), (o4, c, d, b)])
            if crosses or touches:
                raise ValueError('prism polygon must be simple without self-intersections')
    if math.fsum(a[0] * b[1] - a[1] * b[0] for a, b in edges) == 0:
        raise ValueError('prism polygon must have positive area')
    polygon_edges = list(zip(vertices, np.roll(vertices, -1, axis=0)))

    def intervals(point, axis):
        if axis == 2:
            inside = shape._path.contains_points(np.asarray([point[:2]], dtype=float))[0]
            return [(shape.zmin, shape.zmax)] if inside else []
        if not shape.zmin <= point[2] <= shape.zmax:
            return []
        transverse = 1 - axis
        fixed = point[transverse]
        cuts = []
        for a, b in polygon_edges:
            if a[transverse] == b[transverse]:
                if fixed == a[transverse]:
                    cuts.extend([a[axis], b[axis]])
            elif min(a[transverse], b[transverse]) <= fixed <= max(a[transverse], b[transverse]):
                t = (fixed - a[transverse]) / (b[transverse] - a[transverse])
                cuts.append((1 - t) * a[axis] + t * b[axis])
        cuts = sorted(set(cuts))
        if len(cuts) < 2:
            return []
        segments = list(zip(cuts[:-1], cuts[1:]))
        probes = np.empty((len(segments), 2))
        probes[:, transverse] = fixed
        probes[:, axis] = [a + (b - a) * .5 for a, b in segments]
        inside = shape._path.contains_points(probes)
        return [segment for segment, occupied in zip(segments, inside) if occupied]

    return intervals


def prepare_line_interval(shape):
    """Validate one primitive and return its interval on an axis-aligned line."""
    bounds = np.asarray(shape.bbox(), dtype=float)
    if (bounds.shape != (3, 2) or not np.all(np.isfinite(bounds))
            or np.any(bounds[:, 1] <= bounds[:, 0])):
        raise ValueError('material edge integration requires finite positive primitive spans')
    if type(shape) is Box:
        def box_line(point, axis):
            if all(bounds[a, 0] <= point[a] <= bounds[a, 1]
                   for a in range(3) if a != axis):
                return tuple(bounds[axis])
            return None
        return box_line
    if type(shape) is Sphere:
        center = (shape.cx, shape.cy, shape.cz)
        radius = shape.r
    elif type(shape) is Cylinder:
        if shape.axis not in 'xyz' or len(shape.axis) != 1:
            raise ValueError('cylinder axis must be x, y or z')
        axial = 'xyz'.index(shape.axis)
        transverse = [a for a in range(3) if a != axial]
        center = [0., 0., 0.]
        center[transverse[0]], center[transverse[1]] = shape.c1, shape.c2
        radius = shape.r
    else:
        raise ValueError('unsupported analytic edge primitive')
    if (not np.all(np.isfinite(center)) or isinstance(radius, (bool, np.bool_))
            or not math.isfinite(radius) or radius <= 0):
        raise ValueError('primitive center and positive radius must be finite')

    def chord(point, axis, radial_axes):
        # Scaling by radius avoids squaring large dimensional coordinates.
        offsets = [abs(float(point[a]) - center[a]) for a in radial_axes]
        if any(d > radius for d in offsets):
            return None
        distance = math.hypot(*(d / radius for d in offsets))
        if distance > 1:
            return None
        half = radius * math.sqrt((1 - distance) * (1 + distance))
        return center[axis] - half, center[axis] + half

    if type(shape) is Sphere:
        return lambda point, axis: chord(point, axis, [a for a in range(3) if a != axis])

    def cylinder_line(point, axis):
        if axis == axial:
            distance = math.hypot(*((float(point[a]) - center[a]) / radius for a in transverse))
            return (shape.zmin, shape.zmax) if distance <= 1 else None
        if not shape.zmin <= point[axial] <= shape.zmax:
            return None
        return chord(point, axis, [a for a in transverse if a != axis])

    return cylinder_line
