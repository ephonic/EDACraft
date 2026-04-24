"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_macro_xor(Module):
    def __init__(self, name: str = "js_vm_macro_xor"):
        super().__init__(name or "js_vm_macro_xor")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.eu_macro_xor_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "eu_macro_xor_data")
        self.eu_macro_xor_i_valid = Input(1, "eu_macro_xor_i_valid")
        self.eu_macro_xor_i_vm_id = Input(4, "eu_macro_xor_i_vm_id")
        self.eu_macro_xor_o_ready = Input(1, "eu_macro_xor_o_ready")
        self.eu_macro_xor_o_valid = Output(1, "eu_macro_xor_o_valid")
        self.eu_macro_xor_i_ready = Output(1, "eu_macro_xor_i_ready")
        self.eu_macro_xor_o_vm_id = Output(4, "eu_macro_xor_o_vm_id")
        self.eu_macro_xor_variable = Output(((self.ISA_BITS + self.REG_WIDTH) - 0 + 1), "eu_macro_xor_variable")

        self.isa_r1 = Reg((self.ISA_BITS - 0 + 1), "isa_r1")
        self.vm_id = Reg(4, "vm_id")
        self.xor_o_valid = Reg(1, "xor_o_valid")
        self.xor_data = Reg(((self.REG_WIDTH - 1) - 0 + 1), "xor_data")
        self.operand_0 = Wire(((self.REG_WIDTH - 1) - 0 + 1), "operand_0")
        self.operand_1 = Wire(((self.REG_WIDTH - 1) - 0 + 1), "operand_1")
        self.operand_xor = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "operand_xor")
        self.operand_xor_tmp = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "operand_xor_tmp")
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

        self.eu_macro_xor_i_ready <<= ((~self.eu_macro_xor_o_valid) | self.eu_macro_xor_o_ready)
        self.eu_macro_xor_o_vm_id <<= self.vm_id
        self.eu_macro_xor_variable <<= Cat(self.isa_r1, self.xor_data)
        self.eu_macro_xor_o_valid <<= self.xor_o_valid
        self.operand_1 <<= self.eu_macro_xor_data[((2 * self.REG_WIDTH) - 1):self.REG_WIDTH]
        self.operand_0 <<= self.eu_macro_xor_data[(self.REG_WIDTH - 1):0]
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.eu_macro_xor_data[(self.ISA_BITS + (2 * self.REG_WIDTH)):((2 * self.REG_WIDTH) + 1)]
        # Consider using Split() or manual bit slicing
        self.operand_xor_tmp <<= (self.operand_0[(self.DATA_WIDTH - 1):0] ^ self.operand_1[(self.DATA_WIDTH - 1):0])
        self.bit_nums <<= Mux((self.src0_fmt == 10), self.src0_imm, Mux(((self.src0_fmt == 0) | (self.src0_fmt == 1)), 8, Mux(((self.src0_fmt == 2) | (self.src0_fmt == 3)), 16, Mux(((self.src0_fmt == 4) | (self.src0_fmt == 5)), 32, Mux(((self.src0_fmt == 6) | (self.src0_fmt == 7)), 64, Mux(((self.src0_fmt == 8) | (self.src0_fmt == 9)), 128, 0))))))
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.operand_xor[i] <<= Mux((i < self.bit_nums), self.operand_xor_tmp[i], 0)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.isa_r1 <<= 0
                self.vm_id <<= 0
            with Else():
                with If((self.eu_macro_xor_i_valid & self.eu_macro_xor_i_ready)):
                    self.isa_r1 <<= self.eu_macro_xor_data[(self.ISA_BITS + (2 * self.REG_WIDTH)):(2 * self.REG_WIDTH)]
                    self.vm_id <<= self.eu_macro_xor_i_vm_id

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.xor_o_valid <<= 0
            with Else():
                with If(self.eu_macro_xor_i_ready):
                    self.xor_o_valid <<= self.eu_macro_xor_i_valid

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.xor_data <<= 0
            with Else():
                with If((self.eu_macro_xor_i_valid & self.eu_macro_xor_i_ready)):
                    self.xor_data <<= Cat(self.operand_0[(self.REG_WIDTH - 1):self.DATA_WIDTH], self.operand_xor)
