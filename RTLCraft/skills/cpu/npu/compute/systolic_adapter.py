"""
SystolicDataAdapter — bridges scalar SRAM to wide systolic array

Buffers weight and activation matrices from SRAM, streams them into
the SystolicArray, captures results, and writes them back.

SRAM width = DATA_WIDTH (16b).  Systolic width = ARRAY_SIZE × DATA_WIDTH.
Results are truncated from ACC_WIDTH down to DATA_WIDTH on write-back.

FSM:
  IDLE → RD_WEIGHT → RD_ACT → RUN → WR_RESULT → DONE → IDLE

Assumes k_dim ≤ ARRAY_SIZE for simplicity.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector, Memory
from rtlgen.logic import If, Else, Mux


# FSM states
ST_IDLE = 0
ST_RD_WEIGHT = 1
ST_RD_ACT = 2
ST_RUN = 3
ST_WR_RESULT = 4
ST_DONE = 5


class SystolicDataAdapter(Module):
    """Scalar-SRAM to systolic-array bridge."""

    def __init__(
        self,
        array_size: int = 8,
        data_width: int = 16,
        acc_width: int = 32,
        addr_width: int = 13,
        name: str = "SystolicDataAdapter",
    ):
        super().__init__(name)
        self.array_size = array_size
        self.data_width = data_width
        self.acc_width = acc_width
        self.addr_width = addr_width
        self.buf_depth = array_size * array_size
        self.buf_addr_width = max((self.buf_depth - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Control
        # -----------------------------------------------------------------
        self.start = Input(1, "start")
        self.k_dim = Input(8, "k_dim")
        self.weight_base_addr = Input(addr_width, "weight_base_addr")
        self.act_base_addr = Input(addr_width, "act_base_addr")
        self.result_base_addr = Input(addr_width, "result_base_addr")
        self.done = Output(1, "done")

        # -----------------------------------------------------------------
        # Weight SRAM read interface  (→ SRAM_A)
        # -----------------------------------------------------------------
        self.weight_req_valid = Output(1, "weight_req_valid")
        self.weight_req_addr = Output(addr_width, "weight_req_addr")
        self.weight_resp_data = Input(data_width, "weight_resp_data")
        self.weight_resp_valid = Input(1, "weight_resp_valid")

        # -----------------------------------------------------------------
        # Activation SRAM read interface (→ SRAM_B)
        # -----------------------------------------------------------------
        self.act_req_valid = Output(1, "act_req_valid")
        self.act_req_addr = Output(addr_width, "act_req_addr")
        self.act_resp_data = Input(data_width, "act_resp_data")
        self.act_resp_valid = Input(1, "act_resp_valid")

        # -----------------------------------------------------------------
        # Result SRAM write interface (→ SRAM_C)
        # -----------------------------------------------------------------
        self.result_wr_valid = Output(1, "result_wr_valid")
        self.result_wr_addr = Output(addr_width, "result_wr_addr")
        self.result_wr_data = Output(data_width, "result_wr_data")
        self.result_wr_we = Output(1, "result_wr_we")

        # -----------------------------------------------------------------
        # Systolic control & data
        # -----------------------------------------------------------------
        self.systolic_start = Output(1, "systolic_start")
        self.systolic_k_dim = Output(8, "systolic_k_dim")
        self.systolic_done = Input(1, "systolic_done")

        self.weight_load_en = Output(1, "weight_load_en")
        self.weight_out = Vector(data_width, array_size, "weight_out", vtype=Output)

        self.act_valid = Output(1, "act_valid")
        self.act_out = Vector(data_width, array_size, "act_out", vtype=Output)

        self.result_valid = Input(1, "result_valid")
        self.result_in = Vector(acc_width, array_size, "result_in", vtype=Input)

        # -----------------------------------------------------------------
        # Internal buffers
        # -----------------------------------------------------------------
        self.weight_buf = Memory(data_width, self.buf_depth, "weight_buf")
        self.act_buf = Memory(data_width, self.buf_depth, "act_buf")
        self.result_buf = Memory(data_width, self.buf_depth, "result_buf")
        self.add_memory(self.weight_buf, "weight_buf")
        self.add_memory(self.act_buf, "act_buf")
        self.add_memory(self.result_buf, "result_buf")

        # -----------------------------------------------------------------
        # FSM & counters
        # -----------------------------------------------------------------
        self.state = Reg(3, "state")
        self.rd_ptr = Reg(self.buf_addr_width, "rd_ptr")
        self.wr_ptr = Reg(self.buf_addr_width, "wr_ptr")
        self.run_cnt = Reg(16, "run_cnt")
        self.k_dim_r = Reg(8, "k_dim_r")

        # -----------------------------------------------------------------
        # Combinational: SRAM request defaults
        # -----------------------------------------------------------------
        self.weight_req_valid <<= (self.state == ST_RD_WEIGHT) & (self.rd_ptr < (self.k_dim_r * array_size))
        self.weight_req_addr <<= self.weight_base_addr + self.rd_ptr

        self.act_req_valid <<= (self.state == ST_RD_ACT) & (self.rd_ptr < (self.k_dim_r * array_size))
        self.act_req_addr <<= self.act_base_addr + self.rd_ptr

        self.result_wr_valid <<= (self.state == ST_WR_RESULT) & (self.wr_ptr < (self.k_dim_r * array_size))
        self.result_wr_we <<= self.result_wr_valid
        self.result_wr_addr <<= self.result_base_addr + self.wr_ptr
        self.result_wr_data <<= self.result_buf[self.wr_ptr]

        # -----------------------------------------------------------------
        # Combinational: systolic data outputs
        # -----------------------------------------------------------------
        self.systolic_start <<= (self.state == ST_RUN) & (self.run_cnt == 0)
        self.systolic_k_dim <<= self.k_dim_r

        self.weight_load_en <<= (self.state == ST_RUN) & (self.run_cnt < array_size)
        self.act_valid <<= (self.state == ST_RUN) & (self.run_cnt >= (array_size + 1)) & (self.run_cnt < (array_size + 1 + self.k_dim_r))

        @self.comb
        def _drive_systolic_data():
            for r in range(array_size):
                with If(self.state == ST_RUN):
                    # Weight loading: systolic enters LOAD_WEIGHT one cycle after start,
                    # so weight_out is delayed by 1 run_cnt to align with systolic's load_row
                    with If(self.run_cnt == 0):
                        self.weight_out[r] <<= 0
                    with If((self.run_cnt > 0) & (self.run_cnt <= array_size)):
                        self.weight_out[r] <<= self.weight_buf[(self.run_cnt - 1) * array_size + r]
                    with Else():
                        self.weight_out[r] <<= 0

                    # Activation streaming with row skew: row r is delayed by r cycles
                    # to align with systolic array propagation delay
                    with If((self.run_cnt >= (array_size + 1 + r)) & (self.run_cnt < (array_size + 1 + r + self.k_dim_r))):
                        self.act_out[r] <<= self.act_buf[(self.run_cnt - array_size - 1 - r) * array_size + r]
                    with Else():
                        self.act_out[r] <<= 0
                with Else():
                    self.weight_out[r] <<= 0
                    self.act_out[r] <<= 0

        # -----------------------------------------------------------------
        # Sequential: FSM, buffer fill, result capture
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                self.rd_ptr <<= 0
                self.wr_ptr <<= 0
                self.run_cnt <<= 0
            with Else():
                with If(self.state == ST_IDLE):
                    with If(self.start):
                        self.state <<= ST_RD_WEIGHT
                        self.k_dim_r <<= self.k_dim
                        self.rd_ptr <<= 0
                        self.wr_ptr <<= 0

                with If(self.state == ST_RD_WEIGHT):
                    self.rd_ptr <<= self.rd_ptr + 1
                    with If(self.weight_resp_valid):
                        self.weight_buf[self.wr_ptr] <<= self.weight_resp_data
                        self.wr_ptr <<= self.wr_ptr + 1
                    with If(self.wr_ptr == (self.k_dim_r * array_size)):
                        self.state <<= ST_RD_ACT
                        self.rd_ptr <<= 0
                        self.wr_ptr <<= 0

                with If(self.state == ST_RD_ACT):
                    self.rd_ptr <<= self.rd_ptr + 1
                    with If(self.act_resp_valid):
                        self.act_buf[self.wr_ptr] <<= self.act_resp_data
                        self.wr_ptr <<= self.wr_ptr + 1
                    with If(self.wr_ptr == (self.k_dim_r * array_size)):
                        self.state <<= ST_RUN
                        self.run_cnt <<= 0
                        self.rd_ptr <<= 0
                        self.wr_ptr <<= 0

                with If(self.state == ST_RUN):
                    self.run_cnt <<= self.run_cnt + 1

                    # Capture result rows after systolic array has finished computing
                    # and is draining results (all psums have propagated to bottom)
                    drain_start = array_size + array_size + 2
                    for c in range(array_size):
                        with If(
                            self.result_valid
                            & (self.run_cnt >= (drain_start + c))
                            & (self.run_cnt < (drain_start + c + self.k_dim_r))
                        ):
                            row_idx = self.run_cnt - (drain_start + c)
                            # Truncate accumulator to data_width
                            self.result_buf[row_idx * array_size + c] <<= self.result_in[c][self.data_width - 1 : 0]

                    with If(self.systolic_done):
                        self.state <<= ST_WR_RESULT
                        self.wr_ptr <<= 0

                with If(self.state == ST_WR_RESULT):
                    self.wr_ptr <<= self.wr_ptr + 1
                    with If(self.wr_ptr == ((self.k_dim_r * array_size) - 1)):
                        self.state <<= ST_DONE

                with If(self.state == ST_DONE):
                    self.state <<= ST_IDLE

        self.done <<= (self.state == ST_DONE)
