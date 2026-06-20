"""Fully-pipelined 128-bit Barrett modular multiplier (executable DSL model).

Computes ``r = (a * b) mod N`` as a TRUE fully-pipelined unit: each stage
latches its result in a pipeline register, one operand set is accepted per
cycle, one result emerges per cycle after a fixed latency, and ``in_accept``
is always high (no back-pressure). Targeted at high Fmax: the long
combinational paths (128x128 multiply, quotient estimate, residual subtract)
are each isolated in their own pipeline stage so no single stage carries an
oversized combinational cone.

The modulus ``N`` must be a full 128-bit value (2^127 <= N < 2^128), which
fixes the Barrett constant ``m = floor(2^256 / N)`` to exactly 129 bits.

Pipeline stages (each = one registered stage):

    S0  MUL    p   = a * b                   (256-bit, 8x8 schoolbook of 16x16)
    S1  QEST   q   = ( (p>>127) * m ) >> 129 (Barrett quotient, full width)
    S2  RESID  r   = p - q*N                 (residual, 0 <= r < 3N)
    S3  CSUB0  r  -= N  if r >= N            (first conditional subtraction)
    S4  CSUB1  r  -= N  if r >= N            (second; at most two suffice)

The datapath has 5 registered stages. In the rtlgen_x step API, the result for
an input sample becomes observable 4 steps after the submission step because
stage S0 captures the operands on the same edge that accepts them.

Reset is active-high ``rst`` (rtlgen_x legacy-DSL convention).
"""

from __future__ import annotations

from rtlgen_x.dsl import (
    Const,
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

LIMB = 16                  # 16x16 single-cycle multiplier primitive width
NLIMB = K // LIMB          # 8 limbs per 128-bit operand
QEST_IN_W = K + 1
QEST_MUL_W = 2 * QEST_IN_W
REDUCE_MUL_W = PROD_WIDTH + 2


def _mul128(a_sig, b_sig):
    """256-bit product from 8x8 = 64 sixteen-bit limb multipliers (DSP-friendly).

    The accumulator is kept wide (ACC_W) so no intermediate masking/slicing is
    needed during the sum — only the final result is sliced to PROD_WIDTH. This
    avoids the codegen sub-expression extractor mis-handling nested Slice(BinOp)
    chains (audit0620.md, issue A2).
    """
    ACC_W = PROD_WIDTH + LIMB  # 272 bits: enough for any shifted 32-bit partial
    acc = Const(0, ACC_W)
    for i in range(NLIMB):
        for j in range(NLIMB):
            a_limb = a_sig[i * LIMB + LIMB - 1: i * LIMB]
            b_limb = b_sig[j * LIMB + LIMB - 1: j * LIMB]
            placed = (a_limb * b_limb) << (i + j) * LIMB
            acc = acc + placed
    return acc[PROD_WIDTH - 1:0]


def _wide_mul(lhs, rhs, operand_width):
    """Force a multiplication to occur in a sufficiently-wide unsigned domain."""
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


class BarrettModMul(Module):
    """Fully-pipelined 128-bit Barrett modular multiplier (5-stage pipe).

    Inputs:  clk, rst, in_valid, a[128], b[128], n[128], m[129]
    Outputs: in_accept, out_valid, r[128]
    Latency: 5 registered stages / 4 post-step drain cycles. Throughput: 1 op/cycle.
    """

    PIPE_STAGES = 5
    LATENCY = PIPE_STAGES - 1

    def __init__(self):
        super().__init__("barrett_mod_mul")

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

        # ---- Pipeline registers (one per stage) ----
        # Valid bits accompany the data.
        self.v0 = Reg(1, "v0", init_value=0)
        self.v1 = Reg(1, "v1", init_value=0)
        self.v2 = Reg(1, "v2", init_value=0)
        self.v3 = Reg(1, "v3", init_value=0)
        self.v4 = Reg(1, "v4", init_value=0)

        # S0 -> S1: product, modulus carried down.
        self.p_q = Reg(PROD_WIDTH, "p_q", init_value=0)
        self.n_q1 = Reg(K, "n_q1", init_value=0)
        self.m_q1 = Reg(M_WIDTH, "m_q1", init_value=0)
        # S1 -> S2: quotient estimate (kept full-width; see _barrett note).
        self.q_q = Reg(K + 2, "q_q", init_value=0)
        self.n_q2 = Reg(K, "n_q2", init_value=0)
        # S2 -> S3: residual (256-bit, 0..3N).
        self.resid_q = Reg(PROD_WIDTH, "resid_q", init_value=0)
        self.n_q3 = Reg(K, "n_q3", init_value=0)
        # S3 -> S4: after first conditional subtraction.
        self.resid1_q = Reg(PROD_WIDTH, "resid1_q", init_value=0)
        self.n_q4 = Reg(K, "n_q4", init_value=0)
        # S4 -> out: after second conditional subtraction (final residual).
        self.resid2_q = Reg(PROD_WIDTH, "resid2_q", init_value=0)

        # ---- Combinational outputs ----
        @self.comb
        def _status():
            # Fully pipelined, no back-pressure: always accept.
            self.in_accept <<= 1
            self.out_valid <<= self.v4
            self.r <<= self.resid2_q[K - 1:0]

        # ---- Pipeline sequencing ----
        # Bubble cycles must not clobber data already in flight, so each stage
        # only updates its payload registers when the matching valid bit is set.
        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.v0 <<= 0; self.v1 <<= 0; self.v2 <<= 0
                self.v3 <<= 0; self.v4 <<= 0
                self.p_q <<= 0
                self.n_q1 <<= 0
                self.m_q1 <<= 0
                self.q_q <<= 0
                self.n_q2 <<= 0
                self.resid_q <<= 0
                self.n_q3 <<= 0
                self.resid1_q <<= 0
                self.n_q4 <<= 0
                self.resid2_q <<= 0
            with Else():
                self.v0 <<= self.in_valid
                self.v1 <<= self.v0
                self.v2 <<= self.v1
                self.v3 <<= self.v2
                self.v4 <<= self.v3

                # S0: 128x128 multiply from the input operands (16x16 limbs).
                with If(self.in_valid == 1):
                    self.p_q <<= _mul128(self.a, self.b)
                    self.n_q1 <<= self.n
                    self.m_q1 <<= self.m

                # S1: Barrett quotient estimate q = ((p>>127)*m)>>129.
                with If(self.v0 == 1):
                    self.q_q <<= _barrett_q_estimate(self.p_q, self.m_q1)
                    self.n_q2 <<= self.n_q1

                # S2: residual r = p - q*N  (0 <= r < 3N).
                with If(self.v1 == 1):
                    self.resid_q <<= _barrett_residual(self.p_q, self.q_q, self.n_q2)
                    self.n_q3 <<= self.n_q2

                # S3: first conditional subtraction (resid >= N).
                with If(self.v2 == 1):
                    self.resid1_q <<= Mux(
                        self.resid_q >= self.n_q3,
                        (self.resid_q - self.n_q3)[PROD_WIDTH - 1:0],
                        self.resid_q,
                    )
                    self.n_q4 <<= self.n_q3

                # S4: second conditional subtraction -> final residual.
                with If(self.v3 == 1):
                    self.resid2_q <<= Mux(
                        self.resid1_q >= self.n_q4,
                        (self.resid1_q - self.n_q4)[PROD_WIDTH - 1:0],
                        self.resid1_q,
                    )


__all__ = ["BarrettModMul"]
