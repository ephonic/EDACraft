"""Thor GPU — Scoreboard L3 DSL. Register dependency tracking."""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else


class Scoreboard(Module):
    def __init__(self, name="scoreboard", n_regs=128):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.alloc_reg = Input(8, "alloc_reg")
        self.alloc_valid = Input(1, "alloc_valid")
        self.commit_reg = Input(8, "commit_reg")
        self.commit_valid = Input(1, "commit_valid")
        self.busy_mask = Output(128, "busy_mask")
        self.ready_bits = Output(128, "ready_bits")

        self._busy = Reg(128, "busy_reg")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._busy <<= 0
            with Else():
                with If(self.alloc_valid):
                    self._busy <<= self._busy | (1 << self.alloc_reg)
                with If(self.commit_valid):
                    self._busy <<= self._busy & ~(1 << self.commit_reg)

        with self.comb:
            self.busy_mask <<= self._busy
            self.ready_bits <<= ~self._busy
