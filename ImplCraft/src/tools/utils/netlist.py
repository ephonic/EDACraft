"""Netlist conversion and standard-cell name-remap utilities."""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("ic_backend")

VT_SUFFIXES = ["UHVT", "ULVT", "LVT", "HVT", "RVT", "SVT"]
PHYSICAL_ONLY_RE = re.compile(
    r"^X\S+\s+(TAPCELL|FILL|DCAP|ENDCAP|BOUNDRY|WELLTAP|ANTENNA)\S*",
    re.IGNORECASE,
)


def strip_vt_suffix(name: str, suffixes: list[str] | None = None) -> tuple[str, str | None]:
    """Return ``(base_name, suffix)`` after stripping a known VT suffix."""
    suffixes = suffixes or VT_SUFFIXES
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[: -len(suffix)], suffix
    return name, None


def spice_subckt_names(spice_file: str | Path) -> set[str]:
    """Return .subckt names from a SPICE/CDL library."""
    names: set[str] = set()
    try:
        text = Path(spice_file).read_text(errors="ignore")
    except OSError as exc:
        logger.warning(f"Could not read SPICE library {spice_file}: {exc}")
        return names
    for match in re.finditer(r"^\.subckt\s+(\S+)", text, re.MULTILINE | re.IGNORECASE):
        names.add(match.group(1))
    return names


def remap_verilog_cells(
    verilog_file: str | Path,
    spice_file: str | Path,
    output: str | Path,
    suffixes: list[str] | None = None,
) -> Path:
    """Remap Verilog cell instantiations to names present in the SPICE library.

    Removes Vt suffixes from cell names when the suffixed name is not in the
    SPICE library but the base name is.
    """
    suffixes = suffixes or VT_SUFFIXES
    spice_cells = spice_subckt_names(spice_file)
    text = Path(verilog_file).read_text(errors="ignore")

    def remap_token(token: str) -> str:
        if token in spice_cells:
            return token
        base, _ = strip_vt_suffix(token, suffixes)
        if base != token and base in spice_cells:
            return base
        return token

    new_lines: list[str] = []
    for line in text.splitlines():
        new_line = " ".join(
            remap_token(tok) if tok in spice_cells or any(tok.endswith(s) for s in suffixes) else tok
            for tok in line.split()
        )
        new_lines.append(new_line)

    out_path = Path(output)
    out_path.write_text("\n".join(new_lines))
    return out_path


def filter_physical_only_cells(spice_path: str | Path) -> None:
    """Strip physical-only standard-cell instances from a SPICE netlist in place."""
    path = Path(spice_path)
    text = path.read_text(errors="ignore")
    filtered = "\n".join(
        line for line in text.splitlines() if not PHYSICAL_ONLY_RE.match(line)
    )
    if filtered != text:
        path.write_text(filtered)
        logger.info(f"Removed physical-only cells from {path}")


def verilog_to_spice(
    verilog_file: str | Path,
    spice_library: str | Path,
    output: str | Path,
    power_nets: list[str],
    ground_nets: list[str],
    env_script: str | None = None,
    work_dir: Path | None = None,
    physical_only_patterns: Any = None,
) -> Path:
    """Convert a Verilog netlist to SPICE using ``v2lvs``.

    Cell names are first remapped to match the SPICE library.  Physical-only
    cells are then stripped from the converted netlist.
    """
    out_path = Path(output).resolve()
    work_dir = Path(work_dir or Path.cwd())

    # Pre-process Verilog so cell names match the SPICE library.
    remapped_v = work_dir / "netlist_lvs.v"
    remap_verilog_cells(verilog_file, spice_library, remapped_v)

    power = power_nets[0] if power_nets else "VDD"
    ground = ground_nets[0] if ground_nets else "VSS"

    args = [
        "v2lvs",
        "-v", str(remapped_v),
        "-lsp", str(spice_library),
        "-s", str(spice_library),
        "-s0", ground,
        "-s1", power,
        "-addpin", power,
        "-addpin", ground,
        "-o", str(out_path),
    ]
    env = env_script or ""
    cmd = f"source {env} 2>/dev/null; {' '.join(args)}"
    logger.info(f"Converting Verilog to SPICE: {cmd}")
    subprocess.run(["bash", "-c", cmd], check=True)

    filter_physical_only_cells(out_path)
    return out_path
