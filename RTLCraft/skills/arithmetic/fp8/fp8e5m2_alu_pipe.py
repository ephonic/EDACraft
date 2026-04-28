#!/usr/bin/env python3
"""
Fully pipelined FP8 (E5M2) ALU.

Supported operations (3-bit op):
  000 = add
  001 = sub
  010 = mul
  011 = min
  100 = max
  101 = cmp_lt
  110 = cmp_eq

Pipeline: 3 stages with valid/ready handshaking.
  Stage 1: Unpack & Align
  Stage 2: Compute (add/sub/mul/cmp)
  Stage 3: Normalize, Round & Pack

Notes:
- Subnormals are handled (exp=0, hidden=0).
- NaN propagation follows simplified rules (any NaN input -> canonical NaN output).
- Rounding is round-half-up for simplicity.
- Overflow -> inf, underflow -> zero.
"""

from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import Const, Cat, Mux, If, Else

BIAS = 15
EXP_WIDTH = 5
MANT_WIDTH = 2
# internal mantissa = hidden + explicit = 3 bits
MAN_FULL_W = 3
# guard bits for add/sub = 3 (GRS)
ADD_GUARD = 3
ADD_PATH_W = MAN_FULL_W + ADD_GUARD  # 6
# add/sub signed width: 6-bit unsigned max 63, signed 8-bit covers [-128,127]
ADD_SIGNED_W = 8


class FP8ALU(Module):
    def __init__(self, name="fp8e5m2_alu"):
        super().__init__(name)

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")

        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.op = Input(3, "op")

        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.result = Output(8, "result")
        self.flags = Output(4, "flags")  # {NV, OF, UF, NX}

        # ------------------------------------------------------------------
        # Stage 1: Unpack wires
        # ------------------------------------------------------------------
        self.a_sign = Wire(1, "a_sign")
        self.a_exp = Wire(EXP_WIDTH, "a_exp")
        self.a_mant = Wire(MANT_WIDTH, "a_mant")
        self.a_hidden = Wire(1, "a_hidden")
        self.a_mant_full = Wire(MAN_FULL_W, "a_mant_full")
        self.a_is_nan = Wire(1, "a_is_nan")
        self.a_is_inf = Wire(1, "a_is_inf")
        self.a_is_zero = Wire(1, "a_is_zero")
        self.a_mag = Wire(EXP_WIDTH + MANT_WIDTH, "a_mag")

        self.b_sign = Wire(1, "b_sign")
        self.b_exp = Wire(EXP_WIDTH, "b_exp")
        self.b_mant = Wire(MANT_WIDTH, "b_mant")
        self.b_hidden = Wire(1, "b_hidden")
        self.b_mant_full = Wire(MAN_FULL_W, "b_mant_full")
        self.b_is_nan = Wire(1, "b_is_nan")
        self.b_is_inf = Wire(1, "b_is_inf")
        self.b_is_zero = Wire(1, "b_is_zero")
        self.b_mag = Wire(EXP_WIDTH + MANT_WIDTH, "b_mag")

        @self.comb
        def _s1_unpack():
            self.a_sign <<= self.a[7]
            self.a_exp <<= self.a[6:2]
            self.a_mant <<= self.a[1:0]
            self.a_hidden <<= Mux(self.a_exp == 0, 0, 1)
            self.a_mant_full <<= Cat(self.a_hidden, self.a_mant)
            self.a_is_nan <<= (self.a_exp == 31) & (self.a_mant != 0)
            self.a_is_inf <<= (self.a_exp == 31) & (self.a_mant == 0)
            self.a_is_zero <<= (self.a_exp == 0) & (self.a_mant == 0)
            self.a_mag <<= Cat(self.a_exp, self.a_mant)

            self.b_sign <<= self.b[7]
            self.b_exp <<= self.b[6:2]
            self.b_mant <<= self.b[1:0]
            self.b_hidden <<= Mux(self.b_exp == 0, 0, 1)
            self.b_mant_full <<= Cat(self.b_hidden, self.b_mant)
            self.b_is_nan <<= (self.b_exp == 31) & (self.b_mant != 0)
            self.b_is_inf <<= (self.b_exp == 31) & (self.b_mant == 0)
            self.b_is_zero <<= (self.b_exp == 0) & (self.b_mant == 0)
            self.b_mag <<= Cat(self.b_exp, self.b_mant)

        # ------------------------------------------------------------------
        # Stage 1 -> Stage 2 registers
        # ------------------------------------------------------------------
        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a_sign = Reg(1, "s1_a_sign")
        self.s1_a_exp = Reg(EXP_WIDTH, "s1_a_exp")
        self.s1_a_mant_full = Reg(MAN_FULL_W, "s1_a_mant_full")
        self.s1_a_is_nan = Reg(1, "s1_a_is_nan")
        self.s1_a_is_inf = Reg(1, "s1_a_is_inf")
        self.s1_a_is_zero = Reg(1, "s1_a_is_zero")
        self.s1_a_mag = Reg(EXP_WIDTH + MANT_WIDTH, "s1_a_mag")

        self.s1_b_sign = Reg(1, "s1_b_sign")
        self.s1_b_exp = Reg(EXP_WIDTH, "s1_b_exp")
        self.s1_b_mant_full = Reg(MAN_FULL_W, "s1_b_mant_full")
        self.s1_b_is_nan = Reg(1, "s1_b_is_nan")
        self.s1_b_is_inf = Reg(1, "s1_b_is_inf")
        self.s1_b_is_zero = Reg(1, "s1_b_is_zero")
        self.s1_b_mag = Reg(EXP_WIDTH + MANT_WIDTH, "s1_b_mag")

        self.s1_op = Reg(3, "s1_op")

        # Pre-declare downstream valid regs for ready calculation
        self.s2_valid = Reg(1, "s2_valid")
        self.o_valid_reg = Reg(1, "o_valid_reg")

        self.s1_ready = Wire(1, "s1_ready")
        self.s2_ready = Wire(1, "s2_ready")
        self.s3_ready = Wire(1, "s3_ready")

        self.s1_ready <<= ~self.s1_valid | self.s2_ready
        self.s2_ready <<= ~self.s2_valid | self.s3_ready
        self.s3_ready <<= ~self.o_valid_reg | self.o_ready
        self.i_ready <<= self.s1_ready

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= Const(0, 1)
            with Else():
                with If(self.s1_ready):
                    self.s1_valid <<= self.i_valid
                    with If(self.i_valid):
                        self.s1_a_sign <<= self.a_sign
                        self.s1_a_exp <<= self.a_exp
                        self.s1_a_mant_full <<= self.a_mant_full
                        self.s1_a_is_nan <<= self.a_is_nan
                        self.s1_a_is_inf <<= self.a_is_inf
                        self.s1_a_is_zero <<= self.a_is_zero
                        self.s1_a_mag <<= self.a_mag

                        self.s1_b_sign <<= self.b_sign
                        self.s1_b_exp <<= self.b_exp
                        self.s1_b_mant_full <<= self.b_mant_full
                        self.s1_b_is_nan <<= self.b_is_nan
                        self.s1_b_is_inf <<= self.b_is_inf
                        self.s1_b_is_zero <<= self.b_is_zero
                        self.s1_b_mag <<= self.b_mag

                        self.s1_op <<= self.op

        # ------------------------------------------------------------------
        # Stage 2: Compute
        # ------------------------------------------------------------------
        self.s2_valid = Reg(1, "s2_valid")

        # Add/Sub intermediate wires
        self.add_eff_b_sign = Wire(1, "add_eff_b_sign")
        self.add_a_is_bigger = Wire(1, "add_a_is_bigger")
        self.add_big_exp = Wire(EXP_WIDTH, "add_big_exp")
        self.add_big_sign = Wire(1, "add_big_sign")
        self.add_big_mant = Wire(MAN_FULL_W, "add_big_mant")
        self.add_small_sign = Wire(1, "add_small_sign")
        self.add_small_mant = Wire(MAN_FULL_W, "add_small_mant")
        self.add_shift = Wire(EXP_WIDTH, "add_shift")
        self.add_small_mant_shifted = Wire(ADD_PATH_W, "add_small_mant_shifted")
        self.add_big_mant_ext = Wire(ADD_SIGNED_W, "add_big_mant_ext")
        self.add_small_mant_ext = Wire(ADD_SIGNED_W, "add_small_mant_ext")
        self.add_signed_big = Wire(ADD_SIGNED_W, "add_signed_big")
        self.add_signed_small = Wire(ADD_SIGNED_W, "add_signed_small")
        self.add_raw_sum = Wire(ADD_SIGNED_W + 1, "add_raw_sum")
        self.add_res_sign = Wire(1, "add_res_sign")
        self.add_res_mag = Wire(ADD_SIGNED_W + 1, "add_res_mag")
        self.add_norm_mant = Wire(MAN_FULL_W, "add_norm_mant")
        self.add_norm_exp = Wire(7, "add_norm_exp")

        # Mul intermediate wires
        self.mul_sign = Wire(1, "mul_sign")
        self.mul_a_eff_exp = Wire(EXP_WIDTH, "mul_a_eff_exp")
        self.mul_b_eff_exp = Wire(EXP_WIDTH, "mul_b_eff_exp")
        self.mul_exp_raw = Wire(7, "mul_exp_raw")
        self.mul_prod = Wire(MAN_FULL_W * 2, "mul_prod")  # 6b
        self.mul_ovf = Wire(1, "mul_ovf")
        self.mul_norm_prod = Wire(MAN_FULL_W * 2, "mul_norm_prod")
        self.mul_guard = Wire(1, "mul_guard")
        self.mul_mant_tmp = Wire(MAN_FULL_W + 1, "mul_mant_tmp")  # 4b
        self.mul_mant_ovf = Wire(1, "mul_mant_ovf")
        self.mul_mant = Wire(MAN_FULL_W, "mul_mant")
        self.mul_exp = Wire(7, "mul_exp")

        # Cmp intermediate wires
        self.cmp_lt = Wire(1, "cmp_lt")
        self.cmp_eq = Wire(1, "cmp_eq")
        self.minmax_sel_a = Wire(1, "minmax_sel_a")

        @self.comb
        def _s2_compute():
            # ---- add/sub --------------------------------------------------
            self.add_eff_b_sign <<= Mux(self.s1_op == 1, self.s1_b_sign ^ 1, self.s1_b_sign)
            self.add_a_is_bigger <<= (self.s1_a_exp > self.s1_b_exp) | (
                (self.s1_a_exp == self.s1_b_exp) & (self.s1_a_mant_full >= self.s1_b_mant_full)
            )
            self.add_big_exp <<= Mux(self.add_a_is_bigger, self.s1_a_exp, self.s1_b_exp)
            self.add_big_sign <<= Mux(self.add_a_is_bigger, self.s1_a_sign, self.add_eff_b_sign)
            self.add_big_mant <<= Mux(self.add_a_is_bigger, self.s1_a_mant_full, self.s1_b_mant_full)
            self.add_small_sign <<= Mux(
                self.add_a_is_bigger, self.add_eff_b_sign, self.s1_a_sign
            )
            self.add_small_mant <<= Mux(self.add_a_is_bigger, self.s1_b_mant_full, self.s1_a_mant_full)
            self.add_shift <<= Mux(
                self.add_a_is_bigger,
                self.s1_a_exp - self.s1_b_exp,
                self.s1_b_exp - self.s1_a_exp,
            )
            # Align small mantissa
            self.add_small_mant_shifted <<= (
                Cat(self.add_small_mant, Const(0, ADD_GUARD)) >> self.add_shift
            )
            self.add_big_mant_ext <<= Cat(Const(0, ADD_SIGNED_W - ADD_PATH_W), self.add_big_mant, Const(0, ADD_GUARD))
            self.add_small_mant_ext <<= Cat(
                Const(0, ADD_SIGNED_W - ADD_PATH_W), self.add_small_mant_shifted
            )
            self.add_signed_big <<= Mux(
                self.add_big_sign,
                Const(0, ADD_SIGNED_W) - self.add_big_mant_ext,
                self.add_big_mant_ext,
            )
            self.add_signed_small <<= Mux(
                self.add_small_sign,
                Const(0, ADD_SIGNED_W) - self.add_small_mant_ext,
                self.add_small_mant_ext,
            )
            self.add_raw_sum <<= Cat(
                self.add_signed_big[ADD_SIGNED_W - 1], self.add_signed_big
            ) + Cat(
                self.add_signed_small[ADD_SIGNED_W - 1], self.add_signed_small
            )
            self.add_res_sign <<= self.add_raw_sum[ADD_SIGNED_W]
            self.add_res_mag <<= Mux(
                self.add_res_sign,
                Const(0, ADD_SIGNED_W + 1) - self.add_raw_sum,
                self.add_raw_sum,
            )

            # Normalize add/sub result (leading zero detection)
            # add_res_mag width = 9. Leading one can be at bit 6 max (64..126)
            with If(self.add_res_mag[6]):
                self.add_norm_mant <<= self.add_res_mag[6:4]
                self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) + 1
            with Else():
                with If(self.add_res_mag[5]):
                    self.add_norm_mant <<= self.add_res_mag[5:3]
                    self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp)
                with Else():
                    with If(self.add_res_mag[4]):
                        self.add_norm_mant <<= self.add_res_mag[4:2]
                        self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 1
                    with Else():
                        with If(self.add_res_mag[3]):
                            self.add_norm_mant <<= self.add_res_mag[3:1]
                            self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 2
                        with Else():
                            with If(self.add_res_mag[2]):
                                self.add_norm_mant <<= self.add_res_mag[2:0]
                                self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 3
                            with Else():
                                with If(self.add_res_mag[1]):
                                    self.add_norm_mant <<= Cat(self.add_res_mag[1:0], Const(0, 1))
                                    self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 4
                                with Else():
                                    with If(self.add_res_mag[0]):
                                        self.add_norm_mant <<= Cat(self.add_res_mag[0], Const(0, 2))
                                        self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 5
                                    with Else():
                                        self.add_norm_mant <<= Const(0, MAN_FULL_W)
                                        self.add_norm_exp <<= Const(0, 7)

            # ---- mul ------------------------------------------------------
            self.mul_sign <<= self.s1_a_sign ^ self.s1_b_sign
            self.mul_a_eff_exp <<= Mux(self.s1_a_exp == 0, 1, self.s1_a_exp)
            self.mul_b_eff_exp <<= Mux(self.s1_b_exp == 0, 1, self.s1_b_exp)
            self.mul_exp_raw <<= self.mul_a_eff_exp + self.mul_b_eff_exp - BIAS
            self.mul_prod <<= self.s1_a_mant_full * self.s1_b_mant_full
            self.mul_ovf <<= self.mul_prod[MAN_FULL_W * 2 - 1]
            self.mul_norm_prod <<= Mux(self.mul_ovf, self.mul_prod >> 1, self.mul_prod)
            self.mul_guard <<= Mux(self.mul_ovf, self.mul_prod[0], self.mul_prod[1])
            self.mul_mant_tmp <<= self.mul_norm_prod[MAN_FULL_W * 2 - 2 : MAN_FULL_W * 2 - 4] + self.mul_guard
            self.mul_mant_ovf <<= self.mul_mant_tmp[MAN_FULL_W]
            self.mul_mant <<= Mux(
                self.mul_mant_ovf,
                Const(0b100, MAN_FULL_W),
                self.mul_mant_tmp[MAN_FULL_W - 1 : 0],
            )
            self.mul_exp <<= self.mul_exp_raw + self.mul_ovf + self.mul_mant_ovf

            # ---- cmp ------------------------------------------------------
            with If(self.s1_a_is_nan | self.s1_b_is_nan):
                self.cmp_lt <<= Const(0, 1)
                self.cmp_eq <<= Const(0, 1)
                self.minmax_sel_a <<= Mux(self.s1_b_is_nan, Const(1, 1), Const(0, 1))
            with Else():
                with If(self.s1_a_is_zero & self.s1_b_is_zero):
                    self.cmp_lt <<= Const(0, 1)
                    self.cmp_eq <<= Const(1, 1)
                    self.minmax_sel_a <<= Const(0, 1)
                with Else():
                    with If(self.s1_a_sign != self.s1_b_sign):
                        self.cmp_eq <<= Const(0, 1)
                        with If(self.s1_a_sign == 1):
                            self.cmp_lt <<= Const(1, 1)
                            self.minmax_sel_a <<= Mux(self.s1_op == 3, Const(1, 1), Const(0, 1))
                        with Else():
                            self.cmp_lt <<= Const(0, 1)
                            self.minmax_sel_a <<= Mux(self.s1_op == 3, Const(0, 1), Const(1, 1))
                    with Else():
                        self.cmp_eq <<= self.s1_a_mag == self.s1_b_mag
                        with If(self.s1_a_sign == 0):
                            self.cmp_lt <<= self.s1_a_mag < self.s1_b_mag
                            self.minmax_sel_a <<= Mux(
                                self.s1_op == 3,
                                self.s1_a_mag < self.s1_b_mag,
                                self.s1_a_mag > self.s1_b_mag,
                            )
                        with Else():
                            self.cmp_lt <<= self.s1_a_mag > self.s1_b_mag
                            self.minmax_sel_a <<= Mux(
                                self.s1_op == 3,
                                self.s1_a_mag > self.s1_b_mag,
                                self.s1_a_mag < self.s1_b_mag,
                            )

        # Stage 2 -> Stage 3 comb + registers
        self.s2_res_sign = Reg(1, "s2_res_sign")
        self.s2_res_exp = Reg(7, "s2_res_exp")
        self.s2_res_mant = Reg(MAN_FULL_W, "s2_res_mant")
        self.s2_is_nan = Reg(1, "s2_is_nan")
        self.s2_is_inf = Reg(1, "s2_is_inf")
        self.s2_is_zero = Reg(1, "s2_is_zero")
        self.s2_op = Reg(3, "s2_op")
        self.s2_cmp_lt = Reg(1, "s2_cmp_lt")
        self.s2_cmp_eq = Reg(1, "s2_cmp_eq")
        self.s2_minmax_sel_a = Reg(1, "s2_minmax_sel_a")
        self.s2_minmax_a = Reg(8, "s2_minmax_a")
        self.s2_minmax_b = Reg(8, "s2_minmax_b")

        self.s2_res_sign_in = Wire(1, "s2_res_sign_in")
        self.s2_res_exp_in = Wire(7, "s2_res_exp_in")
        self.s2_res_mant_in = Wire(MAN_FULL_W, "s2_res_mant_in")
        self.s2_is_nan_in = Wire(1, "s2_is_nan_in")
        self.s2_is_inf_in = Wire(1, "s2_is_inf_in")
        self.s2_is_zero_in = Wire(1, "s2_is_zero_in")
        self.s2_cmp_lt_in = Wire(1, "s2_cmp_lt_in")
        self.s2_cmp_eq_in = Wire(1, "s2_cmp_eq_in")
        self.s2_minmax_sel_a_in = Wire(1, "s2_minmax_sel_a_in")

        @self.comb
        def _s2_to_s3_comb():
            is_mul = self.s1_op == 2
            is_addsub = (self.s1_op == 0) | (self.s1_op == 1)

            self.s2_res_sign_in <<= Mux(is_mul, self.mul_sign, self.add_res_sign)
            self.s2_res_exp_in <<= Mux(is_mul, self.mul_exp, self.add_norm_exp)
            self.s2_res_mant_in <<= Mux(is_mul, self.mul_mant, self.add_norm_mant)

            # NaN/Inf/Zero flags for arith ops
            addsub_nan = self.s1_a_is_nan | self.s1_b_is_nan | (
                self.s1_a_is_inf & self.s1_b_is_inf & is_addsub & (self.s1_a_sign != self.add_eff_b_sign)
            )
            mul_nan = self.s1_a_is_nan | self.s1_b_is_nan | (self.s1_a_is_inf & self.s1_b_is_zero) | (self.s1_a_is_zero & self.s1_b_is_inf)
            arith_nan = Mux(is_mul, mul_nan, addsub_nan)

            mul_exp_msb = self.mul_exp[6]
            add_norm_exp_msb = self.add_norm_exp[6]
            addsub_inf = (self.s1_a_is_inf | self.s1_b_is_inf | ((self.add_norm_exp >= 31) & ~add_norm_exp_msb)) & ~arith_nan
            mul_inf = (self.s1_a_is_inf | self.s1_b_is_inf | ((self.mul_exp >= 31) & ~mul_exp_msb)) & ~arith_nan
            arith_inf = Mux(is_mul, mul_inf, addsub_inf)

            addsub_zero = (self.add_res_mag == 0) & is_addsub
            mul_zero = self.s1_a_is_zero | self.s1_b_is_zero
            arith_zero = Mux(is_mul, mul_zero, addsub_zero)

            self.s2_is_nan_in <<= arith_nan
            self.s2_is_inf_in <<= arith_inf
            self.s2_is_zero_in <<= arith_zero & ~arith_nan & ~arith_inf

            self.s2_cmp_lt_in <<= self.cmp_lt
            self.s2_cmp_eq_in <<= self.cmp_eq
            self.s2_minmax_sel_a_in <<= self.minmax_sel_a

        # Pass raw a/b through s1 for minmax
        self.s1_a_raw = Reg(8, "s1_a_raw")
        self.s1_b_raw = Reg(8, "s1_b_raw")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_raw_seq():
            with If(self.rst_n == 0):
                pass
            with Else():
                with If(self.s1_ready & self.i_valid):
                    self.s1_a_raw <<= self.a
                    self.s1_b_raw <<= self.b

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s2_seq():
            with If(self.rst_n == 0):
                self.s2_valid <<= Const(0, 1)
            with Else():
                with If(self.s2_ready):
                    self.s2_valid <<= self.s1_valid
                    with If(self.s1_valid):
                        self.s2_res_sign <<= self.s2_res_sign_in
                        self.s2_res_exp <<= self.s2_res_exp_in
                        self.s2_res_mant <<= self.s2_res_mant_in
                        self.s2_is_nan <<= self.s2_is_nan_in
                        self.s2_is_inf <<= self.s2_is_inf_in
                        self.s2_is_zero <<= self.s2_is_zero_in
                        self.s2_op <<= self.s1_op
                        self.s2_cmp_lt <<= self.s2_cmp_lt_in
                        self.s2_cmp_eq <<= self.s2_cmp_eq_in
                        self.s2_minmax_sel_a <<= self.s2_minmax_sel_a_in
                        self.s2_minmax_a <<= self.s1_a_raw
                        self.s2_minmax_b <<= self.s1_b_raw

        # ------------------------------------------------------------------
        # Stage 3: Pack & Output
        # ------------------------------------------------------------------
        self.arith_result = Wire(8, "arith_result")
        self.cmp_result = Wire(8, "cmp_result")
        self.minmax_result = Wire(8, "minmax_result")
        self.final_result = Wire(8, "final_result")
        self.final_flags = Wire(4, "final_flags")
        self.result_reg = Reg(8, "result_reg")
        self.flags_reg = Reg(4, "flags_reg")

        @self.comb
        def _s3_pack():
            # Arithmetic packing
            with If(self.s2_is_nan):
                self.arith_result <<= Cat(Const(0, 1), Const(31, EXP_WIDTH), Const(0b01, MANT_WIDTH))
            with Else():
                exp_msb = self.s2_res_exp[6]
                with If(self.s2_is_inf | ((self.s2_res_exp >= 31) & ~exp_msb)):
                    self.arith_result <<= Cat(self.s2_res_sign, Const(31, EXP_WIDTH), Const(0, MANT_WIDTH))
                with Else():
                    with If(self.s2_is_zero | exp_msb):
                        self.arith_result <<= Cat(self.s2_res_sign, Const(0, EXP_WIDTH), Const(0, MANT_WIDTH))
                    with Else():
                        self.arith_result <<= Cat(
                            self.s2_res_sign,
                            self.s2_res_exp[EXP_WIDTH - 1 : 0],
                            self.s2_res_mant[MANT_WIDTH - 1 : 0],
                        )

            # Compare result: bit0 = predicate
            cmp_bit = Mux(self.s2_op == 5, self.s2_cmp_lt, self.s2_cmp_eq)
            self.cmp_result <<= Cat(Const(0, 7), cmp_bit)

            # Min/Max result
            self.minmax_result <<= Mux(self.s2_minmax_sel_a, self.s2_minmax_a, self.s2_minmax_b)

            # Final mux
            is_cmp = (self.s2_op == 5) | (self.s2_op == 6)
            is_minmax = (self.s2_op == 3) | (self.s2_op == 4)
            with If(is_cmp):
                self.final_result <<= self.cmp_result
            with Else():
                with If(is_minmax):
                    self.final_result <<= self.minmax_result
                with Else():
                    self.final_result <<= self.arith_result

            # Flags
            is_arith = (self.s2_op == 0) | (self.s2_op == 1) | (self.s2_op == 2)
            nv = self.s2_is_nan & is_arith
            of = self.s2_is_inf & is_arith
            uf = self.s2_is_zero & ~nv & ~of & is_arith
            self.final_flags <<= Cat(nv, of, uf, Const(0, 1))

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s3_seq():
            with If(self.rst_n == 0):
                self.o_valid_reg <<= Const(0, 1)
            with Else():
                with If(self.s3_ready):
                    self.o_valid_reg <<= self.s2_valid
                    with If(self.s2_valid):
                        self.result_reg <<= self.final_result
                        self.flags_reg <<= self.final_flags

        @self.comb
        def _output_assign():
            self.o_valid <<= self.o_valid_reg
            self.result <<= self.result_reg
            self.flags <<= self.flags_reg


# ---------------------------------------------------------------------------
# Generate Verilog when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from rtlgen import VerilogEmitter

    top = FP8ALU()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
