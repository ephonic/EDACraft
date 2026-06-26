"""L6 Verilog emitter for the EarphoneI2C module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.i2c.layer_L5_dsl.src.dsl import EarphoneI2C


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the I2C DSL layer."""
    design = EarphoneI2C()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_i2c.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneI2C",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the APB I2C DSL contract.",
        "file_name": "earphone_i2c.v",
        "dsl_class": "EarphoneI2C",
        "key_ports": ["paddr", "scl_o", "sda_oe"],
    }


__all__ = ["emit_verilog", "describe"]
