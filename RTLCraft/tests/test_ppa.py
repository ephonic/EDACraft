#!/usr/bin/env python3
"""
Unit tests for rtlgen.ppa.PPAAnalyzer.
"""

import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import Module, Input, Output, Wire, Reg, Switch, If, Else, Mux
from rtlgen import PPAAnalyzer, Simulator


class SimpleAdder(Module):
    def __init__(self):
        super().__init__("SimpleAdder")
        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.y = Output(8, "y")
        @self.comb
        def _logic():
            self.y <<= self.a + self.b


class PipelineMux(Module):
    def __init__(self):
        super().__init__("PipelineMux")
        self.sel = Input(1, "sel")
        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.y = Output(8, "y")
        @self.comb
        def _logic():
            with If(self.sel == 1):
                self.y <<= self.a
            with Else():
                self.y <<= self.b


class BigSwitch(Module):
    def __init__(self):
        super().__init__("BigSwitch")
        self.addr = Input(4, "addr")
        self.data = Output(8, "data")
        @self.comb
        def _logic():
            with Switch(self.addr) as sw:
                for i in range(16):
                    with sw.case(i):
                        self.data <<= i * 3
                with sw.default():
                    self.data <<= 0


def test_adder_logic_depth():
    m = SimpleAdder()
    ppa = PPAAnalyzer(m)
    depths = ppa.analyze_static()["logic_depth"]
    # a + b 是 BinOp "+"，深度为 1（无乘法惩罚）
    assert depths["y"] == 1


def test_adder_gate_count():
    m = SimpleAdder()
    ppa = PPAAnalyzer(m)
    gates = ppa.analyze_static()["gate_count"]
    # 8-bit adder ~ 4 * 8 = 32 NAND2-equiv
    assert gates >= 30


def test_adder_reg_bits():
    m = SimpleAdder()
    ppa = PPAAnalyzer(m)
    assert ppa.analyze_static()["reg_bits"] == 0


def test_mux_logic_depth():
    m = PipelineMux()
    ppa = PPAAnalyzer(m)
    depths = ppa.analyze_static()["logic_depth"]
    # IfNode introduces cond(sel==1) depth 1 + Mux penalty 2 = 3 extra
    assert depths["y"] == 3


def test_mux_gate_count():
    m = PipelineMux()
    ppa = PPAAnalyzer(m)
    gates = ppa.analyze_static()["gate_count"]
    # Should be > 0 due to Mux
    assert gates > 0


def test_switch_mux_complexity():
    m = BigSwitch()
    ppa = PPAAnalyzer(m)
    mux = ppa.analyze_static()["mux_complexity"]
    assert mux["total_cases"] == 16
    assert mux["max_case_width"] == 4


def test_switch_logic_depth():
    m = BigSwitch()
    ppa = PPAAnalyzer(m)
    depths = ppa.analyze_static()["logic_depth"]
    # SwitchNode with 16 cases -> log2(16)+1+expr_d = 4+1+0 = 5
    assert depths["data"] == 5


def test_fanout_analysis():
    m = SimpleAdder()
    ppa = PPAAnalyzer(m)
    fanout = ppa.analyze_static()["fanout_report"]
    assert fanout.get("a", 0) >= 1
    assert fanout.get("b", 0) >= 1


def test_dead_signals():
    class DeadSignalMod(Module):
        def __init__(self):
            super().__init__("DeadSignalMod")
            self.a = Input(8, "a")
            self.unused = Wire(8, "unused")
            self.y = Output(8, "y")
            @self.comb
            def _logic():
                self.y <<= self.a
    m = DeadSignalMod()
    ppa = PPAAnalyzer(m)
    dead = ppa.analyze_static()["dead_signals"]
    assert "unused" in dead


def test_toggle_rates():
    m = SimpleAdder()
    sim = Simulator(m, trace_signals=["a", "b", "y"])
    sim.set("a", 0)
    sim.set("b", 0)
    sim.step()
    sim.set("a", 255)
    sim.set("b", 1)
    sim.step()
    sim.set("a", 0)
    sim.set("b", 0)
    sim.step()

    ppa = PPAAnalyzer(m)
    toggles = ppa.analyze_dynamic(sim)["toggle_rates"]
    assert "a" in toggles
    assert toggles["a"] > 0


def test_suggestions_not_empty_for_big_switch():
    m = BigSwitch()
    ppa = PPAAnalyzer(m)
    suggestions = ppa.suggest_optimizations()
    # 16 cases does not trigger the 32-case area threshold, but depth=5 may trigger timing
    assert len(suggestions) > 0


def test_report_contains_expected_sections():
    m = SimpleAdder()
    sim = Simulator(m, trace_signals=["a", "b", "y"])
    sim.set("a", 5)
    sim.set("b", 3)
    sim.step()
    ppa = PPAAnalyzer(m)
    r = ppa.report(sim)
    assert "Static Analysis" in r or "[Static Analysis]" in r
    assert "Dynamic Analysis" in r or "[Dynamic Analysis]" in r
    assert "PPA Report" in r
