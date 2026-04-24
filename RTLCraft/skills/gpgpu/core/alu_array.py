"""
GPGPU ALU Array —?32-lane SIMD execution unit

Instantiates 32 ALULane modules, one per thread in a warp.
All lanes share the same opcode/func but operate on independent data.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Vector
from rtlgen.logic import If

from skills.gpgpu.common.params import GPGPUParams
from skills.gpgpu.core.alu_lane import ALULane


class ALUArray(Module):
    """32-lane ALU array for SIMT execution."""

    def __init__(self, params: GPGPUParams = None, name: str = "ALUArray"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.num_lanes = params.alu_lanes
        self.data_width = params.data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control (broadcast to all lanes)
        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.shift_amt = Input(5, "shift_amt")

        # Per-lane operands (Vector of width data_width, depth num_lanes)
        self.src_a = Vector(self.data_width, self.num_lanes, "src_a", vtype=Input)
        self.src_b = Vector(self.data_width, self.num_lanes, "src_b", vtype=Input)
        self.src_c = Vector(self.data_width, self.num_lanes, "src_c", vtype=Input)

        # Per-lane predicate mask (input —?used by caller for writeback gating)
        self.pred_mask = Input(self.num_lanes, "pred_mask")

        # Outputs
        self.out_valid = Output(1, "out_valid")
        self.result = Vector(self.data_width, self.num_lanes, "result", vtype=Output)
        self.pred_out = Output(self.num_lanes, "pred_out")

        # -----------------------------------------------------------------
        # Instantiate ALU lanes
        # -----------------------------------------------------------------
        self.lanes = []
        for i in range(self.num_lanes):
            lane = ALULane(self.data_width, name=f"alu_lane_{i}")
            self.lanes.append(lane)
            setattr(self, f"alu_lane_{i}", lane)

            lane.clk <<= self.clk
            lane.rst_n <<= self.rst_n
            lane.valid <<= self.valid
            lane.op <<= self.op
            lane.shift_amt <<= self.shift_amt
            lane.src_a <<= self.src_a[i]
            lane.src_b <<= self.src_b[i]
            lane.src_c <<= self.src_c[i]

            self.result[i] <<= lane.result
            self.pred_out[i] <<= lane.pred_out

        # All lanes share the same out_valid (they are lockstep)
        self.out_valid <<= self.lanes[0].out_valid
