"""
rtlgen.spec_ir — Spec IR / Architecture IR / Optimizable Operators

Defines the intermediate representations that bridge natural-language specs
to PPA-aware RTL generation:

    Spec IR        → what the module should do (function, ports, PPA goals)
    ArchitectureIR → how to implement it (pipeline stages, operator style)
    OptimizableOp  → AST nodes with PPA hints for Mul, Add, etc.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from rtlgen.core import Expr, Module, Signal


# ---------------------------------------------------------------------
# Spec IR
# ---------------------------------------------------------------------

@dataclass
class PortSpec:
    """Single port description."""
    name: str
    direction: str   # "input" | "output"
    width: int = 1
    signed: bool = False


@dataclass
class FunctionSpec:
    """Behavioral description of the module."""
    expr: str = ""                          # e.g. "y = a * b + c"
    overflow: str = "truncate"              # "truncate" | "saturate" | "wrap"
    opcode_field: Optional[str] = None      # for ALUs: which input selects the operation
    operations: Optional[Dict[str, str]] = None  # opcode_value → expression


@dataclass
class InterfaceSpec:
    """Protocol interface (ready-valid, AXI, APB, etc.)."""
    input_protocol: str = "none"            # "none" | "ready_valid" | "axi4lite" | "apb"
    output_protocol: str = "none"
    input_payload: List[PortSpec] = field(default_factory=list)
    output_payload: List[PortSpec] = field(default_factory=list)


@dataclass
class TimingSpec:
    """Timing constraints."""
    latency_max: Optional[int] = None       # max cycles from input to output
    latency_exact: Optional[int] = None
    throughput: Optional[str] = None        # "1" (one per cycle) | "fractional" | "N"
    target_freq_mhz: Optional[float] = None


@dataclass
class PPASpec:
    """PPA goals and allowed optimizations."""
    priority: str = "balanced"              # "timing_first" | "area_first" | "power_first" | "balanced"
    max_area: Optional[int] = None          # gate count budget
    max_logic_depth: Optional[int] = None
    max_registers: Optional[int] = None
    max_power: Optional[float] = None
    allow_pipeline: bool = True
    allow_resource_sharing: bool = False
    allow_operator_rewrite: bool = True
    allow_fast_adder: bool = False
    allow_clock_gating: bool = False
    area_weight: float = 1.0
    timing_weight: float = 1.0
    reg_weight: float = 0.5
    power_weight: float = 1.0


@dataclass
class VerificationSpec:
    """Verification goals."""
    reference_model: Optional[str] = None   # Python expression for reference
    coverage_bins: List[str] = field(default_factory=list)
    protocol_checks: List[str] = field(default_factory=list)
    random_test_count: int = 100


@dataclass
class SpecIR:
    """Top-level specification intermediate representation."""
    name: str = "Module"
    category: str = "comb_alu"              # "comb_alu" | "register_update" | "fsm_controller" | "stream_pipeline"
    function: FunctionSpec = field(default_factory=FunctionSpec)
    ports: List[PortSpec] = field(default_factory=list)
    interfaces: Optional[InterfaceSpec] = None
    timing: TimingSpec = field(default_factory=TimingSpec)
    ppa: PPASpec = field(default_factory=PPASpec)
    verification: VerificationSpec = field(default_factory=VerificationSpec)
    reset_type: str = "sync"                # "sync" | "async"
    reset_active: str = "high"              # "high" | "low"
    reset_name: str = "rst"                 # reset signal name

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "SpecIR":
        """Parse a YAML spec string into SpecIR.

        Supports a simplified YAML subset — for full YAML use a proper parser.
        """
        try:
            import yaml
            data = yaml.safe_load(yaml_text)
        except ImportError:
            data = _parse_simple_yaml(yaml_text)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpecIR":
        """Build SpecIR from a nested dict."""
        spec = cls()

        mod = d.get("module", {})
        spec.name = mod.get("name", "Module")
        spec.category = mod.get("category", "comb_alu")

        func = d.get("function", {})
        spec.function = FunctionSpec(
            expr=func.get("expr", ""),
            overflow=func.get("overflow", "truncate"),
            opcode_field=func.get("opcode_field"),
            operations=func.get("operations"),
        )

        spec.ports = [
            PortSpec(name=p["name"], direction=p["dir"], width=p.get("width", 1), signed=p.get("signed", False))
            for p in d.get("ports", [])
        ]

        iface = d.get("interfaces", d.get("interface", None))
        if iface:
            in_proto = iface.get("input", {}).get("protocol", "none")
            out_proto = iface.get("output", {}).get("protocol", "none")
            in_payload = [
                PortSpec(name=p["name"], direction="input", width=p.get("width", 1), signed=p.get("signed", False))
                for p in iface.get("input", {}).get("payload", [])
            ]
            out_payload = [
                PortSpec(name=p["name"], direction="output", width=p.get("width", 1), signed=p.get("signed", False))
                for p in iface.get("output", {}).get("payload", [])
            ]
            spec.interfaces = InterfaceSpec(
                input_protocol=in_proto, output_protocol=out_proto,
                input_payload=in_payload, output_payload=out_payload,
            )

        tm = d.get("timing", {})
        spec.timing = TimingSpec(
            latency_max=tm.get("latency_max", tm.get("latency")),
            latency_exact=tm.get("latency_exact"),
            throughput=str(tm["throughput"]) if "throughput" in tm else None,
            target_freq_mhz=tm.get("target_freq_mhz"),
        )

        pp = d.get("ppa", {})
        spec.ppa = PPASpec(
            priority=pp.get("priority", "balanced"),
            max_area=pp.get("max_area"),
            max_logic_depth=pp.get("max_logic_depth"),
            max_registers=pp.get("max_registers"),
            max_power=pp.get("max_power"),
            allow_pipeline=pp.get("allow_pipeline", True),
            allow_resource_sharing=pp.get("allow_resource_sharing", False),
            allow_operator_rewrite=pp.get("allow_operator_rewrite", True),
            allow_fast_adder=pp.get("allow_fast_adder", False),
            allow_clock_gating=pp.get("allow_clock_gating", False),
        )

        vf = d.get("verification", {})
        spec.verification = VerificationSpec(
            reference_model=vf.get("reference_model"),
            coverage_bins=vf.get("coverage", []),
            protocol_checks=vf.get("protocol_checks", []),
            random_test_count=vf.get("random_test_count", 100),
        )

        # Assumptions
        assumptions = d.get("assumptions", {})
        spec.reset_type = assumptions.get("reset_type", spec.reset_type)
        spec.reset_active = assumptions.get("reset_active", spec.reset_active)
        spec.reset_name = assumptions.get("reset_name", spec.reset_name)

        return spec

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "module": {"name": self.name, "category": self.category},
            "function": {
                "expr": self.function.expr,
                "overflow": self.function.overflow,
                "opcode_field": self.function.opcode_field,
                "operations": self.function.operations,
            },
            "ports": [{"name": p.name, "dir": p.direction, "width": p.width, "signed": p.signed} for p in self.ports],
            "timing": {
                "latency_max": self.timing.latency_max,
                "throughput": self.timing.throughput,
                "target_freq_mhz": self.timing.target_freq_mhz,
            },
            "ppa": {
                "priority": self.ppa.priority,
                "max_area": self.ppa.max_area,
                "max_logic_depth": self.ppa.max_logic_depth,
                "max_registers": self.ppa.max_registers,
                "allow_pipeline": self.ppa.allow_pipeline,
                "allow_resource_sharing": self.ppa.allow_resource_sharing,
            },
        }

    def complete(self) -> "SpecIR":
        """Fill in missing defaults (Spec Completer)."""
        c = copy.deepcopy(self)
        if not c.reset_type:
            c.reset_type = "sync"
        if not c.reset_active:
            c.reset_active = "high"
        if not c.reset_name:
            c.reset_name = "rst"
        if c.interfaces and c.interfaces.input_protocol == "ready_valid":
            if "backpressure" not in c.verification.protocol_checks:
                c.verification.protocol_checks.append("backpressure")
            if "no_drop_no_duplicate" not in c.verification.protocol_checks:
                c.verification.protocol_checks.append("no_drop_no_duplicate")
        if "reset" not in c.verification.coverage_bins:
            c.verification.coverage_bins.append("reset")
        return c


# ---------------------------------------------------------------------
# Architecture IR
# ---------------------------------------------------------------------

@dataclass
class OperatorImpl:
    """Implementation choice for a specific operator."""
    style: str = "auto"         # "array" | "booth" | "wallace" | "dsp" | "ripple" | "carry_select" | "carry_lookahead"
    pipeline_stages: int = 1
    signed: bool = False


@dataclass
class StageSpec:
    """One pipeline / multi-cycle stage."""
    stage_id: int
    name: str
    ops: List[str]               # e.g. ["mul = a * b"]
    register_inputs: bool = True  # insert regs on stage inputs
    register_outputs: bool = True  # insert regs on stage outputs


@dataclass
class FlowControlSpec:
    """Flow control for the architecture."""
    flow_type: str = "none"          # "none" | "ready_valid" | "fsm"
    stall_policy: str = "stall_all"  # "stall_all" | "independent"
    skid_buffer: bool = False
    fsm_encoding: str = "auto"       # "auto" | "binary" | "one_hot" | "gray"


@dataclass
class ArchitectureIR:
    """Architecture-level intermediate representation.

    Captures HOW the module should be built: pipeline structure,
    operator implementations, and flow control.
    """
    arch_type: str = "combinational"  # "combinational" | "pipelined_datapath" | "multi_cycle" | "fsm_controlled"
    stages: List[StageSpec] = field(default_factory=list)
    operator_impl: Dict[str, OperatorImpl] = field(default_factory=dict)
    flow_control: FlowControlSpec = field(default_factory=FlowControlSpec)
    resource_sharing: Dict[str, Any] = field(default_factory=dict)
    clock_gating: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_stages(self) -> int:
        return len(self.stages)

    @property
    def estimated_latency(self) -> int:
        return self.total_stages


# ---------------------------------------------------------------------
# Optimizable Operators (AST nodes with PPA hints)
# ---------------------------------------------------------------------

class OptimizableOp(Expr):
    """Base class for optimizable arithmetic operators."""

    def __init__(self, op: str, operands: List[Expr], out_width: int,
                 impl: str = "auto", pipeline_stages: int = 1,
                 ppa_hint: str = "balanced", signed: bool = False):
        super().__init__(out_width)
        self.op = op
        self.operands = operands
        self.impl = impl
        self.pipeline_stages = pipeline_stages
        self.ppa_hint = ppa_hint
        self.signed = signed
        self._selected_impl: Optional[str] = None


class MulOp(OptimizableOp):
    """Optimizable multiplication with PPA hints."""
    impl_candidates = ["array", "booth", "wallace", "dsp"]

    def __init__(self, lhs: Expr, rhs: Expr, out_width: int = 0,
                 impl: str = "auto", pipeline_stages: int = 1,
                 ppa_hint: str = "balanced", signed: bool = False):
        if out_width == 0:
            out_width = lhs.width + rhs.width
        super().__init__("mul", [lhs, rhs], out_width, impl, pipeline_stages, ppa_hint, signed)


class AddOp(OptimizableOp):
    """Optimizable addition with PPA hints."""
    impl_candidates = ["ripple", "carry_lookahead", "carry_select", "prefix"]

    def __init__(self, lhs: Expr, rhs: Expr, out_width: int = 0,
                 impl: str = "auto", pipeline_stages: int = 1,
                 ppa_hint: str = "balanced", signed: bool = False):
        if out_width == 0:
            out_width = max(lhs.width, rhs.width) + 1
        super().__init__("add", [lhs, rhs], out_width, impl, pipeline_stages, ppa_hint, signed)


# ---------------------------------------------------------------------
# Simple YAML parser (fallback when PyYAML is not available)
# ---------------------------------------------------------------------

def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Minimal YAML-like parser for the Spec IR subset."""
    import re
    result: Dict[str, Any] = {}
    # Stack entries: (scope_dict, indent_level, list_key_or_None)
    # list_key: if the parent scope was created for a key that might hold a list
    stack: List[tuple] = [(result, -1, None)]

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Pop stack: remove scopes whose indent is >= current line's indent
        while len(stack) > 1 and stack[-1][1] >= indent:
            popped_dict, _, popped_key = stack.pop()
            # If the popped scope was empty and has a list_key, convert to a list
            if popped_key is not None and not popped_dict:
                grandparent = stack[-1][0]
                if isinstance(grandparent, dict) and popped_key in grandparent and grandparent[popped_key] is popped_dict:
                    grandparent[popped_key] = []

        parent_dict = stack[-1][0]

        # Pre-check: if current scope is an empty dict created for a potential list key
        # and the current line is a list item, convert now
        if stripped.startswith("- ") and len(stack) > 1 and stack[-1][2] is not None:
            pending_key = stack[-1][2]
            if not parent_dict:
                grandparent = stack[-1][0] if len(stack) < 2 else stack[-2][0]
                # Replace the empty dict with a list on the grandparent
                if isinstance(grandparent, dict):
                    grandparent[pending_key] = []
                # Pop this scope and continue
                stack.pop()
                # Re-run the pop logic and re-resolve parent
                while len(stack) > 1 and stack[-1][1] >= indent:
                    stack.pop()
                parent_dict = stack[-1][0]

        if stripped.startswith("- "):
            # List item line
            item_str = stripped[2:].strip()

            # Find the list to append to
            lst = _find_list_in_dict(parent_dict)
            if lst is None:
                # Fallback: use first word as key
                first_key = item_str.split(":")[0].strip()
                lst = []
                parent_dict[first_key] = lst

            if ":" in item_str:
                item: Dict[str, Any] = {}
                for kv in re.findall(r'(\w[\w_]*)\s*:\s*([^,}]+)', item_str):
                    k, v = kv
                    v = v.strip().strip('"').strip("'")
                    item[k] = _parse_value(v)
                lst.append(item)
                # Push item scope so sub-fields add to it
                stack.append((item, indent + 1, None))
            else:
                lst.append(_parse_value(item_str))

        elif ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if val:
                parent_dict[key] = _parse_value(val)
            else:
                child: Dict[str, Any] = {}
                parent_dict[key] = child
                stack.append((child, indent, key))

    return result


def _find_list_in_dict(d: Dict[str, Any]) -> Optional[List]:
    """Find the first list value in a dict, or None."""
    for v in d.values():
        if isinstance(v, list):
            return v
    return None


def _parse_value(v: str) -> Any:
    """Parse a YAML value string to Python type."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() == "null" or v == "~":
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v.strip('"').strip("'")
