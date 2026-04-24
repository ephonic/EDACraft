"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class mult(Module):
    def __init__(self, name: str = "mult"):
        super().__init__(name or "mult")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_i = Input(1, "valid_i")
        self.ready_o = Output(1, "ready_o")
        self.mul_full_in = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "mul_full_in")
        self.mul_full_out = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "mul_full_out")
        self.mul_vm_id_in = Input(4, "mul_vm_id_in")
        self.mul_vm_id_out = Output(4, "mul_vm_id_out")
        self.valid_o = Output(1, "valid_o")
        self.ready_i = Input(1, "ready_i")

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
        self.stage1_multiplicand = Wire(128, "stage1_multiplicand")
        self.stage1_multiplier = Wire(128, "stage1_multiplier")
        self.abs_multiplicand = Reg(128, "abs_multiplicand")
        self.abs_multiplier = Reg(128, "abs_multiplier")
        self.multiplicand_sign = Reg(1, "multiplicand_sign")
        self.multiplier_sign = Reg(1, "multiplier_sign")
        self.product_sign = Reg(1, "product_sign")
        self.signed_mode_reg_stage1 = Reg(1, "signed_mode_reg_stage1")
        self.valid_stage1 = Reg(1, "valid_stage1")
        self.ready_stage1 = Reg(1, "ready_stage1")
        self.stage2_product = Reg(256, "stage2_product")
        self.signed_mode_reg_stage2 = Reg(1, "signed_mode_reg_stage2")
        self.product_sign_stage2 = Reg(1, "product_sign_stage2")
        self.valid_stage2 = Reg(1, "valid_stage2")
        self.ready_stage2 = Reg(1, "ready_stage2")
        self.stage3_product = Reg(128, "stage3_product")
        self.product_sign_stage3 = Reg(1, "product_sign_stage3")
        self.valid_stage3 = Reg(1, "valid_stage3")
        self.ready_stage3 = Reg(1, "ready_stage3")
        self.ready_stage4 = Reg(1, "ready_stage4")

        # TODO: unpack assignment: Cat(self.int_and_isa, self.int_and_cc_value, self.int_and_data_y, self.int_and_data_x) = self.mul_full_in
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.int_and_isa
        # Consider using Split() or manual bit slicing
        self.flag_bits <<= self.src0_fmt[(self.ISA_SRC0_FMT_BITS - 1):1]
        self.signed_mode <<= self.src0_fmt[0]
        self.multiplicand <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.int_and_data_x[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 120), self.int_and_data_x[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.int_and_data_x[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 112), self.int_and_data_x[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.int_and_data_x[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 96), self.int_and_data_x[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.int_and_data_x[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 64), self.int_and_data_x[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.int_and_data_x[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.int_and_data_x[127:0], 0))))))))))
        self.multiplier <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.int_and_data_y[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 120), self.int_and_data_y[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.int_and_data_y[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 112), self.int_and_data_y[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.int_and_data_y[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 96), self.int_and_data_y[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.int_and_data_y[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 64), self.int_and_data_y[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.int_and_data_y[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.int_and_data_y[127:0], 0))))))))))

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.abs_multiplicand <<= 0
                self.abs_multiplier <<= 0
                self.product_sign <<= 0
                self.signed_mode_reg_stage1 <<= 0
                self.valid_stage1 <<= 0
                self.mul_full_stage1 <<= 0
                self.vm_id_stage1 <<= 0
            with Else():
                with If((self.valid_i & self.ready_stage1)):
                    self.mul_full_stage1 <<= self.mul_full_in
                    self.vm_id_stage1 <<= self.mul_vm_id_in
                    self.signed_mode_reg_stage1 <<= self.signed_mode
                    self.valid_stage1 <<= 1
                    with If(self.signed_mode):
                        self.abs_multiplicand <<= Mux(self.multiplicand[127], ((not self.multiplicand) + 1), self.multiplicand)
                        self.abs_multiplier <<= Mux(self.multiplier[127], ((not self.multiplier) + 1), self.multiplier)
                        self.product_sign <<= (self.multiplicand[127] ^ self.multiplier[127])
                    with Else():
                        self.abs_multiplicand <<= self.multiplicand
                        self.abs_multiplier <<= self.multiplier
                        self.product_sign <<= 0
                with Else():
                    with If(self.ready_stage2):
                        self.valid_stage1 <<= 0
        self.stage1_multiplicand <<= self.abs_multiplicand
        self.stage1_multiplier <<= self.abs_multiplier

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.ready_o <<= 1
            with Else():
                self.ready_o <<= self.ready_stage1

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.stage2_product <<= 0
                self.signed_mode_reg_stage2 <<= 0
                self.product_sign_stage2 <<= 0
                self.valid_stage2 <<= 0
                self.mul_full_stage2 <<= 0
                self.vm_id_stage2 <<= 0
            with Else():
                with If((self.valid_stage1 & self.ready_stage2)):
                    self.mul_full_stage2 <<= self.mul_full_stage1
                    self.vm_id_stage2 <<= self.vm_id_stage1
                    self.stage2_product <<= (self.stage1_multiplicand * self.stage1_multiplier)
                    self.signed_mode_reg_stage2 <<= self.signed_mode_reg_stage1
                    self.product_sign_stage2 <<= self.product_sign
                    self.valid_stage2 <<= 1
                with Else():
                    with If(self.ready_stage3):
                        self.valid_stage2 <<= 0

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.stage3_product <<= 0
                self.product_sign_stage3 <<= 0
                self.valid_stage3 <<= 0
                self.mul_full_stage3 <<= 0
                self.vm_id_stage3 <<= 0
            with Else():
                with If((self.valid_stage2 & self.ready_stage3)):
                    with If((self.signed_mode_reg_stage2 & self.product_sign_stage2)):
                        self.stage3_product <<= ((not self.stage2_product[127:0]) + 1)
                    with Else():
                        self.stage3_product <<= self.stage2_product[127:0]
                    self.product_sign_stage3 <<= self.product_sign_stage2
                    self.valid_stage3 <<= 1
                    self.mul_full_stage3 <<= self.mul_full_stage2
                    self.vm_id_stage3 <<= self.vm_id_stage2
                with Else():
                    with If(self.ready_stage4):
                        self.valid_stage3 <<= 0

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.product <<= 0
                self.valid_o <<= 0
                self.mul_full_stage4 <<= 0
                self.vm_id_stage4 <<= 0
            with Else():
                with If((self.valid_stage3 & self.ready_stage4)):
                    self.product <<= self.stage3_product
                    self.valid_o <<= 1
                    self.mul_full_stage4 <<= self.mul_full_stage3
                    self.vm_id_stage4 <<= self.vm_id_stage3
                with Else():
                    with If(self.ready_i):
                        self.valid_o <<= 0
        self.ready_stage1 <<= ((~self.valid_stage1) | self.ready_stage2)
        self.ready_stage2 <<= ((~self.valid_stage2) | self.ready_stage3)
        self.ready_stage3 <<= ((~self.valid_stage3) | self.ready_stage4)
        self.ready_stage4 <<= ((~self.valid_o) | self.ready_i)
        # TODO: unpack assignment: Cat(self.int_and_isa_delay, self.int_and_cc_value_delay, self.int_and_data_y_delay, self.int_and_data_x_delay) = self.mul_full_in_delay
        # Consider using Split() or manual bit slicing
        self.flag_bits_delay <<= self.int_and_isa_delay[25:23]
        self.signed_mode_delay <<= self.int_and_isa_delay[23]
        self.res_valid_bits <<= Mux(((self.flag_bits_delay == 0) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 120), self.product[7:0]), Mux(((self.flag_bits_delay == 0) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 120), self.product[7:0]), Mux(((self.flag_bits_delay == 1) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 112), self.product[15:0]), Mux(((self.flag_bits_delay == 1) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 112), self.product[15:0]), Mux(((self.flag_bits_delay == 2) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 96), self.product[31:0]), Mux(((self.flag_bits_delay == 2) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 96), self.product[31:0]), Mux(((self.flag_bits_delay == 3) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 64), self.product[63:0]), Mux(((self.flag_bits_delay == 3) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 64), self.product[63:0]), Mux(((self.flag_bits_delay == 4) & (self.signed_mode_delay == 1)), self.product[127:0], Mux(((self.flag_bits_delay == 4) & (self.signed_mode_delay == 0)), self.product[127:0], 0))))))))))
        self.mul_full_in_delay <<= self.mul_full_stage4
        self.mul_vm_id_in_delay <<= self.vm_id_stage4
        self.mul_full_out <<= Cat(self.mul_full_in_delay[(((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1):((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - (self.ISA_BITS + 1))], Rep(Cat(0), (self.REG_WIDTH - 128)), self.res_valid_bits)
        self.mul_vm_id_out <<= self.mul_vm_id_in_delay
