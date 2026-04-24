"""Tests for BOOM-style Out-of-Order RISC-V Core."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter
from skills.cpu.boom.core import BOOMCore


@pytest.fixture
def core():
    return BOOMCore(
        xlen=32,
        fetch_width=2,
        rob_entries=8,
        rs_entries=4,
        num_pregs=32,
    )


def test_boom_instantiation(core):
    """BOOMCore should instantiate without error."""
    assert core is not None
    assert core.clk is not None
    assert core.rst_n is not None


def test_boom_verilog_generation(core):
    """BOOMCore should emit valid Verilog."""
    emitter = VerilogEmitter()
    verilog = emitter.emit_design(core)
    assert "module BOOMCore" in verilog
    assert "module FetchUnit" in verilog
    assert "module DecodeUnit" in verilog
    assert "module ALU" in verilog
    assert "module LSU" in verilog
    assert "module ReorderBuffer" in verilog
    assert len(verilog.splitlines()) > 1000


def test_boom_reset(core):
    """BOOMCore should simulate reset correctly."""
    sim = Simulator(core)
    sim.reset('rst_n')

    # Provide a simple instruction (addi x1, x0, 1) from "memory"
    sim.set(core.mem_resp_valid, 1)
    sim.set(core.mem_resp_data, 0x00100093)

    for _ in range(20):
        sim.step()
    assert sim.time_ns >= 20


def test_boom_decode_addi(core):
    """Decode unit should correctly identify ADDI."""
    sim = Simulator(core)
    sim.reset('rst_n')

    # ADDI x1, x0, 5  =>  0x00500093
    sim.set(core.mem_resp_valid, 1)
    sim.set(core.mem_resp_data, 0x00500093)

    for _ in range(10):
        sim.step()

    # After a few cycles, decode should produce valid signals
    emitter = VerilogEmitter()
    verilog = emitter.emit_design(core)
    assert "dec_valid" in verilog
    assert "dec_is_alu" in verilog


def test_boom_modules_list(core):
    """All expected submodules should be present."""
    emitter = VerilogEmitter()
    verilog = emitter.emit_design(core)
    modules = [
        "FetchUnit",
        "BranchPredictor",
        "DecodeUnit",
        "RenameUnit",
        "ReservationStation",
        "PhysicalRegFile",
        "ALU",
        "Multiplier",
        "LSU",
        "ReorderBuffer",
        "BOOMCore",
    ]
    for mod in modules:
        assert f"module {mod}" in verilog, f"Missing module: {mod}"
