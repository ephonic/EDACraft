"""
skills.mem.cam.behaviors — CAM Behavior Templates

Domain-specific behavior templates for Content Addressable Memory.
Registered into TemplateRegistry at import time.

Templates:
  - priority_encoder_template: Recursive tree priority encoder (combinational)
  - ram_dp_template: Dual-port RAM with read-first behavior
  - cam_srl_template: SRL-based CAM (shift-register LUT, 4-state FSM)
  - cam_bram_template: BRAM-based CAM (dual-port RAM slices, 6-state FSM)
  - cam_top_template: Top-level wrapper with SRL/BRAM style selection
"""
from __future__ import annotations

import math
from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# PriorityEncoder Template
# =====================================================================

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
