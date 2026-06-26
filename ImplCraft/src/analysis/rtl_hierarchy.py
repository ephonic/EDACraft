"""
Lightweight RTL Hierarchy Extractor

Extracts module instantiation graph and port connectivity from Verilog files.
Combines with DC area report metrics for partition decisions.

Data sources:
  - Verilog RTL: who connects to whom, how many signals cross boundaries
  - DC area report: gate count, area per module (from src/parsers/dc_parser.py)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModuleInfo:
    """Minimal module info extracted from RTL."""
    name: str
    ports: list[tuple[str, str, int]] = field(default_factory=list)  # (name, dir, bits)
    instances: list[tuple[str, str, int]] = field(default_factory=list)  # (module, inst_name, signals)
    file: str = ""

    @property
    def input_bits(self) -> int:
        return sum(b for _, d, b in self.ports if d == "input")

    @property
    def output_bits(self) -> int:
        return sum(b for _, d, b in self.ports if d == "output")

    @property
    def total_io_bits(self) -> int:
        return sum(b for _, _, b in self.ports)


@dataclass
class HierarchyGraph:
    """Module instantiation graph."""
    modules: dict[str, ModuleInfo] = field(default_factory=dict)
    top: str = ""

    def cross_signals(self, parent: str, child_module: str) -> int:
        """Count signals connecting parent to a child instance."""
        mod = self.modules.get(parent)
        if not mod:
            return 0
        total = 0
        for m, _, sigs in mod.instances:
            if m == child_module:
                total += sigs
        return total

    def child_modules(self, parent: str) -> list[str]:
        """Get child module names of parent."""
        mod = self.modules.get(parent)
        if not mod:
            return []
        return [m for m, _, _ in mod.instances]

    def depth(self, name: str, visited: set | None = None) -> int:
        """Hierarchy depth from a module."""
        if visited is None:
            visited = set()
        if name in visited:
            return 0
        visited.add(name)
        children = self.child_modules(name)
        if not children:
            return 1
        return 1 + max(self.depth(c, visited) for c in children)

    def summary(self) -> str:
        lines = [
            f"RTL Hierarchy: {len(self.modules)} modules, top={self.top}",
            f"Depth: {self.depth(self.top)}",
            "",
        ]
        visited: set[str] = set()

        def walk(name: str, indent: int):
            if name in visited:
                return
            visited.add(name)
            mod = self.modules.get(name)
            if not mod:
                return
            prefix = "  " * indent
            io_info = f"IO={mod.total_io_bits}b (in={mod.input_bits}, out={mod.output_bits})"
            inst_info = f"{len(mod.instances)} instances"
            lines.append(f"{prefix}{name} [{io_info}, {inst_info}]")
            for child_mod, inst_name, sigs in mod.instances:
                if child_mod in visited:
                    lines.append(f"{prefix}  └─ {inst_name}: {child_mod} ({sigs} signals)")
                else:
                    lines.append(f"{prefix}  └─ {inst_name}: {child_mod} ({sigs} signals)")
                    walk(child_mod, indent + 2)

        walk(self.top, 0)
        return "\n".join(lines)


# --- Patterns ---

# module Foo #(...) (a, b, c);  or  module Foo (a, b, c);
_RE_MODULE = re.compile(
    r"module\s+(\w+)\s*(?:#\s*\([^)]*\))?\s*\(([^;]*)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

# input/output/inout with optional range: input [7:0] data;
_RE_PORT = re.compile(
    r"(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:signed\s+)?(?:\[(\d+)\s*:\s*(\d+)\])?\s*(\w+)"
)

# Module instantiation:  ModName #(...) inst_name (.p1(w1), ...);
# Captures module name, instance name, and connection list
_RE_INST = re.compile(
    r"^\s{0,4}(\w+)\s+(?:#\s*\([^)]*\)\s+)?(\w+)\s*\(([^;]*)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

# .port(signal) connection
_RE_CONN = re.compile(r"\.(\w+)\s*\(")

# Reserved words that aren't module names
_KEYWORDS = {
    "module", "endmodule", "input", "output", "inout", "wire", "reg",
    "assign", "always", "initial", "begin", "end", "if", "else", "case",
    "for", "while", "function", "task", "generate", "endgenerate",
    "parameter", "localparam", "integer", "real", "time", "genvar",
    "and", "or", "not", "nand", "nor", "xor", "xnor", "buf", "bufif0", "bufif1",
    "specify", "endspecify", "primitive", "endprimitive", "table", "endtable",
    "tri", "tri0", "tri1", "wand", "wor", "supply0", "supply1",
    "posedge", "negedge",
}


def parse_rtl_files(file_paths: list[str]) -> HierarchyGraph:
    """Parse Verilog files and extract hierarchy graph."""
    graph = HierarchyGraph()

    for fpath in file_paths:
        path = Path(fpath)
        if not path.exists():
            continue
        content = path.read_text()
        # Strip comments
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        for m in _RE_MODULE.finditer(content):
            mod_name = m.group(1)
            # port_list_text = m.group(2)

            mod = ModuleInfo(name=mod_name, file=str(path))

            # Extract module body
            body_start = m.end()
            end_pos = content.find("endmodule", body_start)
            if end_pos == -1:
                end_pos = len(content)
            body = content[body_start:end_pos]

            # Parse ports from body
            for pm in _RE_PORT.finditer(body):
                direction = pm.group(1)
                hi = int(pm.group(2)) if pm.group(2) else 0
                lo = int(pm.group(3)) if pm.group(3) else 0
                pname = pm.group(4)
                bits = abs(hi - lo) + 1 if pm.group(2) else 1
                mod.ports.append((pname, direction, bits))

            # Parse instances from body
            for im in _RE_INST.finditer(body):
                inst_mod = im.group(1)
                inst_name = im.group(2)
                conn_text = im.group(3)

                if inst_mod in _KEYWORDS or inst_mod.startswith("$"):
                    continue
                if inst_name in _KEYWORDS:
                    continue

                # Count port connections
                signals = len(_RE_CONN.findall(conn_text))
                if signals == 0:
                    # Positional connection: count commas + 1
                    non_empty = [s.strip() for s in conn_text.split(",") if s.strip()]
                    signals = len(non_empty)

                mod.instances.append((inst_mod, inst_name, signals))

            graph.modules[mod_name] = mod

    # Find top module (not instantiated by anyone)
    instantiated = set()
    for mod in graph.modules.values():
        for child_mod, _, _ in mod.instances:
            instantiated.add(child_mod)
    for name in graph.modules:
        if name not in instantiated:
            graph.top = name
            break

    return graph


def merge_with_dc_metrics(
    graph: HierarchyGraph,
    dc_areas: dict[str, dict],
) -> dict[str, dict]:
    """
    Merge RTL hierarchy with DC area report data.

    Args:
        graph: Hierarchy graph from RTL parsing
        dc_areas: Dict from DC parser, keyed by cell/module name.
                  Expected keys: gate_count, area_um2, cell_count

    Returns:
        Combined data per module.
    """
    combined = {}
    for name, mod in graph.modules.items():
        entry = {
            "name": name,
            "io_bits": mod.total_io_bits,
            "input_bits": mod.input_bits,
            "output_bits": mod.output_bits,
            "num_instances": len(mod.instances),
            "children": [m for m, _, _ in mod.instances],
            "file": mod.file,
        }
        # Merge DC metrics if available
        if name in dc_areas:
            dc = dc_areas[name]
            entry["gate_count"] = dc.get("gate_count", 0)
            entry["area_um2"] = dc.get("area_um2", 0.0)
            entry["cell_count"] = dc.get("cell_count", 0)
        else:
            entry["gate_count"] = 0
            entry["area_um2"] = 0.0
            entry["cell_count"] = 0

        # Cross-module signal counts
        entry["cross_signals"] = {}
        for child_mod, inst_name, sigs in mod.instances:
            entry["cross_signals"][inst_name] = {
                "module": child_mod,
                "signals": sigs,
            }

        combined[name] = entry

    return combined
