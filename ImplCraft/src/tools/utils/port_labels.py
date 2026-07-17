"""Top-level port text-label generation for Calibre LVS.

APR tools often produce abstract top-level ports without physical shapes.  The
DEF still records routed stubs or component-pin locations, so we derive
``LAYOUT TEXT`` coordinates from it.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .gds import apply_def_orientation, parse_std_cell_pin_offsets

# Map metal layer names to Calibre PORT TEXT layer numbers (TSMC 28HPC+).
LAYER_TEXT_MAP: dict[str, int] = {
    "M1": 131, "M2": 132, "M3": 133, "M4": 134, "M5": 135,
    "M6": 136, "M7": 137, "M8": 138, "M9": 139, "M10": 140, "AP": 126,
}
DEFAULT_TEXT_LAYER = 131  # M1


def generate_port_labels_from_def(
    def_file: str | Path,
    port_names: set[str],
    std_gds: str | Path | None = None,
    suffixes: list[str] | None = None,
) -> dict[str, tuple[int, float, float]]:
    """Build a name → (text_layer, x, y) mapping from DEF routes/pins.

    Signal nets with a ``ROUTED`` segment use the first route point and layer.
    Unrouted pins use the standard-cell pin label offset from ``std_gds``.
    Power/ground ports (VDD/VSS) are located by scanning component pin labels.
    """
    suffixes = suffixes or ["UHVT", "ULVT", "LVT", "HVT", "RVT", "SVT"]
    text = Path(def_file).read_text(errors="ignore")

    units_match = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;', text, re.IGNORECASE)
    units = int(units_match.group(1)) if units_match else 1000

    # Component placements: - u_le/U8 AOI22D0BWP30P140UHVT + PLACED ( x y ) N ;
    comp_re = re.compile(
        r'^\s*-\s+(\S+)\s+(\S+)\s+\+\s+PLACED\s+\(\s*([-+]?\d+)\s+([-+]?\d+)\s*\)\s+(\S+)\s*;',
        re.MULTILINE,
    )
    components: dict[str, tuple[str, float, float, str]] = {}
    for m in comp_re.finditer(text):
        components[m.group(1)] = (
            m.group(2),  # master name
            float(m.group(3)) / units,
            float(m.group(4)) / units,
            m.group(5),  # orientation
        )

    # Build std-cell pin offsets so we can place labels on un-routed pins.
    pin_offsets: dict[str, dict[str, tuple[int, float, float]]] = {}
    cell_bboxes: dict[str, tuple[float, float, float, float]] = {}
    master_to_base: dict[str, str] = {}
    if std_gds and Path(std_gds).exists():
        pin_offsets, cell_bboxes = parse_std_cell_pin_offsets(std_gds)
        for master in {c[0] for c in components.values()}:
            base = master
            for suffix in suffixes:
                if base.endswith(suffix):
                    base = base[: -len(suffix)]
                    break
            if base in pin_offsets:
                master_to_base[master] = base

    labels: dict[str, tuple[int, float, float]] = {}

    # Parse NETS section.  DEF nets may span multiple lines and use '+'
    # continuation markers.
    nets_match = re.search(r'NETS\s+\d+\s*;(.*?)END\s+NETS', text, re.DOTALL | re.IGNORECASE)
    if nets_match:
        nets_text = re.sub(r'\n\+', ' ', nets_match.group(1))
        for net_block in re.split(r'\n\s*-\s+', nets_text):
            if not net_block.strip():
                continue
            net_name = net_block.split()[0]
            if net_name not in port_names:
                continue

            # Prefer a routed segment start point.  DEF syntax may include a width
            # before the coordinate list, e.g. ``ROUTED M1 60 ( x y w ) ...``.
            route_m = re.search(
                r'ROUTED\s+(\S+)\s+(?:\d+\s+)?\(\s*([-+]?\d+)\s+([-+]?\d+)', net_block
            )
            if route_m:
                layer = route_m.group(1)
                x = float(route_m.group(2)) / units
                y = float(route_m.group(3)) / units
                labels[net_name] = (LAYER_TEXT_MAP.get(layer, DEFAULT_TEXT_LAYER), x, y)
                continue

            # No route: use the first component pin location, offset by the
            # standard-cell pin label position from the GDS library.
            pin_m = re.search(r'\(\s*(?!PIN\b)(\S+)\s+(\S+)\s*\)', net_block)
            if pin_m:
                comp_name, pin_name = pin_m.group(1), pin_m.group(2)
                if comp_name in components:
                    master, cx, cy, orient = components[comp_name]
                    base = master_to_base.get(master, master)
                    if base in pin_offsets and pin_name in pin_offsets[base]:
                        text_layer, dx, dy = pin_offsets[base][pin_name]
                        bbox = cell_bboxes.get(base)
                        dx, dy = apply_def_orientation(dx, dy, orient, bbox)
                        labels[net_name] = (text_layer, cx + dx, cy + dy)
                    else:
                        # Fallback to component origin.
                        labels[net_name] = (DEFAULT_TEXT_LAYER, cx, cy)

    # Power/ground ports are not listed as regular signal nets in the DEF.
    # Pick any component that has a VDD/VSS pin label and use that location.
    for pg in ("VDD", "VSS"):
        if pg not in port_names or pg in labels:
            continue
        for master, cx, cy, orient in components.values():
            base = master_to_base.get(master, master)
            if base in pin_offsets and pg in pin_offsets[base]:
                text_layer, dx, dy = pin_offsets[base][pg]
                bbox = cell_bboxes.get(base)
                dx, dy = apply_def_orientation(dx, dy, orient, bbox)
                labels[pg] = (text_layer, cx + dx, cy + dy)
                break

    return labels


def write_port_labels(
    labels: dict[str, tuple[int, float, float]],
    output: str | Path,
) -> Path:
    """Write a Calibre port-label file: ``name layer x y`` per line."""
    out_file = Path(output)
    with out_file.open("w") as fp:
        for name, (layer, x, y) in sorted(labels.items()):
            fp.write(f"{name} {layer} {x:.6f} {y:.6f}\n")
    return out_file
