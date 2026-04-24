"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class remainder(Module):
    def __init__(self, name: str = "remainder"):
        super().__init__(name or "remainder")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_i = Input(1, "valid_i")
        self.ready_o = Output(1, "ready_o")
        self.rem_full_in = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "rem_full_in")
        self.rem_full_out = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "rem_full_out")
        self.rem_vm_id_in = Input(4, "rem_vm_id_in")
        self.rem_vm_id_out = Output(4, "rem_vm_id_out")
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
        self.rem_full_in_reg = Reg(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "rem_full_in_reg")
        self.rem_full_delay = Reg(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "rem_full_delay")
        self.rem_vm_id_in_reg = Reg(4, "rem_vm_id_in_reg")
        self.rem_vm_id_delay = Reg(4, "rem_vm_id_delay")
        self.count = Reg(5, "count")
        self.done = Reg(1, "done")
        self.processing = Reg(1, "processing")

        # TODO: unpack assignment: Cat(self.int_and_isa, self.int_and_cc_value, self.int_and_data_y, self.int_and_data_x) = self.rem_full_in
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.int_and_isa
        # Consider using Split() or manual bit slicing
        self.flag_bits <<= self.src0_fmt[(self.ISA_SRC0_FMT_BITS - 1):1]
        self.signed_mode <<= self.src0_fmt[0]
        self.dividend <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.int_and_data_x[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 120), self.int_and_data_x[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.int_and_data_x[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 112), self.int_and_data_x[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.int_and_data_x[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 96), self.int_and_data_x[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.int_and_data_x[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 64), self.int_and_data_x[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.int_and_data_x[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.int_and_data_x[127:0], 0))))))))))
        self.divisor <<= Mux(((self.flag_bits == 0) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 120), self.int_and_data_y[7:0]), Mux(((self.flag_bits == 0) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 120), self.int_and_data_y[7:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 112), self.int_and_data_y[15:0]), Mux(((self.flag_bits == 1) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 112), self.int_and_data_y[15:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 96), self.int_and_data_y[31:0]), Mux(((self.flag_bits == 2) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 96), self.int_and_data_y[31:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 1)), Cat(Rep(Cat(0), 64), self.int_and_data_y[63:0]), Mux(((self.flag_bits == 3) & (self.signed_mode == 0)), Cat(Rep(Cat(1), 64), self.int_and_data_y[63:0]), Mux(((self.flag_bits == 4) & (self.signed_mode == 1)), self.int_and_data_y[127:0], Mux(((self.flag_bits == 4) & (self.signed_mode == 0)), self.int_and_data_y[127:0], 0))))))))))

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.ready_o <<= 1
            with Else():
                with If((self.valid_i & self.ready_o)):
                    self.ready_o <<= 0
                with Else():
                    with If((self.valid_o & self.ready_i)):
                        self.ready_o <<= 1

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.quotient <<= 0
                self.remainder <<= 0
                self.valid_o <<= 0
                self.done <<= 0
                self.count <<= 0
                self.processing <<= 0
                self.rem_full_in_reg <<= 0
                self.rem_vm_id_in_reg <<= 0
                self.partial_remainder <<= 0
                self.temp_quotient <<= 0
                self.shifted_divisor <<= 0
                self.rem_full_delay <<= 0
                self.rem_vm_id_delay <<= 0
            with Else():
                with If(((self.valid_i & self.ready_o) & (~self.processing))):
                    self.processing <<= 1
                    self.done <<= 0
                    self.count <<= 0
                    self.valid_o <<= 0
                    self.rem_full_in_reg <<= self.rem_full_in
                    self.rem_vm_id_in_reg <<= self.rem_vm_id_in
                    with If((self.divisor == 0)):
                        self.quotient <<= 0
                        self.remainder <<= 340282366920938463463374607431768211455
                        self.valid_o <<= 1
                        self.done <<= 1
                        self.processing <<= 0
                    with Else():
                        self.partial_remainder <<= Cat(0, self.abs_dividend)
                        self.temp_quotient <<= 0
                        self.shifted_divisor <<= (self.abs_divisor << 120)
                with Else():
                    with If((self.processing & (~self.done))):
                        with If((self.count <= 16)):
                            self.shifted_divisor <<= (self.abs_divisor << (128 - (8 * (self.count + 1))))
                            # for-loop (non-generate) - parameter-driven
                            for j in range(255, None):
                                with If(((self.partial_remainder >= (self.shifted_divisor * j)) & (self.partial_remainder < (self.shifted_divisor * (j + 1))))):
                                    self.partial_remainder <<= (self.partial_remainder - (self.shifted_divisor * j))
                                    self.temp_quotient <<= ((self.temp_quotient << 8) | j[7:0])
                            self.count <<= (self.count + 1)
                        with Else():
                            self.done <<= 1
                            self.processing <<= 0
                            self.count <<= 0
                            self.rem_full_delay <<= self.rem_full_in_reg
                            self.rem_vm_id_delay <<= self.rem_vm_id_in_reg
                            self.quotient <<= Mux(self.quotient_sign, ((not self.temp_quotient) + 1), self.temp_quotient)
                            self.remainder <<= Mux(self.dividend[127], ((not self.partial_remainder[127:0]) + 1), self.partial_remainder[127:0])
                            self.valid_o <<= 1
                    with Else():
                        with If((self.valid_o & self.ready_i)):
                            self.valid_o <<= 0
        self.abs_dividend <<= Mux(self.signed_mode, Mux(self.dividend[127], ((not self.dividend) + 1), self.dividend), self.dividend)
        self.abs_divisor <<= Mux(self.signed_mode, Mux(self.divisor[127], ((not self.divisor) + 1), self.divisor), self.divisor)
        self.quotient_sign <<= Mux(self.signed_mode, (self.dividend[127] ^ self.divisor[127]), 0)
        # TODO: unpack assignment: Cat(self.int_and_isa_delay, self.int_and_cc_value_delay, self.int_and_data_y_delay, self.int_and_data_x_delay) = self.rem_full_delay
        # Consider using Split() or manual bit slicing
        self.flag_bits_delay <<= self.int_and_isa_delay[25:23]
        self.signed_mode_delay <<= self.int_and_isa_delay[23]
        self.res_valid_bits <<= Mux(((self.flag_bits_delay == 0) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 120), self.remainder[7:0]), Mux(((self.flag_bits_delay == 0) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 120), self.remainder[7:0]), Mux(((self.flag_bits_delay == 1) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 112), self.remainder[15:0]), Mux(((self.flag_bits_delay == 1) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 112), self.remainder[15:0]), Mux(((self.flag_bits_delay == 2) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 96), self.remainder[31:0]), Mux(((self.flag_bits_delay == 2) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 96), self.remainder[31:0]), Mux(((self.flag_bits_delay == 3) & (self.signed_mode_delay == 1)), Cat(Rep(Cat(0), 64), self.remainder[63:0]), Mux(((self.flag_bits_delay == 3) & (self.signed_mode_delay == 0)), Cat(Rep(Cat(1), 64), self.remainder[63:0]), Mux(((self.flag_bits_delay == 4) & (self.signed_mode_delay == 1)), self.remainder[127:0], Mux(((self.flag_bits_delay == 4) & (self.signed_mode_delay == 0)), self.remainder[127:0], 0))))))))))
        self.rem_full_out <<= Cat(self.rem_full_delay[(((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1):((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - (self.ISA_BITS + 1))], Rep(Cat(0), (self.REG_WIDTH - 128)), self.res_valid_bits)
        self.rem_vm_id_out <<= self.rem_vm_id_delay
