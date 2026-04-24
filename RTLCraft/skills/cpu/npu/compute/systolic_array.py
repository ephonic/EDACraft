"""
NeuralAccel Systolic Array

Weight-stationary 8×8 systolic array for INT16 GEMM.

Architecture:
  - ARRAY_SIZE×ARRAY_SIZE grid of ProcessingElement modules
  - Weights are pre-loaded into each PE and remain stationary
  - Activations stream in from the left, shift right each cycle
  - Partial sums flow from top to bottom, accumulating MAC results
  - Results are collected from the bottom row

Control FSM:
  IDLE → LOAD_WEIGHT → COMPUTE → DRAIN → DONE → IDLE

During LOAD_WEIGHT:
  - Weights are shifted in row-by-row from the left edge
  - Each PE captures its weight when load_en is asserted

During COMPUTE:
  - Activations are fed into the leftmost column
  - After ARRAY_SIZE cycles of skew, results start appearing at the bottom

During DRAIN:
  - Remaining partial sums flush through the array
  - Results are captured in the output buffer
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux

from skills.cpu.npu.compute.pe import ProcessingElement


# FSM states
ST_IDLE = 0
ST_LOAD_WEIGHT = 1
ST_COMPUTE = 2
ST_DRAIN = 3
ST_DONE = 4


class SystolicArray(Module):
    """Weight-stationary systolic array for matrix multiplication."""

    def __init__(self, array_size: int = 8, data_width: int = 16, acc_width: int = 32, name: str = "SystolicArray"):
        super().__init__(name)
        self.array_size = array_size
        self.data_width = data_width
        self.acc_width = acc_width
        self.size_bits = max((array_size - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control
        self.start = Input(1, "start")
        self.k_dim = Input(8, "k_dim")  # K dimension for GEMM (max 255)
        self.busy = Output(1, "busy")
        self.done = Output(1, "done")

        # Weight loading interface (left edge)
        self.weight_load_en = Input(1, "weight_load_en")
        self.weight_in = Vector(data_width, array_size, "weight_in", vtype=Input)

        # Activation input interface (left edge)
        self.act_valid = Input(1, "act_valid")
        self.act_in = Vector(data_width, array_size, "act_in", vtype=Input)

        # Result output interface (bottom edge)
        self.result_valid = Output(1, "result_valid")
        self.result_out = Vector(acc_width, array_size, "result_out", vtype=Output)

        # =====================================================================
        # PE Grid
        # =====================================================================
        self.pe = []
        for r in range(array_size):
            row = []
            for c in range(array_size):
                pe = ProcessingElement(data_width, acc_width, name=f"pe_r{r}_c{c}")
                # Register as submodule so VerilogEmitter discovers it
                setattr(self, f"pe_r{r}_c{c}", pe)
                row.append(pe)
            self.pe.append(row)

        # =====================================================================
        # FSM State
        # =====================================================================
        self.state = Reg(3, "state")
        self.cycle_cnt = Reg(8, "cycle_cnt")
        self.load_row = Reg(self.size_bits, "load_row")

        # =====================================================================
        # Connect PE clocks and common controls
        # =====================================================================
        for r in range(array_size):
            for c in range(array_size):
                self.pe[r][c].clk <<= self.clk
                self.pe[r][c].rst_n <<= self.rst_n

        # =====================================================================
        # FSM Sequential Logic
        # =====================================================================
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                self.cycle_cnt <<= 0
                self.load_row <<= 0
            with Else():
                with If(self.state == ST_IDLE):
                    with If(self.start):
                        self.state <<= ST_LOAD_WEIGHT
                        self.cycle_cnt <<= 0
                        self.load_row <<= 0

                with If(self.state == ST_LOAD_WEIGHT):
                    # Load one row per cycle
                    self.load_row <<= self.load_row + 1
                    with If(self.load_row == (array_size - 1)):
                        self.state <<= ST_COMPUTE
                        self.cycle_cnt <<= 0

                with If(self.state == ST_COMPUTE):
                    self.cycle_cnt <<= self.cycle_cnt + 1
                    # Compute for K + array_size cycles (skew + drain)
                    with If(self.cycle_cnt >= (self.k_dim + array_size - 1)):
                        self.state <<= ST_DRAIN
                        self.cycle_cnt <<= 0

                with If(self.state == ST_DRAIN):
                    self.cycle_cnt <<= self.cycle_cnt + 1
                    with If(self.cycle_cnt == (array_size - 1)):
                        self.state <<= ST_DONE

                with If(self.state == ST_DONE):
                    self.state <<= ST_IDLE

        # =====================================================================
        # Weight Loading: shift weights into leftmost column, PEs propagate right
        # =====================================================================
        @self.comb
        def _weight_load():
            for r in range(array_size):
                for c in range(array_size):
                    with If(self.state == ST_LOAD_WEIGHT):
                        # Each row loads independently; leftmost column gets external weight_in
                        with If(c == 0):
                            self.pe[r][c].load_en <<= (self.load_row == r)
                        with Else():
                            # Propagate load_en from left neighbor
                            self.pe[r][c].load_en <<= self.pe[r][c - 1].load_en
                        # Each PE loads its own column from external weight_in
                        self.pe[r][c].weight_in <<= self.weight_in[c]
                    with Else():
                        self.pe[r][c].load_en <<= 0
                        self.pe[r][c].weight_in <<= 0

        # =====================================================================
        # Compute Dataflow: activations left→right, psums top→bottom
        # =====================================================================
        @self.comb
        def _compute():
            compute_active = (self.state == ST_COMPUTE) | (self.state == ST_DRAIN)

            for r in range(array_size):
                for c in range(array_size):
                    pe = self.pe[r][c]
                    pe.valid <<= compute_active

                    # Activation: left edge gets act_in, others get from left neighbor
                    with If(c == 0):
                        pe.a_in <<= self.act_in[r]
                    with Else():
                        pe.a_in <<= self.pe[r][c - 1].a_out

                    # Partial sum: top edge gets 0, others get from top neighbor
                    with If(r == 0):
                        pe.psum_in <<= 0
                    with Else():
                        pe.psum_in <<= self.pe[r - 1][c].psum_out

        # =====================================================================
        # Result Collection: bottom row outputs
        # =====================================================================
        self.result_valid <<= (self.state == ST_COMPUTE) | (self.state == ST_DRAIN)
        for c in range(array_size):
            self.result_out[c] <<= self.pe[array_size - 1][c].psum_out

        # =====================================================================
        # Status Outputs
        # =====================================================================
        self.busy <<= (self.state != ST_IDLE)
        self.done <<= (self.state == ST_DONE)
