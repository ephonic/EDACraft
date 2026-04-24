"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_logical(Module):
    def __init__(self, name: str = "js_vm_logical"):
        super().__init__(name or "js_vm_logical")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.sq_logic_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_logic_data")
        self.sq_logic_i_valid = Input(1, "sq_logic_i_valid")
        self.sq_logic_i_vm_id = Input(4, "sq_logic_i_vm_id")
        self.sq_logic_o_ready = Input(1, "sq_logic_o_ready")
        self.sq_logic_i_ready = Output(1, "sq_logic_i_ready")
        self.sq_logic_o_valid = Output(1, "sq_logic_o_valid")
        self.sq_logic_o_vm_id = Output(4, "sq_logic_o_vm_id")
        self.sq_logic_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "sq_logic_res")
        self.logic_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "logic_sq_fc_dec")
        self.logic_sq_fc_dec_vm_id = Output(4, "logic_sq_fc_dec_vm_id")

        self.sf = Wire(((self.FC_NUM - 1) - 0 + 1), "sf")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")

        # TODO: unpack assignment: Cat(self.sq_logic_isa, self.sq_logic_cc_value, self.logic_data_y, self.logic_data_x) = self.sq_logic_data
        # Consider using Split() or manual bit slicing
        self.sq_logic_data_y <<= Mux(self.sq_logic_i_valid, self.logic_data_y, 0)
        self.sq_logic_data_x <<= Mux(self.sq_logic_i_valid, self.logic_data_x, 0)
        self.opcode <<= self.sq_logic_isa[5:3]
        self.src0_imm <<= self.sq_logic_isa[33:26]
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.DATA_WIDTH):
            self.truncate_window[i] <<= Mux((i < self.src0_imm), 1, 0)

        @self.comb
        def _comb_logic():
            with Switch(self.opcode) as sw:
                with sw.case(self.OPCODE_LXOR):
                    self.result <<= Mux((self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] != self.sq_logic_data_y[(self.DATA_WIDTH - 1):0]), 1, 0)
                with sw.case(self.OPCODE_LAND):
                    self.result <<= Mux(((self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] == 1) & (self.sq_logic_data_y[(self.DATA_WIDTH - 1):0] == 1)), 1, 0)
                with sw.case(self.OPCODE_LOR):
                    self.result <<= Mux(((self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] == 1) | (self.sq_logic_data_y[(self.DATA_WIDTH - 1):0] == 1)), 1, 0)
                with sw.case(self.OPCODE_LNAND):
                    self.result <<= Mux(((self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] == 1) & (self.sq_logic_data_y[(self.DATA_WIDTH - 1):0] == 1)), 0, 1)
                with sw.case(self.OPCODE_LNOR):
                    self.result <<= Mux(((self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] == 1) | (self.sq_logic_data_y[(self.DATA_WIDTH - 1):0] == 1)), 0, 1)
                with sw.case(self.OPCODE_TERNARY):
                    self.result <<= Mux((self.sq_logic_cc_value > 0), self.sq_logic_data_x[(self.DATA_WIDTH - 1):0], self.sq_logic_data_y[(self.DATA_WIDTH - 1):0])
                with sw.case(self.OPCODE_SHIFT):
                    self.result <<= (self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] >> self.src0_imm)
                with sw.case(self.OPCODE_TRUNCATE):
                    self.result <<= (self.sq_logic_data_x[(self.DATA_WIDTH - 1):0] & self.truncate_window)
                with sw.default():
                    self.result <<= 0
        self.sq_logic_i_ready <<= ((~self.sq_logic_o_valid) | self.sq_logic_o_ready)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.sq_logic_o_valid <<= 0
            with Else():
                with If(self.sq_logic_i_ready):
                    self.sq_logic_o_valid <<= self.sq_logic_i_valid

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.sq_logic_o_vm_id <<= 0
                self.sq_logic_res <<= 0
            with Else():
                with If((self.sq_logic_i_ready & self.sq_logic_i_valid)):
                    self.sq_logic_o_vm_id <<= self.sq_logic_i_vm_id
                    self.sq_logic_res <<= Cat(self.sq_logic_isa, self.sq_logic_cc_value, Cat(Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.result))

        @self.comb
        def _comb_logic():
            self.logic_sq_fc_dec <<= self.fc_dec
            self.logic_sq_fc_dec_vm_id <<= self.sq_logic_o_vm_id
        # unhandled statement: # function get_sf
