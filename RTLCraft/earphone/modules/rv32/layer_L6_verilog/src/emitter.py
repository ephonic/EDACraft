"""L6 Verilog emitter for the EarphoneRV32 core.

This layer converts the L5 DSL representation into synthesizable Verilog.
The actual emission is delegated to rtlgen's VerilogEmitter; this module is
responsible for module-level packaging and report collection.
"""

from __future__ import annotations

from typing import Optional, Tuple

from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32


def emit_verilog(output_dir: Optional[str] = None) -> Tuple[str, int]:
    """Generate Verilog for EarphoneRV32.

    Args:
        output_dir: Directory to write the Verilog file.  If None, the file is
            not written and only the source string is returned.

    Returns:
        A tuple of (verilog_source, line_count).
    """
    # The L5 DSL class already exposes an emit_verilog method through rtlgen.
    design = EarphoneRV32()
    # By default design_earphone writes to generated/earphone_rv32.v
    source = design.emit_verilog(output_dir)
    line_count = len(source.splitlines())
    return source, line_count
