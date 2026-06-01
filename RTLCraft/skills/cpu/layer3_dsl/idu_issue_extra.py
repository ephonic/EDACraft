"""
L3 DSL — SDIQ, VIQ, SDIQ, VIQ.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SDIQ(Module):
    def __init__(self):
        super().__init__("sdiq")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.flush = Input(1, "flush")
        self.enqueue = Input(1, "enqueue")
        self.prs1 = Input(7, "prs1")
        self.prs2 = Input(7, "prs2")
        self.prd = Input(7, "prd")
        self.op = Input(6, "op")
        self.wakeup_pr = Input(7, "wakeup_pr")
        self.wakeup_en = Input(1, "wakeup_en")
        self.issue_ready = Input(1, "issue_ready")
        self.issue_op = Output(6, "issue_op")
        self.issue_prd = Output(7, "issue_prd")
        self.issue_valid = Output(1, "issue_valid")
        self.full = Output(1, "full")

        self.cnt = Reg(3, "cnt")
        self.head = Reg(2, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(2, "tail")

        self.op_t = Array(6, 4, "op_t")
        self.prd_t = Array(7, 4, "prd_t")
        self.prs1_t = Array(7, 4, "prs1_t")
        self.prs2_t = Array(7, 4, "prs2_t")
        self.rdy1_t = Array(1, 4, "rdy1_t")
        self.rdy2_t = Array(1, 4, "rdy2_t")
        self.vld_t = Array(1, 4, "vld_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.issue_op <<= 0
                self.issue_prd <<= 0
                self.issue_valid <<= 0
                self.full <<= 0
            with Else():
                self.issue_op <<= self.op_t[self.head]
                self.issue_prd <<= self.prd_t[self.head]
                self.issue_valid <<= (self.cnt > 0) & (self.vld_t[self.head] == 1) & (self.rdy1_t[self.head] == 1) & (self.rdy2_t[self.head] == 1)
                self.full <<= (self.cnt >= 4)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.vld_t[0] <<= 0
                self.rdy1_t[0] <<= 0
                self.rdy2_t[0] <<= 0
                self.vld_t[1] <<= 0
                self.rdy1_t[1] <<= 0
                self.rdy2_t[1] <<= 0
                self.vld_t[2] <<= 0
                self.rdy1_t[2] <<= 0
                self.rdy2_t[2] <<= 0
                self.vld_t[3] <<= 0
                self.rdy1_t[3] <<= 0
                self.rdy2_t[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1) & (self.cnt < 4)):
                    self.op_t[self.tail] <<= self.op
                    self.prd_t[self.tail] <<= self.prd
                    self.prs1_t[self.tail] <<= self.prs1
                    self.prs2_t[self.tail] <<= self.prs2
                    self.rdy1_t[self.tail] <<= 0
                    self.rdy2_t[self.tail] <<= 0
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.wakeup_en == 1)):
                    with If((self.vld_t[0] == 1) & (self.prs1_t[0] == self.wakeup_pr)):
                        self.rdy1_t[0] <<= 1
                    with If((self.vld_t[0] == 1) & (self.prs2_t[0] == self.wakeup_pr)):
                        self.rdy2_t[0] <<= 1
                    with If((self.vld_t[1] == 1) & (self.prs1_t[1] == self.wakeup_pr)):
                        self.rdy1_t[1] <<= 1
                    with If((self.vld_t[1] == 1) & (self.prs2_t[1] == self.wakeup_pr)):
                        self.rdy2_t[1] <<= 1
                    with If((self.vld_t[2] == 1) & (self.prs1_t[2] == self.wakeup_pr)):
                        self.rdy1_t[2] <<= 1
                    with If((self.vld_t[2] == 1) & (self.prs2_t[2] == self.wakeup_pr)):
                        self.rdy2_t[2] <<= 1
                    with If((self.vld_t[3] == 1) & (self.prs1_t[3] == self.wakeup_pr)):
                        self.rdy1_t[3] <<= 1
                    with If((self.vld_t[3] == 1) & (self.prs2_t[3] == self.wakeup_pr)):
                        self.rdy2_t[3] <<= 1
                with If(((self.issue_ready == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1) & (self.rdy1_t[self.head] == 1) & (self.rdy2_t[self.head] == 1)) == 1):
                    self.vld_t[self.head] <<= 0
                    self.head <<= self.head + 1
                    self.cnt <<= self.cnt - 1
                with If((self.flush == 1)):
                    self.head <<= 0
                    self.tail <<= 0
                    self.cnt <<= 0
                    self.vld_t[0] <<= 0
                    self.vld_t[1] <<= 0
                    self.vld_t[2] <<= 0
                    self.vld_t[3] <<= 0


class VIQ(Module):
    def __init__(self):
        super().__init__("viq")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.flush = Input(1, "flush")
        self.enqueue = Input(1, "enqueue")
        self.prs1 = Input(7, "prs1")
        self.prd = Input(7, "prd")
        self.op = Input(6, "op")
        self.wakeup_pr = Input(7, "wakeup_pr")
        self.wakeup_en = Input(1, "wakeup_en")
        self.issue_ready = Input(1, "issue_ready")
        self.issue_op = Output(6, "issue_op")
        self.issue_prd = Output(7, "issue_prd")
        self.issue_valid = Output(1, "issue_valid")
        self.full = Output(1, "full")

        self.cnt = Reg(3, "cnt")
        self.head = Reg(2, "head")
        self.init = Reg(1, "init")
        self.tail = Reg(2, "tail")

        self.op_t = Array(6, 4, "op_t")
        self.prd_t = Array(7, 4, "prd_t")
        self.prs1_t = Array(7, 4, "prs1_t")
        self.rdy1_t = Array(1, 4, "rdy1_t")
        self.vld_t = Array(1, 4, "vld_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.issue_op <<= 0
                self.issue_prd <<= 0
                self.issue_valid <<= 0
                self.full <<= 0
            with Else():
                self.issue_op <<= self.op_t[self.head]
                self.issue_prd <<= self.prd_t[self.head]
                self.issue_valid <<= (self.cnt > 0) & (self.vld_t[self.head] == 1) & (self.rdy1_t[self.head] == 1)
                self.full <<= (self.cnt >= 4)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.head <<= 0
                self.tail <<= 0
                self.cnt <<= 0
                self.vld_t[0] <<= 0
                self.rdy1_t[0] <<= 0
                self.vld_t[1] <<= 0
                self.rdy1_t[1] <<= 0
                self.vld_t[2] <<= 0
                self.rdy1_t[2] <<= 0
                self.vld_t[3] <<= 0
                self.rdy1_t[3] <<= 0
            with Else():
                self.init <<= 1
                with If((self.enqueue == 1) & (self.cnt < 4)):
                    self.op_t[self.tail] <<= self.op
                    self.prd_t[self.tail] <<= self.prd
                    self.prs1_t[self.tail] <<= self.prs1
                    self.rdy1_t[self.tail] <<= 0
                    self.vld_t[self.tail] <<= 1
                    self.tail <<= self.tail + 1
                    self.cnt <<= self.cnt + 1
                with If((self.wakeup_en == 1)):
                    with If((self.vld_t[0] == 1) & (self.prs1_t[0] == self.wakeup_pr)):
                        self.rdy1_t[0] <<= 1
                    with If((self.vld_t[1] == 1) & (self.prs1_t[1] == self.wakeup_pr)):
                        self.rdy1_t[1] <<= 1
                    with If((self.vld_t[2] == 1) & (self.prs1_t[2] == self.wakeup_pr)):
                        self.rdy1_t[2] <<= 1
                    with If((self.vld_t[3] == 1) & (self.prs1_t[3] == self.wakeup_pr)):
                        self.rdy1_t[3] <<= 1
                with If(((self.issue_ready == 1) & (self.cnt > 0) & (self.vld_t[self.head] == 1) & (self.rdy1_t[self.head] == 1)) == 1):
                    self.vld_t[self.head] <<= 0
                    self.head <<= self.head + 1
                    self.cnt <<= self.cnt - 1
                with If((self.flush == 1)):
                    self.head <<= 0
                    self.tail <<= 0
                    self.cnt <<= 0
                    self.vld_t[0] <<= 0
                    self.vld_t[1] <<= 0
                    self.vld_t[2] <<= 0
                    self.vld_t[3] <<= 0


