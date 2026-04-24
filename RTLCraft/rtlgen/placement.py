"""
rtlgen.placement — Fast analytical placement with e-field overlap removal (RePlAce-style).

Algorithm:
- Quadratic wirelength minimization (HPWL-driven)
- Solves Laplacian linear system for x and y separately
- E-field density spreading: solves Poisson equation on a grid and uses the
  resulting potential gradient to push cells out of overloaded bins.
- Simple legalization at the end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, csc_matrix
from scipy.sparse.linalg import spsolve, splu

from rtlgen.lef import LefLibrary
from rtlgen.netlist import Netlist


@dataclass
class PlacementResult:
    positions: Dict[str, Tuple[float, float]]  # cell_name -> (x, y)
    hpwl: float
    width: float
    height: float


class AnalyticalPlacer:
    """Quadratic placer with e-field overlap removal for small-to-medium netlists."""

    def __init__(self, netlist: Netlist, lef: LefLibrary):
        self.netlist = netlist
        self.lef = lef
        self.site_h = lef.get_site_height()

    def _cell_width(self, cell_type: str) -> float:
        macro = self.lef.macros.get(cell_type)
        return macro.size[0] if macro else 1.0

    def _build_conn_matrix(self) -> Tuple[Dict[str, int], np.ndarray, np.ndarray, np.ndarray]:
        """Build connectivity Laplacian and RHS vectors for x/y."""
        cells = list(self.netlist.cells.keys())
        n = len(cells)
        idx_map = {c: i for i, c in enumerate(cells)}

        # Fixed positions: primary inputs on left boundary, outputs on right
        fixed: Dict[str, Tuple[float, float]] = {}
        for name, info in self.netlist.ports.items():
            if info["direction"] == "input":
                fixed[name] = (0.0, self.site_h * 0.5)
            else:
                fixed[name] = (max(10.0, n * 0.5), self.site_h * 0.5)

        # Build weight matrix and RHS
        A_data = []
        A_row = []
        A_col = []
        bx = np.zeros(n)
        by = np.zeros(n)

        def _add_conn(u: str, v: str, w: float):
            nonlocal A_data, A_row, A_col, bx, by
            # Both are cells
            if u in idx_map and v in idx_map:
                i, j = idx_map[u], idx_map[v]
                A_data.append(w)
                A_row.append(i)
                A_col.append(j)
                A_data.append(w)
                A_row.append(j)
                A_col.append(i)
                # Diagonal updates deferred
            # u is cell, v is fixed
            elif u in idx_map and v in fixed:
                i = idx_map[u]
                bx[i] += w * fixed[v][0]
                by[i] += w * fixed[v][1]
            elif v in idx_map and u in fixed:
                i = idx_map[v]
                bx[i] += w * fixed[u][0]
                by[i] += w * fixed[u][1]

        # For each net, create a clique with weight = 1 / degree
        for net in self.netlist.nets.values():
            pins = []
            if net.driver:
                pins.append(net.driver[0])
            for load_cell, _ in net.loads:
                if load_cell not in pins:
                    pins.append(load_cell)
            if len(pins) < 2:
                continue
            w = 1.0 / (len(pins) - 1)
            for i in range(len(pins)):
                for j in range(i + 1, len(pins)):
                    _add_conn(pins[i], pins[j], w)

        # Build diagonal
        diag = np.zeros(n)
        for net in self.netlist.nets.values():
            pins = []
            if net.driver:
                pins.append(net.driver[0])
            for load_cell, _ in net.loads:
                if load_cell not in pins:
                    pins.append(load_cell)
            if len(pins) < 2:
                continue
            w = 1.0 / (len(pins) - 1)
            for p in pins:
                if p in idx_map:
                    diag[idx_map[p]] += w

        # Add diagonal entries to sparse matrix
        lambda_reg = 1e-3
        for i in range(n):
            A_data.append(diag[i] + lambda_reg)
            A_row.append(i)
            A_col.append(i)

        A = csr_matrix((A_data, (A_row, A_col)), shape=(n, n))
        return idx_map, A, bx, by

    # ------------------------------------------------------------------
    # E-field overlap removal
    # ------------------------------------------------------------------

    def _build_poisson_solver(self, bins_x: int, bins_y: int):
        """Build and factorize the 2D Poisson matrix with Dirichlet BCs."""
        n = bins_x * bins_y
        data, row, col = [], [], []
        for j in range(bins_y):
            for i in range(bins_x):
                idx = j * bins_x + i
                if i == 0 or i == bins_x - 1 or j == 0 or j == bins_y - 1:
                    data.append(1.0)
                    row.append(idx)
                    col.append(idx)
                else:
                    data.append(4.0)
                    row.append(idx)
                    col.append(idx)
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nidx = (j + dj) * bins_x + (i + di)
                        data.append(-1.0)
                        row.append(idx)
                        col.append(nidx)
        A = csc_matrix((data, (row, col)), shape=(n, n))
        return splu(A)

    def _compute_density_map(
        self,
        x: np.ndarray,
        y: np.ndarray,
        widths: List[float],
        core_w: float,
        core_h: float,
        bins_x: int,
        bins_y: int,
        target_density: float = 0.75,
    ) -> np.ndarray:
        """Return charge density = actual_density - target_density."""
        bin_w = core_w / bins_x
        bin_h = core_h / bins_y
        bin_area = bin_w * bin_h
        density = np.zeros((bins_y, bins_x))

        for i in range(len(x)):
            w = widths[i]
            h = self.site_h
            # cell rectangle [x1, x2] x [y1, y2]
            x1, x2 = float(x[i]), float(x[i] + w)
            y1, y2 = float(y[i]), float(y[i] + h)

            bx1 = max(0, int(x1 / bin_w))
            bx2 = min(bins_x - 1, int(x2 / bin_w))
            by1 = max(0, int(y1 / bin_h))
            by2 = min(bins_y - 1, int(y2 / bin_h))

            for by in range(by1, by2 + 1):
                for bx in range(bx1, bx2 + 1):
                    ox1 = max(x1, bx * bin_w)
                    ox2 = min(x2, (bx + 1) * bin_w)
                    oy1 = max(y1, by * bin_h)
                    oy2 = min(y2, (by + 1) * bin_h)
                    if ox2 > ox1 and oy2 > oy1:
                        overlap_area = (ox2 - ox1) * (oy2 - oy1)
                        density[by, bx] += overlap_area / bin_area

        return density - target_density

    def _compute_e_field(
        self,
        density: np.ndarray,
        poisson_solver,
        bin_w: float,
        bin_h: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Solve Poisson equation and return electric field components."""
        ny, nx = density.shape
        phi = poisson_solver.solve(-density.flatten()).reshape(ny, nx)

        Ex = np.zeros_like(phi)
        Ey = np.zeros_like(phi)

        # Central differences for interior, one-sided at boundaries
        # Ex = -dphi/dx
        if nx > 2:
            Ex[:, 1:-1] = -(phi[:, 2:] - phi[:, :-2]) / (2.0 * bin_w)
            Ex[:, 0] = -(phi[:, 1] - phi[:, 0]) / bin_w
            Ex[:, -1] = -(phi[:, -1] - phi[:, -2]) / bin_w

        if ny > 2:
            Ey[1:-1, :] = -(phi[2:, :] - phi[:-2, :]) / (2.0 * bin_h)
            Ey[0, :] = -(phi[1, :] - phi[0, :]) / bin_h
            Ey[-1, :] = -(phi[-1, :] - phi[-2, :]) / bin_h

        return Ex, Ey

    def _sample_e_field_at_cells(
        self,
        x: np.ndarray,
        y: np.ndarray,
        Ex: np.ndarray,
        Ey: np.ndarray,
        core_w: float,
        core_h: float,
        bins_x: int,
        bins_y: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Bilinear interpolation of E-field at cell positions."""
        bin_w = core_w / bins_x
        bin_h = core_h / bins_y

        # map to continuous bin coordinates
        cx = np.clip(x / bin_w, 0, bins_x - 1.0001)
        cy = np.clip(y / bin_h, 0, bins_y - 1.0001)

        ix = cx.astype(int)
        iy = cy.astype(int)
        fx = cx - ix
        fy = cy - iy

        # bilinear interpolation
        def _interp(field):
            v00 = field[iy, ix]
            v01 = field[iy, np.clip(ix + 1, 0, bins_x - 1)]
            v10 = field[np.clip(iy + 1, 0, bins_y - 1), ix]
            v11 = field[np.clip(iy + 1, 0, bins_y - 1), np.clip(ix + 1, 0, bins_x - 1)]
            return (1 - fx) * (1 - fy) * v00 + fx * (1 - fy) * v01 + (1 - fx) * fy * v10 + fx * fy * v11

        return _interp(Ex), _interp(Ey)

    # ------------------------------------------------------------------
    # Main placement flow
    # ------------------------------------------------------------------

    def place(self, aspect_ratio: float = 1.0, target_utilization: float = 0.7) -> PlacementResult:
        """Run quadratic placement + e-field overlap spreading + legalization."""
        idx_map, A, bx, by = self._build_conn_matrix()
        n = A.shape[0]
        if n == 0:
            return PlacementResult(positions={}, hpwl=0.0, width=0.0, height=0.0)

        # Initial quadratic solution
        x = spsolve(A, bx)
        y = spsolve(A, by)

        cells = list(self.netlist.cells.keys())
        widths = [self._cell_width(self.netlist.cells[c].cell_type) for c in cells]

        # Estimate core area based on target utilization
        total_area = sum(w * self.site_h for w in widths)
        core_area = total_area / target_utilization
        core_w = math.sqrt(core_area * aspect_ratio)
        core_h = core_area / core_w

        # Adaptive bin grid
        bins_x = max(4, int(math.sqrt(n) * 1.5))
        bins_y = max(4, int(bins_x / aspect_ratio))
        bin_w = core_w / bins_x
        bin_h = core_h / bins_y

        poisson_solver = self._build_poisson_solver(bins_x, bins_y)

        # E-field spreading iterations (gradient descent on density potential)
        max_iter = 80
        x_opt = x.copy()
        y_opt = y.copy()
        # seed y with uniform spread so we don't start fully collapsed
        y = np.linspace(0, core_h - self.site_h, n)
        np.random.RandomState(42).shuffle(y)

        for it in range(max_iter):
            density = self._compute_density_map(
                x, y, widths, core_w, core_h, bins_x, bins_y, target_density=target_utilization
            )
            Ex, Ey = self._compute_e_field(density, poisson_solver, bin_w, bin_h)
            fx, fy = self._sample_e_field_at_cells(
                x, y, Ex, Ey, core_w, core_h, bins_x, bins_y
            )

            step = min(bin_w, bin_h) * 0.4 * (1.0 - it / max_iter)
            alpha = 0.02 * (it / max_iter)  # increasing wirelength restoring force

            x = x + step * fx + alpha * (x_opt - x)
            y = y + step * fy + alpha * (y_opt - y)

            # boundary constraints
            for i in range(n):
                x[i] = max(0.0, min(x[i], core_w - widths[i]))
                y[i] = max(0.0, min(y[i], core_h - self.site_h))

            # convergence check
            max_density = float(np.max(density + 0.75))
            if max_density <= 0.85 and it > 10:
                break

        # ------------------------------------------------------------------
        # Legalization: snap y to nearest site row, cap row width to target util
        # ------------------------------------------------------------------
        rows: Dict[int, List[Tuple[str, float, float]]] = {}
        for idx_c, c in enumerate(cells):
            cx = float(x[idx_c])
            cy = float(y[idx_c])
            row = int(round(cy / self.site_h))
            row = max(0, row)
            w = widths[idx_c]
            rows.setdefault(row, []).append((c, cx, w))

        # Pack rows greedily with a width that respects target utilization.
        # We'll start with core_w as pack width, then stretch rows if needed.
        pack_width = core_w
        legal_positions: Dict[str, Tuple[float, float]] = {}
        spill: List[Tuple[str, float, float]] = []
        next_row = max(rows.keys()) + 1 if rows else 0

        def _pack_row(items: List[Tuple[str, float, float]], row_idx: int):
            nonlocal spill
            items.sort(key=lambda t: t[1])
            cur_x = 0.0
            for c, _, w in items:
                if cur_x + w > pack_width and cur_x > 0:
                    spill.append((c, _, w))
                else:
                    legal_positions[c] = (cur_x, row_idx * self.site_h)
                    cur_x += w

        for row in sorted(rows.keys()):
            _pack_row(rows[row], row)

        while spill:
            row = next_row
            next_row += 1
            cur_x = 0.0
            remaining: List[Tuple[str, float, float]] = []
            for c, _, w in spill:
                if cur_x + w > pack_width and cur_x > 0:
                    remaining.append((c, _, w))
                else:
                    legal_positions[c] = (cur_x, row * self.site_h)
                    cur_x += w
            spill = remaining

        # Re-compact rows to remove blank rows
        used_rows = sorted({int(round(cy / self.site_h)) for _, (_, cy) in legal_positions.items()})
        row_remap = {old: new for new, old in enumerate(used_rows)}
        compact_positions: Dict[str, Tuple[float, float]] = {}
        for c, (cx, cy) in legal_positions.items():
            old_row = int(round(cy / self.site_h))
            compact_positions[c] = (cx, row_remap[old_row] * self.site_h)
        legal_positions = compact_positions

        # Stretch rows to achieve target utilization (insert whitespace uniformly)
        num_rows = len(row_remap)
        if num_rows > 0:
            row_lens = [
                sum(self._cell_width(self.netlist.cells[c].cell_type) for c, pos in legal_positions.items() if int(round(pos[1] / self.site_h)) == r)
                for r in range(num_rows)
            ]
            max_row_len = max(row_lens)
            desired_width = total_area / (num_rows * self.site_h * target_utilization)
            if desired_width > max_row_len:
                stretch = desired_width / max_row_len
                stretched: Dict[str, Tuple[float, float]] = {}
                # Group cells by row and compute stretched positions
                row_groups: Dict[int, List[str]] = {}
                for c, (_, cy) in legal_positions.items():
                    row_groups.setdefault(int(round(cy / self.site_h)), []).append(c)
                for row, rcells in row_groups.items():
                    rcells.sort(key=lambda c: legal_positions[c][0])
                    cum = 0.0
                    for c in rcells:
                        w = self._cell_width(self.netlist.cells[c].cell_type)
                        stretched[c] = (cum * stretch, row * self.site_h)
                        cum += w
                legal_positions = stretched

        # Detailed placement: wirelength-driven local reordering within rows
        legal_positions = self._run_detailed_placement(legal_positions)

        # Compute bounding box and HPWL
        max_x = 0.0
        max_y = 0.0
        for c, (cx, cy) in legal_positions.items():
            w = self._cell_width(self.netlist.cells[c].cell_type)
            max_x = max(max_x, cx + w)
            max_y = max(max_y, cy + self.site_h)

        hpwl = self._calc_hpwl(legal_positions)

        return PlacementResult(
            positions=legal_positions,
            hpwl=hpwl,
            width=max_x,
            height=max_y,
        )

    def _run_detailed_placement(
        self, positions: Dict[str, Tuple[float, float]]
    ) -> Dict[str, Tuple[float, float]]:
        """Greedy swap-based detailed placement to reduce local HPWL.
        For large designs we use fast adjacent-swap only to keep runtime reasonable.
        """
        n_cells = len(positions)
        if n_cells > 5000:
            # Skip expensive detailed placement for very large designs
            return positions

        # Build net -> list of cell positions (fast lookup)
        cell_to_nets: Dict[str, List[str]] = {c: [] for c in positions}
        for net_name, net in self.netlist.nets.items():
            cells_on_net = set()
            if net.driver:
                cells_on_net.add(net.driver[0])
            for load_cell, _ in net.loads:
                cells_on_net.add(load_cell)
            for c in cells_on_net:
                if c in cell_to_nets:
                    cell_to_nets[c].append(net_name)

        # Group by row
        rows: Dict[int, List[Tuple[str, float, float]]] = {}
        widths: Dict[str, float] = {}
        for c, (cx, cy) in positions.items():
            row = int(round(cy / self.site_h))
            widths[c] = self._cell_width(self.netlist.cells[c].cell_type)
            rows.setdefault(row, []).append((c, cx, widths[c]))

        for row in rows:
            rows[row].sort(key=lambda t: t[1])

        def _hpwl_delta_for_swap(row_cells: List[str], i: int, j: int, pos: Dict[str, Tuple[float, float]]) -> float:
            ci, cj = row_cells[i], row_cells[j]
            affected_nets = set(cell_to_nets.get(ci, []) + cell_to_nets.get(cj, []))
            old_hpwl = 0.0
            new_hpwl = 0.0
            for net_name in affected_nets:
                net = self.netlist.nets[net_name]
                pins_old = []
                pins_new = []
                for cell_name in ([net.driver[0]] if net.driver else []) + [lc for lc, _ in net.loads]:
                    if cell_name in pos:
                        pins_old.append(pos[cell_name])
                        if cell_name == ci:
                            pins_new.append((pos[cj][0], pos[ci][1]))
                        elif cell_name == cj:
                            pins_new.append((pos[ci][0], pos[cj][1]))
                        else:
                            pins_new.append(pos[cell_name])
                if len(pins_old) < 2:
                    continue
                old_hpwl += max(p[0] for p in pins_old) - min(p[0] for p in pins_old) + max(p[1] for p in pins_old) - min(p[1] for p in pins_old)
                new_hpwl += max(p[0] for p in pins_new) - min(p[0] for p in pins_new) + max(p[1] for p in pins_new) - min(p[1] for p in pins_new)
            return new_hpwl - old_hpwl

        max_passes = 2
        window = 3 if n_cells <= 2000 else 2
        pos = dict(positions)
        for _pass in range(max_passes):
            improved = False
            for row, items in rows.items():
                row_cells = [c for c, _, _ in items]
                n = len(row_cells)
                if n < 2:
                    continue
                original_row_width = max(pos[c][0] + widths[c] for c in row_cells)
                for i in range(n):
                    best_j = None
                    best_delta = 0.0
                    for j in range(i + 1, min(n, i + window)):
                        delta = _hpwl_delta_for_swap(row_cells, i, j, pos)
                        if delta < best_delta:
                            best_delta = delta
                            best_j = j
                    if best_j is not None:
                        row_cells[i], row_cells[best_j] = row_cells[best_j], row_cells[i]
                        improved = True
                # Recompute x positions greedily for this row, then stretch back
                cur_x = 0.0
                new_items = []
                for c in row_cells:
                    pos[c] = (cur_x, row * self.site_h)
                    cur_x += widths[c]
                    new_items.append((c, pos[c][0], widths[c]))
                if cur_x > 0 and original_row_width > cur_x:
                    scale = original_row_width / cur_x
                    for c in row_cells:
                        pos[c] = (pos[c][0] * scale, pos[c][1])
                        new_items = [(c, pos[c][0], widths[c]) for c in row_cells]
                rows[row] = new_items
            if not improved:
                break
        return pos

    def _calc_hpwl(self, positions: Dict[str, Tuple[float, float]]) -> float:
        hpwl = 0.0
        for net in self.netlist.nets.values():
            pins = []
            if net.driver:
                cell = net.driver[0]
                if cell in positions:
                    pins.append(positions[cell])
            for load_cell, _ in net.loads:
                if load_cell in positions and (load_cell, net.driver[1] if net.driver else None) not in [(c, None) for c, _ in net.loads]:
                    pins.append(positions[load_cell])
            if len(pins) < 2:
                continue
            xs = [p[0] for p in pins]
            ys = [p[1] for p in pins]
            hpwl += max(xs) - min(xs) + max(ys) - min(ys)
        return hpwl
