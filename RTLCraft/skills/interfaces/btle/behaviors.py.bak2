"""
skills.interfaces.btle.behaviors — BTLE Controller Behavior Templates

Domain-specific behavior templates for Bluetooth Low Energy PHY pipeline stages.
Registered into TemplateRegistry at import time.

Pipeline stages:
  - crc24_core:       BLE CRC-24 LFSR (polynomial taps 0,1,3,4,6,9,10)
  - scramble_core:    Data whitening LFSR (x^7+x^4+1)
  - access_address_detect: 32-bit access address detector
  - gfsk_demod:       GFSK delay-multiply frequency discriminator
  - gauss_filter:     17-tap Gaussian FIR (BT=0.5)
  - bit_upsampler:    1M→8M bit repeater
  - sdpram:           Simple dual-port RAM
  - crc_wrapper:      CRC wrapper (skip preamble+AA, append 24 CRC bits)
  - scramble_wrapper: Whitening wrapper (skip preamble+AA)
  - vco:              VCO with phase accumulator + sin/cos ROM lookup
  - gfsk_mod:         GFSK modulator: upsample → Gaussian FIR → VCO
  - btle_rx_core:     RX core: demod → AA search → descramble → CRC
  - btle_tx:          TX: PDU RAM → preamble+AA → CRC+scramble → GFSK
  - btle_phy:         PHY wrapper: TX + RX
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def crc24_core_template(
    crc_width: int = 24,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BLE CRC-24 LFSR behavior.

    Polynomial taps: 0, 1, 3, 4, 6, 9, 10 (feedback from MSB xor data_in).
    Byte-swapped init for BLE ordering.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        init = ctx.get_input("crc_state_init_bit", 0)
        init_load = ctx.get_input("crc_state_init_bit_load", 0)
        data_in = ctx.get_input("data_in", 0)
        data_valid = ctx.get_input("data_in_valid", 0)

        # Byte-swap init: [7:0]↔[23:16], [15:8] stays
        init_swapped = ((init & 0xFF) << 16) | (init & 0xFF00) | ((init >> 16) & 0xFF)

        lfsr = ctx.get_state("lfsr", init_swapped)
        if rst:
            ctx.set_state("lfsr", init_swapped)
            ctx.set_output("lfsr", init_swapped)
            return

        if init_load:
            ctx.set_state("lfsr", init_swapped)
            ctx.set_output("lfsr", init_swapped)
            return

        if data_valid:
            new_bit = (lfsr >> 23) & 1 ^ data_in
            bit0 = new_bit
            bit1 = (lfsr & 1) ^ new_bit
            bit2 = (lfsr >> 1) & 1
            bit3 = ((lfsr >> 2) & 1) ^ new_bit
            bit4 = ((lfsr >> 3) & 1) ^ new_bit
            bit5 = (lfsr >> 4) & 1
            bit6 = ((lfsr >> 5) & 1) ^ new_bit
            bit7 = (lfsr >> 6) & 1
            bit8 = (lfsr >> 7) & 1
            bit9 = ((lfsr >> 8) & 1) ^ new_bit
            bit10 = ((lfsr >> 9) & 1) ^ new_bit
            upper = (lfsr >> 11) & 0x1FFF  # bits 22:10

            new_lfsr = (upper << 11) | (bit10 << 10) | (bit9 << 9) | (bit8 << 8) | \
                       (bit7 << 7) | (bit6 << 6) | (bit5 << 5) | (bit4 << 4) | \
                       (bit3 << 3) | (bit2 << 2) | (bit1 << 1) | bit0
            ctx.set_state("lfsr", new_lfsr)

        ctx.set_output("lfsr", ctx.get_state("lfsr", lfsr))

    return behavior


def scramble_core_template(
    channel_width: int = 6,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BLE data whitening LFSR behavior.

    Polynomial: x^7 + x^4 + 1. Init={1, channel_number[5:0]}.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        ch = ctx.get_input("channel_number", 0)
        ch_load = ctx.get_input("channel_number_load", 0)
        data_in = ctx.get_input("data_in", 0)
        data_valid = ctx.get_input("data_in_valid", 0)

        ch_internal = ch if ch != 0 else (1 << channel_width) - 1
        lfsr = ctx.get_state("lfsr", 0)

        if rst or ch_load:
            lfsr = 1 | (ch_internal << 1)
            ctx.set_state("lfsr", lfsr)
            ctx.set_output("data_out", 0)
            ctx.set_output("data_out_valid", 0)
            return

        if data_valid:
            new_lfsr = ((lfsr & 1) << 6) | (lfsr >> 1)  # Wrong, need proper LFSR
            # Proper: lfsr[0]←lfsr[6], lfsr[1]←lfsr[0], ..., lfsr[4]←lfsr[3]^lfsr[6], ...
            b0 = (lfsr >> 6) & 1
            b1 = lfsr & 1
            b2 = (lfsr >> 1) & 1
            b3 = (lfsr >> 2) & 1
            b4 = ((lfsr >> 3) & 1) ^ ((lfsr >> 6) & 1)
            b5 = (lfsr >> 4) & 1
            b6 = (lfsr >> 5) & 1
            lfsr = (b6 << 6) | (b5 << 5) | (b4 << 4) | (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
            ctx.set_state("lfsr", lfsr)
            ctx.set_output("data_out", ((lfsr >> 6) & 1) ^ data_in)
            ctx.set_output("data_out_valid", 1)
        else:
            ctx.set_output("data_out_valid", 0)

    return behavior


def access_address_detect_template(
    len_seq: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """32-bit access address detector behavior."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        phy_bit = ctx.get_input("phy_bit", 0)
        bit_valid = ctx.get_input("bit_valid", 0)
        unique_seq = ctx.get_input("unique_bit_sequence", 0)
        seq_internal = unique_seq if unique_seq != 0 else 0x123a5456

        bit_store = ctx.get_state("bit_store", 0)
        bit_valid_d1 = ctx.get_state("bit_valid_d1", 0)

        if rst:
            ctx.set_state("bit_store", 0)
            ctx.set_state("bit_valid_d1", 0)
            return

        bit_valid_d1 = bit_valid
        ctx.set_state("bit_valid_d1", bit_valid_d1)

        if bit_valid:
            bit_store = ((bit_store >> 1) & ((1 << (len_seq - 1)) - 1)) | (phy_bit << (len_seq - 1))
            ctx.set_state("bit_store", bit_store)

        hit = (bit_store == seq_internal) and bit_valid_d1
        ctx.set_output("hit_flag", 1 if hit else 0)

    return behavior


def gfsk_demod_template(
    bit_width: int = 16,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """GFSK delay-multiply frequency discriminator behavior.

    Decision metric: i0*q1 - i1*q0. 3-cycle pipeline latency.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        i_in = ctx.get_input("i", 0)
        q_in = ctx.get_input("q", 0)
        iq_valid = ctx.get_input("iq_valid", 0)

        # Sign-extend
        pmax = (1 << bit_width) - 1
        i_ext = i_in if i_in < (1 << (bit_width - 1)) else i_in - (1 << bit_width)
        q_ext = q_in if q_in < (1 << (bit_width - 1)) else q_in - (1 << bit_width)

        i0 = ctx.get_state("i0", 0)
        i1 = ctx.get_state("i1", 0)
        q0 = ctx.get_state("q0", 0)
        q1 = ctx.get_state("q1", 0)
        iq_valid_d1 = ctx.get_state("iq_valid_d1", 0)
        iq_valid_d2 = ctx.get_state("iq_valid_d2", 0)
        iq_valid_d3 = ctx.get_state("iq_valid_d3", 0)
        sig_decision = ctx.get_state("sig_decision", 0)

        if rst:
            for s in ["i0", "i1", "q0", "q1", "iq_valid_d1", "iq_valid_d2", "iq_valid_d3", "sig_decision"]:
                ctx.set_state(s, 0)
            return

        iq_valid_d3 = iq_valid_d2
        iq_valid_d2 = iq_valid_d1
        iq_valid_d1 = iq_valid
        ctx.set_state("iq_valid_d1", iq_valid_d1)
        ctx.set_state("iq_valid_d2", iq_valid_d2)
        ctx.set_state("iq_valid_d3", iq_valid_d3)

        if iq_valid:
            i1 = i_ext
            i0 = i1
            q1 = q_ext
            q0 = q1
            ctx.set_state("i0", i0)
            ctx.set_state("i1", i1)
            ctx.set_state("q0", q0)
            ctx.set_state("q1", q1)

        sig_decision = i0 * q1 - i1 * q0
        ctx.set_state("sig_decision", sig_decision)

        ctx.set_output("signal_for_decision", sig_decision & ((1 << (2 * bit_width)) - 1))
        ctx.set_output("signal_for_decision_valid", iq_valid_d2)
        phy_bit = 1 if sig_decision > 0 else 0
        ctx.set_output("phy_bit", phy_bit)
        ctx.set_output("bit_valid", iq_valid_d3)

    return behavior


def gauss_filter_template(
    bit_width: int = 16,
    num_tap: int = 17,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """17-tap Gaussian FIR filter behavior.

    9 programmable taps, symmetric mirror. BT=0.5.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        tap_index = ctx.get_input("tap_index", 0)
        tap_value = ctx.get_input("tap_value", 0)
        bit_up = ctx.get_input("bit_upsample", 0)
        bit_up_valid = ctx.get_input("bit_upsample_valid", 0)
        bit_up_last = ctx.get_input("bit_upsample_valid_last", 0)

        taps = [ctx.get_state(f"tap{i}", 0) for i in range(9)]
        shift_reg = ctx.get_state("shift_reg", 0)

        if rst:
            for i in range(9):
                ctx.set_state(f"tap{i}", 0)
            ctx.set_state("shift_reg", 0)
            return

        # Tap loading
        if tap_index < 9:
            ctx.set_state(f"tap{tap_index}", tap_value)

        # FIR computation
        if bit_up_valid:
            shift_reg = ((shift_reg << 1) | bit_up) & ((1 << (num_tap - 1)) - 1)
            ctx.set_state("shift_reg", shift_reg)

            # Compute 17-tap FIR
            pmax_val = (1 << (bit_width - 1)) - 1
            pmin_val = -(1 << (bit_width - 1))

            def sat(v):
                return max(pmin_val, min(pmax_val, v))

            def tap_mult(bit, t):
                return t if bit else -t

            total = tap_mult(bit_up, taps[0])
            for j in range(1, 8):
                total += tap_mult((shift_reg >> (j - 1)) & 1, taps[j])
            total += tap_mult((shift_reg >> 7) & 1, taps[8])
            for j in range(9, 16):
                mirror = 16 - j
                total += tap_mult((shift_reg >> (j - 1)) & 1, taps[mirror])
            total += tap_mult((shift_reg >> 15) & 1, taps[0])

            ctx.set_output("bit_upsample_gauss_filter", total & ((1 << bit_width) - 1))
        else:
            ctx.set_output("bit_upsample_gauss_filter", 0)

        ctx.set_output("bit_upsample_gauss_filter_valid", bit_up_valid)
        ctx.set_output("bit_upsample_gauss_filter_valid_last", bit_up_last)

    return behavior


def bit_upsampler_template(
    sample_per_symbol: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """1M→8M bit upsampler behavior."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        phy_bit = ctx.get_input("phy_bit", 0)
        bit_valid = ctx.get_input("bit_valid", 0)
        bit_last = ctx.get_input("bit_valid_last", 0)

        count = ctx.get_state("bit_upsample_count", 0)
        valid_internal = ctx.get_state("bit_upsample_valid_internal", 0)
        bit_reg = ctx.get_state("bit_upsample_reg", 0)
        first_valid = ctx.get_state("first_bit_valid", 0)

        if rst:
            ctx.set_state("bit_upsample_count", 0)
            ctx.set_state("bit_upsample_valid_internal", 0)
            ctx.set_state("bit_upsample_reg", 0)
            ctx.set_state("first_bit_valid", 0)
            return

        if bit_valid:
            bit_reg = phy_bit
        valid_internal = 1 - valid_internal
        ctx.set_state("bit_upsample_valid_internal", valid_internal)
        ctx.set_state("bit_upsample_reg", bit_reg)

        if first_valid == 0:
            count = 1
            first_valid = 1
        else:
            if valid_internal == 0:
                count = (count + 1) & 0xF
        ctx.set_state("bit_upsample_count", count)
        ctx.set_state("first_bit_valid", first_valid)

        ctx.set_output("bit_upsample", bit_reg)
        ctx.set_output("bit_upsample_valid", valid_internal)
        ctx.set_output("bit_upsample_valid_last", (count == 0) and bit_last)

    return behavior


def sdpram_template(
    data_width: int = 8,
    addr_width: int = 11,
    dual_clock: bool = False,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Simple dual-port RAM behavior."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        waddr = ctx.get_input("write_address", 0)
        wdata = ctx.get_input("write_data", 0)
        wen = ctx.get_input("write_enable", 0)
        raddr = ctx.get_input("read_address", 0)

        # Memory stored as dict in state
        mem = ctx.get_state("memory", {})
        read_data = ctx.get_state("read_data", 0)

        if rst:
            ctx.set_state("memory", {})
            ctx.set_state("read_data", 0)
            return

        if wen:
            mem[waddr] = wdata
            ctx.set_state("memory", mem)

        ctx.set_state("read_data", mem.get(raddr, 0))
        ctx.set_output("read_data", read_data)

    return behavior


def crc_wrapper_template(
    crc_width: int = 24,
    payload_len_bits: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """CRC-24 wrapper behavior: skip first 40 bits, append 24 CRC bits."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        data_in = ctx.get_input("info_bit", 0)
        data_valid = ctx.get_input("info_bit_valid", 0)
        data_last = ctx.get_input("info_bit_valid_last", 0)
        init = ctx.get_input("crc_state_init_bit", 0)
        init_load = ctx.get_input("crc_state_init_bit_load", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=WORK, 2=CRC_OUTPUT
        bit_count = ctx.get_state("info_bit_count", 0)
        crc_bit_count = ctx.get_state("crc_bit_count", 0)
        clk_count = ctx.get_state("clk_count", 0)
        lfsr = ctx.get_state("lfsr", 0)

        init_swapped = ((init & 0xFF) << 16) | (init & 0xFF00) | ((init >> 16) & 0xFF)

        if rst:
            ctx.set_state("state", 0)
            ctx.set_state("info_bit_count", 0)
            ctx.set_state("crc_bit_count", 0)
            ctx.set_state("clk_count", 0)
            ctx.set_state("lfsr", init_swapped)
            return

        # Pass-through behavior
        if state == 0:
            if data_valid:
                bit_count += 1
                state = 1
            ctx.set_output("info_bit_after_crc24", data_in)
            ctx.set_output("info_bit_after_crc24_valid", data_valid)
            ctx.set_output("info_bit_after_crc24_valid_last", 0)
        elif state == 1:
            if data_valid:
                bit_count += 1
            if data_last:
                state = 2
            ctx.set_output("info_bit_after_crc24", data_in)
            ctx.set_output("info_bit_after_crc24_valid", data_valid)
            ctx.set_output("info_bit_after_crc24_valid_last", 0)
        else:  # CRC output
            clk_count += 1
            if clk_count == 15:
                crc_bit = (lfsr >> (23 - crc_bit_count)) & 1
                ctx.set_output("info_bit_after_crc24", crc_bit)
                ctx.set_output("info_bit_after_crc24_valid", 1)
                crc_bit_count += 1
                if crc_bit_count == 23:
                    ctx.set_output("info_bit_after_crc24_valid_last", 1)
                    state = 0
                else:
                    ctx.set_output("info_bit_after_crc24_valid_last", 0)
            else:
                ctx.set_output("info_bit_after_crc24_valid", 0)

        ctx.set_state("state", state)
        ctx.set_state("info_bit_count", bit_count)
        ctx.set_state("crc_bit_count", crc_bit_count)
        ctx.set_state("clk_count", clk_count)

    return behavior


def scramble_wrapper_template(
    channel_width: int = 6,
    payload_len_bits: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Whitening wrapper: bypass first 40 bits, 1-bit delay."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        ch = ctx.get_input("channel_number", 0)
        ch_load = ctx.get_input("channel_number_load", 0)
        data_in = ctx.get_input("data_in", 0)
        data_valid = ctx.get_input("data_in_valid", 0)
        data_last = ctx.get_input("data_in_valid_last", 0)

        state = ctx.get_state("state", 0)
        data_count = ctx.get_state("data_in_count", 0)
        lfsr = ctx.get_state("lfsr", 0)

        ch_internal = ch if ch != 0 else (1 << channel_width) - 1

        if rst:
            ctx.set_state("state", 0)
            ctx.set_state("data_in_count", 0)
            lfsr = 1 | (ch_internal << 1)
            ctx.set_state("lfsr", lfsr)
            return

        if ch_load:
            lfsr = 1 | (ch_internal << 1)
            ctx.set_state("lfsr", lfsr)

        if state == 0:
            if data_valid:
                data_count += 1
                state = 1
        else:
            if data_last:
                data_count = 0
                state = 0
            elif data_valid:
                data_count += 1

            # Scramble after 40 bits
            if data_valid and data_count >= 40:
                b0 = (lfsr >> 6) & 1
                b1 = lfsr & 1
                b2 = (lfsr >> 1) & 1
                b3 = (lfsr >> 2) & 1
                b4 = ((lfsr >> 3) & 1) ^ ((lfsr >> 6) & 1)
                b5 = (lfsr >> 4) & 1
                b6 = (lfsr >> 5) & 1
                lfsr = (b6 << 6) | (b5 << 5) | (b4 << 4) | (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
                ctx.set_state("lfsr", lfsr)

        ctx.set_state("state", state)
        ctx.set_state("data_in_count", data_count)

        if data_count >= 41:
            ctx.set_output("data_out", ((lfsr >> 6) & 1) ^ data_in)
        else:
            ctx.set_output("data_out", data_in)
        ctx.set_output("data_out_valid", data_valid)
        ctx.set_output("data_out_valid_last", data_last)

    return behavior


def vco_template(
    vco_width: int = 16,
    rom_addr_width: int = 11,
    iq_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """VCO behavior: phase accumulator + sin/cos ROM lookup."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        voltage = ctx.get_input("voltage_signal", 0)
        voltage_valid = ctx.get_input("voltage_signal_valid", 0)
        voltage_last = ctx.get_input("voltage_signal_valid_last", 0)

        integral = ctx.get_state("integral", 0)

        if rst:
            ctx.set_state("integral", 0)
            return

        if voltage_valid:
            integral = (integral + voltage) & ((1 << vco_width) - 1)
            ctx.set_state("integral", integral)

        addr = integral & ((1 << rom_addr_width) - 1)
        cos_out = ctx.get_state(f"cos_table_{addr}", 0)
        sin_out = ctx.get_state(f"sin_table_{addr}", 0)

        ctx.set_output("cos_out", cos_out)
        ctx.set_output("sin_out", sin_out)
        ctx.set_output("sin_cos_out_valid", voltage_valid)
        ctx.set_output("sin_cos_out_valid_last", voltage_last)

    return behavior


def gfsk_mod_template(
    sample_per_symbol: int = 8,
    gauss_width: int = 16,
    num_tap: int = 17,
    vco_width: int = 16,
    rom_addr_width: int = 11,
    iq_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """GFSK modulator: upsample → Gaussian FIR → VCO."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        phy_bit = ctx.get_input("phy_bit", 0)
        bit_valid = ctx.get_input("bit_valid", 0)
        bit_last = ctx.get_input("bit_valid_last", 0)

        if rst:
            ctx.set_state("vco_integral", 0)
            return

        # Simplified: pass bit through to VCO
        if bit_valid:
            voltage = 100 if phy_bit else -100
            integral = ctx.get_state("vco_integral", 0)
            integral = (integral + voltage) & ((1 << vco_width) - 1)
            ctx.set_state("vco_integral", integral)

            addr = integral & ((1 << rom_addr_width) - 1)
            cos_out = ctx.get_state(f"cos_table_{addr}", 0)
            sin_out = ctx.get_state(f"sin_table_{addr}", 0)
            ctx.set_output("cos_out", cos_out)
            ctx.set_output("sin_out", sin_out)
            ctx.set_output("sin_cos_out_valid", 1)
            ctx.set_output("sin_cos_out_valid_last", bit_last)

    return behavior


def btle_rx_core_template(
    demod_width: int = 16,
    len_seq: int = 32,
    channel_width: int = 6,
    crc_width: int = 24,
    payload_len_bits: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BTLE RX core: GFSK demod → AA search → descramble → CRC.

    3-state FSM: IDLE → EXTRACT_LENGTH → CHECK_CRC
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        i_in = ctx.get_input("i", 0)
        q_in = ctx.get_input("q", 0)
        iq_valid = ctx.get_input("iq_valid", 0)
        aa = ctx.get_input("unique_bit_sequence", 0)
        ch = ctx.get_input("channel_number", 0)
        crc_init = ctx.get_input("crc_state_init_bit", 0)

        state = ctx.get_state("rx_state", 0)
        bit_count = ctx.get_state("bit_count", 0)

        aa_internal = aa if aa != 0 else 0x123a5456
        ch_internal = ch if ch != 0 else (1 << channel_width) - 1

        if rst:
            ctx.set_state("rx_state", 0)
            ctx.set_state("bit_count", 0)
            ctx.set_state("bit_store", 0)
            ctx.set_state("lfsr", crc_init)
            ctx.set_state("scramble_lfsr", 1 | (ch_internal << 1))
            return

        # Demod: i0*q1 - i1*q0 → phy_bit
        sig = ctx.get_state("sig_decision", 0)
        iq_d1 = ctx.get_state("iq_valid_d1", 0)
        iq_d2 = ctx.get_state("iq_valid_d2", 0)
        iq_d3 = ctx.get_state("iq_valid_d3", 0)

        iq_d3 = iq_d2
        iq_d2 = iq_d1
        iq_d1 = iq_valid
        ctx.set_state("iq_valid_d1", iq_d1)
        ctx.set_state("iq_valid_d2", iq_d2)
        ctx.set_state("iq_valid_d3", iq_d3)

        if iq_valid:
            sig = (i_in * q_in)  # Simplified
            ctx.set_state("sig_decision", sig)

        phy_bit = 1 if sig > 0 else 0

        # AA search
        bit_store = ctx.get_state("bit_store", 0)
        bit_v_d1 = ctx.get_state("bit_valid_d1", 0)
        if iq_d3:
            bit_store = ((bit_store >> 1) | (phy_bit << 31)) & 0xFFFFFFFF
            ctx.set_state("bit_store", bit_store)
        bit_v_d1 = iq_d3
        ctx.set_state("bit_valid_d1", bit_v_d1)
        hit = (bit_store == aa_internal) and bit_v_d1

        # Descramble
        s_lfsr = ctx.get_state("scramble_lfsr", 0)
        if iq_d3:
            b0 = (s_lfsr >> 6) & 1
            b1 = s_lfsr & 1
            b2 = (s_lfsr >> 1) & 1
            b3 = (s_lfsr >> 2) & 1
            b4 = ((s_lfsr >> 3) & 1) ^ ((s_lfsr >> 6) & 1)
            b5 = (s_lfsr >> 4) & 1
            b6 = (s_lfsr >> 5) & 1
            s_lfsr = (b6 << 6) | (b5 << 5) | (b4 << 4) | (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
            ctx.set_state("scramble_lfsr", s_lfsr)
        scramble_out = ((s_lfsr >> 6) & 1) ^ phy_bit
        scramble_valid = iq_d3

        # CRC
        c_lfsr = ctx.get_state("lfsr", 0)
        if scramble_valid:
            new_bit = (c_lfsr >> 23) & 1 ^ scramble_out
            c_lfsr = ((c_lfsr >> 1) & 0x7FFFFF) | (new_bit << 0)
            # Simplified: just shift
            ctx.set_state("lfsr", c_lfsr)

        # FSM
        ctx.set_output("hit_flag", 1 if hit else 0)
        ctx.set_output("info_bit", scramble_out)
        ctx.set_output("bit_valid", scramble_valid)

        if state == 0:  # IDLE
            if hit:
                state = 1
                ctx.set_state("bit_count", 0)
        elif state == 1:  # EXTRACT_LENGTH
            if scramble_valid:
                bit_count += 1
            if (bit_count >> 3) >= 2:
                ctx.set_state("payload_length", 0)
                ctx.set_state("payload_length_valid", 1)
                state = 2
        else:  # CHECK_CRC
            if scramble_valid:
                bit_count += 1
            payload_len = ctx.get_state("payload_length", 0)
            if (bit_count >> 3) >= (payload_len + 3):
                ctx.set_output("decode_end", 1)
                ctx.set_output("crc_ok", 1 if c_lfsr == 0 else 0)
                state = 0

        ctx.set_state("rx_state", state)
        ctx.set_state("bit_count", bit_count)

    return behavior


def btle_tx_template(
    payload_len_bits: int = 8,
    crc_width: int = 24,
    channel_width: int = 6,
    vco_width: int = 16,
    rom_addr_width: int = 11,
    iq_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BTLE TX: PDU RAM → preamble+AA → CRC+scramble → GFSK modulate.

    4-state FSM: IDLE → TX_PREAMBLE_ACCESS → TX_PDU → WAIT_LAST_SAMPLE
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        tx_start = ctx.get_input("tx_start", 0)
        preamble = ctx.get_input("preamble", 0)
        aa = ctx.get_input("access_address", 0)
        ch = ctx.get_input("channel_number", 0)
        crc_init = ctx.get_input("crc_state_init_bit", 0)
        crc_init_load = ctx.get_input("crc_state_init_bit_load", 0)

        state = ctx.get_state("tx_state", 0)
        clk_count = ctx.get_state("tx_clk_count", 0)
        bit_count = ctx.get_state("tx_bit_count", 0)
        pa_reg = ctx.get_state("tx_pa_reg", 0)

        if rst:
            ctx.set_state("tx_state", 0)
            ctx.set_state("tx_clk_count", 0)
            ctx.set_state("tx_bit_count", 0)
            ctx.set_state("tx_pa_reg", 0)
            return

        if state == 0:  # IDLE
            if tx_start:
                pa_reg = ((aa & 0xFFFFFFFF) << 8) | (preamble & 0xFF)
                clk_count = 0
                bit_count = 0
                state = 1
                ctx.set_state("tx_pa_reg", pa_reg)

        elif state == 1:  # TX_PREAMBLE_ACCESS
            clk_count += 1
            if (clk_count & 0xF) == 1:
                bit_out = pa_reg & 1
                pa_reg = (pa_reg >> 1) & ((1 << 40) - 1)
                bit_count += 1
                if bit_count == 40:
                    state = 2
                ctx.set_output("iq_valid", 1)
                ctx.set_output("i", 50 if bit_out else -50)
                ctx.set_output("q", 0)
            else:
                ctx.set_output("iq_valid", 0)

        elif state == 2:  # TX_PDU
            clk_count += 1
            if (clk_count & 0xF) == 1:
                bit_count += 1
                if bit_count >= 200:
                    state = 3
                ctx.set_output("iq_valid", 1)

        else:  # WAIT_LAST_SAMPLE
            ctx.set_output("iq_valid", 0)
            state = 0

        ctx.set_state("tx_state", state)
        ctx.set_state("tx_clk_count", clk_count)
        ctx.set_state("tx_bit_count", bit_count)

    return behavior


def btle_phy_template(
    demod_width: int = 16,
    len_seq: int = 32,
    channel_width: int = 6,
    crc_width: int = 24,
    payload_len_bits: int = 8,
    vco_width: int = 16,
    rom_addr_width: int = 11,
    iq_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BTLE PHY wrapper: TX + RX combined."""
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        tx_start = ctx.get_input("tx_start", 0)
        rx_iq_valid = ctx.get_input("rx_iq_valid", 0)
        rx_i = ctx.get_input("rx_i_signal", 0)
        rx_q = ctx.get_input("rx_q_signal", 0)

        if rst:
            ctx.set_state("phy_tx_state", 0)
            ctx.set_state("phy_rx_state", 0)
            return

        # TX: simplified FSM
        tx_state = ctx.get_state("phy_tx_state", 0)
        if tx_state == 0 and tx_start:
            ctx.set_state("phy_tx_state", 1)
            ctx.set_output("tx_iq_valid", 1)
            ctx.set_output("tx_i_signal", 50)
            ctx.set_output("tx_q_signal", 0)
        elif tx_state == 1:
            clk = ctx.get_state("phy_tx_clk", 0) + 1
            ctx.set_state("phy_tx_clk", clk)
            if (clk & 0xF) == 1:
                ctx.set_output("tx_iq_valid", 1)
            else:
                ctx.set_output("tx_iq_valid", 0)
            if clk > 500:
                ctx.set_state("phy_tx_state", 0)

        # RX: simplified
        if rx_iq_valid:
            hit = rx_i > 0
            ctx.set_output("rx_hit_flag", 1 if hit else 0)
            ctx.set_output("rx_decode_run", 1 if hit else 0)

    return behavior


# Register all templates at import time
TemplateRegistry.register("crc24_core", crc24_core_template)
TemplateRegistry.register("scramble_core", scramble_core_template)
TemplateRegistry.register("access_address_detect", access_address_detect_template)
TemplateRegistry.register("gfsk_demod", gfsk_demod_template)
TemplateRegistry.register("gauss_filter", gauss_filter_template)
TemplateRegistry.register("bit_upsampler", bit_upsampler_template)
TemplateRegistry.register("sdpram", sdpram_template)
TemplateRegistry.register("crc_wrapper", crc_wrapper_template)
TemplateRegistry.register("scramble_wrapper", scramble_wrapper_template)
TemplateRegistry.register("vco", vco_template)
TemplateRegistry.register("gfsk_mod", gfsk_mod_template)
TemplateRegistry.register("btle_rx_core", btle_rx_core_template)
TemplateRegistry.register("btle_tx", btle_tx_template)
TemplateRegistry.register("btle_phy", btle_phy_template)
