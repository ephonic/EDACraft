"""Structured Cartesian grid, primarily for C++ FDM solver."""

from __future__ import annotations
from typing import Tuple, Dict, Optional
from operator import index as integer_index
import numpy as np

from .base import Mesh
from tcad.geometry.device_builder import Device


class StructuredGrid(Mesh):
    """
    Cartesian tensor grid with nx, ny, nz nodes.
    Optional coordinate axes support nonuniform spacing; singleton axes use
    the full bounding-box span as their extrusion thickness.
    """

    def __init__(
        self,
        bbox: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]],
        nx: int,
        ny: int,
        nz: int,
        *,
        axes=None,
    ):
        super().__init__()
        (self.xmin, self.xmax), (self.ymin, self.ymax), (self.zmin, self.zmax) = bbox
        # B档修复: validate bbox — an inverted or zero-width span silently
        # produces a negative/zero dx that poisons the stencil and reshapes.
        # (nx=1 with a valid span is allowed; the degenerate axis spacing is
        #  then computed but unused since there is only one node.)
        for axis, (lo, hi) in [("x", (self.xmin, self.xmax)),
                               ("y", (self.ymin, self.ymax)),
                               ("z", (self.zmin, self.zmax))]:
            if not (lo < hi):
                raise ValueError(
                    f"StructuredGrid bbox {axis}-span must be strictly increasing "
                    f"(lo < hi); got ({lo}, {hi}).")
        if any(isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer))
               or n < 1 for n in (nx, ny, nz)):
            raise ValueError('grid node counts must be positive integers')
        # NumPy narrow integer multiplication can wrap even for small meshes.
        nx, ny, nz = int(nx), int(ny), int(nz)
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.dx = (self.xmax - self.xmin) / max(nx - 1, 1)
        self.dy = (self.ymax - self.ymin) / max(ny - 1, 1)
        self.dz = (self.zmax - self.zmin) / max(nz - 1, 1)
        self._build_nodes(axes)

    def _validated_axes(self, axes):
        if len(axes) != 3:
            raise ValueError('grid requires three coordinate axes')
        result = []
        for values, count, (lo, hi) in zip(axes, self.shape(),
                [(self.xmin, self.xmax), (self.ymin, self.ymax), (self.zmin, self.zmax)]):
            if np.iscomplexobj(values):
                raise ValueError('grid coordinates must be real')
            a = np.asarray(values, dtype=float)
            with np.errstate(over='ignore', invalid='ignore'):
                steps = np.diff(a) if a.ndim == 1 else np.array([])
            if (a.ndim != 1 or a.size != count or not np.all(np.isfinite(a))
                    or not np.isfinite(hi - lo) or not 0 < hi - lo
                    or np.any(steps <= 0) or not np.all(np.isfinite(steps))):
                raise ValueError('grid axes require finite increasing coordinates matching node counts')
            if count > 1 and (a[0] != lo or a[-1] != hi):
                raise ValueError('active grid axes must cover their bounding-box endpoints')
            if count == 1 and not lo <= a[0] <= hi:
                raise ValueError('singleton grid coordinate must lie inside its bounding span')
            result.append(a.copy())
        return tuple(result)

    def axis_coordinates(self):
        """Return validated tensor coordinates; reject inconsistent mesh caches.

        Active axes include the bounding-box endpoints. These are node-based
        meshes; cell-centred boundary stencils require a separate convention.
        Construct explicit grids with ``axes=(x, y, z)`` instead of changing
        coordinate arrays independently of nodes and sampled fields.
        """
        arrays = (self.X, self.Y, self.Z)
        if any(a.shape != self.shape() for a in arrays):
            raise ValueError('grid coordinate arrays must match the tensor grid shape')
        axes = self._validated_axes((self.X[:, 0, 0], self.Y[0, :, 0], self.Z[0, 0, :]))
        for axis, (a, values, flat) in enumerate(zip(arrays, axes, self.flat_coords())):
            shape = [1, 1, 1]
            shape[axis] = values.size
            if not np.array_equal(a, np.broadcast_to(values.reshape(shape), self.shape())):
                raise ValueError('grid coordinate arrays must form a Cartesian tensor product')
            if not np.array_equal(flat, a.transpose(2, 1, 0).ravel()):
                raise ValueError('grid flat coordinate cache disagrees with tensor coordinates')
        if self.node_coords is None or not np.array_equal(self.node_coords, np.column_stack(self.flat_coords())):
            raise ValueError('grid node coordinate cache disagrees with tensor coordinates')
        return axes

    def _build_nodes(self, axes=None):
        self.nodes = []
        if axes is None:
            axes = (np.linspace(self.xmin, self.xmax, self.nx),
                    np.linspace(self.ymin, self.ymax, self.ny),
                    np.linspace(self.zmin, self.zmax, self.nz))
        x, y, z = self._validated_axes(axes)
        # 3-D coordinate arrays indexed as [i, j, k] (indexing="ij").
        # NOTE: these are kept for direct 3-D indexing (e.g. grid.X[i,j,k]).
        self.X, self.Y, self.Z = np.meshgrid(x, y, z, indexing="ij")
        # Flat coordinate arrays MUST follow the node ordering convention
        # i + nx*(j + ny*k) (i varies fastest), which is what the C++ solver,
        # index()/ijk(), and every postprocess routine assume.  np.meshgrid's
        # C-order ravel instead varies k fastest (i*(ny*nz)+j*nz+k); the two
        # only coincide for pure 1D (ny=nz=1).  Transpose to (nz,ny,nx) so the
        # C-ravel visits i, then j, then k — matching node order.  (Audit §19.)
        self._flat_x = self.X.transpose(2, 1, 0).ravel()
        self._flat_y = self.Y.transpose(2, 1, 0).ravel()
        self._flat_z = self.Z.transpose(2, 1, 0).ravel()
        idx = 0
        for k in range(self.nz):
            for j in range(self.ny):
                for i in range(self.nx):
                    from .base import Node
                    self.nodes.append(Node(idx, float(x[i]), float(y[j]), float(z[k])))
                    idx += 1
        self.build_node_array()

    @staticmethod
    def _checked_index(value, upper: int, name: str) -> int:
        if isinstance(value, (bool, np.bool_)):
            raise TypeError(f'{name} must be an integer index')
        try:
            value = integer_index(value)
        except TypeError:
            raise TypeError(f'{name} must be an integer index') from None
        if not 0 <= value < upper:
            raise IndexError(f'{name} is outside the grid')
        return value

    def index(self, i: int, j: int, k: int) -> int:
        """Map integer coordinates to a node; reject out-of-range axes."""
        i = self._checked_index(i, self.nx, 'i')
        j = self._checked_index(j, self.ny, 'j')
        k = self._checked_index(k, self.nz, 'k')
        return i + self.nx * (j + self.ny * k)

    def ijk(self, idx: int) -> Tuple[int, int, int]:
        """Map a valid integer node index to Cartesian coordinates."""
        idx = self._checked_index(idx, self.npts(), 'node index')
        i = idx % self.nx
        j = (idx // self.nx) % self.ny
        k = idx // (self.nx * self.ny)
        return i, j, k

    def shape(self) -> Tuple[int, int, int]:
        return self.nx, self.ny, self.nz

    def npts(self) -> int:
        return self.nx * self.ny * self.nz

    def control_volumes(self) -> np.ndarray:
        """Node dual volumes in m^3, ordered with x varying fastest.

        Each active axis uses adjacent half-edge lengths, including half
        cells at the domain endpoints. A singleton
        axis represents the full bbox span (the extrusion of a 1D/2D mesh).
        These volumes integrate nodal multilinear fields, rather than counting
        boundary nodes as full interior cells.
        """
        widths = []
        for coords, (lo, hi, count) in zip(self.axis_coordinates(),
                ((self.xmin, self.xmax, self.nx),
                 (self.ymin, self.ymax, self.ny),
                 (self.zmin, self.zmax, self.nz))):
            span = hi - lo
            if not np.isfinite(span) or span <= 0:
                raise ValueError("control volumes require finite positive bbox spans")
            if count == 1:
                widths.append(np.array([span], dtype=float))
            else:
                half = np.diff(coords) * .5
                w = np.r_[half, 0.] + np.r_[0., half]
                widths.append(w)
        wx, wy, wz = widths
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            volumes = (wz[:, None, None] * wy[None, :, None]
                       * wx[None, None, :]).ravel()
        if not np.all(np.isfinite(volumes)) or np.any(volumes <= 0):
            raise ValueError("control volumes overflowed or underflowed")
        return volumes

    def create_device_fields(self, device: Device) -> Dict[str, np.ndarray]:
        """
        Sample device material properties onto this grid.
        Returns flat arrays aligned with node ordering (i + nx*(j + ny*k)).
        """
        sampled = device.sample_on_grid(self._flat_x, self._flat_y, self._flat_z)
        return sampled

    def contact_masks(self, device: Device) -> Dict[str, np.ndarray]:
        """Return flat boolean masks for each contact, in node order."""
        return device.get_contacts_on_grid(self._flat_x, self._flat_y, self._flat_z)

    # --- Coordinate/field ordering helpers (Audit §19) ---------------------
    # Node order is i + nx*(j + ny*k) (i fastest).  The 3-D arrays X/Y/Z are
    # indexed [i,j,k].  These helpers convert between the node-ordered flat
    # representation (used by fields and the C++ solver) and the [i,j,k]
    # 3-D representation, without relying on ravel/reshape order assumptions.
    def flat_coords(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (x, y, z) flat coordinate arrays in node order."""
        return self._flat_x, self._flat_y, self._flat_z

    def to_3d(self, flat: np.ndarray) -> np.ndarray:
        """Reshape a node-ordered flat array to a 3-D [i,j,k] array."""
        nz, ny, nx = self.nz, self.ny, self.nx
        return np.asarray(flat).reshape((nz, ny, nx)).transpose(2, 1, 0)

    def from_3d(self, arr3d: np.ndarray) -> np.ndarray:
        """Flatten a 3-D [i,j,k] array to node order (i fastest)."""
        return np.asarray(arr3d).transpose(2, 1, 0).ravel()
    # ------------------------------------------------------------------------

    def to_cxx_grid(self):
        """Return parameters needed by C++ Grid3D struct."""
        return {
            "nx": self.nx,
            "ny": self.ny,
            "nz": self.nz,
            "dx": self.dx,
            "dy": self.dy,
            "dz": self.dz,
        }
