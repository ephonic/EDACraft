"""
NeuralAccel NPU Parameters

Reference parameter bundle for a configurable NPU accelerator.
Enhanced defaults for CNN workloads (e.g. ResNet18).
"""

from rtlgen import Parameter


class NeuralAccelParams:
    """Parameter bundle for the NeuralAccel NPU."""

    def __init__(
        self,
        array_size: int = 32,
        data_width: int = 16,
        acc_width: int = 64,
        sram_depth: int = 8192,
        num_lanes: int = 32,
        num_buffers: int = 4,
        crossbar_masters: int = 4,
        crossbar_slaves: int = 4,
    ):
        self.ARRAY_SIZE = array_size
        self.DATA_WIDTH = data_width
        self.ACC_WIDTH = acc_width
        self.SRAM_DEPTH = sram_depth
        self.NUM_LANES = num_lanes
        self.NUM_BUFFERS = num_buffers
        self.CROSSBAR_MASTERS = crossbar_masters
        self.CROSSBAR_SLAVES = crossbar_slaves

        # Derived
        self.ADDR_WIDTH = max((sram_depth - 1).bit_length(), 1)
        self.ARRAY_SIZE_BITS = max((array_size - 1).bit_length(), 1)
        self.NUM_LANES_BITS = max((num_lanes - 1).bit_length(), 1)
        self.OPCODE_WIDTH = 4
        self.FUNC_WIDTH = 4
        self.INSTR_WIDTH = 32

    def to_verilog_params(self):
        """Return list of rtlgen Parameter objects for Verilog generation."""
        return [
            Parameter(self.ARRAY_SIZE, "ARRAY_SIZE"),
            Parameter(self.DATA_WIDTH, "DATA_WIDTH"),
            Parameter(self.ACC_WIDTH, "ACC_WIDTH"),
            Parameter(self.SRAM_DEPTH, "SRAM_DEPTH"),
            Parameter(self.NUM_LANES, "NUM_LANES"),
        ]

    def to_compiler_params(self):
        """Return dict of parameters needed by the compiler."""
        return {
            "array_size": self.ARRAY_SIZE,
            "data_width": self.DATA_WIDTH,
            "acc_width": self.ACC_WIDTH,
            "sram_depth": self.SRAM_DEPTH,
            "num_lanes": self.NUM_LANES,
            "num_buffers": self.NUM_BUFFERS,
            "addr_width": self.ADDR_WIDTH,
        }
