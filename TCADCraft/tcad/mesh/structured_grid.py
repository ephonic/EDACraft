"""Structured Cartesian grid, primarily for C++ FDM solver."""

from __future__ import annotations
from typing import Tuple, Dict, Optional
import numpy as np

from .base import Mesh
from tcad.geometry.device_builder import Device


class StructuredGrid(Mesh):
    """
    Uniform Cartesian grid with nx, ny, nz divisions.
    Compatible with the C++ Poisson solver via regular spacing.
    """

    def __init__(
        self,
        bbox: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]],
        nx: int,
        ny: int,
        nz: int,
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
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.dx = (self.xmax - self.xmin) / max(nx - 1, 1)
        self.dy = (self.ymax - self.ymin) / max(ny - 1, 1)
        self.dz = (self.zmax - self.zmin) / max(nz - 1, 1)
        self._build_nodes()

    def _build_nodes(self):
        self.nodes = []
        x = np.linspace(self.xmin, self.xmax, self.nx)
        y = np.linspace(self.ymin, self.ymax, self.ny)
        z = np.linspace(self.zmin, self.zmax, self.nz)
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

    def index(self, i: int, j: int, k: int) -> int:
        return i + self.nx * (j + self.ny * k)

    def ijk(self, idx: int) -> Tuple[int, int, int]:
        i = idx % self.nx
        j = (idx // self.nx) % self.ny
        k = idx // (self.nx * self.ny)
        return i, j, k

    def shape(self) -> Tuple[int, int, int]:
        return self.nx, self.ny, self.nz

    def npts(self) -> int:
        return self.nx * self.ny * self.nz

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
