"""
skills.interfaces.spi.behaviors — SPI Controller Behavior Templates

Domain-specific behavior templates for APB-SPI controller components.
Registered into TemplateRegistry at import time.

Components:
  - spi_registers:  APB register file (CONFIG/STATUS/IMASK/ENABLE/DELAY/TXD/RXD/SIC/TX_THRESH/RX_THRESH)
  - spi_control:    12-state Master/Slave FSM with timing generation
  - spi_transmit:   TX FIFO management + parallel-to-serial output
  - spi_receive:    Serial-to-parallel deserialization + RX FIFO
  - spi_slave_sync: Slave data/clock synchronization with metastability protection
  - spi_slave_tx:   Slave bit-select down-counter (slave_in_clk domain)
  - spi_ext_sync:   External clock edge detector
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# SPIRegisters Template
# =====================================================================

def spi_registers_template(
    num_slave_selects: int = 4,
    fifo_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """APB register interface behavior.

    Models 9 APB registers at addresses 0x00-0x24:
      CONFIG(0x00), STATUS(0x04), IMASK(0x08), ENABLE(0x0C),
      DELAY(0x10), TXD(0x14), RXD(0x18), SIC(0x1C),
      TX_THRESH(0x20), RX_THRESH(0x24)

    Interrupt generation from 7 maskable sources:
      rx_full, rx_notempty, tx_notfull, tx_empty,
      tx_underflow, s_modf, m_modf
    """
    def behavior(ctx: CycleContext):
        psel = ctx.get_input("psel_i", 0)
        penable = ctx.get_input("penable_i", 0)
        pwrite = ctx.get_input("pwrite_i", 0)
        paddr = ctx.get_input("paddr_i", 0)
        pwdata = ctx.get_input("pwdata_i", 0)

        # Register state
        config_reg = ctx.get_state("config_reg", 0)
        imask_reg = ctx.get_state("imask_reg", 0)
        enable_reg = ctx.get_state("enable_reg", 0)
        delay_reg = ctx.get_state("delay_reg", 0)
        sic_reg = ctx.get_state("sic_reg", 0)
        tx_thresh = ctx.get_state("tx_thresh", 0)
        rx_thresh = ctx.get_state("rx_thresh", 0)

        # FIFO status inputs
        rx_full_i = ctx.get_input("rx_full_i", 0)
        rx_notempty_i = ctx.get_input("rx_notempty_i", 0)
        tx_notfull_i = ctx.get_input("tx_notfull_i", 0)
        tx_empty_i = ctx.get_input("tx_empty_i", 0)
        tx_underflow_i = ctx.get_input("tx_underflow_i", 0)
        s_modf_i = ctx.get_input("s_modf_i", 0)
        m_modf_i = ctx.get_input("m_modf_i", 0)
        idle_spi_i = ctx.get_input("idle_spi_i", 0)
        rx_fifo_i = ctx.get_input("rx_fifo_i", 0)

        # APB read
        prdata = 0
        if psel and penable and not pwrite:
            if paddr == 0x00:
                prdata = config_reg
            elif paddr == 0x04:
                # STATUS: build from FIFO flags + error flags
                status = 0
                if tx_empty_i:
                    status |= (1 << 0)
                if tx_notfull_i:
                    status |= (1 << 2)
                if rx_notempty_i:
                    status |= (1 << 3)
                if rx_full_i:
                    status |= (1 << 4)
                if tx_underflow_i:
                    status |= (1 << 5)
                if s_modf_i:
                    status |= (1 << 6)
                if m_modf_i:
                    status |= (1 << 7)
                prdata = status
            elif paddr == 0x08:
                prdata = imask_reg
            elif paddr == 0x0C:
                prdata = enable_reg
            elif paddr == 0x10:
                prdata = delay_reg
            elif paddr == 0x18:
                prdata = rx_fifo_i
            elif paddr == 0x1C:
                prdata = sic_reg
            elif paddr == 0x20:
                prdata = tx_thresh
            elif paddr == 0x24:
                prdata = rx_thresh

        # APB write
        if psel and penable and pwrite:
            if paddr == 0x00:
                config_reg = pwdata
            elif paddr == 0x08:
                imask_reg = pwdata & 0x7F
            elif paddr == 0x0C:
                enable_reg = pwdata & 0x1
            elif paddr == 0x10:
                delay_reg = pwdata
            elif paddr == 0x1C:
                sic_reg = pwdata & 0xFF
            elif paddr == 0x20:
                tx_thresh = pwdata & 0x7
            elif paddr == 0x24:
                rx_thresh = pwdata & 0x7

        # Extract config fields
        master = config_reg & 0x1
        cpol = (config_reg >> 1) & 0x1
        cpha = (config_reg >> 2) & 0x1
        cks = (config_reg >> 3) & 0x1
        pdec = (config_reg >> 4) & 0x1
        ss = (config_reg >> 5) & ((1 << num_slave_selects) - 1)
        datasize = (config_reg >> 10) & 0x1F
        baud_rate = (config_reg >> 16) & 0xFF

        # Interrupt generation
        int_rx_full = rx_full_i & ((imask_reg >> 0) & 0x1)
        int_rx_notempty = rx_notempty_i & ((imask_reg >> 1) & 0x1)
        int_tx_notfull = tx_notfull_i & ((imask_reg >> 2) & 0x1)
        int_tx_empty = tx_empty_i & ((imask_reg >> 3) & 0x1)
        int_tx_underflow = tx_underflow_i & ((imask_reg >> 4) & 0x1)
        int_s_modf = s_modf_i & ((imask_reg >> 5) & 0x1)
        int_m_modf = m_modf_i & ((imask_reg >> 6) & 0x1)
        interrupt = int_rx_full | int_rx_notempty | int_tx_notfull | \
                    int_tx_empty | int_tx_underflow | int_s_modf | int_m_modf

        # Push/pop signals (timed to APB access)
        tx_push = 1 if (psel and penable and pwrite and paddr == 0x14) else 0
        rx_pop = 1 if (psel and penable and not pwrite and paddr == 0x18) else 0
        tx_clr = 0  # Cleared by separate mechanism
        rx_clr = 0

        # Clear FIFO on tx_push when tx_full
        if tx_push and not rx_full_i:
            ctx.set_state("rx_push_pending", 1)

        # Write outputs
        ctx.set_output("prdata_o", prdata)
        ctx.set_output("interrupt_o", interrupt)
        ctx.set_output("master_o", master)
        ctx.set_output("cpha_o", cpha)
        ctx.set_output("cpol_o", cpol)
        ctx.set_output("cks_o", cks)
        ctx.set_output("pdec_o", pdec)
        ctx.set_output("ss_o", ss)
        ctx.set_output("spi_enable_o", enable_reg)
        ctx.set_output("datasize_o", datasize)
        ctx.set_output("d_init_o", delay_reg & 0xFF)
        ctx.set_output("d_after_o", (delay_reg >> 8) & 0xFF)
        ctx.set_output("d_btwn_o", (delay_reg >> 16) & 0xFF)
        ctx.set_output("d_nss_o", (delay_reg >> 24) & 0xFF)
        ctx.set_output("baud_rate_o", baud_rate)
        ctx.set_output("sic_reg_o", sic_reg)
        ctx.set_output("tx_threshold_o", tx_thresh)
        ctx.set_output("rx_threshold_o", rx_thresh)
        ctx.set_output("man_cs_o", (config_reg >> 25) & 0x1)
        ctx.set_output("man_start_en_o", (config_reg >> 26) & 0x1)
        ctx.set_output("man_start_o", (config_reg >> 27) & 0x1)
        ctx.set_output("modf_en_o", (config_reg >> 28) & 0x1)
        ctx.set_output("m_shiften_del_en_o", (config_reg >> 29) & 0x1)
        ctx.set_output("bsr_o", (config_reg >> 30) & 0x7)

        ctx.set_output("tx_push_o", tx_push)
        ctx.set_output("rx_pop_o", rx_pop)
        ctx.set_output("tx_clr_o", tx_clr)
        ctx.set_output("rx_clr_o", rx_clr)

        # Status for downstream
        ctx.set_output("rx_full_apb_o", rx_full_i)

        # Persist register state
        ctx.set_state("config_reg", config_reg)
        ctx.set_state("imask_reg", imask_reg)
        ctx.set_state("enable_reg", enable_reg)
        ctx.set_state("delay_reg", delay_reg)
        ctx.set_state("sic_reg", sic_reg)
        ctx.set_state("tx_thresh", tx_thresh)
        ctx.set_state("rx_thresh", rx_thresh)

    return behavior


# =====================================================================
# SPIControl Template
# =====================================================================

def spi_control_template(
    fifo_word_size: int = 32,
    delay_size: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """12-state Master/Slave FSM behavior.

    States:
      RESET(0), M_IDLE(1), M_PREAMBLE(2), M_SHIFT1(3), M_SHIFT2(4),
      M_POSTAMBLE(5), M_PAUSE(6), S_IDLE(7), S_PREAMBLE(8),
      S_SHIFT(9), S_POSTAMBLE(10), S_DONE(11)

    Generates:
      - m_txsel: master bit-select counter
      - tx_pop: TX FIFO pop on bit boundary
      - rx_push: RX FIFO push on word complete
      - m_shiften: master shift enable (gated by baud-rate counter)
      - sclk_out: SPI clock output
      - ss_valid: valid slave select
      - mode-fail detection
    """
    # State constants
    STATE_RESET = 0
    STATE_M_IDLE = 1
    STATE_M_PREAMBLE = 2
    STATE_M_SHIFT1 = 3
    STATE_M_SHIFT2 = 4
    STATE_M_POSTAMBLE = 5
    STATE_M_PAUSE = 6
    STATE_S_IDLE = 7
    STATE_S_PREAMBLE = 8
    STATE_S_SHIFT = 9
    STATE_S_POSTAMBLE = 10
    STATE_S_DONE = 11

    def behavior(ctx: CycleContext):
        s_shiften_i = ctx.get_input("s_shiften_i", 0)
        m_clocken_i = ctx.get_input("m_clocken_i", 1)
        s_inprogress_i = ctx.get_input("s_inprogress_i", 0)
        cpol_i = ctx.get_input("cpol_i", 0)
        cpha_i = ctx.get_input("cpha_i", 0)
        tx_empty_i = ctx.get_input("tx_empty_i", 1)
        master_i = ctx.get_input("master_i", 1)
        spi_enable_i = ctx.get_input("spi_enable_i", 0)
        spi_enable_del3_i = ctx.get_input("spi_enable_del3_i", 0)
        n_ss_in_sync_i = ctx.get_input("n_ss_in_sync_i", 1)
        datasize_i = ctx.get_input("datasize_i", 7)
        d_init_i = ctx.get_input("d_init_i", 0)
        d_after_i = ctx.get_input("d_after_i", 0)
        d_btwn_i = ctx.get_input("d_btwn_i", 0)
        d_nss_i = ctx.get_input("d_nss_i", 0)
        baud_rate_i = ctx.get_input("baud_rate_i", 0)
        sclk_in_i = ctx.get_input("sclk_in_i", 0)
        tx_uf_i = ctx.get_input("tx_uf_i", 0)
        sic_reg_i = ctx.get_input("sic_reg_i", 0)
        man_start_en_i = ctx.get_input("man_start_en_i", 0)
        man_start_i = ctx.get_input("man_start_i", 0)
        modf_en_i = ctx.get_input("modf_en_i", 0)
        bsr_i = ctx.get_input("bsr_i", 0)
        m_shiften_del_en_i = ctx.get_input("m_shiften_del_en_i", 0)

        # State
        pr_state = ctx.get_state("pr_state", STATE_RESET)
        master_count = ctx.get_state("master_count", 0)
        m_txsel = ctx.get_state("m_txsel", 0)
        ds_txsel = ctx.get_state("ds_txsel", 0)
        m_shiften = ctx.get_state("m_shiften", 0)
        m_modf = ctx.get_state("m_modf", 0)
        s_modf = ctx.get_state("s_modf", 0)
        ss_valid = ctx.get_state("ss_valid", 0)
        busfree = ctx.get_state("busfree", 0)
        idle_spi = ctx.get_state("idle_spi", 1)
        sclk_out = ctx.get_state("sclk_out", 0)
        gate_tx = ctx.get_state("gate_tx", 0)

        if not spi_enable_i:
            pr_state = STATE_RESET
            master_count = 0
            m_txsel = 0
            ds_txsel = 0
            m_shiften = 0
            m_modf = 0
            s_modf = 0
            ss_valid = 0
            busfree = 0
            idle_spi = 1
            sclk_out = 0
            gate_tx = 0
        elif pr_state == STATE_RESET:
            pr_state = STATE_M_IDLE if master_i else STATE_S_IDLE

        elif master_i:
            # --- Master path ---
            if pr_state == STATE_M_IDLE:
                idle_spi = 1
                if not tx_empty_i and spi_enable_del3_i:
                    if man_start_en_i and not man_start_i:
                        pass  # wait for manual start
                    else:
                        pr_state = STATE_M_PREAMBLE
                        master_count = d_init_i
                        ds_txsel = 0
                        m_txsel = 0
                        idle_spi = 0
                        ss_valid = 1

            elif pr_state == STATE_M_PREAMBLE:
                idle_spi = 0
                if master_count > 0:
                    if m_clocken_i:
                        master_count -= 1
                else:
                    pr_state = STATE_M_SHIFT1
                    m_shiften = 1
                    sclk_out = ~cpol_i if not cpha_i else cpol_i

            elif pr_state == STATE_M_SHIFT1:
                idle_spi = 0
                if m_clocken_i:
                    sclk_out = ~sclk_out
                    if (sclk_out and not cpha_i) or (not sclk_out and cpha_i):
                        if m_txsel == 0:
                            m_txsel = datasize_i
                            ds_txsel += 1
                        else:
                            m_txsel -= 1
                        # Check if word complete
                        if ds_txsel >= ((fifo_word_size + datasize_i) // (datasize_i + 1)):
                            pr_state = STATE_M_POSTAMBLE
                            master_count = d_after_i
                            m_shiften = 0
                            ss_valid = 0
                            ds_txsel = 0

            elif pr_state == STATE_M_SHIFT2:
                idle_spi = 0
                if m_clocken_i:
                    sclk_out = ~sclk_out
                    if (sclk_out and not cpha_i) or (not sclk_out and cpha_i):
                        if m_txsel == 0:
                            m_txsel = datasize_i
                            ds_txsel += 1
                        else:
                            m_txsel -= 1
                        if ds_txsel >= ((fifo_word_size + datasize_i) // (datasize_i + 1)):
                            pr_state = STATE_M_POSTAMBLE
                            master_count = d_after_i
                            m_shiften = 0
                            ss_valid = 0
                            ds_txsel = 0

            elif pr_state == STATE_M_POSTAMBLE:
                idle_spi = 0
                if master_count > 0:
                    if m_clocken_i:
                        master_count -= 1
                else:
                    if not tx_empty_i:
                        pr_state = STATE_M_PREAMBLE
                        master_count = d_btwn_i
                        m_txsel = 0
                        ss_valid = 1
                    else:
                        pr_state = STATE_M_PAUSE
                        master_count = d_nss_i

            elif pr_state == STATE_M_PAUSE:
                if master_count > 0:
                    if m_clocken_i:
                        master_count -= 1
                else:
                    pr_state = STATE_M_IDLE
                    sclk_out = 0

            # Master mode-fail: n_ss_in asserted during transfer
            if modf_en_i and pr_state not in (STATE_M_IDLE, STATE_M_PAUSE, STATE_RESET):
                if not n_ss_in_sync_i:
                    m_modf = 1

        else:
            # --- Slave path ---
            if pr_state == STATE_S_IDLE:
                idle_spi = 1
                m_shiften = 0
                sclk_out = 0
                if s_inprogress_i:
                    pr_state = STATE_S_PREAMBLE
                    idle_spi = 0

            elif pr_state == STATE_S_PREAMBLE:
                idle_spi = 0
                if s_shiften_i:
                    pr_state = STATE_S_SHIFT
                    m_txsel = 0

            elif pr_state == STATE_S_SHIFT:
                idle_spi = 0
                if s_shiften_i:
                    if m_txsel == 0:
                        m_txsel = datasize_i
                        pr_state = STATE_S_POSTAMBLE
                    else:
                        m_txsel -= 1

            elif pr_state == STATE_S_POSTAMBLE:
                pr_state = STATE_S_DONE

            elif pr_state == STATE_S_DONE:
                pr_state = STATE_S_IDLE

            # Slave mode-fail: n_ss_in deasserted mid-transfer
            if modf_en_i and pr_state in (STATE_S_SHIFT, STATE_S_POSTAMBLE):
                if n_ss_in_sync_i:
                    s_modf = 1

        # Bus-free detection (for master idle)
        if master_i and pr_state == STATE_M_IDLE:
            if not n_ss_in_sync_i:
                busfree = 1
            else:
                busfree = 0

        # Gate TX on underflow
        if tx_uf_i:
            gate_tx = 1

        # Outputs
        ctx.set_output("m_txsel_o", m_txsel)
        tx_pop = 1 if (master_i and pr_state in (STATE_M_SHIFT1, STATE_M_SHIFT2) and m_txsel == datasize_i) else 0
        rx_push = 1 if ((master_i and pr_state == STATE_M_POSTAMBLE and master_count == 0) or
                        (not master_i and pr_state == STATE_S_DONE)) else 0
        ctx.set_output("tx_pop_o", tx_pop)
        ctx.set_output("rx_push_o", rx_push)
        ctx.set_output("m_shiften_out_o", m_shiften)
        ctx.set_output("sclk_out_o", sclk_out if master_i else 0)
        ctx.set_output("ss_valid_o", ss_valid)
        ctx.set_output("s_modf_o", s_modf)
        ctx.set_output("m_modf_o", m_modf)
        ctx.set_output("idle_spi_o", idle_spi)
        ctx.set_output("start_slave_o", 0)
        ctx.set_output("tx_underflow_o", tx_uf_i)
        ctx.set_output("so_reg_en_o", 0)
        ctx.set_output("m_out_change_o", 1 if (master_i and m_txsel == 0) else 0)
        ctx.set_output("busfree_o", busfree)
        ctx.set_output("gate_tx_o", gate_tx)

        # Persist state
        ctx.set_state("pr_state", pr_state)
        ctx.set_state("master_count", master_count)
        ctx.set_state("m_txsel", m_txsel)
        ctx.set_state("ds_txsel", ds_txsel)
        ctx.set_state("m_shiften", m_shiften)
        ctx.set_state("m_modf", m_modf)
        ctx.set_state("s_modf", s_modf)
        ctx.set_state("ss_valid", ss_valid)
        ctx.set_state("busfree", busfree)
        ctx.set_state("idle_spi", idle_spi)
        ctx.set_state("sclk_out", sclk_out)
        ctx.set_state("gate_tx", gate_tx)

    return behavior


# =====================================================================
# SPITransmit Template
# =====================================================================

def spi_transmit_template(
    fifo_depth: int = 8,
    fifo_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """TX path behavior: FIFO management + serializer + output enables.

    Models:
      - TX FIFO push/pop with full/empty/threshold flags
      - Master output register (glitch-free mo)
      - Slave serializer with so_reg for last-bit hold
      - Parallel-to-serial MUX (32-bit → 1-bit mo/so)
      - Slave select decoder
    """
    def behavior(ctx: CycleContext):
        tx_push_i = ctx.get_input("tx_push_i", 0)
        tx_pop_i = ctx.get_input("tx_pop_i", 0)
        pwdata_i = ctx.get_input("pwdata_i", 0)
        master_i = ctx.get_input("master_i", 1)
        spi_enable_i = ctx.get_input("spi_enable_i", 0)
        n_ss_in_i = ctx.get_input("n_ss_in_i", 1)
        m_txsel_i = ctx.get_input("m_txsel_i", 0)
        s_txsel_i = ctx.get_input("s_txsel_i", 0)
        so_reg_en_i = ctx.get_input("so_reg_en_i", 0)
        gate_tx_i = ctx.get_input("gate_tx_i", 0)
        m_out_change_i = ctx.get_input("m_out_change_i", 0)
        man_cs_i = ctx.get_input("man_cs_i", 0)
        ss_i = ctx.get_input("ss_i", 0)
        pdec_i = ctx.get_input("pdec_i", 0)
        ss_valid_i = ctx.get_input("ss_valid_i", 0)

        fifo_count = ctx.get_state("fifo_count", 0)
        fifo_data = ctx.get_state("fifo_data", 0)
        master_out = ctx.get_state("master_out", 0)
        so_reg = ctx.get_state("so_reg", 0)

        # TX FIFO push
        if tx_push_i and fifo_count < fifo_depth:
            fifo_data = pwdata_i
            fifo_count += 1

        # TX FIFO pop
        if tx_pop_i and fifo_count > 0:
            fifo_count -= 1

        # Master output update (glitch-free)
        if master_i and m_out_change_i:
            master_out = fifo_data

        # so_reg for slave mode
        if so_reg_en_i and not master_i:
            so_reg = fifo_data & 0x7

        # Serializer output
        if master_i:
            bit_idx = m_txsel_i
            mo = (master_out >> bit_idx) & 0x1
            so = 0
        else:
            bit_idx = s_txsel_i
            if gate_tx_i:
                so = (so_reg >> (bit_idx % 3)) & 0x1
            else:
                so = (fifo_data >> bit_idx) & 0x1
            mo = 0

        # Output enables
        n_so_en = ~(spi_enable_i & ~master_i & ~n_ss_in_i)
        n_mo_en = ~(spi_enable_i & master_i)
        n_ss_en = ~(spi_enable_i & master_i)
        n_sclk_en = ~(spi_enable_i & master_i)

        # Slave select
        if not ss_valid_i and not man_cs_i:
            n_ss_out = 0xF
        elif pdec_i:
            n_ss_out = ~(ss_i & 0xF) & 0xF
        else:
            # One-hot decode
            ss_val = ss_i & 0x3
            n_ss_out = ~(1 << ss_val) & 0xF

        ctx.set_output("mo_o", mo)
        ctx.set_output("so_o", so)
        ctx.set_output("n_so_en_o", n_so_en)
        ctx.set_output("n_mo_en_o", n_mo_en)
        ctx.set_output("n_ss_out_o", n_ss_out)
        ctx.set_output("n_ss_en_o", n_ss_en)
        ctx.set_output("tx_empty_o", 1 if fifo_count <= 0 else 0)
        ctx.set_output("tx_notfull_o", 1 if fifo_count < fifo_depth else 0)
        ctx.set_output("tx_full_o", 1 if fifo_count >= fifo_depth else 0)
        ctx.set_output("n_sclk_en_o", n_sclk_en)

        ctx.set_state("fifo_count", fifo_count)
        ctx.set_state("fifo_data", fifo_data)
        ctx.set_state("master_out", master_out)
        ctx.set_state("so_reg", so_reg)

    return behavior


# =====================================================================
# SPIReceive Template
# =====================================================================

def spi_receive_template(
    fifo_depth: int = 8,
    fifo_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """RX path behavior: deserializer + RX FIFO.

    Models:
      - Serial-to-parallel shift register (32-bit)
      - Master/slave input MUX
      - RX FIFO push/pop with full/empty flags
    """
    def behavior(ctx: CycleContext):
        m_shiften_i = ctx.get_input("m_shiften_i", 0)
        s_shiften_i = ctx.get_input("s_shiften_i", 0)
        s_inprogress_i = ctx.get_input("s_inprogress_i", 0)
        mi_i = ctx.get_input("mi_i", 0)
        si_sync3_i = ctx.get_input("si_sync3_i", 0)
        master_i = ctx.get_input("master_i", 1)
        rx_push_i = ctx.get_input("rx_push_i", 0)
        rx_pop_i = ctx.get_input("rx_pop_i", 0)

        rx_data = ctx.get_state("rx_data", 0)
        fifo_count = ctx.get_state("fifo_count", 0)
        fifo_data = ctx.get_state("fifo_data", 0)

        # Input MUX
        s_to_p_in = (master_i & mi_i) | (~master_i & si_sync3_i)
        shiften_valid = s_shiften_i & s_inprogress_i

        # Shift register
        if shiften_valid or m_shiften_i:
            rx_data = ((rx_data << 1) | s_to_p_in) & 0xFFFFFFFF

        # RX FIFO push
        if rx_push_i and fifo_count < fifo_depth:
            fifo_data = rx_data
            fifo_count += 1

        # RX FIFO pop
        if rx_pop_i and fifo_count > 0:
            fifo_count -= 1

        ctx.set_output("rx_fifo_o", fifo_data)
        ctx.set_output("rx_notempty_o", 1 if fifo_count > 0 else 0)
        ctx.set_output("rx_full_o", 1 if fifo_count >= fifo_depth else 0)

        ctx.set_state("rx_data", rx_data)
        ctx.set_state("fifo_count", fifo_count)
        ctx.set_state("fifo_data", fifo_data)

    return behavior


# =====================================================================
# SPISlaveSync Template
# =====================================================================

def spi_slave_sync_template(
    n_flop_sync: int = 3,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Slave synchronization behavior.

    Models:
      - SI input N-flop metastability synchronizer
      - n_ss_in sync with edge detection (s_inprogress)
      - Slave clock generation (derived from sclk_in + CPOL/CPHA)
      - SPI enable delay chain
      - TX underflow detection
    """
    def behavior(ctx: CycleContext):
        si_i = ctx.get_input("si_i", 0)
        n_ss_in_i = ctx.get_input("n_ss_in_i", 1)
        cpol_i = ctx.get_input("cpol_i", 0)
        cpha_i = ctx.get_input("cpha_i", 0)
        spi_enable_i = ctx.get_input("spi_enable_i", 0)
        sclk_in_i = ctx.get_input("sclk_in_i", 0)
        start_slave_i = ctx.get_input("start_slave_i", 0)
        tx_empty_i = ctx.get_input("tx_empty_i", 1)

        # SI synchronizer chain
        si_sync1 = ctx.get_state("si_sync1", 0)
        si_sync2 = ctx.get_state("si_sync2", 0)
        si_sync3 = ctx.get_state("si_sync3", 0)

        # n_ss_in sync
        n_ss_sync1 = ctx.get_state("n_ss_sync1", 1)
        n_ss_sync2 = ctx.get_state("n_ss_sync2", 1)
        n_ss_sync3 = ctx.get_state("n_ss_sync3", 1)

        # SPI enable delay
        spi_en_del1 = ctx.get_state("spi_en_del1", 0)
        spi_en_del2 = ctx.get_state("spi_en_del2", 0)
        spi_en_del3 = ctx.get_state("spi_en_del3", 0)

        s_inprogress = ctx.get_state("s_inprogress", 0)
        n_ss_in_sync = ctx.get_state("n_ss_in_sync", 1)
        slave_out_clk = ctx.get_state("slave_out_clk", 0)
        s_shiften = ctx.get_state("s_shiften", 0)
        tx_uf = ctx.get_state("tx_uf", 0)

        # SI sync chain
        si_sync1 = si_i
        si_sync2 = si_sync1
        si_sync3 = si_sync2

        # n_ss_in sync chain
        n_ss_sync1 = n_ss_in_i
        n_ss_sync2 = n_ss_sync1
        n_ss_sync3 = n_ss_sync2
        n_ss_in_sync = n_ss_sync3

        # Edge detect: n_ss going low → s_inprogress
        n_ss_falling = (~n_ss_in_i) & n_ss_sync3
        if n_ss_falling and spi_enable_i:
            s_inprogress = 1
        elif not spi_enable_i:
            s_inprogress = 0

        # Slave clock generation
        s_inv = cpol_i ^ cpha_i
        s_inv_clk = (~sclk_in_i) if s_inv else sclk_in_i
        slave_out_clk = s_inv_clk & start_slave_i

        # SPI enable delay chain
        spi_en_del1 = spi_enable_i
        spi_en_del2 = spi_en_del1
        spi_en_del3 = spi_en_del2

        # Shift enable from n_ss edge in burst
        if n_ss_falling and spi_enable_i:
            s_shiften = 1
        elif not s_inprogress:
            s_shiften = 0

        # TX underflow: TX empty during slave transfer
        if tx_empty_i and s_inprogress:
            tx_uf = 1
        elif not s_inprogress:
            tx_uf = 0

        ctx.set_output("si_sync3_o", si_sync3)
        ctx.set_output("s_inprogress_o", s_inprogress)
        ctx.set_output("n_ss_in_sync_o", n_ss_in_sync)
        ctx.set_output("s_shiften_o", s_shiften)
        ctx.set_output("slave_out_clk_o", slave_out_clk)
        ctx.set_output("spi_enable_del3_o", spi_en_del3)
        ctx.set_output("tx_uf_o", tx_uf)

        ctx.set_state("si_sync1", si_sync1)
        ctx.set_state("si_sync2", si_sync2)
        ctx.set_state("si_sync3", si_sync3)
        ctx.set_state("n_ss_sync1", n_ss_sync1)
        ctx.set_state("n_ss_sync2", n_ss_sync2)
        ctx.set_state("n_ss_sync3", n_ss_sync3)
        ctx.set_state("spi_en_del1", spi_en_del1)
        ctx.set_state("spi_en_del2", spi_en_del2)
        ctx.set_state("spi_en_del3", spi_en_del3)
        ctx.set_state("s_inprogress", s_inprogress)
        ctx.set_state("n_ss_in_sync", n_ss_in_sync)
        ctx.set_state("slave_out_clk", slave_out_clk)
        ctx.set_state("s_shiften", s_shiften)
        ctx.set_state("tx_uf", tx_uf)

    return behavior


# =====================================================================
# SPISlaveTX Template
# =====================================================================

def spi_slave_tx_template(
    fifo_word_size: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Slave transmit bit-select counter behavior.

    Down-counter that wraps around, selecting which bit of the
    TX FIFO word drives the slave serial output (so).
    Clocked by slave_in_clk domain.
    """
    def behavior(ctx: CycleContext):
        n_ss_in_i = ctx.get_input("n_ss_in_i", 1)
        cpha_i = ctx.get_input("cpha_i", 0)

        s_txsel = ctx.get_state("s_txsel", 0)
        s_txsel_start = ctx.get_state("s_txsel_start", 1)

        if s_txsel_start and (not n_ss_in_i or not cpha_i):
            s_txsel_start = 0
            s_txsel = fifo_word_size - 1
        elif not n_ss_in_i:
            if s_txsel == 0:
                s_txsel = fifo_word_size - 1
            else:
                s_txsel -= 1

        ctx.set_output("s_txsel_o", s_txsel)

        ctx.set_state("s_txsel", s_txsel)
        ctx.set_state("s_txsel_start", s_txsel_start)

    return behavior


# =====================================================================
# SPIExtSync Template
# =====================================================================

def spi_ext_sync_template(
    n_flop_sync: int = 2,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """External clock synchronizer behavior.

    Generates m_clocken:
      - cks=0: always 1 (use internal clock)
      - cks=1: 1-cycle pulse per rising edge of ext_clk
    """
    def behavior(ctx: CycleContext):
        ext_clk_i = ctx.get_input("ext_clk_i", 0)
        cks_i = ctx.get_input("cks_i", 0)

        ext_clk_sync2 = ctx.get_state("ext_clk_sync2", 0)
        ext_clk_sync3 = ctx.get_state("ext_clk_sync3", 0)

        # Synchronizer chain
        ext_clk_sync2 = ext_clk_i
        ext_clk_sync3 = ext_clk_sync2

        # Rising edge detect
        rising_edge = (~ext_clk_sync3) & ext_clk_sync2

        # m_clocken = ~cks | rising_edge
        m_clocken = (~cks_i) | rising_edge

        ctx.set_output("m_clocken_o", m_clocken)

        ctx.set_state("ext_clk_sync2", ext_clk_sync2)
        ctx.set_state("ext_clk_sync3", ext_clk_sync3)

    return behavior


# Register SPI templates
TemplateRegistry.register("spi_registers", spi_registers_template)
TemplateRegistry.register("spi_control", spi_control_template)
TemplateRegistry.register("spi_transmit", spi_transmit_template)
TemplateRegistry.register("spi_receive", spi_receive_template)
TemplateRegistry.register("spi_slave_sync", spi_slave_sync_template)
TemplateRegistry.register("spi_slave_tx", spi_slave_tx_template)
TemplateRegistry.register("spi_ext_sync", spi_ext_sync_template)

__all__ = [
    "spi_registers_template",
    "spi_control_template",
    "spi_transmit_template",
    "spi_receive_template",
    "spi_slave_sync_template",
    "spi_slave_tx_template",
    "spi_ext_sync_template",
]
