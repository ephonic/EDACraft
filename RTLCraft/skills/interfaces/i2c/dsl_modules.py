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



class I2C_SINGLE_REG(Module):
    """I2C single register slave with input filtering.

    Reference: ref_rtl/interfaces/i2c/rtl/i2c_single_reg.v
    - 7-bit device address matching (DEV_ADDR parameter)
    - Input glitch filter (FILTER_LEN samples)
    - Supports single byte read/write
    - FSM: IDLE → ADDRESS → ACK → WRITE_1/2 → READ_1/2/3
    """

    def __init__(self, filter_len=4, dev_addr=0x70):
        super().__init__("i2c_single_reg")
        self.FILTER_LEN = Parameter(filter_len, "FILTER_LEN")
        self.DEV_ADDR = Parameter(dev_addr, "DEV_ADDR")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # I2C interface (tri-state style)
        self.scl_i = Input(1, "scl_i")
        self.scl_o = Output(1, "scl_o")
        self.scl_t = Output(1, "scl_t")
        self.sda_i = Input(1, "sda_i")
        self.sda_o = Output(1, "sda_o")
        self.sda_t = Output(1, "sda_t")

        # Data register interface
        self.data_in = Input(8, "data_in")
        self.data_latch = Input(1, "data_latch")
        self.data_out = Output(8, "data_out")

        # State encoding
        STATE_IDLE = 0
        STATE_ADDRESS = 1
        STATE_ACK = 2
        STATE_WRITE_1 = 3
        STATE_WRITE_2 = 4
        STATE_READ_1 = 5
        STATE_READ_2 = 6
        STATE_READ_3 = 7

        # State register
        self._state_reg = Reg(3, "state_reg", init_value=STATE_IDLE)

        # Data registers
        self._data_reg = Reg(8, "data_reg", init_value=0)
        self._shift_reg = Reg(8, "shift_reg", init_value=0)
        self._mode_read_reg = Reg(1, "mode_read_reg", init_value=0)
        self._bit_count_reg = Reg(4, "bit_count_reg", init_value=0)

        # Input filter
        self._scl_i_filter_reg = Reg(filter_len, "scl_i_filter_reg", init_value=(1 << filter_len) - 1)
        self._sda_i_filter_reg = Reg(filter_len, "sda_i_filter_reg", init_value=(1 << filter_len) - 1)

        self._scl_i_reg = Reg(1, "scl_i_reg", init_value=1)
        self._sda_i_reg = Reg(1, "sda_i_reg", init_value=1)
        self._last_scl_i_reg = Reg(1, "last_scl_i_reg", init_value=1)
        self._last_sda_i_reg = Reg(1, "last_sda_i_reg", init_value=1)

        self._sda_o_reg = Reg(1, "sda_o_reg", init_value=1)

        # Edge detection
        self._scl_posedge = Wire(1, "scl_posedge")
        self._scl_negedge = Wire(1, "scl_negedge")
        self._sda_posedge = Wire(1, "sda_posedge")
        self._sda_negedge = Wire(1, "sda_negedge")
        self._start_bit = Wire(1, "start_bit")
        self._stop_bit = Wire(1, "stop_bit")

        with self.comb:
            self.scl_o <<= 1
            self.scl_t <<= 1
            self.sda_o <<= self._sda_o_reg
            self.sda_t <<= self._sda_o_reg
            self.data_out <<= self._data_reg

            self._scl_posedge <<= self._scl_i_reg & ~self._last_scl_i_reg
            self._scl_negedge <<= ~self._scl_i_reg & self._last_scl_i_reg
            self._sda_posedge <<= self._sda_i_reg & ~self._last_sda_i_reg
            self._sda_negedge <<= ~self._sda_i_reg & self._last_sda_i_reg
            self._start_bit <<= self._sda_negedge & self._scl_i_reg
            self._stop_bit <<= self._sda_posedge & self._scl_i_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state_reg <<= STATE_IDLE
                self._sda_o_reg <<= 1
                self._scl_i_filter_reg <<= Const((1 << filter_len) - 1, filter_len)
                self._sda_i_filter_reg <<= Const((1 << filter_len) - 1, filter_len)
                self._scl_i_reg <<= 1
                self._sda_i_reg <<= 1
                self._last_scl_i_reg <<= 1
                self._last_sda_i_reg <<= 1
            with Else():
                # Data latch
                with If(self.data_latch == 1):
                    self._data_reg <<= self.data_in

                # Input filter shift
                self._scl_i_filter_reg <<= Cat(self._scl_i_filter_reg[filter_len - 2:0], self.scl_i)
                self._sda_i_filter_reg <<= Cat(self._sda_i_filter_reg[filter_len - 2:0], self.sda_i)

                # Filter decision
                with If(self._scl_i_filter_reg == Const((1 << filter_len) - 1, filter_len)):
                    self._scl_i_reg <<= 1
                with Else():
                    with If(self._scl_i_filter_reg == Const(0, filter_len)):
                        self._scl_i_reg <<= 0

                with If(self._sda_i_filter_reg == Const((1 << filter_len) - 1, filter_len)):
                    self._sda_i_reg <<= 1
                with Else():
                    with If(self._sda_i_filter_reg == Const(0, filter_len)):
                        self._sda_i_reg <<= 0

                self._last_scl_i_reg <<= self._scl_i_reg
                self._last_sda_i_reg <<= self._sda_i_reg

                # Start/stop detection
                with If(self._start_bit == 1):
                    self._sda_o_reg <<= 1
                    self._bit_count_reg <<= 7
                    self._state_reg <<= STATE_ADDRESS
                with Else():
                    with If(self._stop_bit == 1):
                        self._sda_o_reg <<= 1
                        self._state_reg <<= STATE_IDLE
                    with Else():
                        with Switch(self._state_reg) as sw:
                            with sw.case(STATE_IDLE):
                                self._sda_o_reg <<= 1
                                self._state_reg <<= STATE_IDLE
                            with sw.case(STATE_ADDRESS):
                                self._sda_o_reg <<= 1
                                with If(self._scl_posedge == 1):
                                    with If(self._bit_count_reg > 0):
                                        self._bit_count_reg <<= self._bit_count_reg - 1
                                        self._shift_reg <<= Cat(self._shift_reg[6:0], self._sda_i_reg)
                                        self._state_reg <<= STATE_ADDRESS
                                    with Else():
                                        self._mode_read_reg <<= self._sda_i_reg
                                        with If(self._shift_reg[6:0] == dev_addr):
                                            self._state_reg <<= STATE_ACK
                                        with Else():
                                            self._state_reg <<= STATE_IDLE
                                with Else():
                                    self._state_reg <<= STATE_ADDRESS
                            with sw.case(STATE_ACK):
                                with If(self._scl_negedge == 1):
                                    self._sda_o_reg <<= 0
                                    self._bit_count_reg <<= 7
                                    with If(self._mode_read_reg == 1):
                                        self._shift_reg <<= self._data_reg
                                        self._state_reg <<= STATE_READ_1
                                    with Else():
                                        self._state_reg <<= STATE_WRITE_1
                                with Else():
                                    self._state_reg <<= STATE_ACK
                            with sw.case(STATE_WRITE_1):
                                with If(self._scl_negedge == 1):
                                    self._sda_o_reg <<= 1
                                    self._state_reg <<= STATE_WRITE_2
                                with Else():
                                    self._state_reg <<= STATE_WRITE_1
                            with sw.case(STATE_WRITE_2):
                                self._sda_o_reg <<= 1
                                with If(self._scl_posedge == 1):
                                    self._shift_reg <<= Cat(self._shift_reg[6:0], self._sda_i_reg)
                                    with If(self._bit_count_reg > 0):
                                        self._bit_count_reg <<= self._bit_count_reg - 1
                                        self._state_reg <<= STATE_WRITE_2
                                    with Else():
                                        self._data_reg <<= Cat(self._shift_reg[6:0], self._sda_i_reg)
                                        self._state_reg <<= STATE_ACK
                                with Else():
                                    self._state_reg <<= STATE_WRITE_2
                            with sw.case(STATE_READ_1):
                                with If(self._scl_negedge == 1):
                                    self._sda_o_reg <<= self._shift_reg[7]
                                    self._shift_reg <<= Cat(self._shift_reg[6:0], self._sda_i_reg)
                                    with If(self._bit_count_reg > 0):
                                        self._bit_count_reg <<= self._bit_count_reg - 1
                                        self._state_reg <<= STATE_READ_1
                                    with Else():
                                        self._state_reg <<= STATE_READ_2
                                with Else():
                                    self._state_reg <<= STATE_READ_1
                            with sw.case(STATE_READ_2):
                                with If(self._scl_negedge == 1):
                                    self._sda_o_reg <<= 1
                                    self._state_reg <<= STATE_READ_3
                                with Else():
                                    self._state_reg <<= STATE_READ_2
                            with sw.case(STATE_READ_3):
                                with If(self._scl_posedge == 1):
                                    with If(self._sda_i_reg == 1):
                                        self._state_reg <<= STATE_IDLE
                                    with Else():
                                        self._bit_count_reg <<= 7
                                        self._shift_reg <<= self._data_reg
                                        self._state_reg <<= STATE_READ_1
                                with Else():
                                    self._state_reg <<= STATE_READ_3
                            with sw.default():
                                pass

        tpl = ModuleDocTemplate(
            source="I2C_SINGLE_REG — ref_rtl/interfaces/i2c/rtl/i2c_single_reg.v",
            description="I2C single-byte register slave with input filtering. "
                        f"Dev addr=0x{dev_addr:02x}, filter_len={filter_len}.",
            author="rtlgen agent", version="1.0",
            timing="Registered: input filter + FSM. SCL rate <= clk / (2*filter_len)",
        )
        fill_doc_template(tpl, self)
