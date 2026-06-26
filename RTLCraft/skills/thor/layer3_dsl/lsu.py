"""Thor GPU — LSU L3 DSL. 2-stage load/store pipeline.
Stage 0: address generation
Stage 1: memory request (held until mem_data_valid)
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif

from skills.thor import VLEN


class LSU(Module):
    def __init__(self, name="lsu", latency=2):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.op_vload = Input(1, "op_vload"); self.op_vstore = Input(1, "op_vstore")
        self.base_addr = Input(32, "base_addr"); self.offset = Input(16, "offset")
        self.vector_data = Input(VLEN, "vector_data")
        self.mem_data_valid = Input(1, "mem_data_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.mem_req = Output(1, "mem_req"); self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.rd_data = Output(VLEN, "rd_data"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")
        self._pending = Reg(1, "_pending"); self._is_load = Reg(1, "_is_load")
        self._ld_data = Reg(VLEN, "_ld_data")
        self._pipe_v = [Reg(1, f"lsu_pv_{i}") for i in range(latency)]

        addr = Wire(32, "lsu_addr")
        with self.comb: addr <<= self.base_addr + self.offset

        with self.comb:
            want = self.op_vload | self.op_vstore
            self.mem_addr <<= self.base_addr + self.offset
            self.mem_wdata <<= self.vector_data
            self.mem_req <<= want
            self.mem_wen <<= self.op_vstore
            self.rd_data <<= self._ld_data
            self.in_ready <<= (self._pipe_v[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._pending <<= 0; self._is_load <<= 0; self._ld_data <<= 0
                for i in range(latency): self._pipe_v[i] <<= 0
            with Else():
                s0 = self.in_valid & self.in_ready
                with If(s0):
                    self._pipe_v[0] <<= 1
                with Elif(self._pipe_v[0] & self.out_ready):
                    self._pipe_v[0] <<= 0
                for i in range(1, latency):
                    take = self._pipe_v[i - 1] & ((self._pipe_v[i] == 0) | self.out_ready)
                    with If(take):
                        self._pipe_v[i] <<= self._pipe_v[i - 1]
                        self._pipe_v[i - 1] <<= 0
                with If(self._pending == 0):
                    with If((self.op_vload | self.op_vstore) == 1):
                        self._pending <<= 1; self._is_load <<= self.op_vload
                with Else():
                    with If(self.mem_data_valid == 1):
                        self._pending <<= 0
                        with If(self._is_load == 1): self._ld_data <<= self.mem_rdata

        with self.comb:
            self.out_valid <<= self._pipe_v[latency - 1]
