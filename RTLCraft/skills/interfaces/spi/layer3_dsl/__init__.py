"""skills.interfaces.spi.layer3_dsl — DSL Module Implementations"""
from __future__ import annotations
from rtlgen import (
    Input, Output, Wire, Reg, Module,
    Parameter, LocalParam, VerilogEmitter,
)
from rtlgen.logic import If, Else, Const, Cat, Mux, Switch
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template
from .posedgedetector import PosEdgeDetector
from .negedgedetector import NegEdgeDetector
from .spiclockdivider import SPIClockDivider
from .spimodule import SPIModule
from .spitop import SPITop

__all__ = [
    "PosEdgeDetector",
    "NegEdgeDetector",
    "SPIClockDivider",
    "SPIModule",
    "SPITop",
]

