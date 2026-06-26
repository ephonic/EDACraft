"""Karatsuba-Ofman pipelined 128-bit Barrett modular multiplier.

The 128x128 -> 256-bit multiply is decomposed by recursive Karatsuba-Ofman
splitting down to ~16-bit base multipliers (one DSP slice per leaf),
following the PPA report recommendation to break the original depth-72
schoolbook cone into balanced sub-trees with register boundaries inserted.

Three KO recursion levels yield 27 leaf multiplies (vs. 64 limb multiplies in
the prior schoolbook):

    Level 0 (S0_M0)  : split 128 = 64H | 64L; emit 3 sub-pairs (H, M, L)
                       where M operand = (H + L) is one bit wider.
    Level 1 (S0_M1)  : split each 64-ish operand into 32-ish halves; 3 x 3 = 9
                       sub-multiplies.
    Level 2 (S0_M2)  : split each 32-ish operand into 16-ish halves; 3 x 9 = 27
                       leaf multiplies (16x16 .. 19x19, single-DSP friendly).
    Combine M1 (S1)  : 27 -> 9 (level-1 32x32 sub-products).
    Combine M2 (S2)  : 9  -> 3 (level-2 64x64 sub-products).
    Combine M3 (S3)  : 3  -> 1 (final 256-bit product `p_q`).

The Barrett reduction stages remain unchanged from the prior 5-stage pipeline
(QEST -> RESID -> CSUB0 -> CSUB1), giving an 8-stage end-to-end pipeline
(LATENCY = 7) with throughput 1 op/cycle and `in_accept` always high.

All payload registers are valid-gated so that bubble cycles (in_valid = 0)
never overwrite in-flight pipeline data.

The Karatsuba combine at every level is unsigned:

    out = z2 * 2^{2k} + (z1_full - z2 - z0) * 2^k + z0

where ``z1_full = (a_h + a_l) * (b_h + b_l)``. The middle term
``z1m = z1_full - z2 - z0`` equals ``a_h*b_l + a_l*b_h`` and is therefore
non-negative, so unsigned subtraction at sufficient width is exact.
"""

from __future__ import annotations

from rtlgen_x.dsl import (
    Else,
    If,
    Input,
    Module,
    Mux,
    Output,
    PadLeft,
    Reg,
)

from .reference import K, M_WIDTH, PROD_WIDTH

# ---------------------------------------------------------------------------
# Width budgets (uniform per level; loose upper bounds, not bit-tight).
# ---------------------------------------------------------------------------
LIMB = 16                    # Nominal base-multiplier width (16x16 leaf)
QEST_IN_W = K + 1
QEST_MUL_W = 2 * QEST_IN_W
REDUCE_MUL_W = PROD_WIDTH + 2

# Level operand widths (worst-case, taking the all-mid path):
#   Top      : 128
#   Lvl-1 op : 65  (M = H+L of 64)
#   Lvl-2 op : 34  (M of 65 split at 32 = max(33,32)+1)
#   Lvl-3 op : 18  (M of 34 split at 17 = max(17,17)+1)
W_LVL3_MAX = 18
W_LVL2_MAX = 34
W_LVL1_MAX = 65

# Storage widths for the per-level partial-product registers; product width is
# 2*operand_width, with a small slack to be defensive against
# off-by-one width math during recursion.
PROD0_W = 2 * W_LVL3_MAX + 2     # 38 leaf bits + slack -> 38
PROD1_W = 2 * W_LVL2_MAX + 4     # 68 + slack            -> 72
PROD2_W = 2 * W_LVL1_MAX + 4     # 130 + slack           -> 134
PROD3_W = PROD_WIDTH              # final 256

BRANCHES = ("H", "M", "L")   # high, mid (a_h+a_l), low


# ---------------------------------------------------------------------------
# DSL helpers
# ---------------------------------------------------------------------------
def _split(sig, w):
    """Split unsigned ``sig`` of width ``w`` into the three KO branches.

    Returns (branches, k) where:
      branches['H'] = (hi, hi_w)        hi = sig[w-1:k], width = w-k
      branches['L'] = (lo, lo_w)        lo = sig[k-1:0], width = k
      branches['M'] = (mid, mid_w)      mid = hi + lo, width = max(hi_w,lo_w)+1
      k = w // 2 (split point used to reconstruct the product later)
    """
    if w < 2:
        raise ValueError(f"_split requires width >= 2, got {w}")
    k = w // 2
    hi_w = w - k
    lo_w = k
    mid_w = max(hi_w, lo_w) + 1
    hi = sig[w - 1: k]
    lo = sig[k - 1: 0]
    mid = PadLeft(hi, mid_w) + PadLeft(lo, mid_w)
    return ({"H": (hi, hi_w), "L": (lo, lo_w), "M": (mid, mid_w)}, k)


def _ko_combine(z2, z1_full, z0, k_split, out_w):
    """Karatsuba-Ofman combine step (unsigned, widened to ``out_w``).

    out = z2 << 2k  +  (z1_full - z2 - z0) << k  +  z0
    """
    z2w = PadLeft(z2, out_w)
    z1f = PadLeft(z1_full, out_w)
    z0w = PadLeft(z0, out_w)
    z1m = z1f - z2w - z0w
    return (z2w << (2 * k_split)) + (z1m << k_split) + z0w


def _ko_operand_tree(a_sig, b_sig, w_top):
    """Walk the 3-level KO operand tree and collect:

      base_ops:        dict[(t,u,v) -> (a_expr, b_expr, w)]   27 entries
      k_top:           split point at the top (128 -> 64+64)
      splits_lvl2:     dict[t -> k_t]                          (3 entries)
      splits_lvl1:     dict[(t,u) -> k_tu]                     (9 entries)
    """
    base_ops = {}
    splits_lvl2 = {}
    splits_lvl1 = {}

    a1, k_top = _split(a_sig, w_top)
    b1, _ = _split(b_sig, w_top)
    for t in BRANCHES:
        a_t, wa_t = a1[t]
        b_t, wb_t = b1[t]
        w_t = max(wa_t, wb_t)
        a_t_pad = PadLeft(a_t, w_t)
        b_t_pad = PadLeft(b_t, w_t)
        a2, k_t = _split(a_t_pad, w_t)
        b2, _ = _split(b_t_pad, w_t)
        splits_lvl2[t] = k_t
        for u in BRANCHES:
            a_tu, wa_tu = a2[u]
            b_tu, wb_tu = b2[u]
            w_tu = max(wa_tu, wb_tu)
            a_tu_pad = PadLeft(a_tu, w_tu)
            b_tu_pad = PadLeft(b_tu, w_tu)
            a3, k_tu = _split(a_tu_pad, w_tu)
            b3, _ = _split(b_tu_pad, w_tu)
            splits_lvl1[(t, u)] = k_tu
            for v in BRANCHES:
                a_tuv, wa_tuv = a3[v]
                b_tuv, wb_tuv = b3[v]
                w_tuv = max(wa_tuv, wb_tuv)
                base_ops[(t, u, v)] = (
                    PadLeft(a_tuv, w_tuv),
                    PadLeft(b_tuv, w_tuv),
                    w_tuv,
                )
    return base_ops, k_top, splits_lvl2, splits_lvl1


def _wide_mul(lhs, rhs, operand_width):
    """Force a multiplication to occur at a given unsigned width."""
    return PadLeft(lhs, operand_width) * PadLeft(rhs, operand_width)


def _barrett_q_estimate(p_sig, m_sig):
    """q = ((p >> 127) * m) >> 129 with the multiply widened explicitly."""
    p_hi = p_sig[PROD_WIDTH - 1: K - 1]
    return _wide_mul(p_hi, m_sig, QEST_MUL_W) >> (K + 1)


def _barrett_residual(p_sig, q_sig, n_sig):
    """r = p - q*N with the q*N product widened before subtraction."""
    p_ext = PadLeft(p_sig, REDUCE_MUL_W)
    qn_ext = _wide_mul(q_sig, n_sig, REDUCE_MUL_W)
    return (p_ext - qn_ext)[PROD_WIDTH - 1:0]


# ---------------------------------------------------------------------------
# Top module
# ---------------------------------------------------------------------------
class BarrettModMul(Module):
    """Fully-pipelined 128-bit Barrett modular multiplier with KO multiplier.

    Inputs:  clk, rst, in_valid, a[128], b[128], n[128], m[129]
    Outputs: in_accept, out_valid, r[128]

    Pipeline stages (8 total, one register per stage, valid-gated payload):
      S0  KO leaf multiplies         : 27 base products (16x16..19x19)
      S1  KO combine level-1         : 9 32x32-equivalent products
      S2  KO combine level-2         : 3 64x64-equivalent products
      S3  KO combine level-3 -> p_q  : final 256-bit a*b
      S4  QEST                       : Barrett quotient estimate
      S5  RESID                      : r = p - q*N (0..3N)
      S6  CSUB0                      : conditional subtract
      S7  CSUB1                      : conditional subtract -> final r

    Latency = 7, throughput = 1 op/cycle.
    """

    PIPE_STAGES = 8
    LATENCY = PIPE_STAGES - 1  # = 7

    def __init__(self):
        super().__init__("barrett_mod_mul")

        # ---- IO -------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.in_valid = Input(1, "in_valid")
        self.a = Input(K, "a")
        self.b = Input(K, "b")
        self.n = Input(K, "n")
        self.m = Input(M_WIDTH, "m")

        self.in_accept = Output(1, "in_accept")
        self.out_valid = Output(1, "out_valid")
        self.r = Output(K, "r")

        # ---- Valid-bit shift register (8 stages) ---------------------------
        self.v0 = Reg(1, "v0", init_value=0)
        self.v1 = Reg(1, "v1", init_value=0)
        self.v2 = Reg(1, "v2", init_value=0)
        self.v3 = Reg(1, "v3", init_value=0)
        self.v4 = Reg(1, "v4", init_value=0)
        self.v5 = Reg(1, "v5", init_value=0)
        self.v6 = Reg(1, "v6", init_value=0)
        self.v7 = Reg(1, "v7", init_value=0)

        # ---- KO partial-product registers ---------------------------------
        # Level-0: 27 leaf products (one per (t,u,v) path).
        self._base_keys = [(t, u, v)
                           for t in BRANCHES
                           for u in BRANCHES
                           for v in BRANCHES]
        self.p16 = {
            key: Reg(PROD0_W, f"p16_{key[0]}{key[1]}{key[2]}", init_value=0)
            for key in self._base_keys
        }
        # Level-1: 9 combined products (one per (t,u) path).
        self._lvl1_keys = [(t, u) for t in BRANCHES for u in BRANCHES]
        self.p32 = {
            key: Reg(PROD1_W, f"p32_{key[0]}{key[1]}", init_value=0)
            for key in self._lvl1_keys
        }
        # Level-2: 3 combined products (one per t).
        self.p64 = {t: Reg(PROD2_W, f"p64_{t}", init_value=0) for t in BRANCHES}
        # Level-3: final 256-bit product.
        self.p_q = Reg(PROD_WIDTH, "p_q", init_value=0)

        # ---- N / M shift registers carrying through the multiplier --------
        # These delay the modulus and Barrett constant alongside the 4 mul
        # stages so QEST can read them aligned with `p_q`.
        self.n_d0 = Reg(K, "n_d0", init_value=0)
        self.n_d1 = Reg(K, "n_d1", init_value=0)
        self.n_d2 = Reg(K, "n_d2", init_value=0)
        self.n_d3 = Reg(K, "n_d3", init_value=0)
        self.m_d0 = Reg(M_WIDTH, "m_d0", init_value=0)
        self.m_d1 = Reg(M_WIDTH, "m_d1", init_value=0)
        self.m_d2 = Reg(M_WIDTH, "m_d2", init_value=0)
        self.m_d3 = Reg(M_WIDTH, "m_d3", init_value=0)

        # ---- Barrett-reduction pipeline registers (post-multiplier) -------
        self.p_q1 = Reg(PROD_WIDTH, "p_q1", init_value=0)
        self.q_q = Reg(K + 2, "q_q", init_value=0)
        self.n_q2 = Reg(K, "n_q2", init_value=0)
        self.resid_q = Reg(PROD_WIDTH, "resid_q", init_value=0)
        self.n_q3 = Reg(K, "n_q3", init_value=0)
        self.resid1_q = Reg(PROD_WIDTH, "resid1_q", init_value=0)
        self.n_q4 = Reg(K, "n_q4", init_value=0)
        self.resid2_q = Reg(PROD_WIDTH, "resid2_q", init_value=0)

        # ---- Combinational outputs ----------------------------------------
        @self.comb
        def _status():
            self.in_accept <<= 1
            self.out_valid <<= self.v7
            self.r <<= self.resid2_q[K - 1: 0]

        # Pre-compute the operand tree (combinational from a,b at S0 input).
        base_ops, k_top, splits_lvl2, splits_lvl1 = _ko_operand_tree(
            self.a, self.b, K
        )

        # ---- Pipeline sequencing ------------------------------------------
        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                # Reset the valid pipe.
                self.v0 <<= 0; self.v1 <<= 0; self.v2 <<= 0; self.v3 <<= 0
                self.v4 <<= 0; self.v5 <<= 0; self.v6 <<= 0; self.v7 <<= 0
                # Reset KO partial registers.
                for r in self.p16.values():
                    r <<= 0
                for r in self.p32.values():
                    r <<= 0
                for r in self.p64.values():
                    r <<= 0
                self.p_q <<= 0
                # Reset n/m shift registers.
                self.n_d0 <<= 0; self.n_d1 <<= 0
                self.n_d2 <<= 0; self.n_d3 <<= 0
                self.m_d0 <<= 0; self.m_d1 <<= 0
                self.m_d2 <<= 0; self.m_d3 <<= 0
                # Reset Barrett reduction pipeline.
                self.p_q1 <<= 0
                self.q_q <<= 0
                self.n_q2 <<= 0
                self.resid_q <<= 0
                self.n_q3 <<= 0
                self.resid1_q <<= 0
                self.n_q4 <<= 0
                self.resid2_q <<= 0
            with Else():
                # Valid bit progresses unconditionally.
                self.v0 <<= self.in_valid
                self.v1 <<= self.v0
                self.v2 <<= self.v1
                self.v3 <<= self.v2
                self.v4 <<= self.v3
                self.v5 <<= self.v4
                self.v6 <<= self.v5
                self.v7 <<= self.v6

                # ---- S0: 27 leaf multiplies (valid-gated by in_valid) ----
                with If(self.in_valid == 1):
                    for key in self._base_keys:
                        a_op, b_op, _w = base_ops[key]
                        self.p16[key] <<= a_op * b_op
                    self.n_d0 <<= self.n
                    self.m_d0 <<= self.m

                # ---- S1: combine 27 leaves -> 9 lvl-1 (valid-gated by v0)
                with If(self.v0 == 1):
                    for (t, u) in self._lvl1_keys:
                        z2 = self.p16[(t, u, "H")]
                        z1f = self.p16[(t, u, "M")]
                        z0 = self.p16[(t, u, "L")]
                        k = splits_lvl1[(t, u)]
                        self.p32[(t, u)] <<= _ko_combine(z2, z1f, z0, k, PROD1_W)
                    self.n_d1 <<= self.n_d0
                    self.m_d1 <<= self.m_d0

                # ---- S2: combine 9 lvl-1 -> 3 lvl-2 (valid-gated by v1) --
                with If(self.v1 == 1):
                    for t in BRANCHES:
                        z2 = self.p32[(t, "H")]
                        z1f = self.p32[(t, "M")]
                        z0 = self.p32[(t, "L")]
                        k = splits_lvl2[t]
                        self.p64[t] <<= _ko_combine(z2, z1f, z0, k, PROD2_W)
                    self.n_d2 <<= self.n_d1
                    self.m_d2 <<= self.m_d1

                # ---- S3: combine 3 lvl-2 -> 1 final 256-bit (gated by v2)
                with If(self.v2 == 1):
                    z2 = self.p64["H"]
                    z1f = self.p64["M"]
                    z0 = self.p64["L"]
                    self.p_q <<= _ko_combine(z2, z1f, z0, k_top, PROD3_W)
                    self.n_d3 <<= self.n_d2
                    self.m_d3 <<= self.m_d2

                # ---- S4 QEST (gated by v3) ------------------------------
                with If(self.v3 == 1):
                    self.p_q1 <<= self.p_q
                    self.q_q <<= _barrett_q_estimate(self.p_q, self.m_d3)
                    self.n_q2 <<= self.n_d3

                # ---- S5 RESID (gated by v4) -----------------------------
                with If(self.v4 == 1):
                    self.resid_q <<= _barrett_residual(
                        self.p_q1, self.q_q, self.n_q2
                    )
                    self.n_q3 <<= self.n_q2

                # ---- S6 CSUB0 (gated by v5) -----------------------------
                with If(self.v5 == 1):
                    self.resid1_q <<= Mux(
                        self.resid_q >= self.n_q3,
                        (self.resid_q - self.n_q3)[PROD_WIDTH - 1:0],
                        self.resid_q,
                    )
                    self.n_q4 <<= self.n_q3

                # ---- S7 CSUB1 (gated by v6) -----------------------------
                with If(self.v6 == 1):
                    self.resid2_q <<= Mux(
                        self.resid1_q >= self.n_q4,
                        (self.resid1_q - self.n_q4)[PROD_WIDTH - 1:0],
                        self.resid1_q,
                    )


__all__ = ["BarrettModMul"]
