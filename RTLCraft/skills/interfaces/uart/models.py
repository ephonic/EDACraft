"""
skills.interfaces.uart.models — UART Behavioral Models

Golden-reference simulators for UART TX/RX.
Used for cycle-accurate comparison against generated RTL.
"""
from __future__ import annotations


class UART_TX_Model:
    """UART transmitter behavioral model."""

    def __init__(self, data_width: int = 8):
        self.data_width = data_width
        self.reset()

    def reset(self):
        self.txd = 1
        self.busy = 0
        self.s_axis_tready = 0
        self._data_reg = 0
        self._prescale_reg = 0
        self._bit_cnt = 0

    def cycle(self, rst=0, s_axis_tvalid=0, s_axis_tdata=0, prescale=1):
        if rst:
            self.reset()
            return

        if self._prescale_reg > 0:
            self.s_axis_tready = 0
            self._prescale_reg -= 1
        elif self._bit_cnt == 0:
            self.s_axis_tready = 1
            self.busy = 0
            if s_axis_tvalid:
                self.s_axis_tready = 0
                self._prescale_reg = (prescale << 3) - 1
                self._bit_cnt = self.data_width + 1
                self._data_reg = (1 << self.data_width) | s_axis_tdata
                self.txd = 0
                self.busy = 1
        else:
            self.s_axis_tready = 0
            self.busy = 1
            if self._bit_cnt > 1:
                self._bit_cnt -= 1
                self._prescale_reg = (prescale << 3) - 1
                self.txd = self._data_reg & 0x1
                self._data_reg >>= 1
            else:
                self._bit_cnt -= 1
                self.txd = 1


class UART_RX_Model:
    """UART receiver behavioral model."""

    def __init__(self, data_width: int = 8):
        self.data_width = data_width
        self.reset()

    def reset(self):
        self.m_axis_tdata = 0
        self.m_axis_tvalid = 0
        self.busy = 0
        self.overrun_error = 0
        self.frame_error = 0
        self._data_reg = 0
        self._prescale_reg = 0
        self._bit_cnt = 0
        self._rxd_reg = 1
        self._valid_reg = 0

    def cycle(self, rst=0, rxd=1, m_axis_tready=0, prescale=1):
        if rst:
            self.reset()
            return

        self.overrun_error = 0
        self.frame_error = 0

        if self._valid_reg and m_axis_tready:
            self._valid_reg = 0
            self.m_axis_tvalid = 0

        self._rxd_reg = rxd

        if self._prescale_reg > 0:
            self._prescale_reg -= 1
        elif self._bit_cnt > 0:
            if self._bit_cnt > self.data_width + 1:
                if self._rxd_reg == 0:
                    self._bit_cnt -= 1
                    self._prescale_reg = (prescale << 3) - 1
                else:
                    self._bit_cnt = 0
                    self._prescale_reg = 0
            elif self._bit_cnt > 1:
                self._bit_cnt -= 1
                self._prescale_reg = (prescale << 3) - 1
                self._data_reg = (self._rxd_reg << (self.data_width - 1)) | (self._data_reg >> 1)
            else:
                self._bit_cnt -= 1
                if self._rxd_reg == 1:
                    self.m_axis_tdata = self._data_reg
                    self.m_axis_tvalid = 1
                    self._valid_reg = 1
                else:
                    self.frame_error = 1
        else:
            self.busy = 0
            if self._rxd_reg == 0:
                self._prescale_reg = (prescale << 2) - 2
                self._bit_cnt = self.data_width + 2
                self._data_reg = 0
                self.busy = 1


def create_testbench():
    """Simple UART loopback testbench."""
    tx = UART_TX_Model()
    rx = UART_RX_Model()

    # Reset
    tx.cycle(rst=1)
    rx.cycle(rst=1)

    # Send byte 0xAB
    byte_to_send = 0xAB
    prescale = 10
    received = []

    for cycle in range(500):
        # TX side
        send_valid = 1 if (cycle == 1) else 0
        tx.cycle(s_axis_tvalid=send_valid, s_axis_tdata=byte_to_send, prescale=prescale)

        # RX side: feed TX output
        rx.cycle(rxd=tx.txd, prescale=prescale)

        if rx.m_axis_tvalid and cycle > 2:
            received.append(rx.m_axis_tdata)
            rx.cycle(rxd=tx.txd, m_axis_tready=1, prescale=prescale)

    print(f"UART loopback test: sent 0x{byte_to_send:02X}, received: {[hex(b) for b in received]}")
    assert received == [byte_to_send], f"Expected [0x{byte_to_send:02X}], got {[hex(b) for b in received]}"
    print("UART loopback test: PASSED")


if __name__ == "__main__":
    create_testbench()
