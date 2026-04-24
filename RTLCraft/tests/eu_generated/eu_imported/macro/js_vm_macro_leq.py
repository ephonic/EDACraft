"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_macro_leq(Module):
    def __init__(self, name: str = "js_vm_macro_leq"), PIPE_LEVEL: int = 16, PIPE_WIDTH: int = (((self.DATA_WIDTH + self.PIPE_LEVEL) - 1) // self.PIPE_LEVEL), DATA_WIDTH_CEIL: int = (self.PIPE_WIDTH * self.PIPE_LEVEL):
        super().__init__(name or "js_vm_macro_leq")

        self.add_localparam("PIPE_LEVEL", 16)
        self.add_localparam("PIPE_WIDTH", (((self.DATA_WIDTH + self.PIPE_LEVEL) - 1) // self.PIPE_LEVEL))
        self.add_localparam("DATA_WIDTH_CEIL", (self.PIPE_WIDTH * self.PIPE_LEVEL))
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.eu_macro_leq_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "eu_macro_leq_data")
        self.eu_macro_leq_i_valid = Input(1, "eu_macro_leq_i_valid")
        self.eu_macro_leq_i_vm_id = Input(4, "eu_macro_leq_i_vm_id")
        self.eu_macro_leq_o_ready = Input(1, "eu_macro_leq_o_ready")
        self.eu_macro_leq_o_valid = Output(1, "eu_macro_leq_o_valid")
        self.eu_macro_leq_i_ready = Output(1, "eu_macro_leq_i_ready")
        self.eu_macro_leq_o_vm_id = Output(4, "eu_macro_leq_o_vm_id")
        self.eu_macro_leq_variable = Output(((self.ISA_BITS + self.REG_WIDTH) - 0 + 1), "eu_macro_leq_variable")

        self.isa_r = Array((self.ISA_BITS - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "isa_r", vtype=Reg)
        self.vm_id = Array(4, ((self.PIPE_LEVEL - 1) - 0 + 1), "vm_id", vtype=Reg)
        self.leq_valid = Reg(((self.PIPE_LEVEL - 1) - 0 + 1), "leq_valid")
        self.leq_data_x = Array(((self.DATA_WIDTH_CEIL - 1) - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "leq_data_x", vtype=Reg)
        self.leq_data_y = Array(((self.DATA_WIDTH_CEIL - 1) - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "leq_data_y", vtype=Reg)
        self.leq_data_res = Array(((self.DATA_WIDTH_CEIL - 1) - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "leq_data_res", vtype=Reg)
        self.leq_res_temp = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "leq_res_temp")
        self.leq_variable_temp = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "leq_variable_temp")
        self.second_zero_pos = Array(8, ((self.PIPE_LEVEL - 1) - 0 + 1), "second_zero_pos", vtype=Reg)
        self.zero_cnt = Array(8, ((self.PIPE_LEVEL - 1) - 0 + 1), "zero_cnt", vtype=Reg)
        self.second_zero_pos_tmp = Array(8, ((self.PIPE_LEVEL - 1) - 0 + 1), "second_zero_pos_tmp", vtype=Reg)
        self.zero_cnt_tmp = Array(8, ((self.PIPE_LEVEL - 1) - 0 + 1), "zero_cnt_tmp", vtype=Reg)
        self.leq_data_flag = Array((((self.REG_WIDTH - self.DATA_WIDTH) - 1) - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "leq_data_flag", vtype=Reg)
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
        self.bit_nums = Wire(((self.ISA_SRC0_IMM_BITS - 1) - 0 + 1), "bit_nums")
        self.leq_data_logic = Array(((self.PIPE_WIDTH - 1) - 0 + 1), ((self.PIPE_LEVEL - 1) - 0 + 1), "leq_data_logic", vtype=Wire)
        self.leq_x_init = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "leq_x_init")
        self.leq_y_init = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "leq_y_init")
        self.leq_ready = Wire(((self.PIPE_LEVEL - 1) - 0 + 1), "leq_ready")

        self.eu_macro_leq_i_ready <<= self.leq_ready[0]
        self.eu_macro_leq_o_vm_id <<= self.vm_id[(self.PIPE_LEVEL - 1)]
        self.eu_macro_leq_variable <<= Cat(self.isa_r[(self.PIPE_LEVEL - 1)], Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.leq_res_temp)
        self.eu_macro_leq_o_valid <<= self.leq_valid[(self.PIPE_LEVEL - 1)]
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.isa_r[(self.PIPE_LEVEL - 1)][self.ISA_BITS:1]
        # Consider using Split() or manual bit slicing
        self.bit_nums <<= Mux((self.src0_fmt == 10), self.src0_imm, Mux(((self.src0_fmt == 0) | (self.src0_fmt == 1)), 8, Mux(((self.src0_fmt == 2) | (self.src0_fmt == 3)), 16, Mux(((self.src0_fmt == 4) | (self.src0_fmt == 5)), 32, Mux(((self.src0_fmt == 6) | (self.src0_fmt == 7)), 64, Mux(((self.src0_fmt == 8) | (self.src0_fmt == 9)), 128, 0))))))
        self.leq_y_init <<= self.eu_macro_leq_data[((2 * self.REG_WIDTH) - 1):self.REG_WIDTH]
        self.leq_x_init <<= self.eu_macro_leq_data[(self.REG_WIDTH - 1):0]
        self.leq_res_temp <<= (self.leq_variable_temp >> self.second_zero_pos[(self.PIPE_LEVEL - 1)])
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.leq_variable_temp[i] <<= Mux((i < self.bit_nums), self.leq_data_res[(self.PIPE_LEVEL - 1)][i], 0)
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.PIPE_LEVEL):
            with If((i == (self.PIPE_LEVEL - 1))):
                self.leq_ready[i] <<= (self.eu_macro_leq_o_ready | (~self.leq_valid[i]))
            with Else():
                self.leq_ready[i] <<= (self.leq_ready[(i + 1)] | (~self.leq_valid[i]))
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.PIPE_LEVEL):
            with If((i == 0)):
                self.zero_cnt_tmp[i] <<= 0
                self.second_zero_pos_tmp[i] <<= 0
                # for-loop (non-generate) - parameter-driven
                for k in range(0, self.PIPE_WIDTH):
                    with If((~self.leq_y_init[k])):
                        self.zero_cnt_tmp[i] <<= (self.zero_cnt_tmp[i] + 1)
                        with If((self.zero_cnt_tmp[i] == 2)):
                            self.second_zero_pos_tmp[i] <<= k
                with If((~self.rstn)):
                    self.zero_cnt[i] <<= 0
                    self.second_zero_pos[i] <<= 0
                with Else():
                    with If((self.eu_macro_leq_i_valid & self.eu_macro_leq_i_ready)):
                        self.zero_cnt[i] <<= self.zero_cnt_tmp[i]
                        self.second_zero_pos[i] <<= self.second_zero_pos_tmp[i]
                self.leq_data_logic[0][0] <<= Mux(self.leq_y_init[0], 0, self.leq_x_init[0])
                # for-loop (non-generate) - parameter-driven
                for j in range(1, self.PIPE_WIDTH):
                    self.leq_data_logic[0][j] <<= Mux(self.leq_y_init[j], (self.leq_data_logic[0][(j - 1)] & self.leq_x_init[j]), (self.leq_data_logic[0][(j - 1)] | self.leq_x_init[j]))
                with If((~self.rstn)):
                    self.isa_r[i] <<= 0
                    self.vm_id[i] <<= 0
                with Else():
                    with If((self.eu_macro_leq_i_valid & self.eu_macro_leq_i_ready)):
                        self.isa_r[i] <<= self.eu_macro_leq_data[(self.ISA_BITS + (2 * self.REG_WIDTH)):(2 * self.REG_WIDTH)]
                        self.vm_id[i] <<= self.eu_macro_leq_i_vm_id
                with If((~self.rstn)):
                    self.leq_valid[i] <<= 0
                with Else():
                    with If(self.eu_macro_leq_i_ready):
                        self.leq_valid[i] <<= self.eu_macro_leq_i_valid
                with If((~self.rstn)):
                    self.leq_data_x[i] <<= 0
                    self.leq_data_y[i] <<= 0
                    self.leq_data_flag[i] <<= 0
                with Else():
                    with If((self.eu_macro_leq_i_valid & self.eu_macro_leq_i_ready)):
                        self.leq_data_x[i] <<= self.leq_x_init
                        self.leq_data_y[i] <<= self.leq_y_init
                        self.leq_data_flag[i] <<= self.eu_macro_leq_data[(self.REG_WIDTH - 1):self.DATA_WIDTH]
                # for-loop (non-generate) - parameter-driven
                for t in range(0, self.PIPE_LEVEL):
                    with If((~self.rstn)):
                        self.leq_data_res[i][(((t + 1) * self.PIPE_WIDTH) - 1):(t * self.PIPE_WIDTH)] <<= 0
                    with Else():
                        with If((self.eu_macro_leq_i_valid & self.eu_macro_leq_i_ready)):
                            self.leq_data_res[i][(((t + 1) * self.PIPE_WIDTH) - 1):(t * self.PIPE_WIDTH)] <<= Mux((t == i), self.leq_data_logic[i], 0)
            with Else():
                self.leq_data_logic[i][0] <<= Mux(self.leq_data_y[(i - 1)][(i * self.PIPE_WIDTH)], (self.leq_data_res[(i - 1)][((i * self.PIPE_WIDTH) - 1)] & self.leq_data_x[(i - 1)][(i * self.PIPE_WIDTH)]), (self.leq_data_res[(i - 1)][((i * self.PIPE_WIDTH) - 1)] | self.leq_data_x[(i - 1)][(i * self.PIPE_WIDTH)]))
                # for-loop (non-generate) - parameter-driven
                for j in range(1, self.PIPE_WIDTH):
                    self.leq_data_logic[i][j] <<= Mux(self.leq_data_y[(i - 1)][((i * self.PIPE_WIDTH) + j)], (self.leq_data_logic[i][(j - 1)] & self.leq_data_x[(i - 1)][((i * self.PIPE_WIDTH) + j)]), (self.leq_data_logic[i][(j - 1)] | self.leq_data_x[(i - 1)][((i * self.PIPE_WIDTH) + j)]))
                self.zero_cnt_tmp[i] <<= self.zero_cnt[(i - 1)]
                self.second_zero_pos_tmp[i] <<= self.second_zero_pos[(i - 1)]
                # for-loop (non-generate) - parameter-driven
                for k in range(0, self.PIPE_WIDTH):
                    with If((~self.leq_data_y[(i - 1)][((i * self.PIPE_WIDTH) + k)])):
                        self.zero_cnt_tmp[i] <<= (self.zero_cnt_tmp[i] + 1)
                        with If((self.zero_cnt_tmp[i] == 2)):
                            self.second_zero_pos_tmp[i] <<= ((i * self.PIPE_WIDTH) + k)
                with If((~self.rstn)):
                    self.zero_cnt[i] <<= 0
                    self.second_zero_pos[i] <<= 0
                with Else():
                    with If((self.leq_valid[(i - 1)] & self.leq_ready[i])):
                        self.zero_cnt[i] <<= self.zero_cnt_tmp[i]
                        self.second_zero_pos[i] <<= self.second_zero_pos_tmp[i]
                with If((~self.rstn)):
                    self.isa_r[i] <<= 0
                    self.vm_id[i] <<= 0
                with Else():
                    with If((self.leq_valid[(i - 1)] & self.leq_ready[i])):
                        self.isa_r[i] <<= self.isa_r[(i - 1)]
                        self.vm_id[i] <<= self.vm_id[(i - 1)]
                with If((~self.rstn)):
                    self.leq_valid[i] <<= 0
                with Else():
                    with If(self.leq_ready[i]):
                        self.leq_valid[i] <<= self.leq_valid[(i - 1)]
                with If((~self.rstn)):
                    self.leq_data_x[i] <<= 0
                    self.leq_data_y[i] <<= 0
                    self.leq_data_flag[i] <<= 0
                with Else():
                    with If((self.leq_valid[(i - 1)] & self.leq_ready[i])):
                        self.leq_data_x[i] <<= self.leq_data_x[(i - 1)]
                        self.leq_data_y[i] <<= self.leq_data_y[(i - 1)]
                        self.leq_data_flag[i] <<= self.leq_data_flag[(i - 1)]
                # for-loop (non-generate) - parameter-driven
                for t in range(0, self.PIPE_LEVEL):
                    with If((~self.rstn)):
                        self.leq_data_res[i][(((t + 1) * self.PIPE_WIDTH) - 1):(t * self.PIPE_WIDTH)] <<= 0
                    with Else():
                        with If((self.leq_valid[(i - 1)] & self.leq_ready[i])):
                            self.leq_data_res[i][(((t + 1) * self.PIPE_WIDTH) - 1):(t * self.PIPE_WIDTH)] <<= Mux((t == i), self.leq_data_logic[i], self.leq_data_res[(i - 1)][(((t + 1) * self.PIPE_WIDTH) - 1):(t * self.PIPE_WIDTH)])
