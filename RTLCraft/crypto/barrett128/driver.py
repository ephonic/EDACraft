"""Stimulus / driver helpers for the fully-pipelined Barrett modular multiplier.

The DUT is fully pipelined with a fixed latency (``BarrettModMul.LATENCY``):
operands are accepted every cycle (``in_accept`` is always 1), and each result
emerges ``LATENCY`` cycles after its operands were presented.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .dsl import BarrettModMul
from .reference import K, barrett_constant


def _base_inputs(a: int, b: int, n: int, m: int, in_valid: int = 1,
                 clk: int = 0, rst: int = 0) -> Dict[str, int]:
    return {"clk": clk, "rst": rst, "in_valid": in_valid,
            "a": a & ((1 << K) - 1), "b": b & ((1 << K) - 1),
            "n": n & ((1 << K) - 1), "m": m & ((1 << (K + 1)) - 1)}


def reset_sim(sim: Any) -> None:
    """Hold the DUT in reset for one cycle then deassert."""
    sim.step(_base_inputs(0, 0, 0, 0, in_valid=0, rst=1))


def run_one(sim: Any, a: int, b: int, n: int, m: Optional[int] = None,
            max_cycles: int = 16) -> int:
    """Drive a single operand set and return its result.

    Presents the operands with in_valid=1 and returns the combinational result
    observed in the same cycle (latency 0). Falls back to polling out_valid if
    the unit exposes a non-zero latency.
    """
    if m is None:
        m = barrett_constant(n)
    out = sim.step(_base_inputs(a, b, n, m, in_valid=1))
    if BarrettModMul.LATENCY == 0:
        return out["r"]
    for _ in range(max_cycles):
        out = sim.step(_base_inputs(0, 0, 0, 0, in_valid=0))
        if out.get("out_valid"):
            return out["r"]
    return out["r"]


def run_stream(sim: Any, cases: List[Tuple[int, int, int, int]]) -> List[int]:
    """Drive a back-to-back stream of (a,b,n,m) cases through the pipe.

    Returns the results in input order. Each operand set is presented on a
    successive cycle (full throughput); with latency 1 the result for operand i
    is the output of the following cycle.
    """
    latency = BarrettModMul.LATENCY
    results: List[int] = [0] * len(cases)
    outputs: List[Dict[str, int]] = []
    for a, b, n, m in cases:
        outputs.append(sim.step(_base_inputs(a, b, n, m, in_valid=1)))
    for _ in range(latency + 1):
        outputs.append(sim.step(_base_inputs(0, 0, 0, 0, in_valid=0)))
    for i in range(len(cases)):
        # result[i] is the output `latency` cycles after presenting operand i.
        results[i] = outputs[min(i + latency, len(outputs) - 1)]["r"]
    return results


def random_cases(rng: random.Random, count: int, n: Optional[int] = None
                 ) -> Iterable[Tuple[int, int, int, int]]:
    """Yield ``(a, b, n, m)`` random cases with a full 128-bit modulus.

    When ``n`` is None, a fresh random full-width modulus is drawn per case
    (high bit set), satisfying the Barrett precondition.
    """
    for _ in range(count):
        modulus = n if n is not None else (rng.getrandbits(K - 1) | (1 << (K - 1)))
        a = rng.getrandbits(K)
        b = rng.getrandbits(K)
        m = barrett_constant(modulus)
        yield a, b, modulus, m


__all__ = ["reset_sim", "run_one", "run_stream", "random_cases"]
