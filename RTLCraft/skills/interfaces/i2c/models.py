"""
skills.interfaces.i2c.models — I2C Behavioral Models
"""
from __future__ import annotations


class I2C_Single_Reg_Model:
    """I2C single register slave behavioral model."""

    STATE_IDLE = 0
    STATE_ADDRESS = 1
    STATE_ACK = 2
    STATE_WRITE_1 = 3
    STATE_WRITE_2 = 4
    STATE_READ_1 = 5
    STATE_READ_2 = 6
    STATE_READ_3 = 7

    def __init__(self, filter_len: int = 4, dev_addr: int = 0x70):
        self.filter_len = filter_len
        self.dev_addr = dev_addr
        self.reset()

    def reset(self):
        self.sda_o = 1
        self.sda_t = 1
        self.data_out = 0
        self._state = self.STATE_IDLE
        self._data_reg = 0
        self._shift_reg = 0
        self._mode_read = 0
        self._bit_count = 7
        self._scl_filter = (1 << self.filter_len) - 1
        self._sda_filter = (1 << self.filter_len) - 1
        self._scl_i_reg = 1
        self._sda_i_reg = 1
        self._last_scl = 1
        self._last_sda = 1

    def cycle(self, rst=0, scl_i=1, sda_i=1, data_in=0, data_latch=0):
        if rst:
            self.reset()
            return

        if data_latch:
            self._data_reg = data_in

        # Filter
        self._scl_filter = ((self._scl_filter << 1) | scl_i) & ((1 << self.filter_len) - 1)
        self._sda_filter = ((self._sda_filter << 1) | sda_i) & ((1 << self.filter_len) - 1)

        if self._scl_filter == (1 << self.filter_len) - 1:
            self._scl_i_reg = 1
        elif self._scl_filter == 0:
            self._scl_i_reg = 0

        if self._sda_filter == (1 << self.filter_len) - 1:
            self._sda_i_reg = 1
        elif self._sda_filter == 0:
            self._sda_i_reg = 0

        self._last_scl = self._scl_i_reg
        self._last_sda = self._sda_i_reg

        scl_posedge = self._scl_i_reg and not self._last_scl
        scl_negedge = not self._scl_i_reg and self._last_scl
        sda_posedge = self._sda_i_reg and not self._last_sda
        sda_negedge = not self._sda_i_reg and self._last_sda
        start_bit = sda_negedge and self._scl_i_reg
        stop_bit = sda_posedge and self._scl_i_reg

        if start_bit:
            self._sda_o = 1
            self._bit_count = 7
            self._state = self.STATE_ADDRESS
        elif stop_bit:
            self._sda_o = 1
            self._state = self.STATE_IDLE
        elif self._state == self.STATE_IDLE:
            self._sda_o = 1
        elif self._state == self.STATE_ADDRESS:
            if scl_posedge:
                if self._bit_count > 0:
                    self._bit_count -= 1
                    self._shift_reg = ((self._shift_reg << 1) | self._sda_i_reg) & 0xFF
                else:
                    self._mode_read = self._sda_i_reg
                    if (self._shift_reg >> 1) == self.dev_addr:
                        self._state = self.STATE_ACK
                    else:
                        self._state = self.STATE_IDLE
        elif self._state == self.STATE_ACK:
            if scl_negedge:
                self._sda_o = 0
                self._bit_count = 7
                if self._mode_read:
                    self._shift_reg = self._data_reg
                    self._state = self.STATE_READ_1
                else:
                    self._state = self.STATE_WRITE_1
        elif self._state == self.STATE_WRITE_1:
            if scl_negedge:
                self._sda_o = 1
                self._state = self.STATE_WRITE_2
        elif self._state == self.STATE_WRITE_2:
            if scl_posedge:
                self._shift_reg = ((self._shift_reg << 1) | self._sda_i_reg) & 0xFF
                if self._bit_count > 0:
                    self._bit_count -= 1
                else:
                    self._data_reg = self._shift_reg
                    self._state = self.STATE_ACK
        elif self._state == self.STATE_READ_1:
            if scl_negedge:
                self._sda_o = (self._shift_reg >> 7) & 1
                self._shift_reg = ((self._shift_reg << 1) | self._sda_i_reg) & 0xFF
                if self._bit_count > 0:
                    self._bit_count -= 1
                else:
                    self._state = self.STATE_READ_2
        elif self._state == self.STATE_READ_2:
            if scl_negedge:
                self._sda_o = 1
                self._state = self.STATE_READ_3
        elif self._state == self.STATE_READ_3:
            if scl_posedge:
                if self._sda_i_reg:
                    self._state = self.STATE_IDLE
                else:
                    self._bit_count = 7
                    self._shift_reg = self._data_reg
                    self._state = self.STATE_READ_1

        self.sda_o = self._sda_o
        self.sda_t = self._sda_o
        self.data_out = self._data_reg
