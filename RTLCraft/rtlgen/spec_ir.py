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
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from rtlgen.core import Expr, Module, Signal

IR_SCHEMA_VERSION = "2026-06-11.v2"


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
class TestVectorIR:
    """Directed test vector used across lowering stages."""
    name: str
    inputs: Dict[str, int] = field(default_factory=dict)
    expected_outputs: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "inputs": dict(self.inputs),
            "expected_outputs": dict(self.expected_outputs),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TestVectorIR":
        return cls(
            name=d.get("name", ""),
            inputs=dict(d.get("inputs", {})),
            expected_outputs=dict(d.get("expected_outputs", {})),
        )


@dataclass
class CoverageBinIR:
    """Coverage target for structured verification review."""
    name: str
    description: str = ""
    kind: str = "functional"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CoverageBinIR":
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            kind=d.get("kind", "functional"),
        )


@dataclass
class AssertionIR:
    """Assertion intent for generated verification collateral."""
    name: str
    expr: str
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssertionIR":
        return cls(
            name=d.get("name", ""),
            expr=d.get("expr", ""),
            severity=d.get("severity", "error"),
        )


@dataclass
class TracepointIR:
    """Named tracepoint projected across IR layers."""
    name: str
    signals: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TracepointIR":
        return cls(
            name=d.get("name", ""),
            signals=list(d.get("signals", [])),
            description=d.get("description", ""),
        )


@dataclass
class ScoreboardIR:
    """Cross-reference between reference and RTL observations."""
    name: str
    reference: str
    implementation: str
    compare: str = "exact"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScoreboardIR":
        return cls(
            name=d.get("name", ""),
            reference=d.get("reference", ""),
            implementation=d.get("implementation", ""),
            compare=d.get("compare", "exact"),
        )


@dataclass
class ProtocolIR:
    """Protocol boundary projected from module contracts into review IR."""
    name: str
    kind: str
    recipe: str = ""
    request_signals: List[str] = field(default_factory=list)
    response_signals: List[str] = field(default_factory=list)
    flow_control_signals: List[str] = field(default_factory=list)
    ordering: str = "in_order"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProtocolIR":
        return cls(
            name=d.get("name", ""),
            kind=d.get("kind", ""),
            recipe=d.get("recipe", ""),
            request_signals=list(d.get("request_signals", [])),
            response_signals=list(d.get("response_signals", [])),
            flow_control_signals=list(d.get("flow_control_signals", [])),
            ordering=d.get("ordering", "in_order"),
            description=d.get("description", ""),
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class TransactionIR:
    """Transaction boundary shared by behavior and verification plans."""
    name: str
    trigger_signals: List[str] = field(default_factory=list)
    completion_signals: List[str] = field(default_factory=list)
    recipe: str = ""
    trigger_event: str = "level"
    completion_event: str = "level"
    trigger_qualifiers: List[str] = field(default_factory=list)
    completion_qualifiers: List[str] = field(default_factory=list)
    max_cycles: Optional[int] = None
    sample_cycles: int = 0
    ordering: str = "in_order"
    allow_overlap: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransactionIR":
        return cls(
            name=d.get("name", ""),
            trigger_signals=list(d.get("trigger_signals", [])),
            completion_signals=list(d.get("completion_signals", [])),
            recipe=d.get("recipe", ""),
            trigger_event=d.get("trigger_event", "level"),
            completion_event=d.get("completion_event", "level"),
            trigger_qualifiers=list(d.get("trigger_qualifiers", [])),
            completion_qualifiers=list(d.get("completion_qualifiers", [])),
            max_cycles=d.get("max_cycles"),
            sample_cycles=int(d.get("sample_cycles", 0) or 0),
            ordering=d.get("ordering", "in_order"),
            allow_overlap=bool(d.get("allow_overlap", False)),
            description=d.get("description", ""),
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class VerificationPlanIR:
    """Structured verification plan shared across IR layers."""
    module_name: str
    schema_version: str = IR_SCHEMA_VERSION
    directed_tests: List[TestVectorIR] = field(default_factory=list)
    coverage_bins: List[CoverageBinIR] = field(default_factory=list)
    assertions: List[AssertionIR] = field(default_factory=list)
    tracepoints: List[TracepointIR] = field(default_factory=list)
    scoreboards: List[ScoreboardIR] = field(default_factory=list)
    protocols: List[ProtocolIR] = field(default_factory=list)
    transactions: List[TransactionIR] = field(default_factory=list)
    protocol_checks: List[str] = field(default_factory=list)
    random_test_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "module_name": self.module_name,
            "directed_tests": [item.to_dict() for item in self.directed_tests],
            "coverage_bins": [item.to_dict() for item in self.coverage_bins],
            "assertions": [item.to_dict() for item in self.assertions],
            "tracepoints": [item.to_dict() for item in self.tracepoints],
            "scoreboards": [item.to_dict() for item in self.scoreboards],
            "protocols": [item.to_dict() for item in self.protocols],
            "transactions": [item.to_dict() for item in self.transactions],
            "protocol_checks": list(self.protocol_checks),
            "random_test_count": self.random_test_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VerificationPlanIR":
        return cls(
            module_name=d.get("module_name", "Module"),
            schema_version=d.get("schema_version", IR_SCHEMA_VERSION),
            directed_tests=[TestVectorIR.from_dict(item) for item in d.get("directed_tests", [])],
            coverage_bins=[CoverageBinIR.from_dict(item) for item in d.get("coverage_bins", [])],
            assertions=[AssertionIR.from_dict(item) for item in d.get("assertions", [])],
            tracepoints=[TracepointIR.from_dict(item) for item in d.get("tracepoints", [])],
            scoreboards=[ScoreboardIR.from_dict(item) for item in d.get("scoreboards", [])],
            protocols=[ProtocolIR.from_dict(item) for item in d.get("protocols", [])],
            transactions=[TransactionIR.from_dict(item) for item in d.get("transactions", [])],
            protocol_checks=list(d.get("protocol_checks", [])),
            random_test_count=int(d.get("random_test_count", 0) or 0),
        )


@dataclass
class SpecIR:
    """Top-level specification intermediate representation."""
    name: str = "Module"
    schema_version: str = IR_SCHEMA_VERSION
    category: str = "comb_alu"              # "comb_alu" | "register_update" | "fsm_controller" | "stream_pipeline" | "hierarchical"
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
        spec.schema_version = d.get("schema_version", IR_SCHEMA_VERSION)

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
        interfaces = None
        if self.interfaces:
            interfaces = {
                "input": {
                    "protocol": self.interfaces.input_protocol,
                    "payload": [
                        {
                            "name": p.name,
                            "width": p.width,
                            "signed": p.signed,
                        }
                        for p in self.interfaces.input_payload
                    ],
                },
                "output": {
                    "protocol": self.interfaces.output_protocol,
                    "payload": [
                        {
                            "name": p.name,
                            "width": p.width,
                            "signed": p.signed,
                        }
                        for p in self.interfaces.output_payload
                    ],
                },
            }
        return {
            "schema_version": self.schema_version,
            "module": {"name": self.name, "category": self.category},
            "function": {
                "expr": self.function.expr,
                "overflow": self.function.overflow,
                "opcode_field": self.function.opcode_field,
                "operations": self.function.operations,
            },
            "ports": [{"name": p.name, "dir": p.direction, "width": p.width, "signed": p.signed} for p in self.ports],
            "interfaces": interfaces,
            "timing": {
                "latency_max": self.timing.latency_max,
                "latency_exact": self.timing.latency_exact,
                "throughput": self.timing.throughput,
                "target_freq_mhz": self.timing.target_freq_mhz,
            },
            "ppa": {
                "priority": self.ppa.priority,
                "max_area": self.ppa.max_area,
                "max_logic_depth": self.ppa.max_logic_depth,
                "max_registers": self.ppa.max_registers,
                "max_power": self.ppa.max_power,
                "allow_pipeline": self.ppa.allow_pipeline,
                "allow_resource_sharing": self.ppa.allow_resource_sharing,
                "allow_operator_rewrite": self.ppa.allow_operator_rewrite,
                "allow_fast_adder": self.ppa.allow_fast_adder,
                "allow_clock_gating": self.ppa.allow_clock_gating,
            },
            "verification": {
                "reference_model": self.verification.reference_model,
                "coverage": list(self.verification.coverage_bins),
                "protocol_checks": list(self.verification.protocol_checks),
                "random_test_count": self.verification.random_test_count,
            },
            "assumptions": {
                "reset_type": self.reset_type,
                "reset_active": self.reset_active,
                "reset_name": self.reset_name,
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
# Behavior / Cycle / Structural IR
# ---------------------------------------------------------------------

@dataclass
class AssumptionIR:
    """Reviewable assumption carried across lowerings."""
    kind: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssumptionIR":
        return cls(kind=d.get("kind", ""), detail=d.get("detail", ""))


@dataclass
class InvariantIR:
    """High-level behavioral invariant."""
    name: str
    expr: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InvariantIR":
        return cls(name=d.get("name", ""), expr=d.get("expr", ""))


@dataclass
class BehaviorRuleIR:
    """One behavior-level rule."""
    rule_id: str
    trigger: str
    effect: str
    category: str = "functional"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BehaviorRuleIR":
        return cls(
            rule_id=d.get("rule_id", ""),
            trigger=d.get("trigger", "always"),
            effect=d.get("effect", ""),
            category=d.get("category", "functional"),
        )


@dataclass
class BehaviorIR:
    """Serializable behavior-level IR for review and checking."""
    module_name: str
    schema_version: str = IR_SCHEMA_VERSION
    ports: List[PortSpec] = field(default_factory=list)
    function_expr: str = ""
    required_behaviors: List[str] = field(default_factory=list)
    rules: List[BehaviorRuleIR] = field(default_factory=list)
    assumptions: List[AssumptionIR] = field(default_factory=list)
    invariants: List[InvariantIR] = field(default_factory=list)
    tracepoints: List[str] = field(default_factory=list)
    protocols: List[ProtocolIR] = field(default_factory=list)
    transactions: List[TransactionIR] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "module_name": self.module_name,
            "ports": [
                {"name": p.name, "dir": p.direction, "width": p.width, "signed": p.signed}
                for p in self.ports
            ],
            "function_expr": self.function_expr,
            "required_behaviors": list(self.required_behaviors),
            "rules": [rule.to_dict() for rule in self.rules],
            "assumptions": [item.to_dict() for item in self.assumptions],
            "invariants": [item.to_dict() for item in self.invariants],
            "tracepoints": list(self.tracepoints),
            "protocols": [item.to_dict() for item in self.protocols],
            "transactions": [item.to_dict() for item in self.transactions],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BehaviorIR":
        return cls(
            module_name=d.get("module_name", "Module"),
            schema_version=d.get("schema_version", IR_SCHEMA_VERSION),
            ports=[
                PortSpec(
                    name=p.get("name", ""),
                    direction=p.get("dir", p.get("direction", "input")),
                    width=p.get("width", 1),
                    signed=p.get("signed", False),
                )
                for p in d.get("ports", [])
            ],
            function_expr=d.get("function_expr", ""),
            required_behaviors=list(d.get("required_behaviors", [])),
            rules=[BehaviorRuleIR.from_dict(item) for item in d.get("rules", [])],
            assumptions=[AssumptionIR.from_dict(item) for item in d.get("assumptions", [])],
            invariants=[InvariantIR.from_dict(item) for item in d.get("invariants", [])],
            tracepoints=list(d.get("tracepoints", [])),
            protocols=[ProtocolIR.from_dict(item) for item in d.get("protocols", [])],
            transactions=[TransactionIR.from_dict(item) for item in d.get("transactions", [])],
        )


@dataclass
class StateIR:
    """One cycle-visible piece of state."""
    name: str
    width: int = 1
    kind: str = "reg"
    reset_value: str = "0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StateIR":
        return cls(
            name=d.get("name", ""),
            width=d.get("width", 1),
            kind=d.get("kind", "reg"),
            reset_value=str(d.get("reset_value", "0")),
        )


@dataclass
class StateUpdateIR:
    """Next-state update rule for one state."""
    state: str
    when: str
    next_expr: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StateUpdateIR":
        return cls(
            state=d.get("state", ""),
            when=d.get("when", "always"),
            next_expr=d.get("next_expr", ""),
        )


@dataclass
class HandshakeRuleIR:
    """Cycle-level handshake rule."""
    interface: str
    rule: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HandshakeRuleIR":
        return cls(interface=d.get("interface", ""), rule=d.get("rule", ""))


@dataclass
class TraceEventIR:
    """Observable trace event for cross-layer comparison."""
    name: str
    condition: str
    observed_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TraceEventIR":
        return cls(
            name=d.get("name", ""),
            condition=d.get("condition", "always"),
            observed_signals=list(d.get("observed_signals", [])),
        )


@dataclass
class TransactionEventIR:
    """Cycle-level event boundary for a transaction."""
    name: str
    event: str = "level"
    signals: List[str] = field(default_factory=list)
    qualifiers: List[str] = field(default_factory=list)
    condition: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransactionEventIR":
        return cls(
            name=d.get("name", ""),
            event=d.get("event", "level"),
            signals=list(d.get("signals", [])),
            qualifiers=list(d.get("qualifiers", [])),
            condition=d.get("condition", ""),
        )


@dataclass
class CycleTransactionIR:
    """Cycle-level transaction boundary projected from behavior contracts."""
    name: str
    recipe: str = ""
    trigger: TransactionEventIR = field(default_factory=lambda: TransactionEventIR(name="trigger"))
    completion: TransactionEventIR = field(default_factory=lambda: TransactionEventIR(name="completion"))
    max_cycles: Optional[int] = None
    sample_cycles: int = 0
    ordering: str = "in_order"
    allow_overlap: bool = False
    temporal_relation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "recipe": self.recipe,
            "trigger": self.trigger.to_dict(),
            "completion": self.completion.to_dict(),
            "max_cycles": self.max_cycles,
            "sample_cycles": self.sample_cycles,
            "ordering": self.ordering,
            "allow_overlap": self.allow_overlap,
            "temporal_relation": self.temporal_relation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CycleTransactionIR":
        return cls(
            name=d.get("name", ""),
            recipe=d.get("recipe", ""),
            trigger=TransactionEventIR.from_dict(d.get("trigger", {"name": "trigger"})),
            completion=TransactionEventIR.from_dict(d.get("completion", {"name": "completion"})),
            max_cycles=d.get("max_cycles"),
            sample_cycles=int(d.get("sample_cycles", 0) or 0),
            ordering=d.get("ordering", "in_order"),
            allow_overlap=bool(d.get("allow_overlap", False)),
            temporal_relation=d.get("temporal_relation", ""),
        )


@dataclass
class CycleIR:
    """Serializable cycle-level IR."""
    module_name: str
    schema_version: str = IR_SCHEMA_VERSION
    latency: Optional[int] = None
    throughput: Optional[str] = None
    states: List[StateIR] = field(default_factory=list)
    updates: List[StateUpdateIR] = field(default_factory=list)
    handshakes: List[HandshakeRuleIR] = field(default_factory=list)
    trace_events: List[TraceEventIR] = field(default_factory=list)
    transactions: List[CycleTransactionIR] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "module_name": self.module_name,
            "latency": self.latency,
            "throughput": self.throughput,
            "states": [state.to_dict() for state in self.states],
            "updates": [update.to_dict() for update in self.updates],
            "handshakes": [rule.to_dict() for rule in self.handshakes],
            "trace_events": [event.to_dict() for event in self.trace_events],
            "transactions": [txn.to_dict() for txn in self.transactions],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CycleIR":
        return cls(
            module_name=d.get("module_name", "Module"),
            schema_version=d.get("schema_version", IR_SCHEMA_VERSION),
            latency=d.get("latency"),
            throughput=d.get("throughput"),
            states=[StateIR.from_dict(item) for item in d.get("states", [])],
            updates=[StateUpdateIR.from_dict(item) for item in d.get("updates", [])],
            handshakes=[HandshakeRuleIR.from_dict(item) for item in d.get("handshakes", [])],
            trace_events=[TraceEventIR.from_dict(item) for item in d.get("trace_events", [])],
            transactions=[CycleTransactionIR.from_dict(item) for item in d.get("transactions", [])],
        )


@dataclass
class ClockResetDomainIR:
    """Clock/reset assumptions for structural review."""
    clock: str = "clk"
    reset: str = "rst"
    reset_type: str = "sync"
    reset_active: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClockResetDomainIR":
        return cls(
            clock=d.get("clock", "clk"),
            reset=d.get("reset", "rst"),
            reset_type=d.get("reset_type", "sync"),
            reset_active=d.get("reset_active", "high"),
        )


@dataclass
class StructuralIR:
    """Serializable structural refinement layer."""
    module_name: str
    schema_version: str = IR_SCHEMA_VERSION
    hierarchy_mode: str = "monolithic"
    ports: List[PortSpec] = field(default_factory=list)
    submodules: List["SubmoduleInstanceSpec"] = field(default_factory=list)
    connections: List["ConnectionSpec"] = field(default_factory=list)
    clock_reset: ClockResetDomainIR = field(default_factory=ClockResetDomainIR)
    internal_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "module_name": self.module_name,
            "hierarchy_mode": self.hierarchy_mode,
            "ports": [
                {"name": p.name, "dir": p.direction, "width": p.width, "signed": p.signed}
                for p in self.ports
            ],
            "submodules": [sm.to_dict() for sm in self.submodules],
            "connections": [conn.to_dict() for conn in self.connections],
            "clock_reset": self.clock_reset.to_dict(),
            "internal_signals": list(self.internal_signals),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StructuralIR":
        return cls(
            module_name=d.get("module_name", "Module"),
            schema_version=d.get("schema_version", IR_SCHEMA_VERSION),
            hierarchy_mode=d.get("hierarchy_mode", "monolithic"),
            ports=[
                PortSpec(
                    name=p.get("name", ""),
                    direction=p.get("dir", p.get("direction", "input")),
                    width=p.get("width", 1),
                    signed=p.get("signed", False),
                )
                for p in d.get("ports", [])
            ],
            submodules=[SubmoduleInstanceSpec(**item) for item in d.get("submodules", [])],
            connections=[ConnectionSpec(**item) for item in d.get("connections", [])],
            clock_reset=ClockResetDomainIR.from_dict(d.get("clock_reset", {})),
            internal_signals=list(d.get("internal_signals", [])),
        )


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
class OperationSpec:
    """One arithmetic / logical operation in the micro-architecture plan."""
    op_id: int
    kind: str
    output: str
    inputs: List[str]
    expr: str
    width: int = 1
    stage_id: Optional[int] = None
    signed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegisterTransferSpec:
    """Register inserted at a stage boundary."""
    name: str
    source: str
    width: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FSMStateSpec:
    """Structured FSM state description for review / lowering."""
    name: str
    encoding: int
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HandshakeIR:
    """Protocol-level handshake description."""
    valid_in: Optional[str] = None
    ready_out: Optional[str] = None
    ready_in: Optional[str] = None
    valid_out: Optional[str] = None
    stall_signal: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubmoduleInstanceSpec:
    """Future-facing structural refinement placeholder."""
    module_type: str
    instance_name: str
    port_map: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConnectionSpec:
    """Future-facing structural connection placeholder."""
    source: str
    sink: str
    signal: str
    width: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StageSpec:
    """One pipeline / multi-cycle stage."""
    stage_id: int
    name: str
    ops: List[str]               # e.g. ["mul = a * b"]
    operation_specs: List[OperationSpec] = field(default_factory=list)
    registers: List[RegisterTransferSpec] = field(default_factory=list)
    register_inputs: bool = True  # insert regs on stage inputs
    register_outputs: bool = True  # insert regs on stage outputs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "ops": list(self.ops),
            "operation_specs": [op.to_dict() for op in self.operation_specs],
            "registers": [reg.to_dict() for reg in self.registers],
            "register_inputs": self.register_inputs,
            "register_outputs": self.register_outputs,
        }


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
    arch_type: str = "combinational"  # "combinational" | "pipelined_datapath" | "multi_cycle" | "fsm_controlled" | "hierarchical"
    stages: List[StageSpec] = field(default_factory=list)
    operator_impl: Dict[str, OperatorImpl] = field(default_factory=dict)
    flow_control: FlowControlSpec = field(default_factory=FlowControlSpec)
    resource_sharing: Dict[str, Any] = field(default_factory=dict)
    clock_gating: Dict[str, Any] = field(default_factory=dict)
    signal_widths: Dict[str, int] = field(default_factory=dict)
    output_names: List[str] = field(default_factory=list)
    handshake: Optional[HandshakeIR] = None
    fsm_states: List[FSMStateSpec] = field(default_factory=list)
    submodules: List[SubmoduleInstanceSpec] = field(default_factory=list)
    connections: List[ConnectionSpec] = field(default_factory=list)

    @property
    def total_stages(self) -> int:
        return len(self.stages)

    @property
    def estimated_latency(self) -> int:
        return self.total_stages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arch_type": self.arch_type,
            "stages": [stage.to_dict() for stage in self.stages],
            "operator_impl": {
                name: asdict(impl) for name, impl in self.operator_impl.items()
            },
            "flow_control": asdict(self.flow_control),
            "resource_sharing": dict(self.resource_sharing),
            "clock_gating": dict(self.clock_gating),
            "signal_widths": dict(self.signal_widths),
            "output_names": list(self.output_names),
            "handshake": None if self.handshake is None else self.handshake.to_dict(),
            "fsm_states": [state.to_dict() for state in self.fsm_states],
            "submodules": [sm.to_dict() for sm in self.submodules],
            "connections": [conn.to_dict() for conn in self.connections],
        }


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
