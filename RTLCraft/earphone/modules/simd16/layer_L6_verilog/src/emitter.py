"""L6 Verilog emitter for the EarphoneSIMD16 module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.simd16.layer_L5_dsl.src.dsl import EarphoneSIMD16


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the SIMD16 DSL layer."""
    design = EarphoneSIMD16()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_simd16.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneSIMD16",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the SIMD16 DSL contract.",
        "file_name": "earphone_simd16.v",
        "dsl_class": "EarphoneSIMD16",
        "key_ports": ["vsrc0", "vdst", "done"],
    }


__all__ = ["emit_verilog", "describe"]
