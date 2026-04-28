"""
GPGPU Special Function Unit (SFU)

Per-lane lookup-table-based special functions.
Uses 256-entry LUTs per function, indexed by upper 8 bits of input
(after range quantization).

Functions: SIN, COS, LOG2, EXP2, RECIP, RSQRT
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import math

from rtlgen import Module, Input, Output, Reg, Memory, Wire
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common import isa
from skills.gpgpu.common.params import GPGPUParams


def _generate_lut(func_name: str, scale: float = 256.0):
    """Generate a 256-entry LUT for the given function."""
    lut = []
    for i in range(256):
        x = (i - 128) / 16.0  # map [0,255] to [-8, 8]
        if func_name == "sin":
            y = math.sin(x)
        elif func_name == "cos":
            y = math.cos(x)
        elif func_name == "log2":
            y = math.log2(max(1e-6, x + 8.5))  # shift to positive
        elif func_name == "exp2":
            y = math.pow(2.0, x)
        elif func_name == "recip":
            y = 1.0 / max(1e-6, x + 8.5)
        elif func_name == "rsqrt":
            y = 1.0 / math.sqrt(max(1e-6, x + 8.5))
        else:
            y = 0.0
        lut.append(int(y * scale) & 0xFFFF)
    return lut


# Pre-computed LUTs
LUT_SIN = _generate_lut("sin")
LUT_COS = _generate_lut("cos")
LUT_LOG2 = _generate_lut("log2")
LUT_EXP2 = _generate_lut("exp2")
LUT_RECIP = _generate_lut("recip")
LUT_RSQRT = _generate_lut("rsqrt")


class SFULane(Module):
    """Single-lane LUT-based special function unit."""

    def __init__(self, data_width: int = 32, name: str = "SFULane"):
        super().__init__(name)
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.src = Input(data_width, "src")

        self.out_valid = Output(1, "out_valid")
        self.result = Output(data_width, "result")

        # LUT memories (256 entries, 16-bit each)
        self.lut_sin = Memory(16, 256, "lut_sin", init_file=None)
        self.lut_cos = Memory(16, 256, "lut_cos", init_file=None)
        self.lut_log2 = Memory(16, 256, "lut_log2", init_file=None)
        self.lut_exp2 = Memory(16, 256, "lut_exp2", init_file=None)
        self.lut_recip = Memory(16, 256, "lut_recip", init_file=None)
        self.lut_rsqrt = Memory(16, 256, "lut_rsqrt", init_file=None)

        for m in [self.lut_sin, self.lut_cos, self.lut_log2,
                  self.lut_exp2, self.lut_recip, self.lut_rsqrt]:
            self.add_memory(m, m.name)

        # Quantize input to 8-bit index
        self.idx = Wire(8, "idx")
        self.lut_val = Wire(16, "lut_val")

        @self.comb
        def _quantize():
            # Clip to [0, 255] after shifting
            raw = (self.src >> 8) + 128
            self.idx <<= Mux(raw > 255, 255, Mux(raw < 0, 0, raw[7:0]))

        # Select LUT based on op
        @self.comb
        def _lut_select():
            self.lut_val <<= 0
            with If(self.op == isa.SFU_SIN):
                self.lut_val <<= self.lut_sin[self.idx]
            with If(self.op == isa.SFU_COS):
                self.lut_val <<= self.lut_cos[self.idx]
            with If(self.op == isa.SFU_LOG2):
                self.lut_val <<= self.lut_log2[self.idx]
            with If(self.op == isa.SFU_EXP2):
                self.lut_val <<= self.lut_exp2[self.idx]
            with If(self.op == isa.SFU_RECIP):
                self.lut_val <<= self.lut_recip[self.idx]
            with If(self.op == isa.SFU_RSQRT):
                self.lut_val <<= self.lut_rsqrt[self.idx]

        # Pipeline registers (2-stage: quantize -> lookup)
        self.pipe_valid = [Reg(1, f"pipe_v{i}") for i in range(2)]
        self.pipe_val = [Reg(16, f"pipe_val{i}") for i in range(2)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _pipeline():
            self.pipe_valid[0] <<= self.valid
            self.pipe_val[0] <<= self.lut_val
            self.pipe_valid[1] <<= self.pipe_valid[0]
            self.pipe_val[1] <<= self.pipe_val[0]

        self.out_valid <<= self.pipe_valid[1]
        self.result <<= self.pipe_val[1]


class SFUArray(Module):
    """Array of SFU lanes — 4 shared lanes with round-robin dispatch."""

    def __init__(self, params: GPGPUParams = None, name: str = "SFUArray"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.warp_size = params.warp_size
        self.num_sfu = params.num_sfu
        self.data_width = params.data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.src = [Input(self.data_width, f"src_{i}") for i in range(self.warp_size)]

        self.out_valid = Output(1, "out_valid")
        self.result = [Output(self.data_width, f"result_{i}") for i in range(self.warp_size)]

        # Buffers
        self.req_buffer = [Reg(self.data_width, f"req_buf_{i}") for i in range(self.warp_size)]
        self.result_buffer = [Reg(self.data_width, f"res_buf_{i}") for i in range(self.warp_size)]

        # 4 SFU lanes
        self.lanes = []
        for i in range(self.num_sfu):
            lane = SFULane(self.data_width, name=f"sfu_lane_{i}")
            self.lanes.append(lane)
            setattr(self, f"sfu_lane_{i}", lane)
            lane.clk <<= self.clk
            lane.rst_n <<= self.rst_n
            lane.op <<= self.op

        # Wires to buffer lane outputs — avoids Simulator port-map Mux bug
        # when lane.result is read inside conditional seq blocks
        self.lane_result = [Wire(self.data_width, f"lane_result_{i}") for i in range(self.num_sfu)]
        self.lane_out_valid = [Wire(1, f"lane_out_valid_{i}") for i in range(self.num_sfu)]
        for i in range(self.num_sfu):
            self.lane_result[i] <<= self.lanes[i].result
            self.lane_out_valid[i] <<= self.lanes[i].out_valid

        # Control FSM
        self.state = Reg(2, "state")
        self.dispatch_cnt = Reg(3, "dispatch_cnt")
        self.wait_cnt = Reg(2, "wait_cnt")
        self.lane_tag = [Reg(5, f"lane_tag_{i}") for i in range(self.num_sfu)]

        ST_IDLE = 0
        ST_DISPATCH = 1
        ST_WAIT = 2
        ST_DONE = 3

        # Mux helper for selecting from req_buffer
        def _mux_n(items, sel):
            result = items[0]
            for i in range(1, len(items)):
                result = Mux(sel == i, items[i], result)
            return result

        # Drive lane inputs based on dispatch counter
        @self.comb
        def _drive_lanes():
            for i in range(self.num_sfu):
                lane_idx = self.dispatch_cnt * self.num_sfu + i
                lane_valid = (self.state == ST_DISPATCH) & (lane_idx < self.warp_size)
                self.lanes[i].valid <<= lane_valid
                self.lanes[i].src <<= _mux_n(self.req_buffer, lane_idx)

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                self.dispatch_cnt <<= 0
                self.wait_cnt <<= 0
                for i in range(self.num_sfu):
                    self.lane_tag[i] <<= 0
            with Else():
                # Latch inputs + start
                with If(self.state == ST_IDLE):
                    with If(self.valid):
                        self.state <<= ST_DISPATCH
                        self.dispatch_cnt <<= 0
                        self.wait_cnt <<= 0
                        for i in range(self.warp_size):
                            self.req_buffer[i] <<= self.src[i]

                with If(self.state == ST_DISPATCH):
                    # Record which thread each lane is processing
                    for i in range(self.num_sfu):
                        self.lane_tag[i] <<= self.dispatch_cnt * self.num_sfu + i
                    self.dispatch_cnt <<= self.dispatch_cnt + 1
                    with If(self.dispatch_cnt == 7):
                        self.state <<= ST_WAIT

                with If(self.state == ST_WAIT):
                    self.wait_cnt <<= self.wait_cnt + 1
                    with If(self.wait_cnt == 3):
                        self.state <<= ST_DONE

                with If(self.state == ST_DONE):
                    self.state <<= ST_IDLE

        # Collect results from lanes (unrolled to avoid Signal indexing)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _collect():
            for i in range(self.num_sfu):
                with If(self.lane_out_valid[i]):
                    tag = self.lane_tag[i]
                    for idx in range(self.warp_size):
                        with If(tag == idx):
                            self.result_buffer[idx] <<= self.lane_result[i]

        # Output assignments
        for i in range(self.warp_size):
            self.result[i] <<= self.result_buffer[i]
        self.out_valid <<= (self.state == ST_DONE)
