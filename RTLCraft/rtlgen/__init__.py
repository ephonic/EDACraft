"""
rtlgen — Python API for Verilog RTL Generation

Public API exports
"""
from rtlgen.core import (
    Array,
    BehavioralModule,
    BehavioralRTLPair,
    BlackBoxModule,
    Input,
    IntentContext,
    Memory,
    ModelRegistry,
    ModelVersion,
    Module,
    Output,
    LocalParam,
    Parameter,
    Reg,
    Signal,
    SourceLoc,
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
    Elif,
    ForGen,
    Foreach,
    GenElse,
    GenIf,
    If,
    Mux,
    Otherwise,
    PadLeft,
    Rep,
    Split,
    StateTransition,
    Switch,
    When,
    comment,
)
from rtlgen.pipeline import Handshake, Pipeline, StageContext
from rtlgen.protocols import AHBLite, APB, AXI4, AXI4Lite, AXI4Stream, Bundle, Wishbone
from rtlgen.ram import SimpleDualPortRAM, SinglePortRAM
from rtlgen.codegen import EmitProfile, VerilogEmitter, inject_doc_comments, inject_doc_all_modules, ModuleDocTemplate, fill_doc_template
from rtlgen.lint import VerilogLinter, LintResult
from rtlgen.uvmgen import UVMEmitter
from rtlgen.regmodel import RegField, Register, RegBlock
from rtlgen.cocotbgen import CocotbEmitter
from rtlgen.decomposition import (
    BehavioralSpec,
    BoardSpec,
    CacheHierarchySpec,
    ConnectionSpec,
    CoreSpec,
    DataPacker,
    DecompositionResult,
    DesignDocBundle,
    DeviceSpec,
    MemorySpec,
    MicroArchDoc,
    ModuleDoc,
    PhysicalHint,
    PPAViolation,
    ProcessorSpec,
    SimulationDoc,
    SimulationResult,
    StrategyDoc,
    StrategySpec,
    SubModuleTemplates,
    SystemSpec,
    SystemSimulator,
    TopLevelDoc,
    Transform,
    generate_dsl_skeleton,
    submodule_to_spec,
)
from rtlgen.decomposition_rules import (
    DecompositionEngine,
    DecompositionRule,
    PrePPAAnalyzer,
    RuleRegistry,
)
from rtlgen.sim import Simulator
from rtlgen.ppa import PPAAnalyzer
from rtlgen.passes import ConstantFoldPass, DeadCodeElimPass, LintPass, PassManager
from rtlgen.registry import ComponentMeta, ComponentRegistry
from rtlgen.spec_ir import (
    AddOp,
    ArchitectureIR,
    FlowControlSpec,
    FunctionSpec,
    InterfaceSpec,
    MulOp,
    OptimizableOp,
    OperatorImpl,
    PortSpec,
    PPASpec,
    SpecIR,
    StageSpec,
    TimingSpec,
    VerificationSpec,
)
from rtlgen.spec_extractor import SpecCompleter, SpecExtractor
from rtlgen.arch_planner import ArchitecturePlanner
from rtlgen.dsl_gen import DSLGenerator
from rtlgen.ppa_optimizer import (
    BitwidthReduction,
    FSMEncodingSelect,
    MuxBalancing,
    OperatorSelection,
    OptimizationStrategy,
    PPAOptimizer,
    PPAGoal,
    PPAScore,
    PipelineInsertion,
    ResourceSharing,
)
from rtlgen.verif_gen import SpecCoverageTracker, ReferenceModel, TestGenerator, VerificationReport, VerificationRunner
from rtlgen.blifgen import (
    AdderStyle,
    BLIFEmitter,
    DividerStyle,
    MultiplierStyle,
    SynthConfig,
)
from rtlgen.synth import ABCSynthesizer, SynthResult, WireLoadModel
from rtlgen.iss_base import ISSBase
from rtlgen.behaviors import (
    TemplateRegistry,
    ifu_template,
    idu_template,
    alu_template,
    lsu_template,
    rob_template,
    regfile_template,
    datapath_template,
    fifo_template,
    axi_handshake_template,
    bpu_template,
    issue_queue_template,
    pipeline_connect_template,
    circular_queue_template,
    writeback_arbiter_template,
)
from rtlgen.tech_library import TechNode
from rtlgen.params import ConfigSpec, Config, PEParams, ParamAccessor, PresetSpecs
from rtlgen.processor_models import (
    BehavioralModelFactory,
    CPUModel,
    GPGPUModel,
    GPUState,
    GPUThread,
    GPUWarp,
    RV32ISS,
    RV32State,
)
from rtlgen.arch_def import (
    AgentPackage,
    Algorithm_Model,
    ArchDefinition,
    CoverageTracker,
    CoverageTracker as ArchCoverageTracker,
    CycleContext,
    ExuConfig,
    FuConfig,
    HandshakeSpec,
    InterconnectSpec,
    ISA_Model,
    MemoryModel,
    MemoryControllerSpec,
    ModelProvider,
    PortDesc,
    ProcessingElement,
    Protocol_Model,
    QueueSpec,
    SchedulerConfig,
    StateDesc,
    Stream_Model,
)
from rtlgen.arch_sim import ArchSimulator
from rtlgen.arch_skel import ArchSkeletonGenerator, GenerateLoopPattern
from rtlgen.mem_timing import DDR3Timing, ns_to_cycles
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


def __getattr__(name: str):
    """Lazy-load memory templates to avoid circular import."""
    if name in ("memory_controller_template", "dfi_sequencer_template"):
        try:
            from skills.mem.ddr3.behaviors import (
                memory_controller_template,
                dfi_sequencer_template,
            )
            return locals()[name]
        except ImportError:
            return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "Elif",
    "GenIf",
    "GenElse",
    "Switch",
    "ForGen",
    "Foreach",
    "When",
    "Otherwise",
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
    # Passes
    "PassManager",
    "LintPass",
    "ConstantFoldPass",
    "DeadCodeElimPass",
    # Registry
    "ComponentRegistry",
    "ComponentMeta",
    # Spec IR
    "SpecIR",
    "PortSpec",
    "FunctionSpec",
    "InterfaceSpec",
    "TimingSpec",
    "PPASpec",
    "VerificationSpec",
    "ArchitectureIR",
    "StageSpec",
    "OperatorImpl",
    "FlowControlSpec",
    "OptimizableOp",
    "MulOp",
    "AddOp",
    # Spec Extractor
    "SpecCompleter",
    "SpecExtractor",
    # Architecture Planner
    "ArchitecturePlanner",
    # DSL Generator
    "DSLGenerator",
    # PPA Optimizer
    "PPAGoal",
    "PPAScore",
    "PPAOptimizer",
    "OptimizationStrategy",
    "PipelineInsertion",
    "ResourceSharing",
    "BitwidthReduction",
    "OperatorSelection",
    "MuxBalancing",
    "FSMEncodingSelect",
    # Verification Generator
    "ReferenceModel",
    "TestGenerator",
    "SpecCoverageTracker",
    "CoverageTracker",
    "VerificationRunner",
    "VerificationReport",
    # Codegen
    "EmitProfile",
    "inject_doc_comments",
    "inject_doc_all_modules",
    "ModuleDocTemplate",
    "fill_doc_template",
    # Core (new)
    "SourceLoc",
    "IntentContext",
    "ModuleDoc",
    # Behavioral / RTL Correspondence
    "BehavioralModule",
    "BlackBoxModule",
    "BehavioralRTLPair",
    "ModelVersion",
    "ModelRegistry",
    # Processor Models
    "ISSBase",
    "CPUModel",
    # Behavior Templates
    "TemplateRegistry",
    "ifu_template",
    "idu_template",
    "alu_template",
    "lsu_template",
    "rob_template",
    "regfile_template",
    "datapath_template",
    "fifo_template",
    "axi_handshake_template",
    "bpu_template",
    "issue_queue_template",
    "pipeline_connect_template",
    "circular_queue_template",
    "writeback_arbiter_template",
    "memory_controller_template",
    "dfi_sequencer_template",
    "GPGPUModel",
    "GPUState",
    "GPUThread",
    "GPUWarp",
    "RV32ISS",
    "RV32State",
    "BehavioralModelFactory",
    # Synthesis
    "BLIFEmitter",
    "ABCSynthesizer",
    "SynthResult",
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
    # Decomposition
    "BehavioralSpec",
    "ConnectionSpec",
    "DecompositionResult",
    "StrategySpec",
    "SubModuleTemplates",
    "SystemSimulator",
    "submodule_to_spec",
    "generate_dsl_skeleton",
    "Transform",
    "PhysicalHint",
    "PPAViolation",
    "DataPacker",
    # Decomposition Rules
    "RuleRegistry",
    "DecompositionRule",
    "DecompositionEngine",
    "PrePPAAnalyzer",
    # Documentation
    "ModuleDoc",
    "TopLevelDoc",
    "StrategyDoc",
    "SimulationResult",
    "SimulationDoc",
    "MicroArchDoc",
    "DesignDocBundle",
    # Processor Architecture (gem5-style)
    "CoreSpec",
    "CacheHierarchySpec",
    "MemorySpec",
    "DeviceSpec",
    "BoardSpec",
    "ProcessorSpec",
    "SystemSpec",
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
    # Architecture Framework
    "ProcessingElement",
    "StateDesc",
    "PortDesc",
    "CycleContext",
    "InterconnectSpec",
    "HandshakeSpec",
    "QueueSpec",
    "ArchDefinition",
    "AgentPackage",
    "ModelProvider",
    "ISA_Model",
    "Protocol_Model",
    "Stream_Model",
    "Algorithm_Model",
    "MemoryModel",
    "MemoryControllerSpec",
    "ArchCoverageTracker",
    "ArchSimulator",
    "ArchSkeletonGenerator",
    "GenerateLoopPattern",
    # EXU Configuration (XiangShan-style)
    "FuConfig",
    "ExuConfig",
    "SchedulerConfig",
    # Tech Library
    "TechNode",
    # Memory Timing
    "DDR3Timing",
    "ns_to_cycles",
    # Params System
    "ConfigSpec",
    "Config",
    "PEParams",
    "ParamAccessor",
    "PresetSpecs",
]
