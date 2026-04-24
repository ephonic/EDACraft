"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class divider_core(Module):
    def __init__(self, name: str = "divider_core"), IDLE: int = 0, PRE_PROCESSING: int = 1, PROCESSING: int = 2, OUTPUT: int = 3:
        super().__init__(name or "divider_core")

        self.add_localparam("IDLE", 0)
        self.add_localparam("PRE_PROCESSING", 1)
        self.add_localparam("PROCESSING", 2)
        self.add_localparam("OUTPUT", 3)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_i = Input(1, "valid_i")
        self.ready_o = Output(1, "ready_o")
        self.valid_o = Output(1, "valid_o")
        self.ready_i = Input(1, "ready_i")
        self.flags_src0 = Input(3, "flags_src0")
        self.flags_src1 = Input(3, "flags_src1")
        self.signed_mode_src0 = Input(1, "signed_mode_src0")
        self.signed_mode_src1 = Input(1, "signed_mode_src1")
        self.src0 = Input(128, "src0")
        self.src1 = Input(128, "src1")
        self.vm_id_in = Input(4, "vm_id_in")
        self.div_full_in = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "div_full_in")
        self.div_full_out = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "div_full_out")
        self.vm_id_out = Output(4, "vm_id_out")

        self.res = Reg(128, "res")
        self.state = Reg(2, "state")
        self.state_nxt = Reg(2, "state_nxt")
        self.dividend = Reg(128, "dividend")
        self.divisor = Reg(128, "divisor")
        self.abs_dividend = Reg(128, "abs_dividend")
        self.abs_divisor = Reg(128, "abs_divisor")
        self.partial_remainder = Reg(256, "partial_remainder")
        self.partial_remainder_nxt = Reg(256, "partial_remainder_nxt")
        self.shifted_divisor = Reg(256, "shifted_divisor")
        self.temp_quotient = Reg(128, "temp_quotient")
        self.temp_quotient_nxt = Reg(128, "temp_quotient_nxt")
        self.total_count = Reg(9, "total_count")
        self.count = Reg(9, "count")
        self.count_nxt = Reg(9, "count_nxt")
        self.sign_src0 = Reg(1, "sign_src0")
        self.sign_src1 = Reg(1, "sign_src1")
        self.res_tmp = Reg(128, "res_tmp")
        self.output_sign = Reg(1, "output_sign")
        self.src0_sign_ext = Reg(1, "src0_sign_ext")
        self.src1_sign_ext = Reg(1, "src1_sign_ext")
        self.data_8 = Reg(8, "data_8")
        self.data_16 = Reg(16, "data_16")
        self.data_32 = Reg(32, "data_32")
        self.data_64 = Reg(64, "data_64")


        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.state <<= self.IDLE
                self.partial_remainder <<= 0
                self.temp_quotient <<= 0
                self.count <<= 0
            with Else():
                self.state <<= self.state_nxt
                self.partial_remainder <<= self.partial_remainder_nxt
                self.temp_quotient <<= self.temp_quotient_nxt
                self.count <<= self.count_nxt

        @self.comb
        def _comb_logic():
            self.sign_src0 <<= 0
            self.sign_src1 <<= 0
            self.dividend <<= 0
            self.abs_dividend <<= 0
            self.total_count <<= 0
            self.divisor <<= 0
            self.abs_divisor <<= 0
            self.src0_sign_ext <<= 0
            self.src1_sign_ext <<= 0
            self.data_8 <<= 0
            self.data_16 <<= 0
            self.data_32 <<= 0
            self.data_64 <<= 0
            with Switch(self.flags_src0) as sw:
                with sw.case(0):
                    self.sign_src0 <<= self.src0[7]
                    self.src0_sign_ext <<= Mux(self.signed_mode_src0, self.sign_src0, 0)
                    self.dividend <<= Cat(Rep(Cat(self.src0_sign_ext), 120), self.src0[7:0])
                    self.data_8 <<= Mux((~self.signed_mode_src0), Mux(self.sign_src0, ((not self.src0[7:0]) + 1), self.src0[7:0]), self.src0[7:0])
                    self.abs_dividend <<= Cat(0, self.data_8)
                    self.total_count <<= 4
                with sw.case(1):
                    self.sign_src0 <<= self.src0[15]
                    self.src0_sign_ext <<= Mux(self.signed_mode_src0, self.sign_src0, 0)
                    self.dividend <<= Cat(Rep(Cat(self.src0_sign_ext), 112), self.src0[15:0])
                    self.data_16 <<= Mux((~self.signed_mode_src0), Mux(self.sign_src0, ((not self.src0[15:0]) + 1), self.src0[15:0]), self.src0[15:0])
                    self.abs_dividend <<= Cat(0, self.data_16)
                    self.total_count <<= 8
                with sw.case(2):
                    self.sign_src0 <<= self.src0[31]
                    self.src0_sign_ext <<= Mux(self.signed_mode_src0, self.sign_src0, 0)
                    self.dividend <<= Cat(Rep(Cat(self.src0_sign_ext), 96), self.src0[31:0])
                    self.data_32 <<= Mux((~self.signed_mode_src0), Mux(self.sign_src0, ((not self.src0[31:0]) + 1), self.src0[31:0]), self.src0[31:0])
                    self.abs_dividend <<= Cat(0, self.data_32)
                    self.total_count <<= 16
                with sw.case(3):
                    self.sign_src0 <<= self.src0[63]
                    self.src0_sign_ext <<= Mux(self.signed_mode_src0, self.sign_src0, 0)
                    self.dividend <<= Cat(Rep(Cat(self.src0_sign_ext), 64), self.src0[63:0])
                    self.data_64 <<= Mux((~self.signed_mode_src0), Mux(self.sign_src0, ((not self.src0[63:0]) + 1), self.src0[63:0]), self.src0[63:0])
                    self.abs_dividend <<= Cat(0, self.data_64)
                    self.total_count <<= 32
                with sw.case(4):
                    self.sign_src0 <<= self.src0[127]
                    self.dividend <<= self.src0
                    self.abs_dividend <<= Mux((~self.signed_mode_src0), Mux(self.sign_src0, ((not self.src0) + 1), self.src0), self.src0)
                    self.total_count <<= 64
            with Switch(self.flags_src1) as sw:
                with sw.case(0):
                    self.sign_src1 <<= self.src1[7]
                    self.src1_sign_ext <<= Mux(self.signed_mode_src1, self.sign_src1, 0)
                    self.divisor <<= Cat(Rep(Cat(self.src1_sign_ext), 120), self.src1[7:0])
                    self.data_8 <<= Mux((~self.signed_mode_src1), Mux(self.sign_src1, ((not self.src1[7:0]) + 1), self.src1[7:0]), self.src1[7:0])
                    self.abs_divisor <<= Cat(0, self.data_8)
                with sw.case(1):
                    self.sign_src1 <<= self.src1[15]
                    self.src1_sign_ext <<= Mux(self.signed_mode_src1, self.sign_src1, 0)
                    self.divisor <<= Cat(Rep(Cat(self.src1_sign_ext), 112), self.src1[15:0])
                    self.data_16 <<= Mux((~self.signed_mode_src1), Mux(self.sign_src1, ((not self.src1[15:0]) + 1), self.src1[15:0]), self.src1[15:0])
                    self.abs_divisor <<= Cat(0, self.data_16)
                with sw.case(2):
                    self.sign_src1 <<= self.src1[31]
                    self.src1_sign_ext <<= Mux(self.signed_mode_src1, self.sign_src1, 0)
                    self.divisor <<= Cat(Rep(Cat(self.src1_sign_ext), 96), self.src1[31:0])
                    self.data_32 <<= Mux((~self.signed_mode_src1), Mux(self.sign_src1, ((not self.src1[31:0]) + 1), self.src1[31:0]), self.src1[31:0])
                    self.abs_divisor <<= Cat(0, self.data_32)
                with sw.case(3):
                    self.sign_src1 <<= self.src1[63]
                    self.src1_sign_ext <<= Mux(self.signed_mode_src1, self.sign_src1, 0)
                    self.divisor <<= Cat(Rep(Cat(self.src1_sign_ext), 64), self.src1[63:0])
                    self.data_64 <<= Mux((~self.signed_mode_src1), Mux(self.sign_src1, ((not self.src1[63:0]) + 1), self.src1[63:0]), self.src1[63:0])
                    self.abs_divisor <<= Cat(0, self.data_64)
                with sw.case(4):
                    self.sign_src1 <<= self.src1[127]
                    self.divisor <<= self.src1
                    self.abs_divisor <<= Mux((~self.signed_mode_src1), Mux(self.sign_src1, ((not self.src1) + 1), self.src1), self.src1)

        @self.comb
        def _comb_logic():
            self.state_nxt <<= self.state
            self.partial_remainder_nxt <<= self.partial_remainder
            self.temp_quotient_nxt <<= self.temp_quotient
            self.count_nxt <<= self.count
            self.vm_id_out <<= self.vm_id_in
            self.valid_o <<= 0
            self.ready_o <<= 0
            self.shifted_divisor <<= 0
            self.res <<= 0
            with Switch(self.state) as sw:
                with sw.case(self.IDLE):
                    self.temp_quotient_nxt <<= 0
                    with If(self.valid_i):
                        self.state_nxt <<= self.PRE_PROCESSING
                with sw.case(self.PRE_PROCESSING):
                    self.partial_remainder_nxt <<= Cat(0, self.abs_dividend)
                    with If((self.abs_divisor == 0)):
                        self.res <<= 0
                        self.valid_o <<= 1
                        with If(self.ready_i):
                            self.state_nxt <<= self.IDLE
                            self.ready_o <<= 1
                        self.vm_id_out <<= self.vm_id_in
                    with Else():
                        self.state_nxt <<= self.PROCESSING
                        self.count_nxt <<= 0
                with sw.case(self.PROCESSING):
                    with If((self.count < self.total_count)):
                        self.shifted_divisor <<= (self.abs_divisor << ((self.total_count * 2) - (2 * (self.count + 1))))
                        with If((self.partial_remainder >= (self.shifted_divisor * 3))):
                            self.partial_remainder_nxt <<= (self.partial_remainder - (self.shifted_divisor * 3))
                            self.temp_quotient_nxt <<= ((self.temp_quotient << 2) | 3)
                        with Else():
                            with If((self.partial_remainder >= (self.shifted_divisor * 2))):
                                self.partial_remainder_nxt <<= (self.partial_remainder - (self.shifted_divisor * 2))
                                self.temp_quotient_nxt <<= ((self.temp_quotient << 2) | 2)
                            with Else():
                                with If((self.partial_remainder >= (self.shifted_divisor * 1))):
                                    self.partial_remainder_nxt <<= (self.partial_remainder - (self.shifted_divisor * 1))
                                    self.temp_quotient_nxt <<= ((self.temp_quotient << 2) | 1)
                                with Else():
                                    self.partial_remainder_nxt <<= self.partial_remainder
                                    self.temp_quotient_nxt <<= (self.temp_quotient << 2)
                        self.count_nxt <<= (self.count + 1)
                        self.state_nxt <<= self.PROCESSING
                    with Else():
                        self.state_nxt <<= self.OUTPUT
                with sw.case(self.OUTPUT):
                    self.output_sign <<= (Mux((~self.signed_mode_src0), self.sign_src0, 0) ^ Mux((~self.signed_mode_src1), self.sign_src1, 0))
                    self.res_tmp <<= Mux(self.output_sign, ((not self.temp_quotient) + 1), self.temp_quotient)
                    with Switch(self.flags_src0) as sw:
                        with sw.case(0):
                            self.res <<= Cat(0, self.res_tmp[7:0])
                        with sw.case(1):
                            self.res <<= Cat(0, self.res_tmp[15:0])
                        with sw.case(2):
                            self.res <<= Cat(0, self.res_tmp[31:0])
                        with sw.case(3):
                            self.res <<= Cat(0, self.res_tmp[63:0])
                        with sw.case(4):
                            self.res <<= self.res_tmp
                    self.valid_o <<= 1
                    with If(self.ready_i):
                        self.state_nxt <<= self.IDLE
                        self.ready_o <<= 1
                    self.vm_id_out <<= self.vm_id_in
        self.div_full_out <<= Cat(self.div_full_in[(((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1):((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - (self.ISA_BITS + 1))], Rep(Cat(0), (self.REG_WIDTH - 128)), self.res)
