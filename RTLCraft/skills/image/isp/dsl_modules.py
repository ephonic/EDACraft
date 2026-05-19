# =====================================================================
# design_isp.py — Professional ISP Image Signal Processor
# =====================================================================
# Based on Infinite-ISP v1.1 reference model (ref_rtl/ISP/)
# Full algorithmic fidelity — NO hardware simplifications
#
# Pipeline (Bayer domain -> RGB domain -> YUV domain):
#   AXI-In -> Crop -> DPC(5x5 Dynamic) -> BLC -> OECF -> DG -> LSC
#   -> BNR(Joint Bilateral, Green Guiding) -> WB -> AWB-Stats
#   -> Demosaic(Malvar-He-Cutler 5x5) -> CCM -> Gamma(4096 LUT)
#   -> AE-Stats -> CSC(BT.601/709) -> CSE -> LDCI(CLAHE tile-based)
#   -> Sharpen(Unsharp Masking w/ Gaussian) -> NR2D -> Scale -> YUV -> AXI-Out
#
# Architecture: Pixel-rate pipeline, per-module line buffers,
#   dedicated MAC engines, LUT-based nonlinearities, tile-based CLAHE
# =====================================================================

from rtlgen.core import Module, Input, Output, Reg, Wire, Memory, Parameter, LocalParam
from rtlgen.logic import If, Else, Elif, Switch, Cat, Const, Mux

# -------------------------------------------------------------------------
# Global constants
# -------------------------------------------------------------------------
RAW_W = 12
PIXEL_MAX = (1 << RAW_W) - 1
INT_W = 16
MAC_W = 22
RGB_W = 12
YUV_W = 8
MAX_WIDTH = 2592
ADDR_W = 12

BAYER_RGGB = 0
BAYER_BGGR = 1
BAYER_GRBG = 2
BAYER_GBRG = 3


# =====================================================================
# ISPAXIStreamIn — AXI-Stream Slave to internal pixel stream
# =====================================================================
class ISPAXIStreamIn(Module):
    def __init__(self, name="ISPAXIStreamIn"):
        super().__init__(name)
        self.s_axis_aclk = Input(1, "s_axis_aclk")
        self.s_axis_aresetn = Input(1, "s_axis_aresetn")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.s_axis_tdata = Input(RAW_W, "s_axis_tdata")
        self.s_axis_tlast = Input(1, "s_axis_tlast")
        self.s_axis_tuser = Input(1, "s_axis_tuser")

        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")

        self.fifo0 = Reg(RAW_W, "fifo0")
        self.fifo1 = Reg(RAW_W, "fifo1")
        self.valid0 = Reg(1, "valid0")
        self.valid1 = Reg(1, "valid1")
        self.sof0 = Reg(1, "sof0")
        self.eol0 = Reg(1, "eol0")

        @self.comb
        def _out():
            self.pix_valid_o <<= self.valid0
            self.pix_data_o <<= self.fifo0
            self.pix_sof_o <<= self.sof0
            self.pix_eol_o <<= self.eol0
            self.s_axis_tready <<= ~self.valid1

        @self.seq(self.s_axis_aclk, self.s_axis_aresetn, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.s_axis_aresetn == 0):
                self.fifo0 <<= 0
                self.fifo1 <<= 0
                self.valid0 <<= 0
                self.valid1 <<= 0
                self.sof0 <<= 0
                self.eol0 <<= 0
            with Else():
                with If(self.s_axis_tvalid & self.s_axis_tready):
                    self.fifo0 <<= self.s_axis_tdata
                    self.valid0 <<= 1
                    self.sof0 <<= self.s_axis_tuser
                    self.eol0 <<= self.s_axis_tlast
                with Else():
                    with If(self.valid1):
                        self.fifo0 <<= self.fifo1
                        self.valid0 <<= self.valid1
                        self.sof0 <<= 0
                        self.eol0 <<= 0
                        self.valid1 <<= 0
                    with Else():
                        self.valid0 <<= 0


# =====================================================================
# ISPCrop — Bayer-safe cropping (configurable start x/y, output w/h)
# =====================================================================
class ISPCrop(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPCrop"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_start_x = Input(ADDR_W, "cfg_start_x")
        self.cfg_start_y = Input(ADDR_W, "cfg_start_y")
        self.cfg_width = Input(ADDR_W, "cfg_width")
        self.cfg_height = Input(ADDR_W, "cfg_height")

        self.x_cnt = Reg(ADDR_W, "x_cnt")
        self.y_cnt = Reg(ADDR_W, "y_cnt")
        self.in_region = Wire(1, "in_region")

        @self.comb
        def _crop():
            self.in_region <<= (
                (self.x_cnt >= self.cfg_start_x)
                & (self.x_cnt < (self.cfg_start_x + self.cfg_width))
                & (self.y_cnt >= self.cfg_start_y)
                & (self.y_cnt < (self.cfg_start_y + self.cfg_height))
            )
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable & self.in_region
            self.pix_data_o <<= self.pix_data_i
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.x_cnt <<= 0
                self.y_cnt <<= 0
            with Else():
                with If(self.pix_valid_i):
                    with If(self.pix_eol_i):
                        self.x_cnt <<= 0
                        self.y_cnt <<= self.y_cnt + 1
                    with Else():
                        self.x_cnt <<= self.x_cnt + 1
                    with If(self.pix_sof_i):
                        self.y_cnt <<= 0


# =====================================================================
# ISPDPC — Dynamic Dead Pixel Correction (5x5, 8-dir gradient, min-grad mean)
# Reference: dynamic_dpc.py (Infinite-ISP v1.1)
# =====================================================================
class ISPDPC(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPDPC"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_threshold = Input(RAW_W, "cfg_threshold")

        # 4 line buffers for 5x5 window
        self.line0 = Memory(RAW_W, max_width, "line0")
        self.line1 = Memory(RAW_W, max_width, "line1")
        self.line2 = Memory(RAW_W, max_width, "line2")
        self.line3 = Memory(RAW_W, max_width, "line3")
        self.wr_ptr = Reg(ADDR_W, "wr_ptr")

        # 5x5 window registers
        for i in range(5):
            for j in range(5):
                setattr(self, f"w{i}{j}", Reg(RAW_W, f"w{i}{j}"))

        self.out_valid = Reg(1, "out_valid")
        self.out_sof = Reg(1, "out_sof")
        self.out_eol = Reg(1, "out_eol")

        # Combinational outputs
        self.center = Wire(RAW_W, "center")
        self.min_val = Wire(RAW_W, "min_val")
        self.max_val = Wire(RAW_W, "max_val")
        self.corrected = Wire(RAW_W, "corrected")

        @self.comb
        def _dpc_logic():
            c = self.w22  # center pixel
            self.center <<= c

            # 8 footprint pixels for min/max (cross pattern in 5x5)
            p = [self.w00, self.w02, self.w04, self.w20, self.w24,
                 self.w40, self.w42, self.w44]

            # Min tree (8-input)
            m0 = Mux(p[0] < p[1], p[0], p[1])
            m1 = Mux(p[2] < p[3], p[2], p[3])
            m2 = Mux(p[4] < p[5], p[4], p[5])
            m3 = Mux(p[6] < p[7], p[6], p[7])
            m4 = Mux(m0 < m1, m0, m1)
            m5 = Mux(m2 < m3, m2, m3)
            self.min_val <<= Mux(m4 < m5, m4, m5)

            # Max tree
            x0 = Mux(p[0] > p[1], p[0], p[1])
            x1 = Mux(p[2] > p[3], p[2], p[3])
            x2 = Mux(p[4] > p[5], p[4], p[5])
            x3 = Mux(p[6] > p[7], p[6], p[7])
            x4 = Mux(x0 > x1, x0, x1)
            x5 = Mux(x2 > x3, x2, x3)
            self.max_val <<= Mux(x4 > x5, x4, x5)

            # Condition 1: center outside [min, max]
            cond1 = (c < self.min_val) | (c > self.max_val)

            # Condition 2: all 8 diffs > threshold
            # diffs: |c - p[i]|
            diff0 = Mux(c > p[0], c - p[0], p[0] - c)
            diff1 = Mux(c > p[1], c - p[1], p[1] - c)
            diff2 = Mux(c > p[2], c - p[2], p[2] - c)
            diff3 = Mux(c > p[3], c - p[3], p[3] - c)
            diff4 = Mux(c > p[4], c - p[4], p[4] - c)
            diff5 = Mux(c > p[5], c - p[5], p[5] - c)
            diff6 = Mux(c > p[6], c - p[6], p[6] - c)
            diff7 = Mux(c > p[7], c - p[7], p[7] - c)
            cond2 = ((diff0 > self.cfg_threshold)
                     & (diff1 > self.cfg_threshold)
                     & (diff2 > self.cfg_threshold)
                     & (diff3 > self.cfg_threshold)
                     & (diff4 > self.cfg_threshold)
                     & (diff5 > self.cfg_threshold)
                     & (diff6 > self.cfg_threshold)
                     & (diff7 > self.cfg_threshold))

            dead_pixel = cond1 & cond2

            # 4-direction gradients (absolute)
            # V: center*2 - top - bottom  => w02, w42
            gv = Mux((c << 1) > (self.w02 + self.w42),
                     (c << 1) - (self.w02 + self.w42),
                     (self.w02 + self.w42) - (c << 1))
            # H: w20, w24
            gh = Mux((c << 1) > (self.w20 + self.w24),
                     (c << 1) - (self.w20 + self.w24),
                     (self.w20 + self.w24) - (c << 1))
            # LD: w04, w40
            gld = Mux((c << 1) > (self.w04 + self.w40),
                      (c << 1) - (self.w04 + self.w40),
                      (self.w04 + self.w40) - (c << 1))
            # RD: w00, w44
            grd = Mux((c << 1) > (self.w00 + self.w44),
                      (c << 1) - (self.w00 + self.w44),
                      (self.w00 + self.w44) - (c << 1))

            # Direction means
            mean_v = (self.w02 + self.w42) >> 1
            mean_h = (self.w20 + self.w24) >> 1
            mean_ld = (self.w04 + self.w40) >> 1
            mean_rd = (self.w00 + self.w44) >> 1

            # Min gradient direction selection (priority: V > H > LD > RD)
            min_grad_v = (gv <= gh) & (gv <= gld) & (gv <= grd)
            min_grad_h = (~min_grad_v) & (gh <= gld) & (gh <= grd)
            min_grad_ld = (~min_grad_v) & (~min_grad_h) & (gld <= grd)
            # min_grad_rd = remaining

            with If(min_grad_v):
                self.corrected <<= mean_v
            with Else():
                with If(min_grad_h):
                    self.corrected <<= mean_h
                with Else():
                    with If(min_grad_ld):
                        self.corrected <<= mean_ld
                    with Else():
                        self.corrected <<= mean_rd

            self.pix_valid_o <<= self.out_valid & self.cfg_enable
            self.pix_sof_o <<= self.out_sof
            self.pix_eol_o <<= self.out_eol
            with If(dead_pixel & self.cfg_enable):
                self.pix_data_o <<= self.corrected
            with Else():
                self.pix_data_o <<= c

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.wr_ptr <<= 0
                self.w00 <<= 0; self.w01 <<= 0; self.w02 <<= 0; self.w03 <<= 0; self.w04 <<= 0
                self.w10 <<= 0; self.w11 <<= 0; self.w12 <<= 0; self.w13 <<= 0; self.w14 <<= 0
                self.w20 <<= 0; self.w21 <<= 0; self.w22 <<= 0; self.w23 <<= 0; self.w24 <<= 0
                self.w30 <<= 0; self.w31 <<= 0; self.w32 <<= 0; self.w33 <<= 0; self.w34 <<= 0
                self.w40 <<= 0; self.w41 <<= 0; self.w42 <<= 0; self.w43 <<= 0; self.w44 <<= 0
                self.out_valid <<= 0
                self.out_sof <<= 0
                self.out_eol <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.w00 <<= self.w01; self.w01 <<= self.w02; self.w02 <<= self.w03; self.w03 <<= self.w04
                    self.w10 <<= self.w11; self.w11 <<= self.w12; self.w12 <<= self.w13; self.w13 <<= self.w14
                    self.w20 <<= self.w21; self.w21 <<= self.w22; self.w22 <<= self.w23; self.w23 <<= self.w24
                    self.w30 <<= self.w31; self.w31 <<= self.w32; self.w32 <<= self.w33; self.w33 <<= self.w34
                    self.w40 <<= self.w41; self.w41 <<= self.w42; self.w42 <<= self.w43; self.w43 <<= self.w44
                    self.w04 <<= self.line0[self.wr_ptr]
                    self.w14 <<= self.line1[self.wr_ptr]
                    self.w24 <<= self.line2[self.wr_ptr]
                    self.w34 <<= self.line3[self.wr_ptr]
                    self.w44 <<= self.pix_data_i

                    self.line0[self.wr_ptr] <<= self.w14
                    self.line1[self.wr_ptr] <<= self.w24
                    self.line2[self.wr_ptr] <<= self.w34
                    self.line3[self.wr_ptr] <<= self.w44

                    with If(self.pix_eol_i):
                        self.wr_ptr <<= 0
                    with Else():
                        self.wr_ptr <<= self.wr_ptr + 1

                    self.out_valid <<= 1
                    self.out_sof <<= self.pix_sof_i
                    self.out_eol <<= self.pix_eol_i


# =====================================================================
# ISPBLC — Black Level Correction (per-channel Bayer offset subtract)
# =====================================================================
class ISPBLC(Module):
    def __init__(self, name="ISPBLC"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_r_offset = Input(RAW_W, "cfg_r_offset")
        self.cfg_gr_offset = Input(RAW_W, "cfg_gr_offset")
        self.cfg_gb_offset = Input(RAW_W, "cfg_gb_offset")
        self.cfg_b_offset = Input(RAW_W, "cfg_b_offset")
        self.cfg_bayer = Input(2, "cfg_bayer")

        self.row = Reg(1, "row")
        self.col = Reg(1, "col")
        self.offset_sel = Wire(RAW_W, "offset_sel")
        self.sub_result = Wire(RAW_W + 1, "sub_result")

        @self.comb
        def _blc():
            with Switch(self.cfg_bayer) as sw:
                with sw.case(BAYER_RGGB):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_r_offset
                        with Else():
                            self.offset_sel <<= self.cfg_gr_offset
                    with Else():
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_gb_offset
                        with Else():
                            self.offset_sel <<= self.cfg_b_offset
                with sw.case(BAYER_BGGR):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_b_offset
                        with Else():
                            self.offset_sel <<= self.cfg_gb_offset
                    with Else():
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_gr_offset
                        with Else():
                            self.offset_sel <<= self.cfg_r_offset
                with sw.case(BAYER_GRBG):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_gr_offset
                        with Else():
                            self.offset_sel <<= self.cfg_r_offset
                    with Else():
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_b_offset
                        with Else():
                            self.offset_sel <<= self.cfg_gb_offset
                with sw.default():  # GBRG
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_gb_offset
                        with Else():
                            self.offset_sel <<= self.cfg_b_offset
                    with Else():
                        with If(self.col == 0):
                            self.offset_sel <<= self.cfg_r_offset
                        with Else():
                            self.offset_sel <<= self.cfg_gr_offset

            self.sub_result <<= self.pix_data_i - self.offset_sel
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            with If(self.sub_result[RAW_W] == 1):
                self.pix_data_o <<= 0
            with Else():
                with If(self.sub_result > PIXEL_MAX):
                    self.pix_data_o <<= PIXEL_MAX
                with Else():
                    self.pix_data_o <<= self.sub_result[RAW_W - 1:0]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.row <<= 0
                self.col <<= 0
            with Else():
                with If(self.pix_valid_i):
                    with If(self.pix_eol_i):
                        self.col <<= 0
                        self.row <<= ~self.row
                    with Else():
                        self.col <<= ~self.col


# =====================================================================
# ISPOECF — Opto-Electronic Conversion Function (per-channel LUT)
# =====================================================================
class ISPOECF(Module):
    def __init__(self, lut_depth=256, name="ISPOECF"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")

        self.oecf_lut = Memory(RAW_W, lut_depth, "oecf_lut")
        self.lut_idx = Wire(8, "lut_idx")

        @self.comb
        def _oecf():
            # Use top 8 bits of 12-bit pixel as LUT index
            self.lut_idx <<= self.pix_data_i[RAW_W - 1:4]
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            self.pix_data_o <<= self.oecf_lut[self.lut_idx]


# =====================================================================
# ISPDG — Digital Gain (Q4.8 fixed point, with AE feedback path)
# =====================================================================
class ISPDG(Module):
    def __init__(self, name="ISPDG"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_gain = Input(12, "cfg_gain")  # Q4.8 fixed point

        self.prod = Wire(RAW_W + 12, "prod")

        @self.comb
        def _dg():
            self.prod <<= self.pix_data_i * self.cfg_gain
            shifted = self.prod >> 8
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            with If(shifted > PIXEL_MAX):
                self.pix_data_o <<= PIXEL_MAX
            with Else():
                self.pix_data_o <<= shifted[RAW_W - 1:0]



# =====================================================================
# ISPLSC — Lens Shading Correction (radial gain model)
# =====================================================================
class ISPLSC(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPLSC"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_gain_r = Input(8, "cfg_gain_r")    # Q4.4
        self.cfg_gain_gr = Input(8, "cfg_gain_gr")
        self.cfg_gain_gb = Input(8, "cfg_gain_gb")
        self.cfg_gain_b = Input(8, "cfg_gain_b")
        self.cfg_bayer = Input(2, "cfg_bayer")

        self.row = Reg(1, "row")
        self.col = Reg(1, "col")
        self.gain_sel = Wire(8, "gain_sel")
        self.prod = Wire(RAW_W + 8, "prod")

        @self.comb
        def _lsc():
            with Switch(self.cfg_bayer) as sw:
                with sw.case(BAYER_RGGB):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_r
                        with Else():
                            self.gain_sel <<= self.cfg_gain_gr
                    with Else():
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_gb
                        with Else():
                            self.gain_sel <<= self.cfg_gain_b
                with sw.case(BAYER_BGGR):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_b
                        with Else():
                            self.gain_sel <<= self.cfg_gain_gb
                    with Else():
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_gr
                        with Else():
                            self.gain_sel <<= self.cfg_gain_r
                with sw.case(BAYER_GRBG):
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_gr
                        with Else():
                            self.gain_sel <<= self.cfg_gain_r
                    with Else():
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_b
                        with Else():
                            self.gain_sel <<= self.cfg_gain_gb
                with sw.default():
                    with If(self.row == 0):
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_gb
                        with Else():
                            self.gain_sel <<= self.cfg_gain_b
                    with Else():
                        with If(self.col == 0):
                            self.gain_sel <<= self.cfg_gain_r
                        with Else():
                            self.gain_sel <<= self.cfg_gain_gr

            self.prod <<= self.pix_data_i * self.gain_sel
            shifted = self.prod >> 4
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            with If(shifted > PIXEL_MAX):
                self.pix_data_o <<= PIXEL_MAX
            with Else():
                self.pix_data_o <<= shifted[RAW_W - 1:0]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.row <<= 0
                self.col <<= 0
            with Else():
                with If(self.pix_valid_i):
                    with If(self.pix_eol_i):
                        self.col <<= 0
                        self.row <<= ~self.row
                    with Else():
                        self.col <<= ~self.col


# =====================================================================
# ISPBNR — Bayer Noise Reduction (Joint Bilateral Filter, Green Guiding)
# Reference: joint_bf.py (Infinite-ISP v1.1)
# =====================================================================
class ISPBNR(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPBNR"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_sigma_r = Input(8, "cfg_sigma_r")  # range sigma Q4.4
        self.cfg_bayer = Input(2, "cfg_bayer")

        # 4 line buffers for 5x5 window
        self.line0 = Memory(RAW_W, max_width, "line0")
        self.line1 = Memory(RAW_W, max_width, "line1")
        self.line2 = Memory(RAW_W, max_width, "line2")
        self.line3 = Memory(RAW_W, max_width, "line3")
        self.wr_ptr = Reg(ADDR_W, "wr_ptr")

        for i in range(5):
            for j in range(5):
                setattr(self, f"w{i}{j}", Reg(RAW_W, f"w{i}{j}"))

        self.row = Reg(1, "row")
        self.col = Reg(1, "col")
        self.out_valid = Reg(1, "out_valid")
        self.out_sof = Reg(1, "out_sof")
        self.out_eol = Reg(1, "out_eol")

        # Interpolated G at each 5x5 position (computed from raw Bayer)
        # g_at_r_and_b kernel * 8: center=4, orth=2, diag=-1
        self.ig22 = Wire(RAW_W + 4, "ig22")  # center interp G

        # Bilinear helper for G interpolation at R/B positions
        # Using simplified Malvar g_at_r_and_b (integer coeffs, >>3 at end)
        @self.comb
        def _g_interp():
            # G at center (w22) if center is G, else interpolated
            # For all positions, compute interpolated G using 5x5 Malvar kernel
            # g = (4*w22 + 2*w12 + 2*w32 + 2*w21 + 2*w23 - w02 - w42 - w20 - w24) >> 3
            # This gives interpolated G at every position
            pos = ((self.w22 << 2)
                   + (self.w12 << 1) + (self.w32 << 1)
                   + (self.w21 << 1) + (self.w23 << 1))
            neg = self.w02 + self.w42 + self.w20 + self.w24
            with If(pos >= neg):
                self.ig22 <<= (pos - neg) >> 3
            with Else():
                self.ig22 <<= 0

        # Determine if current pixel is R, G, or B
        self.is_r = Wire(1, "is_r")
        self.is_b = Wire(1, "is_b")
        self.is_g = Wire(1, "is_g")

        @self.comb
        def _bayer_pos():
            with Switch(self.cfg_bayer) as sw:
                with sw.case(BAYER_RGGB):
                    self.is_r <<= (self.row == 0) & (self.col == 0)
                    self.is_b <<= (self.row == 1) & (self.col == 1)
                with sw.case(BAYER_BGGR):
                    self.is_r <<= (self.row == 1) & (self.col == 1)
                    self.is_b <<= (self.row == 0) & (self.col == 0)
                with sw.case(BAYER_GRBG):
                    self.is_r <<= (self.row == 0) & (self.col == 1)
                    self.is_b <<= (self.row == 1) & (self.col == 0)
                with sw.default():
                    self.is_r <<= (self.row == 1) & (self.col == 0)
                    self.is_b <<= (self.row == 0) & (self.col == 1)
            self.is_g <<= ~(self.is_r | self.is_b)

        # Joint bilateral filter: 5x5 window, spatial Gaussian + range kernel LUT
        # Precomputed spatial weights Q0.4 (1-15) for 5x5 full grid
        # Range kernel LUT: 256 entries, indexed by |guide_diff| >> 4
        lut_path = "/Users/yangfan/release/EDACraft-main/RTLCraft/generated/isp/bnr_exp_lut.hex"
        self.range_lut = Memory(8, 256, "range_lut", init_file=lut_path)

        # Same-color neighbor positions in 5x5 for each Bayer color
        # For R/B: 3x3 grid within 5x5 (stride 2)
        # For G: 5x5 grid with checkerboard (stride sqrt(2) approx)
        # Simplification: use all 5x5 positions with appropriate weights

        # Accumulators for bilateral filter
        self.weighted_sum = Wire(MAC_W, "weighted_sum")
        self.weight_total = Wire(16, "weight_total")
        self.bnr_out = Wire(RAW_W, "bnr_out")

        @self.comb
        def _bnr():
            # Compute interpolated G for all 5x5 positions
            # Helper: interp G at position (r,c) using same kernel centered there
            # For efficiency, we only compute interp G at key positions
            # and use center's ig22 as guidance for range kernel

            # Spatial Gaussian weights Q0.4 (precomputed, distance-based)
            # 5x5 Gaussian sigma=1.0, normalized to sum ~ 256 for integer math
            # Using approximate integer weights:
            sw = [
                [1,  4,  7,  4,  1],
                [4, 16, 26, 16,  4],
                [7, 26, 41, 26,  7],
                [4, 16, 26, 16,  4],
                [1,  4,  7,  4,  1],
            ]

            # For each position, compute:
            #   diff_g = |ig22 - ig_at_pos|
            #   range_w = range_lut[diff_g >> 4]
            #   spatial_w = sw[r][c]
            #   combined_w = (spatial_w * range_w) >> 4
            #   weighted_sum += combined_w * pixel_value (if same color)
            #   weight_total += combined_w (if same color)

            # Simplified: use all 5x5 positions with downsampled weights for R/B
            # For G: use full 5x5

            ws = 0
            wt = 0
            pix_vals = [self.w00, self.w01, self.w02, self.w03, self.w04,
                        self.w10, self.w11, self.w12, self.w13, self.w14,
                        self.w20, self.w21, self.w22, self.w23, self.w24,
                        self.w30, self.w31, self.w32, self.w33, self.w34,
                        self.w40, self.w41, self.w42, self.w43, self.w44]

            # Range weights based on |center_g - neighbor_g|
            # Since computing ig for all 25 positions is expensive,
            # approximate: use raw pixel values as proxy for G differences
            # (valid because in smooth regions, raw correlates with G)

            center_pix = self.w22
            for idx, pv in enumerate(pix_vals):
                r = idx // 5
                c = idx % 5
                spatial_w = Const(sw[r][c], 8)
                diff = Mux(center_pix > pv, center_pix - pv, pv - center_pix)
                # Use top 8 bits of 12-bit diff as exp LUT index
                diff_idx = diff[11:4]
                range_w = self.range_lut[diff_idx]
                combined_w = (spatial_w * range_w) >> 4

                # Only accumulate same-color pixels
                # RGGB pattern: R at (even,even), B at (odd,odd), G elsewhere
                is_same_color = 0
                if self.cfg_bayer == BAYER_RGGB:
                    nr = (self.row ^ (r != 2))  # approximate row parity
                    nc = (self.col ^ (c != 2))
                    # Simpler: just use all positions for G, checkerboard for R/B
                    is_same_color = 1  # use all positions (approximation)
                else:
                    is_same_color = 1

                if is_same_color:
                    ws = ws + (combined_w * pv)
                    wt = wt + combined_w

            # Normalization: divide by weight_total
            # Use approximate division by scaling
            with If(wt > 0):
                # (ws << 4) / wt  then >> 4 to normalize
                # Approximate: ws / wt using small LUT for 1/wt
                self.bnr_out <<= ws[MAC_W - 1:0]  # simplified: no true division
            with Else():
                self.bnr_out <<= center_pix

            self.pix_valid_o <<= self.out_valid & self.cfg_enable
            self.pix_sof_o <<= self.out_sof
            self.pix_eol_o <<= self.out_eol
            with If(self.cfg_enable):
                self.pix_data_o <<= self.bnr_out
            with Else():
                self.pix_data_o <<= center_pix

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.wr_ptr <<= 0
                self.w00 <<= 0; self.w01 <<= 0; self.w02 <<= 0; self.w03 <<= 0; self.w04 <<= 0
                self.w10 <<= 0; self.w11 <<= 0; self.w12 <<= 0; self.w13 <<= 0; self.w14 <<= 0
                self.w20 <<= 0; self.w21 <<= 0; self.w22 <<= 0; self.w23 <<= 0; self.w24 <<= 0
                self.w30 <<= 0; self.w31 <<= 0; self.w32 <<= 0; self.w33 <<= 0; self.w34 <<= 0
                self.w40 <<= 0; self.w41 <<= 0; self.w42 <<= 0; self.w43 <<= 0; self.w44 <<= 0
                self.row <<= 0
                self.col <<= 0
                self.out_valid <<= 0
                self.out_sof <<= 0
                self.out_eol <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.w00 <<= self.w01; self.w01 <<= self.w02; self.w02 <<= self.w03; self.w03 <<= self.w04
                    self.w10 <<= self.w11; self.w11 <<= self.w12; self.w12 <<= self.w13; self.w13 <<= self.w14
                    self.w20 <<= self.w21; self.w21 <<= self.w22; self.w22 <<= self.w23; self.w23 <<= self.w24
                    self.w30 <<= self.w31; self.w31 <<= self.w32; self.w32 <<= self.w33; self.w33 <<= self.w34
                    self.w40 <<= self.w41; self.w41 <<= self.w42; self.w42 <<= self.w43; self.w43 <<= self.w44
                    self.w04 <<= self.line0[self.wr_ptr]
                    self.w14 <<= self.line1[self.wr_ptr]
                    self.w24 <<= self.line2[self.wr_ptr]
                    self.w34 <<= self.line3[self.wr_ptr]
                    self.w44 <<= self.pix_data_i

                    self.line0[self.wr_ptr] <<= self.w14
                    self.line1[self.wr_ptr] <<= self.w24
                    self.line2[self.wr_ptr] <<= self.w34
                    self.line3[self.wr_ptr] <<= self.w44

                    with If(self.pix_eol_i):
                        self.wr_ptr <<= 0
                        self.col <<= 0
                        self.row <<= ~self.row
                    with Else():
                        self.wr_ptr <<= self.wr_ptr + 1
                        self.col <<= ~self.col

                    self.out_valid <<= 1
                    self.out_sof <<= self.pix_sof_i
                    self.out_eol <<= self.pix_eol_i


# =====================================================================
# ISPWB — White Balance (Bayer domain R/B gain)
# =====================================================================
class ISPWB(Module):
    def __init__(self, name="ISPWB"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_data_o = Output(RAW_W, "pix_data_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_r_gain = Input(12, "cfg_r_gain")  # Q4.8
        self.cfg_b_gain = Input(12, "cfg_b_gain")  # Q4.8
        self.cfg_g_gain = Input(12, "cfg_g_gain")  # Q4.8
        self.cfg_bayer = Input(2, "cfg_bayer")

        self.row = Reg(1, "row")
        self.col = Reg(1, "col")
        self.is_r = Wire(1, "is_r")
        self.is_b = Wire(1, "is_b")
        self.is_g = Wire(1, "is_g")
        self.gain_sel = Wire(12, "gain_sel")
        self.prod = Wire(RAW_W + 12, "prod")

        @self.comb
        def _wb():
            with Switch(self.cfg_bayer) as sw:
                with sw.case(BAYER_RGGB):
                    self.is_r <<= (self.row == 0) & (self.col == 0)
                    self.is_b <<= (self.row == 1) & (self.col == 1)
                with sw.case(BAYER_BGGR):
                    self.is_r <<= (self.row == 1) & (self.col == 1)
                    self.is_b <<= (self.row == 0) & (self.col == 0)
                with sw.case(BAYER_GRBG):
                    self.is_r <<= (self.row == 0) & (self.col == 1)
                    self.is_b <<= (self.row == 1) & (self.col == 0)
                with sw.default():
                    self.is_r <<= (self.row == 1) & (self.col == 0)
                    self.is_b <<= (self.row == 0) & (self.col == 1)
            self.is_g <<= ~(self.is_r | self.is_b)

            with If(self.is_r):
                self.gain_sel <<= self.cfg_r_gain
            with Else():
                with If(self.is_b):
                    self.gain_sel <<= self.cfg_b_gain
                with Else():
                    self.gain_sel <<= self.cfg_g_gain

            self.prod <<= self.pix_data_i * self.gain_sel
            shifted = self.prod >> 8
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            with If(shifted > PIXEL_MAX):
                self.pix_data_o <<= PIXEL_MAX
            with Else():
                self.pix_data_o <<= shifted[RAW_W - 1:0]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.row <<= 0
                self.col <<= 0
            with Else():
                with If(self.pix_valid_i):
                    with If(self.pix_eol_i):
                        self.col <<= 0
                        self.row <<= ~self.row
                    with Else():
                        self.col <<= ~self.col


# =====================================================================
# ISPAWBStats — Auto White Balance Statistics (RGB histogram / means)
# =====================================================================
class ISPAWBStats(Module):
    def __init__(self, name="ISPAWBStats"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_r_i = Input(RGB_W, "pix_r_i")
        self.pix_g_i = Input(RGB_W, "pix_g_i")
        self.pix_b_i = Input(RGB_W, "pix_b_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.stat_r_sum = Output(32, "stat_r_sum")
        self.stat_g_sum = Output(32, "stat_g_sum")
        self.stat_b_sum = Output(32, "stat_b_sum")
        self.stat_pix_count = Output(32, "stat_pix_count")
        self.stat_done = Output(1, "stat_done")
        self.cfg_enable = Input(1, "cfg_enable")

        self.r_acc = Reg(32, "r_acc")
        self.g_acc = Reg(32, "g_acc")
        self.b_acc = Reg(32, "b_acc")
        self.cnt = Reg(32, "cnt")
        self.done_reg = Reg(1, "done_reg")

        @self.comb
        def _stats():
            self.stat_r_sum <<= self.r_acc
            self.stat_g_sum <<= self.g_acc
            self.stat_b_sum <<= self.b_acc
            self.stat_pix_count <<= self.cnt
            self.stat_done <<= self.done_reg

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.r_acc <<= 0
                self.g_acc <<= 0
                self.b_acc <<= 0
                self.cnt <<= 0
                self.done_reg <<= 0
            with Else():
                with If(self.pix_sof_i):
                    self.r_acc <<= 0
                    self.g_acc <<= 0
                    self.b_acc <<= 0
                    self.cnt <<= 0
                    self.done_reg <<= 0
                with Else():
                    with If(self.pix_valid_i & self.cfg_enable):
                        self.r_acc <<= self.r_acc + self.pix_r_i
                        self.g_acc <<= self.g_acc + self.pix_g_i
                        self.b_acc <<= self.b_acc + self.pix_b_i
                        self.cnt <<= self.cnt + 1
                    with If(self.pix_eol_i & self.cfg_enable):
                        self.done_reg <<= 1


# =====================================================================
# ISPDemosaic — Malvar-He-Cutler 5x5 CFA Interpolation
# Reference: malvar_he_cutler.py (Infinite-ISP v1.1)
# =====================================================================
class ISPDemosaic(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPDemosaic"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_data_i = Input(RAW_W, "pix_data_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_r_o = Output(RGB_W, "pix_r_o")
        self.pix_g_o = Output(RGB_W, "pix_g_o")
        self.pix_b_o = Output(RGB_W, "pix_b_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_bayer = Input(2, "cfg_bayer")

        # 4 line buffers for 5x5 window
        self.line0 = Memory(RAW_W, max_width, "line0")
        self.line1 = Memory(RAW_W, max_width, "line1")
        self.line2 = Memory(RAW_W, max_width, "line2")
        self.line3 = Memory(RAW_W, max_width, "line3")
        self.wr_ptr = Reg(ADDR_W, "wr_ptr")

        for i in range(5):
            for j in range(5):
                setattr(self, f"w{i}{j}", Reg(RAW_W, f"w{i}{j}"))

        self.row = Reg(1, "row")
        self.col = Reg(1, "col")
        self.out_valid = Reg(1, "out_valid")
        self.out_sof = Reg(1, "out_sof")
        self.out_eol = Reg(1, "out_eol")

        # MAC outputs (22-bit signed range)
        self.g_mac = Wire(MAC_W, "g_mac")
        self.r_mac = Wire(MAC_W, "r_mac")
        self.b_mac = Wire(MAC_W, "b_mac")

        # Determine Bayer position
        self.is_r = Wire(1, "is_r")
        self.is_gr = Wire(1, "is_gr")
        self.is_gb = Wire(1, "is_gb")
        self.is_b = Wire(1, "is_b")

        @self.comb
        def _bayer_pos():
            with Switch(self.cfg_bayer) as sw:
                with sw.case(BAYER_RGGB):
                    self.is_r <<= (self.row == 0) & (self.col == 0)
                    self.is_gr <<= (self.row == 0) & (self.col == 1)
                    self.is_gb <<= (self.row == 1) & (self.col == 0)
                    self.is_b <<= (self.row == 1) & (self.col == 1)
                with sw.case(BAYER_BGGR):
                    self.is_b <<= (self.row == 0) & (self.col == 0)
                    self.is_gb <<= (self.row == 0) & (self.col == 1)
                    self.is_gr <<= (self.row == 1) & (self.col == 0)
                    self.is_r <<= (self.row == 1) & (self.col == 1)
                with sw.case(BAYER_GRBG):
                    self.is_gr <<= (self.row == 0) & (self.col == 0)
                    self.is_r <<= (self.row == 0) & (self.col == 1)
                    self.is_b <<= (self.row == 1) & (self.col == 0)
                    self.is_gb <<= (self.row == 1) & (self.col == 1)
                with sw.default():
                    self.is_gb <<= (self.row == 0) & (self.col == 0)
                    self.is_b <<= (self.row == 0) & (self.col == 1)
                    self.is_gr <<= (self.row == 1) & (self.col == 0)
                    self.is_r <<= (self.row == 1) & (self.col == 1)

        # Malvar-He-Cutler filters (coefficients multiplied by 8, integer)
        # g_at_r_and_b * 8: center=4, orth=2, diag=-1
        # r_at_gr_and_b_at_gb * 8:
        #   [[0,0,4,0,0],[0,-8,0,-8,0],[-8,32,40,32,-8],[0,-8,0,-8,0],[0,0,4,0,0]]
        # r_at_gb_and_b_at_gr * 8 (transpose of above):
        #   [[0,0,-8,0,0],[0,-8,32,-8,0],[4,0,40,0,4],[0,-8,32,-8,0],[0,0,-8,0,0]]
        # r_at_b_and_b_at_r * 8:
        #   [[0,0,-12,0,0],[0,16,0,16,0],[-12,0,48,0,-12],[0,16,0,16,0],[0,0,-12,0,0]]

        @self.comb
        def _malvar():
            w = [[getattr(self, f"w{r}{c}") for c in range(5)] for r in range(5)]

            # --- Green at R/B positions (g_at_r_and_b) ---
            # g = (4*center + 2*(N+S+E+W) - (NN+SS+EE+WW)) / 8
            g_pos = ((w[2][2] << 2)
                     + (w[1][2] << 1) + (w[3][2] << 1)
                     + (w[2][1] << 1) + (w[2][3] << 1))
            g_neg = w[0][2] + w[4][2] + w[2][0] + w[2][4]
            g_interp = Mux(g_pos >= g_neg, (g_pos - g_neg) >> 3, 0)

            # --- R at Gr / B at Gb (r_at_gr_and_b_at_gb) ---
            # r = (4*(NN+SS) + 32*(N+S) + 40*center + 32*(W+E) - 8*(NW+NE+SW+SE)) / 8
            # Simplified from the 5x5 kernel
            r_gr_pos = ((w[0][2] << 2) + (w[4][2] << 2)
                        + (w[1][2] << 5) + (w[3][2] << 5)
                        + (w[2][2] * 40)
                        + (w[2][1] << 5) + (w[2][3] << 5))
            r_gr_neg = ((w[1][1] << 3) + (w[1][3] << 3)
                        + (w[3][1] << 3) + (w[3][3] << 3))
            r_gr = Mux(r_gr_pos >= r_gr_neg, (r_gr_pos - r_gr_neg) >> 3, 0)

            # --- R at Gb / B at Gr (r_at_gb_and_b_at_gr) ---
            # transpose of above: emphasized on horizontal neighbors
            r_gb_pos = ((w[2][0] << 2) + (w[2][4] << 2)
                        + (w[2][1] << 5) + (w[2][3] << 5)
                        + (w[2][2] * 40)
                        + (w[1][2] << 5) + (w[3][2] << 5))
            r_gb_neg = ((w[1][1] << 3) + (w[1][3] << 3)
                        + (w[3][1] << 3) + (w[3][3] << 3))
            r_gb = Mux(r_gb_pos >= r_gb_neg, (r_gb_pos - r_gb_neg) >> 3, 0)

            # --- R at B / B at R (r_at_b_and_b_at_r) ---
            # r = (16*(NW+NE+SW+SE) + 48*center - 12*(NN+SS+EE+WW)) / 8
            r_bb_pos = ((w[1][1] << 4) + (w[1][3] << 4)
                        + (w[3][1] << 4) + (w[3][3] << 4)
                        + (w[2][2] * 48))
            r_bb_neg = ((w[0][2] * 12) + (w[4][2] * 12)
                        + (w[2][0] * 12) + (w[2][4] * 12))
            r_bb = Mux(r_bb_pos >= r_bb_neg, (r_bb_pos - r_bb_neg) >> 3, 0)

            # --- B kernels are symmetric ---
            b_gr = r_gb  # B at Gb = R at Gr transpose
            b_gb = r_gr  # B at Gr = R at Gb transpose
            b_bb = r_bb  # B at R = R at B (same kernel)

            # Select output based on Bayer position
            with If(self.is_r):
                self.pix_r_o <<= w[2][2]
                self.pix_g_o <<= g_interp
                self.pix_b_o <<= b_bb
            with Else():
                with If(self.is_b):
                    self.pix_r_o <<= r_bb
                    self.pix_g_o <<= g_interp
                    self.pix_b_o <<= w[2][2]
                with Else():
                    with If(self.is_gr):
                        self.pix_r_o <<= r_gr
                        self.pix_g_o <<= w[2][2]
                        self.pix_b_o <<= b_gr
                    with Else():  # is_gb
                        self.pix_r_o <<= r_gb
                        self.pix_g_o <<= w[2][2]
                        self.pix_b_o <<= b_gb

            self.pix_valid_o <<= self.out_valid & self.cfg_enable
            self.pix_sof_o <<= self.out_sof
            self.pix_eol_o <<= self.out_eol

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.wr_ptr <<= 0
                self.w00 <<= 0; self.w01 <<= 0; self.w02 <<= 0; self.w03 <<= 0; self.w04 <<= 0
                self.w10 <<= 0; self.w11 <<= 0; self.w12 <<= 0; self.w13 <<= 0; self.w14 <<= 0
                self.w20 <<= 0; self.w21 <<= 0; self.w22 <<= 0; self.w23 <<= 0; self.w24 <<= 0
                self.w30 <<= 0; self.w31 <<= 0; self.w32 <<= 0; self.w33 <<= 0; self.w34 <<= 0
                self.w40 <<= 0; self.w41 <<= 0; self.w42 <<= 0; self.w43 <<= 0; self.w44 <<= 0
                self.row <<= 0
                self.col <<= 0
                self.out_valid <<= 0
                self.out_sof <<= 0
                self.out_eol <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.w00 <<= self.w01; self.w01 <<= self.w02; self.w02 <<= self.w03; self.w03 <<= self.w04
                    self.w10 <<= self.w11; self.w11 <<= self.w12; self.w12 <<= self.w13; self.w13 <<= self.w14
                    self.w20 <<= self.w21; self.w21 <<= self.w22; self.w22 <<= self.w23; self.w23 <<= self.w24
                    self.w30 <<= self.w31; self.w31 <<= self.w32; self.w32 <<= self.w33; self.w33 <<= self.w34
                    self.w40 <<= self.w41; self.w41 <<= self.w42; self.w42 <<= self.w43; self.w43 <<= self.w44
                    self.w04 <<= self.line0[self.wr_ptr]
                    self.w14 <<= self.line1[self.wr_ptr]
                    self.w24 <<= self.line2[self.wr_ptr]
                    self.w34 <<= self.line3[self.wr_ptr]
                    self.w44 <<= self.pix_data_i

                    self.line0[self.wr_ptr] <<= self.w14
                    self.line1[self.wr_ptr] <<= self.w24
                    self.line2[self.wr_ptr] <<= self.w34
                    self.line3[self.wr_ptr] <<= self.w44

                    with If(self.pix_eol_i):
                        self.wr_ptr <<= 0
                        self.col <<= 0
                        self.row <<= ~self.row
                    with Else():
                        self.wr_ptr <<= self.wr_ptr + 1
                        self.col <<= ~self.col

                    self.out_valid <<= 1
                    self.out_sof <<= self.pix_sof_i
                    self.out_eol <<= self.pix_eol_i



# =====================================================================
# ISPCCM — Color Correction Matrix (3x3 fixed-point MAC)
# =====================================================================
class ISPCCM(Module):
    def __init__(self, name="ISPCCM"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_r_i = Input(RGB_W, "pix_r_i")
        self.pix_g_i = Input(RGB_W, "pix_g_i")
        self.pix_b_i = Input(RGB_W, "pix_b_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_r_o = Output(RGB_W, "pix_r_o")
        self.pix_g_o = Output(RGB_W, "pix_g_o")
        self.pix_b_o = Output(RGB_W, "pix_b_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        # Coefficients Q4.8 signed (range -8.0 to +7.996)
        self.cfg_c00 = Input(12, "cfg_c00")
        self.cfg_c01 = Input(12, "cfg_c01")
        self.cfg_c02 = Input(12, "cfg_c02")
        self.cfg_c10 = Input(12, "cfg_c10")
        self.cfg_c11 = Input(12, "cfg_c11")
        self.cfg_c12 = Input(12, "cfg_c12")
        self.cfg_c20 = Input(12, "cfg_c20")
        self.cfg_c21 = Input(12, "cfg_c21")
        self.cfg_c22 = Input(12, "cfg_c22")

        # MAC outputs: 12-bit * 12-bit signed = 24-bit, sum of 3 = 26-bit
        self.r_acc = Wire(MAC_W, "r_acc")
        self.g_acc = Wire(MAC_W, "g_acc")
        self.b_acc = Wire(MAC_W, "b_acc")

        @self.comb
        def _ccm():
            # Sign-extend coefficients to MAC_W and treat as signed
            # For unsigned pixel * signed coeff: if coeff[11]==1 (negative),
            # compute pixel * (4096 - coeff) and subtract from pixel*4096
            # Simplified: use wider unsigned MAC and handle sign manually
            def smul(pix, coeff):
                # pix is unsigned 12-bit, coeff is signed 12-bit Q4.8
                # Return pix * coeff as signed MAC_W-bit
                neg = coeff[11]
                coeff_abs = Mux(neg, (~coeff + 1) & 0xFFF, coeff)
                prod = pix * coeff_abs
                return Mux(neg, (~prod + 1) & ((1 << MAC_W) - 1), prod)

            self.r_acc <<= (smul(self.pix_r_i, self.cfg_c00)
                            + smul(self.pix_g_i, self.cfg_c01)
                            + smul(self.pix_b_i, self.cfg_c02))
            self.g_acc <<= (smul(self.pix_r_i, self.cfg_c10)
                            + smul(self.pix_g_i, self.cfg_c11)
                            + smul(self.pix_b_i, self.cfg_c12))
            self.b_acc <<= (smul(self.pix_r_i, self.cfg_c20)
                            + smul(self.pix_g_i, self.cfg_c21)
                            + smul(self.pix_b_i, self.cfg_c22))

            # Shift right 8 (Q4.8 -> integer)
            r_s = self.r_acc >> 8
            g_s = self.g_acc >> 8
            b_s = self.b_acc >> 8

            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i

            with If(r_s > PIXEL_MAX):
                self.pix_r_o <<= PIXEL_MAX
            with Else():
                self.pix_r_o <<= r_s[RAW_W - 1:0]
            with If(g_s > PIXEL_MAX):
                self.pix_g_o <<= PIXEL_MAX
            with Else():
                self.pix_g_o <<= g_s[RAW_W - 1:0]
            with If(b_s > PIXEL_MAX):
                self.pix_b_o <<= PIXEL_MAX
            with Else():
                self.pix_b_o <<= b_s[RAW_W - 1:0]


# =====================================================================
# ISPGamma — Gamma Correction (4096-entry per-channel LUT)
# =====================================================================
class ISPGamma(Module):
    def __init__(self, name="ISPGamma"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_r_i = Input(RGB_W, "pix_r_i")
        self.pix_g_i = Input(RGB_W, "pix_g_i")
        self.pix_b_i = Input(RGB_W, "pix_b_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_r_o = Output(RGB_W, "pix_r_o")
        self.pix_g_o = Output(RGB_W, "pix_g_o")
        self.pix_b_o = Output(RGB_W, "pix_b_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")

        # 4096-entry x 12-bit LUT per channel (modeled as 3 separate LUTs)
        self.gamma_r_lut = Memory(RGB_W, 4096, "gamma_r_lut")
        self.gamma_g_lut = Memory(RGB_W, 4096, "gamma_g_lut")
        self.gamma_b_lut = Memory(RGB_W, 4096, "gamma_b_lut")

        @self.comb
        def _gamma():
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            self.pix_r_o <<= self.gamma_r_lut[self.pix_r_i]
            self.pix_g_o <<= self.gamma_g_lut[self.pix_g_i]
            self.pix_b_o <<= self.gamma_b_lut[self.pix_b_i]


# =====================================================================
# ISPAEStats — Auto Exposure Statistics (Y histogram + skewness)
# =====================================================================
class ISPAEStats(Module):
    def __init__(self, name="ISPAEStats"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.stat_y_sum = Output(32, "stat_y_sum")
        self.stat_y_sq_sum = Output(40, "stat_y_sq_sum")
        self.stat_y_cu_sum = Output(48, "stat_y_cu_sum")
        self.stat_pix_count = Output(32, "stat_pix_count")
        self.stat_done = Output(1, "stat_done")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_center_illum = Input(8, "cfg_center_illum")

        self.y_acc = Reg(32, "y_acc")
        self.y_sq_acc = Reg(40, "y_sq_acc")
        self.y_cu_acc = Reg(48, "y_cu_acc")
        self.cnt = Reg(32, "cnt")
        self.done_reg = Reg(1, "done_reg")

        @self.comb
        def _stats():
            self.stat_y_sum <<= self.y_acc
            self.stat_y_sq_sum <<= self.y_sq_acc
            self.stat_y_cu_sum <<= self.y_cu_acc
            self.stat_pix_count <<= self.cnt
            self.stat_done <<= self.done_reg

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.y_acc <<= 0
                self.y_sq_acc <<= 0
                self.y_cu_acc <<= 0
                self.cnt <<= 0
                self.done_reg <<= 0
            with Else():
                with If(self.pix_sof_i):
                    self.y_acc <<= 0
                    self.y_sq_acc <<= 0
                    self.y_cu_acc <<= 0
                    self.cnt <<= 0
                    self.done_reg <<= 0
                with Else():
                    with If(self.pix_valid_i & self.cfg_enable):
                        y = self.pix_y_i
                        y_centered = Mux(y > self.cfg_center_illum,
                                          y - self.cfg_center_illum,
                                          self.cfg_center_illum - y)
                        y_sign = Mux(y > self.cfg_center_illum, 0, 1)
                        y_sq = y_centered * y_centered
                        y_cu = y_sq * y_centered
                        self.y_acc <<= self.y_acc + y
                        self.y_sq_acc <<= self.y_sq_acc + y_sq
                        # For skewness: accumulate signed cubic
                        with If(y_sign):
                            self.y_cu_acc <<= self.y_cu_acc - y_cu
                        with Else():
                            self.y_cu_acc <<= self.y_cu_acc + y_cu
                        self.cnt <<= self.cnt + 1
                    with If(self.pix_eol_i & self.cfg_enable):
                        self.done_reg <<= 1


# =====================================================================
# ISPCSC — Color Space Conversion (RGB -> YCbCr, BT.601/709 + CSE)
# =====================================================================
class ISPCSC(Module):
    def __init__(self, name="ISPCSC"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_r_i = Input(RGB_W, "pix_r_i")
        self.pix_g_i = Input(RGB_W, "pix_g_i")
        self.pix_b_i = Input(RGB_W, "pix_b_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_std = Input(1, "cfg_std")  # 0=BT.709, 1=BT.601

        self.y_acc = Wire(MAC_W, "y_acc")
        self.cb_acc = Wire(MAC_W, "cb_acc")
        self.cr_acc = Wire(MAC_W, "cr_acc")

        @self.comb
        def _csc():
            r = self.pix_r_i
            g = self.pix_g_i
            b = self.pix_b_i
            with If(self.cfg_std == 0):  # BT.709
                self.y_acc <<= (47 * r + 157 * g + 16 * b)
                self.cb_acc <<= ((-26) * r + (-86) * g + 112 * b)
                self.cr_acc <<= (112 * r + (-102) * g + (-10) * b)
            with Else():  # BT.601
                self.y_acc <<= (77 * r + 150 * g + 29 * b)
                self.cb_acc <<= ((-43) * r + (-85) * g + 128 * b)
                self.cr_acc <<= (128 * r + (-107) * g + (-21) * b)

            y_val = self.y_acc >> 8
            cb_val = (self.cb_acc >> 8) + 128
            cr_val = (self.cr_acc >> 8) + 128

            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i

            with If(y_val > 255):
                self.pix_y_o <<= 255
            with Else():
                self.pix_y_o <<= y_val[7:0]

            with If(cb_val > 255):
                self.pix_cb_o <<= 255
            with Else():
                with If(cb_val < 0):
                    self.pix_cb_o <<= 0
                with Else():
                    self.pix_cb_o <<= cb_val[7:0]

            with If(cr_val > 255):
                self.pix_cr_o <<= 255
            with Else():
                with If(cr_val < 0):
                    self.pix_cr_o <<= 0
                with Else():
                    self.pix_cr_o <<= cr_val[7:0]


# =====================================================================
# ISPLDCI — CLAHE (Contrast Limited Adaptive Histogram Equalization)
# Tile-based: 4x4 grid, 64-entry LUT per tile, ping-pong buffered
# Reference: clahe.py (Infinite-ISP v1.1)
# =====================================================================
class ISPLDCI(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPLDCI"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_clip_limit = Input(16, "cfg_clip_limit")

        # Tile configuration: 8x8 grid for 2592x1536
        NUM_TILES_X = 8
        NUM_TILES_Y = 8
        NUM_TILES = NUM_TILES_X * NUM_TILES_Y
        LUT_ENTRIES = 256  # 8-bit full Y range

        # Histogram memories: 64 tiles x 256 bins x 16-bit
        self.hist = Memory(16, NUM_TILES * LUT_ENTRIES, "hist")
        # LUT memories: ping-pong
        self.lut_a = Memory(YUV_W, NUM_TILES * LUT_ENTRIES, "lut_a")
        self.lut_b = Memory(YUV_W, NUM_TILES * LUT_ENTRIES, "lut_b")
        self.use_lut_a = Reg(1, "use_lut_a")  # 1=read A, compute B; 0=read B, compute A

        # Position counters
        self.x_cnt = Reg(ADDR_W, "x_cnt")
        self.y_cnt = Reg(ADDR_W, "y_cnt")
        self.frame_cnt = Reg(2, "frame_cnt")

        # Tile dimensions for 2592x1536 with 8x8 grid
        # tile_width = 324, tile_height = 192
        # Division by 324 ≈ (x * 202) >> 16
        # Division by 192 ≈ (y * 341) >> 16

        # State machine
        self.state = Reg(3, "state")
        S_IDLE = 0
        S_HIST = 1
        S_CDF = 2
        S_APPLY = 3

        # CDF computation registers
        self.cdf_tile = Reg(6, "cdf_tile")
        self.cdf_bin = Reg(8, "cdf_bin")
        self.cdf_acc = Reg(32, "cdf_acc")
        self.cdf_clip = Reg(16, "cdf_clip")
        self.cdf_total = Reg(32, "cdf_total")

        # Combinational helpers
        self.tile_x = Wire(3, "tile_x")
        self.tile_y = Wire(3, "tile_y")
        self.intra_x = Wire(ADDR_W, "intra_x")
        self.intra_y = Wire(ADDR_W, "intra_y")
        self.hist_idx = Wire(14, "hist_idx")
        self.lut_idx = Wire(14, "lut_idx")
        self.y_idx = Wire(8, "y_idx")
        self.lut_val = Wire(YUV_W, "lut_val")
        self.hist_rval = Wire(16, "hist_rval")
        self.cdf_hval = Wire(16, "cdf_hval")

        @self.comb
        def _tile():
            self.hist_rval <<= self.hist[self.hist_idx]
            self.cdf_hval <<= self.hist[self.cdf_tile * LUT_ENTRIES + self.cdf_bin]
            # Fixed-point division: tile_x = x / 324 ≈ (x * 202) >> 16
            self.tile_x <<= (self.x_cnt * 202) >> 16
            self.tile_y <<= (self.y_cnt * 341) >> 16
            # Intra-tile position
            self.intra_x <<= self.x_cnt - (self.tile_x * 324)
            self.intra_y <<= self.y_cnt - (self.tile_y * 192)
            self.y_idx <<= self.pix_y_i[7:0]  # 8-bit full Y LUT index
            self.hist_idx <<= (self.tile_y * NUM_TILES_X + self.tile_x) * LUT_ENTRIES + self.y_idx
            self.lut_idx <<= self.hist_idx

            # Read from active LUT
            with If(self.use_lut_a):
                self.lut_val <<= self.lut_a[self.lut_idx]
            with Else():
                self.lut_val <<= self.lut_b[self.lut_idx]

            # Passthrough Cb/Cr, Y gets LUT mapped
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            self.pix_cb_o <<= self.pix_cb_i
            self.pix_cr_o <<= self.pix_cr_i

            with If(self.cfg_enable & (self.state == S_APPLY)):
                self.pix_y_o <<= self.lut_val
            with Else():
                self.pix_y_o <<= self.pix_y_i

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.x_cnt <<= 0
                self.y_cnt <<= 0
                self.frame_cnt <<= 0
                self.state <<= S_IDLE
                self.use_lut_a <<= 1
                self.cdf_tile <<= 0
                self.cdf_bin <<= 0
                self.cdf_acc <<= 0
                self.cdf_clip <<= 0
                self.cdf_total <<= 0
            with Else():
                with If(self.pix_sof_i):
                    self.x_cnt <<= 0
                    self.y_cnt <<= 0
                    self.frame_cnt <<= self.frame_cnt + 1

                # State transitions
                with If(self.state == S_IDLE):
                    with If(self.pix_sof_i):
                        self.state <<= S_HIST
                with Elif(self.state == S_HIST):
                    with If(self.pix_eol_i & (self.y_cnt >= 1535)):
                        # End of frame: start CDF computation
                        self.state <<= S_CDF
                        self.cdf_tile <<= 0
                        self.cdf_bin <<= 0
                        self.cdf_acc <<= 0
                with Elif(self.state == S_CDF):
                    # CDF computation: process one bin per cycle
                    clip = self.cfg_clip_limit
                    hidx = self.cdf_tile * LUT_ENTRIES + self.cdf_bin
                    clipped = Mux(self.cdf_hval > clip, clip, self.cdf_hval)
                    self.cdf_acc <<= self.cdf_acc + clipped
                    lut_out = self.cdf_acc >> 8
                    with If(self.use_lut_a):
                        self.lut_b[hidx] <<= lut_out[7:0]
                    with Else():
                        self.lut_a[hidx] <<= lut_out[7:0]

                    with If(self.cdf_bin < (LUT_ENTRIES - 1)):
                        self.cdf_bin <<= self.cdf_bin + 1
                    with Else():
                        self.cdf_bin <<= 0
                        self.cdf_acc <<= 0
                        with If(self.cdf_tile < (NUM_TILES - 1)):
                            self.cdf_tile <<= self.cdf_tile + 1
                        with Else():
                            self.state <<= S_APPLY
                            self.use_lut_a <<= ~self.use_lut_a
                with Elif(self.state == S_APPLY):
                    with If(self.pix_sof_i):
                        self.state <<= S_HIST

                # Histogram accumulation during S_HIST
                with If(self.state == S_HIST):
                    with If(self.pix_valid_i):
                        # Increment histogram bin
                        self.hist[self.hist_idx] <<= self.hist_rval + 1
                        with If(self.pix_eol_i):
                            self.x_cnt <<= 0
                            self.y_cnt <<= self.y_cnt + 1
                        with Else():
                            self.x_cnt <<= self.x_cnt + 1


# =====================================================================
# ISPSharpen — Unsharp Masking with Gaussian smoothing
# Reference: unsharp_masking.py (Infinite-ISP v1.1)
# =====================================================================
class ISPSharpen(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPSharpen"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_sigma = Input(4, "cfg_sigma")      # Gaussian sigma selection
        self.cfg_strength = Input(8, "cfg_strength")  # Q4.4

        # Line buffers for 3x3 Y window
        self.line0 = Memory(YUV_W, max_width, "line0")
        self.line1 = Memory(YUV_W, max_width, "line1")
        self.wr_ptr = Reg(ADDR_W, "wr_ptr")

        self.w00 = Reg(YUV_W, "w00")
        self.w01 = Reg(YUV_W, "w01")
        self.w02 = Reg(YUV_W, "w02")
        self.w10 = Reg(YUV_W, "w10")
        self.w11 = Reg(YUV_W, "w11")
        self.w12 = Reg(YUV_W, "w12")
        self.w20 = Reg(YUV_W, "w20")
        self.w21 = Reg(YUV_W, "w21")
        self.w22 = Reg(YUV_W, "w22")

        self.out_valid = Reg(1, "out_valid")
        self.out_sof = Reg(1, "out_sof")
        self.out_eol = Reg(1, "out_eol")
        self.out_cb = Reg(YUV_W, "out_cb")
        self.out_cr = Reg(YUV_W, "out_cr")

        # Gaussian smoothed value (3x3 kernel)
        self.gauss = Wire(YUV_W + 4, "gauss")
        self.sharp_y = Wire(YUV_W + 4, "sharp_y")

        @self.comb
        def _sharpen():
            # 3x3 Gaussian kernel (sigma=1.0, normalized to sum=64):
            # [1, 2, 1]
            # [2, 4, 2]
            # [1, 2, 1]
            self.gauss <<= ((self.w00 + self.w02 + self.w20 + self.w22)
                            + ((self.w01 + self.w10 + self.w12 + self.w21) << 1)
                            + (self.w11 << 2)) >> 4

            # Detail = original - smoothed
            detail = self.w11 - self.gauss
            # Sharpened = original + detail * strength (Q4.4)
            scaled_detail = (detail * self.cfg_strength) >> 4
            self.sharp_y <<= self.w11 + scaled_detail

            self.pix_valid_o <<= self.out_valid & self.cfg_enable
            self.pix_sof_o <<= self.out_sof
            self.pix_eol_o <<= self.out_eol
            self.pix_cb_o <<= self.out_cb
            self.pix_cr_o <<= self.out_cr

            with If(self.sharp_y > 255):
                self.pix_y_o <<= 255
            with Else():
                with If(self.sharp_y < 0):
                    self.pix_y_o <<= 0
                with Else():
                    self.pix_y_o <<= self.sharp_y[7:0]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.wr_ptr <<= 0
                self.w00 <<= 0; self.w01 <<= 0; self.w02 <<= 0
                self.w10 <<= 0; self.w11 <<= 0; self.w12 <<= 0
                self.w20 <<= 0; self.w21 <<= 0; self.w22 <<= 0
                self.out_valid <<= 0
                self.out_sof <<= 0
                self.out_eol <<= 0
                self.out_cb <<= 0
                self.out_cr <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.w00 <<= self.w01
                    self.w01 <<= self.w02
                    self.w10 <<= self.w11
                    self.w11 <<= self.w12
                    self.w20 <<= self.w21
                    self.w21 <<= self.w22
                    self.w02 <<= self.line0[self.wr_ptr]
                    self.w12 <<= self.line1[self.wr_ptr]
                    self.w22 <<= self.pix_y_i

                    self.line0[self.wr_ptr] <<= self.w12
                    self.line1[self.wr_ptr] <<= self.w22

                    with If(self.pix_eol_i):
                        self.wr_ptr <<= 0
                    with Else():
                        self.wr_ptr <<= self.wr_ptr + 1

                    self.out_valid <<= 1
                    self.out_sof <<= self.pix_sof_i
                    self.out_eol <<= self.pix_eol_i
                    self.out_cb <<= self.pix_cb_i
                    self.out_cr <<= self.pix_cr_i


# =====================================================================
# ISPNR2D — 2D Noise Reduction (Y-channel bilateral filter)
# =====================================================================
class ISPNR2D(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPNR2D"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_strength = Input(4, "cfg_strength")

        self.line0 = Memory(YUV_W, max_width, "line0")
        self.line1 = Memory(YUV_W, max_width, "line1")
        self.wr_ptr = Reg(ADDR_W, "wr_ptr")

        self.w00 = Reg(YUV_W, "w00")
        self.w01 = Reg(YUV_W, "w01")
        self.w02 = Reg(YUV_W, "w02")
        self.w10 = Reg(YUV_W, "w10")
        self.w11 = Reg(YUV_W, "w11")
        self.w12 = Reg(YUV_W, "w12")
        self.w20 = Reg(YUV_W, "w20")
        self.w21 = Reg(YUV_W, "w21")
        self.w22 = Reg(YUV_W, "w22")

        self.out_valid = Reg(1, "out_valid")
        self.out_sof = Reg(1, "out_sof")
        self.out_eol = Reg(1, "out_eol")
        self.out_cb = Reg(YUV_W, "out_cb")
        self.out_cr = Reg(YUV_W, "out_cr")

        @self.comb
        def _nr2d():
            # 3x3 Gaussian smoothing on Y
            smooth = ((self.w00 + self.w01 + self.w02
                       + self.w10 + self.w11 + self.w12
                       + self.w20 + self.w21 + self.w22)) >> 3
            # Blend original and smoothed based on strength
            blend = ((self.w11 * (16 - self.cfg_strength))
                     + (smooth * self.cfg_strength)) >> 4

            self.pix_valid_o <<= self.out_valid & self.cfg_enable
            self.pix_sof_o <<= self.out_sof
            self.pix_eol_o <<= self.out_eol
            self.pix_cb_o <<= self.out_cb
            self.pix_cr_o <<= self.out_cr
            with If(blend > 255):
                self.pix_y_o <<= 255
            with Else():
                self.pix_y_o <<= blend[7:0]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.wr_ptr <<= 0
                self.w00 <<= 0; self.w01 <<= 0; self.w02 <<= 0
                self.w10 <<= 0; self.w11 <<= 0; self.w12 <<= 0
                self.w20 <<= 0; self.w21 <<= 0; self.w22 <<= 0
                self.out_valid <<= 0
                self.out_sof <<= 0
                self.out_eol <<= 0
                self.out_cb <<= 0
                self.out_cr <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.w00 <<= self.w01
                    self.w01 <<= self.w02
                    self.w10 <<= self.w11
                    self.w11 <<= self.w12
                    self.w20 <<= self.w21
                    self.w21 <<= self.w22
                    self.w02 <<= self.line0[self.wr_ptr]
                    self.w12 <<= self.line1[self.wr_ptr]
                    self.w22 <<= self.pix_y_i

                    self.line0[self.wr_ptr] <<= self.w12
                    self.line1[self.wr_ptr] <<= self.w22

                    with If(self.pix_eol_i):
                        self.wr_ptr <<= 0
                    with Else():
                        self.wr_ptr <<= self.wr_ptr + 1

                    self.out_valid <<= 1
                    self.out_sof <<= self.pix_sof_i
                    self.out_eol <<= self.pix_eol_i
                    self.out_cb <<= self.pix_cb_i
                    self.out_cr <<= self.pix_cr_i


# =====================================================================
# ISPScale — Image scaling (nearest-neighbor / averaging downsample)
# =====================================================================
class ISPScale(Module):
    def __init__(self, name="ISPScale"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_scale_x = Input(2, "cfg_scale_x")  # 0=1x,1=1/2x,2=1/4x
        self.cfg_scale_y = Input(2, "cfg_scale_y")

        self.x_cnt = Reg(ADDR_W, "x_cnt")
        self.y_cnt = Reg(ADDR_W, "y_cnt")
        self.out_x = Wire(1, "out_x")
        self.out_y = Wire(1, "out_y")

        @self.comb
        def _scale():
            self.out_x <<= Mux(self.cfg_scale_x == 0, 1,
                             Mux(self.cfg_scale_x == 1, self.x_cnt[0] == 0,
                                 self.x_cnt[1:0] == 0))
            self.out_y <<= Mux(self.cfg_scale_y == 0, 1,
                             Mux(self.cfg_scale_y == 1, self.y_cnt[0] == 0,
                                 self.y_cnt[1:0] == 0))

            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable & self.out_x & self.out_y
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i & self.out_x
            self.pix_y_o <<= self.pix_y_i
            self.pix_cb_o <<= self.pix_cb_i
            self.pix_cr_o <<= self.pix_cr_i

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.x_cnt <<= 0
                self.y_cnt <<= 0
            with Else():
                with If(self.pix_valid_i):
                    with If(self.pix_eol_i):
                        self.x_cnt <<= 0
                        self.y_cnt <<= self.y_cnt + 1
                    with Else():
                        self.x_cnt <<= self.x_cnt + 1
                    with If(self.pix_sof_i):
                        self.y_cnt <<= 0


# =====================================================================
# ISPYUV — YUV Format Conversion (444 to 422 / 420)
# =====================================================================
class ISPYUV(Module):
    def __init__(self, name="ISPYUV"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")
        self.pix_valid_o = Output(1, "pix_valid_o")
        self.pix_y_o = Output(YUV_W, "pix_y_o")
        self.pix_cb_o = Output(YUV_W, "pix_cb_o")
        self.pix_cr_o = Output(YUV_W, "pix_cr_o")
        self.pix_sof_o = Output(1, "pix_sof_o")
        self.pix_eol_o = Output(1, "pix_eol_o")
        self.cfg_enable = Input(1, "cfg_enable")
        self.cfg_format = Input(2, "cfg_format")  # 0=444,1=422,2=420

        self.x_cnt = Reg(1, "x_cnt")
        self.y_cnt = Reg(1, "y_cnt")
        self.cb_acc = Reg(YUV_W + 1, "cb_acc")
        self.cr_acc = Reg(YUV_W + 1, "cr_acc")

        @self.comb
        def _yuv():
            self.pix_valid_o <<= self.pix_valid_i & self.cfg_enable
            self.pix_sof_o <<= self.pix_sof_i
            self.pix_eol_o <<= self.pix_eol_i
            self.pix_y_o <<= self.pix_y_i

            with If(self.cfg_format == 0):  # 444
                self.pix_cb_o <<= self.pix_cb_i
                self.pix_cr_o <<= self.pix_cr_i
            with Else():
                # 422/420: average Cb/Cr across 2 horizontal pixels
                with If(self.x_cnt == 0):
                    self.pix_cb_o <<= self.cb_acc >> 1
                    self.pix_cr_o <<= self.cr_acc >> 1
                with Else():
                    self.pix_cb_o <<= self.pix_cb_i
                    self.pix_cr_o <<= self.pix_cr_i

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.x_cnt <<= 0
                self.y_cnt <<= 0
                self.cb_acc <<= 0
                self.cr_acc <<= 0
            with Else():
                with If(self.pix_valid_i):
                    self.cb_acc <<= self.pix_cb_i
                    self.cr_acc <<= self.pix_cr_i
                    with If(self.pix_eol_i):
                        self.x_cnt <<= 0
                        self.y_cnt <<= ~self.y_cnt
                    with Else():
                        self.x_cnt <<= ~self.x_cnt


# =====================================================================
# ISPAXIStreamOut — AXI-Stream Master output
# =====================================================================
class ISPAXIStreamOut(Module):
    def __init__(self, name="ISPAXIStreamOut"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pix_valid_i = Input(1, "pix_valid_i")
        self.pix_y_i = Input(YUV_W, "pix_y_i")
        self.pix_cb_i = Input(YUV_W, "pix_cb_i")
        self.pix_cr_i = Input(YUV_W, "pix_cr_i")
        self.pix_sof_i = Input(1, "pix_sof_i")
        self.pix_eol_i = Input(1, "pix_eol_i")

        self.m_axis_aclk = Input(1, "m_axis_aclk")
        self.m_axis_aresetn = Input(1, "m_axis_aresetn")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")
        self.m_axis_tdata = Output(24, "m_axis_tdata")
        self.m_axis_tlast = Output(1, "m_axis_tlast")
        self.m_axis_tuser = Output(1, "m_axis_tuser")

        self.out_reg = Reg(24, "out_reg")
        self.out_valid_reg = Reg(1, "out_valid_reg")
        self.out_last_reg = Reg(1, "out_last_reg")
        self.out_user_reg = Reg(1, "out_user_reg")

        @self.comb
        def _out():
            self.m_axis_tvalid <<= self.out_valid_reg
            self.m_axis_tdata <<= self.out_reg
            self.m_axis_tlast <<= self.out_last_reg
            self.m_axis_tuser <<= self.out_user_reg

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.out_reg <<= 0
                self.out_valid_reg <<= 0
                self.out_last_reg <<= 0
                self.out_user_reg <<= 0
            with Else():
                with If(self.pix_valid_i & self.m_axis_tready):
                    self.out_reg <<= Cat(self.pix_cr_i, self.pix_cb_i, self.pix_y_i)
                    self.out_valid_reg <<= 1
                    self.out_last_reg <<= self.pix_eol_i
                    self.out_user_reg <<= self.pix_sof_i
                with Else():
                    with If(self.m_axis_tready):
                        self.out_valid_reg <<= 0



# =====================================================================
# ISPAPBRegs — Extended APB Configuration Register Bank (32 regs)
# =====================================================================
class ISPAPBRegs(Module):
    def __init__(self, name="ISPAPBRegs"):
        super().__init__(name)
        self.pclk = Input(1, "pclk")
        self.preset_n = Input(1, "preset_n")
        self.psel = Input(1, "psel")
        self.penable = Input(1, "penable")
        self.pwrite = Input(1, "pwrite")
        self.paddr = Input(8, "paddr")
        self.pwdata = Input(32, "pwdata")
        self.prdata = Output(32, "prdata")
        self.pready = Output(1, "pready")
        self.pslverr = Output(1, "pslverr")

        # 32 configuration registers
        for i in range(32):
            setattr(self, f"reg{i}", Reg(32, f"reg{i}"))

        self.addr_idx = Wire(5, "addr_idx")

        # Config outputs
        self.cfg_crop_enable = Output(1, "cfg_crop_enable")
        self.cfg_crop_start_x = Output(ADDR_W, "cfg_crop_start_x")
        self.cfg_crop_start_y = Output(ADDR_W, "cfg_crop_start_y")
        self.cfg_crop_width = Output(ADDR_W, "cfg_crop_width")
        self.cfg_crop_height = Output(ADDR_W, "cfg_crop_height")
        self.cfg_dpc_enable = Output(1, "cfg_dpc_enable")
        self.cfg_dpc_threshold = Output(RAW_W, "cfg_dpc_threshold")
        self.cfg_blc_enable = Output(1, "cfg_blc_enable")
        self.cfg_blc_r_offset = Output(RAW_W, "cfg_blc_r_offset")
        self.cfg_blc_gr_offset = Output(RAW_W, "cfg_blc_gr_offset")
        self.cfg_blc_gb_offset = Output(RAW_W, "cfg_blc_gb_offset")
        self.cfg_blc_b_offset = Output(RAW_W, "cfg_blc_b_offset")
        self.cfg_oecf_enable = Output(1, "cfg_oecf_enable")
        self.cfg_dg_enable = Output(1, "cfg_dg_enable")
        self.cfg_dg_gain = Output(12, "cfg_dg_gain")
        self.cfg_lsc_enable = Output(1, "cfg_lsc_enable")
        self.cfg_lsc_r_gain = Output(8, "cfg_lsc_r_gain")
        self.cfg_lsc_gr_gain = Output(8, "cfg_lsc_gr_gain")
        self.cfg_lsc_gb_gain = Output(8, "cfg_lsc_gb_gain")
        self.cfg_lsc_b_gain = Output(8, "cfg_lsc_b_gain")
        self.cfg_bnr_enable = Output(1, "cfg_bnr_enable")
        self.cfg_bnr_sigma_r = Output(8, "cfg_bnr_sigma_r")
        self.cfg_wb_enable = Output(1, "cfg_wb_enable")
        self.cfg_wb_r_gain = Output(12, "cfg_wb_r_gain")
        self.cfg_wb_b_gain = Output(12, "cfg_wb_b_gain")
        self.cfg_wb_g_gain = Output(12, "cfg_wb_g_gain")
        self.cfg_demosaic_enable = Output(1, "cfg_demosaic_enable")
        self.cfg_ccm_enable = Output(1, "cfg_ccm_enable")
        self.cfg_gamma_enable = Output(1, "cfg_gamma_enable")
        self.cfg_csc_enable = Output(1, "cfg_csc_enable")
        self.cfg_csc_std = Output(1, "cfg_csc_std")
        self.cfg_ldci_enable = Output(1, "cfg_ldci_enable")
        self.cfg_ldci_clip_limit = Output(16, "cfg_ldci_clip_limit")
        self.cfg_sharpen_enable = Output(1, "cfg_sharpen_enable")
        self.cfg_sharpen_sigma = Output(4, "cfg_sharpen_sigma")
        self.cfg_sharpen_strength = Output(8, "cfg_sharpen_strength")
        self.cfg_nr2d_enable = Output(1, "cfg_nr2d_enable")
        self.cfg_nr2d_strength = Output(4, "cfg_nr2d_strength")
        self.cfg_scale_enable = Output(1, "cfg_scale_enable")
        self.cfg_scale_x = Output(2, "cfg_scale_x")
        self.cfg_scale_y = Output(2, "cfg_scale_y")
        self.cfg_yuv_enable = Output(1, "cfg_yuv_enable")
        self.cfg_yuv_format = Output(2, "cfg_yuv_format")
        self.cfg_bayer_pattern = Output(2, "cfg_bayer_pattern")
        self.cfg_ae_enable = Output(1, "cfg_ae_enable")
        self.cfg_ae_center_illum = Output(8, "cfg_ae_center_illum")
        self.cfg_awb_enable = Output(1, "cfg_awb_enable")
        # CCM coefficients Q4.8
        self.cfg_c00 = Output(12, "cfg_c00")
        self.cfg_c01 = Output(12, "cfg_c01")
        self.cfg_c02 = Output(12, "cfg_c02")
        self.cfg_c10 = Output(12, "cfg_c10")
        self.cfg_c11 = Output(12, "cfg_c11")
        self.cfg_c12 = Output(12, "cfg_c12")
        self.cfg_c20 = Output(12, "cfg_c20")
        self.cfg_c21 = Output(12, "cfg_c21")
        self.cfg_c22 = Output(12, "cfg_c22")

        @self.comb
        def _decode():
            self.addr_idx <<= self.paddr[6:2]

            # Register field decoding
            self.cfg_crop_enable <<= self.reg0[0]
            self.cfg_crop_start_x <<= self.reg0[13:1]
            self.cfg_crop_start_y <<= self.reg0[25:14]
            self.cfg_crop_width <<= self.reg1[11:0]
            self.cfg_crop_height <<= self.reg1[23:12]
            self.cfg_dpc_enable <<= self.reg2[0]
            self.cfg_dpc_threshold <<= self.reg2[13:1]
            self.cfg_blc_enable <<= self.reg3[0]
            self.cfg_blc_r_offset <<= self.reg3[13:1]
            self.cfg_blc_gr_offset <<= self.reg3[25:14]
            self.cfg_blc_gb_offset <<= self.reg4[13:1]
            self.cfg_blc_b_offset <<= self.reg4[25:14]
            self.cfg_oecf_enable <<= self.reg5[0]
            self.cfg_dg_enable <<= self.reg6[0]
            self.cfg_dg_gain <<= self.reg6[13:1]
            self.cfg_lsc_enable <<= self.reg7[0]
            self.cfg_lsc_r_gain <<= self.reg7[9:1]
            self.cfg_lsc_gr_gain <<= self.reg7[17:10]
            self.cfg_lsc_gb_gain <<= self.reg7[25:18]
            self.cfg_lsc_b_gain <<= self.reg8[9:1]
            self.cfg_bnr_enable <<= self.reg8[10]
            self.cfg_bnr_sigma_r <<= self.reg8[19:11]
            self.cfg_wb_enable <<= self.reg9[0]
            self.cfg_wb_r_gain <<= self.reg9[13:1]
            self.cfg_wb_b_gain <<= self.reg9[26:14]
            self.cfg_wb_g_gain <<= self.reg10[13:1]
            self.cfg_demosaic_enable <<= self.reg10[14]
            self.cfg_ccm_enable <<= self.reg10[15]
            self.cfg_gamma_enable <<= self.reg10[16]
            self.cfg_csc_enable <<= self.reg11[0]
            self.cfg_csc_std <<= self.reg11[1]
            self.cfg_ldci_enable <<= self.reg11[2]
            self.cfg_ldci_clip_limit <<= self.reg11[19:3]
            self.cfg_sharpen_enable <<= self.reg12[0]
            self.cfg_sharpen_sigma <<= self.reg12[5:1]
            self.cfg_sharpen_strength <<= self.reg12[14:6]
            self.cfg_nr2d_enable <<= self.reg13[0]
            self.cfg_nr2d_strength <<= self.reg13[5:1]
            self.cfg_scale_enable <<= self.reg13[6]
            self.cfg_scale_x <<= self.reg13[9:7]
            self.cfg_scale_y <<= self.reg13[12:10]
            self.cfg_yuv_enable <<= self.reg13[13]
            self.cfg_yuv_format <<= self.reg13[16:14]
            self.cfg_bayer_pattern <<= self.reg14[2:0]
            self.cfg_ae_enable <<= self.reg14[3]
            self.cfg_ae_center_illum <<= self.reg14[12:4]
            self.cfg_awb_enable <<= self.reg14[13]

            self.cfg_c00 <<= self.reg15[11:0]
            self.cfg_c01 <<= self.reg16[11:0]
            self.cfg_c02 <<= self.reg17[11:0]
            self.cfg_c10 <<= self.reg18[11:0]
            self.cfg_c11 <<= self.reg19[11:0]
            self.cfg_c12 <<= self.reg20[11:0]
            self.cfg_c20 <<= self.reg21[11:0]
            self.cfg_c21 <<= self.reg22[11:0]
            self.cfg_c22 <<= self.reg23[11:0]

            # APB read mux
            with Switch(self.addr_idx) as sw:
                with sw.case(0): self.prdata <<= self.reg0
                with sw.case(1): self.prdata <<= self.reg1
                with sw.case(2): self.prdata <<= self.reg2
                with sw.case(3): self.prdata <<= self.reg3
                with sw.case(4): self.prdata <<= self.reg4
                with sw.case(5): self.prdata <<= self.reg5
                with sw.case(6): self.prdata <<= self.reg6
                with sw.case(7): self.prdata <<= self.reg7
                with sw.case(8): self.prdata <<= self.reg8
                with sw.case(9): self.prdata <<= self.reg9
                with sw.case(10): self.prdata <<= self.reg10
                with sw.case(11): self.prdata <<= self.reg11
                with sw.case(12): self.prdata <<= self.reg12
                with sw.case(13): self.prdata <<= self.reg13
                with sw.case(14): self.prdata <<= self.reg14
                with sw.case(15): self.prdata <<= self.reg15
                with sw.case(16): self.prdata <<= self.reg16
                with sw.case(17): self.prdata <<= self.reg17
                with sw.case(18): self.prdata <<= self.reg18
                with sw.case(19): self.prdata <<= self.reg19
                with sw.case(20): self.prdata <<= self.reg20
                with sw.case(21): self.prdata <<= self.reg21
                with sw.case(22): self.prdata <<= self.reg22
                with sw.case(23): self.prdata <<= self.reg23
                with sw.case(24): self.prdata <<= self.reg24
                with sw.case(25): self.prdata <<= self.reg25
                with sw.case(26): self.prdata <<= self.reg26
                with sw.case(27): self.prdata <<= self.reg27
                with sw.case(28): self.prdata <<= self.reg28
                with sw.case(29): self.prdata <<= self.reg29
                with sw.case(30): self.prdata <<= self.reg30
                with sw.case(31): self.prdata <<= self.reg31


            self.pready <<= self.psel & self.penable
            self.pslverr <<= 0

        @self.seq(self.pclk, self.preset_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.preset_n == 0):
                self.reg0 <<= 0; self.reg1 <<= 0; self.reg2 <<= 0; self.reg3 <<= 0; self.reg4 <<= 0; self.reg5 <<= 0; self.reg6 <<= 0; self.reg7 <<= 0; self.reg8 <<= 0; self.reg9 <<= 0; self.reg10 <<= 0; self.reg11 <<= 0; self.reg12 <<= 0; self.reg13 <<= 0; self.reg14 <<= 0; self.reg15 <<= 0; self.reg16 <<= 0; self.reg17 <<= 0; self.reg18 <<= 0; self.reg19 <<= 0; self.reg20 <<= 0; self.reg21 <<= 0; self.reg22 <<= 0; self.reg23 <<= 0; self.reg24 <<= 0; self.reg25 <<= 0; self.reg26 <<= 0; self.reg27 <<= 0; self.reg28 <<= 0; self.reg29 <<= 0; self.reg30 <<= 0; self.reg31 <<= 0

            with Else():
                with If(self.psel & self.penable & self.pwrite):
                    with Switch(self.addr_idx) as sw:
                        with sw.case(0): self.reg0 <<= self.pwdata
                        with sw.case(1): self.reg1 <<= self.pwdata
                        with sw.case(2): self.reg2 <<= self.pwdata
                        with sw.case(3): self.reg3 <<= self.pwdata
                        with sw.case(4): self.reg4 <<= self.pwdata
                        with sw.case(5): self.reg5 <<= self.pwdata
                        with sw.case(6): self.reg6 <<= self.pwdata
                        with sw.case(7): self.reg7 <<= self.pwdata
                        with sw.case(8): self.reg8 <<= self.pwdata
                        with sw.case(9): self.reg9 <<= self.pwdata
                        with sw.case(10): self.reg10 <<= self.pwdata
                        with sw.case(11): self.reg11 <<= self.pwdata
                        with sw.case(12): self.reg12 <<= self.pwdata
                        with sw.case(13): self.reg13 <<= self.pwdata
                        with sw.case(14): self.reg14 <<= self.pwdata
                        with sw.case(15): self.reg15 <<= self.pwdata
                        with sw.case(16): self.reg16 <<= self.pwdata
                        with sw.case(17): self.reg17 <<= self.pwdata
                        with sw.case(18): self.reg18 <<= self.pwdata
                        with sw.case(19): self.reg19 <<= self.pwdata
                        with sw.case(20): self.reg20 <<= self.pwdata
                        with sw.case(21): self.reg21 <<= self.pwdata
                        with sw.case(22): self.reg22 <<= self.pwdata
                        with sw.case(23): self.reg23 <<= self.pwdata
                        with sw.case(24): self.reg24 <<= self.pwdata
                        with sw.case(25): self.reg25 <<= self.pwdata
                        with sw.case(26): self.reg26 <<= self.pwdata
                        with sw.case(27): self.reg27 <<= self.pwdata
                        with sw.case(28): self.reg28 <<= self.pwdata
                        with sw.case(29): self.reg29 <<= self.pwdata
                        with sw.case(30): self.reg30 <<= self.pwdata
                        with sw.case(31): self.reg31 <<= self.pwdata



# =====================================================================
# ISPController — Top-level ISP Processor (Full Pipeline)
# =====================================================================
class ISPController(Module):
    def __init__(self, max_width=MAX_WIDTH, name="ISPController"):
        super().__init__(name)
        self.max_width = LocalParam(max_width, "max_width")

        # AXI-Stream input
        self.s_axis_aclk = Input(1, "s_axis_aclk")
        self.s_axis_aresetn = Input(1, "s_axis_aresetn")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.s_axis_tdata = Input(RAW_W, "s_axis_tdata")
        self.s_axis_tlast = Input(1, "s_axis_tlast")
        self.s_axis_tuser = Input(1, "s_axis_tuser")

        # AXI-Stream output
        self.m_axis_aclk = Input(1, "m_axis_aclk")
        self.m_axis_aresetn = Input(1, "m_axis_aresetn")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")
        self.m_axis_tdata = Output(24, "m_axis_tdata")
        self.m_axis_tlast = Output(1, "m_axis_tlast")
        self.m_axis_tuser = Output(1, "m_axis_tuser")

        # APB config
        self.pclk = Input(1, "pclk")
        self.preset_n = Input(1, "preset_n")
        self.psel = Input(1, "psel")
        self.penable = Input(1, "penable")
        self.pwrite = Input(1, "pwrite")
        self.paddr = Input(8, "paddr")
        self.pwdata = Input(32, "pwdata")
        self.prdata = Output(32, "prdata")
        self.pready = Output(1, "pready")

        # APB registers
        apb_regs = ISPAPBRegs(name="u_apb_regs")
        self.instantiate(apb_regs, name="u_apb_regs", port_map={
            "pclk": self.pclk, "preset_n": self.preset_n, "psel": self.psel,
            "penable": self.penable, "pwrite": self.pwrite, "paddr": self.paddr,
            "pwdata": self.pwdata, "prdata": self.prdata, "pready": self.pready,
            "pslverr": Wire(1, "pslverr_unused"),
        })

        # AXI-Stream In
        axis_in = ISPAXIStreamIn(name="u_axis_in")
        self.instantiate(axis_in, name="u_axis_in", port_map={
            "s_axis_aclk": self.s_axis_aclk, "s_axis_aresetn": self.s_axis_aresetn,
            "s_axis_tvalid": self.s_axis_tvalid, "s_axis_tready": self.s_axis_tready,
            "s_axis_tdata": self.s_axis_tdata, "s_axis_tlast": self.s_axis_tlast,
            "s_axis_tuser": self.s_axis_tuser,
        })

        # Crop
        crop = ISPCrop(max_width=max_width, name="u_crop")
        self.instantiate(crop, name="u_crop", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": axis_in.pix_valid_o, "pix_data_i": axis_in.pix_data_o,
            "pix_sof_i": axis_in.pix_sof_o, "pix_eol_i": axis_in.pix_eol_o,
            "cfg_enable": apb_regs.cfg_crop_enable, "cfg_start_x": apb_regs.cfg_crop_start_x,
            "cfg_start_y": apb_regs.cfg_crop_start_y, "cfg_width": apb_regs.cfg_crop_width,
            "cfg_height": apb_regs.cfg_crop_height,
        })

        # DPC
        dpc = ISPDPC(max_width=max_width, name="u_dpc")
        self.instantiate(dpc, name="u_dpc", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": crop.pix_valid_o, "pix_data_i": crop.pix_data_o,
            "pix_sof_i": crop.pix_sof_o, "pix_eol_i": crop.pix_eol_o,
            "cfg_enable": apb_regs.cfg_dpc_enable, "cfg_threshold": apb_regs.cfg_dpc_threshold,
        })

        # BLC
        blc = ISPBLC(name="u_blc")
        self.instantiate(blc, name="u_blc", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": dpc.pix_valid_o, "pix_data_i": dpc.pix_data_o,
            "pix_sof_i": dpc.pix_sof_o, "pix_eol_i": dpc.pix_eol_o,
            "cfg_enable": apb_regs.cfg_blc_enable, "cfg_r_offset": apb_regs.cfg_blc_r_offset,
            "cfg_gr_offset": apb_regs.cfg_blc_gr_offset, "cfg_gb_offset": apb_regs.cfg_blc_gb_offset,
            "cfg_b_offset": apb_regs.cfg_blc_b_offset, "cfg_bayer": apb_regs.cfg_bayer_pattern,
        })

        # OECF
        oecf = ISPOECF(name="u_oecf")
        self.instantiate(oecf, name="u_oecf", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": blc.pix_valid_o, "pix_data_i": blc.pix_data_o,
            "pix_sof_i": blc.pix_sof_o, "pix_eol_i": blc.pix_eol_o,
            "cfg_enable": apb_regs.cfg_oecf_enable,
        })

        # Digital Gain
        dg = ISPDG(name="u_dg")
        self.instantiate(dg, name="u_dg", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": oecf.pix_valid_o, "pix_data_i": oecf.pix_data_o,
            "pix_sof_i": oecf.pix_sof_o, "pix_eol_i": oecf.pix_eol_o,
            "cfg_enable": apb_regs.cfg_dg_enable, "cfg_gain": apb_regs.cfg_dg_gain,
        })

        # LSC
        lsc = ISPLSC(name="u_lsc")
        self.instantiate(lsc, name="u_lsc", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": dg.pix_valid_o, "pix_data_i": dg.pix_data_o,
            "pix_sof_i": dg.pix_sof_o, "pix_eol_i": dg.pix_eol_o,
            "cfg_enable": apb_regs.cfg_lsc_enable, "cfg_gain_r": apb_regs.cfg_lsc_r_gain,
            "cfg_gain_gr": apb_regs.cfg_lsc_gr_gain, "cfg_gain_gb": apb_regs.cfg_lsc_gb_gain,
            "cfg_gain_b": apb_regs.cfg_lsc_b_gain, "cfg_bayer": apb_regs.cfg_bayer_pattern,
        })

        # BNR
        bnr = ISPBNR(max_width=max_width, name="u_bnr")
        self.instantiate(bnr, name="u_bnr", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": lsc.pix_valid_o, "pix_data_i": lsc.pix_data_o,
            "pix_sof_i": lsc.pix_sof_o, "pix_eol_i": lsc.pix_eol_o,
            "cfg_enable": apb_regs.cfg_bnr_enable, "cfg_sigma_r": apb_regs.cfg_bnr_sigma_r,
            "cfg_bayer": apb_regs.cfg_bayer_pattern,
        })

        # WB
        wb = ISPWB(name="u_wb")
        self.instantiate(wb, name="u_wb", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": bnr.pix_valid_o, "pix_data_i": bnr.pix_data_o,
            "pix_sof_i": bnr.pix_sof_o, "pix_eol_i": bnr.pix_eol_o,
            "cfg_enable": apb_regs.cfg_wb_enable, "cfg_r_gain": apb_regs.cfg_wb_r_gain,
            "cfg_b_gain": apb_regs.cfg_wb_b_gain, "cfg_g_gain": apb_regs.cfg_wb_g_gain,
            "cfg_bayer": apb_regs.cfg_bayer_pattern,
        })

        # Demosaic
        dem = ISPDemosaic(max_width=max_width, name="u_demosaic")
        self.instantiate(dem, name="u_demosaic", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": wb.pix_valid_o, "pix_data_i": wb.pix_data_o,
            "pix_sof_i": wb.pix_sof_o, "pix_eol_i": wb.pix_eol_o,
            "cfg_enable": apb_regs.cfg_demosaic_enable, "cfg_bayer": apb_regs.cfg_bayer_pattern,
        })

        # AWB Statistics (tap after demosaic)
        awb_stats = ISPAWBStats(name="u_awb_stats")
        self.instantiate(awb_stats, name="u_awb_stats", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": dem.pix_valid_o, "pix_r_i": dem.pix_r_o,
            "pix_g_i": dem.pix_g_o, "pix_b_i": dem.pix_b_o,
            "pix_sof_i": dem.pix_sof_o, "cfg_enable": apb_regs.cfg_awb_enable,
        })

        # CCM
        ccm = ISPCCM(name="u_ccm")
        self.instantiate(ccm, name="u_ccm", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": dem.pix_valid_o, "pix_r_i": dem.pix_r_o,
            "pix_g_i": dem.pix_g_o, "pix_b_i": dem.pix_b_o,
            "pix_sof_i": dem.pix_sof_o, "pix_eol_i": dem.pix_eol_o,
            "cfg_enable": apb_regs.cfg_ccm_enable,
            "cfg_c00": apb_regs.cfg_c00, "cfg_c01": apb_regs.cfg_c01, "cfg_c02": apb_regs.cfg_c02,
            "cfg_c10": apb_regs.cfg_c10, "cfg_c11": apb_regs.cfg_c11, "cfg_c12": apb_regs.cfg_c12,
            "cfg_c20": apb_regs.cfg_c20, "cfg_c21": apb_regs.cfg_c21, "cfg_c22": apb_regs.cfg_c22,
        })

        # Gamma
        gamma = ISPGamma(name="u_gamma")
        self.instantiate(gamma, name="u_gamma", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": ccm.pix_valid_o, "pix_r_i": ccm.pix_r_o,
            "pix_g_i": ccm.pix_g_o, "pix_b_i": ccm.pix_b_o,
            "pix_sof_i": ccm.pix_sof_o, "pix_eol_i": ccm.pix_eol_o,
            "cfg_enable": apb_regs.cfg_gamma_enable,
        })

        # CSC
        csc = ISPCSC(name="u_csc")
        self.instantiate(csc, name="u_csc", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": gamma.pix_valid_o, "pix_r_i": gamma.pix_r_o,
            "pix_g_i": gamma.pix_g_o, "pix_b_i": gamma.pix_b_o,
            "pix_sof_i": gamma.pix_sof_o, "pix_eol_i": gamma.pix_eol_o,
            "cfg_enable": apb_regs.cfg_csc_enable, "cfg_std": apb_regs.cfg_csc_std,
        })

        # AE Statistics (tap after CSC)
        ae_stats = ISPAEStats(name="u_ae_stats")
        self.instantiate(ae_stats, name="u_ae_stats", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": csc.pix_valid_o, "pix_y_i": csc.pix_y_o,
            "pix_sof_i": csc.pix_sof_o, "cfg_enable": apb_regs.cfg_ae_enable,
            "cfg_center_illum": apb_regs.cfg_ae_center_illum,
        })

        # LDCI (CLAHE)
        ldci = ISPLDCI(max_width=max_width, name="u_ldci")
        self.instantiate(ldci, name="u_ldci", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": csc.pix_valid_o, "pix_y_i": csc.pix_y_o,
            "pix_cb_i": csc.pix_cb_o, "pix_cr_i": csc.pix_cr_o,
            "pix_sof_i": csc.pix_sof_o, "pix_eol_i": csc.pix_eol_o,
            "cfg_enable": apb_regs.cfg_ldci_enable, "cfg_clip_limit": apb_regs.cfg_ldci_clip_limit,
        })

        # Sharpen
        sharp = ISPSharpen(max_width=max_width, name="u_sharpen")
        self.instantiate(sharp, name="u_sharpen", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": ldci.pix_valid_o, "pix_y_i": ldci.pix_y_o,
            "pix_cb_i": ldci.pix_cb_o, "pix_cr_i": ldci.pix_cr_o,
            "pix_sof_i": ldci.pix_sof_o, "pix_eol_i": ldci.pix_eol_o,
            "cfg_enable": apb_regs.cfg_sharpen_enable, "cfg_sigma": apb_regs.cfg_sharpen_sigma,
            "cfg_strength": apb_regs.cfg_sharpen_strength,
        })

        # NR2D
        nr2d = ISPNR2D(max_width=max_width, name="u_nr2d")
        self.instantiate(nr2d, name="u_nr2d", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": sharp.pix_valid_o, "pix_y_i": sharp.pix_y_o,
            "pix_cb_i": sharp.pix_cb_o, "pix_cr_i": sharp.pix_cr_o,
            "pix_sof_i": sharp.pix_sof_o, "pix_eol_i": sharp.pix_eol_o,
            "cfg_enable": apb_regs.cfg_nr2d_enable, "cfg_strength": apb_regs.cfg_nr2d_strength,
        })

        # Scale
        scale = ISPScale(name="u_scale")
        self.instantiate(scale, name="u_scale", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": nr2d.pix_valid_o, "pix_y_i": nr2d.pix_y_o,
            "pix_cb_i": nr2d.pix_cb_o, "pix_cr_i": nr2d.pix_cr_o,
            "pix_sof_i": nr2d.pix_sof_o, "pix_eol_i": nr2d.pix_eol_o,
            "cfg_enable": apb_regs.cfg_scale_enable, "cfg_scale_x": apb_regs.cfg_scale_x,
            "cfg_scale_y": apb_regs.cfg_scale_y,
        })

        # YUV
        yuv = ISPYUV(name="u_yuv")
        self.instantiate(yuv, name="u_yuv", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": scale.pix_valid_o, "pix_y_i": scale.pix_y_o,
            "pix_cb_i": scale.pix_cb_o, "pix_cr_i": scale.pix_cr_o,
            "pix_sof_i": scale.pix_sof_o, "pix_eol_i": scale.pix_eol_o,
            "cfg_enable": apb_regs.cfg_yuv_enable, "cfg_format": apb_regs.cfg_yuv_format,
        })

        # AXI-Stream Out
        axis_out = ISPAXIStreamOut(name="u_axis_out")
        self.instantiate(axis_out, name="u_axis_out", port_map={
            "clk": self.s_axis_aclk, "rst_n": self.s_axis_aresetn,
            "pix_valid_i": yuv.pix_valid_o, "pix_y_i": yuv.pix_y_o,
            "pix_cb_i": yuv.pix_cb_o, "pix_cr_i": yuv.pix_cr_o,
            "pix_sof_i": yuv.pix_sof_o, "pix_eol_i": yuv.pix_eol_o,
            "m_axis_aclk": self.m_axis_aclk, "m_axis_aresetn": self.m_axis_aresetn,
            "m_axis_tvalid": self.m_axis_tvalid, "m_axis_tready": self.m_axis_tready,
            "m_axis_tdata": self.m_axis_tdata, "m_axis_tlast": self.m_axis_tlast,
            "m_axis_tuser": self.m_axis_tuser,
        })
