"""
Spec2RTL Design Flow: LDPC Decoder — Low-Density Parity-Check Decoder
======================================================================

Reference: ref_rtl/LDPC_Decoder (WiMax 802.16e LDPC, rate-1/2, n=576, prec=4)

This design implements a parameterizable LDPC decoder using the Min-Sum
algorithm. The default configuration uses a scaled WiMax H matrix (z=1,
n=24) for manageable Verilog generation, but all submodules are fully
parameterizable and the H matrix can be swapped for larger codes.

Algorithm (one iteration per clock cycle):
  1. VarNode:  P_v = llr + Σ(R_messages)   [saturating quantized]
               Q_i = P_v - R_i              [saturating quantized, per edge]
               x   = sign(P_v)
  2. CheckNode: sign_product = XOR of all Q signs
                min1, min2   = two smallest |Q|
                R_i = (sign_product ⊕ Q_sign_i) ? -min : min
                (if |Q_i| == min1, use min2 instead)
  3. Control:  count iterations; done when count==MAX_ITER or all checks pass

Module hierarchy:
  LDPC_Decoder (parameterized by H matrix)
    ├── VarNode[N]    (variable node, degree from H matrix column)
    ├── CheckNode[M]  (check node, degree from H matrix row)
    ├── Comparator    (min/second-min tree node)
    ├── QuantizedAdder     (saturating signed add)
    └── QuantizedSubber    (saturating signed subtract)
"""

from __future__ import annotations
import os, sys, math
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
    Algorithm_Model, datapath_template,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const,
    Memory, Parameter, LocalParam,
)
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Switch, ForGen, GenIf, GenElse
from rtlgen.codegen import VerilogEmitter, EmitProfile, ModuleDocTemplate, fill_doc_template
from rtlgen.ppa_optimizer import PPAOptimizer, SpecIR

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

# ============================================================================
# WiMax 802.16e LDPC Base Matrix (Rate 1/2)
# ============================================================================
# From InitializeWiMaxLDPC.m — this is the 12×24 base matrix Hbm.
# For z=1, each non-negative entry becomes 1 and -1 becomes 0, giving H directly.
# For larger z, each entry expands to a z×z circulant permutation matrix.
# ============================================================================
_HBM_RATE_1_2 = [
    [-1, 94, 73, -1, -1, -1, -1, -1, 55, 83, -1, -1, 7, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 27, -1, -1, -1, 22, 79, 9, -1, -1, -1, 12, -1, 0, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 24, 22, 81, -1, 33, -1, -1, -1, 0, -1, -1, 0, 0, -1, -1, -1, -1, -1, -1, -1, -1],
    [61, -1, 47, -1, -1, -1, -1, -1, 65, 25, -1, -1, -1, -1, -1, 0, 0, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 39, -1, -1, -1, 84, -1, -1, 41, 72, -1, -1, -1, -1, -1, 0, 0, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 46, 40, -1, 82, -1, -1, -1, 79, 0, -1, -1, -1, -1, 0, 0, -1, -1, -1, -1, -1],
    [-1, -1, 95, 53, -1, -1, -1, -1, -1, 14, 18, -1, -1, -1, -1, -1, -1, -1, 0, 0, -1, -1, -1, -1],
    [-1, 11, 73, -1, -1, -1, 2, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0, -1, -1, -1],
    [12, -1, -1, -1, 83, 24, -1, 43, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0, -1, -1],
    [-1, -1, -1, -1, -1, 94, -1, 59, -1, -1, 70, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0, -1],
    [-1, -1, 7, 65, -1, -1, -1, -1, 39, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0],
    [43, -1, -1, -1, -1, 66, -1, 41, -1, -1, -1, 26, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],
]


def build_ldpc_params(Hbm, z=1):
    """Build LDPC parameters from base matrix Hbm and expansion factor z.

    For z=1: H is the binary matrix directly derived from Hbm.
    For z>1: Hbm entries expand to z×z circulant permutation matrices.
    """
    m_b = len(Hbm)
    n_b = len(Hbm[0])
    m = m_b * z
    n = n_b * z

    # For z=1: simple binary expansion
    if z == 1:
        H = [[1 if Hbm[i][j] != -1 else 0 for j in range(n_b)] for i in range(m_b)]
    else:
        # For z>1: expand each entry to z×z circulant
        H = [[0] * n for _ in range(m)]
        for i_b in range(m_b):
            for j_b in range(n_b):
                val = Hbm[i_b][j_b]
                if val == -1:
                    continue
                elif val == 0:
                    # Identity matrix
                    for k in range(z):
                        H[i_b * z + k][j_b * z + k] = 1
                else:
                    # Circulant permutation matrix
                    shift = (val * z) // 96  # standard WiMax formula
                    for k in range(z):
                        col = (k + shift) % z
                        H[i_b * z + k][j_b * z + col] = 1

    vn_degrees = [sum(H[row][col] for row in range(m)) for col in range(n)]
    cn_degrees = [sum(H[row][col] for col in range(n)) for row in range(m)]
    vn_edges = [[r for r in range(m) if H[r][c]] for c in range(n)]
    cn_edges = [[c for c in range(n) if H[r][c]] for r in range(m)]

    return {
        "n": n, "m": m, "z": z,
        "H": H,
        "vn_degrees": vn_degrees,
        "cn_degrees": cn_degrees,
        "vn_edges": vn_edges,
        "cn_edges": cn_edges,
    }


# Default configuration: z=1 → n=24, m=12 (demonstration size)
# For production, set z=24 → n=576, m=288 (full WiMax)
LDPC_PARAMS = build_ldpc_params(_HBM_RATE_1_2, z=1)

PREC = 4
ITER_MAX = 25
NUM_VN = LDPC_PARAMS["n"]
NUM_CN = LDPC_PARAMS["m"]
VN_DEGREES = LDPC_PARAMS["vn_degrees"]
CN_DEGREES = LDPC_PARAMS["cn_degrees"]
VN_EDGES = LDPC_PARAMS["vn_edges"]
CN_EDGES = LDPC_PARAMS["cn_edges"]

print(f"LDPC Decoder parameters: N={NUM_VN}, M={NUM_CN}, prec={PREC}, z={LDPC_PARAMS['z']}")
print(f"  Total edges: {sum(VN_DEGREES)}")
print(f"  VN degrees: min={min(VN_DEGREES)}, max={max(VN_DEGREES)}")
print(f"  CN degrees: min={min(CN_DEGREES)}, max={max(CN_DEGREES)}")


# ============================================================================
# Module 1: QuantizedAdder (saturating signed adder)
# ============================================================================
class QuantizedAdder(Module):
    """Saturating signed adder with (PREC+1)-bit internal precision.

    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/QuantizedAdder.v
    """
    def __init__(self, prec=4):
        super().__init__("quantized_adder")
        self.PREC = Parameter(prec, "PREC")

        self.in1 = Input(prec, "in1", signed=True)
        self.in2 = Input(prec, "in2", signed=True)
        self.sum = Output(prec, "sum", signed=True)

        self._sum_wire = Wire(prec + 1, "sum_wire", signed=True)

        with self.comb:
            self._sum_wire <<= self.in1 + self.in2
            with If(self._sum_wire[prec] == self._sum_wire[prec - 1]):
                self.sum <<= self._sum_wire[prec - 1 : 0]
            with Else():
                self.sum <<= Cat(
                    self._sum_wire[prec],
                    Rep(self._sum_wire[prec - 1], prec - 1),
                )

        tpl = ModuleDocTemplate(
            source="LDPC QuantizedAdder — ref_rtl/LDPC_Decoder/QuantizedAdder.v",
            description=f"{prec}-bit saturating signed adder. "
                        "Overflow clips to max positive / max negative.",
            author="rtlgen agent", version="1.0",
            timing="Combinational: 1-cycle latency",
            port_description="in1,in2: signed inputs; sum: saturated signed output",
        )
        fill_doc_template(tpl, self)


print("  - QuantizedAdder defined")


# ============================================================================
# Module 2: QuantizedSubber (saturating signed subtractor)
# ============================================================================
class QuantizedSubber(Module):
    """Saturating signed subtractor: sum = in1 - in2.

    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/QuantizedSubber.v
    """
    def __init__(self, prec=4):
        super().__init__("quantized_subber")
        self.PREC = Parameter(prec, "PREC")

        self.in1 = Input(prec, "in1", signed=True)
        self.in2 = Input(prec, "in2", signed=True)
        self.sum = Output(prec, "sum", signed=True)

        self._sum_wire = Wire(prec + 1, "sum_wire", signed=True)

        with self.comb:
            self._sum_wire <<= self.in1 - self.in2
            with If(self._sum_wire[prec] == self._sum_wire[prec - 1]):
                self.sum <<= self._sum_wire[prec - 1 : 0]
            with Else():
                self.sum <<= Cat(
                    self._sum_wire[prec],
                    Rep(self._sum_wire[prec - 1], prec - 1),
                )

        tpl = ModuleDocTemplate(
            source="LDPC QuantizedSubber — ref_rtl/LDPC_Decoder/QuantizedSubber.v",
            description=f"{prec}-bit saturating signed subtractor.",
            author="rtlgen agent", version="1.0",
            timing="Combinational: 1-cycle latency",
        )
        fill_doc_template(tpl, self)


print("  - QuantizedSubber defined")


# ============================================================================
# Module 3: Comparator (min + second_min tree node)
# ============================================================================
class Comparator(Module):
    """Tree comparator node: given two (min, sec_min) pairs, output the
    overall minimum and second-minimum.

    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/Comparator.v
    """
    def __init__(self, prec=4):
        super().__init__("comparator")
        self.PREC = Parameter(prec, "PREC")

        self.min1 = Input(prec, "min1")
        self.min2 = Input(prec, "min2")
        self.sec_min1 = Input(prec, "sec_min1")
        self.sec_min2 = Input(prec, "sec_min2")
        self.min = Output(prec, "min")
        self.sec_min = Output(prec, "sec_min")

        self._not_min = Wire(prec, "not_min")
        self._not_max = Wire(prec, "not_max")

        with self.comb:
            with If(self.min2 > self.min1):
                self.min <<= self.min1
                self._not_min <<= self.min2
            with Else():
                self.min <<= self.min2
                self._not_min <<= self.min1
            with If(self.sec_min1 <= self.sec_min2):
                self._not_max <<= self.sec_min1
            with Else():
                self._not_max <<= self.sec_min2
            with If(self._not_min <= self._not_max):
                self.sec_min <<= self._not_min
            with Else():
                self.sec_min <<= self._not_max

        tpl = ModuleDocTemplate(
            source="LDPC Comparator — ref_rtl/LDPC_Decoder/Comparator.v",
            description=f"{prec}-bit min/second-min comparator tree node. "
                        "Outputs: min = smallest of four inputs; "
                        "sec_min = second smallest.",
            author="rtlgen agent", version="1.0",
            timing="Combinational: 1-cycle latency",
        )
        fill_doc_template(tpl, self)


print("  - Comparator defined")


# ============================================================================
# Module 4: CheckNode (Min-Sum check node)
# ============================================================================
class CheckNode(Module):
    """Min-Sum check node.

    For each connected variable node i:
      R_i = sign_product xor Q_sign_i ? -min_abs : min_abs
      (if |Q_i| == min, use second_min instead)

    Uses a binary tree of Comparators to find min and second_min.
    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/CheckNode.v
    """
    def __init__(self, num_connections=6, prec=4):
        super().__init__("check_node")
        self.NUM_CONNECTIONS = Parameter(num_connections, "NUM_CONNECTIONS")
        self.PREC = Parameter(prec, "PREC")

        self.Qwires = Input(num_connections * prec, "Qwires", signed=True)
        self.Rwires = Output(num_connections * prec, "Rwires", signed=True)
        self.rst = Input(1, "rst")
        self.clk = Input(1, "clk")

        # Extract Q values
        self._Q_vals = [Wire(prec, f"Q_{i}", signed=True) for i in range(num_connections)]
        self._Q_signs = [Wire(1, f"Qs_{i}") for i in range(num_connections)]
        self._abs_Q = [Wire(prec, f"aQ_{i}", signed=True) for i in range(num_connections)]

        self._sign_product = Wire(1, "sign_prod")

        # Comparator tree (reference uses min_tree_wires[num_conn*2-2:0])
        tree_size = num_connections * 2 - 1
        self._min_w = [Wire(prec, f"min_w_{i}", signed=True) for i in range(tree_size)]
        self._sec_w = [Wire(prec, f"sec_w_{i}", signed=True) for i in range(tree_size)]
        self._min = Wire(prec, "min_val", signed=True)
        self._second_min = Wire(prec, "sec_min_val", signed=True)

        self._R_signs = [Wire(1, f"Rs_{i}") for i in range(num_connections)]
        self._abs_R = [Wire(prec, f"aR_{i}", signed=True) for i in range(num_connections)]
        self._Rvals = [Wire(prec, f"Rv_{i}", signed=True) for i in range(num_connections)]
        self._Rreg = [Reg(prec, f"Rr_{i}", init_value=0, signed=True) for i in range(num_connections)]

        with self.comb:
            for i in range(num_connections):
                self._Q_vals[i] <<= self.Qwires[(i + 1) * prec - 1 : i * prec]
                self._Q_signs[i] <<= self._Q_vals[i][prec - 1]
                with If(self._Q_signs[i]):
                    self._abs_Q[i] <<= -self._Q_vals[i]
                with Else():
                    self._abs_Q[i] <<= self._Q_vals[i]

            # XOR tree for sign_product
            sp = self._Q_signs[0]
            for i in range(1, num_connections):
                sp = sp ^ self._Q_signs[i]
            self._sign_product <<= sp

            # Tree leaves
            for i in range(num_connections):
                self._min_w[i] <<= self._abs_Q[i]
                self._sec_w[i] <<= Const((1 << prec) - 1, prec)

        # Internal comparator nodes (outside comb block — Verilog does not allow module instantiation inside always)
        for i in range(num_connections - 1):
            idx = i + num_connections
            comp = Comparator(prec=prec)
            self.instantiate(comp, f"cmp_{i}", port_map={
                "min1": self._min_w[i * 2],
                "min2": self._min_w[i * 2 + 1],
                "sec_min1": self._sec_w[i * 2],
                "sec_min2": self._sec_w[i * 2 + 1],
                "min": self._min_w[idx],
                "sec_min": self._sec_w[idx],
            })

        with self.comb:
            self._min <<= self._min_w[tree_size - 1]
            self._second_min <<= self._sec_w[tree_size - 1]

            # Compute R values
            for i in range(num_connections):
                with If(self._sign_product):
                    self._R_signs[i] <<= ~self._Q_signs[i]
                with Else():
                    self._R_signs[i] <<= self._Q_signs[i]
                with If(self._abs_Q[i] == self._min):
                    self._abs_R[i] <<= self._second_min
                with Else():
                    self._abs_R[i] <<= self._min
                with If(self._R_signs[i]):
                    self._Rvals[i] <<= -self._abs_R[i]
                with Else():
                    self._Rvals[i] <<= self._abs_R[i]

            # Pack output from registers (assign style to avoid unregistered_output lint)
            r_bits = []
            for i in range(num_connections - 1, -1, -1):
                r_bits.append(self._Rreg[i])
            self.Rwires <<= Cat(*r_bits)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(num_connections):
                    self._Rreg[i] <<= Const(0, prec)
            with Else():
                for i in range(num_connections):
                    self._Rreg[i] <<= self._Rvals[i]

        tpl = ModuleDocTemplate(
            source="LDPC CheckNode — ref_rtl/LDPC_Decoder/CheckNode.v",
            description=f"Min-Sum check node: {num_connections} edges, {prec}-bit precision. "
                        "Registered outputs (1-cycle latency).",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency per iteration",
        )
        fill_doc_template(tpl, self)


print("  - CheckNode defined")


# ============================================================================
# Module 5: VarNode (variable node)
# ============================================================================
class VarNode(Module):
    """Variable node.

    sum_R = sum of all incoming R messages (quantized saturating add tree)
    P_v   = quantize(sum_R + llr)
    Q_i   = quantize(P_v - R_i)  for each connected check node
    x     = P_v[prec-1] (hard decision sign bit)

    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/VarNode.v
    """
    def __init__(self, num_connections=3, prec=4):
        super().__init__("var_node")
        self.NUM_CONNECTIONS = Parameter(num_connections, "NUM_CONNECTIONS")
        self.PREC = Parameter(prec, "PREC")

        self.P_v = Output(prec, "P_v", signed=True)
        self.x = Output(1, "x")
        self.Qwires = Output(num_connections * prec, "Qwires", signed=True)
        self.Rwires = Input(num_connections * prec, "Rwires", signed=True)
        self.llr = Input(prec, "llr", signed=True)
        self.rst = Input(1, "rst")
        self.clk = Input(1, "clk")

        self._R_vals = [Wire(prec, f"R_{i}", signed=True) for i in range(num_connections)]

        tree_size = num_connections * 2 - 1
        self._sum_w = [Wire(prec, f"sw_{i}", signed=True) for i in range(tree_size)]
        self._sum_R = Wire(prec, "sumR", signed=True)
        self._P_v_wire = Wire(prec, "Pv", signed=True)
        self._Q_vals = [Wire(prec, f"Q_{i}", signed=True) for i in range(num_connections)]
        self._sub_w = [Wire(prec, f"sb_{i}", signed=True) for i in range(num_connections)]
        self._Qreg = Reg(num_connections * prec, "Qreg", init_value=0, signed=True)

        with self.comb:
            for i in range(num_connections):
                self._R_vals[i] <<= self.Rwires[(i + 1) * prec - 1 : i * prec]
            for i in range(num_connections):
                self._sum_w[i] <<= self._R_vals[i]

        for i in range(num_connections - 1):
            idx = i + num_connections
            adder = QuantizedAdder(prec=prec)
            self.instantiate(adder, f"add_{i}", port_map={
                "in1": self._sum_w[i * 2],
                "in2": self._sum_w[i * 2 + 1],
                "sum": self._sum_w[idx],
            })

        with self.comb:
            self._sum_R <<= self._sum_w[tree_size - 1]

        pv_adder = QuantizedAdder(prec=prec)
        self.instantiate(pv_adder, "pv_add", port_map={
            "in1": self._sum_R,
            "in2": self.llr,
            "sum": self._P_v_wire,
        })

        with self.comb:
            self.P_v <<= self._P_v_wire
            self.x <<= self._P_v_wire[prec - 1]

        for i in range(num_connections):
            subber = QuantizedSubber(prec=prec)
            self.instantiate(subber, f"sub_{i}", port_map={
                "in1": self._P_v_wire,
                "in2": self._R_vals[i],
                "sum": self._sub_w[i],
            })

        with self.comb:
            for i in range(num_connections):
                self._Q_vals[i] <<= self._sub_w[i]
            q_bits = []
            for i in range(num_connections - 1, -1, -1):
                q_bits.append(self._Q_vals[i])
            self.Qwires <<= Cat(*q_bits)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._Qreg <<= Const(0, num_connections * prec)
            with Else():
                self._Qreg <<= self.Qwires

        tpl = ModuleDocTemplate(
            source="LDPC VarNode — ref_rtl/LDPC_Decoder/VarNode.v",
            description=f"Variable node: {num_connections} edges, {prec}-bit precision. "
                        "P_v = llr + sum(R); Q_i = P_v - R_i.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency per iteration",
        )
        fill_doc_template(tpl, self)


print("  - VarNode defined")


# ============================================================================
# Module 6: LDPC_Decoder (top-level)
# ============================================================================
class LDPC_Decoder(Module):
    """Top-level LDPC decoder with parameterized Tanner graph.

    The H matrix determines the VN/CN count, degrees, and edge topology.
    One decoding iteration is performed per clock cycle.
    Termination: MAX_ITER iterations or all parity checks satisfied.

    Reference: ref_rtl/LDPC_Decoder/verilog/VFiles/LDPC.v
    """
    def __init__(self, n=NUM_VN, m=NUM_CN, prec=PREC, iter_max=ITER_MAX,
                 vn_degrees=VN_DEGREES, cn_degrees=CN_DEGREES,
                 vn_edges=VN_EDGES, cn_edges=CN_EDGES):
        super().__init__("ldpc_decoder")
        self.N = Parameter(n, "N")
        self.M = Parameter(m, "M")
        self.PREC = Parameter(prec, "PREC")
        self.ITER_MAX = Parameter(iter_max, "ITER_MAX")

        self.llr = Input(n * prec, "llr", signed=True)
        self.out = Output(n * prec, "out", signed=True)
        self.x = Output(n, "x")
        self.done = Output(1, "done")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # Edge index maps
        vn_edge_idx = {v: {c: i for i, c in enumerate(vn_edges[v])} for v in range(n)}
        cn_edge_idx = {c: {v: i for i, v in enumerate(cn_edges[c])} for c in range(m)}

        # Per-node packed wire bundles
        self._Qwires_vn = [Wire(vn_degrees[v] * prec, f"Q_vn{v}", signed=True) for v in range(n)]
        self._Rwires_vn = [Wire(vn_degrees[v] * prec, f"R_vn{v}", signed=True) for v in range(n)]
        self._Qwires_cn = [Wire(cn_degrees[c] * prec, f"Q_cn{c}", signed=True) for c in range(m)]
        self._Rwires_cn = [Wire(cn_degrees[c] * prec, f"R_cn{c}", signed=True) for c in range(m)]

        # Interconnect: per-edge segment assignments
        with self.comb:
            for v in range(n):
                for c in vn_edges[v]:
                    v_idx = vn_edge_idx[v][c]
                    c_idx = cn_edge_idx[c][v]
                    # VN Q output segment → CN Q input segment
                    vq_lo = v_idx * prec
                    vq_hi = vq_lo + prec - 1
                    cq_lo = c_idx * prec
                    cq_hi = cq_lo + prec - 1
                    self._Qwires_cn[c][cq_hi : cq_lo] <<= self._Qwires_vn[v][vq_hi : vq_lo]
                    # CN R output segment → VN R input segment
                    cr_lo = c_idx * prec
                    cr_hi = cr_lo + prec - 1
                    vr_lo = v_idx * prec
                    vr_hi = vr_lo + prec - 1
                    self._Rwires_vn[v][vr_hi : vr_lo] <<= self._Rwires_cn[c][cr_hi : cr_lo]

        # Instantiate VarNodes
        for v in range(n):
            vn = VarNode(num_connections=vn_degrees[v], prec=prec)
            self.instantiate(vn, f"vn{v}", port_map={
                "P_v": self.out[(v + 1) * prec - 1 : v * prec],
                "x": self.x[v],
                "Qwires": self._Qwires_vn[v],
                "Rwires": self._Rwires_vn[v],
                "llr": self.llr[(v + 1) * prec - 1 : v * prec],
                "rst": self.rst,
                "clk": self.clk,
            })

        # Instantiate CheckNodes
        for c in range(m):
            cn = CheckNode(num_connections=cn_degrees[c], prec=prec)
            self.instantiate(cn, f"cn{c}", port_map={
                "Qwires": self._Qwires_cn[c],
                "Rwires": self._Rwires_cn[c],
                "rst": self.rst,
                "clk": self.clk,
            })

        # Control: iteration counter + parity check + done
        self._count = Reg(5, "count", init_value=0)
        self._done_reg = Reg(1, "done_r", init_value=0)
        self._out_check = Wire(m, "out_check")

        with self.comb:
            for c in range(m):
                parity = self.x[cn_edges[c][0]]
                for v in cn_edges[c][1:]:
                    parity = parity ^ self.x[v]
                self._out_check[c] <<= parity

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._count <<= Const(0, 5)
                self._done_reg <<= Const(0, 1)
            with Else():
                with If((self._count == iter_max) | (self._out_check == Const(0, m))):
                    self._done_reg <<= Const(1, 1)
                with Else():
                    with If(self._count < iter_max):
                        self._count <<= self._count + 1

        with self.comb:
            self.done <<= self._done_reg

        tpl = ModuleDocTemplate(
            source="LDPC Decoder Top — ref_rtl/LDPC_Decoder/LDPC.v",
            description=f"LDPC decoder: N={n}, M={m}, {prec}-bit precision, "
                        f"max {iter_max} iterations. Min-Sum algorithm.",
            author="rtlgen agent", version="1.0",
            timing="1 iteration per clock cycle. done when converged or max_iter.",
        )
        fill_doc_template(tpl, self)
