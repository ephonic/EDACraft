"""
skills.hetero_riscv4.arch_templates — Heterogeneous 4-Core SoC Architecture

Top-level architecture definition, interconnect, model provider,
simulation, DSL generation, PPA estimation, and Verilog emission
for heterogeneous 4-core RISC-V SoC with directory-based MSI coherence.

Layout:
  [Big0]  (0,0)  ---  [Big1]  (1,0)
    |                      |
  [Small0] (0,1)  ---  [Small1] (1,1)

Usage:
    from skills.hetero_riscv4.arch_templates import build_hetero_arch
    arch = build_hetero_arch()
    from rtlgen import ArchSimulator
    sim = ArchSimulator(arch)
    result = sim.run(num_cycles=1000)
"""
from __future__ import annotations

from typing import Any, Dict, List

from rtlgen.arch_def import (
    ArchDefinition,
    InterconnectSpec,
    ModelProvider,
    ProcessingElement,
    PortDesc,
    StateDesc,
)
from rtlgen.behaviors import TemplateRegistry
from rtlgen import arch_skel

from skills.hetero_riscv4.behaviors import (
    perf_core_template,
    eff_core_template,
    l1_cache_template,
    coherence_dir_template,
    noc_router_template,
    mesh_top_template,
)
from skills.hetero_riscv4.models import HeteroSoCModel
from skills.hetero_riscv4.skeleton_templates import register_hetero_skeleton_steps

# Global parameters
XLEN = 64
FLIT_WIDTH = 64
L1_BIG_SIZE_KB = 64
L1_BIG_WAYS = 8
L1_SMALL_SIZE_KB = 16
L1_SMALL_WAYS = 2
BUFFER_DEPTH = 4


# =====================================================================
# SoC Model Provider
# =====================================================================

class HeteroSoCModelProvider(ModelProvider):
    """Heterogeneous 4-core SoC behavioral model provider."""
    model_type = "hetero_riscv4"

    def __init__(self):
        self.soc = HeteroSoCModel()

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        return self.soc.run(num_cycles=num_cycles)

    def get_status(self) -> Dict[str, Any]:
        return self.soc.get_status()


# =====================================================================
# Architecture Builder
# =====================================================================

def build_hetero_arch() -> ArchDefinition:
    """Build heterogeneous 4-core RISC-V SoC ArchDefinition.

    Creates:
      - 2 big cores (5-stage RV64I) + 2 little cores (3-stage RV64I)
      - L1 caches per core
      - Shared coherence directory
      - 2x2 mesh NoC interconnect
    """
    # Register skeleton steps
    register_hetero_skeleton_steps(arch_skel._TEMPLATE_STEPS)

    # Create model provider
    hetero_model = HeteroSoCModelProvider()

    pes: List[ProcessingElement] = []
    interconnects: List[InterconnectSpec] = []

    # Core definitions
    core_defs = [
        {"cid": 0, "name": "PerfCore0", "pe_type": "perf_core", "x": 0, "y": 0},
        {"cid": 1, "name": "PerfCore1", "pe_type": "perf_core", "x": 1, "y": 0},
        {"cid": 2, "name": "EffCore0", "pe_type": "eff_core", "x": 0, "y": 1},
        {"cid": 3, "name": "EffCore1", "pe_type": "eff_core", "x": 1, "y": 1},
    ]

    for core_def in core_defs:
        cid = core_def["cid"]
        name = core_def["name"]
        pe_type = core_def["pe_type"]
        behavior = perf_core_template() if pe_type == "perf_core" else eff_core_template()

        # Core PE
        core_pe = ProcessingElement(
            name=name,
            pe_type=pe_type,
            behavior=behavior,
            inputs=[
                PortDesc(name="clk", width=1, direction="input"),
                PortDesc(name="rst_n", width=1, direction="input"),
                PortDesc(name="icache_rdata", width=XLEN, direction="input"),
                PortDesc(name="icache_valid", width=1, direction="input"),
                PortDesc(name="dcache_rdata", width=XLEN, direction="input"),
                PortDesc(name="dcache_valid", width=1, direction="input"),
            ],
            outputs=[
                PortDesc(name="icache_req", width=1, direction="output"),
                PortDesc(name="icache_addr", width=XLEN, direction="output"),
                PortDesc(name="dcache_req", width=1, direction="output"),
                PortDesc(name="dcache_addr", width=XLEN, direction="output"),
                PortDesc(name="dcache_wdata", width=XLEN, direction="output"),
                PortDesc(name="dcache_wen", width=1, direction="output"),
                PortDesc(name="dcache_ready", width=1, direction="output"),
                PortDesc(name="core_stall", width=1, direction="output"),
            ],
            state=[
                StateDesc(name="pc"),
                StateDesc(name="retire_count"),
            ],
        )
        pes.append(core_pe)

        # L1 Cache PE
        l1_pe = ProcessingElement(
            name=f"L1_{cid}",
            pe_type="l1_cache",
            behavior=l1_cache_template(),
            inputs=[
                PortDesc(name="clk", width=1, direction="input"),
                PortDesc(name="rst_n", width=1, direction="input"),
                PortDesc(name="req", width=1, direction="input"),
                PortDesc(name="addr", width=XLEN, direction="input"),
            ],
            outputs=[
                PortDesc(name="rdata", width=XLEN, direction="output"),
                PortDesc(name="valid", width=1, direction="output"),
                PortDesc(name="ready", width=1, direction="output"),
            ],
            state=[
                StateDesc(name="tag_ram"),
                StateDesc(name="msi_state"),
            ],
        )
        pes.append(l1_pe)

        # NoC Router PE
        router_pe = ProcessingElement(
            name=f"NoCRouter_{cid}",
            pe_type="noc_router",
            behavior=noc_router_template(x=core_def["x"], y=core_def["y"]),
            inputs=[
                PortDesc(name="clk", width=1, direction="input"),
                PortDesc(name="rst_n", width=1, direction="input"),
                PortDesc(name="e_flit", width=FLIT_WIDTH, direction="input"),
                PortDesc(name="e_valid", width=1, direction="input"),
                PortDesc(name="w_flit", width=FLIT_WIDTH, direction="input"),
                PortDesc(name="w_valid", width=1, direction="input"),
                PortDesc(name="n_flit", width=FLIT_WIDTH, direction="input"),
                PortDesc(name="n_valid", width=1, direction="input"),
                PortDesc(name="s_flit", width=FLIT_WIDTH, direction="input"),
                PortDesc(name="s_valid", width=1, direction="input"),
                PortDesc(name="loc_inj_flit", width=FLIT_WIDTH, direction="input"),
                PortDesc(name="loc_inj_valid", width=1, direction="input"),
            ],
            outputs=[
                PortDesc(name="e_flit_o", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="e_valid_o", width=1, direction="output"),
                PortDesc(name="w_flit_o", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="w_valid_o", width=1, direction="output"),
                PortDesc(name="n_flit_o", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="n_valid_o", width=1, direction="output"),
                PortDesc(name="s_flit_o", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="s_valid_o", width=1, direction="output"),
                PortDesc(name="loc_ej_flit", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="loc_ej_valid", width=1, direction="output"),
            ],
            state=[
                StateDesc(name="buf_count"),
                StateDesc(name="crossbar_state"),
            ],
        )
        pes.append(router_pe)

        # Per-core interconnects
        interconnects.append(InterconnectSpec(
            src_pe=name, dst_pe=f"L1_{cid}",
            signals=[
                PortDesc(name="req", width=1, direction="output"),
                PortDesc(name="addr", width=XLEN, direction="output"),
            ],
            flow_type="stream",
        ))

    # Coherence Directory PE (shared)
    dir_pe = ProcessingElement(
        name="CoherenceDir",
        pe_type="coherence_dir",
        behavior=coherence_dir_template(),
        inputs=[
            PortDesc(name="clk", width=1, direction="input"),
            PortDesc(name="rst_n", width=1, direction="input"),
            PortDesc(name="req_valid", width=1, direction="input"),
            PortDesc(name="req_addr", width=XLEN, direction="input"),
            PortDesc(name="req_core_id", width=6, direction="input"),
        ],
        outputs=[
            PortDesc(name="resp_valid", width=1, direction="output"),
            PortDesc(name="resp_action", width=3, direction="output"),
            PortDesc(name="probe_targets", width=4, direction="output"),
        ],
        state=[
            StateDesc(name="directory_entries"),
            StateDesc(name="sharers_bitmask"),
        ],
    )
    pes.append(dir_pe)

    # Mesh NoC interconnects (router-to-router)
    mesh_links = [
        (0, 1, "east_west"),   # PerfCore0 ↔ PerfCore1
        (2, 3, "east_west"),   # EffCore0 ↔ EffCore1
        (0, 2, "north_south"), # PerfCore0 ↔ EffCore0
        (1, 3, "north_south"), # PerfCore1 ↔ EffCore1
    ]
    for src_id, dst_id, _ in mesh_links:
        interconnects.append(InterconnectSpec(
            src_pe=f"NoCRouter_{src_id}", dst_pe=f"NoCRouter_{dst_id}",
            signals=[
                PortDesc(name="flit", width=FLIT_WIDTH, direction="output"),
                PortDesc(name="valid", width=1, direction="output"),
            ],
            flow_type="stream",
        ))

    # Mesh Top PE
    top_pe = ProcessingElement(
        name="HeteroMeshTop",
        pe_type="mesh_top",
        behavior=mesh_top_template(),
        inputs=[
            PortDesc(name="clk", width=1, direction="input"),
            PortDesc(name="rst_n", width=1, direction="input"),
        ],
        outputs=[
            PortDesc(name="core0_req", width=1, direction="output"),
            PortDesc(name="core1_req", width=1, direction="output"),
            PortDesc(name="core2_req", width=1, direction="output"),
            PortDesc(name="core3_req", width=1, direction="output"),
        ],
        state=[],
    )
    pes.append(top_pe)

    arch = ArchDefinition(
        name="HeteroRISCV4",
        description="Heterogeneous 4-core RISC-V SoC: 2 big + 2 little cores with 2x2 mesh NoC and MSI coherence",
        processing_elements=pes,
        interconnects=interconnects,
        model=hetero_model,
    )

    return arch


# Convenience alias
build_hetero_riscv4 = build_hetero_arch
