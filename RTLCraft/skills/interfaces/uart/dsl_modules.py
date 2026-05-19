"""dsl_modules — DSL Reference Implementations

Extracted from design_interfaces.py.
"""
from __future__ import annotations

from rtlgen import (
    Input, Output, Wire, Reg, Module, Vector, Array, VerilogEmitter,
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, HandshakeSpec, QueueSpec,
    ArchSimulator, ArchSkeletonGenerator,
    BehavioralSpec, StrategySpec, DecompositionResult,
    Memory, Parameter, LocalParam,
)
from rtlgen.logic import If, Else, Elif, When, Otherwise, Const, Cat, Mux, Switch, Rep, ForGen
from rtlgen.lib import SyncFIFO
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template



class UART_TX(Module):
    """UART transmitter with AXI-Stream input interface.

    Reference: ref_rtl/interfaces/uart/rtl/uart_tx.v
    - Receives bytes via s_axis_tdata/tvalid/tready handshake
    - Transmits UART frame: start(0) + data[0..N-1] + stop(1)
    - Baud rate = clk_freq / (prescale * 8)
    - busy=1 while transmitting
    """

    def __init__(self, data_width=8):
        super().__init__("uart_tx")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input
        self.s_axis_tdata = Input(data_width, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")

        # UART output
        self.txd = Output(1, "txd")

        # Status
        self.busy = Output(1, "busy")

        # Configuration
        self.prescale = Input(16, "prescale")

        # State registers (power-on init mimics reference's = 0)
        self._s_axis_tready_reg = Reg(1, "s_axis_tready_reg", init_value=0)
        self._txd_reg = Reg(1, "txd_reg", init_value=1)
        self._busy_reg = Reg(1, "busy_reg", init_value=0)
        self._data_reg = Reg(data_width + 1, "data_reg", init_value=0)
        self._prescale_reg = Reg(19, "prescale_reg", init_value=0)
        self._bit_cnt = Reg(4, "bit_cnt", init_value=0)

        # Combinational outputs
        with self.comb:
            self.s_axis_tready <<= self._s_axis_tready_reg
            self.txd <<= self._txd_reg
            self.busy <<= self._busy_reg

        # Sequential logic
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._s_axis_tready_reg <<= 0
                self._txd_reg <<= 1
                self._prescale_reg <<= 0
                self._bit_cnt <<= 0
                self._busy_reg <<= 0
            with Else():
                with If(self._prescale_reg > 0):
                    self._s_axis_tready_reg <<= 0
                    self._prescale_reg <<= self._prescale_reg - 1
                with Else():
                    with If(self._bit_cnt == 0):
                        self._s_axis_tready_reg <<= 1
                        self._busy_reg <<= 0
                        with If(self.s_axis_tvalid == 1):
                            # Toggle ready to indicate one-cycle accept
                            self._s_axis_tready_reg <<= 0
                            self._prescale_reg <<= (self.prescale << 3) - 1
                            self._bit_cnt <<= data_width + 1
                            self._data_reg <<= Cat(Const(1, 1), self.s_axis_tdata)
                            self._txd_reg <<= 0
                            self._busy_reg <<= 1
                    with Else():
                        with If(self._bit_cnt > 1):
                            self._bit_cnt <<= self._bit_cnt - 1
                            self._prescale_reg <<= (self.prescale << 3) - 1
                            # {data_reg, txd_reg} <= {1'b0, data_reg}
                            self._data_reg <<= Cat(Const(0, 1), self._data_reg[data_width:1])
                            self._txd_reg <<= self._data_reg[0]
                        with Else():  # bit_cnt == 1
                            self._bit_cnt <<= self._bit_cnt - 1
                            self._prescale_reg <<= self.prescale << 3
                            self._txd_reg <<= 1

        tpl = ModuleDocTemplate(
            source="UART_TX — ref_rtl/interfaces/uart/rtl/uart_tx.v",
            description=f"{data_width}-bit UART transmitter with AXI-Stream input. "
                        "Start bit + data + stop bit framing.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-byte latency + (prescale*8) per bit",
        )
        fill_doc_template(tpl, self)


class UART_RX(Module):
    """UART receiver with AXI-Stream output interface.

    Reference: ref_rtl/interfaces/uart/rtl/uart_rx.v
    - Receives UART frame: start(0) + data[0..N-1] + stop(1)
    - Outputs bytes via m_axis_tdata/tvalid/tready handshake
    - overrun_error: new byte received before previous read
    - frame_error: stop bit was 0 (framing error)
    """

    def __init__(self, data_width=8):
        super().__init__("uart_rx")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream output
        self.m_axis_tdata = Output(data_width, "m_axis_tdata")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")

        # UART input
        self.rxd = Input(1, "rxd")

        # Status
        self.busy = Output(1, "busy")
        self.overrun_error = Output(1, "overrun_error")
        self.frame_error = Output(1, "frame_error")

        # Configuration
        self.prescale = Input(16, "prescale")

        # State registers
        self._m_axis_tdata_reg = Reg(data_width, "m_axis_tdata_reg", init_value=0)
        self._m_axis_tvalid_reg = Reg(1, "m_axis_tvalid_reg", init_value=0)
        self._rxd_reg = Reg(1, "rxd_reg", init_value=1)
        self._busy_reg = Reg(1, "busy_reg", init_value=0)
        self._overrun_error_reg = Reg(1, "overrun_error_reg", init_value=0)
        self._frame_error_reg = Reg(1, "frame_error_reg", init_value=0)
        self._data_reg = Reg(data_width, "data_reg", init_value=0)
        self._prescale_reg = Reg(19, "prescale_reg", init_value=0)
        self._bit_cnt = Reg(4, "bit_cnt", init_value=0)

        with self.comb:
            self.m_axis_tdata <<= self._m_axis_tdata_reg
            self.m_axis_tvalid <<= self._m_axis_tvalid_reg
            self.busy <<= self._busy_reg
            self.overrun_error <<= self._overrun_error_reg
            self.frame_error <<= self._frame_error_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._m_axis_tdata_reg <<= 0
                self._m_axis_tvalid_reg <<= 0
                self._rxd_reg <<= 1
                self._prescale_reg <<= 0
                self._bit_cnt <<= 0
                self._busy_reg <<= 0
                self._overrun_error_reg <<= 0
                self._frame_error_reg <<= 0
            with Else():
                self._rxd_reg <<= self.rxd
                self._overrun_error_reg <<= 0
                self._frame_error_reg <<= 0

                with If((self._m_axis_tvalid_reg == 1) & (self.m_axis_tready == 1)):
                    self._m_axis_tvalid_reg <<= 0

                with If(self._prescale_reg > 0):
                    self._prescale_reg <<= self._prescale_reg - 1
                with Else():
                    with If(self._bit_cnt > 0):
                        with If(self._bit_cnt > data_width + 1):
                            # Waiting for start bit to complete sampling
                            with If(self._rxd_reg == 0):
                                self._bit_cnt <<= self._bit_cnt - 1
                                self._prescale_reg <<= (self.prescale << 3) - 1
                            with Else():
                                self._bit_cnt <<= 0
                                self._prescale_reg <<= 0
                        with Else():
                            with If(self._bit_cnt > 1):
                                self._bit_cnt <<= self._bit_cnt - 1
                                self._prescale_reg <<= (self.prescale << 3) - 1
                                # data_reg <= {rxd_reg, data_reg[DATA_WIDTH-1:1]}
                                self._data_reg <<= Cat(self._rxd_reg, self._data_reg[data_width - 1:1])
                            with Else():  # bit_cnt == 1
                                self._bit_cnt <<= self._bit_cnt - 1
                                with If(self._rxd_reg == 1):
                                    self._m_axis_tdata_reg <<= self._data_reg
                                    self._m_axis_tvalid_reg <<= 1
                                    self._overrun_error_reg <<= self._m_axis_tvalid_reg
                                with Else():
                                    self._frame_error_reg <<= 1
                    with Else():
                        self._busy_reg <<= 0
                        with If(self._rxd_reg == 0):
                            self._prescale_reg <<= (self.prescale << 2) - 2
                            self._bit_cnt <<= data_width + 2
                            self._data_reg <<= 0
                            self._busy_reg <<= 1

        tpl = ModuleDocTemplate(
            source="UART_RX — ref_rtl/interfaces/uart/rtl/uart_rx.v",
            description=f"{data_width}-bit UART receiver with AXI-Stream output. "
                        "Overrun and frame error detection.",
            author="rtlgen agent", version="1.0",
            timing="Registered: start-bit detect + (prescale*8) per bit",
        )
        fill_doc_template(tpl, self)


class UART(Module):
    """UART top-level: instantiates uart_tx and uart_rx."""

    def __init__(self, data_width=8):
        super().__init__("uart")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input (to TX)
        self.s_axis_tdata = Input(data_width, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")

        # AXI-Stream output (from RX)
        self.m_axis_tdata = Output(data_width, "m_axis_tdata")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")

        # UART pins
        self.rxd = Input(1, "rxd")
        self.txd = Output(1, "txd")

        # Status
        self.tx_busy = Output(1, "tx_busy")
        self.rx_busy = Output(1, "rx_busy")
        self.rx_overrun_error = Output(1, "rx_overrun_error")
        self.rx_frame_error = Output(1, "rx_frame_error")

        # Configuration
        self.prescale = Input(16, "prescale")

        tx_inst = UART_TX(data_width=data_width)
        self.instantiate(tx_inst, "uart_tx_inst", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "s_axis_tdata": self.s_axis_tdata,
            "s_axis_tvalid": self.s_axis_tvalid,
            "s_axis_tready": self.s_axis_tready,
            "txd": self.txd,
            "busy": self.tx_busy,
            "prescale": self.prescale,
        })

        rx_inst = UART_RX(data_width=data_width)
        self.instantiate(rx_inst, "uart_rx_inst", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "m_axis_tdata": self.m_axis_tdata,
            "m_axis_tvalid": self.m_axis_tvalid,
            "m_axis_tready": self.m_axis_tready,
            "rxd": self.rxd,
            "busy": self.rx_busy,
            "overrun_error": self.rx_overrun_error,
            "frame_error": self.rx_frame_error,
            "prescale": self.prescale,
        })

        tpl = ModuleDocTemplate(
            source="UART — ref_rtl/interfaces/uart/rtl/uart.v",
            description="UART top-level: TX + RX with AXI-Stream interfaces",
            author="rtlgen agent", version="1.0",
            timing="Pass-through to tx/rx submodules",
        )
        fill_doc_template(tpl, self)
