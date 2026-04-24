"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_int_alu(Module):
    def __init__(self, name: str = "js_int_alu"):
        super().__init__(name or "js_int_alu")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.valid_i = Input(1, "valid_i")
        self.vm_id_i = Input(4, "vm_id_i")
        self.data_i = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "data_i")
        self.ready_i = Output(1, "ready_i")
        self.valid_o = Output(1, "valid_o")
        self.ready_o = Input(1, "ready_o")
        self.data_o = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "data_o")
        self.vm_id_o = Output(4, "vm_id_o")

        self.valid_p1 = Reg(1, "valid_p1")
        self.valid_p2 = Reg(1, "valid_p2")
        self.valid_p3 = Reg(1, "valid_p3")
        self.ready_p1 = Wire(1, "ready_p1")
        self.ready_p2 = Wire(1, "ready_p2")
        self.ready_p3 = Wire(1, "ready_p3")
        self.en0 = Wire(1, "en0")
        self.en1 = Wire(1, "en1")
        self.en2 = Wire(1, "en2")
        self.en3 = Wire(1, "en3")
        self.optype = Wire(((self.ISA_OPTYPE_BITS - 1) - 0 + 1), "optype")
        self.opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "opcode")
        self.cc_reg = Wire(((self.ISA_CC_BITS - 1) - 0 + 1), "cc_reg")
        self.sf = Wire(((self.ISA_SF_BITS - 1) - 0 + 1), "sf")
        self.wf = Wire(((self.ISA_WF_BITS - 1) - 0 + 1), "wf")
        self.src0_reg = Wire(((self.ISA_SRC0_REG_BITS - 1) - 0 + 1), "src0_reg")
        self.src0_type = Wire(((self.ISA_SRC0_TYPE_BITS - 1) - 0 + 1), "src0_type")
        self.src0_fmt = Wire(((self.ISA_SRC0_FMT_BITS - 1) - 0 + 1), "src0_fmt")
        self.src0_imm = Wire(((self.ISA_SRC0_IMM_BITS - 1) - 0 + 1), "src0_imm")
        self.src1_reg = Wire(((self.ISA_SRC1_REG_BITS - 1) - 0 + 1), "src1_reg")
        self.src1_type = Wire(((self.ISA_SRC1_TYPE_BITS - 1) - 0 + 1), "src1_type")
        self.src1_fmt = Wire(((self.ISA_SRC1_FMT_BITS - 1) - 0 + 1), "src1_fmt")
        self.src1_imm = Wire(((self.ISA_SRC1_IMM_BITS - 1) - 0 + 1), "src1_imm")
        self.dst0_reg = Wire(((self.ISA_DST0_REG_BITS - 1) - 0 + 1), "dst0_reg")
        self.dst1_reg = Wire(((self.ISA_DST1_REG_BITS - 1) - 0 + 1), "dst1_reg")
        self.dst_type = Wire(((self.ISA_DST_TYPE_BITS - 1) - 0 + 1), "dst_type")
        self.dst_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "dst_fmt")
        self.rsv = Wire(((self.ISA_RSV_BITS - 1) - 0 + 1), "rsv")
        self.operand_a_sign = Wire(1, "operand_a_sign")
        self.operand_b_sign = Wire(1, "operand_b_sign")
        self.a_abs = Wire(128, "a_abs")
        self.b_abs = Wire(128, "b_abs")
        self.b_neg = Wire(128, "b_neg")
        self.is_mult = Wire(1, "is_mult")
        self.is_add = Wire(1, "is_add")
        self.is_sub = Wire(1, "is_sub")
        self.op_a_p1 = Reg(128, "op_a_p1")
        self.op_b_p1 = Reg(128, "op_b_p1")
        self.op_a_sign_p1 = Reg(1, "op_a_sign_p1")
        self.op_b_sign_p1 = Reg(1, "op_b_sign_p1")
        self.alu_isa_p1 = Reg(((self.ISA_BITS - 1) - 0 + 1), "alu_isa_p1")
        self.opcode_p1 = Reg(3, "opcode_p1")
        self.flag_p1 = Reg(3, "flag_p1")
        self.vm_id_p1 = Reg(4, "vm_id_p1")
        self.is_add_p1 = Wire(1, "is_add_p1")
        self.is_sub_p1 = Wire(1, "is_sub_p1")
        self.is_mul_p1 = Wire(1, "is_mul_p1")
        self.ab_add_res = Wire(128, "ab_add_res")
        self.ab_mul_00 = Wire(128, "ab_mul_00")
        self.ab_mul_01 = Wire(128, "ab_mul_01")
        self.ab_mul_10 = Wire(128, "ab_mul_10")
        self.ab_mul_11 = Wire(128, "ab_mul_11")
        self.ab_mul_sign = Wire(1, "ab_mul_sign")
        self.ab_mul_sign_p2 = Reg(1, "ab_mul_sign_p2")
        self.ab_tmp_00_p2 = Reg(128, "ab_tmp_00_p2")
        self.ab_tmp_01_p2 = Reg(128, "ab_tmp_01_p2")
        self.ab_tmp_10_p2 = Reg(128, "ab_tmp_10_p2")
        self.ab_tmp_11_p2 = Reg(128, "ab_tmp_11_p2")
        self.alu_isa_p2 = Reg(((self.ISA_BITS - 1) - 0 + 1), "alu_isa_p2")
        self.opcode_p2 = Reg(3, "opcode_p2")
        self.flag_p2 = Reg(3, "flag_p2")
        self.vm_id_p2 = Reg(4, "vm_id_p2")
        self.is_mul_p2 = Wire(1, "is_mul_p2")
        self.ab_mul_tmp = Wire(256, "ab_mul_tmp")
        self.ab_op_res = Wire(256, "ab_op_res")
        self.ab_res_p3 = Reg(256, "ab_res_p3")
        self.alu_isa_p3 = Reg(((self.ISA_BITS - 1) - 0 + 1), "alu_isa_p3")
        self.flag_p3 = Reg(3, "flag_p3")
        self.vm_id_p3 = Reg(4, "vm_id_p3")
        self.alu_res = Wire(128, "alu_res")


        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.valid_p1 <<= 0
                self.valid_p2 <<= 0
                self.valid_p3 <<= 0
            with Else():
                with If(self.ready_i):
                    self.valid_p1 <<= self.valid_i
                with If(self.ready_p1):
                    self.valid_p2 <<= self.valid_p1
                with If(self.ready_p2):
                    self.valid_p3 <<= self.valid_p2
        self.ready_i <<= (self.ready_p1 | (~self.valid_p1))
        self.ready_p1 <<= (self.ready_p2 | (~self.valid_p2))
        self.ready_p2 <<= (self.ready_p3 | (~self.valid_p3))
        self.ready_p3 <<= self.ready_o
        self.valid_o <<= self.valid_p3
        self.en0 <<= (self.valid_i & self.ready_i)
        self.en1 <<= (self.valid_p1 & self.ready_p1)
        self.en2 <<= (self.valid_p2 & self.ready_p2)
        self.en3 <<= (self.valid_p3 & self.ready_p3)
        # TODO: unpack assignment: Cat(self.alu_isa, self.alu_cc_value, self.src1_data, self.src0_data) = self.data_i
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.alu_isa
        # Consider using Split() or manual bit slicing
        self.flag_bits <<= self.src0_fmt[(self.ISA_SRC0_FMT_BITS - 1):1]
        self.signed_mode <<= self.src0_fmt[0]
        self.operand_a <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.src0_data[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src0_data[7]), 120), self.src0_data[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.src0_data[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src0_data[15]), 112), self.src0_data[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.src0_data[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src0_data[31]), 96), self.src0_data[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.src0_data[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src0_data[63]), 64), self.src0_data[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.src0_data[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.src0_data[127:0], 0))))))))))
        self.operand_b <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.src1_data[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src1_data[7]), 120), self.src1_data[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.src1_data[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src1_data[15]), 112), self.src1_data[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.src1_data[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src1_data[31]), 96), self.src1_data[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.src1_data[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(self.src1_data[63]), 64), self.src1_data[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.src1_data[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.src1_data[127:0], 0))))))))))

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en0):
                self.op_a_sign_p1 <<= self.operand_a_sign
                self.op_b_sign_p1 <<= self.operand_b_sign
                self.op_a_p1 <<= Mux(self.is_mult, self.a_abs, self.operand_a)
                self.op_b_p1 <<= Mux(self.is_mult, self.b_abs, Mux(self.is_sub, self.b_neg, self.operand_b))
                self.alu_isa_p1 <<= self.alu_isa
                self.opcode_p1 <<= self.opcode
                self.flag_p1 <<= self.flag_bits
                self.vm_id_p1 <<= self.vm_id_i

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en1):
                self.ab_mul_sign_p2 <<= self.ab_mul_sign
                self.ab_tmp_00_p2 <<= Mux(self.is_mul_p1, self.ab_mul_00, self.ab_add_res)
                self.ab_tmp_01_p2 <<= self.ab_mul_01
                self.ab_tmp_10_p2 <<= self.ab_mul_10
                self.ab_tmp_11_p2 <<= self.ab_mul_11
                self.alu_isa_p2 <<= self.alu_isa_p1
                self.opcode_p2 <<= self.opcode_p1
                self.flag_p2 <<= self.flag_p1
                self.vm_id_p2 <<= self.vm_id_p1

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en2):
                self.ab_res_p3 <<= self.ab_op_res
                self.alu_isa_p3 <<= self.alu_isa_p2
                self.flag_p3 <<= self.flag_p2
                self.vm_id_p3 <<= self.vm_id_p2
        self.alu_res <<= Mux((self.flag_p3 == 0), Cat(0, self.ab_res_p3[7:0]), Mux((self.flag_p3 == 1), Cat(0, self.ab_res_p3[15:0]), Mux((self.flag_p3 == 2), Cat(0, self.ab_res_p3[31:0]), Mux((self.flag_p3 == 3), Cat(0, self.ab_res_p3[63:0]), Mux((self.flag_p3 == 4), self.ab_res_p3[127:0], 0)))))
        self.data_o <<= Cat(self.alu_isa_p3, 0, Rep(Cat(0), (self.REG_WIDTH - 128)), self.alu_res)
        self.vm_id_o <<= self.vm_id_p3
