"""L6 Verilog emitter for the EarphoneAPBBridge module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.apb_bridge.layer_L5_dsl.src.dsl import EarphoneAPBBridge


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the APB bridge DSL layer."""
    design = EarphoneAPBBridge()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_apb_bridge.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneAPBBridge",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the APB bridge DSL contract.",
        "file_name": "earphone_apb_bridge.v",
        "dsl_class": "EarphoneAPBBridge",
        "key_ports": ["m_paddr", "s_psel", "m_pready"],
    }


__all__ = ["emit_verilog", "describe"]
