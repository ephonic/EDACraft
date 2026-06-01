"""Behavior template registration for the skill_ppa pipeline.

Registers all cycle-level models with the TemplateRegistry
so the PPA pipeline can discover and analyze them.
"""

from rtlgen.behaviors import TemplateRegistry

from skills.riscv_ooo_7nm.functional import (
    ooo_core_functional,
    fetch_functional,
    bpredict_functional,
    rename_functional,
    rob_functional,
)
from skills.riscv_ooo_7nm.cycle_level import (
    fetch_stage_cycle,
    decode_stage_cycle,
    issue_queue_cycle,
    alu_exec_cycle,
    lsu_cycle,
    rob_cycle,
)


SKILL_MODULES = {
    "fetch": {
        "functional": fetch_functional,
        "cycle": fetch_stage_cycle,
        "tags": ["fetch", "pcgen", "icache", "pipeline"],
        "interface": ["branch_redirect", "branch_target", "fetch_pc", "fetch_valid"],
    },
    "decode": {
        "functional": None,
        "cycle": decode_stage_cycle,
        "tags": ["decode", "rename", "pipeline"],
        "interface": ["instr", "rename_valid", "rd", "rs1", "rs2", "opcode"],
    },
    "issue_queue": {
        "functional": None,
        "cycle": issue_queue_cycle,
        "tags": ["issue", "wakeup", "select"],
        "interface": ["enqueue", "wakeup_pdst", "issue_valid", "issue_pdst"],
    },
    "alu_exec": {
        "functional": None,
        "cycle": alu_exec_cycle,
        "tags": ["execute", "alu", "arithmetic"],
        "interface": ["src0", "src1", "funct3", "opcode", "result"],
    },
    "lsu": {
        "functional": None,
        "cycle": lsu_cycle,
        "tags": ["memory", "load", "store", "dcache"],
        "interface": ["ld_req", "st_req", "addr", "ld_result", "st_done"],
    },
    "rob": {
        "functional": rob_functional,
        "cycle": rob_cycle,
        "tags": ["commit", "retire", "reorder"],
        "interface": ["dispatch_valid", "complete_valid", "commit_valid"],
    },
    "ooo_core": {
        "functional": ooo_core_functional,
        "cycle": None,
        "tags": ["core", "pipeline", "riscv"],
        "interface": ["instr", "rs1_val", "rs2_val", "pc", "result_valid", "pc_next"],
    },
}


def register_behaviors() -> None:
    """Register all behavior templates with the global TemplateRegistry."""
    for name, mod in SKILL_MODULES.items():
        tags = mod.get("tags", []) + ["riscv_ooo_7nm"]
        TemplateRegistry.register(
            name=name,
            behavior_func=mod["functional"],
            cycle_func=mod["cycle"],
            tags=tags,
            interface=mod.get("interface", []),
        )
