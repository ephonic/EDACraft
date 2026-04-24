"""
rtlgen.routing — Global and Detailed Routing for educational use.

Supports:
- Global routing grid construction with congestion-aware A* search
- Pin concentration to grid cell centers
- Rectilinear Steiner tree via Hanan grid + MST (FLUTE-like behavior)
- Rip-up and re-route for congestion removal
- Detailed routing grid with obstacle avoidance and channel allocation
- Final A* detailed routing
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from rtlgen.netlist import Netlist
from rtlgen.placement import PlacementResult


@dataclass
class RoutingResult:
    global_routes: Dict[str, List[List[Tuple[int, int]]]]  # net -> list of grid point sequences
    detailed_routes: Dict[str, List[List[Tuple[float, float]]]]  # net -> physical point sequences
    global_h_use: np.ndarray = field(repr=False)
    global_v_use: np.ndarray = field(repr=False)


# ------------------------------------------------------------------
# Rectilinear Steiner Tree (Hanan grid + MST)
# ------------------------------------------------------------------

def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _build_steiner_tree(pins: List[Tuple[int, int]]) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Build a rectilinear Steiner tree and return 2-pin edges.
    
    For small nets (<=6 pins) we use Hanan-grid MST for quality.
    For larger nets we fall back to a fast star to the median point
    to keep runtime manageable in pure Python.
    """
    unique_pins = list(dict.fromkeys(pins))
    if len(unique_pins) <= 1:
        return []
    if len(unique_pins) == 2:
        return [(unique_pins[0], unique_pins[1])]

    # Fast star for larger nets (common case in big designs)
    if len(unique_pins) > 6:
        mx = int(round(np.median([p[0] for p in unique_pins])))
        my = int(round(np.median([p[1] for p in unique_pins])))
        center = (mx, my)
        return [(center, p) for p in unique_pins if p != center]

    xs = sorted(set(p[0] for p in unique_pins))
    ys = sorted(set(p[1] for p in unique_pins))
    hanan = [(x, y) for x in xs for y in ys]
    all_pts = list(dict.fromkeys(unique_pins + hanan))
    n = len(all_pts)

    in_mst = [False] * n
    parent = [-1] * n
    heap = [(0, 0, -1)]
    while heap:
        d, u, p = heapq.heappop(heap)
        if in_mst[u]:
            continue
        in_mst[u] = True
        parent[u] = p
        ux, uy = all_pts[u]
        for v in range(n):
            if not in_mst[v]:
                nd = abs(ux - all_pts[v][0]) + abs(uy - all_pts[v][1])
                heapq.heappush(heap, (nd, v, u))

    edges = []
    for v in range(n):
        if parent[v] != -1:
            edges.append((all_pts[parent[v]], all_pts[v]))
    return edges


# ------------------------------------------------------------------
# Global Router
# ------------------------------------------------------------------

class GlobalRouter:
    def __init__(
        self,
        netlist: Netlist,
        placement: PlacementResult,
        cell_widths: Dict[str, float],
        cell_heights: Dict[str, float],
        grid_cols: int = 64,
        grid_rows: int = 64,
        base_penalty: float = 2.0,
        pin_access: Optional[Dict[str, Dict[str, Tuple[float, float]]]] = None,
    ):
        self.netlist = netlist
        self.placement = placement
        self.cell_widths = cell_widths
        self.cell_heights = cell_heights
        self.cols = max(2, grid_cols)
        self.rows = max(2, grid_rows)
        self.width = max(1.0, placement.width)
        self.height = max(1.0, placement.height)
        self.grid_w = self.width / self.cols
        self.grid_h = self.height / self.rows
        self.base_penalty = base_penalty
        self.pin_access = pin_access or {}

        # Capacities roughly proportional to length (in grid units)
        # Assume routing pitch ~1.0, so a grid edge of length L can fit ~L tracks.
        # Scale by 1.5 to account for multiple metal layers / over-the-cell routing.
        h_cap_val = max(3, int(round(self.grid_w * 3.0)))
        v_cap_val = max(3, int(round(self.grid_h * 3.0)))
        self.h_cap = np.full((self.rows, max(1, self.cols - 1)), h_cap_val, dtype=int)
        self.v_cap = np.full((max(1, self.rows - 1), self.cols), v_cap_val, dtype=int)
        self.h_use = np.zeros_like(self.h_cap)
        self.v_use = np.zeros_like(self.v_cap)

        # Net -> 2-pin segment list (grid points)
        self.net_routes: Dict[str, List[List[Tuple[int, int]]]] = {}

    def _cell_to_grid(self, cell_name: str) -> Tuple[int, int]:
        x, y = self.placement.positions[cell_name]
        w = self.cell_widths.get(cell_name, 1.0)
        h = self.cell_heights.get(cell_name, 1.0)
        cx = x + w / 2.0
        cy = y + h / 2.0
        gx = min(self.cols - 1, max(0, int(cx / self.grid_w)))
        gy = min(self.rows - 1, max(0, int(cy / self.grid_h)))
        return gx, gy

    def _edge_cost(self, x: int, y: int, nx: int, ny: int) -> float:
        """Cost of moving from (x,y) to (nx,ny)."""
        if x == nx:
            # vertical move
            ey = min(y, ny)
            ex = x
            if ey < 0 or ey >= self.v_use.shape[0] or ex < 0 or ex >= self.v_use.shape[1]:
                return float('inf')
            used = self.v_use[ey, ex]
            cap = self.v_cap[ey, ex]
            overflow = max(0, used + 1 - cap)
            return 1.0 + self.base_penalty * (overflow / max(1, cap))
        elif y == ny:
            # horizontal move
            ex = min(x, nx)
            ey = y
            if ey < 0 or ey >= self.h_use.shape[0] or ex < 0 or ex >= self.h_use.shape[1]:
                return float('inf')
            used = self.h_use[ey, ex]
            cap = self.h_cap[ey, ex]
            overflow = max(0, used + 1 - cap)
            return 1.0 + self.base_penalty * (overflow / max(1, cap))
        else:
            return float('inf')

    def _astar(self, src: Tuple[int, int], dst: Tuple[int, int]) -> List[Tuple[int, int]]:
        """A* on the global routing grid with L-shape fast path."""
        if src == dst:
            return [src]
        sx, sy = src
        tx, ty = dst

        # Generate both L-shapes
        hv = []
        cx, cy = sx, sy
        while cx != tx:
            cx += 1 if tx > cx else -1
            hv.append((cx, cy))
        while cy != ty:
            cy += 1 if ty > cy else -1
            hv.append((cx, cy))

        vh = []
        cx, cy = sx, sy
        while cy != ty:
            cy += 1 if ty > cy else -1
            vh.append((cx, cy))
        while cx != tx:
            cx += 1 if tx > cx else -1
            vh.append((cx, cy))

        def _path_free(path):
            prev = src
            for p in path:
                if math.isinf(self._edge_cost(prev[0], prev[1], p[0], p[1])):
                    return False
                prev = p
            return True

        free_hv = _path_free(hv)
        free_vh = _path_free(vh)
        if free_hv and free_vh:
            return [src] + (hv if len(hv) <= len(vh) else vh)
        if free_hv:
            return [src] + hv
        if free_vh:
            return [src] + vh

        # Maze routing fallback
        open_set = [(0.0, 0.0, sx, sy)]
        gscore: Dict[Tuple[int, int], float] = {(sx, sy): 0.0}
        parent: Dict[Tuple[int, int], Tuple[int, int]] = {}
        visited: Set[Tuple[int, int]] = set()

        while open_set:
            _, g, x, y = heapq.heappop(open_set)
            if (x, y) in visited:
                continue
            visited.add((x, y))
            if (x, y) == dst:
                path = []
                cur: Optional[Tuple[int, int]] = dst
                while cur is not None:
                    path.append(cur)
                    cur = parent.get(cur)
                return path[::-1]

            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < self.cols and 0 <= ny_ < self.rows):
                    continue
                step_cost = self._edge_cost(x, y, nx_, ny_)
                if math.isinf(step_cost):
                    continue
                nxt = (nx_, ny_)
                ng = g + step_cost
                if ng < gscore.get(nxt, float('inf')):
                    gscore[nxt] = ng
                    parent[nxt] = (x, y)
                    h = abs(nx_ - tx) + abs(ny_ - ty)
                    heapq.heappush(open_set, (ng + h, ng, nx_, ny_))

        return [src] + hv

    def _add_route_to_usage(self, path: List[Tuple[int, int]], delta: int = 1):
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            if x1 == x2:
                ey = min(y1, y2)
                ex = x1
                if 0 <= ey < self.v_use.shape[0] and 0 <= ex < self.v_use.shape[1]:
                    self.v_use[ey, ex] += delta
            elif y1 == y2:
                ex = min(x1, x2)
                ey = y1
                if 0 <= ey < self.h_use.shape[0] and 0 <= ex < self.h_use.shape[1]:
                    self.h_use[ey, ex] += delta

    def _net_pins_to_grid(self, net_name: str) -> List[Tuple[int, int]]:
        """Collect unique grid points for all pins on the net."""
        net = self.netlist.nets[net_name]
        seen: Set[Tuple[int, int]] = set()
        pts: List[Tuple[int, int]] = []

        def add(x: float, y: float):
            gx = min(self.cols - 1, max(0, int(x / self.grid_w)))
            gy = min(self.rows - 1, max(0, int(y / self.grid_h)))
            if (gx, gy) not in seen:
                seen.add((gx, gy))
                pts.append((gx, gy))

        def proc(cell_name: str, pin_name: Optional[str]):
            if cell_name not in self.placement.positions:
                return
            if self.pin_access and cell_name in self.pin_access and pin_name in self.pin_access[cell_name]:
                add(*self.pin_access[cell_name][pin_name])
            else:
                add(*self.placement.positions[cell_name])

        if net.driver:
            proc(net.driver[0], net.driver[1])
        for load_cell, load_pin in net.loads:
            proc(load_cell, load_pin)
        return pts

    def _route_net(self, net_name: str) -> List[List[Tuple[int, int]]]:
        """Route a single net and return list of 2-pin grid paths."""
        pins = self._net_pins_to_grid(net_name)
        if len(pins) < 2:
            return []

        edges = _build_steiner_tree(pins)
        segments: List[List[Tuple[int, int]]] = []
        for a, b in edges:
            path = self._astar(a, b)
            segments.append(path)
            self._add_route_to_usage(path, +1)
        return segments

    def _rip_up_net(self, net_name: str):
        for path in self.net_routes.get(net_name, []):
            self._add_route_to_usage(path, -1)

    def _overflow_score(self) -> float:
        h_over = np.maximum(0, self.h_use - self.h_cap).sum()
        v_over = np.maximum(0, self.v_use - self.v_cap).sum()
        return float(h_over + v_over)

    def route(self, max_iterations: int = 3) -> RoutingResult:
        """Run global routing with rip-up and re-route."""
        net_names = list(self.netlist.nets.keys())

        # Pass 1: initial routing
        print("Global routing: pass 1 (initial)...")
        for name in net_names:
            self.net_routes[name] = self._route_net(name)

        # Pass 2+: R&R with increasing penalty
        for it in range(1, max_iterations):
            overflow = self._overflow_score()
            print(f"Global routing: pass {it + 1}, overflow = {overflow:.0f}")
            if overflow == 0:
                break
            self.base_penalty *= 2.0
            # Sort nets by number of overflowed edges (descending)
            net_scores = []
            for name in net_names:
                score = 0
                for path in self.net_routes.get(name, []):
                    for i in range(len(path) - 1):
                        x1, y1 = path[i]
                        x2, y2 = path[i + 1]
                        if x1 == x2:
                            ey, ex = min(y1, y2), x1
                            if 0 <= ey < self.v_use.shape[0] and 0 <= ex < self.v_use.shape[1]:
                                if self.v_use[ey, ex] > self.v_cap[ey, ex]:
                                    score += 1
                        else:
                            ey, ex = y1, min(x1, x2)
                            if 0 <= ey < self.h_use.shape[0] and 0 <= ex < self.h_use.shape[1]:
                                if self.h_use[ey, ex] > self.h_cap[ey, ex]:
                                    score += 1
                if score > 0:
                    net_scores.append((score, name))
            net_scores.sort(reverse=True)
            for _, name in net_scores:
                self._rip_up_net(name)
                self.net_routes[name] = self._route_net(name)

        return RoutingResult(
            global_routes=dict(self.net_routes),
            detailed_routes={},
            global_h_use=self.h_use.copy(),
            global_v_use=self.v_use.copy(),
        )


# ------------------------------------------------------------------
# Detailed Router
# ------------------------------------------------------------------

class DetailedRouter:
    def __init__(
        self,
        netlist: Netlist,
        placement: PlacementResult,
        global_result: RoutingResult,
        cell_widths: Dict[str, float],
        cell_heights: Dict[str, float],
        resolution: float = 0.5,
        margin: float = 0.1,
        pin_access: Optional[Dict[str, Dict[str, Tuple[float, float]]]] = None,
    ):
        self.netlist = netlist
        self.placement = placement
        self.global_result = global_result
        self.cell_widths = cell_widths
        self.cell_heights = cell_heights
        self.res = resolution
        self.margin = margin
        self.pin_access = pin_access or {}

        self.dcols = max(1, int(math.ceil(placement.width / resolution)))
        self.drows = max(1, int(math.ceil(placement.height / resolution)))

        # Obstacle map: True = blocked (cell + margin)
        self.obstacle = np.zeros((self.drows, self.dcols), dtype=bool)
        for cname, (cx, cy) in placement.positions.items():
            w = cell_widths.get(cname, 1.0)
            h = cell_heights.get(cname, 1.0)
            x1 = max(0, int(math.floor((cx - margin) / resolution)))
            x2 = min(self.dcols - 1, int(math.ceil((cx + w + margin) / resolution)))
            y1 = max(0, int(math.floor((cy - margin) / resolution)))
            y2 = min(self.drows - 1, int(math.ceil((cy + h + margin) / resolution)))
            self.obstacle[y1:y2 + 1, x1:x2 + 1] = True

        # Track usage for channel allocation (horizontal / vertical occupancy)
        self.h_occ = np.zeros((self.drows, max(1, self.dcols - 1)), dtype=int)
        self.v_occ = np.zeros((max(1, self.drows - 1), self.dcols), dtype=int)

        self.detailed_routes: Dict[str, List[List[Tuple[float, float]]]] = {}

    def _to_detailed(self, x: float, y: float) -> Tuple[int, int]:
        dx = min(self.dcols - 1, max(0, int(round(x / self.res))))
        dy = min(self.drows - 1, max(0, int(round(y / self.res))))
        return dx, dy

    def _to_phys(self, dx: int, dy: int) -> Tuple[float, float]:
        return dx * self.res, dy * self.res

    def _detailed_edge_cost(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Cost for moving on detailed grid."""
        # Blocked if either endpoint is inside obstacle
        if self.obstacle[y1, x1] or self.obstacle[y2, x2]:
            return float('inf')
        base = 1.0
        if x1 == x2:
            ey = min(y1, y2)
            ex = x1
            if 0 <= ey < self.v_occ.shape[0] and 0 <= ex < self.v_occ.shape[1]:
                base += self.v_occ[ey, ex] * 0.5
        elif y1 == y2:
            ey = y1
            ex = min(x1, x2)
            if 0 <= ey < self.h_occ.shape[0] and 0 <= ex < self.h_occ.shape[1]:
                base += self.h_occ[ey, ex] * 0.5
        return base

    def _try_lshape(
        self,
        src: Tuple[int, int],
        dst: Tuple[int, int],
        corridor_mask: np.ndarray,
    ) -> Optional[List[Tuple[int, int]]]:
        """Try both L-shapes and return the shorter valid one."""
        if src == dst:
            return [src]
        sx, sy = src
        tx, ty = dst

        # L-shape 1: horizontal then vertical
        path1 = []
        x, y = sx, sy
        while x != tx:
            x += 1 if tx > x else -1
            path1.append((x, y))
        while y != ty:
            y += 1 if ty > y else -1
            path1.append((x, y))
        valid1 = all(
            0 <= px < self.dcols and 0 <= py < self.drows
            and corridor_mask[py, px]
            and not self.obstacle[py, px]
            for px, py in path1
        )

        # L-shape 2: vertical then horizontal
        path2 = []
        x, y = sx, sy
        while y != ty:
            y += 1 if ty > y else -1
            path2.append((x, y))
        while x != tx:
            x += 1 if tx > x else -1
            path2.append((x, y))
        valid2 = all(
            0 <= px < self.dcols and 0 <= py < self.drows
            and corridor_mask[py, px]
            and not self.obstacle[py, px]
            for px, py in path2
        )

        if valid1 and valid2:
            return path1 if len(path1) <= len(path2) else path2
        if valid1:
            return path1
        if valid2:
            return path2
        return None

    def _astar_detailed(
        self,
        src: Tuple[int, int],
        dst: Tuple[int, int],
        corridor_mask: np.ndarray,
    ) -> List[Tuple[int, int]]:
        """A* on detailed grid restricted to corridor mask."""
        if src == dst:
            return [src]
        sx, sy = src
        tx, ty = dst

        # Fast path: try L-shapes first
        lpath = self._try_lshape(src, dst, corridor_mask)
        if lpath is not None:
            return [src] + lpath

        # Maze routing with int-indexed dicts for speed
        dc = self.dcols
        def _idx(x, y): return y * dc + x
        gscore: Dict[int, float] = {_idx(sx, sy): 0.0}
        parent: Dict[int, int] = {}
        visited: Set[int] = set()
        heap = [(0.0, _idx(sx, sy), sx, sy)]
        target_idx = _idx(tx, ty)

        while heap:
            _, uidx, x, y = heapq.heappop(heap)
            if uidx in visited:
                continue
            visited.add(uidx)
            if uidx == target_idx:
                path = []
                cur = target_idx
                while cur in parent:
                    cx = cur % dc
                    cy = cur // dc
                    path.append((cx, cy))
                    cur = parent[cur]
                path.append((sx, sy))
                return path[::-1]

            cg = gscore[uidx]
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < self.dcols and 0 <= ny_ < self.drows):
                    continue
                if not corridor_mask[ny_, nx_]:
                    continue
                cost = self._detailed_edge_cost(x, y, nx_, ny_)
                if math.isinf(cost):
                    continue
                nidx = _idx(nx_, ny_)
                ng = cg + cost
                if ng < gscore.get(nidx, float('inf')):
                    gscore[nidx] = ng
                    parent[nidx] = uidx
                    h = abs(nx_ - tx) + abs(ny_ - ty)
                    heapq.heappush(heap, (ng + h, nidx, nx_, ny_))

        # Fallback L-shape (ignore obstacles)
        path = [src]
        cx, cy = sx, sy
        while cx != tx:
            cx += 1 if tx > cx else -1
            path.append((cx, cy))
        while cy != ty:
            cy += 1 if ty > cy else -1
            path.append((cx, cy))
        return path

    def _add_detailed_usage(self, path: List[Tuple[int, int]]):
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            if x1 == x2:
                ey = min(y1, y2)
                ex = x1
                if 0 <= ey < self.v_occ.shape[0] and 0 <= ex < self.v_occ.shape[1]:
                    self.v_occ[ey, ex] += 1
            elif y1 == y2:
                ey = y1
                ex = min(x1, x2)
                if 0 <= ey < self.h_occ.shape[0] and 0 <= ex < self.h_occ.shape[1]:
                    self.h_occ[ey, ex] += 1

    def _build_corridor_mask(self, global_path: List[Tuple[int, int]]) -> np.ndarray:
        """Expand global grid path to a detailed grid corridor mask (+/- 1 global cell)."""
        mask = np.zeros((self.drows, self.dcols), dtype=bool)
        for gx, gy in global_path:
            cx0 = max(0, int(gx * self.global_w / self.res - 1))
            cx1 = min(self.dcols - 1, int((gx + 1) * self.global_w / self.res + 1))
            cy0 = max(0, int(gy * self.global_h / self.res - 1))
            cy1 = min(self.drows - 1, int((gy + 1) * self.global_h / self.res + 1))
            mask[cy0:cy1 + 1, cx0:cx1 + 1] = True
        return mask

    def route(self) -> RoutingResult:
        """Run detailed routing for all globally routed nets."""
        grouter = self.global_result
        self.global_w = self.placement.width / max(1, grouter.global_h_use.shape[1] + 1)
        self.global_h = self.placement.height / max(1, grouter.global_h_use.shape[0])

        # Precompute precise pin access points mapped to detailed grid per net
        net_pin_access: Dict[str, Dict[Tuple[int, int], Tuple[float, float]]] = {}
        for name in grouter.global_routes:
            if not grouter.global_routes[name]:
                continue
            net = self.netlist.nets[name]
            d: Dict[Tuple[int, int], Tuple[float, float]] = {}
            def _add_pin(cell_name: str, pin_name: str):
                if cell_name not in self.placement.positions:
                    return
                if cell_name in self.pin_access and pin_name in self.pin_access[cell_name]:
                    phys = self.pin_access[cell_name][pin_name]
                else:
                    phys = self.placement.positions[cell_name]
                dg = self._to_detailed(phys[0], phys[1])
                d[dg] = phys
            if net.driver:
                _add_pin(net.driver[0], net.driver[1])
            for lc, lp in net.loads:
                _add_pin(lc, lp)
            net_pin_access[name] = d

        net_names = [n for n in grouter.global_routes if grouter.global_routes[n]]
        total = len(net_names)
        for idx, name in enumerate(net_names):
            if idx % 2000 == 0:
                print(f"Detailed routing: {idx}/{total} nets done...", flush=True)
            segments: List[List[Tuple[float, float]]] = []
            for gpath in grouter.global_routes[name]:
                if len(gpath) < 2:
                    continue
                # Map global path endpoints to physical centers (fallback)
                src_gx, src_gy = gpath[0]
                dst_gx, dst_gy = gpath[-1]
                src_x = (src_gx + 0.5) * self.global_w
                src_y = (src_gy + 0.5) * self.global_h
                dst_x = (dst_gx + 0.5) * self.global_w
                dst_y = (dst_gy + 0.5) * self.global_h

                # Use pin access precise coords when available
                src_d_fallback = self._to_detailed(src_x, src_y)
                dst_d_fallback = self._to_detailed(dst_x, dst_y)
                src_x, src_y = net_pin_access[name].get(src_d_fallback, (src_x, src_y))
                dst_x, dst_y = net_pin_access[name].get(dst_d_fallback, (dst_x, dst_y))

                src_d = self._to_detailed(src_x, src_y)
                dst_d = self._to_detailed(dst_x, dst_y)
                corridor_mask = self._build_corridor_mask(gpath)
                dpath = self._astar_detailed(src_d, dst_d, corridor_mask)
                self._add_detailed_usage(dpath)
                phys_path = [self._to_phys(dx, dy) for dx, dy in dpath]
                segments.append(phys_path)
            self.detailed_routes[name] = segments

        print(f"Detailed routing: completed {total} nets.", flush=True)
        return RoutingResult(
            global_routes=grouter.global_routes,
            detailed_routes=self.detailed_routes,
            global_h_use=grouter.global_h_use,
            global_v_use=grouter.global_v_use,
        )
