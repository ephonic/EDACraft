"""
L3 DSL — C910Pipeline, ExecuteStage.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class C910Pipeline(Module):
    def __init__(self):
        super().__init__("c910pipeline")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.halt = Input(1, "halt")

        self.init = Reg(1, "init")
        self.instr = Wire(32, "instr")
        self.instr_valid = Wire(1, "instr_valid")
        self.redirect = Wire(1, "redirect")
        self.redirect_pc = Wire(39, "redirect_pc")
        self.stall = Wire(1, "stall")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                pass
            with Else():
                self.stall <<= self.halt
                self.redirect <<= 0
                self.redirect_pc <<= 0
                self.instr <<= self.instr
                self.instr_valid <<= self.instr_valid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


class ExecuteStage(Module):
    def __init__(self):
        super().__init__("executestage")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.instr = Input(32, "instr")
        self.instr_valid = Input(1, "instr_valid")
        self.result = Output(64, "result")
        self.result_valid = Output(1, "result_valid")

        self.a = Wire(64, "a")
        self.alloc = Wire(1, "alloc")
        self.alloc_phy = Wire(7, "alloc_phy")
        self.b = Wire(64, "b")
        self.complete = Wire(1, "complete")
        self.complete_idx = Wire(6, "complete_idx")
        self.enqueue = Wire(1, "enqueue")
        self.init = Reg(1, "init")
        self.issue_op = Wire(6, "issue_op")
        self.issue_prd = Wire(7, "issue_prd")
        self.issue_ready = Wire(1, "issue_ready")
        self.issue_valid = Wire(1, "issue_valid")
        self.op = Wire(4, "op")
        self.opcode = Wire(7, "opcode")
        self.prd = Wire(7, "prd")
        self.prs1 = Wire(7, "prs1")
        self.prs2 = Wire(7, "prs2")
        self.rd_phy = Wire(7, "rd_phy")
        self.retire_ready = Wire(1, "retire_ready")
        self.rs1 = Wire(5, "rs1")
        self.rs2 = Wire(6, "rs2")
        self.wakeup_en = Wire(1, "wakeup_en")
        self.wakeup_pr = Wire(7, "wakeup_pr")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.result <<= 0
                self.result_valid <<= 0
            with Else():
                self.instr <<= self.instr
                self.rs1 <<= self.rs1
                self.rs2 <<= self.rs2
                self.alloc <<= self.instr_valid
                self.enqueue <<= self.instr_valid
                self.prs1 <<= self.prs1
                self.prs2 <<= self.prs2
                self.prd <<= self.alloc_phy
                self.op <<= self.opcode
                self.wakeup_en <<= 0
                self.wakeup_pr <<= 0
                self.issue_ready <<= 1
                self.op <<= self.issue_op
                self.a <<= 5
                self.b <<= 3
                self.alloc <<= self.issue_valid
                self.rd_phy <<= self.issue_prd
                self.complete <<= 1
                self.complete_idx <<= 0
                self.retire_ready <<= 1
                with If((self.issue_valid == 1)):
                    self.result <<= self.result
                    self.result_valid <<= 1
                with Else():
                    self.result <<= 0
                    self.result_valid <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1
