"""L6 Verilog emitter for the ThorGpuSM module."""

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

from thor_gpu.modules.gpu_sm.layer_L5_dsl.src.dsl import ThorGpuSM


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the SM DSL layer."""
    design = ThorGpuSM()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_gpu_sm.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorGpuSM",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor SM DSL contract.",
        "file_name": "thor_gpu_sm.v",
        "dsl_class": "ThorGpuSM",
        "key_ports": ["sm_done", "debug_w0_acc0", "imem_wr_en", "start"],
    }


__all__ = ["emit_verilog", "describe"]
