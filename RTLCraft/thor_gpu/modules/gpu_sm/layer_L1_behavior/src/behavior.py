"""L1 BehaviorIR model for the ThorGpuSM.

Cycle-unaware functional reference for one streaming multiprocessor. The model
takes an instruction memory (list of 32-bit encoded instructions), a per-warp
starting PC, and executes each warp to completion using the Thor ISA, returning
the final VRF state and per-warp accumulators.
"""

from __future__ import annotations

from typing import Any, Dict, List

from thor_gpu.modules.common.utils import _to_u32, _to_s32, _unpack_u32_lanes, _pack_u32_lanes

XLEN = 32
NLANE = 8
VLEN = XLEN * NLANE  # 256
VREGS = 8
NWARP = 4
IMEM_DEPTH = 32
ACCW = 64

# Opcodes (inst[31:28])
OP_NOP = 0x0
OP_VLOAD = 0x1
OP_VSTORE = 0x2
OP_VADD = 0x3
OP_VMUL = 0x4
OP_VMAC = 0x5
OP_BARRIER = 0x6
OP_SLOAD = 0x7
OP_DONE = 0xF


def _decode(inst: int) -> Dict[str, int]:
    return {
        "opcode": (inst >> 28) & 0xF,
        "rd": (inst >> 24) & 0xF,
        "rs1": (inst >> 20) & 0xF,
        "rs2": (inst >> 16) & 0xF,
        "imm": inst & 0xFFFF,
    }


def _sext16(imm: int) -> int:
    """Sign-extend a 16-bit immediate to a Python signed int."""
    imm &= 0xFFFF
    return imm - 0x10000 if imm & 0x8000 else imm


def sm_functional(imem: List[int], start_pc: int = 0,
                  global_mem: Dict[int, int] = None) -> Dict[str, Any]:
    """Execute all warps of one SM to completion.

    Returns ``{"vrf": <list of 256-bit words>, "warp_acc": <list of ints>,
               "warp_done": <list of bools>}``.
    """
    gmem = global_mem if global_mem is not None else {}
    vrf = [0] * (VREGS * NWARP)
    warp_pc = [start_pc] * NWARP
    warp_done = [False] * NWARP
    warp_acc = [0] * NWARP
    barrier_mask = [False] * NWARP
    steps = 0
    MAX_STEPS = 100000

    while steps < MAX_STEPS:
        steps += 1
        if all(warp_done):
            break
        # Barrier release check.
        all_blocked = all(barrier_mask[w] or warp_done[w] for w in range(NWARP))
        if all_blocked:
            for w in range(NWARP):
                barrier_mask[w] = False
        # Round-robin one step per warp.
        progressed = False
        for w in range(NWARP):
            if warp_done[w] or barrier_mask[w]:
                continue
            pc = warp_pc[w]
            if pc >= len(imem):
                warp_done[w] = True
                continue
            d = _decode(imem[pc])
            base = w * VREGS
            op = d["opcode"]
            if op == OP_NOP:
                warp_pc[w] = pc + 1
            elif op == OP_SLOAD:
                vrf[base + d["rd"]] = _pack_u32_lanes([_to_u32(_sext16(d["imm"]))] * NLANE)
                warp_pc[w] = pc + 1
            elif op == OP_VADD:
                a = _unpack_u32_lanes(vrf[base + d["rs1"]])
                b = _unpack_u32_lanes(vrf[base + d["rs2"]])
                vrf[base + d["rd"]] = _pack_u32_lanes([_to_u32(_to_s32(x) + _to_s32(y)) for x, y in zip(a, b)])
                warp_pc[w] = pc + 1
            elif op == OP_VMUL:
                a = _unpack_u32_lanes(vrf[base + d["rs1"]])
                b = _unpack_u32_lanes(vrf[base + d["rs2"]])
                vrf[base + d["rd"]] = _pack_u32_lanes([_to_u32(_to_s32(x) * _to_s32(y)) for x, y in zip(a, b)])
                warp_pc[w] = pc + 1
            elif op == OP_VMAC:
                a0 = _to_s32(_unpack_u32_lanes(vrf[base + d["rs1"]])[0])
                b0 = _to_s32(_unpack_u32_lanes(vrf[base + d["rs2"]])[0])
                warp_acc[w] = (warp_acc[w] + a0 * b0) & ((1 << ACCW) - 1)
                warp_pc[w] = pc + 1
            elif op == OP_VLOAD:
                vrf[base + d["rd"]] = gmem.get(d["imm"], 0)
                warp_pc[w] = pc + 1
            elif op == OP_VSTORE:
                gmem[d["imm"]] = vrf[base + d["rd"]]
                warp_pc[w] = pc + 1
            elif op == OP_BARRIER:
                barrier_mask[w] = True
                warp_pc[w] = pc + 1
            elif op == OP_DONE:
                warp_done[w] = True
            else:
                warp_pc[w] = pc + 1
            progressed = True
        if not progressed and not all_blocked:
            break  # deadlock guard

    return {"vrf": vrf, "warp_acc": warp_acc, "warp_done": warp_done, "global_mem": gmem}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorGpuSM",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Functional reference for one SM: 4 warps x 8 lanes, Thor ISA.",
        "xlen": XLEN, "nlane": NLANE, "vlen": VLEN, "vregs": VREGS, "nwarp": NWARP,
        "imem_depth": IMEM_DEPTH, "accw": ACCW,
        "isa": "NOP/VLOAD/VSTORE/VADD/VMUL/VMAC/BARRIER/SLOAD/DONE",
    }


__all__ = [
    "XLEN", "NLANE", "VLEN", "VREGS", "NWARP", "IMEM_DEPTH", "ACCW",
    "OP_NOP", "OP_VLOAD", "OP_VSTORE", "OP_VADD", "OP_VMUL", "OP_VMAC",
    "OP_BARRIER", "OP_SLOAD", "OP_DONE",
    "sm_functional", "describe",
]
