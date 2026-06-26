"""
L3 DSL — AtomicOp, AtomicOp.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class AtomicOp(Module):
    def __init__(self):
        super().__init__("atomicop")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.op = Input(4, "op")
        self.addr = Input(64, "addr")
        self.rs2_data = Input(64, "rs2_data")
        self.mem_rdata = Input(64, "mem_rdata")
        self.mem_rvalid = Input(1, "mem_rvalid")
        self.result = Output(64, "result")
        self.valid = Output(1, "valid")
        self.busy = Output(1, "busy")

        self.init = Reg(1, "init")
        self.pending = Reg(1, "pending")
        self.result_r = Reg(64, "result_r")
        self.valid_r = Reg(1, "valid_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.valid <<= 0
                self.result <<= 0
                self.busy <<= 0
            with Else():
                self.result <<= self.result_r
                self.valid <<= self.valid_r
                self.busy <<= self.pending

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pending <<= 0
                self.result_r <<= 0
                self.valid_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1)):
                    self.pending <<= 1
                    self.valid_r <<= 0
                with Elif((self.mem_rvalid == 1) & (self.pending == 1)):
                    self.pending <<= 0
                    with If((self.op == 0)):
                        self.result_r <<= self.rs2_data
                    with Elif((self.op == 1)):
                        self.result_r <<= self.rs2_data + self.mem_rdata
                    with Elif((self.op == 2)):
                        self.result_r <<= self.rs2_data & self.mem_rdata
                    with Elif((self.op == 3)):
                        self.result_r <<= self.rs2_data | self.mem_rdata
                    with Elif((self.op == 4)):
                        self.result_r <<= self.rs2_data ^ self.mem_rdata
                    with Elif((self.op == 5)):
                        with If((self.rs2_data[63] == 1) & (self.mem_rdata[63] == 0)):
                            self.result_r <<= self.rs2_data
                        with Elif((self.rs2_data[63] == 0) & (self.mem_rdata[63] == 1)):
                            self.result_r <<= self.mem_rdata
                        with Elif((self.rs2_data[62:0] < self.mem_rdata[62:0])):
                            self.result_r <<= self.rs2_data
                        with Else():
                            self.result_r <<= self.mem_rdata
                    with Elif((self.op == 6)):
                        with If((self.rs2_data[63] == 0) & (self.mem_rdata[63] == 1)):
                            self.result_r <<= self.rs2_data
                        with Elif((self.rs2_data[63] == 1) & (self.mem_rdata[63] == 0)):
                            self.result_r <<= self.mem_rdata
                        with Elif((self.rs2_data[62:0] > self.mem_rdata[62:0])):
                            self.result_r <<= self.rs2_data
                        with Else():
                            self.result_r <<= self.mem_rdata
                    with Elif((self.op == 7)):
                        with If((self.rs2_data < self.mem_rdata)):
                            self.result_r <<= self.rs2_data
                        with Else():
                            self.result_r <<= self.mem_rdata
                    with Elif((self.op == 8)):
                        with If((self.rs2_data > self.mem_rdata)):
                            self.result_r <<= self.rs2_data
                        with Else():
                            self.result_r <<= self.mem_rdata
                    self.valid_r <<= 1


