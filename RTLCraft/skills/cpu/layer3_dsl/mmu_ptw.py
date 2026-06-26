"""
L3 DSL — PTW.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class PTW(Module):
    def __init__(self):
        super().__init__("ptw")
        for w, n in [(1,"clk"),(1,"rst_n"),(1,"req_valid"),(48,"req_vaddr"),(16,"req_asid"),
                     (1,"req_sv39"),(28,"satp_ppn"),(1,"mem_resp_valid"),(64,"mem_resp_data")]:
            setattr(self, n, Input(w, n))
        for w, n in [(1,"resp_valid"),(28,"resp_ppn"),(27,"resp_vpn"),(16,"resp_asid"),
                     (8,"resp_perms"),(3,"resp_level"),(1,"resp_page_fault"),(1,"busy"),
                     (1,"mem_req_valid"),(56,"mem_req_addr")]:
            setattr(self, n, Output(w, n))
        self.init = Reg(1, "init")
        self.state = Reg(3, "state")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.resp_valid <<= 0; self.busy <<= 0; self.mem_req_valid <<= 0
            with Else():
                with If(self.state == 0):
                    self.busy <<= 0; self.mem_req_valid <<= 0; self.resp_valid <<= 0
                with Elif(self.state == 4):
                    self.busy <<= 1; self.mem_req_valid <<= 0
                    self.resp_valid <<= 1
                    self.resp_ppn <<= self.mem_resp_data[53:26]
                    self.resp_vpn <<= self.req_vaddr[38:12]
                    self.resp_asid <<= self.req_asid
                    self.resp_perms <<= self.mem_resp_data[7:0]
                    self.resp_level <<= 0; self.resp_page_fault <<= 0
                with Else():
                    self.busy <<= 1; self.mem_req_valid <<= 1
                    self.resp_valid <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0; self.state <<= 0
            with Else():
                self.init <<= 1
                with If(self.state == 0):
                    with If(self.req_valid == 1):
                        self.state <<= 1
                with Elif(self.state == 1):
                    with If(self.mem_resp_valid == 1):
                        self.state <<= 2
                with Elif(self.state == 2):
                    with If(self.mem_resp_valid == 1):
                        self.state <<= 3
                with Elif(self.state == 3):
                    with If(self.mem_resp_valid == 1):
                        self.state <<= 4
                with Elif(self.state == 4):
                    self.state <<= 5
                with Else():
                    self.state <<= 0
