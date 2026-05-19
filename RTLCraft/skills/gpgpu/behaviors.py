"""
skills.gpgpu.behaviors — GPGPU Behavior Templates

Domain-specific behavior templates for GPGPU pipeline stages.
Registered into TemplateRegistry at import time.

GPGPU pipeline stages currently use generic behavior templates
(fifo, datapath) with skeleton step guidance in skeleton_templates.py.
Future: add cycle-accurate behavioral models for:
  - cta_scheduler: Workgroup dispatch + resource allocation
  - warp_scheduler: Per-SM warp-level scheduling
  - pipe: SM pipeline stage execution
"""
from __future__ import annotations

from typing import Any, Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry, fifo_template, datapath_template


def cta_scheduler_template(
    num_cus: int = 4,
    vgpr_per_cu: int = 256,
    sgpr_per_cu: int = 512,
    lds_size_kb: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """CTA (workgroup) scheduler behavior.

    Manages workgroup dispatch to CUs, VGPR/SGPR/LDS resource allocation.
    """
    def behavior(ctx: CycleContext):
        wg_valid = ctx.get_input("wg_valid", 0)
        cu_ready = ctx.get_input("cu_ready", 0)

        dispatch_count = ctx.get_state("dispatch_count", 0)
        active_wgs = ctx.get_state("active_wgs", 0)

        if wg_valid and active_wgs < num_cus:
            ctx.set_output("wg_ready", 1)
            ctx.set_output("dispatch_valid", 1)
            ctx.set_output("dispatch_cu_id", active_wgs % num_cus)
            active_wgs = active_wgs + 1
            dispatch_count = dispatch_count + 1
        else:
            ctx.set_output("wg_ready", 0)
            ctx.set_output("dispatch_valid", 0)
            ctx.set_output("dispatch_cu_id", 0)

        ctx.set_state("dispatch_count", dispatch_count)
        ctx.set_state("active_wgs", active_wgs)

    return behavior


def warp_scheduler_template(
    num_warps: int = 8,
    num_pipes: int = 7,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Warp scheduler behavior.

    Manages per-warp PC, warp active tracking, and pipe dispatch.
    """
    def behavior(ctx: CycleContext):
        warp_end = ctx.get_input("warp_end", 0)
        warp_req = ctx.get_input("warp_req", 0)

        active_mask = ctx.get_state("active_mask", 0)
        dispatch_ptr = ctx.get_state("dispatch_ptr", 0)

        if warp_req:
            active_mask = active_mask | (1 << dispatch_ptr)
            dispatch_ptr = (dispatch_ptr + 1) % num_warps

        if warp_end:
            active_mask = active_mask & ~(1 << 0)  # Simplified

        ctx.set_output("active_count", bin(active_mask).count('1'))
        ctx.set_output("next_warp_id", dispatch_ptr)
        ctx.set_state("active_mask", active_mask)
        ctx.set_state("dispatch_ptr", dispatch_ptr)

    return behavior


# Register GPGPU templates
TemplateRegistry.register("cta_scheduler", cta_scheduler_template)
TemplateRegistry.register("warp_scheduler", warp_scheduler_template)

__all__ = [
    "cta_scheduler_template",
    "warp_scheduler_template",
]
