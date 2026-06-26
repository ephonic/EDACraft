"""
skills.riscv64_soc.cycle_level — Layer 2: Cycle-Level Models + Template Registry
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry

def rv64core_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def l1cache_cycle(**kwargs) -> Callable[[CycleContext], None]:
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

def l2cacheslice_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def nocbuffer_cycle(**kwargs) -> Callable[[CycleContext], None]:
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

def clustertop_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def meshtop_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def dramctrl_cycle(**kwargs) -> Callable[[CycleContext], None]:
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
    "rv64core": rv64core_cycle,
    "l1cache": l1cache_cycle,
    "coherencedir": coherencedir_cycle,
    "l2cacheslice": l2cacheslice_cycle,
    "nocbuffer": nocbuffer_cycle,
    "nocrouter": nocrouter_cycle,
    "clustertop": clustertop_cycle,
    "meshtop": meshtop_cycle,
    "dramctrl": dramctrl_cycle,
    "rv64_core": rv64core_cycle,
    "l1_cache": l1cache_cycle,
    "coherence_dir": coherencedir_cycle,
    "l2_cache": l2cacheslice_cycle,
    "noc_router": nocrouter_cycle,
    "cluster": clustertop_cycle,
    "soc_top": meshtop_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

#===========================================================================
# Backward-Compatible Aliases
#===========================================================================

rv64core_template = rv64core_cycle
l1cache_template = l1cache_cycle
coherencedir_template = coherencedir_cycle
l2cacheslice_template = l2cacheslice_cycle
nocbuffer_template = nocbuffer_cycle
nocrouter_template = nocrouter_cycle
clustertop_template = clustertop_cycle
meshtop_template = meshtop_cycle
dramctrl_template = dramctrl_cycle
rv64_core_template = rv64core_cycle
l1_cache_template = l1cache_cycle
coherence_dir_template = coherencedir_cycle
l2_cache_template = l2cacheslice_cycle
noc_router_template = nocrouter_cycle
cluster_template = clustertop_cycle
soc_top_template = meshtop_cycle

def skeleton_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
skeleton_template = skeleton_gen
