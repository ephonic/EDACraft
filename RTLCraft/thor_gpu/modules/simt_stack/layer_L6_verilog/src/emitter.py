"""L6 Verilog emitter for the ThorSIMTStack module."""

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

from thor_gpu.modules.simt_stack.layer_L5_dsl.src.dsl import ThorSIMTStack


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the SIMT stack DSL layer."""
    design = ThorSIMTStack()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_simt_stack.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorSIMTStack",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor SIMT stack DSL contract.",
        "file_name": "thor_simt_stack.v",
        "dsl_class": "ThorSIMTStack",
        "key_ports": ["push", "pop", "next_pc", "next_mask", "stack_depth"],
    }


__all__ = ["emit_verilog", "describe"]
