"""Thor GPU — SIMT Stack L3 DSL. Branch divergence handling with push/pop."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Mux
from rtlgen.logic import If, Else, Elif, Switch


class SIMTStack(Module):
    def __init__(self):
        super().__init__("simt_stack")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.push = Input(1, "push"); self.pop = Input(1, "pop")
        self.fallthrough_pc = Input(16, "fallthrough_pc")
        self.branch_pc = Input(16, "branch_pc")
        self.reconv_pc = Input(16, "reconv_pc")
        self.predicate_mask = Input(16, "predicate_mask")
        self.active_mask = Output(16, "active_mask")
        self.stack_empty = Output(1, "stack_empty")

        self._sp = Reg(5, "sp")
        self._active = Reg(16, "active")
        self._r0 = Reg(16, "r0"); self._r1 = Reg(16, "r1")
        self._r2 = Reg(16, "r2"); self._r3 = Reg(16, "r3")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._sp <<= 0; self._active <<= 0xFFFF
                self._r0 <<= 0; self._r1 <<= 0; self._r2 <<= 0; self._r3 <<= 0
            with Else():
                with If(self.push & (self._sp < 4)):
                    with Switch(self._sp) as sw:
                        with sw.case(0): self._r0 <<= self.reconv_pc
                        with sw.case(1): self._r1 <<= self.reconv_pc
                        with sw.case(2): self._r2 <<= self.reconv_pc
                        with sw.case(3): self._r3 <<= self.reconv_pc
                    self._sp <<= self._sp + 1
                    self._active <<= self._active & self.predicate_mask
                with Elif(self.pop & (self._sp > 0)):
                    self._sp <<= self._sp - 1
                    self._active <<= 0xFFFF

        spm1 = Wire(3, "spm1")
        with self.comb:
            spm1 <<= self._sp - 1
            self.active_mask <<= self._active
            with Switch(spm1) as sw:
                with sw.case(0): pass
                with sw.case(1): pass
                with sw.case(2): pass
                with sw.case(3): pass
            self.stack_empty <<= (self._sp == 0)
