"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class divider(Module):
    def __init__(self, name: str = "divider"):
        super().__init__(name or "divider")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_i = Input(1, "valid_i")
        self.ready_o = Output(1, "ready_o")
        self.div_full_in = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "div_full_in")
        self.div_full_out = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "div_full_out")
        self.div_vm_id_in = Input(4, "div_vm_id_in")
        self.div_vm_id_out = Output(4, "div_vm_id_out")
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
        self.res = Wire(128, "res")

        # TODO: unpack assignment: Cat(self.int_and_isa, self.int_and_cc_value, self.int_and_data_y, self.int_and_data_x) = self.div_full_in
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype) = self.int_and_isa
        # Consider using Split() or manual bit slicing
        self.flag_bits <<= self.src0_fmt[(self.ISA_SRC0_FMT_BITS - 1):1]
        self.signed_mode_src0 <<= self.src0_fmt[0]
        self.signed_mode_src1 <<= self.src1_fmt[0]

        div_core = divider_core()
        self.instantiate(
            div_core,
            "div_core",
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "valid_i": self.valid_i,
                "ready_o": self.ready_o,
                "valid_o": self.valid_o,
                "ready_i": self.ready_i,
                "flags_src0": self.flag_bits,
                "flags_src1": self.flag_bits,
                "signed_mode_src0": self.signed_mode_src0,
                "signed_mode_src1": self.signed_mode_src1,
                "src0": self.int_and_data_x[127:0],
                "src1": self.int_and_data_y[127:0],
                "vm_id_in": self.div_vm_id_in,
                "vm_id_out": self.div_vm_id_out,
                "div_full_in": self.div_full_in,
                "div_full_out": self.div_full_out,
            },
        )
