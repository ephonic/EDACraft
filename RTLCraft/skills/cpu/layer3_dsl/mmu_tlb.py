"""
L3 DSL — ITLB, DTLB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class ITLB(Module):
    def __init__(self):
        super().__init__("itlb")
        for w, n in [(1,"clk"),(1,"rst_n"),(1,"req_valid"),(48,"req_vaddr"),(16,"req_asid"),
                     (1,"req_sv39"),(1,"flush"),(1,"flush_asid"),(1,"ptw_resp_valid"),
                     (28,"ptw_resp_ppn"),(27,"ptw_resp_vpn"),(16,"ptw_resp_asid"),
                     (8,"ptw_resp_perms"),(3,"ptw_resp_level")]:
            setattr(self, n, Input(w, n))
        for w, n in [(1,"resp_valid"),(56,"resp_paddr"),(1,"resp_miss"),(1,"resp_page_fault"),
                     (1,"ptw_req_valid"),(48,"ptw_req_vaddr"),(16,"ptw_req_asid")]:
            setattr(self, n, Output(w, n))
        self.init = Reg(1, "init")
        self.vld = Array(1, 32, "vld")
        self.vpn = Array(27, 32, "vpn")
        self.ppn = Array(28, 32, "ppn")
        self.asid_t = Array(16, 32, "asid_t")
        self.perm = Array(8, 32, "perm")

        @self.comb
        def _comb():
            req_vpn = self.req_vaddr[38:12]
            hit = 0
            hit_ppn = 0
            for i in range(32):
                with If(self.vld[i] == 1 & self.vpn[i] == req_vpn & self.asid_t[i] == self.req_asid):
                    hit = 1
                    hit_ppn = self.ppn[i]
            with If(self.init == 0):
                self.resp_valid <<= 0; self.resp_miss <<= 0
                self.resp_page_fault <<= 0; self.ptw_req_valid <<= 0
            with Else():
                self.resp_valid <<= self.req_valid & hit
                self.resp_miss <<= self.req_valid & (~hit)
                self.resp_page_fault <<= 0
                self.ptw_req_valid <<= self.req_valid & (~hit)
                self.ptw_req_vaddr <<= self.req_vaddr
                self.ptw_req_asid <<= self.req_asid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                for i in range(32):
                    self.vld[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.flush == 1):
                    for i in range(32):
                        self.vld[i] <<= 0
                with Elif(self.ptw_resp_valid == 1):
                    for i in range(31):
                        with If(self.vld[i] == 0):
                            self.vld[i] <<= 1
                            self.vpn[i] <<= self.ptw_resp_vpn
                            self.ppn[i] <<= self.ptw_resp_ppn
                            self.asid_t[i] <<= self.ptw_resp_asid
                            self.perm[i] <<= self.ptw_resp_perms
                    with If(self.vld[31] == 1):
                        self.vld[0] <<= 1
                        self.vpn[0] <<= self.ptw_resp_vpn
                        self.ppn[0] <<= self.ptw_resp_ppn
                        self.asid_t[0] <<= self.ptw_resp_asid
                        self.perm[0] <<= self.ptw_resp_perms
                    with Else():
                        self.vld[31] <<= 1
                        self.vpn[31] <<= self.ptw_resp_vpn
                        self.ppn[31] <<= self.ptw_resp_ppn
                        self.asid_t[31] <<= self.ptw_resp_asid
                        self.perm[31] <<= self.ptw_resp_perms


class DTLB(Module):
    def __init__(self):
        super().__init__("dtlb")
        for w, n in [(1,"clk"),(1,"rst_n"),(1,"req_valid"),(48,"req_vaddr"),(16,"req_asid"),
                     (1,"req_sv39"),(1,"req_is_store"),(1,"req_user"),(1,"flush"),(1,"flush_asid"),
                     (1,"ptw_resp_valid"),(28,"ptw_resp_ppn"),(27,"ptw_resp_vpn"),
                     (16,"ptw_resp_asid"),(8,"ptw_resp_perms"),(3,"ptw_resp_level")]:
            setattr(self, n, Input(w, n))
        for w, n in [(1,"resp_valid"),(56,"resp_paddr"),(1,"resp_miss"),(1,"resp_page_fault"),
                     (1,"ptw_req_valid"),(48,"ptw_req_vaddr"),(16,"ptw_req_asid")]:
            setattr(self, n, Output(w, n))
        self.init = Reg(1, "init")
        self.vld = Array(1, 32, "vld")
        self.vpn = Array(27, 32, "vpn")
        self.ppn = Array(28, 32, "ppn")
        self.asid_t = Array(16, 32, "asid_t")
        self.perm = Array(8, 32, "perm")

        @self.comb
        def _comb():
            req_vpn = self.req_vaddr[38:12]
            hit = 0; hit_ppn = 0
            for i in range(32):
                with If(self.vld[i] == 1 & self.vpn[i] == req_vpn & self.asid_t[i] == self.req_asid):
                    hit = 1; hit_ppn = self.ppn[i]
            with If(self.init == 0):
                self.resp_valid <<= 0; self.resp_miss <<= 0
                self.resp_page_fault <<= 0; self.ptw_req_valid <<= 0
            with Else():
                self.resp_valid <<= self.req_valid & hit
                self.resp_miss <<= self.req_valid & (~hit)
                self.resp_page_fault <<= 0
                self.ptw_req_valid <<= self.req_valid & (~hit)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                for i in range(32): self.vld[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.flush == 1):
                    for i in range(32): self.vld[i] <<= 0
                with Elif(self.ptw_resp_valid == 1):
                    for i in range(31):
                        with If(self.vld[i] == 0):
                            self.vld[i] <<= 1; self.vpn[i] <<= self.ptw_resp_vpn
                            self.ppn[i] <<= self.ptw_resp_ppn
                            self.asid_t[i] <<= self.ptw_resp_asid
                            self.perm[i] <<= self.ptw_resp_perms
                    with If(self.vld[31] == 1):
                        self.vld[0] <<= 1; self.vpn[0] <<= self.ptw_resp_vpn
                        self.ppn[0] <<= self.ptw_resp_ppn
                        self.asid_t[0] <<= self.ptw_resp_asid; self.perm[0] <<= self.ptw_resp_perms
                    with Else():
                        self.vld[31] <<= 1; self.vpn[31] <<= self.ptw_resp_vpn
                        self.ppn[31] <<= self.ptw_resp_ppn
                        self.asid_t[31] <<= self.ptw_resp_asid; self.perm[31] <<= self.ptw_resp_perms
