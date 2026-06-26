"""L1 BehaviorIR model for the ThorLSU.

Cycle-unaware functional reference for the vector load/store unit. A load
returns the memory word at the requested address; a store commits the vector
word. The unit maps directly onto the memory interface.
"""

from __future__ import annotations

from typing import Any, Dict


def lsu_functional(mem: Dict[int, int], op: int, addr: int, wdata: int) -> Dict[str, int]:
    """One LSU access.

    ``op``: 0 = load, 1 = store. Returns ``{"rdata", "mem_req", "mem_wen", "mem_addr",
    "mem_wdata", "done"}``.
    """
    addr &= 0xFFFFFFFF
    if op == 1:  # store
        mem[addr] = wdata & ((1 << 256) - 1)
        return {"rdata": 0, "mem_req": 1, "mem_wen": 1, "mem_addr": addr,
                "mem_wdata": wdata, "done": 1}
    # load
    return {"rdata": mem.get(addr, 0), "mem_req": 1, "mem_wen": 0, "mem_addr": addr,
            "mem_wdata": 0, "done": 1}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorLSU",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Vector load/store unit functional reference (req/response handshake).",
        "data_width": 256,
        "addr_width": 32,
        "ops": "load(0), store(1)",
    }


__all__ = ["lsu_functional", "describe"]
