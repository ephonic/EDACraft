"""
L3 DSL — VectorFetch, VectorFetch.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class VectorFetch(Module):
    def __init__(self):
        super().__init__("vectorfetch")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")
        self.start_pc = Input(39, "start_pc")
        self.vlen = Input(4, "vlen")
        self.fetch_ready = Input(1, "fetch_ready")
        self.fetch_addr = Output(39, "fetch_addr")
        self.fetch_valid = Output(1, "fetch_valid")
        self.busy = Output(1, "busy")
        self.done = Output(1, "done")

        self.init = Reg(1, "init")
        self.v_active = Reg(1, "v_active")
        self.v_count = Reg(4, "v_count")
        self.v_cur_pc = Reg(39, "v_cur_pc")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.fetch_addr <<= 0
                self.fetch_valid <<= 0
                self.busy <<= 0
                self.done <<= 0
            with Else():
                self.fetch_addr <<= self.v_cur_pc
                self.fetch_valid <<= self.v_active & self.fetch_ready
                self.busy <<= self.v_active
                self.done <<= (self.v_active == 1) & (self.v_count <= 1) & self.fetch_ready

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.v_active <<= 0
                self.v_count <<= 0
            with Else():
                self.init <<= 1
                with If((self.start == 1) & (self.v_active == 0)):
                    self.v_active <<= 1
                    self.v_cur_pc <<= self.start_pc
                    self.v_count <<= self.vlen
                with Elif((self.v_active == 1) & (self.fetch_ready == 1)):
                    with If((self.v_count > 1)):
                        self.v_cur_pc <<= self.v_cur_pc + 4
                        self.v_count <<= self.v_count - 1
                    with Else():
                        self.v_active <<= 0
                        self.v_count <<= 0


