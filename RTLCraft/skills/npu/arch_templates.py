"""
skills.npu.arch_templates — NPU Architecture Template System

Extensible architecture templates that generate ArchDefinition from
user requirements. Users select a template family (basic, pipeline,
multi-pipeline), customize parameters, and the template builds the
full architecture.

Architecture families:
  - basic:       Single MVU → eVRF → MFU → LD pipeline
  - dual_pipeline: Dual loader + dual eVRF (matches FPGA-NPU ref RTL)
  - multi_tile:  Multiple MVU tiles with shared scheduler

Custom architectures:
  Users can subclass NpuArchTemplate and override build_pes() /
  build_interconnects() to define their own micro-architectures.

Usage:
    from skills.npu.arch_templates import BasicTemplate, NpuArchParams

    params = NpuArchParams(ntile=7, ndpe=40, ew=8)
    template = BasicTemplate(params)
    arch = template.build()
"""
from __future__ import annotations

# Import behaviors first to register templates in TemplateRegistry
import skills.npu.behaviors  # noqa: F401

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    ArchDefinition, InterconnectSpec,
)
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# Architecture Parameters — user-facing config
# =====================================================================

@dataclass
class NpuArchParams:
    """NPU architecture parameters.

    These map to the micro-architecture in a predictable way.
    Users set these directly; templates translate them into PE configs.
    """
    name: str = "my_npu"
    description: str = ""

    # Compute array
    ntile: int = 7                # number of tiles
    ndpe: int = 40               # DPEs per tile
    ew: int = 8                  # element width (INT8)
    accw: int = 32               # accumulator width
    dotw: int = 40               # dot-product width

    # VRF
    nvrf: int = 12               # number of VRF ports
    vrf_depth: int = 512         # VRF depth

    # Schedulers
    scheduler_miw: int = 30      # MVU macro instruction width
    scheduler_uiw: int = 25      # MVU micro instruction width
    scheduler_loop_depth: int = 8
    scheduler_unroll_factor: int = 1

    # MFU
    num_mfu_funcs: int = 8       # number of supported functions
    mfu_pipeline_stages: int = 1

    # LD
    ld_fifo_depth: int = 16

    # eVRF
    evrf_num_banks: int = 4
    evrf_bank_latency: int = 2

    # Pipeline topology
    num_pipeline_stages: int = 4  # MVU → eVRF → MFU → LD
    has_dual_loader: bool = False

    # PPA targets
    ppa_targets: Dict[str, Any] = field(default_factory=lambda: {
        "max_area": 200000,
        "min_freq_mhz": 200,
    })

    # Simulation
    sim_cycles: int = 50

    # Output
    output_dir: str = ""

    def classify(self) -> str:
        """Auto-detect architecture family from parameters."""
        if self.has_dual_loader:
            return "dual_pipeline"
        if self.ntile >= 14 or self.ndpe >= 80:
            return "multi_tile"
        return "basic"

    def suggested_template(self) -> str:
        """Suggest the best matching architecture template."""
        kind = self.classify()
        mapping = {
            "basic": "basic",
            "dual_pipeline": "dual_pipeline",
            "multi_tile": "multi_tile",
        }
        return mapping.get(kind, "basic")


# =====================================================================
# PE Builder — factory function with parameters
# =====================================================================

@dataclass
class NpuPeBuilder:
    """Named NPU PE builder."""
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
# PE Catalog — pre-defined builders for NPU blocks
# =====================================================================

class NpuPeCatalog:
    """Pre-defined PE builders for NPU pipeline stages.

    Each method returns a PeBuilder configured for a specific stage.
    Templates compose these to build their architecture.
    """

    @staticmethod
    def top_scheduler(params: NpuArchParams) -> NpuPeBuilder:
        num_units = 4 if not params.has_dual_loader else 6
        unit_names = ("mvu", "evrf", "mfu", "ld") if not params.has_dual_loader else (
            "mvu", "evrf0", "mfu0", "mfu1", "ld0", "ld1"
        )
        return NpuPeBuilder(
            name="TopScheduler", pe_type="npu_top_scheduler",
            description="Top-level scheduler: instruction chain + multi-unit dispatch",
            behavior_fn=lambda: TemplateRegistry.get("npu_top_scheduler")(
                num_units=num_units, unit_names=unit_names,
            ),
            inputs=[
                _ins("i_start"), _ins("minst_chain_wr_en"),
                _ins("minst_chain_wr_addr", 9), _ins("minst_chain_wr_din", 130),
                _ins("pc_start_offset", 9),
            ] + [
                _ins(f"i_{u}_minst_rd_rdy") for u in unit_names
            ],
            outputs=[
                _out("o_done"),
            ] + [
                _out(f"o_{u}_minst_rd_rdy") for u in unit_names
            ] + [
                _out(f"o_{u}_minst_rd_dout", 32) for u in unit_names
            ],
        )

    @staticmethod
    def mvu_scheduler(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="MVU_Scheduler", pe_type="mvu_scheduler",
            description="MVU scheduler: macro→micro decode with loop unrolling",
            behavior_fn=lambda: TemplateRegistry.get("mvu_scheduler")(
                miw=params.scheduler_miw,
                uiw=params.scheduler_uiw,
                loop_depth=params.scheduler_loop_depth,
                unroll_factor=params.scheduler_unroll_factor,
            ),
            inputs=[
                _ins("minst_wr_en"), _ins("minst_wr_din", params.scheduler_miw),
                _ins("uinst_rd_en"),
            ],
            outputs=[
                _out("minst_wr_rdy"), _out("uinst_rd_rdy"),
                _out("uinst_rd_dout", params.scheduler_uiw),
            ],
        )

    @staticmethod
    def mvu_datapath(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="MVU_Datapath", pe_type="mvu_datapath",
            description=f"MVU datapath: {params.ntile}×{params.ndpe} MAC array",
            behavior_fn=lambda: TemplateRegistry.get("mvu_datapath")(
                ew=params.ew, accw=params.accw, dotw=params.dotw,
                ntile=params.ntile, ndpe=params.ndpe,
                vrf_depth=params.vrf_depth, nvrf=params.nvrf,
            ),
            inputs=[
                _ins("start"), _ins("vrf_wr_en"),
                _ins("vrf_wr_addr", 9), _ins("vrf_wr_data", params.accw),
            ],
            outputs=[
                _out("busy"), _out("done"),
                _out("tile_done", 32),
            ],
        )

    @staticmethod
    def evrf_scheduler(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="EVRF_Scheduler", pe_type="evrf_scheduler",
            description="eVRF scheduler: macro→micro decode",
            behavior_fn=lambda: TemplateRegistry.get("evrf_scheduler")(
                miw=15, uiw=14,
                loop_depth=params.scheduler_loop_depth // 2,
            ),
            inputs=[
                _ins("minst_wr_en"), _ins("minst_wr_din", 15),
                _ins("uinst_rd_en"),
            ],
            outputs=[
                _out("minst_wr_rdy"), _out("uinst_rd_rdy"),
                _out("uinst_rd_dout", 14),
            ],
        )

    @staticmethod
    def evrf_datapath(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="EVRF_Datapath", pe_type="evrf_datapath",
            description=f"eVRF datapath: {params.evrf_num_banks}-banked pipeline",
            behavior_fn=lambda: TemplateRegistry.get("evrf_datapath")(
                accw=params.accw, ndpe=params.ndpe,
                num_banks=params.evrf_num_banks,
                bank_latency=params.evrf_bank_latency,
            ),
            inputs=[
                _ins("data_wr_en"), _ins("data_wr_din", params.accw),
            ],
            outputs=[
                _out("busy"), _out("done"),
                _out("data_rd_dout", params.accw),
            ],
        )

    @staticmethod
    def mfu_scheduler(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="MFU_Scheduler", pe_type="mfu_scheduler",
            description="MFU scheduler: macro→micro decode for multi-function unit",
            behavior_fn=lambda: TemplateRegistry.get("mfu_scheduler")(
                miw=25, uiw=24,
                loop_depth=params.scheduler_loop_depth // 2,
            ),
            inputs=[
                _ins("minst_wr_en"), _ins("minst_wr_din", 25),
                _ins("uinst_rd_en"),
            ],
            outputs=[
                _out("minst_wr_rdy"), _out("uinst_rd_rdy"),
                _out("uinst_rd_dout", 24),
            ],
        )

    @staticmethod
    def mfu_datapath(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="MFU_Datapath", pe_type="mfu_datapath",
            description=f"MFU datapath: {params.num_mfu_funcs} functions, {params.mfu_pipeline_stages} stages",
            behavior_fn=lambda: TemplateRegistry.get("mfu_datapath")(
                num_funcs=params.num_mfu_funcs,
                ew=params.ew, accw=params.accw,
                pipeline_stages=params.mfu_pipeline_stages,
            ),
            inputs=[
                _ins("data_wr_en"), _ins("data_wr_din", params.accw),
                _ins("func_op", 3),
            ],
            outputs=[
                _out("busy"), _out("done"),
                _out("data_rd_dout", params.accw),
            ],
        )

    @staticmethod
    def ld_scheduler(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="LD_Scheduler", pe_type="ld_scheduler",
            description="LD scheduler: macro→micro decode for load/store",
            behavior_fn=lambda: TemplateRegistry.get("ld_scheduler")(
                miw=35, uiw=34,
                loop_depth=params.scheduler_loop_depth // 2,
            ),
            inputs=[
                _ins("minst_wr_en"), _ins("minst_wr_din", 35),
                _ins("uinst_rd_en"),
            ],
            outputs=[
                _out("minst_wr_rdy"), _out("uinst_rd_rdy"),
                _out("uinst_rd_dout", 34),
            ],
        )

    @staticmethod
    def ld_datapath(params: NpuArchParams) -> NpuPeBuilder:
        return NpuPeBuilder(
            name="LD_Datapath", pe_type="ld_datapath",
            description=f"LD datapath: FIFO-based load/store unit",
            behavior_fn=lambda: TemplateRegistry.get("ld_datapath")(
                ew=params.ew, accw=params.accw,
                in_fifo_depth=params.ld_fifo_depth,
                out_fifo_depth=params.ld_fifo_depth,
                wb_fifo_depth=params.ld_fifo_depth,
            ),
            inputs=[
                _ins("in_wr_en"), _ins("out_rd_en"),
            ],
            outputs=[
                _out("in_wr_rdy"), _out("out_rd_rdy"),
                _out("out_rd_dout", params.accw),
                _out("result_count", 32),
                _out("vrf_wr_en"), _out("vrf_wr_data", params.accw),
            ],
        )

    @staticmethod
    def datapath(params: NpuArchParams, name: str = "Datapath",
                 pe_type: str = "npu_scheduler", operation: str = "pass_through",
                 inputs: Optional[List[PortDesc]] = None,
                 outputs: Optional[List[PortDesc]] = None,
                 description: str = "") -> NpuPeBuilder:
        """Generic datapath PE for custom blocks."""
        return NpuPeBuilder(
            name=name, pe_type=pe_type,
            description=description,
            behavior_fn=lambda: TemplateRegistry.get("npu_scheduler")(),
            inputs=inputs or [_ins("input", 32)],
            outputs=outputs or [_out("output", 32)],
        )


# =====================================================================
# NpuArchTemplate — base class for architecture templates
# =====================================================================

class NpuArchTemplate(ABC):
    """Base class for NPU architecture templates.

    Subclasses override:
    - family_name: human-readable name
    - build_pes(): list of NpuPeBuilder instances
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

    def default_params(self) -> NpuArchParams:
        return NpuArchParams()

    @abstractmethod
    def build_pes(self, params: NpuArchParams) -> List[NpuPeBuilder]:
        pass

    @abstractmethod
    def build_interconnects(self, params: NpuArchParams) -> List[Tuple[str, str, List[str]]]:
        pass

    def build(self, params: Optional[NpuArchParams] = None) -> ArchDefinition:
        """Build full ArchDefinition from parameters."""
        if params is None:
            params = self.default_params()

        pe_builders = self.build_pes(params)
        connections = self.build_interconnects(params)

        arch = ArchDefinition(
            name=params.name.upper().replace(" ", "_"),
            description=params.description or self.description,
            isa="npu_custom",
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

    def summarize(self, params: Optional[NpuArchParams] = None) -> str:
        """One-line summary of what this template builds."""
        if params is None:
            params = self.default_params()
        pes = self.build_pes(params)
        pe_names = [b.name for b in pes]
        return (
            f"{self.family_name}: {len(pes)} PEs [{', '.join(pe_names)}] | "
            f"ntile={params.ntile}, ndpe={params.ndpe}, ew={params.ew}"
        )


# =====================================================================
# Template: Basic NPU (single pipeline)
# =====================================================================

class BasicTemplate(NpuArchTemplate):
    """Basic NPU: single MVU → eVRF → MFU → LD pipeline.

    Simplest NPU configuration with one of each pipeline stage.
    Suitable for small-scale edge AI acceleration.
    """

    @property
    def family_name(self) -> str:
        return "Basic NPU Pipeline"

    @property
    def description(self) -> str:
        return "Single pipeline: TopScheduler → MVU → eVRF → MFU → LD"

    def default_params(self) -> NpuArchParams:
        return NpuArchParams(
            name="basic_npu",
            ntile=7, ndpe=40, ew=8, accw=32, dotw=40,
            vrf_depth=512, nvrf=12,
            scheduler_loop_depth=8,
            ppa_targets={"max_area": 100000, "min_freq_mhz": 200},
        )

    def build_pes(self, params: NpuArchParams) -> List[NpuPeBuilder]:
        catalog = NpuPeCatalog()
        return [
            catalog.top_scheduler(params),
            catalog.mvu_scheduler(params),
            catalog.mvu_datapath(params),
            catalog.evrf_scheduler(params),
            catalog.evrf_datapath(params),
            catalog.mfu_scheduler(params),
            catalog.mfu_datapath(params),
            catalog.ld_scheduler(params),
            catalog.ld_datapath(params),
        ]

    def build_interconnects(self, params: NpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("TopScheduler", "MVU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MVU_Scheduler", "MVU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MVU_Datapath", "EVRF_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "EVRF_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("EVRF_Scheduler", "EVRF_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("EVRF_Datapath", "MFU_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "MFU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MFU_Scheduler", "MFU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MFU_Datapath", "LD_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "LD_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("LD_Scheduler", "LD_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
        ]


# =====================================================================
# Template: Dual Pipeline (matches FPGA-NPU ref RTL)
# =====================================================================

class DualPipelineTemplate(NpuArchTemplate):
    """Dual-pipeline NPU with dual loaders and dual eVRF.

    Matches the reference FPGA-NPU RTL architecture:
    - Two loader instances (ld, ld1) for parallel data loading
    - Two eVRF instances for parallel VRF access
    - Single MVU with shared scheduler
    - Dual MFU instances

    Suitable for mid-range FPGA acceleration.
    """

    @property
    def family_name(self) -> str:
        return "Dual Pipeline NPU"

    @property
    def description(self) -> str:
        return "Dual pipeline: dual loader + dual eVRF + MVU + dual MFU"

    def default_params(self) -> NpuArchParams:
        return NpuArchParams(
            name="dual_pipeline_npu",
            ntile=7, ndpe=40, ew=8, accw=32, dotw=40,
            vrf_depth=512, nvrf=12,
            has_dual_loader=True,
            scheduler_loop_depth=8,
            ppa_targets={"max_area": 200000, "min_freq_mhz": 200},
        )

    def build_pes(self, params: NpuArchParams) -> List[NpuPeBuilder]:
        catalog = NpuPeCatalog()
        return [
            catalog.top_scheduler(params),
            catalog.mvu_scheduler(params),
            catalog.mvu_datapath(params),
            catalog.evrf_scheduler(params),
            catalog.evrf_datapath(params),
            catalog.mfu_scheduler(params),
            catalog.mfu_datapath(params),
            catalog.ld_scheduler(params),
            catalog.ld_datapath(params),
        ]

    def build_interconnects(self, params: NpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("TopScheduler", "MVU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MVU_Scheduler", "MVU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MVU_Datapath", "EVRF_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "EVRF_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("EVRF_Scheduler", "EVRF_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("EVRF_Datapath", "MFU_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "MFU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MFU_Scheduler", "MFU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MFU_Datapath", "LD_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "LD_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("LD_Scheduler", "LD_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
        ]


# =====================================================================
# Template: Multi-Tile NPU
# =====================================================================

class MultiTileTemplate(NpuArchTemplate):
    """Multi-tile NPU with large compute array.

    Scales NTILE and NDPE for higher throughput.
    Suitable for datacenter-class AI acceleration.
    """

    @property
    def family_name(self) -> str:
        return "Multi-Tile NPU"

    @property
    def description(self) -> str:
        return "Large-scale: 14+ tiles, 80+ DPEs per tile"

    def default_params(self) -> NpuArchParams:
        return NpuArchParams(
            name="multi_tile_npu",
            ntile=14, ndpe=80, ew=8, accw=32, dotw=40,
            vrf_depth=1024, nvrf=24,
            scheduler_loop_depth=16,
            evrf_num_banks=8,
            ppa_targets={"max_area": 500000, "min_freq_mhz": 500},
        )

    def build_pes(self, params: NpuArchParams) -> List[NpuPeBuilder]:
        catalog = NpuPeCatalog()
        return [
            catalog.top_scheduler(params),
            catalog.mvu_scheduler(params),
            catalog.mvu_datapath(params),
            catalog.evrf_scheduler(params),
            catalog.evrf_datapath(params),
            catalog.mfu_scheduler(params),
            catalog.mfu_datapath(params),
            catalog.ld_scheduler(params),
            catalog.ld_datapath(params),
        ]

    def build_interconnects(self, params: NpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("TopScheduler", "MVU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MVU_Scheduler", "MVU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MVU_Datapath", "EVRF_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "EVRF_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("EVRF_Scheduler", "EVRF_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("EVRF_Datapath", "MFU_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "MFU_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("MFU_Scheduler", "MFU_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
            ("MFU_Datapath", "LD_Datapath", ["data_wr_en", "data_wr_din"]),
            ("TopScheduler", "LD_Scheduler", ["minst_wr_en", "minst_wr_din"]),
            ("LD_Scheduler", "LD_Datapath", ["uinst_rd_en", "uinst_rd_dout"]),
        ]


# =====================================================================
# Template Registry — discover all NPU templates
# =====================================================================

_NPU_TEMPLATES: Dict[str, type] = {
    "basic": BasicTemplate,
    "dual_pipeline": DualPipelineTemplate,
    "multi_tile": MultiTileTemplate,
}


def get_template(name: str) -> NpuArchTemplate:
    """Get an NPU architecture template by name."""
    cls = _NPU_TEMPLATES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown NPU template: {name}. "
            f"Available: {list(_NPU_TEMPLATES.keys())}"
        )
    return cls()


def list_templates() -> Dict[str, str]:
    """List all available NPU templates with descriptions."""
    return {
        name: cls().family_name
        for name, cls in _NPU_TEMPLATES.items()
    }


def register_template(name: str, template_class: type):
    """Register a custom NPU architecture template."""
    if not issubclass(template_class, NpuArchTemplate):
        raise TypeError("template_class must inherit from NpuArchTemplate")
    _NPU_TEMPLATES[name] = template_class


# =====================================================================
# Custom Architecture — user-defined from scratch
# =====================================================================

class CustomNpuArchTemplate(NpuArchTemplate):
    """Custom NPU architecture built from a list of PeBuilders and connections.

    Usage:
        from skills.npu.arch_templates import CustomNpuArchTemplate, NpuPeCatalog

        params = NpuArchParams(name="my_custom")
        catalog = NpuPeCatalog()

        template = CustomNpuArchTemplate(
            family_name="My Custom NPU",
            pe_builders=[catalog.top_scheduler(params), catalog.mvu_datapath(params)],
            connections=[("TopScheduler", "MVU_Datapath", ["start"])],
        )
        arch = template.build(params)
    """

    def __init__(self, family_name: str,
                 pe_builders: List[NpuPeBuilder],
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

    def build_pes(self, params: NpuArchParams) -> List[NpuPeBuilder]:
        return self._pe_builders

    def build_interconnects(self, params: NpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return self._connections


def build_npu_arch() -> ArchDefinition:
    """Build default NPU ArchDefinition for Spec2RTL flow.

    Creates a basic NPU with TopScheduler + MVU/MFU/EVRF/LD datapaths
    and interconnects between them.
    """
    params = NpuArchParams(name="npu_default")
    template = MultiTileTemplate()
    return template.build(params)
