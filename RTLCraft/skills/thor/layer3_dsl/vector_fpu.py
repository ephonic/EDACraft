"""Thor GPU — Vector FPU L3 DSL. 16-lane FP32 SIMD, 5-stage pipelined."""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif, Switch

from skills.thor import FLEN, NLANE, VLEN


class VectorFPU(Module):
    def __init__(self, name="vector_fpu", latency=5):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.opcode = Input(5, "opcode")
        self.op1 = Input(VLEN, "op1"); self.op2 = Input(VLEN, "op2")
        self.pred_mask = Input(NLANE, "pred_mask")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.result = Output(VLEN, "result"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")
        F32 = (1 << FLEN) - 1

        self._pipe_v = [Reg(1, f"fpu_pv_{i}") for i in range(latency)]
        self._pipe_d = [Reg(VLEN, f"fpu_pd_{i}") for i in range(latency)]

        with self.comb:
            self.in_ready <<= (self._pipe_v[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(latency):
                    self._pipe_v[i] <<= 0; self._pipe_d[i] <<= 0
            with Else():
                with If(self.in_valid & self.in_ready):
                    r = 0
                    for lane in range(NLANE):
                        with If((self.pred_mask >> lane) & 1):
                            a = (self.op1 >> (lane * FLEN)) & F32
                            b = (self.op2 >> (lane * FLEN)) & F32
                            with Switch(self.opcode) as sw:
                                with sw.case(0x08): r |= (a + b) << (lane * FLEN)
                                with sw.case(0x09): r |= (a * b) << (lane * FLEN)
                    self._pipe_d[0] <<= r; self._pipe_v[0] <<= 1
                with Elif(self._pipe_v[0] & self.out_ready):
                    self._pipe_v[0] <<= 0
                for i in range(1, latency):
                    take = self._pipe_v[i - 1] & ((self._pipe_v[i] == 0) | self.out_ready)
                    with If(take):
                        self._pipe_d[i] <<= self._pipe_d[i - 1]
                        self._pipe_v[i] <<= self._pipe_v[i - 1]
                        self._pipe_v[i - 1] <<= 0

        with self.comb:
            self.result <<= self._pipe_d[latency - 1]
            self.out_valid <<= self._pipe_v[latency - 1]
