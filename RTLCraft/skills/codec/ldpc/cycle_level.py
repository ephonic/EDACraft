"""
skills.codec.ldpc.cycle_level — Layer 2: Cycle-Level Models (register-accurate)
(Extracted from behaviors.py)
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def quantizedadder_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate QuantizedAdder model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def quantizedsubber_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate QuantizedSubber model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def comparator_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Comparator model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def checknode_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CheckNode model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def varnode_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate VarNode model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
    return behavior

def ldpc_decoder_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate LDPC_Decoder model."""
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
    "quantizedadder": quantizedadder_cycle,
    "quantizedsubber": quantizedsubber_cycle,
    "comparator": comparator_cycle,
    "checknode": checknode_cycle,
    "varnode": varnode_cycle,
    "ldpc_decoder": ldpc_decoder_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)


#===========================================================================
# Backward-Compatible Aliases
#===========================================================================

quantizedadder_template = quantizedadder_cycle
quantizedsubber_template = quantizedsubber_cycle
comparator_template = comparator_cycle
checknode_template = checknode_cycle
varnode_template = varnode_cycle
ldpc_decoder_template = ldpc_decoder_cycle

def arch_gen(**kwargs):
    """Auto-generated stub for arch_template."""
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
arch_template = arch_gen
