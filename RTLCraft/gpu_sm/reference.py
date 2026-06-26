"""Golden reference model for the compact GPU Streaming Multiprocessor (SM).

The reference mirrors the RTL timing: a 2-stage issue/execute pipeline with
unit-specific latencies and registered outputs.  It is used to compute expected
writeback transactions for directed tests, streaming tests, and iverilog cosim.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Mapping, Sequence, Tuple

# ---------------------------------------------------------------------------
# Architecture parameters
# ---------------------------------------------------------------------------

NUM_WARPS = 2
LANES = 4
REGS_PER_WARP = 16
DATA_WIDTH = 16
LANE_MASK = (1 << DATA_WIDTH) - 1
REG_WORD_WIDTH = LANES * DATA_WIDTH
SHARED_MEM_SIZE = 256
INSTR_WIDTH = 32

WARP_ID_W = max((NUM_WARPS - 1).bit_length(), 1)
REG_ADDR_W = max((REGS_PER_WARP - 1).bit_length(), 1)
SHARED_ADDR_W = max((SHARED_MEM_SIZE - 1).bit_length(), 1)

# ---------------------------------------------------------------------------
# Instruction encoding
# ---------------------------------------------------------------------------

OP_NOP = 0
OP_SIMD_ADD = 1
OP_SIMD_SUB = 2
OP_SIMD_MUL = 3
OP_SIMD_AND = 4
OP_SIMD_OR = 5
OP_SIMD_XOR = 6
OP_SFU_RSQRT = 7
OP_GEMM_MATMUL = 8
OP_LOAD_IMM = 9
OP_LOAD_MEM = 10
OP_STORE_MEM = 11

SIMD_OPS = (OP_SIMD_ADD, OP_SIMD_SUB, OP_SIMD_MUL, OP_SIMD_AND, OP_SIMD_OR, OP_SIMD_XOR)
LONG_LATENCY_OPS = (OP_SFU_RSQRT, OP_GEMM_MATMUL)

OP_NAME = {
    OP_NOP: "NOP",
    OP_SIMD_ADD: "SIMD_ADD",
    OP_SIMD_SUB: "SIMD_SUB",
    OP_SIMD_MUL: "SIMD_MUL",
    OP_SIMD_AND: "SIMD_AND",
    OP_SIMD_OR: "SIMD_OR",
    OP_SIMD_XOR: "SIMD_XOR",
    OP_SFU_RSQRT: "SFU_RSQRT",
    OP_GEMM_MATMUL: "GEMM_MATMUL",
    OP_LOAD_IMM: "LOAD_IMM",
    OP_LOAD_MEM: "LOAD_MEM",
    OP_STORE_MEM: "STORE_MEM",
}


@dataclass(frozen=True)
class Instruction:
    """Decoded instruction."""

    opcode: int
    warp: int
    dst: int
    src0: int
    src1: int
    src2: int
    imm: int

    @staticmethod
    def encode(opcode: int, warp: int, dst: int, src0: int, src1: int, src2: int, imm: int) -> int:
        """Encode instruction to match the RTL DSL bit layout.

        [31:28] opcode, [27:26] warp_id, [25:22] dst, [21:18] src0,
        [17:14] src1, [13:10] src2, [9:0] imm.
        """
        value = 0
        value |= (opcode & 0xF) << 28
        value |= (warp & 0x3) << 26
        value |= (dst & ((1 << REG_ADDR_W) - 1)) << 22
        value |= (src0 & ((1 << REG_ADDR_W) - 1)) << 18
        value |= (src1 & ((1 << REG_ADDR_W) - 1)) << 14
        value |= (src2 & ((1 << REG_ADDR_W) - 1)) << 10
        value |= imm & 0x3FF
        return value & ((1 << INSTR_WIDTH) - 1)

    @classmethod
    def decode(cls, value: int) -> "Instruction":
        value &= (1 << INSTR_WIDTH) - 1
        opcode = (value >> 28) & 0xF
        warp = (value >> 26) & 0x3
        dst = (value >> 22) & ((1 << REG_ADDR_W) - 1)
        src0 = (value >> 18) & ((1 << REG_ADDR_W) - 1)
        src1 = (value >> 14) & ((1 << REG_ADDR_W) - 1)
        src2 = (value >> 10) & ((1 << REG_ADDR_W) - 1)
        imm = value & 0x3FF
        return cls(opcode, warp, dst, src0, src1, src2, imm)


# ---------------------------------------------------------------------------
# SFU helper: Q0.16 reciprocal-square-root LUT
# ---------------------------------------------------------------------------

SFU_LUT_SIZE = 64
SFU_LUT_ADDR_BITS = 6


def _build_rsqrt_lut(size: int = SFU_LUT_SIZE) -> Tuple[int, ...]:
    """Build a direct 1/sqrt(x) LUT for 16-bit unsigned Q0.16 inputs.

    Index = top SFU_LUT_ADDR_BITS bits of the input (treated as a fraction in
    [0,1)).  For index 0 (input near zero) we clamp to the maximum output.
    Output is a 16-bit unsigned Q0.16 value.
    """
    table: List[int] = []
    for idx in range(size):
        if idx == 0:
            table.append(0xFFFF)
            continue
        # midpoint of the bucket
        x_q16 = int(round((idx + 0.5) / size * (1 << 16)))
        val = 1.0 / math.sqrt(x_q16 / (1 << 16))
        val_q16 = int(round(val * (1 << 16)))
        table.append(max(0, min(val_q16, 0xFFFF)))
    return tuple(table)


SFU_RSQRT_LUT = _build_rsqrt_lut()


def rsqrt_q16(x: int) -> int:
    """Reference rsqrt for a single 16-bit unsigned lane."""
    x &= LANE_MASK
    if x == 0:
        return 0xFFFF
    idx = x >> (DATA_WIDTH - SFU_LUT_ADDR_BITS)
    return SFU_RSQRT_LUT[idx]


# ---------------------------------------------------------------------------
# Reference simulator
# ---------------------------------------------------------------------------

@dataclass
class WritebackEvent:
    """One register-file writeback event."""

    warp: int
    reg: int
    data: int  # 64-bit concatenation of 4 lanes


@dataclass
class SmState:
    """Reference SM architectural state."""

    warp_pc: List[int] = field(default_factory=lambda: [0] * NUM_WARPS)
    warp_busy: List[int] = field(default_factory=lambda: [0] * NUM_WARPS)
    warp_active: List[int] = field(default_factory=lambda: [1] * NUM_WARPS)
    reg_file: List[List[int]] = field(
        default_factory=lambda: [[0] * REGS_PER_WARP for _ in range(NUM_WARPS)]
    )
    shared_mem: List[int] = field(default_factory=lambda: [0] * SHARED_MEM_SIZE)


class GpuSmRef:
    """Cycle-accurate reference model for GpuSm.

    The pipeline timing matches the RTL:
      * issue stage captures a valid instruction and reads its operands
      * execute stage (one cycle later) computes the result
      * SIMD/LOAD/STORE write back in the execute cycle
      * SFU_RSQRT and GEMM_MATMUL have a 4-cycle pipelined latency; like the
        RTL, the reference produces a registered "preview" output in the
        execute cycle and performs the actual register-file writeback when
        the unit pipeline retires
      * outputs (out_valid/out_warp/out_reg/out_data) are registered, so
        they appear one cycle after issue
      * a warp is considered busy for the whole duration of a long-latency
        operation and can re-issue only in the cycle after writeback
    """

    SIMD_LATENCY = 1
    LOAD_LATENCY = 1
    SFU_LATENCY = 4
    GEMM_LATENCY = 4

    def __init__(self) -> None:
        self.state = SmState()
        self._issue_q: List[Tuple[Instruction, int, int]] = []
        # Outstanding long-latency operations: list of (cycles_left, event)
        self._outstanding: List[Tuple[int, WritebackEvent]] = []
        # Registered output (one-cycle delay to match RTL)
        self._out_valid_reg = 0
        self._out_warp_reg = 0
        self._out_reg_reg = 0
        self._out_data_reg = 0

    def _read_reg(self, warp: int, addr: int) -> int:
        return self.state.reg_file[warp][addr % REGS_PER_WARP]

    def _write_reg(self, warp: int, addr: int, data: int) -> None:
        self.state.reg_file[warp][addr % REGS_PER_WARP] = data & ((1 << REG_WORD_WIDTH) - 1)

    def _extract_lane(self, word: int, lane: int) -> int:
        return (word >> (lane * DATA_WIDTH)) & LANE_MASK

    def _pack_lanes(self, lanes: Sequence[int]) -> int:
        word = 0
        for i, value in enumerate(lanes):
            word |= (value & LANE_MASK) << (i * DATA_WIDTH)
        return word

    def _apply_simd(self, op: int, a_word: int, b_word: int) -> int:
        lanes: List[int] = []
        for lane in range(LANES):
            a = self._extract_lane(a_word, lane)
            b = self._extract_lane(b_word, lane)
            if op == OP_SIMD_ADD:
                r = (a + b) & LANE_MASK
            elif op == OP_SIMD_SUB:
                r = (a - b) & LANE_MASK
            elif op == OP_SIMD_MUL:
                r = (a * b) & LANE_MASK
            elif op == OP_SIMD_AND:
                r = a & b
            elif op == OP_SIMD_OR:
                r = a | b
            elif op == OP_SIMD_XOR:
                r = a ^ b
            else:
                r = 0
            lanes.append(r)
        return self._pack_lanes(lanes)

    def _apply_gemm(self, a_word: int, b_word: int) -> int:
        """2x2 matrix multiply C = A * B.

        Lanes are laid out as [A00, A01, A10, A11] and [B00, B01, B10, B11].
        """
        a = [self._extract_lane(a_word, i) for i in range(LANES)]
        b = [self._extract_lane(b_word, i) for i in range(LANES)]
        products = [
            (a[0] * b[0], a[1] * b[2]),  # C00
            (a[0] * b[1], a[1] * b[3]),  # C01
            (a[2] * b[0], a[3] * b[2]),  # C10
            (a[2] * b[1], a[3] * b[3]),  # C11
        ]
        lanes = [((p0 + p1) >> 8) & LANE_MASK for p0, p1 in products]
        return self._pack_lanes(lanes)

    def _apply_sfu(self, a_word: int) -> int:
        lanes = [rsqrt_q16(self._extract_lane(a_word, i)) for i in range(LANES)]
        return self._pack_lanes(lanes)

    def _decode(self, instr: int) -> Instruction:
        return Instruction.decode(instr)

    def _select_warp(self, requested: int) -> int:
        warp = requested % NUM_WARPS
        if self.state.warp_active[warp] and self.state.warp_busy[warp] == 0:
            return warp
        return -1

    def _latency_for_op(self, op: int) -> int:
        if op in LONG_LATENCY_OPS:
            return self.SFU_LATENCY
        return self.SIMD_LATENCY

    def predict(self, inputs: Mapping[str, int]) -> dict[str, int]:
        """UVM-style predictor wrapper around step()."""
        return self.step(inputs)

    def step(self, inputs: dict[str, int] | int, instr: int | None = None) -> dict[str, int]:
        """Advance one cycle.  Returns a dict matching the RTL output ports.

        Accepts either a dict (matching simulator convention) or the legacy
        positional (instr_valid, instr) form for convenience.
        """
        if isinstance(inputs, dict):
            instr_valid = int(inputs.get("instr_valid", 0))
            instr = int(inputs.get("instr", 0))
        else:
            instr_valid = int(inputs)
            instr = int(instr or 0)
        out_valid = self._out_valid_reg
        out_warp = self._out_warp_reg
        out_reg = self._out_reg_reg
        out_data = self._out_data_reg

        # Prepare next output register value from this cycle's writeback events.
        next_out_valid = 0
        next_out_warp = 0
        next_out_reg = 0
        next_out_data = 0

        # Step A: decrement outstanding long-latency operations and commit
        # those whose timer has reached zero.  Only the register file is
        # updated here; the preview output was already produced in the
        # execute cycle (Step B) to match the RTL's registered out_valid.
        busy_clear_flags = [False] * NUM_WARPS
        still_outstanding: List[Tuple[int, WritebackEvent]] = []
        for cycles_left, event in self._outstanding:
            if cycles_left <= 1:
                self._write_reg(event.warp, event.reg, event.data)
                busy_clear_flags[event.warp] = True
            else:
                still_outstanding.append((cycles_left - 1, event))
        self._outstanding = still_outstanding

        # Step B: execute whatever was issued last cycle.
        if self._issue_q:
            issued, a_word, b_word = self._issue_q.pop(0)
            op = issued.opcode
            if op in SIMD_OPS or op == OP_LOAD_IMM or op == OP_LOAD_MEM:
                if op in SIMD_OPS:
                    data = self._apply_simd(op, a_word, b_word)
                elif op == OP_LOAD_IMM:
                    imm16 = issued.imm & LANE_MASK
                    data = self._pack_lanes([imm16] * LANES)
                else:  # LOAD_MEM
                    addr = (issued.src0 + issued.imm) % SHARED_MEM_SIZE
                    mem_word = self.state.shared_mem[addr]
                    data = self._pack_lanes([mem_word & LANE_MASK] * LANES)
                self._write_reg(issued.warp, issued.dst, data)
                next_out_valid = 1
                next_out_warp = issued.warp
                next_out_reg = issued.dst
                next_out_data = data
                busy_clear_flags[issued.warp] = True
            elif op == OP_STORE_MEM:
                addr = (issued.src0 + issued.imm) % SHARED_MEM_SIZE
                self.state.shared_mem[addr] = self._extract_lane(b_word, 0)
                busy_clear_flags[issued.warp] = True
            elif op == OP_SFU_RSQRT:
                data = self._apply_sfu(a_word)
                next_out_valid = 1
                next_out_warp = issued.warp
                next_out_reg = issued.dst
                next_out_data = data
                self._outstanding.append((self.SFU_LATENCY - 1, WritebackEvent(issued.warp, issued.dst, data)))
            elif op == OP_GEMM_MATMUL:
                data = self._apply_gemm(a_word, b_word)
                next_out_valid = 1
                next_out_warp = issued.warp
                next_out_reg = issued.dst
                next_out_data = data
                self._outstanding.append((self.GEMM_LATENCY - 1, WritebackEvent(issued.warp, issued.dst, data)))

        # Step C: issue a new instruction if valid and the requested warp is
        # not currently busy.  This uses the busy value from the start of the
        # cycle, before any clear from step A/B or decrement from step D.
        issued_warp = -1
        if instr_valid:
            inst = self._decode(instr)
            selected = self._select_warp(inst.warp)
            if selected >= 0:
                a_word = self._read_reg(selected, inst.src0)
                b_word = self._read_reg(selected, inst.src1)
                self._issue_q.append((inst, a_word, b_word))
                issued_warp = selected

        # Step D: update warp busy counters for the next cycle.
        for w in range(NUM_WARPS):
            if issued_warp == w:
                self.state.warp_busy[w] = self._latency_for_op(self._issue_q[-1][0].opcode)
            elif busy_clear_flags[w]:
                self.state.warp_busy[w] = 0
            elif self.state.warp_busy[w] > 0:
                self.state.warp_busy[w] -= 1

        self._out_valid_reg = next_out_valid
        self._out_warp_reg = next_out_warp
        self._out_reg_reg = next_out_reg
        self._out_data_reg = next_out_data

        # Return the output that is visible at the end of this cycle, matching
        # the behavior of PythonSimulator/CompiledSimulator step().
        return {
            "out_valid": next_out_valid,
            "out_warp": next_out_warp,
            "out_reg": next_out_reg,
            "out_data": next_out_data,
        }

    def reset(self) -> None:
        self.state = SmState()
        self._issue_q.clear()
        self._outstanding.clear()
        self._out_valid_reg = 0
        self._out_warp_reg = 0
        self._out_reg_reg = 0
        self._out_data_reg = 0
