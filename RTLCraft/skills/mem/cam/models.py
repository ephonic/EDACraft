"""
skills.mem.cam.models — CAM Behavioral Models

Cycle-accurate behavioral models for CAM components.
Used for golden-reference simulation and verification comparison.
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_def import CycleContext, ModelProvider


class CAMModel(ModelProvider):
    """Golden-reference behavioral model for Content Addressable Memory.

    Supports both SRL and BRAM backends:
      - SRL: shift-register LUT array, SLICE_WIDTH=4
      - BRAM: dual-port RAM slices with erase tracking, SLICE_WIDTH=9

    Operations:
      - Write: store data at specified address
      - Delete: remove entry at specified address
      - Match: find all addresses matching compare_data
    """

    name = "cam_model"
    description = "CAM golden-reference model (SRL and BRAM variants)"

    def create_behavior(
        self,
        cam_style: str = "SRL",
        data_width: int = 64,
        addr_width: int = 5,
        slice_width: int = 4,
        **kwargs,
    ):
        """Create CAM behavioral model.

        Args:
            cam_style: "SRL" or "BRAM"
            data_width: Search data bus width
            addr_width: Memory size in log2(words)
            slice_width: Data bus slice width
        """
        ram_depth = 2 ** addr_width
        slice_count = (data_width + slice_width - 1) // slice_width

        def behavior(ctx: CycleContext):
            rst = ctx.get_input("rst", 0)
            write_enable = ctx.get_input("write_enable", 0)
            write_addr = ctx.get_input("write_addr", 0)
            write_data = ctx.get_input("write_data", 0)
            write_delete = ctx.get_input("write_delete", 0)
            compare_data = ctx.get_input("compare_data", 0)

            if cam_style == "SRL":
                self._srl_cycle(ctx, ram_depth, slice_count, slice_width,
                                rst, write_enable, write_addr, write_data,
                                write_delete, compare_data)
            else:
                self._bram_cycle(ctx, ram_depth, slice_count, slice_width,
                                 rst, write_enable, write_addr, write_data,
                                 write_delete, compare_data)

        return behavior

    def _srl_cycle(self, ctx, ram_depth, slice_count, slice_width,
                   rst, write_enable, write_addr, write_data,
                   write_delete, compare_data):
        """SRL-based CAM cycle simulation."""
        STATE_INIT = 0
        STATE_IDLE = 1
        STATE_WRITE = 2
        STATE_DELETE = 3
        srl_depth = 2 ** slice_width

        if rst:
            ctx.set_state("cam_state", STATE_INIT)
            ctx.set_state("count", srl_depth - 1)
            ctx.set_state("write_busy", 1)
            ctx.set_state("match", 0)
            ctx.set_state("match_addr", 0)
            ctx.set_state("match_many", 0)
            ctx.set_state("match_single", 0)
            ctx.set_state("srl_mem", {})
            return

        state = ctx.get_state("cam_state", STATE_INIT)
        count = ctx.get_state("count", srl_depth - 1)
        srl_mem = ctx.get_state("srl_mem", {})
        write_addr_reg = ctx.get_state("write_addr_reg", 0)
        write_data_reg = ctx.get_state("write_data_reg", 0)
        write_delete_reg = ctx.get_state("write_delete_reg", 0)

        next_state = STATE_IDLE
        next_count = count
        next_write_addr = write_addr_reg
        next_write_data = write_data_reg
        next_write_delete = write_delete_reg
        shift_en = [0] * ram_depth
        shift_data = [0] * slice_count

        if state == STATE_INIT:
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
                next_write_data = write_data
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

        # SRL shift
        new_srl = {}
        for key, bits in srl_mem.items():
            row, s = key
            if shift_en[row]:
                new_srl[key] = bits[1:] + [shift_data[s]]
            else:
                new_srl[key] = list(bits)

        # Initialize missing entries
        for row in range(ram_depth):
            for s in range(slice_count):
                key = (row, s)
                if key not in new_srl:
                    if shift_en[row]:
                        new_srl[key] = [0] * (srl_depth - 1) + [shift_data[s]]
                    else:
                        new_srl[key] = [0] * srl_depth

        # Match
        match_many = 0
        for row in range(ram_depth):
            row_match = 1
            for s in range(slice_count):
                slice_val = (compare_data >> (s * slice_width)) & ((1 << slice_width) - 1)
                key = (row, s)
                bits = new_srl.get(key, [0] * srl_depth)
                if slice_val >= len(bits) or bits[slice_val] == 0:
                    row_match = 0
                    break
            if row_match:
                match_many |= (1 << row)

        # Priority encoder (LSB priority)
        found = 0
        match_addr = 0
        for i in range(ram_depth):
            if (match_many >> i) & 1 and not found:
                match_addr = i
                found = 1

        ctx.set_state("cam_state", next_state)
        ctx.set_state("count", next_count)
        ctx.set_state("srl_mem", new_srl)
        ctx.set_state("write_addr_reg", next_write_addr)
        ctx.set_state("write_data_reg", next_write_data)
        ctx.set_state("write_delete_reg", next_write_delete)
        ctx.set_state("write_busy", 1 if next_state != STATE_IDLE else 0)
        ctx.set_state("match", found)
        ctx.set_state("match_addr", match_addr)
        ctx.set_state("match_many", match_many)
        ctx.set_state("match_single", 1 << match_addr if found else 0)

        ctx.set_output("write_busy", 1 if next_state != STATE_IDLE else 0)
        ctx.set_output("match", found)
        ctx.set_output("match_addr", match_addr)
        ctx.set_output("match_many", match_many)
        ctx.set_output("match_single", 1 << match_addr if found else 0)

    def _bram_cycle(self, ctx, ram_depth, slice_count, slice_width,
                    rst, write_enable, write_addr, write_data,
                    write_delete, compare_data):
        """BRAM-based CAM cycle simulation."""
        STATE_INIT = 0
        STATE_IDLE = 1
        STATE_DELETE_1 = 2
        STATE_DELETE_2 = 3
        STATE_WRITE_1 = 4
        STATE_WRITE_2 = 5

        if rst:
            ctx.set_state("cam_state", STATE_INIT)
            ctx.set_state("count", (1 << slice_width) - 1)
            ctx.set_state("write_busy", 1)
            ctx.set_state("match", 0)
            ctx.set_state("match_addr", 0)
            ctx.set_state("match_many", 0)
            ctx.set_state("match_single", 0)
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
            clear_bit = (1 << ram_depth) - 1
            wr_en = 1
            if count == 0:
                next_state = STATE_IDLE
            else:
                next_count = count - 1
                next_state = STATE_INIT

        elif state == STATE_IDLE:
            next_write_addr = write_addr
            next_write_data = write_data
            next_write_delete = write_delete
            if write_enable:
                next_state = STATE_DELETE_1
            else:
                next_state = STATE_IDLE

        elif state == STATE_DELETE_1:
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
            next_state = STATE_WRITE_2

        elif state == STATE_WRITE_2:
            set_bit = 1 << (write_addr_reg % ram_depth)
            wr_en = 1
            next_state = STATE_IDLE

        # Update erase_ram
        if erase_ram_wr_en:
            erase_ram[write_addr_reg % ram_depth] = write_data_reg

        # Update BRAM slices
        if wr_en:
            new_slices = []
            for s in range(slice_count):
                old_val = bram_slices[s]
                new_val = (old_val & ~clear_bit) | set_bit
                new_slices.append(new_val)
            bram_slices = new_slices

        # Match logic
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
                break

        # Priority encoder
        found = 0
        match_addr = 0
        for i in range(ram_depth):
            if (match_many >> i) & 1 and not found:
                match_addr = i
                found = 1

        ctx.set_state("cam_state", next_state)
        ctx.set_state("count", next_count)
        ctx.set_state("write_addr_reg", next_write_addr)
        ctx.set_state("write_data_reg", next_write_data)
        ctx.set_state("write_delete_reg", next_write_delete)
        ctx.set_state("erase_ram", erase_ram)
        ctx.set_state("bram_slices", bram_slices)
        ctx.set_state("write_busy", 1 if next_state != STATE_IDLE else 0)
        ctx.set_state("match", found)
        ctx.set_state("match_addr", match_addr)
        ctx.set_state("match_many", match_many)
        ctx.set_state("match_single", 1 << match_addr if found else 0)

        ctx.set_output("write_busy", 1 if next_state != STATE_IDLE else 0)
        ctx.set_output("match", found)
        ctx.set_output("match_addr", match_addr)
        ctx.set_output("match_many", match_many)
        ctx.set_output("match_single", 1 << match_addr if found else 0)

    def create_testbench(self, **kwargs) -> List[Dict]:
        """Generate basic CAM test sequences."""
        tests = []

        # Test 1: Reset
        tests.append({
            "name": "reset",
            "setup": {"rst": 1, "write_enable": 0, "compare_data": 0},
            "cycles": 1,
            "check": {"write_busy": 1, "match": 0},
        })

        # Test 2: Write entry
        tests.append({
            "name": "write_entry",
            "setup": {"rst": 0, "write_enable": 1, "write_addr": 0,
                      "write_data": 0x12345678, "write_delete": 0,
                      "compare_data": 0},
            "cycles": 1,
            "check": {"write_busy": 1},
        })

        # Test 3: Match
        tests.append({
            "name": "match_found",
            "setup": {"rst": 0, "write_enable": 0, "compare_data": 0x12345678},
            "cycles": 1,
            "check": {"match": 1, "match_addr": 0},
        })

        return tests


__all__ = ["CAMModel"]
