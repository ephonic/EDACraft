"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_eu_slice(Module):
    def __init__(self, name: str = "js_vm_eu_slice"), ID_BITS: int = # <SystemCall>:
        super().__init__(name or "js_vm_eu_slice")

        self.add_localparam("ID_BITS", # <SystemCall>)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.aleo_cr_debug_mode = Input(2, "aleo_cr_debug_mode")
        self.aleo_cr_debug_id = Input(4, "aleo_cr_debug_id")
        self.aleo_cr_q = Input(256, "aleo_cr_q")
        self.aleo_cr_mu = Input(256, "aleo_cr_mu")
        self.slice_sq_pap_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_pap_valid")
        self.slice_sq_pap_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_pap_data")
        self.slice_sq_pap_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_pap_ready")
        self.slice_sq_map_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_map_valid")
        self.slice_sq_map_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_map_data")
        self.slice_sq_map_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_map_ready")
        self.slice_sq_mip_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_mip_valid")
        self.slice_sq_mip_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_mip_data")
        self.slice_sq_mip_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_mip_ready")
        self.slice_sq_lgc_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_lgc_valid")
        self.slice_sq_lgc_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_lgc_data")
        self.slice_sq_lgc_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_lgc_ready")
        self.slice_sq_alu_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_alu_valid")
        self.slice_sq_alu_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_alu_data")
        self.slice_sq_alu_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_alu_ready")
        self.slice_sq_tbt_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_tbt_valid")
        self.slice_sq_tbt_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_tbt_data")
        self.slice_sq_tbt_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_tbt_ready")
        self.slice_sq_mov_valid = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_mov_valid")
        self.slice_sq_mov_data = Input((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_sq_mov_data")
        self.slice_sq_mov_ready = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_sq_mov_ready")
        self.slice_pap_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_pap_sq_fc_dec")
        self.slice_map_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_map_sq_fc_dec")
        self.slice_mip_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_mip_sq_fc_dec")
        self.slice_lgc_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_lgc_sq_fc_dec")
        self.slice_alu_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_alu_sq_fc_dec")
        self.slice_tbt_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_tbt_sq_fc_dec")
        self.slice_mov_sq_fc_dec = Output((((self.VM_PER_SLICE * self.FC_NUM) - 1) - 0 + 1), "slice_mov_sq_fc_dec")
        self.slice_pap_sq_hq_rel_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_pap_sq_hq_rel_valid")
        self.slice_cc_update = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_cc_update")
        self.slice_cc_update_value = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_cc_update_value")
        self.slice_rbank0_write_addr = Output((((self.VM_PER_SLICE * (self.GPR_ADDR_BITS - 1)) - 1) - 0 + 1), "slice_rbank0_write_addr")
        self.slice_rbank0_write_data = Output((((self.VM_PER_SLICE * self.REG_WIDTH) - 1) - 0 + 1), "slice_rbank0_write_data")
        self.slice_rbank0_write_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_rbank0_write_valid")
        self.slice_rbank1_write_addr = Output((((self.VM_PER_SLICE * (self.GPR_ADDR_BITS - 1)) - 1) - 0 + 1), "slice_rbank1_write_addr")
        self.slice_rbank1_write_data = Output((((self.VM_PER_SLICE * self.REG_WIDTH) - 1) - 0 + 1), "slice_rbank1_write_data")
        self.slice_rbank1_write_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_rbank1_write_valid")
        self.slice_eu_mh_valid = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_eu_mh_valid")
        self.slice_eu_mh_index = Output((((self.VM_PER_SLICE * 18) - 1) - 0 + 1), "slice_eu_mh_index")
        self.slice_eu_mh_vm_id = Output((((self.VM_PER_SLICE * 4) - 1) - 0 + 1), "slice_eu_mh_vm_id")
        self.slice_eu_mh_data = Output((((self.VM_PER_SLICE * 256) - 1) - 0 + 1), "slice_eu_mh_data")
        self.slice_eu_mh_type = Output((((self.VM_PER_SLICE * 4) - 1) - 0 + 1), "slice_eu_mh_type")
        self.slice_eu_mh_last = Output(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_eu_mh_last")
        self.slice_eu_mh_ready = Input(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_eu_mh_ready")
        self.debug_mh_valid = Output(1, "debug_mh_valid")
        self.debug_mh_data = Output(256, "debug_mh_data")
        self.debug_mh_ready = Input(1, "debug_mh_ready")

        self.slice_alu_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_alu_sq_data")
        self.slice_alu_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_alu_sq_ready")
        self.slice_alu_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_alu_sq_valid")
        self.slice_lgc_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_lgc_sq_data")
        self.slice_lgc_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_lgc_sq_ready")
        self.slice_lgc_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_lgc_sq_valid")
        self.slice_map_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_map_sq_data")
        self.slice_map_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_map_sq_ready")
        self.slice_map_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_map_sq_valid")
        self.slice_mip_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_mip_sq_data")
        self.slice_mip_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_mip_sq_ready")
        self.slice_mip_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_mip_sq_valid")
        self.slice_mov_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_mov_sq_data")
        self.slice_mov_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_mov_sq_ready")
        self.slice_mov_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_mov_sq_valid")
        self.slice_pap_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_pap_sq_data")
        self.slice_pap_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_pap_sq_ready")
        self.slice_pap_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_pap_sq_valid")
        self.slice_tbt_sq_data = Wire((((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "slice_tbt_sq_data")
        self.slice_tbt_sq_mask = Wire((((self.VM_PER_SLICE * 2) - 1) - 0 + 1), "slice_tbt_sq_mask")
        self.slice_tbt_sq_ready = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_tbt_sq_ready")
        self.slice_tbt_sq_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_tbt_sq_valid")
        self.sq_alu_vm_id = Wire(((4 - 1) - 0 + 1), "sq_alu_vm_id")
        self.sq_lgc_vm_id = Wire(((4 - 1) - 0 + 1), "sq_lgc_vm_id")
        self.sq_map_vm_id = Wire(((4 - 1) - 0 + 1), "sq_map_vm_id")
        self.sq_mip_vm_id = Wire(((4 - 1) - 0 + 1), "sq_mip_vm_id")
        self.sq_mov_vm_id = Wire(((4 - 1) - 0 + 1), "sq_mov_vm_id")
        self.sq_pap_vm_id = Wire(((4 - 1) - 0 + 1), "sq_pap_vm_id")
        self.sq_tbt_vm_id = Wire(((4 - 1) - 0 + 1), "sq_tbt_vm_id")
        self.sq_pap_valid = Wire(1, "sq_pap_valid")
        self.sq_pap_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_pap_data")
        self.sq_pap_ready = Wire(1, "sq_pap_ready")
        self.sq_map_valid = Wire(1, "sq_map_valid")
        self.sq_map_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_map_data")
        self.sq_map_ready = Wire(1, "sq_map_ready")
        self.sq_mip_valid = Wire(1, "sq_mip_valid")
        self.sq_mip_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_mip_data")
        self.sq_mip_ready = Wire(1, "sq_mip_ready")
        self.sq_lgc_valid = Wire(1, "sq_lgc_valid")
        self.sq_lgc_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_lgc_data")
        self.sq_lgc_ready = Wire(1, "sq_lgc_ready")
        self.sq_alu_valid = Wire(1, "sq_alu_valid")
        self.sq_alu_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_alu_data")
        self.sq_alu_ready = Wire(1, "sq_alu_ready")
        self.sq_tbt_valid = Wire(1, "sq_tbt_valid")
        self.sq_tbt_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_tbt_data")
        self.sq_tbt_ready = Wire(1, "sq_tbt_ready")
        self.sq_mov_valid = Wire(1, "sq_mov_valid")
        self.sq_mov_data = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_mov_data")
        self.sq_mov_ready = Wire(1, "sq_mov_ready")
        self.sq_pap_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_pap_data_array", vtype=Wire)
        self.sq_map_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_map_data_array", vtype=Wire)
        self.sq_mip_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_mip_data_array", vtype=Wire)
        self.sq_lgc_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_lgc_data_array", vtype=Wire)
        self.sq_alu_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_alu_data_array", vtype=Wire)
        self.sq_tbt_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_tbt_data_array", vtype=Wire)
        self.sq_mov_data_array = Array(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), (0 - (self.VM_PER_SLICE - 1) + 1), "sq_mov_data_array", vtype=Wire)
        self.pap_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "pap_sq_fc_dec")
        self.pap_sq_fc_dec_vm_id = Wire(4, "pap_sq_fc_dec_vm_id")
        self.map_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "map_sq_fc_dec")
        self.map_sq_fc_dec_vm_id = Wire(4, "map_sq_fc_dec_vm_id")
        self.mip_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "mip_sq_fc_dec")
        self.mip_sq_fc_dec_vm_id = Wire(4, "mip_sq_fc_dec_vm_id")
        self.lgc_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "lgc_sq_fc_dec")
        self.lgc_sq_fc_dec_vm_id = Wire(4, "lgc_sq_fc_dec_vm_id")
        self.alu_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "alu_sq_fc_dec")
        self.alu_sq_fc_dec_vm_id = Wire(4, "alu_sq_fc_dec_vm_id")
        self.tbt_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "tbt_sq_fc_dec")
        self.tbt_sq_fc_dec_vm_id = Wire(4, "tbt_sq_fc_dec_vm_id")
        self.mov_sq_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "mov_sq_fc_dec")
        self.mov_sq_fc_dec_vm_id = Wire(4, "mov_sq_fc_dec_vm_id")
        self.pap_sq_hq_rel_valid = Wire(1, "pap_sq_hq_rel_valid")
        self.pap_sq_hq_rel_vm_id = Wire(4, "pap_sq_hq_rel_vm_id")
        self.slice_debug_mh_valid = Wire(((self.VM_PER_SLICE - 1) - 0 + 1), "slice_debug_mh_valid")
        self.slice_debug_mh_data = Array(256, ((self.VM_PER_SLICE - 1) - 0 + 1), "slice_debug_mh_data", vtype=Wire)


        u_pap_pipe = js_vm_eu_pipe(PIPE_TYPE=0)
        self.instantiate(
            u_pap_pipe,
            "u_pap_pipe",
            params={'PIPE_TYPE': 0},
            port_map={
                "slice_i_ready": self.slice_sq_pap_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_pap_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_pap_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_pap_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": self.slice_pap_sq_hq_rel_valid[(self.VM_PER_SLICE - 1):0],
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_pap_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_pap_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_pap_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_map_pipe = js_vm_eu_pipe(PIPE_TYPE=1)
        self.instantiate(
            u_map_pipe,
            "u_map_pipe",
            params={'PIPE_TYPE': 1},
            port_map={
                "slice_i_ready": self.slice_sq_map_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_map_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_map_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_map_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_map_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_map_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_map_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_mip_pipe = js_vm_eu_pipe(PIPE_TYPE=2)
        self.instantiate(
            u_mip_pipe,
            "u_mip_pipe",
            params={'PIPE_TYPE': 2},
            port_map={
                "slice_i_ready": self.slice_sq_mip_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_mip_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_mip_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_mip_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_mip_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_mip_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_mip_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_lgc_pipe = js_vm_eu_pipe(PIPE_TYPE=3)
        self.instantiate(
            u_lgc_pipe,
            "u_lgc_pipe",
            params={'PIPE_TYPE': 3},
            port_map={
                "slice_i_ready": self.slice_sq_lgc_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_lgc_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_lgc_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_lgc_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_lgc_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_lgc_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_lgc_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_alu_pipe = js_vm_eu_pipe(PIPE_TYPE=4)
        self.instantiate(
            u_alu_pipe,
            "u_alu_pipe",
            params={'PIPE_TYPE': 4},
            port_map={
                "slice_i_ready": self.slice_sq_alu_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_alu_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_alu_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_alu_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_alu_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_alu_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_alu_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_mov_pipe = js_vm_eu_pipe(PIPE_TYPE=6)
        self.instantiate(
            u_mov_pipe,
            "u_mov_pipe",
            params={'PIPE_TYPE': 6},
            port_map={
                "slice_i_ready": self.slice_sq_mov_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_mov_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_mov_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": None,
                "slice_o_fc_dec": self.slice_mov_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_mov_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_mov_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_mov_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )

        u_tbt_pipe = js_vm_eu_pipe(PIPE_TYPE=5)
        self.instantiate(
            u_tbt_pipe,
            "u_tbt_pipe",
            params={'PIPE_TYPE': 5},
            port_map={
                "slice_i_ready": self.slice_sq_tbt_ready[(self.VM_PER_SLICE - 1):0],
                "slice_o_valid": self.slice_tbt_sq_valid[(self.VM_PER_SLICE - 1):0],
                "slice_o_data": self.slice_tbt_sq_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_mask": self.slice_tbt_sq_mask[((self.VM_PER_SLICE * 2) - 1):0],
                "slice_o_fc_dec": self.slice_tbt_sq_fc_dec[((self.VM_PER_SLICE * self.FC_NUM) - 1):0],
                "slice_o_hq_rel_valid": None,
                "clk": self.clk,
                "rstn": self.rstn,
                "aleo_cr_q": self.aleo_cr_q[255:0],
                "aleo_cr_mu": self.aleo_cr_mu[255:0],
                "slice_i_valid": self.slice_sq_tbt_valid[(self.VM_PER_SLICE - 1):0],
                "slice_i_data": self.slice_sq_tbt_data[((self.VM_PER_SLICE * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1):0],
                "slice_o_ready": self.slice_tbt_sq_ready[(self.VM_PER_SLICE - 1):0],
            },
        )
        self.debug_mh_valid <<= (self.slice_debug_mh_valid[self.aleo_cr_debug_id[1:0]] & self.aleo_cr_debug_mode[1])
        self.debug_mh_data <<= self.slice_debug_mh_data[self.aleo_cr_debug_id[1:0]]
        with GenIf((self.VM_PER_SLICE == 1)):

            @self.comb
            def _comb_logic():
                self.slice_debug_mh_ready <<= self.debug_mh_ready
        with GenElse():

            @self.comb
            def _comb_logic():
                self.slice_debug_mh_ready <<= Rep(Cat(1), self.VM_PER_SLICE)
                self.slice_debug_mh_ready[self.aleo_cr_debug_id[1:0]] <<= self.debug_mh_ready
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.VM_PER_SLICE):
            # unhandled statement: # <InstanceList>
