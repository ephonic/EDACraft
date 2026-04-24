"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_eu_warb(Module):
    def __init__(self, name: str = "js_vm_eu_warb"), MAC_GPR_IDLE: int = 0, MAC_GPR_DST0: int = 1, MAC_GPR_DST1: int = 2:
        super().__init__(name or "js_vm_eu_warb")

        self.add_localparam("MAC_GPR_IDLE", 0)
        self.add_localparam("MAC_GPR_DST0", 1)
        self.add_localparam("MAC_GPR_DST1", 2)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.aleo_cr_debug_id = Input(4, "aleo_cr_debug_id")
        self.aleo_cr_debug_mode = Input(2, "aleo_cr_debug_mode")
        self.pap_sq_valid = Input(1, "pap_sq_valid")
        self.pap_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "pap_sq_res")
        self.pap_sq_ready = Output(1, "pap_sq_ready")
        self.lgc_sq_valid = Input(1, "lgc_sq_valid")
        self.lgc_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "lgc_sq_res")
        self.lgc_sq_ready = Output(1, "lgc_sq_ready")
        self.map_sq_valid = Input(1, "map_sq_valid")
        self.map_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "map_sq_res")
        self.map_sq_ready = Output(1, "map_sq_ready")
        self.mac_sq_valid = Input(1, "mac_sq_valid")
        self.mac_sq_mask = Input(2, "mac_sq_mask")
        self.mac_sq_res = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "mac_sq_res")
        self.mac_sq_ready = Output(1, "mac_sq_ready")
        self.alu_sq_valid = Input(1, "alu_sq_valid")
        self.alu_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "alu_sq_res")
        self.alu_sq_ready = Output(1, "alu_sq_ready")
        self.mip_sq_valid = Input(1, "mip_sq_valid")
        self.mip_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "mip_sq_res")
        self.mip_sq_ready = Output(1, "mip_sq_ready")
        self.mov_sq_valid = Input(1, "mov_sq_valid")
        self.mov_sq_res = Input(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "mov_sq_res")
        self.mov_sq_ready = Output(1, "mov_sq_ready")
        self.cc_update = Output(1, "cc_update")
        self.cc_update_value = Output(1, "cc_update_value")
        self.rbank0_write_addr = Output((((self.GPR_ADDR_BITS - 1) - 1) - 0 + 1), "rbank0_write_addr")
        self.rbank0_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "rbank0_write_data")
        self.rbank0_write_valid = Output(1, "rbank0_write_valid")
        self.rbank1_write_addr = Output((((self.GPR_ADDR_BITS - 1) - 1) - 0 + 1), "rbank1_write_addr")
        self.rbank1_write_data = Output(((self.REG_WIDTH - 1) - 0 + 1), "rbank1_write_data")
        self.rbank1_write_valid = Output(1, "rbank1_write_valid")
        self.eu_mh_valid = Output(1, "eu_mh_valid")
        self.eu_mh_index = Output(((18 - 1) - 0 + 1), "eu_mh_index")
        self.eu_mh_vm_id = Output(((4 - 1) - 0 + 1), "eu_mh_vm_id")
        self.eu_mh_data = Output(((256 - 1) - 0 + 1), "eu_mh_data")
        self.eu_mh_type = Output(((4 - 1) - 0 + 1), "eu_mh_type")
        self.eu_mh_last = Output(1, "eu_mh_last")
        self.eu_mh_ready = Input(1, "eu_mh_ready")
        self.debug_mh_valid = Output(1, "debug_mh_valid")
        self.debug_mh_data = Output(256, "debug_mh_data")
        self.debug_mh_ready = Input(1, "debug_mh_ready")

        self.pap_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "pap_res_fmt")
        self.pap_res_type = Wire(2, "pap_res_type")
        self.pap_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "pap_res_opcode")
        self.pap_res_cc = Wire(1, "pap_res_cc")
        self.pap_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "pap_res_addr")
        self.pap_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "pap_res_data")
        self.lgc_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "lgc_res_fmt")
        self.lgc_res_type = Wire(2, "lgc_res_type")
        self.lgc_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "lgc_res_opcode")
        self.lgc_res_cc = Wire(1, "lgc_res_cc")
        self.lgc_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "lgc_res_addr")
        self.lgc_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "lgc_res_data")
        self.alu_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "alu_res_fmt")
        self.alu_res_type = Wire(2, "alu_res_type")
        self.alu_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "alu_res_opcode")
        self.alu_res_cc = Wire(1, "alu_res_cc")
        self.alu_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "alu_res_addr")
        self.alu_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "alu_res_data")
        self.map_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "map_res_fmt")
        self.map_res_type = Wire(2, "map_res_type")
        self.map_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "map_res_opcode")
        self.map_res_cc = Wire(1, "map_res_cc")
        self.map_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "map_res_addr")
        self.map_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "map_res_data")
        self.mip_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "mip_res_fmt")
        self.mip_res_type = Wire(2, "mip_res_type")
        self.mip_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "mip_res_opcode")
        self.mip_res_cc = Wire(1, "mip_res_cc")
        self.mip_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "mip_res_addr")
        self.mip_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "mip_res_data")
        self.mac_res_type = Wire(2, "mac_res_type")
        self.mac_res_cc = Wire(1, "mac_res_cc")
        self.mac_res0_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "mac_res0_addr")
        self.mac_res0_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "mac_res0_data")
        self.mac_res1_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "mac_res1_addr")
        self.mac_res1_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "mac_res1_data")
        self.mov_res_fmt = Wire(((self.ISA_DST_FMT_BITS - 1) - 0 + 1), "mov_res_fmt")
        self.mov_res_type = Wire(2, "mov_res_type")
        self.mov_res_opcode = Wire(((self.ISA_OPCODE_BITS - 1) - 0 + 1), "mov_res_opcode")
        self.mov_res_cc = Wire(1, "mov_res_cc")
        self.mov_res_addr = Wire(((self.GPR_ADDR_BITS - 1) - 0 + 1), "mov_res_addr")
        self.mov_res_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "mov_res_data")
        self.mov_res_merkel_bit = Wire(1, "mov_res_merkel_bit")
        self.mov_res_merkel_num = Wire(8, "mov_res_merkel_num")
        self.mac_gpr_st = Reg(2, "mac_gpr_st")
        self.mac_gpr_st_nxt = Reg(2, "mac_gpr_st_nxt")
        self.mac_gpr_ready = Reg(1, "mac_gpr_ready")
        self.mac_gpr_valid0 = Reg(1, "mac_gpr_valid0")
        self.mac_gpr_valid1 = Reg(1, "mac_gpr_valid1")
        self.mac_gpr_ready0 = Wire(1, "mac_gpr_ready0")
        self.mac_gpr_ready1 = Wire(1, "mac_gpr_ready1")
        self.pipe0_gpr_bank0_valid = Wire(1, "pipe0_gpr_bank0_valid")
        self.pipe1_gpr_bank0_valid = Wire(1, "pipe1_gpr_bank0_valid")
        self.pipe2_gpr_bank0_valid = Wire(1, "pipe2_gpr_bank0_valid")
        self.pipe3_gpr_bank0_valid = Wire(1, "pipe3_gpr_bank0_valid")
        self.pipe4_gpr_bank0_valid = Wire(1, "pipe4_gpr_bank0_valid")
        self.pipe5_gpr_bank0_valid = Wire(1, "pipe5_gpr_bank0_valid")
        self.pipe6_gpr_bank0_valid = Wire(1, "pipe6_gpr_bank0_valid")
        self.pipe7_gpr_bank0_valid = Wire(1, "pipe7_gpr_bank0_valid")
        self.pipe0_gpr_bank1_valid = Wire(1, "pipe0_gpr_bank1_valid")
        self.pipe1_gpr_bank1_valid = Wire(1, "pipe1_gpr_bank1_valid")
        self.pipe2_gpr_bank1_valid = Wire(1, "pipe2_gpr_bank1_valid")
        self.pipe3_gpr_bank1_valid = Wire(1, "pipe3_gpr_bank1_valid")
        self.pipe4_gpr_bank1_valid = Wire(1, "pipe4_gpr_bank1_valid")
        self.pipe5_gpr_bank1_valid = Wire(1, "pipe5_gpr_bank1_valid")
        self.pipe6_gpr_bank1_valid = Wire(1, "pipe6_gpr_bank1_valid")
        self.pipe7_gpr_bank1_valid = Wire(1, "pipe7_gpr_bank1_valid")
        self.pipe0_gpr_bank0_ready = Wire(1, "pipe0_gpr_bank0_ready")
        self.pipe0_gpr_bank1_ready = Wire(1, "pipe0_gpr_bank1_ready")
        self.pipe1_gpr_bank0_ready = Wire(1, "pipe1_gpr_bank0_ready")
        self.pipe1_gpr_bank1_ready = Wire(1, "pipe1_gpr_bank1_ready")
        self.pipe2_gpr_bank0_ready = Wire(1, "pipe2_gpr_bank0_ready")
        self.pipe2_gpr_bank1_ready = Wire(1, "pipe2_gpr_bank1_ready")
        self.pipe3_gpr_bank0_ready = Wire(1, "pipe3_gpr_bank0_ready")
        self.pipe3_gpr_bank1_ready = Wire(1, "pipe3_gpr_bank1_ready")
        self.pipe4_gpr_bank0_ready = Wire(1, "pipe4_gpr_bank0_ready")
        self.pipe4_gpr_bank1_ready = Wire(1, "pipe4_gpr_bank1_ready")
        self.pipe5_gpr_bank0_ready = Wire(1, "pipe5_gpr_bank0_ready")
        self.pipe5_gpr_bank1_ready = Wire(1, "pipe5_gpr_bank1_ready")
        self.pipe6_gpr_bank0_ready = Wire(1, "pipe6_gpr_bank0_ready")
        self.pipe6_gpr_bank1_ready = Wire(1, "pipe6_gpr_bank1_ready")
        self.pipe7_gpr_bank0_ready = Wire(1, "pipe7_gpr_bank0_ready")
        self.pipe7_gpr_bank1_ready = Wire(1, "pipe7_gpr_bank1_ready")
        self.pap_gpr_ready = Wire(1, "pap_gpr_ready")
        self.map_gpr_ready = Wire(1, "map_gpr_ready")
        self.mip_gpr_ready = Wire(1, "mip_gpr_ready")
        self.alu_gpr_ready = Wire(1, "alu_gpr_ready")
        self.lgc_gpr_ready = Wire(1, "lgc_gpr_ready")
        self.mov_gpr_ready = Wire(1, "mov_gpr_ready")
        self.gpr_bank0_valids = Wire(8, "gpr_bank0_valids")
        self.gpr_bank1_valids = Wire(8, "gpr_bank1_valids")
        self.cc_updates = Wire(8, "cc_updates")
        self.merkel_valids = Wire(8, "merkel_valids")
        self.slice_rbank0_valids = Wire(8, "slice_rbank0_valids")
        self.slice_rbank1_valids = Wire(8, "slice_rbank1_valids")
        self.slice_rbank0_readys = Wire(8, "slice_rbank0_readys")
        self.slice_rbank1_readys = Wire(8, "slice_rbank1_readys")
        self.slice_rbank0_rrb_valid = Wire(1, "slice_rbank0_rrb_valid")
        self.slice_rbank1_rrb_valid = Wire(1, "slice_rbank1_rrb_valid")
        self.slice_rbank0_sel = Wire(3, "slice_rbank0_sel")
        self.slice_rbank1_sel = Wire(3, "slice_rbank1_sel")
        self.slice_rbank0_rrb_addr = Wire((((self.GPR_ADDR_BITS - 1) - 1) - 0 + 1), "slice_rbank0_rrb_addr")
        self.slice_rbank1_rrb_addr = Wire((((self.GPR_ADDR_BITS - 1) - 1) - 0 + 1), "slice_rbank1_rrb_addr")
        self.slice_rbank0_rrb_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "slice_rbank0_rrb_data")
        self.slice_rbank1_rrb_data = Wire(((self.REG_WIDTH - 1) - 0 + 1), "slice_rbank1_rrb_data")
        self.pap_cc_ready = Wire(1, "pap_cc_ready")
        self.map_cc_ready = Wire(1, "map_cc_ready")
        self.mip_cc_ready = Wire(1, "mip_cc_ready")
        self.alu_cc_ready = Wire(1, "alu_cc_ready")
        self.lgc_cc_ready = Wire(1, "lgc_cc_ready")
        self.mov_cc_ready = Wire(1, "mov_cc_ready")
        self.mac_cc_ready = Wire(1, "mac_cc_ready")
        self.slice_cc_valid = Wire(1, "slice_cc_valid")
        self.slice_cc_value = Wire(1, "slice_cc_value")
        self.mh_obuf_dout = Wire((((((1 + 1) + 8) + 256) - 1) - 0 + 1), "mh_obuf_dout")
        self.mh_obuf_push = Wire(1, "mh_obuf_push")
        self.mh_obuf_pop = Wire(1, "mh_obuf_pop")
        self.mh_obuf_full = Wire(1, "mh_obuf_full")
        self.mh_obuf_empty = Wire(1, "mh_obuf_empty")
        self.mh_obuf_eop = Wire(1, "mh_obuf_eop")
        self.mh_obuf_bit = Wire(1, "mh_obuf_bit")
        self.mh_obuf_num = Wire(8, "mh_obuf_num")
        self.mh_obuf_data = Wire(256, "mh_obuf_data")
        self.mh_obuf_res = Wire(((((1 + 8) + 256) - 1) - 0 + 1), "mh_obuf_res")
        self.mov_merkel_valid = Wire(1, "mov_merkel_valid")
        self.mov_merkel_ready = Wire(1, "mov_merkel_ready")
        self.mov_merkel_eop = Wire(1, "mov_merkel_eop")
        self.mh_obuf_valid = Wire(1, "mh_obuf_valid")
        self.mh_obuf_ready = Wire(1, "mh_obuf_ready")
        self.mov_mh_valid = Wire(1, "mov_mh_valid")
        self.mov_mh_ready = Wire(1, "mov_mh_ready")
        self.mov_mh_data = Wire(256, "mov_mh_data")
        self.mov_mh_type = Wire(4, "mov_mh_type")
        self.mov_mh_index = Wire(18, "mov_mh_index")
        self.mov_mh_last = Wire(1, "mov_mh_last")
        self.dbg_o_valid = Wire(1, "dbg_o_valid")
        self.dbg_o_ready = Wire(1, "dbg_o_ready")
        self.mkl_o_valid = Wire(1, "mkl_o_valid")
        self.mkl_o_ready = Wire(1, "mkl_o_ready")
        self.dbg_ff_push = Wire(1, "dbg_ff_push")
        self.dbg_ff_din = Wire(256, "dbg_ff_din")
        self.dbg_ff_dout = Wire(256, "dbg_ff_dout")
        self.dbg_ff_pop = Wire(1, "dbg_ff_pop")
        self.dbg_ff_full = Wire(1, "dbg_ff_full")
        self.dbg_ff_empty = Wire(1, "dbg_ff_empty")
        self.dbg_type = Wire(3, "dbg_type")
        self.dbg_data = Wire(256, "dbg_data")
        self.dbg_index = Wire(18, "dbg_index")

        # TODO: unpack assignment: Cat(self.pap_res_fmt, self.pap_res_type, self.pap_res_opcode, self.pap_res_cc, self.pap_res_addr, self.pap_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.lgc_res_fmt, self.lgc_res_type, self.lgc_res_opcode, self.lgc_res_cc, self.lgc_res_addr, self.lgc_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.alu_res_fmt, self.alu_res_type, self.alu_res_opcode, self.alu_res_cc, self.alu_res_addr, self.alu_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.map_res_fmt, self.map_res_type, self.map_res_opcode, self.map_res_cc, self.map_res_addr, self.map_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.mip_res_fmt, self.mip_res_type, self.mip_res_opcode, self.mip_res_cc, self.mip_res_addr, self.mip_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.mac_res_type, self.mac_res_cc, self.mac_res1_addr, self.mac_res1_data, self.mac_res0_addr, self.mac_res0_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.mov_res_fmt, self.mov_res_type, self.mov_res_opcode, self.mov_res_cc, self.mov_res_addr, self.mov_res_data) = # <FunctionCall>
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.mov_res_merkel_bit, self.mov_res_merkel_num) = # <FunctionCall>
        # Consider using Split() or manual bit slicing

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mac_gpr_st <<= self.MAC_GPR_IDLE
            with Else():
                self.mac_gpr_st <<= self.mac_gpr_st_nxt

        @self.comb
        def _comb_logic():
            self.mac_gpr_st_nxt <<= self.mac_gpr_st
            self.mac_gpr_ready <<= 0
            self.mac_gpr_valid0 <<= 0
            self.mac_gpr_valid1 <<= 0
            with Switch(self.mac_gpr_st) as sw:
                with sw.case(self.MAC_GPR_IDLE):
                    with If((self.mac_sq_valid & (self.mac_res_type == 0))):
                        self.mac_gpr_valid0 <<= self.mac_sq_mask[0]
                        self.mac_gpr_valid1 <<= self.mac_sq_mask[1]
                        with If((self.mac_sq_mask == 0)):
                            self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
                        with Else():
                            with If(((self.mac_sq_mask == 1) & self.mac_gpr_ready0)):
                                self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
                                self.mac_gpr_ready <<= 1
                            with Else():
                                with If(((self.mac_sq_mask == 2) & self.mac_gpr_ready1)):
                                    self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
                                    self.mac_gpr_ready <<= 1
                                with Else():
                                    with If((self.mac_sq_mask == 3)):
                                        with If((self.mac_gpr_ready0 & self.mac_gpr_ready1)):
                                            self.mac_gpr_ready <<= 1
                                        with Else():
                                            with If(self.mac_gpr_ready0):
                                                self.mac_gpr_st_nxt <<= self.MAC_GPR_DST1
                                            with Else():
                                                with If(self.mac_gpr_ready1):
                                                    self.mac_gpr_st_nxt <<= self.MAC_GPR_DST0
                with sw.case(self.MAC_GPR_DST0):
                    self.mac_gpr_valid0 <<= 1
                    with If(self.mac_gpr_ready0):
                        self.mac_gpr_ready <<= 1
                        self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
                with sw.case(self.MAC_GPR_DST1):
                    self.mac_gpr_valid1 <<= 1
                    with If(self.mac_gpr_ready1):
                        self.mac_gpr_ready <<= 1
                        self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
                with sw.default():
                    self.mac_gpr_st_nxt <<= self.MAC_GPR_IDLE
        self.pipe0_gpr_bank0_valid <<= (((self.pap_sq_valid & (self.pap_res_type == 0)) & (self.pap_res_fmt == 12)) & (~self.pap_res_addr[0]))
        self.pipe1_gpr_bank0_valid <<= (((self.map_sq_valid & (self.map_res_type == 0)) & Mux((self.map_res_opcode == self.OPCODE_MADD), ((self.map_res_fmt == 12) | (self.map_res_fmt == 13)), 1)) & (~self.map_res_addr[0]))
        self.pipe2_gpr_bank0_valid <<= ((self.mip_sq_valid & (self.mip_res_type == 0)) & (~self.mip_res_addr[0]))
        self.pipe3_gpr_bank0_valid <<= ((self.alu_sq_valid & (self.alu_res_type == 0)) & (~self.alu_res_addr[0]))
        self.pipe4_gpr_bank0_valid <<= ((self.lgc_sq_valid & (self.lgc_res_type == 0)) & (~self.lgc_res_addr[0]))
        self.pipe5_gpr_bank0_valid <<= ((self.mov_sq_valid & (self.mov_res_type == 0)) & (~self.mov_res_addr[0]))
        self.pipe6_gpr_bank0_valid <<= (self.mac_gpr_valid0 & (~self.mac_res0_addr[0]))
        self.pipe7_gpr_bank0_valid <<= (self.mac_gpr_valid1 & (~self.mac_res1_addr[0]))
        self.pipe0_gpr_bank1_valid <<= (((self.pap_sq_valid & (self.pap_res_type == 0)) & (self.pap_res_fmt == 12)) & self.pap_res_addr[0])
        self.pipe1_gpr_bank1_valid <<= (((self.map_sq_valid & (self.map_res_type == 0)) & Mux((self.map_res_opcode == self.OPCODE_MADD), ((self.map_res_fmt == 12) | (self.map_res_fmt == 13)), 1)) & self.map_res_addr[0])
        self.pipe2_gpr_bank1_valid <<= ((self.mip_sq_valid & (self.mip_res_type == 0)) & self.mip_res_addr[0])
        self.pipe3_gpr_bank1_valid <<= ((self.alu_sq_valid & (self.alu_res_type == 0)) & self.alu_res_addr[0])
        self.pipe4_gpr_bank1_valid <<= ((self.lgc_sq_valid & (self.lgc_res_type == 0)) & self.lgc_res_addr[0])
        self.pipe5_gpr_bank1_valid <<= ((self.mov_sq_valid & (self.mov_res_type == 0)) & self.mov_res_addr[0])
        self.pipe6_gpr_bank1_valid <<= (self.mac_gpr_valid0 & self.mac_res0_addr[0])
        self.pipe7_gpr_bank1_valid <<= (self.mac_gpr_valid1 & self.mac_res1_addr[0])
        self.mac_gpr_ready0 <<= Mux(self.mac_res0_addr[0], (|self.pipe6_gpr_bank1_ready), (|self.pipe6_gpr_bank0_ready))
        self.mac_gpr_ready1 <<= Mux(self.mac_res1_addr[0], (|self.pipe7_gpr_bank1_ready), (|self.pipe7_gpr_bank0_ready))
        self.pipe0_gpr_bank0_ready <<= self.slice_rbank0_readys[0]
        self.pipe0_gpr_bank1_ready <<= self.slice_rbank1_readys[0]
        self.pipe1_gpr_bank0_ready <<= self.slice_rbank0_readys[1]
        self.pipe1_gpr_bank1_ready <<= self.slice_rbank1_readys[1]
        self.pipe2_gpr_bank0_ready <<= self.slice_rbank0_readys[2]
        self.pipe2_gpr_bank1_ready <<= self.slice_rbank1_readys[2]
        self.pipe3_gpr_bank0_ready <<= self.slice_rbank0_readys[3]
        self.pipe3_gpr_bank1_ready <<= self.slice_rbank1_readys[3]
        self.pipe4_gpr_bank0_ready <<= self.slice_rbank0_readys[4]
        self.pipe4_gpr_bank1_ready <<= self.slice_rbank1_readys[4]
        self.pipe5_gpr_bank0_ready <<= self.slice_rbank0_readys[5]
        self.pipe5_gpr_bank1_ready <<= self.slice_rbank1_readys[5]
        self.pipe6_gpr_bank0_ready <<= self.slice_rbank0_readys[6]
        self.pipe6_gpr_bank1_ready <<= self.slice_rbank1_readys[6]
        self.pipe7_gpr_bank0_ready <<= self.slice_rbank0_readys[7]
        self.pipe7_gpr_bank1_ready <<= self.slice_rbank1_readys[7]
        self.slice_rbank0_valids <<= Cat(self.pipe7_gpr_bank0_valid, self.pipe6_gpr_bank0_valid, self.pipe5_gpr_bank0_valid, self.pipe4_gpr_bank0_valid, self.pipe3_gpr_bank0_valid, self.pipe2_gpr_bank0_valid, self.pipe1_gpr_bank0_valid, self.pipe0_gpr_bank0_valid)
        self.slice_rbank1_valids <<= Cat(self.pipe7_gpr_bank1_valid, self.pipe6_gpr_bank1_valid, self.pipe5_gpr_bank1_valid, self.pipe4_gpr_bank1_valid, self.pipe3_gpr_bank1_valid, self.pipe2_gpr_bank1_valid, self.pipe1_gpr_bank1_valid, self.pipe0_gpr_bank1_valid)

        u_slice_rbank0_rrb = js_vm_rr_arb(NUM=8, ID_BITS=3)
        self.instantiate(
            u_slice_rbank0_rrb,
            "u_slice_rbank0_rrb",
            params={'NUM': 8, 'ID_BITS': 3},
            port_map={
                "in_readys": self.slice_rbank0_readys[7:0],
                "out_valid": self.slice_rbank0_rrb_valid,
                "grant_id": self.slice_rbank0_sel[2:0],
                "clk": self.clk,
                "rstn": self.rstn,
                "in_valids": self.slice_rbank0_valids[7:0],
                "out_ready": 1,
            },
        )

        u_slice_rbank1_rrb = js_vm_rr_arb(NUM=8, ID_BITS=3)
        self.instantiate(
            u_slice_rbank1_rrb,
            "u_slice_rbank1_rrb",
            params={'NUM': 8, 'ID_BITS': 3},
            port_map={
                "in_readys": self.slice_rbank1_readys[7:0],
                "out_valid": self.slice_rbank1_rrb_valid,
                "grant_id": self.slice_rbank1_sel[2:0],
                "clk": self.clk,
                "rstn": self.rstn,
                "in_valids": self.slice_rbank1_valids[7:0],
                "out_ready": 1,
            },
        )
        self.slice_rbank0_rrb_addr[((self.GPR_ADDR_BITS - 1) - 1):0] <<= Mux((self.slice_rbank0_sel == 0), self.pap_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 1), self.map_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 2), self.mip_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 3), self.alu_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 4), self.lgc_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 5), self.mov_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 6), self.mac_res0_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank0_sel == 7), self.mac_res1_addr[(self.GPR_ADDR_BITS - 1):1], 0))))))))
        self.slice_rbank1_rrb_addr[((self.GPR_ADDR_BITS - 1) - 1):0] <<= Mux((self.slice_rbank1_sel == 0), self.pap_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 1), self.map_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 2), self.mip_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 3), self.alu_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 4), self.lgc_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 5), self.mov_res_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 6), self.mac_res0_addr[(self.GPR_ADDR_BITS - 1):1], Mux((self.slice_rbank1_sel == 7), self.mac_res1_addr[(self.GPR_ADDR_BITS - 1):1], 0))))))))
        self.slice_rbank0_rrb_data[(self.REG_WIDTH - 1):0] <<= Mux((self.slice_rbank0_sel == 0), self.pap_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 1), self.map_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 2), self.mip_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 3), self.alu_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 4), self.lgc_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 5), self.mov_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 6), self.mac_res0_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank0_sel == 7), self.mac_res1_data[(self.REG_WIDTH - 1):0], 0))))))))
        self.slice_rbank1_rrb_data[(self.REG_WIDTH - 1):0] <<= Mux((self.slice_rbank1_sel == 0), self.pap_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 1), self.map_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 2), self.mip_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 3), self.alu_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 4), self.lgc_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 5), self.mov_res_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 6), self.mac_res0_data[(self.REG_WIDTH - 1):0], Mux((self.slice_rbank1_sel == 7), self.mac_res1_data[(self.REG_WIDTH - 1):0], 0))))))))

        @self.comb
        def _comb_logic():
            self.rbank1_write_valid <<= self.slice_rbank1_rrb_valid
            self.rbank0_write_valid <<= self.slice_rbank0_rrb_valid
            self.rbank0_write_data <<= self.slice_rbank0_rrb_data
            self.rbank0_write_addr <<= self.slice_rbank0_rrb_addr
            self.rbank1_write_data <<= self.slice_rbank1_rrb_data
            self.rbank1_write_addr <<= self.slice_rbank1_rrb_addr
        self.slice_cc_valid <<= (((((((self.pap_sq_valid & (self.pap_res_type == 1)) | (self.map_sq_valid & (self.map_res_type == 1))) | (self.mip_sq_valid & (self.mip_res_type == 1))) | (self.lgc_sq_valid & (self.lgc_res_type == 1))) | (self.alu_sq_valid & (self.alu_res_type == 1))) | (self.mac_sq_valid & (self.mac_res_type == 1))) | (self.mov_sq_valid & (self.mov_res_type == 1)))
        self.slice_cc_value <<= ((((((((self.pap_sq_valid & (self.pap_res_type == 1)) & self.pap_res_cc) | ((self.map_sq_valid & (self.map_res_type == 1)) & self.map_res_cc)) | ((self.mip_sq_valid & (self.mip_res_type == 1)) & self.mip_res_cc)) | ((self.lgc_sq_valid & (self.lgc_res_type == 1)) & self.lgc_res_cc)) | ((self.alu_sq_valid & (self.alu_res_type == 1)) & self.alu_res_cc)) | ((self.mac_sq_valid & (self.mac_res_type == 1)) & self.mac_res_cc)) | ((self.mov_sq_valid & (self.mov_res_type == 1)) & self.mov_res_cc))

        @self.comb
        def _comb_logic():
            self.cc_update <<= self.slice_cc_valid
            self.cc_update_value <<= self.slice_cc_value
        self.mh_obuf_push <<= (self.mov_merkel_valid & self.mov_merkel_ready)

        u_mh_buf = js_vm_sfifo(WIDTH=(((1 + 1) + 8) + 256), DEPTH=2)
        self.instantiate(
            u_mh_buf,
            "u_mh_buf",
            params={'WIDTH': (((1 + 1) + 8) + 256), 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.mh_obuf_push,
                "din": Cat(self.mov_merkel_eop, self.mov_res_merkel_bit, self.mov_res_merkel_num, self.mov_res_data[255:0]),
                "pop": self.mh_obuf_pop,
                "dout": self.mh_obuf_dout,
                "full": self.mh_obuf_full,
                "empty": self.mh_obuf_empty,
            },
        )
        # TODO: unpack assignment: Cat(self.mh_obuf_eop, self.mh_obuf_bit, self.mh_obuf_num, self.mh_obuf_data) = self.mh_obuf_dout
        # Consider using Split() or manual bit slicing
        self.mh_obuf_valid <<= (~self.mh_obuf_empty)
        self.mh_obuf_pop <<= (self.mh_obuf_valid & self.mh_obuf_ready)
        self.mh_obuf_res <<= Cat(self.mh_obuf_bit, self.mh_obuf_num, self.mh_obuf_data)

        u_mh_loop = js_vm_eu_mh_loop()
        self.instantiate(
            u_mh_loop,
            "u_mh_loop",
            port_map={
                "mov_merkel_ready": self.mh_obuf_ready,
                "mov_mh_valid": self.mov_mh_valid,
                "mov_mh_data": self.mov_mh_data[255:0],
                "mov_mh_type": self.mov_mh_type[3:0],
                "mov_mh_index": self.mov_mh_index[17:0],
                "mov_mh_last": self.mov_mh_last,
                "clk": self.clk,
                "rstn": self.rstn,
                "mov_merkel_valid": self.mh_obuf_valid,
                "mov_merkel_eop": self.mh_obuf_eop,
                "mov_merkel_res": self.mh_obuf_res[(((1 + 8) + 256) - 1):0],
                "mov_mh_ready": self.mov_mh_ready,
            },
        )
        self.mov_mh_ready <<= (self.mkl_o_ready & self.dbg_o_ready)
        self.mkl_o_valid <<= (self.mov_mh_valid & self.dbg_o_ready)
        self.dbg_o_valid <<= (self.mov_mh_valid & self.mkl_o_ready)
        self.mkl_o_ready <<= ((~self.eu_mh_valid) | self.eu_mh_ready)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.eu_mh_valid <<= 0
            with Else():
                with If(self.mkl_o_ready):
                    self.eu_mh_valid <<= self.mkl_o_valid

        @self.seq(self.clk, None)
        def _seq_logic():
            with If((self.mov_mh_valid & self.mov_mh_ready)):
                self.eu_mh_data <<= self.mov_mh_data
                self.eu_mh_index <<= self.mov_mh_index
                self.eu_mh_type <<= self.mov_mh_type
                self.eu_mh_last <<= self.mov_mh_last
        self.dbg_ff_push <<= (self.dbg_o_valid & self.dbg_o_ready)
        self.dbg_ff_din <<= Cat(self.dbg_type[2:0], self.dbg_data[252:0])
        self.dbg_ff_pop <<= (self.debug_mh_valid & self.debug_mh_ready)
        self.dbg_o_ready <<= (~self.dbg_ff_full)

        u_dbg_ff = js_vm_sfifo(WIDTH=256, DEPTH=2)
        self.instantiate(
            u_dbg_ff,
            "u_dbg_ff",
            params={'WIDTH': 256, 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.dbg_ff_push,
                "din": self.dbg_ff_din[255:0],
                "pop": self.dbg_ff_pop,
                "dout": self.debug_mh_data,
                "full": self.dbg_ff_full,
                "empty": self.dbg_ff_empty,
            },
        )
        self.debug_mh_valid <<= (~self.dbg_ff_empty)
        self.pap_sq_ready <<= Mux((self.pap_res_type == 0), self.pap_gpr_ready, Mux((self.pap_res_type == 1), self.pap_cc_ready, 1))
        self.map_sq_ready <<= Mux((self.map_res_type == 0), self.map_gpr_ready, Mux((self.map_res_type == 1), self.map_cc_ready, 1))
        self.mip_sq_ready <<= Mux((self.mip_res_type == 0), self.mip_gpr_ready, Mux((self.mip_res_type == 1), self.mip_cc_ready, 1))
        self.alu_sq_ready <<= Mux((self.alu_res_type == 0), self.alu_gpr_ready, Mux((self.alu_res_type == 1), self.alu_cc_ready, 1))
        self.lgc_sq_ready <<= Mux((self.lgc_res_type == 0), self.lgc_gpr_ready, Mux((self.lgc_res_type == 1), self.lgc_cc_ready, 1))
        self.mac_sq_ready <<= Mux((self.mac_res_type == 0), self.mac_gpr_ready, Mux((self.mac_res_type == 1), self.mac_cc_ready, 1))
        self.mov_sq_ready <<= Mux((self.mov_res_type == 0), self.mov_gpr_ready, Mux((self.mov_res_type == 1), self.mov_cc_ready, self.mov_merkel_ready))
        # unhandled statement: # function extract_merkel
        # unhandled statement: # function extract_one_dst
        # unhandled statement: # function extract_two_dst
