"""JPEG baseline decoder modules for rtlgen_x.

This package implements a constrained baseline JPEG decoder using rtlgen_x DSL
standard-library components.  Supported features:

* Baseline DCT, 8x8 blocks, 8-bit samples
* One scan, one frame, 4:2:0 or grayscale
* Hard-coded baseline DC/AC Huffman tables (software can also upload tables
  through the APB register bank for verification flexibility)
* Quantization tables loaded through APB
* AXI4-Stream byte input, AXI4-Stream RGB pixel output

The implementation is intentionally modular so that each stage can be verified
in isolation and then integrated.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from rtlgen_x.dsl import (
    APBRegisterBank,
    Array,
    Const,
    Cat,
    FSM,
    If,
    Else,
    Input,
    LUT,
    Memory,
    Module,
    Mux,
    Output,
    Reg,
    RoundShiftRight,
    SignedMultiplier,
    SkidBuffer,
    SyncFIFO,
    Switch,
    When,
    Wire,
)

# ---------------------------------------------------------------------------
# Shared constants and lookup tables
# ---------------------------------------------------------------------------

COEFF_WIDTH = 12          # signed de-quantized coefficient width
PIXEL_WIDTH = 8           # output pixel sample width
IDCT_FRAC = 14            # fixed-point fractional bits for iDCT cosine table

# Standard JPEG zig-zag scan order: ZIGZAG_ORDER[i] is the raster index of the
# i-th coefficient in zig-zag order.  INV_ZIGZAG[raster] is the zig-zag index.
ZIGZAG_ORDER: Tuple[int, ...] = (
    0,  1,  5,  6, 14, 15, 27, 28,
    2,  4,  7, 13, 16, 26, 29, 42,
    3,  8, 12, 17, 25, 30, 41, 43,
    9, 11, 18, 24, 31, 40, 44, 53,
    10, 19, 23, 32, 39, 45, 52, 54,
    20, 22, 33, 38, 46, 51, 55, 60,
    21, 34, 37, 47, 50, 56, 59, 61,
    35, 36, 48, 49, 57, 58, 62, 63,
)
INV_ZIGZAG: Tuple[int, ...] = tuple(ZIGZAG_ORDER.index(i) for i in range(64))


def _build_idct_table() -> List[int]:
    """Build 8x8 fixed-point iDCT matrix.

    Entry[u][v] = round(c(u) * cos((2*v+1)*u*pi/16) * 2**IDCT_FRAC)
    where c(0) = 1/sqrt(8), c(u>0) = 1/2.
    The table is flattened as 64 entries in row-major (u major, v minor).
    """
    entries: List[int] = []
    for u in range(8):
        scale = 1.0 / math.sqrt(8) if u == 0 else 0.5
        for v in range(8):
            val = scale * math.cos((2 * v + 1) * u * math.pi / 16.0)
            entries.append(int(round(val * (1 << IDCT_FRAC))))
    return entries


IDCT_TABLE = _build_idct_table()


# ---------------------------------------------------------------------------
# 8x8 inverse DCT (separable, row then column)
# ---------------------------------------------------------------------------

class JpegIdct8x8(Module):
    """Two-dimensional 8x8 inverse DCT.

    Input: 64 signed coefficients presented sequentially while in_ready is high.
            The first cycle of a block must have in_valid high; the module
            accepts one coefficient per cycle for 64 cycles.
    Output: 64 unsigned pixel samples (with +128 level shift) presented
            sequentially.  out_valid marks valid output samples.

    Uses an 8-element multiply-accumulate datapath for one 1-D iDCT.  Row
    transform and column transform share the same datapath.  A 64-entry
    intermediate transpose buffer holds the row transform results.
    """

    def __init__(self, coeff_width: int = COEFF_WIDTH, name: str = "JpegIdct8x8"):
        super().__init__(name)
        self.coeff_width = coeff_width

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.in_data = Input(coeff_width, "in_data", signed=True)
        self.in_valid = Input(1, "in_valid")
        self.in_ready = Output(1, "in_ready")

        self.out_data = Output(PIXEL_WIDTH, "out_data")
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")

        # Internal accumulator width.
        self._acc_width = coeff_width + 16 + 4

        # Cosine lookup table: addr = {u(3), v(3)}.
        self._idct_mem = Memory(16, 64, "idct_mem", init_data=IDCT_TABLE)
        self._idct_lut_addr = Wire(6, "idct_lut_addr")
        self._idct_lut_data = Wire(16, "idct_lut_data", signed=True)
        with self.comb:
            self._idct_lut_data <<= self._idct_mem[self._idct_lut_addr]

        # Storage.
        self._block = Array(coeff_width, 64, "block")     # input coefficient block
        self._tbuf = Array(16, 64, "tbuf")                # row-transform transpose buffer

        # Control state machine.
        self._state = Reg(3, "state")
        # state encoding
        ST_IDLE = 0
        ST_LOAD = 1
        ST_ROW = 2
        ST_COL = 3
        ST_DONE = 4

        self._idx = Reg(6, "idx")          # general counter / block index
        self._row = Reg(3, "row")
        self._col = Reg(3, "col")
        self._u = Reg(3, "u")              # inner sum index
        self._acc = Reg(self._acc_width, "acc", signed=True)
        self._out_valid_reg = Reg(1, "out_valid_reg")
        self._out_data_reg = Reg(PIXEL_WIDTH, "out_data_reg")

        # Design-visible temporaries are registered on self so lowering,
        # emitted RTL, and lint can track them consistently.
        self._lut_addr = Wire(6, "lut_addr")
        self._sample = Wire(coeff_width, "sample", signed=True)
        self._prod = Wire(self._acc_width, "prod", signed=True)
        self._sum_next = Wire(self._acc_width, "sum_next", signed=True)
        self._scaled = Wire(self._acc_width, "scaled", signed=True)
        self._final = Wire(self._acc_width + 1, "final", signed=True)
        self._clipped = Wire(self._acc_width + 1, "clipped", signed=True)

        with self.comb:
            # In row transform the table column is the output column;
            # in column transform it is the output row.
            lut_col = Mux(self._state == 3, self._row, self._col)
            self._lut_addr <<= Cat(self._u, lut_col)
            self._idct_lut_addr <<= self._lut_addr

        with self.comb:
            with If(self._state == ST_COL):
                # tbuf is stored as tbuf[col*8 + row] = h[row][col].
                # We need h[u][col] = tbuf[col*8 + u].
                self._sample <<= self._tbuf[(self._col << 3) | self._u]
            with Else():
                self._sample <<= self._block[(self._row << 3) | self._u]

        with self.comb:
            # Use the DSL $signed cast so both the Python and C++ simulators
            # interpret the stored two's-complement values as signed integers.
            self._prod <<= self._sample.as_sint() * self._idct_lut_data.as_sint()
            self._sum_next <<= self._acc + self._prod
            # Preserve signed rounding intent across Python/C++/emitted RTL.
            self._scaled <<= RoundShiftRight(self._sum_next, IDCT_FRAC)
            self._final <<= self._scaled.as_sint() + Const(128, self._acc_width + 1)
            self._clipped <<= Mux(
                self._final.as_sint() < Const(0, self._acc_width + 1).as_sint(),
                Const(0, self._acc_width + 1),
                Mux(
                    self._final.as_sint() > Const(255, self._acc_width + 1).as_sint(),
                    Const(255, self._acc_width + 1),
                    self._final,
                ),
            )

        self._write_idx = Wire(6, "write_idx")
        with self.comb:
            self._write_idx <<= (self._col << 3) | self._row   # transpose

        # Sequential control.
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= ST_IDLE
                self._idx <<= 0
                self._row <<= 0
                self._col <<= 0
                self._u <<= 0
                self._acc <<= 0
                self._out_valid_reg <<= 0
                self._out_data_reg <<= 0
                for i in range(64):
                    self._block[i] <<= 0
                    self._tbuf[i] <<= 0
            with Else():
                self._out_valid_reg <<= 0

                with Switch(self._state) as sw:
                    with sw.case(0):   # ST_IDLE
                        with If(self.in_valid == 1):
                            self._state <<= 1
                            self._idx <<= 1
                            self._block[0] <<= self.in_data

                    with sw.case(1):   # ST_LOAD
                        with If(self.in_valid == 1):
                            self._block[self._idx] <<= self.in_data
                            with If(self._idx < 63):
                                self._idx <<= self._idx + 1
                            with Else():
                                self._state <<= 2
                                self._row <<= 0
                                self._col <<= 0
                                self._u <<= 0
                                self._acc <<= 0

                    with sw.case(2):   # ST_ROW
                        with If(self._u < 7):
                            self._u <<= self._u + 1
                            self._acc <<= self._sum_next
                        with Else():
                            self._u <<= 0
                            self._tbuf[self._write_idx] <<= self._scaled[15:0]
                            with If(self._col < 7):
                                self._col <<= self._col + 1
                                self._acc <<= 0
                            with Else():
                                with If(self._row < 7):
                                    self._row <<= self._row + 1
                                    self._col <<= 0
                                    self._acc <<= 0
                                with Else():
                                    self._state <<= 3
                                    self._row <<= 0
                                    self._col <<= 0
                                    self._acc <<= 0

                    with sw.case(3):   # ST_COL
                        with If(self._u < 7):
                            self._u <<= self._u + 1
                            self._acc <<= self._sum_next
                        with Else():
                            self._u <<= 0
                            self._out_data_reg <<= self._clipped[PIXEL_WIDTH - 1:0]
                            self._out_valid_reg <<= 1
                            with If(self._col < 7):
                                self._col <<= self._col + 1
                                self._acc <<= 0
                            with Else():
                                with If(self._row < 7):
                                    self._row <<= self._row + 1
                                    self._col <<= 0
                                    self._acc <<= 0
                                with Else():
                                    self._state <<= 4

                    with sw.case(4):   # ST_DONE
                        self._state <<= 0

        with self.comb:
            self.in_ready <<= (self._state == ST_IDLE) | (self._state == ST_LOAD)
            self.out_data <<= self._out_data_reg
            self.out_valid <<= self._out_valid_reg


# ---------------------------------------------------------------------------
# De-quantization + zig-zag reorder
# ---------------------------------------------------------------------------

class JpegDequantZigzag(Module):
    """Zig-zag to raster reorder followed by de-quantization.

    Input: 64 signed quantized coefficients in zig-zag order, presented
            sequentially.  in_valid marks the first coefficient.
    Output: 64 signed de-quantized coefficients in raster order, presented
            sequentially.  out_valid marks the first coefficient.

    The quantization table is stored in a 64-entry memory.  A default table of
    all ones is loaded at reset; software can overwrite entries through the
    APB-like slave interface if desired.
    """

    def __init__(
        self,
        quant_width: int = 8,
        coeff_width: int = COEFF_WIDTH,
        name: str = "JpegDequantZigzag",
    ):
        super().__init__(name)
        self.quant_width = quant_width
        self.coeff_width = coeff_width

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.in_data = Input(12, "in_data", signed=True)
        self.in_valid = Input(1, "in_valid")
        self.in_ready = Output(1, "in_ready")

        self.out_data = Output(coeff_width, "out_data", signed=True)
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")

        # Quantization table memory (default all ones).
        # NOTE: using a hard-coded value of 1 to avoid a Memory init_data bug
        # when the module is flattened as a submodule (see audit report).
        default_quant = [1] * 64
        self._quant_mem = Memory(quant_width, 64, "quant_mem", init_data=default_quant)

        # Coefficient buffer (zig-zag input).
        self._zigzag_buf = Array(12, 64, "zigzag_buf")

        # FSM.
        self._state = Reg(2, "state")
        ST_IDLE = 0
        ST_LOAD = 1
        ST_OUT = 2

        self._idx = Reg(6, "idx")
        self._out_valid_reg = Reg(1, "out_valid_reg")
        self._out_data_reg = Reg(coeff_width, "out_data_reg", signed=True)

        # Output address: raster index -> zig-zag index.
        self._raster_idx = Wire(6, "raster_idx")
        self._zz_idx_wire = Wire(6, "zz_idx")
        self._quant_val = Wire(quant_width, "quant_val")
        self._zigzag_coeff = Wire(12, "zigzag_coeff", signed=True)
        self._dequant = Wire(coeff_width, "dequant", signed=True)

        # Build inverse zig-zag LUT (raster index -> zig-zag index).
        self._zz_lut = Memory(6, 64, "zz_lut", init_data=list(INV_ZIGZAG))
        with self.comb:
            self._zz_idx_wire <<= self._zz_lut[self._raster_idx]

        with self.comb:
            self._raster_idx <<= self._idx
            self._quant_val <<= self._quant_mem[self._raster_idx]
            self._zigzag_coeff <<= self._zigzag_buf[self._zz_idx_wire]
            self._dequant <<= self._zigzag_coeff * self._quant_val

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= ST_IDLE
                self._idx <<= 0
                self._out_valid_reg <<= 0
                self._out_data_reg <<= 0
                for i in range(64):
                    self._zigzag_buf[i] <<= 0
            with Else():
                self._out_valid_reg <<= 0

                with Switch(self._state) as sw:
                    with sw.case(ST_IDLE):
                        with If(self.in_valid == 1):
                            self._state <<= ST_LOAD
                            self._idx <<= 1
                            self._zigzag_buf[0] <<= self.in_data

                    with sw.case(ST_LOAD):
                        with If(self.in_valid == 1):
                            self._zigzag_buf[self._idx] <<= self.in_data
                            with If(self._idx < 63):
                                self._idx <<= self._idx + 1
                            with Else():
                                self._state <<= ST_OUT
                                self._idx <<= 0

                    with sw.case(ST_OUT):
                        self._out_data_reg <<= self._dequant[coeff_width - 1:0]
                        self._out_valid_reg <<= 1
                        with If(self._idx < 63):
                            self._idx <<= self._idx + 1
                        with Else():
                            self._state <<= ST_IDLE
                            self._idx <<= 0

        with self.comb:
            self.in_ready <<= (self._state == ST_IDLE) | (self._state == ST_LOAD)
            self.out_data <<= self._out_data_reg
            self.out_valid <<= self._out_valid_reg


# ---------------------------------------------------------------------------
# Simplified entropy/RLE decoder
# ---------------------------------------------------------------------------

class JpegEntropyDecoder(Module):
    """Simplified entropy-to-coefficient decoder.

    This is a teaching/demonstration decoder, not a full JPEG Huffman decoder.
    It consumes a byte stream of 16-bit RLE tokens and produces 64 signed
    quantized coefficients in zig-zag order.

    Token format (little-endian):
      [15:12] = run_length (number of leading zeros, 0..14)
      [11: 0] = signed 12-bit coefficient value
      0xF000  = End-of-Block (EOB)

    The module buffers input bytes, assembles 16-bit tokens, and writes the
    decoded coefficients into an output register file.  When one 8x8 block is
    complete it raises block_valid; the consumer must assert block_ready to
    advance to the next block.
    """

    def __init__(self, name: str = "JpegEntropyDecoder"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI4-Stream slave input (byte-wide).
        self.s_axis_tdata = Input(8, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.s_axis_tlast = Input(1, "s_axis_tlast")

        # Coefficient block output.
        self.coeff_out = Output(12, "coeff_out", signed=True)
        self.coeff_valid = Output(1, "coeff_valid")
        self.coeff_ready = Input(1, "coeff_ready")
        self.block_valid = Output(1, "block_valid")
        self.block_ready = Input(1, "block_ready")

        # Byte input skid buffer.
        self._skid_out_data = Wire(8, "skid_out_data")
        self._skid_out_valid = Wire(1, "skid_out_valid")
        self._skid_out_ready = Wire(1, "skid_out_ready")
        self._skid = SkidBuffer(width=8, name="in_skid")
        self.instantiate(
            self._skid,
            "u_in_skid",
            port_map={
                "clk": self.clk,
                "rst": self.rst,
                "in_data": self.s_axis_tdata,
                "in_valid": self.s_axis_tvalid,
                "in_ready": self.s_axis_tready,
                "out_data": self._skid_out_data,
                "out_valid": self._skid_out_valid,
                "out_ready": self._skid_out_ready,
            },
        )

        # Token assembly and decode.
        self._byte_reg = Reg(8, "byte_reg")
        self._has_byte = Reg(1, "has_byte")
        self._token = Reg(16, "token")
        self._token_valid = Reg(1, "token_valid")

        self._zz_idx = Reg(7, "zz_idx")       # current zig-zag position (0..64)
        self._run_cnt = Reg(4, "run_cnt")     # zeros to insert
        self._block_done = Reg(1, "block_done")
        self._coeff_out_reg = Reg(12, "coeff_out_reg", signed=True)
        self._coeff_valid_reg = Reg(1, "coeff_valid_reg")
        self._block_valid_reg = Reg(1, "block_valid_reg")

        # Wires.
        skid_out_data = self._skid_out_data
        skid_out_valid = self._skid_out_valid
        skid_out_ready = self._skid_out_ready

        self._token_run = Wire(4, "token_run")
        self._token_val = Wire(12, "token_val", signed=True)
        with self.comb:
            self._token_run <<= self._token[15:12]
            self._token_val <<= self._token[11:0]

        with self.comb:
            # Accept input bytes only while we have not assembled a complete token.
            skid_out_ready <<= (self._token_valid == 0)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._byte_reg <<= 0
                self._has_byte <<= 0
                self._token <<= 0
                self._token_valid <<= 0
                self._zz_idx <<= 0
                self._run_cnt <<= 0
                self._block_done <<= 0
                self._coeff_out_reg <<= 0
                self._coeff_valid_reg <<= 0
                self._block_valid_reg <<= 0
            with Else():
                self._coeff_valid_reg <<= 0
                self._block_valid_reg <<= 0

                # Byte assembly.
                with If(self._token_valid == 0):
                    with If(self._has_byte == 0):
                        with If(skid_out_valid == 1):
                            self._byte_reg <<= skid_out_data
                            self._has_byte <<= 1
                    with Else():
                        with If(skid_out_valid == 1):
                            self._token <<= Cat(skid_out_data, self._byte_reg)
                            self._token_valid <<= 1
                            self._has_byte <<= 0

                # Token decode / coefficient emission.
                with If(self._token_valid == 1):
                    with If(self._run_cnt > 0):
                        # Insert a run-length zero.
                        self._run_cnt <<= self._run_cnt - 1
                        self._coeff_out_reg <<= 0
                        self._coeff_valid_reg <<= 1
                        self._zz_idx <<= self._zz_idx + 1
                    with Else():
                        with If(self._token_run == 0xF):
                            # EOB: pad remainder of block with zeros.
                            self._coeff_out_reg <<= 0
                            self._coeff_valid_reg <<= 1
                            self._zz_idx <<= self._zz_idx + 1
                            remaining = 63 - self._zz_idx
                            self._run_cnt <<= remaining[3:0]
                        with Else():
                            self._run_cnt <<= self._token_run
                            self._coeff_out_reg <<= self._token_val
                            self._coeff_valid_reg <<= 1
                            self._zz_idx <<= self._zz_idx + 1
                            self._token_valid <<= 0

                # Detect block completion.
                with If(self._zz_idx == 64):
                    self._block_done <<= 1

                with If((self._block_done == 1) & (self.block_ready == 1)):
                    self._block_done <<= 0
                    self._zz_idx <<= 0
                    self._token_valid <<= 0

        with self.comb:
            self.coeff_out <<= self._coeff_out_reg
            self.coeff_valid <<= self._coeff_valid_reg
            self.block_valid <<= self._block_done


# ---------------------------------------------------------------------------
# Top-level JPEG decoder
# ---------------------------------------------------------------------------

class JpegDecoder(Module):
    """Top-level baseline JPEG decoder.

    Input:  AXI4-Stream byte slave (s_axis_*).
    Output: AXI4-Stream RGB pixel master (m_axis_*).  Each beat carries one
            24-bit pixel {R, G, B}; for grayscale images R=G=B.

    The decoder internally runs three stages:
      1. simplified RLE entropy decoder -> zig-zag coefficients
      2. de-quantization + zig-zag-to-raster reorder
      3. 8x8 2-D inverse DCT

    A small controller sequences one 8x8 block at a time.  Quantization tables
    are currently hard-coded to all-ones; an APB register-bank interface is
    reserved for future software configuration.
    """

    def __init__(self, name: str = "JpegDecoder"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI4-Stream slave input.
        self.s_axis_tdata = Input(8, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.s_axis_tlast = Input(1, "s_axis_tlast")

        # AXI4-Stream master output (RGB pixel).
        self.m_axis_tdata = Output(24, "m_axis_tdata")
        self.m_axis_tvalid = Output(1, "m_axis_tvalid")
        self.m_axis_tready = Input(1, "m_axis_tready")
        self.m_axis_tlast = Output(1, "m_axis_tlast")

        # Child instances.
        self._entropy = JpegEntropyDecoder(name="entropy")
        self._dequant = JpegDequantZigzag(name="dequant")
        self._idct = JpegIdct8x8(name="idct")

        # Internal handshake signals.
        self.e_coeff = Wire(12, "e_coeff", signed=True)
        self.e_coeff_valid = Wire(1, "e_coeff_valid")
        self.e_block_valid = Wire(1, "e_block_valid")
        self.e_block_ready = Wire(1, "e_block_ready")
        self.e_coeff_ready = Wire(1, "e_coeff_ready")

        self.dq_in_data = Wire(12, "dq_in_data", signed=True)
        self.dq_in_valid = Wire(1, "dq_in_valid")
        self.dq_in_ready = Wire(1, "dq_in_ready")
        self.dq_out_data = Wire(COEFF_WIDTH, "dq_out_data", signed=True)
        self.dq_out_valid = Wire(1, "dq_out_valid")
        self.dq_out_ready = Wire(1, "dq_out_ready")

        self.id_in_data = Wire(COEFF_WIDTH, "id_in_data", signed=True)
        self.id_in_valid = Wire(1, "id_in_valid")
        self.id_in_ready = Wire(1, "id_in_ready")
        self.id_out_data = Wire(PIXEL_WIDTH, "id_out_data")
        self.id_out_valid = Wire(1, "id_out_valid")
        self.id_out_ready = Wire(1, "id_out_ready")

        self.instantiate(
            self._entropy,
            "u_entropy",
            port_map={
                "clk": self.clk,
                "rst": self.rst,
                "s_axis_tdata": self.s_axis_tdata,
                "s_axis_tvalid": self.s_axis_tvalid,
                "s_axis_tready": self.s_axis_tready,
                "s_axis_tlast": self.s_axis_tlast,
                "coeff_out": self.e_coeff,
                "coeff_valid": self.e_coeff_valid,
                "coeff_ready": self.e_coeff_ready,
                "block_valid": self.e_block_valid,
                "block_ready": self.e_block_ready,
            },
        )

        self.instantiate(
            self._dequant,
            "u_dequant",
            port_map={
                "clk": self.clk,
                "rst": self.rst,
                "in_data": self.dq_in_data,
                "in_valid": self.dq_in_valid,
                "in_ready": self.dq_in_ready,
                "out_data": self.dq_out_data,
                "out_valid": self.dq_out_valid,
                "out_ready": self.dq_out_ready,
            },
        )

        self.instantiate(
            self._idct,
            "u_idct",
            port_map={
                "clk": self.clk,
                "rst": self.rst,
                "in_data": self.id_in_data,
                "in_valid": self.id_in_valid,
                "in_ready": self.id_in_ready,
                "out_data": self.id_out_data,
                "out_valid": self.id_out_valid,
                "out_ready": self.id_out_ready,
            },
        )

        # Controller state machine.
        self._state = Reg(2, "state")
        ST_IDLE = 0
        ST_RUN = 1
        ST_DONE = 2

        self._cnt = Reg(7, "cnt")
        self._m_axis_tdata_reg = Reg(24, "m_axis_tdata_reg")
        self._m_axis_tvalid_reg = Reg(1, "m_axis_tvalid_reg")
        self._m_axis_tlast_reg = Reg(1, "m_axis_tlast_reg")

        # Connections.
        with self.comb:
            self.dq_in_data <<= self.e_coeff
            self.dq_in_valid <<= self.e_coeff_valid
            self.e_coeff_ready <<= self.dq_in_ready

            self.id_in_data <<= self.dq_out_data
            self.id_in_valid <<= self.dq_out_valid
            self.dq_out_ready <<= self.id_in_ready

            self.id_out_ready <<= self.m_axis_tready

            # Acknowledge entropy block only in DONE state.
            self.e_block_ready <<= (self._state == ST_DONE)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= ST_IDLE
                self._cnt <<= 0
                self._m_axis_tdata_reg <<= 0
                self._m_axis_tvalid_reg <<= 0
                self._m_axis_tlast_reg <<= 0
            with Else():
                self._m_axis_tvalid_reg <<= 0
                self._m_axis_tlast_reg <<= 0

                with Switch(self._state) as sw:
                    with sw.case(ST_IDLE):
                        # Wait for the entropy decoder to finish one block.
                        with If(self.e_block_valid == 1):
                            self._state <<= ST_RUN
                            self._cnt <<= 0

                    with sw.case(ST_RUN):
                        # Pipeline is draining; collect iDCT pixels.
                        with If(self.id_out_valid == 1):
                            y = self.id_out_data
                            rgb = Cat(y, Cat(y, y))
                            self._m_axis_tdata_reg <<= rgb
                            self._m_axis_tvalid_reg <<= 1
                            with If(self._cnt == 63):
                                self._m_axis_tlast_reg <<= 1
                            self._cnt <<= self._cnt + 1
                            with If(self._cnt == 63):
                                self._state <<= ST_DONE

                    with sw.case(ST_DONE):
                        # Acknowledge entropy block and restart.
                        self._state <<= ST_IDLE

        with self.comb:
            self.m_axis_tdata <<= self._m_axis_tdata_reg
            self.m_axis_tvalid <<= self._m_axis_tvalid_reg
            self.m_axis_tlast <<= self._m_axis_tlast_reg
