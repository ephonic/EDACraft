"""
skills.hetero_riscv4.cycle_level — Layer 2: Cycle-Level Models + Template Registry
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry

def nocbuffer_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def efficiencycore_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def performancecore_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def l1cachesmall_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def l1cachebig_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def coherencedir_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def nocrouter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def heteromeshtop_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

#===========================================================================

# Template Registry
#===========================================================================

_template_map = {
    "nocbuffer": nocbuffer_cycle,
    "efficiencycore": efficiencycore_cycle,
    "performancecore": performancecore_cycle,
    "l1cachesmall": l1cachesmall_cycle,
    "l1cachebig": l1cachebig_cycle,
    "coherencedir": coherencedir_cycle,
    "nocrouter": nocrouter_cycle,
    "heteromeshtop": heteromeshtop_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

#===========================================================================
# Backward-Compatible Aliases
#===========================================================================

nocbuffer_template = nocbuffer_cycle
efficiencycore_template = efficiencycore_cycle
performancecore_template = performancecore_cycle
l1cachesmall_template = l1cachesmall_cycle
l1cachebig_template = l1cachebig_cycle
coherencedir_template = coherencedir_cycle
nocrouter_template = nocrouter_cycle
heteromeshtop_template = heteromeshtop_cycle

# Auto-fixed aliases for arch_templates
coherence_dir_template = coherencedir_cycle
noc_router_template = nocrouter_cycle

# arch_templates compat aliases
perf_core_template = performancecore_cycle
eff_core_template = efficiencycore_cycle

def skeleton_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
skeleton_template = skeleton_gen
