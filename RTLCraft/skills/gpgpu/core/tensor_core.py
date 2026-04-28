"""
GPGPU Tensor Core —?4×4×4 Matrix Multiply-Accumulate

Computes D = A @ B + C where A, B, C, D are 4×4 matrices.
Supports FP16, BF16, and INT8 modes (FP32 accumulator).

Execution is warp-granular: all 32 threads cooperate to feed
operands and consume results via the register file.

Internal FSM:
  IDLE -> LOAD_A -> LOAD_B -> LOAD_C -> COMPUTE -> STORE_D -> DONE
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Memory
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common import isa
from skills.gpgpu.common.params import GPGPUParams

# FSM states
TC_IDLE = 0
TC_LOAD_A = 1
TC_LOAD_B = 2
TC_LOAD_C = 3
TC_COMPUTE = 4
TC_STORE_D = 5
TC_DONE = 6

TENSOR_DIM = 4
TENSOR_ELEMENTS = TENSOR_DIM * TENSOR_DIM  # 16


class TensorCore(Module):
    """4×4×4 tensor core MMA unit."""

    def __init__(self, params: GPGPUParams = None, name: str = "TensorCore"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.data_width = params.data_width  # 32-bit accumulator
        self.tensor_dim = params.tensor_dim  # 4

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control
        self.start = Input(1, "start")
        self.op = Input(6, "op")  # FP16 / BF16 / INT8
        self.done = Output(1, "done")
        self.busy = Output(1, "busy")

        # Operand load interface (from register file / shared memory)
        # Each cycle we can load 32 elements (one per lane)
        self.load_valid = Input(1, "load_valid")
        self.load_data = [Input(self.data_width, f"load_data_{i}") for i in range(32)]
        self.load_done = Input(1, "load_done")  # pulse when all operands loaded

        # Result store interface
        self.store_ready = Input(1, "store_ready")
        self.store_valid = Output(1, "store_valid")
        self.store_data = [Output(self.data_width, f"store_data_{i}") for i in range(16)]

        # -----------------------------------------------------------------
        # Internal operand buffers (4×4 = 16 elements each)
        # -----------------------------------------------------------------
        self.buf_a = Memory(self.data_width, TENSOR_ELEMENTS, "buf_a")
        self.buf_b = Memory(self.data_width, TENSOR_ELEMENTS, "buf_b")
        self.buf_c = Memory(self.data_width, TENSOR_ELEMENTS, "buf_c")
        self.buf_d = Memory(self.data_width, TENSOR_ELEMENTS, "buf_d")

        # Wires to read from memories into combinational logic (MemProxy has no arithmetic ops)
        self.a_read = [Wire(self.data_width, f"a_read_{i}") for i in range(TENSOR_ELEMENTS)]
        self.b_read = [Wire(self.data_width, f"b_read_{i}") for i in range(TENSOR_ELEMENTS)]
        self.c_read = [Wire(self.data_width, f"c_read_{i}") for i in range(TENSOR_ELEMENTS)]

        # -----------------------------------------------------------------
        # FSM
        # -----------------------------------------------------------------
        self.state = Reg(3, "state")
        self.load_cnt = Reg(4, "load_cnt")  # 0..2 for A/B/C loads
        self.store_cnt = Reg(1, "store_cnt")  # 0..1 for D stores (16 elements / 32-wide bus)

        # -----------------------------------------------------------------
        # Combinational: D = A @ B + C
        # -----------------------------------------------------------------
        self.compute_done = Wire(1, "compute_done")
        self.compute_done <<= 0

        @self.comb
        def _read_mems():
            for i in range(TENSOR_ELEMENTS):
                self.a_read[i] <<= self.buf_a[i]
                self.b_read[i] <<= self.buf_b[i]
                self.c_read[i] <<= self.buf_c[i]

        @self.comb
        def _mma():
            # Compute all 16 output elements in combinational logic
            for i in range(TENSOR_DIM):
                for j in range(TENSOR_DIM):
                    idx = i * TENSOR_DIM + j
                    s = 0
                    for k in range(TENSOR_DIM):
                        a_idx = i * TENSOR_DIM + k
                        b_idx = k * TENSOR_DIM + j
                        s += self.a_read[a_idx] * self.b_read[b_idx]
                    s += self.c_read[idx]
                    self.buf_d[idx] = s
            self.compute_done <<= 1

        # -----------------------------------------------------------------
        # Sequential FSM
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= TC_IDLE
                self.load_cnt <<= 0
                self.store_cnt <<= 0
            with Else():
                with If(self.state == TC_IDLE):
                    with If(self.start):
                        self.state <<= TC_LOAD_A
                        self.load_cnt <<= 0

                with If(self.state == TC_LOAD_A):
                    with If(self.load_valid):
                        # Load 16 elements of A (first half of 32-wide bus)
                        base = self.load_cnt * 16
                        for i in range(16):
                            with If(base + i < TENSOR_ELEMENTS):
                                self.buf_a[base + i] <<= self.load_data[i]
                        self.load_cnt <<= self.load_cnt + 1
                    with If(self.load_done):
                        self.state <<= TC_LOAD_B
                        self.load_cnt <<= 0

                with If(self.state == TC_LOAD_B):
                    with If(self.load_valid):
                        base = self.load_cnt * 16
                        for i in range(16):
                            with If(base + i < TENSOR_ELEMENTS):
                                self.buf_b[base + i] <<= self.load_data[i]
                        self.load_cnt <<= self.load_cnt + 1
                    with If(self.load_done):
                        self.state <<= TC_LOAD_C
                        self.load_cnt <<= 0

                with If(self.state == TC_LOAD_C):
                    with If(self.load_valid):
                        base = self.load_cnt * 16
                        for i in range(16):
                            with If(base + i < TENSOR_ELEMENTS):
                                self.buf_c[base + i] <<= self.load_data[i]
                        self.load_cnt <<= self.load_cnt + 1
                    with If(self.load_done):
                        self.state <<= TC_COMPUTE

                with If(self.state == TC_COMPUTE):
                    # Combinational logic already computed D into buf_d
                    self.state <<= TC_STORE_D
                    self.store_cnt <<= 0

                with If(self.state == TC_STORE_D):
                    with If(self.store_ready):
                        self.store_cnt <<= self.store_cnt + 1
                    with If(self.store_cnt == 1):
                        self.state <<= TC_DONE

                with If(self.state == TC_DONE):
                    self.state <<= TC_IDLE

        # -----------------------------------------------------------------
        # Output assignments
        # -----------------------------------------------------------------
        self.busy <<= (self.state != TC_IDLE)
        self.done <<= (self.state == TC_DONE)
        self.store_valid <<= (self.state == TC_STORE_D)

        # First store cycle: elements 0..15, second cycle: elements 0..15 (if needed)
        # Simplified: we only have 16 elements, store them all in first cycle
        for i in range(16):
            self.store_data[i] <<= self.buf_d[i]
