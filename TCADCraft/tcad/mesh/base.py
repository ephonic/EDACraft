"""Base mesh classes."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict
import numpy as np


@dataclass
class Node:
    idx: int
    x: float
    y: float
    z: float


@dataclass
class Element:
    idx: int
    node_indices: List[int]
    etype: str  # 'tetra', 'hexa', 'wedge', etc.
    tag: Optional[int] = None  # Material or region tag


class Mesh:
    """
    Generic unstructured or structured mesh.
    """

    def __init__(self):
        self.nodes: List[Node] = []
        self.elements: List[Element] = []
        self.node_coords: Optional[np.ndarray] = None  # Nx3 array for fast access
        self.fields: Dict[str, np.ndarray] = {}  # node-centered fields

    def num_nodes(self) -> int:
        return len(self.nodes)

    def num_elements(self) -> int:
        return len(self.elements)

    def build_node_array(self):
        """Cache Nx3 numpy array of node coordinates."""
        self.node_coords = np.array([[n.x, n.y, n.z] for n in self.nodes], dtype=float)

    def add_field(self, name: str, data: np.ndarray):
        if data.shape[0] != self.num_nodes():
            raise ValueError(f"Field '{name}' size mismatch: {data.shape[0]} vs {self.num_nodes()}")
        self.fields[name] = data.copy()

    def get_field(self, name: str) -> np.ndarray:
        return self.fields[name]

    def save(self, filename: str):
        """Save mesh and fields using meshio."""
        import meshio
        if self.node_coords is None:
            self.build_node_array()
        cells = []
        cell_data = {}
        if self.elements:
            # Group elements by type
            etypes = {}
            for e in self.elements:
                etypes.setdefault(e.etype, []).append(e.node_indices)
            for etype, conn in etypes.items():
                meshio_type = {
                    "tetra": "tetra",
                    "hexa": "hexahedron",
                    "wedge": "wedge",
                    "tri": "triangle",
                    "quad": "quad",
                }.get(etype, etype)
                cells.append((meshio_type, np.array(conn)))
        meshio.write_points_cells(
            filename,
            self.node_coords,
            cells,
            point_data=self.fields,
        )

    @classmethod
    def load(cls, filename: str) -> Mesh:
        """Load mesh from file (meshio supported formats)."""
        import meshio
        m = meshio.read(filename)
        mesh = cls()
        for i, (x, y, z) in enumerate(m.points):
            mesh.nodes.append(Node(i, float(x), float(y), float(z)))
        mesh.node_coords = m.points.astype(float)
        idx = 0
        for cell_block in m.cells:
            etype = {
                "tetrahedron": "tetra",
                "hexahedron": "hexa",
                "wedge": "wedge",
                "triangle": "tri",
                "quad": "quad",
            }.get(cell_block.type, cell_block.type)
            for row in cell_block.data:
                mesh.elements.append(Element(idx, row.tolist(), etype))
                idx += 1
        for name, data in m.point_data.items():
            mesh.fields[name] = data
        return mesh
