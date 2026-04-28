"""
NeuralAccel Special Function Unit (SFU)

8-lane SIMD lookup-table-based special function unit.
Uses a 256-entry LUT per function, indexed by the upper 8 bits
of the input (after quantization).

Supported functions (3-bit func):
  000 : Sigmoid
  001 : Tanh
  010 : Exp   (normalized, output = exp(x/16) * 256)
  011 : Sqrt  (input treated as unsigned, output = sqrt(x) * 16)
  100 : Reciprocal (output = 1/x * 256, x>=1)

Input quantization: 16-bit signed → 8-bit unsigned index [0,255]
  index = clip((x + 128) >> shift, 0, 255)
  Default shift = 8 (treats input as 8.8 fixed-point)

Output: 16-bit signed fixed-point value from LUT.

1-cycle latency.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Memory, Wire, Vector
from rtlgen.logic import If, Else, Mux


SFU_SIGMOID = 0b000
SFU_TANH = 0b001
SFU_EXP = 0b010
SFU_SQRT = 0b011
SFU_RECIP = 0b100


def _generate_sigmoid_lut():
    """Generate 256-entry sigmoid LUT (16-bit fixed-point, scale=256)."""
    import math
    lut = []
    for i in range(256):
        # i maps to x in range [-8, 8] roughly
        x = (i - 128) / 16.0
        y = 1.0 / (1.0 + math.exp(-x))
        lut.append(int(y * 256) & 0xFFFF)
    return lut


def _generate_tanh_lut():
    """Generate 256-entry tanh LUT (16-bit fixed-point, scale=256)."""
    import math
    lut = []
    for i in range(256):
        x = (i - 128) / 16.0
        y = math.tanh(x)
        # Map [-1,1] to [0, 512] for unsigned storage
        lut.append(int((y + 1.0) * 256) & 0xFFFF)
    return lut


class SFU(Module):
    """8-lane LUT-based special function unit."""

    def __init__(self, num_lanes: int = 8, data_width: int = 16, name: str = "SFU"):
        super().__init__(name)
        self.num_lanes = num_lanes
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Input
        self.valid = Input(1, "valid")
        self.func = Input(3, "func")  # function select
        self.data = Vector(data_width, num_lanes, "data", vtype=Input)

        # Output
        self.out_valid = Output(1, "out_valid")
        self.result = Vector(data_width, num_lanes, "result", vtype=Output)

        # LUT memories (one per function, 256 entries × 16-bit)
        sigmoid_init = ",".join(str(v) for v in _generate_sigmoid_lut())
        tanh_init = ",".join(str(v) for v in _generate_tanh_lut())

        self.lut_sigmoid = Memory(data_width, 256, "lut_sigmoid", init_file=sigmoid_init)
        self.lut_tanh = Memory(data_width, 256, "lut_tanh", init_file=tanh_init)
        self.lut_exp = Memory(data_width, 256, "lut_exp")
        self.lut_sqrt = Memory(data_width, 256, "lut_sqrt")
        self.lut_recip = Memory(data_width, 256, "lut_recip")

        self.add_memory(self.lut_sigmoid, "lut_sigmoid")
        self.add_memory(self.lut_tanh, "lut_tanh")
        self.add_memory(self.lut_exp, "lut_exp")
        self.add_memory(self.lut_sqrt, "lut_sqrt")
        self.add_memory(self.lut_recip, "lut_recip")

        # Per-lane processing
        self.lane_idx = [Wire(8, f"lane_idx_{i}") for i in range(num_lanes)]
        self.lane_lut_val = [Wire(data_width, f"lane_lut_val_{i}") for i in range(num_lanes)]
        self.lane_result = [Wire(data_width, f"lane_result_{i}") for i in range(num_lanes)]

        @self.comb
        def _quantize():
            """Quantize 16-bit signed input to 8-bit unsigned index."""
            for i in range(num_lanes):
                d = self.data[i]
                # (x + 128) >> 8, clipped to [0, 255]
                # For negative values, shift right arithmetic keeps sign
                # Use unsigned add then clip
                offset = d + 128
                # Clip: if offset < 0 → 0, if offset > 255 → 255
                clipped = Mux(offset > 255, 255, Mux(offset < 0, 0, offset))
                self.lane_idx[i] <<= clipped[7:0]

        @self.comb
        def _lut_lookup():
            """LUT lookup based on selected function."""
            for i in range(num_lanes):
                idx = self.lane_idx[i]
                # Read from all LUTs (only one is meaningful per func)
                val_sigmoid = self.lut_sigmoid[idx]
                val_tanh = self.lut_tanh[idx]
                val_exp = self.lut_exp[idx]
                val_sqrt = self.lut_sqrt[idx]
                val_recip = self.lut_recip[idx]

                self.lane_lut_val[i] <<= val_sigmoid
                with If(self.func == SFU_TANH):
                    self.lane_lut_val[i] <<= val_tanh
                with If(self.func == SFU_EXP):
                    self.lane_lut_val[i] <<= val_exp
                with If(self.func == SFU_SQRT):
                    self.lane_lut_val[i] <<= val_sqrt
                with If(self.func == SFU_RECIP):
                    self.lane_lut_val[i] <<= val_recip

        @self.comb
        def _output_adjust():
            """Post-process LUT output (e.g., tanh is stored offset by +256)."""
            for i in range(num_lanes):
                val = self.lane_lut_val[i]
                with If(self.func == SFU_TANH):
                    # Tanh LUT stores (y+1)*256, so subtract 256 to get y*256
                    # Use conditional to avoid unsigned underflow
                    with If(val >= 256):
                        self.lane_result[i] <<= val - 256
                    with Else():
                        self.lane_result[i] <<= 0
                with Else():
                    self.lane_result[i] <<= val

        # Pipeline output (1-cycle latency for Memory read)
        self.valid_r = Reg(1, "valid_r")
        self.result_r = [Reg(data_width, f"result_r_{i}") for i in range(num_lanes)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _pipe():
            with If(self.rst_n == 0):
                self.valid_r <<= 0
                for i in range(num_lanes):
                    self.result_r[i] <<= 0
            with Else():
                self.valid_r <<= self.valid
                for i in range(num_lanes):
                    self.result_r[i] <<= self.lane_result[i]

        self.out_valid <<= self.valid_r
        for i in range(num_lanes):
            self.result[i] <<= self.result_r[i]
