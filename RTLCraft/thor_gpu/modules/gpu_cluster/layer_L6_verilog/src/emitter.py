"""L6 Verilog emitter for the ThorCluster module (cluster top)."""

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

from thor_gpu.modules.gpu_cluster.layer_L5_dsl.src.dsl import ThorCluster


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the cluster DSL layer (top)."""
    design = ThorCluster()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "thor_cluster.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorCluster",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the Thor cluster top DSL contract.",
        "file_name": "thor_cluster.v",
        "dsl_class": "ThorCluster",
        "key_ports": ["all_done", "sm0_w0_acc0", "sm1_w0_acc0", "start", "mem_req"],
    }


__all__ = ["emit_verilog", "describe"]
