"""
skills.interfaces.spi.arch_templates — SPI Architecture Templates

Build ProcessingElement and ArchDefinition for SPI components.
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_spi_arch(
    cpol: int = 0,
    cpha: int = 0,
    invert_data_order: int = 0,
    spi_master: int = 1,
    spi_word_len: int = 8,
    clk_div_n: int = 4,
) -> ArchDefinition:
    """Build SPI architecture with 3 PEs: spi_clock_divider, spi_module, spi_top.

    PEs:
      - SPI_CLOCK_DIVIDER: programmable clock divider (2^DIV_N)
      - SPI_MODULE: core SPI master/slave engine (CPOL/CPHA, configurable word length)
      - SPI_TOP: top-level wrapper (divider + core)
    """
    divider_behavior = TemplateRegistry.get("spi_clock_divider")
    module_behavior = TemplateRegistry.get("spi_module")
    top_behavior = TemplateRegistry.get("spi_top")

    pe_divider = ProcessingElement(
        name="SPI_CLOCK_DIVIDER", pe_type="spi_clock_divider",
        inputs=[
            PortDesc("clk_in", "input", 1),
            PortDesc("rst", "input", 1),
        ],
        outputs=[
            PortDesc("clk_out", "output", 1),
            PortDesc("is_ready", "output", 1),
        ],
        state=[
            StateDesc("divcounter", "int", "Divider counter", rtl_type="reg", rtl_width=clk_div_n),
            StateDesc("is_ready_reg", "int", "Ready flag", rtl_type="reg", rtl_width=1),
        ],
        behavior=divider_behavior(div_n=clk_div_n) if divider_behavior else None,
        can_stall=False, latency=1,
    )

    pe_module = ProcessingElement(
        name="SPI_MODULE", pe_type="spi_module",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("sclk_in", "input", 1),
            PortDesc("ss_in", "input", 1),
            PortDesc("miso", "input", 1),
            PortDesc("data_word_send", "input", spi_word_len),
            PortDesc("process_next_word", "input", 1),
        ],
        outputs=[
            PortDesc("sclk_out", "output", 1),
            PortDesc("ss_out", "output", 1),
            PortDesc("mosi", "output", 1),
            PortDesc("data_word_recv", "output", spi_word_len),
            PortDesc("processing_word", "output", 1),
            PortDesc("is_ready", "output", 1),
        ],
        state=[
            StateDesc("is_ready_reg", "int", "Ready flag", rtl_type="reg", rtl_width=1),
            StateDesc("activate_ss", "int", "SS active", rtl_type="reg", rtl_width=1),
            StateDesc("activate_sclk", "int", "SCLK active", rtl_type="reg", rtl_width=1),
            StateDesc("status_ignore_first_edge", "int", "Ignore first edge (CPHA)", rtl_type="reg", rtl_width=1),
            StateDesc("data_word_recv_reg", "int", "Receive shift register", rtl_type="reg", rtl_width=spi_word_len),
            StateDesc("bit_counter", "int", "Bit counter", rtl_type="reg", rtl_width=(spi_word_len - 1).bit_length() or 1),
            StateDesc("spi_status", "int", "FSM state", rtl_type="reg", rtl_width=3),
            StateDesc("last_sclk", "int", "Previous SCLK sample", rtl_type="reg", rtl_width=1),
        ],
        behavior=module_behavior(
            cpol=cpol, cpha=cpha,
            invert_data_order=invert_data_order,
            spi_master=spi_master,
            spi_word_len=spi_word_len,
        ) if module_behavior else None,
        can_stall=False, latency=1,
    )

    pe_top = ProcessingElement(
        name="SPI_TOP", pe_type="spi_top",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("sclk", "input", 1),
            PortDesc("ss", "input", 1),
            PortDesc("miso", "input", 1),
            PortDesc("data_word_send", "input", spi_word_len),
            PortDesc("process_next_word", "input", 1),
        ],
        outputs=[
            PortDesc("sclk", "output", 1),
            PortDesc("ss", "output", 1),
            PortDesc("mosi", "output", 1),
            PortDesc("data_word_recv", "output", spi_word_len),
            PortDesc("processing_word", "output", 1),
            PortDesc("is_ready", "output", 1),
        ],
        state=[
            StateDesc("divcounter", "int", "Divider counter", rtl_type="reg", rtl_width=clk_div_n),
            StateDesc("is_ready_reg", "int", "Ready flag", rtl_type="reg", rtl_width=1),
            StateDesc("activate_ss", "int", "SS active", rtl_type="reg", rtl_width=1),
            StateDesc("activate_sclk", "int", "SCLK active", rtl_type="reg", rtl_width=1),
            StateDesc("status_ignore_first_edge", "int", "Ignore first edge (CPHA)", rtl_type="reg", rtl_width=1),
            StateDesc("data_word_recv_reg", "int", "Receive shift register", rtl_type="reg", rtl_width=spi_word_len),
            StateDesc("bit_counter", "int", "Bit counter", rtl_type="reg", rtl_width=(spi_word_len - 1).bit_length() or 1),
            StateDesc("spi_status", "int", "FSM state", rtl_type="reg", rtl_width=3),
            StateDesc("last_sclk", "int", "Previous SCLK sample", rtl_type="reg", rtl_width=1),
        ],
        behavior=top_behavior(
            cpol=cpol, cpha=cpha,
            invert_data_order=invert_data_order,
            spi_master=spi_master,
            spi_word_len=spi_word_len,
            clk_div_n=clk_div_n,
        ) if top_behavior else None,
        can_stall=False, latency=1,
    )

    arch = ArchDefinition(
        name="SPI",
        description=f"SPI {spi_word_len}-bit master={spi_master} CPOL={cpol} CPHA={cpha}",
        isa="protocol",
        processing_elements=[pe_divider, pe_module, pe_top],
        interconnects=[],
        model=Protocol_Model(),
    )

    return arch


SPI_ControllerModel = Protocol_Model

__all__ = ["build_spi_arch", "SPI_ControllerModel"]
