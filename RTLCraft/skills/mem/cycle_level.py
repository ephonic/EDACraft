"""
Cycle-level models for skills.mem
"""
from __future__ import annotations
from typing import Any, Callable
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def priority_encoder_template(
    width: int = 32,
    lsb_priority: str = "HIGH",
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Priority encoder: find first/last set bit in input vector.

    LSB_PRIORITY="HIGH": lowest set bit wins (bit 0 has highest priority).
    LSB_PRIORITY="LOW": highest set bit wins (MSB has highest priority).
    """
    enc_width = max(width.bit_length(), 1)

    def behavior(ctx: CycleContext):
        input_val = ctx.get_input("input_unencoded", 0)

        if lsb_priority == "LOW":
            # MSB priority: scan from MSB down
            found = 0
            result = 0
            for i in range(width - 1, -1, -1):
                if (input_val >> i) & 1 and not found:
                    result = i
                    found = 1
        else:
            # LSB priority: scan from LSB up
            found = 0
            result = 0
            for i in range(width):
                if (input_val >> i) & 1 and not found:
                    result = i
                    found = 1

        ctx.set_output("output_valid", found)
        ctx.set_output("output_encoded", result)
        ctx.set_output("output_unencoded", 1 << result if found else 0)

    return behavior


# =====================================================================
# RamDP Template
# =====================================================================


def ram_dp_template(
    data_width: int = 32,
    addr_width: int = 10,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Dual-port RAM with read-first behavior.

    Port A: read data registered, write with read-first (write + read new data)
    Port B: read data registered, write with read-first (write + read new data)
    """
    depth = 2 ** addr_width

    def behavior(ctx: CycleContext):
        a_we = ctx.get_input("a_we", 0)
        a_addr = ctx.get_input("a_addr", 0)
        a_din = ctx.get_input("a_din", 0)
        b_we = ctx.get_input("b_we", 0)
        b_addr = ctx.get_input("b_addr", 0)
        b_din = ctx.get_input("b_din", 0)

        mem = ctx.get_state("mem", [0] * depth)
        mask = (1 << data_width) - 1

        # Read current values
        a_data = mem[a_addr % depth] if a_addr < depth else 0
        b_data = mem[b_addr % depth] if b_addr < depth else 0

        # Write (read-first: write new data to output too)
        if a_we:
            mem[a_addr % depth] = a_din & mask
            a_data = a_din & mask
        if b_we:
            mem[b_addr % depth] = b_din & mask
            b_data = b_din & mask

        ctx.set_output("a_dout", a_data)
        ctx.set_output("b_dout", b_data)
        ctx.set_state("mem", mem)

    return behavior


# =====================================================================
# CamSRL Template
# =====================================================================


def cam_srl_template(
    data_width: int = 64,
    addr_width: int = 5,
    slice_width: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """SRL-based CAM behavioral model.

    FSM states: INIT (0) → IDLE (1) → WRITE (2) → DELETE (3)

    Write operation: shift data into SRL at write_addr over SLICE_WIDTH cycles.
    Delete operation: shift zeros into SRL at write_addr over SLICE_WIDTH cycles.
    Match: AND across all slices of SRL lookup (compare_data slice → SRL index).
    """
    slice_count = (data_width + slice_width - 1) // slice_width
    ram_depth = 2 ** addr_width
    srl_depth = 2 ** slice_width
    STATE_INIT = 0
    STATE_IDLE = 1
    STATE_WRITE = 2
    STATE_DELETE = 3

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        clk_cycle = ctx.get_input("clk", 0)  # simplified: treat as cycle counter

        write_enable = ctx.get_input("write_enable", 0)
        write_addr = ctx.get_input("write_addr", 0)
        write_data = ctx.get_input("write_data", 0)
        write_delete = ctx.get_input("write_delete", 0)
        compare_data = ctx.get_input("compare_data", 0)

        # Pad data to slice boundary
        pad_width = slice_count * slice_width - data_width
        compare_padded = compare_data  # Python handles arbitrary width
        write_padded = write_data

        if rst:
            ctx.set_state("cam_state", STATE_INIT)
            ctx.set_state("count", srl_depth - 1)
            ctx.set_state("write_busy", 1)
            ctx.set_state("match_many", 0)
            ctx.set_state("match_addr", 0)
            ctx.set_state("match_single", 0)
            ctx.set_state("match", 0)
            # Initialize SRL memory to zeros
            ctx.set_state("srl_mem", {})
            return

        state = ctx.get_state("cam_state", STATE_INIT)
        count = ctx.get_state("count", srl_depth - 1)
        srl_mem = ctx.get_state("srl_mem", {})  # (row, slice) -> list of bits
        write_addr_reg = ctx.get_state("write_addr_reg", 0)
        write_data_reg = ctx.get_state("write_data_reg", 0)
        write_delete_reg = ctx.get_state("write_delete_reg", 0)

        next_state = STATE_IDLE
        next_count = count
        shift_en = [0] * ram_depth
        shift_data = [0] * slice_count
        next_write_addr = write_addr_reg
        next_write_data = write_data_reg
        next_write_delete = write_delete_reg

        if state == STATE_INIT:
            # Zero-out all SRL entries
            shift_en = [1] * ram_depth
            shift_data = [0] * slice_count
            if count == 0:
                next_state = STATE_IDLE
            else:
                next_count = count - 1
                next_state = STATE_INIT

        elif state == STATE_IDLE:
            if write_enable:
                next_write_addr = write_addr
                next_write_data = write_padded
                next_write_delete = write_delete
                next_count = srl_depth - 1
                if write_delete:
                    next_state = STATE_DELETE
                else:
                    next_state = STATE_WRITE
            else:
                next_state = STATE_IDLE

        elif state == STATE_WRITE:
            shift_en = [0] * ram_depth
            shift_en[write_addr_reg % ram_depth] = 1
            for s in range(slice_count):
                slice_val = (write_data_reg >> (s * slice_width)) & ((1 << slice_width) - 1)
                shift_data[s] = 1 if count == slice_val else 0
            if count == 0:
                next_state = STATE_IDLE
            else:
                next_count = count - 1
                next_state = STATE_WRITE

        elif state == STATE_DELETE:
            shift_en = [0] * ram_depth
            shift_en[write_addr_reg % ram_depth] = 1
            shift_data = [0] * slice_count
            if count == 0:
                next_state = STATE_IDLE
            else:
                next_count = count - 1
                next_state = STATE_DELETE

        # Perform SRL shift
        new_srl = dict(srl_mem)
        for row in range(ram_depth):
            if shift_en[row]:
                for s in range(slice_count):
                    key = (row, s)
                    old = new_srl.get(key, [0] * srl_depth)
                    # Shift left, insert new bit at end
                    new_srl[key] = old[1:] + [shift_data[s]]

        # Match logic: for each slice, lookup compare_data slice in SRL
        match_many = (1 << ram_depth) - 1  # start all 1s
        match_many &= ~((1 << ram_depth) - 1)  # start all 0s, then AND
        match_mask = ~0  # all 1s
        for row in range(ram_depth):
            row_match = 1
            for s in range(slice_count):
                slice_val = (compare_padded >> (s * slice_width)) & ((1 << slice_width) - 1)
                key = (row, s)
                srl_bits = new_srl.get(key, [0] * srl_depth)
                if slice_val < len(srl_bits):
                    if srl_bits[slice_val] == 0:
                        row_match = 0
                else:
                    row_match = 0
            if row_match:
                match_many |= (1 << row)

        # Priority encoder on match_many
        enc_width = max(addr_width, 1)
        found = 0
        match_addr = 0
        for i in range(ram_depth):
            if (match_many >> i) & 1 and not found:
                match_addr = i
                found = 1

        # Single match: 1 << match_addr
        match_single = 1 << match_addr if found else 0

        # Write busy
        write_busy = 1 if next_state != STATE_IDLE else 0

        ctx.set_state("cam_state", next_state)
        ctx.set_state("count", next_count)
        ctx.set_state("srl_mem", new_srl)
        ctx.set_state("write_addr_reg", next_write_addr)
        ctx.set_state("write_data_reg", next_write_data)
        ctx.set_state("write_delete_reg", next_write_delete)

        ctx.set_output("write_busy", write_busy)
        ctx.set_output("match_many", match_many & ((1 << ram_depth) - 1))
        ctx.set_output("match_single", match_single & ((1 << ram_depth) - 1))
        ctx.set_output("match_addr", match_addr)
        ctx.set_output("match", found)

    return behavior


# =====================================================================
# CamBRAM Template
# =====================================================================


def cam_bram_template(
    data_width: int = 64,
    addr_width: int = 5,
    slice_width: int = 9,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """BRAM-based CAM behavioral model.

    FSM states: INIT (0) → IDLE (1) → DELETE_1 (2) → DELETE_2 (3)
                → WRITE_1 (4) → WRITE_2 (5)

    Each slice is a RamDP: data_width = RAM_DEPTH, addr_width = slice_width.
    Match = AND of all slice read outputs.
    Write = read-modify-write: clear old bits, set new bits at write_addr.
    Erase RAM tracks stored data for correct delete.
    """
    slice_count = (data_width + slice_width - 1) // slice_width
    ram_depth = 2 ** addr_width
    STATE_INIT = 0
    STATE_IDLE = 1
    STATE_DELETE_1 = 2
    STATE_DELETE_2 = 3
    STATE_WRITE_1 = 4
    STATE_WRITE_2 = 5

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)

        write_enable = ctx.get_input("write_enable", 0)
        write_addr = ctx.get_input("write_addr", 0)
        write_data = ctx.get_input("write_data", 0)
        write_delete_in = ctx.get_input("write_delete", 0)
        compare_data = ctx.get_input("compare_data", 0)

        if rst:
            ctx.set_state("cam_state", STATE_INIT)
            ctx.set_state("count", (1 << slice_width) - 1)
            ctx.set_state("write_busy", 1)
            ctx.set_state("match_many", 0)
            ctx.set_state("match_addr", 0)
            ctx.set_state("match_single", 0)
            ctx.set_state("match", 0)
            # Initialize BRAM slices
            ctx.set_state("bram_slices", [0] * slice_count)
            ctx.set_state("erase_ram", {})
            return

        state = ctx.get_state("cam_state", STATE_INIT)
        count = ctx.get_state("count", (1 << slice_width) - 1)
        write_addr_reg = ctx.get_state("write_addr_reg", 0)
        write_data_reg = ctx.get_state("write_data_reg", 0)
        write_delete_reg = ctx.get_state("write_delete_reg", 0)
        erase_ram = ctx.get_state("erase_ram", {})
        bram_slices = ctx.get_state("bram_slices", [0] * slice_count)

        next_state = STATE_IDLE
        next_count = count
        next_write_addr = write_addr_reg
        next_write_data = write_data_reg
        next_write_delete = write_delete_reg
        set_bit = 0
        clear_bit = 0
        wr_en = 0
        erase_ram_wr_en = 0

        if state == STATE_INIT:
            # Zero-out all BRAM entries
            clear_bit = (1 << ram_depth) - 1
            wr_en = 1
            ram_addr_pattern = count & ((1 << slice_width) - 1)
            if count == 0:
                next_state = STATE_IDLE
            else:
                next_count = count - 1
                next_state = STATE_INIT

        elif state == STATE_IDLE:
            next_write_addr = write_addr
            next_write_data = write_data
            next_write_delete = write_delete_in
            if write_enable:
                next_state = STATE_DELETE_1
            else:
                next_state = STATE_IDLE

        elif state == STATE_DELETE_1:
            # Wait cycle for erase_ram read
            next_state = STATE_DELETE_2

        elif state == STATE_DELETE_2:
            clear_bit = 1 << (write_addr_reg % ram_depth)
            wr_en = 1
            if write_delete_reg:
                next_state = STATE_IDLE
            else:
                erase_ram_wr_en = 1
                next_state = STATE_WRITE_1

        elif state == STATE_WRITE_1:
            # Wait cycle
            next_state = STATE_WRITE_2

        elif state == STATE_WRITE_2:
            set_bit = 1 << (write_addr_reg % ram_depth)
            wr_en = 1
            next_state = STATE_IDLE

        # Write to erase_ram
        if erase_ram_wr_en:
            erase_ram[write_addr_reg % ram_depth] = write_data_reg

        # Write to BRAM slices
        if wr_en:
            for s in range(slice_count):
                old_val = bram_slices[s]
                new_val = (old_val & ~clear_bit) | set_bit
                bram_slices[s] = new_val

        # Read erase_data for ram_addr
        erase_data = erase_ram.get(write_addr_reg % ram_depth, 0)

        # Match logic: AND of all slice reads
        match_mask = (1 << ram_depth) - 1
        for s in range(slice_count):
            w = slice_width if s < slice_count - 1 else (data_width - slice_width * s)
            slice_val = (compare_data >> (s * slice_width)) & ((1 << w) - 1)
            # RamDP read: bram_slices[s] at addr = slice_val
            # In behavioral model: check if bit at slice_val position is set
            # Actually: the BRAM stores bit-vectors indexed by data slice value
            # The output at address X tells us which rows have value X at this slice
            # Match = AND of all slice outputs
            slice_match = (bram_slices[s] >> slice_val) & 1 if slice_val < ram_depth else 0
            match_mask &= (slice_match << slice_val) if slice_match else 0

        # Simplified: just use bram_slices directly
        match_many = (1 << ram_depth) - 1
        for s in range(slice_count):
            w = slice_width if s < slice_count - 1 else (data_width - slice_width * s)
            slice_val = (compare_data >> (s * slice_width)) & ((1 << w) - 1)
            if slice_val < ram_depth:
                bit = (bram_slices[s] >> slice_val) & 1
                if not bit:
                    match_many &= ~(1 << slice_val)
            else:
                match_many = 0

        # Priority encoder
        found = 0
        match_addr = 0
        for i in range(ram_depth):
            if (match_many >> i) & 1 and not found:
                match_addr = i
                found = 1

        match_single = 1 << match_addr if found else 0
        write_busy = 1 if next_state != STATE_IDLE else 0

        ctx.set_state("cam_state", next_state)
        ctx.set_state("count", next_count)
        ctx.set_state("write_addr_reg", next_write_addr)
        ctx.set_state("write_data_reg", next_write_data)
        ctx.set_state("write_delete_reg", next_write_delete)
        ctx.set_state("erase_ram", erase_ram)
        ctx.set_state("bram_slices", bram_slices)

        ctx.set_output("write_busy", write_busy)
        ctx.set_output("match_many", match_many)
        ctx.set_output("match_single", match_single)
        ctx.set_output("match_addr", match_addr)
        ctx.set_output("match", found)

    return behavior


# =====================================================================
# CAM Top Template
# =====================================================================


def cam_top_template(
    cam_style: str = "SRL",
    data_width: int = 64,
    addr_width: int = 5,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Top-level CAM wrapper with style selection.

    CAM_STYLE="SRL" → delegates to cam_srl_template
    CAM_STYLE="BRAM" → delegates to cam_bram_template
    """
    if cam_style == "SRL":
        sub_behavior = cam_srl_template(data_width=data_width, addr_width=addr_width, **kwargs)
    else:
        sub_behavior = cam_bram_template(data_width=data_width, addr_width=addr_width, **kwargs)

    def behavior(ctx: CycleContext):
        return sub_behavior(ctx)

    return behavior


# Register CAM templates
TemplateRegistry.register("priority_encoder", priority_encoder_template)
TemplateRegistry.register("ram_dp", ram_dp_template)
TemplateRegistry.register("cam_srl", cam_srl_template)
TemplateRegistry.register("cam_bram", cam_bram_template)
TemplateRegistry.register("cam_top", cam_top_template)

__all__ = [
    "priority_encoder_template",
    "ram_dp_template",
    "cam_srl_template",
    "cam_bram_template",
    "cam_top_template",
]

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


# =====================================================================
# DFI Sequencer — DDR PHY Interface Sequencer Behavior Template
# =====================================================================


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

TemplateRegistry.register("cam_bram", cam_bram_template)
TemplateRegistry.register("cam_srl", cam_srl_template)
TemplateRegistry.register("cam_top", cam_top_template)
TemplateRegistry.register("dfi_sequencer", dfi_sequencer_template)
TemplateRegistry.register("memory_controller", memory_controller_template)
TemplateRegistry.register("priority_encoder", priority_encoder_template)
TemplateRegistry.register("ram_dp", ram_dp_template)
__all__ = [
