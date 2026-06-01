"""
L3 DSL — I2C Master Controller with FSM.

Extracted from ref_rtl/interfaces/i2c/rtl/i2c_master.v
Micro-architecture: bit-banged I2C with FSM (IDLE→START→BIT→ACK→STOP).
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Switch


class I2CMaster(Module):
    """I2C master controller with configurable clock divider."""

    def __init__(self, clk_div=50, name="i2c_master"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        # Control interface
        self.start = Input(1, "start"); self.addr = Input(7, "addr")
        self.rw = Input(1, "rw")  # 0=write, 1=read
        self.wdata = Input(8, "wdata")
        self.ready = Output(1, "ready"); self.rdata = Output(8, "rdata")
        self.ack_error = Output(1, "ack_error")

        # I2C bus (tri-state, modeled as input/output)
        self.sda_in = Input(1, "sda_in"); self.sda_out = Output(1, "sda_out")
        self.sda_oen = Output(1, "sda_oen")  # 0=output enabled
        self.scl_in = Input(1, "scl_in"); self.scl_out = Output(1, "scl_out")
        self.scl_oen = Output(1, "scl_oen")

        # FSM states
        IDLE = 0; START = 1; SEND_BYTE = 2; WAIT_ACK = 3
        RECV_BYTE = 4; SEND_ACK = 5; STOP = 6

        self._state = Reg(3, "i2c_state"); self._bit_cnt = Reg(4, "i2c_bit")
        self._div = Reg(16, "i2c_div")
        self._data = Reg(8, "i2c_data"); self._sr = Reg(8, "i2c_sr")

        with self.comb:
            self.ready <<= (self._state == IDLE)
            self.scl_out <<= 0; self.sda_out <<= 0
            self.sda_oen <<= 1; self.scl_oen <<= 1
            self.rdata <<= self._sr

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= IDLE; self._div <<= 0
                self._data <<= 0; self._sr <<= 0; self._bit_cnt <<= 0
            with Else():
                tick = (self._div == 0)
                with If(tick == 0):
                    self._div <<= self._div - 1
                with Else():
                    self._div <<= clk_div

                with Switch(self._state) as sw:
                    with sw.case(IDLE):
                        self.sda_oen <<= 1; self.scl_oen <<= 1
                        with If(self.start & tick):
                            self._state <<= START; self._data <<= self.wdata
                            self._bit_cnt <<= 7

                    with sw.case(START):
                        with If(tick):
                            self.sda_oen <<= 0; self.sda_out <<= 0
                            self.scl_oen <<= 0; self.scl_out <<= 0
                            self._state <<= SEND_BYTE
                            self._bit_cnt <<= 7

                    with sw.case(SEND_BYTE):
                        with If(tick):
                            self.scl_oen <<= 0; self.scl_out <<= 0
                            self.sda_oen <<= 0
                            self.sda_out <<= (self._data >> self._bit_cnt) & 1
                            with If(self._bit_cnt > 0):
                                self._bit_cnt <<= self._bit_cnt - 1
                            with Else():
                                self._state <<= WAIT_ACK

                    with sw.case(WAIT_ACK):
                        with If(tick):
                            self.scl_oen <<= 0; self.scl_out <<= 0
                            self.sda_oen <<= 1  # release SDA for ACK
                            self.ack_error <<= self.sda_in  # NACK if high
                            self._state <<= STOP

                    with sw.case(STOP):
                        with If(tick):
                            self.sda_oen <<= 0; self.sda_out <<= 1
                            self.scl_oen <<= 1
                            self._state <<= IDLE
