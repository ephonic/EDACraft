"""GDSII manipulation utilities (cell listing, remap, merge, pin offsets)."""
from __future__ import annotations

import logging
import struct
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("ic_backend")

# Default pin-text layers for TSMC 28HPC+: 131=M1 ... 140=M10, 126=AP.
PIN_TEXT_LAYERS = frozenset({126, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140})


def run_calibredrv(
    args: list[str],
    env_script: str | None,
    cwd: Path | None = None,
) -> None:
    """Run calibredrv with the given EDA environment loaded."""
    env = env_script or ""
    cmd = f"source {env} 2>/dev/null; calibredrv {' '.join(args)}"
    logger.info(f"[calibredrv] {cmd}")
    subprocess.run(
        ["bash", "-c", cmd],
        cwd=str(cwd or Path.cwd()),
        check=True,
    )


def list_gds_cells(gds_file: str | Path, env_script: str | None = None) -> set[str]:
    """Return the set of cell names defined in a GDS file."""
    cells: set[str] = set()
    env = env_script or ""
    try:
        out = subprocess.check_output(
            ["bash", "-c", f"source {env} 2>/dev/null; calibredrv -a layout peek '{gds_file}' -cells"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in out.splitlines():
            cells.update(line.split())
    except subprocess.CalledProcessError as exc:
        logger.warning(f"Could not list cells in {gds_file}: {exc}")
    return cells


def list_gds_undefined_cells(gds_file: str | Path, env_script: str | None = None) -> set[str]:
    """Return cells referenced but not defined in the given GDS file."""
    undefined: set[str] = set()
    env = env_script or ""
    try:
        out = subprocess.check_output(
            ["bash", "-c", f"source {env} 2>/dev/null; calibredrv -a layout peek '{gds_file}' -undefcells"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in out.splitlines():
            undefined.update(line.split())
    except subprocess.CalledProcessError as exc:
        logger.warning(f"Could not list undefined cells in {gds_file}: {exc}")
    return undefined


def build_cell_name_map(
    undefined_cells: set[str],
    known_cells: set[str],
    suffixes: list[str] | None = None,
) -> dict[str, str]:
    """Map suffixed cell names to known base names.

    Common foundry flows append a Vt suffix (e.g. UHVT) to physical cell names
    while the library GDS uses the unsuffixed name.
    """
    suffixes = suffixes or ["UHVT", "ULVT", "LVT", "HVT", "RVT", "SVT"]
    mapping: dict[str, str] = {}
    for cell in undefined_cells:
        if cell in known_cells:
            continue
        for suffix in suffixes:
            if cell.endswith(suffix):
                base = cell[: -len(suffix)]
                if base in known_cells:
                    mapping[cell] = base
                break
    return mapping


def merge_gds(
    design_gds: str | Path,
    std_cell_gds: str | Path,
    output: str | Path,
    cell_map: dict[str, str] | None = None,
    env_script: str | None = None,
    work_dir: Path | None = None,
) -> Path:
    """Merge a routed design GDS with a standard-cell library GDS.

    If ``cell_map`` is provided, ``-map_cell`` is passed to calibredrv so
    referenced cell names are remapped to library definitions.
    """
    out_path = Path(output).resolve()
    args = [
        "-a", "layout", "filemerge",
        "-in", str(design_gds),
        "-in", str(std_cell_gds),
        "-out", str(out_path),
    ]
    if cell_map:
        map_file = (Path(work_dir or Path.cwd()) / "gds_cell_map.txt").resolve()
        map_file.write_text("\n".join(f"{k} {v}" for k, v in cell_map.items()))
        args.extend(["-map_cell", str(map_file)])
    run_calibredrv(args, env_script, cwd=work_dir)
    logger.info(f"Merged standard-cell GDS into {out_path}")
    return out_path


def parse_std_cell_pin_offsets(
    std_gds: str | Path,
) -> tuple[dict[str, dict[str, tuple[int, float, float]]], dict[str, tuple[float, float, float, float]]]:
    """Return ({cell: {pin: (text_layer, x, y)}}, {cell: bbox}) from a std-cell GDS.

    Pin labels are read from text elements on the metal pin-text layers
    (``PIN_TEXT_LAYERS``).  The text layer number is preserved so the Calibre
    ``LAYOUT TEXT`` statement can be placed on the matching PORT TEXT layer.
    Cell bounding boxes are computed from all boundary/path XY coordinates.
    Coordinates are returned in microns.
    """
    offsets: dict[str, dict[str, tuple[int, float, float]]] = {}
    bboxes: dict[str, list[float]] = {}
    try:
        data = Path(std_gds).read_bytes()
    except OSError:
        return offsets, {}

    n = len(data)
    i = 0
    cell = None
    in_text = False
    in_shape = False
    layer: int | None = None
    x = y = 0.0
    string: str | None = None

    def add_point(px: float, py: float) -> None:
        if cell is None:
            return
        if cell not in bboxes:
            bboxes[cell] = [px, py, px, py]
        else:
            b = bboxes[cell]
            b[0] = min(b[0], px)
            b[1] = min(b[1], py)
            b[2] = max(b[2], px)
            b[3] = max(b[3], py)

    while i < n:
        rec_len = struct.unpack('>H', data[i:i + 2])[0]
        if rec_len < 4 or i + rec_len > n:
            break
        rec_type = data[i + 2]
        payload = data[i + 4:i + rec_len]
        if rec_type == 0x05:  # BGNSTR
            cell = None
        elif rec_type == 0x06:  # STRNAME
            cell = payload.decode('ascii', errors='ignore').strip('\x00')
        elif rec_type in (0x08, 0x09):  # BOUNDARY / PATH
            in_shape = True
        elif rec_type == 0x0C:  # TEXT
            in_text = True
            layer = None
            x = y = 0.0
            string = None
        elif rec_type == 0x0D:  # LAYER
            layer = struct.unpack('>H', payload)[0]
        elif rec_type == 0x10:  # XY
            coords = struct.unpack('>' + str(len(payload) // 4) + 'i', payload)
            pts = [c / 1000.0 for c in coords]
            xy = list(zip(pts[::2], pts[1::2]))
            if in_shape and cell:
                for px, py in xy:
                    add_point(px, py)
            elif in_text and cell and xy:
                x, y = xy[0]
        elif rec_type == 0x19:  # STRING
            string = payload.decode('ascii', errors='ignore').strip('\x00')
        elif rec_type == 0x11:  # ENDEL
            if in_text and cell and layer in PIN_TEXT_LAYERS and string:
                offsets.setdefault(cell, {})[string] = (layer, x, y)
            in_text = False
            in_shape = False
        i += rec_len

    bbox_out = {c: (b[0], b[1], b[2], b[3]) for c, b in bboxes.items()}
    return offsets, bbox_out


def apply_def_orientation(
    x: float,
    y: float,
    orient: str,
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[float, float]:
    """Apply a DEF orientation to a point relative to a cell origin.

    The placement origin in DEF is the lower-left corner of the (possibly
    transformed) cell bounding box.  ``bbox`` is the cell's untransformed
    bounding box ``(minx, miny, maxx, maxy)``.
    """
    if bbox is None:
        bbox = (0.0, 0.0, 0.0, 0.0)
    minx, miny, maxx, maxy = bbox
    w = maxx - minx
    h = maxy - miny

    if orient == "N":
        return (x, y)
    if orient == "S":
        return (minx + w - (x - minx), miny + h - (y - miny))
    if orient == "FN":
        return (minx + w - (x - minx), y)
    if orient == "FS":
        return (x, miny + h - (y - miny))
    if orient == "E":
        return (minx + h - (y - miny), miny + (x - minx))
    if orient == "FE":
        return (minx + h - (y - miny), miny + w - (x - minx))
    if orient == "W":
        return (minx + (y - miny), miny + w - (x - minx))
    if orient == "FW":
        return (minx + (y - miny), miny + (x - minx))
    return (x, y)
