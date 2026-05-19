"""
skills.gpgpu.arch_templates — GPGPU Architecture Template System

Extensible architecture templates that generate ArchDefinition from
user requirements. Users select a template family (basic, compute cluster,
stream processor, etc.), customize parameters, and the template builds
the full architecture.

Architecture families:
  - basic:         Single CU with warp scheduler (minimal GPU)
  - compute_cluster: Multiple CUs with shared memory fabric
  - stream_processor: SIMD-wide vector processors (like older shaders)
  - multi_cu:      Full GPGPU with many CUs, LDS, arbitration

Custom architectures:
  Users can subclass GpgpuArchTemplate and override build_pes() /
  build_interconnects() to define their own micro-architectures.

Usage:
    from skills.gpgpu.arch_templates import ComputeClusterTemplate, GpgpuArchParams

    params = GpgpuArchParams(num_cus=8, warps_per_cu=16, vgpr_per_cu=256)
    template = ComputeClusterTemplate(params)
    arch = template.build()
"""
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    ArchDefinition, InterconnectSpec, ModelProvider,
)
from rtlgen.behaviors import TemplateRegistry

# Import behaviors to register GPGPU templates in TemplateRegistry
import skills.gpgpu.behaviors  # noqa: F401

from skills.gpgpu.models import GPGPUModel


# =====================================================================
# Architecture Parameters — user-facing config
# =====================================================================

@dataclass
class GpgpuArchParams:
    """GPGPU architecture parameters.

    These map to the micro-architecture in a predictable way.
    Users set these directly; templates translate them into PE configs.
    """
    name: str = "my_gpu"
    description: str = ""
    isa: str = "simt"  # simt, simd, vliw

    # Compute units (CU/SM)
    num_cus: int = 4              # number of compute units
    warps_per_cu: int = 8         # warps/wavefronts per CU
    threads_per_warp: int = 32    # threads per warp (wavefront width)

    # Register files
    vgpr_per_cu: int = 256        # vector GPRs per CU
    sgpr_per_cu: int = 512        # scalar GPRs per CU

    # Local data share
    lds_size_kb: int = 64         # LDS per CU in KB
    lds_banks: int = 32           # number of LDS banks

    # Instruction fetch / dispatch
    fetch_width: int = 2          # instructions fetched per warp per cycle
    issue_width: int = 2          # instructions issued per cycle

    # Execution pipes per CU
    alu_pipes: int = 2            # vector ALU pipes
    sfu_pipes: int = 0            # special function units (sin, exp, etc.)
    has_lds: bool = True          # local data share support

    # Memory
    l2_ways: int = 16             # L2 cache associativity
    l2_size_kb: int = 256         # shared L2 cache size
    mem_bus_width: int = 256      # memory interface width (bits)

    # Scheduler
    scheduler_type: str = "round_robin"  # round_robin, priority, lottery

    # PPA targets
    ppa_targets: Dict[str, Any] = field(default_factory=lambda: {
        "max_area": 200000,
        "min_freq_mhz": 1000,
    })

    # Simulation
    sim_cycles: int = 20

    # Output
    output_dir: str = ""

    def classify(self) -> str:
        """Auto-detect architecture family from parameters."""
        if self.num_cus <= 1 and self.alu_pipes <= 1:
            return "basic"
        if self.alu_pipes > 2 and not self.has_lds:
            return "stream_processor"
        if self.num_cus >= 4 and self.has_lds:
            return "compute_cluster"
        if self.num_cus >= 8:
            return "multi_cu"
        return "compute_cluster"

    def suggested_template(self) -> str:
        """Suggest the best matching architecture template."""
        kind = self.classify()
        mapping = {
            "basic": "basic",
            "compute_cluster": "compute_cluster",
            "stream_processor": "stream_processor",
            "multi_cu": "multi_cu",
            "custom": "compute_cluster",
        }
        return mapping.get(kind, "compute_cluster")

    def __post_init__(self):
        """Auto-adjust PPA targets based on architecture class."""
        kind = self.classify()
        if kind == "basic" and not self.ppa_targets.get("max_area"):
            self.ppa_targets.update({"max_area": 50000, "min_freq_mhz": 800})
        elif kind == "multi_cu" and not self.ppa_targets.get("min_ipc"):
            self.ppa_targets["min_ipc"] = self.num_cus * self.fetch_width


# =====================================================================
# PE Builder — factory function with parameters
# =====================================================================

@dataclass
class GpgpuPeBuilder:
    """Named PE builder for GPGPU components."""
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
# GPGPU PE Catalog
# =====================================================================

class GpgpuPeCatalog:
    """Pre-defined PE builders for GPGPU components."""

    @staticmethod
    def cta_scheduler(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="CTA_Scheduler", pe_type="cta_scheduler",
            description="CTA/Workgroup scheduler: resource allocation + dispatch to CUs",
            behavior_fn=lambda: TemplateRegistry.get("cta_scheduler")(
                num_cus=params.num_cus,
                vgpr_per_cu=params.vgpr_per_cu,
                sgpr_per_cu=params.sgpr_per_cu,
                lds_size_kb=params.lds_size_kb,
            ),
            inputs=[
                _ins("wg_valid"), _ins("cu_ready", params.num_cus),
                _ins("wg_done", params.num_cus),
            ],
            outputs=[
                _out("wg_ready"), _out("dispatch_valid"),
                _out("dispatch_cu_id", 8), _out("host_notify"),
            ],
        )

    @staticmethod
    def warp_scheduler(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="Warp_Scheduler", pe_type="warp_scheduler",
            description="Per-CU warp scheduler: active mask tracking + pipe dispatch",
            behavior_fn=lambda: TemplateRegistry.get("warp_scheduler")(
                num_warps=params.warps_per_cu,
            ),
            inputs=[
                _ins("warp_end"), _ins("warp_req", params.warps_per_cu),
                _ins("pipe_ready"),
            ],
            outputs=[
                _out("active_count", 8), _out("next_warp_id", 8),
                _out("dispatch_valid"), _out("dispatch_warp_id", 8),
            ],
        )

    @staticmethod
    def sm_pipe(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="SM_Pipe", pe_type="pipe",
            description="SM execution pipe: fetch/decode/issue/execute/writeback",
            behavior_fn=lambda: TemplateRegistry.get("datapath")(operation="pass_through"),
            inputs=[
                _ins("fetch_valid"), _ins("fetch_pc", 32),
                _ins("issue_en"), _ins("wb_ack"),
            ],
            outputs=[
                _out("pipe_busy"), _out("wb_valid"),
                _out("wb_pc", 32), _out("fetch_ready"),
            ],
        )

    @staticmethod
    def shared_mem(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="SharedMem", pe_type="shared_mem",
            description="Local data share (LDS): multi-bank SRAM with conflict detection",
            behavior_fn=lambda: TemplateRegistry.get("fifo")(depth=64),
            inputs=[
                _ins("req_valid"), _ins("req_rd"), _ins("req_addr", 16),
                _ins("req_wdata", 32), _ins("req_wen"),
            ],
            outputs=[
                _out("req_ready"), _out("resp_valid"),
                _out("resp_rdata", 32), _out("bank_conflict"),
            ],
        )

    @staticmethod
    def warp_arbiter(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="WarpArbiter", pe_type="arbiter",
            description="Warp instruction arbiter: select among ready warps",
            behavior_fn=lambda: TemplateRegistry.get("axi_handshake")(direction="slave"),
            inputs=[
                _ins("req_valid", params.warps_per_cu),
                _ins("req_warp_id", 8 * params.warps_per_cu),
            ],
            outputs=[
                _out("grant_valid"), _out("grant_warp_id", 8),
                _out("grant_onehot", params.warps_per_cu),
            ],
        )

    @staticmethod
    def pop_cnt(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="PopCnt", pe_type="pop_cnt",
            description="Population count: count active warps/instructions",
            behavior_fn=lambda: TemplateRegistry.get("datapath")(operation="pass_through"),
            inputs=[_ins("vec_in", 32)],
            outputs=[_out("count", 8)],
        )

    @staticmethod
    def vgpr_bank(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="VGPR_Bank", pe_type="vgpr",
            description="Vector GPR bank: multi-port register file for warp contexts",
            behavior_fn=lambda: TemplateRegistry.get("fifo")(depth=params.vgpr_per_cu),
            inputs=[
                _ins("rd_en"), _ins("wr_en"), _ins("addr", 8),
                _ins("wdata", 32),
            ],
            outputs=[
                _out("rdata", 32), _out("bank_busy"),
            ],
        )

    @staticmethod
    def l2_cache(params: GpgpuArchParams) -> GpgpuPeBuilder:
        return GpgpuPeBuilder(
            name="L2_Cache", pe_type="l2_cache",
            description="Shared L2 cache: crossbar-connected, multi-way set-associative",
            behavior_fn=lambda: TemplateRegistry.get("fifo")(depth=32),
            inputs=[
                _ins("cu_req_valid", params.num_cus),
                _ins("cu_req_rd", params.num_cus),
                _ins("cu_req_addr", 32 * params.num_cus),
                _ins("cu_req_wdata", 32 * params.num_cus),
                _ins("cu_req_wen", params.num_cus),
            ],
            outputs=[
                _out("cu_req_ready", params.num_cus),
                _out("cu_resp_valid", params.num_cus),
                _out("cu_resp_rdata", 32 * params.num_cus),
                _out("mem_req_valid"),
            ],
        )


# =====================================================================
# GpgpuArchTemplate — base class
# =====================================================================

class GpgpuArchTemplate(ABC):
    """Base class for GPGPU architecture templates.

    Subclasses override:
    - family_name: human-readable name
    - build_pes(): list of GpgpuPeBuilder instances
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

    def default_params(self) -> GpgpuArchParams:
        return GpgpuArchParams()

    @abstractmethod
    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        pass

    @abstractmethod
    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        pass

    def build(self, params: Optional[GpgpuArchParams] = None) -> ArchDefinition:
        """Build full ArchDefinition from parameters."""
        if params is None:
            params = self.default_params()

        pe_builders = self.build_pes(params)
        connections = self.build_interconnects(params)

        # Create SIMT model
        simt_model = SIMT_Model(num_cus=params.num_cus,
                                warps_per_cu=params.warps_per_cu)

        arch = ArchDefinition(
            name=params.name.upper().replace(" ", "_"),
            description=params.description or self.description,
            isa=params.isa,
            model=simt_model,
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

    def summarize(self, params: Optional[GpgpuArchParams] = None) -> str:
        """One-line summary of what this template builds."""
        if params is None:
            params = self.default_params()
        pes = self.build_pes(params)
        pe_names = [b.name for b in pes]
        return (
            f"{self.family_name}: {len(pes)} PEs [{', '.join(pe_names)}] | "
            f"CUs={params.num_cus}, warps/CU={params.warps_per_cu}"
        )


# =====================================================================
# SIMT Model Provider
# =====================================================================

class SIMT_Model(ModelProvider):
    """SIMT execution model for GPGPU behavioral simulation."""
    model_type = "simt"

    def __init__(self, num_cus: int = 4, warps_per_cu: int = 8):
        self.num_cus = num_cus
        self.warps_per_cu = warps_per_cu
        self.gpu = GPGPUModel("SIMT_Model")
        self.gpu.configure(
            grid_dim=(num_cus, 1, 1),
            block_dim=(warps_per_cu, 1, 1),
        )

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "warp_schedule":
            if self.gpu.state.active_warps:
                warp_id = self.gpu.state.active_warps[0]
                return {"warp_id": warp_id, "executed": True}
            return {"warp_id": -1, "executed": False}
        if name == "resource_check":
            cu_id = kwargs.get("cu_id", 0)
            return {
                "vgpr_available": self.gpu.state.threads_per_block() > 0,
                "lds_available": True,
            }
        if name == "step":
            self.gpu._step()
            return {"cycle": self.gpu.state.cycle_count}
        if name == "status":
            return self.gpu.get_status()
        return None


# =====================================================================
# Template: Basic Single-CU GPU
# =====================================================================

class BasicGpuTemplate(GpgpuArchTemplate):
    """Minimal single-CU GPU with warp scheduler.

    Architecture: Warp_Scheduler → SM_Pipe → SharedMem
    Suitable for simple graphics and embedded compute.
    """

    @property
    def family_name(self) -> str:
        return "Basic Single-CU GPU"

    @property
    def description(self) -> str:
        return "Minimal GPU: single CU, warp scheduler, basic LDS"

    def default_params(self) -> GpgpuArchParams:
        return GpgpuArchParams(
            name="basic_gpu",
            num_cus=1, warps_per_cu=4,
            vgpr_per_cu=128, sgpr_per_cu=256,
            lds_size_kb=32, alu_pipes=1,
            ppa_targets={"max_area": 50000, "min_freq_mhz": 800},
        )

    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        catalog = GpgpuPeCatalog()
        return [
            catalog.warp_scheduler(params),
            catalog.sm_pipe(params),
            catalog.shared_mem(params),
        ]

    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("Warp_Scheduler", "SM_Pipe", ["dispatch_valid", "dispatch_warp_id"]),
            ("SM_Pipe", "SharedMem", ["req_valid", "req_rd", "req_addr"]),
            ("SharedMem", "SM_Pipe", ["resp_valid", "resp_rdata"]),
        ]


# =====================================================================
# Template: Compute Cluster (multi-CU)
# =====================================================================

class ComputeClusterTemplate(GpgpuArchTemplate):
    """Multiple CUs with shared L2 cache and crossbar.

    Architecture: [CU0 (WarpSched+Pipe+LDS), CU1, ...] → L2 Cache → Memory
    Each CU has independent warp scheduler and execution pipes.
    Suitable for modern GPGPU designs (CUDA-like).
    """

    @property
    def family_name(self) -> str:
        return "Compute Cluster"

    @property
    def description(self) -> str:
        return "Multi-CU GPU with L2 cache, warp schedulers per CU"

    def default_params(self) -> GpgpuArchParams:
        return GpgpuArchParams(
            name="compute_cluster",
            num_cus=4, warps_per_cu=8,
            vgpr_per_cu=256, sgpr_per_cu=512,
            lds_size_kb=64, alu_pipes=2,
            ppa_targets={"max_area": 200000, "min_freq_mhz": 1000, "min_ipc": 8},
        )

    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        catalog = GpgpuPeCatalog()
        pes = [
            catalog.cta_scheduler(params),
            catalog.warp_scheduler(params),
            catalog.sm_pipe(params),
            catalog.shared_mem(params),
            catalog.warp_arbiter(params),
            catalog.vgpr_bank(params),
        ]
        if params.l2_size_kb > 0:
            pes.append(catalog.l2_cache(params))
        return pes

    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        conns = [
            ("CTA_Scheduler", "Warp_Scheduler", ["dispatch_valid", "dispatch_cu_id"]),
            ("Warp_Scheduler", "SM_Pipe", ["dispatch_valid", "dispatch_warp_id"]),
            ("SM_Pipe", "SharedMem", ["req_valid", "req_rd", "req_addr", "req_wdata", "req_wen"]),
            ("SharedMem", "SM_Pipe", ["req_ready", "resp_valid", "resp_rdata"]),
            ("Warp_Scheduler", "WarpArbiter", ["active_count"]),
            ("WarpArbiter", "Warp_Scheduler", ["grant_valid", "grant_warp_id"]),
            ("VGPR_Bank", "SM_Pipe", ["rdata", "bank_busy"]),
            ("SM_Pipe", "VGPR_Bank", ["wb_valid"]),
        ]
        if params.l2_size_kb > 0:
            conns.extend([
                ("SharedMem", "L2_Cache", ["req_valid", "req_rd", "req_addr"]),
                ("L2_Cache", "SharedMem", ["resp_valid", "resp_rdata"]),
            ])
        return conns


# =====================================================================
# Template: Stream Processor (SIMD-wide)
# =====================================================================

class StreamProcessorTemplate(GpgpuArchTemplate):
    """SIMD-wide vector processor (older shader model).

    Architecture: Fetch/Decode → Wide SIMD ALU → Register File
    No warp scheduling, all threads execute same instruction.
    Suitable for simple vector processors and DSP.
    """

    @property
    def family_name(self) -> str:
        return "Stream Processor (SIMD)"

    @property
    def description(self) -> str:
        return "SIMD-wide vector processor: no warps, all threads in lockstep"

    def default_params(self) -> GpgpuArchParams:
        return GpgpuArchParams(
            name="stream_proc",
            num_cus=1, warps_per_cu=1,
            threads_per_warp=64,
            vgpr_per_cu=512, sgpr_per_cu=0,
            lds_size_kb=0, has_lds=False,
            alu_pipes=4,
            ppa_targets={"max_area": 100000, "min_freq_mhz": 600},
        )

    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        catalog = GpgpuPeCatalog()
        return [
            catalog.sm_pipe(params),
            catalog.vgpr_bank(params),
            catalog.pop_cnt(params),
        ]

    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("SM_Pipe", "VGPR_Bank", ["req_valid", "req_rd", "req_addr", "req_wdata", "req_wen"]),
            ("VGPR_Bank", "SM_Pipe", ["req_ready", "resp_valid", "resp_rdata"]),
            ("SM_Pipe", "PopCnt", ["wb_valid"]),
            ("PopCnt", "SM_Pipe", ["count"]),
        ]


# =====================================================================
# Template: Multi-CU GPGPU
# =====================================================================

class MultiCuTemplate(GpgpuArchTemplate):
    """Full GPGPU with many CUs, full arbitration, and L2.

    Architecture: CTA Scheduler → [CU0..CUN] → L2 → Memory
    Features: CTA dispatch, per-CU warp scheduling, arbitration,
    VGPR banks, LDS, L2 cache.
    Suitable for high-performance compute accelerators.
    """

    @property
    def family_name(self) -> str:
        return "Multi-CU GPGPU"

    @property
    def description(self) -> str:
        return "Full GPGPU: CTA dispatch, per-CU schedulers, L2 cache, arbitration"

    def default_params(self) -> GpgpuArchParams:
        return GpgpuArchParams(
            name="multi_cu_gpu",
            num_cus=8, warps_per_cu=16,
            vgpr_per_cu=256, sgpr_per_cu=512,
            lds_size_kb=64, alu_pipes=2, sfu_pipes=1,
            l2_size_kb=512, mem_bus_width=512,
            ppa_targets={"max_area": 500000, "min_freq_mhz": 1200, "min_ipc": 16},
        )

    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        catalog = GpgpuPeCatalog()
        return [
            catalog.cta_scheduler(params),
            catalog.warp_scheduler(params),
            catalog.sm_pipe(params),
            catalog.shared_mem(params),
            catalog.warp_arbiter(params),
            catalog.pop_cnt(params),
            catalog.vgpr_bank(params),
            catalog.l2_cache(params),
        ]

    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return [
            ("CTA_Scheduler", "Warp_Scheduler", ["dispatch_valid", "dispatch_cu_id"]),
            ("Warp_Scheduler", "SM_Pipe", ["dispatch_valid", "dispatch_warp_id"]),
            ("SM_Pipe", "SharedMem", ["req_valid", "req_rd", "req_addr", "req_wdata", "req_wen"]),
            ("SharedMem", "SM_Pipe", ["req_ready", "resp_valid", "resp_rdata"]),
            ("Warp_Scheduler", "WarpArbiter", ["active_count"]),
            ("WarpArbiter", "Warp_Scheduler", ["grant_valid", "grant_warp_id"]),
            ("SM_Pipe", "PopCnt", ["wb_valid"]),
            ("PopCnt", "Warp_Scheduler", ["count"]),
            ("VGPR_Bank", "SM_Pipe", ["rdata", "bank_busy"]),
            ("SM_Pipe", "VGPR_Bank", ["wb_valid"]),
            ("SharedMem", "L2_Cache", ["req_valid", "req_rd", "req_addr"]),
            ("L2_Cache", "SharedMem", ["resp_valid", "resp_rdata"]),
            ("L2_Cache", "CTA_Scheduler", ["mem_req_valid"]),
        ]


# =====================================================================
# Template Registry
# =====================================================================

_GPU_TEMPLATES: Dict[str, type] = {
    "basic": BasicGpuTemplate,
    "compute_cluster": ComputeClusterTemplate,
    "stream_processor": StreamProcessorTemplate,
    "multi_cu": MultiCuTemplate,
}


def get_template(name: str) -> GpgpuArchTemplate:
    """Get a GPGPU architecture template by name."""
    cls = _GPU_TEMPLATES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown GPGPU template: {name}. "
            f"Available: {list(_GPU_TEMPLATES.keys())}"
        )
    return cls()


def list_templates() -> Dict[str, str]:
    """List all available GPGPU templates with descriptions."""
    return {
        name: cls().family_name
        for name, cls in _GPU_TEMPLATES.items()
    }


def register_template(name: str, template_class: type):
    """Register a custom GPGPU architecture template."""
    if not issubclass(template_class, GpgpuArchTemplate):
        raise TypeError(f"Template must subclass GpgpuArchTemplate, got {template_class}")
    _GPU_TEMPLATES[name] = template_class


class CustomGpuArchTemplate(GpgpuArchTemplate):
    """User-defined GPU architecture.

    Users pass their own build_pes/build_interconnects functions.
    """

    def __init__(self, family_name: str,
                 pes_fn: Callable[[GpgpuArchParams], List[GpgpuPeBuilder]],
                 conns_fn: Callable[[GpgpuArchParams], List[Tuple[str, str, List[str]]]],
                 desc: str = "",
                 defaults: Optional[GpgpuArchParams] = None):
        self._family_name = family_name
        self._pes_fn = pes_fn
        self._conns_fn = conns_fn
        self._desc = desc
        self._defaults = defaults or GpgpuArchParams(name="custom_gpu")

    @property
    def family_name(self) -> str:
        return self._family_name

    @property
    def description(self) -> str:
        return self._desc

    def default_params(self) -> GpgpuArchParams:
        return self._defaults

    def build_pes(self, params: GpgpuArchParams) -> List[GpgpuPeBuilder]:
        return self._pes_fn(params)

    def build_interconnects(self, params: GpgpuArchParams) -> List[Tuple[str, str, List[str]]]:
        return self._conns_fn(params)
