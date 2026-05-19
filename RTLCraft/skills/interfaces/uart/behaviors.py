"""
skills.interfaces.uart.behaviors — UART Behavior Templates

Domain-specific behavior templates for AXI-Stream UART components.
Registered into TemplateRegistry at import time.

Components:
  - uart_tx:      UART transmitter with AXI-Stream input (start+data+stop framing)
  - uart_rx:      UART receiver with AXI-Stream output (overrun/frame error detection)
  - uart_top:     UART top-level wrapper (tx + rx)

Reference: ref_rtl/interfaces/uart/rtl/uart_tx.v, uart_rx.v, uart.v
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# UART_TX Template
# =====================================================================

def uart_tx_template(
    data_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """UART transmitter behavior.

    FSM-less counter-based design:
      - Idle: ready=1, busy=0, txd=1
      - On tvalid: ready toggles, prescale=prescale*8-1, bit_cnt=data_width+1, txd=0 (start bit)
      - During transmit: prescale countdown, shift data_reg out LSB first
      - After last data bit: txd=1 (stop bit), return to idle

    Frame: start(0) + data[0..N-1] + stop(1)
    Baud rate = clk_freq / (prescale * 8)
    """
    total_bits = data_width + 1  # start bit + data bits

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        if rst == 1:
            ctx.set_output("s_axis_tready", 0)
            ctx.set_output("txd", 1)
            ctx.set_output("busy", 0)
            ctx.set_state("bit_cnt", 0)
            ctx.set_state("prescale_reg", 0)
            ctx.set_state("data_reg", 0)
            ctx.set_state("txd_reg", 1)
            return

        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)
        bit_cnt = ctx.get_state("bit_cnt", 0)
        prescale_reg = ctx.get_state("prescale_reg", 0)
        data_reg = ctx.get_state("data_reg", 0)
        txd_reg = ctx.get_state("txd_reg", 1)

        prescale = ctx.get_input("prescale", 1)

        if prescale_reg > 0:
            prescale_reg -= 1
            ctx.set_output("s_axis_tready", 0)
        elif bit_cnt == 0:
            # Idle
            ctx.set_output("s_axis_tready", 1)
            ctx.set_output("busy", 0)
            if s_axis_tvalid:
                ctx.set_output("s_axis_tready", 0)
                ctx.set_output("busy", 1)
                prescale_reg = (prescale << 3) - 1
                bit_cnt = total_bits
                data_reg = (1 << data_width) | ctx.get_input("s_axis_tdata", 0)
                txd_reg = 0
        else:
            ctx.set_output("s_axis_tready", 0)
            ctx.set_output("busy", 1)
            if bit_cnt > 1:
                bit_cnt -= 1
                prescale_reg = (prescale << 3) - 1
                # Shift right: LSB first
                txd_reg = data_reg & 0x1
                data_reg >>= 1
            else:
                bit_cnt -= 1
                txd_reg = 1

        ctx.set_output("txd", txd_reg)
        ctx.set_state("bit_cnt", bit_cnt)
        ctx.set_state("prescale_reg", prescale_reg)
        ctx.set_state("data_reg", data_reg)
        ctx.set_state("txd_reg", txd_reg)

    return behavior


# =====================================================================
# UART_RX Template
# =====================================================================

def uart_rx_template(
    data_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """UART receiver behavior.

    Counter-based design (no explicit FSM states):
      - Idle: wait for rxd=0 (start bit)
      - Start bit detection: set prescale for half-bit sampling
      - Data sampling: sample at middle of each bit period
      - Stop bit check: if rxd=1 → valid, else → frame_error
      - Overrun: if previous data not consumed before new data arrives

    Outputs: m_axis_tdata/tvalid, busy, overrun_error, frame_error
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        if rst == 1:
            ctx.set_output("m_axis_tvalid", 0)
            ctx.set_output("busy", 0)
            ctx.set_output("overrun_error", 0)
            ctx.set_output("frame_error", 0)
            ctx.set_state("bit_cnt", 0)
            ctx.set_state("prescale_reg", 0)
            ctx.set_state("data_reg", 0)
            ctx.set_state("m_axis_tvalid_reg", 0)
            ctx.set_state("rxd_reg", 1)
            return

        rxd = ctx.get_input("rxd", 1)
        m_axis_tready = ctx.get_input("m_axis_tready", 0)
        prescale = ctx.get_input("prescale", 1)

        m_axis_tvalid_reg = ctx.get_state("m_axis_tvalid_reg", 0)
        bit_cnt = ctx.get_state("bit_cnt", 0)
        prescale_reg = ctx.get_state("prescale_reg", 0)
        data_reg = ctx.get_state("data_reg", 0)
        rxd_reg = ctx.get_state("rxd_reg", 1)

        # Clear errors
        ctx.set_output("overrun_error", 0)
        ctx.set_output("frame_error", 0)

        # Clear valid when consumed
        if m_axis_tvalid_reg and m_axis_tready:
            m_axis_tvalid_reg = 0

        rxd_reg = rxd

        if prescale_reg > 0:
            prescale_reg -= 1
        elif bit_cnt > 0:
            if bit_cnt > data_width + 1:
                # Start bit sampling period
                if rxd_reg == 0:
                    bit_cnt -= 1
                    prescale_reg = (prescale << 3) - 1
                else:
                    # False start bit
                    bit_cnt = 0
                    prescale_reg = 0
            elif bit_cnt > 1:
                # Data sampling
                bit_cnt -= 1
                prescale_reg = (prescale << 3) - 1
                data_reg = (rxd_reg << (data_width - 1)) | (data_reg >> 1)
            else:
                # Stop bit check
                bit_cnt -= 1
                if rxd_reg == 1:
                    ctx.set_output("m_axis_tdata", data_reg)
                    m_axis_tvalid_reg = 1
                    # Overrun if previous valid not consumed
                    ctx.set_output("overrun_error", ctx.get_state("m_axis_tvalid_reg", 0))
                else:
                    ctx.set_output("frame_error", 1)
        else:
            # Idle
            ctx.set_output("busy", 0)
            if rxd_reg == 0:
                # Start bit detected
                prescale_reg = (prescale << 2) - 2
                bit_cnt = data_width + 2
                data_reg = 0
                ctx.set_output("busy", 1)

        ctx.set_output("m_axis_tvalid", m_axis_tvalid_reg)
        ctx.set_state("m_axis_tvalid_reg", m_axis_tvalid_reg)
        ctx.set_state("bit_cnt", bit_cnt)
        ctx.set_state("prescale_reg", prescale_reg)
        ctx.set_state("data_reg", data_reg)
        ctx.set_state("rxd_reg", rxd_reg)

    return behavior


# =====================================================================
# UART Top Template
# =====================================================================

def uart_top_template(
    data_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """UART top-level wrapper behavior (tx + rx combined)."""
    def behavior(ctx: CycleContext):
        # TX behavior
        rst = ctx.get_input("rst", 1)
        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)
        rxd = ctx.get_input("rxd", 1)
        m_axis_tready = ctx.get_input("m_axis_tready", 0)
        prescale = ctx.get_input("prescale", 1)

        tx_bit_cnt = ctx.get_state("tx_bit_cnt", 0)
        tx_prescale = ctx.get_state("tx_prescale", 0)
        tx_txd = ctx.get_state("tx_txd", 1)
        tx_data = ctx.get_state("tx_data", 0)

        rx_bit_cnt = ctx.get_state("rx_bit_cnt", 0)
        rx_prescale = ctx.get_state("rx_prescale", 0)
        rx_valid = ctx.get_state("rx_valid", 0)
        rx_data = ctx.get_state("rx_data", 0)
        rx_rxd = ctx.get_state("rx_rxd", 1)

        if not rst:
            # TX
            if tx_prescale > 0:
                tx_prescale -= 1
                ctx.set_output("s_axis_tready", 0)
            elif tx_bit_cnt == 0:
                ctx.set_output("s_axis_tready", 1)
                if s_axis_tvalid:
                    tx_prescale = (prescale << 3) - 1
                    tx_bit_cnt = data_width + 1
                    tx_data = (1 << data_width) | ctx.get_input("s_axis_tdata", 0)
                    tx_txd = 0
            elif tx_bit_cnt > 1:
                tx_bit_cnt -= 1
                tx_prescale = (prescale << 3) - 1
                tx_txd = tx_data & 0x1
                tx_data >>= 1
            else:
                tx_bit_cnt -= 1
                tx_txd = 1

            # RX
            if rx_valid and m_axis_tready:
                rx_valid = 0
            rx_rxd = rxd
            if rx_prescale > 0:
                rx_prescale -= 1
            elif rx_bit_cnt > 0:
                if rx_bit_cnt > data_width + 1:
                    if rx_rxd == 0:
                        rx_bit_cnt -= 1
                        rx_prescale = (prescale << 3) - 1
                    else:
                        rx_bit_cnt = 0
                elif rx_bit_cnt > 1:
                    rx_bit_cnt -= 1
                    rx_prescale = (prescale << 3) - 1
                    rx_data = (rx_rxd << (data_width - 1)) | (rx_data >> 1)
                else:
                    rx_bit_cnt -= 1
                    if rx_rxd == 1:
                        ctx.set_output("m_axis_tdata", rx_data)
                        rx_valid = 1
                    else:
                        ctx.set_output("frame_error", 1)

        ctx.set_output("txd", tx_txd)
        ctx.set_output("tx_busy", 1 if tx_bit_cnt > 0 else 0)
        ctx.set_output("rx_busy", 1 if rx_bit_cnt > 0 else 0)
        ctx.set_output("m_axis_tvalid", rx_valid)

        ctx.set_state("tx_bit_cnt", tx_bit_cnt)
        ctx.set_state("tx_prescale", tx_prescale)
        ctx.set_state("tx_txd", tx_txd)
        ctx.set_state("tx_data", tx_data)
        ctx.set_state("rx_bit_cnt", rx_bit_cnt)
        ctx.set_state("rx_prescale", rx_prescale)
        ctx.set_state("rx_valid", rx_valid)
        ctx.set_state("rx_data", rx_data)
        ctx.set_state("rx_rxd", rx_rxd)

    return behavior


# Register UART templates
TemplateRegistry.register("uart_tx", uart_tx_template)
TemplateRegistry.register("uart_rx", uart_rx_template)
TemplateRegistry.register("uart_top", uart_top_template)

__all__ = [
    "uart_tx_template",
    "uart_rx_template",
    "uart_top_template",
]
