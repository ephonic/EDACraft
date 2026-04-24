"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_macro_top(Module):
    def __init__(self, name: str = "js_vm_macro_top"):
        super().__init__(name or "js_vm_macro_top")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.mac_active = Output(1, "mac_active")
        self.sq_mac_valid = Input(1, "sq_mac_valid")
        self.sq_mac_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_mac_data")
        self.sq_mac_vm_id = Input(4, "sq_mac_vm_id")
        self.sq_mac_ready = Output(1, "sq_mac_ready")
        self.mac_sq_res = Output(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "mac_sq_res")
        self.mac_sq_valid = Output(1, "mac_sq_valid")
        self.mac_sq_vm_id = Output(4, "mac_sq_vm_id")
        self.mac_sq_mask = Output(2, "mac_sq_mask")
        self.mac_sq_ready = Input(1, "mac_sq_ready")
        self.mac_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "mac_sq_fc_dec")
        self.mac_sq_fc_dec_vm_id = Output(4, "mac_sq_fc_dec_vm_id")

        self.sync_din = Wire(3, "sync_din")
        self.sync_dout = Wire(3, "sync_dout")
        self.sync_pop = Wire(1, "sync_pop")
        self.sync_full = Wire(1, "sync_full")
        self.sync_empty = Wire(1, "sync_empty")
        self.sync_push = Wire(1, "sync_push")
        self.sf = Wire(((self.FC_NUM - 1) - 0 + 1), "sf")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")
        self.merge_o_valid = Wire(1, "merge_o_valid")
        self.merge_o_vm_id = Wire(4, "merge_o_vm_id")
        self.merge_o_res = Wire(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "merge_o_res")
        self.merge_o_ready = Wire(1, "merge_o_ready")
        self.obuf_push = Wire(1, "obuf_push")
        self.obuf_din = Wire((((((4 + self.ISA_BITS) + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "obuf_din")
        self.obuf_pop = Wire(1, "obuf_pop")
        self.obuf_dout = Wire((((((4 + self.ISA_BITS) + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "obuf_dout")
        self.obuf_empty = Wire(1, "obuf_empty")
        self.obuf_full = Wire(1, "obuf_full")

        self.opcode <<= self.sq_mac_data[(((2 * self.REG_WIDTH) + 1) + 3):((((2 * self.REG_WIDTH) + 1) + 3) + 3)]
        self.leq_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCLEQ))
        self.ternary_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCTERNARY))
        self.xor_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCXOR))
        self.and_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCAND))
        self.or_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCOR))
        self.lessthan_is_valid <<= ((self.sq_mac_valid & (~self.sync_full)) & (self.opcode == self.OPCODE_MCLT))
        self.sq_mac_ready <<= Mux((self.opcode == self.OPCODE_MCLEQ), (self.eu_macro_leq_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MCTERNARY), (self.eu_macro_ternary_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MCXOR), (self.eu_macro_xor_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MCAND), (self.eu_macro_and_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MCOR), (self.eu_macro_or_i_ready & (~self.sync_full)), Mux((self.opcode == self.OPCODE_MCLT), (self.eu_macro_lessthan_i_ready & (~self.sync_full)), 0))))))
        self.eu_macro_leq_data <<= self.sq_mac_data
        self.eu_macro_ternary_data <<= self.sq_mac_data
        self.eu_macro_xor_data <<= self.sq_mac_data
        self.eu_macro_and_data <<= self.sq_mac_data
        self.eu_macro_or_data <<= self.sq_mac_data
        self.eu_macro_lessthan_data <<= self.sq_mac_data
        self.eu_macro_leq_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_ternary_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_xor_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_and_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_or_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_lessthan_i_vm_id <<= self.sq_mac_vm_id
        self.eu_macro_leq_i_valid <<= self.leq_is_valid
        self.eu_macro_ternary_i_valid <<= self.ternary_is_valid
        self.eu_macro_xor_i_valid <<= self.xor_is_valid
        self.eu_macro_and_i_valid <<= self.and_is_valid
        self.eu_macro_or_i_valid <<= self.or_is_valid
        self.eu_macro_lessthan_i_valid <<= self.lessthan_is_valid
        self.mac_sq_mask <<= Mux((self.mac_sq_res[(((2 * self.REG_WIDTH) + 1) + 3):((((2 * self.REG_WIDTH) + 1) + 3) + 3)] == self.OPCODE_MCLT), self.eu_macro_lessthan_o_mask, 1)

        @self.comb
        def _comb_logic():
            self.mac_sq_fc_dec <<= self.fc_dec
            self.mac_sq_fc_dec_vm_id <<= self.mac_sq_vm_id
        self.sync_pop <<= (self.mac_sq_valid & self.mac_sq_ready)
        self.sync_din <<= Mux((self.opcode == self.OPCODE_MCLEQ), 0, Mux((self.opcode == self.OPCODE_MCTERNARY), 1, Mux((self.opcode == self.OPCODE_MCXOR), 2, Mux((self.opcode == self.OPCODE_MCAND), 3, Mux((self.opcode == self.OPCODE_MCOR), 4, Mux((self.opcode == self.OPCODE_MCLT), 5, 0))))))

        u_sync_fifo = js_vm_sfifo(WIDTH=3, DEPTH=2)
        self.instantiate(
            u_sync_fifo,
            "u_sync_fifo",
            params={'WIDTH': 3, 'DEPTH': 2},
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
        self.obuf_push <<= (self.merge_o_valid & self.merge_o_ready)
        self.obuf_din <<= Cat(self.merge_o_vm_id, self.merge_o_res)
        self.mac_sq_valid <<= (~self.obuf_empty)
        # TODO: unpack assignment: Cat(self.mac_sq_vm_id, self.mac_sq_res) = self.obuf_dout
        # Consider using Split() or manual bit slicing
        self.obuf_pop <<= (self.mac_sq_valid & self.mac_sq_ready)
        self.merge_o_ready <<= (~self.obuf_full)

        u_out_fifo = js_vm_sfifo(WIDTH=(((4 + self.ISA_BITS) + (2 * self.REG_WIDTH)) + 1), DEPTH=2)
        self.instantiate(
            u_out_fifo,
            "u_out_fifo",
            params={'WIDTH': (((4 + self.ISA_BITS) + (2 * self.REG_WIDTH)) + 1), 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.obuf_push,
                "din": self.obuf_din,
                "pop": self.obuf_pop,
                "dout": self.obuf_dout,
                "empty": self.obuf_empty,
                "full": self.obuf_full,
            },
        )
        self.eu_macro_leq_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 0)) & self.merge_o_ready)
        self.eu_macro_ternary_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 1)) & self.merge_o_ready)
        self.eu_macro_xor_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 2)) & self.merge_o_ready)
        self.eu_macro_and_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 3)) & self.merge_o_ready)
        self.eu_macro_or_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 4)) & self.merge_o_ready)
        self.eu_macro_lessthan_o_ready <<= (((~self.sync_empty) & (self.sync_dout == 5)) & self.merge_o_ready)

        u_macro_leq = js_vm_macro_leq()
        self.instantiate(
            u_macro_leq,
            "u_macro_leq",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_leq_data": self.eu_macro_leq_data,
                "eu_macro_leq_i_valid": self.eu_macro_leq_i_valid,
                "eu_macro_leq_i_vm_id": self.eu_macro_leq_i_vm_id,
                "eu_macro_leq_o_ready": self.eu_macro_leq_o_ready,
                "eu_macro_leq_o_valid": self.eu_macro_leq_o_valid,
                "eu_macro_leq_i_ready": self.eu_macro_leq_i_ready,
                "eu_macro_leq_o_vm_id": self.eu_macro_leq_o_vm_id,
                "eu_macro_leq_variable": self.eu_macro_leq_variable,
            },
        )

        u_macro_ternary = js_vm_macro_ternary()
        self.instantiate(
            u_macro_ternary,
            "u_macro_ternary",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_ternary_data": self.eu_macro_ternary_data,
                "eu_macro_ternary_i_valid": self.eu_macro_ternary_i_valid,
                "eu_macro_ternary_i_vm_id": self.eu_macro_ternary_i_vm_id,
                "eu_macro_ternary_o_ready": self.eu_macro_ternary_o_ready,
                "eu_macro_ternary_o_valid": self.eu_macro_ternary_o_valid,
                "eu_macro_ternary_i_ready": self.eu_macro_ternary_i_ready,
                "eu_macro_ternary_o_vm_id": self.eu_macro_ternary_o_vm_id,
                "eu_macro_ternary_variable": self.eu_macro_ternary_variable,
            },
        )

        u_macro_xor = js_vm_macro_xor()
        self.instantiate(
            u_macro_xor,
            "u_macro_xor",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_xor_data": self.eu_macro_xor_data,
                "eu_macro_xor_i_valid": self.eu_macro_xor_i_valid,
                "eu_macro_xor_i_vm_id": self.eu_macro_xor_i_vm_id,
                "eu_macro_xor_o_ready": self.eu_macro_xor_o_ready,
                "eu_macro_xor_o_valid": self.eu_macro_xor_o_valid,
                "eu_macro_xor_i_ready": self.eu_macro_xor_i_ready,
                "eu_macro_xor_o_vm_id": self.eu_macro_xor_o_vm_id,
                "eu_macro_xor_variable": self.eu_macro_xor_variable,
            },
        )

        u_macro_and = js_vm_macro_and()
        self.instantiate(
            u_macro_and,
            "u_macro_and",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_and_data": self.eu_macro_and_data,
                "eu_macro_and_i_valid": self.eu_macro_and_i_valid,
                "eu_macro_and_i_vm_id": self.eu_macro_and_i_vm_id,
                "eu_macro_and_o_ready": self.eu_macro_and_o_ready,
                "eu_macro_and_i_ready": self.eu_macro_and_i_ready,
                "eu_macro_and_o_valid": self.eu_macro_and_o_valid,
                "eu_macro_and_o_vm_id": self.eu_macro_and_o_vm_id,
                "eu_macro_and_res": self.eu_macro_and_res,
            },
        )

        u_macro_or = js_vm_macro_or()
        self.instantiate(
            u_macro_or,
            "u_macro_or",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_or_data": self.eu_macro_or_data,
                "eu_macro_or_i_valid": self.eu_macro_or_i_valid,
                "eu_macro_or_i_vm_id": self.eu_macro_or_i_vm_id,
                "eu_macro_or_o_ready": self.eu_macro_or_o_ready,
                "eu_macro_or_i_ready": self.eu_macro_or_i_ready,
                "eu_macro_or_o_valid": self.eu_macro_or_o_valid,
                "eu_macro_or_o_vm_id": self.eu_macro_or_o_vm_id,
                "eu_macro_or_res": self.eu_macro_or_res,
            },
        )

        u_macro_lessthan = js_vm_macro_lessthan()
        self.instantiate(
            u_macro_lessthan,
            "u_macro_lessthan",
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "eu_macro_lessthan_data": self.eu_macro_lessthan_data,
                "eu_macro_lessthan_i_valid": self.eu_macro_lessthan_i_valid,
                "eu_macro_lessthan_i_vm_id": self.eu_macro_lessthan_i_vm_id,
                "eu_macro_lessthan_o_ready": self.eu_macro_lessthan_o_ready,
                "eu_macro_lessthan_i_ready": self.eu_macro_lessthan_i_ready,
                "eu_macro_lessthan_o_valid": self.eu_macro_lessthan_o_valid,
                "eu_macro_lessthan_o_vm_id": self.eu_macro_lessthan_o_vm_id,
                "eu_macro_lessthan_o_mask": self.eu_macro_lessthan_o_mask,
                "eu_macro_lessthan_res": self.eu_macro_lessthan_res,
            },
        )
        self.mac_active <<= (((~self.sync_empty) | (~self.obuf_empty)) | self.sq_mac_valid)
        # unhandled statement: # function get_sf
