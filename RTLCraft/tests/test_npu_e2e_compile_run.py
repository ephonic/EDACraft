"""End-to-end test: compile PyTorch model → load program → run on NPU.

These tests simulate a minimal AXI4 slave that immediately responds
to DMA read/write requests so that LOAD/STORE instructions complete.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
import torch
import torch.nn as nn
from rtlgen.sim import Simulator

from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.core import NeuralAccel


def _poke_axi_slave_ready(sim):
    """Make AXI slave always ready for address phases."""
    sim.poke('m_axi_arready', 1)
    sim.poke('m_axi_awready', 1)
    sim.poke('m_axi_wready', 1)


def _poke_axi_read_response(sim, data=0, last=1):
    """Provide AXI read data response."""
    sim.poke('m_axi_rvalid', 1)
    sim.poke('m_axi_rdata', data)
    sim.poke('m_axi_rlast', last)
    sim.poke('m_axi_rresp', 0)


def _poke_axi_write_response(sim):
    """Provide AXI write response."""
    sim.poke('m_axi_bvalid', 1)
    sim.poke('m_axi_bresp', 0)


def _clear_axi_pokes(sim):
    """Clear AXI inputs to default idle."""
    sim.poke('m_axi_arready', 0)
    sim.poke('m_axi_awready', 0)
    sim.poke('m_axi_wready', 0)
    sim.poke('m_axi_rvalid', 0)
    sim.poke('m_axi_bvalid', 0)
    sim.poke('m_axi_rdata', 0)
    sim.poke('m_axi_rlast', 0)
    sim.poke('m_axi_rresp', 0)
    sim.poke('m_axi_bresp', 0)


def _load_program(sim, compiled):
    """Load compiled program into NPU instruction memory."""
    for addr, instr in compiled.get_program_load_sequence():
        sim.poke('prog_load_valid', 1)
        sim.poke('prog_load_addr', addr)
        sim.poke('prog_load_data', instr)
        sim.poke('prog_load_we', 1)
        sim.step()
    sim.poke('prog_load_valid', 0)
    sim.poke('prog_load_we', 0)


def _run_npu(sim, compiled, max_cycles=500):
    """Run NPU with AXI slave stub until program completes."""
    sim.poke('prog_length', compiled.get_program_length())
    sim.poke('run', 1)
    sim.step()
    sim.poke('run', 0)

    completed = False
    for _ in range(max_cycles):
        # AXI slave stub: always ready, immediate data/response
        _poke_axi_slave_ready(sim)
        _poke_axi_read_response(sim, data=0, last=1)
        _poke_axi_write_response(sim)

        sim.step()

        if sim.peek('prog_done'):
            completed = True
            break

    _clear_axi_pokes(sim)
    return completed


def test_e2e_sync_program():
    """Compile a trivial model and run it on NPU."""
    model = nn.Sequential()
    compiled = compile_model(model, example_input=torch.randn(1, 4))

    assert compiled.get_program_length() > 0
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    _load_program(sim, compiled)
    completed = _run_npu(sim, compiled)

    assert completed, f"Program should complete. ASM:\n{compiled.to_asm()}"


def test_e2e_relu_program():
    """Compile a ReLU-only model and run it on NPU."""
    model = nn.Sequential(nn.ReLU())
    compiled = compile_model(model, example_input=torch.randn(1, 8))

    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    _load_program(sim, compiled)
    completed = _run_npu(sim, compiled)

    assert completed, f"Program should complete. ASM:\n{compiled.to_asm()}"


def test_e2e_linear_program():
    """Compile a Linear model and run it on NPU."""
    model = nn.Linear(8, 4, bias=False)
    with torch.no_grad():
        model.weight.copy_(torch.eye(4, 8) * 0.1)

    compiled = compile_model(model, example_input=torch.randn(1, 8))

    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset('rst_n')

    _load_program(sim, compiled)
    completed = _run_npu(sim, compiled, max_cycles=1500)

    assert completed, f"Program should complete. ASM:\n{compiled.to_asm()}"
