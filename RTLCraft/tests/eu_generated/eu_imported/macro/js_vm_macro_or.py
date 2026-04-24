"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_macro_or(Module):
    def __init__(self, name: str = "js_vm_macro_or"):
        super().__init__(name or "js_vm_macro_or")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.eu_macro_or_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "eu_macro_or_data")
        self.eu_macro_or_i_valid = Input(1, "eu_macro_or_i_valid")
        self.eu_macro_or_i_vm_id = Input(4, "eu_macro_or_i_vm_id")
        self.eu_macro_or_o_ready = Input(1, "eu_macro_or_o_ready")
        self.eu_macro_or_i_ready = Output(1, "eu_macro_or_i_ready")
        self.eu_macro_or_o_valid = Output(1, "eu_macro_or_o_valid")
        self.eu_macro_or_o_vm_id = Output(4, "eu_macro_or_o_vm_id")
        self.eu_macro_or_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "eu_macro_or_res")

        # TODO: unpack assignment: Cat(self.eu_macro_or_isa, self.eu_macro_or_cc_value, self.eu_macro_or_data_y, self.eu_macro_or_data_x) = self.eu_macro_or_data
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.eu_macro_or_isa
        # Consider using Split() or manual bit slicing
        self.eu_macro_or_data_tmp <<= (self.eu_macro_or_data_y[(self.DATA_WIDTH - 1):0] | self.eu_macro_or_data_x[(self.DATA_WIDTH - 1):0])
        self.eu_pipe_en <<= (self.eu_macro_or_i_valid & self.eu_macro_or_i_ready)
        self.bit_nums <<= Mux((self.src0_fmt == 10), self.src0_imm, Mux(((self.src0_fmt == 0) | (self.src0_fmt == 1)), 8, Mux(((self.src0_fmt == 2) | (self.src0_fmt == 3)), 16, Mux(((self.src0_fmt == 4) | (self.src0_fmt == 5)), 32, Mux(((self.src0_fmt == 6) | (self.src0_fmt == 7)), 64, Mux(((self.src0_fmt == 8) | (self.src0_fmt == 9)), 128, 0))))))
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.eu_macro_or_res_tmp[i] <<= Mux((i < self.bit_nums), self.eu_macro_or_data_tmp[i], 0)

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.eu_pipe_en):
                self.eu_macro_or_res <<= Cat(self.eu_macro_or_isa, self.eu_macro_or_cc_value, Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.eu_macro_or_res_tmp)
                self.eu_macro_or_o_vm_id <<= self.eu_macro_or_i_vm_id
        self.eu_macro_or_i_ready <<= ((~self.eu_macro_or_o_valid) | self.eu_macro_or_o_ready)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.eu_macro_or_o_valid <<= 0
            with Else():
                with If(self.eu_macro_or_i_ready):
                    self.eu_macro_or_o_valid <<= self.eu_macro_or_i_valid
                with Else():
                    self.eu_macro_or_o_valid <<= self.eu_macro_or_o_valid
