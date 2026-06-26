"""Thor GPU — Tensor Core L3 DSL. 4x4x4 FP16 matrix multiply-accumulate.
D = A × B + C  (all matrices 4×4, FP16 elements)

5-stage pipeline:
  Stage 0: input capture
  Stage 1-2: partial products (multiply)
  Stage 3: reduction sum
  Stage 4: accumulation with C, output
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Elif, Else, ForGen

from skills.thor import FLEN


class TensorCore(Module):
    def __init__(self, name="tensor_core", latency=5):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.a00 = Input(16, "a00"); self.a01 = Input(16, "a01")
        self.a02 = Input(16, "a02"); self.a03 = Input(16, "a03")
        self.b00 = Input(16, "b00"); self.b10 = Input(16, "b10")
        self.b20 = Input(16, "b20"); self.b30 = Input(16, "b30")
        self.c0 = Input(16, "c0")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.d0 = Output(16, "d0"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")

        self._pv = [Reg(1, f"tc_pv_{i}") for i in range(latency)]
        # Pipeline data (partial sums across stages)
        self._pp = [Reg(32, f"tc_pp_{i}") for i in range(3)]
        self._p0 = [Reg(16, f"tc_p0_{i}") for i in range(4)]

        with self.comb:
            self.in_ready <<= (self._pv[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(latency): self._pv[i] <<= 0
                for i in range(3): self._pp[i] <<= 0
                for i in range(4): self._p0[i] <<= 0
            with Else():
                s0 = self.in_valid & self.in_ready
                with If(s0):
                    # Stage 0: partial products a0i * bi0
                    self._p0[0] <<= self.a00 * self.b00
                    self._p0[1] <<= self.a01 * self.b10
                    self._p0[2] <<= self.a02 * self.b20
                    self._p0[3] <<= self.a03 * self.b30
                    self._pv[0] <<= 1
                with Elif(self._pv[0] & self.out_ready):
                    self._pv[0] <<= 0

                for i in range(1, 3):
                    take = self._pv[i - 1] & ((self._pv[i] == 0) | self.out_ready)
                    with If(take):
                        # Stage 1-2: sum partial products pairwise
                        if i == 1:
                            self._pp[0] <<= (self._p0[0] + self._p0[1]) & 0xFFFFFFFF
                            self._pp[1] <<= (self._p0[2] + self._p0[3]) & 0xFFFFFFFF
                        else:
                            self._pp[2] <<= (self._pp[0] + self._pp[1]) & 0xFFFFFFFF
                        self._pv[i] <<= self._pv[i - 1]
                        self._pv[i - 1] <<= 0

                for i in range(3, latency):
                    take = self._pv[i - 1] & ((self._pv[i] == 0) | self.out_ready)
                    with If(take):
                        self._pv[i] <<= self._pv[i - 1]
                        self._pv[i - 1] <<= 0

        with self.comb:
            self.d0 <<= (self._pp[2] + self.c0) & 0xFFFF
            self.out_valid <<= self._pv[latency - 1]
