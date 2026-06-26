"""Gmsh-based unstructured tetrahedral mesh generation."""

from __future__ import annotations
from typing import Optional
import numpy as np

from .base import Mesh, Node, Element
from tcad.geometry.device_builder import Device


class GmshMeshGenerator:
    """
    Wrapper around Gmsh Python API for generating tetrahedral meshes.
    Gmsh is an optional dependency; install with ``pip install tcad[gmsh]``.
    """

    def __init__(self, verbose: int = 0):
        try:
            import gmsh
            self.gmsh = gmsh
            gmsh.initialize()
            gmsh.option.setNumber("General.Verbosity", verbose)
        except ImportError as exc:
            raise ImportError(
                "Gmsh is required for unstructured meshing. "
                "Install with: pip install gmsh"
            ) from exc

    def __del__(self):
        if hasattr(self, "gmsh"):
            try:
                self.gmsh.finalize()
            except Exception:
                pass

    def generate(
        self,
        device: Device,
        max_element_size: Optional[float] = None,
        min_element_size: Optional[float] = None,
        optimize: bool = True,
    ) -> Mesh:
        """
        Generate a tetrahedral mesh for the device.
        Uses Gmsh's constructive solid geometry to build regions.
        """
        g = self.gmsh
        g.model.add(device.name)

        # Create volumes from device regions
        region_tags = {}
        for rid, region in enumerate(device.regions):
            bbox = region.shape.bbox()
            # Simplified: use bounding box as a first approximation
            # For complex shapes, user should override with custom Gmsh script
            (xmin, xmax), (ymin, ymax), (zmin, zmax) = bbox
            tag = g.model.occ.addBox(xmin, ymin, zmin, xmax - xmin, ymax - ymin, zmax - zmin)
            region_tags[rid] = tag

        g.model.occ.synchronize()

        # Assign physical groups for materials
        for rid, region in enumerate(device.regions):
            g.model.addPhysicalGroup(3, [region_tags[rid]], tag=rid, name=region.name)

        # Meshing options
        if max_element_size:
            g.option.setNumber("Mesh.MeshSizeMax", max_element_size)
        if min_element_size:
            g.option.setNumber("Mesh.MeshSizeMin", min_element_size)

        g.model.mesh.generate(3)
        if optimize:
            g.model.mesh.optimize("Netgen")

        # Extract nodes and elements
        node_tags, coords, _ = g.model.mesh.getNodes()
        coords = coords.reshape(-1, 3)
        mesh = Mesh()
        tag_to_idx = {}
        for idx, (tag, (x, y, z)) in enumerate(zip(node_tags, coords)):
            mesh.nodes.append(Node(idx, float(x), float(y), float(z)))
            tag_to_idx[tag] = idx

        # Elements
        elem_types, elem_tags, elem_node_tags = g.model.mesh.getElements()
        eidx = 0
        for etype, tags, nodes in zip(elem_types, elem_tags, elem_node_tags):
            # Gmsh type 4 = tetra4, 5 = hexa8, 6 = prism6, 7 = pyramid5, 11 = tetra10
            type_map = {4: "tetra", 5: "hexa", 6: "wedge", 7: "pyramid", 11: "tetra10"}
            if etype not in type_map:
                continue
            etype_str = type_map[etype]
            nnodes = {4: 4, 5: 8, 6: 6, 7: 5, 11: 10}[etype]
            nodes = nodes.reshape(-1, nnodes)
            for tag, conn in zip(tags, nodes):
                mesh.elements.append(Element(
                    eidx,
                    [tag_to_idx[int(t)] for t in conn],
                    etype_str,
                    tag=int(tag),
                ))
                eidx += 1

        mesh.build_node_array()

        # Sample device properties onto nodes
        x = mesh.node_coords[:, 0]
        y = mesh.node_coords[:, 1]
        z = mesh.node_coords[:, 2]
        sampled = device.sample_on_grid(x, y, z)
        for name, data in sampled.items():
            mesh.add_field(name, data)

        return mesh
