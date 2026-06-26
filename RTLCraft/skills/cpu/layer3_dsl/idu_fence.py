"""
L3 DSL — FenceUnit, FenceUnit.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class FenceUnit(Module):
    def __init__(self):
        super().__init__("fenceunit")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.is_fence_i = Input(1, "is_fence_i")
        self.store_buffer_drain = Input(1, "store_buffer_drain")
        self.icache_flush_rdy = Input(1, "icache_flush_rdy")
        self.busy = Output(1, "busy")
        self.store_drain_req = Output(1, "store_drain_req")
        self.icache_flush_req = Output(1, "icache_flush_req")
        self.completed = Output(1, "completed")

        self.init = Reg(1, "init")
        self.next_state = Wire(2, "next_state")
        self.state = Reg(2, "state")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.next_state <<= 0
                self.busy <<= 0
                self.store_drain_req <<= 0
                self.icache_flush_req <<= 0
                self.completed <<= 0
            with Else():
                with If((self.state == 0)):
                    with If((self.enqueue == 1)):
                        self.next_state <<= 1
                    with Else():
                        self.next_state <<= 0
                with Elif((self.state == 1)):
                    with If((self.store_buffer_drain == 1)):
                        with If((self.is_fence_i == 1)):
                            self.next_state <<= 2
                        with Else():
                            self.next_state <<= 3
                    with Else():
                        self.next_state <<= 1
                with Elif((self.state == 2)):
                    with If((self.icache_flush_rdy == 1)):
                        self.next_state <<= 3
                    with Else():
                        self.next_state <<= 2
                with Else():
                    self.next_state <<= 0
                self.busy <<= (self.state != 0)
                self.store_drain_req <<= (self.state == 1)
                self.icache_flush_req <<= (self.state == 2)
                self.completed <<= (self.state == 3)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.state <<= 0
            with Else():
                self.init <<= 1
                self.state <<= self.next_state


