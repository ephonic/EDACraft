"""L1 BehaviorIR model for the ThorSIMTStack.

Cycle-unaware functional reference for the SIMT divergence/reconvergence
stack. On a divergent branch the stack records the not-taken mask and the
reconvergence PC; when the active path converges (or pops), control returns
to the recorded PC with the recorded mask.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def simt_push(stack: List[Tuple[int, int]], reconverge_pc: int, not_taken_mask: int) -> None:
    """Push a (reconverge_pc, not_taken_mask) frame onto the SIMT stack."""
    stack.append((reconverge_pc & 0xFFFFFFFF, not_taken_mask & 0xFF))


def simt_pop(stack: List[Tuple[int, int]]) -> Tuple[int, int]:
    """Pop the top frame; return (reconverge_pc, mask). Empty stack -> (0,0)."""
    if not stack:
        return (0, 0)
    return stack.pop()


def simt_functional(stack: List[Tuple[int, int]], push: int, pop: int,
                    branch_pc: int, reconverge_pc: int,
                    taken_mask: int, active_mask: int) -> Dict[str, int]:
    """One SIMT stack operation.

    On ``push``: the not-taken lanes (active & ~taken) are saved with the
    reconvergence PC; the result carries the taken path (active & taken).
    On ``pop``: control resumes at the saved PC with the saved mask.
    Returns ``{"next_pc", "next_mask", "stack_depth"}``.
    """
    if push:
        not_taken = active_mask & (~taken_mask & 0xFF)
        simt_push(stack, reconverge_pc, not_taken)
        return {"next_pc": branch_pc, "next_mask": active_mask & taken_mask,
                "stack_depth": len(stack)}
    if pop:
        rpc, rmask = simt_pop(stack)
        return {"next_pc": rpc, "next_mask": rmask, "stack_depth": len(stack)}
    return {"next_pc": 0, "next_mask": active_mask, "stack_depth": len(stack)}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorSIMTStack",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "SIMT divergence/reconvergence stack functional reference.",
        "mask_width": 8,
        "max_depth": 8,
        "frame_fields": "reconverge_pc, not_taken_mask",
    }


__all__ = ["simt_push", "simt_pop", "simt_functional", "describe"]
