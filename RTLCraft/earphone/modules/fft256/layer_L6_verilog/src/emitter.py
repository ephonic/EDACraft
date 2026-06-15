"""L6 Verilog emitter for the EarphoneFFT256 module."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.fft256.layer_L5_dsl.src.dsl import EarphoneFFT256


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Emit synthesizable Verilog for the FFT wrapper DSL layer."""
    design = EarphoneFFT256()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_fft256.v"), "w", encoding="utf-8") as f:
            f.write(source)
    return source, len(source.splitlines())


def describe() -> Dict[str, Any]:
    """Return Verilog deliverable metadata for document generation."""
    return {
        "name": "EarphoneFFT256",
        "layer": "L6_verilog",
        "status": "implemented",
        "description": "Verilog emission wrapper for the FFT256 DSL contract.",
        "file_name": "earphone_fft256.v",
        "dsl_class": "EarphoneFFT256",
        "key_ports": ["di_en", "do_en", "do_re", "do_im"],
    }


__all__ = ["emit_verilog", "describe"]
