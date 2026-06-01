"""ddr3 Layer 1: Template functions."""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import math
from rtlgen.arch_def import CycleContext

def memory_controller_template(
    mem_type: str = "DDR3",
    bank_count: int = 8,
    row_w: int = 15,
    col_w: int = 10,
    burst_len: int = 8,
    init_delay_cycles: int = 15000,
    refresh_cycles: int = 1000,
    addr_mapping: str = "rbc",
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Memory controller FSM behavior.

    States: INIT → DELAY → IDLE → ACTIVATE → READ/WRITE → PRECHARGE → REFRESH

    Ports (behavioral interface):
      Inputs:  cfg_enable_i, cfg_stb_i, cfg_data_i,
               inport_wr_i, inport_rd_i, inport_addr_i,
               inport_write_data_i, inport_req_id_i,
               dfi_rddata_i, dfi_rddata_valid_i
      Outputs: cfg_stall_o, inport_accept_o, inport_ack_o,
               inport_error_o, inport_resp_id_o, inport_read_data_o,
               dfi_command_o, dfi_address_o, dfi_bank_o,
               dfi_cke_o, dfi_wrdata_en_o, dfi_rddata_en_o
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst_i", 0)
        if rst == 1:
            ctx.set_state("state", _STATE_INIT)
            ctx.set_state("target_state", _STATE_IDLE)
            ctx.set_state("refresh_timer", init_delay_cycles)
            ctx.set_state("refresh_q", 0)
            ctx.set_state("row_open_q", 0)
            ctx.set_state("write_ack_q", 0)
            ctx.set_state("req_id", 0)
            ctx.set_state("read_data", 0)
            for i in range(bank_count):
                ctx.set_state(f"active_row_{i}", 0)
            # Clear outputs
            ctx.set_output("cfg_stall_o", 1)
            ctx.set_output("inport_accept_o", 0)
            ctx.set_output("inport_ack_o", 0)
            ctx.set_output("inport_error_o", 0)
            ctx.set_output("inport_resp_id_o", 0)
            ctx.set_output("inport_read_data_o", 0)
            ctx.set_output("dfi_command_o", _CMD_NOP)
            ctx.set_output("dfi_address_o", 0)
            ctx.set_output("dfi_bank_o", 0)
            ctx.set_output("dfi_cke_o", 1)
            ctx.set_output("dfi_wrdata_en_o", 0)
            ctx.set_output("dfi_rddata_en_o", 0)
            return

        state = ctx.get_state("state", _STATE_INIT)
        target_state = ctx.get_state("target_state", _STATE_IDLE)
        refresh_timer = ctx.get_state("refresh_timer", init_delay_cycles)
        refresh_q = ctx.get_state("refresh_q", 0)
        row_open_q = ctx.get_state("row_open_q", 0)
        write_ack_q = ctx.get_state("write_ack_q", 0)

        # ---- Refresh timer countdown ----
        if refresh_timer <= 1:
            ctx.set_state("refresh_timer", refresh_cycles)
            ctx.set_state("refresh_q", 1)
        else:
            ctx.set_state("refresh_timer", refresh_timer - 1)
            if refresh_q and state != _STATE_REFRESH:
                # Refresh already triggered, clear flag when handled
                pass

        # ---- Read inputs ----
        cfg_enable = ctx.get_input("cfg_enable_i", 1)
        inport_wr = ctx.get_input("inport_wr_i", 0)
        inport_rd = ctx.get_input("inport_rd_i", 0)
        inport_addr = ctx.get_input("inport_addr_i", 0)
        inport_write_data = ctx.get_input("inport_write_data_i", 0)
        inport_req_id = ctx.get_input("inport_req_id_i", 0)
        dfi_rddata = ctx.get_input("dfi_rddata_i", 0)
        dfi_rddata_valid = ctx.get_input("dfi_rddata_valid_i", 0)

        # ---- Address decode ----
        import math
        col_bits = int(math.log2(1 << col_w))
        bank_bits = int(math.log2(bank_count))
        if addr_mapping == "rbc":
            addr_col = inport_addr & ((1 << col_bits) - 1)
            addr_bank = (inport_addr >> col_bits) & ((1 << bank_bits) - 1)
            addr_row = inport_addr >> (col_bits + bank_bits)
        else:
            addr_bank = inport_addr & ((1 << bank_bits) - 1)
            addr_col = (inport_addr >> bank_bits) & ((1 << col_bits) - 1)
            addr_row = inport_addr >> (col_bits + bank_bits)

        ctx.set_state("addr_col", addr_col)
        ctx.set_state("addr_bank", addr_bank)
        ctx.set_state("addr_row", addr_row)

        # ---- Row hit/miss detection ----
        bank_row = ctx.get_state(f"active_row_{addr_bank}", 0)
        row_open_bit = (row_open_q >> addr_bank) & 1
        row_hit = row_open_bit & (bank_row == addr_row)
        row_miss = row_open_bit & (bank_row != addr_row)

        has_request = (inport_wr != 0) or inport_rd
        is_write = inport_wr != 0

        # ---- Default outputs ----
        next_cmd = _CMD_NOP
        next_addr = 0
        next_bank = 0
        next_cke = 1
        next_wrdata_en = 0
        next_rddata_en = 0
        next_accept = 0
        next_ack = 0
        next_resp_id = ctx.get_state("req_id", 0)
        next_read_data = ctx.get_state("read_data", 0)
        next_stall = 1
        next_state = state
        next_target = target_state
        next_refresh_q = refresh_q
        next_write_ack = write_ack_q
        next_row_open = row_open_q

        # ---- State machine ----
        if state == _STATE_INIT:
            # Power-up initialization countdown
            if refresh_timer < init_delay_cycles - 2500:
                next_cke = 0
            if refresh_timer == 2400:
                # LOAD_MODE MR2
                next_cmd = _CMD_LOAD_MODE
                next_bank = 2
            elif refresh_timer == 2300:
                # LOAD_MODE MR3
                next_cmd = _CMD_LOAD_MODE
                next_bank = 3
            elif refresh_timer == 2200:
                # LOAD_MODE MR1
                next_cmd = _CMD_LOAD_MODE
                next_bank = 1
            elif refresh_timer == 2100:
                # LOAD_MODE MR0
                next_cmd = _CMD_LOAD_MODE
                next_bank = 0
            elif refresh_timer == 2000:
                # ZQCL
                next_cmd = _CMD_ZQCL
            elif refresh_timer == 10:
                # PRECHARGE ALL
                next_cmd = _CMD_PRECHARGE
                next_addr = 1 << 10  # all_banks bit
            elif refresh_timer == 0:
                next_state = _STATE_IDLE
                next_refresh_q = 0

        elif state == _STATE_IDLE:
            if not cfg_enable:
                next_stall = 1
            elif refresh_q:
                # Must do refresh
                if row_open_q != 0:
                    next_state = _STATE_PRECHARGE
                    next_target = _STATE_REFRESH
                else:
                    next_state = _STATE_REFRESH
                    next_target = _STATE_REFRESH
                next_stall = 1
            elif has_request:
                next_stall = 0
                if row_hit:
                    next_state = _STATE_WRITE if is_write else _STATE_READ
                    next_accept = 1
                    ctx.set_state("req_id", inport_req_id)
                    if is_write:
                        ctx.set_state("write_data", inport_write_data)
                elif row_miss:
                    next_state = _STATE_PRECHARGE
                    next_target = _STATE_WRITE if is_write else _STATE_READ
                    next_accept = 0
                else:
                    next_state = _STATE_ACTIVATE
                    next_target = _STATE_WRITE if is_write else _STATE_READ
                    next_accept = 0
            else:
                next_stall = 1

        elif state == _STATE_ACTIVATE:
            next_cmd = _CMD_ACTIVE
            next_addr = addr_row
            next_bank = addr_bank
            # Activate complete, move to target
            next_state = target_state
            # Track opened row
            next_row_open = row_open_q | (1 << addr_bank)
            ctx.set_state(f"active_row_{addr_bank}", addr_row)

        elif state == _STATE_READ:
            next_cmd = _CMD_READ
            next_addr = addr_col
            next_bank = addr_bank
            next_rddata_en = 1
            next_accept = 1
            # Wait for read data
            if dfi_rddata_valid:
                next_read_data = dfi_rddata
                next_ack = 1
                next_state = _STATE_IDLE
            else:
                next_stall = 1

        elif state == _STATE_WRITE:
            next_cmd = _CMD_WRITE
            next_addr = addr_col
            next_bank = addr_bank
            next_wrdata_en = 1
            next_accept = 1
            next_write_ack = 1
            next_state = _STATE_IDLE
            next_ack = 1

        elif state == _STATE_PRECHARGE:
            next_cmd = _CMD_PRECHARGE
            if target_state == _STATE_REFRESH:
                next_addr = 1 << 10  # all_banks
                next_state = _STATE_REFRESH
                next_row_open = 0
            else:
                next_bank = addr_bank
                next_state = _STATE_ACTIVATE
                # Close this bank
                next_row_open = row_open_q & ~(1 << addr_bank)

        elif state == _STATE_REFRESH:
            next_cmd = _CMD_REFRESH
            next_state = _STATE_IDLE
            next_refresh_q = 0
            next_row_open = 0

        # ---- Commit state updates ----
        ctx.set_state("state", next_state)
        ctx.set_state("target_state", next_target)
        ctx.set_state("refresh_q", next_refresh_q)
        ctx.set_state("write_ack_q", next_write_ack)
        ctx.set_state("row_open_q", next_row_open)
        ctx.set_state("read_data", next_read_data)

        # ---- Commit outputs ----
        ctx.set_output("cfg_stall_o", next_stall)
        ctx.set_output("inport_accept_o", next_accept)
        ctx.set_output("inport_ack_o", next_ack)
        ctx.set_output("inport_error_o", 0)
        ctx.set_output("inport_resp_id_o", next_resp_id)
        ctx.set_output("inport_read_data_o", next_read_data)
        ctx.set_output("dfi_command_o", next_cmd)
        ctx.set_output("dfi_address_o", next_addr)
        ctx.set_output("dfi_bank_o", next_bank)
        ctx.set_output("dfi_cke_o", next_cke)
        ctx.set_output("dfi_wrdata_en_o", next_wrdata_en)
        ctx.set_output("dfi_rddata_en_o", next_rddata_en)

    return behavior

def dfi_sequencer_template(
    write_latency: int = 6,
    read_latency: int = 5,
    burst_len: int = 4,
    data_w: int = 32,
    wrdata_w: int = 128,
    trcd_cycles: int = 2,
    trp_cycles: int = 2,
    trfc_cycles: int = 26,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """DFI sequencer behavior: command timing delays + data serialization.

    Ports (behavioral interface):
      Inputs:  command_i, address_i, bank_i, cke_i,
               wrdata_i, wrdata_mask_i,
               dfi_rddata_i, dfi_rddata_valid_i
      Outputs: accept_o,
               dfi_cs_n, dfi_ras_n, dfi_cas_n, dfi_we_n,
               dfi_address, dfi_bank, dfi_cke,
               dfi_wrdata_en, dfi_rddata_en,
               dfi_wrdata, dfi_wrdata_mask
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst_i", 0)
        if rst == 1:
            ctx.set_state("delay_q", 0)
            ctx.set_state("last_cmd", _CMD_NOP)
            ctx.set_state("command_q", _CMD_NOP)
            ctx.set_state("addr_q", 0)
            ctx.set_state("bank_q", 0)
            ctx.set_state("cke_q", 0)
            ctx.set_state("wrdata_en", 0)
            ctx.set_state("rddata_en", 0)
            ctx.set_state("wr_idx", 0)
            ctx.set_state("rd_idx", 0)
            ctx.set_state("rd_data", 0)
            ctx.set_state("rd_valid", 0)
            ctx.set_output("accept_o", 1)
            ctx.set_output("dfi_cs_n", 1)
            ctx.set_output("dfi_ras_n", 1)
            ctx.set_output("dfi_cas_n", 1)
            ctx.set_output("dfi_we_n", 1)
            ctx.set_output("dfi_address", 0)
            ctx.set_output("dfi_bank", 0)
            ctx.set_output("dfi_cke", 0)
            ctx.set_output("dfi_wrdata_en", 0)
            ctx.set_output("dfi_rddata_en", 0)
            ctx.set_output("dfi_wrdata", 0)
            ctx.set_output("dfi_wrdata_mask", 0)
            return

        delay = ctx.get_state("delay_q", 0)
        cmd = ctx.get_input("command_i", _CMD_NOP)
        addr = ctx.get_input("address_i", 0)
        bank = ctx.get_input("bank_i", 0)
        cke = ctx.get_input("cke_i", 0)
        dfi_rddata = ctx.get_input("dfi_rddata_i", 0)
        dfi_rddata_valid = ctx.get_input("dfi_rddata_valid_i", 0)

        # ---- Accept condition ----
        rw_nonseq = write_latency + burst_len
        rw_seq = rw_nonseq + 1 - burst_len
        last_cmd = ctx.get_state("last_cmd", _CMD_NOP)

        early_accept = 0
        if (last_cmd == _CMD_READ and cmd == _CMD_READ and delay == rw_seq):
            early_accept = 1
        if (last_cmd == _CMD_WRITE and cmd == _CMD_WRITE and delay == rw_seq):
            early_accept = 1

        accept = (delay == 0) or early_accept or (cmd == _CMD_NOP)
        ctx.set_output("accept_o", 1 if accept else 0)

        # ---- Command processing ----
        if accept and cmd != _CMD_NOP:
            ctx.set_state("command_q", cmd)
            ctx.set_state("addr_q", addr)
            ctx.set_state("bank_q", bank)
            ctx.set_state("cke_q", cke)
            ctx.set_state("last_cmd", cmd)

            # Set delay based on command type
            if cmd == _CMD_ACTIVE:
                ctx.set_state("delay_q", trcd_cycles)
            elif cmd in (_CMD_READ, _CMD_WRITE):
                ctx.set_state("delay_q", rw_nonseq)
            elif cmd == _CMD_PRECHARGE:
                ctx.set_state("delay_q", trp_cycles)
            elif cmd == _CMD_REFRESH:
                ctx.set_state("delay_q", trfc_cycles)
            else:
                ctx.set_state("delay_q", 0)

            ctx.set_state("wrdata_en", 1 if cmd == _CMD_WRITE else 0)
            ctx.set_state("rddata_en", 1 if cmd == _CMD_READ else 0)
        elif not accept:
            ctx.set_state("delay_q", delay - 1)
            ctx.set_state("command_q", _CMD_NOP)
            ctx.set_state("wrdata_en", 0)
            ctx.set_state("rddata_en", 0)

        # ---- Read data assembly ----
        if dfi_rddata_valid:
            rd_idx = ctx.get_state("rd_idx", 0)
            rd_data = ctx.get_state("rd_data", 0)
            rd_data = (rd_data >> data_w) | (dfi_rddata << (wrdata_w - data_w))
            ctx.set_state("rd_data", rd_data)
            ctx.set_state("rd_idx", (rd_idx + 1) % burst_len)
            if rd_idx == burst_len - 1:
                ctx.set_state("rd_valid", 1)
            else:
                ctx.set_state("rd_valid", 0)

        # ---- DFI output mapping ----
        command_q = ctx.get_state("command_q", _CMD_NOP)
        ctx.set_output("dfi_cs_n", (command_q >> 3) & 1)
        ctx.set_output("dfi_ras_n", (command_q >> 2) & 1)
        ctx.set_output("dfi_cas_n", (command_q >> 1) & 1)
        ctx.set_output("dfi_we_n", command_q & 1)
        ctx.set_output("dfi_address", ctx.get_state("addr_q", 0))
        ctx.set_output("dfi_bank", ctx.get_state("bank_q", 0))
        ctx.set_output("dfi_cke", ctx.get_state("cke_q", 0))
        ctx.set_output("dfi_wrdata_en", ctx.get_state("wrdata_en", 0))
        ctx.set_output("dfi_rddata_en", ctx.get_state("rddata_en", 0))

    return behavior


# Register memory templates into TemplateRegistry
from rtlgen.behaviors import TemplateRegistry

TemplateRegistry.register("memory_controller", memory_controller_template)
TemplateRegistry.register("dfi_sequencer", dfi_sequencer_template)

