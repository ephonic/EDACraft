"""
rtlgen — Python API for Verilog RTL Generation

Public API exports
"""
from rtlgen.core import (
    Array,
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
from rtlgen.logic import (
    Cat,
    Const,
    Else,
    ForGen,
    GenElse,
    GenIf,
    If,
    Mux,
    PadLeft,
    Rep,
    Split,
    StateTransition,
    Switch,
    comment,
)
from rtlgen.pipeline import Handshake, Pipeline, StageContext
from rtlgen.protocols import AHBLite, APB, AXI4, AXI4Lite, AXI4Stream, Bundle, Wishbone
from rtlgen.ram import SimpleDualPortRAM, SinglePortRAM
from rtlgen.codegen import VerilogEmitter
from rtlgen.lint import VerilogLinter, LintResult
from rtlgen.uvmgen import UVMEmitter
from rtlgen.regmodel import RegField, Register, RegBlock
from rtlgen.cocotbgen import CocotbEmitter
from rtlgen.sim import Simulator
from rtlgen.ppa import PPAAnalyzer
from rtlgen.blifgen import (
    AdderStyle,
    BLIFEmitter,
    DividerStyle,
    MultiplierStyle,
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
    LefLayer,
    LefLibrary,
    LefMacro,
    LefPin,
)
from rtlgen.netlist import Netlist, annotate_net_directions, parse_mapped_verilog
from rtlgen.uvmvip import UVMVIPEmitter
from rtlgen.pyuvm import (
    UVMAnalysisImp,
    UVMAnalysisPort,
    UVMAgent,
    UVMComponent,
    UVMDriver,
    UVMEnv,
    UVMField,
    UVMMonitor,
    UVMPhase,
    UVMScoreboard,
    UVMSequence,
    UVMSequenceItem,
    UVMSequencer,
    UVMSeqItemExport,
    UVMSeqItemPort,
    UVMTest,
    create,
    delay,
    randomize,
    repeat,
    start_item,
    finish_item,
    uvm_error,
    uvm_fatal,
    uvm_info,
    uvm_warning,
)
from rtlgen.pyuvmgen import UVMEmitter as PyUVMEmitter

# Optional: requires `pip install pyverilog`
try:
    from rtlgen.verilog_import import VerilogImporter
except ImportError:
    VerilogImporter = None  # type: ignore[misc,assignment]

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
    "StateTransition",
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
    "AdderStyle",
    "MultiplierStyle",
    "DividerStyle",
    "SynthConfig",
    # Liberty
    "generate_demo_liberty",
    "generate_sizing_demo_liberty",
    "parse_liberty",
    # LEF
    "generate_demo_lef",
    "parse_lef",
    "LefLibrary",
    "LefMacro",
    "LefLayer",
    "LefPin",
    # Netlist
    "Netlist",
    "parse_mapped_verilog",
    "annotate_net_directions",
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
    # Verilog Import (optional)
    "VerilogImporter",
]
