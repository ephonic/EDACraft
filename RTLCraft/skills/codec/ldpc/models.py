"""
skills.codec.ldpc.models — LDPC Decoder Behavioral Models

Golden reference models for LDPC Min-Sum decoder verification:
  - LDPCDecoder_Model: Top-level cycle-accurate behavioral model
  - CheckNode_Model: Per-check-node Min-Sum behavior
  - VarNode_Model: Per-variable-node behavior
  - minsum_decode: Pure-Python Min-Sum decoder (from design_ldpc.py)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# Min-Sum Golden Reference Decoder
# =====================================================================

def minsum_decode(
    llr_list: List[int],
    H: List[List[int]],
    max_iter: int = 25,
    prec: int = 4,
) -> Tuple[List[int], List[int], int, bool]:
    """Min-Sum LDPC decoder — golden reference for verification.

    Args:
        llr_list: list of N signed integers (LLR values)
        H: M×N binary parity-check matrix
        max_iter: maximum decoding iterations
        prec: message precision (for saturation emulation)

    Returns:
        (P_v_list, x_list, num_iter, converged)
    """
    m = len(H)
    n = len(H[0])

    # Build edge list
    edges: List[Tuple[int, int]] = []
    vn_edge_map: List[List[int]] = [[] for _ in range(n)]
    cn_edge_map: List[List[int]] = [[] for _ in range(m)]
    for c in range(m):
        for v in range(n):
            if H[c][v]:
                eidx = len(edges)
                edges.append((v, c))
                vn_edge_map[v].append(eidx)
                cn_edge_map[c].append(eidx)

    # Initialize Q = llr for all edges
    Q = [llr_list[v] for v, c in edges]
    R = [0] * len(edges)

    pmax = (1 << (prec - 1)) - 1
    pmin = -(1 << (prec - 1))

    def saturate(val: int) -> int:
        if val > pmax:
            return pmax
        if val < pmin:
            return pmin
        return val

    num_iter = 0
    converged = False

    for iteration in range(max_iter):
        # --- CheckNode update ---
        for c in range(m):
            eidxs = cn_edge_map[c]
            q_vals = [Q[e] for e in eidxs]
            signs = [1 if q < 0 else 0 for q in q_vals]
            abs_q = [abs(q) for q in q_vals]
            sign_prod = sum(signs) & 1

            sorted_abs = sorted((abs_q[i], i) for i in range(len(abs_q)))
            min1 = sorted_abs[0][0]
            min2 = sorted_abs[1][0] if len(sorted_abs) > 1 else min1

            for i, eidx in enumerate(eidxs):
                s = sign_prod ^ signs[i]
                use_min = min2 if abs_q[i] == min1 else min1
                R[eidx] = saturate(-use_min if s else use_min)

        # --- VarNode update ---
        P_v = [0] * n
        for v in range(n):
            sum_r = sum(R[e] for e in vn_edge_map[v])
            P_v[v] = saturate(llr_list[v] + sum_r)
            for e in vn_edge_map[v]:
                Q[e] = saturate(P_v[v] - R[e])

        # --- Hard decision ---
        x = [1 if P_v[v] < 0 else 0 for v in range(n)]

        # --- Parity check ---
        all_zero = True
        for c in range(m):
            parity = sum(x[v] for v in range(n) if H[c][v]) & 1
            if parity != 0:
                all_zero = False
                break

        num_iter = iteration + 1
        if all_zero:
            converged = True
            break

    return P_v, x, num_iter, converged


# =====================================================================
# CheckNode Model
# =====================================================================

class CheckNode_Model:
    """Min-Sum check node behavioral model.

    Tracks registered R outputs and computes min/second-min from |Q| inputs.
    """

    def __init__(self, num_connections: int = 6, prec: int = 4):
        self.num_connections = num_connections
        self.prec = prec
        self.pmax = (1 << (prec - 1)) - 1
        self.pmin = -(1 << (prec - 1))
        self.Rreg = [0] * num_connections

    def step(self, Qwires: int, rst: int = 0) -> int:
        """Execute one cycle. Returns packed Rwires (registered output).

        Args:
            Qwires: packed Q values (num_connections * prec bits)
            rst: reset signal
        """
        if rst:
            self.Rreg = [0] * self.num_connections
            return self._pack_R()

        # Extract Q values
        q_vals = []
        for i in range(self.num_connections):
            raw = (Qwires >> (i * self.prec)) & ((1 << self.prec) - 1)
            if raw >= (1 << (self.prec - 1)):
                raw -= (1 << self.prec)
            q_vals.append(raw)

        signs = [1 if q < 0 else 0 for q in q_vals]
        abs_q = [abs(q) for q in q_vals]
        sign_product = sum(signs) & 1

        sorted_abs = sorted((abs_q[i], i) for i in range(self.num_connections))
        min1 = sorted_abs[0][0]
        min2 = sorted_abs[1][0] if self.num_connections > 1 else min1

        # Compute new R
        for i in range(self.num_connections):
            s = sign_product ^ signs[i]
            use_min = min2 if abs_q[i] == min1 else min1
            r_val = -use_min if s else use_min
            self.Rreg[i] = self._saturate(r_val)

        return self._pack_R()

    def _saturate(self, val: int) -> int:
        if val > self.pmax:
            return self.pmax
        if val < self.pmin:
            return self.pmin
        return val

    def _pack_R(self) -> int:
        packed = 0
        for i in range(self.num_connections - 1, -1, -1):
            packed = (packed << self.prec) | (self.Rreg[i] & ((1 << self.prec) - 1))
        return packed


# =====================================================================
# VarNode Model
# =====================================================================

class VarNode_Model:
    """Variable node behavioral model.

    Computes P_v = saturate(llr + sum_R), Q_i = saturate(P_v - R_i).
    Registered Qwires output (1-cycle latency).
    """

    def __init__(self, num_connections: int = 3, prec: int = 4):
        self.num_connections = num_connections
        self.prec = prec
        self.pmax = (1 << (prec - 1)) - 1
        self.pmin = -(1 << (prec - 1))
        self.Qreg = 0

    def step(self, llr: int, Rwires: int, rst: int = 0) -> Tuple[int, int, int]:
        """Execute one cycle. Returns (P_v, x, packed_Qwires).

        Args:
            llr: LLR input (signed)
            Rwires: packed R values (num_connections * prec bits)
            rst: reset signal
        """
        if rst:
            self.Qreg = 0
            return 0, 0, 0

        # Extract R values
        r_vals = []
        for i in range(self.num_connections):
            raw = (Rwires >> (i * self.prec)) & ((1 << self.prec) - 1)
            if raw >= (1 << (self.prec - 1)):
                raw -= (1 << self.prec)
            r_vals.append(raw)

        # Saturating sum tree
        tree = list(r_vals)
        while len(tree) > 1:
            next_tree = []
            for j in range(0, len(tree) - 1, 2):
                next_tree.append(self._sat(tree[j] + tree[j + 1]))
            if len(tree) % 2 == 1:
                next_tree.append(tree[-1])
            tree = next_tree
        sum_r = tree[0] if tree else 0

        # P_v and hard decision
        p_v = self._sat(sum_r + llr)
        x = 1 if p_v < 0 else 0

        # Q_i = P_v - R_i
        q_vals = []
        for i in range(self.num_connections):
            q_i = self._sat(p_v - r_vals[i])
            q_vals.append(q_i)

        # Pack into Qreg (registered output)
        packed = 0
        for i in range(self.num_connections - 1, -1, -1):
            packed = (packed << self.prec) | (q_vals[i] & ((1 << self.prec) - 1))
        self.Qreg = packed

        return p_v & ((1 << self.prec) - 1), x, self.Qreg

    def _sat(self, val: int) -> int:
        if val > self.pmax:
            return self.pmax
        if val < self.pmin:
            return self.pmin
        return val


# =====================================================================
# LDPC Decoder Top-Level Model
# =====================================================================

class LDPCDecoder_Model:
    """Top-level LDPC decoder behavioral model.

    Runs Min-Sum iterations cycle-by-cycle until convergence or max_iter.

    Usage:
        model = LDPCDecoder_Model(H=H_matrix, prec=4, max_iter=25)
        model.load_llrs(llr_values)
        for _ in range(30):
            done = model.cycle()
            if done:
                break
        print(f"Decoded in {model.iterations} iterations, converged={model.converged}")
    """

    def __init__(
        self,
        H: List[List[int]],
        prec: int = 4,
        max_iter: int = 25,
    ):
        self.H = H
        self.m = len(H)
        self.n = len(H[0])
        self.prec = prec
        self.max_iter = max_iter
        self.pmax = (1 << (prec - 1)) - 1
        self.pmin = -(1 << (prec - 1))

        # Build edge maps
        self.edges: List[Tuple[int, int]] = []
        self.vn_edge_map: List[List[int]] = [[] for _ in range(self.n)]
        self.cn_edge_map: List[List[int]] = [[] for _ in range(self.m)]
        for c in range(self.m):
            for v in range(self.n):
                if H[c][v]:
                    eidx = len(self.edges)
                    self.edges.append((v, c))
                    self.vn_edge_map[v].append(eidx)
                    self.cn_edge_map[c].append(eidx)

        # State
        self.Q: List[int] = []
        self.R: List[int] = []
        self.P_v: List[int] = []
        self.x: List[int] = []
        self.iterations = 0
        self.converged = False
        self._done = False
        self._rst = True

    def load_llrs(self, llr_list: List[int]):
        """Load LLR inputs and initialize decoder state."""
        assert len(llr_list) == self.n, f"Expected {self.n} LLRs, got {len(llr_list)}"
        self.Q = [llr_list[v] for v, c in self.edges]
        self.R = [0] * len(self.edges)
        self.P_v = [0] * self.n
        self.x = [0] * self.n
        self.iterations = 0
        self.converged = False
        self._done = False
        self._rst = False

    def cycle(self) -> bool:
        """Execute one decoding iteration. Returns done flag."""
        if self._rst:
            return False

        if self._done:
            return True

        self._decode_iteration()
        self.iterations += 1

        # Parity check
        all_zero = True
        for c in range(self.m):
            parity = sum(self.x[v] for v in range(self.n) if self.H[c][v]) & 1
            if parity != 0:
                all_zero = False
                break

        if all_zero or self.iterations >= self.max_iter:
            self._done = True
            self.converged = all_zero

        return self._done

    def _decode_iteration(self):
        """One Min-Sum iteration."""
        def sat(val: int) -> int:
            if val > self.pmax:
                return self.pmax
            if val < self.pmin:
                return self.pmin
            return val

        # CheckNode update
        for c in range(self.m):
            eidxs = self.cn_edge_map[c]
            q_vals = [self.Q[e] for e in eidxs]
            signs = [1 if q < 0 else 0 for q in q_vals]
            abs_q = [abs(q) for q in q_vals]
            sign_prod = sum(signs) & 1

            sorted_abs = sorted((abs_q[i], i) for i in range(len(abs_q)))
            min1 = sorted_abs[0][0]
            min2 = sorted_abs[1][0] if len(sorted_abs) > 1 else min1

            for i, eidx in enumerate(eidxs):
                s = sign_prod ^ signs[i]
                use_min = min2 if abs_q[i] == min1 else min1
                self.R[eidx] = sat(-use_min if s else use_min)

        # VarNode update
        for v in range(self.n):
            sum_r = sum(self.R[e] for e in self.vn_edge_map[v])
            self.P_v[v] = sat(self.Q[0] if not self.vn_edge_map[v] else self.Q[self.vn_edge_map[v][0]] - self.R[self.vn_edge_map[v][0]] if self.vn_edge_map[v] else 0)
            # Actually: P_v = sat(llr + sum_R), but llr = Q[e] - R[e] initially
            # For cycle-accurate model, we track edge Q/R, so:
            # llr[v] can be recovered from Q[e] - R[e] for any edge e
            if self.vn_edge_map[v]:
                llr_v = sat(self.Q[self.vn_edge_map[v][0]] - self.R[self.vn_edge_map[v][0]])
            else:
                llr_v = 0
            self.P_v[v] = sat(llr_v + sum_r)
            self.x[v] = 1 if self.P_v[v] < 0 else 0
            for e in self.vn_edge_map[v]:
                self.Q[e] = sat(self.P_v[v] - self.R[e])

    def get_outputs(self) -> Dict[str, Any]:
        """Get current decoder outputs."""
        return {
            "P_v": self.P_v,
            "x": self.x,
            "iterations": self.iterations,
            "converged": self.converged,
            "done": self._done,
        }
