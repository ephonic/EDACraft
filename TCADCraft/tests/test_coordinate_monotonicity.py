"""Coordinate-monotonicity stability tests (audit §19 / conclusion-① note).

The user's note flagged "横坐标错误" (x-axis errors) as a possible agent
instability. Audit §19 fixed the structured-grid node-ordering bug (edges
sorted by coordinate). This test pins that fix: every code path that returns
spatial coordinates for plotting/reporting/cutline extraction MUST yield
strictly monotonically increasing coordinates along an axis. If a refactor
re-introduces an ordering bug, these tests fail loudly.

Covered:
  1. ``StructuredGrid.flat_coords()`` — x, y, z monotonic per axis.
  2. ``cutline_x_at_jk`` (bands.py) — x strictly increasing for any (j,k).
  3. Slice coordinates in ``plot_mesh_slice`` — the two in-plane axes are
     monotonic (the plot x-axis must read left-to-right).
"""

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid


def _make_grid(nx=7, ny=5, nz=4, Lx=1e-6, Ly=0.5e-6, Lz=0.3e-6):
    return StructuredGrid(
        bbox=((0.0, Lx), (0.0, Ly), (0.0, Lz)),
        nx=nx, ny=ny, nz=nz,
    )


class TestFlatCoordsMonotonic:
    """flat_coords() must give monotonic coordinates along each axis line."""

    def test_flat_x_monotonic_along_x_line(self):
        mesh = _make_grid()
        fx, fy, fz = mesh.flat_coords()
        nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
        # Along an x-line (i varies, j,k fixed): fx strictly increasing.
        for j in (0, ny // 2, ny - 1):
            for k in (0, nz // 2, nz - 1):
                line = np.array([i + nx * (j + ny * k) for i in range(nx)])
                xs = fx[line]
                assert np.all(np.diff(xs) > 0), (
                    f"flat x not strictly increasing along x-line (j={j},k={k}): "
                    f"{xs}")
                # y, z must be constant along this x-line.
                assert np.allclose(fy[line], fy[line[0]]), (
                    f"flat y varies along an x-line (j={j},k={k})")
                assert np.allclose(fz[line], fz[line[0]]), (
                    f"flat z varies along an x-line (j={j},k={k})")

    def test_flat_y_monotonic_along_y_line(self):
        mesh = _make_grid()
        fx, fy, fz = mesh.flat_coords()
        nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
        for i in (0, nx // 2, nx - 1):
            for k in (0, nz // 2, nz - 1):
                line = np.array([i + nx * (j + ny * k) for j in range(ny)])
                ys = fy[line]
                assert np.all(np.diff(ys) > 0), (
                    f"flat y not strictly increasing along y-line (i={i},k={k})")

    def test_flat_z_monotonic_along_z_line(self):
        mesh = _make_grid()
        fx, fy, fz = mesh.flat_coords()
        nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
        for i in (0, nx // 2, nx - 1):
            for j in (0, ny // 2, ny - 1):
                line = np.array([i + nx * (j + ny * k) for k in range(nz)])
                zs = fz[line]
                assert np.all(np.diff(zs) > 0), (
                    f"flat z not strictly increasing along z-line (i={i},j={j})")


class TestCutlineMonotonic:
    """The bands cutline extractor must return strictly increasing x coords."""

    def test_cutline_x_strictly_increasing(self):
        from tcad.postprocess.bands import cutline_x_at_jk
        mesh = _make_grid()
        ny, nz = mesh.ny, mesh.nz
        for j in (0, ny // 2, ny - 1):
            for k in (0, nz // 2, nz - 1):
                x, line = cutline_x_at_jk(mesh, j=j, k=k)
                assert np.all(np.diff(x) > 0), (
                    f"cutline x not strictly increasing at (j={j},k={k}): {x}")
                # Indices must be the contiguous x-line in node order.
                expected = np.array([i + mesh.nx * (j + mesh.ny * k)
                                     for i in range(mesh.nx)], dtype=np.int64)
                assert np.array_equal(line, expected), (
                    f"cutline indices wrong at (j={j},k={k})")

    def test_cutline_matches_flat_x(self):
        """cutline x must equal flat_coords x at the same nodes (consistency)."""
        from tcad.postprocess.bands import cutline_x_at_jk
        mesh = _make_grid()
        fx = mesh.flat_coords()[0]
        x_cut, line = cutline_x_at_jk(mesh, j=2, k=1)
        assert np.allclose(x_cut, fx[line]), (
            "cutline x disagrees with flat_coords at the same nodes")


class TestSlicePlotCoordsMonotonic:
    """The 2D slice plot consumes mesh.X/Y/Z in-plane slices; those must be
    monotonic (we assert on the grid arrays directly rather than calling the
    matplotlib plotter, to keep the test headless and backend-independent —
    the plotter only forwards these arrays to pcolormesh)."""

    def test_z_slice_in_plane_monotonic(self):
        mesh = _make_grid()
        idx = mesh.nz // 2
        # z-slice: in-plane axes are x (cols of X[:,:,idx]) and y (rows).
        xx = mesh.X[:, :, idx]   # shape (nx, ny): x increases along axis 0
        yy = mesh.Y[:, :, idx]
        assert np.all(np.diff(xx[:, 0]) > 0), "z-slice x not monotonic"
        assert np.all(np.diff(yy[0, :]) > 0), "z-slice y not monotonic"

    def test_x_slice_in_plane_monotonic(self):
        mesh = _make_grid()
        idx = mesh.nx // 2
        # x-slice: in-plane axes are y and z.
        yy = mesh.Y[idx, :, :]   # shape (ny, nz)
        zz = mesh.Z[idx, :, :]
        assert np.all(np.diff(yy[:, 0]) > 0), "x-slice y not monotonic"
        assert np.all(np.diff(zz[0, :]) > 0), "x-slice z not monotonic"


class TestFieldCutlineAlignment:
    """A field sampled along a cutline must align with the cutline x coords
    (no off-by-one / transposition that would produce a 'wrong x-axis')."""

    def test_field_values_track_cutline_coords(self):
        """Build a field that is a known linear function of x; the cutline
        values must match x (up to scale) — if the indexing were transposed
        the values would be scrambled."""
        from tcad.postprocess.bands import cutline_x_at_jk
        mesh = _make_grid()
        fx = mesh.flat_coords()[0]
        N = mesh.npts()
        # phi = x (a linear ramp); along an x-cutline the values must equal x.
        field = fx.copy()
        x_cut, line = cutline_x_at_jk(mesh, j=0, k=0)
        vals = field[line]
        assert np.allclose(vals, x_cut), (
            "cutline field values do not track cutline x coords — indexing "
            "transposition (the 'wrong x-axis' bug)")
