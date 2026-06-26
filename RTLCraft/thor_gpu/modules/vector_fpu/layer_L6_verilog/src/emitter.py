"""L6 Verilog emitter for the ThorVectorFPU module."""

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

from thor_gpu.modules.vector_fpu.layer_L5_dsl.src.dsl import ThorVectorFPU


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the vector FPU DSL layer."""
    design = ThorVectorFPU()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_vector_fpu.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorVectorFPU",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor vector FPU DSL contract.",
        "file_name": "thor_vector_fpu.v",
        "dsl_class": "ThorVectorFPU",
        "key_ports": ["src1", "src2", "src3", "result", "active_mask", "fpu_fn"],
    }


__all__ = ["emit_verilog", "describe"]
