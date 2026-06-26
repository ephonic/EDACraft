"""
skills.mem.ddr3.models — DDR3 Behavioral Models

Cycle-accurate behavioral models for DDR3 controller components.
Used for golden-reference simulation and verification comparison.
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_def import CycleContext, ModelProvider


# DDR3 commands
_CMD_NOP = 0b0111
_CMD_ACTIVE = 0b0011
_CMD_READ = 0b0101
_CMD_WRITE = 0b0100
_CMD_PRECHARGE = 0b0010
_CMD_REFRESH = 0b0001
_CMD_LOAD_MODE = 0b0000
_CMD_ZQCL = 0b0110

# State encoding
_STATE_INIT = 0
_STATE_DELAY = 1
_STATE_IDLE = 2
_STATE_ACTIVATE = 3
_STATE_READ = 4
_STATE_WRITE = 5
_STATE_PRECHARGE = 6
_STATE_REFRESH = 7


class DDR3CoreModel(ModelProvider):
    """Golden-reference behavioral model for DDR3 controller core FSM.

    States: INIT → DELAY → IDLE → ACTIVATE → READ/WRITE → PRECHARGE → REFRESH

    Tracks:
      - Per-bank open row (row buffer)
      - Refresh timer countdown
      - Request accept/ack handshake
      - DFI command generation
    """

    name = "ddr3_core_model"
    description = "DDR3 controller core FSM behavioral model"

    def create_behavior(
        self,
        bank_count: int = 8,
        row_w: int = 15,
        col_w: int = 10,
        burst_len: int = 8,
        init_delay_cycles: int = 15000,
        refresh_cycles: int = 1000,
        addr_mapping: str = "rbc",
        **kwargs,
    ):
        """Create DDR3 core behavioral model."""

        def behavior(ctx: CycleContext):
            rst = ctx.get_input("rst_i", 0)
            if rst == 1:
                ctx.set_state("state", _STATE_INIT)
                ctx.set_state("target_state", _STATE_IDLE)
                ctx.set_state("refresh_timer", init_delay_cycles)
                ctx.set_state("refresh_q", 0)
                ctx.set_state("row_open_q", 0)
                ctx.set_state("write_ack_q", 0)
                for i in range(bank_count):
                    ctx.set_state(f"active_row_{i}", 0)
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

            # Refresh timer countdown
            if refresh_timer <= 1:
                ctx.set_state("refresh_timer", refresh_cycles)
                ctx.set_state("refresh_q", 1)
            else:
                ctx.set_state("refresh_timer", refresh_timer - 1)

            # Read inputs
            cfg_enable = ctx.get_input("cfg_enable_i", 1)
            inport_wr = ctx.get_input("inport_wr_i", 0)
            inport_rd = ctx.get_input("inport_rd_i", 0)
            inport_addr = ctx.get_input("inport_addr_i", 0)
            inport_write_data = ctx.get_input("inport_write_data_i", 0)
            inport_req_id = ctx.get_input("inport_req_id_i", 0)
            dfi_rddata = ctx.get_input("dfi_rddata_i", 0)
            dfi_rddata_valid = ctx.get_input("dfi_rddata_valid_i", 0)

            # Address decode (RBC mode)
            import math
            col_bits = col_w
            bank_bits = 3  # 8 banks
            if addr_mapping == "rbc":
                addr_col = inport_addr & ((1 << col_bits) - 1)
                addr_bank = (inport_addr >> col_bits) & ((1 << bank_bits) - 1)
                addr_row = inport_addr >> (col_bits + bank_bits)
            else:
                addr_bank = inport_addr & ((1 << bank_bits) - 1)
                addr_col = (inport_addr >> bank_bits) & ((1 << col_bits) - 1)
                addr_row = inport_addr >> (col_bits + bank_bits)

            # Row hit/miss
            bank_row = ctx.get_state(f"active_row_{addr_bank}", 0)
            row_open_bit = (row_open_q >> addr_bank) & 1
            row_hit = row_open_bit & (bank_row == addr_row)
            row_miss = row_open_bit & (bank_row != addr_row)

            has_request = (inport_wr != 0) or inport_rd
            is_write = inport_wr != 0

            # Default outputs
            next_cmd = _CMD_NOP
            next_addr = 0
            next_bank = 0
            next_cke = 1
            next_wrdata_en = 0
            next_rddata_en = 0
            next_accept = 0
            next_ack = 0
            next_stall = 1
            next_state = state
            next_target = target_state
            next_refresh_q = refresh_q
            next_write_ack = write_ack_q
            next_row_open = row_open_q
            next_read_data = ctx.get_state("read_data", 0)

            # State machine
            if state == _STATE_INIT:
                if refresh_timer < init_delay_cycles - 2500:
                    next_cke = 0
                if refresh_timer == 2400:
                    next_cmd = _CMD_LOAD_MODE; next_bank = 2
                elif refresh_timer == 2300:
                    next_cmd = _CMD_LOAD_MODE; next_bank = 3
                elif refresh_timer == 2200:
                    next_cmd = _CMD_LOAD_MODE; next_bank = 1
                elif refresh_timer == 2100:
                    next_cmd = _CMD_LOAD_MODE; next_bank = 0
                elif refresh_timer == 2000:
                    next_cmd = _CMD_ZQCL
                elif refresh_timer == 10:
                    next_cmd = _CMD_PRECHARGE; next_addr = 1 << 10
                elif refresh_timer == 0:
                    next_state = _STATE_IDLE
                    next_refresh_q = 0

            elif state == _STATE_IDLE:
                if not cfg_enable:
                    next_stall = 1
                elif refresh_q:
                    if row_open_q != 0:
                        next_state = _STATE_PRECHARGE; next_target = _STATE_REFRESH
                    else:
                        next_state = _STATE_REFRESH
                    next_stall = 1
                elif has_request:
                    next_stall = 0
                    if row_hit:
                        next_state = _STATE_WRITE if is_write else _STATE_READ
                        next_accept = 1
                    elif row_miss:
                        next_state = _STATE_PRECHARGE
                        next_target = _STATE_WRITE if is_write else _STATE_READ
                    else:
                        next_state = _STATE_ACTIVATE
                        next_target = _STATE_WRITE if is_write else _STATE_READ
                else:
                    next_stall = 1

            elif state == _STATE_ACTIVATE:
                next_cmd = _CMD_ACTIVE; next_addr = addr_row; next_bank = addr_bank
                next_state = target_state
                next_row_open = row_open_q | (1 << addr_bank)
                ctx.set_state(f"active_row_{addr_bank}", addr_row)

            elif state == _STATE_READ:
                next_cmd = _CMD_READ; next_addr = addr_col; next_bank = addr_bank
                next_rddata_en = 1; next_accept = 1
                if dfi_rddata_valid:
                    next_read_data = dfi_rddata; next_ack = 1; next_state = _STATE_IDLE
                else:
                    next_stall = 1

            elif state == _STATE_WRITE:
                next_cmd = _CMD_WRITE; next_addr = addr_col; next_bank = addr_bank
                next_wrdata_en = 1; next_accept = 1; next_write_ack = 1
                next_state = _STATE_IDLE; next_ack = 1

            elif state == _STATE_PRECHARGE:
                next_cmd = _CMD_PRECHARGE
                if target_state == _STATE_REFRESH:
                    next_addr = 1 << 10; next_state = _STATE_REFRESH; next_row_open = 0
                else:
                    next_bank = addr_bank; next_state = _STATE_ACTIVATE
                    next_row_open = row_open_q & ~(1 << addr_bank)

            elif state == _STATE_REFRESH:
                next_cmd = _CMD_REFRESH; next_state = _STATE_IDLE
                next_refresh_q = 0; next_row_open = 0

            # Commit state and outputs
            ctx.set_state("state", next_state)
            ctx.set_state("target_state", next_target)
            ctx.set_state("refresh_q", next_refresh_q)
            ctx.set_state("write_ack_q", next_write_ack)
            ctx.set_state("row_open_q", next_row_open)
            ctx.set_state("read_data", next_read_data)

            ctx.set_output("cfg_stall_o", next_stall)
            ctx.set_output("inport_accept_o", next_accept)
            ctx.set_output("inport_ack_o", next_ack)
            ctx.set_output("inport_error_o", 0)
            ctx.set_output("dfi_command_o", next_cmd)
            ctx.set_output("dfi_address_o", next_addr)
            ctx.set_output("dfi_bank_o", next_bank)
            ctx.set_output("dfi_cke_o", next_cke)
            ctx.set_output("dfi_wrdata_en_o", next_wrdata_en)
            ctx.set_output("dfi_rddata_en_o", next_rddata_en)
            ctx.set_output("inport_read_data_o", next_read_data)

        return behavior


class DDR3DFISeqModel(ModelProvider):
    """Golden-reference behavioral model for DFI sequencer.

    Handles command timing delays (tRCD, tRP, tRFC) and
    write/read data serialization/deserialization.
    """

    name = "ddr3_dfi_seq_model"
    description = "DDR3 DFI sequencer behavioral model"

    def create_behavior(
        self,
        write_latency: int = 6,
        read_latency: int = 5,
        burst_len: int = 8,
        data_w: int = 32,
        trcd_cycles: int = 2,
        trp_cycles: int = 2,
        trfc_cycles: int = 26,
        **kwargs,
    ):
        """Create DFI sequencer behavioral model."""

        def behavior(ctx: CycleContext):
            rst = ctx.get_input("rst_i", 0)
            if rst == 1:
                ctx.set_state("delay_q", 0)
                ctx.set_state("last_cmd", _CMD_NOP)
                ctx.set_state("command_q", _CMD_NOP)
                ctx.set_state("addr_q", 0)
                ctx.set_state("bank_q", 0)
                ctx.set_state("wr_en_q", 0)
                ctx.set_state("rd_en_q", 0)
                ctx.set_state("rd_data_q", 0)
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
                return

            delay = ctx.get_state("delay_q", 0)
            cmd = ctx.get_input("command_i", _CMD_NOP)
            addr = ctx.get_input("address_i", 0)
            bank = ctx.get_input("bank_i", 0)
            cke = ctx.get_input("cke_i", 0)

            last_cmd = ctx.get_state("last_cmd", _CMD_NOP)
            rw_nonseq = write_latency + burst_len
            rw_seq = rw_nonseq + 1 - burst_len

            early_accept = 0
            if last_cmd == _CMD_READ and cmd == _CMD_READ and delay == rw_seq:
                early_accept = 1
            if last_cmd == _CMD_WRITE and cmd == _CMD_WRITE and delay == rw_seq:
                early_accept = 1

            accept = (delay == 0) or early_accept or (cmd == _CMD_NOP)
            ctx.set_output("accept_o", 1 if accept else 0)

            if accept and cmd != _CMD_NOP:
                ctx.set_state("command_q", cmd)
                ctx.set_state("addr_q", addr)
                ctx.set_state("bank_q", bank)
                ctx.set_state("last_cmd", cmd)
                if cmd == _CMD_ACTIVE:
                    ctx.set_state("delay_q", trcd_cycles)
                elif cmd in (_CMD_READ, _CMD_WRITE):
                    ctx.set_state("delay_q", rw_nonseq)
                    ones = (1 << burst_len) - 1
                    ctx.set_state("wr_en_q", (ones << write_latency) | (ctx.get_state("wr_en_q", 0) >> 1))
                    ctx.set_state("rd_en_q", (ones << read_latency) | (ctx.get_state("rd_en_q", 0) >> 1))
                elif cmd == _CMD_PRECHARGE:
                    ctx.set_state("delay_q", trp_cycles)
                elif cmd == _CMD_REFRESH:
                    ctx.set_state("delay_q", trfc_cycles)
                else:
                    ctx.set_state("delay_q", 0)
            elif not accept:
                ctx.set_state("delay_q", delay - 1)
                ctx.set_state("command_q", _CMD_NOP)

            # DFI output mapping
            command_q = ctx.get_state("command_q", _CMD_NOP)
            ctx.set_output("dfi_cs_n", (command_q >> 3) & 1)
            ctx.set_output("dfi_ras_n", (command_q >> 2) & 1)
            ctx.set_output("dfi_cas_n", (command_q >> 1) & 1)
            ctx.set_output("dfi_we_n", command_q & 1)
            ctx.set_output("dfi_address", ctx.get_state("addr_q", 0))
            ctx.set_output("dfi_bank", ctx.get_state("bank_q", 0))
            ctx.set_output("dfi_wrdata_en", ctx.get_state("wr_en_q", 0) & 1)
            ctx.set_output("dfi_rddata_en", ctx.get_state("rd_en_q", 0) & 1)

        return behavior


class DDR3Model(ModelProvider):
    """Combined DDR3 controller behavioral model (core + DFI sequencer)."""

    name = "ddr3_model"
    description = "DDR3 controller full behavioral model"

    def create_behavior(self, **kwargs):
        core_model = DDR3CoreModel().create_behavior(**kwargs)

        def behavior(ctx: CycleContext):
            return core_model(ctx)

        return behavior

    def create_testbench(self, **kwargs) -> List[Dict]:
        tests = []
        tests.append({
            "name": "reset",
            "setup": {"rst_i": 1, "cfg_enable_i": 0},
            "cycles": 1,
            "check": {"cfg_stall_o": 1, "dfi_command_o": _CMD_NOP},
        })
        tests.append({
            "name": "idle_after_reset",
            "setup": {"rst_i": 0, "cfg_enable_i": 0},
            "cycles": 1,
            "check": {"cfg_stall_o": 1},
        })
        tests.append({
            "name": "accept_read",
            "setup": {"rst_i": 0, "cfg_enable_i": 1, "inport_rd_i": 1,
                      "inport_addr_i": 0x1000},
            "cycles": 1,
            "check": {"inport_accept_o": 1},
        })
        return tests


__all__ = ["DDR3CoreModel", "DDR3DFISeqModel", "DDR3Model"]
