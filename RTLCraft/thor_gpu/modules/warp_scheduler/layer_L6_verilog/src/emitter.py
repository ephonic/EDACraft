"""L6 Verilog emitter for the ThorWarpScheduler module."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional, Tuple

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.codegen import VerilogEmitter

from thor_gpu.modules.warp_scheduler.layer_L5_dsl.src.dsl import ThorWarpScheduler


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the warp scheduler DSL layer."""
    design = ThorWarpScheduler()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_warp_scheduler.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorWarpScheduler",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor warp scheduler DSL contract.",
        "file_name": "thor_warp_scheduler.v",
        "dsl_class": "ThorWarpScheduler",
        "key_ports": ["warp_sel", "barrier_release", "sm_done", "warp_idle"],
    }


__all__ = ["emit_verilog", "describe"]
