"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_macro_lessthan(Module):
    def __init__(self, name: str = "js_vm_macro_lessthan"), DELAY: int = 8, SEGMENT: int = (((self.DATA_WIDTH + self.DELAY) - 1) // self.DELAY), BIT1: int = 0, BIT8: int = 1, BIT16: int = 2, BIT32: int = 3, BIT64: int = 4, BIT128: int = 5, BIT253: int = 6, BITMULTI: int = 7:
        super().__init__(name or "js_vm_macro_lessthan")

        self.add_localparam("DELAY", 8)
        self.add_localparam("SEGMENT", (((self.DATA_WIDTH + self.DELAY) - 1) // self.DELAY))
        self.add_localparam("BIT1", 0)
        self.add_localparam("BIT8", 1)
        self.add_localparam("BIT16", 2)
        self.add_localparam("BIT32", 3)
        self.add_localparam("BIT64", 4)
        self.add_localparam("BIT128", 5)
        self.add_localparam("BIT253", 6)
        self.add_localparam("BITMULTI", 7)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.eu_macro_lessthan_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "eu_macro_lessthan_data")
        self.eu_macro_lessthan_i_valid = Input(1, "eu_macro_lessthan_i_valid")
        self.eu_macro_lessthan_i_vm_id = Input(4, "eu_macro_lessthan_i_vm_id")
        self.eu_macro_lessthan_o_ready = Input(1, "eu_macro_lessthan_o_ready")
        self.eu_macro_lessthan_i_ready = Output(1, "eu_macro_lessthan_i_ready")
        self.eu_macro_lessthan_o_valid = Output(1, "eu_macro_lessthan_o_valid")
        self.eu_macro_lessthan_o_vm_id = Output(4, "eu_macro_lessthan_o_vm_id")
        self.eu_macro_lessthan_o_mask = Output(2, "eu_macro_lessthan_o_mask")
        self.eu_macro_lessthan_res = Output(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "eu_macro_lessthan_res")

        # TODO: unpack assignment: Cat(self.eu_macro_lessthan_isa, self.eu_macro_lessthan_cc_value, self.eu_macro_lessthan_data_y, self.eu_macro_lessthan_data_x) = self.eu_macro_lessthan_data
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.eu_macro_lessthan_isa_r[(self.DELAY - 1)]
        # Consider using Split() or manual bit slicing
        self.bit_nums <<= Mux((self.src0_fmt == 10), self.src0_imm, Mux(((self.src0_fmt == 0) | (self.src0_fmt == 1)), 8, Mux(((self.src0_fmt == 2) | (self.src0_fmt == 3)), 16, Mux(((self.src0_fmt == 4) | (self.src0_fmt == 5)), 32, Mux(((self.src0_fmt == 6) | (self.src0_fmt == 7)), 64, Mux(((self.src0_fmt == 8) | (self.src0_fmt == 9)), 128, 0))))))
        self.eu_macro_lessthan_condition <<= (Cat(Rep(Cat(0), ((self.DELAY * self.SEGMENT) - self.DATA_WIDTH)), self.eu_macro_lessthan_data_y[(self.DATA_WIDTH - 1):0]) ^ Cat(Rep(Cat(0), ((self.DELAY * self.SEGMENT) - self.DATA_WIDTH)), self.eu_macro_lessthan_data_x[(self.DATA_WIDTH - 1):0]))
        self.eu_macro_lessthan_i_ready <<= self.eu_pipe_i_ready[0]
        self.eu_macro_lessthan_o_valid <<= self.eu_pipe_o_valid[(self.DELAY - 1)]
        self.eu_macro_lessthan_o_vm_id <<= self.eu_macro_lessthan_vm_id_r[(self.DELAY - 1)]
        self.eu_macro_lessthan_res <<= Cat(self.eu_macro_lessthan_isa_r[(self.DELAY - 1)], self.eu_macro_lessthan_cc_value_r[(self.DELAY - 1)], Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.res_tmp[((2 * self.DATA_WIDTH) - 1):self.DATA_WIDTH], Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.res_tmp[(self.DATA_WIDTH - 1):0])
        self.eu_macro_lessthan_o_mask <<= Mux((self.bit_nums > 126), 3, 1)
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.res_tmp[(2 * i)] <<= Mux((i < self.bit_nums), self.eu_macro_lessthan_condition_r[(self.DELAY - 1)][i], 0)
            self.res_tmp[((2 * i) + 1)] <<= Mux((i < self.bit_nums), self.eu_macro_lessthan_tmp_r[(self.DELAY - 1)][i], 0)
        # for-loop (non-generate) - parameter-driven
        for dly in range(0, self.DELAY):
            with If((dly == 0)):
                self.eu_pipe_i_valid[dly] <<= self.eu_macro_lessthan_i_valid
                self.eu_pipe_o_ready[dly] <<= self.eu_pipe_i_ready[(dly + 1)]
            with Else():
                with If((dly == (self.DELAY - 1))):
                    self.eu_pipe_i_valid[dly] <<= self.eu_pipe_o_valid[(dly - 1)]
                    self.eu_pipe_o_ready[dly] <<= self.eu_macro_lessthan_o_ready
                with Else():
                    self.eu_pipe_i_valid[dly] <<= self.eu_pipe_o_valid[(dly - 1)]
                    self.eu_pipe_o_ready[dly] <<= self.eu_pipe_i_ready[(dly + 1)]
            self.eu_pipe_en[dly] <<= (self.eu_pipe_i_valid[dly] & self.eu_pipe_i_ready[dly])
            self.eu_pipe_i_ready[dly] <<= ((~self.eu_pipe_o_valid[dly]) | self.eu_pipe_o_ready[dly])
            with If((~self.rstn)):
                self.eu_pipe_o_valid[dly] <<= 0
            with Else():
                with If(self.eu_pipe_i_ready[dly]):
                    self.eu_pipe_o_valid[dly] <<= self.eu_pipe_i_valid[dly]
                with Else():
                    self.eu_pipe_o_valid[dly] <<= self.eu_pipe_o_valid[dly]
            with If((dly == 0)):
                self.eu_macro_lessthan_tmp[dly] <<= 0
                self.eu_macro_lessthan_tmp[dly][(dly * self.SEGMENT)] <<= (self.eu_macro_lessthan_condition[(dly * self.SEGMENT)] & self.eu_macro_lessthan_data_y[(dly * self.SEGMENT)])
                # for-loop (non-generate) - parameter-driven
                for seg in range(1, self.SEGMENT):
                    self.eu_macro_lessthan_tmp[dly][((dly * self.SEGMENT) + seg)] <<= Mux(self.eu_macro_lessthan_condition[((dly * self.SEGMENT) + seg)], self.eu_macro_lessthan_data_y[((dly * self.SEGMENT) + seg)], self.eu_macro_lessthan_tmp[dly][(((dly * self.SEGMENT) + seg) - 1)])
                with If(self.eu_pipe_en[dly]):
                    self.eu_macro_lessthan_isa_r[dly] <<= self.eu_macro_lessthan_isa
                    self.eu_macro_lessthan_cc_value_r[dly] <<= self.eu_macro_lessthan_cc_value
                    self.eu_macro_lessthan_vm_id_r[dly] <<= self.eu_macro_lessthan_i_vm_id
                    self.eu_macro_lessthan_data_y_r[dly] <<= Cat(Rep(Cat(0), ((self.DELAY * self.SEGMENT) - self.DATA_WIDTH)), self.eu_macro_lessthan_data_y[(self.DATA_WIDTH - 1):0])
                    self.eu_macro_lessthan_condition_r[dly] <<= self.eu_macro_lessthan_condition
                    self.eu_macro_lessthan_tmp_r[dly] <<= self.eu_macro_lessthan_tmp[dly]
            with Else():
                self.eu_macro_lessthan_tmp[dly] <<= self.eu_macro_lessthan_tmp_r[(dly - 1)]
                self.eu_macro_lessthan_tmp[dly][(dly * self.SEGMENT)] <<= Mux(self.eu_macro_lessthan_condition_r[(dly - 1)][(dly * self.SEGMENT)], self.eu_macro_lessthan_data_y_r[(dly - 1)][(dly * self.SEGMENT)], self.eu_macro_lessthan_tmp_r[(dly - 1)][((dly * self.SEGMENT) - 1)])
                # for-loop (non-generate) - parameter-driven
                for seg in range(1, self.SEGMENT):
                    self.eu_macro_lessthan_tmp[dly][((dly * self.SEGMENT) + seg)] <<= Mux(self.eu_macro_lessthan_condition_r[(dly - 1)][((dly * self.SEGMENT) + seg)], self.eu_macro_lessthan_data_y_r[(dly - 1)][((dly * self.SEGMENT) + seg)], self.eu_macro_lessthan_tmp[dly][(((dly * self.SEGMENT) + seg) - 1)])
                with If(self.eu_pipe_en[dly]):
                    self.eu_macro_lessthan_isa_r[dly] <<= self.eu_macro_lessthan_isa_r[(dly - 1)]
                    self.eu_macro_lessthan_cc_value_r[dly] <<= self.eu_macro_lessthan_cc_value_r[(dly - 1)]
                    self.eu_macro_lessthan_vm_id_r[dly] <<= self.eu_macro_lessthan_vm_id_r[(dly - 1)]
                    self.eu_macro_lessthan_data_y_r[dly] <<= self.eu_macro_lessthan_data_y_r[(dly - 1)]
                    self.eu_macro_lessthan_condition_r[dly] <<= self.eu_macro_lessthan_condition_r[(dly - 1)]
                    self.eu_macro_lessthan_tmp_r[dly] <<= self.eu_macro_lessthan_tmp[dly]
