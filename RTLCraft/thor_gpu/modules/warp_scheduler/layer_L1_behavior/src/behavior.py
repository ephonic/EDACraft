"""L1 BehaviorIR model for the ThorWarpScheduler.

Cycle-unaware functional reference for the sticky round-robin warp scheduler
and barrier-synchronization unit. The scheduler advances ``warp_sel`` only
when the currently selected warp is idle (IDLE/DONE/BARRIER). A warp reaches
the barrier state via ``warp_at_barrier``; the barrier releases when every
warp is either at the barrier or done.
"""

from __future__ import annotations

from typing import Any, Dict

NWARP = 4


def scheduler_step(warp_sel: int, warp_idle: int, warp_done: int,
                   warp_at_barrier: int, start: int = 0) -> Dict[str, int]:
    """Compute one scheduler decision.

    Returns ``{"warp_sel", "barrier_release", "sm_done"}``.
    - ``warp_sel``: next selected warp (sticky: advance only when current is idle).
    - ``barrier_release``: 1 when all warps are at-barrier or done.
    - ``sm_done``: 1 when all warps are done.
    """
    sm_done = 1
    for w in range(NWARP):
        if not ((warp_done >> w) & 1):
            sm_done = 0
            break

    barrier_release = 1
    for w in range(NWARP):
        at = ((warp_at_barrier >> w) & 1) or ((warp_done >> w) & 1)
        if not at:
            barrier_release = 0
            break

    # Sticky round-robin: advance only when the currently selected warp is idle.
    cur_idle = (warp_idle >> warp_sel) & 1
    if cur_idle:
        next_sel = (warp_sel + 1) % NWARP
    else:
        next_sel = warp_sel

    return {"warp_sel": next_sel, "barrier_release": barrier_release, "sm_done": sm_done}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorWarpScheduler",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Sticky round-robin warp scheduler with barrier synchronization.",
        "num_warps": NWARP,
        "policy": "sticky round-robin (advance when current warp idle)",
    }


__all__ = ["NWARP", "scheduler_step", "describe"]
