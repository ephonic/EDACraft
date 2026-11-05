"""Adaptive mesh refinement for structured Cartesian grids.

Refinement strategy:
1. Feature-based pre-refinement: doping gradients and sampled material interfaces.
2. Solution-based post-refinement: potential / carrier density gradients after a coarse solve.
3. Multi-round adaptive loop: coarse solve -> estimate error -> refine -> prolongate -> re-solve.
"""

from __future__ import annotations
from typing import Tuple, Dict, Optional, List, Callable
import numpy as np

from .structured_grid import StructuredGrid
from .generator import structured_mesh_from_device
from tcad.geometry.device_builder import Device


def _coordinate_metrics(grid):
    coordinates = grid.axis_coordinates()
    spacing = []
    for axis, coords in enumerate(coordinates):
        shape = [1, 1, 1]
        shape[axis] = len(coords) - 1
        spacing.append(np.diff(coords).reshape(shape))
    return coordinates, spacing


def _cell_shape(grid):
    """Keep one logical extrusion cell on each singleton axis."""
    return tuple(max(n - 1, 1) for n in grid.shape())


def _incident_cells(flags, edge_axis=None):
    """Map nodal/edge flags to every incident tensor cell, including outer faces."""
    cells = flags
    for axis in range(3):
        if axis == edge_axis or cells.shape[axis] == 1:
            continue
        low, high = [slice(None)] * 3, [slice(None)] * 3
        low[axis], high[axis] = slice(None, -1), slice(1, None)
        cells = cells[tuple(low)] | cells[tuple(high)]
    return cells


def _nonnegative_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(value)


def _coordinate_laplacian(data, coordinates, spacing):
    """Differences of edge slopes over adjacent half-edge widths."""
    lap = np.zeros_like(data)
    for axis, coords in enumerate(coordinates):
        if len(coords) < 3:
            continue
        h = np.diff(coords)
        shape = [1, 1, 1]
        shape[axis] = len(coords) - 2
        widths = (.5 * h[:-1] + .5 * h[1:]).reshape(shape)
        slopes = np.diff(data, axis=axis) / spacing[axis]
        interior = [slice(None)] * 3
        interior[axis] = slice(1, -1)
        lap[tuple(interior)] += np.diff(slopes, axis=axis) / widths
    return lap


class AdaptiveRefiner:
    """
    Adaptive refinement controller for structured grids.

    Parameters
    ----------
    device : Device
    base_resolution : tuple
        Mesh spacing (dx, dy, dz) in meters.
    max_level : int
        Maximum subdivision exponent per refinement call (default 3).
        This is not a cumulative limit across adaptive rounds.
    refinement_ratio : int
        Subdivision factor per level (default 2).
    axis_refinement : dict, optional
        Per-axis maximum subdivision exponents per call. Example:
        ``{"x": 4, "y": 2, "z": 2}`` with ratio=2 allows factors 16, 4, 4.
        If omitted, all axes use ``max_level``.
    directional_thresholds : dict, optional
        Per-axis doping-gradient thresholds [cm^-3 / m].  Example:
        ``{"x": 1e20, "y": 5e19, "z": 5e19}``.
        If omitted, 1e20 is used for all axes.
    base_shape : tuple(int, int, int), optional
        Explicit base node counts. Set inactive axes to 1 for an extruded
        1-D/2-D mesh; otherwise base_resolution determines all node counts.
    """

    def __init__(
        self,
        device: Device,
        base_resolution: Tuple[float, float, float] = (50e-9, 50e-9, 50e-9),
        max_level: int = 3,
        refinement_ratio: int = 2,
        axis_refinement: Optional[Dict[str, int]] = None,
        directional_thresholds: Optional[Dict[str, float]] = None,
        base_shape: Optional[Tuple[int, int, int]] = None,
    ):
        self.device = device
        self.base_resolution = base_resolution
        self.max_level = _nonnegative_integer(max_level, 'max_level')
        self.ratio = _nonnegative_integer(refinement_ratio, 'refinement_ratio')
        if self.ratio < 2:
            raise ValueError('refinement_ratio must be at least 2')
        self.axis_refinement = axis_refinement or {}
        self.directional_thresholds = directional_thresholds or {}
        for key, value in self.axis_refinement.items():
            if key not in ('x', 'y', 'z'):
                raise ValueError('axis_refinement keys must be x, y or z')
            _nonnegative_integer(value, 'axis_refinement level')
        if base_shape is not None:
            if len(base_shape) != 3 or any(_nonnegative_integer(n, 'base_shape count') < 1 for n in base_shape):
                raise ValueError('base_shape requires three positive integer node counts')
            base_shape = tuple(int(n) for n in base_shape)
        self.base_shape = base_shape

    def generate_feature_refined_mesh(self, level: int = 1, preset: Optional[str] = None) -> StructuredGrid:
        """
        Generate a mesh refined based on device geometry features:
        - PN junctions (doping gradient)
        - Material interfaces (epsilon change)

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

        level = _nonnegative_integer(level, 'level')
        counts = dict(zip(('nx', 'ny', 'nz'), self.base_shape)) if self.base_shape else {}
        coarse = structured_mesh_from_device(self.device, resolution=self.base_resolution, **counts)
        return self._refine_from_markers(coarse, self._compute_feature_markers(coarse), level)

    def _compute_feature_markers(self, grid: StructuredGrid) -> Dict[str, np.ndarray]:
        """Doping/interface edge flags on logical cells; inactive axes stay false."""
        coordinates, spacing = _coordinate_metrics(grid)
        markers = {a: np.zeros(_cell_shape(grid), dtype=bool) for a in 'xyz'}
        for axis, name in enumerate('xyz'):
            if len(coordinates[axis]) == 1:
                continue
            if 'doping' in grid.fields:
                doping = grid.to_3d(grid.fields['doping'])
                gradient = np.abs(np.diff(doping, axis=axis)) / spacing[axis]
                flags = gradient > self.directional_thresholds.get(name, 1e20)
                markers[name] |= _incident_cells(flags, edge_axis=axis)
            if 'epsilon' in grid.fields:
                epsilon = grid.to_3d(grid.fields['epsilon'])
                flags = np.diff(epsilon, axis=axis) != 0
                markers[name] |= _incident_cells(flags, edge_axis=axis)
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
        _nonnegative_integer(level, 'level')
        if mode not in ('gradient', 'residual'):
            raise ValueError("mode must be 'gradient' or 'residual'")
        coordinates, spacing = _coordinate_metrics(grid)
        markers = {a: np.zeros(_cell_shape(grid), dtype=bool) for a in 'xyz'}
        if fields is None:
            fields = ['phi', 'n', 'p']
        # These remain derivative heuristics in physical coordinates, not
        # equation residuals or certified error bounds.
        grad_threshold = 1e-2 * (0.5 ** level)
        residual_threshold = 1e-4 * (0.5 ** level)
        for fname in fields:
            if fname not in results:
                continue
            data = grid.to_3d(results[fname])
            dmin, dmax = data.min(), data.max()
            normed = (data - dmin) / max(dmax - dmin, 1e-30)
            if mode == 'gradient':
                for axis, name in enumerate('xyz'):
                    if len(coordinates[axis]) > 1:
                        flags = np.abs(np.diff(normed, axis=axis)) / spacing[axis] > grad_threshold
                        markers[name] |= _incident_cells(flags, edge_axis=axis)
            else:
                lap = _coordinate_laplacian(normed, coordinates, spacing)
                flagged = _incident_cells(np.abs(lap) > residual_threshold)
                for axis, name in enumerate('xyz'):
                    if len(coordinates[axis]) > 1:
                        markers[name] |= flagged
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
        if combine not in ('union', 'intersection'):
            raise ValueError("combine must be 'union' or 'intersection'")
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
        level = _nonnegative_integer(level, 'level')
        coords = grid.axis_coordinates()
        axes = []
        for axis, name in enumerate('xyz'):
            marker = np.asarray(markers[name], dtype=bool)
            if marker.shape != _cell_shape(grid):
                raise ValueError('markers must match the logical cell shape (singleton axes have one cell)')
            if len(coords[axis]) == 1:
                if marker.any():
                    raise ValueError('singleton axes cannot be marked for subdivision')
                axes.append(coords[axis])
                continue
            marked = marker.any(axis=tuple(a for a in range(3) if a != axis))
            exponent = min(level, self.axis_refinement.get(name, self.max_level))
            factors = np.where(marked, self.ratio ** exponent, 1)
            nodes = [coords[axis][0]]
            for i, factor in enumerate(factors):
                segment = np.linspace(coords[axis][i], coords[axis][i+1], int(factor)+1)
                nodes.extend(segment[1:].tolist())
            axes.append(np.asarray(nodes))
        bbox = ((grid.xmin, grid.xmax), (grid.ymin, grid.ymax), (grid.zmin, grid.zmax))
        new_grid = StructuredGrid(bbox, *(len(a) for a in axes), axes=axes)
        new_grid._material_shapes = [
            (region.shape, rid)
            for rid, region in enumerate(self.device.regions)
        ]
        new_grid._material_permittivity = {
            rid: region.material.epsilon_r * 8.854187817e-12
            for rid, region in enumerate(self.device.regions)
        }

        # Re-sample device fields (node-ordered coords)
        sampled = self.device.sample_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, data in sampled.items():
            new_grid.add_field(name, data)

        contacts = self.device.get_contacts_on_grid(new_grid._flat_x, new_grid._flat_y, new_grid._flat_z)
        for name, mask in contacts.items():
            new_grid.add_field(f"contact_{name}", mask.astype(float))

        from tcad.configuration import remember_device_fields
        remember_device_fields(new_grid)

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
        x, y, z = coarse.axis_coordinates()

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
        x, y, z = coarse.axis_coordinates()

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
        x, y, z = fine.axis_coordinates()

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
            Configuration template, left unchanged. Each round inherits its
            explicit physics, boundary and solver settings on a refined mesh.
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
        sim_kwargs = dict(sim_kwargs)
        # Refinement is a numerical re-solve at one physical bias, not a clock
        # advancement of FE/trap/reliability history.
        sim_kwargs.setdefault('physical_step', False)
        if error_fields is None:
            error_fields = ["phi", "n", "p"]

        grids: List[StructuredGrid] = []
        results: List[Dict[str, np.ndarray]] = []
        history: Dict[str, List[float]] = {"npts": [], "max_error": [], "delta_phi": []}

        # Round 0: feature-based pre-refined mesh + initial solve
        mesh = self._refine_from_markers(simulator.mesh,
            self._compute_feature_markers(simulator.mesh), initial_level)
        prev_result = None

        for rnd in range(max_rounds):
            if verbose:
                print(f"[adaptive round {rnd + 1}/{max_rounds}] "
                      f"mesh {mesh.nx}x{mesh.ny}x{mesh.nz} "
                      f"({mesh.npts()} nodes)")

            # Build simulator on current mesh
            sim = simulator.clone_on_mesh(mesh)

            # Re-apply contacts from the original simulator's mesh
            # (contact names are encoded in the device)
            for name in self.device.contacts:
                if name not in sim._contact_voltages:
                    shape, voltage = self.device.contacts[name]
                    sim.set_contact(name, float(voltage))

            # Propagate previous solution as initial guess
            if prev_result is not None:
                sim._sim.set_initial_guess(
                    prev_result["phi"].astype(np.float64),
                    prev_result["n"].astype(np.float64),
                    prev_result["p"].astype(np.float64),
                )

            result = sim.run(**sim_kwargs)
            grids.append(mesh)
            results.append(result)

            # Compute error indicator
            error = self._compute_global_error(mesh, result, error_fields, error_mode)
            history["npts"].append(float(mesh.npts()))
            history["max_error"].append(float(error))
            phi = result["phi"]
            history["delta_phi"].append(float(phi.max() - phi.min()))

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

            if rnd + 1 == max_rounds:
                break

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

        Returns RMS normalized derivatives in physical coordinates. This is
        a heuristic indicator, not an error bound; it need not decrease under
        refinement. Singleton axes have no derivative contribution.
        """
        if mode not in ('gradient', 'residual'):
            raise ValueError("mode must be 'gradient' or 'residual'")
        coordinates, spacing = _coordinate_metrics(grid)
        total_error = 0.0

        for fname in fields:
            if fname not in results:
                continue
            # B档修复: to_3d (node order i fastest), not plain reshape (scrambles
            # i,j,k in 3D — corrupts gradient/error markers and convergence metric).
            data = grid.to_3d(results[fname])
            dmin, dmax = data.min(), data.max()
            span = max(dmax - dmin, 1e-30)
            normed = (data - dmin) / span

            if mode == "gradient":
                slopes = [np.diff(normed, axis=a) / spacing[a] for a in range(3)]
                total_error += float(np.sqrt(sum(float((s*s).mean()) for s in slopes if s.size)))
            elif mode == "residual":
                lap = _coordinate_laplacian(normed, coordinates, spacing)
                total_error += float(np.sqrt((lap**2).mean()))

        return total_error
