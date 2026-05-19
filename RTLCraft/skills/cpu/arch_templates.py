"""
skills.cpu.arch_templates — CPU Architecture Template System

Extensible architecture templates that generate ArchDefinition from
user requirements. Users select a template family (in-order, OoO, etc.),
customize parameters, and the template builds the full architecture.

Architecture families:
  - in_order:       Classic 5-stage pipeline (IF/ID/EX/MEM/WB)
  - out_of_order:   Superscalar with ROB, issue queue, register renaming
  - embedded:       Minimal single-issue core, no prediction
  - multi_core:     Multiple in-order cores with shared L2

Custom architectures:
  Users can subclass CpuArchTemplate and override build_pes() /
  build_interconnects() to define their own micro-architectures.

Usage:
    from skills.cpu.arch_templates import OutOfOrderTemplate, CpuArchParams

    params = CpuArchParams(fetch_width=4, dispatch_width=6, rob_depth=128)
    template = OutOfOrderTemplate(params)
    arch = template.build()
"""
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    ArchDefinition, InterconnectSpec, ISA_Model,
)
from rtlgen.behaviors import TemplateRegistry

from skills.cpu.models import RV32ISS


# =====================================================================
# Architecture Parameters — user-facing config
# =====================================================================

@dataclass
class CpuArchParams:
    """CPU architecture parameters.

    These map to the micro-architecture in a predictable way.
    Users set these directly; templates translate them into PE configs.
    """
    name: str = "my_cpu"
    description: str = ""
    isa: str = "riscv"
    xlen: int = 32

    # Pipeline topology (template decides what to use)
    pipeline_stages: int = 5           # 5=classic, more=deeper

    # Frontend
    fetch_width: int = 1              # instructions per cycle
    btb_entries: int = 64             # branch target buffer
    bht_entries: int = 512            # branch history table
    ras_entries: int = 16             # return address stack
    ibuf_depth: int = 16              # instruction buffer depth

    # Decode / Dispatch
    dispatch_width: int = 1           # rename/dispatch per cycle
    rename_table_size: int = 128      # physical register file entries

    # Execution
    alu_pipes: int = 1                # ALU execution pipes
    has_mul_pipe: bool = False        # dedicated multiplier pipe
    has_fpu_pipe: bool = False        # FPU pipe (future)
    issue_queue_depth: int = 16       # reservation station entries
    issue_width: int = 2              # instructions issued per cycle

    # Load/Store
    lq_size: int = 32                 # load queue entries
    sq_size: int = 32                 # store queue entries
    cache_latency: int = 3            # L1 hit latency

    # Retire
    rob_depth: int = 32               # reorder buffer entries
    retire_width: int = 1             # instructions retired per cycle

    # Memory hierarchy
    l1i_size_kb: int = 32
    l1d_size_kb: int = 32
    l2_size_kb: int = 0               # 0 = no L2
    l2_ways: int = 8

    # PPA targets
    ppa_targets: Dict[str, Any] = field(default_factory=lambda: {
        "max_area": 50000,
        "min_freq_mhz": 500,
    })

    # Simulation
    sim_cycles: int = 50

    # Output
    output_dir: str = ""

    def classify(self) -> str:
        """Auto-detect architecture family from parameters."""
        if self.dispatch_width > 1 and self.rob_depth > 32:
            return "out_of_order"
        if self.dispatch_width == 1 and self.rob_depth <= 32:
            return "in_order"
        if self.fetch_width == 1 and self.dispatch_width == 1:
            return "embedded"
        return "custom"

    def suggested_template(self) -> str:
        """Suggest the best matching architecture template."""
        kind = self.classify()
        mapping = {
            "out_of_order": "out_of_order",
            "in_order": "in_order",
            "embedded": "embedded",
            "custom": "out_of_order",
        }
        return mapping.get(kind, "out_of_order")

    def __post_init__(self):
        """Auto-adjust PPA targets based on architecture class."""
        kind = self.classify()
        if kind == "embedded" and not self.ppa_targets.get("max_area"):
            self.ppa_targets.update({"max_area": 5000, "min_freq_mhz": 100})
        elif kind == "out_of_order" and not self.ppa_targets.get("min_ipc"):
            self.ppa_targets["min_ipc"] = min(self.fetch_width, self.dispatch_width)


# =====================================================================
# PE Builder — factory function with parameters
# =====================================================================

@dataclass
class PeBuilder:
    """Named PE builder.

    name:        PE name in the architecture (e.g., "IFU")
    pe_type:     Template key (e.g., "ifu") — maps to skeleton steps
    behavior_fn: Callable that returns the behavior function
    inputs:      Port definitions
    outputs:     Port definitions
    state:       State variable definitions (optional)
    description: Human-readable description
    """
    name: str
    pe_type: str
    behavior_fn: Callable[[], Callable]
    inputs: List[PortDesc]
    outputs: List[PortDesc]
    state: List[StateDesc] = field(default_factory=list)
    description: str = ""

    def build(self) -> ProcessingElement:
        return ProcessingElement(
            name=self.name,
            pe_type=self.pe_type,
            description=self.description,
            behavior=self.behavior_fn(),
            inputs=copy.deepcopy(self.inputs),
            outputs=copy.deepcopy(self.outputs),
            state=copy.deepcopy(self.state),
        )


def _ins(name: str, width: int = 1) -> PortDesc:
    return PortDesc(name=name, direction="input", width=width)


def _out(name: str, width: int = 1) -> PortDesc:
    return PortDesc(name=name, direction="output", width=width)


# =====================================================================
# PE Catalog — pre-defined builders for common CPU blocks
# =====================================================================

class PeCatalog:
    """Pre-defined PE builders for CPU pipeline stages.

    Each method returns a PeBuilder configured for a specific pipeline stage.
    Templates compose these to build their architecture.
    """

    @staticmethod
    def ifu(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="IFU", pe_type="ifu",
            description="Instruction Fetch Unit",
            behavior_fn=lambda: TemplateRegistry.get("ifu")(
                fetch_width=params.fetch_width,
                btb_entries=params.btb_entries,
                bht_entries=params.bht_entries,
                ras_entries=params.ras_entries,
                ibuf_depth=params.ibuf_depth,
            ),
            inputs=[
                _ins("redirect_valid"), _ins("flush"), _ins("idu_stall"),
                _ins("bht_feedback_valid"), _ins("bht_feedback_taken"),
                _ins("redirect_pc", 32),
            ],
            outputs=[
                _out("pc_out", 32), _out("inst_valid"),
                _out("inst_count", 3), _out("ifu_flush_req"),
            ],
        )

    @staticmethod
    def bpu(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="BPU", pe_type="bpu",
            description="Branch Prediction Unit",
            behavior_fn=lambda: TemplateRegistry.get("bpu")(
                btb_entries=params.btb_entries,
                bht_length=params.bht_entries,
                ras_entries=params.ras_entries,
            ),
            inputs=[
                _ins("fetch_pc", 32), _ins("fetch_valid"),
                _ins("bpu_update_valid"), _ins("bpu_update_pc", 32),
                _ins("bpu_update_taken"), _ins("bpu_update_target", 32),
            ],
            outputs=[
                _out("predicted_pc", 32), _out("predicted_taken"),
                _out("predictions_total", 16),
            ],
        )

    @staticmethod
    def idu(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="IDU", pe_type="idu",
            description="Instruction Decode/Dispatch",
            behavior_fn=lambda: TemplateRegistry.get("idu")(
                dispatch_width=params.dispatch_width,
            ),
            inputs=[
                _ins("inst_valid"), _ins("inst_count", 3),
                _ins("rtu_stall"),
            ],
            outputs=[
                _out("dispatch_count", 3), _out("dispatch_valid"),
                _out("rob_write_en"), _out("iu_issue_en"), _out("lsu_issue_en"),
            ],
        )

    @staticmethod
    def alu(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="ALU", pe_type="alu",
            description="Integer Execution Unit",
            behavior_fn=lambda: TemplateRegistry.get("alu")(
                num_pipes=params.alu_pipes,
                has_multiplier=params.has_mul_pipe,
            ),
            inputs=[
                _ins("issue_en"), _ins("dispatch_count", 3),
            ],
            outputs=[
                _out("iu_complete"), _out("iu_busy"),
                _out("bht_feedback_taken"), _out("bht_feedback_valid"),
                _out("redirect_valid"),
            ],
        )

    @staticmethod
    def lsu(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="LSU", pe_type="lsu",
            description="Load/Store Unit",
            behavior_fn=lambda: TemplateRegistry.get("lsu")(
                lq_depth=params.lq_size,
                sq_depth=params.sq_size,
                cache_latency=params.cache_latency,
            ),
            inputs=[
                _ins("issue_en"), _ins("dispatch_count", 3),
                _ins("dcache_hit"),
            ],
            outputs=[
                _out("lsu_complete"), _out("lsu_busy"),
                _out("dcache_req"), _out("dcache_addr", 32),
                _out("dcache_wen"),
            ],
        )

    @staticmethod
    def rob(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="ROB", pe_type="rtu",
            description="Reorder Buffer",
            behavior_fn=lambda: TemplateRegistry.get("rob")(
                rob_depth=params.rob_depth,
                retire_width=params.retire_width,
                dispatch_width=params.dispatch_width,
            ),
            inputs=[
                _ins("dispatch_count", 3), _ins("dispatch_valid"),
                _ins("iu_complete"), _ins("lsu_complete"),
            ],
            outputs=[
                _out("retire_count", 3), _out("retire_valid"),
                _out("rob_head", 32), _out("rob_full"), _out("flush"),
            ],
        )

    @staticmethod
    def regfile(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="RegFile", pe_type="regfile",
            description="Physical Register File",
            behavior_fn=lambda: TemplateRegistry.get("regfile")(
                num_entries=params.rename_table_size,
                xlen=params.xlen,
            ),
            inputs=[
                _ins("wen0"), _ins("waddr0", 8), _ins("wdata0", params.xlen),
                _ins("ren0", 8), _ins("ren1", 8), _ins("ren2", 8),
            ],
            outputs=[
                _out("rdata0", params.xlen), _out("rdata1", params.xlen),
                _out("rdata2", params.xlen), _out("preg_busy"),
            ],
        )

    @staticmethod
    def issue_queue(params: CpuArchParams) -> PeBuilder:
        return PeBuilder(
            name="IssueQueue", pe_type="issue_queue",
            description="Reservation Station",
            behavior_fn=lambda: TemplateRegistry.get("issue_queue")(
                depth=params.issue_queue_depth,
                issue_width=params.issue_width,
            ),
            inputs=[
                _ins("dispatch_valid"), _ins("dispatch_count", 3),
                _ins("wakeup_valid"),
            ],
            outputs=[
                _out("issue_valid"), _out("issue_count", 3),
                _out("rs_full"),
            ],
        )

    @staticmethod
    def datapath(params: CpuArchParams, name: str = "Datapath",
                 pe_type: str = "generic", operation: str = "pass_through",
                 inputs: Optional[List[PortDesc]] = None,
                 outputs: Optional[List[PortDesc]] = None,
                 description: str = "") -> PeBuilder:
        """Generic datapath PE for custom blocks."""
        return PeBuilder(
            name=name, pe_type=pe_type,
            description=description,
            behavior_fn=lambda: TemplateRegistry.get("datapath")(operation=operation),
            inputs=inputs or [_ins("input", 32)],
            outputs=outputs or [_out("output", 32)],
        )


# =====================================================================
# CpuArchTemplate — base class for architecture templates
# =====================================================================

class CpuArchTemplate(ABC):
    """Base class for CPU architecture templates.

    Subclasses override:
    - family_name: human-readable name (e.g., "Superscalar Out-of-Order")
    - build_pes(): list of PeBuilder instances
    - build_interconnects(): list of (src, dst, signals) tuples
    - default_params(): sensible defaults for this template family
    """

    @property
    @abstractmethod
    def family_name(self) -> str:
        pass

    @property
    def description(self) -> str:
        return ""

    def default_params(self) -> CpuArchParams:
        return CpuArchParams()

    @abstractmethod
    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        pass

    @abstractmethod
    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        pass

    def build(self, params: Optional[CpuArchParams] = None) -> ArchDefinition:
        """Build full ArchDefinition from parameters."""
        if params is None:
            params = self.default_params()

        pe_builders = self.build_pes(params)
        connections = self.build_interconnects(params)

        arch = ArchDefinition(
            name=params.name.upper().replace(" ", "_"),
            description=params.description or self.description,
            isa=params.isa,
            model=ISA_Model(iss=RV32ISS()),
            ppa_targets=dict(params.ppa_targets),
        )

        for builder in pe_builders:
            arch.add_pe(builder.build())

        for src, dst, signals in connections:
            arch.add_interconnect(InterconnectSpec(
                src_pe=src, dst_pe=dst,
                signals=[_out(s) for s in signals],
            ))

        return arch

    def summarize(self, params: Optional[CpuArchParams] = None) -> str:
        """One-line summary of what this template builds."""
        if params is None:
            params = self.default_params()
        pes = self.build_pes(params)
        pe_names = [b.name for b in pes]
        return (
            f"{self.family_name}: {len(pes)} PEs [{', '.join(pe_names)}] | "
            f"fetch={params.fetch_width}, dispatch={params.dispatch_width}, "
            f"rob={params.rob_depth}"
        )


# =====================================================================
# Template: Embedded Single-Issue
# =====================================================================

class EmbeddedTemplate(CpuArchTemplate):
    """Minimal single-issue in-order core.

    Pipeline: IFU → IDU → ALU/LSU → WB
    No branch prediction, no ROB, no register renaming.
    Suitable for microcontrollers and IoT.
    """

    @property
    def family_name(self) -> str:
        return "Embedded Single-Issue"

    @property
    def description(self) -> str:
        return "Minimal in-order core: 5-stage pipeline, no prediction, no OoO"

    def default_params(self) -> CpuArchParams:
        return CpuArchParams(
            name="embedded_cpu",
            fetch_width=1, dispatch_width=1, rob_depth=0,
            alu_pipes=1, has_mul_pipe=False,
            btb_entries=0, bht_entries=0, ras_entries=0,
            lq_size=4, sq_size=4,
            ppa_targets={"max_area": 5000, "min_freq_mhz": 100},
        )

    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        catalog = PeCatalog()
        return [
            catalog.ifu(params),
            catalog.idu(params),
            catalog.alu(params),
            catalog.lsu(params),
        ]

    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("IFU", "IDU", ["inst_valid", "inst_count", "pc_out"]),
            ("IDU", "ALU", ["dispatch_count", "dispatch_valid"]),
            ("IDU", "LSU", ["dispatch_count", "dispatch_valid"]),
        ]


# =====================================================================
# Template: In-Order Pipelined
# =====================================================================

class InOrderTemplate(CpuArchTemplate):
    """Classic 5-stage in-order pipeline with branch prediction.

    Pipeline: IFU+BPU → IDU → ALU → LSU → WB
    Has BPU for prediction but no OoO execution.
    Suitable for application processors and mid-range embedded.
    """

    @property
    def family_name(self) -> str:
        return "In-Order Pipelined"

    @property
    def description(self) -> str:
        return "Classic 5-stage pipeline with BPU, no register renaming"

    def default_params(self) -> CpuArchParams:
        return CpuArchParams(
            name="in_order_cpu",
            fetch_width=2, dispatch_width=2, rob_depth=0,
            alu_pipes=1, has_mul_pipe=True,
            btb_entries=64, bht_entries=256, ras_entries=8,
            lq_size=16, sq_size=16,
            ppa_targets={"max_area": 20000, "min_freq_mhz": 300},
        )

    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        catalog = PeCatalog()
        return [
            catalog.ifu(params),
            catalog.bpu(params),
            catalog.idu(params),
            catalog.alu(params),
            catalog.lsu(params),
        ]

    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("IFU", "IDU", ["inst_valid", "inst_count", "pc_out"]),
            ("BPU", "IFU", ["predicted_pc", "predicted_taken"]),
            ("IDU", "ALU", ["dispatch_count", "dispatch_valid", "iu_issue_en"]),
            ("IDU", "LSU", ["dispatch_count", "dispatch_valid", "lsu_issue_en"]),
            ("ALU", "IFU", ["bht_feedback_valid", "bht_feedback_taken"]),
        ]


# =====================================================================
# Template: Superscalar Out-of-Order
# =====================================================================

class OutOfOrderTemplate(CpuArchTemplate):
    """Superscalar out-of-order execution core.

    Pipeline: IFU+BPU → IDU (rename) → [IssueQueue → ALU/LSU] → ROB (retire)
    Features: register renaming, issue queue, ROB, multi-pipe execution.
    Suitable for high-performance application processors.
    """

    @property
    def family_name(self) -> str:
        return "Superscalar Out-of-Order"

    @property
    def description(self) -> str:
        return "Superscalar OoO: BPU, rename, issue queue, ROB, multi-pipe ALU"

    def default_params(self) -> CpuArchParams:
        return CpuArchParams(
            name="oo_cpu",
            fetch_width=3, dispatch_width=4, rob_depth=64,
            alu_pipes=1, has_mul_pipe=False,
            issue_queue_depth=16, issue_width=2,
            btb_entries=64, bht_entries=512, ras_entries=16,
            lq_size=32, sq_size=32,
            rename_table_size=128,
            ppa_targets={"max_area": 50000, "min_freq_mhz": 500, "min_ipc": 4},
        )

    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        catalog = PeCatalog()
        return [
            catalog.ifu(params),
            catalog.bpu(params),
            catalog.idu(params),
            catalog.alu(params),
            catalog.lsu(params),
            catalog.rob(params),
            catalog.regfile(params),
            catalog.issue_queue(params),
        ]

    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("IFU", "IDU", ["inst_valid", "inst_count", "pc_out"]),
            ("IDU", "ALU", ["dispatch_count", "dispatch_valid", "iu_issue_en"]),
            ("IDU", "LSU", ["dispatch_count", "dispatch_valid", "lsu_issue_en"]),
            ("IDU", "ROB", ["dispatch_count", "dispatch_valid", "rob_write_en"]),
            ("IDU", "IssueQueue", ["dispatch_valid", "dispatch_count"]),
            ("ALU", "ROB", ["iu_complete"]),
            ("LSU", "ROB", ["lsu_complete"]),
            ("ALU", "IFU", ["bht_feedback_valid", "bht_feedback_taken", "redirect_valid"]),
            ("ROB", "IDU", ["rtu_stall"]),
            ("RegFile", "ALU", ["rdata0", "rdata1", "rdata2"]),
            ("ALU", "RegFile", ["iu_complete"]),
        ]


# =====================================================================
# Template: Multi-Core (shared L2)
# =====================================================================

class MultiCoreTemplate(CpuArchTemplate):
    """Multiple in-order cores sharing an L2 cache.

    Architecture: [Core0, Core1, ...] → L2 Cache → Memory
    Each core is a simple in-order pipeline.
    Suitable for multi-core embedded and IoT hubs.
    """

    @property
    def family_name(self) -> str:
        return "Multi-Core (shared L2)"

    @property
    def description(self) -> str:
        return "Multiple in-order cores sharing L2 cache"

    def default_params(self) -> CpuArchParams:
        return CpuArchParams(
            name="multi_core_cpu",
            fetch_width=1, dispatch_width=1, rob_depth=0,
            alu_pipes=1, has_mul_pipe=False,
            l2_size_kb=256, l2_ways=8,
            ppa_targets={"max_area": 30000, "min_freq_mhz": 200},
        )

    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        catalog = PeCatalog()
        # Single core as representative (multi-core = replicate + interconnect)
        return [
            catalog.ifu(params),
            catalog.idu(params),
            catalog.alu(params),
            catalog.lsu(params),
            catalog.datapath(params,
                name="L2Cache", pe_type="cache", operation="pass_through",
                inputs=[_ins("core0_req"), _ins("core0_wen"), _ins("core0_addr", 32),
                        _ins("core0_wdata", 32)],
                outputs=[_out("core0_ack"), _out("core0_rdata", 32)],
                description="Shared L2 Cache",
            ),
        ]

    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("IFU", "IDU", ["inst_valid", "inst_count", "pc_out"]),
            ("IDU", "ALU", ["dispatch_count", "dispatch_valid"]),
            ("IDU", "LSU", ["dispatch_count", "dispatch_valid"]),
            ("LSU", "L2Cache", ["core0_req", "core0_wen", "core0_addr", "core0_wdata"]),
            ("L2Cache", "LSU", ["core0_ack", "core0_rdata"]),
        ]


# =====================================================================
# Template Registry — discover all CPU templates
# =====================================================================

_CPU_TEMPLATES: Dict[str, type] = {
    "embedded": EmbeddedTemplate,
    "in_order": InOrderTemplate,
    "out_of_order": OutOfOrderTemplate,
    "multi_core": MultiCoreTemplate,
}


def get_template(name: str) -> CpuArchTemplate:
    """Get a CPU architecture template by name."""
    cls = _CPU_TEMPLATES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown CPU template: {name}. "
            f"Available: {list(_CPU_TEMPLATES.keys())}"
        )
    return cls()


def list_templates() -> Dict[str, str]:
    """List all available CPU templates with descriptions."""
    return {
        name: cls().family_name
        for name, cls in _CPU_TEMPLATES.items()
    }


def register_template(name: str, template_class: type):
    """Register a custom CPU architecture template.

    Usage:
        from skills.cpu.arch_templates import register_template, CpuArchTemplate

        class MyCustomCPU(CpuArchTemplate):
            @property
            def family_name(self):
                return "My Custom CPU"
            # ... override build_pes(), build_interconnects()

        register_template("my_custom", MyCustomCPU)
    """
    if not issubclass(template_class, CpuArchTemplate):
        raise TypeError("template_class must inherit from CpuArchTemplate")
    _CPU_TEMPLATES[name] = template_class


# =====================================================================
# Custom Architecture — user-defined from scratch
# =====================================================================

class CustomArchTemplate(CpuArchTemplate):
    """Custom architecture built from a list of PeBuilders and connections.

    Usage:
        from skills.cpu.arch_templates import CustomArchTemplate, PeCatalog

        params = CpuArchParams(name="my_custom")
        catalog = PeCatalog()

        template = CustomArchTemplate(
            family_name="My Custom",
            pe_builders=[catalog.ifu(params), catalog.alu(params)],
            connections=[("IFU", "ALU", ["inst_valid"])],
        )
        arch = template.build(params)
    """

    def __init__(self, family_name: str,
                 pe_builders: List[PeBuilder],
                 connections: List[Tuple[str, str, List[str]]],
                 description: str = ""):
        self._family_name = family_name
        self._pe_builders = pe_builders
        self._connections = connections
        self._description = description

    @property
    def family_name(self) -> str:
        return self._family_name

    @property
    def description(self) -> str:
        return self._description

    def build_pes(self, params: CpuArchParams) -> List[PeBuilder]:
        return self._pe_builders

    def build_interconnects(self, params: CpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return self._connections
