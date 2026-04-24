"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_mov(Module):
    def __init__(self, name: str = "js_vm_mov"):
        super().__init__(name or "js_vm_mov")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.sq_mov_valid = Input(1, "sq_mov_valid")
        self.sq_mov_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_mov_data")
        self.sq_mov_vm_id = Input(4, "sq_mov_vm_id")
        self.sq_mov_ready = Output(1, "sq_mov_ready")
        self.mov_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "mov_sq_fc_dec")
        self.mov_sq_fc_dec_vm_id = Output(4, "mov_sq_fc_dec_vm_id")
        self.mov_res_valid = Output(1, "mov_res_valid")
        self.mov_res_vm_id = Output(4, "mov_res_vm_id")
        self.mov_res_data = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "mov_res_data")
        self.mov_res_ready = Input(1, "mov_res_ready")

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
        self.sf_ext = Wire(((self.ISA_SF_EXT_BITS - 1) - 0 + 1), "sf_ext")
        self.wf_ext = Wire(((self.ISA_WF_EXT_BITS - 1) - 0 + 1), "wf_ext")
        self.rsv = Wire(((self.ISA_RSV_EXT_BITS - 1) - 0 + 1), "rsv")
        self.cc_value = Wire(1, "cc_value")
        self.src1_value = Wire(((self.REG_WIDTH - 1) - 0 + 1), "src1_value")
        self.src0_value = Wire(((self.REG_WIDTH - 1) - 0 + 1), "src0_value")
        self.truncate_window = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "truncate_window")
        self.src0_tmp = Array(1, ((self.REG_WIDTH - 1) - 0 + 1), "src0_tmp", vtype=Wire)
        self.mov_zero = Wire(1, "mov_zero")
        self.src0_value_adj = Wire(((self.REG_WIDTH - 1) - 0 + 1), "src0_value_adj")
        self.extracted_bit = Wire(1, "extracted_bit")
        self.res_data_tmp = Wire(((self.REG_WIDTH - 1) - 0 + 1), "res_data_tmp")
        self.res_data_d0 = Wire(((((self.ISA_BITS + 1) + self.REG_WIDTH) - 1) - 0 + 1), "res_data_d0")
        self.res_valid = Reg(1, "res_valid")
        self.res_data = Reg(((((self.ISA_BITS + 1) + self.REG_WIDTH) - 1) - 0 + 1), "res_data")
        self.res_vm_id = Reg(4, "res_vm_id")
        self.res_gpr_addr = Reg(((self.GPR_ADDR_BITS - 1) - 0 + 1), "res_gpr_addr")
        self.res_type = Reg(2, "res_type")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")
        self.res_fc_dec = Reg(((self.FC_NUM - 1) - 0 + 1), "res_fc_dec")

        # TODO: unpack assignment: Cat(self.rsv, self.wf_ext, self.sf_ext, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype, self.cc_value, self.src1_value, self.src0_value) = self.sq_mov_data[(((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1):0]
        # Consider using Split() or manual bit slicing
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.REG_WIDTH):
            with If(((i >= 0) & (i < self.DATA_WIDTH))):
                self.src0_tmp[i] <<= self.src0_value_adj[i]
            with Else():
                self.src0_tmp[i] <<= 0
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.truncate_window[i] <<= Mux((i < self.src0_imm), 1, 0)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.res_valid <<= 0
            with Else():
                with If(self.sq_mov_ready):
                    self.res_valid <<= self.sq_mov_valid

        @self.seq(self.clk, None)
        def _seq_logic():
            with If((self.sq_mov_valid & self.sq_mov_ready)):
                self.res_data <<= self.res_data_d0
                self.res_vm_id <<= self.sq_mov_vm_id
                self.res_gpr_addr <<= self.dst0_reg
                self.res_type <<= self.dst_type
        self.sq_mov_ready <<= ((~self.res_valid) | self.mov_res_ready)
        self.mov_res_valid <<= self.res_valid
        self.mov_res_data <<= self.res_data
        self.mov_res_vm_id <<= self.res_vm_id

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.res_fc_dec <<= 0
            with Else():
                with If((self.sq_mov_valid & self.sq_mov_ready)):
                    self.res_fc_dec <<= self.fc_dec

        @self.comb
        def _comb_logic():
            self.mov_sq_fc_dec <<= (Rep(Cat((self.mov_res_valid & self.mov_res_ready)), self.FC_NUM) & self.res_fc_dec)
            self.mov_sq_fc_dec_vm_id <<= self.res_vm_id
        # unhandled statement: # function get_sf
