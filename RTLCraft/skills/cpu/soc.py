"""
soc — Quad-Core Heterogeneous SoC Platform.

Components:
  2 × HPCore (core 0, 1) — 6-issue OoO
  2 × EECore (core 2, 3) — 1-issue in-order
  Shared L2 cache (direct-mapped, 64 sets)
  Crossbar interconnect with round-robin arbitration
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif, Mux

from skills.cpu.core_types import HPCore, EECore


class L2Cache(Module):
    """Shared L2 cache: direct-mapped, 64 sets."""
    def __init__(self, sets=64, width=64):
        super().__init__("l2_cache")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(64, "req_addr")
        self.req_we = Input(1, "req_we")
        self.req_data = Input(width, "req_data")
        self.req_id = Input(2, "req_id")
        self.resp_data = Output(width, "resp_data")
        self.resp_valid = Output(1, "resp_valid")
        self.resp_id = Output(2, "resp_id")
        self.busy = Output(1, "busy")

        vld_arr = Array(1, sets, "vld_arr")
        tag_arr = Array(20, sets, "tag_arr")
        data_arr = Array(width, sets, "data_arr")
        pending = Reg(1, "pending"); resp_r = Reg(width, "resp_r")
        valid_r = Reg(1, "valid_r"); id_r = Reg(2, "id_r")
        addr_r = Reg(64, "addr_r"); we_r = Reg(1, "we_r"); wdata_r = Reg(width, "wdata_r")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                init <<= 0; pending <<= 0; valid_r <<= 0
                for i in range(sets):
                    vld_arr[i] <<= 0; tag_arr[i] <<= 0; data_arr[i] <<= 0
            with Else():
                init <<= 1; valid_r <<= 0
                with If((self.req_valid == 1) & (pending == 0)):
                    pending <<= 1; id_r <<= self.req_id; addr_r <<= self.req_addr
                    we_r <<= self.req_we; wdata_r <<= self.req_data
                with If(pending == 1):
                    pending <<= 0; valid_r <<= 1
                    with If(we_r == 1):
                        for i in range(sets):
                            with If(Const(i, 6) == addr_r[11:6]):
                                vld_arr[i] <<= 1; tag_arr[i] <<= addr_r[63:44]
                                data_arr[i] <<= wdata_r

        with self.comb:
            with If(init == 0):
                self.resp_data <<= Const(0, width); self.resp_valid <<= 0
                self.resp_id <<= 0; self.busy <<= 1
            with Else():
                sel_data = Wire(width, "sel_data"); sel_hit = Wire(1, "sel_hit")
                sel_data <<= Const(0, width); sel_hit <<= 0
                for i in range(sets):
                    with If(Const(i, 6) == self.req_addr[11:6]):
                        sel_hit <<= vld_arr[i] & (tag_arr[i] == self.req_addr[63:44])
                        sel_data <<= data_arr[i]
                self.resp_data <<= Mux(pending, resp_r, sel_data)
                self.resp_valid <<= valid_r | ((self.req_valid == 1) & sel_hit & (pending == 0))
                self.resp_id <<= id_r
                self.busy <<= pending


class Crossbar(Module):
    """4→1 crossbar with round-robin arbitration."""
    def __init__(self):
        super().__init__("crossbar")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.core_req_valid = [Input(1, f"crv_{i}") for i in range(4)]
        self.core_req_addr = [Input(64, f"cra_{i}") for i in range(4)]
        self.core_req_we = [Input(1, f"crw_{i}") for i in range(4)]
        self.core_req_data = [Input(64, f"crd_{i}") for i in range(4)]
        self.core_resp_data = [Output(64, f"crspd_{i}") for i in range(4)]
        self.core_resp_valid = [Output(1, f"crspv_{i}") for i in range(4)]
        self.l2_req_valid = Output(1, "l2_req_valid")
        self.l2_req_addr = Output(64, "l2_req_addr")
        self.l2_req_we = Output(1, "l2_req_we")
        self.l2_req_data = Output(64, "l2_req_data")
        self.l2_req_id = Output(2, "l2_req_id")
        self.l2_resp_data = Input(64, "l2_resp_data")
        self.l2_resp_valid = Input(1, "l2_resp_valid")
        self.l2_resp_id = Input(2, "l2_resp_id")
        self.l2_busy = Input(1, "l2_busy")

        sel = Reg(2, "sel"); busy_r = Reg(1, "busy_r")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; sel <<= 0; busy_r <<= 0
            with Else():
                init <<= 1
                with If((busy_r == 0) & (self.l2_busy == 0)):
                    for i in range(4):
                        with If(self.core_req_valid[i] == 1):
                            sel <<= i
                            busy_r <<= 1
                with If(self.l2_resp_valid == 1):
                    busy_r <<= 0

        with self.comb:
            with If(init == 0):
                for i in range(4):
                    self.core_resp_data[i] <<= Const(0, 64)
                    self.core_resp_valid[i] <<= 0
                self.l2_req_valid <<= 0; self.l2_req_addr <<= Const(0, 64)
                self.l2_req_we <<= 0; self.l2_req_data <<= Const(0, 64); self.l2_req_id <<= 0
            with Else():
                mux_vld = Wire(1, "mux_vld")
                mux_vld <<= Mux(Const(0, 2) == sel, self.core_req_valid[0],
                               Mux(Const(1, 2) == sel, self.core_req_valid[1],
                                   Mux(Const(2, 2) == sel, self.core_req_valid[2],
                                       self.core_req_valid[3])))
                self.l2_req_valid <<= mux_vld & busy_r
                self.l2_req_addr <<= Mux(Const(0, 2) == sel, self.core_req_addr[0],
                                        Mux(Const(1, 2) == sel, self.core_req_addr[1],
                                            Mux(Const(2, 2) == sel, self.core_req_addr[2],
                                                self.core_req_addr[3])))
                self.l2_req_we <<= Mux(Const(0, 2) == sel, self.core_req_we[0],
                                      Mux(Const(1, 2) == sel, self.core_req_we[1],
                                          Mux(Const(2, 2) == sel, self.core_req_we[2],
                                              self.core_req_we[3])))
                self.l2_req_data <<= Mux(Const(0, 2) == sel, self.core_req_data[0],
                                        Mux(Const(1, 2) == sel, self.core_req_data[1],
                                            Mux(Const(2, 2) == sel, self.core_req_data[2],
                                                self.core_req_data[3])))
                self.l2_req_id <<= sel

                for i in range(4):
                    with If(Const(i, 2) == self.l2_resp_id):
                        self.core_resp_data[i] <<= self.l2_resp_data
                        self.core_resp_valid[i] <<= self.l2_resp_valid
                    with Else():
                        self.core_resp_data[i] <<= 0
                        self.core_resp_valid[i] <<= 0


class QuadCoreSoC(Module):
    """Quad-core heterogeneous SoC: 2×HPCore + 2×EECore + L2 + crossbar."""
    def __init__(self):
        super().__init__("quad_core_soc")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.core_instr = [Input(32, f"ci_{i}") for i in range(4)]
        self.core_instr_valid = [Input(1, f"civ_{i}") for i in range(4)]
        self.core_result = [Output(64, f"cr_{i}") for i in range(4)]
        self.core_result_valid = [Output(1, f"crv_{i}") for i in range(4)]
        self.core_retired = [Output(1, f"cret_{i}") for i in range(4)]

        cores = [HPCore(hartid=0, PC_WIDTH=39, XLEN=64),
                 HPCore(hartid=1, PC_WIDTH=39, XLEN=64),
                 EECore(hartid=2, PC_WIDTH=39, XLEN=64),
                 EECore(hartid=3, PC_WIDTH=39, XLEN=64)]

        l2 = L2Cache(sets=64, width=64)
        xbar = Crossbar()

        self._submodules.extend([(f"core_{i}", cores[i]) for i in range(4)])
        self._submodules.extend([("l2", l2), ("xbar", xbar)])

        init = Reg(1, "init")
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0
            with Else(): init <<= 1

        with self.comb:
            with If(init == 0):
                for i in range(4):
                    self.core_result[i] <<= 0; self.core_result_valid[i] <<= 0; self.core_retired[i] <<= 0
                    cores[i].instr <<= 0; cores[i].instr_valid <<= 0; cores[i].hartid <<= 0
                    cores[i].mem_rdata <<= 0; cores[i].mem_rvalid <<= 0
                    cores[i].mtip <<= 0; cores[i].meip <<= 0; cores[i].msip <<= 0
            with Else():
                for i in range(4):
                    c = cores[i]
                    c.hartid <<= Const(i, 8)
                    c.instr <<= self.core_instr[i]
                    c.instr_valid <<= self.core_instr_valid[i]
                    c.mtip <<= 0; c.meip <<= 0; c.msip <<= 0
                    c.mem_rdata <<= xbar.core_resp_data[i]
                    c.mem_rvalid <<= xbar.core_resp_valid[i]
                    self.core_result[i] <<= c.result
                    self.core_result_valid[i] <<= c.result_valid
                    self.core_retired[i] <<= c.retired
                    xbar.core_req_valid[i] <<= c.mem_req_valid
                    xbar.core_req_addr[i] <<= c.mem_req_addr
                    xbar.core_req_we[i] <<= c.mem_req_we
                    xbar.core_req_data[i] <<= c.mem_req_data

                xbar.l2_resp_data <<= l2.resp_data
                xbar.l2_resp_valid <<= l2.resp_valid
                xbar.l2_resp_id <<= l2.resp_id
                xbar.l2_busy <<= l2.busy
                l2.req_valid <<= xbar.l2_req_valid
                l2.req_addr <<= xbar.l2_req_addr
                l2.req_we <<= xbar.l2_req_we
                l2.req_data <<= xbar.l2_req_data
                l2.req_id <<= xbar.l2_req_id
