"""Thor GPU — Memory Controller L3 DSL. HBM3-like with burst and timing.
4 channels, each 128b wide, burst length 8 = 512B per request.
Pipeline: CMD -> tRCD -> tCAS -> data -> tRP
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif, Switch


class MemController(Module):
    def __init__(self, t_rcd=4, t_cas=4, t_rp=4):
        super().__init__("mem_controller")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.req_valid = Input(1, "req_valid")
        self.addr = Input(32, "addr"); self.wen = Input(1, "wen")
        self.wdata = Input(512, "wdata")
        self.ready = Input(1, "ready")
        self.grant = Output(1, "grant")
        self.rdata = Output(512, "rdata")
        self.resp_valid = Output(1, "resp_valid")

        # FSM: IDLE=0, ACT=1(tRCD), RD/WR=2(tCAS), PRE=3(tRP)
        self._state = Reg(3, "mem_state")
        self._timer = Reg(4, "mem_timer")
        self._is_write = Reg(1, "mem_is_write")
        self._burst_cnt = Reg(4, "mem_burst")
        self._hold_data = Reg(512, "mem_hold_data")

        with self.comb:
            self.grant <<= (self._state == 0) & self.req_valid & self.ready
            self.resp_valid <<= (self._state == 2) & (self._timer == 1) & ~self._is_write
            self.rdata <<= self._hold_data

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= 0; self._timer <<= 0
                self._is_write <<= 0; self._burst_cnt <<= 0
            with Else():
                with Switch(self._state) as sw:
                    with sw.case(0):  # IDLE
                        with If(self.req_valid & self.ready):
                            self._state <<= 1  # ACT
                            self._timer <<= t_rcd - 1
                            self._is_write <<= self.wen
                            self._hold_data <<= self.wdata
                    with sw.case(1):  # ACT (tRCD)
                        with If(self._timer > 0):
                            self._timer <<= self._timer - 1
                        with Else():
                            self._state <<= 2
                            self._timer <<= t_cas - 1
                            self._burst_cnt <<= 8
                    with sw.case(2):  # RD/WR (tCAS + burst)
                        with If(self._timer > 0):
                            self._timer <<= self._timer - 1
                        with Else():
                            self._state <<= 3
                            self._timer <<= t_rp - 1
                    with sw.case(3):  # PRE (tRP)
                        with If(self._timer > 0):
                            self._timer <<= self._timer - 1
                        with Else():
                            self._state <<= 0
