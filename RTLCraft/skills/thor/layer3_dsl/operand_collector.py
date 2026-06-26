"""Thor GPU — Operand Collector L3 DSL. Register read with bypass."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Mux
from rtlgen.logic import If, Else

from skills.thor import VLEN


class OperandCollector(Module):
    def __init__(self):
        super().__init__("operand_collector")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.rs1 = Input(8, "rs1"); self.rs2 = Input(8, "rs2")
        self.rf_data1 = Input(VLEN, "rf_data1")
        self.rf_data2 = Input(VLEN, "rf_data2")
        self.bypass_addr = Input(8, "bypass_addr")
        self.bypass_data = Input(VLEN, "bypass_data")
        self.bypass_valid = Input(1, "bypass_valid")
        self.op1 = Output(VLEN, "op1"); self.op2 = Output(VLEN, "op2")

        with self.comb:
            self.op1 <<= Mux(self.bypass_valid & (self.bypass_addr == self.rs1),
                             self.bypass_data, self.rf_data1)
            self.op2 <<= Mux(self.bypass_valid & (self.bypass_addr == self.rs2),
                             self.bypass_data, self.rf_data2)
