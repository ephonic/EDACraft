"""Small SystemVerilog cosimulation helpers used by :mod:`rtlgen.sim.cosim`."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional


class CosimError(RuntimeError):
    """Raised when an external RTL cosimulation compile or run fails."""


def _to_sv_literal(value: Any) -> str:
    """Convert a Python scalar into a simple SystemVerilog literal."""
    if isinstance(value, bool):
        return "1'b1" if value else "1'b0"
    if isinstance(value, int):
        return str(value)
    raise CosimError(f"Unsupported SystemVerilog literal type: {type(value)} for value {value!r}")


def _parse_sv_output(stdout: str) -> List[Dict[str, int]]:
    """Parse ``CYCLE <n> key=value`` lines emitted by generated testbenches."""
    trace: List[Dict[str, int]] = []
    cycle_pattern = re.compile(r"^\s*CYCLE\s+(\d+)\s+(.*)$")
    for line in stdout.splitlines():
        match = cycle_pattern.match(line)
        if not match:
            continue
        snapshot: Dict[str, int] = {"_cycle": int(match.group(1))}
        for key, raw_value in re.findall(r"(\w+)=(-?\d+)", match.group(2)):
            snapshot[key] = int(raw_value)
        trace.append(snapshot)
    return trace


def _compile_and_run(sv_src: str, src_files: Optional[List[str]] = None) -> str:
    """Compile and run a small SystemVerilog testbench with local iverilog."""
    with tempfile.TemporaryDirectory(prefix="rtlgen_cosim_") as tmpdir:
        tb_path = os.path.join(tmpdir, "tb_top.sv")
        with open(tb_path, "w", encoding="utf-8") as handle:
            handle.write(sv_src)

        vvp_path = os.path.join(tmpdir, "tb_top.vvp")
        compile_cmd = ["iverilog", "-g2012", "-o", vvp_path, tb_path]
        if src_files:
            compile_cmd.extend(src_files)
        compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if compile_result.returncode != 0:
            raise CosimError(
                "iverilog compilation failed:\n"
                f"stdout={compile_result.stdout}\n"
                f"stderr={compile_result.stderr}"
            )

        run_result = subprocess.run(["vvp", vvp_path], capture_output=True, text=True)
        if run_result.returncode != 0:
            raise CosimError(
                "vvp execution failed:\n"
                f"stdout={run_result.stdout}\n"
                f"stderr={run_result.stderr}"
            )
        return run_result.stdout
