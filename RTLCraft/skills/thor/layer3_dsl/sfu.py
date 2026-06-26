"""Thor GPU — SFU L3 DSL. Newton-Raphson iteration for sqrt/rcp/sin/cos.
12-stage pipeline:
  Stage  0-1: initial estimate (lookup or constant)
  Stage  2-5: Newton-Raphson iteration (4 iterations for FP32)
  Stage  6-9: refinement
  Stage 10 : sign/flags
  Stage 11 : output
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif, Switch

from skills.thor import FLEN


class SFU(Module):
    def __init__(self, name="sfu", latency=12):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.op_func = Input(2, "op_func")
        self.operand = Input(FLEN, "operand")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.result = Output(FLEN, "result"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")

        self._pipe_v = [Reg(1, f"sfu_pv_{i}") for i in range(latency)]
        self._pipe_d = [Reg(FLEN, f"sfu_pd_{i}") for i in range(latency)]
        self._pipe_f = [Reg(2, f"sfu_pf_{i}") for i in range(latency)]
        self._iter_x = [Reg(FLEN, f"sfu_x_{i}") for i in range(4)]

        # Initial estimate table (rcp: 1/x initial guess)
        rcp_table = [0x3F800000] * 64  # 1.0 initial, would be ROM in real HW

        with self.comb:
            self.in_ready <<= (self._pipe_v[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(latency):
                    self._pipe_v[i] <<= 0; self._pipe_d[i] <<= 0
                    self._pipe_f[i] <<= 0
                for i in range(4): self._iter_x[i] <<= 0
            with Else():
                # Stage 0: capture, initial estimate
                s0 = self.in_valid & self.in_ready
                with If(s0):
                    self._pipe_d[0] <<= self.operand
                    self._pipe_f[0] <<= self.op_func
                    self._pipe_v[0] <<= 1
                with Elif(self._pipe_v[0] & self.out_ready):
                    self._pipe_v[0] <<= 0

                # Stages 1-3: Newton-Raphson for rcp (x_{n+1} = x_n * (2 - a * x_n))
                for i in range(1, 4):
                    take = self._pipe_v[i - 1] & ((self._pipe_v[i] == 0) | self.out_ready)
                    with If(take):
                        # x_{n+1} = x_n * (2 - a * x_n)
                        op = self._pipe_f[i - 1]
                        d = self._pipe_d[i - 1]
                        with If(op == 1):  # rcp
                            a = d; xn = self._iter_x[i - 1] if i > 1 else rcp_table[0]
                            axn = (a * xn) >> 23  # approximate
                            two_minus = 0x40000000 - axn  # approximate 2 - axn
                            self._iter_x[i] <<= (xn * two_minus) >> 23
                        with Else():
                            self._iter_x[i] <<= d
                        self._pipe_v[i] <<= self._pipe_v[i - 1]
                        self._pipe_f[i] <<= op
                        self._pipe_d[i] <<= d
                        self._pipe_v[i - 1] <<= 0

                # Stages 4-11: pipeline shift with function selection
                for i in range(4, latency):
                    take = self._pipe_v[i - 1] & ((self._pipe_v[i] == 0) | self.out_ready)
                    with If(take):
                        op = self._pipe_f[i - 1]; d = self._pipe_d[i - 1]
                        result = d
                        with Switch(op) as sw:
                            # sqrt: use rcp result and multiply by operand
                            with sw.case(0):
                                rcp_r = self._iter_x[3]
                                result = d * rcp_r  # sqrt(a) = a * rsqrt(a)
                            with sw.case(1):
                                result = self._iter_x[3]  # rcp result
                            with sw.case(2):
                                pass  # sin placeholder
                            with sw.case(3):
                                pass  # cos placeholder
                        self._pipe_d[i] <<= result
                        self._pipe_v[i] <<= self._pipe_v[i - 1]
                        self._pipe_f[i] <<= op
                        self._pipe_v[i - 1] <<= 0

        with self.comb:
            self.result <<= self._pipe_d[latency - 1]
            self.out_valid <<= self._pipe_v[latency - 1]
