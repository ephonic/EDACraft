"""
L3 DSL — L1Refill, L1Refill.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class L1Refill(Module):
    def __init__(self):
        super().__init__("l1refill")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.miss_addr = Input(39, "miss_addr")
        self.miss_valid = Input(1, "miss_valid")
        self.l2_rdata = Input(39, "l2_rdata")
        self.l2_ready = Input(1, "l2_ready")
        self.refill_addr = Output(39, "refill_addr")
        self.refill_req = Output(1, "refill_req")
        self.refill_data = Output(39, "refill_data")
        self.refill_done = Output(1, "refill_done")
        self.busy = Output(1, "busy")

        self.init = Reg(1, "init")
        self.rf_base = Reg(39, "rf_base")
        self.rf_burst = Reg(3, "rf_burst")
        self.rf_done = Reg(1, "rf_done")
        self.rf_state = Reg(2, "rf_state")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.refill_addr <<= 0
                self.refill_req <<= 0
                self.refill_data <<= 0
                self.refill_done <<= 0
                self.busy <<= 0
            with Else():
                self.refill_addr <<= self.rf_base
                self.refill_req <<= (self.rf_state == 1)
                self.refill_data <<= self.l2_rdata
                self.refill_done <<= self.rf_done
                self.busy <<= (self.rf_state != 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.rf_state <<= 0
                self.rf_burst <<= 0
                self.rf_done <<= 0
            with Else():
                self.init <<= 1
                self.rf_done <<= 0
                with If((self.rf_state == 0)):
                    with If((self.miss_valid == 1)):
                        self.rf_state <<= 1
                        self.rf_base <<= self.miss_addr
                        self.rf_burst <<= 4
                with Elif((self.rf_state == 1)):
                    self.rf_state <<= 2
                with Elif((self.rf_state == 2)):
                    with If((self.l2_ready == 1)):
                        with If((self.rf_burst > 1)):
                            self.rf_burst <<= self.rf_burst - 1
                        with Else():
                            self.rf_state <<= 0
                            self.rf_burst <<= 0
                            self.rf_done <<= 1


