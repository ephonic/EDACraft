"""
Hierarchy Analyzer — builds ModuleGraph from synthesis reports and RTL.

Input sources:
1. DC hierarchical area report (report_area -hierarchy)
2. RTL Verilog files (module declarations and instantiations)
3. Timing reports (critical path attribution)

Output:
- Populated ModuleGraph with metrics per module
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

from .module_graph import (
    ModuleGraph, ModuleNode, ModuleMetrics,
    PartitionDecision, TimingCriticality,
)

logger = logging.getLogger("ic_backend")


class HierarchyAnalyzer:
    """
    Build and analyze design hierarchy from synthesis reports and RTL.

    Usage:
        analyzer = HierarchyAnalyzer()
        graph = analyzer.analyze(
            dc_area_report="synthesis/DC/report/area.rpt",
            rtl_files=["rtl/top.v", "rtl/sub.v"],
            timing_report="synthesis/DC/report/timing_setup.rpt",
        )
    """

    def __init__(self, gate_limit: int = 4_000_000):
        self.gate_limit = gate_limit

    def analyze(
        self,
        dc_area_report: str | Path | None = None,
        rtl_files: list[str | Path] | None = None,
        timing_report: str | Path | None = None,
        design_name: str = "top",
    ) -> ModuleGraph:
        """
        Build complete module graph from available sources.

        Priority:
        1. DC area report (most accurate gate counts)
        2. RTL files (module hierarchy and connectivity)
        3. Timing report (criticality attribution)
        """
        graph = ModuleGraph(design_name=design_name)
        graph.gate_limit = self.gate_limit

        # Parse DC area report
        if dc_area_report and Path(dc_area_report).exists():
            graph = self._parse_dc_area(dc_area_report, design_name)
            logger.info(f"Parsed DC area report: {graph.total_gate_count():,} gates")

        # If no DC report, try RTL
        if graph.root is None and rtl_files:
            graph = self._parse_rtl_hierarchy(rtl_files, design_name)
            logger.info(f"Parsed RTL hierarchy: {len(list(graph.root.walk())) if graph.root else 0} modules")

        # Annotate timing criticality
        if timing_report and Path(timing_report).exists():
            self._annotate_timing(graph, timing_report)

        return graph

    def _parse_dc_area(self, report_path: str | Path, design_name: str) -> ModuleGraph:
        """
        Parse DC hierarchical area report.

        Expected format (report_area -hierarchy):
        -----------------------------------------------------------
        Hierarchy                    Cell Area  Combinational  Sequential
        -----------------------------------------------------------
        top                          12345.6    5678           1234
          u_cpu                      8000.0     4000           800
            u_alu                    3000.0     2000           200
            u_regfile                2500.0     500            400
          u_mem                      2000.0     200            300
          u_periph                   1000.0     478            134
        -----------------------------------------------------------
        Total cell area: 12345.6
        """
        graph = ModuleGraph(design_name=design_name)
        graph.gate_limit = self.gate_limit

        text = Path(report_path).read_text(errors="ignore")
        lines = text.splitlines()

        # Find hierarchy section
        in_hierarchy = False
        hierarchy_lines = []
        dash_count = 0
        for line in lines:
            if re.match(r'^[-=]+$', line.strip()):
                dash_count += 1
                if dash_count == 2:  # Second dash line = end of header
                    in_hierarchy = True
                elif dash_count == 3:  # Third dash line = end of data
                    break
                continue
            if in_hierarchy:
                hierarchy_lines.append(line)
            elif dash_count == 1:
                # Skip header line between first and second dash
                pass

        if not hierarchy_lines:
            # Try alternative format: indented module names with numbers
            for line in lines:
                if re.match(r'^\s*\S+\s+[-.\d]+\s+\d+', line):
                    hierarchy_lines.append(line)

        # Parse hierarchy lines
        root = None
        stack: list[tuple[int, ModuleNode]] = []  # (indent_level, node)

        for line in hierarchy_lines:
            stripped_line = line.rstrip()
            if not stripped_line.strip():
                continue

            # Calculate indentation
            stripped = stripped_line.lstrip()
            indent = len(stripped_line) - len(stripped)

            # Parse: name area comb seq
            m = re.match(r'(\S+)\s+([-.\d]+)\s+(\d+)\s+(\d+)', stripped)
            if not m:
                # Try: name area
                m = re.match(r'(\S+)\s+([-.\d]+)', stripped)
                if not m:
                    continue
                name = m.group(1)
                area = float(m.group(2))
                comb = 0
                seq = 0
            else:
                name = m.group(1)
                area = float(m.group(2))
                comb = int(m.group(3))
                seq = int(m.group(4))

            node = ModuleNode(
                name=name,
                instance_path=name,
                metrics=ModuleMetrics(
                    gate_count=comb + seq,
                    area_um2=area,
                    num_comb_cells=comb,
                    num_seq_cells=seq,
                ),
            )

            if not stack:
                # Root module
                root = node
                stack.append((indent, node))
            else:
                # Find parent: pop stack until we find a node with less indentation
                while stack and stack[-1][0] >= indent:
                    stack.pop()

                if stack:
                    parent = stack[-1][1]
                    parent.add_child(node)
                    # Build instance path
                    node.instance_path = f"{parent.instance_path}/{name}"
                else:
                    root = node

                stack.append((indent, node))

        if root is None:
            root = ModuleNode(name=design_name)

        graph.root = root
        return graph

    def _parse_rtl_hierarchy(
        self, rtl_files: list[str | Path], design_name: str
    ) -> ModuleGraph:
        """
        Parse RTL Verilog files to extract module hierarchy.

        Extracts:
        - Module declarations
        - Module instantiations (instance_name: module_name(...))
        - Port counts
        """
        graph = ModuleGraph(design_name=design_name)
        graph.gate_limit = self.gate_limit

        # Collect all module definitions
        module_defs: dict[str, ModuleInfo] = {}

        for rtl_file in rtl_files:
            path = Path(rtl_file)
            if not path.exists():
                continue
            text = path.read_text(errors="ignore")
            self._extract_modules_from_verilog(text, module_defs)

        # Build hierarchy tree
        # Find top module
        top_module = module_defs.get(design_name)
        if top_module is None:
            # Try to find module with no parent (not instantiated by anyone)
            instantiated = set()
            for info in module_defs.values():
                for inst in info.instantiations:
                    instantiated.add(inst.module_name)
            for name, info in module_defs.items():
                if name not in instantiated:
                    top_module = info
                    break

        if top_module is None and module_defs:
            top_module = next(iter(module_defs.values()))

        if top_module is None:
            graph.root = ModuleNode(name=design_name)
            return graph

        # Build tree recursively
        root = self._build_tree(top_module, module_defs, set())
        graph.root = root

        return graph

    def _extract_modules_from_verilog(
        self, text: str, module_defs: dict[str, ModuleInfo]
    ):
        """Extract module definitions and instantiations from Verilog text."""
        # Remove comments
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # Find module declarations
        for m in re.finditer(
            r'module\s+(\w+)\s*(?:#\s*\([^)]*\))?\s*\(([^)]*)\)',
            text, re.DOTALL
        ):
            mod_name = m.group(1)
            ports_text = m.group(2)

            # Count ports
            port_count = len(re.findall(r'\b(input|output|inout)\b', ports_text))
            if port_count == 0:
                # Try ANSI style
                port_count = len(re.findall(r',', ports_text)) + 1 if ports_text.strip() else 0

            info = ModuleInfo(name=mod_name, num_ports=port_count)
            module_defs[mod_name] = info

        # Find instantiations
        # Pattern: module_name instance_name ( ... );
        # or: module_name #(params) instance_name ( ... );
        for m in re.finditer(
            r'(\w+)\s+(?:#\s*\([^)]*\)\s+)?(\w+)\s*\(',
            text
        ):
            mod_name = m.group(1)
            inst_name = m.group(2)

            # Skip keywords
            if mod_name in ('module', 'endmodule', 'input', 'output', 'inout',
                           'wire', 'reg', 'assign', 'always', 'initial',
                           'generate', 'if', 'for', 'case', 'begin'):
                continue
            if inst_name in ('module', 'endmodule'):
                continue

            # Find which module this instantiation belongs to
            # Look backwards for 'module' keyword
            pos = m.start()
            # Find the enclosing module
            enclosing = None
            for mm in re.finditer(r'module\s+(\w+)', text[:pos]):
                enclosing = mm.group(1)

            if enclosing and enclosing in module_defs:
                module_defs[enclosing].instantiations.append(
                    Instantiation(inst_name=inst_name, module_name=mod_name)
                )

    def _build_tree(
        self,
        module_info: ModuleInfo,
        all_modules: dict[str, ModuleInfo],
        visited: set[str],
    ) -> ModuleNode:
        """Recursively build module tree."""
        node = ModuleNode(
            name=module_info.name,
            instance_path=module_info.name,
            metrics=ModuleMetrics(
                num_ports=module_info.num_ports,
            ),
        )

        if module_info.name in visited:
            node.notes.append("circular reference detected")
            return node

        visited = visited | {module_info.name}

        for inst in module_info.instantiations:
            child_info = all_modules.get(inst.module_name)
            if child_info:
                child = self._build_tree(child_info, all_modules, visited)
                child.name = f"{inst.inst_name} ({inst.module_name})"
                child.instance_path = f"{node.instance_path}/{inst.inst_name}"
                node.add_child(child)
            else:
                # Leaf module (primitive or external)
                leaf = ModuleNode(
                    name=inst.inst_name,
                    instance_path=f"{node.instance_path}/{inst.inst_name}",
                )
                leaf.notes.append(f"module '{inst.module_name}' not found in RTL")
                node.add_child(leaf)

        return node

    def _annotate_timing(self, graph: ModuleGraph, timing_report: str | Path):
        """Annotate modules with timing criticality from timing report."""
        if graph.root is None:
            return

        text = Path(timing_report).read_text(errors="ignore")

        # Extract critical path cells
        critical_cells = set()
        for m in re.finditer(r'^\s*(\S+/\S+)\s+\(', text, re.MULTILINE):
            cell_path = m.group(1)
            # Extract module name from hierarchical path
            parts = cell_path.split("/")
            if len(parts) >= 2:
                critical_cells.add(parts[0])
                for i in range(1, len(parts) - 1):
                    critical_cells.add("/".join(parts[:i+1]))

        # Annotate nodes
        for node in graph.root.walk():
            path = node.instance_path
            if path in critical_cells or node.name in critical_cells:
                node.metrics.timing_criticality = TimingCriticality.CRITICAL
            elif any(c.startswith(path) for c in critical_cells):
                node.metrics.timing_criticality = TimingCriticality.MODERATE


@dataclass
class Instantiation:
    """A module instantiation."""
    inst_name: str
    module_name: str


@dataclass
class ModuleInfo:
    """Basic module info from RTL parsing."""
    name: str
    num_ports: int = 0
    instantiations: list[Instantiation] = field(default_factory=list)
