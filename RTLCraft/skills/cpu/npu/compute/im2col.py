"""
NeuralAccel Im2Col Engine

Transforms an NCHW or NHWC feature map into a column matrix suitable
for GEMM-based convolution (im2col).

Operation:
  Input feature map:  (H, W, C) stored in source SRAM
  Output matrix:      (K*K*C, H_out*W_out) stored in destination SRAM

For each output spatial position (oh, ow) and each kernel position (kh, kw):
  ih = oh * stride_h + kh - pad_h
  iw = ow * stride_w + kw - pad_w
  if 0 <= ih < in_h and 0 <= iw < in_w:
    copy in_c channels from (ih, iw) to output column
  else:
    write zeros (padding)

Assumes CHW layout in memory: addr = base + (ih*in_w + iw)*in_c + ic
Output layout (column-major-ish): addr = base + col*(kh*kw*in_c) + row

For simplicity this version processes one channel word per cycle.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else, Mux


# FSM states
IM2_IDLE = 0
IM2_WORK = 1
IM2_WAIT_RD = 2
IM2_WRITE = 3
IM2_DONE = 4


class Im2Col(Module):
    """Im2Col data rearrangement engine for CNN convolution."""

    def __init__(self, data_width: int = 16, addr_width: int = 16, array_size: int = 32, name: str = "Im2Col"):
        super().__init__(name)
        self.data_width = data_width
        self.addr_width = addr_width
        self.array_size = array_size

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Configuration (loaded via CONFIG instruction or similar)
        # -----------------------------------------------------------------
        self.cfg_kh = Input(4, "cfg_kh")
        self.cfg_kw = Input(4, "cfg_kw")
        self.cfg_stride_h = Input(4, "cfg_stride_h")
        self.cfg_stride_w = Input(4, "cfg_stride_w")
        self.cfg_pad_h = Input(4, "cfg_pad_h")
        self.cfg_pad_w = Input(4, "cfg_pad_w")
        self.cfg_in_h = Input(16, "cfg_in_h")
        self.cfg_in_w = Input(16, "cfg_in_w")
        self.cfg_in_c = Input(16, "cfg_in_c")
        self.cfg_out_h = Input(16, "cfg_out_h")
        self.cfg_out_w = Input(16, "cfg_out_w")
        self.cfg_src_addr = Input(addr_width, "cfg_src_addr")
        self.cfg_dst_addr = Input(addr_width, "cfg_dst_addr")

        # Control
        self.start = Input(1, "start")
        self.done = Output(1, "done")
        self.busy = Output(1, "busy")

        # SRAM source interface (read feature map)
        self.src_req_valid = Output(1, "src_req_valid")
        self.src_req_addr = Output(addr_width, "src_req_addr")
        self.src_req_we = Output(1, "src_req_we")
        self.src_resp_data = Input(data_width, "src_resp_data")
        self.src_resp_valid = Input(1, "src_resp_valid")

        # SRAM destination interface (write column matrix)
        self.dst_req_valid = Output(1, "dst_req_valid")
        self.dst_req_addr = Output(addr_width, "dst_req_addr")
        self.dst_req_wdata = Output(data_width, "dst_req_wdata")
        self.dst_req_we = Output(1, "dst_req_we")

        # -----------------------------------------------------------------
        # Internal state
        # -----------------------------------------------------------------
        self.state = Reg(3, "state")

        # Loop counters
        self.oh_r = Reg(16, "oh_r")
        self.ow_r = Reg(16, "ow_r")
        self.kh_r = Reg(4, "kh_r")
        self.kw_r = Reg(4, "kw_r")
        self.ic_r = Reg(16, "ic_r")

        # Config latches (loaded when start is asserted in IDLE)
        self.kh_l = Reg(4, "kh_l")
        self.kw_l = Reg(4, "kw_l")
        self.stride_h_l = Reg(4, "stride_h_l")
        self.stride_w_l = Reg(4, "stride_w_l")
        self.pad_h_l = Reg(4, "pad_h_l")
        self.pad_w_l = Reg(4, "pad_w_l")
        self.in_h_l = Reg(16, "in_h_l")
        self.in_w_l = Reg(16, "in_w_l")
        self.in_c_l = Reg(16, "in_c_l")
        self.out_h_l = Reg(16, "out_h_l")
        self.out_w_l = Reg(16, "out_w_l")
        self.src_addr_l = Reg(addr_width, "src_addr_l")
        self.dst_addr_l = Reg(addr_width, "dst_addr_l")

        # Derived values (combinational)
        self.ih = Wire(16, "ih")
        self.iw = Wire(16, "iw")
        self.in_bounds = Wire(1, "in_bounds")
        self.col_len = Wire(16, "col_len")
        self.out_col = Wire(32, "out_col")
        self.out_row = Wire(32, "out_row")
        self.src_rd_addr = Wire(addr_width, "src_rd_addr")
        self.dst_wr_addr = Wire(addr_width, "dst_wr_addr")

        # -----------------------------------------------------------------
        # Combinational helpers
        # -----------------------------------------------------------------
        self.ih <<= (self.oh_r * self.stride_h_l) + self.kh_r - self.pad_h_l
        self.iw <<= (self.ow_r * self.stride_w_l) + self.kw_r - self.pad_w_l
        self.in_bounds <<= (
            (self.ih >= 0) & (self.ih < self.in_h_l) &
            (self.iw >= 0) & (self.iw < self.in_w_l)
        )
        self.col_len <<= self.kh_l * self.kw_l * self.in_c_l
        self.out_col <<= (self.oh_r * self.out_w_l) + self.ow_r
        self.out_row <<= (self.kh_r * self.kw_l * self.in_c_l) + (self.kw_r * self.in_c_l) + self.ic_r
        # SRAM layout uses array_size as row stride to match systolic adapter
        self.src_rd_addr <<= self.src_addr_l + ((self.ih * self.in_w_l) + self.iw) * self.array_size + self.ic_r
        self.dst_wr_addr <<= self.dst_addr_l + (self.out_col * self.array_size) + self.out_row

        # Defaults
        self.src_req_valid <<= 0
        self.src_req_addr <<= 0
        self.src_req_we <<= 0
        self.dst_req_valid <<= 0
        self.dst_req_addr <<= 0
        self.dst_req_wdata <<= 0
        self.dst_req_we <<= 0
        self.done <<= 0
        self.busy <<= (self.state != IM2_IDLE)

        # -----------------------------------------------------------------
        # FSM Sequential Logic
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm_seq():
            with If(self.rst_n == 0):
                self.state <<= IM2_IDLE
                self.oh_r <<= 0
                self.ow_r <<= 0
                self.kh_r <<= 0
                self.kw_r <<= 0
                self.ic_r <<= 0
            with Else():
                with If(self.state == IM2_IDLE):
                    with If(self.start):
                        # Latch configuration
                        self.kh_l <<= self.cfg_kh
                        self.kw_l <<= self.cfg_kw
                        self.stride_h_l <<= self.cfg_stride_h
                        self.stride_w_l <<= self.cfg_stride_w
                        self.pad_h_l <<= self.cfg_pad_h
                        self.pad_w_l <<= self.cfg_pad_w
                        self.in_h_l <<= self.cfg_in_h
                        self.in_w_l <<= self.cfg_in_w
                        self.in_c_l <<= self.cfg_in_c
                        self.out_h_l <<= self.cfg_out_h
                        self.out_w_l <<= self.cfg_out_w
                        self.src_addr_l <<= self.cfg_src_addr
                        self.dst_addr_l <<= self.cfg_dst_addr
                        # Reset counters
                        self.oh_r <<= 0
                        self.ow_r <<= 0
                        self.kh_r <<= 0
                        self.kw_r <<= 0
                        self.ic_r <<= 0
                        self.state <<= IM2_WORK

                with If(self.state == IM2_WORK):
                    with If(self.in_bounds):
                        self.state <<= IM2_WAIT_RD
                    with Else():
                        # Padding: write zero and advance
                        self.state <<= IM2_WRITE

                with If(self.state == IM2_WAIT_RD):
                    with If(self.src_resp_valid):
                        self.state <<= IM2_WRITE

                with If(self.state == IM2_WRITE):
                    # Advance counters with direct nested-if assignments
                    with If(self.ic_r + 1 >= self.in_c_l):
                        with If(self.kw_r + 1 >= self.kw_l):
                            with If(self.kh_r + 1 >= self.kh_l):
                                with If(self.ow_r + 1 >= self.out_w_l):
                                    with If(self.oh_r + 1 >= self.out_h_l):
                                        self.state <<= IM2_DONE
                                    with Else():
                                        self.oh_r <<= self.oh_r + 1
                                        self.ow_r <<= 0
                                        self.kh_r <<= 0
                                        self.kw_r <<= 0
                                        self.ic_r <<= 0
                                        self.state <<= IM2_WORK
                                with Else():
                                    self.ow_r <<= self.ow_r + 1
                                    self.kh_r <<= 0
                                    self.kw_r <<= 0
                                    self.ic_r <<= 0
                                    self.state <<= IM2_WORK
                            with Else():
                                self.kh_r <<= self.kh_r + 1
                                self.kw_r <<= 0
                                self.ic_r <<= 0
                                self.state <<= IM2_WORK
                        with Else():
                            self.kw_r <<= self.kw_r + 1
                            self.ic_r <<= 0
                            self.state <<= IM2_WORK
                    with Else():
                        self.ic_r <<= self.ic_r + 1
                        self.state <<= IM2_WORK

                with If(self.state == IM2_DONE):
                    self.state <<= IM2_IDLE

        # -----------------------------------------------------------------
        # Output combinational
        # -----------------------------------------------------------------
        @self.comb
        def _outputs():
            with If(self.state == IM2_WORK):
                with If(~self.in_bounds):
                    # Padding: write zero directly
                    self.dst_req_valid <<= 1
                    self.dst_req_addr <<= self.dst_wr_addr
                    self.dst_req_wdata <<= 0
                    self.dst_req_we <<= 1

            with If(self.state == IM2_WAIT_RD):
                self.src_req_valid <<= 1
                self.src_req_addr <<= self.src_rd_addr
                self.src_req_we <<= 0

            with If(self.state == IM2_WRITE):
                self.dst_req_valid <<= 1
                self.dst_req_addr <<= self.dst_wr_addr
                with If(self.in_bounds):
                    self.dst_req_wdata <<= self.src_resp_data
                with Else():
                    self.dst_req_wdata <<= 0
                self.dst_req_we <<= 1

            self.done <<= (self.state == IM2_DONE)
