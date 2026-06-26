"""Thor GPU — IBuffer L3 DSL. Instruction buffer FIFO per scheduler."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class IBuffer(Module):
    def __init__(self, name="ibuffer", depth=8):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.push_valid = Input(1, "push_valid")
        self.push_data = Input(32, "push_data")
        self.pop_ready = Input(1, "pop_ready")
        self.instr = Output(32, "instr"); self.valid = Output(1, "valid")
        self.stall = Output(1, "stall"); self.count = Output(4, "count")

        self._wr = Reg(3, "wr"); self._rd = Reg(3, "rd"); self._cnt = Reg(4, "cnt")
        self._mem = Array(32, depth, "mem")
        self._bp_v = Reg(1, "bp_v"); self._bp_d = Reg(32, "bp_d")

        with self.comb:
            self.valid <<= (self._cnt != 0) | self._bp_v
            with If(self._cnt != 0): self.instr <<= self._mem[self._rd]
            with Else(): self.instr <<= self._bp_d
            self.stall <<= (self._cnt >= depth) & self.push_valid
            self.count <<= self._cnt

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._wr <<= 0; self._rd <<= 0; self._cnt <<= 0; self._bp_v <<= 0
            with Else():
                push_ok = self.push_valid & (self._cnt < depth)
                pop_ok = self.pop_ready & (self._cnt > 0)
                with If(push_ok):
                    self._mem[self._wr] <<= self.push_data
                    self._wr <<= self._wr + 1
                with If(pop_ok): self._rd <<= self._rd + 1
                with If(push_ok & ~pop_ok): self._cnt <<= self._cnt + 1
                with Elif(~push_ok & pop_ok): self._cnt <<= self._cnt - 1
                self._bp_v <<= self.push_valid & ~self.pop_ready
                with If(self.push_valid & ~self.pop_ready):
                    self._bp_d <<= self.push_data
