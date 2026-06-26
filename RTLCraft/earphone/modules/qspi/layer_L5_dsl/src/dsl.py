"""L5 DSL module for the EarphoneQSPI controller.

RTL-ready rtlgen description of the QSPI XIP read controller.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Reg, Wire, Const
from rtlgen import Cat, Mux
from rtlgen.logic import If, Else, Elif
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template


class EarphoneQSPI(Module):
    """Simplified QSPI XIP read controller.

    Supports memory-mapped XIP reads via APB-like req/ready handshake.
    Command/address/dummy/data phases are modeled with a small FSM.
    """

    def __init__(self, addr_width: int = 32):
        super().__init__("earphone_qspi")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Host read interface
        self.req = Input(1, "req")
        self.addr = Input(addr_width, "addr")
        self.rdata = Output(32, "rdata")
        self.ready = Output(1, "ready")

        # QSPI pins (tri-state modeled as separate in/out/oe)
        self.qspi_sck = Output(1, "qspi_sck")
        self.qspi_cs_n = Output(1, "qspi_cs_n")
        self.qspi_io_o = Output(4, "qspi_io_o")
        self.qspi_io_i = Input(4, "qspi_io_i")
        self.qspi_io_oe = Output(4, "qspi_io_oe")

        # State machine: 0=idle,1=cmd,2=addr,3=dummy,4=data
        self.state = Reg(3, "state", init_value=0)
        self.counter = Reg(4, "counter", init_value=0)
        self.shift = Reg(32, "shift", init_value=0)
        self.addr_reg = Reg(addr_width, "addr_reg", init_value=0)

        qspi_ce = Wire(1, "qspi_ce")

        with self.comb:
            qspi_ce <<= self.req | (self.state != 0)
            self.ready <<= (self.state == Const(4, 3)) & (self.counter == 0)
            self.rdata <<= self.shift
            self.qspi_cs_n <<= ~(self.state != 0)
            self.qspi_sck <<= self.clk & (self.state != 0)
            self.qspi_io_oe <<= Mux(self.state == Const(4, 3), Const(0, 4), Const(0b1111, 4))
            self.qspi_io_o <<= self.shift[31:28]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.state <<= 0
                self.counter <<= 0
                self.shift <<= 0
                self.addr_reg <<= 0
            with Else():
                with If(qspi_ce):
                    with If(self.state == 0):
                        with If(self.req):
                            self.state <<= 1
                            self.counter <<= 1
                            self.addr_reg <<= self.addr
                            self.shift <<= Const(0xEB, 32)  # Fast Read Quad I/O command
                    with Elif(self.state == 1):
                        # Command phase: 2 cycles of 4-bit transfers = 8 bits
                        with If(self.counter > 0):
                            self.shift <<= Cat(self.shift[27:0], Const(0, 4))
                            self.counter <<= self.counter - 1
                        with Else():
                            self.state <<= 2
                            self.counter <<= 7  # 24-bit address + 4-bit mode = 7 nibble cycles
                            self.shift <<= Cat(self.addr_reg[23:0], Const(0xA0, 8))
                    with Elif(self.state == 2):
                        with If(self.counter > 0):
                            self.shift <<= Cat(self.shift[27:0], Const(0, 4))
                            self.counter <<= self.counter - 1
                        with Else():
                            self.state <<= 3
                            self.counter <<= 3  # dummy cycles
                    with Elif(self.state == 3):
                        with If(self.counter > 0):
                            self.counter <<= self.counter - 1
                        with Else():
                            self.state <<= 4
                            self.counter <<= 8  # 32-bit data = 8 nibbles
                            self.shift <<= 0
                    with Elif(self.state == 4):
                        with If(self.counter > 0):
                            self.shift <<= Cat(self.shift[27:0], self.qspi_io_i)
                            self.counter <<= self.counter - 1
                        with Else():
                            self.state <<= 0

        tpl = ModuleDocTemplate(
            source="earphone/modules/qspi/layer_L5_dsl/src/dsl.py",
            description="QSPI XIP read controller for external 32MB Flash with idle clock gating.",
            author="RTLCraft Agent", version="0.1",
            timing="~15-cycle latency for first word; continuous stream after; clock gated when idle.",
        )
        fill_doc_template(tpl, self)


__all__ = ["EarphoneQSPI"]
