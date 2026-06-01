"""
skills.npu.cycle_level — Layer 2: Cycle-Level Models + Template Registry
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry

def topscheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate TopScheduler model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def genericscheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate GenericScheduler model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def mvu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate MVU model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def mfu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate MFU model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def evrf_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate EVRF model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def ld_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate LD model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def nputop_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate NPUTop model."""
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
    "topscheduler": topscheduler_cycle,
    "genericscheduler": genericscheduler_cycle,
    "mvu": mvu_cycle,
    "mfu": mfu_cycle,
    "evrf": evrf_cycle,
    "ld": ld_cycle,
    "nputop": nputop_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

#===========================================================================
# Backward-Compatible Aliases
#===========================================================================

topscheduler_template = topscheduler_cycle
genericscheduler_template = genericscheduler_cycle
mvu_template = mvu_cycle
mfu_template = mfu_cycle
evrf_template = evrf_cycle
ld_template = ld_cycle
nputop_template = nputop_cycle

def arch_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
arch_template = arch_gen

def get_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
get_template = get_gen

def list_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
list_template = list_gen

def register_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
register_template = register_gen

def suggested_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
suggested_template = suggested_gen
