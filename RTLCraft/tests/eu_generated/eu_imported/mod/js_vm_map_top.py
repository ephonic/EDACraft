"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_map_top(Module):
    def __init__(self, name: str = "js_vm_map_top"):
        super().__init__(name or "js_vm_map_top")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.map_active = Output(1, "map_active")
        self.sq_map_valid = Input(1, "sq_map_valid")
        self.sq_map_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_map_data")
        self.sq_map_modsub_q = Input(((self.DATA_WIDTH - 1) - 0 + 1), "sq_map_modsub_q")
        self.sq_map_modadd_q = Input(((self.DATA_WIDTH - 1) - 0 + 1), "sq_map_modadd_q")
        self.sq_map_vm_id = Input(4, "sq_map_vm_id")
        self.sq_map_ready = Output(1, "sq_map_ready")
        self.map_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "map_sq_fc_dec")
        self.map_sq_fc_dec_vm_id = Output(4, "map_sq_fc_dec_vm_id")
        self.map_sq_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "map_sq_res")
        self.map_sq_valid = Output(1, "map_sq_valid")
        self.map_sq_vm_id = Output(4, "map_sq_vm_id")
        self.map_sq_ready = Input(1, "map_sq_ready")

        self.sync_push = Wire(1, "sync_push")
        self.sync_din = Wire(2, "sync_din")
        self.sync_pop = Wire(1, "sync_pop")
        self.sync_dout = Wire(2, "sync_dout")
        self.sync_empty = Wire(1, "sync_empty")
        self.sync_full = Wire(1, "sync_full")
        self.map_sq_sf = Wire(((self.FC_NUM - 1) - 0 + 1), "map_sq_sf")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")


        u_sync_fifo = js_vm_sfifo(WIDTH=2, DEPTH=16)
        self.instantiate(
            u_sync_fifo,
            "u_sync_fifo",
            params={'WIDTH': 2, 'DEPTH': 16},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.sync_push,
                "din": self.sync_din,
                "pop": self.sync_pop,
                "dout": self.sync_dout,
                "empty": self.sync_empty,
                "full": self.sync_full,
            },
        )
        self.sync_pop <<= (self.map_sq_valid & self.map_sq_ready)
        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype, self.cc_value, self.src1_value, self.src0_value) = self.sq_map_data
        # Consider using Split() or manual bit slicing
        # for-loop (non-generate) - parameter-driven
        for i in range(0, self.REG_WIDTH):
            with If(((i >= 0) & (i < self.DATA_WIDTH))):
                self.src0_tmp[i] <<= self.src0_value[i]
                self.src1_tmp[i] <<= self.src1_value[i]
            with Else():
                self.src0_tmp[i] <<= 0
                self.src1_tmp[i] <<= 0
        self.sync_din <<= Mux((self.opcode == self.OPCODE_MADD_ACC), 0, Mux((self.opcode == self.OPCODE_MSUB), 1, Mux((self.opcode == self.OPCODE_MADD), 2, 0)))
        self.src0_truncated_bit <<= self.src0_tmp[self.src0_imm]
        self.src1_truncated_bit <<= self.src1_tmp[self.src1_imm]
        self.pipe_used_data <<= Cat(self.sq_map_data[(2 * self.REG_WIDTH):((2 * self.REG_WIDTH) + (self.ISA_BITS + 1))], Mux((self.src1_fmt == 10), Cat(Rep(Cat(0), (self.REG_WIDTH - 1)), self.src1_truncated_bit), self.src1_value), Mux((self.src0_fmt == 10), Cat(Rep(Cat(0), (self.REG_WIDTH - 1)), self.src0_truncated_bit), self.src0_value))
        self.modsub_i_valid <<= ((self.sq_map_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MSUB))
        self.modadd_i_valid <<= ((self.sq_map_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MADD))
        self.modacc_i_valid <<= ((self.sq_map_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MADD_ACC))
        self.sq_map_ready <<= Mux((self.opcode == self.OPCODE_MSUB), (self.modsub_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MADD), (self.modadd_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MADD_ACC), (self.modacc_i_ready & (~self.sync_full)), 0)))
        self.map_sq_valid <<= ((~self.sync_empty) & ((((self.sync_dout == 0) & self.modacc_o_valid) | ((self.sync_dout == 1) & self.modsub_o_valid)) | ((self.sync_dout == 2) & self.modadd_o_valid)))
        self.map_sq_vm_id <<= Mux((self.sync_dout == 0), self.modacc_o_vm_id, Mux((self.sync_dout == 1), self.modsub_o_vm_id, Mux((self.sync_dout == 2), self.modadd_o_vm_id, 0)))
        self.map_sq_res <<= Mux((self.sync_dout == 0), self.modacc_res, Mux((self.sync_dout == 1), self.modsub_res, Mux((self.sync_dout == 2), self.modadd_res, 0)))
        self.modacc_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 0)) & self.map_sq_ready)
        self.modsub_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 1)) & self.map_sq_ready)
        self.modadd_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 2)) & self.map_sq_ready)

        @self.comb
        def _comb_logic():
            self.map_sq_fc_dec <<= self.fc_dec
            self.map_sq_fc_dec_vm_id <<= Mux(self.modsub_o_valid, self.modsub_o_vm_id, self.modadd_o_vm_id)

        u_modsub = js_vm_modsub()
        self.instantiate(
            u_modsub,
            "u_modsub",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "data": self.pipe_used_data,
                "q": self.sq_map_modsub_q,
                "res": self.modsub_res,
                "i_vm_id": self.sq_map_vm_id,
                "o_vm_id": self.modsub_o_vm_id,
                "i_valid": self.modsub_i_valid,
                "o_valid": self.modsub_o_valid,
                "i_ready": self.modsub_i_ready,
                "o_ready": self.modsub_o_ready,
            },
        )

        u_modacc = js_vm_modaddc()
        self.instantiate(
            u_modacc,
            "u_modacc",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "data": self.pipe_used_data,
                "q": self.sq_map_modadd_q,
                "res": self.modacc_res,
                "i_vm_id": self.sq_map_vm_id,
                "o_vm_id": self.modacc_o_vm_id,
                "i_valid": self.modacc_i_valid,
                "o_valid": self.modacc_o_valid,
                "i_ready": self.modacc_i_ready,
                "o_ready": self.modacc_o_ready,
            },
        )

        u_modadd = js_vm_modadd()
        self.instantiate(
            u_modadd,
            "u_modadd",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "data": self.pipe_used_data,
                "q": self.sq_map_modadd_q,
                "res": self.modadd_res,
                "i_vm_id": self.sq_map_vm_id,
                "o_vm_id": self.modadd_o_vm_id,
                "i_valid": self.modadd_i_valid,
                "o_valid": self.modadd_o_valid,
                "i_ready": self.modadd_i_ready,
                "o_ready": self.modadd_o_ready,
            },
        )
        self.map_active <<= ((~self.sync_empty) | self.sq_map_valid)
        # unhandled statement: # function get_sf
