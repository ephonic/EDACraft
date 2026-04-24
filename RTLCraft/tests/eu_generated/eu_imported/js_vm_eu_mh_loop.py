"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_eu_mh_loop(Module):
    def __init__(self, name: str = "js_vm_eu_mh_loop"), MERKEL_MAX: int = (1 << (3 * self.MERKEL_LEVEL)), MH_IDLE: int = 0, MH_LOOP: int = 1, MH_EOP: int = 2:
        super().__init__(name or "js_vm_eu_mh_loop")

        self.add_localparam("MERKEL_MAX", (1 << (3 * self.MERKEL_LEVEL)))
        self.add_localparam("MH_IDLE", 0)
        self.add_localparam("MH_LOOP", 1)
        self.add_localparam("MH_EOP", 2)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.mov_merkel_valid = Input(1, "mov_merkel_valid")
        self.mov_merkel_eop = Input(1, "mov_merkel_eop")
        self.mov_merkel_res = Input(((((1 + 8) + 256) - 1) - 0 + 1), "mov_merkel_res")
        self.mov_merkel_ready = Output(1, "mov_merkel_ready")
        self.mov_mh_valid = Output(1, "mov_mh_valid")
        self.mov_mh_data = Output(256, "mov_mh_data")
        self.mov_mh_type = Output(4, "mov_mh_type")
        self.mov_mh_index = Output(18, "mov_mh_index")
        self.mov_mh_last = Output(1, "mov_mh_last")
        self.mov_mh_ready = Input(1, "mov_mh_ready")

        self.mh_valid = Reg(1, "mh_valid")
        self.mh_ready = Wire(1, "mh_ready")
        self.mh_st = Reg(2, "mh_st")
        self.mh_st_nxt = Reg(2, "mh_st_nxt")
        self.mov_merkel_data = Wire(((253 - 1) - 0 + 1), "mov_merkel_data")
        self.mov_rsv = Wire(3, "mov_rsv")
        self.mov_merkel_bit = Wire(1, "mov_merkel_bit")
        self.mov_merkel_mcnt = Wire(8, "mov_merkel_mcnt")
        self.mov_merkel_is_fr = Wire(1, "mov_merkel_is_fr")
        self.mov_merkel_is_bit = Wire(1, "mov_merkel_is_bit")
        self.mov_merkel_mnum = Wire(8, "mov_merkel_mnum")
        self.mov_merkel_index = Reg(18, "mov_merkel_index")
        self.mov_merkel_index_nxt = Wire(19, "mov_merkel_index_nxt")
        self.mov_merkel_sending = Wire(19, "mov_merkel_sending")
        self.mh_cnt = Reg(32, "mh_cnt")
        self.pre_max_merkel = Wire(19, "pre_max_merkel")
        self.max_merkel = Reg(19, "max_merkel")
        self.mh_padding_start = Reg(1, "mh_padding_start")
        self.mov_bit_data = Wire(((264 - 1) - 0 + 1), "mov_bit_data")
        self.mov_bit_array = Array(8, -31, "mov_bit_array", vtype=Wire)
        self.mov_eop_padding_bit_num = Wire(18, "mov_eop_padding_bit_num")
        self.mov_eop_padding_1st_bad = Wire(1, "mov_eop_padding_1st_bad")
        self.mov_eop_padding_1st_num = Wire(4, "mov_eop_padding_1st_num")
        self.mov_eop_padding_cycle = Wire(6, "mov_eop_padding_cycle")
        self.mov_bit_num = Wire(9, "mov_bit_num")
        self.mov_bit_need_split = Wire(1, "mov_bit_need_split")
        self.mov_bit_1st_bad = Wire(1, "mov_bit_1st_bad")
        self.mov_bit_1st_num = Wire(4, "mov_bit_1st_num")
        self.mov_bit_num_adj = Wire(9, "mov_bit_num_adj")
        self.mov_bit_cycle = Wire(6, "mov_bit_cycle")
        self.mov_trans_bits = Wire(18, "mov_trans_bits")
        self.mov_trans_num = Wire(6, "mov_trans_num")
        self.mov_trans_cnt = Reg(6, "mov_trans_cnt")
        self.mov_trans_last = Wire(1, "mov_trans_last")
        self.mov_trans_cnt_nxt = Wire(6, "mov_trans_cnt_nxt")
        self.mov_trans_first = Wire(1, "mov_trans_first")
        self.mov_mh_bits = Wire(8, "mov_mh_bits")
        self.mov_mh_index_nxt = Wire(19, "mov_mh_index_nxt")
        self.mh_bit_num = Reg(4, "mh_bit_num")
        self.mov_loop_bit_num = Wire(4, "mov_loop_bit_num")
        self.mh_inc_num = Wire(18, "mh_inc_num")
        self.mh_is_bit = Reg(1, "mh_is_bit")

        # TODO: unpack assignment: Cat(self.mov_merkel_bit, self.mov_merkel_mcnt, self.mov_rsv, self.mov_merkel_data) = self.mov_merkel_res
        # Consider using Split() or manual bit slicing

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mov_merkel_index <<= 0
            with Else():
                with If((self.mov_merkel_valid & self.mov_merkel_ready)):
                    self.mov_merkel_index <<= self.mov_merkel_index_nxt[17:0]

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mh_cnt <<= 0
            with Else():
                with If((self.mov_merkel_valid & self.mov_merkel_ready)):
                    self.mh_cnt <<= (self.mh_cnt + 1)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.max_merkel <<= 0
            with Else():
                with If(self.mh_padding_start):
                    self.max_merkel <<= self.pre_max_merkel
        with ForGen("i", 0, 33) as i:
            self.mov_bit_array[i] <<= self.mov_bit_data[(i * 8):((i * 8) + 8)]

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mov_trans_cnt <<= 0
            with Else():
                with If((self.mov_mh_valid & self.mov_mh_ready)):
                    self.mov_trans_cnt <<= self.mov_trans_cnt_nxt
        self.mov_mh_valid <<= self.mh_valid
        self.mov_mh_type[2:0] <<= Mux(((self.mh_st != self.MH_EOP) & self.mov_merkel_is_fr), 0, Mux(((self.mh_st != self.MH_EOP) & self.mov_merkel_is_bit), Mux((self.mh_bit_num == 8), 2, 1), Mux((|self.mov_mh_index[2:0]), 1, Mux((|self.mov_mh_index[5:3]), 2, Mux((|self.mov_mh_index[8:6]), 3, Mux((|self.mov_mh_index[11:9]), 4, Mux((|self.mov_mh_index[14:12]), 5, Mux((|self.mov_mh_index[17:15]), 6, 7))))))))
        self.mov_mh_type[3] <<= Mux((self.mh_st == self.MH_EOP), (Cat(0, self.mov_mh_index) >= self.max_merkel), (Cat(0, self.mov_mh_index) > self.pre_max_merkel))
        self.mov_mh_index_nxt <<= (Cat(0, self.mov_mh_index) + self.mh_inc_num)
        self.mov_mh_last <<= (self.mov_mh_index_nxt == self.MERKEL_MAX)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mov_mh_index <<= 0
            with Else():
                with If((self.mov_mh_valid & self.mov_mh_ready)):
                    self.mov_mh_index <<= Mux(self.mov_mh_last, 0, self.mov_mh_index_nxt[17:0])

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.mh_st <<= self.MH_IDLE
            with Else():
                self.mh_st <<= self.mh_st_nxt

        @self.comb
        def _comb_logic():
            self.mh_st_nxt <<= self.mh_st
            self.mh_valid <<= 0
            self.mov_merkel_ready <<= 0
            self.mh_bit_num <<= 0
            self.mh_padding_start <<= 0
            with Switch(self.mh_st) as sw:
                with sw.case(self.MH_IDLE):
                    with If(self.mov_merkel_valid):
                        self.mh_valid <<= Mux(self.mov_merkel_bit, (self.mov_merkel_mcnt != 0), 1)
                        with If(self.mov_merkel_bit):
                            with If(((self.mov_merkel_index[2:0] + self.mov_merkel_mcnt) > 8)):
                                self.mh_bit_num <<= (8 - self.mov_mh_index[2:0])
                            with Else():
                                self.mh_bit_num <<= self.mov_merkel_mcnt[3:0]
                        with Else():
                            self.mh_bit_num <<= 1
                        with If((self.mov_merkel_bit & (self.mov_merkel_mcnt == 0))):
                            with If(self.mov_merkel_eop):
                                self.mov_merkel_ready <<= self.mov_mh_last
                                self.mh_st_nxt <<= Mux(self.mov_mh_last, self.MH_IDLE, self.MH_EOP)
                                self.mh_padding_start <<= (~self.mov_mh_last)
                            with Else():
                                self.mov_merkel_ready <<= 1
                                self.mh_st_nxt <<= self.MH_IDLE
                        with Else():
                            with If(self.mov_mh_ready):
                                with If(self.mov_trans_last):
                                    with If(self.mov_merkel_eop):
                                        self.mov_merkel_ready <<= self.mov_mh_last
                                        self.mh_st_nxt <<= Mux(self.mov_mh_last, self.MH_IDLE, self.MH_EOP)
                                        self.mh_padding_start <<= (~self.mov_mh_last)
                                    with Else():
                                        self.mov_merkel_ready <<= 1
                                with Else():
                                    self.mh_st_nxt <<= self.MH_LOOP
                with sw.case(self.MH_LOOP):
                    self.mh_valid <<= 1
                    self.mh_bit_num <<= Mux(self.mov_trans_last, Cat((~|self.mov_merkel_sending[2:0]), self.mov_merkel_sending[2:0]), 8)
                    with If(self.mov_mh_ready):
                        with If(self.mov_trans_last):
                            with If(self.mov_merkel_eop):
                                self.mov_merkel_ready <<= self.mov_mh_last
                                self.mh_st_nxt <<= Mux(self.mov_mh_last, self.MH_IDLE, self.MH_EOP)
                                self.mh_padding_start <<= (~self.mov_mh_last)
                            with Else():
                                self.mov_merkel_ready <<= 1
                                self.mh_st_nxt <<= self.MH_IDLE
                with sw.case(self.MH_EOP):
                    self.mh_valid <<= 1
                    with If(self.mov_trans_first):
                        self.mh_bit_num <<= (8 - self.mov_mh_index[2:0])
                    with Else():
                        self.mh_bit_num <<= 15
                    with If(self.mov_mh_ready):
                        with If(self.mov_mh_last):
                            self.mh_st_nxt <<= self.MH_IDLE
                            self.mov_merkel_ready <<= 1
                with sw.default():
                    self.mh_st_nxt <<= self.MH_IDLE
