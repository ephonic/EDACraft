"""Unstructured finite-volume-method (FVM) solver backend.

This module provides a node-centered FVM discretization on tetrahedral
meshes, solving Poisson and drift-diffusion equations using SciPy sparse
linear algebra.  It complements the structured-grid C++ backend for
device geometries that require body-fitted unstructured meshes.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import sparse
from scipy.sparse import linalg as spla

from tcad.mesh.base import Mesh
from tcad.mesh.fvm_geometry import build_fvm_geometry


class UnstructuredFVM:
    """
    Node-centered finite-volume assembler for tetrahedral meshes.

    Parameters
    ----------
    mesh : Mesh
        Unstructured mesh with tetrahedral elements.
    """

    def __init__(self, mesh: Mesh):
        self.mesh = mesh
        self.geom = build_fvm_geometry(mesh)
        self.n_nodes = mesh.num_nodes()
        self.coords = mesh.node_coords
        self.neighbors = self.geom["neighbors"]
        self.cv = self.geom["control_volume"]
        self.edge_area = self.geom["edge_area"]
        self.edge_len = self.geom["edge_length"]

        # Build CSR neighbor index maps for fast iteration
        self._build_csr_neighbors()

        # Fields
        self.eps = np.ones(self.n_nodes, dtype=float) * 8.854187817e-12 * 11.7
        self.doping = np.zeros(self.n_nodes, dtype=float)
        self.mu_n = np.ones(self.n_nodes, dtype=float) * 1400e-4
        self.mu_p = np.ones(self.n_nodes, dtype=float) * 450e-4

        # Boundary conditions
        self.dirichlet: Dict[int, float] = {}

    def _build_csr_neighbors(self):
        """Build CSR-like arrays for neighbor iteration."""
        row_ptr = [0]
        col_idx = []
        for i in range(self.n_nodes):
            col_idx.extend(self.neighbors[i])
            row_ptr.append(len(col_idx))
        self.neigh_row_ptr = np.array(row_ptr, dtype=int)
        self.neigh_col_idx = np.array(col_idx, dtype=int)

    def set_permittivity(self, eps: np.ndarray):
        self.eps = np.asarray(eps, dtype=float).ravel()

    def set_doping(self, doping: np.ndarray):
        self.doping = np.asarray(doping, dtype=float).ravel()

    def set_mobility(self, mu_n: np.ndarray, mu_p: np.ndarray):
        self.mu_n = np.asarray(mu_n, dtype=float).ravel()
        self.mu_p = np.asarray(mu_p, dtype=float).ravel()

    def set_dirichlet(self, bc: Dict[int, float]):
        self.dirichlet = dict(bc)

    def _effective_eps(self, i: int, j: int) -> float:
        """Harmonic mean of permittivity on edge (i, j)."""
        e1, e2 = self.eps[i], self.eps[j]
        s = e1 + e2
        return 2.0 * e1 * e2 / s if s > 0 else 0.0

    def assemble_poisson(self, n: np.ndarray, p: np.ndarray) -> Tuple[sparse.csr_matrix, np.ndarray]:
        """
        Assemble Poisson matrix A and RHS b for:
            div(eps * grad(phi)) = -rho
        where rho = q * (p - n + doping).

        Returns
        -------
        A : scipy.sparse.csr_matrix, shape (n_nodes, n_nodes)
        b : np.ndarray, shape (n_nodes,)
        """
        q = 1.602176634e-19
        rho = q * (p - n + self.doping)

        data = []
        row_ind = []
        col_ind = []
        rhs = -rho * self.cv  # node-centered source

        for i in range(self.n_nodes):
            diag = 0.0
            for j in self.neighbors[i]:
                if j <= i:
                    continue  # only upper triangle + diagonal
                e = (i, j)
                area = self.edge_area.get(e, 0.0)
                length = self.edge_len.get(e, 1.0)
                if length <= 0 or area <= 0:
                    continue
                eps_eff = self._effective_eps(i, j)
                coeff = eps_eff * area / length

                data.append(coeff)
                row_ind.append(i)
                col_ind.append(j)

                data.append(coeff)
                row_ind.append(j)
                col_ind.append(i)

                diag -= coeff
                # symmetric diagonal contribution for j
                # will be handled when i loops to j, or we accumulate separately

        # Build diagonal from row sums
        diag_vals = np.zeros(self.n_nodes, dtype=float)
        for i in range(self.n_nodes):
            d = 0.0
            for j in self.neighbors[i]:
                e = (min(i, j), max(i, j))
                area = self.edge_area.get(e, 0.0)
                length = self.edge_len.get(e, 1.0)
                if length <= 0 or area <= 0:
                    continue
                eps_eff = self._effective_eps(i, j)
                coeff = eps_eff * area / length
                d -= coeff
            diag_vals[i] = d
            rhs[i] -= d * 0.0  # no dirichlet shift yet

        # Add diagonal entries
        for i in range(self.n_nodes):
            data.append(diag_vals[i])
            row_ind.append(i)
            col_ind.append(i)

        # Apply Dirichlet BC by modifying COO entries directly
        if self.dirichlet:
            # Remove any entries in Dirichlet rows
            mask = np.ones(len(data), dtype=bool)
            for idx, val in self.dirichlet.items():
                mask &= ~(np.array(row_ind) == idx)
            data = [d for d, m in zip(data, mask) if m]
            row_ind = [r for r, m in zip(row_ind, mask) if m]
            col_ind = [c for c, m in zip(col_ind, mask) if m]
            # Add diagonal entries for Dirichlet rows
            for idx, val in self.dirichlet.items():
                data.append(1.0)
                row_ind.append(idx)
                col_ind.append(idx)
                rhs[idx] = val

        A = sparse.coo_matrix((data, (row_ind, col_ind)), shape=(self.n_nodes, self.n_nodes))
        A = A.tocsr()

        return A, rhs

    def solve_poisson(self, n: Optional[np.ndarray] = None,
                      p: Optional[np.ndarray] = None,
                      phi0: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Solve Poisson equation for potential phi.

        Parameters
        ----------
        n, p : np.ndarray, optional
            Carrier densities [m^-3].  Defaults to equilibrium values.
        phi0 : np.ndarray, optional
            Initial guess [V].

        Returns
        -------
        phi : np.ndarray, shape (n_nodes,)
        """
        if n is None:
            ni = self._intrinsic_concentration()
            n = np.full(self.n_nodes, ni, dtype=float)
        if p is None:
            ni = self._intrinsic_concentration()
            p = np.full(self.n_nodes, ni, dtype=float)

        A, b = self.assemble_poisson(n, p)

        if phi0 is not None:
            x0 = phi0.copy()
        else:
            x0 = np.zeros(self.n_nodes, dtype=float)

        # Apply Dirichlet values to initial guess
        for idx, val in self.dirichlet.items():
            x0[idx] = val

        # Solve using sparse direct solver (SUPERLU)
        phi = spla.spsolve(A, b)
        return phi

    def _intrinsic_concentration(self) -> float:
        """Approximate intrinsic concentration for Silicon at 300K."""
        return 1.0e16 * 1e6  # 1e16 cm^-3 -> m^-3

    def compute_electric_field(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute electric field components from phi using node-neighbor
        least-squares gradient reconstruction.
        """
        Ex = np.zeros(self.n_nodes, dtype=float)
        Ey = np.zeros(self.n_nodes, dtype=float)
        Ez = np.zeros(self.n_nodes, dtype=float)

        for i in range(self.n_nodes):
            nbrs = self.neighbors[i]
            if not nbrs:
                continue
            # Weighted least-squares: sum w_j (grad_phi · dx_j - dphi_j)^2
            dx = self.coords[nbrs] - self.coords[i]  # (m, 3)
            dphi = phi[nbrs] - phi[i]  # (m,)
            w = 1.0 / (np.linalg.norm(dx, axis=1) + 1e-30)
            W = np.diag(w)
            # Solve (DX^T W DX) grad = DX^T W dphi
            DX = dx  # (m, 3)
            M = DX.T @ W @ DX
            rhs = DX.T @ (w * dphi)
            try:
                grad = np.linalg.solve(M, rhs)
            except np.linalg.LinAlgError:
                grad = np.zeros(3)
            Ex[i], Ey[i], Ez[i] = -grad

        return Ex, Ey, Ez
