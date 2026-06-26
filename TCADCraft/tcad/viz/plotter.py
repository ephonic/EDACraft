"""Visualization tools for device geometry, mesh, and simulation results."""

from __future__ import annotations
from typing import Optional, Dict, List, Tuple
import numpy as np


def plot_device_geometry(
    device,
    figsize: Tuple[int, int] = (10, 8),
    show_contacts: bool = True,
):
    """
    Plot a 3D wireframe representation of device regions using matplotlib.
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    colors = plt.cm.tab10(np.linspace(0, 1, max(len(device.regions), 1)))

    for rid, region in enumerate(device.regions):
        (xmin, xmax), (ymin, ymax), (zmin, zmax) = region.shape.bbox()
        # Draw box edges
        verts = [
            [xmin, ymin, zmin], [xmax, ymin, zmin], [xmax, ymax, zmin], [xmin, ymax, zmin],
            [xmin, ymin, zmax], [xmax, ymin, zmax], [xmax, ymax, zmax], [xmin, ymax, zmax],
        ]
        faces = [
            [verts[0], verts[1], verts[2], verts[3]],
            [verts[4], verts[5], verts[6], verts[7]],
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[0], verts[3], verts[7], verts[4]],
        ]
        ax.add_collection3d(Poly3DCollection(
            faces, facecolors=colors[rid % len(colors)], alpha=0.3, edgecolors="k", linewidths=0.5
        ))
        ax.text((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2, region.name, fontsize=7)

    if show_contacts:
        for name, (shape, voltage) in device.contacts.items():
            (xmin, xmax), (ymin, ymax), (zmin, zmax) = shape.bbox()
            ax.plot([xmin, xmax, xmax, xmin, xmin], [ymin, ymin, ymax, ymax, ymin], [zmax, zmax, zmax, zmax, zmax], "r-", lw=2)
            ax.text((xmin + xmax) / 2, (ymin + ymax) / 2, zmax, name, color="red", fontsize=8)

    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")
    ax.set_title(f"Device: {device.name}")
    plt.tight_layout()
    plt.show()


def plot_mesh_slice(
    mesh,
    field: Optional[str] = None,
    axis: str = "z",
    index: Optional[int] = None,
    coord: Optional[float] = None,
    cmap: str = "viridis",
    figsize: Tuple[int, int] = (8, 6),
):
    """
    Plot a 2D slice of a structured mesh field using matplotlib.

    Parameters
    ----------
    mesh : StructuredGrid
    field : str, optional
        Field name to color-map.  If None, shows mesh grid only.
    axis : 'x' | 'y' | 'z'
        Axis normal to slice.
    index : int, optional
        Grid index along axis.
    coord : float, optional
        Physical coordinate along axis (find nearest index).
    """
    from tcad.mesh.structured_grid import StructuredGrid
    if not isinstance(mesh, StructuredGrid):
        raise TypeError("plot_mesh_slice currently only supports StructuredGrid")

    import matplotlib.pyplot as plt
    nx, ny, nz = mesh.shape()
    X, Y, Z = mesh.X, mesh.Y, mesh.Z

    if axis == "z":
        if coord is not None:
            index = int(np.argmin(np.abs(mesh.Z[0, 0, :] - coord)))
        idx = index or nz // 2
        xx, yy = X[:, :, idx], Y[:, :, idx]
        title = f"z = {Z[0,0,idx]:.3e} m"
    elif axis == "y":
        if coord is not None:
            index = int(np.argmin(np.abs(mesh.Y[0, :, 0] - coord)))
        idx = index or ny // 2
        xx, yy = X[:, idx, :], Z[:, idx, :]
        title = f"y = {Y[0,idx,0]:.3e} m"
    elif axis == "x":
        if coord is not None:
            index = int(np.argmin(np.abs(mesh.X[:, 0, 0] - coord)))
        idx = index or nx // 2
        xx, yy = Y[idx, :, :], Z[idx, :, :]
        title = f"x = {X[idx,0,0]:.3e} m"
    else:
        raise ValueError(f"Invalid axis: {axis}")

    fig, ax = plt.subplots(figsize=figsize)
    if field and field in mesh.fields:
        data = mesh.fields[field]
        if axis == "z":
            slab = data.reshape(nx, ny, nz)[:, :, idx]
        elif axis == "y":
            slab = data.reshape(nx, ny, nz)[:, idx, :]
        else:
            slab = data.reshape(nx, ny, nz)[idx, :, :]
        im = ax.pcolormesh(xx, yy, slab.T, cmap=cmap, shading="auto")
        fig.colorbar(im, ax=ax, label=field)
    else:
        ax.plot(xx.ravel(), yy.ravel(), "k.", ms=0.5)

    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel(f"{axis.replace('x','y').replace('y','x').replace('z','x')} [m]")
    ax.set_ylabel(f"{axis.replace('x','z').replace('y','z').replace('z','y')} [m]")
    plt.tight_layout()
    plt.show()


def plot_3d_field(
    mesh,
    field: str,
    isosurface: Optional[float] = None,
    clip_plane: Optional[Tuple[str, float]] = None,
    cmap: str = "viridis",
    show_edges: bool = False,
):
    """
    Interactive 3D visualization using PyVista (if available).
    Falls back to matplotlib contour slice if PyVista is not installed.
    """
    try:
        import pyvista as pv
    except ImportError:
        print("PyVista not installed; falling back to matplotlib slice plot.")
        plot_mesh_slice(mesh, field=field)
        return

    if mesh.node_coords is None:
        mesh.build_node_array()

    # Build unstructured grid for pyvista
    points = mesh.node_coords
    # Only tetra/hexa supported for now
    cells = []
    for e in mesh.elements:
        if e.etype == "tetra":
            cells.append([4] + e.node_indices)
        elif e.etype == "hexa":
            cells.append([8] + e.node_indices)
    if not cells:
        print("No volumetric elements for 3D plot; falling back to slice.")
        plot_mesh_slice(mesh, field=field)
        return

    cell_array = np.hstack(cells)
    cell_types = []
    for e in mesh.elements:
        if e.etype == "tetra":
            cell_types.append(pv.CellType.TETRA)
        elif e.etype == "hexa":
            cell_types.append(pv.CellType.HEXAHEDRON)

    grid = pv.UnstructuredGrid(cell_array, cell_types, points)
    if field in mesh.fields:
        grid.point_data[field] = mesh.fields[field]

    pl = pv.Plotter()
    if isosurface is not None:
        pl.add_mesh(grid.contour([isosurface], scalars=field), cmap=cmap, opacity=0.8)
    else:
        pl.add_mesh(grid, scalars=field, cmap=cmap, show_edges=show_edges, opacity=0.85)

    if clip_plane:
        normal_map = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
        normal = normal_map.get(clip_plane[0], (1, 0, 0))
        origin = [0, 0, 0]
        axis_idx = {"x": 0, "y": 1, "z": 2}[clip_plane[0]]
        origin[axis_idx] = clip_plane[1]
        pl.add_mesh_slice(grid, scalars=field, normal=normal, origin=origin, cmap=cmap)

    pl.add_axes()
    pl.show()


def plot_1d_cutline(
    mesh,
    field: str,
    start: Tuple[float, float, float],
    end: Tuple[float, float, float],
    num_points: int = 200,
    figsize: Tuple[int, int] = (8, 4),
):
    """
    Extract and plot a 1D cutline from a structured grid.
    """
    from tcad.mesh.structured_grid import StructuredGrid
    if not isinstance(mesh, StructuredGrid):
        raise NotImplementedError("1D cutline only for structured grids")

    import matplotlib.pyplot as plt
    from scipy.interpolate import RegularGridInterpolator

    nx, ny, nz = mesh.shape()
    x = np.linspace(mesh.xmin, mesh.xmax, nx)
    y = np.linspace(mesh.ymin, mesh.ymax, ny)
    z = np.linspace(mesh.zmin, mesh.zmax, nz)
    data = mesh.fields[field].reshape(nx, ny, nz)

    interpolator = RegularGridInterpolator((x, y, z), data, bounds_error=False, fill_value=0.0)

    t = np.linspace(0, 1, num_points)
    xs = start[0] + t * (end[0] - start[0])
    ys = start[1] + t * (end[1] - start[1])
    zs = start[2] + t * (end[2] - start[2])
    pts = np.column_stack((xs, ys, zs))
    vals = interpolator(pts)

    # Distance along cutline
    dist = np.sqrt((xs - start[0])**2 + (ys - start[1])**2 + (zs - start[2])**2)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(dist, vals, "b-")
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel(field)
    ax.set_title(f"Cutline: {start} -> {end}")
    ax.grid(True)
    plt.tight_layout()
    plt.show()
