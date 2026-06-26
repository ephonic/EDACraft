"""
skills.hetero_riscv4.behaviors — Thin shim (re-exports from functional & cycle_level)
"""
from skills.hetero_riscv4.functional import *  # noqa: F401,F403
from skills.hetero_riscv4.cycle_level import *  # noqa: F401,F403

l1_cache_template = l1cachesmall_functional
mesh_top_template = heteromeshtop_functional
