"""
skills.mem.cam.arch_templates — CAM Architecture Templates

Provides:
  - build_cam_arch() to create ProcessingElements for CAM pipeline
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rtlgen.arch_def import (
    InterconnectSpec,
    PortDesc,
    ProcessingElement,
    StateDesc,
    ArchDefinition,
    ModelProvider,
)
from skills.mem.cam.behaviors import (
    priority_encoder_template,
    ram_dp_template,
    cam_srl_template,
    cam_bram_template,
    cam_top_template,
)
from skills.mem.cam.models import CAMModel


class CAM_Model(ModelProvider):
    """Model provider for CAM architecture."""

    name = "cam_model"
    description = "CAM golden-reference model (SRL and BRAM variants)"

    def create_behavior(self, **kwargs):
        return CAMModel().create_behavior(**kwargs)

    def create_testbench(self, **kwargs) -> List[Dict]:
        return CAMModel().create_testbench(**kwargs)


def build_cam_arch(
    design_name: str = "cam",
    cam_style: str = "SRL",
    data_width: int = 64,
    addr_width: int = 5,
    slice_width: int = 4,
) -> ArchDefinition:
    """Build an ArchDefinition for the CAM.

    Creates 5 ProcessingElements matching the hardware hierarchy:
      PriorityEncoder, RamDP, CamSRL, CamBRAM, CAM (top wrapper)
    """
    ram_depth = 2 ** addr_width
    slice_count = (data_width + slice_width - 1) // slice_width
    enc_width = max(addr_width, 1)

    pes: List[ProcessingElement] = []

    # 1. PriorityEncoder
    pes.append(ProcessingElement(
        name="PriorityEncoder",
        pe_type="priority_encoder",
        description=f"{ram_depth}-input recursive tree priority encoder",
        inputs=[
            PortDesc("input_unencoded", ram_depth),
        ],
        outputs=[
            PortDesc("output_valid", 1),
            PortDesc("output_encoded", enc_width),
            PortDesc("output_unencoded", ram_depth),
        ],
        state=[],
        behavior=priority_encoder_template(width=ram_depth, lsb_priority="HIGH"),
    ))

    # 2. RamDP
    pes.append(ProcessingElement(
        name="RamDP",
        pe_type="ram_dp",
        description=f"Dual-port RAM: {ram_depth}x{slice_width} read-first",
        inputs=[
            PortDesc("a_clk", 1),
            PortDesc("a_we", 1),
            PortDesc("a_addr", slice_width),
            PortDesc("a_din", ram_depth),
            PortDesc("b_clk", 1),
            PortDesc("b_we", 1),
            PortDesc("b_addr", slice_width),
            PortDesc("b_din", ram_depth),
        ],
        outputs=[
            PortDesc("a_dout", ram_depth),
            PortDesc("b_dout", ram_depth),
        ],
        state=[
            StateDesc("mem", ram_depth * slice_width),
        ],
        behavior=ram_dp_template(data_width=ram_depth, addr_width=slice_width),
    ))

    # 3. CamSRL
    pes.append(ProcessingElement(
        name="CamSRL",
        pe_type="cam_srl",
        description=f"SRL-based CAM: {data_width}-bit data, {ram_depth} entries, {slice_count} slices",
        inputs=[
            PortDesc("clk", 1),
            PortDesc("rst", 1),
            PortDesc("write_addr", addr_width),
            PortDesc("write_data", data_width),
            PortDesc("write_delete", 1),
            PortDesc("write_enable", 1),
            PortDesc("compare_data", data_width),
        ],
        outputs=[
            PortDesc("write_busy", 1),
            PortDesc("match_many", ram_depth),
            PortDesc("match_single", ram_depth),
            PortDesc("match_addr", addr_width),
            PortDesc("match", 1),
        ],
        state=[
            StateDesc("cam_state", 2),
            StateDesc("count", slice_width),
            StateDesc("write_addr_reg", addr_width),
            StateDesc("write_data_reg", slice_count * slice_width),
            StateDesc("write_delete_reg", 1),
        ],
        behavior=cam_srl_template(
            data_width=data_width, addr_width=addr_width, slice_width=slice_width,
        ),
    ))

    # 4. CamBRAM
    bram_slice_width = 9  # default BRAM slice width
    bram_slice_count = (data_width + bram_slice_width - 1) // bram_slice_width
    pes.append(ProcessingElement(
        name="CamBRAM",
        pe_type="cam_bram",
        description=f"BRAM-based CAM: {data_width}-bit data, {ram_depth} entries, {bram_slice_count} slices",
        inputs=[
            PortDesc("clk", 1),
            PortDesc("rst", 1),
            PortDesc("write_addr", addr_width),
            PortDesc("write_data", data_width),
            PortDesc("write_delete", 1),
            PortDesc("write_enable", 1),
            PortDesc("compare_data", data_width),
        ],
        outputs=[
            PortDesc("write_busy", 1),
            PortDesc("match_many", ram_depth),
            PortDesc("match_single", ram_depth),
            PortDesc("match_addr", addr_width),
            PortDesc("match", 1),
        ],
        state=[
            StateDesc("cam_state", 3),
            StateDesc("count", bram_slice_width),
            StateDesc("write_addr_reg", addr_width),
            StateDesc("write_data_reg", bram_slice_count * bram_slice_width),
            StateDesc("write_delete_reg", 1),
        ],
        behavior=cam_bram_template(
            data_width=data_width, addr_width=addr_width, slice_width=bram_slice_width,
        ),
    ))

    # 5. CAM (top wrapper)
    pes.append(ProcessingElement(
        name="CAM",
        pe_type="cam_top",
        description=f"Top-level CAM wrapper ({cam_style} backend)",
        inputs=[
            PortDesc("clk", 1),
            PortDesc("rst", 1),
            PortDesc("write_addr", addr_width),
            PortDesc("write_data", data_width),
            PortDesc("write_delete", 1),
            PortDesc("write_enable", 1),
            PortDesc("compare_data", data_width),
        ],
        outputs=[
            PortDesc("write_busy", 1),
            PortDesc("match_many", ram_depth),
            PortDesc("match_single", ram_depth),
            PortDesc("match_addr", addr_width),
            PortDesc("match", 1),
        ],
        state=[
            StateDesc("cam_state", 3),
            StateDesc("count", slice_width),
            StateDesc("write_addr_reg", addr_width),
        ],
        behavior=cam_top_template(
            cam_style=cam_style,
            data_width=data_width, addr_width=addr_width, slice_width=slice_width,
        ),
    ))

    # Interconnects (top wrapper connects to selected backend)
    interconnects: List[InterconnectSpec] = [
        # CAM → CamSRL (when SRL style)
        InterconnectSpec(
            src_pe="CAM", dst_pe="CamSRL",
            signals=[PortDesc("clk", 1), PortDesc("rst", 1),
                     PortDesc("write_addr", addr_width),
                     PortDesc("write_data", data_width),
                     PortDesc("write_delete", 1),
                     PortDesc("write_enable", 1),
                     PortDesc("compare_data", data_width)],
        ),
        # CAM → CamBRAM (when BRAM style)
        InterconnectSpec(
            src_pe="CAM", dst_pe="CamBRAM",
            signals=[PortDesc("clk", 1), PortDesc("rst", 1),
                     PortDesc("write_addr", addr_width),
                     PortDesc("write_data", data_width),
                     PortDesc("write_delete", 1),
                     PortDesc("write_enable", 1),
                     PortDesc("compare_data", data_width)],
        ),
        # CamSRL → PriorityEncoder
        InterconnectSpec(
            src_pe="CamSRL", dst_pe="PriorityEncoder",
            signals=[PortDesc("match_many", ram_depth)],
        ),
        # PriorityEncoder → CamSRL (match results)
        InterconnectSpec(
            src_pe="PriorityEncoder", dst_pe="CamSRL",
            signals=[PortDesc("output_valid", 1),
                     PortDesc("output_encoded", enc_width),
                     PortDesc("output_unencoded", ram_depth)],
        ),
        # CamBRAM → RamDP (write to slices)
        InterconnectSpec(
            src_pe="CamBRAM", dst_pe="RamDP",
            signals=[PortDesc("clk", 1), PortDesc("wr_en", 1)],
        ),
    ]

    arch = ArchDefinition(
        name=design_name,
        isa="CAM",
        processing_elements=pes,
        interconnects=interconnects,
    )

    return arch
