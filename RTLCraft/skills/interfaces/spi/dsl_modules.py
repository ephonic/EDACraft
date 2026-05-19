"""skills.interfaces.spi.dsl_modules — SPI Master/Slave DSL Modules

Reference: ref_rtl/interfaces/spi/ (verilog_spi by Dr. med. Jan Schiefer)
- LGPL-2.1 licensed open-source SPI implementation
- Supports all 4 SPI modes (CPOL/CPHA)
- Supports configurable word length and inverted data order
- No external IP used

This is a clean-room Python DSL redesign inspired by the reference
Verilog implementation.  Copyright of the original Verilog designs
remains with the original author.
"""
from __future__ import annotations

from rtlgen import (
    Input, Output, Wire, Reg, Module,
    Parameter, LocalParam, VerilogEmitter,
)
from rtlgen.logic import If, Else, Const, Cat, Mux, Switch
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template


# =====================================================================
# Edge Detectors
# =====================================================================

class PosEdgeDetector(Module):
    """Positive-edge detector.

    Generates a one-cycle pulse when a rising edge is detected on `sig`.
    """

    def __init__(self):
        super().__init__("pos_edge_det")
        self.sig = Input(1, "sig")
        self.clk = Input(1, "clk")
        self.pe = Output(1, "pe")

        self._sig_dly = Reg(1, "sig_dly", init_value=0)

        with self.comb:
            self.pe <<= self.sig & ~self._sig_dly

        with self.seq(self.clk):
            self._sig_dly <<= self.sig


class NegEdgeDetector(Module):
    """Negative-edge detector.

    Generates a one-cycle pulse when a falling edge is detected on `sig`.
    """

    def __init__(self):
        super().__init__("neg_edge_det")
        self.sig = Input(1, "sig")
        self.clk = Input(1, "clk")
        self.ne = Output(1, "ne")

        self._sig_dly = Reg(1, "sig_dly", init_value=0)

        with self.comb:
            self.ne <<= ~self.sig & self._sig_dly

        with self.seq(self.clk):
            self._sig_dly <<= self.sig


# =====================================================================
# Clock Divider
# =====================================================================

class SPIClockDivider(Module):
    """Simple clock divider for SPI SCLK generation.

    Divides `clk_in` by 2^DIV_N using a free-running counter.
    Output toggles when the MSB of the counter changes.
    """

    def __init__(self, div_n=4):
        super().__init__("spi_clock_divider")
        self.DIV_N = Parameter(div_n, "DIV_N")

        self.clk_in = Input(1, "clk_in")
        self.rst = Input(1, "rst")
        self.clk_out = Output(1, "clk_out")
        self.is_ready = Output(1, "is_ready")

        self._divcounter = Reg(div_n, "divcounter", init_value=0)
        self._is_ready_reg = Reg(1, "is_ready_reg", init_value=1)

        with self.comb:
            self.clk_out <<= self._divcounter[div_n - 1]
            self.is_ready <<= self._is_ready_reg

        with self.seq(self.clk_in, self.rst):
            with If(self.rst == 1):
                self._divcounter <<= 0
                self._is_ready_reg <<= 1
            with Else():
                self._divcounter <<= self._divcounter + 1


# =====================================================================
# SPI Core Module (Master/Slave)
# =====================================================================

class SPIModule(Module):
    """SPI master/slave core with full CPOL/CPHA support.

    Parameters:
        CPOL (int): Clock polarity (0=idle low, 1=idle high).
        CPHA (int): Clock phase (0=sample on first edge, 1=sample on second edge).
        INVERT_DATA_ORDER (int): 0=MSB first, 1=LSB first.
        SPI_MASTER (int): 1=master mode, 0=slave mode.
        SPI_WORD_LEN (int): Word length in bits (default 8).

    Reference: verilog_spi by Dr. med. Jan Schiefer
    """

    SPI_STATUS_IDLE = 0
    SPI_STATUS_CYCLE_BITS = 7

    def __init__(self, cpol=0, cpha=0, invert_data_order=0, spi_master=1, spi_word_len=8):
        super().__init__("spi_module")
        self.CPOL = Parameter(cpol, "CPOL")
        self.CPHA = Parameter(cpha, "CPHA")
        self.INVERT_DATA_ORDER = Parameter(invert_data_order, "INVERT_DATA_ORDER")
        self.SPI_MASTER = Parameter(spi_master, "SPI_MASTER")
        self.SPI_WORD_LEN = Parameter(spi_word_len, "SPI_WORD_LEN")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # SPI clock interface
        self.sclk_out = Output(1, "sclk_out")
        self.sclk_in = Input(1, "sclk_in")

        # Chip-select interface
        self.ss_out = Output(1, "ss_out")
        self.ss_in = Input(1, "ss_in")

        # Data interface
        self.mosi = Output(1, "mosi")
        self.miso = Input(1, "miso")

        # Data word interface
        self.data_word_send = Input(spi_word_len, "data_word_send")
        self.data_word_recv = Output(spi_word_len, "data_word_recv")

        # Control / status
        self.process_next_word = Input(1, "process_next_word")
        self.processing_word = Output(1, "processing_word")
        self.is_ready = Output(1, "is_ready")

        # -----------------------------------------------------------------
        # Internal signals
        # -----------------------------------------------------------------
        self._is_ready_reg = Reg(1, "is_ready_reg", init_value=1)
        self._activate_ss = Reg(1, "activate_ss", init_value=0)
        self._activate_sclk = Reg(1, "activate_sclk", init_value=0)
        self._status_ignore_first_edge = Reg(1, "status_ignore_first_edge", init_value=0)

        self._data_word_recv_reg = Reg(spi_word_len, "data_word_recv_reg", init_value=0)

        # Bit counter needs enough bits for [0, SPI_WORD_LEN-1]
        counter_w = (spi_word_len - 1).bit_length()
        self._bit_counter = Reg(counter_w, "bit_counter", init_value=(spi_word_len - 1))

        self._spi_status = Reg(3, "spi_status", init_value=self.SPI_STATUS_IDLE)

        # Edge detection wires
        self._rising_sclk_edge = Wire(1, "rising_sclk_edge")
        self._falling_sclk_edge = Wire(1, "falling_sclk_edge")

        # Delayed polarity / edge selection
        self._delay_pol = Wire(1, "delay_pol")
        self._get_number_edge = Wire(1, "get_number_edge")
        self._switch_number_edge = Wire(1, "switch_number_edge")

        self._ss = Wire(1, "ss")

        # -----------------------------------------------------------------
        # Combinational logic
        # -----------------------------------------------------------------
        with self.comb:
            self.is_ready <<= self._is_ready_reg
            self.data_word_recv <<= self._data_word_recv_reg
            self.processing_word <<= Mux(
                self._spi_status == self.SPI_STATUS_IDLE,
                Const(0, 1), Const(1, 1)
            )

            # Master mode: drive SCLK and SS
            self.sclk_out <<= Mux(
                self._activate_sclk,
                self.sclk_in,
                self.CPOL
            )
            self.ss_out <<= Mux(
                self._activate_ss,
                Const(0, 1), Const(1, 1)
            )

            # MOSI output
            self.mosi <<= Mux(
                self._activate_ss,
                self.data_word_send[self._bit_counter],
                Const(0, 1)
            )

            # SS selection
            self._ss <<= Mux(
                self.SPI_MASTER == 1,
                self.ss_out, self.ss_in
            )

            # delay_pol = CPHA ? (CPOL ? rising : falling) : (CPOL ? sclk_in : ~sclk_in)
            self._delay_pol <<= Mux(
                self.CPHA == 1,
                Mux(self.CPOL == 1, self._rising_sclk_edge, self._falling_sclk_edge),
                Mux(self.CPOL == 1, self.sclk_in, ~self.sclk_in)
            )

            # get_number_edge = CPHA ? (CPOL ? rising : falling) : (CPOL ? falling : rising)
            self._get_number_edge <<= Mux(
                self.CPHA == 1,
                Mux(self.CPOL == 1, self._rising_sclk_edge, self._falling_sclk_edge),
                Mux(self.CPOL == 1, self._falling_sclk_edge, self._rising_sclk_edge)
            )

            # switch_number_edge = CPHA ? (CPOL ? falling : rising) : (CPOL ? rising : falling)
            self._switch_number_edge <<= Mux(
                self.CPHA == 1,
                Mux(self.CPOL == 1, self._falling_sclk_edge, self._rising_sclk_edge),
                Mux(self.CPOL == 1, self._rising_sclk_edge, self._falling_sclk_edge)
            )

        # -----------------------------------------------------------------
        # Edge detector instances
        # -----------------------------------------------------------------
        pos_det = PosEdgeDetector()
        self.instantiate(pos_det, "pos_det", port_map={
            "sig": self.sclk_in,
            "clk": self.clk,
            "pe": self._rising_sclk_edge,
        })

        neg_det = NegEdgeDetector()
        self.instantiate(neg_det, "neg_det", port_map={
            "sig": self.sclk_in,
            "clk": self.clk,
            "ne": self._falling_sclk_edge,
        })

        # -----------------------------------------------------------------
        # Sequential logic — FSM
        # -----------------------------------------------------------------
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._activate_ss <<= 0
                self._activate_sclk <<= 0
                self._bit_counter <<= Mux(
                    self.INVERT_DATA_ORDER == 1,
                    Const(0, counter_w),
                    Const(spi_word_len - 1, counter_w)
                )
                self._status_ignore_first_edge <<= 0
                self._spi_status <<= self.SPI_STATUS_IDLE
                self._is_ready_reg <<= 1
            with Else():
                with Switch(self._spi_status) as sw:
                    with sw.case(Const(self.SPI_STATUS_IDLE, 3)):
                        with If(self.process_next_word & self._delay_pol):
                            self._status_ignore_first_edge <<= 0
                            self._activate_ss <<= 1
                            self._activate_sclk <<= 1
                            self._spi_status <<= self.SPI_STATUS_CYCLE_BITS
                    with sw.case(Const(self.SPI_STATUS_CYCLE_BITS, 3)):
                        with If(~self._ss):
                            # Sample MISO on get_number_edge
                            with If(self._get_number_edge):
                                self._data_word_recv_reg[self._bit_counter] <<= self.miso

                            # Switch bit on switch_number_edge
                            with If(self._switch_number_edge):
                                with If((self.CPHA == 1) & ~self._status_ignore_first_edge):
                                    self._status_ignore_first_edge <<= 1
                                with Else():
                                    with If(Mux(
                                        self.INVERT_DATA_ORDER == 1,
                                        self._bit_counter == (spi_word_len - 1),
                                        self._bit_counter == 0
                                    )):
                                        # Word complete
                                        self._activate_ss <<= 0
                                        self._activate_sclk <<= 0
                                        self._bit_counter <<= Mux(
                                            self.INVERT_DATA_ORDER == 1,
                                            Const(0, counter_w),
                                            Const(spi_word_len - 1, counter_w)
                                        )
                                        self._spi_status <<= self.SPI_STATUS_IDLE
                                    with Else():
                                        self._bit_counter <<= Mux(
                                            self.INVERT_DATA_ORDER == 1,
                                            self._bit_counter + 1,
                                            self._bit_counter - 1
                                        )


# =====================================================================
# SPI Top-Level Wrapper
# =====================================================================

class SPITop(Module):
    """SPI top-level with clock divider and core.

    Provides a complete SPI master/slave interface with an internal
    clock divider for generating the SPI SCLK from the system clock.
    """

    def __init__(self, cpol=0, cpha=0, invert_data_order=0, spi_master=1,
                 spi_word_len=8, clk_div_n=4):
        super().__init__("spi_top")
        self.CPOL = Parameter(cpol, "CPOL")
        self.CPHA = Parameter(cpha, "CPHA")
        self.INVERT_DATA_ORDER = Parameter(invert_data_order, "INVERT_DATA_ORDER")
        self.SPI_MASTER = Parameter(spi_master, "SPI_MASTER")
        self.SPI_WORD_LEN = Parameter(spi_word_len, "SPI_WORD_LEN")
        self.CLK_DIV_N = Parameter(clk_div_n, "CLK_DIV_N")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # External SPI pins
        self.sclk = Output(1, "sclk")
        self.ss = Output(1, "ss")
        self.mosi = Output(1, "mosi")
        self.miso = Input(1, "miso")

        # Data word interface
        self.data_word_send = Input(spi_word_len, "data_word_send")
        self.data_word_recv = Output(spi_word_len, "data_word_recv")

        # Control / status
        self.process_next_word = Input(1, "process_next_word")
        self.processing_word = Output(1, "processing_word")
        self.is_ready = Output(1, "is_ready")

        # Internal wires
        self._divided_clk = Wire(1, "divided_clk")
        self._divider_ready = Wire(1, "divider_ready")

        # Clock divider (only used in master mode)
        clk_div = SPIClockDivider(div_n=clk_div_n)
        self.instantiate(clk_div, "clk_div", port_map={
            "clk_in": self.clk,
            "rst": self.rst,
            "clk_out": self._divided_clk,
            "is_ready": self._divider_ready,
        })

        # SPI core
        spi = SPIModule(
            cpol=cpol, cpha=cpha,
            invert_data_order=invert_data_order,
            spi_master=spi_master,
            spi_word_len=spi_word_len
        )

        # sclk_in selection: master uses divided clock, slave uses external sclk
        sclk_in_sel = Wire(1, "sclk_in_sel")
        spi_is_ready = Wire(1, "spi_is_ready")

        with self.comb:
            sclk_in_sel <<= Mux(self.SPI_MASTER == 1, self._divided_clk, self.sclk)
            self.is_ready <<= Mux(
                self.SPI_MASTER == 1,
                spi_is_ready & self._divider_ready,
                spi_is_ready
            )

        self.instantiate(spi, "spi_core", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "sclk_in": sclk_in_sel,
            "ss_in": self.ss,
            "miso": self.miso,
            "data_word_send": self.data_word_send,
            "process_next_word": self.process_next_word,
            "sclk_out": self.sclk,
            "ss_out": self.ss,
            "mosi": self.mosi,
            "data_word_recv": self.data_word_recv,
            "processing_word": self.processing_word,
            "is_ready": spi_is_ready,
        })


# =====================================================================
# Verilog emission helper
# =====================================================================

def emit_spi_modules():
    """Emit all SPI modules to generated Verilog files."""
    from rtlgen import VerilogEmitter

    modules = [
        PosEdgeDetector(),
        NegEdgeDetector(),
        SPIClockDivider(div_n=4),
        SPIModule(cpol=0, cpha=0, spi_master=1, spi_word_len=8),
        SPITop(cpol=0, cpha=0, spi_master=1, spi_word_len=8, clk_div_n=4),
    ]

    for m in modules:
        tpl = ModuleDocTemplate(
            source="skills.interfaces.spi — Python DSL redesign",
            description=f"{m.name} — SPI interface module",
            author="RTLCraft agent",
            version="1.0",
            timing="Synchronous logic driven by system clock.",
        )
        fill_doc_template(tpl, m)
        verilog = VerilogEmitter().emit(m)
        print(f"// ===== {m.name} =====")
        print(verilog)
        print()


if __name__ == "__main__":
    emit_spi_modules()
