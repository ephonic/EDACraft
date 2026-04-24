"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_eu_pipe(Module):
    def __init__(self, name: str = "js_vm_eu_pipe"), PIPE_TYPE: int = 0, ID_BITS: int = # <SystemCall>:
        super().__init__(name or "js_vm_eu_pipe")

        self.add_localparam("ID_BITS", # <SystemCall>)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.aleo_cr_q = Input(256, "aleo_cr_q")
        self.aleo_cr_mu = Input(256, "aleo_cr_mu")
        self.slice_i_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_i_valid")
        self.slice_i_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_i_data")
        self.slice_i_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_i_ready")
        self.slice_o_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_o_valid")
        self.slice_o_data = Output((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_o_data")
        self.slice_o_mask = Output((((self.VM_PER_SLICE * 2) - 1) - 0 + 1), "slice_o_mask")
        self.slice_o_ready = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_o_ready")
        self.slice_o_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_o_fc_dec")
        self.slice_o_hq_rel_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_o_hq_rel_valid")

        self.pipe_o_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "pipe_o_fc_dec")
        self.pipe_o_fc_dec_vm_id = Wire(4, "pipe_o_fc_dec_vm_id")
        self.pipe_o_valid = Wire(1, "pipe_o_valid")
        self.pipe_o_data = Wire(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "pipe_o_data")
        self.pipe_o_vm_id = Wire(4, "pipe_o_vm_id")
        self.pipe_o_ready = Wire(1, "pipe_o_ready")
        self.pipe_o_hq_rel_valid = Wire(1, "pipe_o_hq_rel_valid")
        self.pipe_o_hq_rel_vm_id = Wire(4, "pipe_o_hq_rel_vm_id")
        self.slice_i_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "slice_i_data_array", vtype=Wire)

        with GenIf((self.PIPE_TYPE == 0)):
            self.slice_o_mask <<= 0
            # for-loop (non-generate) - parameter-driven
            for i in range(0, self.VM_PER_SLICE):
                self.slice_i_data_array[i] <<= self.slice_i_data[(i * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)):((i * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) + ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1))]
            with If((self.VM_PER_SLICE == 1)):
                self.pipe_i_vm_id <<= 0
                self.pipe_i_valid <<= self.slice_i_valid
                self.pipe_i_data <<= self.slice_i_data
                self.slice_i_ready <<= self.pipe_i_ready
                self.slice_o_valid <<= self.pipe_o_valid
                self.slice_o_data <<= Cat(Rep(Cat(0), self.REG_WIDTH), self.pipe_o_data)
                self.pipe_o_ready <<= self.slice_o_ready
                self.slice_o_fc_dec <<= self.pipe_o_fc_dec
                self.slice_o_hq_rel_valid <<= self.pipe_o_hq_rel_valid
            with Else():
                self.pipe_i_data <<= self.slice_i_data_array[self.pipe_i_vm_id[(self.ID_BITS - 1):0]]
                self.slice_o_valid <<= Mux(self.pipe_o_valid, (Cat(Rep(Cat(0), (self.VM_PER_SLICE - 1)), 1) << self.pipe_o_vm_id[(self.ID_BITS - 1):0]), 0)
                self.slice_o_data <<= (Cat(Rep(Cat(0), ((self.VM_PER_SLICE - 1) * (self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)))), Cat(Rep(Cat(0), self.REG_WIDTH), self.pipe_o_data)) << (self.pipe_o_vm_id[(self.ID_BITS - 1):0] * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)))
                self.pipe_o_ready <<= self.slice_o_ready[self.pipe_o_vm_id[(self.ID_BITS - 1):0]]
                self.slice_o_fc_dec <<= Mux((~|self.pipe_o_fc_dec), Rep(Cat(0), (self.VM_PER_SLICE * self.FC_NUM)), (Cat(Rep(Cat(0), ((self.VM_PER_SLICE * self.FC_NUM) - self.FC_NUM)), self.pipe_o_fc_dec) << (self.pipe_o_fc_dec_vm_id[(self.ID_BITS - 1):0] * self.FC_NUM)))
                self.slice_o_hq_rel_valid <<= Mux((not self.pipe_o_hq_rel_valid), Rep(Cat(0), self.VM_PER_SLICE), (Cat(Rep(Cat(0), (self.VM_PER_SLICE - 1)), self.pipe_o_hq_rel_valid) << self.pipe_o_hq_rel_vm_id[(self.ID_BITS - 1):0]))
                # unhandled statement: # <InstanceList>
                with If((self.VM_PER_SLICE != 16)):
                    self.pipe_i_vm_id[3:self.ID_BITS] <<= 0
            # unhandled statement: # <InstanceList>
            # unhandled statement: # <InstanceList>
        with GenElse():
            with If((self.PIPE_TYPE == 1)):
                self.slice_o_mask <<= 0
                self.slice_o_hq_rel_valid <<= 0
                # for-loop (non-generate) - parameter-driven
                for i in range(0, self.VM_PER_SLICE):
                    self.slice_i_vm_id[i] <<= i
                    # unhandled statement: # <InstanceList>
                    # unhandled statement: # <InstanceList>
            with Else():
                with If((self.PIPE_TYPE == 2)):
                    self.slice_o_mask <<= 0
                    self.slice_o_hq_rel_valid <<= 0
                    self.slice_i_ready <<= (not self.mip_infifo_full)
                    # for-loop (non-generate) - parameter-driven
                    for i in range(0, self.VM_PER_SLICE):
                        self.slice_i_vm_id[i] <<= i
                        self.mip_slice_i_valid[i] <<= (~self.mip_infifo_empty[i])
                        self.mip_infifo_pop[i] <<= (self.mip_slice_i_valid[i] & self.mip_slice_i_ready[i])
                        # unhandled statement: # <InstanceList>
                        # unhandled statement: # <InstanceList>
                        # unhandled statement: # <InstanceList>
                with Else():
                    with If((self.PIPE_TYPE == 3)):
                        self.slice_o_mask <<= 0
                        self.slice_o_hq_rel_valid <<= 0
                        # for-loop (non-generate) - parameter-driven
                        for i in range(0, self.VM_PER_SLICE):
                            self.slice_i_vm_id[i] <<= i
                            # unhandled statement: # <InstanceList>
                    with Else():
                        with If((self.PIPE_TYPE == 4)):
                            self.slice_o_mask <<= 0
                            # for-loop (non-generate) - parameter-driven
                            for i in range(0, self.VM_PER_SLICE):
                                self.slice_i_data_array[i] <<= self.slice_i_data[(i * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)):((i * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) + ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1))]
                            with If((self.VM_PER_SLICE == 1)):
                                self.pipe_i_vm_id <<= 0
                                self.pipe_i_valid <<= self.slice_i_valid
                                self.pipe_i_data <<= self.slice_i_data
                                self.slice_i_ready <<= self.pipe_i_ready
                                self.slice_o_valid <<= self.pipe_o_valid
                                self.slice_o_data <<= Cat(Rep(Cat(0), self.REG_WIDTH), self.pipe_o_data)
                                self.pipe_o_ready <<= self.slice_o_ready
                                self.slice_o_fc_dec <<= self.pipe_o_fc_dec
                                self.slice_o_hq_rel_valid <<= 0
                            with Else():
                                self.pipe_i_data_pre <<= self.slice_i_data_array[self.pipe_i_vm_id_pre[(self.ID_BITS - 1):0]]
                                self.slice_o_valid <<= Mux(self.pipe_o_valid, (Cat(Rep(Cat(0), (self.VM_PER_SLICE - 1)), 1) << self.pipe_o_vm_id[(self.ID_BITS - 1):0]), 0)
                                self.slice_o_data <<= (Cat(Rep(Cat(0), ((self.VM_PER_SLICE - 1) * (self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)))), Cat(Rep(Cat(0), self.REG_WIDTH), self.pipe_o_data)) << (self.pipe_o_vm_id[(self.ID_BITS - 1):0] * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)))
                                self.pipe_o_ready <<= self.slice_o_ready[self.pipe_o_vm_id[(self.ID_BITS - 1):0]]
                                self.slice_o_fc_dec <<= Mux((~|self.pipe_o_fc_dec), Rep(Cat(0), (self.VM_PER_SLICE * self.FC_NUM)), (Cat(Rep(Cat(0), ((self.VM_PER_SLICE * self.FC_NUM) - self.FC_NUM)), self.pipe_o_fc_dec) << (self.pipe_o_fc_dec_vm_id[(self.ID_BITS - 1):0] * self.FC_NUM)))
                                self.slice_o_hq_rel_valid <<= 0
                                # unhandled statement: # <InstanceList>
                                with If((self.VM_PER_SLICE != 16)):
                                    self.pipe_i_vm_id_pre[3:self.ID_BITS] <<= 0

                            @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
                            def _seq_logic():
                                with If((~self.rstn)):
                                    self.pipe_i_valid <<= 0
                                with Else():
                                    with If(self.pipe_i_ready_pre):
                                        self.pipe_i_valid <<= self.pipe_i_valid_pre
                            self.pipe_i_ready_pre <<= (self.pipe_i_ready | (~self.pipe_i_valid))

                            @self.seq(self.clk, None)
                            def _seq_logic():
                                with If((self.pipe_i_valid_pre & self.pipe_i_ready_pre)):
                                    self.pipe_i_vm_id <<= self.pipe_i_vm_id_pre
                                    self.pipe_i_data <<= self.pipe_i_data_pre
                            # unhandled statement: # <InstanceList>
                            # unhandled statement: # <InstanceList>
                        with Else():
                            with If((self.PIPE_TYPE == 5)):
                                self.slice_o_hq_rel_valid <<= 0
                                # for-loop (non-generate) - parameter-driven
                                for i in range(0, self.VM_PER_SLICE):
                                    self.slice_i_vm_id[i] <<= i
                                    # unhandled statement: # <InstanceList>
                                    # unhandled statement: # <InstanceList>
                            with Else():
                                with If((self.PIPE_TYPE == 6)):
                                    self.slice_o_mask <<= 0
                                    self.slice_o_hq_rel_valid <<= 0
                                    # for-loop (non-generate) - parameter-driven
                                    for i in range(0, self.VM_PER_SLICE):
                                        self.slice_i_vm_id[i] <<= i
                                        # unhandled statement: # <InstanceList>
