"""
NeuralAccel Pooling Engine

Hardware pooling unit for MaxPool and AvgPool operations.

Architecture:
  - Sequential window processing (one 16-bit element per cycle)
  - Per-channel reduction: for each output position (oh, ow, ic),
    accumulates over the kh x kw window.
  - MAX mode: tracks running maximum
  - AVG mode: accumulates sum, then right-shifts by div_shift

Data layout (assumed CHW-like):
  src_addr = base + ((ih * in_w) + iw) * in_c + ic
  dst_addr = base + ((oh * out_w) + ow) * out_c + ic

Timing: ~kh*kw cycles per output element (plus SRAM latency).
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else, Mux


# FSM states
POOL_IDLE = 0
POOL_WORK = 1
POOL_WAIT_RD = 2
POOL_ACC = 3
POOL_WRITE = 4
POOL_DONE = 5

# Pool types
POOL_MAX = 0
POOL_AVG = 1


class PoolEngine(Module):
    """Hardware pooling engine for 2D MAX/AVG pooling."""

    def __init__(self, data_width: int = 16, addr_width: int = 16, name: str = "PoolEngine"):
        super().__init__(name)
        self.data_width = data_width
        self.addr_width = addr_width
        # Accumulator width: enough for kh*kw * max_int16 (max 9 * 32767 < 2^19)
        self.acc_width = 32

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Configuration
        # -----------------------------------------------------------------
        self.cfg_pool_type = Input(1, "cfg_pool_type")  # 0=MAX, 1=AVG
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
        self.cfg_div_shift = Input(4, "cfg_div_shift")  # for AVG: right shift amount
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

        # SRAM destination interface (write pooled output)
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

        # Config latches
        self.pool_type_l = Reg(1, "pool_type_l")
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
        self.div_shift_l = Reg(4, "div_shift_l")
        self.src_addr_l = Reg(addr_width, "src_addr_l")
        self.dst_addr_l = Reg(addr_width, "dst_addr_l")

        # Accumulator
        self.acc = Reg(self.acc_width, "acc")

        # Saved write address (latched when window completes)
        self.wr_addr_r = Reg(addr_width, "wr_addr_r")

        # Derived combinational
        self.ih = Wire(16, "ih")
        self.iw = Wire(16, "iw")
        self.in_bounds = Wire(1, "in_bounds")
        self.src_rd_addr = Wire(addr_width, "src_rd_addr")
        self.dst_wr_addr = Wire(addr_width, "dst_wr_addr")
        self.out_data = Wire(data_width, "out_data")

        # -----------------------------------------------------------------
        # Combinational helpers
        # -----------------------------------------------------------------
        self.ih <<= (self.oh_r * self.stride_h_l) + self.kh_r - self.pad_h_l
        self.iw <<= (self.ow_r * self.stride_w_l) + self.kw_r - self.pad_w_l
        self.in_bounds <<= (
            (self.ih >= 0) & (self.ih < self.in_h_l) &
            (self.iw >= 0) & (self.iw < self.in_w_l)
        )
        self.src_rd_addr <<= self.src_addr_l + (((self.ih * self.in_w_l) + self.iw) * self.in_c_l) + self.ic_r
        self.dst_wr_addr <<= self.dst_addr_l + (((self.oh_r * self.out_w_l) + self.ow_r) * self.in_c_l) + self.ic_r

        # AVG output: acc >> div_shift; MAX output: acc clipped to data_width
        self.out_data <<= Mux(
            self.pool_type_l == POOL_AVG,
            (self.acc >> self.div_shift_l)[self.data_width - 1:0],
            self.acc[self.data_width - 1:0]
        )

        # Defaults
        self.src_req_valid <<= 0
        self.src_req_addr <<= 0
        self.src_req_we <<= 0
        self.dst_req_valid <<= 0
        self.dst_req_addr <<= 0
        self.dst_req_wdata <<= 0
        self.dst_req_we <<= 0
        self.done <<= 0
        self.busy <<= (self.state != POOL_IDLE)

        # -----------------------------------------------------------------
        # FSM Sequential Logic
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm_seq():
            with If(self.rst_n == 0):
                self.state <<= POOL_IDLE
                self.oh_r <<= 0
                self.ow_r <<= 0
                self.kh_r <<= 0
                self.kw_r <<= 0
                self.ic_r <<= 0
                self.acc <<= 0
            with Else():
                with If(self.state == POOL_IDLE):
                    with If(self.start):
                        # Latch configuration
                        self.pool_type_l <<= self.cfg_pool_type
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
                        self.div_shift_l <<= self.cfg_div_shift
                        self.src_addr_l <<= self.cfg_src_addr
                        self.dst_addr_l <<= self.cfg_dst_addr
                        # Reset counters
                        self.oh_r <<= 0
                        self.ow_r <<= 0
                        self.kh_r <<= 0
                        self.kw_r <<= 0
                        self.ic_r <<= 0
                        # Init accumulator
                        with If(self.cfg_pool_type == POOL_MAX):
                            self.acc <<= 0  # Will be compared using offset trick
                        with Else():
                            self.acc <<= 0
                        self.state <<= POOL_WORK

                with If(self.state == POOL_WORK):
                    with If(self.in_bounds):
                        self.state <<= POOL_WAIT_RD
                    with Else():
                        # Padding: skip this position
                        with If(self.kw_r + 1 >= self.kw_l):
                            with If(self.kh_r + 1 >= self.kh_l):
                                with If(self.ow_r + 1 >= self.out_w_l):
                                    with If(self.oh_r + 1 >= self.out_h_l):
                                        with If(self.ic_r + 1 >= self.in_c_l):
                                            self.state <<= POOL_DONE
                                        with Else():
                                            self.ic_r <<= self.ic_r + 1
                                            self.oh_r <<= 0
                                            self.ow_r <<= 0
                                            self.kh_r <<= 0
                                            self.kw_r <<= 0
                                            self.state <<= POOL_WRITE
                                    with Else():
                                        self.oh_r <<= self.oh_r + 1
                                        self.ow_r <<= 0
                                        self.kh_r <<= 0
                                        self.kw_r <<= 0
                                        self.state <<= POOL_WRITE
                                with Else():
                                    self.ow_r <<= self.ow_r + 1
                                    self.kh_r <<= 0
                                    self.kw_r <<= 0
                                    self.state <<= POOL_WRITE
                            with Else():
                                self.kh_r <<= self.kh_r + 1
                                self.kw_r <<= 0
                                self.state <<= POOL_WORK
                        with Else():
                            self.kw_r <<= self.kw_r + 1
                            self.state <<= POOL_WORK

                with If(self.state == POOL_WAIT_RD):
                    with If(self.src_resp_valid):
                        self.state <<= POOL_ACC

                with If(self.state == POOL_ACC):
                    # Update accumulator with fetched data
                    with If(self.pool_type_l == POOL_MAX):
                        # Use XOR-with-MSB trick for unsigned comparison of signed values
                        offset_msb = 1 << (self.data_width - 1)
                        a_offset = self.src_resp_data ^ offset_msb
                        b_offset = self.acc[self.data_width - 1:0] ^ offset_msb
                        self.acc <<= Mux(a_offset > b_offset, self.src_resp_data, self.acc[self.data_width - 1:0])
                    with Else():
                        self.acc <<= self.acc + self.src_resp_data

                    # Advance counters and check window completion
                    with If(self.kw_r + 1 >= self.kw_l):
                        with If(self.kh_r + 1 >= self.kh_l):
                            # Window done: latch write address and go to WRITE
                            # Do NOT advance spatial counters here; WRITE will do it
                            self.wr_addr_r <<= self.dst_wr_addr
                            self.state <<= POOL_WRITE
                        with Else():
                            self.kh_r <<= self.kh_r + 1
                            self.kw_r <<= 0
                            self.state <<= POOL_WORK
                    with Else():
                        self.kw_r <<= self.kw_r + 1
                        self.state <<= POOL_WORK

                with If(self.state == POOL_WRITE):
                    # Advance to next window and reset accumulator
                    with If(self.ow_r + 1 >= self.out_w_l):
                        with If(self.oh_r + 1 >= self.out_h_l):
                            with If(self.ic_r + 1 >= self.in_c_l):
                                self.state <<= POOL_DONE
                            with Else():
                                self.ic_r <<= self.ic_r + 1
                                self.oh_r <<= 0
                                self.ow_r <<= 0
                                self.kh_r <<= 0
                                self.kw_r <<= 0
                                self.state <<= POOL_WORK
                        with Else():
                            self.oh_r <<= self.oh_r + 1
                            self.ow_r <<= 0
                            self.kh_r <<= 0
                            self.kw_r <<= 0
                            self.state <<= POOL_WORK
                    with Else():
                        self.ow_r <<= self.ow_r + 1
                        self.kh_r <<= 0
                        self.kw_r <<= 0
                        self.state <<= POOL_WORK

                    # Reset accumulator for next window
                    self.acc <<= 0

                with If(self.state == POOL_DONE):
                    self.state <<= POOL_IDLE

        # -----------------------------------------------------------------
        # Output combinational
        # -----------------------------------------------------------------
        @self.comb
        def _outputs():
            with If(self.state == POOL_WAIT_RD):
                self.src_req_valid <<= 1
                self.src_req_addr <<= self.src_rd_addr
                self.src_req_we <<= 0

            with If(self.state == POOL_WRITE):
                self.dst_req_valid <<= 1
                self.dst_req_addr <<= self.wr_addr_r
                self.dst_req_wdata <<= self.out_data
                self.dst_req_we <<= 1

            self.done <<= (self.state == POOL_DONE)
