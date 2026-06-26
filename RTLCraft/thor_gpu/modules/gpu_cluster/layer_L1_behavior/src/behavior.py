"""L1 BehaviorIR model for the ThorCluster (GpuCluster).

Cycle-unaware functional reference for the 2-SM compute cluster with a
shared global memory port. Each SM runs the L1 SM functional model; the
cluster merges their global-memory effects and reports all_done.
"""

from __future__ import annotations

from typing import Any, Dict, List

from thor_gpu.modules.gpu_sm.layer_L1_behavior.src.behavior import sm_functional

NSM = 2


def cluster_functional(imems: List[List[int]]) -> Dict[str, Any]:
    """Run each SM to completion over its own IMEM, sharing one global memory.

    Returns ``{"sm_results": [...], "all_done": bool, "warp_acc": [[...], ...]}``.
    """
    gmem: Dict[int, int] = {}
    sm_results = []
    for i in range(NSM):
        res = sm_functional(imems[i], global_mem=gmem)
        sm_results.append(res)
    all_done = all(all(r["warp_done"]) for r in sm_results)
    return {
        "sm_results": sm_results,
        "all_done": all_done,
        "warp_acc": [r["warp_acc"] for r in sm_results],
        "global_mem": gmem,
    }


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorCluster",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "2-SM compute cluster with round-robin L2 arbiter (functional reference).",
        "nsm": NSM,
        "arbiter": "round-robin",
    }


__all__ = ["NSM", "cluster_functional", "describe"]
