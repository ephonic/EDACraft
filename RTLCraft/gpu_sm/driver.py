"""Simulation helpers for the compact GPU SM.

The helpers here work with any object that exposes a ``step(inputs_dict)``
method returning an output dict, including:

* ``rtlgen_x.sim.PythonSimulator`` / ``CompiledSimulator``
* generated reference models
"""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple

from .dsl import GpuSm
from .reference import (
    DATA_WIDTH,
    INSTR_WIDTH,
    Instruction,
    OP_GEMM_MATMUL,
    OP_LOAD_IMM,
    OP_LOAD_MEM,
    OP_SIMD_ADD,
    OP_SIMD_AND,
    OP_SIMD_MUL,
    OP_SIMD_OR,
    OP_SIMD_SUB,
    OP_SIMD_XOR,
    OP_SFU_RSQRT,
    OP_STORE_MEM,
    SIMD_OPS,
)


def _inputs(
    instr_valid: int = 0,
    instr: int = 0,
    rst: int = 0,
    clk: int = 0,
) -> dict[str, int]:
    return {
        "clk": clk,
        "rst": rst,
        "instr_valid": instr_valid,
        "instr": instr & ((1 << INSTR_WIDTH) - 1),
    }


def reset_sim(sim: Any) -> None:
    """Apply a synchronous reset sequence."""
    sim.step(_inputs(rst=1))
    sim.step(_inputs())


def issue_one(sim: Any, instr: int) -> dict[str, int]:
    """Issue a single instruction and return the output of that cycle."""
    return sim.step(_inputs(instr_valid=1, instr=instr))


def run_program(
    sim: Any,
    program: Sequence[Tuple[int, int]],
    *,
    drain_cycles: int | None = None,
) -> List[dict[str, int]]:
    """Run a list of (instr_valid, instr) tuples and collect outputs.

    If ``drain_cycles`` is None, a safe default based on the program length is
    used so that long-latency operations have time to retire.
    """
    outputs: List[dict[str, int]] = []
    for valid, instr in program:
        outputs.append(sim.step(_inputs(instr_valid=valid, instr=instr)))
    eff_drain = drain_cycles if drain_cycles is not None else len(program) + GpuSm.SFU_LATENCY + 4
    for _ in range(eff_drain):
        outputs.append(sim.step(_inputs()))
    return outputs


def collect_writebacks(outputs: Sequence[dict[str, int]]) -> List[Tuple[int, int, int]]:
    """Filter output trace to only cycles where ``out_valid`` is high.

    Returns a list of (warp, reg, data) tuples.
    """
    results: List[Tuple[int, int, int]] = []
    for out in outputs:
        if int(out.get("out_valid", 0)):
            results.append((int(out.get("out_warp", 0)), int(out.get("out_reg", 0)), int(out.get("out_data", 0))))
    return results


# ---------------------------------------------------------------------------
# Small instruction builders
# ---------------------------------------------------------------------------


def load_imm(warp: int, dst: int, imm: int) -> int:
    return Instruction.encode(OP_LOAD_IMM, warp, dst, 0, 0, 0, imm)


def simd(opcode: int, warp: int, dst: int, src0: int, src1: int) -> int:
    return Instruction.encode(opcode, warp, dst, src0, src1, 0, 0)


def sfu_rsqrt(warp: int, dst: int, src0: int) -> int:
    return Instruction.encode(OP_SFU_RSQRT, warp, dst, src0, 0, 0, 0)


def gemm_matmul(warp: int, dst: int, src_a: int, src_b: int) -> int:
    return Instruction.encode(OP_GEMM_MATMUL, warp, dst, src_a, src_b, 0, 0)


def load_mem(warp: int, dst: int, base_reg: int, offset: int) -> int:
    return Instruction.encode(OP_LOAD_MEM, warp, dst, base_reg, 0, 0, offset)


def store_mem(warp: int, base_reg: int, data_reg: int, offset: int) -> int:
    return Instruction.encode(OP_STORE_MEM, warp, 0, base_reg, data_reg, 0, offset)


# ---------------------------------------------------------------------------
# Reference-program builders
# ---------------------------------------------------------------------------


def directed_program() -> List[Tuple[int, int]]:
    """Return a small deterministic program covering SIMD, GEMM, and LOAD/STORE.

    Uses warp 0 and inserts NOPs so that no warp is issued while it is still
    busy.  This mirrors the behavior of a scoreboard-stalled in-order SM.
    """
    prog: List[Tuple[int, int]] = []

    def issue(instr: int):
        prog.append((1, instr))

    def nop(count: int = 1):
        for _ in range(count):
            prog.append((0, 0))

    # SIMD add: reg3 = reg1 + reg2  (after loading 5 and 7)
    issue(load_imm(0, 1, 5))
    nop()
    issue(load_imm(0, 2, 7))
    nop()
    issue(simd(OP_SIMD_ADD, 0, 3, 1, 2))
    nop()

    # SIMD mul: reg4 = reg1 * reg2
    issue(simd(OP_SIMD_MUL, 0, 4, 1, 2))
    nop()

    # SIMD sub/and/or/xor on different regs
    issue(simd(OP_SIMD_SUB, 0, 5, 2, 1))
    nop()
    issue(simd(OP_SIMD_AND, 0, 6, 5, 1))
    nop()
    issue(simd(OP_SIMD_OR, 0, 7, 5, 1))
    nop()
    issue(simd(OP_SIMD_XOR, 0, 8, 5, 1))
    nop()

    # GEMM: reg10 = reg3 (as A) * reg3 (as B)
    issue(gemm_matmul(0, 10, 3, 3))
    nop(GpuSm.GEMM_LATENCY)

    # SFU rsqrt: reg13 = 1/sqrt(reg4)
    issue(sfu_rsqrt(0, 13, 4))
    nop(GpuSm.SFU_LATENCY)

    # Store lane-0 of reg4 to shared memory address 8, then load it back to reg11
    issue(store_mem(0, 0, 4, 8))
    nop()
    issue(load_mem(0, 11, 0, 8))
    nop()

    return prog


def random_program(rng: Any, count: int) -> List[Tuple[int, int]]:
    """Return a random program with one instruction every other cycle.

    This avoids structural stalls so the expected writeback stream is simply
    every other output cycle.
    """
    prog: List[Tuple[int, int]] = []
    opcodes = [OP_SIMD_ADD, OP_SIMD_SUB, OP_SIMD_MUL, OP_SIMD_AND, OP_SIMD_OR, OP_SIMD_XOR]
    for _ in range(count):
        op = rng.choice(opcodes)
        warp = rng.randrange(2)
        dst = rng.randrange(1, 16)
        src0 = rng.randrange(16)
        src1 = rng.randrange(16)
        prog.append((1, simd(op, warp, dst, src0, src1)))
        prog.append((0, 0))
    return prog


__all__ = [
    "reset_sim",
    "issue_one",
    "run_program",
    "collect_writebacks",
    "load_imm",
    "simd",
    "sfu_rsqrt",
    "gemm_matmul",
    "load_mem",
    "store_mem",
    "directed_program",
    "random_program",
]
