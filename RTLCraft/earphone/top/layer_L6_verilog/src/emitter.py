"""L6 Verilog emitter for the Earphone top-level SoC."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.top.layer_L5_dsl.src.dsl import build_top


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit Verilog for the current top-level DSL contract."""
    source = VerilogEmitter().emit(build_top())
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_top.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return top-level Verilog deliverable metadata."""
    return {
        "name": "EarphoneTop",
        "layer": "L6_verilog",
        "status": "implemented",
        "file_name": "earphone_top.v",
        "dsl_source": "earphone/top/layer_L5_dsl/src/dsl.py",
        "key_ports": ["clk", "rst_n", "apb_paddr", "qspi_cs_n", "scl_o", "sda_o"],
    }


__all__ = ["emit_verilog", "describe"]
