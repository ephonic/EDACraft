"""
L3 DSL — ReservationStation, DispatchUnit, OoOCore.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class ReservationStation(Module):
    def __init__(self):
        super().__init__("rs")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.dispatch = Input(1, "dispatch"); self.op = Input(6, "op")
        self.prs1 = Input(7, "prs1"); self.prs2 = Input(7, "prs2")
        self.prd = Input(7, "prd"); self.wakeup_en = Input(1, "wakeup_en")
        self.wakeup_pr = Input(7, "wakeup_pr"); self.issue_ready = Input(1, "issue_ready")
        self.issue_valid = Output(1, "issue_valid"); self.issue_op = Output(6, "issue_op")
        self.issue_prd = Output(7, "issue_prd"); self.full = Output(1, "full")
        self.init = Reg(1, "init")
        self.vld = Array(1, 8, "vld"); self.op_r = Array(6, 8, "op_r")
        self.prd_r = Array(7, 8, "prd_r"); self.rdy1 = Array(1, 8, "rdy1")
        self.rdy2 = Array(1, 8, "rdy2"); self.rdy = Array(2, 8, "rdy")
        self.head = Reg(3, "head"); self.tail = Reg(3, "tail"); self.cnt = Reg(4, "cnt")

        @self.comb
        def _comb():
            issue_found = 0; issue_op_w = 0; issue_prd_w = 0
            for i in range(8):
                with If(self.vld[i] == 1 & self.rdy1[i] == 1 & self.rdy2[i] == 1 & issue_found == 0):
                    issue_found = 1; issue_op_w = self.op_r[i]; issue_prd_w = self.prd_r[i]
            with If(self.init == 0):
                self.issue_valid <<= 0; self.issue_op <<= 0; self.issue_prd <<= 0; self.full <<= 0
            with Else():
                self.issue_valid <<= issue_found
                self.issue_op <<= issue_op_w; self.issue_prd <<= issue_prd_w
                self.full <<= self.cnt >= 8

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0; self.head <<= 0; self.tail <<= 0; self.cnt <<= 0
                for i in range(8): self.vld[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.dispatch == 1 & self.cnt < 8):
                    self.vld[self.tail] <<= 1; self.op_r[self.tail] <<= self.op
                    self.prd_r[self.tail] <<= self.prd
                    with If(self.prs1 == 0): self.rdy1[self.tail] <<= 1
                    with Else(): self.rdy1[self.tail] <<= 0
                    with If(self.prs2 == 0): self.rdy2[self.tail] <<= 1
                    with Else(): self.rdy2[self.tail] <<= 0
                    self.tail <<= (self.tail + 1) & 7; self.cnt <<= self.cnt + 1


class DispatchUnit(Module):
    def __init__(self):
        super().__init__("dispatch")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        for i in range(6):
            setattr(self, f"slot_valid_{i}", Input(1, f"slot_valid_{i}"))
            setattr(self, f"slot_op_{i}", Input(6, f"slot_op_{i}"))
            setattr(self, f"slot_prs1_{i}", Input(7, f"slot_prs1_{i}"))
            setattr(self, f"slot_prs2_{i}", Input(7, f"slot_prs2_{i}"))
            setattr(self, f"slot_prd_{i}", Input(7, f"slot_prd_{i}"))
            setattr(self, f"rs_full_{i}", Input(1, f"rs_full_{i}"))
            setattr(self, f"dispatch_{i}", Output(1, f"dispatch_{i}"))
            setattr(self, f"dispatch_op_{i}", Output(6, f"dispatch_op_{i}"))
            setattr(self, f"dispatch_prs1_{i}", Output(7, f"dispatch_prs1_{i}"))
            setattr(self, f"dispatch_prs2_{i}", Output(7, f"dispatch_prs2_{i}"))
            setattr(self, f"dispatch_prd_{i}", Output(7, f"dispatch_prd_{i}"))
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If(self.init == 0):
                for i in range(6):
                    d = getattr(self, f"dispatch_{i}")
                    d <<= 0
            with Else():
                for i in range(6):
                    d = getattr(self, f"dispatch_{i}")
                    sv = getattr(self, f"slot_valid_{i}")
                    rf = getattr(self, f"rs_full_{i}")
                    d <<= sv & (~rf)
                    op = getattr(self, f"dispatch_op_{i}")
                    op <<= getattr(self, f"slot_op_{i}")
                    ps1 = getattr(self, f"dispatch_prs1_{i}")
                    ps1 <<= getattr(self, f"slot_prs1_{i}")
                    ps2 = getattr(self, f"dispatch_prs2_{i}")
                    ps2 <<= getattr(self, f"slot_prs2_{i}")
                    pd = getattr(self, f"dispatch_prd_{i}")
                    pd <<= getattr(self, f"slot_prd_{i}")

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0): self.init <<= 0
            with Else(): self.init <<= 1


class OoOCore(Module):
    def __init__(self):
        super().__init__("ooocore")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        for i in range(6):
            setattr(self, f"slot_valid_{i}", Input(1, f"slot_valid_{i}"))
            setattr(self, f"slot_op_{i}", Input(6, f"slot_op_{i}"))
            setattr(self, f"slot_prs1_{i}", Input(7, f"slot_prs1_{i}"))
            setattr(self, f"slot_prs2_{i}", Input(7, f"slot_prs2_{i}"))
            setattr(self, f"slot_prd_{i}", Input(7, f"slot_prd_{i}"))
            setattr(self, f"commit_valid_{i}", Output(1, f"commit_valid_{i}"))
            setattr(self, f"commit_prd_{i}", Output(7, f"commit_prd_{i}"))
            setattr(self, f"commit_data_{i}", Output(64, f"commit_data_{i}"))
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If(self.init == 0):
                for i in range(6):
                    cv = getattr(self, f"commit_valid_{i}")
                    cv <<= 0
            with Else():
                cv0 = self.commit_valid_0
                cv0 <<= self.slot_valid_0
                cp0 = self.commit_prd_0
                cp0 <<= self.slot_prd_0
                cd0 = self.commit_data_0
                cd0 <<= self.slot_op_0
                for i in range(1, 6):
                    cv = getattr(self, f"commit_valid_{i}")
                    cv <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0): self.init <<= 0
            with Else(): self.init <<= 1
