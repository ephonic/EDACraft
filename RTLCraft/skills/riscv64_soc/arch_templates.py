"""
skills.riscv64_soc.arch_templates — SoC Architecture Templates for Spec2RTL Flow

Top-level architecture definition, interconnect, model provider,
simulation, DSL generation, PPA estimation, and Verilog emission
for 64-core RISC-V SoC with directory-based MSI coherence.

Usage:
    from skills.riscv64_soc.arch_templates import build_soc_arch
    arch = build_soc_arch(mesh_x=8, mesh_y=8)
    from rtlgen import ArchSimulator
    sim = ArchSimulator(arch)
    result = sim.run(num_cycles=1000)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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

from skills.riscv64_soc.behaviors import (
    rv64_core_template,
    l1_cache_template,
    coherence_dir_template,
    l2_cache_template,
    noc_router_template,
    cluster_template,
    soc_top_template,
)
from skills.riscv64_soc.models import SoCModel
from skills.riscv64_soc.skeleton_templates import register_soc_skeleton_steps

# Global parameters
XLEN = 64
FLIT_WIDTH = 64
L1_SIZE_KB = 32
L1_WAYS = 8
L1_LINE_SIZE = 64
L2_SLICE_KB = 4
L2_WAYS = 8
DIR_ENTRIES = 64
DIR_WAYS = 4
BUFFER_DEPTH = 4
NUM_VC = 3


# =====================================================================
# SoC Model Provider
# =====================================================================

class SoC_Model(ModelProvider):
    """64-core RISC-V SoC behavioral model provider.

    Wraps SoCModel for the Spec2RTL ArchDefinition.
    """
    model_type = "riscv64_soc"

    def __init__(
        self,
        mesh_x: int = 8,
        mesh_y: int = 8,
    ):
        self.mesh_x = mesh_x
        self.mesh_y = mesh_y
        self.soc = SoCModel(mesh_x=mesh_x, mesh_y=mesh_y)

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        return self.soc.run(num_cycles=num_cycles)

    def get_status(self) -> Dict[str, Any]:
        return self.soc.get_status()


# =====================================================================
# Architecture Builder
# =====================================================================

def build_soc_arch(
    mesh_x: int = 8,
    mesh_y: int = 8,
    l1_ways: int = L1_WAYS,
    l2_ways: int = L2_WAYS,
) -> ArchDefinition:
    """Build a 64-core RISC-V SoC ArchDefinition.

    Creates:
      - 64 clusters × (RV64Core + L1Cache×2 + CoherenceDir + L2CacheSlice + NoCRouter)
      - Mesh NoC interconnects (east-west, north-south)
      - SoC_Model as behavioral model
    """
    # Register skeleton steps
    register_soc_skeleton_steps(arch_skel._TEMPLATE_STEPS)

    # Create model provider
    soc_model = SoC_Model(mesh_x=mesh_x, mesh_y=mesh_y)

    num_cores = mesh_x * mesh_y
    pes: List[ProcessingElement] = []
    interconnects: List[InterconnectSpec] = []

    for cy in range(mesh_y):
        for cx in range(mesh_x):
            cid = cy * mesh_x + cx

            # RV64 Core
            core_pe = ProcessingElement(
                name=f"Core_{cid}",
                pe_type="rv64_core",
                behavior=rv64_core_template(),
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
                    PortDesc(name="icache_ready", width=1, direction="output"),
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

            # L1 I-Cache
            l1i_pe = ProcessingElement(
                name=f"L1I_{cid}",
                pe_type="l1_cache",
                behavior=l1_cache_template(ways=l1_ways, tag="I"),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="rst_n", width=1, direction="input"),
                    PortDesc(name="req", width=1, direction="input"),
                    PortDesc(name="addr", width=XLEN, direction="input"),
                    PortDesc(name="fill_data", width=XLEN, direction="input"),
                    PortDesc(name="fill_valid", width=1, direction="input"),
                ],
                outputs=[
                    PortDesc(name="rdata", width=XLEN, direction="output"),
                    PortDesc(name="valid", width=1, direction="output"),
                    PortDesc(name="ready", width=1, direction="output"),
                    PortDesc(name="miss", width=1, direction="output"),
                    PortDesc(name="miss_addr", width=XLEN, direction="output"),
                ],
                state=[
                    StateDesc(name="tag_ram"),
                    StateDesc(name="msi_state"),
                ],
            )
            pes.append(l1i_pe)

            # L1 D-Cache
            l1d_pe = ProcessingElement(
                name=f"L1D_{cid}",
                pe_type="l1_cache",
                behavior=l1_cache_template(ways=l1_ways, tag="D"),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="rst_n", width=1, direction="input"),
                    PortDesc(name="req", width=1, direction="input"),
                    PortDesc(name="addr", width=XLEN, direction="input"),
                    PortDesc(name="wdata", width=XLEN, direction="input"),
                    PortDesc(name="wen", width=1, direction="input"),
                    PortDesc(name="fill_data", width=XLEN, direction="input"),
                    PortDesc(name="fill_valid", width=1, direction="input"),
                ],
                outputs=[
                    PortDesc(name="rdata", width=XLEN, direction="output"),
                    PortDesc(name="valid", width=1, direction="output"),
                    PortDesc(name="ready", width=1, direction="output"),
                    PortDesc(name="miss", width=1, direction="output"),
                    PortDesc(name="miss_addr", width=XLEN, direction="output"),
                ],
                state=[
                    StateDesc(name="tag_ram"),
                    StateDesc(name="msi_state"),
                ],
            )
            pes.append(l1d_pe)

            # Coherence Directory
            dir_pe = ProcessingElement(
                name=f"CoherenceDir_{cid}",
                pe_type="coherence_dir",
                behavior=coherence_dir_template(),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="rst_n", width=1, direction="input"),
                    PortDesc(name="req_type", width=2, direction="input"),
                    PortDesc(name="req_core", width=6, direction="input"),
                    PortDesc(name="req_addr", width=XLEN, direction="input"),
                    PortDesc(name="snoop_ack", width=1, direction="input"),
                ],
                outputs=[
                    PortDesc(name="grant_state", width=2, direction="output"),
                    PortDesc(name="snoop_req", width=1, direction="output"),
                    PortDesc(name="snoop_addr", width=XLEN, direction="output"),
                    PortDesc(name="dir_ready", width=1, direction="output"),
                ],
                state=[
                    StateDesc(name="directory_entries"),
                    StateDesc(name="sharers_bitmask"),
                ],
            )
            pes.append(dir_pe)

            # L2 Cache Slice
            l2_pe = ProcessingElement(
                name=f"L2Slice_{cid}",
                pe_type="l2_cache",
                behavior=l2_cache_template(ways=l2_ways),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="rst_n", width=1, direction="input"),
                    PortDesc(name="req", width=1, direction="input"),
                    PortDesc(name="addr", width=XLEN, direction="input"),
                    PortDesc(name="wdata", width=XLEN, direction="input"),
                    PortDesc(name="wen", width=1, direction="input"),
                    PortDesc(name="dram_data", width=XLEN, direction="input"),
                    PortDesc(name="dram_valid", width=1, direction="input"),
                ],
                outputs=[
                    PortDesc(name="rdata", width=XLEN, direction="output"),
                    PortDesc(name="valid", width=1, direction="output"),
                    PortDesc(name="ready", width=1, direction="output"),
                    PortDesc(name="dram_req", width=1, direction="output"),
                    PortDesc(name="dram_addr", width=XLEN, direction="output"),
                ],
                state=[
                    StateDesc(name="tag_ram"),
                    StateDesc(name="lru"),
                ],
            )
            pes.append(l2_pe)

            # NoC Router
            router_pe = ProcessingElement(
                name=f"NoCRouter_{cid}",
                pe_type="noc_router",
                behavior=noc_router_template(x=cx, y=cy),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="rst_n", width=1, direction="input"),
                    # East input
                    PortDesc(name="e_flit", width=FLIT_WIDTH, direction="input"),
                    PortDesc(name="e_valid", width=1, direction="input"),
                    PortDesc(name="e_ready", width=1, direction="input"),
                    # West input
                    PortDesc(name="w_flit", width=FLIT_WIDTH, direction="input"),
                    PortDesc(name="w_valid", width=1, direction="input"),
                    PortDesc(name="w_ready", width=1, direction="input"),
                    # North input
                    PortDesc(name="n_flit", width=FLIT_WIDTH, direction="input"),
                    PortDesc(name="n_valid", width=1, direction="input"),
                    PortDesc(name="n_ready", width=1, direction="input"),
                    # South input
                    PortDesc(name="s_flit", width=FLIT_WIDTH, direction="input"),
                    PortDesc(name="s_valid", width=1, direction="input"),
                    PortDesc(name="s_ready", width=1, direction="input"),
                    # Local inject
                    PortDesc(name="j_flit", width=FLIT_WIDTH, direction="input"),
                    PortDesc(name="j_valid", width=1, direction="input"),
                    PortDesc(name="j_ready", width=1, direction="input"),
                ],
                outputs=[
                    # East output
                    PortDesc(name="e_flit_out", width=FLIT_WIDTH, direction="output"),
                    PortDesc(name="e_valid_out", width=1, direction="output"),
                    PortDesc(name="e_ready_out", width=1, direction="output"),
                    # West output
                    PortDesc(name="w_flit_out", width=FLIT_WIDTH, direction="output"),
                    PortDesc(name="w_valid_out", width=1, direction="output"),
                    PortDesc(name="w_ready_out", width=1, direction="output"),
                    # North output
                    PortDesc(name="n_flit_out", width=FLIT_WIDTH, direction="output"),
                    PortDesc(name="n_valid_out", width=1, direction="output"),
                    PortDesc(name="n_ready_out", width=1, direction="output"),
                    # South output
                    PortDesc(name="s_flit_out", width=FLIT_WIDTH, direction="output"),
                    PortDesc(name="s_valid_out", width=1, direction="output"),
                    PortDesc(name="s_ready_out", width=1, direction="output"),
                    # Local eject
                    PortDesc(name="j_flit_out", width=FLIT_WIDTH, direction="output"),
                    PortDesc(name="j_valid_out", width=1, direction="output"),
                    PortDesc(name="j_ready_out", width=1, direction="output"),
                ],
                state=[
                    StateDesc(name="e_buf_count"),
                    StateDesc(name="w_buf_count"),
                    StateDesc(name="n_buf_count"),
                    StateDesc(name="s_buf_count"),
                    StateDesc(name="j_buf_count"),
                ],
            )
            pes.append(router_pe)

            # Per-cluster interconnects
            # Core → L1I
            interconnects.append(InterconnectSpec(
                src_pe=f"Core_{cid}", dst_pe=f"L1I_{cid}",
                signals=[
                    PortDesc(name="icache_req", width=1, direction="output"),
                    PortDesc(name="icache_addr", width=XLEN, direction="output"),
                ],
                flow_type="stream",
            ))
            # Core → L1D
            interconnects.append(InterconnectSpec(
                src_pe=f"Core_{cid}", dst_pe=f"L1D_{cid}",
                signals=[
                    PortDesc(name="dcache_req", width=1, direction="output"),
                    PortDesc(name="dcache_addr", width=XLEN, direction="output"),
                    PortDesc(name="dcache_wdata", width=XLEN, direction="output"),
                    PortDesc(name="dcache_wen", width=1, direction="output"),
                ],
                flow_type="stream",
            ))
            # L1I/L1D → CoherenceDir
            interconnects.append(InterconnectSpec(
                src_pe=f"L1I_{cid}", dst_pe=f"CoherenceDir_{cid}",
                signals=[
                    PortDesc(name="miss", width=1, direction="output"),
                    PortDesc(name="miss_addr", width=XLEN, direction="output"),
                ],
                flow_type="handshake",
            ))
            # CoherenceDir → L2Slice
            interconnects.append(InterconnectSpec(
                src_pe=f"CoherenceDir_{cid}", dst_pe=f"L2Slice_{cid}",
                signals=[
                    PortDesc(name="req", width=1, direction="output"),
                    PortDesc(name="req_addr", width=XLEN, direction="output"),
                ],
                flow_type="handshake",
            ))
            # L2Slice → NoCRouter
            interconnects.append(InterconnectSpec(
                src_pe=f"L2Slice_{cid}", dst_pe=f"NoCRouter_{cid}",
                signals=[
                    PortDesc(name="dram_req", width=1, direction="output"),
                    PortDesc(name="dram_addr", width=XLEN, direction="output"),
                ],
                flow_type="handshake",
            ))

    # Mesh interconnects (router-to-router)
    for cy in range(mesh_y):
        for cx in range(mesh_x):
            cid = cy * mesh_x + cx
            src = f"NoCRouter_{cid}"

            # East → neighbor West
            if cx + 1 < mesh_x:
                dst = f"NoCRouter_{(cy * mesh_x) + (cx + 1)}"
                interconnects.append(InterconnectSpec(
                    src_pe=src, dst_pe=dst,
                    signals=[
                        PortDesc(name="e_flit_out", width=FLIT_WIDTH, direction="output"),
                        PortDesc(name="e_valid_out", width=1, direction="output"),
                    ],
                    flow_type="stream",
                ))
            # South → neighbor North
            if cy + 1 < mesh_y:
                dst = f"NoCRouter_{((cy + 1) * mesh_x) + cx}"
                interconnects.append(InterconnectSpec(
                    src_pe=src, dst_pe=dst,
                    signals=[
                        PortDesc(name="s_flit_out", width=FLIT_WIDTH, direction="output"),
                        PortDesc(name="s_valid_out", width=1, direction="output"),
                    ],
                    flow_type="stream",
                ))

    # Build architecture
    arch = ArchDefinition(
        name=f"RISCV64_SoC_{mesh_x}x{mesh_y}",
        description=f"{num_cores}-core RISC-V SoC with {mesh_x}×{mesh_y} mesh NoC, directory-based MSI coherence",
        processing_elements=pes,
        interconnects=interconnects,
        model=soc_model,
    )

    return arch


def build_4core_soc_arch() -> ArchDefinition:
    """Preferred four-core configuration for the skill/PPA/RTL flow."""
    return build_soc_arch(mesh_x=2, mesh_y=2)


# Convenience alias
build_riscv64_soc = build_soc_arch
