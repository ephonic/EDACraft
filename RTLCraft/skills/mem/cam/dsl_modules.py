"""
Spec2RTL Design Flow: CAM — Content Addressable Memory (Professional)
=====================================================================

Reference: Alex Forencich's verilog-cam (ref_rtl/cam)

This design implements a complete, parameterizable CAM with two backends:
  - SRL-based: uses shift-register LUT emulation via Memory(1, depth)
  - BRAM-based: uses dual-port RAM (RamDP) per slice with erase tracking

Key framework extensions used:
  - Memory.init_zero          : zero-init for RAM/erase_ram
  - Reg.init_value            : power-on initialization (e.g., count_reg)
  - Parameter in GenIf        : recursive generate-if for PriorityEncoder
  - Dynamic Memory indexing   : eliminates 500+ Switch statements in CamSRL

Module hierarchy:
  CAM #(CAM_STYLE)
    ├── CamSRL  (when CAM_STYLE == "SRL")
    │     ├── PriorityEncoder
    │     └── Memory-based SRL array
    └── CamBRAM (when CAM_STYLE == "BRAM")
          ├── PriorityEncoder
          ├── RamDP × SLICE_COUNT
          └── erase_ram (Memory)
"""

from __future__ import annotations
import os, sys, math
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const,
    Memory, Parameter, LocalParam,
)
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Switch, ForGen, GenIf, GenElse
from rtlgen.codegen import VerilogEmitter, EmitProfile, ModuleDocTemplate, fill_doc_template

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

# ============================================================================
# Module 1: PriorityEncoder (recursive generate-if style)
# ============================================================================
class PriorityEncoder(Module):
    """Priority encoder with recursive tree structure.

    LSB_PRIORITY="HIGH": lowest set bit wins (rightmost, i.e., LSB has priority).
    LSB_PRIORITY="LOW" : highest set bit wins (leftmost, i.e., MSB has priority).
    """

    def __init__(self, width=4, lsb_priority="HIGH"):
        super().__init__("priority_encoder")
        self.WIDTH = Parameter(width, "WIDTH")
        self.LSB_PRIORITY = Parameter(lsb_priority, "LSB_PRIORITY")

        self.input_unencoded = Input(width, "input_unencoded")
        self.output_valid = Output(1, "output_valid")
        self.output_encoded = Output(max(width.bit_length(), 1), "output_encoded")
        self.output_unencoded = Output(width, "output_unencoded")

        # Build recursive tree in Python (mirrors reference RTL's generate-if)
        self._build_tree(width, lsb_priority)

        # output_unencoded = 1 << output_encoded
        with self.comb:
            self.output_unencoded <<= Const(1, width) << self.output_encoded

        # Documentation
        tpl = ModuleDocTemplate(
            source="CAM PriorityEncoder — recursive tree",
            description=f"{width}-input priority encoder ({lsb_priority} priority)",
            author="rtlgen agent",
            version="1.0",
            timing="Combinational: 1-cycle latency",
        )
        fill_doc_template(tpl, self)

    def _build_tree(self, width: int, lsb_priority: str):
        """Recursively build priority encoder tree via submodule instantiation."""
        if width == 1:
            with self.comb:
                self.output_valid <<= self.input_unencoded[0]
                self.output_encoded <<= 0
            return

        if width == 2:
            with self.comb:
                self.output_valid <<= self.input_unencoded[0] | self.input_unencoded[1]
                if lsb_priority == "LOW":
                    self.output_encoded <<= self.input_unencoded[1]
                else:
                    self.output_encoded <<= ~self.input_unencoded[0]
            return

        # width > 2: split and recurse
        w1 = 2 ** math.ceil(math.log2(width)) if width > 1 else 1
        w2 = w1 // 2
        enc_w = max(w2.bit_length(), 1)

        out1 = Wire(enc_w, "out1")
        out2 = Wire(enc_w, "out2")
        valid1 = Wire(1, "valid1")
        valid2 = Wire(1, "valid2")

        pe1 = PriorityEncoder(width=w2, lsb_priority=lsb_priority)
        pe2 = PriorityEncoder(width=w2, lsb_priority=lsb_priority)

        self.instantiate(pe1, "pe1", port_map={
            "input_unencoded": self.input_unencoded[w2 - 1 : 0],
            "output_valid": valid1,
            "output_encoded": out1,
        })

        if width == w1:
            # No padding needed
            self.instantiate(pe2, "pe2", port_map={
                "input_unencoded": self.input_unencoded[width - 1 : w2],
                "output_valid": valid2,
                "output_encoded": out2,
            })
        else:
            # Pad with zeros
            pad = w1 - width
            self.instantiate(pe2, "pe2", port_map={
                "input_unencoded": Cat(Const(0, pad), self.input_unencoded[width - 1 : w2]),
                "output_valid": valid2,
                "output_encoded": out2,
            })

        with self.comb:
            self.output_valid <<= valid1 | valid2
            if lsb_priority == "LOW":
                # MSB priority: valid2 (upper half) wins
                self.output_encoded <<= Mux(
                    valid2,
                    Cat(Const(1, 1), out2),
                    Cat(Const(0, 1), out1),
                )
            else:
                # LSB priority: valid1 (lower half) wins
                self.output_encoded <<= Mux(
                    valid1,
                    Cat(Const(0, 1), out1),
                    Cat(Const(1, 1), out2),
                )


print("  - PriorityEncoder defined")


# ============================================================================
# Module 2: RamDP (dual-port RAM)
# ============================================================================
class RamDP(Module):
    """Generic dual-port RAM with read-first behavior and zero-init.

    Port A: read + optional write (read-first)
    Port B: read + optional write (read-first)
    """

    def __init__(self, data_width=32, addr_width=10):
        super().__init__("ram_dp")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")

        # Port A
        self.a_clk = Input(1, "a_clk")
        self.a_we = Input(1, "a_we")
        self.a_addr = Input(addr_width, "a_addr")
        self.a_din = Input(data_width, "a_din")
        self.a_dout = Output(data_width, "a_dout")
        # Port B
        self.b_clk = Input(1, "b_clk")
        self.b_we = Input(1, "b_we")
        self.b_addr = Input(addr_width, "b_addr")
        self.b_din = Input(data_width, "b_din")
        self.b_dout = Output(data_width, "b_dout")

        depth = 2 ** addr_width
        self._mem = Memory(data_width, depth, "mem", init_zero=True)
        self._a_dout_reg = Reg(data_width, "a_dout_reg", init_value=0)
        self._b_dout_reg = Reg(data_width, "b_dout_reg", init_value=0)

        with self.comb:
            self.a_dout <<= self._a_dout_reg
            self.b_dout <<= self._b_dout_reg

        with self.seq(self.a_clk):
            self._a_dout_reg <<= self._mem[self.a_addr]
            with If(self.a_we == 1):
                self._mem[self.a_addr] <<= self.a_din
                self._a_dout_reg <<= self.a_din

        with self.seq(self.b_clk):
            self._b_dout_reg <<= self._mem[self.b_addr]
            with If(self.b_we == 1):
                self._mem[self.b_addr] <<= self.b_din
                self._b_dout_reg <<= self.b_din

        tpl = ModuleDocTemplate(
            source="CAM RamDP — dual-port RAM",
            description=f"{data_width}×{depth} dual-port RAM with read-first behavior",
            author="rtlgen agent",
            version="1.0",
            timing="Read-first: read data available on next clock edge",
        )
        fill_doc_template(tpl, self)


print("  - RamDP defined")


# ============================================================================
# Module 3: CamSRL (shift-register based CAM)
# ============================================================================
class CamSRL(Module):
    """SRL-based CAM using Memory(1, depth) per (row, slice) flattened storage.

    Match logic uses direct dynamic indexing (no Switch cascade).
    Shift logic uses nested ForGen with non-blocking assignments.
    """

    def __init__(self, data_width=64, addr_width=5, slice_width=4):
        super().__init__("cam_srl")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")
        self.SLICE_WIDTH = Parameter(slice_width, "SLICE_WIDTH")

        # Derived parameters (as LocalParam for Verilog visibility)
        self.SLICE_COUNT = LocalParam(
            (data_width + slice_width - 1) // slice_width, "SLICE_COUNT"
        )
        self.RAM_DEPTH = LocalParam(2 ** addr_width, "RAM_DEPTH")
        self.SRL_DEPTH = LocalParam(2 ** slice_width, "SRL_DEPTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.write_addr = Input(addr_width, "write_addr")
        self.write_data = Input(data_width, "write_data")
        self.write_delete = Input(1, "write_delete")
        self.write_enable = Input(1, "write_enable")
        self.write_busy = Output(1, "write_busy")

        self.compare_data = Input(data_width, "compare_data")
        self.match_many = Output(2 ** addr_width, "match_many")
        self.match_single = Output(2 ** addr_width, "match_single")
        self.match_addr = Output(addr_width, "match_addr")
        self.match = Output(1, "match")

        slice_count = self.SLICE_COUNT.value
        ram_depth = self.RAM_DEPTH.value
        srl_depth = self.SRL_DEPTH.value
        pad_width = slice_count * slice_width - data_width

        # State encoding
        STATE_INIT = 0
        STATE_IDLE = 1
        STATE_WRITE = 2
        STATE_DELETE = 3

        # ------------------------------------------------------------------
        # Padded data wires
        # ------------------------------------------------------------------
        self._compare_data_padded = Wire(slice_count * slice_width,
                                         "compare_data_padded")
        self._write_data_padded = Wire(slice_count * slice_width,
                                       "write_data_padded")

        # ------------------------------------------------------------------
        # SRL storage: flattened Memory(width=1, depth=ram_depth*slice_count*srl_depth)
        # Access: srl_mem[row*slice_count*srl_depth + slice*srl_depth + addr]
        # ------------------------------------------------------------------
        total_srl_depth = ram_depth * slice_count * srl_depth
        self._srl_mem = Memory(1, total_srl_depth, "srl_mem", init_zero=True)

        # ------------------------------------------------------------------
        # State machine registers
        # ------------------------------------------------------------------
        self._state_reg = Reg(2, "state_reg", init_value=STATE_INIT)
        self._state_next = Wire(2, "state_next")
        self._count_reg = Reg(slice_width, "count_reg",
                              init_value=(1 << slice_width) - 1)
        self._count_next = Wire(slice_width, "count_next")

        self._shift_data = Wire(slice_count, "shift_data")
        self._shift_en = Wire(ram_depth, "shift_en")

        self._write_addr_reg = Reg(addr_width, "write_addr_reg", init_value=0)
        self._write_addr_next = Wire(addr_width, "write_addr_next")
        self._write_data_padded_reg = Reg(slice_count * slice_width,
                                          "write_data_padded_reg", init_value=0)
        self._write_data_padded_next = Wire(slice_count * slice_width,
                                            "write_data_padded_next")
        self._write_busy_reg = Reg(1, "write_busy_reg", init_value=1)

        # ------------------------------------------------------------------
        # Match vectors
        # ------------------------------------------------------------------
        self._match_raw_out = [Wire(ram_depth, f"match_raw_out_{s}")
                               for s in range(slice_count)]
        self._match_many_raw = Wire(ram_depth, "match_many_raw")
        self._match_many_reg = Reg(ram_depth, "match_many_reg", init_value=0)

        # ------------------------------------------------------------------
        # Priority encoder
        # ------------------------------------------------------------------
        self._pe = PriorityEncoder(width=ram_depth, lsb_priority="HIGH")
        self.instantiate(self._pe, "priority_encoder_inst", port_map={
            "input_unencoded": self._match_many_reg,
            "output_valid": self.match,
            "output_encoded": self.match_addr,
            "output_unencoded": self.match_single,
        })

        # ------------------------------------------------------------------
        # Comb: padding
        # ------------------------------------------------------------------
        with self.comb:
            if pad_width > 0:
                self._compare_data_padded <<= Cat(
                    Const(0, pad_width), self.compare_data
                )
                self._write_data_padded <<= Cat(
                    Const(0, pad_width), self.write_data
                )
            else:
                self._compare_data_padded <<= self.compare_data
                self._write_data_padded <<= self.write_data

        # ------------------------------------------------------------------
        # Comb: match logic (dynamic Memory indexing — no Switch cascade)
        # ------------------------------------------------------------------
        with self.comb:
            for s in range(slice_count):
                bits = []
                for row in range(ram_depth):
                    addr = self._compare_data_padded[
                        s * slice_width + slice_width - 1 : s * slice_width
                    ]
                    base = row * slice_count * srl_depth + s * srl_depth
                    bit = self._srl_mem[base + addr]
                    bits.append(bit)
                self._match_raw_out[s] <<= Cat(*reversed(bits))

            # AND across all slices, starting from ~shift_en
            match_expr = ~self._shift_en
            for s in range(slice_count):
                match_expr = match_expr & self._match_raw_out[s]
            self._match_many_raw <<= match_expr
            self.match_many <<= self._match_many_reg

        # ------------------------------------------------------------------
        # Seq: match pipeline
        # ------------------------------------------------------------------
        with self.seq(self.clk):
            self._match_many_reg <<= self._match_many_raw

        # ------------------------------------------------------------------
        # Comb: write FSM next-state logic
        # ------------------------------------------------------------------
        with self.comb:
            # Defaults
            self._state_next <<= STATE_IDLE
            self._count_next <<= self._count_reg
            self._shift_data <<= Const(0, slice_count)
            self._shift_en <<= Const(0, ram_depth)
            self._write_addr_next <<= self._write_addr_reg
            self._write_data_padded_next <<= self._write_data_padded_reg

            with Switch(self._state_reg) as sw:
                with sw.case(STATE_INIT):
                    self._shift_en <<= Const((1 << ram_depth) - 1, ram_depth)
                    self._shift_data <<= Const(0, slice_count)
                    with If(self._count_reg == 0):
                        self._state_next <<= STATE_IDLE
                    with Else():
                        self._count_next <<= self._count_reg - 1
                        self._state_next <<= STATE_INIT

                with sw.case(STATE_IDLE):
                    with If(self.write_enable == 1):
                        self._write_addr_next <<= self.write_addr
                        self._write_data_padded_next <<= self._write_data_padded
                        self._count_next <<= Const(
                            (1 << slice_width) - 1, slice_width
                        )
                        with If(self.write_delete == 1):
                            self._state_next <<= STATE_DELETE
                        with Else():
                            self._state_next <<= STATE_WRITE
                    with Else():
                        self._state_next <<= STATE_IDLE

                with sw.case(STATE_WRITE):
                    self._shift_en <<= Const(1, ram_depth) << self.write_addr
                    # shift_data[i] = (count_reg == write_data slice i)
                    sd_bits = []
                    for s in range(slice_count):
                        slice_val = self._write_data_padded_reg[
                            s * slice_width + slice_width - 1 : s * slice_width
                        ]
                        sd_bits.append(self._count_reg == slice_val)
                    self._shift_data <<= Cat(*reversed(sd_bits))

                    with If(self._count_reg == 0):
                        self._state_next <<= STATE_IDLE
                    with Else():
                        self._count_next <<= self._count_reg - 1
                        self._state_next <<= STATE_WRITE

                with sw.case(STATE_DELETE):
                    self._shift_en <<= Const(1, ram_depth) << self.write_addr
                    self._shift_data <<= Const(0, slice_count)
                    with If(self._count_reg == 0):
                        self._state_next <<= STATE_IDLE
                    with Else():
                        self._count_next <<= self._count_reg - 1
                        self._state_next <<= STATE_DELETE

                with sw.default():
                    pass

            self.write_busy <<= self._write_busy_reg

        # ------------------------------------------------------------------
        # Seq: write FSM state registers
        # ------------------------------------------------------------------
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state_reg <<= STATE_INIT
                self._count_reg <<= Const((1 << slice_width) - 1, slice_width)
                self._write_busy_reg <<= 1
            with Else():
                self._state_reg <<= self._state_next
                self._count_reg <<= self._count_next
                self._write_busy_reg <<= (self._state_next != STATE_IDLE)

            self._write_addr_reg <<= self._write_addr_next
            self._write_data_padded_reg <<= self._write_data_padded_next

        # ------------------------------------------------------------------
        # Seq: SRL shift registers
        # ------------------------------------------------------------------
        with self.seq(self.clk):
            with ForGen("row", 0, ram_depth) as row:
                with If(self._shift_en[row] == 1):
                    with ForGen("s", 0, slice_count) as s:
                        with ForGen("addr", srl_depth - 1, -1, step=-1) as addr:
                            base = row * slice_count * srl_depth + s * srl_depth + addr
                            with If(addr > 0):
                                self._srl_mem[base] <<= self._srl_mem[base - 1]
                            with Else():
                                self._srl_mem[base] <<= self._shift_data[s]

        tpl = ModuleDocTemplate(
            source="CAM CamSRL — SRL-based content addressable memory",
            description=f"SRL CAM: {data_width}-bit data, {ram_depth} entries, {slice_count} slices",
            author="rtlgen agent",
            version="1.0",
            timing="Match: 1-cycle registered output. Write: {srl_depth}+1 cycles per entry.",
        )
        fill_doc_template(tpl, self)


print("  - CamSRL defined")


# ============================================================================
# Module 4: CamBRAM (block-RAM based CAM)
# ============================================================================
class CamBRAM(Module):
    """BRAM-based CAM using dual-port RAM per slice with erase tracking.

    Each slice has a RamDP (depth=RAM_DEPTH, addr_width=slice_width).
    erase_ram tracks stored data for correct delete operation.
    """

    def __init__(self, data_width=64, addr_width=5, slice_width=9):
        super().__init__("cam_bram")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")
        self.SLICE_WIDTH = Parameter(slice_width, "SLICE_WIDTH")

        self.SLICE_COUNT = LocalParam(
            (data_width + slice_width - 1) // slice_width, "SLICE_COUNT"
        )
        self.RAM_DEPTH = LocalParam(2 ** addr_width, "RAM_DEPTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.write_addr = Input(addr_width, "write_addr")
        self.write_data = Input(data_width, "write_data")
        self.write_delete = Input(1, "write_delete")
        self.write_enable = Input(1, "write_enable")
        self.write_busy = Output(1, "write_busy")

        self.compare_data = Input(data_width, "compare_data")
        self.match_many = Output(2 ** addr_width, "match_many")
        self.match_single = Output(2 ** addr_width, "match_single")
        self.match_addr = Output(addr_width, "match_addr")
        self.match = Output(1, "match")

        slice_count = self.SLICE_COUNT.value
        ram_depth = self.RAM_DEPTH.value
        pad_width = slice_count * slice_width - data_width

        # State encoding
        STATE_INIT = 0
        STATE_IDLE = 1
        STATE_DELETE_1 = 2
        STATE_DELETE_2 = 3
        STATE_WRITE_1 = 4
        STATE_WRITE_2 = 5

        # ------------------------------------------------------------------
        # Padded data wires
        # ------------------------------------------------------------------
        self._compare_data_padded = Wire(slice_count * slice_width,
                                         "compare_data_padded")
        self._write_data_padded = Wire(slice_count * slice_width,
                                       "write_data_padded")

        # ------------------------------------------------------------------
        # State machine registers
        # ------------------------------------------------------------------
        self._state_reg = Reg(3, "state_reg", init_value=STATE_INIT)
        self._state_next = Wire(3, "state_next")
        self._count_reg = Reg(slice_width, "count_reg",
                              init_value=(1 << slice_width) - 1)
        self._count_next = Wire(slice_width, "count_next")

        self._ram_addr = Wire(slice_count * slice_width, "ram_addr")
        self._set_bit = Wire(ram_depth, "set_bit")
        self._clear_bit = Wire(ram_depth, "clear_bit")
        self._wr_en = Wire(1, "wr_en")

        self._write_addr_reg = Reg(addr_width, "write_addr_reg", init_value=0)
        self._write_addr_next = Wire(addr_width, "write_addr_next")
        self._write_data_padded_reg = Reg(slice_count * slice_width,
                                          "write_data_padded_reg", init_value=0)
        self._write_data_padded_next = Wire(slice_count * slice_width,
                                            "write_data_padded_next")
        self._write_delete_reg = Reg(1, "write_delete_reg", init_value=0)
        self._write_delete_next = Wire(1, "write_delete_next")
        self._write_busy_reg = Reg(1, "write_busy_reg", init_value=1)

        # ------------------------------------------------------------------
        # Match vectors
        # ------------------------------------------------------------------
        self._match_raw_out = [Wire(ram_depth, f"match_raw_out_{s}")
                               for s in range(slice_count)]
        self._match_many_raw = Wire(ram_depth, "match_many_raw")

        # ------------------------------------------------------------------
        # Erase RAM (tracks stored data for delete)
        # ------------------------------------------------------------------
        self._erase_ram = Memory(data_width, ram_depth, "erase_ram",
                                 init_zero=True)
        self._erase_data = Reg(data_width, "erase_data", init_value=0)
        self._erase_ram_wr_en = Wire(1, "erase_ram_wr_en")

        # ------------------------------------------------------------------
        # RamDP data wires (for write-back)
        # ------------------------------------------------------------------
        self._ram_data = [Wire(ram_depth, f"ram_data_{s}")
                          for s in range(slice_count)]

        # ------------------------------------------------------------------
        # BRAM slice instances
        # ------------------------------------------------------------------
        for s in range(slice_count):
            # Last slice may be narrower
            w = (data_width - slice_width * s) if s == slice_count - 1 else slice_width
            ram_inst = RamDP(data_width=ram_depth, addr_width=w)
            self.instantiate(ram_inst, f"ram_inst_{s}", port_map={
                "a_clk": self.clk,
                "a_we": Const(0, 1),
                "a_addr": self._compare_data_padded[
                    s * slice_width + w - 1 : s * slice_width
                ],
                "a_din": Const(0, ram_depth),
                "a_dout": self._match_raw_out[s],
                "b_clk": self.clk,
                "b_we": self._wr_en,
                "b_addr": self._ram_addr[
                    s * slice_width + w - 1 : s * slice_width
                ],
                "b_din": (self._ram_data[s] & ~self._clear_bit) | self._set_bit,
                "b_dout": self._ram_data[s],
            })

        # ------------------------------------------------------------------
        # Priority encoder
        # ------------------------------------------------------------------
        self._pe = PriorityEncoder(width=ram_depth, lsb_priority="HIGH")
        self.instantiate(self._pe, "priority_encoder_inst", port_map={
            "input_unencoded": self._match_many_raw,
            "output_valid": self.match,
            "output_encoded": self.match_addr,
            "output_unencoded": self.match_single,
        })

        # ------------------------------------------------------------------
        # Comb: padding
        # ------------------------------------------------------------------
        with self.comb:
            if pad_width > 0:
                self._compare_data_padded <<= Cat(
                    Const(0, pad_width), self.compare_data
                )
                self._write_data_padded <<= Cat(
                    Const(0, pad_width), self.write_data
                )
            else:
                self._compare_data_padded <<= self.compare_data
                self._write_data_padded <<= self.write_data

        # ------------------------------------------------------------------
        # Comb: match many
        # ------------------------------------------------------------------
        with self.comb:
            match_expr = Const((1 << ram_depth) - 1, ram_depth)
            for s in range(slice_count):
                match_expr = match_expr & self._match_raw_out[s]
            self._match_many_raw <<= match_expr
            self.match_many <<= self._match_many_raw

        # ------------------------------------------------------------------
        # Seq: erase RAM
        # ------------------------------------------------------------------
        with self.seq(self.clk):
            self._erase_data <<= self._erase_ram[self._write_addr_next]
            with If(self._erase_ram_wr_en == 1):
                self._erase_data <<= self._write_data_padded_reg
                self._erase_ram[self._write_addr_next] <<= self._write_data_padded_reg

        # ------------------------------------------------------------------
        # Comb: write FSM next-state logic
        # ------------------------------------------------------------------
        with self.comb:
            # Defaults
            self._state_next <<= STATE_IDLE
            self._count_next <<= self._count_reg
            self._ram_addr <<= self._erase_data
            self._set_bit <<= Const(0, ram_depth)
            self._clear_bit <<= Const(0, ram_depth)
            self._wr_en <<= 0
            self._erase_ram_wr_en <<= 0
            self._write_addr_next <<= self._write_addr_reg
            self._write_data_padded_next <<= self._write_data_padded_reg
            self._write_delete_next <<= self._write_delete_reg

            with Switch(self._state_reg) as sw:
                with sw.case(STATE_INIT):
                    # Zero out RAMs: ram_addr = {SLICE_COUNT{count_reg}} & mask
                    full_ones = Const((1 << data_width) - 1, data_width)
                    mask = Cat(Const(0, pad_width), full_ones) if pad_width > 0 else full_ones
                    self._ram_addr <<= (Rep(self._count_reg, slice_count) & mask)
                    self._clear_bit <<= Const((1 << ram_depth) - 1, ram_depth)
                    self._wr_en <<= 1
                    with If(self._count_reg == 0):
                        self._state_next <<= STATE_IDLE
                    with Else():
                        self._count_next <<= self._count_reg - 1
                        self._state_next <<= STATE_INIT

                with sw.case(STATE_IDLE):
                    self._write_addr_next <<= self.write_addr
                    self._write_data_padded_next <<= self._write_data_padded
                    self._write_delete_next <<= self.write_delete
                    with If(self.write_enable == 1):
                        self._state_next <<= STATE_DELETE_1
                    with Else():
                        self._state_next <<= STATE_IDLE

                with sw.case(STATE_DELETE_1):
                    self._state_next <<= STATE_DELETE_2

                with sw.case(STATE_DELETE_2):
                    self._clear_bit <<= Const(1, ram_depth) << self.write_addr
                    self._wr_en <<= 1
                    with If(self._write_delete_reg == 1):
                        self._state_next <<= STATE_IDLE
                    with Else():
                        self._erase_ram_wr_en <<= 1
                        self._state_next <<= STATE_WRITE_1

                with sw.case(STATE_WRITE_1):
                    self._state_next <<= STATE_WRITE_2

                with sw.case(STATE_WRITE_2):
                    self._set_bit <<= Const(1, ram_depth) << self.write_addr
                    self._wr_en <<= 1
                    self._state_next <<= STATE_IDLE

                with sw.default():
                    pass

            self.write_busy <<= self._write_busy_reg

        # ------------------------------------------------------------------
        # Seq: write FSM state registers
        # ------------------------------------------------------------------
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state_reg <<= STATE_INIT
                self._count_reg <<= Const((1 << slice_width) - 1, slice_width)
                self._write_busy_reg <<= 1
            with Else():
                self._state_reg <<= self._state_next
                self._count_reg <<= self._count_next
                self._write_busy_reg <<= (self._state_next != STATE_IDLE)

            self._write_addr_reg <<= self._write_addr_next
            self._write_data_padded_reg <<= self._write_data_padded_next
            self._write_delete_reg <<= self._write_delete_next

        tpl = ModuleDocTemplate(
            source="CAM CamBRAM — BRAM-based content addressable memory",
            description=f"BRAM CAM: {data_width}-bit data, {ram_depth} entries, {slice_count} slices",
            author="rtlgen agent",
            version="1.0",
            timing="Match: combinational. Write: 4-5 cycles per entry.",
        )
        fill_doc_template(tpl, self)


print("  - CamBRAM defined")


# ============================================================================
# Module 5: CAM (top wrapper with generate-if)
# ============================================================================
class CAM(Module):
    """Top-level CAM wrapper with parameterizable CAM_STYLE.

    CAM_STYLE = "SRL"  → instantiates CamSRL
    CAM_STYLE = "BRAM" → instantiates CamBRAM
    """

    def __init__(self, cam_style="SRL"):
        super().__init__("cam")
        # Use integer encoding: 0=SRL, 1=BRAM (strings not supported in GenIf expressions)
        style_val = 0 if cam_style == "SRL" else 1
        self.CAM_STYLE = Parameter(style_val, "CAM_STYLE")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.write_addr = Input(5, "write_addr")
        self.write_data = Input(64, "write_data")
        self.write_delete = Input(1, "write_delete")
        self.write_enable = Input(1, "write_enable")
        self.write_busy = Output(1, "write_busy")

        self.compare_data = Input(64, "compare_data")
        self.match_many = Output(32, "match_many")
        self.match_single = Output(32, "match_single")
        self.match_addr = Output(5, "match_addr")
        self.match = Output(1, "match")

        with GenIf(self.CAM_STYLE == 0):
            srl_inst = CamSRL(data_width=64, addr_width=5, slice_width=4)
            self.instantiate(srl_inst, "cam_srl_inst", port_map={
                "clk": self.clk,
                "rst": self.rst,
                "write_addr": self.write_addr,
                "write_data": self.write_data,
                "write_delete": self.write_delete,
                "write_enable": self.write_enable,
                "write_busy": self.write_busy,
                "compare_data": self.compare_data,
                "match_many": self.match_many,
                "match_single": self.match_single,
                "match_addr": self.match_addr,
                "match": self.match,
            })

        with GenElse():
            bram_inst = CamBRAM(data_width=64, addr_width=5, slice_width=9)
            self.instantiate(bram_inst, "cam_bram_inst", port_map={
                "clk": self.clk,
                "rst": self.rst,
                "write_addr": self.write_addr,
                "write_data": self.write_data,
                "write_delete": self.write_delete,
                "write_enable": self.write_enable,
                "write_busy": self.write_busy,
                "compare_data": self.compare_data,
                "match_many": self.match_many,
                "match_single": self.match_single,
                "match_addr": self.match_addr,
                "match": self.match,
            })

        tpl = ModuleDocTemplate(
            source="CAM — top-level wrapper",
            description="Content Addressable Memory with SRL/BRAM backend selection",
            author="rtlgen agent",
            version="1.0",
            timing="Pass-through to selected backend",
        )
        fill_doc_template(tpl, self)
