"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_modadd(Module):
    def __init__(self, name: str = "js_vm_modadd"), PART: int = 4, SEG_WIDTH: int = (((self.DATA_WIDTH + self.PART) - 1) // self.PART):
        super().__init__(name or "js_vm_modadd")

        self.add_localparam("PART", 4)
        self.add_localparam("SEG_WIDTH", (((self.DATA_WIDTH + self.PART) - 1) // self.PART))
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "data")
        self.q = Input(((self.DATA_WIDTH - 1) - 0 + 1), "q")
        self.i_vm_id = Input(4, "i_vm_id")
        self.i_valid = Input(1, "i_valid")
        self.o_ready = Input(1, "o_ready")
        self.o_vm_id = Output(4, "o_vm_id")
        self.o_valid = Output(1, "o_valid")
        self.i_ready = Output(1, "i_ready")
        self.res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "res")

        self.isa = Wire(((self.ISA_BITS - 1) - 0 + 1), "isa")
        self.cc_val = Wire(1, "cc_val")
        self.flag_bits = Wire((((self.REG_WIDTH - self.DATA_WIDTH) - 1) - 0 + 1), "flag_bits")
        self.s0_isa = Reg(((self.ISA_BITS - 1) - 0 + 1), "s0_isa")
        self.s0_cc_val = Reg(1, "s0_cc_val")
        self.s0_flag_bits = Reg((((self.REG_WIDTH - self.DATA_WIDTH) - 1) - 0 + 1), "s0_flag_bits")
        self.s0_vm_id = Reg(4, "s0_vm_id")
        self.s1_isa = Reg(((self.ISA_BITS - 1) - 0 + 1), "s1_isa")
        self.s1_cc_val = Reg(1, "s1_cc_val")
        self.s1_flag_bits = Reg((((self.REG_WIDTH - self.DATA_WIDTH) - 1) - 0 + 1), "s1_flag_bits")
        self.s1_vm_id = Reg(4, "s1_vm_id")
        self.a = Wire(((self.REG_WIDTH - 1) - 0 + 1), "a")
        self.b = Wire(((self.REG_WIDTH - 1) - 0 + 1), "b")
        self.a_ext = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "a_ext")
        self.b_ext = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "b_ext")
        self.q_ext = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "q_ext")
        self.q_ext_r = Reg((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "q_ext_r")
        self.a_segment = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "a_segment", vtype=Wire)
        self.b_segment = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "b_segment", vtype=Wire)
        self.q_segment = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "q_segment", vtype=Wire)
        self.s0_sum_0 = Wire(((self.SEG_WIDTH - 1) - 0 + 1), "s0_sum_0")
        self.s0_sum_segment_0 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s0_sum_segment_0", vtype=Wire)
        self.s0_sum_segment_1 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s0_sum_segment_1", vtype=Wire)
        self.s0_carry_segment = Wire(((self.PART - 1) - 0 + 1), "s0_carry_segment")
        self.s0_carry_segment_0 = Wire(((self.PART - 2) - 0 + 1), "s0_carry_segment_0")
        self.s0_carry_segment_1 = Wire(((self.PART - 2) - 0 + 1), "s0_carry_segment_1")
        self.s0_sum_segment_r = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "s0_sum_segment_r", vtype=Reg)
        self.s0_carry_r = Reg(1, "s0_carry_r")
        self.s1_sum_1 = Wire(((self.SEG_WIDTH - 1) - 0 + 1), "s1_sum_1")
        self.s1_sum_segment_0 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s1_sum_segment_0", vtype=Wire)
        self.s1_sum_segment_1 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s1_sum_segment_1", vtype=Wire)
        self.s1_carry_segment = Wire(((self.PART - 1) - 0 + 1), "s1_carry_segment")
        self.s1_carry_segment_0 = Wire(((self.PART - 2) - 0 + 1), "s1_carry_segment_0")
        self.s1_carry_segment_1 = Wire(((self.PART - 2) - 0 + 1), "s1_carry_segment_1")
        self.s1_sum_segment_r = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "s1_sum_segment_r", vtype=Reg)
        self.res_tmp = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "res_tmp")
        self.pipe_en0 = Wire(1, "pipe_en0")
        self.pipe_en1 = Wire(1, "pipe_en1")
        self.pipe_i_valid0 = Wire(1, "pipe_i_valid0")
        self.pipe_i_ready0 = Wire(1, "pipe_i_ready0")
        self.pipe_o_valid0 = Reg(1, "pipe_o_valid0")
        self.pipe_o_ready0 = Wire(1, "pipe_o_ready0")
        self.pipe_i_valid1 = Wire(1, "pipe_i_valid1")
        self.pipe_i_ready1 = Wire(1, "pipe_i_ready1")
        self.pipe_o_valid1 = Reg(1, "pipe_o_valid1")
        self.pipe_o_ready1 = Wire(1, "pipe_o_ready1")

        # TODO: unpack assignment: Cat(self.isa, self.cc_val, self.b, self.a) = self.data
        # Consider using Split() or manual bit slicing
        self.flag_bits <<= self.a[(self.REG_WIDTH - 1):self.DATA_WIDTH]
        self.a_ext <<= Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.a)
        self.b_ext <<= Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.b)
        self.q_ext <<= (not Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.q))
        # for-loop (non-generate) - parameter-driven
        for part in range(0, self.PART):
            self.a_segment[part][(self.SEG_WIDTH - 1):0] <<= self.a_ext[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
            self.b_segment[part][(self.SEG_WIDTH - 1):0] <<= self.b_ext[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
            with If((part == 0)):
                # TODO: unpack assignment: Cat(self.s0_carry_segment[part], self.s0_sum_0) = (self.a_segment[part] + self.b_segment[part])
                # Consider using Split() or manual bit slicing
                with If(self.pipe_en0):
                    self.s0_sum_segment_r[part] <<= self.s0_sum_0
                with Else():
                    self.s0_sum_segment_r[part] <<= self.s0_sum_segment_r[part]
            with Else():
                # TODO: unpack assignment: Cat(self.s0_carry_segment_0[(part - 1)], self.s0_sum_segment_0[(part - 1)]) = (self.a_segment[part] + self.b_segment[part])
                # Consider using Split() or manual bit slicing
                # TODO: unpack assignment: Cat(self.s0_carry_segment_1[(part - 1)], self.s0_sum_segment_1[(part - 1)]) = ((self.a_segment[part] + self.b_segment[part]) + 1)
                # Consider using Split() or manual bit slicing
                self.s0_carry_segment[part] <<= Mux(self.s0_carry_segment[(part - 1)], self.s0_carry_segment_1[(part - 1)], self.s0_carry_segment_0[(part - 1)])
                with If((part == (self.PART - 1))):
                    with If(self.pipe_en0):
                        self.s0_carry_r <<= self.s0_carry_segment[part]
                    with Else():
                        self.s0_carry_r <<= self.s0_carry_r
                with If(self.pipe_en0):
                    self.s0_sum_segment_r[part] <<= Mux(self.s0_carry_segment[(part - 1)], self.s0_sum_segment_1[(part - 1)], self.s0_sum_segment_0[(part - 1)])
                with Else():
                    self.s0_sum_segment_r[part] <<= self.s0_sum_segment_r[part]

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.pipe_en0):
                self.q_ext_r <<= self.q_ext
                self.s0_isa <<= self.isa
                self.s0_cc_val <<= self.cc_val
                self.s0_flag_bits <<= self.flag_bits
                self.s0_vm_id <<= self.i_vm_id
            with Else():
                self.q_ext_r <<= self.q_ext_r
                self.s0_isa <<= self.s0_isa
                self.s0_cc_val <<= self.s0_cc_val
                self.s0_flag_bits <<= self.s0_flag_bits
                self.s0_vm_id <<= self.s0_vm_id
        # for-loop (non-generate) - parameter-driven
        for part in range(0, self.PART):
            self.q_segment[part][(self.SEG_WIDTH - 1):0] <<= self.q_ext_r[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
            with If((part == 0)):
                # TODO: unpack assignment: Cat(self.s1_carry_segment[part], self.s1_sum_1) = ((self.s0_sum_segment_r[part] + self.q_segment[part]) + 1)
                # Consider using Split() or manual bit slicing
                with If(self.pipe_en1):
                    self.s1_sum_segment_r[part] <<= Mux((self.s0_carry_r | self.s1_carry_segment[(self.PART - 1)]), self.s1_sum_1, self.s0_sum_segment_r[part])
                with Else():
                    self.s1_sum_segment_r[part] <<= self.s1_sum_segment_r[part]
            with Else():
                # TODO: unpack assignment: Cat(self.s1_carry_segment_0[(part - 1)], self.s1_sum_segment_0[(part - 1)]) = (self.s0_sum_segment_r[part] + self.q_segment[part])
                # Consider using Split() or manual bit slicing
                # TODO: unpack assignment: Cat(self.s1_carry_segment_1[(part - 1)], self.s1_sum_segment_1[(part - 1)]) = ((self.s0_sum_segment_r[part] + self.q_segment[part]) + 1)
                # Consider using Split() or manual bit slicing
                self.s1_carry_segment[part] <<= Mux(self.s1_carry_segment[(part - 1)], self.s1_carry_segment_1[(part - 1)], self.s1_carry_segment_0[(part - 1)])
                with If(self.pipe_en1):
                    self.s1_sum_segment_r[part] <<= Mux((self.s0_carry_r | self.s1_carry_segment[(self.PART - 1)]), Mux(self.s1_carry_segment[(part - 1)], self.s1_sum_segment_1[(part - 1)], self.s1_sum_segment_0[(part - 1)]), self.s0_sum_segment_r[part])
                with Else():
                    self.s1_sum_segment_r[part] <<= self.s1_sum_segment_r[part]
            self.res_tmp[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)] <<= self.s1_sum_segment_r[part]

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.pipe_en1):
                self.s1_isa <<= self.s0_isa
                self.s1_cc_val <<= self.s0_cc_val
                self.s1_flag_bits <<= self.s0_flag_bits
                self.s1_vm_id <<= self.s0_vm_id
            with Else():
                self.s1_isa <<= self.s1_isa
                self.s1_cc_val <<= self.s1_cc_val
                self.s1_flag_bits <<= self.s1_flag_bits
                self.s1_vm_id <<= self.s1_vm_id
        self.res <<= Cat(self.s1_isa, self.s1_cc_val, self.s1_flag_bits, self.res_tmp[(self.DATA_WIDTH - 1):0])
        self.o_vm_id <<= self.s1_vm_id
        self.pipe_en0 <<= (self.pipe_i_valid0 & self.pipe_i_ready0)
        self.pipe_en1 <<= (self.pipe_i_valid1 & self.pipe_i_ready1)
        self.pipe_i_valid0 <<= self.i_valid
        self.pipe_o_ready0 <<= self.pipe_i_ready1
        self.pipe_i_valid1 <<= self.pipe_o_valid0
        self.pipe_o_ready1 <<= self.o_ready
        self.pipe_i_ready0 <<= ((~self.pipe_o_valid0) | self.pipe_o_ready0)
        self.pipe_i_ready1 <<= ((~self.pipe_o_valid1) | self.pipe_o_ready1)
        self.i_ready <<= self.pipe_i_ready0
        self.o_valid <<= self.pipe_o_valid1

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.pipe_o_valid0 <<= 0
            with Else():
                with If(self.pipe_i_ready0):
                    self.pipe_o_valid0 <<= self.pipe_i_valid0
                with Else():
                    self.pipe_o_valid0 <<= self.pipe_o_valid0

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.pipe_o_valid1 <<= 0
            with Else():
                with If(self.pipe_i_ready1):
                    self.pipe_o_valid1 <<= self.pipe_i_valid1
                with Else():
                    self.pipe_o_valid1 <<= self.pipe_o_valid1
