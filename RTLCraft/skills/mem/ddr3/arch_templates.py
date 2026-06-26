"""
skills.mem.ddr3.arch_templates — DDR3 Architecture Templates

Provides:
  - build_ddr3_arch() to create ProcessingElements for DDR3 controller
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
from skills.mem.ddr3.behaviors import (
    memory_controller_template,
    dfi_sequencer_template,
)
from skills.mem.ddr3.models import DDR3Model
from rtlgen.behaviors import fifo_template, TemplateRegistry


class DDR3_Model(ModelProvider):
    """Model provider for DDR3 architecture."""

    name = "ddr3_model"
    description = "DDR3 controller behavioral model (core FSM + DFI sequencer)"

    def create_behavior(self, **kwargs):
        return DDR3Model().create_behavior(**kwargs)

    def create_testbench(self, **kwargs) -> List[Dict]:
        return DDR3Model().create_testbench(**kwargs)


def build_ddr3_arch(
    design_name: str = "DDR3Controller",
    mem_type: str = "DDR3",
    bank_count: int = 8,
    row_w: int = 15,
    col_w: int = 10,
    bus_width: int = 128,
    fifo_width: int = 16,
    fifo_depth: int = 8,
    **kwargs,
) -> ArchDefinition:
    """Build an ArchDefinition for the DDR3 controller.

    Creates 3 ProcessingElements matching the hardware hierarchy:
      DDR3FIFO — synchronous FIFO for ID tracking
      DDR3DFISeq — DFI sequencer (timing + data serialization)
      DDR3Core — core FSM (INIT/IDLE/ACT/READ/WRITE/PRE/REF)
    """
    pes: List[ProcessingElement] = []

    # 1. DDR3FIFO
    pes.append(ProcessingElement(
        name="DDR3FIFO",
        pe_type="fifo",
        description="Synchronous FIFO for ID tracking and write data buffering",
        inputs=[
            PortDesc("clk_i", 1),
            PortDesc("rst_i", 1),
            PortDesc("data_in_i", fifo_width),
            PortDesc("push_i", 1),
            PortDesc("pop_i", 1),
        ],
        outputs=[
            PortDesc("data_out_o", fifo_width),
            PortDesc("accept_o", 1),
            PortDesc("valid_o", 1),
        ],
        state=[
            StateDesc("rd_ptr", 4),
            StateDesc("wr_ptr", 4),
            StateDesc("count", 4),
        ],
        behavior=fifo_template(depth=fifo_depth, data_width=fifo_width),
    ))

    # 2. DDR3DFISeq
    trcd = kwargs.get("trcd_cycles", 2)
    trp = kwargs.get("trp_cycles", 2)
    trfc = kwargs.get("trfc_cycles", 26)

    pes.append(ProcessingElement(
        name="DDR3DFISeq",
        pe_type="dfi_sequencer",
        description="DFI sequencer: command timing delays + data serialization/deserialization",
        inputs=[
            PortDesc("clk_i", 1),
            PortDesc("rst_i", 1),
            PortDesc("command_i", 4),
            PortDesc("address_i", row_w),
            PortDesc("bank_i", 3),
            PortDesc("cke_i", 1),
            PortDesc("wrdata_i", bus_width),
            PortDesc("wrdata_mask_i", 16),
            PortDesc("dfi_rddata_i", 32),
            PortDesc("dfi_rddata_valid_i", 1),
        ],
        outputs=[
            PortDesc("accept_o", 1),
            PortDesc("rddata_o", bus_width),
            PortDesc("rddata_valid_o", 1),
            PortDesc("dfi_cs_n", 1),
            PortDesc("dfi_ras_n", 1),
            PortDesc("dfi_cas_n", 1),
            PortDesc("dfi_we_n", 1),
            PortDesc("dfi_address", row_w),
            PortDesc("dfi_bank", 3),
            PortDesc("dfi_cke", 1),
            PortDesc("dfi_wrdata_en", 1),
            PortDesc("dfi_rddata_en", 1),
            PortDesc("dfi_wrdata", 32),
            PortDesc("dfi_wrdata_mask", 4),
        ],
        state=[
            StateDesc("delay_q", 6),
            StateDesc("command_q", 4),
            StateDesc("addr_q", row_w),
            StateDesc("bank_q", 3),
            StateDesc("last_cmd", 4),
            StateDesc("wr_en_q", 16),
            StateDesc("rd_en_q", 13),
        ],
        behavior=dfi_sequencer_template(
            write_latency=6, read_latency=5, burst_len=8, data_w=32,
            wrdata_w=bus_width,
            trcd_cycles=trcd, trp_cycles=trp, trfc_cycles=trfc,
        ),
    ))

    # 3. DDR3Core
    pes.append(ProcessingElement(
        name="DDR3Core",
        pe_type="memory_controller",
        description="Core DDR3 controller FSM: initialization, refresh, row buffer management, command scheduling",
        inputs=[
            PortDesc("clk_i", 1),
            PortDesc("rst_i", 1),
            PortDesc("cfg_enable_i", 1),
            PortDesc("inport_wr_i", 16),
            PortDesc("inport_rd_i", 1),
            PortDesc("inport_addr_i", 32),
            PortDesc("inport_write_data_i", bus_width),
            PortDesc("inport_req_id_i", 16),
            PortDesc("dfi_rddata_i", 32),
            PortDesc("dfi_rddata_valid_i", 1),
        ],
        outputs=[
            PortDesc("cfg_stall_o", 1),
            PortDesc("inport_accept_o", 1),
            PortDesc("inport_ack_o", 1),
            PortDesc("inport_error_o", 1),
            PortDesc("inport_resp_id_o", 16),
            PortDesc("inport_read_data_o", bus_width),
            PortDesc("dfi_command_o", 4),
            PortDesc("dfi_address_o", row_w),
            PortDesc("dfi_bank_o", 3),
            PortDesc("dfi_cke_o", 1),
            PortDesc("dfi_wrdata_en_o", 1),
            PortDesc("dfi_rddata_en_o", 1),
        ],
        state=[
            StateDesc("state", 4),
            StateDesc("target_state", 4),
            StateDesc("refresh_timer", 20),
            StateDesc("refresh_q", 1),
            StateDesc("row_open_q", 8),
            StateDesc("write_ack_q", 1),
            StateDesc("req_id", 16),
            StateDesc("read_data", bus_width),
        ],
        behavior=memory_controller_template(
            mem_type=mem_type, bank_count=bank_count,
            row_w=row_w, col_w=col_w, burst_len=8,
            refresh_cycles=1000, addr_mapping="rbc",
        ),
    ))

    # Children for hierarchical decomposition
    pes[2].children = [pes[0], pes[1]]

    # Interconnects
    interconnects: List[InterconnectSpec] = [
        # Core → DFI sequencer
        InterconnectSpec(
            src_pe="DDR3Core", dst_pe="DDR3DFISeq",
            signals=[
                PortDesc("command", 4),
                PortDesc("address", row_w),
                PortDesc("bank", 3),
                PortDesc("cke", 1),
            ],
            flow_type="handshake",
        ),
        # DFI sequencer → Core feedback
        InterconnectSpec(
            src_pe="DDR3DFISeq", dst_pe="DDR3Core",
            signals=[
                PortDesc("accept", 1),
                PortDesc("rddata", bus_width),
                PortDesc("rddata_valid", 1),
            ],
            flow_type="handshake",
        ),
        # Core → FIFO (ID tracking)
        InterconnectSpec(
            src_pe="DDR3Core", dst_pe="DDR3FIFO",
            signals=[
                PortDesc("req_id", 16),
            ],
            flow_type="handshake",
        ),
    ]

    arch = ArchDefinition(
        name=design_name,
        isa="protocol",
        processing_elements=pes,
        interconnects=interconnects,
    )

    return arch
