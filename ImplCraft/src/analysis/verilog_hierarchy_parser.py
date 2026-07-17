"""
Verilog Hierarchy Parser for Partition Analysis

Extracts module hierarchy, instantiations, and connections from Verilog RTL files.
Provides the data structure needed for intelligent partition decisions.

Usage:
    parser = VerilogHierarchyParser()
    hierarchy = parser.parse_files(['top.v', 'sub1.v', 'sub2.v'])
    graph = hierarchy.build_module_graph()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .module_graph import ModuleGraph, ModuleNode, ModuleMetrics, PartitionDecision


@dataclass
class VerilogPort:
    """Represents a Verilog port."""
    name: str
    direction: str  # 'input', 'output', 'inout'
    width: int = 1
    start: int = 0
    end: int = 0
    
    @property
    def bit_count(self) -> int:
        """Total number of bits in this port."""
        if self.width == 0:
            return 1
        return abs(self.start - self.end) + 1


@dataclass
class VerilogInstance:
    """Represents a module instantiation."""
    instance_name: str
    module_name: str
    port_connections: dict[str, str] = field(default_factory=dict)
    parameters: dict[str, str] = field(default_factory=dict)
    line_number: int = 0


@dataclass
class VerilogModule:
    """Represents a Verilog module with its hierarchy information."""
    name: str
    ports: list[VerilogPort] = field(default_factory=list)
    instances: list[VerilogInstance] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)
    wire_count: int = 0
    reg_count: int = 0
    always_count: int = 0
    assign_count: int = 0
    file_path: str = ""
    line_number: int = 0
    
    @property
    def total_port_bits(self) -> int:
        """Total number of port bits."""
        return sum(p.bit_count for p in self.ports)
    
    @property
    def input_bits(self) -> int:
        """Number of input port bits."""
        return sum(p.bit_count for p in self.ports if p.direction == 'input')
    
    @property
    def output_bits(self) -> int:
        """Number of output port bits."""
        return sum(p.bit_count for p in self.ports if p.direction == 'output')
    
    @property
    def instance_count(self) -> int:
        """Number of module instances."""
        return len(self.instances)
    
    def get_child_modules(self) -> list[str]:
        """Get list of instantiated module names."""
        return [inst.module_name for inst in self.instances]
    
    def estimate_complexity(self) -> int:
        """Estimate module complexity (heuristic)."""
        # Simple heuristic: more instances + more ports = more complex
        return self.instance_count * 100 + self.total_port_bits


@dataclass
class VerilogHierarchy:
    """Complete hierarchy information from parsed Verilog files."""
    modules: dict[str, VerilogModule] = field(default_factory=dict)
    top_module: str = ""
    parse_errors: list[str] = field(default_factory=list)
    
    def get_module(self, name: str) -> VerilogModule | None:
        """Get module by name."""
        return self.modules.get(name)
    
    def get_hierarchy_depth(self, module_name: str) -> int:
        """Calculate hierarchy depth from a module."""
        visited = set()
        
        def depth(name: str) -> int:
            if name in visited:
                return 0
            visited.add(name)
            
            module = self.modules.get(name)
            if not module or not module.instances:
                return 1
            
            max_child_depth = 0
            for inst in module.instances:
                child_depth = depth(inst.module_name)
                max_child_depth = max(max_child_depth, child_depth)
            
            return 1 + max_child_depth
        
        return depth(module_name)
    
    def count_total_instances(self, module_name: str) -> int:
        """Count total instances in hierarchy."""
        module = self.modules.get(module_name)
        if not module:
            return 0
        
        count = 1  # Count this module
        for inst in module.instances:
            count += self.count_total_instances(inst.module_name)
        
        return count
    
    def build_module_graph(self) -> ModuleGraph:
        """Build ModuleGraph for partition analysis."""
        graph = ModuleGraph()
        
        # Create nodes for each module
        for name, module in self.modules.items():
            # Create metrics
            metrics = ModuleMetrics(
                gate_count=module.estimate_complexity(),
                num_ports=len(module.ports),
            )
            
            # Create node
            node = ModuleNode(
                name=name,
                metrics=metrics,
            )
            graph.add_node(node)
        
        # Add edges for instantiations
        for name, module in self.modules.items():
            for inst in module.instances:
                graph.add_edge(name, inst.module_name)
        
        # Set top module
        if self.top_module:
            graph.set_top_module(self.top_module)
        
        return graph
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "top_module": self.top_module,
            "modules": {
                name: {
                    "ports": len(mod.ports),
                    "port_bits": mod.total_port_bits,
                    "instances": mod.instance_count,
                    "children": mod.get_child_modules(),
                    "file": mod.file_path,
                }
                for name, mod in self.modules.items()
            },
            "hierarchy_depth": self.get_hierarchy_depth(self.top_module),
            "total_instances": self.count_total_instances(self.top_module),
            "parse_errors": self.parse_errors,
        }
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 70,
            f"Verilog Hierarchy Summary",
            "=" * 70,
            "",
            f"Top Module: {self.top_module}",
            f"Total Modules: {len(self.modules)}",
            f"Hierarchy Depth: {self.get_hierarchy_depth(self.top_module)}",
            f"Total Instances: {self.count_total_instances(self.top_module)}",
            "",
        ]
        
        if self.parse_errors:
            lines.append("Parse Errors:")
            for error in self.parse_errors:
                lines.append(f"  ⚠ {error}")
            lines.append("")
        
        # Show module hierarchy
        lines.append("Module Hierarchy:")
        
        def print_tree(name: str, indent: int = 0):
            module = self.modules.get(name)
            if not module:
                return
            
            prefix = "  " * indent
            info = f"{module.instance_count} insts, {len(module.ports)} ports"
            lines.append(f"{prefix}- {name} ({info})")
            
            for inst in module.instances:
                print_tree(inst.module_name, indent + 1)
        
        print_tree(self.top_module)
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)


class VerilogHierarchyParser:
    """
    Parser for extracting hierarchy from Verilog files.
    
    Focuses on:
    - Module declarations and ports
    - Module instantiations
    - Basic structure (wire/reg/always/assign counts)
    
    Does NOT perform full synthesis - only structural extraction.
    """
    
    def __init__(self):
        # Regex patterns for Verilog parsing
        
        # Module declaration: handles both styles
        # Style 1: module name (ports);
        # Style 2: module name #(...) (ports);
        self.module_pattern = re.compile(
            r'module\s+(\w+)\s*(?:#\s*\([^)]*\))?\s*\(([^)]*)\)\s*;',
            re.MULTILINE | re.DOTALL
        )
        
        # Port declarations inside module body
        self.port_pattern = re.compile(
            r'(input|output|inout)\s+(?:wire|reg)?\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',
            re.MULTILINE
        )
        
        # Module instantiation: handles multiple styles
        # Style 1: ModuleName inst_name (connections);
        # Style 2: ModuleName #(...) inst_name (connections);
        self.instance_pattern = re.compile(
            r'^\s*(\w+)\s+(?:#\s*\([^)]*\)\s+)?(\w+)\s*\(',
            re.MULTILINE
        )
        
        self.parameter_pattern = re.compile(
            r'parameter\s+(\w+)\s*=\s*([^,;]+)',
            re.MULTILINE
        )
        
    def parse_files(self, file_paths: list[str]) -> VerilogHierarchy:
        """Parse multiple Verilog files and build hierarchy."""
        hierarchy = VerilogHierarchy()
        
        # Parse each file
        for file_path in file_paths:
            try:
                modules = self._parse_file(file_path)
                for module in modules:
                    hierarchy.modules[module.name] = module
            except Exception as e:
                hierarchy.parse_errors.append(f"Error parsing {file_path}: {e}")
        
        # Find top module (module not instantiated by others)
        hierarchy.top_module = self._find_top_module(hierarchy)
        
        return hierarchy
    
    def _parse_file(self, file_path: str) -> list[VerilogModule]:
        """Parse a single Verilog file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text()
        modules = []
        
        # Find all module declarations
        for match in self.module_pattern.finditer(content):
            module_name = match.group(1)
            port_section = match.group(2)
            
            # Calculate line number
            line_number = content[:match.start()].count('\n') + 1
            
            # Create module
            module = VerilogModule(
                name=module_name,
                file_path=str(path),
                line_number=line_number,
            )
            
            # Extract module body
            module_start = match.end()
            # Find endmodule
            endmodule_pos = content.find('endmodule', module_start)
            if endmodule_pos == -1:
                endmodule_pos = len(content)
            
            module_body = content[module_start:endmodule_pos]
            
            # Parse ports from module body (not just header)
            module.ports = self._parse_ports(module_body)
            
            # Parse instances
            module.instances = self._parse_instances(module_body)
            
            # Parse parameters
            module.parameters = self._parse_parameters(module_body)
            
            # Count basic constructs
            module.wire_count = len(re.findall(r'\bwire\b', module_body))
            module.reg_count = len(re.findall(r'\breg\b', module_body))
            module.always_count = len(re.findall(r'\balways\b', module_body))
            module.assign_count = len(re.findall(r'\bassign\b', module_body))
            
            modules.append(module)
        
        return modules
    
    def _parse_ports(self, module_body: str) -> list[VerilogPort]:
        """Parse port declarations from module body."""
        ports = []
        
        # Look for input/output/inout declarations
        for match in self.port_pattern.finditer(module_body):
            direction = match.group(1)
            start = int(match.group(2)) if match.group(2) else 0
            end = int(match.group(3)) if match.group(3) else 0
            name = match.group(4)
            
            width = abs(start - end) + 1 if match.group(2) else 1
            
            port = VerilogPort(
                name=name,
                direction=direction,
                width=width,
                start=start,
                end=end,
            )
            ports.append(port)
        
        return ports
    
    def _parse_instances(self, module_body: str) -> list[VerilogInstance]:
        """Parse module instantiations."""
        instances = []
        
        # Filter out common false positives
        keywords = {'module', 'endmodule', 'input', 'output', 'inout', 'wire', 'reg', 
                   'assign', 'always', 'initial', 'begin', 'end', 'if', 'else', 'case',
                   'for', 'while', 'function', 'task', 'generate'}
        
        for match in self.instance_pattern.finditer(module_body):
            module_name = match.group(1)
            instance_name = match.group(2)
            
            # Skip if it's a keyword
            if module_name in keywords:
                continue
            
            # Skip if it looks like a system task or primitive
            if module_name.startswith('$') or module_name in {'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor'}:
                continue
            
            # Skip if instance name is a keyword
            if instance_name in keywords:
                continue
            
            line_number = module_body[:match.start()].count('\n') + 1
            
            instance = VerilogInstance(
                instance_name=instance_name,
                module_name=module_name,
                line_number=line_number,
            )
            instances.append(instance)
        
        return instances
    
    def _parse_parameters(self, module_body: str) -> dict[str, str]:
        """Parse parameter declarations."""
        parameters = {}
        
        for match in self.parameter_pattern.finditer(module_body):
            name = match.group(1)
            value = match.group(2).strip()
            parameters[name] = value
        
        return parameters
    
    def _find_top_module(self, hierarchy: VerilogHierarchy) -> str:
        """Find the top module (not instantiated by others)."""
        # Collect all instantiated module names
        instantiated = set()
        for module in hierarchy.modules.values():
            for inst in module.instances:
                instantiated.add(inst.module_name)
        
        # Top module is one that's not instantiated
        for name in hierarchy.modules.keys():
            if name not in instantiated:
                return name
        
        # If all modules are instantiated, return first one
        if hierarchy.modules:
            return next(iter(hierarchy.modules.keys()))
        
        return ""
