"""
L3 DSL — L2TLB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class L2TLB(Module):
    def __init__(self):
        super().__init__("l2tlb")
        for w, n in [(1,"clk"),(1,"rst_n"),(1,"req_valid"),(48,"req_vaddr"),(16,"req_asid"),
                     (1,"flush"),(1,"flush_asid"),(1,"ptw_resp_valid"),(28,"ptw_resp_ppn"),
                     (27,"ptw_resp_vpn"),(16,"ptw_resp_asid"),(8,"ptw_resp_perms"),(3,"ptw_resp_level")]:
            setattr(self, n, Input(w, n))
        for w, n in [(1,"resp_valid"),(1,"resp_hit"),(28,"resp_ppn"),(27,"resp_vpn"),
                     (16,"resp_asid"),(8,"resp_perms"),(3,"resp_level"),(1,"ptw_req_valid")]:
            setattr(self, n, Output(w, n))
        self.init = Reg(1, "init")
        self.vld = Array(1, 256, "vld")
        self.tag = Array(21, 256, "tag")
        self.ppn = Array(28, 256, "ppn")
        self.asid_t = Array(16, 256, "asid_t")

        @self.comb
        def _comb():
            set_idx = self.req_vaddr[17:12]
            req_tag = self.req_vaddr[38:18]
            hit = 0
            for i in range(4):
                idx = (set_idx * 4) + i
                with If(self.vld[idx] == 1 & self.tag[idx] == req_tag & self.asid_t[idx] == self.req_asid):
                    hit = 1
            with If(self.init == 0):
                self.resp_valid <<= 0; self.resp_hit <<= 0; self.ptw_req_valid <<= 0
            with Else():
                self.resp_valid <<= self.req_valid
                self.resp_hit <<= self.req_valid & hit
                self.ptw_req_valid <<= self.req_valid & (~hit)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                for i in range(256): self.vld[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.flush == 1):
                    for i in range(256): self.vld[i] <<= 0
                with Elif(self.ptw_resp_valid == 1):
                    for i in range(255):
                        with If(self.vld[i] == 0):
                            self.vld[i] <<= 1; self.tag[i] <<= self.ptw_resp_vpn[38:18]
                            self.ppn[i] <<= self.ptw_resp_ppn; self.asid_t[i] <<= self.ptw_resp_asid
                    self.vld[255] <<= 1; self.tag[255] <<= self.ptw_resp_vpn[38:18]
                    self.ppn[255] <<= self.ptw_resp_ppn; self.asid_t[255] <<= self.ptw_resp_asid
