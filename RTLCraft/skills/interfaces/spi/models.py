"""skills.interfaces.spi.models — SPI Behavioral Models

Golden-reference simulators for SPI master/slave.
Used for cycle-accurate comparison against generated RTL.
"""
from __future__ import annotations


class SPIModuleModel:
    """SPI master/slave core behavioral model."""

    SPI_STATUS_IDLE = 0
    SPI_STATUS_CYCLE_BITS = 7

    def __init__(self, cpol=0, cpha=0, invert_data_order=0, spi_master=1, spi_word_len=8):
        self.CPOL = cpol
        self.CPHA = cpha
        self.INVERT_DATA_ORDER = invert_data_order
        self.SPI_MASTER = spi_master
        self.SPI_WORD_LEN = spi_word_len
        self.reset()

    def reset(self):
        self.is_ready = 1
        self.processing_word = 0
        self.sclk_out = self.CPOL
        self.ss_out = 1
        self.mosi = 0
        self.data_word_recv = 0
        self._activate_ss = 0
        self._activate_sclk = 0
        self._status_ignore_first_edge = 0
        self._data_word_recv_reg = 0
        self._bit_counter = 0 if self.INVERT_DATA_ORDER else (self.SPI_WORD_LEN - 1)
        self._spi_status = self.SPI_STATUS_IDLE
        self._last_sclk = 0

    def cycle(self, rst=0, sclk_in=0, ss_in=1, miso=0, data_word_send=0, process_next_word=0):
        if rst:
            self.reset()
            return

        rising = (sclk_in == 1) and (self._last_sclk == 0)
        falling = (sclk_in == 0) and (self._last_sclk == 1)

        if self.CPHA:
            delay_pol = rising if self.CPOL else falling
            get_number_edge = rising if self.CPOL else falling
            switch_number_edge = falling if self.CPOL else rising
        else:
            delay_pol = bool(sclk_in) if self.CPOL else (not bool(sclk_in))
            get_number_edge = falling if self.CPOL else rising
            switch_number_edge = rising if self.CPOL else falling

        # SS selection
        ss = self.ss_out if self.SPI_MASTER else ss_in

        # Update outputs from state (before sequential update)
        self.ss_out = 0 if self._activate_ss else 1
        self.sclk_out = sclk_in if self._activate_sclk else self.CPOL
        self.mosi = ((data_word_send >> self._bit_counter) & 1) if self._activate_ss else 0
        self.processing_word = 0 if (self._spi_status == self.SPI_STATUS_IDLE) else 1
        self.data_word_recv = self._data_word_recv_reg

        # Sequential logic
        if self._spi_status == self.SPI_STATUS_IDLE:
            if process_next_word and delay_pol:
                self._status_ignore_first_edge = 0
                self._activate_ss = 1
                self._activate_sclk = 1
                self._spi_status = self.SPI_STATUS_CYCLE_BITS
        elif self._spi_status == self.SPI_STATUS_CYCLE_BITS:
            if not ss:
                if get_number_edge:
                    mask = 1 << self._bit_counter
                    self._data_word_recv_reg = (self._data_word_recv_reg & ~mask) | (miso << self._bit_counter)
                if switch_number_edge:
                    if self.CPHA and not self._status_ignore_first_edge:
                        self._status_ignore_first_edge = 1
                    else:
                        done = (self._bit_counter == (self.SPI_WORD_LEN - 1)) if self.INVERT_DATA_ORDER else (self._bit_counter == 0)
                        if done:
                            self._activate_ss = 0
                            self._activate_sclk = 0
                            self._bit_counter = 0 if self.INVERT_DATA_ORDER else (self.SPI_WORD_LEN - 1)
                            self._spi_status = self.SPI_STATUS_IDLE
                        else:
                            self._bit_counter = self._bit_counter + 1 if self.INVERT_DATA_ORDER else self._bit_counter - 1

        self._last_sclk = sclk_in


class SPIClockDividerModel:
    """SPI clock divider behavioral model."""

    def __init__(self, div_n=4):
        self.DIV_N = div_n
        self.reset()

    def reset(self):
        self.clk_out = 0
        self.is_ready = 1
        self._divcounter = 0

    def cycle(self, rst=0):
        if rst:
            self.reset()
            return
        self._divcounter = (self._divcounter + 1) & ((1 << self.DIV_N) - 1)
        self.clk_out = (self._divcounter >> (self.DIV_N - 1)) & 1


class SPITopModel:
    """SPI top-level wrapper behavioral model (divider + core)."""

    def __init__(self, cpol=0, cpha=0, invert_data_order=0, spi_master=1, spi_word_len=8, clk_div_n=4):
        self.core = SPIModuleModel(cpol, cpha, invert_data_order, spi_master, spi_word_len)
        self.divider = SPIClockDividerModel(clk_div_n)
        self.SPI_MASTER = spi_master
        self.reset()

    def reset(self):
        self.core.reset()
        self.divider.reset()
        self.sclk = self.core.CPOL
        self.ss = 1
        self.mosi = 0
        self.data_word_recv = 0
        self.processing_word = 0
        self.is_ready = 0

    def cycle(self, rst=0, sclk=0, ss=1, miso=0, data_word_send=0, process_next_word=0):
        self.divider.cycle(rst)
        sclk_in = self.divider.clk_out if self.SPI_MASTER else sclk
        self.core.cycle(rst, sclk_in, ss, miso, data_word_send, process_next_word)
        self.sclk = self.core.sclk_out
        self.ss = self.core.ss_out
        self.mosi = self.core.mosi
        self.data_word_recv = self.core.data_word_recv
        self.processing_word = self.core.processing_word
        self.is_ready = self.core.is_ready & self.divider.is_ready if self.SPI_MASTER else self.core.is_ready


def create_testbench():
    """Simple SPI master→slave loopback testbench."""
    master = SPITopModel(cpol=0, cpha=0, spi_master=1, spi_word_len=8, clk_div_n=2)
    slave = SPITopModel(cpol=0, cpha=0, spi_master=0, spi_word_len=8, clk_div_n=2)

    master.reset()
    slave.reset()

    byte_to_send = 0xAB
    received = []

    master_proc = 0
    slave_proc = 0

    for cycle in range(200):
        # Pulse process_next_word when not processing
        if not master.processing_word and cycle >= 5:
            master_proc = 1
        elif master.processing_word and master_proc:
            master_proc = 0

        if not slave.processing_word and cycle >= 5:
            slave_proc = 1
        elif slave.processing_word and slave_proc:
            slave_proc = 0

        master.cycle(
            rst=0,
            process_next_word=master_proc,
            data_word_send=byte_to_send,
            miso=slave.mosi,
        )

        slave.cycle(
            rst=0,
            sclk=master.sclk,
            ss=master.ss,
            miso=master.mosi,
            process_next_word=slave_proc,
            data_word_send=byte_to_send,
        )

        if not master.processing_word and cycle > 10:
            received.append(master.data_word_recv)
            break

    if received:
        print(f"SPI loopback test: sent 0x{byte_to_send:02X}, received: 0x{received[0]:02X}")
        assert received[0] == byte_to_send, f"Expected 0x{byte_to_send:02X}, got 0x{received[0]:02X}"
        print("SPI loopback test: PASSED")
    else:
        print("SPI loopback test: FAILED — no data received")


if __name__ == "__main__":
    create_testbench()
