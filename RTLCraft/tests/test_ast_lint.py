"""Tests for Module.lint() AST-level rules."""

import pytest
import sys

sys.path.insert(0, "/home/yangfan/EDAClaw/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else


# ---------------------------------------------------------------------------
# Rule: seq_output_assign
# ---------------------------------------------------------------------------
def test_seq_output_assign_detected():
    """Output assigned directly in @seq should trigger SeqOutputAssign."""

    class BadModule(Module):
        def __init__(self):
            super().__init__("BadModule")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.out = Output(8, "out")

            @self.seq(self.clk, self.rst)
            def _bad():
                with If(self.rst == 1):
                    self.out <<= 0
                with Else():
                    self.out <<= self.out + 1

    dut = BadModule()
    violations = dut.lint(rules=["seq_output_assign"])
    assert any("SeqOutputAssign" in v for v in violations)
    assert any("out" in v for v in violations)


def test_seq_output_assign_fixed():
    """Using internal Reg + @comb forwarding should NOT trigger SeqOutputAssign."""

    class GoodModule(Module):
        def __init__(self):
            super().__init__("GoodModule")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.out = Output(8, "out")

            self.out_reg = Reg(8, "out_reg")

            @self.seq(self.clk, self.rst)
            def _seq():
                with If(self.rst == 1):
                    self.out_reg <<= 0
                with Else():
                    self.out_reg <<= self.out_reg + 1

            @self.comb
            def _output():
                self.out <<= self.out_reg

    dut = GoodModule()
    violations = dut.lint(rules=["seq_output_assign"])
    assert not any("SeqOutputAssign" in v for v in violations)


# ---------------------------------------------------------------------------
# Rule: unregistered_output with comb forwarding
# ---------------------------------------------------------------------------
def test_unregistered_output_with_comb_forwarding():
    """Output driven by @comb from a Reg should NOT trigger UnregisteredOutput."""

    class GoodModule(Module):
        def __init__(self):
            super().__init__("GoodModule")
            self.clk = Input(1, "clk")
            self.rst = Input(1, "rst")
            self.out = Output(8, "out")

            self.out_reg = Reg(8, "out_reg")

            @self.seq(self.clk, self.rst)
            def _seq():
                with If(self.rst == 1):
                    self.out_reg <<= 0
                with Else():
                    self.out_reg <<= self.out_reg + 1

            @self.comb
            def _output():
                self.out <<= self.out_reg

    dut = GoodModule()
    violations = dut.lint(rules=["unregistered_output"])
    assert not any("UnregisteredOutput" in v for v in violations)


def test_unregistered_output_pure_comb():
    """Output driven purely by combinational logic SHOULD trigger UnregisteredOutput."""

    class CombModule(Module):
        def __init__(self):
            super().__init__("CombModule")
            self.a = Input(8, "a")
            self.out = Output(8, "out")

            @self.comb
            def _logic():
                self.out <<= self.a + 1

    dut = CombModule()
    violations = dut.lint(rules=["unregistered_output"])
    assert any("UnregisteredOutput" in v for v in violations)


# ---------------------------------------------------------------------------
# Integration: decoder_8b10b
# ---------------------------------------------------------------------------
def test_decoder_8b10b_no_seq_output_assign():
    from examples.decoder_8b10b import Decoder8b10b

    dut = Decoder8b10b()
    violations = dut.lint(rules=["seq_output_assign"])
    assert not any("SeqOutputAssign" in v for v in violations)
