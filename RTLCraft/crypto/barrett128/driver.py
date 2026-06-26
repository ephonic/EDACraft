"""Stimulus / driver helpers for the fully-pipelined Barrett modular multiplier.

The DUT is fully pipelined with a fixed latency (``BarrettModMul.LATENCY``):
operands are accepted every cycle (``in_accept`` is always 1), and each result
emerges ``LATENCY`` cycles after its operands were presented, marked by
``out_valid``.

The redesigned rtlgen_x bundled simulator is RTL-faithful, so these helpers
work on it as well as on the compiled sim and (with cycle-accurate stimulus)
iverilog cosim.
"""

from __future__ import annotations

import random
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


def run_one(sim: Any, a: int, b: int, n: int, m: Optional[int] = None) -> int:
    """Drive a single operand set and return its result.

    Presents the operands for one cycle, then clocks until ``out_valid``
    asserts and returns ``r``. Self-calibrating to the unit's actual latency.
    """
    if m is None:
        m = barrett_constant(n)
    sim.step(_base_inputs(a, b, n, m, in_valid=1))
    for _ in range(BarrettModMul.LATENCY + 2):
        out = sim.step(_base_inputs(0, 0, 0, 0, in_valid=0))
        if out.get("out_valid"):
            return out["r"]
    return out["r"]


def run_stream(sim: Any, cases: List[Tuple[int, int, int, int]]) -> List[int]:
    """Drive a back-to-back stream of (a,b,n,m) cases through the pipe.

    Returns the results in input order. Each operand set is presented on a
    successive cycle (full throughput), then the pipe is drained by watching
    ``out_valid`` rather than by assuming fixed output slots.
    """
    results: List[int] = []
    for a, b, n, m in cases:
        out = sim.step(_base_inputs(a, b, n, m, in_valid=1))
        if out.get("out_valid"):
            results.append(out["r"])
    max_drain_steps = len(cases) + BarrettModMul.LATENCY + 4
    for _ in range(max_drain_steps):
        if len(results) == len(cases):
            break
        out = sim.step(_base_inputs(0, 0, 0, 0, in_valid=0))
        if out.get("out_valid"):
            results.append(out["r"])
    if len(results) != len(cases):
        raise RuntimeError(
            f"expected {len(cases)} streamed results, collected {len(results)}"
        )
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
