"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_int(Module):
    def __init__(self, name: str = "js_vm_int"):
        super().__init__(name or "js_vm_int")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.int_active = Output(1, "int_active")
        self.int_and_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "int_and_data")
        self.int_and_i_valid = Input(1, "int_and_i_valid")
        self.int_and_i_ready = Output(1, "int_and_i_ready")
        self.int_and_o_ready = Input(1, "int_and_o_ready")
        self.int_and_o_valid = Output(1, "int_and_o_valid")
        self.int_and_i_vm_id = Input(4, "int_and_i_vm_id")
        self.int_and_o_vm_id = Output(4, "int_and_o_vm_id")
        self.int_and_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "int_and_res")
        self.int_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "int_sq_fc_dec")
        self.int_sq_fc_dec_vm_id = Output(4, "int_sq_fc_dec_vm_id")

        self.sync_push = Wire(1, "sync_push")
        self.sync_din = Wire(1, "sync_din")
        self.sync_pop = Wire(1, "sync_pop")
        self.sync_dout = Wire(1, "sync_dout")
        self.sync_empty = Wire(1, "sync_empty")
        self.sync_full = Wire(1, "sync_full")
        self.obuf_push = Wire(1, "obuf_push")
        self.obuf_din = Wire((((((4 + self.ISA_BITS) + self.REG_WIDTH) + 1) - 1) - 0 + 1), "obuf_din")
        self.obuf_pop = Wire(1, "obuf_pop")
        self.obuf_dout = Wire((((((4 + self.ISA_BITS) + self.REG_WIDTH) + 1) - 1) - 0 + 1), "obuf_dout")
        self.obuf_empty = Wire(1, "obuf_empty")
        self.obuf_full = Wire(1, "obuf_full")
        self.integer_mode = Wire(3, "integer_mode")
        self.valid_i_main = Wire(1, "valid_i_main")
        self.ready_i_main = Wire(1, "ready_i_main")
        self.valid_o_main = Wire(1, "valid_o_main")
        self.ready_o_main = Wire(1, "ready_o_main")
        self.sf = Wire(((self.FC_NUM - 1) - 0 + 1), "sf")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")
        self.fc_dec_vm_id = Wire(4, "fc_dec_vm_id")
        self.data_o_main = Wire(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "data_o_main")
        self.merge_o_valid = Wire(1, "merge_o_valid")
        self.merge_o_vm_id = Wire(4, "merge_o_vm_id")
        self.merge_o_res = Wire(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "merge_o_res")
        self.merge_o_ready = Wire(1, "merge_o_ready")
        self.div_phase = Reg(1, "div_phase")
        self.div_pulse = Wire(1, "div_pulse")

        # TODO: unpack assignment: Cat(self.int_and_isa, self.int_and_cc_value, self.int_and_data_y, self.int_and_data_x) = self.int_and_data
        # Consider using Split() or manual bit slicing
        self.add_full_in <<= self.int_and_data
        self.sub_full_in <<= self.int_and_data
        self.mul_full_in <<= self.int_and_data
        self.div_full_in <<= self.int_and_data
        self.rem_full_in <<= self.int_and_data
        self.vm_id_add_in <<= self.int_and_i_vm_id
        self.vm_id_sub_in <<= self.int_and_i_vm_id
        self.vm_id_mul_in <<= self.int_and_i_vm_id
        self.vm_id_div_in <<= self.int_and_i_vm_id
        self.vm_id_rem_in <<= self.int_and_i_vm_id
        self.integer_mode <<= Mux((self.int_and_isa[2:0] == 3), Mux((self.int_and_isa[5:3] == 0), 0, Mux((self.int_and_isa[5:3] == 1), 1, Mux((self.int_and_isa[5:3] == 2), 2, Mux((self.int_and_isa[5:3] == 3), 3, Mux((self.int_and_isa[5:3] == 4), 4, 0))))), 0)
        self.valid_i_div <<= Mux((self.integer_mode == 3), (self.int_and_i_valid & (~self.sync_full)), 0)
        self.valid_i_rem <<= Mux((self.integer_mode == 4), self.int_and_i_valid, 0)
        self.int_and_i_ready <<= ((((self.valid_i_main & self.ready_o_main) | (self.valid_i_div & self.ready_o_div)) | (self.valid_i_rem & self.ready_o_rem)) & (~self.sync_full))

        @self.comb
        def _comb_logic():
            self.int_sq_fc_dec <<= self.fc_dec
            self.int_sq_fc_dec_vm_id <<= self.fc_dec_vm_id

        u_main = js_int_alu()
        self.instantiate(
            u_main,
            "u_main",
            port_map={
                "ready_i": self.ready_o_main,
                "valid_o": self.valid_o_main,
                "data_o": self.data_o_main[(((self.ISA_BITS + self.REG_WIDTH) + 1) - 1):0],
                "vm_id_o": self.vm_id_o_main[3:0],
                "clk": self.clk,
                "rstn": self.rstn,
                "valid_i": self.valid_i_main,
                "vm_id_i": self.int_and_i_vm_id[3:0],
                "data_i": self.int_and_data[(((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1):0],
                "ready_o": self.ready_i_main,
            },
        )

        div_inst = divider()
        self.instantiate(
            div_inst,
            "div_inst",
            port_map={
                "clk": self.clk,
                "rst_n": self.rstn,
                "valid_i": self.valid_i_div,
                "ready_o": self.ready_o_div,
                "valid_o": self.valid_o_div,
                "ready_i": self.ready_i_div,
                "div_full_in": self.div_full_in,
                "div_full_out": self.div_full_out,
                "div_vm_id_in": self.vm_id_div_in,
                "div_vm_id_out": self.vm_id_div_out,
            },
        )
        self.ready_o_rem <<= 1
        self.valid_o_rem <<= 0
        self.rem_full_out <<= 0
        self.vm_id_rem_out <<= 0
        self.ready_i_div <<= (((~self.sync_empty) & self.sync_dout) & self.merge_o_ready)
        self.ready_i_main <<= (((~self.sync_empty) & (~self.sync_dout)) & self.merge_o_ready)
        self.ready_i_rem <<= 1

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.div_phase <<= 0
            with Else():
                with If(((self.int_and_i_valid & (self.integer_mode == 3)) & (~self.div_phase))):
                    self.div_phase <<= 1
                with Else():
                    with If((self.valid_o_div & self.ready_i_div)):
                        self.div_phase <<= 0
        self.sync_push <<= (self.int_and_i_valid & Mux((self.integer_mode == 3), self.div_pulse, self.int_and_i_ready))
        self.sync_din <<= (self.integer_mode == 3)

        u_sync_fifo = js_vm_sfifo(WIDTH=1, DEPTH=4)
        self.instantiate(
            u_sync_fifo,
            "u_sync_fifo",
            params={'WIDTH': 1, 'DEPTH': 4},
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
        self.sync_pop <<= (self.merge_o_valid & self.merge_o_ready)
        self.obuf_push <<= (self.merge_o_valid & self.merge_o_ready)
        self.obuf_din <<= Cat(self.merge_o_vm_id, self.merge_o_res)
        self.int_and_o_valid <<= (~self.obuf_empty)
        # TODO: unpack assignment: Cat(self.int_and_o_vm_id, self.int_and_res) = self.obuf_dout
        # Consider using Split() or manual bit slicing
        self.obuf_pop <<= (self.int_and_o_valid & self.int_and_o_ready)

        u_out_fifo = js_vm_sfifo(WIDTH=(((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), DEPTH=2)
        self.instantiate(
            u_out_fifo,
            "u_out_fifo",
            params={'WIDTH': (((4 + self.ISA_BITS) + self.REG_WIDTH) + 1), 'DEPTH': 2},
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
        self.int_active <<= (((~self.obuf_empty) | (~self.sync_empty)) | self.int_and_i_valid)
        # unhandled statement: # function get_sf
