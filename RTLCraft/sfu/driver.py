"""Streaming stimulus helpers for the fully pipelined FP16 SFU."""

from __future__ import annotations

import random
from typing import Any, Iterable, List, Sequence, Tuple

from .dsl import Fp16Sfu
from .reference import OP_COS, OP_RELU, OP_SIGMOID, OP_SIN, OP_TANH


ALL_OPS = (OP_RELU, OP_SIGMOID, OP_TANH, OP_SIN, OP_COS)


def _inputs(op: int, operand: int, *, in_valid: int, rst: int = 0, clk: int = 0) -> dict[str, int]:
    return {
        "clk": clk,
        "rst": rst,
        "in_valid": in_valid,
        "op": op & 0x7,
        "operand": operand & 0xFFFF,
    }


def reset_sim(sim: Any) -> None:
    sim.step(_inputs(0, 0, in_valid=0, rst=1))


def run_one(sim: Any, op: int, operand: int) -> int:
    sim.step(_inputs(op, operand, in_valid=1))
    out = {"result": 0, "out_valid": 0}
    for _ in range(Fp16Sfu.LATENCY + 2):
        out = sim.step(_inputs(0, 0, in_valid=0))
        if out.get("out_valid"):
            return int(out["result"])
    return int(out["result"])


def run_stream(sim: Any, cases: Sequence[Tuple[int, int]]) -> list[int]:
    results: list[int] = []
    for op, operand in cases:
        out = sim.step(_inputs(op, operand, in_valid=1))
        if out.get("out_valid"):
            results.append(int(out["result"]))
    max_drain = len(cases) + Fp16Sfu.LATENCY + 4
    for _ in range(max_drain):
        if len(results) == len(cases):
            break
        out = sim.step(_inputs(0, 0, in_valid=0))
        if out.get("out_valid"):
            results.append(int(out["result"]))
    if len(results) != len(cases):
        raise RuntimeError(f"expected {len(cases)} results, got {len(results)}")
    return results


def random_cases(rng: random.Random, count: int) -> Iterable[Tuple[int, int]]:
    for _ in range(count):
        yield rng.choice(ALL_OPS), rng.randrange(0, 1 << 16)


__all__ = ["ALL_OPS", "random_cases", "reset_sim", "run_one", "run_stream"]
