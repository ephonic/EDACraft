"""
skills.riscv_ooo_4core.arch_templates — Architecture Definition for 4-Core OoO RISC-V

Creates:
  - 4 × OoOCore (2-wide, out-of-order)
  - 4 × L1Cache (private I/D, MESI)
  - 4 × NoCRouter (2x2 mesh)
  - 1 × CoherenceBus (snooping)
  - 1 × L2Cache (shared)
"""
from rtlgen.arch_def import (
    ArchDefinition, ProcessingElement, PortDesc, StateDesc, InterconnectSpec,
)
from rtlgen.behaviors import TemplateRegistry
from skills.riscv_ooo_4core.behaviors import (
    ooo_core_cycle, l1_cache_cycle, coherence_bus_cycle, noc_router_cycle,
)

XLEN = 64
FLIT_WIDTH = 64
CORE_IDS = [0, 1, 2, 3]


def build_ooo_soc_arch(mesh_x: int = 2, mesh_y: int = 2) -> ArchDefinition:
    """Build 4-core OoO RISC-V SoC ArchDefinition."""
    arch = ArchDefinition(
        name="RISCV_OFO_4Core",
        description="4-core out-of-order RISC-V processor with MESI coherence over 2x2 mesh NoC",
        isa="riscv64",
    )

    pes = []
    interconnects = []

    for cid in CORE_IDS:
        cx = cid % mesh_x
        cy = cid // mesh_x

        # OoO Core
        core_pe = ProcessingElement(
            name=f"Core_{cid}",
            pe_type="ooo_core",
            behavior=ooo_core_cycle(),
            inputs=[
                PortDesc("clk", "input", 1),
                PortDesc("rst_n", "input", 1),
                PortDesc("icache_rdata", "input", XLEN),
                PortDesc("icache_valid", "input", 1),
                PortDesc("dcache_rdata", "input", XLEN),
                PortDesc("dcache_valid", "input", 1),
            ],
            outputs=[
                PortDesc("icache_req", "output", 1),
                PortDesc("icache_addr", "output", XLEN),
                PortDesc("dcache_req", "output", 1),
                PortDesc("dcache_addr", "output", XLEN),
                PortDesc("dcache_wdata", "output", XLEN),
                PortDesc("dcache_wen", "output", 1),
                PortDesc("core_stall", "output", 1),
                PortDesc("retire_valid", "output", 1),
                PortDesc("retire_count", "output", 3),
            ],
            state=[
                StateDesc("pc"), StateDesc("rob_head"), StateDesc("rob_tail"),
                StateDesc("retire_count"),
            ],
            latency=1,
            can_stall=True,
            is_pipeline_stage=True,
        )
        pes.append(core_pe)

        # L1 I-Cache
        l1i_pe = ProcessingElement(
            name=f"L1I_{cid}",
            pe_type="l1_cache",
            behavior=l1_cache_cycle(),
            inputs=[
                PortDesc("clk", "input", 1), PortDesc("rst_n", "input", 1),
                PortDesc("req", "input", 1), PortDesc("addr", "input", XLEN),
                PortDesc("fill_data", "input", XLEN), PortDesc("fill_valid", "input", 1),
                PortDesc("snoop_addr", "input", XLEN), PortDesc("snoop_invalidate", "input", 1),
            ],
            outputs=[
                PortDesc("rdata", "output", XLEN), PortDesc("valid", "output", 1),
                PortDesc("ready", "output", 1), PortDesc("miss", "output", 1),
                PortDesc("miss_addr", "output", XLEN), PortDesc("snoop_ack", "output", 1),
            ],
            state=[StateDesc("tag_ram"), StateDesc("mesi_state")],
        )
        pes.append(l1i_pe)

        # L1 D-Cache
        l1d_pe = ProcessingElement(
            name=f"L1D_{cid}",
            pe_type="l1_cache",
            behavior=l1_cache_cycle(),
            inputs=[
                PortDesc("clk", "input", 1), PortDesc("rst_n", "input", 1),
                PortDesc("req", "input", 1), PortDesc("addr", "input", XLEN),
                PortDesc("wdata", "input", XLEN), PortDesc("wen", "input", 1),
                PortDesc("fill_data", "input", XLEN), PortDesc("fill_valid", "input", 1),
                PortDesc("snoop_addr", "input", XLEN), PortDesc("snoop_invalidate", "input", 1),
            ],
            outputs=[
                PortDesc("rdata", "output", XLEN), PortDesc("valid", "output", 1),
                PortDesc("ready", "output", 1), PortDesc("miss", "output", 1),
                PortDesc("miss_addr", "output", XLEN), PortDesc("snoop_ack", "output", 1),
            ],
            state=[StateDesc("tag_ram"), StateDesc("mesi_state")],
        )
        pes.append(l1d_pe)

        # NoC Router
        noc_pe = ProcessingElement(
            name=f"NoCRouter_{cid}",
            pe_type="noc_router",
            behavior=noc_router_cycle(),
            inputs=[
                PortDesc("clk", "input", 1), PortDesc("rst_n", "input", 1),
                PortDesc("x_pos", "input", 3), PortDesc("y_pos", "input", 3),
            ],
            outputs=[],
        )
        for d in ['e','w','n','s']:
            noc_pe.inputs.append(PortDesc(f"{d}_flit", "input", FLIT_WIDTH))
            noc_pe.inputs.append(PortDesc(f"{d}_valid", "input", 1))
            noc_pe.outputs.append(PortDesc(f"{d}_ready", "output", 1))
            noc_pe.outputs.append(PortDesc(f"{d}_flit_o", "output", FLIT_WIDTH))
            noc_pe.outputs.append(PortDesc(f"{d}_valid_o", "output", 1))
        noc_pe.inputs.append(PortDesc("loc_inj_flit", "input", FLIT_WIDTH))
        noc_pe.inputs.append(PortDesc("loc_inj_valid", "input", 1))
        noc_pe.outputs.append(PortDesc("loc_inj_ready", "output", 1))
        noc_pe.outputs.append(PortDesc("loc_ej_flit", "output", FLIT_WIDTH))
        noc_pe.outputs.append(PortDesc("loc_ej_valid", "output", 1))
        noc_pe.state.append(StateDesc(f"buf_count_{d}"))
        pes.append(noc_pe)

        # Core → L1I interconnect
        interconnects.append(InterconnectSpec(
            src_pe=f"Core_{cid}", dst_pe=f"L1I_{cid}",
            signals=[
                PortDesc(f"icache_req_{cid}", "wire", 1),
                PortDesc(f"icache_addr_{cid}", "wire", XLEN),
            ],
            flow_type="handshake",
        ))

    # Coherence Bus
    coherence_pe = ProcessingElement(
        name="CoherenceBus",
        pe_type="coherence_bus",
        behavior=coherence_bus_cycle(),
        inputs=[PortDesc("clk", "input", 1), PortDesc("rst_n", "input", 1)],
        outputs=[PortDesc("snoop_valid", "output", 1), PortDesc("snoop_addr", "output", XLEN)],
    )
    for cid in CORE_IDS:
        coherence_pe.inputs.append(PortDesc(f"req_valid_{cid}", "input", 1))
        coherence_pe.inputs.append(PortDesc(f"req_addr_{cid}", "input", XLEN))
        coherence_pe.inputs.append(PortDesc(f"snoop_ack_{cid}", "input", 1))
    pes.append(coherence_pe)

    arch.processing_elements = pes
    arch.interconnects = interconnects
    return arch
