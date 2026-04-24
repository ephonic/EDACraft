"""Auto-layout for rtlgen visualization graphs."""

from typing import Dict, List
from rtlgen.viz.model import VizGraph, VizModule


# Domain-specific hierarchical layer assignments.
# Lower layer numbers = higher up on the canvas.
_LAYER_MAP: Dict[str, int] = {
    "(top)": 0,
    "decode": 1,
    "inst_mem": 1,
    "dma": 2,
    "crossbar": 2,
    "systolic": 3,
    "v_alu": 3,
    "sfu": 3,
    "pool": 3,
    "im2col": 3,
    "sram_a": 4,
    "sram_b": 4,
    "sram_c": 4,
    "scratch": 4,
}


def _count_grouped_ports(ports: List) -> int:
    """Count ports after grouping vector ports into buses."""
    from collections import defaultdict
    groups = defaultdict(list)
    singles = 0
    for p in ports:
        name = getattr(p, 'name', '')
        if '_' in name:
            prefix, suffix = name.rsplit('_', 1)
            if suffix.isdigit():
                groups[prefix].append(int(suffix))
                continue
        singles += 1

    grouped = 0
    for prefix, indices in groups.items():
        indices = sorted(indices)
        if len(indices) >= 2 and indices == list(range(min(indices), max(indices) + 1)):
            grouped += 1
        else:
            grouped += len(indices)

    return singles + grouped


def auto_layout(graph: VizGraph, width: float = 1600, height: float = 1000) -> None:
    """Compute positions for all modules in the graph.

    Uses a domain-aware hierarchical layout:
      - Parent (top) module at the top
      - Control / program flow next
      - External interface / routing in the middle
      - Compute engines below
      - Memory banks at the bottom

    Ports are arranged on left (inputs) and right (outputs) sides.
    Vector ports (e.g. weight_in_0..31) are grouped into buses for sizing.

    Args:
        graph: The VizGraph to layout.
        width: Canvas width in pixels.
        height: Canvas height in pixels.
    """
    if not graph.modules:
        return

    # ------------------------------------------------------------------
    # 1. Compute module sizes based on grouped port counts
    # ------------------------------------------------------------------
    for mod in graph.modules:
        n_inputs = _count_grouped_ports([p for p in mod.ports if p.direction == "input"])
        n_outputs = _count_grouped_ports([p for p in mod.ports if p.direction == "output"])
        max_ports = max(n_inputs, n_outputs, 1)
        mod.height = max(80, 40 + max_ports * 18)
        name_len = max(len(mod.instance_name), len(mod.name))
        mod.width = max(160, 100 + name_len * 9)

    # ------------------------------------------------------------------
    # 2. Assign modules to layers
    # ------------------------------------------------------------------
    layers: Dict[int, List[VizModule]] = {}
    for mod in graph.modules:
        layer = _LAYER_MAP.get(mod.instance_name, 2)
        layers.setdefault(layer, []).append(mod)

    # Sort modules within each layer by connection count (most connected first)
    def _connection_count(m: VizModule) -> int:
        return sum(
            1
            for s in graph.signals
            if s.src_module == m.instance_name or s.dst_module == m.instance_name
        )

    for layer, mods in layers.items():
        mods.sort(key=_connection_count, reverse=True)

    # ------------------------------------------------------------------
    # 3. Position modules within each layer
    # ------------------------------------------------------------------
    margin_x = 60
    margin_y = 20
    gap_x = 50

    # Scale layer Y positions to fit within canvas height
    n_layers = max(layers.keys()) + 1 if layers else 1
    layer_height = (height - 2 * margin_y) / max(n_layers, 1)

    for layer, mods in sorted(layers.items()):
        if not mods:
            continue

        y = margin_y + layer * layer_height

        # Ensure y doesn't push modules off the bottom
        max_h = max(m.height for m in mods)
        if y + max_h > height - margin_y:
            y = height - max_h - margin_y
        if y < margin_y:
            y = margin_y

        total_width = sum(m.width for m in mods) + (len(mods) - 1) * gap_x
        start_x = (width - total_width) / 2
        if start_x < margin_x:
            start_x = margin_x

        x = start_x
        for mod in mods:
            mod.x = x
            mod.y = y
            x += mod.width + gap_x

    # ------------------------------------------------------------------
    # 4. Special handling for the parent (top) module
    # ------------------------------------------------------------------
    top_mod = graph.get_module("(top)")
    if top_mod is not None:
        top_mod.x = max(margin_x, (width - top_mod.width) / 2)
        top_mod.y = margin_y
