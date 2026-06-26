"""skills.interfaces.uart.layer3_dsl — DSL Module Implementations"""
from __future__ import annotations
from rtlgen import (
    Input, Output, Wire, Reg, Module, Vector, Array, VerilogEmitter,
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, HandshakeSpec, QueueSpec,
    ArchSimulator, ArchSkeletonGenerator,
    BehavioralSpec, StrategySpec, DecompositionResult,
    Memory, Parameter, LocalParam,
)
from rtlgen.logic import If, Else, Elif, When, Otherwise, Const, Cat, Mux, Switch, Rep, ForGen
from rtlgen.lib import SyncFIFO
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template
from .uart_tx import UART_TX
from .uart_rx import UART_RX
from .uart import UART

__all__ = [
    "UART_TX",
    "UART_RX",
    "UART",
]

