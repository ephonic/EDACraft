"""
L3 DSL — PreDecodeBuffer, PreDecodeBuffer.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PreDecodeBuffer(Module):
    def __init__(self):
        super().__init__("predecodebuffer")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.push_valid = Input(1, "push_valid")
        self.push_instr = Input(32, "push_instr")
        self.push_tag = Input(8, "push_tag")
        self.pop_ready = Input(1, "pop_ready")
        self.flush = Input(1, "flush")
        self.instr = Output(32, "instr")
        self.tag = Output(8, "tag")
        self.valid = Output(1, "valid")
        self.stall = Output(1, "stall")
        self.free_slots = Output(3, "free_slots")

        self.init = Reg(1, "init")
        self.pd_bp_i = Reg(32, "pd_bp_i")
        self.pd_bp_t = Reg(8, "pd_bp_t")
        self.pd_bp_v = Reg(1, "pd_bp_v")
        self.pd_cnt = Reg(3, "pd_cnt")
        self.pd_rd = Reg(2, "pd_rd")
        self.pd_wr = Reg(2, "pd_wr")

        self.pd_mem_i = Array(32, 4, "pd_mem_i")
        self.pd_mem_t = Array(8, 4, "pd_mem_t")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.instr <<= 0
                self.tag <<= 0
                self.valid <<= 0
                self.stall <<= 0
                self.free_slots <<= 0
            with Else():
                with If((self.pd_cnt != 0) == 1):
                    self.instr <<= self.pd_mem_i[self.pd_rd]
                    self.tag <<= self.pd_mem_t[self.pd_rd]
                    self.valid <<= 1
                with Elif((self.pd_bp_v == 1)):
                    self.instr <<= self.pd_bp_i
                    self.tag <<= self.pd_bp_t
                    self.valid <<= 1
                with Else():
                    self.valid <<= 0
                self.stall <<= (self.pd_cnt >= 4) & self.push_valid
                self.free_slots <<= 4 - self.pd_cnt

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pd_wr <<= 0
                self.pd_rd <<= 0
                self.pd_cnt <<= 0
                self.pd_bp_v <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.pd_wr <<= 0
                    self.pd_rd <<= 0
                    self.pd_cnt <<= 0
                    self.pd_bp_v <<= 0
                with Else():
                    with If((self.push_valid == 1) & (self.pd_cnt < 4)):
                        self.pd_mem_i[self.pd_wr] <<= self.push_instr
                        self.pd_mem_t[self.pd_wr] <<= self.push_tag
                        self.pd_wr <<= self.pd_wr + 1
                        self.pd_cnt <<= self.pd_cnt + 1
                    with If((self.pop_ready == 1) & (self.pd_cnt > 0)):
                        self.pd_rd <<= self.pd_rd + 1
                        self.pd_cnt <<= self.pd_cnt - 1
                    with If((self.push_valid == 1) & (self.pop_ready == 0)):
                        self.pd_bp_v <<= 1
                        self.pd_bp_i <<= self.push_instr
                        self.pd_bp_t <<= self.push_tag
                    with Elif((self.pop_ready == 1)):
                        self.pd_bp_v <<= 0


