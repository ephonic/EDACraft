"""
skills.interfaces.spi.arch_templates — SPI Architecture Templates

Provides:
  - SPI_ControllerModel(ModelProvider) for architecture registration
  - build_spi_arch() to create ProcessingElements for SPI controller
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rtlgen.arch_def import (
    AgentPackage,
    InterconnectSpec,
    PortDesc,
    ProcessingElement,
    StateDesc,
    ArchDefinition,
    ModelProvider,
)
from rtlgen.arch_skel import _TEMPLATE_STEPS
from skills.interfaces.spi.behaviors import (
    spi_registers_template,
    spi_control_template,
    spi_transmit_template,
    spi_receive_template,
    spi_slave_sync_template,
    spi_slave_tx_template,
    spi_ext_sync_template,
)
from skills.interfaces.spi.models import SPIControllerModel


class SPI_ControllerModel(ModelProvider):
    """Model provider for SPI controller architecture."""

    name = "spi_controller_model"
    description = "APB-SPI controller with Master/Slave dual-mode operation"

    def create_behavior(self, **kwargs):
        return spi_control_template(**kwargs)

    def create_testbench(self, **kwargs) -> List[Dict]:
        return SPIControllerModel().create_testbench(**kwargs)


def build_spi_arch(
    design_name: str = "spi_controller",
    master_mode: bool = True,
    cpol: int = 0,
    cpha: int = 0,
    fifo_depth: int = 8,
    fifo_width: int = 32,
    num_slave_selects: int = 4,
    slave_idle_count: int = 8,
) -> ArchDefinition:
    """Build an ArchDefinition for the SPI controller.

    Creates 7 ProcessingElements matching the hardware hierarchy:
      SPIRegisters, SPIControl, SPITransmit, SPIReceive,
      SPISlaveSync, SPISlaveTX, SPIExtSync
    """
    pes: List[ProcessingElement] = []

    # 1. SPIRegisters
    pes.append(ProcessingElement(
        name="SPIRegisters",
        pe_type="spi_registers",
        description="APB register interface with 9 registers and interrupt generation",
        inputs=[
            PortDesc("psel_i", 1),
            PortDesc("penable_i", 1),
            PortDesc("pwrite_i", 1),
            PortDesc("paddr_i", 8),
            PortDesc("pwdata_i", 32),
            PortDesc("rx_full_i", 1),
            PortDesc("rx_notempty_i", 1),
            PortDesc("tx_full_i", 1),
            PortDesc("tx_notfull_i", 1),
            PortDesc("rx_fifo_i", 32),
            PortDesc("s_modf_i", 1),
            PortDesc("m_modf_i", 1),
            PortDesc("idle_spi_i", 1),
            PortDesc("tx_underflow_i", 1),
        ],
        outputs=[
            PortDesc("prdata_o", 32),
            PortDesc("interrupt_o", 1),
            PortDesc("master_o", 1),
            PortDesc("tx_push_o", 1),
            PortDesc("rx_pop_o", 1),
            PortDesc("tx_clr_o", 1),
            PortDesc("rx_clr_o", 1),
            PortDesc("cpha_o", 1),
            PortDesc("cpol_o", 1),
            PortDesc("cks_o", 1),
            PortDesc("pdec_o", 1),
            PortDesc("ss_o", num_slave_selects),
            PortDesc("spi_enable_o", 1),
            PortDesc("datasize_o", 5),
            PortDesc("baud_rate_o", 8),
            PortDesc("sic_reg_o", 8),
            PortDesc("tx_threshold_o", 3),
            PortDesc("rx_threshold_o", 3),
            PortDesc("man_cs_o", 1),
            PortDesc("man_start_en_o", 1),
            PortDesc("man_start_o", 1),
            PortDesc("modf_en_o", 1),
            PortDesc("rx_full_apb_o", 1),
            PortDesc("bsr_o", 3),
            PortDesc("m_shiften_del_en_o", 1),
        ],
        state=[
            StateDesc("config_reg", 32),
            StateDesc("imask_reg", 7),
            StateDesc("enable_reg", 1),
            StateDesc("delay_reg", 32),
        ],
        behavior=spi_registers_template(
            num_slave_selects=num_slave_selects,
            fifo_width=fifo_width,
        ),
    ))

    # 2. SPIControl
    pes.append(ProcessingElement(
        name="SPIControl",
        pe_type="spi_control",
        description="12-state Master/Slave FSM with timing generation",
        inputs=[
            PortDesc("s_shiften_i", 1),
            PortDesc("m_clocken_i", 1),
            PortDesc("s_inprogress_i", 1),
            PortDesc("cpol_i", 1),
            PortDesc("cpha_i", 1),
            PortDesc("tx_empty_i", 1),
            PortDesc("master_i", 1),
            PortDesc("spi_enable_i", 1),
            PortDesc("spi_enable_del3_i", 1),
            PortDesc("n_ss_in_sync_i", 1),
            PortDesc("datasize_i", 5),
            PortDesc("d_init_i", 8),
            PortDesc("d_after_i", 8),
            PortDesc("d_btwn_i", 8),
            PortDesc("d_nss_i", 8),
            PortDesc("baud_rate_i", 8),
            PortDesc("sclk_in_i", 1),
            PortDesc("tx_uf_i", 1),
            PortDesc("sic_reg_i", 8),
            PortDesc("man_start_en_i", 1),
            PortDesc("man_start_i", 1),
            PortDesc("modf_en_i", 1),
            PortDesc("bsr_i", 3),
            PortDesc("m_shiften_del_en_i", 1),
        ],
        outputs=[
            PortDesc("m_txsel_o", 5),
            PortDesc("tx_pop_o", 1),
            PortDesc("rx_push_o", 1),
            PortDesc("m_shiften_out_o", 1),
            PortDesc("sclk_out_o", 1),
            PortDesc("ss_valid_o", 1),
            PortDesc("s_modf_o", 1),
            PortDesc("m_modf_o", 1),
            PortDesc("idle_spi_o", 1),
            PortDesc("start_slave_o", 1),
            PortDesc("tx_underflow_o", 1),
            PortDesc("so_reg_en_o", 1),
            PortDesc("m_out_change_o", 1),
            PortDesc("busfree_o", 1),
            PortDesc("gate_tx_o", 1),
        ],
        state=[
            StateDesc("pr_state", 4),
            StateDesc("master_count", 8),
            StateDesc("m_txsel", 5),
            StateDesc("ds_txsel", 5),
        ],
        behavior=spi_control_template(
            fifo_word_size=fifo_width,
        ),
    ))

    # 3. SPITransmit
    pes.append(ProcessingElement(
        name="SPITransmit",
        pe_type="spi_transmit",
        description="TX FIFO + serializer + output enables",
        inputs=[
            PortDesc("tx_push_i", 1),
            PortDesc("tx_pop_i", 1),
            PortDesc("pwdata_i", 32),
            PortDesc("master_i", 1),
            PortDesc("spi_enable_i", 1),
            PortDesc("n_ss_in_i", 1),
            PortDesc("m_txsel_i", 5),
            PortDesc("s_txsel_i", 5),
            PortDesc("so_reg_en_i", 1),
            PortDesc("gate_tx_i", 1),
            PortDesc("m_out_change_i", 1),
            PortDesc("man_cs_i", 1),
            PortDesc("ss_i", num_slave_selects),
            PortDesc("pdec_i", 1),
            PortDesc("ss_valid_i", 1),
        ],
        outputs=[
            PortDesc("so_o", 1),
            PortDesc("mo_o", 1),
            PortDesc("n_so_en_o", 1),
            PortDesc("n_mo_en_o", 1),
            PortDesc("n_ss_out_o", num_slave_selects),
            PortDesc("n_ss_en_o", 1),
            PortDesc("tx_empty_o", 1),
            PortDesc("tx_notfull_o", 1),
            PortDesc("tx_full_o", 1),
            PortDesc("n_sclk_en_o", 1),
        ],
        state=[
            StateDesc("fifo_count", 4),
            StateDesc("fifo_data", fifo_width),
            StateDesc("master_out", fifo_width),
        ],
        behavior=spi_transmit_template(
            fifo_depth=fifo_depth,
            fifo_width=fifo_width,
        ),
    ))

    # 4. SPIReceive
    pes.append(ProcessingElement(
        name="SPIReceive",
        pe_type="spi_receive",
        description="RX deserializer + FIFO",
        inputs=[
            PortDesc("m_shiften_i", 1),
            PortDesc("s_shiften_i", 1),
            PortDesc("s_inprogress_i", 1),
            PortDesc("mi_i", 1),
            PortDesc("si_sync3_i", 1),
            PortDesc("master_i", 1),
            PortDesc("rx_push_i", 1),
            PortDesc("rx_pop_i", 1),
        ],
        outputs=[
            PortDesc("rx_fifo_o", fifo_width),
            PortDesc("rx_notempty_o", 1),
            PortDesc("rx_full_o", 1),
        ],
        state=[
            StateDesc("rx_data", fifo_width),
            StateDesc("fifo_count", 4),
        ],
        behavior=spi_receive_template(
            fifo_depth=fifo_depth,
            fifo_width=fifo_width,
        ),
    ))

    # 5. SPISlaveSync
    pes.append(ProcessingElement(
        name="SPISlaveSync",
        pe_type="spi_slave_sync",
        description="Slave data/clock sync with metastability protection",
        inputs=[
            PortDesc("si_i", 1),
            PortDesc("n_ss_in_i", 1),
            PortDesc("cpol_i", 1),
            PortDesc("cpha_i", 1),
            PortDesc("spi_enable_i", 1),
            PortDesc("sclk_in_i", 1),
            PortDesc("start_slave_i", 1),
            PortDesc("tx_empty_i", 1),
        ],
        outputs=[
            PortDesc("si_sync3_o", 1),
            PortDesc("s_inprogress_o", 1),
            PortDesc("n_ss_in_sync_o", 1),
            PortDesc("s_shiften_o", 1),
            PortDesc("slave_out_clk_o", 1),
            PortDesc("spi_enable_del3_o", 1),
            PortDesc("tx_uf_o", 1),
        ],
        state=[
            StateDesc("si_sync1", 1),
            StateDesc("si_sync2", 1),
            StateDesc("si_sync3", 1),
            StateDesc("s_inprogress", 1),
            StateDesc("n_ss_in_sync", 1),
        ],
        behavior=spi_slave_sync_template(),
    ))

    # 6. SPISlaveTX
    pes.append(ProcessingElement(
        name="SPISlaveTX",
        pe_type="spi_slave_tx",
        description="Slave bit-select down-counter",
        inputs=[
            PortDesc("n_ss_in_i", 1),
            PortDesc("cpha_i", 1),
        ],
        outputs=[
            PortDesc("s_txsel_o", 5),
        ],
        state=[
            StateDesc("s_txsel", 5),
            StateDesc("s_txsel_start", 1),
        ],
        behavior=spi_slave_tx_template(
            fifo_word_size=fifo_width,
        ),
    ))

    # 7. SPIExtSync
    pes.append(ProcessingElement(
        name="SPIExtSync",
        pe_type="spi_ext_sync",
        description="External clock edge detector",
        inputs=[
            PortDesc("ext_clk_i", 1),
            PortDesc("cks_i", 1),
        ],
        outputs=[
            PortDesc("m_clocken_o", 1),
        ],
        state=[
            StateDesc("ext_clk_sync2", 1),
            StateDesc("ext_clk_sync3", 1),
        ],
        behavior=spi_ext_sync_template(),
    ))

    # Interconnects between PEs
    interconnects: List[InterconnectSpec] = [
        # Registers → Control
        InterconnectSpec(
            src_pe="SPIRegisters",
            dst_pe="SPIControl",
            signals=[PortDesc("master_o", 1), PortDesc("cpha_o", 1),
                     PortDesc("cpol_o", 1), PortDesc("spi_enable_o", 1),
                     PortDesc("datasize_o", 5), PortDesc("baud_rate_o", 8)],
        ),
        # Registers → Transmit
        InterconnectSpec(
            src_pe="SPIRegisters",
            dst_pe="SPITransmit",
            signals=[PortDesc("ss_o", num_slave_selects), PortDesc("pdec_o", 1),
                     PortDesc("man_cs_o", 1)],
        ),
        # Control → Transmit
        InterconnectSpec(
            src_pe="SPIControl",
            dst_pe="SPITransmit",
            signals=[PortDesc("m_txsel_o", 5), PortDesc("tx_pop_o", 1),
                     PortDesc("ss_valid_o", 1), PortDesc("m_out_change_o", 1),
                     PortDesc("gate_tx_o", 1), PortDesc("so_reg_en_o", 1)],
        ),
        # Control → Receive
        InterconnectSpec(
            src_pe="SPIControl",
            dst_pe="SPIReceive",
            signals=[PortDesc("m_shiften_out_o", 1), PortDesc("rx_push_o", 1)],
        ),
        # Transmit → Registers (status feedback)
        InterconnectSpec(
            src_pe="SPITransmit",
            dst_pe="SPIRegisters",
            signals=[PortDesc("tx_empty_o", 1), PortDesc("tx_notfull_o", 1),
                     PortDesc("tx_full_o", 1)],
        ),
        # Receive → Registers (status + data feedback)
        InterconnectSpec(
            src_pe="SPIReceive",
            dst_pe="SPIRegisters",
            signals=[PortDesc("rx_fifo_o", fifo_width), PortDesc("rx_notempty_o", 1),
                     PortDesc("rx_full_o", 1)],
        ),
        # SlaveSync → Control
        InterconnectSpec(
            src_pe="SPISlaveSync",
            dst_pe="SPIControl",
            signals=[PortDesc("s_shiften_o", 1), PortDesc("s_inprogress_o", 1),
                     PortDesc("n_ss_in_sync_o", 1), PortDesc("spi_enable_del3_o", 1),
                     PortDesc("tx_uf_o", 1)],
        ),
        # SlaveTX → Transmit
        InterconnectSpec(
            src_pe="SPISlaveTX",
            dst_pe="SPITransmit",
            signals=[PortDesc("s_txsel_o", 5)],
        ),
        # ExtSync → Control
        InterconnectSpec(
            src_pe="SPIExtSync",
            dst_pe="SPIControl",
            signals=[PortDesc("m_clocken_o", 1)],
        ),
    ]

    arch = ArchDefinition(
        name=design_name,
        isa="SPI",
        processing_elements=pes,
        interconnects=interconnects,
    )

    return arch
