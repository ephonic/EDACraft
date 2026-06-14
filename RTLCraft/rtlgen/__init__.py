"""
rtlgen — Python API for Verilog RTL Generation

Public API exports
"""
from rtlgen.core import (
    Array,
    BehavioralModule,
    BehavioralRTLPair,
    BlackBoxModule,
    CacheInterface,
    connect_interfaces,
    HandshakeInterface,
    Input,
    IntentContext,
    Interface,
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
from rtlgen.contracts import (
    IRConstraint,
    FunctionalConstraint,
    PerformanceConstraint,
    PowerConstraint,
    TimingConstraint,
    VerificationIntent,
    ConstraintFeedback,
    FeedbackSeverity,
    ConstraintPropagator,
    DesignGate,
    DesignDecision,
    IREntity,
    LayerEmitter,
)
from rtlgen.scaffold import DesignScaffold, make_scaffold
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
    AssumptionIR,
    AddOp,
    ArchitectureIR,
    AssertionIR,
    BehaviorIR,
    BehaviorRuleIR,
    ClockResetDomainIR,
    ConnectionSpec as IRConnectionSpec,
    CoverageBinIR,
    CycleTransactionIR,
    CycleIR,
    FSMStateSpec,
    FlowControlSpec,
    FunctionSpec,
    HandshakeIR,
    HandshakeRuleIR,
    InterfaceSpec,
    InvariantIR,
    MulOp,
    OptimizableOp,
    OperationSpec,
    OperatorImpl,
    PortSpec,
    PPASpec,
    ProtocolIR,
    ScoreboardIR,
    StateIR,
    StateUpdateIR,
    RegisterTransferSpec,
    SpecIR,
    StageSpec,
    SubmoduleInstanceSpec,
    StructuralIR,
    TestVectorIR,
    TimingSpec,
    TraceEventIR,
    TracepointIR,
    TransactionEventIR,
    TransactionIR,
    VerificationPlanIR,
    VerificationSpec,
)
from rtlgen.spec_extractor import SpecCompleter, SpecExtractor
from rtlgen.arch_planner import ArchitecturePlanner
from rtlgen.agent_dsl_generator import AgentDSLGenerationResult, AgentDSLGenerator
from rtlgen.dsl_gen import DSLGenerator
from rtlgen.dsl_sim import DSLSimReport, DSLSimValidator, ModuleSimResult
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
from rtlgen.verifier import RepairContext, VerificationResult, Verifier
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
    datapath_template,
    fifo_template,
    axi_handshake_template,
    pipeline_connect_template,
    circular_queue_template,
    writeback_arbiter_template,
)
# Skill-specific templates loaded lazily via __getattr__
from rtlgen.tech_library import TechNode
from rtlgen.params import ConfigSpec, Config, PEParams, ParamAccessor, PresetSpecs
# Deferred import to avoid circular dependency:
# rtlgen.__init__ -> processor_models -> skills.cpu.models -> rtlgen.core
# triggers rtlgen.__init__ again while skills.cpu.models is partially loaded.
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
    """Lazy-load processor models and memory templates to avoid circular imports."""
    # Processor models (deferred to avoid: __init__ -> processor_models -> skills.cpu.models -> core)
    if name in ("BehavioralModelFactory", "CPUModel", "RV32ISS", "RV32State"):
        from rtlgen.processor_models import BehavioralModelFactory, CPUModel, RV32ISS, RV32State
        return locals()[name]
    if name in ("GPGPUModel", "GPUState", "GPUThread", "GPUWarp"):
        from rtlgen.processor_models import GPGPUModel, GPUState, GPUThread, GPUWarp
        return locals()[name]
    # Memory templates (deferred to avoid importing skills at package init time)
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
    # Interfaces
    "Interface",
    "HandshakeInterface",
    "CacheInterface",
    "connect_interfaces",
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
    # Constraints / Intent Framework
    "IRConstraint",
    "FunctionalConstraint",
    "PerformanceConstraint",
    "PowerConstraint",
    "TimingConstraint",
    "VerificationIntent",
    "ConstraintFeedback",
    "FeedbackSeverity",
    "ConstraintPropagator",
    "DesignGate",
    "DesignDecision",
    "IREntity",
    "LayerEmitter",
    # Scaffold
    "DesignScaffold",
    "make_scaffold",
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
    "TestVectorIR",
    "CoverageBinIR",
    "CycleTransactionIR",
    "AssertionIR",
    "TracepointIR",
    "ScoreboardIR",
    "ProtocolIR",
    "TransactionIR",
    "VerificationPlanIR",
    "AssumptionIR",
    "InvariantIR",
    "BehaviorRuleIR",
    "BehaviorIR",
    "StateIR",
    "StateUpdateIR",
    "HandshakeRuleIR",
    "TraceEventIR",
    "TransactionEventIR",
    "CycleIR",
    "ClockResetDomainIR",
    "StructuralIR",
    "ArchitectureIR",
    "StageSpec",
    "OperationSpec",
    "RegisterTransferSpec",
    "OperatorImpl",
    "FlowControlSpec",
    "HandshakeIR",
    "FSMStateSpec",
    "SubmoduleInstanceSpec",
    "IRConnectionSpec",
    "OptimizableOp",
    "MulOp",
    "AddOp",
    # Spec Extractor
    "SpecCompleter",
    "SpecExtractor",
    # Architecture Planner
    "ArchitecturePlanner",
    "AgentDSLGenerator",
    "AgentDSLGenerationResult",
    # DSL Generator
    "DSLGenerator",
    "DSLSimValidator",
    "DSLSimReport",
    "ModuleSimResult",
    "Verifier",
    "VerificationResult",
    "RepairContext",
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


# Lazy-load skill-specific templates via TemplateRegistry
_skill_template_cache = {}

def __getattr__(name: str):
    """Lazy-load any template by name from TemplateRegistry.
    
    Resolution strategy:
      1. Exact match: name → register(name, fn)
      2. Remove _template suffix → lookup
      3. Fuzzy match: find any key where name contains key or key contains name
      4. Try loading skill module and retry
    """
    if name.endswith("_template"):
        from rtlgen.registry import TemplateRegistry as _tr
        key = name.replace("_template", "")
        
        # 1. Exact match
        fn = _tr.get(key)
        if fn is not None:
            return fn
        
        # 2. Try the name itself (for edge cases)
        fn = _tr.get(name)
        if fn is not None:
            return fn
        
        # 3. Fuzzy: find any registered key that's contained in the name
        all_keys = _tr.list()
        for k in all_keys:
            if k in key or key in k:
                fn = _tr.get(k)
                if fn is not None:
                    # Cache for future lookups
                    _tr.register(key, fn)
                    return fn
        
        # 4. Try stripping common prefixes like 'isp_', 'cam_', etc.
        for prefix in ['isp_', 'cam_', 'ddr3_', 'fft_']:
            if key.startswith(prefix):
                stripped = key[len(prefix):]
                fn = _tr.get(stripped)
                if fn is not None:
                    _tr.register(key, fn)
                    return fn
        
        # 5. Last resort: try loading the skill module itself
        if not name.startswith('_'):
            _skill_map = {
                'isp_': 'image.isp', 'cam_': 'mem.cam', 'memory_': 'mem.ddr3',
                'dfi_': 'mem.ddr3', 'fft_': 'fft', 'router_': 'noc',
                'buffer_': 'noc', 'perf_core_': 'hetero_riscv4', 'eff_core_': 'hetero_riscv4',
                'uart_': 'interfaces.uart',
            }
            for prefix, sk in _skill_map.items():
                if key.startswith(prefix) or key == prefix.rstrip('_'):
                    import importlib
                    for mod_name in ('cycle_level', 'functional', 'behaviors'):
                        try:
                            mod = importlib.import_module(f'skills.{sk}.{mod_name}')
                            fn = getattr(mod, name, None)
                            if fn is not None:
                                _tr.register(key, fn)
                                return fn
                        except Exception:
                            pass
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
