"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_vm_mip_top(Module):
    def __init__(self, name: str = "js_vm_mip_top"):
        super().__init__(name or "js_vm_mip_top")

        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.mip_active = Output(1, "mip_active")
        self.sq_mip_valid = Input(1, "sq_mip_valid")
        self.sq_mip_data = Input(((((self.ISA_BITS + (2 * self.REG_WIDTH)) + 1) - 1) - 0 + 1), "sq_mip_data")
        self.sq_mip_q = Input(256, "sq_mip_q")
        self.sq_mip_vm_id = Input(4, "sq_mip_vm_id")
        self.sq_mip_ready = Output(1, "sq_mip_ready")
        self.mip_sq_fc_dec = Output(((self.FC_NUM - 1) - 0 + 1), "mip_sq_fc_dec")
        self.mip_sq_fc_dec_vm_id = Output(4, "mip_sq_fc_dec_vm_id")
        self.mip_sq_res = Output(((((self.ISA_BITS + self.REG_WIDTH) + 1) - 1) - 0 + 1), "mip_sq_res")
        self.mip_sq_vm_id = Output(4, "mip_sq_vm_id")
        self.mip_sq_valid = Output(1, "mip_sq_valid")
        self.mip_sq_ready = Input(1, "mip_sq_ready")

        self.sff_push = Wire(1, "sff_push")
        self.sff_din = Wire((((((5 + self.ISA_BITS) + 1) + self.DATA_WIDTH) - 1) - 0 + 1), "sff_din")
        self.sff_pop = Wire(1, "sff_pop")
        self.sff_dout = Wire((((((5 + self.ISA_BITS) + 1) + self.DATA_WIDTH) - 1) - 0 + 1), "sff_dout")
        self.sff_empty = Wire(1, "sff_empty")
        self.sff_full = Wire(1, "sff_full")
        self.dff_push = Wire(1, "dff_push")
        self.dff_din = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "dff_din")
        self.dff_pop = Wire(1, "dff_pop")
        self.dff_dout = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "dff_dout")
        self.dff_empty = Wire(1, "dff_empty")
        self.dff_full = Wire(1, "dff_full")
        self.modi_valid = Wire(1, "modi_valid")
        self.modi_ready = Wire(1, "modi_ready")
        self.modi_ot = Reg(2, "modi_ot")
        self.out_is_zero = Wire(1, "out_is_zero")
        self.out_isa = Wire(((self.ISA_BITS - 1) - 0 + 1), "out_isa")
        self.out_cc = Wire(1, "out_cc")
        self.out_b = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "out_b")
        self.mip_sq_sf = Wire(((self.FC_NUM - 1) - 0 + 1), "mip_sq_sf")
        self.fc_dec_vm_id = Wire(4, "fc_dec_vm_id")
        self.fc_dec = Wire(((self.FC_NUM - 1) - 0 + 1), "fc_dec")

        # TODO: unpack assignment: Cat(self.rsv, self.dst_fmt, self.dst_type, self.dst1_reg, self.dst0_reg, self.src1_imm, self.src1_fmt, self.src1_type, self.src1_reg, self.src0_imm, self.src0_fmt, self.src0_type, self.src0_reg, self.wf, self.sf, self.cc_reg, self.opcode, self.optype, self.cc_value, self.src1_value, self.src0_value) = self.sq_mip_data
        # Consider using Split() or manual bit slicing
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
        self.modinv_a <<= Mux((self.src0_fmt == 10), Cat(Rep(Cat(0), (self.DATA_WIDTH - 1)), self.src0_truncated_bit), self.src0_value[(self.DATA_WIDTH - 1):0])
        self.modinv_b <<= Mux((self.src1_fmt == 10), Cat(Rep(Cat(0), (self.DATA_WIDTH - 1)), self.src1_truncated_bit), self.src1_value[(self.DATA_WIDTH - 1):0])
        self.modinv_a_is_zero <<= (self.modinv_a == 0)
        self.sff_push <<= (self.sq_mip_valid & self.sq_mip_ready)
        self.sff_din <<= Cat(self.modinv_a_is_zero, self.sq_mip_vm_id, self.sq_mip_data[(2 * self.REG_WIDTH):((2 * self.REG_WIDTH) + (self.ISA_BITS + 1))], self.modinv_b)
        self.sff_pop <<= (self.mip_sq_valid & self.mip_sq_ready)

        u_sync_fifo = js_vm_sfifo(WIDTH=(((5 + self.ISA_BITS) + 1) + self.DATA_WIDTH), DEPTH=4)
        self.instantiate(
            u_sync_fifo,
            "u_sync_fifo",
            params={'WIDTH': (((5 + self.ISA_BITS) + 1) + self.DATA_WIDTH), 'DEPTH': 4},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.sff_push,
                "din": self.sff_din,
                "pop": self.sff_pop,
                "dout": self.sff_dout,
                "full": self.sff_full,
                "empty": self.sff_empty,
            },
        )

        u_data_fifo = js_vm_sfifo(WIDTH=self.DATA_WIDTH, DEPTH=2)
        self.instantiate(
            u_data_fifo,
            "u_data_fifo",
            params={'WIDTH': self.DATA_WIDTH, 'DEPTH': 2},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "push": self.dff_push,
                "din": self.dff_din,
                "pop": self.dff_pop,
                "dout": self.dff_dout,
                "full": self.dff_full,
                "empty": self.dff_empty,
            },
        )
        self.modinv_go <<= (self.modi_valid & self.modi_ready)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.modi_ot <<= 2
            with Else():
                self.modi_ot <<= ((self.modi_ot - (self.modi_valid & self.modi_ready)) + self.dff_pop)
        self.modi_ready <<= ((~self.busy) & (self.modi_ot != 0))
        self.sq_mip_ready <<= ((~self.sff_full) & Mux(self.modinv_a_is_zero, 1, self.modi_ready))
        self.dff_push <<= self.modinv_valid
        self.dff_din <<= self.modinv_R
        # TODO: unpack assignment: Cat(self.out_is_zero, self.mip_sq_vm_id, self.out_isa, self.out_cc, self.out_b) = self.sff_dout
        # Consider using Split() or manual bit slicing
        self.mip_sq_valid <<= ((~self.sff_empty) & Mux(self.out_is_zero, 1, (~self.dff_empty)))
        self.mip_sq_res <<= Mux(((~self.sff_empty) & self.out_is_zero), Cat(self.out_isa, self.out_cc, Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.out_b), Cat(self.out_isa, self.out_cc, Rep(Cat(0), (self.REG_WIDTH - self.DATA_WIDTH)), self.dff_dout))
        self.dff_pop <<= (self.sff_pop & (~self.out_is_zero))

        @self.comb
        def _comb_logic():
            self.mip_sq_fc_dec <<= self.fc_dec
            self.mip_sq_fc_dec_vm_id <<= self.fc_dec_vm_id

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.busy <<= 0
            with Else():
                with If(self.modinv_go):
                    self.busy <<= 1
                with Else():
                    with If(self.modinv_valid):
                        self.busy <<= 0
                    with Else():
                        self.busy <<= self.busy

        u_modinv = mod_inverse(MODULU_LENGTH=self.DATA_WIDTH)
        self.instantiate(
            u_modinv,
            "u_modinv",
            params={'MODULU_LENGTH': self.DATA_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "go": self.modinv_go,
                "valid": self.modinv_valid,
                "prime_q": self.sq_mip_q[(self.DATA_WIDTH - 1):0],
                "a": self.modinv_a,
                "R": self.modinv_R,
            },
        )
        self.mip_active <<= ((self.busy | (~self.sff_empty)) | self.sq_mip_valid)
        # unhandled statement: # function get_sf
