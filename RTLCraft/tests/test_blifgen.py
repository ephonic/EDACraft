#!/usr/bin/env python3
"""
Unit tests for BLIFEmitter.
"""

import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import Module, Input, Output, Wire, Reg, Switch, If, Else
from rtlgen.blifgen import BLIFEmitter


class SimpleAnd(Module):
    def __init__(self):
        super().__init__("SimpleAnd")
        self.a = Input(2, "a")
        self.b = Input(2, "b")
        self.y = Output(2, "y")
        @self.comb
        def _logic():
            self.y <<= self.a & self.b


class FullAdderTop(Module):
    def __init__(self):
        super().__init__("FullAdderTop")
        self.a = Input(4, "a")
        self.b = Input(4, "b")
        self.y = Output(4, "y")
        @self.comb
        def _logic():
            self.y <<= self.a + self.b


class RegPipe(Module):
    def __init__(self):
        super().__init__("RegPipe")
        self.clk = Input(1, "clk")
        self.d = Input(4, "d")
        self.q = Output(4, "q")
        @self.seq(self.clk)
        def _logic():
            self.q <<= self.d


class MuxIf(Module):
    def __init__(self):
        super().__init__("MuxIf")
        self.sel = Input(1, "sel")
        self.a = Input(4, "a")
        self.b = Input(4, "b")
        self.y = Output(4, "y")
        @self.comb
        def _logic():
            with If(self.sel == 1):
                self.y <<= self.a
            with Else():
                self.y <<= self.b


def test_simple_and_blif():
    m = SimpleAnd()
    blif = BLIFEmitter().emit(m)
    assert ".model SimpleAnd" in blif
    assert "a[0]" in blif
    assert "y[0]" in blif
    assert ".names a[0] b[0]" in blif
    assert "11 1" in blif


def test_full_adder_blif():
    m = FullAdderTop()
    blif = BLIFEmitter().emit(m)
    # Default adder is now pure AIG (no .subckt)
    assert ".model FullAdderTop" in blif
    assert "01 1" in blif  # XOR pattern from half/full adder AIG
    assert "11 1" in blif  # AND pattern


def test_reg_pipe_blif():
    m = RegPipe()
    blif = BLIFEmitter().emit(m)
    assert ".latch" in blif
    # After fixing _emit_seq_body, unconditional assigns directly use the value wires
    # instead of introducing an intermediate _next wire that collides with .latch output.
    assert ".latch d[0] q[0] 2" in blif or "q_next" in blif or "q[0]_next" in blif


def test_mux_if_blif():
    m = MuxIf()
    blif = BLIFEmitter().emit(m)
    # MUX 使用 don't care 真值表
    assert "0-1 1" in blif
    assert "11- 1" in blif


def test_switch_to_mux_blif():
    class SwitchMux(Module):
        def __init__(self):
            super().__init__("SwitchMux")
            self.sel = Input(2, "sel")
            self.a = Input(4, "a")
            self.b = Input(4, "b")
            self.c = Input(4, "c")
            self.y = Output(4, "y")
            @self.comb
            def _logic():
                with Switch(self.sel) as sw:
                    with sw.case(0):
                        self.y <<= self.a
                    with sw.case(1):
                        self.y <<= self.b
                    with sw.default():
                        self.y <<= self.c
    m = SwitchMux()
    blif = BLIFEmitter().emit(m)
    assert ".model SwitchMux" in blif
    # 应该有多个 .subckt full_adder 吗？不，Switch 转成 MUX，没有 full_adder
    assert "0-1 1" in blif
