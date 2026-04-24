"""Tests for AXI4 DMA engine."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.npu.memory.axi_dma import AXI4DMA, DMA_IDLE


def test_axi_dma_instantiation():
    """AXI4DMA should instantiate with all AXI ports."""
    dma = AXI4DMA()
    assert dma is not None
    assert dma.arvalid is not None
    assert dma.rready is not None
    assert dma.awvalid is not None
    assert dma.wvalid is not None
    assert dma.bready is not None


def test_axi_dma_reset():
    """AXI4DMA should reset to IDLE."""
    dma = AXI4DMA()
    sim = Simulator(dma)
    sim.reset('rst_n')

    assert sim.peek('dma_busy') == 0
    assert sim.peek('dma_done') == 0


def test_axi_dma_verilog_generation():
    """AXI4DMA should emit valid Verilog."""
    dma = AXI4DMA()
    emitter = VerilogEmitter(use_sv_always=True)
    verilog = emitter.emit_design(dma)
    assert "module AXI4DMA" in verilog
    assert "arvalid" in verilog
    assert "rready" in verilog
    assert "awvalid" in verilog
    assert "wvalid" in verilog
    assert "bready" in verilog


def test_axi_dma_load_dispatch():
    """LOAD should start DMA read FSM."""
    dma = AXI4DMA()
    sim = Simulator(dma)
    sim.reset('rst_n')

    # Configure: ext_addr=0x1000, len=8 words, sram_addr=0
    sim.poke('cfg_ext_addr', 0x1000)
    sim.poke('cfg_len', 8)
    sim.poke('cfg_sram_addr', 0)

    # Start LOAD
    sim.poke('dma_start', 1)
    sim.poke('dma_dir', 0)
    sim.step()
    sim.poke('dma_start', 0)

    # Should be in AR_SEND state
    assert sim.peek('dma_busy') == 1
    assert sim.peek('arvalid') == 1
    assert sim.peek('araddr') == 0x1000


def test_axi_dma_store_dispatch():
    """STORE should start DMA write FSM."""
    dma = AXI4DMA()
    sim = Simulator(dma)
    sim.reset('rst_n')

    sim.poke('cfg_ext_addr', 0x2000)
    sim.poke('cfg_len', 4)
    sim.poke('cfg_sram_addr', 0)

    # Start STORE
    sim.poke('dma_start', 1)
    sim.poke('dma_dir', 1)
    sim.step()
    sim.poke('dma_start', 0)

    # Should enter W_PREP (reading SRAM)
    assert sim.peek('dma_busy') == 1
    assert sim.peek('local_req_valid') == 1
    assert sim.peek('local_req_we') == 0
