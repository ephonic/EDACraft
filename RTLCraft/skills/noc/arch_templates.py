"""
skills.noc.arch_templates — NoC Architecture Templates for Spec2RTL Flow

Top-level architecture definition, interconnect, model provider,
simulation, DSL generation, PPA estimation, and Verilog emission
for mesh-based Network-on-Chip.

Usage:
    from skills.noc.arch_templates import build_noc_arch
    arch = build_noc_arch(mesh_size=8)
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

from skills.noc.behaviors import (
    router_template,
    input_unit_template,
    output_unit_template,
    vc_alloc_template,
    crossbar_template,
    route_func_template,
    buffer_template,
    packet_gen_template,
    packet_rec_template,
    st_controler_template,
    select_gen_template,
    set_alloc_template,
    out_en_gen_template,
    network_template,
)
from skills.noc.models import NoCModel, RouterModel
from skills.noc.skeleton_templates import register_noc_skeleton_steps


# =====================================================================
# NoC Model Provider
# =====================================================================

class NoC_Model(ModelProvider):
    """NoC behavioral model provider.

    Wraps NoCModel for the Spec2RTL ArchDefinition.
    """
    model_type = "noc"

    def __init__(
        self,
        mesh_size: int = 8,
        buffer_depth: int = 4,
        flit_width: int = 64,
    ):
        self.mesh_size = mesh_size
        self.buffer_depth = buffer_depth
        self.flit_width = flit_width
        self.noc = NoCModel(
            mesh_size=mesh_size,
            buffer_depth=buffer_depth,
            flit_width=flit_width,
        )

    def run(self, num_cycles: int = 5000) -> Dict[str, Any]:
        return self.noc.run(num_cycles=num_cycles)

    def get_status(self) -> Dict[str, Any]:
        return self.noc.get_status()


# =====================================================================
# Architecture Builder
# =====================================================================

def build_noc_arch(
    mesh_size: int = 8,
    buffer_depth: int = 4,
    flit_width: int = 64,
    num_vc: int = 1,
) -> ArchDefinition:
    """Build a mesh NoC ArchDefinition.

    Creates:
      - 1 Network PE (top-level mesh wrapper)
      - mesh_size² Router PEs
      - Interconnects for east/west/north/south links
      - NoC_Model as behavioral model
    """
    # Register skeleton steps
    register_noc_skeleton_steps(arch_skel._TEMPLATE_STEPS)

    # Create model provider
    noc_model = NoC_Model(
        mesh_size=mesh_size,
        buffer_depth=buffer_depth,
        flit_width=flit_width,
    )

    # Router PEs (mesh_size × mesh_size)
    routers: List[ProcessingElement] = []
    for y in range(mesh_size):
        for x in range(mesh_size):
            pe = ProcessingElement(
                name=f"Router_{x}_{y}",
                pe_type="router",
                behavior=router_template(
                    num_ports=5,
                    buffer_depth=buffer_depth,
                    flit_width=flit_width,
                ),
                inputs=[
                    PortDesc(name="clk", width=1, direction="input"),
                    PortDesc(name="reset", width=1, direction="input"),
                    # East interface
                    PortDesc(name="e_bf_in", width=flit_width, direction="input"),
                    PortDesc(name="e_push_x", width=1, direction="input"),
                    # West interface
                    PortDesc(name="w_bf_in", width=flit_width, direction="input"),
                    PortDesc(name="w_push_x", width=1, direction="input"),
                    # North interface
                    PortDesc(name="n_bf_in", width=flit_width, direction="input"),
                    PortDesc(name="n_push_x", width=1, direction="input"),
                    # South interface
                    PortDesc(name="s_bf_in", width=flit_width, direction="input"),
                    PortDesc(name="s_push_x", width=1, direction="input"),
                    # Inject/Eject interface
                    PortDesc(name="inj_bf_in", width=flit_width, direction="input"),
                    PortDesc(name="inj_push_x", width=1, direction="input"),
                ],
                outputs=[
                    # East interface
                    PortDesc(name="e_bf_out", width=flit_width, direction="output"),
                    PortDesc(name="e_push_o", width=1, direction="output"),
                    PortDesc(name="e_em_pl", width=3, direction="output"),
                    # West interface
                    PortDesc(name="w_bf_out", width=flit_width, direction="output"),
                    PortDesc(name="w_push_o", width=1, direction="output"),
                    PortDesc(name="w_em_pl", width=3, direction="output"),
                    # North interface
                    PortDesc(name="n_bf_out", width=flit_width, direction="output"),
                    PortDesc(name="n_push_o", width=1, direction="output"),
                    PortDesc(name="n_em_pl", width=3, direction="output"),
                    # South interface
                    PortDesc(name="s_bf_out", width=flit_width, direction="output"),
                    PortDesc(name="s_push_o", width=1, direction="output"),
                    PortDesc(name="s_em_pl", width=3, direction="output"),
                    # Inject/Eject interface
                    PortDesc(name="inj_bf_out", width=flit_width, direction="output"),
                    PortDesc(name="inj_push_o", width=1, direction="output"),
                    PortDesc(name="inj_em_pl", width=3, direction="output"),
                    PortDesc(name="ej_flit", width=flit_width, direction="output"),
                    PortDesc(name="ej_valid", width=1, direction="output"),
                ],
                state=[
                    StateDesc(name="e_buf_count"),
                    StateDesc(name="w_buf_count"),
                    StateDesc(name="n_buf_count"),
                    StateDesc(name="s_buf_count"),
                    StateDesc(name="j_buf_count"),
                ],
            )
            routers.append(pe)

    # Network PE (top-level wrapper)
    net_inputs = [
        PortDesc(name="clk", width=1, direction="input"),
        PortDesc(name="reset", width=1, direction="input"),
        PortDesc(name="sys_start_i", width=1, direction="input"),
    ] + [
        PortDesc(name=f"node_{i}_inj_req", width=1, direction="input")
        for i in range(mesh_size * mesh_size)
    ] + [
        PortDesc(name=f"node_{i}_ej_valid", width=1, direction="input")
        for i in range(mesh_size * mesh_size)
    ]

    network_pe = ProcessingElement(
        name=f"NoC_{mesh_size}x{mesh_size}",
        pe_type="network",
        behavior=network_template(
            mesh_size=mesh_size,
            num_ports=5,
            buffer_depth=buffer_depth,
            flit_width=flit_width,
        ),
        inputs=net_inputs,
        outputs=[
            PortDesc(name="sys_done_o", width=1, direction="output"),
        ],
        state=[
            StateDesc(name="cycle"),
            StateDesc(name="total_injected"),
            StateDesc(name="total_received"),
        ],
    )

    # Interconnects: router-to-router links
    interconnects: List[InterconnectSpec] = []
    for y in range(mesh_size):
        for x in range(mesh_size):
            src = f"Router_{x}_{y}"
            # East → neighbor West
            if x + 1 < mesh_size:
                dst = f"Router_{x+1}_{y}"
                interconnects.append(InterconnectSpec(
                    src_pe=src,
                    dst_pe=dst,
                    signals=[
                        PortDesc(name="link_data", width=flit_width, direction="output"),
                        PortDesc(name="link_ctrl", width=1, direction="output"),
                    ],
                    flow_type="stream",
                ))
            # South → neighbor North
            if y + 1 < mesh_size:
                dst = f"Router_{x}_{y+1}"
                interconnects.append(InterconnectSpec(
                    src_pe=src,
                    dst_pe=dst,
                    signals=[
                        PortDesc(name="link_data", width=flit_width, direction="output"),
                        PortDesc(name="link_ctrl", width=1, direction="output"),
                    ],
                    flow_type="stream",
                ))

    # Build architecture
    arch = ArchDefinition(
        name=f"NoC_{mesh_size}x{mesh_size}",
        description=f"{mesh_size}×{mesh_size} mesh NoC with XY routing, {num_vc} VC(s)",
        processing_elements=routers + [network_pe],
        interconnects=interconnects,
        model=noc_model,
    )

    return arch


# Convenience alias
build_noc = build_noc_arch
