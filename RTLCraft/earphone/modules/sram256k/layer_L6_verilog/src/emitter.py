"""L6 Verilog emitter for the EarphoneSRAM256K module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.sram256k.layer_L5_dsl.src.dsl import EarphoneSRAM256K


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the SRAM DSL layer."""
    design = EarphoneSRAM256K()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_sram256k.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneSRAM256K",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the SRAM DSL contract.",
        "file_name": "earphone_sram256k.v",
        "dsl_class": "EarphoneSRAM256K",
        "key_ports": ["paddr", "prdata", "pstrb"],
    }


__all__ = ["emit_verilog", "describe"]
