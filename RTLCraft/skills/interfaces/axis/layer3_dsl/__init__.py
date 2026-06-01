"""skills.interfaces.axis.layer3_dsl — DSL Module Implementations"""
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
from .axis_register import AXIS_REGISTER
from .axis_adapter import AXIS_ADAPTER
from .axis_broadcast import AXIS_BROADCAST

__all__ = [
    "AXIS_REGISTER",
    "AXIS_ADAPTER",
    "AXIS_BROADCAST",
]

