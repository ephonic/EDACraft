"""Adaptive mesh refinement for structured Cartesian grids.

Refinement strategy:
1. Feature-based pre-refinement: doping gradients, material interfaces, contacts.
2. Solution-based post-refinement: potential / carrier density gradients after a coarse solve.
3. Multi-round adaptive loop: coarse solve -> estimate error -> refine -> prolongate -> re-solve.
"""

from __future__ import annotations
from typing import Tuple, Dict, Optional, List, Callable
import numpy as np

from .structured_grid import StructuredGrid
from .generator import structured_mesh_from_device
from tcad.geometry.device_builder import Device


class AdaptiveRefiner:
    """
    Adaptive refinement controller for structured grids.

    Parameters
    ----------
    device : Device
    base_resolution : tuple
        Mesh spacing (dx, dy, dz) in meters.
    max_level : int
        Maximum refinement level (default 3).
    refinement_ratio : int
        Subdivision factor per level (default 2).
    axis_refinement : dict, optional
        Per-axis maximum refinement multipliers.  Example:
        ``{"x": 4, "y": 2, "z": 2}`` refines x up to 4x, y/z up to 2x.
        If omitted, all axes use ``max_level``.
    directional_thresholds : dict, optional
        Per-axis doping-gradient thresholds [cm^-3 / m].  Example:
        ``{"x": 1e20, "y": 5e19, "z": 5e19}``.
        If omitted, 1e20 is used for all axes.
    """

    def __init__(
        self,
        device: Device,
        base_resolution: Tuple[float, float, float] = (50e-9, 50e-9, 50e-9),
        max_level: int = 3,
        refinement_ratio: int = 2,
        axis_refinement: Optional[Dict[str, int]] = None,
        directional_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.device = device
        self.base_resolution = base_resolution
        self.max_level = max_level
        self.ratio = refinement_ratio
        self.axis_refinement = axis_refinement or {}
        self.directional_thresholds = directional_thresholds or {}

    def generate_feature_refined_mesh(self, level: int = 1, preset: Optional[str] = None) -> StructuredGrid:
        """
        Generate a mesh refined based on device geometry features:
        - PN junctions (doping gradient)
        - Material interfaces (epsilon change)
        - Contact edges

        Parameters
        ----------
        level : int
            Number of refinement passes.
        preset : str, optional
            Device-template preset name.  Supported:
            ``"gaa"``, ``"finfet"``, ``"mosfet"``, ``"pnjunction"``.
            Overrides ``axis_refinement`` and ``directional_thresholds``
            with template-specific defaults.
        """
        if preset is not None:
            self._apply_preset(preset)

        # Start with base mesh
        coarse = structured_mesh_from_device(self.device, resolution=self.base_resolution)

        # Compute feature markers on coarse grid (per-axis)
        markers = self._compute_feature_markers(coarse)

        # Determine local resolutions
        nx, ny, nz = coarse.nx, coarse.ny, coarse.nz
        dx = np.diff(np.linspace(coarse.xmin, coarse.xmax, nx))
        dy = np.diff(np.linspace(coarse.ymin, coarse.ymax, ny))
        dz = np.diff(np.linspace(coarse.zmin, coarse.zmax, nz))

        # Refinement factors per axis
        rx = np.ones(nx - 1, dtype=int)
        ry = np.ones(ny - 1, dtype=int)
        rz = np.ones(nz - 1, dtype=int)

        # Per-axis max ratios
        max_rx = self.ratio ** self.axis_refinement.get("x", self.max_level)
        max_ry = self.ratio ** self.axis_refinement.get("y", self.max_level)
        max_rz = self.ratio ** self.axis_refinement.get("z", self.max_level)

        # Mark cells for refinement (vectorized, per-axis)
        for _ in range(level):
            marked_i, _, _ = np.where(markers["x"])
            if marked_i.size > 0:
                rx[marked_i] *= self.ratio
            _, marked_j, _ = np.where(markers["y"])
            if marked_j.size > 0:
                ry[marked_j] *= self.ratio
            _, _, marked_k = np.where(markers["z"])
            if marked_k.size > 0:
                rz[marked_k] *= self.ratio

        # Clamp to per-axis limits
        rx = np.clip(rx, 1, max_rx)
        ry = np.clip(ry, 1, max_ry)
        rz = np.clip(rz, 1, max_rz)

        # Build new node coordinates
        x_nodes = [coarse.xmin]
        for i in range(nx - 1):
            seg = np.linspace(x_nodes[-1], coarse.X[i + 1, 0, 0], rx[i] + 1)
            x_nodes.extend(seg[1:].tolist())

        y_nodes = [coarse.ymin]
        for j in range(ny - 1):
            seg = np.linspace(y_nodes[-1], coarse.Y[0, j + 1, 0], ry[j] + 1)
            y_nodes.extend(seg[1:].tolist())

        z_nodes = [coarse.zmin]
        for k in range(nz - 1):
            seg = np.linspace(z_nodes[-1], coarse.Z[0, 0, k + 1], rz[k] + 1)
            z_nodes.extend(seg[1:].tolist())

        # Re-sample device fields onto new mesh
        from .base import Node, Mesh
        new_grid = StructuredGrid.__new__(StructuredGrid)
        Mesh.__init__(new_grid)  # Initialize fields, nodes, elements
        new_grid.xmin, new_grid.xmax = coarse.xmin, coarse.xmax
        new_grid.ymin, new_grid.ymax = coarse.ymin, coarse.ymax
        new_grid.zmin, new_grid.zmax = coarse.zmin, coarse.zmax
        new_grid.nx = len(x_nodes)
        new_grid.ny = len(y_nodes)
        new_grid.nz = len(z_nodes)
        new_grid.dx = (new_grid.xmax - new_grid.xmin) / max(new_grid.nx - 1, 1)
        new_grid.dy = (new_grid.ymax - new_grid.ymin) / max(new_grid.ny - 1, 1)
        new_grid.dz = (new_grid.zmax - new_grid.zmin) / max(new_grid.nz - 1, 1)

        x = np.array(x_nodes)
        y = np.array(y_nodes)
        z = np.array(z_nodes)
        new_grid.X, new_grid.Y, new_grid.Z = np.meshgrid(x, y, z, indexing="ij")
        # Node-ordered flat coordinates (i fastest) — Audit §19.
        new_grid._flat_x = new_grid.X.transpose(2, 1, 0).ravel()
        new_grid._flat_y = new_grid.Y.transpose(2, 1, 0).ravel()
        new_grid._flat_z = new_grid.Z.transpose(2, 1, 0).ravel()

        # Vectorized node construction
        idx = np.arange(new_grid.nx * new_grid.ny * new_grid.nz)
        xi = idx % new_grid.nx
        yi = (idx // new_grid.nx) % new_grid.ny
        zi = idx // (new_grid.nx * new_grid.ny)
        new_grid.nodes = [
            Node(int(i), float(x[xi[i]]), float(y[yi[i]]), float(z[zi[i]]))
            for i in idx
        ]
        new_grid.build_node_array()

        # Re-sample fields (node-ordered coords)
        sampled = self.device.sample_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, data in sampled.items():
            new_grid.add_field(name, data)

        contacts = self.device.get_contacts_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, mask in contacts.items():
            new_grid.add_field(f"contact_{name}", mask.astype(float))

        return new_grid

    def _compute_feature_markers(self, grid: StructuredGrid) -> Dict[str, np.ndarray]:
        """Per-axis boolean marker arrays indicating cells to refine."""
        nx, ny, nz = grid.nx, grid.ny, grid.nz
        thresholds = {
            "x": self.directional_thresholds.get("x", 1e20),
            "y": self.directional_thresholds.get("y", 1e20),
            "z": self.directional_thresholds.get("z", 1e20),
        }

        markers = {
            "x": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
            "y": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
            "z": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
        }

        if "doping" in grid.fields:
            doping = grid.to_3d(grid.fields["doping"])
            # x-direction gradient
            gx = np.abs(np.diff(doping, axis=0)) / grid.dx
            gx_c = gx[:, :ny - 1, :nz - 1]
            markers["x"] |= gx_c > thresholds["x"]
            # y-direction gradient
            gy = np.abs(np.diff(doping, axis=1)) / grid.dy
            gy_c = gy[:nx - 1, :, :nz - 1]
            markers["y"] |= gy_c > thresholds["y"]
            # z-direction gradient
            gz = np.abs(np.diff(doping, axis=2)) / grid.dz
            gz_c = gz[:nx - 1, :ny - 1, :]
            markers["z"] |= gz_c > thresholds["z"]

        if "epsilon" in grid.fields:
            eps = grid.fields["epsilon"].reshape(nx, ny, nz)
            de_x = (eps[:-1, :-1, :-1] != eps[1:, :-1, :-1])
            de_y = (eps[:-1, :-1, :-1] != eps[:-1, 1:, :-1])
            de_z = (eps[:-1, :-1, :-1] != eps[:-1, :-1, 1:])
            markers["x"] |= de_x
            markers["y"] |= de_y
            markers["z"] |= de_z

        return markers

    def _apply_preset(self, preset: str) -> None:
        """Apply device-template-specific refinement defaults."""
        presets = {
            "gaa": {
                "axis_refinement": {"x": 2, "y": 4, "z": 4},
                "directional_thresholds": {"x": 1e20, "y": 5e19, "z": 5e19},
            },
            "finfet": {
                "axis_refinement": {"x": 2, "y": 4, "z": 2},
                "directional_thresholds": {"x": 1e20, "y": 5e19, "z": 1e20},
            },
            "mosfet": {
                "axis_refinement": {"x": 2, "y": 2, "z": 4},
                "directional_thresholds": {"x": 1e20, "y": 1e20, "z": 5e19},
            },
            "pnjunction": {
                "axis_refinement": {"x": 4, "y": 2, "z": 2},
                "directional_thresholds": {"x": 5e19, "y": 1e20, "z": 1e20},
            },
        }
        if preset not in presets:
            raise ValueError(f"Unknown preset '{preset}'.  Known: {list(presets.keys())}")
        cfg = presets[preset]
        self.axis_refinement = cfg["axis_refinement"]
        self.directional_thresholds = cfg["directional_thresholds"]

    def _compute_solution_error_markers(
        self,
        grid: StructuredGrid,
        results: Dict[str, np.ndarray],
        level: int,
        fields: Optional[List[str]] = None,
        mode: str = "gradient",
    ) -> Dict[str, np.ndarray]:
        """Per-axis boolean markers indicating cells where the solution
        has large gradients or residuals and needs refinement.

        Parameters
        ----------
        grid : StructuredGrid
            The grid on which the solution was computed.
        results : dict
            Simulation results with keys like "phi", "n", "p".
        level : int
            Current refinement level (used to tighten thresholds).
        fields : list, optional
            Fields to include in error estimation. Default: ["phi", "n", "p"].
        mode : str
            "gradient" (gradient magnitude) or "residual" (discrete Laplacian residual).

        Returns
        -------
        dict
            Per-axis boolean arrays matching `_compute_feature_markers` format.
        """
        nx, ny, nz = grid.nx, grid.ny, grid.nz
        markers = {
            "x": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
            "y": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
            "z": np.zeros((nx - 1, ny - 1, nz - 1), dtype=bool),
        }
        if fields is None:
            fields = ["phi", "n", "p"]

        # Thresholds tighten with refinement level: higher level = more selective
        # so we focus only on the strongest features.
        grad_threshold = 1e-2 * (0.5 ** level)  # relative threshold
        residual_threshold = 1e-4 * (0.5 ** level)

        for fname in fields:
            if fname not in results:
                continue
            data = results[fname].reshape(nx, ny, nz)
            # Normalize to [0, 1] for scale-invariant thresholds
            dmin, dmax = data.min(), data.max()
            span = max(dmax - dmin, 1e-30)
            normed = (data - dmin) / span

            if mode == "gradient":
                gx = np.abs(np.diff(normed, axis=0)) / grid.dx
                gy = np.abs(np.diff(normed, axis=1)) / grid.dy
                gz = np.abs(np.diff(normed, axis=2)) / grid.dz
                # Map to cell centers
                gx_c = gx[:, :ny - 1, :nz - 1]
                gy_c = gy[:nx - 1, :, :nz - 1]
                gz_c = gz[:nx - 1, :ny - 1, :]
                markers["x"] |= gx_c > grad_threshold
                markers["y"] |= gy_c > grad_threshold
                markers["z"] |= gz_c > grad_threshold

            elif mode == "residual":
                # Discrete Laplacian: lap(u)_ijk = sum(u_nbr - u_ijk) / h^2
                lap = np.zeros_like(normed)
                lap[1:-1, :, :] += (normed[:-2, :, :] - 2 * normed[1:-1, :, :] + normed[2:, :, :]) / (grid.dx * grid.dx)
                lap[:, 1:-1, :] += (normed[:, :-2, :] - 2 * normed[:, 1:-1, :] + normed[:, 2:, :]) / (grid.dy * grid.dy)
                lap[:, :, 1:-1] += (normed[:, :, :-2] - 2 * normed[:, :, 1:-1] + normed[:, :, 2:]) / (grid.dz * grid.dz)
                lap_c = np.abs(lap)[:nx - 1, :ny - 1, :nz - 1]
                # Mark cells where residual exceeds threshold in any axis
                flagged = lap_c > residual_threshold
                markers["x"] |= flagged
                markers["y"] |= flagged
                markers["z"] |= flagged

        return markers

    def refine_from_solution(
        self,
        grid: StructuredGrid,
        results: Dict[str, np.ndarray],
        level: int = 1,
        fields: Optional[List[str]] = None,
        mode: str = "gradient",
        combine: str = "union",
    ) -> StructuredGrid:
        """Generate a refined mesh combining feature-based and solution-driven markers.

        Parameters
        ----------
        grid : StructuredGrid
            Current mesh.
        results : dict
            Latest simulation results.
        level : int
            Refinement level.
        fields : list, optional
            Fields for solution error estimation. Default: ["phi", "n", "p"].
        mode : str
            Error estimation mode: "gradient" or "residual".
        combine : str
            How to merge feature and solution markers: "union" (refine if either
            flags the cell) or "intersection" (only if both agree).

        Returns
        -------
        StructuredGrid
            Refined mesh.
        """
        feature_markers = self._compute_feature_markers(grid)
        solution_markers = self._compute_solution_error_markers(grid, results, level, fields, mode)

        if combine == "union":
            combined = {
                ax: feature_markers[ax] | solution_markers[ax]
                for ax in ("x", "y", "z")
            }
        else:
            combined = {
                ax: feature_markers[ax] & solution_markers[ax]
                for ax in ("x", "y", "z")
            }

        return self._refine_from_markers(grid, combined, level)

    def _refine_from_markers(
        self,
        grid: StructuredGrid,
        markers: Dict[str, np.ndarray],
        level: int,
    ) -> StructuredGrid:
        """Internal: apply refinement given pre-computed per-axis markers."""
        nx, ny, nz = grid.nx, grid.ny, grid.nz

        rx = np.ones(nx - 1, dtype=int)
        ry = np.ones(ny - 1, dtype=int)
        rz = np.ones(nz - 1, dtype=int)

        max_rx = self.ratio ** self.axis_refinement.get("x", self.max_level)
        max_ry = self.ratio ** self.axis_refinement.get("y", self.max_level)
        max_rz = self.ratio ** self.axis_refinement.get("z", self.max_level)

        for _ in range(level):
            marked_i, _, _ = np.where(markers["x"])
            if marked_i.size > 0:
                rx[marked_i] *= self.ratio
            _, marked_j, _ = np.where(markers["y"])
            if marked_j.size > 0:
                ry[marked_j] *= self.ratio
            _, _, marked_k = np.where(markers["z"])
            if marked_k.size > 0:
                rz[marked_k] *= self.ratio

        rx = np.clip(rx, 1, max_rx)
        ry = np.clip(ry, 1, max_ry)
        rz = np.clip(rz, 1, max_rz)

        # Build new node coordinates
        x_nodes = [grid.xmin]
        for i in range(nx - 1):
            seg = np.linspace(x_nodes[-1], grid.X[i + 1, 0, 0], rx[i] + 1)
            x_nodes.extend(seg[1:].tolist())

        y_nodes = [grid.ymin]
        for j in range(ny - 1):
            seg = np.linspace(y_nodes[-1], grid.Y[0, j + 1, 0], ry[j] + 1)
            y_nodes.extend(seg[1:].tolist())

        z_nodes = [grid.zmin]
        for k in range(nz - 1):
            seg = np.linspace(z_nodes[-1], grid.Z[0, 0, k + 1], rz[k] + 1)
            z_nodes.extend(seg[1:].tolist())

        # Build new grid
        from .base import Node, Mesh
        new_grid = StructuredGrid.__new__(StructuredGrid)
        Mesh.__init__(new_grid)
        new_grid.xmin, new_grid.xmax = grid.xmin, grid.xmax
        new_grid.ymin, new_grid.ymax = grid.ymin, grid.ymax
        new_grid.zmin, new_grid.zmax = grid.zmin, grid.zmax
        new_grid.nx = len(x_nodes)
        new_grid.ny = len(y_nodes)
        new_grid.nz = len(z_nodes)
        new_grid.dx = (new_grid.xmax - new_grid.xmin) / max(new_grid.nx - 1, 1)
        new_grid.dy = (new_grid.ymax - new_grid.ymin) / max(new_grid.ny - 1, 1)
        new_grid.dz = (new_grid.zmax - new_grid.zmin) / max(new_grid.nz - 1, 1)

        x = np.array(x_nodes)
        y = np.array(y_nodes)
        z = np.array(z_nodes)
        new_grid.X, new_grid.Y, new_grid.Z = np.meshgrid(x, y, z, indexing="ij")
        # Node-ordered flat coordinates (i fastest) — Audit §19.
        new_grid._flat_x = new_grid.X.transpose(2, 1, 0).ravel()
        new_grid._flat_y = new_grid.Y.transpose(2, 1, 0).ravel()
        new_grid._flat_z = new_grid.Z.transpose(2, 1, 0).ravel()

        idx = np.arange(new_grid.nx * new_grid.ny * new_grid.nz)
        xi = idx % new_grid.nx
        yi = (idx // new_grid.nx) % new_grid.ny
        zi = idx // (new_grid.nx * new_grid.ny)
        new_grid.nodes = [
            Node(int(i), float(x[xi[i]]), float(y[yi[i]]), float(z[zi[i]]))
            for i in idx
        ]
        new_grid.build_node_array()

        # Re-sample device fields (node-ordered coords)
        sampled = self.device.sample_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, data in sampled.items():
            new_grid.add_field(name, data)

        contacts = self.device.get_contacts_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, mask in contacts.items():
            new_grid.add_field(f"contact_{name}", mask.astype(float))

        return new_grid

    @staticmethod
    def prolongate(
        coarse: StructuredGrid,
        fine: StructuredGrid,
        field_name: str,
    ) -> np.ndarray:
        """
        Trilinear interpolation of a scalar field from coarse to fine grid.
        Returns flat array aligned with fine grid node ordering (i fastest).
        """
        from scipy.interpolate import RegularGridInterpolator

        if field_name not in coarse.fields:
            raise KeyError(f"Field '{field_name}' not found on coarse grid")

        data = coarse.to_3d(coarse.fields[field_name])  # [i,j,k] — Audit §19
        x = np.linspace(coarse.xmin, coarse.xmax, coarse.nx)
        y = np.linspace(coarse.ymin, coarse.ymax, coarse.ny)
        z = np.linspace(coarse.zmin, coarse.zmax, coarse.nz)

        interpolator = RegularGridInterpolator(
            (x, y, z),
            data,
            bounds_error=False,
            fill_value=0.0,
        )

        fx, fy, fz = fine.flat_coords()  # node-ordered
        pts = np.column_stack((fx, fy, fz))
        return interpolator(pts)

    @staticmethod
    def _prolongate_data(
        coarse: StructuredGrid,
        fine: StructuredGrid,
        data: np.ndarray,
    ) -> np.ndarray:
        """Trilinear interpolation of raw field data from coarse to fine grid."""
        from scipy.interpolate import RegularGridInterpolator

        arr = coarse.to_3d(data)  # [i,j,k] — Audit §19
        x = np.linspace(coarse.xmin, coarse.xmax, coarse.nx)
        y = np.linspace(coarse.ymin, coarse.ymax, coarse.ny)
        z = np.linspace(coarse.zmin, coarse.zmax, coarse.nz)

        interpolator = RegularGridInterpolator(
            (x, y, z),
            arr,
            bounds_error=False,
            fill_value=0.0,
        )

        fx, fy, fz = fine.flat_coords()  # node-ordered
        pts = np.column_stack((fx, fy, fz))
        return interpolator(pts)

    @staticmethod
    def restrict(
        fine: StructuredGrid,
        coarse: StructuredGrid,
        field_name: str,
    ) -> np.ndarray:
        """
        Simple restriction (sampling at coarse nodes) from fine to coarse grid.
        """
        from scipy.interpolate import RegularGridInterpolator

        if field_name not in fine.fields:
            raise KeyError(f"Field '{field_name}' not found on fine grid")

        data = fine.to_3d(fine.fields[field_name])  # [i,j,k] — Audit §19
        x = np.linspace(fine.xmin, fine.xmax, fine.nx)
        y = np.linspace(fine.ymin, fine.ymax, fine.ny)
        z = np.linspace(fine.zmin, fine.zmax, fine.nz)

        interpolator = RegularGridInterpolator(
            (x, y, z),
            data,
            bounds_error=False,
            fill_value=0.0,
        )

        fx, fy, fz = coarse.flat_coords()  # node-ordered
        pts = np.column_stack((fx, fy, fz))
        return interpolator(pts)

    def run_adaptive_solve(
        self,
        simulator,
        max_rounds: int = 5,
        tol: float = 1e-3,
        initial_level: int = 1,
        refine_level: int = 1,
        error_fields: Optional[List[str]] = None,
        error_mode: str = "gradient",
        marker_combine: str = "union",
        verbose: bool = True,
        sim_kwargs: Optional[Dict] = None,
    ) -> Tuple[List[StructuredGrid], List[Dict[str, np.ndarray]], Dict[str, List[float]]]:
        """Multi-round adaptive refinement loop.

        Performs the following cycle up to ``max_rounds`` times:
            solve on current mesh -> estimate solution error -> refine mesh
            -> prolongate solution -> re-solve

        The loop terminates early if the estimated error drops below ``tol``
        or if the mesh size stops growing (no new cells marked).

        Parameters
        ----------
        simulator : Simulator
            Simulator instance (will have its mesh replaced each round).
        max_rounds : int
            Maximum adaptive refinement cycles.
        tol : float
            Convergence tolerance on the relative error reduction.
            The loop stops when the max solution error stops decreasing
            by more than this fraction between rounds.
        initial_level : int
            Initial feature-based refinement level before the first solve.
        refine_level : int
            Additional refinement level applied each adaptive round.
        error_fields : list, optional
            Fields to use for error estimation. Default: ["phi", "n", "p"].
        error_mode : str
            "gradient" or "residual".
        marker_combine : str
            "union" or "intersection" for merging feature + solution markers.
        verbose : bool
            Print progress per round.
        sim_kwargs : dict, optional
            Passed to ``simulator.run()``.

        Returns
        -------
        grids : list of StructuredGrid
            Mesh at each round (including initial).
        results : list of dict
            Simulation results at each round.
        history : dict
            Per-round metrics: npts, max_error, delta_phi.
        """
        if sim_kwargs is None:
            sim_kwargs = {}
        if error_fields is None:
            error_fields = ["phi", "n", "p"]

        grids: List[StructuredGrid] = []
        results: List[Dict[str, np.ndarray]] = []
        history: Dict[str, List[float]] = {"npts": [], "max_error": [], "delta_phi": []}

        # Round 0: feature-based pre-refined mesh + initial solve
        mesh = self.generate_feature_refined_mesh(level=initial_level)
        prev_result = None

        for rnd in range(max_rounds):
            if verbose:
                print(f"[adaptive round {rnd + 1}/{max_rounds}] "
                      f"mesh {mesh.nx}x{mesh.ny}x{mesh.nz} "
                      f"({mesh.npts()} nodes)")

            # Build simulator on current mesh
            from tcad.simulator import Simulator
            sim = Simulator(mesh, temperature=simulator.temperature)
            sim.set_material_from_mesh()

            # Re-apply contacts from the original simulator's mesh
            # (contact names are encoded in the device)
            for name in self.device.contacts:
                shape, voltage = self.device.contacts[name]
                sim.set_contact(name, float(voltage))

            # Propagate previous solution as initial guess
            if prev_result is not None:
                sim._sim.set_initial_guess(
                    prev_result["phi"].astype(np.float64),
                    prev_result["n"].astype(np.float64),
                    prev_result["p"].astype(np.float64),
                )

            # Use PETSc for large meshes, dense for small
            from tcad.core import SolverType
            if mesh.npts() > 2000:
                sim.set_solver_type(SolverType.PETSC, SolverType.PETSC)
            result = sim.run(**sim_kwargs)
            grids.append(mesh)
            results.append(result)

            # Compute error indicator
            error = self._compute_global_error(mesh, result, error_fields, error_mode)
            history["npts"].append(float(mesh.npts()))
            history["max_error"].append(float(error))

            # Check convergence
            if len(history["max_error"]) >= 2:
                prev_err = history["max_error"][-2]
                curr_err = history["max_error"][-1]
                if prev_err > 0:
                    rel_change = abs(prev_err - curr_err) / prev_err
                    if rel_change < tol:
                        if verbose:
                            print(f"  converged: error change {rel_change:.2e} < tol {tol:.2e}")
                        break

            # Compute delta_phi for history
            phi = result["phi"]
            history["delta_phi"].append(float(phi.max() - phi.min()))

            # Check if refinement would actually add nodes
            new_mesh = self.refine_from_solution(
                mesh, result, level=refine_level,
                fields=error_fields, mode=error_mode,
                combine=marker_combine,
            )
            if new_mesh.npts() <= mesh.npts():
                if verbose:
                    print("  stopping: no new nodes added by refinement")
                break

            # Prolongate solution onto the new mesh for initial guess
            prev_result = {}
            for field in ["phi", "n", "p"]:
                if field in result:
                    prev_result[field] = self._prolongate_data(
                        mesh, new_mesh, result[field],
                    )

            mesh = new_mesh

        return grids, results, history

    def _compute_global_error(
        self,
        grid: StructuredGrid,
        results: Dict[str, np.ndarray],
        fields: List[str],
        mode: str,
    ) -> float:
        """Scalar global error indicator from solution fields.

        Returns the L2-norm of normalized gradients across all requested fields,
        giving a single number that decreases as the mesh resolves features.
        """
        nx, ny, nz = grid.nx, grid.ny, grid.nz
        total_error = 0.0

        for fname in fields:
            if fname not in results:
                continue
            data = results[fname].reshape(nx, ny, nz)
            dmin, dmax = data.min(), data.max()
            span = max(dmax - dmin, 1e-30)
            normed = (data - dmin) / span

            if mode == "gradient":
                gx = np.diff(normed, axis=0) / grid.dx
                gy = np.diff(normed, axis=1) / grid.dy
                gz = np.diff(normed, axis=2) / grid.dz
                # L2 norm of gradient magnitudes
                total_error += float(np.sqrt(
                    (gx**2).mean() + (gy**2).mean() + (gz**2).mean()
                ))
            elif mode == "residual":
                lap = np.zeros_like(normed)
                lap[1:-1, :, :] += (normed[:-2, :, :] - 2 * normed[1:-1, :, :] + normed[2:, :, :]) / (grid.dx * grid.dx)
                lap[:, 1:-1, :] += (normed[:, :-2, :] - 2 * normed[:, 1:-1, :] + normed[:, 2:, :]) / (grid.dy * grid.dy)
                lap[:, :, 1:-1] += (normed[:, :, :-2] - 2 * normed[:, :, 1:-1] + normed[:, :, 2:]) / (grid.dz * grid.dz)
                total_error += float(np.sqrt((lap**2).mean()))

        return total_error
