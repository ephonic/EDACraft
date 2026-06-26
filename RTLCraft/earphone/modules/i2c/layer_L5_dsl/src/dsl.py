"""L5 DSL module for the EarphoneI2C controller.

RTL-ready rtlgen description of the APB I2C master byte controller.
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


class EarphoneI2C(Module):
    """Simplified APB I2C master controller.

    Supports single-byte write/read transactions with 7-bit slave address.
    """

    def __init__(self):
        super().__init__("earphone_i2c")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # APB slave interface
        self.paddr = Input(12, "paddr")
        self.pwdata = Input(32, "pwdata")
        self.prdata = Output(32, "prdata")
        self.pwrite = Input(1, "pwrite")
        self.psel = Input(1, "psel")
        self.penable = Input(1, "penable")
        self.pready = Output(1, "pready")

        # I2C pins (open-drain, oe active low)
        self.scl_i = Input(1, "scl_i")
        self.scl_o = Output(1, "scl_o")
        self.scl_oe = Output(1, "scl_oe")
        self.sda_i = Input(1, "sda_i")
        self.sda_o = Output(1, "sda_o")
        self.sda_oe = Output(1, "sda_oe")

        # Registers
        self.ctrl = Reg(32, "ctrl", init_value=0)      # start, addr, rw
        self.data = Reg(32, "data", init_value=0)      # tx/rx byte
        self.status = Reg(32, "status", init_value=0)  # busy, done, ack

        # Bit-level FSM
        self.state = Reg(4, "state", init_value=0)
        self.bit_cnt = Reg(4, "bit_cnt", init_value=0)
        self.shift = Reg(9, "shift", init_value=0)
        self.scl_reg = Reg(1, "scl_reg", init_value=1)
        self.sda_reg = Reg(1, "sda_reg", init_value=1)
        self.sent_data = Reg(1, "sent_data", init_value=0)

        i2c_ce = Wire(1, "i2c_ce")

        with self.comb:
            i2c_ce <<= (self.state != 0) | self.ctrl[0] | (self.psel & self.penable)
            self.prdata <<= Mux(self.paddr[3:0] == 0, self.ctrl,
                          Mux(self.paddr[3:0] == 4, self.data,
                          self.status))
            self.pready <<= self.psel & self.penable
            self.scl_o <<= self.scl_reg
            self.scl_oe <<= ~((self.state != 0) | (self.ctrl[0] == 1))
            self.sda_o <<= self.sda_reg
            self.sda_oe <<= ~((self.state != 0) & (self.state != 11))  # high-z during ack/read

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.ctrl <<= 0
                self.data <<= 0
                self.status <<= 0
                self.state <<= 0
                self.bit_cnt <<= 0
                self.shift <<= 0
                self.scl_reg <<= 1
                self.sda_reg <<= 1
                self.sent_data <<= 0
            with Else():
                with If(i2c_ce):
                    # APB register writes
                    with If(self.psel & self.penable & self.pwrite):
                        with If(self.paddr[3:0] == 0):
                            self.ctrl <<= self.pwdata
                        with Elif(self.paddr[3:0] == 4):
                            self.data <<= self.pwdata

                    # State machine
                    with If(self.state == 0):
                        self.sent_data <<= 0
                        with If(self.ctrl[0]):
                            self.status <<= 0
                            self.state <<= 1
                            self.ctrl[0] <<= 0
                            self.bit_cnt <<= 8
                            addr = (self.ctrl[15:8] << 1) | self.ctrl[1]
                            self.shift <<= Cat(addr, Const(1, 1))
                    with Elif(self.state == 1):
                        # START condition
                        self.sda_reg <<= 0
                        self.state <<= 2
                    with Elif(self.state == 2):
                        # Shift out address+R/W
                        self.scl_reg <<= 0
                        self.sda_reg <<= self.shift[8]
                        self.state <<= 3
                    with Elif(self.state == 3):
                        self.scl_reg <<= 1
                        self.state <<= 4
                    with Elif(self.state == 4):
                        self.shift <<= Cat(self.shift[7:0], Const(0, 1))
                        self.scl_reg <<= 0
                        with If(self.bit_cnt > 0):
                            self.bit_cnt <<= self.bit_cnt - 1
                            self.state <<= 3
                        with Else():
                            self.state <<= 5
                            self.bit_cnt <<= 8
                    with Elif(self.state == 5):
                        # ACK bit
                        self.scl_reg <<= 1
                        self.state <<= 6
                    with Elif(self.state == 6):
                        self.status[2] <<= self.sda_i  # ack status
                        self.scl_reg <<= 0
                        with If(self.ctrl[1] == 0):
                            # Write direction
                            with If(self.sent_data):
                                # Data byte already sent; generate STOP
                                self.state <<= 12
                            with Else():
                                # Load data byte to send
                                self.shift <<= Cat(self.data[7:0], Const(1, 1))
                                self.sent_data <<= 1
                                self.state <<= 7
                        with Else():
                            # Read byte
                            self.shift <<= 0
                            self.state <<= 9
                    with Elif(self.state == 7):
                        # Write byte
                        self.sda_reg <<= self.shift[8]
                        self.state <<= 8
                    with Elif(self.state == 8):
                        self.scl_reg <<= 1
                        self.state <<= 4
                    with Elif(self.state == 9):
                        # Read byte
                        self.sda_reg <<= 1
                        self.state <<= 10
                    with Elif(self.state == 10):
                        self.scl_reg <<= 1
                        self.state <<= 11
                    with Elif(self.state == 11):
                        self.shift <<= Cat(self.shift[7:0], self.sda_i)
                        self.scl_reg <<= 0
                        with If(self.bit_cnt > 0):
                            self.bit_cnt <<= self.bit_cnt - 1
                            self.state <<= 10
                        with Else():
                            self.data[7:0] <<= self.shift[8:1]
                            self.state <<= 12
                    with Elif(self.state == 12):
                        # STOP condition
                        self.sda_reg <<= 0
                        self.scl_reg <<= 1
                        self.state <<= 13
                    with Elif(self.state == 13):
                        self.sda_reg <<= 1
                        self.status[0] <<= 1  # done
                        self.state <<= 0

        tpl = ModuleDocTemplate(
            source="earphone/modules/i2c/layer_L5_dsl/src/dsl.py",
            description="APB I2C master byte controller with idle clock gating.",
            author="RTLCraft Agent", version="0.1",
            timing="~36 cycles per byte write; clock gated between transactions.",
        )
        fill_doc_template(tpl, self)


__all__ = ["EarphoneI2C"]
