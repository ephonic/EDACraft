"""Tests for rtlgen visualizer scanner and layout."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from skills.cpu.npu.core import NeuralAccel
from rtlgen.viz.scanner import scan_module
from rtlgen.viz.layout import auto_layout
from rtlgen.viz.model import VizGraph, VizModule, VizPort, VizSignal


def test_scan_neural_accel():
    """NeuralAccel should scan into a graph with all submodules."""
    npu = NeuralAccel()
    graph = scan_module(npu)

    assert graph.name == "NeuralAccel"

    # Should have all major submodules + (top)
    instance_names = {m.instance_name for m in graph.modules}
    expected = {
        "decode", "inst_mem", "sram_a", "sram_b", "sram_c",
        "scratch", "systolic", "v_alu", "sfu", "im2col",
        "pool", "crossbar", "dma", "(top)",
    }
    assert expected.issubset(instance_names)


def test_scan_ports():
    """Each submodule should have ports extracted."""
    npu = NeuralAccel()
    graph = scan_module(npu)

    dma = graph.get_module("dma")
    assert dma is not None
    assert len(dma.ports) > 0
    input_names = {p.name for p in dma.ports if p.direction == "input"}
    output_names = {p.name for p in dma.ports if p.direction == "output"}
    assert len(input_names) > 0
    assert len(output_names) > 0


def test_scan_signals():
    """Should extract some signal connections."""
    npu = NeuralAccel()
    graph = scan_module(npu)

    # There should be at least some connections
    assert len(graph.signals) > 0

    # Check for known connections
    conns = [(s.src_module, s.src_port, s.dst_module, s.dst_port) for s in graph.signals]

    # Submodule output -> parent
    assert ("dma", "dma_done", "(top)", "dma_done") in conns
    assert ("systolic", "done", "(top)", "systolic_done") in conns
    assert ("pool", "done", "(top)", "pool_done") in conns

    # DMA AXI outputs -> parent top outputs
    assert ("dma", "araddr", "(top)", "m_axi_araddr") in conns


def test_layout():
    """Auto-layout should assign positions to all modules."""
    npu = NeuralAccel()
    graph = scan_module(npu)
    auto_layout(graph)

    for mod in graph.modules:
        assert mod.x >= 0
        assert mod.y >= 0
        assert mod.width > 0
        assert mod.height > 0


def test_graph_get_module():
    """VizGraph.get_module should find by instance name."""
    npu = NeuralAccel()
    graph = scan_module(npu)

    assert graph.get_module("dma") is not None
    assert graph.get_module("nonexistent") is None
