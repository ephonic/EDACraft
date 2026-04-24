"""
RTLGen Visualizer — Interactive hardware architecture diagram viewer.

Usage:
    python -m rtlgen.viz --target skills.cpu.npu.core.NeuralAccel
"""

from rtlgen.viz.model import VizGraph, VizModule, VizPort, VizSignal

try:
    from rtlgen.viz.scanner import scan_module
except ImportError:  # pragma: no cover
    scan_module = None

try:
    from rtlgen.viz.layout import auto_layout
except ImportError:  # pragma: no cover
    auto_layout = None

__all__ = ["VizGraph", "VizModule", "VizPort", "VizSignal", "scan_module", "auto_layout"]
