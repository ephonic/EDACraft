"""
L3 DSL — L0BTB, PCGen, PCGen, PCGen, PCReg, RedirectMux, WayPred, PCGen, L0BTB, PCGen, PCReg, RedirectMux, WayPred.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class L0BTB(Module):
    def __init__(self):
        super().__init__("l0btb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_pc = Input(39, "req_pc")
        self.upd_pc = Input(39, "upd_pc")
        self.upd_target = Input(39, "upd_target")
        self.upd_valid = Input(1, "upd_valid")
        self.hit = Output(1, "hit")
        self.target = Output(39, "target")

        self.vld = Array(1, 4, "vld")
        self.tag = Array(20, 1, "tag")
        self.tgt = Array(39, 1, "tgt")

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.vld[0] <<= 0
                self.vld[1] <<= 0
                self.vld[2] <<= 0
                self.vld[3] <<= 0
            with Elif((self.upd_valid == 1)):
                self.tag[0] <<= self.upd_pc >> 3
                self.tgt[0] <<= self.upd_target
                self.vld[0] <<= 1


class PCGen(Module):
    def __init__(self):
        super().__init__("pcgen")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.rv = Input(9, "rv")
        self.rpc = Input(351, "rpc")
        self.stall = Input(1, "stall")
        self.pc = Output(39, "pc")
        self.pc_chg = Output(1, "pc_chg")

        self.any_rv = Wire(1, "any_rv")
        self.init = Reg(1, "init")
        self.u_pcreg_inc = Wire(1, "u_pcreg_inc")
        self.u_pcreg_load = Wire(1, "u_pcreg_load")
        self.u_pcreg_next_pc = Wire(39, "u_pcreg_next_pc")
        self.u_rmux_target = Wire(39, "u_rmux_target")
        self.u_rmux_any_vld = Wire(1, "u_rmux_any_vld")
        self.u_l0_hit = Wire(1, "u_l0_hit")
        self.u_l0_target = Wire(39, "u_l0_target")
        self.u_wp_way = Wire(2, "u_wp_way")
        self.u_pcreg_pc = Wire(39, "u_pcreg_pc")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pc <<= 0
                self.pc_chg <<= 0
            with Else():
                self.u_rmux_rv <<= self.rv
                self.u_rmux_rpc <<= self.rpc
            self.target <<= self.u_rmux_target
            self.any_rv <<= self.u_rmux_any_vld
            self.pc <<= self.u_pcreg_pc
            self.pc_chg <<= self.any_rv

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


class PCReg(Module):
    def __init__(self):
        super().__init__("pcreg")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.next_pc = Input(39, "next_pc")
        self.load = Input(1, "load")
        self.inc = Input(1, "inc")
        self.stall = Input(1, "stall")
        self.pc = Output(39, "pc")

        self.r = Reg(39, "r")

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.r <<= 0
            with Elif((self.load == 1)):
                self.r <<= self.next_pc
            with Elif((self.inc == 1)):
                self.r <<= self.r + 4


class RedirectMux(Module):
    def __init__(self):
        super().__init__("redirectmux")

        self.rv = Input(9, "rv")
        self.rpc = Input(351, "rpc")
        self.target = Output(39, "target")
        self.any_vld = Output(1, "any_vld")

        @self.comb
        def _comb():
            with If((self.rv[0] == 1)):
                self.target <<= self.rpc[38:0]
            with Elif((self.rv[1] == 1)):
                self.target <<= self.rpc[77:39]
            with Elif((self.rv[2] == 1)):
                self.target <<= self.rpc[116:78]
            with Elif((self.rv[3] == 1)):
                self.target <<= self.rpc[155:117]
            with Elif((self.rv[4] == 1)):
                self.target <<= self.rpc[194:156]
            with Elif((self.rv[5] == 1)):
                self.target <<= self.rpc[233:195]
            with Elif((self.rv[6] == 1)):
                self.target <<= self.rpc[272:234]
            with Elif((self.rv[7] == 1)):
                self.target <<= self.rpc[311:273]
            with Elif((self.rv[8] == 1)):
                self.target <<= self.rpc[350:312]
            with Else():
                self.target <<= 0
            self.any_vld <<= (self.rv != 0)


class WayPred(Module):
    def __init__(self):
        super().__init__("waypred")

        self.pc = Input(39, "pc")
        self.inner_way = Input(2, "inner_way")
        self.chgflw_way = Input(2, "chgflw_way")
        self.chgflw_vld = Input(1, "chgflw_vld")
        self.stall = Input(1, "stall")
        self.way = Output(2, "way")

        @self.comb
        def _comb():
            with If((self.chgflw_vld == 1)):
                self.way <<= self.chgflw_way
            with Elif((self.pc[4] == 1)):
                self.way <<= self.inner_way
            with Else():
                self.way <<= 3


