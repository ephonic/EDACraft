"""
rtlgen — Python API for Verilog RTL Generation

Public API 导出
"""
from rtlgen.core import (
    Array,
    Const as _Const,  # internal, logic.Const is preferred
    Input,
    Memory,
    Module,
    Output,
    LocalParam,
    Parameter,
    Reg,
    Signal,
    Vector,
    Wire,
)
from rtlgen.lib import (
    AsyncFIFO,
    BarrelShifter,
    CRC,
    Decoder,
    Divider,
    FSM,
    LFSR,
    PriorityEncoder,
    RoundRobinArbiter,
    SyncFIFO,
)
from rtlgen.logic import Cat, Const, Else, ForGen, GenElse, GenIf, If, Mux, Rep, Split, StateTransition, Switch, comment, PadLeft
from rtlgen.pipeline import Handshake, Pipeline, StageContext
from rtlgen.protocols import AHBLite, APB, AXI4, AXI4Lite, AXI4Stream, Bundle, Wishbone
from rtlgen.ram import SimpleDualPortRAM, SinglePortRAM
from rtlgen.codegen import VerilogEmitter
from rtlgen.lint import VerilogLinter, LintResult
from rtlgen.uvmgen import UVMEmitter
from rtlgen.regmodel import RegField, Register, RegBlock
from rtlgen.cocotbgen import CocotbEmitter
from rtlgen.uvmvip import UVMVIPEmitter
from rtlgen.sim import Simulator
from rtlgen.ppa import PPAAnalyzer
from rtlgen.blifgen import (
    BLIFEmitter,
    AdderStyle,
    MultiplierStyle,
    DividerStyle,
    SynthConfig,
)
from rtlgen.synth import ABCSynthesizer, WireLoadModel
from rtlgen.liberty import (
    generate_demo_liberty,
    generate_sizing_demo_liberty,
    parse_liberty,
)
from rtlgen.lef import (
    generate_demo_lef,
    parse_lef,
    LefLibrary,
    LefMacro,
    LefLayer,
    LefPin,
)
from rtlgen.netlist import parse_mapped_verilog, annotate_net_directions, Netlist
from rtlgen.timing import TimingAnalyzer
from rtlgen.sizing import GateSizer, SizingResult
from rtlgen.placement import AnalyticalPlacer, PlacementResult
from rtlgen.rc import FastRCExtractor, RCExtractionResult as FastRCResult
from rtlgen.routing import GlobalRouter, DetailedRouter, RoutingResult
from rtlgen.pinaccess import PinAccessOptimizer
from rtlgen.rcextract import (
    GlobalRCExtractor,
    DetailedRCExtractor,
    RTLFeedbackEngine,
    NetRC,
    RCExtractionResult,
    RTLFeedbackReport,
    RTLFeedbackItem,
)
from rtlgen.svagen import SVAEmitter
from rtlgen.pyuvm import (
    UVMComponent,
    UVMAgent,
    UVMAnalysisImp,
    UVMAnalysisPort,
    UVMDriver,
    UVMEnv,
    UVMField,
    UVMMonitor,
    UVMScoreboard,
    UVMSequence,
    UVMSequenceItem,
    UVMSequencer,
    UVMTest,
    UVMSeqItemPort,
    UVMSeqItemExport,
    UVMPhase,
    create,
    delay,
    repeat,
    randomize,
    start_item,
    finish_item,
    uvm_fatal,
    uvm_error,
    uvm_warning,
    uvm_info,
)
from rtlgen.pyuvmgen import UVMEmitter as PyUVMEmitter
from rtlgen.verilog_import import VerilogImporter

__all__ = [
    # Core
    "Module",
    "Signal",
    "Input",
    "Output",
    "Wire",
    "Reg",
    "LocalParam",
    "Parameter",
    "Memory",
    "Vector",
    "Array",
    # Logic
    "If",
    "Else",
    "GenIf",
    "GenElse",
    "Switch",
    "ForGen",
    "Mux",
    "Cat",
    "Rep",
    "Split",
    "PadLeft",
    "Const",
    "comment",
    # Pipeline
    "Pipeline",
    "StageContext",
    "Handshake",
    # Protocols
    "Bundle",
    "AXI4Stream",
    "APB",
    "AXI4Lite",
    "AXI4",
    "AHBLite",
    "Wishbone",
    # Lib
    "FSM",
    "SyncFIFO",
    "AsyncFIFO",
    "RoundRobinArbiter",
    "Decoder",
    "PriorityEncoder",
    "BarrelShifter",
    "LFSR",
    "CRC",
    "Divider",
    # RAM
    "SinglePortRAM",
    "SimpleDualPortRAM",
    # Codegen
    "VerilogEmitter",
    "VerilogLinter",
    "LintResult",
    "UVMEmitter",
    # RAL
    "RegField",
    "Register",
    "RegBlock",
    # Cocotb
    "CocotbEmitter",
    # VIP
    "UVMVIPEmitter",
    # Simulation
    "Simulator",
    # PPA
    "PPAAnalyzer",
    # Synthesis
    "BLIFEmitter",
    "ABCSynthesizer",
    "WireLoadModel",
    "generate_demo_liberty",
    "generate_sizing_demo_liberty",
    "parse_liberty",
    "parse_mapped_verilog",
    "annotate_net_directions",
    "Netlist",
    "TimingAnalyzer",
    "GateSizer",
    "SizingResult",
    "AnalyticalPlacer",
    "PlacementResult",
    "FastRCExtractor",
    "RCExtractionResult",
    "NetRC",
    "generate_demo_lef",
    "parse_lef",
    "LefLibrary",
    "LefMacro",
    "LefLayer",
    "LefPin",
    "AdderStyle",
    "MultiplierStyle",
    "DividerStyle",
    "SynthConfig",
    # SVA
    "SVAEmitter",
    # pyUVM
    "UVMComponent",
    "UVMAgent",
    "UVMAnalysisImp",
    "UVMAnalysisPort",
    "UVMDriver",
    "UVMEnv",
    "UVMField",
    "UVMMonitor",
    "UVMScoreboard",
    "UVMSequence",
    "UVMSequenceItem",
    "UVMSequencer",
    "UVMTest",
    "UVMSeqItemPort",
    "UVMSeqItemExport",
    "UVMPhase",
    "create",
    "delay",
    "repeat",
    "randomize",
    "start_item",
    "finish_item",
    "uvm_fatal",
    "uvm_error",
    "uvm_warning",
    "uvm_info",
    "PyUVMEmitter",
    # Verilog Import
    "VerilogImporter",
]
