"""
L3 DSL — MMU.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class MMU(Module):
    def __init__(self):
        super().__init__("mmu")
        for w, n in [(1,"clk"),(1,"rst_n"),(1,"ifu_req_valid"),(48,"ifu_req_vaddr"),
                     (1,"lsr_req_valid"),(48,"lsr_req_vaddr"),(1,"lsr_req_is_store"),
                     (1,"lsr_req_user"),(28,"satp_ppn"),(4,"satp_mode"),(1,"flush"),(1,"flush_asid")]:
            setattr(self, n, Input(w, n))
        for w, n in [(1,"ifu_resp_valid"),(56,"ifu_resp_paddr"),(1,"ifu_resp_page_fault"),
                     (1,"lsr_resp_valid"),(56,"lsr_resp_paddr"),(1,"lsr_resp_page_fault"),(1,"busy")]:
            setattr(self, n, Output(w, n))
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.ifu_resp_valid <<= 0; self.ifu_resp_paddr <<= 0
                self.ifu_resp_page_fault <<= 0; self.lsr_resp_valid <<= 0
                self.lsr_resp_paddr <<= 0; self.lsr_resp_page_fault <<= 0
                self.busy <<= 0
            with Else():
                self.ifu_resp_valid <<= self.ifu_req_valid
                self.ifu_resp_paddr <<= self.ifu_req_vaddr
                self.ifu_resp_page_fault <<= 0
                self.lsr_resp_valid <<= self.lsr_req_valid
                self.lsr_resp_paddr <<= self.lsr_req_vaddr
                self.lsr_resp_page_fault <<= 0
                self.busy <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0): self.init <<= 0
            with Else(): self.init <<= 1
