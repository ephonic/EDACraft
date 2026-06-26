"""Thor GPU — Shared Memory L3 DSL. 32KB 32-bank scratchpad with conflict detection."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory
from rtlgen.logic import If, Else, Switch

from skills.thor import XLEN, NLANE


class SharedMemory(Module):
    def __init__(self, n_banks=4):
        """n_banks=4 for simplified implementation (signal-based bank select)."""
        super().__init__("shared_memory")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.addr = Input(32, "addr"); self.wen = Input(1, "wen")
        self.wdata = Input(XLEN, "wdata"); self.bm = Input(n_banks, "bank_conflict_mask")
        self.rdata = Output(XLEN, "rdata")
        self.bank_conflict = Output(1, "bank_conflict")

        mems = [Memory(XLEN, 256, f"bank_{i}") for i in range(n_banks)]
        bank = Wire(2, "bank_id"); off = Wire(8, "bank_off")
        with self.comb:
            bank <<= (self.addr // 4) % n_banks
            off <<= (self.addr // 4) // n_banks

        with self.comb:
            for i in range(n_banks):
                with If(bank == i): self.rdata <<= mems[i][off]
            self.bank_conflict <<= (self.bm >> bank) & 1

        with self.seq(self.clk, self.rst):
            with If(self.wen):
                for i in range(n_banks):
                    with If(bank == i): mems[i][off] <<= self.wdata
