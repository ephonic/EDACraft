"""High-level mesh generation entry points."""

from __future__ import annotations
from typing import Tuple, Optional
import math

from tcad.geometry.device_builder import Device
from .structured_grid import StructuredGrid
from .base import Mesh


def structured_mesh_from_device(
    device: Device,
    resolution: Optional[Tuple[float, float, float]] = None,
    nx: Optional[int] = None,
    ny: Optional[int] = None,
    nz: Optional[int] = None,
) -> StructuredGrid:
    """
    Generate a structured Cartesian mesh from a Device bounding box.

    Parameters
    ----------
    device : Device
        The device to mesh.
    resolution : tuple(float, float, float), optional
        Desired grid spacing (dx, dy, dz) in meters.
    nx, ny, nz : int, optional
        Explicit node counts (override resolution).
    """
    bbox = device.bbox()
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bbox

    if resolution is not None:
        dx, dy, dz = resolution
        _nx = max(3, math.ceil((xmax - xmin) / dx) + 1) if nx is None else nx
        _ny = max(3, math.ceil((ymax - ymin) / dy) + 1) if ny is None else ny
        _nz = max(3, math.ceil((zmax - zmin) / dz) + 1) if nz is None else nz
    else:
        _nx = nx or 51
        _ny = ny or 51
        _nz = nz or 51

    grid = StructuredGrid(bbox, _nx, _ny, _nz)
    # Attach device fields
    fields = grid.create_device_fields(device)
    for name, data in fields.items():
        grid.add_field(name, data)
    # Contact masks as fields too
    contacts = grid.contact_masks(device)
    for name, mask in contacts.items():
        grid.add_field(f"contact_{name}", mask.astype(float))
    return grid


def generate_mesh(
    device: Device,
    method: str = "structured",
    **kwargs,
) -> Mesh:
    """
    Universal mesh generation dispatcher.

    method : 'structured' | 'gmsh'
    """
    if method == "structured":
        return structured_mesh_from_device(device, **kwargs)
    elif method == "gmsh":
        from .gmsh_wrapper import GmshMeshGenerator
        gen = GmshMeshGenerator()
        return gen.generate(device, **kwargs)
    else:
        raise ValueError(f"Unknown mesh method: {method}")
