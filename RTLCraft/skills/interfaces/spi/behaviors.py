"""skills.interfaces.spi.behaviors — SPI Behavior Templates

Domain-specific behavior templates for SPI master/slave components.
Registered into TemplateRegistry at import time.

Components:
  - spi_module:       SPI core (master/slave, CPOL/CPHA, configurable word length)
  - spi_clock_divider: Programmable clock divider
  - spi_top:          Top-level wrapper (divider + core)

Reference: ref_rtl/interfaces/spi/ (verilog_spi by Dr. med. Jan Schiefer)
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# SPI Clock Divider Template
# =====================================================================

def spi_clock_divider_template(
    div_n: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """SPI clock divider behavior.

    Free-running counter; output = counter[DIV_N-1].
    Divides clk_in by 2^DIV_N.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        if rst == 1:
            ctx.set_output("clk_out", 0)
            ctx.set_output("is_ready", 1)
            ctx.set_state("divcounter", 0)
            return

        divcounter = ctx.get_state("divcounter", 0)
        divcounter = (divcounter + 1) & ((1 << div_n) - 1)

        ctx.set_output("clk_out", (divcounter >> (div_n - 1)) & 1)
        ctx.set_output("is_ready", 1)
        ctx.set_state("divcounter", divcounter)

    return behavior


# =====================================================================
# SPI Module Template
# =====================================================================

def spi_module_template(
    cpol: int = 0,
    cpha: int = 0,
    invert_data_order: int = 0,
    spi_master: int = 1,
    spi_word_len: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """SPI master/slave core behavior.

    2-state FSM:
      IDLE(0) → CYCLE_BITS(7) → IDLE

    - Supports all 4 SPI modes via CPOL/CPHA
    - Supports inverted data order (LSB first)
    - Master mode drives SCLK_OUT and SS_OUT
    - Slave mode receives SCLK_IN and SS_IN
    """
    SPI_STATUS_IDLE = 0
    SPI_STATUS_CYCLE_BITS = 7

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)

        # Load state
        is_ready_reg = ctx.get_state("is_ready_reg", 1)
        activate_ss = ctx.get_state("activate_ss", 0)
        activate_sclk = ctx.get_state("activate_sclk", 0)
        status_ignore_first_edge = ctx.get_state("status_ignore_first_edge", 0)
        data_word_recv_reg = ctx.get_state("data_word_recv_reg", 0)
        bit_counter = ctx.get_state("bit_counter", spi_word_len - 1)
        spi_status = ctx.get_state("spi_status", SPI_STATUS_IDLE)
        last_sclk = ctx.get_state("last_sclk", 0)

        # Inputs
        sclk_in = ctx.get_input("sclk_in", 0)
        ss_in = ctx.get_input("ss_in", 1)
        miso = ctx.get_input("miso", 0)
        data_word_send = ctx.get_input("data_word_send", 0)
        process_next_word = ctx.get_input("process_next_word", 0)

        # Edge detection
        rising_sclk_edge = (sclk_in == 1) and (last_sclk == 0)
        falling_sclk_edge = (sclk_in == 0) and (last_sclk == 1)

        # Combinational edge selection based on CPOL/CPHA
        if cpha:
            delay_pol = rising_sclk_edge if cpol else falling_sclk_edge
            get_number_edge = rising_sclk_edge if cpol else falling_sclk_edge
            switch_number_edge = falling_sclk_edge if cpol else rising_sclk_edge
        else:
            delay_pol = bool(sclk_in) if cpol else (not bool(sclk_in))
            get_number_edge = falling_sclk_edge if cpol else rising_sclk_edge
            switch_number_edge = rising_sclk_edge if cpol else falling_sclk_edge

        # Outputs (combinational from state)
        ss_out = 0 if activate_ss else 1
        sclk_out = sclk_in if activate_sclk else cpol
        mosi = ((data_word_send >> bit_counter) & 1) if activate_ss else 0
        processing_word = 0 if (spi_status == SPI_STATUS_IDLE) else 1

        # SS selection (master sees its own output, slave sees external)
        ss = ss_out if spi_master else ss_in

        # Sequential logic
        if rst == 1:
            activate_ss = 0
            activate_sclk = 0
            bit_counter = 0 if invert_data_order else (spi_word_len - 1)
            status_ignore_first_edge = 0
            spi_status = SPI_STATUS_IDLE
            is_ready_reg = 1
            data_word_recv_reg = 0
        else:
            if spi_status == SPI_STATUS_IDLE:
                if process_next_word and delay_pol:
                    status_ignore_first_edge = 0
                    activate_ss = 1
                    activate_sclk = 1
                    spi_status = SPI_STATUS_CYCLE_BITS
            elif spi_status == SPI_STATUS_CYCLE_BITS:
                if not ss:
                    if get_number_edge:
                        mask = 1 << bit_counter
                        data_word_recv_reg = (data_word_recv_reg & ~mask) | (miso << bit_counter)
                    if switch_number_edge:
                        if cpha and not status_ignore_first_edge:
                            status_ignore_first_edge = 1
                        else:
                            done = (bit_counter == (spi_word_len - 1)) if invert_data_order else (bit_counter == 0)
                            if done:
                                activate_ss = 0
                                activate_sclk = 0
                                bit_counter = 0 if invert_data_order else (spi_word_len - 1)
                                spi_status = SPI_STATUS_IDLE
                            else:
                                bit_counter = bit_counter + 1 if invert_data_order else bit_counter - 1

        # Save state
        ctx.set_output("sclk_out", int(sclk_out))
        ctx.set_output("ss_out", int(ss_out))
        ctx.set_output("mosi", int(mosi))
        ctx.set_output("data_word_recv", data_word_recv_reg)
        ctx.set_output("processing_word", processing_word)
        ctx.set_output("is_ready", is_ready_reg)

        ctx.set_state("is_ready_reg", is_ready_reg)
        ctx.set_state("activate_ss", activate_ss)
        ctx.set_state("activate_sclk", activate_sclk)
        ctx.set_state("status_ignore_first_edge", status_ignore_first_edge)
        ctx.set_state("data_word_recv_reg", data_word_recv_reg)
        ctx.set_state("bit_counter", bit_counter)
        ctx.set_state("spi_status", spi_status)
        ctx.set_state("last_sclk", int(sclk_in))

    return behavior


# =====================================================================
# SPI Top Template
# =====================================================================

def spi_top_template(
    cpol: int = 0,
    cpha: int = 0,
    invert_data_order: int = 0,
    spi_master: int = 1,
    spi_word_len: int = 8,
    clk_div_n: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """SPI top-level wrapper behavior (divider + core combined)."""
    SPI_STATUS_IDLE = 0
    SPI_STATUS_CYCLE_BITS = 7

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)

        # Clock divider state
        divcounter = ctx.get_state("divcounter", 0)
        divider_ready = 1

        # Core state
        is_ready_reg = ctx.get_state("is_ready_reg", 1)
        activate_ss = ctx.get_state("activate_ss", 0)
        activate_sclk = ctx.get_state("activate_sclk", 0)
        status_ignore_first_edge = ctx.get_state("status_ignore_first_edge", 0)
        data_word_recv_reg = ctx.get_state("data_word_recv_reg", 0)
        bit_counter = ctx.get_state("bit_counter", spi_word_len - 1)
        spi_status = ctx.get_state("spi_status", SPI_STATUS_IDLE)
        last_sclk = ctx.get_state("last_sclk", 0)

        # Inputs
        sclk_ext = ctx.get_input("sclk", 0)
        ss_ext = ctx.get_input("ss", 1)
        miso = ctx.get_input("miso", 0)
        data_word_send = ctx.get_input("data_word_send", 0)
        process_next_word = ctx.get_input("process_next_word", 0)

        # Clock generation (master only)
        if spi_master:
            divcounter = (divcounter + 1) & ((1 << clk_div_n) - 1)
            sclk_in = (divcounter >> (clk_div_n - 1)) & 1
        else:
            sclk_in = sclk_ext

        # Edge detection
        rising_sclk_edge = (sclk_in == 1) and (last_sclk == 0)
        falling_sclk_edge = (sclk_in == 0) and (last_sclk == 1)

        # Combinational edge selection
        if cpha:
            delay_pol = rising_sclk_edge if cpol else falling_sclk_edge
            get_number_edge = rising_sclk_edge if cpol else falling_sclk_edge
            switch_number_edge = falling_sclk_edge if cpol else rising_sclk_edge
        else:
            delay_pol = bool(sclk_in) if cpol else (not bool(sclk_in))
            get_number_edge = falling_sclk_edge if cpol else rising_sclk_edge
            switch_number_edge = rising_sclk_edge if cpol else falling_sclk_edge

        # Outputs
        ss_out = 0 if activate_ss else 1
        sclk_out = sclk_in if activate_sclk else cpol
        mosi = ((data_word_send >> bit_counter) & 1) if activate_ss else 0
        processing_word = 0 if (spi_status == SPI_STATUS_IDLE) else 1

        # SS selection
        ss = ss_out if spi_master else ss_ext

        # Sequential logic
        if rst == 1:
            activate_ss = 0
            activate_sclk = 0
            bit_counter = 0 if invert_data_order else (spi_word_len - 1)
            status_ignore_first_edge = 0
            spi_status = SPI_STATUS_IDLE
            is_ready_reg = 1
            data_word_recv_reg = 0
            divcounter = 0
        else:
            if spi_status == SPI_STATUS_IDLE:
                if process_next_word and delay_pol:
                    status_ignore_first_edge = 0
                    activate_ss = 1
                    activate_sclk = 1
                    spi_status = SPI_STATUS_CYCLE_BITS
            elif spi_status == SPI_STATUS_CYCLE_BITS:
                if not ss:
                    if get_number_edge:
                        mask = 1 << bit_counter
                        data_word_recv_reg = (data_word_recv_reg & ~mask) | (miso << bit_counter)
                    if switch_number_edge:
                        if cpha and not status_ignore_first_edge:
                            status_ignore_first_edge = 1
                        else:
                            done = (bit_counter == (spi_word_len - 1)) if invert_data_order else (bit_counter == 0)
                            if done:
                                activate_ss = 0
                                activate_sclk = 0
                                bit_counter = 0 if invert_data_order else (spi_word_len - 1)
                                spi_status = SPI_STATUS_IDLE
                            else:
                                bit_counter = bit_counter + 1 if invert_data_order else bit_counter - 1

        is_ready_gated = is_ready_reg & divider_ready if spi_master else is_ready_reg

        ctx.set_output("sclk", int(sclk_out))
        ctx.set_output("ss", int(ss_out))
        ctx.set_output("mosi", int(mosi))
        ctx.set_output("data_word_recv", data_word_recv_reg)
        ctx.set_output("processing_word", processing_word)
        ctx.set_output("is_ready", is_ready_gated)

        ctx.set_state("divcounter", divcounter)
        ctx.set_state("is_ready_reg", is_ready_reg)
        ctx.set_state("activate_ss", activate_ss)
        ctx.set_state("activate_sclk", activate_sclk)
        ctx.set_state("status_ignore_first_edge", status_ignore_first_edge)
        ctx.set_state("data_word_recv_reg", data_word_recv_reg)
        ctx.set_state("bit_counter", bit_counter)
        ctx.set_state("spi_status", spi_status)
        ctx.set_state("last_sclk", int(sclk_in))

    return behavior


# Register templates
TemplateRegistry.register("spi_clock_divider", spi_clock_divider_template)
TemplateRegistry.register("spi_module", spi_module_template)
TemplateRegistry.register("spi_top", spi_top_template)

__all__ = [
    "spi_clock_divider_template",
    "spi_module_template",
    "spi_top_template",
]
