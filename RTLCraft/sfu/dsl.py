"""Legacy-DSL implementation of a pipelined FP16 activation/trig SFU."""

from __future__ import annotations

from rtlgen_x.dsl import (
    Cat,
    Const,
    Else,
    If,
    Input,
    Memory,
    Module,
    Mux,
    Output,
    Reg,
    SRA,
    Switch,
    Wire,
)

from .lut_generator import (
    COEFF_STORAGE_WIDTH,
    COS_QUADRANT_TABLE,
    SIGMOID_TABLE,
    SIN_QUADRANT_TABLE,
    TANH_TABLE,
    pack_coeff_rows,
)
from .reference import (
    COEFF_FRAC_BITS,
    HALF_PI_Q24,
    OP_COS,
    OP_RELU,
    OP_SIGMOID,
    OP_SIN,
    OP_TANH,
    Q12_FRAC_BITS,
    Q12_ONE,
    Q24_FRAC_BITS,
    SIGMOID_MAX_Q12,
    TANH_MAX_Q12,
    TRIG_NORMALIZE_RECIP,
    TRIG_NORMALIZE_SHIFT,
    TRIG_REDUCE_RECIP,
    TRIG_REDUCE_RECIP_SHIFT,
)


OP_WIDTH = 3
FP16_WIDTH = 16
Q12_WIDTH = 16
Q24_WIDTH = 42
INDEX_WIDTH = 5
COEFF_WIDTH = 18
COEFF_PACK_WIDTH = COEFF_STORAGE_WIDTH * 3
DELTA2_WIDTH = 16
TERM_WIDTH = 36
POLY_WIDTH = 17

Q16_ONE = 1 << COEFF_FRAC_BITS
FP16_QNAN = 0x7E00
FP16_ONE = 0x3C00
FP16_NEG_ONE = 0xBC00


class Fp16Sfu(Module):
    """Fully pipelined scalar FP16 SFU with one-result-per-cycle throughput."""

    PIPE_STAGES = 6
    LATENCY = PIPE_STAGES - 1

    def __init__(self):
        super().__init__("fp16_sfu")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.in_valid = Input(1, "in_valid")
        self.op = Input(OP_WIDTH, "op")
        self.operand = Input(FP16_WIDTH, "operand")

        self.in_accept = Output(1, "in_accept")
        self.out_valid = Output(1, "out_valid")
        self.result = Output(FP16_WIDTH, "result")

        self.v0 = Reg(1, "v0", init_value=0)
        self.v1 = Reg(1, "v1", init_value=0)
        self.v2 = Reg(1, "v2", init_value=0)
        self.v3 = Reg(1, "v3", init_value=0)
        self.v4 = Reg(1, "v4", init_value=0)
        self.v5 = Reg(1, "v5", init_value=0)

        self.op_q0 = Reg(OP_WIDTH, "op_q0", init_value=0)
        self.sign_q0 = Reg(1, "sign_q0", init_value=0)
        self.relu_q0 = Reg(FP16_WIDTH, "relu_q0", init_value=0)
        self.is_nan_q0 = Reg(1, "is_nan_q0", init_value=0)
        self.is_inf_q0 = Reg(1, "is_inf_q0", init_value=0)
        self.sig_sat_q0 = Reg(1, "sig_sat_q0", init_value=0)
        self.sig_sat_val_q0 = Reg(FP16_WIDTH, "sig_sat_val_q0", init_value=0)
        self.tanh_sat_q0 = Reg(1, "tanh_sat_q0", init_value=0)
        self.tanh_sat_val_q0 = Reg(FP16_WIDTH, "tanh_sat_val_q0", init_value=0)
        self.mag_q12_q0 = Reg(Q12_WIDTH, "mag_q12_q0", init_value=0)
        self.mag_q24_q0 = Reg(Q24_WIDTH, "mag_q24_q0", init_value=0)

        self.op_q1 = Reg(OP_WIDTH, "op_q1", init_value=0)
        self.sign_q1 = Reg(1, "sign_q1", init_value=0)
        self.relu_q1 = Reg(FP16_WIDTH, "relu_q1", init_value=0)
        self.is_nan_q1 = Reg(1, "is_nan_q1", init_value=0)
        self.is_inf_q1 = Reg(1, "is_inf_q1", init_value=0)
        self.sig_sat_q1 = Reg(1, "sig_sat_q1", init_value=0)
        self.sig_sat_val_q1 = Reg(FP16_WIDTH, "sig_sat_val_q1", init_value=0)
        self.tanh_sat_q1 = Reg(1, "tanh_sat_q1", init_value=0)
        self.tanh_sat_val_q1 = Reg(FP16_WIDTH, "tanh_sat_val_q1", init_value=0)
        self.seg_idx_q1 = Reg(INDEX_WIDTH, "seg_idx_q1", init_value=0)
        self.delta_q12_q1 = Reg(Q12_WIDTH, "delta_q12_q1", init_value=0)
        self.trig_quad_q1 = Reg(2, "trig_quad_q1", init_value=0)
        self.trig_boundary_q1 = Reg(1, "trig_boundary_q1", init_value=0)
        self.trig_use_cos_q1 = Reg(1, "trig_use_cos_q1", init_value=0)

        self.op_q2 = Reg(OP_WIDTH, "op_q2", init_value=0)
        self.sign_q2 = Reg(1, "sign_q2", init_value=0)
        self.relu_q2 = Reg(FP16_WIDTH, "relu_q2", init_value=0)
        self.is_nan_q2 = Reg(1, "is_nan_q2", init_value=0)
        self.is_inf_q2 = Reg(1, "is_inf_q2", init_value=0)
        self.sig_sat_q2 = Reg(1, "sig_sat_q2", init_value=0)
        self.sig_sat_val_q2 = Reg(FP16_WIDTH, "sig_sat_val_q2", init_value=0)
        self.tanh_sat_q2 = Reg(1, "tanh_sat_q2", init_value=0)
        self.tanh_sat_val_q2 = Reg(FP16_WIDTH, "tanh_sat_val_q2", init_value=0)
        self.delta_q12_q2 = Reg(Q12_WIDTH, "delta_q12_q2", init_value=0)
        self.trig_quad_q2 = Reg(2, "trig_quad_q2", init_value=0)
        self.trig_boundary_q2 = Reg(1, "trig_boundary_q2", init_value=0)
        self.trig_use_cos_q2 = Reg(1, "trig_use_cos_q2", init_value=0)
        self.c0_q2 = Reg(COEFF_WIDTH, "c0_q2", init_value=0)
        self.c1_q2 = Reg(COEFF_WIDTH, "c1_q2", init_value=0)
        self.c2_q2 = Reg(COEFF_WIDTH, "c2_q2", init_value=0)

        self.op_q3 = Reg(OP_WIDTH, "op_q3", init_value=0)
        self.sign_q3 = Reg(1, "sign_q3", init_value=0)
        self.relu_q3 = Reg(FP16_WIDTH, "relu_q3", init_value=0)
        self.is_nan_q3 = Reg(1, "is_nan_q3", init_value=0)
        self.is_inf_q3 = Reg(1, "is_inf_q3", init_value=0)
        self.sig_sat_q3 = Reg(1, "sig_sat_q3", init_value=0)
        self.sig_sat_val_q3 = Reg(FP16_WIDTH, "sig_sat_val_q3", init_value=0)
        self.tanh_sat_q3 = Reg(1, "tanh_sat_q3", init_value=0)
        self.tanh_sat_val_q3 = Reg(FP16_WIDTH, "tanh_sat_val_q3", init_value=0)
        self.trig_quad_q3 = Reg(2, "trig_quad_q3", init_value=0)
        self.trig_boundary_q3 = Reg(1, "trig_boundary_q3", init_value=0)
        self.trig_use_cos_q3 = Reg(1, "trig_use_cos_q3", init_value=0)
        self.c0_q3 = Reg(COEFF_WIDTH, "c0_q3", init_value=0)
        self.c2_q3 = Reg(COEFF_WIDTH, "c2_q3", init_value=0)
        self.delta2_q12_q3 = Reg(DELTA2_WIDTH, "delta2_q12_q3", init_value=0)
        self.term1_q3 = Reg(TERM_WIDTH, "term1_q3", init_value=0)

        self.op_q4 = Reg(OP_WIDTH, "op_q4", init_value=0)
        self.sign_q4 = Reg(1, "sign_q4", init_value=0)
        self.relu_q4 = Reg(FP16_WIDTH, "relu_q4", init_value=0)
        self.is_nan_q4 = Reg(1, "is_nan_q4", init_value=0)
        self.is_inf_q4 = Reg(1, "is_inf_q4", init_value=0)
        self.sig_sat_q4 = Reg(1, "sig_sat_q4", init_value=0)
        self.sig_sat_val_q4 = Reg(FP16_WIDTH, "sig_sat_val_q4", init_value=0)
        self.tanh_sat_q4 = Reg(1, "tanh_sat_q4", init_value=0)
        self.tanh_sat_val_q4 = Reg(FP16_WIDTH, "tanh_sat_val_q4", init_value=0)
        self.trig_quad_q4 = Reg(2, "trig_quad_q4", init_value=0)
        self.trig_boundary_q4 = Reg(1, "trig_boundary_q4", init_value=0)
        self.trig_use_cos_q4 = Reg(1, "trig_use_cos_q4", init_value=0)
        self.poly_q16_q4 = Reg(POLY_WIDTH, "poly_q16_q4", init_value=0)

        self.result_q5 = Reg(FP16_WIDTH, "result_q5", init_value=0)

        self.sig_lut = self.add_memory(
            Memory(COEFF_PACK_WIDTH, SIGMOID_TABLE.segments, "sig_lut", init_data=list(pack_coeff_rows(SIGMOID_TABLE)))
        )
        self.tanh_lut = self.add_memory(
            Memory(COEFF_PACK_WIDTH, TANH_TABLE.segments, "tanh_lut", init_data=list(pack_coeff_rows(TANH_TABLE)))
        )
        self.sin_lut = self.add_memory(
            Memory(COEFF_PACK_WIDTH, SIN_QUADRANT_TABLE.segments, "sin_lut", init_data=list(pack_coeff_rows(SIN_QUADRANT_TABLE)))
        )
        self.cos_lut = self.add_memory(
            Memory(COEFF_PACK_WIDTH, COS_QUADRANT_TABLE.segments, "cos_lut", init_data=list(pack_coeff_rows(COS_QUADRANT_TABLE)))
        )

        self.sign_w = Wire(1, "sign_w")
        self.exp_w = Wire(5, "exp_w")
        self.frac_w = Wire(10, "frac_w")
        self.mant_w = Wire(11, "mant_w")
        self.is_nan_w = Wire(1, "is_nan_w")
        self.is_inf_w = Wire(1, "is_inf_w")
        self.relu_w = Wire(FP16_WIDTH, "relu_w")
        self.mag_q12_w = Wire(Q12_WIDTH, "mag_q12_w")
        self.mag_q24_w = Wire(Q24_WIDTH, "mag_q24_w")
        self.sig_sat_w = Wire(1, "sig_sat_w")
        self.sig_sat_val_w = Wire(FP16_WIDTH, "sig_sat_val_w")
        self.tanh_sat_w = Wire(1, "tanh_sat_w")
        self.tanh_sat_val_w = Wire(FP16_WIDTH, "tanh_sat_val_w")

        self.seg_idx_w = Wire(INDEX_WIDTH, "seg_idx_w")
        self.delta_q12_w = Wire(Q12_WIDTH, "delta_q12_w")
        self.trig_quad_w = Wire(2, "trig_quad_w")
        self.trig_boundary_w = Wire(1, "trig_boundary_w")
        self.trig_use_cos_w = Wire(1, "trig_use_cos_w")

        self.sig_pack_w = Wire(COEFF_PACK_WIDTH, "sig_pack_w")
        self.tanh_pack_w = Wire(COEFF_PACK_WIDTH, "tanh_pack_w")
        self.sin_pack_w = Wire(COEFF_PACK_WIDTH, "sin_pack_w")
        self.cos_pack_w = Wire(COEFF_PACK_WIDTH, "cos_pack_w")
        self.c0_sel_w = Wire(COEFF_WIDTH, "c0_sel_w")
        self.c1_sel_w = Wire(COEFF_WIDTH, "c1_sel_w")
        self.c2_sel_w = Wire(COEFF_WIDTH, "c2_sel_w")

        self.trig_quad_est_w = Wire(Q24_WIDTH, "trig_quad_est_w")
        self.trig_prod_w = Wire(Q24_WIDTH, "trig_prod_w")
        self.trig_diff_w = Wire(Q24_WIDTH, "trig_diff_w")
        self.trig_over_w = Wire(1, "trig_over_w")
        self.trig_wrap_w = Wire(1, "trig_wrap_w")
        self.trig_delta_w = Wire(Q24_WIDTH, "trig_delta_w")
        self.trig_t_q12_w = Wire(Q12_WIDTH, "trig_t_q12_w")
        self.trig_quad_raw_w = Wire(Q24_WIDTH, "trig_quad_raw_w")

        self.pack_in_q16_w = Wire(POLY_WIDTH, "pack_in_q16_w")
        self.pack_sign_w = Wire(1, "pack_sign_w")
        self.pack_fp16_w = Wire(FP16_WIDTH, "pack_fp16_w")
        self.result_pre_w = Wire(FP16_WIDTH, "result_pre_w")

        with self.comb:
            self.in_accept <<= 1
            self.out_valid <<= self.v5
            self.result <<= self.result_q5

        @self.comb
        def _decode_comb():
            self.sign_w <<= self.operand[15]
            self.exp_w <<= self.operand[14:10]
            self.frac_w <<= self.operand[9:0]
            self.mant_w <<= Mux(self.operand[14:10] == 0, Cat(Const(0, 1), self.operand[9:0]), Cat(Const(1, 1), self.operand[9:0]))
            self.is_nan_w <<= (self.operand[14:10] == Const(0x1F, 5)) & (self.operand[9:0] != 0)
            self.is_inf_w <<= (self.operand[14:10] == Const(0x1F, 5)) & (self.operand[9:0] == 0)
            self.relu_w <<= self.operand
            with If(self.is_nan_w == 1):
                self.relu_w <<= Const(FP16_QNAN, FP16_WIDTH)
            with Else():
                with If(self.sign_w == 1):
                    self.relu_w <<= 0

            self.mag_q12_w <<= 0
            self.mag_q24_w <<= 0
            with Switch(self.exp_w) as sw:
                for exp_val in range(31):
                    with sw.case(exp_val):
                        if exp_val == 0:
                            self.mag_q12_w <<= self.frac_w
                            self.mag_q24_w <<= self.frac_w << (Q24_FRAC_BITS - 10)
                        else:
                            self.mag_q24_w <<= self.mant_w << (exp_val - 1)
                            if exp_val <= 12:
                                self.mag_q12_w <<= self.mant_w >> (13 - exp_val)
                            elif exp_val <= 17:
                                self.mag_q12_w <<= self.mant_w << (exp_val - 13)
                            else:
                                self.mag_q12_w <<= Const(SIGMOID_MAX_Q12, Q12_WIDTH)
                with sw.default():
                    self.mag_q12_w <<= 0
                    self.mag_q24_w <<= 0

            self.sig_sat_w <<= self.is_inf_w | (self.mag_q12_w >= Const(SIGMOID_MAX_Q12, Q12_WIDTH))
            self.sig_sat_val_w <<= Mux(self.sign_w == 1, Const(0, FP16_WIDTH), Const(FP16_ONE, FP16_WIDTH))
            self.tanh_sat_w <<= self.is_inf_w | (self.mag_q12_w >= Const(TANH_MAX_Q12, Q12_WIDTH))
            self.tanh_sat_val_w <<= Mux(self.sign_w == 1, Const(FP16_NEG_ONE, FP16_WIDTH), Const(FP16_ONE, FP16_WIDTH))

        @self.comb
        def _stage1_comb():
            self.trig_quad_est_w <<= (self.mag_q24_q0 * Const(TRIG_REDUCE_RECIP, 16)) >> TRIG_REDUCE_RECIP_SHIFT
            self.trig_prod_w <<= self.trig_quad_est_w * Const(HALF_PI_Q24, 25)
            self.trig_diff_w <<= self.mag_q24_q0 - self.trig_prod_w
            self.trig_over_w <<= self.trig_prod_w > self.mag_q24_q0
            self.trig_wrap_w <<= self.trig_diff_w >= Const(HALF_PI_Q24, 25)
            self.trig_delta_w <<= Mux(
                self.trig_over_w == 1,
                self.mag_q24_q0 + Const(HALF_PI_Q24, 25) - self.trig_prod_w,
                Mux(self.trig_wrap_w == 1, self.trig_diff_w - Const(HALF_PI_Q24, 25), self.trig_diff_w),
            )
            self.trig_quad_raw_w <<= Mux(
                self.trig_over_w == 1,
                self.trig_quad_est_w - 1,
                Mux(self.trig_wrap_w == 1, self.trig_quad_est_w + 1, self.trig_quad_est_w),
            )
            self.trig_quad_w <<= self.trig_quad_raw_w[1:0]
            self.trig_t_q12_w <<= (self.trig_delta_w * Const(TRIG_NORMALIZE_RECIP, 16)) >> TRIG_NORMALIZE_SHIFT

            self.seg_idx_w <<= 0
            self.delta_q12_w <<= 0
            self.trig_boundary_w <<= self.trig_t_q12_w >= Const(Q12_ONE, 16)
            self.trig_use_cos_w <<= 0

            with If(self.op_q0 == OP_SIGMOID):
                self.seg_idx_w <<= self.mag_q12_q0[14:10]
                self.delta_q12_w <<= Cat(Const(0, 6), self.mag_q12_q0[9:0])
            with Else():
                with If(self.op_q0 == OP_TANH):
                    self.seg_idx_w <<= self.mag_q12_q0[13:9]
                    self.delta_q12_w <<= Cat(Const(0, 7), self.mag_q12_q0[8:0])
                with Else():
                    with If((self.op_q0 == OP_SIN) | (self.op_q0 == OP_COS)):
                        self.seg_idx_w <<= Mux(self.trig_boundary_w == 1, Const(31, INDEX_WIDTH), self.trig_t_q12_w[11:7])
                        self.delta_q12_w <<= Mux(
                            self.trig_boundary_w == 1,
                            Const(0, Q12_WIDTH),
                            Cat(Const(0, 9), self.trig_t_q12_w[6:0]),
                        )
                        self.trig_use_cos_w <<= Mux(self.op_q0 == OP_SIN, self.trig_quad_w[0], ~self.trig_quad_w[0])

        @self.comb
        def _rom_select_comb():
            self.sig_pack_w <<= self.sig_lut[self.seg_idx_q1]
            self.tanh_pack_w <<= self.tanh_lut[self.seg_idx_q1]
            self.sin_pack_w <<= self.sin_lut[self.seg_idx_q1]
            self.cos_pack_w <<= self.cos_lut[self.seg_idx_q1]
            self.c0_sel_w <<= 0
            self.c1_sel_w <<= 0
            self.c2_sel_w <<= 0
            with If(self.op_q1 == OP_SIGMOID):
                self.c0_sel_w <<= self.sig_pack_w[53:36]
                self.c1_sel_w <<= self.sig_pack_w[35:18]
                self.c2_sel_w <<= self.sig_pack_w[17:0]
            with Else():
                with If(self.op_q1 == OP_TANH):
                    self.c0_sel_w <<= self.tanh_pack_w[53:36]
                    self.c1_sel_w <<= self.tanh_pack_w[35:18]
                    self.c2_sel_w <<= self.tanh_pack_w[17:0]
                with Else():
                    with If(self.trig_use_cos_q1 == 1):
                        self.c0_sel_w <<= self.cos_pack_w[53:36]
                        self.c1_sel_w <<= self.cos_pack_w[35:18]
                        self.c2_sel_w <<= self.cos_pack_w[17:0]
                    with Else():
                        self.c0_sel_w <<= self.sin_pack_w[53:36]
                        self.c1_sel_w <<= self.sin_pack_w[35:18]
                        self.c2_sel_w <<= self.sin_pack_w[17:0]

        @self.comb
        def _pack_comb():
            self.pack_fp16_w <<= 0
            with If(self.pack_in_q16_w == 0):
                self.pack_fp16_w <<= 0
            with Else():
                with If(self.pack_in_q16_w >= Const(Q16_ONE, POLY_WIDTH)):
                    self.pack_fp16_w <<= Const(FP16_ONE, FP16_WIDTH)
                with Else():
                    with If(self.pack_in_q16_w < Const(4, POLY_WIDTH)):
                        self.pack_fp16_w <<= self.pack_in_q16_w << 8
                    with Else():
                        with If(self.pack_in_q16_w[15] == 1):
                            rem = self.pack_in_q16_w - Const(1 << 15, POLY_WIDTH)
                            self.pack_fp16_w <<= Const(14 << 10, FP16_WIDTH) | (rem >> 5)[9:0]
                        with Else():
                            with If(self.pack_in_q16_w[14] == 1):
                                rem = self.pack_in_q16_w - Const(1 << 14, POLY_WIDTH)
                                self.pack_fp16_w <<= Const(13 << 10, FP16_WIDTH) | (rem >> 4)[9:0]
                            with Else():
                                with If(self.pack_in_q16_w[13] == 1):
                                    rem = self.pack_in_q16_w - Const(1 << 13, POLY_WIDTH)
                                    self.pack_fp16_w <<= Const(12 << 10, FP16_WIDTH) | (rem >> 3)[9:0]
                                with Else():
                                    with If(self.pack_in_q16_w[12] == 1):
                                        rem = self.pack_in_q16_w - Const(1 << 12, POLY_WIDTH)
                                        self.pack_fp16_w <<= Const(11 << 10, FP16_WIDTH) | (rem >> 2)[9:0]
                                    with Else():
                                        with If(self.pack_in_q16_w[11] == 1):
                                            rem = self.pack_in_q16_w - Const(1 << 11, POLY_WIDTH)
                                            self.pack_fp16_w <<= Const(10 << 10, FP16_WIDTH) | (rem >> 1)[9:0]
                                        with Else():
                                            with If(self.pack_in_q16_w[10] == 1):
                                                rem = self.pack_in_q16_w - Const(1 << 10, POLY_WIDTH)
                                                self.pack_fp16_w <<= Const(9 << 10, FP16_WIDTH) | rem[9:0]
                                            with Else():
                                                with If(self.pack_in_q16_w[9] == 1):
                                                    rem = self.pack_in_q16_w - Const(1 << 9, POLY_WIDTH)
                                                    self.pack_fp16_w <<= Const(8 << 10, FP16_WIDTH) | (rem << 1)[9:0]
                                                with Else():
                                                    with If(self.pack_in_q16_w[8] == 1):
                                                        rem = self.pack_in_q16_w - Const(1 << 8, POLY_WIDTH)
                                                        self.pack_fp16_w <<= Const(7 << 10, FP16_WIDTH) | (rem << 2)[9:0]
                                                    with Else():
                                                        with If(self.pack_in_q16_w[7] == 1):
                                                            rem = self.pack_in_q16_w - Const(1 << 7, POLY_WIDTH)
                                                            self.pack_fp16_w <<= Const(6 << 10, FP16_WIDTH) | (rem << 3)[9:0]
                                                        with Else():
                                                            with If(self.pack_in_q16_w[6] == 1):
                                                                rem = self.pack_in_q16_w - Const(1 << 6, POLY_WIDTH)
                                                                self.pack_fp16_w <<= Const(5 << 10, FP16_WIDTH) | (rem << 4)[9:0]
                                                            with Else():
                                                                with If(self.pack_in_q16_w[5] == 1):
                                                                    rem = self.pack_in_q16_w - Const(1 << 5, POLY_WIDTH)
                                                                    self.pack_fp16_w <<= Const(4 << 10, FP16_WIDTH) | (rem << 5)[9:0]
                                                                with Else():
                                                                    with If(self.pack_in_q16_w[4] == 1):
                                                                        rem = self.pack_in_q16_w - Const(1 << 4, POLY_WIDTH)
                                                                        self.pack_fp16_w <<= Const(3 << 10, FP16_WIDTH) | (rem << 6)[9:0]
                                                                    with Else():
                                                                        with If(self.pack_in_q16_w[3] == 1):
                                                                            rem = self.pack_in_q16_w - Const(1 << 3, POLY_WIDTH)
                                                                            self.pack_fp16_w <<= Const(2 << 10, FP16_WIDTH) | (rem << 7)[9:0]
                                                                        with Else():
                                                                            rem = self.pack_in_q16_w - Const(1 << 2, POLY_WIDTH)
                                                                            self.pack_fp16_w <<= Const(1 << 10, FP16_WIDTH) | (rem << 8)[9:0]

        @self.comb
        def _finalize_comb():
            trig_mag = Mux(
                self.trig_boundary_q4 == 1,
                Mux(self.trig_use_cos_q4 == 1, Const(0, POLY_WIDTH), Const(Q16_ONE, POLY_WIDTH)),
                self.poly_q16_q4,
            )
            trig_sign = Mux(
                self.op_q4 == OP_SIN,
                self.sign_q4 ^ self.trig_quad_q4[1],
                self.trig_quad_q4[1] ^ self.trig_quad_q4[0],
            )
            self.pack_in_q16_w <<= self.poly_q16_q4
            self.pack_sign_w <<= 0
            self.result_pre_w <<= Const(FP16_QNAN, FP16_WIDTH)

            with If(self.op_q4 == OP_SIGMOID):
                self.pack_in_q16_w <<= Mux(self.sign_q4 == 1, Const(Q16_ONE, POLY_WIDTH) - self.poly_q16_q4, self.poly_q16_q4)
                self.pack_sign_w <<= 0
            with Else():
                with If(self.op_q4 == OP_TANH):
                    self.pack_in_q16_w <<= self.poly_q16_q4
                    self.pack_sign_w <<= self.sign_q4
                with Else():
                    with If((self.op_q4 == OP_SIN) | (self.op_q4 == OP_COS)):
                        self.pack_in_q16_w <<= trig_mag
                        self.pack_sign_w <<= trig_sign

            signed_pack = Mux(
                (self.pack_sign_w == 1) & (self.pack_fp16_w != 0),
                self.pack_fp16_w | Const(0x8000, FP16_WIDTH),
                self.pack_fp16_w,
            )
            self.result_pre_w <<= self.relu_q4
            with If(self.is_nan_q4 == 1):
                self.result_pre_w <<= Const(FP16_QNAN, FP16_WIDTH)
            with Else():
                with If(self.op_q4 == OP_RELU):
                    self.result_pre_w <<= self.relu_q4
                with Else():
                    with If(self.op_q4 == OP_SIGMOID):
                        self.result_pre_w <<= Mux(self.sig_sat_q4 == 1, self.sig_sat_val_q4, self.pack_fp16_w)
                    with Else():
                        with If(self.op_q4 == OP_TANH):
                            self.result_pre_w <<= Mux(self.tanh_sat_q4 == 1, self.tanh_sat_val_q4, signed_pack)
                        with Else():
                            self.result_pre_w <<= Mux(self.is_inf_q4 == 1, Const(FP16_QNAN, FP16_WIDTH), signed_pack)

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.v0 <<= 0
                self.v1 <<= 0
                self.v2 <<= 0
                self.v3 <<= 0
                self.v4 <<= 0
                self.v5 <<= 0
                self.result_q5 <<= 0
            with Else():
                self.v0 <<= self.in_valid
                self.v1 <<= self.v0
                self.v2 <<= self.v1
                self.v3 <<= self.v2
                self.v4 <<= self.v3
                self.v5 <<= self.v4

                with If(self.in_valid == 1):
                    self.op_q0 <<= self.op
                    self.sign_q0 <<= self.sign_w
                    self.relu_q0 <<= self.relu_w
                    self.is_nan_q0 <<= self.is_nan_w
                    self.is_inf_q0 <<= self.is_inf_w
                    self.sig_sat_q0 <<= self.sig_sat_w
                    self.sig_sat_val_q0 <<= self.sig_sat_val_w
                    self.tanh_sat_q0 <<= self.tanh_sat_w
                    self.tanh_sat_val_q0 <<= self.tanh_sat_val_w
                    self.mag_q12_q0 <<= self.mag_q12_w
                    self.mag_q24_q0 <<= self.mag_q24_w

                with If(self.v0 == 1):
                    self.op_q1 <<= self.op_q0
                    self.sign_q1 <<= self.sign_q0
                    self.relu_q1 <<= self.relu_q0
                    self.is_nan_q1 <<= self.is_nan_q0
                    self.is_inf_q1 <<= self.is_inf_q0
                    self.sig_sat_q1 <<= self.sig_sat_q0
                    self.sig_sat_val_q1 <<= self.sig_sat_val_q0
                    self.tanh_sat_q1 <<= self.tanh_sat_q0
                    self.tanh_sat_val_q1 <<= self.tanh_sat_val_q0
                    self.seg_idx_q1 <<= self.seg_idx_w
                    self.delta_q12_q1 <<= self.delta_q12_w
                    self.trig_quad_q1 <<= self.trig_quad_w
                    self.trig_boundary_q1 <<= self.trig_boundary_w
                    self.trig_use_cos_q1 <<= self.trig_use_cos_w

                with If(self.v1 == 1):
                    self.op_q2 <<= self.op_q1
                    self.sign_q2 <<= self.sign_q1
                    self.relu_q2 <<= self.relu_q1
                    self.is_nan_q2 <<= self.is_nan_q1
                    self.is_inf_q2 <<= self.is_inf_q1
                    self.sig_sat_q2 <<= self.sig_sat_q1
                    self.sig_sat_val_q2 <<= self.sig_sat_val_q1
                    self.tanh_sat_q2 <<= self.tanh_sat_q1
                    self.tanh_sat_val_q2 <<= self.tanh_sat_val_q1
                    self.delta_q12_q2 <<= self.delta_q12_q1
                    self.trig_quad_q2 <<= self.trig_quad_q1
                    self.trig_boundary_q2 <<= self.trig_boundary_q1
                    self.trig_use_cos_q2 <<= self.trig_use_cos_q1
                    self.c0_q2 <<= self.c0_sel_w
                    self.c1_q2 <<= self.c1_sel_w
                    self.c2_q2 <<= self.c2_sel_w

                with If(self.v2 == 1):
                    self.op_q3 <<= self.op_q2
                    self.sign_q3 <<= self.sign_q2
                    self.relu_q3 <<= self.relu_q2
                    self.is_nan_q3 <<= self.is_nan_q2
                    self.is_inf_q3 <<= self.is_inf_q2
                    self.sig_sat_q3 <<= self.sig_sat_q2
                    self.sig_sat_val_q3 <<= self.sig_sat_val_q2
                    self.tanh_sat_q3 <<= self.tanh_sat_q2
                    self.tanh_sat_val_q3 <<= self.tanh_sat_val_q2
                    self.trig_quad_q3 <<= self.trig_quad_q2
                    self.trig_boundary_q3 <<= self.trig_boundary_q2
                    self.trig_use_cos_q3 <<= self.trig_use_cos_q2
                    self.c0_q3 <<= self.c0_q2
                    self.c2_q3 <<= self.c2_q2
                    self.delta2_q12_q3 <<= (self.delta_q12_q2 * self.delta_q12_q2) >> Q12_FRAC_BITS
                    self.term1_q3 <<= SRA(self.c1_q2.as_sint() * self.delta_q12_q2.as_sint(), Q12_FRAC_BITS)

                with If(self.v3 == 1):
                    term2 = SRA(self.c2_q3.as_sint() * self.delta2_q12_q3.as_sint(), Q12_FRAC_BITS)
                    poly_sum = self.c0_q3.as_sint() + self.term1_q3.as_sint() + term2.as_sint()

                    self.op_q4 <<= self.op_q3
                    self.sign_q4 <<= self.sign_q3
                    self.relu_q4 <<= self.relu_q3
                    self.is_nan_q4 <<= self.is_nan_q3
                    self.is_inf_q4 <<= self.is_inf_q3
                    self.sig_sat_q4 <<= self.sig_sat_q3
                    self.sig_sat_val_q4 <<= self.sig_sat_val_q3
                    self.tanh_sat_q4 <<= self.tanh_sat_q3
                    self.tanh_sat_val_q4 <<= self.tanh_sat_val_q3
                    self.trig_quad_q4 <<= self.trig_quad_q3
                    self.trig_boundary_q4 <<= self.trig_boundary_q3
                    self.trig_use_cos_q4 <<= self.trig_use_cos_q3

                    with If(poly_sum < 0):
                        self.poly_q16_q4 <<= 0
                    with Else():
                        with If(poly_sum > Const(Q16_ONE, TERM_WIDTH).as_sint()):
                            self.poly_q16_q4 <<= Const(Q16_ONE, POLY_WIDTH)
                        with Else():
                            self.poly_q16_q4 <<= poly_sum[POLY_WIDTH - 1:0]

                with If(self.v4 == 1):
                    self.result_q5 <<= self.result_pre_w


Fp16Sfu32 = Fp16Sfu


__all__ = ["Fp16Sfu", "Fp16Sfu32"]
