"""3D primitive shapes using implicit functions and bounding-box tests."""

from __future__ import annotations
import numpy as np
from typing import Protocol, Tuple


class Shape(Protocol):
    """Protocol for a 3D geometric primitive."""

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Return boolean mask of points inside the shape."""
        ...

    def bbox(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """Return ((xmin, xmax), (ymin, ymax), (zmin, zmax))."""
        ...


class Box:
    """Axis-aligned box."""

    def __init__(self, xmin: float, xmax: float, ymin: float, ymax: float, zmin: float, zmax: float):
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        return (
            (x >= self.xmin) & (x <= self.xmax) &
            (y >= self.ymin) & (y <= self.ymax) &
            (z >= self.zmin) & (z <= self.zmax)
        )

    def bbox(self):
        return (self.xmin, self.xmax), (self.ymin, self.ymax), (self.zmin, self.zmax)


class Sphere:
    """Sphere."""

    def __init__(self, cx: float, cy: float, cz: float, r: float):
        self.cx, self.cy, self.cz = cx, cy, cz
        self.r = r

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        dx = x - self.cx
        dy = y - self.cy
        dz = z - self.cz
        return dx * dx + dy * dy + dz * dz <= self.r * self.r

    def bbox(self):
        return (
            (self.cx - self.r, self.cx + self.r),
            (self.cy - self.r, self.cy + self.r),
            (self.cz - self.r, self.cz + self.r),
        )


class Cylinder:
    """Axis-aligned cylinder."""

    def __init__(self, axis: str, c1: float, c2: float, zmin: float, zmax: float, r: float):
        """
        axis: 'x', 'y', or 'z' — the axis of the cylinder.
        c1, c2: center coordinates in the two transverse directions.
        zmin, zmax: extent along the cylinder axis.
        r: radius.
        """
        self.axis = axis.lower()
        self.c1, self.c2 = c1, c2
        self.zmin, self.zmax = zmin, zmax
        self.r = r

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        if self.axis == "z":
            dx = x - self.c1
            dy = y - self.c2
            dz_ok = (z >= self.zmin) & (z <= self.zmax)
            return (dx * dx + dy * dy <= self.r * self.r) & dz_ok
        elif self.axis == "y":
            dx = x - self.c1
            dz = z - self.c2
            dy_ok = (y >= self.zmin) & (y <= self.zmax)
            return (dx * dx + dz * dz <= self.r * self.r) & dy_ok
        elif self.axis == "x":
            dy = y - self.c1
            dz = z - self.c2
            dx_ok = (x >= self.zmin) & (x <= self.zmax)
            return (dy * dy + dz * dz <= self.r * self.r) & dx_ok
        else:
            raise ValueError(f"Invalid axis: {self.axis}")

    def bbox(self):
        if self.axis == "z":
            return (
                (self.c1 - self.r, self.c1 + self.r),
                (self.c2 - self.r, self.c2 + self.r),
                (self.zmin, self.zmax),
            )
        elif self.axis == "y":
            return (
                (self.c1 - self.r, self.c1 + self.r),
                (self.zmin, self.zmax),
                (self.c2 - self.r, self.c2 + self.r),
            )
        else:  # x
            return (
                (self.zmin, self.zmax),
                (self.c1 - self.r, self.c1 + self.r),
                (self.c2 - self.r, self.c2 + self.r),
            )


class Cone:
    """Axis-aligned cone (truncated or full)."""

    def __init__(self, axis: str, c1: float, c2: float, zmin: float, zmax: float, rmin: float, rmax: float):
        self.axis = axis.lower()
        self.c1, self.c2 = c1, c2
        self.zmin, self.zmax = zmin, zmax
        self.rmin, self.rmax = rmin, rmax

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        if self.axis == "z":
            dx = x - self.c1
            dy = y - self.c2
            dz_ok = (z >= self.zmin) & (z <= self.zmax)
            # Linear interpolation of radius
            t = np.zeros_like(z)
            denom = self.zmax - self.zmin
            if denom != 0:
                t = (z - self.zmin) / denom
            r_allowed = self.rmin + t * (self.rmax - self.rmin)
            return (dx * dx + dy * dy <= r_allowed * r_allowed) & dz_ok
        else:
            raise NotImplementedError("Cone only implemented for z-axis")

    def bbox(self):
        r = max(self.rmin, self.rmax)
        if self.axis == "z":
            return (
                (self.c1 - r, self.c1 + r),
                (self.c2 - r, self.c2 + r),
                (self.zmin, self.zmax),
            )
        raise NotImplementedError


class Prism:
    """Extruded 2D polygon along z-axis."""

    def __init__(self, polygon_vertices: np.ndarray, zmin: float, zmax: float):
        """
        polygon_vertices: Nx2 array of (x, y) vertices in order.
        """
        self.vertices = np.asarray(polygon_vertices)
        self.zmin, self.zmax = zmin, zmax
        # Cache Path object for repeated contains() calls
        from matplotlib.path import Path
        self._path = Path(self.vertices)

    def contains(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        points = np.column_stack((x.ravel(), y.ravel()))
        inside = self._path.contains_points(points).reshape(x.shape)
        dz_ok = (z >= self.zmin) & (z <= self.zmax)
        return inside & dz_ok

    def bbox(self):
        xs = self.vertices[:, 0]
        ys = self.vertices[:, 1]
        return (
            (float(xs.min()), float(xs.max())),
            (float(ys.min()), float(ys.max())),
            (self.zmin, self.zmax),
        )
