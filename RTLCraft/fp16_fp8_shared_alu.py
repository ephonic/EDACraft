#!/usr/bin/env python3
"""
FP16 / FP8 (E5M2) Shared Hardware Pipeline ALU.

Supported operations (3-bit op):
  000 = add
  001 = sub
  010 = mul
  011 = min
  100 = max
  101 = cmp_lt
  110 = cmp_eq

Format (1-bit fmt):
  0 = FP8  (E5M2, 8-bit, occupies low byte of 16-bit port)
  1 = FP16 (E5M10, 16-bit full width)

Pipeline: 3 stages with valid/ready handshaking.
  Stage 1: Unpack & Align  (format-aware unpack to unified internal format)
  Stage 2: Compute         (shared datapath at FP16 precision)
  Stage 3: Normalize, Round & Pack  (format-aware pack)

Notes:
- FP8 inputs are unpacked with mantissa zero-extended to 10 bits,
  allowing them to share the FP16 compute datapath.
- FP8 outputs are packed by truncating/rounding the 10-bit mantissa
  down to 2 bits.
- Subnormals are handled (exp=0, hidden=0).
- NaN propagation follows simplified rules (any NaN input -> canonical NaN output).
- Rounding is round-half-up.
- Overflow -> inf, underflow -> zero.
"""

from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import Const, Cat, Mux, If, Else

BIAS = 15
EXP_WIDTH = 5
FP16_MANT_WIDTH = 10
FP8_MANT_WIDTH = 2
# Internal unified mantissa = hidden + explicit = 11 bits
MAN_FULL_W = 11
# Guard bits for add/sub = 3 (GRS)
ADD_GUARD = 3
ADD_PATH_W = MAN_FULL_W + ADD_GUARD  # 14
# Add/sub signed width: 14-bit unsigned max 16383, signed 16-bit covers [-32768,32767]
ADD_SIGNED_W = 16


class FP16FP8SharedALU(Module):
    def __init__(self, name="FP16FP8SharedALU"):
        super().__init__(name)

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")

        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.op = Input(3, "op")
        self.fmt = Input(1, "fmt")   # 0=FP8, 1=FP16

        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.result = Output(16, "result")
        self.flags = Output(4, "flags")  # {NV, OF, UF, NX}

        # ------------------------------------------------------------------
        # Stage 1: Unpack wires (format-aware)
        # ------------------------------------------------------------------
        # FP8 signals (low byte)
        self.a_sign_fp8 = Wire(1, "a_sign_fp8")
        self.a_exp_fp8 = Wire(EXP_WIDTH, "a_exp_fp8")
        self.a_mant_fp8 = Wire(FP8_MANT_WIDTH, "a_mant_fp8")
        self.a_hidden_fp8 = Wire(1, "a_hidden_fp8")
        self.a_mant_full_fp8 = Wire(MAN_FULL_W, "a_mant_full_fp8")

        self.b_sign_fp8 = Wire(1, "b_sign_fp8")
        self.b_exp_fp8 = Wire(EXP_WIDTH, "b_exp_fp8")
        self.b_mant_fp8 = Wire(FP8_MANT_WIDTH, "b_mant_fp8")
        self.b_hidden_fp8 = Wire(1, "b_hidden_fp8")
        self.b_mant_full_fp8 = Wire(MAN_FULL_W, "b_mant_full_fp8")

        # FP16 signals (full width)
        self.a_sign_fp16 = Wire(1, "a_sign_fp16")
        self.a_exp_fp16 = Wire(EXP_WIDTH, "a_exp_fp16")
        self.a_mant_fp16 = Wire(FP16_MANT_WIDTH, "a_mant_fp16")
        self.a_hidden_fp16 = Wire(1, "a_hidden_fp16")
        self.a_mant_full_fp16 = Wire(MAN_FULL_W, "a_mant_full_fp16")

        self.b_sign_fp16 = Wire(1, "b_sign_fp16")
        self.b_exp_fp16 = Wire(EXP_WIDTH, "b_exp_fp16")
        self.b_mant_fp16 = Wire(FP16_MANT_WIDTH, "b_mant_fp16")
        self.b_hidden_fp16 = Wire(1, "b_hidden_fp16")
        self.b_mant_full_fp16 = Wire(MAN_FULL_W, "b_mant_full_fp16")

        # Format-muxed outputs of stage 1
        self.a_sign = Wire(1, "a_sign")
        self.a_exp = Wire(EXP_WIDTH, "a_exp")
        self.a_mant_full = Wire(MAN_FULL_W, "a_mant_full")
        self.a_is_nan = Wire(1, "a_is_nan")
        self.a_is_inf = Wire(1, "a_is_inf")
        self.a_is_zero = Wire(1, "a_is_zero")
        self.a_mag = Wire(EXP_WIDTH + FP16_MANT_WIDTH, "a_mag")

        self.b_sign = Wire(1, "b_sign")
        self.b_exp = Wire(EXP_WIDTH, "b_exp")
        self.b_mant_full = Wire(MAN_FULL_W, "b_mant_full")
        self.b_is_nan = Wire(1, "b_is_nan")
        self.b_is_inf = Wire(1, "b_is_inf")
        self.b_is_zero = Wire(1, "b_is_zero")
        self.b_mag = Wire(EXP_WIDTH + FP16_MANT_WIDTH, "b_mag")

        @self.comb
        def _s1_unpack():
            # ---- FP8 unpack (low byte) ----
            self.a_sign_fp8 <<= self.a[7]
            self.a_exp_fp8 <<= self.a[6:2]
            self.a_mant_fp8 <<= self.a[1:0]
            self.a_hidden_fp8 <<= Mux(self.a_exp_fp8 == 0, 0, 1)
            # zero-extend 2-bit mant to 10 bits, prepend hidden => 11 bits
            self.a_mant_full_fp8 <<= Cat(self.a_hidden_fp8, self.a_mant_fp8, Const(0, FP16_MANT_WIDTH - FP8_MANT_WIDTH))

            self.b_sign_fp8 <<= self.b[7]
            self.b_exp_fp8 <<= self.b[6:2]
            self.b_mant_fp8 <<= self.b[1:0]
            self.b_hidden_fp8 <<= Mux(self.b_exp_fp8 == 0, 0, 1)
            self.b_mant_full_fp8 <<= Cat(self.b_hidden_fp8, self.b_mant_fp8, Const(0, FP16_MANT_WIDTH - FP8_MANT_WIDTH))

            # ---- FP16 unpack ----
            self.a_sign_fp16 <<= self.a[15]
            self.a_exp_fp16 <<= self.a[14:10]
            self.a_mant_fp16 <<= self.a[9:0]
            self.a_hidden_fp16 <<= Mux(self.a_exp_fp16 == 0, 0, 1)
            self.a_mant_full_fp16 <<= Cat(self.a_hidden_fp16, self.a_mant_fp16)

            self.b_sign_fp16 <<= self.b[15]
            self.b_exp_fp16 <<= self.b[14:10]
            self.b_mant_fp16 <<= self.b[9:0]
            self.b_hidden_fp16 <<= Mux(self.b_exp_fp16 == 0, 0, 1)
            self.b_mant_full_fp16 <<= Cat(self.b_hidden_fp16, self.b_mant_fp16)

            # ---- Format mux ----
            self.a_sign <<= Mux(self.fmt, self.a_sign_fp16, self.a_sign_fp8)
            self.a_exp <<= Mux(self.fmt, self.a_exp_fp16, self.a_exp_fp8)
            self.a_mant_full <<= Mux(self.fmt, self.a_mant_full_fp16, self.a_mant_full_fp8)
            self.a_is_nan <<= Mux(self.fmt,
                (self.a_exp_fp16 == 31) & (self.a_mant_fp16 != 0),
                (self.a_exp_fp8 == 31) & (self.a_mant_fp8 != 0))
            self.a_is_inf <<= Mux(self.fmt,
                (self.a_exp_fp16 == 31) & (self.a_mant_fp16 == 0),
                (self.a_exp_fp8 == 31) & (self.a_mant_fp8 == 0))
            self.a_is_zero <<= Mux(self.fmt,
                (self.a_exp_fp16 == 0) & (self.a_mant_fp16 == 0),
                (self.a_exp_fp8 == 0) & (self.a_mant_fp8 == 0))
            self.a_mag <<= Cat(self.a_exp, Mux(self.fmt, self.a_mant_fp16, Cat(self.a_mant_fp8, Const(0, FP16_MANT_WIDTH - FP8_MANT_WIDTH))))

            self.b_sign <<= Mux(self.fmt, self.b_sign_fp16, self.b_sign_fp8)
            self.b_exp <<= Mux(self.fmt, self.b_exp_fp16, self.b_exp_fp8)
            self.b_mant_full <<= Mux(self.fmt, self.b_mant_full_fp16, self.b_mant_full_fp8)
            self.b_is_nan <<= Mux(self.fmt,
                (self.b_exp_fp16 == 31) & (self.b_mant_fp16 != 0),
                (self.b_exp_fp8 == 31) & (self.b_mant_fp8 != 0))
            self.b_is_inf <<= Mux(self.fmt,
                (self.b_exp_fp16 == 31) & (self.b_mant_fp16 == 0),
                (self.b_exp_fp8 == 31) & (self.b_mant_fp8 == 0))
            self.b_is_zero <<= Mux(self.fmt,
                (self.b_exp_fp16 == 0) & (self.b_mant_fp16 == 0),
                (self.b_exp_fp8 == 0) & (self.b_mant_fp8 == 0))
            self.b_mag <<= Cat(self.b_exp, Mux(self.fmt, self.b_mant_fp16, Cat(self.b_mant_fp8, Const(0, FP16_MANT_WIDTH - FP8_MANT_WIDTH))))

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
        self.s1_a_mag = Reg(EXP_WIDTH + FP16_MANT_WIDTH, "s1_a_mag")

        self.s1_b_sign = Reg(1, "s1_b_sign")
        self.s1_b_exp = Reg(EXP_WIDTH, "s1_b_exp")
        self.s1_b_mant_full = Reg(MAN_FULL_W, "s1_b_mant_full")
        self.s1_b_is_nan = Reg(1, "s1_b_is_nan")
        self.s1_b_is_inf = Reg(1, "s1_b_is_inf")
        self.s1_b_is_zero = Reg(1, "s1_b_is_zero")
        self.s1_b_mag = Reg(EXP_WIDTH + FP16_MANT_WIDTH, "s1_b_mag")

        self.s1_op = Reg(3, "s1_op")
        self.s1_fmt = Reg(1, "s1_fmt")

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
                        self.s1_fmt <<= self.fmt

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
        self.add_norm_shift = Wire(4, "add_norm_shift")
        self.add_norm_shifted = Wire(32, "add_norm_shifted")
        self.add_norm_mant = Wire(MAN_FULL_W, "add_norm_mant")
        self.add_norm_exp = Wire(7, "add_norm_exp")

        # Mul intermediate wires
        self.mul_sign = Wire(1, "mul_sign")
        self.mul_a_eff_exp = Wire(EXP_WIDTH, "mul_a_eff_exp")
        self.mul_b_eff_exp = Wire(EXP_WIDTH, "mul_b_eff_exp")
        self.mul_exp_raw = Wire(7, "mul_exp_raw")
        self.mul_prod = Wire(MAN_FULL_W * 2, "mul_prod")  # 22b
        self.mul_ovf = Wire(1, "mul_ovf")
        self.mul_norm_prod = Wire(MAN_FULL_W * 2, "mul_norm_prod")
        self.mul_guard = Wire(1, "mul_guard")
        self.mul_mant_tmp = Wire(MAN_FULL_W + 1, "mul_mant_tmp")  # 12b
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

            # Normalize add/sub result via LZD (leading zero detection)
            # add_res_mag[14:0] holds the magnitude. Build priority encoder.
            shift_val = Const(15, 4)  # default: all zeros
            for i in range(0, 15):
                desired_shift = 14 - i
                shift_val = Mux(self.add_res_mag[i], Const(desired_shift, 4), shift_val)
            self.add_norm_shift <<= shift_val

            self.add_norm_shifted <<= self.add_res_mag << self.add_norm_shift
            self.add_norm_mant <<= Mux(
                self.add_res_mag == 0,
                Const(0, MAN_FULL_W),
                self.add_norm_shifted[14:4],
            )
            self.add_norm_exp <<= Mux(
                self.add_res_mag == 0,
                Const(0, 7),
                Cat(Const(0, 2), self.add_big_exp) + 1 - self.add_norm_shift,
            )

            # ---- mul ------------------------------------------------------
            self.mul_sign <<= self.s1_a_sign ^ self.s1_b_sign
            self.mul_a_eff_exp <<= Mux(self.s1_a_exp == 0, 1, self.s1_a_exp)
            self.mul_b_eff_exp <<= Mux(self.s1_b_exp == 0, 1, self.s1_b_exp)
            self.mul_exp_raw <<= self.mul_a_eff_exp + self.mul_b_eff_exp - BIAS
            self.mul_prod <<= self.s1_a_mant_full * self.s1_b_mant_full
            self.mul_ovf <<= self.mul_prod[MAN_FULL_W * 2 - 1]
            self.mul_norm_prod <<= Mux(self.mul_ovf, self.mul_prod >> 1, self.mul_prod)
            self.mul_guard <<= Mux(self.mul_ovf, self.mul_prod[0], self.mul_prod[1])
            self.mul_mant_tmp <<= self.mul_norm_prod[MAN_FULL_W * 2 - 2 : MAN_FULL_W * 2 - 12] + self.mul_guard
            self.mul_mant_ovf <<= self.mul_mant_tmp[MAN_FULL_W]
            self.mul_mant <<= Mux(
                self.mul_mant_ovf,
                Const(0b1 << (MAN_FULL_W - 1), MAN_FULL_W),  # 1 followed by zeros
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
        self.s2_fmt = Reg(1, "s2_fmt")
        self.s2_cmp_lt = Reg(1, "s2_cmp_lt")
        self.s2_cmp_eq = Reg(1, "s2_cmp_eq")
        self.s2_minmax_sel_a = Reg(1, "s2_minmax_sel_a")
        self.s2_minmax_a = Reg(16, "s2_minmax_a")
        self.s2_minmax_b = Reg(16, "s2_minmax_b")

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

        # Pass raw a/b through s1 for minmax (16-bit full)
        self.s1_a_raw = Reg(16, "s1_a_raw")
        self.s1_b_raw = Reg(16, "s1_b_raw")

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
                        self.s2_fmt <<= self.s1_fmt
                        self.s2_cmp_lt <<= self.s2_cmp_lt_in
                        self.s2_cmp_eq <<= self.s2_cmp_eq_in
                        self.s2_minmax_sel_a <<= self.s2_minmax_sel_a_in
                        self.s2_minmax_a <<= self.s1_a_raw
                        self.s2_minmax_b <<= self.s1_b_raw

        # ------------------------------------------------------------------
        # Stage 3: Pack & Output
        # ------------------------------------------------------------------
        # FP16 arithmetic pack
        self.arith_result_fp16 = Wire(16, "arith_result_fp16")
        # FP8 arithmetic pack
        self.arith_result_fp8 = Wire(8, "arith_result_fp8")
        self.arith_result = Wire(16, "arith_result")

        self.cmp_result = Wire(16, "cmp_result")
        self.minmax_result = Wire(16, "minmax_result")
        self.final_result = Wire(16, "final_result")
        self.final_flags = Wire(4, "final_flags")
        self.result_reg = Reg(16, "result_reg")
        self.flags_reg = Reg(4, "flags_reg")

        # FP8 pack helper wires
        self.fp8_mant_top3 = Wire(3, "fp8_mant_top3")   # {hidden, m9, m8}
        self.fp8_mant_lower = Wire(8, "fp8_mant_lower") # m7..m0
        self.fp8_rounded_mant3 = Wire(4, "fp8_rounded_mant3")  # +1 may overflow to 4 bits
        self.fp8_rounded_exp = Wire(7, "fp8_rounded_exp")
        self.fp8_pack_exp = Wire(EXP_WIDTH, "fp8_pack_exp")
        self.fp8_pack_mant = Wire(FP8_MANT_WIDTH, "fp8_pack_mant")

        @self.comb
        def _s3_pack():
            # ---- FP16 arithmetic packing ----
            with If(self.s2_is_nan):
                self.arith_result_fp16 <<= Cat(Const(0, 1), Const(31, EXP_WIDTH), Const(1, FP16_MANT_WIDTH))
            with Else():
                exp_msb = self.s2_res_exp[6]
                with If(self.s2_is_inf | ((self.s2_res_exp >= 31) & ~exp_msb)):
                    self.arith_result_fp16 <<= Cat(self.s2_res_sign, Const(31, EXP_WIDTH), Const(0, FP16_MANT_WIDTH))
                with Else():
                    with If(self.s2_is_zero | exp_msb):
                        self.arith_result_fp16 <<= Cat(self.s2_res_sign, Const(0, EXP_WIDTH), Const(0, FP16_MANT_WIDTH))
                    with Else():
                        self.arith_result_fp16 <<= Cat(
                            self.s2_res_sign,
                            self.s2_res_exp[EXP_WIDTH - 1 : 0],
                            self.s2_res_mant[FP16_MANT_WIDTH - 1 : 0],
                        )

            # ---- FP8 arithmetic packing (round 10-bit mant to 2-bit) ----
            # Internal mant_full = {hidden, mant[9:0]} = 11 bits
            # For FP8 we need 2 explicit bits => top3 = mant_full[10:8], lower8 = mant_full[7:0]
            self.fp8_mant_top3 <<= self.s2_res_mant[10:8]
            self.fp8_mant_lower <<= self.s2_res_mant[7:0]
            # Round-half-up: if lower8 >= 128 (bit7 set), add 1 to top3
            self.fp8_rounded_mant3 <<= Cat(Const(0, 1), self.fp8_mant_top3) + Mux(self.fp8_mant_lower >= 128, Const(1, 1), Const(0, 1))
            # If overflow (4'b1000), right-shift and inc exp
            self.fp8_rounded_exp <<= self.s2_res_exp + Mux(self.fp8_rounded_mant3[3], Const(1, 1), Const(0, 1))
            # Final pack values after overflow handling
            self.fp8_pack_exp <<= Mux(self.fp8_rounded_mant3[3], self.fp8_rounded_exp[EXP_WIDTH - 1 : 0], self.fp8_rounded_exp[EXP_WIDTH - 1 : 0])
            self.fp8_pack_mant <<= Mux(self.fp8_rounded_mant3[3], Const(0, FP8_MANT_WIDTH), self.fp8_rounded_mant3[FP8_MANT_WIDTH - 1 : 0])

            with If(self.s2_is_nan):
                self.arith_result_fp8 <<= Cat(Const(0, 1), Const(31, EXP_WIDTH), Const(0b01, FP8_MANT_WIDTH))
            with Else():
                exp_msb = self.fp8_rounded_exp[6]
                with If(self.s2_is_inf | ((self.fp8_rounded_exp >= 31) & ~exp_msb)):
                    self.arith_result_fp8 <<= Cat(self.s2_res_sign, Const(31, EXP_WIDTH), Const(0, FP8_MANT_WIDTH))
                with Else():
                    with If(self.s2_is_zero | exp_msb):
                        self.arith_result_fp8 <<= Cat(self.s2_res_sign, Const(0, EXP_WIDTH), Const(0, FP8_MANT_WIDTH))
                    with Else():
                        self.arith_result_fp8 <<= Cat(
                            self.s2_res_sign,
                            self.fp8_pack_exp,
                            self.fp8_pack_mant,
                        )

            # Select arithmetic result by format
            self.arith_result <<= Mux(self.s2_fmt, self.arith_result_fp16, Cat(Const(0, 8), self.arith_result_fp8))

            # Compare result: bit0 = predicate
            cmp_bit = Mux(self.s2_op == 5, self.s2_cmp_lt, self.s2_cmp_eq)
            self.cmp_result <<= Cat(Const(0, 15), cmp_bit)

            # Min/Max result (format-aware: return same-format input)
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
            fp8_pack_overflow = self.fp8_rounded_mant3[3] & ~self.s2_fmt & (self.fp8_rounded_exp >= 31)
            of = (self.s2_is_inf | fp8_pack_overflow) & is_arith
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
            self.result <<= Mux(self.o_valid_reg, self.result_reg, Const(0, 16))
            self.flags <<= Mux(self.o_valid_reg, self.flags_reg, Const(0, 4))


# ---------------------------------------------------------------------------
# Generate Verilog when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from rtlgen import VerilogEmitter

    top = FP16FP8SharedALU()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
