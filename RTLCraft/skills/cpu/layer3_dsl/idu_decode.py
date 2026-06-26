"""
L3 DSL — Decoder, Decoder.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class Decoder(Module):
    def __init__(self):
        super().__init__("decoder")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.instr = Input(32, "instr")
        self.opcode = Output(7, "opcode")
        self.rd = Output(5, "rd")
        self.rs1 = Output(5, "rs1")
        self.rs2 = Output(5, "rs2")
        self.funct3 = Output(3, "funct3")
        self.funct7 = Output(7, "funct7")
        self.imm = Output(64, "imm")
        self.is_imm = Output(1, "is_imm")

        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.opcode <<= 0
                self.rd <<= 0
                self.rs1 <<= 0
                self.rs2 <<= 0
                self.funct3 <<= 0
                self.funct7 <<= 0
                self.imm <<= 0
                self.is_imm <<= 0
            with Else():
                self.opcode <<= self.instr[6:0]
                self.rd <<= self.instr[11:7]
                self.rs1 <<= self.instr[19:15]
                self.rs2 <<= self.instr[24:20]
                self.funct3 <<= self.instr[14:12]
                self.funct7 <<= self.instr[31:25]
                self.is_imm <<= (self.instr[6:0] != 51) & (self.instr[6:0] != 59)
                with If((self.instr[6:0] == 19) | (self.instr[6:0] == 3) | (self.instr[6:0] == 103) | (self.instr[6:0] == 115) | (self.instr[6:0] == 27)):
                    self.imm <<= Cat(Rep(self.instr[31], 52), self.instr[31:20])
                with Elif((self.instr[6:0] == 35)):
                    self.imm <<= Cat(Rep(self.instr[31], 52), self.instr[31:25], self.instr[11:7])
                with Elif((self.instr[6:0] == 99)):
                    self.imm <<= Cat(Rep(self.instr[31], 51), self.instr[31], self.instr[7], self.instr[30:25], self.instr[11:8], 0)
                with Elif((self.instr[6:0] == 55) | (self.instr[6:0] == 23)):
                    self.imm <<= Cat(0, self.instr[31:12], 0)
                with Elif((self.instr[6:0] == 111)):
                    self.imm <<= Cat(Rep(self.instr[31], 43), self.instr[31], self.instr[19:12], self.instr[20], self.instr[30:21], 0)
                with Else():
                    self.imm <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


