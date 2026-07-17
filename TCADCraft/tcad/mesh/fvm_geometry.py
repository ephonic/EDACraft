"""Finite-volume geometry preprocessing for unstructured tetrahedral meshes.

Builds node-centered control volumes and edge face-areas using the
median-dual (barycentric-dual) mesh construction.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set
import numpy as np

from .base import Mesh, Element


def build_fvm_geometry(mesh: Mesh) -> Dict[str, np.ndarray]:
    """
    Compute control volumes and edge face-areas for a tetrahedral mesh.

    Returns
    -------
    dict with keys:
        - ``control_volume`` : np.ndarray, shape (n_nodes,)
        - ``neighbors``      : list of list of int — neighbor nodes per node
        - ``edge_area``      : dict mapping (i, j) with i < j -> face area
        - ``edge_length``    : dict mapping (i, j) with i < j -> edge length
    """
    if mesh.node_coords is None:
        mesh.build_node_array()

    n_nodes = mesh.num_nodes()
    coords = mesh.node_coords

    # --- 1. Filter tetrahedral elements ---
    tets = [e for e in mesh.elements if e.etype == "tetra"]
    if not tets:
        raise ValueError("Mesh contains no tetrahedral elements")

    n_tets = len(tets)
    tet_nodes = np.array([e.node_indices for e in tets], dtype=int)  # (n_tets, 4)

    # --- 2. Tetrahedron volumes ---
    p0 = coords[tet_nodes[:, 0]]  # (n_tets, 3)
    p1 = coords[tet_nodes[:, 1]]
    p2 = coords[tet_nodes[:, 2]]
    p3 = coords[tet_nodes[:, 3]]

    # V = |det(p1-p0, p2-p0, p3-p0)| / 6
    vols = np.abs(np.einsum(
        'ij,ij->i',
        np.cross(p1 - p0, p2 - p0),
        p3 - p0
    )) / 6.0

    # --- 3. Node control volumes (barycentric: V/4 per node) ---
    cv = np.zeros(n_nodes, dtype=float)
    for t in range(n_tets):
        v = vols[t] / 4.0
        for nid in tet_nodes[t]:
            cv[nid] += v

    # --- 4. Edge-based geometry ---
    # Map each undirected edge to the list of adjacent tetrahedra
    edge_to_tets: Dict[Tuple[int, int], List[int]] = {}
    for t in range(n_tets):
        nodes = tet_nodes[t]
        # 6 edges of a tetrahedron
        edges = [(nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[0], nodes[3]),
                 (nodes[1], nodes[2]), (nodes[1], nodes[3]), (nodes[2], nodes[3])]
        for a, b in edges:
            e = (a, b) if a < b else (b, a)
            edge_to_tets.setdefault(e, []).append(t)

    edge_area: Dict[Tuple[int, int], float] = {}
    edge_len: Dict[Tuple[int, int], float] = {}
    neighbors: List[Set[int]] = [set() for _ in range(n_nodes)]

    # Precompute tetrahedron centroids
    centroids = (p0 + p1 + p2 + p3) / 4.0  # (n_tets, 3)

    # Precompute face centroids for each tetrahedron
    # Faces: (0,1,2), (0,1,3), (0,2,3), (1,2,3)
    face_nodes = np.array([
        [0, 1, 2],
        [0, 1, 3],
        [0, 2, 3],
        [1, 2, 3],
    ], dtype=int)  # (4, 3)

    # face_centroids[t, f, :] = centroid of face f of tet t
    face_centroids = np.zeros((n_tets, 4, 3), dtype=float)
    for f in range(4):
        fn = face_nodes[f]
        face_centroids[:, f, :] = (
            coords[tet_nodes[:, fn[0]]] +
            coords[tet_nodes[:, fn[1]]] +
            coords[tet_nodes[:, fn[2]]]
        ) / 3.0

    # For each edge, compute median-dual face area
    for (a, b), tlist in edge_to_tets.items():
        neighbors[a].add(b)
        neighbors[b].add(a)
        edge_len[(a, b)] = np.linalg.norm(coords[a] - coords[b])

        total_area = 0.0
        for t in tlist:
            nodes = tet_nodes[t]
            # Find which two faces contain edge (a,b)
            face_idx = []
            for f in range(4):
                fn = face_nodes[f]
                face_nids = [nodes[fn[0]], nodes[fn[1]], nodes[fn[2]]]
                if a in face_nids and b in face_nids:
                    face_idx.append(f)

            if len(face_idx) != 2:
                # Degenerate or boundary — skip
                continue

            c_t = centroids[t]
            c1 = face_centroids[t, face_idx[0]]
            c2 = face_centroids[t, face_idx[1]]
            m = (coords[a] + coords[b]) / 2.0

            # Two triangles: (c_t, c1, m) and (c_t, m, c2)
            tri1 = np.cross(c1 - c_t, m - c_t)
            tri2 = np.cross(m - c_t, c2 - c_t)
            total_area += 0.5 * (np.linalg.norm(tri1) + np.linalg.norm(tri2))

        edge_area[(a, b)] = total_area

    return {
        "control_volume": cv,
        "neighbors": [sorted(list(s)) for s in neighbors],
        "edge_area": edge_area,
        "edge_length": edge_len,
        "tet_volumes": vols,
        "tet_nodes": tet_nodes,
    }
