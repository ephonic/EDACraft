"""
L3 DSL — AddrGen, ICacheIF, IFCtrl, LBuf, AddrGen, ICacheIF, IFCtrl, LBuf.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class AddrGen(Module):
    def __init__(self):
        super().__init__("addrgen")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.pc = Input(39, "pc")
        self.redirect = Input(1, "redirect")
        self.redirect_pc = Input(39, "redirect_pc")
        self.stall = Input(1, "stall")
        self.fetch_addr = Output(39, "fetch_addr")
        self.fetch_valid = Output(1, "fetch_valid")

        self.init = Reg(1, "init")
        self.sel_pc = Wire(39, "sel_pc")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.fetch_addr <<= 0
                self.fetch_valid <<= 0
            with Else():
                with If((self.redirect == 1)):
                    self.sel_pc <<= self.redirect_pc
                with Else():
                    self.sel_pc <<= self.pc
                self.fetch_addr <<= self.sel_pc
                self.fetch_valid <<= ~self.stall

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


class ICacheIF(Module):
    def __init__(self):
        super().__init__("icacheif")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_addr = Input(39, "req_addr")
        self.req_valid = Input(1, "req_valid")
        self.cache_rdata = Input(64, "cache_rdata")
        self.cache_ready = Input(1, "cache_ready")
        self.flush = Input(1, "flush")
        self.req_ready = Output(1, "req_ready")
        self.rdata = Output(64, "rdata")
        self.rvalid = Output(1, "rvalid")
        self.miss = Output(1, "miss")

        self.init = Reg(1, "init")
        self.miss_r = Reg(1, "miss_r")
        self.pending = Reg(1, "pending")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.req_ready <<= 0
                self.rdata <<= 0
                self.rvalid <<= 0
                self.miss <<= 0
            with Else():
                self.req_ready <<= ~self.pending
                self.rdata <<= self.cache_rdata
                self.rvalid <<= self.cache_ready & self.pending
                self.miss <<= self.miss_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pending <<= 0
            with Else():
                self.init <<= 1
                with If((self.req_valid == 1) & (self.pending == 0)):
                    self.pending <<= 1
                    self.miss_r <<= 0
                with If((self.cache_ready == 1)):
                    self.pending <<= 0
                with If((self.flush == 1)):
                    self.pending <<= 0


class IFCtrl(Module):
    def __init__(self):
        super().__init__("ifctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.branch_taken = Input(1, "branch_taken")
        self.branch_target = Input(39, "branch_target")
        self.icache_miss = Input(1, "icache_miss")
        self.ibuf_full = Input(1, "ibuf_full")
        self.flush = Input(1, "flush")
        self.redirect = Output(1, "redirect")
        self.redirect_pc = Output(39, "redirect_pc")
        self.stall_fetch = Output(1, "stall_fetch")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.redirect <<= 0
                self.redirect_pc <<= 0
                self.stall_fetch <<= 0
            with Else():
                self.redirect <<= self.branch_taken | self.flush
                self.redirect_pc <<= self.branch_target
                self.stall_fetch <<= self.icache_miss | self.ibuf_full

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


class LBuf(Module):
    def __init__(self):
        super().__init__("lbuf")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.fill = Input(1, "fill")
        self.fill_data = Input(32, "fill_data")
        self.fill_idx = Input(4, "fill_idx")
        self.loop_active = Input(1, "loop_active")
        self.loop_start = Input(4, "loop_start")
        self.loop_end = Input(4, "loop_end")
        self.rd_idx = Input(4, "rd_idx")
        self.rdata = Output(32, "rdata")
        self.rhit = Output(1, "rhit")

        self.init = Reg(1, "init")

        self.lbuf_mem = Array(32, 16, "lbuf_mem")
        self.lbuf_vld = Array(1, 16, "lbuf_vld")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.rdata <<= 0
                self.rhit <<= 0
            with Else():
                self.rdata <<= self.lbuf_mem[self.rd_idx]
                self.rhit <<= self.loop_active & self.lbuf_vld[self.rd_idx] & (self.rd_idx >= self.loop_start) & (self.rd_idx <= self.loop_end)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.lbuf_vld[0] <<= 0
                self.lbuf_vld[1] <<= 0
                self.lbuf_vld[2] <<= 0
                self.lbuf_vld[3] <<= 0
                self.lbuf_vld[4] <<= 0
                self.lbuf_vld[5] <<= 0
                self.lbuf_vld[6] <<= 0
                self.lbuf_vld[7] <<= 0
                self.lbuf_vld[8] <<= 0
                self.lbuf_vld[9] <<= 0
                self.lbuf_vld[10] <<= 0
                self.lbuf_vld[11] <<= 0
                self.lbuf_vld[12] <<= 0
                self.lbuf_vld[13] <<= 0
                self.lbuf_vld[14] <<= 0
                self.lbuf_vld[15] <<= 0
            with Else():
                self.init <<= 1
                with If((self.fill == 1)):
                    self.lbuf_mem[self.fill_idx] <<= self.fill_data
                    self.lbuf_vld[self.fill_idx] <<= 1


