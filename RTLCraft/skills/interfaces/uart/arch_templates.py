"""
skills.interfaces.uart.arch_templates — UART Architecture Templates

Build ProcessingElement and ArchDefinition for UART components.
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc, CycleContext
from rtlgen import InterconnectSpec, ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_uart_arch(
    data_width: int = 8,
) -> ArchDefinition:
    """Build UART architecture with 3 PEs: uart_tx, uart_rx, uart_top.

    PEs:
      - UART_TX: transmitter (AXI-Stream in, UART out)
      - UART_RX: receiver (UART in, AXI-Stream out)
      - UART_TOP: wrapper (combines tx+rx)
    """
    uart_tx_behavior = TemplateRegistry.get("uart_tx")
    uart_rx_behavior = TemplateRegistry.get("uart_rx")
    uart_top_behavior = TemplateRegistry.get("uart_top")

    pe_tx = ProcessingElement(
        name="UART_TX", pe_type="uart_tx",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("s_axis_tdata", "input", data_width),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("prescale", "input", 16),
        ],
        outputs=[
            PortDesc("s_axis_tready", "output", 1),
            PortDesc("txd", "output", 1),
            PortDesc("busy", "output", 1),
        ],
        state=[
            StateDesc("bit_cnt", "int", "Bit counter", rtl_type="reg", rtl_width=4),
            StateDesc("prescale_reg", "int", "Baud prescaler", rtl_type="reg", rtl_width=19),
        ],
        behavior=uart_tx_behavior(data_width=data_width) if uart_tx_behavior else None,
        can_stall=False, latency=1,
    )

    pe_rx = ProcessingElement(
        name="UART_RX", pe_type="uart_rx",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("rxd", "input", 1),
            PortDesc("m_axis_tready", "input", 1),
            PortDesc("prescale", "input", 16),
        ],
        outputs=[
            PortDesc("m_axis_tdata", "output", data_width),
            PortDesc("m_axis_tvalid", "output", 1),
            PortDesc("busy", "output", 1),
            PortDesc("overrun_error", "output", 1),
            PortDesc("frame_error", "output", 1),
        ],
        state=[
            StateDesc("bit_cnt", "int", "Bit counter", rtl_type="reg", rtl_width=4),
            StateDesc("m_axis_tvalid_reg", "int", "Output valid", rtl_type="reg", rtl_width=1),
        ],
        behavior=uart_rx_behavior(data_width=data_width) if uart_rx_behavior else None,
        can_stall=False, latency=1,
    )

    pe_top = ProcessingElement(
        name="UART", pe_type="uart_top",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("s_axis_tdata", "input", data_width),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("m_axis_tready", "input", 1),
            PortDesc("rxd", "input", 1),
            PortDesc("prescale", "input", 16),
        ],
        outputs=[
            PortDesc("s_axis_tready", "output", 1),
            PortDesc("txd", "output", 1),
            PortDesc("m_axis_tdata", "output", data_width),
            PortDesc("m_axis_tvalid", "output", 1),
            PortDesc("tx_busy", "output", 1),
            PortDesc("rx_busy", "output", 1),
            PortDesc("rx_frame_error", "output", 1),
        ],
        state=[
            StateDesc("tx_bit_cnt", "int", "TX bit counter", rtl_type="reg", rtl_width=4),
            StateDesc("rx_bit_cnt", "int", "RX bit counter", rtl_type="reg", rtl_width=4),
        ],
        behavior=uart_top_behavior(data_width=data_width) if uart_top_behavior else None,
        can_stall=False, latency=1,
    )

    arch = ArchDefinition(
        name="UART",
        description=f"UART {data_width}-bit with AXI-Stream interfaces",
        isa="protocol",
        processing_elements=[pe_tx, pe_rx, pe_top],
        interconnects=[],
        model=Protocol_Model(),
    )

    return arch


UART_ControllerModel = Protocol_Model

__all__ = ["build_uart_arch", "UART_ControllerModel"]
