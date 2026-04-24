"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_pap_top(Module):
    def __init__(self, name: str = "js_vm_pap_top"), MODMUL_DELAY: int = 18:
        super().__init__(name or "js_vm_pap_top")

        self.add_localparam("MODMUL_DELAY", 18)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.pap_active = Output(1, "pap_active")
        self.sq_pap_valid = Input(1, "sq_pap_valid")
        self.sq_pap_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_pap_data")
        self.sq_pap_q = Input(256, "sq_pap_q")
        self.sq_pap_mu = Input(256, "sq_pap_mu")
        self.sq_pap_vm_id = Input(4, "sq_pap_vm_id")
        self.sq_pap_ready = Output(1, "sq_pap_ready")
        self.pap_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "pap_sq_fc_dec")
        self.pap_sq_fc_dec_vm_id = Output(4, "pap_sq_fc_dec_vm_id")
        self.pap_sq_valid = Output(1, "pap_sq_valid")
        self.pap_sq_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "pap_sq_res")
        self.pap_sq_vm_id = Output(4, "pap_sq_vm_id")
        self.pap_sq_ready = Input(1, "pap_sq_ready")
        self.pap_sq_hq_rel_valid = Output(1, "pap_sq_hq_rel_valid")
        self.pap_sq_hq_rel_vm_id = Output(4, "pap_sq_hq_rel_vm_id")

        self.sync_push = Wire(1, "sync_push")
        self.sync_din = Wire(1, "sync_din")
        self.sync_pop0 = Wire(1, "sync_pop0")
        self.sync_pop1 = Wire(1, "sync_pop1")
        self.sync_dout0 = Wire(1, "sync_dout0")
        self.sync_dout1 = Wire(1, "sync_dout1")
        self.sync_empty0 = Wire(1, "sync_empty0")
        self.sync_empty1 = Wire(1, "sync_empty1")
        self.sync_full = Wire(1, "sync_full")
        self.obuf_push = Wire(1, "obuf_push")
        self.obuf_din = Wire((((((4 + self.ISA_BITS) + self.REG_WIDTH) + 1) - 1) - 0 + 1), "obuf_din")
        self.obuf_pop = Wire(1, "obuf_pop")
        self.obuf_dout = Wire((((((4 + self.ISA_BITS) + self.REG_WIDTH) + 1) - 1) - 0 + 1), "obuf_dout")
        self.obuf_full = Wire(1, "obuf_full")
        self.obuf_empty = Wire(1, "obuf_empty")
        self.lff_push = Wire(1, "lff_push")
        self.lff_pop = Wire(1, "lff_pop")
        self.lff_dout = Wire((((((4 + self.ISA_BITS) + self.REG_WIDTH) + 1) - 1) - 0 + 1), "lff_dout")
        self.lff_empty = Wire(1, "lff_empty")
        self.lff_full = Wire(1, "lff_full")
        self.merge_o_valid = Wire(1, "merge_o_valid")
        self.merge_o_res = Wire(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "merge_o_res")
        self.merge_o_vm_id = Wire(4, "merge_o_vm_id")
        self.merge_o_ready = Wire(1, "merge_o_ready")
        self.pap_res_valid = Wire(1, "pap_res_valid")
        self.pap_sq_sf = Wire(((self.FC_NUM - 1) - 0 + 1), "pap_sq_sf")
        self.pap_fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "pap_fc_dec")
        self.pap_res_vm_id = Wire(4, "pap_res_vm_id")
        self.modacc_i_valid = Wire(1, "modacc_i_valid")
        self.modacc_i_ready = Wire(1, "modacc_i_ready")

        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype, self.cc_value, self.src1_value, self.src0_value) = self.sq_pap_data
        # Consider using Split() or manual bit slicing

        u_sync_fifo = js_vm_sfifo_1w2r(WIDTH=1, DEPTH=32)
        self.instantiate(
            u_sync_fifo,
            "u_sync_fifo",
            params={'WIDTH': 1, 'DEPTH': 32},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.sync_push,
                "din": self.sync_din,
                "pop0": self.sync_pop0,
                "dout0": self.sync_dout0,
                "pop1": self.sync_pop1,
                "dout1": self.sync_dout1,
                "empty0": self.sync_empty0,
                "empty1": self.sync_empty1,
                "full": self.sync_full,
            },
        )
        self.acc_o_ready <<= (((~self.sync_empty1) & (~self.sync_dout1)) & self.merge_o_ready)
        self.obuf_push <<= (self.merge_o_valid & self.merge_o_ready)
        self.obuf_din <<= Cat(self.merge_o_vm_id, self.merge_o_res)
        self.obuf_pop <<= (self.pap_sq_valid & self.pap_sq_ready)
        # TODO: unpack assignment: Cat(self.pap_sq_vm_id, self.pap_sq_res) = self.obuf_dout
        # Consider using Split() or manual bit slicing
        self.pap_sq_valid <<= (~self.obuf_empty)

        obuf_fifo = js_vm_sfifo(WIDTH=(((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), DEPTH=2)
        self.instantiate(
            obuf_fifo,
            "obuf_fifo",
            params={'WIDTH': (((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.obuf_push,
                "din": self.obuf_din,
                "pop": self.obuf_pop,
                "dout": self.obuf_dout,
                "full": self.obuf_full,
                "empty": self.obuf_empty,
            },
        )
        self.sync_pop0 <<= (self.monmul_o_valid & self.monmul_o_ready)
        self.sync_pop1 <<= (self.merge_o_valid & self.merge_o_ready)
        self.lff_pop <<= ((self.merge_o_valid & self.merge_o_ready) & self.sync_dout1)
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.REG_WIDTH):
            with If(((i >= 0) & (i < self.DATA_WIDTH))):
                self.src0_tmp[i] <<= self.src0_value[i]
                self.src1_tmp[i] <<= self.src1_value[i]
            with Else():
                self.src0_tmp[i] <<= 0
                self.src1_tmp[i] <<= 0
        self.src0_truncated_bit <<= self.src0_tmp[self.src0_imm]
        self.src1_truncated_bit <<= self.src1_tmp[self.src1_imm]
        self.monmul_a <<= Mux((self.src0_fmt == 10), Cat(Rep(Cat(0), (self.DATA_WIDTH - 1)), self.src0_truncated_bit), self.src0_value[(self.DATA_WIDTH - 1):0])
        self.monmul_b <<= Mux((self.src1_fmt == 10), Cat(Rep(Cat(0), (self.DATA_WIDTH - 1)), self.src1_truncated_bit), self.src1_value[(self.DATA_WIDTH - 1):0])
        # for-loop (non-generate) - parameter-driven
        for dly in range(0, self.MODMUL_DELAY):
            with If((dly == 0)):
                with If(self.monmul_o_ready):
                    self.sq_pap_isa_dly[dly] <<= self.sq_pap_data[(2 * self.REG_WIDTH):((2 * self.REG_WIDTH) + (self.ISA_BITS + 1))]
                    self.sq_pap_vm_id_dly[dly] <<= self.sq_pap_vm_id
            with Else():
                with If(self.monmul_o_ready):
                    self.sq_pap_isa_dly[dly] <<= self.sq_pap_isa_dly[(dly - 1)]
                    self.sq_pap_vm_id_dly[dly] <<= self.sq_pap_vm_id_dly[(dly - 1)]
        self.sq_pap_ready <<= (self.monmul_o_ready & (~self.sync_full))

        @self.comb
        def _comb_logic():
            self.pap_sq_hq_rel_valid <<= self.pap_res_valid
            self.pap_sq_fc_dec <<= self.pap_fc_dec
            self.pap_sq_fc_dec_vm_id <<= self.pap_res_vm_id
        self.pap_sq_hq_rel_vm_id <<= self.pap_sq_fc_dec_vm_id

        u_barr_modmul = barr_modmult(DATA_WIDTH=self.DATA_WIDTH, E_WIDTH=2, VALID_WIDTH=1)
        self.instantiate(
            u_barr_modmul,
            "u_barr_modmul",
            params={'DATA_WIDTH': self.DATA_WIDTH, 'E_WIDTH': 2, 'VALID_WIDTH': 1},
            port_map={
                "clk": self.clk,
                "rst_n": self.rstn,
                "mul_a": self.monmul_a,
                "mul_b": self.monmul_b,
                "pre_c": self.sq_pap_mu[self.DATA_WIDTH:0],
                "prime": self.sq_pap_q[(self.DATA_WIDTH - 1):0],
                "en": self.monmul_o_ready,
                "i_valid": self.sq_pap_valid,
                "o_valid": self.monmul_o_valid,
                "res": self.monmul_res,
            },
        )
        self.monmul_o_ready <<= ((~self.lff_full) & self.modacc_i_ready)

        u_modacc = js_vm_modacc()
        self.instantiate(
            u_modacc,
            "u_modacc",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "data": Cat(self.sq_pap_isa_dly[(self.MODMUL_DELAY - 1)], 6, 0, self.monmul_res[(self.DATA_WIDTH - 1):0]),
                "q": self.sq_pap_q[(self.DATA_WIDTH - 1):0],
                "res": self.acc_o_res,
                "i_vm_id": self.sq_pap_vm_id_dly[(self.MODMUL_DELAY - 1)],
                "o_vm_id": self.acc_o_vm_id,
                "i_valid": self.modacc_i_valid,
                "o_valid": self.acc_o_valid,
                "i_ready": self.modacc_i_ready,
                "o_ready": self.acc_o_ready,
            },
        )
        self.lff_push <<= ((((~self.sync_empty0) & (self.sync_dout0 == 1)) & (~self.lff_full)) & self.monmul_o_valid)

        u_mmul_lff = js_vm_sfifo(WIDTH=(((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), DEPTH=10)
        self.instantiate(
            u_mmul_lff,
            "u_mmul_lff",
            params={'WIDTH': (((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), 'DEPTH': 10},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.lff_push,
                "din": Cat(self.sq_pap_vm_id_dly[(self.MODMUL_DELAY - 1)], self.sq_pap_isa_dly[(self.MODMUL_DELAY - 1)], 6, 0, self.monmul_res[(self.DATA_WIDTH - 1):0]),
                "pop": self.lff_pop,
                "dout": self.lff_dout,
                "empty": self.lff_empty,
                "full": self.lff_full,
            },
        )
        self.pap_active <<= (((((~self.lff_empty) | (~self.obuf_empty)) | (~self.sync_empty0)) | (~self.sync_empty1)) | self.sq_pap_valid)
        # unhandled statement: # function get_sf
