"""L6 Verilog emitter for the ThorTensorCore module."""

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

from thor_gpu.modules.tensor_core.layer_L5_dsl.src.dsl import ThorTensorCore


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the tensor core DSL layer."""
    design = ThorTensorCore()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_tensor_core.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorTensorCore",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor tensor core DSL contract.",
        "file_name": "thor_tensor_core.v",
        "dsl_class": "ThorTensorCore",
        "key_ports": ["a", "b", "c", "result", "start"],
    }


__all__ = ["emit_verilog", "describe"]
