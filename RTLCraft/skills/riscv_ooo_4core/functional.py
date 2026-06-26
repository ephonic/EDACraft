"""
skills.riscv_ooo_4core.functional — Layer 1: Functional Models
"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional

def ooo_core_functional(**kwargs) -> Callable:
    def func(instr: int = 0x00000013, pc: int = 0x1000,
             regfile: Optional[Dict[int, int]] = None) -> Dict:
        rf = regfile or {}
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct3 = (instr >> 12) & 0x7
        funct7 = (instr >> 25) & 0x7F
        imm_i = (instr >> 20) & 0xFFF
        if imm_i & 0x800:
            imm_i |= ~0xFFF
        result = pc + 4
        write_reg = False
        if opcode == 0x13:
            if funct3 == 0:
                result = rf.get(rs1, 0) + imm_i
                write_reg = True
        elif opcode == 0x33:
            a, b = rf.get(rs1, 0), rf.get(rs2, 0)
            if funct3 == 0 and funct7 == 0:
                result = a + b; write_reg = True
            elif funct3 == 0 and funct7 == 0x20:
                result = a - b; write_reg = True
        elif opcode == 0x03:
            result = 0; write_reg = True
        elif opcode == 0x23:
            pass
        return {"next_pc": pc + 4, "result": result,
                "rd": rd if write_reg else 0, "write_reg": write_reg, "retire": True}
    return func

def l1_cache_functional(**kwargs) -> Callable:
    def func(addr: int, tag_array: dict, data_array: dict,
             valid_array: dict, mesi_state: dict) -> Dict:
        idx = (addr >> 6) & 0x3F
        tag = addr >> 12
        hit = valid_array.get(idx, False) and tag_array.get(idx) == tag
        mesi = mesi_state.get(idx, "I")
        return {"hit": hit, "rdata": data_array.get(idx, {}).get(tag, 0) if hit else 0,
                "miss": not hit, "mesi": mesi}
    return func

def coherence_bus_functional(**kwargs) -> Callable:
    def func(snoop_addr: int, request_type: str,
             core_id: int, mesi_states: Dict[int, str]) -> Dict:
        actions = {}
        for cid, state in mesi_states.items():
            if state == "M" and request_type in ("read", "invalidate"):
                actions[cid] = "writeback"
            elif state == "S" and request_type == "invalidate":
                actions[cid] = "invalidate"
            else:
                actions[cid] = "none"
        return {"actions": actions, "shared": "S" in mesi_states.values()}
    return func

# =====================================================================
# Layer 2: Cycle-Level Models
# =====================================================================