"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_modaddc(Module):
    def __init__(self, name: str = "js_vm_modaddc"), EXT_BITS: int = 8, PART: int = 4, SEG_WIDTH: int = ((((self.DATA_WIDTH + self.EXT_BITS) + self.PART) - 1) // self.PART):
        super().__init__(name or "js_vm_modaddc")

        self.add_localparam("EXT_BITS", 8)
        self.add_localparam("PART", 4)
        self.add_localparam("SEG_WIDTH", ((((self.DATA_WIDTH + self.EXT_BITS) + self.PART) - 1) // self.PART))
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
        self.s0_vm_id = Reg(4, "s0_vm_id")
        self.s0_b_is_one = Reg(1, "s0_b_is_one")
        self.s1_isa = Array(((self.ISA_BITS - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_isa", vtype=Reg)
        self.s1_cc_val = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "s1_cc_val", vtype=Reg)
        self.s1_vm_id = Array(4, ((self.EXT_BITS - 1) - 0 + 1), "s1_vm_id", vtype=Reg)
        self.s1_b_is_one = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "s1_b_is_one", vtype=Reg)
        self.a = Wire(((self.REG_WIDTH - 1) - 0 + 1), "a")
        self.b = Wire(((self.REG_WIDTH - 1) - 0 + 1), "b")
        self.a_ext = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "a_ext")
        self.b_ext = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "b_ext")
        self.q_redc_ext = Array((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "q_redc_ext", vtype=Wire)
        self.q_r = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "q_r")
        self.q_redc = Array(((self.DATA_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "q_redc", vtype=Reg)
        self.a_seg = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "a_seg", vtype=Wire)
        self.b_seg = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "b_seg", vtype=Wire)
        self.q_seg = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "q_seg", vtype=Wire)
        self.s0_sum_0 = Wire(((self.SEG_WIDTH - 1) - 0 + 1), "s0_sum_0")
        self.s0_sum_seg_0 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s0_sum_seg_0", vtype=Wire)
        self.s0_sum_seg_1 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 2) - 0 + 1), "s0_sum_seg_1", vtype=Wire)
        self.s0_carry_seg = Wire(((self.PART - 1) - 0 + 1), "s0_carry_seg")
        self.s0_carry_seg_0 = Wire(((self.PART - 2) - 0 + 1), "s0_carry_seg_0")
        self.s0_carry_seg_1 = Wire(((self.PART - 2) - 0 + 1), "s0_carry_seg_1")
        self.s0_sum_seg_r = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "s0_sum_seg_r", vtype=Reg)
        self.s0_carry_r = Reg(1, "s0_carry_r")
        self.s0_sum_seg = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "s0_sum_seg", vtype=Wire)
        self.s0_carry = Wire(1, "s0_carry")
        self.to_redc_seg = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.PART - 1) - 0 + 1), "to_redc_seg", vtype=Wire)
        self.s1_sum_1 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_sum_1", vtype=Wire)
        self.s1_sum_seg_0 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_sum_seg_0", vtype=Wire)
        self.s1_sum_seg_1 = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_sum_seg_1", vtype=Wire)
        self.s1_carry_seg = Array(((self.PART - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_carry_seg", vtype=Wire)
        self.s1_carry_seg_0 = Array(((self.PART - 2) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_carry_seg_0", vtype=Wire)
        self.s1_carry_seg_1 = Array(((self.PART - 2) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_carry_seg_1", vtype=Wire)
        self.s1_sum_seg_r = Array(((self.SEG_WIDTH - 1) - 0 + 1), ((self.EXT_BITS - 1) - 0 + 1), "s1_sum_seg_r", vtype=Reg)
        self.res_tmp = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "res_tmp")
        self.acc_reg = Array((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), 16, "acc_reg", vtype=Reg)
        self.acc_reg_d1 = Array((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), 16, "acc_reg_d1", vtype=Reg)
        self.acc_res = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "acc_res")
        self.acc_count = Array(((self.EXT_BITS - 1) - 0 + 1), 16, "acc_count", vtype=Reg)
        self.acc_overflow = Wire(1, "acc_overflow")
        self.acc_update = Reg(((self.EXT_BITS - 1) - 0 + 1), "acc_update")
        self.add_a = Wire(((self.REG_WIDTH - 1) - 0 + 1), "add_a")
        self.add_b = Wire((((self.PART * self.SEG_WIDTH) - 1) - 0 + 1), "add_b")
        self.b_is_one = Wire(1, "b_is_one")
        self.i_dst_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "i_dst_fmt")
        self.s0_dst_fmt = Reg(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "s0_dst_fmt")
        self.o_dst_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "o_dst_fmt")
        self.pipe_en0 = Wire(1, "pipe_en0")
        self.pipe_en1 = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "pipe_en1", vtype=Wire)
        self.pipe_i_valid0 = Wire(1, "pipe_i_valid0")
        self.pipe_i_ready0 = Wire(1, "pipe_i_ready0")
        self.pipe_o_valid0 = Reg(1, "pipe_o_valid0")
        self.pipe_o_ready0 = Wire(1, "pipe_o_ready0")
        self.pipe_i_valid1 = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "pipe_i_valid1", vtype=Wire)
        self.pipe_i_ready1 = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "pipe_i_ready1", vtype=Wire)
        self.pipe_o_valid1 = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "pipe_o_valid1", vtype=Reg)
        self.pipe_o_ready1 = Array(1, ((self.EXT_BITS - 1) - 0 + 1), "pipe_o_ready1", vtype=Wire)

        # TODO: unpack assignment: Cat(self.isa, self.cc_val, self.b, self.a) = self.data
        # Consider using Split() or manual bit slicing
        self.i_dst_fmt <<= self.isa[82:79]
        self.add_a <<= self.a
        self.add_b <<= Mux((self.i_dst_fmt == 13), Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.b), Mux(self.b_is_one, self.acc_reg[self.i_vm_id], 0))
        self.b_is_one <<= (self.b[(self.DATA_WIDTH - 1):0] == 1)
        self.a_ext <<= Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.add_a[(self.DATA_WIDTH - 1):0])
        self.b_ext <<= self.add_b
        # for-loop (non-generate) - parameter-driven
        for part in range(0, self.PART):
            self.a_seg[part][(self.SEG_WIDTH - 1):0] <<= self.a_ext[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
            self.b_seg[part][(self.SEG_WIDTH - 1):0] <<= self.b_ext[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
            with If((part == 0)):
                # TODO: unpack assignment: Cat(self.s0_carry_seg[part], self.s0_sum_0) = (self.a_seg[part] + self.b_seg[part])
                # Consider using Split() or manual bit slicing
                self.s0_sum_seg[part] <<= self.s0_sum_0
            with Else():
                # TODO: unpack assignment: Cat(self.s0_carry_seg_0[(part - 1)], self.s0_sum_seg_0[(part - 1)]) = (self.a_seg[part] + self.b_seg[part])
                # Consider using Split() or manual bit slicing
                # TODO: unpack assignment: Cat(self.s0_carry_seg_1[(part - 1)], self.s0_sum_seg_1[(part - 1)]) = ((self.a_seg[part] + self.b_seg[part]) + 1)
                # Consider using Split() or manual bit slicing
                self.s0_carry_seg[part] <<= Mux(self.s0_carry_seg[(part - 1)], self.s0_carry_seg_1[(part - 1)], self.s0_carry_seg_0[(part - 1)])
                self.s0_sum_seg[part] <<= Mux(self.s0_carry_seg[(part - 1)], self.s0_sum_seg_1[(part - 1)], self.s0_sum_seg_0[(part - 1)])
            with If(self.pipe_en0):
                self.s0_sum_seg_r[part] <<= self.s0_sum_seg[part]
            with Else():
                self.s0_sum_seg_r[part] <<= self.s0_sum_seg_r[part]
            self.acc_res[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)] <<= self.s0_sum_seg[part]

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                with ForGen("i", 0, 16) as i:
                    self.acc_reg[i] <<= 0
                    self.acc_count[i] <<= 0
            with Else():
                with If(self.pipe_en0):
                    with If(((self.i_dst_fmt == 11) & self.b_is_one)):
                        self.acc_reg[self.i_vm_id] <<= self.acc_res
                        self.acc_count[self.i_vm_id] <<= (self.acc_count[self.i_vm_id] + 1)
                    with Else():
                        with If(((self.i_dst_fmt == 12) | (self.i_dst_fmt == 13))):
                            self.acc_reg[self.i_vm_id] <<= 0
                            self.acc_count[self.i_vm_id] <<= 0
                with Else():
                    with If((self.acc_update[(self.EXT_BITS - 1)] & self.acc_overflow)):
                        self.acc_reg[self.s1_vm_id[(self.EXT_BITS - 1)]] <<= Cat(Rep(Cat(0), ((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH)), self.res_tmp[(self.DATA_WIDTH - 1):0])
                        self.acc_count[self.s1_vm_id[(self.EXT_BITS - 1)]] <<= 0
        with ForGen("i", 0, 16) as i:

            @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
            def _seq_logic():
                with If((~self.rstn)):
                    self.acc_reg_d1[i] <<= 0
                with Else():
                    with If((self.pipe_en0 & (self.i_vm_id == i))):
                        self.acc_reg_d1[i] <<= self.acc_reg[i]
        self.acc_overflow <<= (self.acc_count[self.s0_vm_id] == ((2 ** self.EXT_BITS) - 1))

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.q_r <<= 0
                self.s0_isa <<= 0
                self.s0_cc_val <<= 0
                self.s0_vm_id <<= 0
                self.s0_b_is_one <<= 0
                self.s0_dst_fmt <<= 0
            with Else():
                with If(self.pipe_en0):
                    self.q_r <<= (not self.q)
                    self.s0_isa <<= self.isa
                    self.s0_cc_val <<= self.cc_val
                    self.s0_vm_id <<= self.i_vm_id
                    self.s0_b_is_one <<= self.b_is_one
                    self.s0_dst_fmt <<= self.i_dst_fmt
                with Else():
                    self.q_r <<= self.q_r
                    self.s0_isa <<= self.s0_isa
                    self.s0_cc_val <<= self.s0_cc_val
                    self.s0_vm_id <<= self.s0_vm_id
                    self.s0_b_is_one <<= self.s0_b_is_one
                    self.s0_dst_fmt <<= self.s0_dst_fmt
        # for-loop (non-generate) - parameter-driven
        for redc in range(0, self.EXT_BITS):
            with If((redc == 0)):
                self.q_redc_ext[redc] <<= Cat(Rep(Cat(1), (((((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH) - self.EXT_BITS) + 1) + redc)), self.q_r, Rep(Cat(1), ((self.EXT_BITS - 1) - redc)))
                # for-loop (non-generate) - parameter-driven
                for part in range(0, self.PART):
                    self.to_redc_seg[part] <<= Mux(self.acc_overflow, self.acc_reg_d1[self.s0_vm_id][(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)], Mux((self.s0_dst_fmt == 12), Mux(self.s0_b_is_one, self.s0_sum_seg_r[part], self.acc_reg_d1[self.s0_vm_id][(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]), Mux((self.s0_dst_fmt == 13), self.s0_sum_seg_r[part], 0)))
                    self.q_seg[redc][part][(self.SEG_WIDTH - 1):0] <<= self.q_redc_ext[redc][(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
                    with If((part == 0)):
                        # TODO: unpack assignment: Cat(self.s1_carry_seg[redc][part], self.s1_sum_1[redc]) = ((self.to_redc_seg[part] + self.q_seg[redc][part]) + 1)
                        # Consider using Split() or manual bit slicing
                        with If(self.pipe_en1[redc]):
                            self.s1_sum_seg_r[redc][part] <<= Mux(self.s1_carry_seg[redc][(self.PART - 1)], self.s1_sum_1[redc], self.to_redc_seg[part])
                        with Else():
                            self.s1_sum_seg_r[redc][part] <<= self.s1_sum_seg_r[redc][part]
                    with Else():
                        # TODO: unpack assignment: Cat(self.s1_carry_seg_0[redc][(part - 1)], self.s1_sum_seg_0[redc][(part - 1)]) = (self.to_redc_seg[part] + self.q_seg[redc][part])
                        # Consider using Split() or manual bit slicing
                        # TODO: unpack assignment: Cat(self.s1_carry_seg_1[redc][(part - 1)], self.s1_sum_seg_1[redc][(part - 1)]) = ((self.to_redc_seg[part] + self.q_seg[redc][part]) + 1)
                        # Consider using Split() or manual bit slicing
                        self.s1_carry_seg[redc][part] <<= Mux(self.s1_carry_seg[redc][(part - 1)], self.s1_carry_seg_1[redc][(part - 1)], self.s1_carry_seg_0[redc][(part - 1)])
                        with If(self.pipe_en1[redc]):
                            self.s1_sum_seg_r[redc][part] <<= Mux(self.s1_carry_seg[redc][(self.PART - 1)], Mux(self.s1_carry_seg[redc][(part - 1)], self.s1_sum_seg_1[redc][(part - 1)], self.s1_sum_seg_0[redc][(part - 1)]), self.to_redc_seg[part])
                        with Else():
                            self.s1_sum_seg_r[redc][part] <<= self.s1_sum_seg_r[redc][part]
                with If((~self.rstn)):
                    self.s1_isa[redc] <<= 0
                    self.s1_cc_val[redc] <<= 0
                    self.s1_vm_id[redc] <<= 0
                    self.s1_b_is_one[redc] <<= 0
                    self.q_redc[redc] <<= 0
                    self.acc_update[redc] <<= 0
                with Else():
                    with If(self.pipe_en1[redc]):
                        self.s1_isa[redc] <<= self.s0_isa
                        self.s1_cc_val[redc] <<= self.s0_cc_val
                        self.s1_vm_id[redc] <<= self.s0_vm_id
                        self.s1_b_is_one[redc] <<= self.s0_b_is_one
                        self.q_redc[redc] <<= self.q_r
                        self.acc_update[redc] <<= self.acc_overflow
                    with Else():
                        self.s1_isa[redc] <<= self.s1_isa[redc]
                        self.s1_cc_val[redc] <<= self.s1_cc_val[redc]
                        self.s1_vm_id[redc] <<= self.s1_vm_id[redc]
                        self.s1_b_is_one[redc] <<= self.s1_b_is_one[redc]
                        self.q_redc[redc] <<= self.q_redc[redc]
                        self.acc_update[redc] <<= self.acc_update[redc]
            with Else():
                self.q_redc_ext[redc] <<= Cat(Rep(Cat(1), (((((self.PART * self.SEG_WIDTH) - self.DATA_WIDTH) - self.EXT_BITS) + 1) + redc)), self.q_redc[(redc - 1)], Rep(Cat(1), ((self.EXT_BITS - 1) - redc)))
                # for-loop (non-generate) - parameter-driven
                for part in range(0, self.PART):
                    self.q_seg[redc][part][(self.SEG_WIDTH - 1):0] <<= self.q_redc_ext[redc][(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)]
                    with If((part == 0)):
                        # TODO: unpack assignment: Cat(self.s1_carry_seg[redc][part], self.s1_sum_1[redc]) = ((self.s1_sum_seg_r[(redc - 1)][part] + self.q_seg[redc][part]) + 1)
                        # Consider using Split() or manual bit slicing
                        with If(self.pipe_en1[redc]):
                            self.s1_sum_seg_r[redc][part] <<= Mux(self.s1_carry_seg[redc][(self.PART - 1)], self.s1_sum_1[redc], self.s1_sum_seg_r[(redc - 1)][part])
                        with Else():
                            self.s1_sum_seg_r[redc][part] <<= self.s1_sum_seg_r[redc][part]
                    with Else():
                        # TODO: unpack assignment: Cat(self.s1_carry_seg_0[redc][(part - 1)], self.s1_sum_seg_0[redc][(part - 1)]) = (self.s1_sum_seg_r[(redc - 1)][part] + self.q_seg[redc][part])
                        # Consider using Split() or manual bit slicing
                        # TODO: unpack assignment: Cat(self.s1_carry_seg_1[redc][(part - 1)], self.s1_sum_seg_1[redc][(part - 1)]) = ((self.s1_sum_seg_r[(redc - 1)][part] + self.q_seg[redc][part]) + 1)
                        # Consider using Split() or manual bit slicing
                        self.s1_carry_seg[redc][part] <<= Mux(self.s1_carry_seg[redc][(part - 1)], self.s1_carry_seg_1[redc][(part - 1)], self.s1_carry_seg_0[redc][(part - 1)])
                        with If(self.pipe_en1[redc]):
                            self.s1_sum_seg_r[redc][part] <<= Mux(self.s1_carry_seg[redc][(self.PART - 1)], Mux(self.s1_carry_seg[redc][(part - 1)], self.s1_sum_seg_1[redc][(part - 1)], self.s1_sum_seg_0[redc][(part - 1)]), self.s1_sum_seg_r[(redc - 1)][part])
                        with Else():
                            self.s1_sum_seg_r[redc][part] <<= self.s1_sum_seg_r[redc][part]
                    with If((redc == (self.EXT_BITS - 1))):
                        self.res_tmp[(((part + 1) * self.SEG_WIDTH) - 1):(part * self.SEG_WIDTH)] <<= self.s1_sum_seg_r[(self.EXT_BITS - 1)][part]
                with If((~self.rstn)):
                    self.s1_isa[redc] <<= 0
                    self.s1_cc_val[redc] <<= 0
                    self.s1_vm_id[redc] <<= 0
                    self.s1_b_is_one[redc] <<= 0
                    self.q_redc[redc] <<= 0
                    self.acc_update[redc] <<= 0
                with Else():
                    with If(self.pipe_en1[redc]):
                        self.s1_isa[redc] <<= self.s1_isa[(redc - 1)]
                        self.s1_cc_val[redc] <<= self.s1_cc_val[(redc - 1)]
                        self.s1_vm_id[redc] <<= self.s1_vm_id[(redc - 1)]
                        self.s1_b_is_one[redc] <<= self.s1_b_is_one[(redc - 1)]
                        self.q_redc[redc] <<= self.q_redc[(redc - 1)]
                        self.acc_update[redc] <<= self.acc_update[(redc - 1)]
                    with Else():
                        self.s1_isa[redc] <<= self.s1_isa[redc]
                        self.s1_cc_val[redc] <<= self.s1_cc_val[redc]
                        self.s1_vm_id[redc] <<= self.s1_vm_id[redc]
                        self.s1_b_is_one[redc] <<= self.s1_b_is_one[redc]
                        self.q_redc[redc] <<= self.q_redc[redc]
                        self.acc_update[redc] <<= self.acc_update[redc]
            with If((redc == 0)):
                self.pipe_i_valid1[redc] <<= self.pipe_o_valid0
                self.pipe_o_ready1[redc] <<= self.pipe_i_ready1[(redc + 1)]
            with Else():
                with If((redc == (self.EXT_BITS - 1))):
                    self.pipe_i_valid1[redc] <<= self.pipe_o_valid1[(redc - 1)]
                    self.pipe_o_ready1[redc] <<= self.o_ready
                with Else():
                    self.pipe_i_valid1[redc] <<= self.pipe_o_valid1[(redc - 1)]
                    self.pipe_o_ready1[redc] <<= self.pipe_i_ready1[(redc + 1)]
            self.pipe_en1[redc] <<= (self.pipe_i_valid1[redc] & self.pipe_i_ready1[redc])
            self.pipe_i_ready1[redc] <<= ((~self.pipe_o_valid1[redc]) | self.pipe_o_ready1[redc])
            with If((~self.rstn)):
                self.pipe_o_valid1[redc] <<= 0
            with Else():
                with If(self.pipe_i_ready1[redc]):
                    self.pipe_o_valid1[redc] <<= self.pipe_i_valid1[redc]
                with Else():
                    self.pipe_o_valid1[redc] <<= self.pipe_o_valid1[redc]
        self.o_dst_fmt <<= self.s1_isa[(self.EXT_BITS - 1)][82:79]
        self.res <<= Cat(self.s1_isa[(self.EXT_BITS - 1)], self.s1_cc_val[(self.EXT_BITS - 1)], Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.res_tmp[(self.DATA_WIDTH - 1):0])
        self.o_vm_id <<= self.s1_vm_id[(self.EXT_BITS - 1)]
        self.pipe_en0 <<= (self.pipe_i_valid0 & self.pipe_i_ready0)
        self.pipe_i_valid0 <<= self.i_valid
        self.pipe_o_ready0 <<= self.pipe_i_ready1[0]
        self.pipe_i_ready0 <<= ((~self.pipe_o_valid0) | self.pipe_o_ready0)
        self.i_ready <<= (self.pipe_i_ready0 & (~self.acc_overflow))
        self.o_valid <<= self.pipe_o_valid1[(self.EXT_BITS - 1)]

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.pipe_o_valid0 <<= 0
            with Else():
                with If(self.pipe_i_ready0):
                    self.pipe_o_valid0 <<= self.pipe_i_valid0
                with Else():
                    self.pipe_o_valid0 <<= self.pipe_o_valid0
