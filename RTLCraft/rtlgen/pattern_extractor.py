"""
rtlgen.pattern_extractor — Extract Structural Patterns from Reference DSL Source

Parses reference DSL module Python source to extract:
  - Port declarations (name, width, direction)
  - State variables (Reg/Wire/Array with width and name)
  - Combinational logic blocks (assignments, control structures)
  - Sequential logic blocks (reset handling, state updates)
  - FSM structure (Switch-based state machines)
  - Handshake patterns (valid-ready fire conditions)
  - Data flow patterns (mux chains, priority encoders)

These patterns enrich ReferenceSummary so the LogicGenerator can
reference actual implementation structures rather than just metadata.

Reference: skills/plan_0525.md Section 4
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class PortInfo:
    """Extracted port declaration."""
    name: str
    width: str  # e.g., "ADDR_WIDTH", "1", "NUM_WARP"
    direction: str  # "input" | "output"
    line: int = 0


@dataclass
class StateInfo:
    """Extracted state variable."""
    name: str
    kind: str  # "Reg" | "Wire" | "Array"
    width: str
    size: str = ""  # for Array: depth
    line: int = 0


@dataclass
class LogicBlock:
    """Extracted logic block (comb or seq)."""
    block_type: str  # "comb" | "seq"
    line: int = 0
    assignments: List[str] = field(default_factory=list)  # "target <<= expr"
    if_conditions: List[str] = field(default_factory=list)
    switch_targets: List[str] = field(default_factory=list)
    for_loops: List[str] = field(default_factory=list)


@dataclass
class FSMInfo:
    """Extracted FSM structure."""
    state_reg: str = ""  # name of state register
    state_width: str = ""
    num_states: int = 0
    transitions: List[Tuple[str, str, str]] = field(default_factory=list)  # (from, to, condition)
    line: int = 0


@dataclass
class HandshakeInfo:
    """Extracted valid-ready handshake."""
    valid_signal: str = ""
    ready_signal: str = ""
    fire_condition: str = ""  # "valid & ready"
    payload_signals: List[str] = field(default_factory=list)
    line: int = 0


@dataclass
class ModulePattern:
    """Complete extracted pattern set from a DSL module."""
    module_name: str
    source_file: str
    class_line: int = 0
    docstring: str = ""
    ports: List[PortInfo] = field(default_factory=list)
    state_vars: List[StateInfo] = field(default_factory=list)
    comb_blocks: List[LogicBlock] = field(default_factory=list)
    seq_blocks: List[LogicBlock] = field(default_factory=list)
    fsm: Optional[FSMInfo] = None
    handshakes: List[HandshakeInfo] = field(default_factory=list)
    # Derived patterns for generation
    has_round_robin: bool = False
    has_fifo: bool = False
    has_scoreboard: bool = False
    has_pipeline: bool = False
    has_fsm: bool = False
    has_valid_ready: bool = False
    summary_patterns: List[str] = field(default_factory=list)


class PatternExtractor:
    """Extract structural patterns from DSL module source code.

    Usage:
        extractor = PatternExtractor()
        pattern = extractor.extract_from_file("skills/gpgpu/dsl_modules.py", "WarpScheduler")
        # or
        pattern = extractor.extract_from_source(source_text, "WarpScheduler")
    """

    def extract_from_file(self, filepath: str, class_name: str) -> Optional[ModulePattern]:
        """Extract patterns from a DSL module class in a file."""
        if not os.path.isfile(filepath):
            return None
        with open(filepath, "r") as f:
            source = f.read()
        return self.extract_from_source(source, class_name, filepath)

    def extract_from_source(self, source: str, class_name: str,
                            filepath: str = "") -> Optional[ModulePattern]:
        """Extract patterns from source text for a specific class."""
        tree = ast.parse(source)

        # Find the target class
        target_cls = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                target_cls = node
                break

        if target_cls is None:
            return None

        pattern = ModulePattern(
            module_name=class_name,
            source_file=filepath or "unknown",
            class_line=target_cls.lineno,
        )

        # Extract docstring
        pattern.docstring = self._get_docstring(target_cls)

        # Find __init__ method
        init_method = None
        for item in target_cls.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method is None:
            return pattern

        # Extract all blocks in __init__ (ports, state, comb, seq)
        self._extract_ports(init_method, pattern)
        self._extract_state_vars(init_method, pattern)
        self._extract_logic_blocks(init_method, pattern)

        # Also extract from decorated methods (alternative DSL syntax)
        self._extract_decorated_logic_blocks(target_cls, pattern)

        self._detect_derived_patterns(pattern)

        return pattern

    def extract_multi(self, filepath: str,
                      class_names: List[str]) -> Dict[str, ModulePattern]:
        """Extract patterns from multiple classes in one file."""
        results = {}
        for name in class_names:
            p = self.extract_from_file(filepath, name)
            if p:
                results[name] = p
        return results

    # ------------------------------------------------------------------
    # Internal: extraction helpers
    # ------------------------------------------------------------------

    def _get_docstring(self, cls_node: ast.ClassDef) -> str:
        """Get class docstring."""
        return ast.get_docstring(cls_node) or ""

    def _expr_str(self, node: ast.expr) -> str:
        """Convert an AST expression node to a string representation."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._expr_str(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return f"{self._expr_str(node.value)}[{self._expr_str(node.slice)}]"
        if isinstance(node, ast.BinOp):
            op_map = {
                ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
                ast.Div: "/", ast.Mod: "%", ast.LShift: "<<",
                ast.RShift: ">>", ast.BitOr: "|", ast.BitAnd: "&",
                ast.BitXor: "^",
            }
            op = op_map.get(type(node.op), "?")
            return f"({self._expr_str(node.left)} {op} {self._expr_str(node.right)})"
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return f"-{self._expr_str(node.operand)}"
            if isinstance(node.op, ast.Not):
                return f"~{self._expr_str(node.operand)}"
        if isinstance(node, ast.Compare):
            parts = []
            left = self._expr_str(node.left)
            for op, comp in zip(node.ops, node.comparators):
                op_map = {
                    ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<",
                    ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
                }
                o = op_map.get(type(op), "??")
                parts.append(f"{left} {o} {self._expr_str(comp)}")
            return " & ".join(parts)
        if isinstance(node, ast.List):
            elts = [self._expr_str(e) for e in node.elts]
            return "[" + ", ".join(elts) + "]"
        return ast.dump(node)

    def _extract_ports(self, init: ast.FunctionDef, pattern: ModulePattern):
        """Extract Input/Output port declarations."""
        for node in ast.walk(init):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Attribute):
                    continue
                # self.portname = Input(width, "name") or Output(width, "name")
                if not isinstance(node.value, ast.Call):
                    continue
                callee = node.value.func
                callee_name = self._expr_str(callee)
                if callee_name not in ("Input", "Output"):
                    continue

                # Extract width and name from args
                args = node.value.args
                width_str = self._expr_str(args[0]) if len(args) > 0 else "1"
                name_str = self._expr_str(args[1]) if len(args) > 1 else target.attr

                port = PortInfo(
                    name=target.attr,
                    width=width_str,
                    direction="output" if callee_name == "Output" else "input",
                    line=node.lineno,
                )
                pattern.ports.append(port)

    def _extract_state_vars(self, init: ast.FunctionDef, pattern: ModulePattern):
        """Extract Reg/Wire/Array state variables."""
        for node in ast.walk(init):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if not isinstance(node.value, ast.Call):
                    continue
                callee = node.value.func
                callee_name = self._expr_str(callee)
                if callee_name not in ("Reg", "Wire", "Array"):
                    continue

                args = node.value.args
                width_str = self._expr_str(args[0]) if len(args) > 0 else "1"
                name_str = self._expr_str(args[1]) if len(args) > 1 else target.attr
                size_str = self._expr_str(args[2]) if len(args) > 2 else ""

                state = StateInfo(
                    name=target.attr,
                    kind=callee_name,
                    width=width_str,
                    size=size_str,
                    line=node.lineno,
                )
                pattern.state_vars.append(state)

            # Also handle list comprehensions: self._pc = [Reg(...) for ...]
            if isinstance(node.value, ast.ListComp):
                elt = node.value.elt  # The expression being repeated
                gen = node.value.generators
                if isinstance(elt, ast.Call):
                    callee = elt.func
                    callee_name = self._expr_str(callee)
                    if callee_name in ("Reg", "Wire"):
                        args = elt.args
                        width_str = self._expr_str(args[0]) if len(args) > 0 else "1"
                        state = StateInfo(
                            name=target.attr,
                            kind=f"{callee_name}[]",  # array of Reg/Wire
                            width=width_str,
                            size=f"list_comp",
                            line=node.lineno,
                        )
                        pattern.state_vars.append(state)

    def _extract_logic_blocks(self, init: ast.FunctionDef, pattern: ModulePattern):
        """Extract comb/seq blocks and their internal structure.

        Handles two DSL syntax patterns:
        1. with self.comb: / with self.seq(clk, rst):  (context manager)
        2. @self.comb / @self.seq(clk, rst)            (decorator on method)
        """
        for node in ast.walk(init):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                expr = item.context_expr

                # Handle "with self.comb:" (Attribute)
                block_type = ""
                if isinstance(expr, ast.Attribute):
                    if expr.attr == "comb":
                        block_type = "comb"
                    elif expr.attr == "seq":
                        block_type = "seq"

                # Handle "with self.seq(clk, rst):" (Call with Attribute func)
                elif isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
                    if expr.func.attr == "seq":
                        block_type = "seq"

                if not block_type:
                    continue

                block = LogicBlock(
                    block_type=block_type,
                    line=node.lineno,
                )
                self._walk_logic_body(node.body, block, pattern)

                if block_type == "comb":
                    pattern.comb_blocks.append(block)
                else:
                    pattern.seq_blocks.append(block)

    def _extract_decorated_logic_blocks(self, cls_node: ast.ClassDef,
                                        pattern: ModulePattern):
        """Extract comb/seq blocks from decorated methods (alternative DSL syntax).

        Handles @self.comb and @self.seq(...) decorators on class methods.
        """
        for item in ast.walk(cls_node):
            if not isinstance(item, ast.FunctionDef):
                continue
            for decorator in item.decorator_list:
                block_type = ""

                # @self.comb
                if isinstance(decorator, ast.Attribute) and decorator.attr == "comb":
                    block_type = "comb"
                elif isinstance(decorator, ast.Attribute) and decorator.attr == "seq":
                    block_type = "seq"

                # @self.seq(clk, rst_n)
                elif (isinstance(decorator, ast.Call) and
                      isinstance(decorator.func, ast.Attribute)):
                    if decorator.func.attr == "seq":
                        block_type = "seq"

                if not block_type:
                    continue

                block = LogicBlock(
                    block_type=block_type,
                    line=item.lineno,
                )
                self._walk_logic_body(item.body, block, pattern)

                if block_type == "comb":
                    pattern.comb_blocks.append(block)
                else:
                    pattern.seq_blocks.append(block)

    def _walk_logic_body(self, body: list, block: LogicBlock,
                         pattern: ModulePattern, prefix: str = ""):
        """Recursively walk logic block body to extract patterns."""
        for node in body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    tgt = self._expr_str(target)
                    val = self._expr_str(node.value)
                    block.assignments.append(f"{tgt} = {val}")
            elif isinstance(node, ast.AugAssign):
                # target <<= value is AugAssign with LShift operator
                if isinstance(node.op, ast.LShift):
                    tgt = self._expr_str(node.target)
                    val = self._expr_str(node.value)
                    block.assignments.append(f"{tgt} <<= {val}")
                else:
                    tgt = self._expr_str(node.target)
                    val = self._expr_str(node.value)
                    block.assignments.append(f"{tgt} ??? {val}")
            elif isinstance(node, ast.If):
                cond = self._expr_str(node.test)
                block.if_conditions.append(f"if {cond}")
                self._walk_logic_body(node.body, block, pattern, prefix + "  ")
                self._walk_logic_body(node.orelse, block, pattern, prefix + "  ")

                # Detect Switch-based FSM
                self._try_detect_fsm(node, pattern)

            elif isinstance(node, ast.For):
                iter_str = self._expr_str(node.iter)
                block.for_loops.append(f"for in {iter_str}")
                self._walk_logic_body(node.body, block, pattern, prefix + "  ")

    def _try_detect_fsm(self, if_node: ast.If, pattern: ModulePattern):
        """Detect Switch-based FSM from comb block structure."""
        if pattern.fsm is not None:
            return

        for node in if_node.body:
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        callee = item.context_expr.func
                        if self._expr_str(callee) == "Switch":
                            # Found a Switch — likely FSM
                            switch_target = self._expr_str(
                                item.context_expr.args[0]
                            ) if item.context_expr.args else "unknown"

                            # Find the state register
                            state_reg = switch_target
                            if switch_target.startswith("_next_"):
                                # Corresponding state reg
                                state_reg = switch_target.replace("_next_", "_")

                            fsm = FSMInfo(
                                state_reg=state_reg,
                                line=if_node.lineno,
                            )

                            # Extract transitions from cases
                            self._extract_fsm_transitions(node.body, fsm)

                            pattern.fsm = fsm
                            pattern.has_fsm = True

    def _extract_fsm_transitions(self, body: list, fsm: FSMInfo):
        """Extract state transitions from Switch cases."""
        for node in body:
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Attribute):
                        case_name = item.context_expr.attr  # "case" or "default"
                        # Look for assignments inside: _next_state <<= X
                        for inner in ast.walk(node):
                            if isinstance(inner, ast.Assign):
                                for target in inner.targets:
                                    if isinstance(target, ast.Attribute):
                                        if "next_state" in target.attr or "next" in target.attr:
                                            from_state = case_name
                                            to_val = self._expr_str(inner.value)
                                            cond = ""
                                            # Check for If condition wrapping this
                                            fsm.transitions.append(
                                                (from_state, to_val, cond)
                                            )
                                            fsm.num_states += 1

    def _detect_derived_patterns(self, pattern: ModulePattern):
        """Detect high-level patterns from extracted structures."""
        src_all = ""
        for block in pattern.comb_blocks + pattern.seq_blocks:
            src_all += " ".join(block.assignments)
            src_all += " ".join(block.if_conditions)
            src_all += " ".join(block.for_loops)

        # Round-robin: rr_ptr + modular addition
        rr_keywords = ["rr_ptr", "next_warp", "next_sel", "priority_scan"]
        pattern.has_round_robin = any(
            kw in src_all for kw in rr_keywords
        ) or any(
            kw in src_all.lower() for kw in ["round", "robin", "rotate"]
        )

        # FIFO: head/tail pointers + push/pop
        fifo_keywords = ["fifo_head", "fifo_tail", "push", "pop", "full", "empty"]
        pattern.has_fifo = sum(
            1 for kw in fifo_keywords if kw in src_all.lower()
        ) >= 3

        # Scoreboard: busy bits + hazard check
        pattern.has_scoreboard = (
            "busy" in src_all.lower() and
            ("hazard" in src_all.lower() or "stall" in src_all.lower())
        )

        # Pipeline: stage_valid + stage_ready pattern
        pattern.has_pipeline = (
            "pipeline" in src_all.lower() or
            (src_all.count("_valid") >= 3 and src_all.count("_ready") >= 3)
        )

        # Valid-ready handshakes
        for port in pattern.ports:
            if "valid" in port.name.lower():
                for port2 in pattern.ports:
                    if "ready" in port2.name.lower():
                        pattern.has_valid_ready = True
                        hs = HandshakeInfo(
                            valid_signal=port.name,
                            ready_signal=port2.name,
                            fire_condition=f"{port.name} & {port2.name}",
                            line=port.line,
                        )
                        pattern.handshakes.append(hs)
                        break

        # Build summary patterns
        pattern.summary_patterns = self._build_summary_patterns(pattern)

    def _build_summary_patterns(self, pattern: ModulePattern) -> List[str]:
        """Build concise summary patterns for generation guidance."""
        summaries = []

        # Port summary
        input_count = sum(1 for p in pattern.ports if p.direction == "input")
        output_count = sum(1 for p in pattern.ports if p.direction == "output")
        if input_count or output_count:
            summaries.append(
                f"Interface: {input_count} inputs, {output_count} outputs"
            )

        # State summary
        reg_count = sum(1 for s in pattern.state_vars if "Reg" in s.kind)
        if reg_count:
            summaries.append(f"State: {reg_count} registers")

        # Logic summary
        comb_count = len(pattern.comb_blocks)
        seq_count = len(pattern.seq_blocks)
        if comb_count or seq_count:
            summaries.append(
                f"Logic: {comb_count} comb blocks, {seq_count} seq blocks"
            )

        # FSM
        if pattern.fsm:
            summaries.append(
                f"FSM: {pattern.fsm.state_reg} with {pattern.fsm.num_states} transitions"
            )

        # Handshakes
        if pattern.handshakes:
            hs_names = [f"{h.valid_signal}/{h.ready_signal}"
                        for h in pattern.handshakes[:3]]
            summaries.append(f"Handshakes: {', '.join(hs_names)}")

        # Derived patterns
        derived = []
        if pattern.has_round_robin:
            derived.append("round_robin")
        if pattern.has_fifo:
            derived.append("fifo")
        if pattern.has_scoreboard:
            derived.append("scoreboard")
        if pattern.has_pipeline:
            derived.append("pipeline")
        if pattern.has_fsm:
            derived.append("fsm")
        if derived:
            summaries.append(f"Patterns: {', '.join(derived)}")

        return summaries


# ---------------------------------------------------------------------------
# Convenience: batch extract from all DSL module files
# ---------------------------------------------------------------------------

_SKILL_DIRS = [
    "gpgpu", "cpu", "noc", "npu", "dsp", "fft",
    "hetero_riscv4", "riscv64_soc",
]


def extract_all_known_modules(skill_dir: Optional[str] = None,
                              base_path: str = "") -> Dict[str, ModulePattern]:
    """Extract patterns from all DSL modules in skill directories.

    Args:
        skill_dir: Specific skill to extract (e.g., "gpgpu")
        base_path: Base path to skills directory

    Returns:
        Dict[class_name, ModulePattern] for all extracted modules
    """
    if not base_path:
        # Try to locate skills relative to this module
        here = os.path.dirname(os.path.abspath(__file__))
        # /path/to/RTLCraft/rtlgen -> /path/to/RTLCraft/skills
        base_path = os.path.join(os.path.dirname(here), "skills")

    extractor = PatternExtractor()
    all_patterns: Dict[str, ModulePattern] = {}

    dirs = [skill_dir] if skill_dir else _SKILL_DIRS

    for sd in dirs:
        filepath = os.path.join(base_path, sd, "dsl_modules.py")
        if not os.path.isfile(filepath):
            continue

        # Get class names from the file
        with open(filepath, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        class_names = [
            node.name for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.ClassDef) and node.name != "Module"
        ]

        for name in class_names:
            p = extractor.extract_from_source(source, name, filepath)
            if p:
                all_patterns[f"{sd}:{name}"] = p

    return all_patterns
