"""
skills.codec.ldpc.arch_templates — LDPC Decoder Architecture Templates

Builds ArchDefinition for LDPC Min-Sum decoder with configurable
H matrix, precision, and iteration count.

Architecture:
  LDPC_Decoder (top wrapper: llr in → decoded bits out)
    ├── VarNode[N]  — variable nodes (per column of H matrix)
    ├── CheckNode[M] — check nodes (per row of H matrix)
    └── Control     — iteration counter + parity check + done

Usage:
    from skills.codec.ldpc.arch_templates import build_ldpc_arch
    from skills.codec.ldpc.models import LDPC_PARAMS

    arch = build_ldpc_arch(n=24, m=12, prec=4, iter_max=25)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    Algorithm_Model,
)
from rtlgen.behaviors import TemplateRegistry

# Import behaviors to register LDPC templates in TemplateRegistry
import skills.codec.ldpc.behaviors  # noqa: F401

from skills.codec.ldpc.models import minsum_decode, LDPCDecoder_Model


# =====================================================================
# LDPC Parameter Builder
# =====================================================================

def build_ldpc_params(Hbm: List[List[int]], z: int = 1) -> Dict[str, Any]:
    """Build LDPC parameters from base matrix Hbm and expansion factor z.

    For z=1: H is the binary matrix directly derived from Hbm.
    For z>1: Hbm entries expand to z×z circulant permutation matrices.
    """
    m_b = len(Hbm)
    n_b = len(Hbm[0])
    m = m_b * z
    n = n_b * z

    if z == 1:
        H = [[1 if Hbm[i][j] != -1 else 0 for j in range(n_b)] for i in range(m_b)]
    else:
        H = [[0] * n for _ in range(m)]
        for i_b in range(m_b):
            for j_b in range(n_b):
                val = Hbm[i_b][j_b]
                if val == -1:
                    continue
                elif val == 0:
                    for k in range(z):
                        H[i_b * z + k][j_b * z + k] = 1
                else:
                    shift = (val * z) // 96
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


def build_ldpc_arch(
    n: int = 24,
    m: int = 12,
    prec: int = 4,
    iter_max: int = 25,
    vn_degrees: Optional[List[int]] = None,
    cn_degrees: Optional[List[int]] = None,
    H: Optional[List[List[int]]] = None,
) -> ArchDefinition:
    """Build ArchDefinition for LDPC decoder.

    Creates 3 PE types:
    - var_node: Variable node (N instances, degree varies per column)
    - check_node: Check node (M instances, degree varies per row)
    - ldpc_decoder: Top-level decoder with iteration control

    Args:
        n: Number of variable nodes (code length)
        m: Number of check nodes (parity constraints)
        prec: Message bit precision
        iter_max: Maximum decoding iterations
        vn_degrees: Per-VN connection counts (default: [3]*n)
        cn_degrees: Per-CN connection counts (default: [6]*m)
        H: Parity check matrix (for golden reference verification)
    """
    if vn_degrees is None:
        vn_degrees = [3] * n
    if cn_degrees is None:
        cn_degrees = [6] * m
    if H is None:
        H = [[0] * n for _ in range(m)]

    max_vn_deg = max(vn_degrees)
    max_cn_deg = max(cn_degrees)

    vn_pe = ProcessingElement(
        name="VarNode", pe_type="var_node",
        inputs=[PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
                PortDesc("llr", "input", prec),
                PortDesc("Rwires", "input", max_vn_deg * prec)],
        outputs=[PortDesc("P_v", "output", prec), PortDesc("x", "output", 1),
                 PortDesc("Qwires", "output", max_vn_deg * prec)],
        state=[StateDesc("Qreg", "int", "Q register", rtl_type="reg",
                         rtl_width=max_vn_deg * prec)],
        behavior=TemplateRegistry.get("var_node") or _default_var_node_behavior,
        can_stall=False, latency=1,
    )

    cn_pe = ProcessingElement(
        name="CheckNode", pe_type="check_node",
        inputs=[PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
                PortDesc("Qwires", "input", max_cn_deg * prec)],
        outputs=[PortDesc("Rwires", "output", max_cn_deg * prec)],
        state=[StateDesc("Rreg", "int", "R register", rtl_type="reg",
                         rtl_width=max_cn_deg * prec)],
        behavior=TemplateRegistry.get("check_node") or _default_check_node_behavior,
        can_stall=False, latency=1,
    )

    ldpc_pe = ProcessingElement(
        name="LDPC_Decoder", pe_type="ldpc_decoder",
        inputs=[PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
                PortDesc("llr", "input", n * prec)],
        outputs=[PortDesc("out", "output", n * prec),
                 PortDesc("x", "output", n),
                 PortDesc("done", "output", 1)],
        state=[StateDesc("count", "int", "Iteration counter", rtl_type="reg", rtl_width=5),
               StateDesc("done_r", "int", "Done flag", rtl_type="reg", rtl_width=1)],
        behavior=TemplateRegistry.get("ldpc_decoder") or _default_ldpc_behavior,
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="LDPC_Decoder",
        description=f"LDPC decoder: N={n}, M={m}, {prec}-bit precision, "
                    f"max {iter_max} iterations. Min-Sum algorithm.",
        isa="algorithm",
        processing_elements=[vn_pe, cn_pe, ldpc_pe],
        interconnects=[],
        model=Algorithm_Model(),
        ppa_targets={"max_area": 50000, "target_freq": 500e6},
    )


def _default_var_node_behavior(ctx: CycleContext):
    """Fallback var_node behavior if TemplateRegistry lookup fails."""
    rst = ctx.get_input("rst", 0)
    if rst:
        ctx.set_state("Qreg", 0)
        return
    ctx.set_output("P_v", ctx.get_input("llr", 0))
    ctx.set_output("x", 1 if ctx.get_input("llr", 0) >= (1 << 3) else 0)


def _default_check_node_behavior(ctx: CycleContext):
    """Fallback check_node behavior if TemplateRegistry lookup fails."""
    rst = ctx.get_input("rst", 0)
    if rst:
        ctx.set_state("Rreg", 0)
