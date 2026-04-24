"""
Tests for parameterized modules with param/localparam and instantiation overrides.
"""

import pytest
from rtlgen import Module, Input, Output, Wire, Reg, VerilogEmitter, Simulator


class ParamAdder(Module):
    def __init__(self, name="ParamAdder", **kwargs):
        super().__init__(name, **kwargs)
        self.add_param("WIDTH", 8)
        self.add_localparam("OFFSET", 1)
        self.a = Input(self.WIDTH.value, "a")
        self.b = Input(self.WIDTH.value, "b")
        self.y = Output(self.WIDTH.value, "y")

        @self.comb
        def _logic():
            self.y <<= self.a + self.b + self.OFFSET.value


class ParamShift(Module):
    def __init__(self, name="ParamShift", **kwargs):
        super().__init__(name, **kwargs)
        self.add_param("WIDTH", 8)
        self.add_param("SHIFT", 2)
        self.add_localparam("MASK", (1 << 8) - 1)
        self.a = Input(self.WIDTH.value, "a")
        self.y = Output(self.WIDTH.value, "y")

        @self.comb
        def _logic():
            self.y <<= (self.a << self.SHIFT) & self.MASK.value


class TopExplicit(Module):
    """Top module that instantiates submodules explicitly with params override."""

    def __init__(self):
        super().__init__("TopExplicit")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.y = Output(16, "y")

        adder = ParamAdder()
        self.instantiate(adder, "u_adder", params={"WIDTH": 16}, port_map={
            "a": self.a,
            "b": self.b,
            "y": self.y,
        })


class TopImplicit(Module):
    """Top module that instantiates submodules implicitly with param_bindings."""

    def __init__(self):
        super().__init__("TopImplicit")
        self.WIDTH = __import__("rtlgen").Parameter(16, "WIDTH")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.y = Output(16, "y")
        self.adder = ParamAdder(param_bindings={"WIDTH": self.WIDTH})


class TopAutoParam(Module):
    """Top module with same-named parameter auto-mapped to submodule."""

    def __init__(self):
        super().__init__("TopAutoParam")
        self.WIDTH = __import__("rtlgen").Parameter(16, "WIDTH")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.y = Output(16, "y")
        self.adder = ParamAdder()  # auto-map WIDTH


def test_verilog_emits_parameter_and_localparam():
    adder = ParamAdder()
    sv = VerilogEmitter().emit(adder)
    assert "parameter WIDTH = 8" in sv
    assert "localparam OFFSET = 1" in sv
    assert "module ParamAdder #(parameter WIDTH = 8)" in sv


def test_verilog_no_localparam_in_module_header():
    adder = ParamAdder()
    sv = VerilogEmitter().emit(adder)
    lines = sv.splitlines()
    header_line = [l for l in lines if "module ParamAdder" in l][0]
    assert "OFFSET" not in header_line


def test_explicit_inst_param_override():
    top = TopExplicit()
    sv = VerilogEmitter().emit_design(top)
    assert "ParamAdder #(.WIDTH(16)) u_adder" in sv


def test_implicit_inst_param_bindings():
    top = TopImplicit()
    sv = VerilogEmitter().emit_design(top)
    assert "ParamAdder #(.WIDTH(WIDTH)) adder" in sv


def test_auto_param_mapping():
    top = TopAutoParam()
    sv = VerilogEmitter().emit_design(top)
    assert "ParamAdder #(.WIDTH(WIDTH)) adder" in sv


def test_sim_explicit_param_override():
    top = TopExplicit()
    sim = Simulator(top)
    sim.set("a", 3)
    sim.set("b", 5)
    sim.step()
    # 3 + 5 + 1 = 9
    assert sim.get_int("y") == 9


def test_sim_implicit_param_bindings():
    top = TopImplicit()
    sim = Simulator(top)
    sim.set("a", 10)
    sim.set("b", 20)
    sim.step()
    # 10 + 20 + 1 = 31
    assert sim.get_int("y") == 31


def test_sim_auto_param_mapping():
    top = TopAutoParam()
    sim = Simulator(top)
    sim.set("a", 7)
    sim.set("b", 8)
    sim.step()
    # 7 + 8 + 1 = 16
    assert sim.get_int("y") == 16


def test_sim_param_shift_override():
    class TopShift(Module):
        def __init__(self):
            super().__init__("TopShift")
            self.a = Input(8, "a")
            self.y = Output(8, "y")
            sh = ParamShift()
            self.instantiate(sh, "u_shift", params={"WIDTH": 8, "SHIFT": 3}, port_map={
                "a": self.a,
                "y": self.y,
            })

    top = TopShift()
    sim = Simulator(top)
    sim.set("a", 0b00001111)
    sim.step()
    # 0b00001111 << 3 = 0b01111000 = 120
    assert sim.get_int("y") == 120


def test_localparam_not_overridable_in_header():
    """LocalParam should not appear in the #( ... ) parameter list."""
    class MixedParams(Module):
        def __init__(self, name="MixedParams", **kwargs):
            super().__init__(name, **kwargs)
            self.add_param("WIDTH", 8)
            self.add_localparam("DEPTH", 16)
            self.add_param("STAGES", 2)

    m = MixedParams()
    sv = VerilogEmitter().emit(m)
    header = [l for l in sv.splitlines() if "module MixedParams" in l][0]
    assert "parameter WIDTH = 8" in header
    assert "parameter STAGES = 2" in header
    assert "DEPTH" not in header
    assert "localparam DEPTH = 16" in sv
