"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_eu(Module):
    def __init__(self, name: str = "js_vm_eu"):
        super().__init__(name or "js_vm_eu")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.aleo_cr_debug_mode = Input(2, "aleo_cr_debug_mode")
        self.aleo_cr_debug_id = Input(4, "aleo_cr_debug_id")
        self.aleo_cr_q = Input(256, "aleo_cr_q")
        self.aleo_cr_mu = Input(256, "aleo_cr_mu")
        self.sq_pap_valids = Input(16, "sq_pap_valids")
        self.sq_pap_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_pap_datas")
        self.sq_pap_readys = Output(16, "sq_pap_readys")
        self.sq_map_valids = Input(16, "sq_map_valids")
        self.sq_map_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_map_datas")
        self.sq_map_readys = Output(16, "sq_map_readys")
        self.sq_mip_valids = Input(16, "sq_mip_valids")
        self.sq_mip_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_mip_datas")
        self.sq_mip_readys = Output(16, "sq_mip_readys")
        self.sq_lgc_valids = Input(16, "sq_lgc_valids")
        self.sq_lgc_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_lgc_datas")
        self.sq_lgc_readys = Output(16, "sq_lgc_readys")
        self.sq_alu_valids = Input(16, "sq_alu_valids")
        self.sq_alu_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_alu_datas")
        self.sq_alu_readys = Output(16, "sq_alu_readys")
        self.sq_tbt_valids = Input(16, "sq_tbt_valids")
        self.sq_tbt_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_tbt_datas")
        self.sq_tbt_readys = Output(16, "sq_tbt_readys")
        self.sq_mov_valids = Input(16, "sq_mov_valids")
        self.sq_mov_datas = Input((((16 * ((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1)) - 1) - 0 + 1), "sq_mov_datas")
        self.sq_mov_readys = Output(16, "sq_mov_readys")
        self.pap_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "pap_sq_fc_dec")
        self.map_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "map_sq_fc_dec")
        self.mip_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "mip_sq_fc_dec")
        self.lgc_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "lgc_sq_fc_dec")
        self.alu_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "alu_sq_fc_dec")
        self.tbt_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "tbt_sq_fc_dec")
        self.mov_sq_fc_dec = Output((((16 * self.FC_NUM) - 1) - 0 + 1), "mov_sq_fc_dec")
        self.pap_sq_hq_rel_valid = Output(16, "pap_sq_hq_rel_valid")
        self.debug_mh_data = Output(256, "debug_mh_data")
        self.debug_mh_valid = Output(1, "debug_mh_valid")
        self.vm0_cc_update = Output(1, "vm0_cc_update")
        self.vm0_cc_update_value = Output(1, "vm0_cc_update_value")
        self.vm0_eu_mh_data = Output(256, "vm0_eu_mh_data")
        self.vm0_eu_mh_index = Output(18, "vm0_eu_mh_index")
        self.vm0_eu_mh_last = Output(1, "vm0_eu_mh_last")
        self.vm0_eu_mh_type = Output(4, "vm0_eu_mh_type")
        self.vm0_eu_mh_valid = Output(1, "vm0_eu_mh_valid")
        self.vm0_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm0_rbank0_write_addr")
        self.vm0_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm0_rbank0_write_data")
        self.vm0_rbank0_write_valid = Output(1, "vm0_rbank0_write_valid")
        self.vm0_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm0_rbank1_write_addr")
        self.vm0_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm0_rbank1_write_data")
        self.vm0_rbank1_write_valid = Output(1, "vm0_rbank1_write_valid")
        self.vm10_cc_update = Output(1, "vm10_cc_update")
        self.vm10_cc_update_value = Output(1, "vm10_cc_update_value")
        self.vm10_eu_mh_data = Output(256, "vm10_eu_mh_data")
        self.vm10_eu_mh_index = Output(18, "vm10_eu_mh_index")
        self.vm10_eu_mh_last = Output(1, "vm10_eu_mh_last")
        self.vm10_eu_mh_type = Output(4, "vm10_eu_mh_type")
        self.vm10_eu_mh_valid = Output(1, "vm10_eu_mh_valid")
        self.vm10_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm10_rbank0_write_addr")
        self.vm10_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm10_rbank0_write_data")
        self.vm10_rbank0_write_valid = Output(1, "vm10_rbank0_write_valid")
        self.vm10_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm10_rbank1_write_addr")
        self.vm10_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm10_rbank1_write_data")
        self.vm10_rbank1_write_valid = Output(1, "vm10_rbank1_write_valid")
        self.vm11_cc_update = Output(1, "vm11_cc_update")
        self.vm11_cc_update_value = Output(1, "vm11_cc_update_value")
        self.vm11_eu_mh_data = Output(256, "vm11_eu_mh_data")
        self.vm11_eu_mh_index = Output(18, "vm11_eu_mh_index")
        self.vm11_eu_mh_last = Output(1, "vm11_eu_mh_last")
        self.vm11_eu_mh_type = Output(4, "vm11_eu_mh_type")
        self.vm11_eu_mh_valid = Output(1, "vm11_eu_mh_valid")
        self.vm11_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm11_rbank0_write_addr")
        self.vm11_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm11_rbank0_write_data")
        self.vm11_rbank0_write_valid = Output(1, "vm11_rbank0_write_valid")
        self.vm11_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm11_rbank1_write_addr")
        self.vm11_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm11_rbank1_write_data")
        self.vm11_rbank1_write_valid = Output(1, "vm11_rbank1_write_valid")
        self.vm12_cc_update = Output(1, "vm12_cc_update")
        self.vm12_cc_update_value = Output(1, "vm12_cc_update_value")
        self.vm12_eu_mh_data = Output(256, "vm12_eu_mh_data")
        self.vm12_eu_mh_index = Output(18, "vm12_eu_mh_index")
        self.vm12_eu_mh_last = Output(1, "vm12_eu_mh_last")
        self.vm12_eu_mh_type = Output(4, "vm12_eu_mh_type")
        self.vm12_eu_mh_valid = Output(1, "vm12_eu_mh_valid")
        self.vm12_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm12_rbank0_write_addr")
        self.vm12_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm12_rbank0_write_data")
        self.vm12_rbank0_write_valid = Output(1, "vm12_rbank0_write_valid")
        self.vm12_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm12_rbank1_write_addr")
        self.vm12_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm12_rbank1_write_data")
        self.vm12_rbank1_write_valid = Output(1, "vm12_rbank1_write_valid")
        self.vm13_cc_update = Output(1, "vm13_cc_update")
        self.vm13_cc_update_value = Output(1, "vm13_cc_update_value")
        self.vm13_eu_mh_data = Output(256, "vm13_eu_mh_data")
        self.vm13_eu_mh_index = Output(18, "vm13_eu_mh_index")
        self.vm13_eu_mh_last = Output(1, "vm13_eu_mh_last")
        self.vm13_eu_mh_type = Output(4, "vm13_eu_mh_type")
        self.vm13_eu_mh_valid = Output(1, "vm13_eu_mh_valid")
        self.vm13_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm13_rbank0_write_addr")
        self.vm13_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm13_rbank0_write_data")
        self.vm13_rbank0_write_valid = Output(1, "vm13_rbank0_write_valid")
        self.vm13_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm13_rbank1_write_addr")
        self.vm13_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm13_rbank1_write_data")
        self.vm13_rbank1_write_valid = Output(1, "vm13_rbank1_write_valid")
        self.vm14_cc_update = Output(1, "vm14_cc_update")
        self.vm14_cc_update_value = Output(1, "vm14_cc_update_value")
        self.vm14_eu_mh_data = Output(256, "vm14_eu_mh_data")
        self.vm14_eu_mh_index = Output(18, "vm14_eu_mh_index")
        self.vm14_eu_mh_last = Output(1, "vm14_eu_mh_last")
        self.vm14_eu_mh_type = Output(4, "vm14_eu_mh_type")
        self.vm14_eu_mh_valid = Output(1, "vm14_eu_mh_valid")
        self.vm14_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm14_rbank0_write_addr")
        self.vm14_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm14_rbank0_write_data")
        self.vm14_rbank0_write_valid = Output(1, "vm14_rbank0_write_valid")
        self.vm14_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm14_rbank1_write_addr")
        self.vm14_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm14_rbank1_write_data")
        self.vm14_rbank1_write_valid = Output(1, "vm14_rbank1_write_valid")
        self.vm15_cc_update = Output(1, "vm15_cc_update")
        self.vm15_cc_update_value = Output(1, "vm15_cc_update_value")
        self.vm15_eu_mh_data = Output(256, "vm15_eu_mh_data")
        self.vm15_eu_mh_index = Output(18, "vm15_eu_mh_index")
        self.vm15_eu_mh_last = Output(1, "vm15_eu_mh_last")
        self.vm15_eu_mh_type = Output(4, "vm15_eu_mh_type")
        self.vm15_eu_mh_valid = Output(1, "vm15_eu_mh_valid")
        self.vm15_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm15_rbank0_write_addr")
        self.vm15_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm15_rbank0_write_data")
        self.vm15_rbank0_write_valid = Output(1, "vm15_rbank0_write_valid")
        self.vm15_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm15_rbank1_write_addr")
        self.vm15_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm15_rbank1_write_data")
        self.vm15_rbank1_write_valid = Output(1, "vm15_rbank1_write_valid")
        self.vm1_cc_update = Output(1, "vm1_cc_update")
        self.vm1_cc_update_value = Output(1, "vm1_cc_update_value")
        self.vm1_eu_mh_data = Output(256, "vm1_eu_mh_data")
        self.vm1_eu_mh_index = Output(18, "vm1_eu_mh_index")
        self.vm1_eu_mh_last = Output(1, "vm1_eu_mh_last")
        self.vm1_eu_mh_type = Output(4, "vm1_eu_mh_type")
        self.vm1_eu_mh_valid = Output(1, "vm1_eu_mh_valid")
        self.vm1_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm1_rbank0_write_addr")
        self.vm1_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm1_rbank0_write_data")
        self.vm1_rbank0_write_valid = Output(1, "vm1_rbank0_write_valid")
        self.vm1_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm1_rbank1_write_addr")
        self.vm1_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm1_rbank1_write_data")
        self.vm1_rbank1_write_valid = Output(1, "vm1_rbank1_write_valid")
        self.vm2_cc_update = Output(1, "vm2_cc_update")
        self.vm2_cc_update_value = Output(1, "vm2_cc_update_value")
        self.vm2_eu_mh_data = Output(256, "vm2_eu_mh_data")
        self.vm2_eu_mh_index = Output(18, "vm2_eu_mh_index")
        self.vm2_eu_mh_last = Output(1, "vm2_eu_mh_last")
        self.vm2_eu_mh_type = Output(4, "vm2_eu_mh_type")
        self.vm2_eu_mh_valid = Output(1, "vm2_eu_mh_valid")
        self.vm2_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm2_rbank0_write_addr")
        self.vm2_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm2_rbank0_write_data")
        self.vm2_rbank0_write_valid = Output(1, "vm2_rbank0_write_valid")
        self.vm2_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm2_rbank1_write_addr")
        self.vm2_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm2_rbank1_write_data")
        self.vm2_rbank1_write_valid = Output(1, "vm2_rbank1_write_valid")
        self.vm3_cc_update = Output(1, "vm3_cc_update")
        self.vm3_cc_update_value = Output(1, "vm3_cc_update_value")
        self.vm3_eu_mh_data = Output(256, "vm3_eu_mh_data")
        self.vm3_eu_mh_index = Output(18, "vm3_eu_mh_index")
        self.vm3_eu_mh_last = Output(1, "vm3_eu_mh_last")
        self.vm3_eu_mh_type = Output(4, "vm3_eu_mh_type")
        self.vm3_eu_mh_valid = Output(1, "vm3_eu_mh_valid")
        self.vm3_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm3_rbank0_write_addr")
        self.vm3_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm3_rbank0_write_data")
        self.vm3_rbank0_write_valid = Output(1, "vm3_rbank0_write_valid")
        self.vm3_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm3_rbank1_write_addr")
        self.vm3_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm3_rbank1_write_data")
        self.vm3_rbank1_write_valid = Output(1, "vm3_rbank1_write_valid")
        self.vm4_cc_update = Output(1, "vm4_cc_update")
        self.vm4_cc_update_value = Output(1, "vm4_cc_update_value")
        self.vm4_eu_mh_data = Output(256, "vm4_eu_mh_data")
        self.vm4_eu_mh_index = Output(18, "vm4_eu_mh_index")
        self.vm4_eu_mh_last = Output(1, "vm4_eu_mh_last")
        self.vm4_eu_mh_type = Output(4, "vm4_eu_mh_type")
        self.vm4_eu_mh_valid = Output(1, "vm4_eu_mh_valid")
        self.vm4_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm4_rbank0_write_addr")
        self.vm4_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm4_rbank0_write_data")
        self.vm4_rbank0_write_valid = Output(1, "vm4_rbank0_write_valid")
        self.vm4_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm4_rbank1_write_addr")
        self.vm4_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm4_rbank1_write_data")
        self.vm4_rbank1_write_valid = Output(1, "vm4_rbank1_write_valid")
        self.vm5_cc_update = Output(1, "vm5_cc_update")
        self.vm5_cc_update_value = Output(1, "vm5_cc_update_value")
        self.vm5_eu_mh_data = Output(256, "vm5_eu_mh_data")
        self.vm5_eu_mh_index = Output(18, "vm5_eu_mh_index")
        self.vm5_eu_mh_last = Output(1, "vm5_eu_mh_last")
        self.vm5_eu_mh_type = Output(4, "vm5_eu_mh_type")
        self.vm5_eu_mh_valid = Output(1, "vm5_eu_mh_valid")
        self.vm5_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm5_rbank0_write_addr")
        self.vm5_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm5_rbank0_write_data")
        self.vm5_rbank0_write_valid = Output(1, "vm5_rbank0_write_valid")
        self.vm5_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm5_rbank1_write_addr")
        self.vm5_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm5_rbank1_write_data")
        self.vm5_rbank1_write_valid = Output(1, "vm5_rbank1_write_valid")
        self.vm6_cc_update = Output(1, "vm6_cc_update")
        self.vm6_cc_update_value = Output(1, "vm6_cc_update_value")
        self.vm6_eu_mh_data = Output(256, "vm6_eu_mh_data")
        self.vm6_eu_mh_index = Output(18, "vm6_eu_mh_index")
        self.vm6_eu_mh_last = Output(1, "vm6_eu_mh_last")
        self.vm6_eu_mh_type = Output(4, "vm6_eu_mh_type")
        self.vm6_eu_mh_valid = Output(1, "vm6_eu_mh_valid")
        self.vm6_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm6_rbank0_write_addr")
        self.vm6_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm6_rbank0_write_data")
        self.vm6_rbank0_write_valid = Output(1, "vm6_rbank0_write_valid")
        self.vm6_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm6_rbank1_write_addr")
        self.vm6_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm6_rbank1_write_data")
        self.vm6_rbank1_write_valid = Output(1, "vm6_rbank1_write_valid")
        self.vm7_cc_update = Output(1, "vm7_cc_update")
        self.vm7_cc_update_value = Output(1, "vm7_cc_update_value")
        self.vm7_eu_mh_data = Output(256, "vm7_eu_mh_data")
        self.vm7_eu_mh_index = Output(18, "vm7_eu_mh_index")
        self.vm7_eu_mh_last = Output(1, "vm7_eu_mh_last")
        self.vm7_eu_mh_type = Output(4, "vm7_eu_mh_type")
        self.vm7_eu_mh_valid = Output(1, "vm7_eu_mh_valid")
        self.vm7_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm7_rbank0_write_addr")
        self.vm7_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm7_rbank0_write_data")
        self.vm7_rbank0_write_valid = Output(1, "vm7_rbank0_write_valid")
        self.vm7_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm7_rbank1_write_addr")
        self.vm7_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm7_rbank1_write_data")
        self.vm7_rbank1_write_valid = Output(1, "vm7_rbank1_write_valid")
        self.vm8_cc_update = Output(1, "vm8_cc_update")
        self.vm8_cc_update_value = Output(1, "vm8_cc_update_value")
        self.vm8_eu_mh_data = Output(256, "vm8_eu_mh_data")
        self.vm8_eu_mh_index = Output(18, "vm8_eu_mh_index")
        self.vm8_eu_mh_last = Output(1, "vm8_eu_mh_last")
        self.vm8_eu_mh_type = Output(4, "vm8_eu_mh_type")
        self.vm8_eu_mh_valid = Output(1, "vm8_eu_mh_valid")
        self.vm8_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm8_rbank0_write_addr")
        self.vm8_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm8_rbank0_write_data")
        self.vm8_rbank0_write_valid = Output(1, "vm8_rbank0_write_valid")
        self.vm8_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm8_rbank1_write_addr")
        self.vm8_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm8_rbank1_write_data")
        self.vm8_rbank1_write_valid = Output(1, "vm8_rbank1_write_valid")
        self.vm9_cc_update = Output(1, "vm9_cc_update")
        self.vm9_cc_update_value = Output(1, "vm9_cc_update_value")
        self.vm9_eu_mh_data = Output(256, "vm9_eu_mh_data")
        self.vm9_eu_mh_index = Output(18, "vm9_eu_mh_index")
        self.vm9_eu_mh_last = Output(1, "vm9_eu_mh_last")
        self.vm9_eu_mh_type = Output(4, "vm9_eu_mh_type")
        self.vm9_eu_mh_valid = Output(1, "vm9_eu_mh_valid")
        self.vm9_rbank0_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm9_rbank0_write_addr")
        self.vm9_rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm9_rbank0_write_data")
        self.vm9_rbank0_write_valid = Output(1, "vm9_rbank0_write_valid")
        self.vm9_rbank1_write_addr = Output(((self.GPR_ADDR_BITS - 2) - 0 + 1), "vm9_rbank1_write_addr")
        self.vm9_rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "vm9_rbank1_write_data")
        self.vm9_rbank1_write_valid = Output(1, "vm9_rbank1_write_valid")
        self.debug_mh_ready = Input(1, "debug_mh_ready")
        self.vm0_eu_mh_ready = Input(1, "vm0_eu_mh_ready")
        self.vm1_eu_mh_ready = Input(1, "vm1_eu_mh_ready")
        self.vm2_eu_mh_ready = Input(1, "vm2_eu_mh_ready")
        self.vm3_eu_mh_ready = Input(1, "vm3_eu_mh_ready")
        self.vm4_eu_mh_ready = Input(1, "vm4_eu_mh_ready")
        self.vm5_eu_mh_ready = Input(1, "vm5_eu_mh_ready")
        self.vm6_eu_mh_ready = Input(1, "vm6_eu_mh_ready")
        self.vm7_eu_mh_ready = Input(1, "vm7_eu_mh_ready")
        self.vm8_eu_mh_ready = Input(1, "vm8_eu_mh_ready")
        self.vm9_eu_mh_ready = Input(1, "vm9_eu_mh_ready")
        self.vm10_eu_mh_ready = Input(1, "vm10_eu_mh_ready")
        self.vm11_eu_mh_ready = Input(1, "vm11_eu_mh_ready")
        self.vm12_eu_mh_ready = Input(1, "vm12_eu_mh_ready")
        self.vm13_eu_mh_ready = Input(1, "vm13_eu_mh_ready")
        self.vm14_eu_mh_ready = Input(1, "vm14_eu_mh_ready")
        self.vm15_eu_mh_ready = Input(1, "vm15_eu_mh_ready")

        self.cc_update = Wire(((16 - 1) - 0 + 1), "cc_update")
        self.cc_update_value = Wire(((16 - 1) - 0 + 1), "cc_update_value")
        self.rbank0_write_addr = Wire((((16 * (self.GPR_ADDR_BITS - 1)) - 1) - 0 + 1), "rbank0_write_addr")
        self.rbank0_write_data = Wire((((16 * self.REG_WIDTH) - 1) - 0 + 1), "rbank0_write_data")
        self.rbank0_write_valid = Wire(((16 - 1) - 0 + 1), "rbank0_write_valid")
        self.rbank1_write_addr = Wire((((16 * (self.GPR_ADDR_BITS - 1)) - 1) - 0 + 1), "rbank1_write_addr")
        self.rbank1_write_data = Wire((((16 * self.REG_WIDTH) - 1) - 0 + 1), "rbank1_write_data")
        self.rbank1_write_valid = Wire(((16 - 1) - 0 + 1), "rbank1_write_valid")
        self.eu_mh_valid = Wire(((16 - 1) - 0 + 1), "eu_mh_valid")
        self.eu_mh_index = Wire((((16 * 18) - 1) - 0 + 1), "eu_mh_index")
        self.eu_mh_vm_id = Wire((((16 * 4) - 1) - 0 + 1), "eu_mh_vm_id")
        self.eu_mh_data = Wire((((16 * 256) - 1) - 0 + 1), "eu_mh_data")
        self.eu_mh_type = Wire((((16 * 4) - 1) - 0 + 1), "eu_mh_type")
        self.eu_mh_last = Wire(((16 - 1) - 0 + 1), "eu_mh_last")
        self.eu_mh_ready = Wire(((16 - 1) - 0 + 1), "eu_mh_ready")
        self.slice_debug_mh_valid = Wire(((self.EU_SLICE_NUM - 1) - 0 + 1), "slice_debug_mh_valid")
        self.slice_debug_mh_data = Wire((((self.EU_SLICE_NUM * 256) - 1) - 0 + 1), "slice_debug_mh_data")
        self.dbg_ff_push = Wire(1, "dbg_ff_push")
        self.dbg_ff_din = Wire(256, "dbg_ff_din")
        self.dbg_ff_pop = Wire(1, "dbg_ff_pop")
        self.dbg_ff_dout = Wire(256, "dbg_ff_dout")
        self.dbg_ff_empty = Wire(1, "dbg_ff_empty")
        self.dbg_ff_full = Wire(1, "dbg_ff_full")
        self.dbg_valid = Wire(1, "dbg_valid")
        self.slice_debug_mh_data_array = Array(256, (0 - (self.EU_SLICE_NUM - 1) + 1), "slice_debug_mh_data_array", vtype=Wire)
        self.dbg_data = Wire(256, "dbg_data")
        self.dbg_ff_valid = Wire(1, "dbg_ff_valid")
        self.dbg_ff_data = Wire(256, "dbg_ff_data")
        self.dbg_ff_ready = Wire(1, "dbg_ff_ready")

        # TODO: unpack assignment: Cat(self.vm15_cc_update, self.vm14_cc_update, self.vm13_cc_update, self.vm12_cc_update, self.vm11_cc_update, self.vm10_cc_update, self.vm9_cc_update, self.vm8_cc_update, self.vm7_cc_update, self.vm6_cc_update, self.vm5_cc_update, self.vm4_cc_update, self.vm3_cc_update, self.vm2_cc_update, self.vm1_cc_update, self.vm0_cc_update) = self.cc_update
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_cc_update_value, self.vm14_cc_update_value, self.vm13_cc_update_value, self.vm12_cc_update_value, self.vm11_cc_update_value, self.vm10_cc_update_value, self.vm9_cc_update_value, self.vm8_cc_update_value, self.vm7_cc_update_value, self.vm6_cc_update_value, self.vm5_cc_update_value, self.vm4_cc_update_value, self.vm3_cc_update_value, self.vm2_cc_update_value, self.vm1_cc_update_value, self.vm0_cc_update_value) = self.cc_update_value
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank0_write_valid, self.vm14_rbank0_write_valid, self.vm13_rbank0_write_valid, self.vm12_rbank0_write_valid, self.vm11_rbank0_write_valid, self.vm10_rbank0_write_valid, self.vm9_rbank0_write_valid, self.vm8_rbank0_write_valid, self.vm7_rbank0_write_valid, self.vm6_rbank0_write_valid, self.vm5_rbank0_write_valid, self.vm4_rbank0_write_valid, self.vm3_rbank0_write_valid, self.vm2_rbank0_write_valid, self.vm1_rbank0_write_valid, self.vm0_rbank0_write_valid) = self.rbank0_write_valid
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank0_write_addr, self.vm14_rbank0_write_addr, self.vm13_rbank0_write_addr, self.vm12_rbank0_write_addr, self.vm11_rbank0_write_addr, self.vm10_rbank0_write_addr, self.vm9_rbank0_write_addr, self.vm8_rbank0_write_addr, self.vm7_rbank0_write_addr, self.vm6_rbank0_write_addr, self.vm5_rbank0_write_addr, self.vm4_rbank0_write_addr, self.vm3_rbank0_write_addr, self.vm2_rbank0_write_addr, self.vm1_rbank0_write_addr, self.vm0_rbank0_write_addr) = self.rbank0_write_addr
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank0_write_data, self.vm14_rbank0_write_data, self.vm13_rbank0_write_data, self.vm12_rbank0_write_data, self.vm11_rbank0_write_data, self.vm10_rbank0_write_data, self.vm9_rbank0_write_data, self.vm8_rbank0_write_data, self.vm7_rbank0_write_data, self.vm6_rbank0_write_data, self.vm5_rbank0_write_data, self.vm4_rbank0_write_data, self.vm3_rbank0_write_data, self.vm2_rbank0_write_data, self.vm1_rbank0_write_data, self.vm0_rbank0_write_data) = self.rbank0_write_data
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank1_write_valid, self.vm14_rbank1_write_valid, self.vm13_rbank1_write_valid, self.vm12_rbank1_write_valid, self.vm11_rbank1_write_valid, self.vm10_rbank1_write_valid, self.vm9_rbank1_write_valid, self.vm8_rbank1_write_valid, self.vm7_rbank1_write_valid, self.vm6_rbank1_write_valid, self.vm5_rbank1_write_valid, self.vm4_rbank1_write_valid, self.vm3_rbank1_write_valid, self.vm2_rbank1_write_valid, self.vm1_rbank1_write_valid, self.vm0_rbank1_write_valid) = self.rbank1_write_valid
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank1_write_addr, self.vm14_rbank1_write_addr, self.vm13_rbank1_write_addr, self.vm12_rbank1_write_addr, self.vm11_rbank1_write_addr, self.vm10_rbank1_write_addr, self.vm9_rbank1_write_addr, self.vm8_rbank1_write_addr, self.vm7_rbank1_write_addr, self.vm6_rbank1_write_addr, self.vm5_rbank1_write_addr, self.vm4_rbank1_write_addr, self.vm3_rbank1_write_addr, self.vm2_rbank1_write_addr, self.vm1_rbank1_write_addr, self.vm0_rbank1_write_addr) = self.rbank1_write_addr
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_rbank1_write_data, self.vm14_rbank1_write_data, self.vm13_rbank1_write_data, self.vm12_rbank1_write_data, self.vm11_rbank1_write_data, self.vm10_rbank1_write_data, self.vm9_rbank1_write_data, self.vm8_rbank1_write_data, self.vm7_rbank1_write_data, self.vm6_rbank1_write_data, self.vm5_rbank1_write_data, self.vm4_rbank1_write_data, self.vm3_rbank1_write_data, self.vm2_rbank1_write_data, self.vm1_rbank1_write_data, self.vm0_rbank1_write_data) = self.rbank1_write_data
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_eu_mh_valid, self.vm14_eu_mh_valid, self.vm13_eu_mh_valid, self.vm12_eu_mh_valid, self.vm11_eu_mh_valid, self.vm10_eu_mh_valid, self.vm9_eu_mh_valid, self.vm8_eu_mh_valid, self.vm7_eu_mh_valid, self.vm6_eu_mh_valid, self.vm5_eu_mh_valid, self.vm4_eu_mh_valid, self.vm3_eu_mh_valid, self.vm2_eu_mh_valid, self.vm1_eu_mh_valid, self.vm0_eu_mh_valid) = self.eu_mh_valid
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_eu_mh_index, self.vm14_eu_mh_index, self.vm13_eu_mh_index, self.vm12_eu_mh_index, self.vm11_eu_mh_index, self.vm10_eu_mh_index, self.vm9_eu_mh_index, self.vm8_eu_mh_index, self.vm7_eu_mh_index, self.vm6_eu_mh_index, self.vm5_eu_mh_index, self.vm4_eu_mh_index, self.vm3_eu_mh_index, self.vm2_eu_mh_index, self.vm1_eu_mh_index, self.vm0_eu_mh_index) = self.eu_mh_index
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_eu_mh_type, self.vm14_eu_mh_type, self.vm13_eu_mh_type, self.vm12_eu_mh_type, self.vm11_eu_mh_type, self.vm10_eu_mh_type, self.vm9_eu_mh_type, self.vm8_eu_mh_type, self.vm7_eu_mh_type, self.vm6_eu_mh_type, self.vm5_eu_mh_type, self.vm4_eu_mh_type, self.vm3_eu_mh_type, self.vm2_eu_mh_type, self.vm1_eu_mh_type, self.vm0_eu_mh_type) = self.eu_mh_type
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_eu_mh_data, self.vm14_eu_mh_data, self.vm13_eu_mh_data, self.vm12_eu_mh_data, self.vm11_eu_mh_data, self.vm10_eu_mh_data, self.vm9_eu_mh_data, self.vm8_eu_mh_data, self.vm7_eu_mh_data, self.vm6_eu_mh_data, self.vm5_eu_mh_data, self.vm4_eu_mh_data, self.vm3_eu_mh_data, self.vm2_eu_mh_data, self.vm1_eu_mh_data, self.vm0_eu_mh_data) = self.eu_mh_data
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.vm15_eu_mh_last, self.vm14_eu_mh_last, self.vm13_eu_mh_last, self.vm12_eu_mh_last, self.vm11_eu_mh_last, self.vm10_eu_mh_last, self.vm9_eu_mh_last, self.vm8_eu_mh_last, self.vm7_eu_mh_last, self.vm6_eu_mh_last, self.vm5_eu_mh_last, self.vm4_eu_mh_last, self.vm3_eu_mh_last, self.vm2_eu_mh_last, self.vm1_eu_mh_last, self.vm0_eu_mh_last) = self.eu_mh_last
        # Consider using Split() or manual bit slicing
        self.eu_mh_ready <<= Cat(self.vm15_eu_mh_ready, self.vm14_eu_mh_ready, self.vm13_eu_mh_ready, self.vm12_eu_mh_ready, self.vm11_eu_mh_ready, self.vm10_eu_mh_ready, self.vm9_eu_mh_ready, self.vm8_eu_mh_ready, self.vm7_eu_mh_ready, self.vm6_eu_mh_ready, self.vm5_eu_mh_ready, self.vm4_eu_mh_ready, self.vm3_eu_mh_ready, self.vm2_eu_mh_ready, self.vm1_eu_mh_ready, self.vm0_eu_mh_ready)

        @self.comb
        def _comb_logic():
            self.slice_debug_mh_ready <<= Rep(Cat(1), self.EU_SLICE_NUM)
            self.slice_debug_mh_ready[self.aleo_cr_debug_id[3:2]] <<= (~self.dbg_ff_full)

        u_dbg_fifo = js_vm_sfifo(WIDTH=256, DEPTH=2)
        self.instantiate(
            u_dbg_fifo,
            "u_dbg_fifo",
            params={'WIDTH': 256, 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.dbg_ff_push,
                "din": self.dbg_ff_din,
                "pop": self.dbg_ff_pop,
                "dout": self.dbg_ff_dout,
                "empty": self.dbg_ff_empty,
                "full": self.dbg_ff_full,
            },
        )
        self.dbg_ff_push <<= (self.dbg_valid & (~self.dbg_ff_full))
        self.dbg_ff_din <<= self.dbg_data
        self.dbg_ff_pop <<= (self.dbg_ff_valid & self.dbg_ff_ready)

        u_dbg_mh_regslice = js_lib_regslice(D=256, N=1)
        self.instantiate(
            u_dbg_mh_regslice,
            "u_dbg_mh_regslice",
            params={'D': 256, 'N': 1},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "i_valid": self.dbg_ff_valid,
                "i_data": self.dbg_ff_data,
                "i_ready": self.dbg_ff_ready,
                "o_valid": self.debug_mh_valid,
                "o_data": self.debug_mh_data,
                "o_ready": self.debug_mh_ready,
            },
        )
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.EU_SLICE_NUM):
            # unhandled statement: # <InstanceList>
        # for-loop (non-generate) - parameter-driven
        for k in range(0, self.EU_SLICE_NUM):
            self.slice_debug_mh_data_array[k] <<= self.slice_debug_mh_data[(k * 256):((k * 256) + 256)]
