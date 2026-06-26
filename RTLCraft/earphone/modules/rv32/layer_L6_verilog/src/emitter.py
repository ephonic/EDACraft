"""L6 Verilog emitter for the EarphoneRV32 core.

This layer converts the L5 DSL representation into synthesizable Verilog.
The actual emission is delegated to rtlgen's VerilogEmitter; this module is
responsible for module-level packaging and report collection.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Generate Verilog for EarphoneRV32.

    Args:
        output_dir: Directory to write the Verilog file.  If None, the file is
            not written and only the source string is returned.

    Returns:
        A tuple of (verilog_source, line_count).
    """
    design = EarphoneRV32()
    source = VerilogEmitter().emit(design)
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "earphone_rv32.v"), "w", encoding="utf-8") as f:
            f.write(source)
    line_count = len(source.splitlines())
    return source, line_count
