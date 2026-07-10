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


# ---------------------------------------------------------------------------
# Device-characteristic plotters (P4.2): P-V, P-E loops, Id-Vg transfer, PUND.
#
# These produce paper-ready figures. They apply the academic style (serif fonts,
# inward ticks, thin axes) from tcad.viz.style so the 3rd-generation plots
# match the academic look of the 2nd-generation figures (comments.docx).
# ---------------------------------------------------------------------------

def plot_pv_loop(
    voltages,
    P,
    ax=None,
    Ps: Optional[float] = None,
    Vc: Optional[float] = None,
    unit_uc_cm2: bool = True,
    label: Optional[str] = None,
    show_legend: bool = True,
):
    """Plot a polarization-voltage (P-V) hysteresis loop.

    Parameters
    ----------
    voltages : array-like
        Applied voltage sequence [V] (a bipolar sweep, e.g. from
        :func:`tcad.postprocess.fe_loops.run_pv_sweep`).
    P : array-like
        Polarization [C/m^2], same length as ``voltages``.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; created if None.
    Ps : float, optional
        Saturation polarization [C/m^2]. Drawn as a dashed reference line.
    Vc : float, optional
        Coercive voltage [V]. Drawn as vertical dashed reference lines.
    unit_uc_cm2 : bool
        If True (default), convert P to uC/cm^2 for the y-axis (x100).
    label : str, optional
        Legend label for the loop.
    show_legend : bool
        Whether to show the legend.

    Returns
    -------
    matplotlib.axes.Axes
        The axes with the plot.
    """
    from tcad.viz.style import set_academic_style
    import matplotlib.pyplot as plt
    set_academic_style()
    if ax is None:
        fig, ax = plt.subplots()
    P_arr = np.asarray(P, dtype=float)
    y = P_arr * 100.0 if unit_uc_cm2 else P_arr
    ax.plot(voltages, y, "-", lw=1.5, label=label)
    ylab = r"Polarization [$\mu$C/cm$^2$]" if unit_uc_cm2 else r"Polarization [C/m$^2$]"
    ax.set_xlabel("Voltage [V]")
    ax.set_ylabel(ylab)
    ax.axhline(0, color="0.5", lw=0.5)
    ax.axvline(0, color="0.5", lw=0.5)
    if Ps is not None:
        ys = Ps * 100.0 if unit_uc_cm2 else Ps
        ax.axhline(ys, ls="--", color="0.6", lw=0.7)
        ax.axhline(-ys, ls="--", color="0.6", lw=0.7)
    if Vc is not None:
        ax.axvline(Vc, ls="--", color="0.6", lw=0.7)
        ax.axvline(-Vc, ls="--", color="0.6", lw=0.7)
    if show_legend and label is not None:
        ax.legend()
    return ax


def plot_pe_loop(
    E,
    P,
    ax=None,
    Ps: Optional[float] = None,
    Ec: Optional[float] = None,
    unit_uc_cm2: bool = True,
    label: Optional[str] = None,
    show_legend: bool = True,
):
    """Plot a polarization-electric-field (P-E) hysteresis loop.

    Parameters
    ----------
    E : array-like
        Electric field [V/m] (or [MV/cm] if ``unit_MV_cm`` handled by caller).
    P : array-like
        Polarization [C/m^2].
    ax : matplotlib.axes.Axes, optional
        Axes to draw on.
    Ps : float, optional
        Saturation polarization [C/m^2] (reference line).
    Ec : float, optional
        Coercive field [V/m] (reference line).
    unit_uc_cm2 : bool
        Convert P to uC/cm^2 for the y-axis.
    label, show_legend : see :func:`plot_pv_loop`.
    """
    from tcad.viz.style import set_academic_style
    import matplotlib.pyplot as plt
    set_academic_style()
    if ax is None:
        fig, ax = plt.subplots()
    P_arr = np.asarray(P, dtype=float)
    y = P_arr * 100.0 if unit_uc_cm2 else P_arr
    E_arr = np.asarray(E, dtype=float)
    ax.plot(E_arr * 1e-8, y, "-", lw=1.5, label=label)   # V/m -> MV/cm
    ax.set_xlabel(r"Electric field [MV/cm]")
    ylab = r"Polarization [$\mu$C/cm$^2$]" if unit_uc_cm2 else r"Polarization [C/m$^2$]"
    ax.set_ylabel(ylab)
    ax.axhline(0, color="0.5", lw=0.5)
    ax.axvline(0, color="0.5", lw=0.5)
    if Ps is not None:
        ys = Ps * 100.0 if unit_uc_cm2 else Ps
        ax.axhline(ys, ls="--", color="0.6", lw=0.7)
        ax.axhline(-ys, ls="--", color="0.6", lw=0.7)
    if Ec is not None:
        ax.axvline(Ec * 1e-8, ls="--", color="0.6", lw=0.7)
        ax.axvline(-Ec * 1e-8, ls="--", color="0.6", lw=0.7)
    if show_legend and label is not None:
        ax.legend()
    return ax


def plot_transfer(
    vgs,
    ids,
    ax=None,
    Vth: Optional[float] = None,
    log_scale: bool = True,
    label: Optional[str] = None,
    show_legend: bool = True,
):
    """Plot a transfer characteristic (Id-Vg).

    Parameters
    ----------
    vgs : array-like
        Gate voltage [V].
    ids : array-like
        Drain current [A].
    ax : matplotlib.axes.Axes, optional
        Axes to draw on.
    Vth : float, optional
        Threshold voltage [V] (vertical reference line).
    log_scale : bool
        Use a logarithmic y-axis (default True — standard for transfer curves).
    label, show_legend : see :func:`plot_pv_loop`.
    """
    from tcad.viz.style import set_academic_style
    import matplotlib.pyplot as plt
    set_academic_style()
    if ax is None:
        fig, ax = plt.subplots()
    ids_arr = np.abs(np.asarray(ids, dtype=float))   # |Id| for log scale
    if log_scale:
        ax.semilogy(vgs, ids_arr, "-o", ms=3, lw=1.5, label=label)
    else:
        ax.plot(vgs, ids_arr, "-o", ms=3, lw=1.5, label=label)
    ax.set_xlabel(r"Gate voltage $V_G$ [V]")
    ax.set_ylabel(r"Drain current $|I_D|$ [A]")
    if Vth is not None:
        ax.axvline(Vth, ls="--", color="0.6", lw=0.7)
    if show_legend and label is not None:
        ax.legend()
    return ax


def plot_pund(
    times,
    voltages,
    P,
    ax=None,
):
    """Plot a PUND (Positive-Up-Negative-Down) pulse sequence and response.

    Parameters
    ----------
    times : array-like
        Time points [s].
    voltages : array-like
        Applied voltage pulse sequence [V].
    P : array-like
        Polarization response [C/m^2].
    ax : matplotlib.axes.Axes, optional
        Axes to draw on (a twin y-axis is used for voltage).

    Returns
    -------
    matplotlib.axes.Axes
        The polarization axis.
    """
    from tcad.viz.style import set_academic_style
    import matplotlib.pyplot as plt
    set_academic_style()
    if ax is None:
        fig, ax = plt.subplots()
    t = np.asarray(times)
    P_arr = np.asarray(P, dtype=float) * 100.0   # C/m^2 -> uC/cm^2
    ax.plot(t * 1e6, P_arr, "b-", lw=1.5, label=r"$P$")
    ax.set_xlabel(r"Time [$\mu$s]")
    ax.set_ylabel(r"Polarization [$\mu$C/cm$^2$]", color="b")
    ax.tick_params(axis="y", labelcolor="b")
    ax2 = ax.twinx()
    ax2.plot(t * 1e6, np.asarray(voltages), "r--", lw=1.0, alpha=0.6, label=r"$V$")
    ax2.set_ylabel("Voltage [V]", color="r")
    ax2.tick_params(axis="y", labelcolor="r")
    ax2.grid(False)
    return ax
