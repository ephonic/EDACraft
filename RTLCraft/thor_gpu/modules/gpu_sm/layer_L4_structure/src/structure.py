"""L4 StructuralIR for the ThorGpuSM module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class GpuSMStructure:
    name: str = "ThorGpuSM"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock("warp_scheduler", "Sticky-RR scheduler and barrier sync.", ["warp_sel", "warp_pc"]),
        SubBlock("imem", "32-entry instruction memory (host-writable).", ["imem_wr_*", "inst"]),
        SubBlock("vrf", "Vector register file (8 regs x 4 warps x 256b).", ["vrf_*", "operands"]),
        SubBlock("decode", "Decode the current instruction into controls.", ["inst", "opcode", "rd", "rs1", "rs2", "imm"]),
        SubBlock("vALU", "8-lane INT32 ALU for VADD/VMUL.", ["operands", "alu_fn", "result"]),
        SubBlock("vmac_acc", "64-bit per-warp VMAC accumulator.", ["lane0_products", "warp_acc"]),
        SubBlock("lsu", "Vector load/store unit.", ["op", "addr", "mem_*"]),
        SubBlock("shared_memory", "Per-SM shared SRAM.", ["addr", "wdata", "rdata"]),
    ])


STRUCTURE = GpuSMStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into scheduler, IMEM, VRF, decode, ALU, VMAC, LSU, shared memory.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["imem_write", "global_memory", "sm_done"],
    }


__all__ = ["SubBlock", "GpuSMStructure", "STRUCTURE", "describe"]
