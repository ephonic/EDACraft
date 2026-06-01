"""
skills.interfaces.i2c.behaviors — I2C Behavior Templates

Domain-specific behavior templates for I2C components.
Registered into TemplateRegistry at import time.

Components:
  - i2c_single_reg: I2C slave register with input filtering (7-bit addr, single byte R/W)

Reference: ref_rtl/interfaces/i2c/rtl/i2c_single_reg.v
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# I2C_SINGLE_REG Template
# =====================================================================

def i2c_single_reg_template(
    filter_len: int = 4,
    dev_addr: int = 0x70,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """I2C single register slave behavior.

    8-state FSM:
      IDLE → ADDRESS (shift in 7-bit addr + R/W) → ACK → WRITE_1/2 or READ_1/2/3
    - Input glitch filter: shift-register of FILTER_LEN samples
    - Start/stop detection: SDA edge while SCL high
    - Clock edge detection on filtered SCL/SDA
    """
    STATE_IDLE = 0
    STATE_ADDRESS = 1
    STATE_ACK = 2
    STATE_WRITE_1 = 3
    STATE_WRITE_2 = 4
    STATE_READ_1 = 5
    STATE_READ_2 = 6
    STATE_READ_3 = 7

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)

        state_reg = ctx.get_state("state_reg", STATE_IDLE)
        data_reg = ctx.get_state("data_reg", 0)
        shift_reg = ctx.get_state("shift_reg", 0)
        mode_read_reg = ctx.get_state("mode_read_reg", 0)
        bit_count_reg = ctx.get_state("bit_count_reg", 7)
        sda_o_reg = ctx.get_state("sda_o_reg", 1)
        scl_i_reg = ctx.get_state("scl_i_reg", 1)
        sda_i_reg = ctx.get_state("sda_i_reg", 1)
        last_scl_i_reg = ctx.get_state("last_scl_i_reg", 1)
        last_sda_i_reg = ctx.get_state("last_sda_i_reg", 1)
        scl_filter = ctx.get_state("scl_filter", (1 << filter_len) - 1)
        sda_filter = ctx.get_state("sda_filter", (1 << filter_len) - 1)

        scl_i_raw = ctx.get_input("scl_i", 1)
        sda_i_raw = ctx.get_input("sda_i", 1)

        if rst:
            state_reg = STATE_IDLE
            sda_o_reg = 1
            shift_reg = 0
            bit_count_reg = 7

        # Input filter
        scl_filter = ((scl_filter << 1) | scl_i_raw) & ((1 << filter_len) - 1)
        sda_filter = ((sda_filter << 1) | sda_i_raw) & ((1 << filter_len) - 1)

        if scl_filter == (1 << filter_len) - 1:
            scl_i_reg = 1
        elif scl_filter == 0:
            scl_i_reg = 0

        if sda_filter == (1 << filter_len) - 1:
            sda_i_reg = 1
        elif sda_filter == 0:
            sda_i_reg = 0

        last_scl_i_reg = scl_i_reg
        last_sda_i_reg = sda_i_reg

        # Edge detection
        scl_posedge = scl_i_reg and not last_scl_i_reg
        scl_negedge = not scl_i_reg and last_scl_i_reg
        sda_posedge = sda_i_reg and not last_sda_i_reg
        sda_negedge = not sda_i_reg and last_sda_i_reg
        start_bit = sda_negedge and scl_i_reg
        stop_bit = sda_posedge and scl_i_reg

        # Data latch
        if ctx.get_input("data_latch", 0):
            data_reg = ctx.get_input("data_in", 0)

        # FSM
        if start_bit:
            sda_o_reg = 1
            bit_count_reg = 7
            state_reg = STATE_ADDRESS
        elif stop_bit:
            sda_o_reg = 1
            state_reg = STATE_IDLE
        elif state_reg == STATE_IDLE:
            sda_o_reg = 1
        elif state_reg == STATE_ADDRESS:
            sda_o_reg = 1
            if scl_posedge:
                if bit_count_reg > 0:
                    bit_count_reg -= 1
                    shift_reg = ((shift_reg << 1) | sda_i_reg) & 0xFF
                else:
                    mode_read_reg = sda_i_reg
                    if (shift_reg >> 1) == dev_addr:
                        state_reg = STATE_ACK
                    else:
                        state_reg = STATE_IDLE
        elif state_reg == STATE_ACK:
            if scl_negedge:
                sda_o_reg = 0
                bit_count_reg = 7
                if mode_read_reg:
                    shift_reg = data_reg
                    state_reg = STATE_READ_1
                else:
                    state_reg = STATE_WRITE_1
        elif state_reg == STATE_WRITE_1:
            if scl_negedge:
                sda_o_reg = 1
                state_reg = STATE_WRITE_2
        elif state_reg == STATE_WRITE_2:
            sda_o_reg = 1
            if scl_posedge:
                shift_reg = ((shift_reg << 1) | sda_i_reg) & 0xFF
                if bit_count_reg > 0:
                    bit_count_reg -= 1
                else:
                    data_reg = shift_reg
                    state_reg = STATE_ACK
        elif state_reg == STATE_READ_1:
            if scl_negedge:
                sda_o_reg = (shift_reg >> 7) & 1
                shift_reg = ((shift_reg << 1) | sda_i_reg) & 0xFF
                if bit_count_reg > 0:
                    bit_count_reg -= 1
                else:
                    state_reg = STATE_READ_2
        elif state_reg == STATE_READ_2:
            if scl_negedge:
                sda_o_reg = 1
                state_reg = STATE_READ_3
        elif state_reg == STATE_READ_3:
            if scl_posedge:
                if sda_i_reg:
                    state_reg = STATE_IDLE
                else:
                    bit_count_reg = 7
                    shift_reg = data_reg
                    state_reg = STATE_READ_1

        ctx.set_output("sda_o", sda_o_reg)
        ctx.set_output("sda_t", sda_o_reg)
        ctx.set_output("scl_o", 1)
        ctx.set_output("scl_t", 1)
        ctx.set_output("data_out", data_reg)

        ctx.set_state("state_reg", state_reg)
        ctx.set_state("data_reg", data_reg)
        ctx.set_state("shift_reg", shift_reg)
        ctx.set_state("mode_read_reg", mode_read_reg)
        ctx.set_state("bit_count_reg", bit_count_reg)
        ctx.set_state("sda_o_reg", sda_o_reg)
        ctx.set_state("scl_i_reg", scl_i_reg)
        ctx.set_state("sda_i_reg", sda_i_reg)
        ctx.set_state("last_scl_i_reg", last_scl_i_reg)
        ctx.set_state("last_sda_i_reg", last_sda_i_reg)
        ctx.set_state("scl_filter", scl_filter)
        ctx.set_state("sda_filter", sda_filter)

    return behavior


TemplateRegistry.register("i2c_single_reg", i2c_single_reg_template)

__all__ = ["i2c_single_reg_template"]
