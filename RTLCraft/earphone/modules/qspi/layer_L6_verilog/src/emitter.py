"""L6 Verilog emitter for the EarphoneQSPI module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.qspi.layer_L5_dsl.src.dsl import EarphoneQSPI


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the QSPI DSL layer."""
    design = EarphoneQSPI()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_qspi.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneQSPI",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the QSPI DSL contract.",
        "file_name": "earphone_qspi.v",
        "dsl_class": "EarphoneQSPI",
        "key_ports": ["req", "ready", "qspi_cs_n", "qspi_io_i"],
    }


__all__ = ["emit_verilog", "describe"]
