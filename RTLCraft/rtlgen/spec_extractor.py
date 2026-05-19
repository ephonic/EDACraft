"""
rtlgen.spec_extractor — Natural-Language Spec Extraction + Spec Completer

Two entry points:
1. Extractor: Parse natural-language descriptions or structured dicts into SpecIR
2. Completer: Fill in missing defaults and cross-field consistency
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from rtlgen.spec_ir import (
    FlowControlSpec,
    FunctionSpec,
    InterfaceSpec,
    PortSpec,
    PPASpec,
    SpecIR,
    TimingSpec,
    VerificationSpec,
)


# ---------------------------------------------------------------------------
# Spec Completer
# ---------------------------------------------------------------------------

class SpecCompleter:
    """Fill in missing defaults and enforce cross-field consistency."""

    DEFAULTS = {
        "reset_type": "sync",
        "reset_active": "high",
        "reset_name": "rst",
        "overflow": "truncate",
        "ppa_priority": "balanced",
        "allow_pipeline": True,
        "allow_resource_sharing": False,
        "allow_operator_rewrite": True,
        "allow_fast_adder": False,
        "allow_clock_gating": False,
        "random_test_count": 100,
    }

    @classmethod
    def complete(cls, spec: SpecIR) -> SpecIR:
        """Return a completed copy of the spec with all fields populated."""
        import copy
        c = copy.deepcopy(spec)

        # Module defaults
        if not c.name:
            c.name = "Module"
        if not c.category:
            c.category = cls._infer_category(c)

        # Auto-infer ports from expression if none specified
        if not c.ports:
            c.ports = cls._infer_ports_from_expr(c.function.expr)

        # Normalize bare expressions to assignment form (e.g. "a + b" → "out=a + b")
        if c.function.expr and "=" not in c.function.expr:
            output_names = [p.name for p in c.ports if p.direction == "output"]
            out_name = output_names[0] if output_names else "out"
            c.function.expr = f"{out_name}={c.function.expr}"
            if not output_names:
                c.ports.append(PortSpec(name="out", direction="output", width=8))

        # Reset defaults
        if not c.reset_type:
            c.reset_type = cls.DEFAULTS["reset_type"]
        if not c.reset_active:
            c.reset_active = cls.DEFAULTS["reset_active"]
        if not c.reset_name:
            c.reset_name = cls.DEFAULTS["reset_name"]

        # Function defaults
        if not c.function.overflow:
            c.function.overflow = cls.DEFAULTS["overflow"]

        # PPA defaults
        pp = c.ppa
        if not pp.priority:
            pp.priority = cls.DEFAULTS["ppa_priority"]
        if not pp.allow_pipeline:
            pp.allow_pipeline = cls.DEFAULTS["allow_pipeline"]
        # allow_resource_sharing defaults to False (already dataclass default)
        # allow_operator_rewrite defaults to True
        # allow_fast_adder defaults to False
        # allow_clock_gating defaults to False

        # Timing defaults
        if c.timing.throughput and c.timing.latency_max is None:
            if c.timing.throughput == "1":
                c.timing.latency_max = 1

        # Interface completion
        if c.interfaces:
            cls._complete_interfaces(c)

        # Verification defaults
        cls._complete_verification(c)

        # Cross-field consistency
        cls._enforce_consistency(c)

        return c

    @classmethod
    def _infer_ports_from_expr(cls, expr: str) -> List[PortSpec]:
        """Infer port specs from expression when none are provided."""
        import re
        # Strip assignment: "y = a * b + c" → inputs: [a, b, c], output: [y]
        lhs = ""
        rhs = expr
        if "=" in expr:
            lhs, rhs = expr.split("=", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()

        # Find all identifiers in RHS (inputs)
        input_names = set(re.findall(r'\b([a-zA-Z_]\w*)\b', rhs))
        # Filter out common keywords
        input_names -= {"and", "or", "not", "xor", "nand", "nor"}

        # Default width
        default_width = 8

        ports: List[PortSpec] = []
        for name in sorted(input_names):
            ports.append(PortSpec(name=name, direction="input", width=default_width))

        if lhs:
            ports.append(PortSpec(name=lhs, direction="output", width=default_width * 2))
        else:
            # Bare expression without assignment — add a default output
            ports.append(PortSpec(name="out", direction="output", width=default_width * 2))

        return ports

    @classmethod
    def _infer_category(cls, spec: SpecIR) -> str:
        """Infer module category from function expression and ports."""
        expr = spec.function.expr.lower()
        ports = spec.ports

        # Has opcode_field → ALU
        if spec.function.opcode_field or spec.function.operations:
            return "comb_alu"

        # Has ready_valid interface → stream_pipeline
        if spec.interfaces:
            if spec.interfaces.input_protocol == "ready_valid" or spec.interfaces.output_protocol == "ready_valid":
                return "stream_pipeline"

        # Expression has only increment/decrement pattern → register_update
        if re.search(r'\+\s*1|-\s*1', expr):
            if not any(p.direction == "input" for p in ports if "opcode" in p.name.lower()):
                return "register_update"

        # Expression with mul/add and no state → comb_alu
        if any(op in expr for op in ["*", "+", "-", "&", "|", "^"]):
            return "comb_alu"

        # Default
        return "comb_alu"

    @classmethod
    def _complete_interfaces(cls, spec: SpecIR):
        """Add protocol-specific verification checks and defaults."""
        iface = spec.interfaces
        if iface.input_protocol == "ready_valid" or iface.output_protocol == "ready_valid":
            vc = spec.verification
            if "backpressure" not in vc.protocol_checks:
                vc.protocol_checks.append("backpressure")
            if "no_drop_no_duplicate" not in vc.protocol_checks:
                vc.protocol_checks.append("no_drop_no_duplicate")

            # Add handshake ports if not already present
            cls._ensure_handshake_ports(spec, iface)

    @classmethod
    def _ensure_handshake_ports(cls, spec: SpecIR, iface: InterfaceSpec):
        """Add in_valid/in_ready/out_valid/out_ready ports if missing."""
        existing_names = {p.name for p in spec.ports}

        if iface.input_protocol == "ready_valid":
            if "in_valid" not in existing_names:
                spec.ports.append(PortSpec(name="in_valid", direction="input", width=1))
            if "in_ready" not in existing_names:
                spec.ports.append(PortSpec(name="in_ready", direction="output", width=1))

        if iface.output_protocol == "ready_valid":
            if "out_valid" not in existing_names:
                spec.ports.append(PortSpec(name="out_valid", direction="output", width=1))
            if "out_ready" not in existing_names:
                spec.ports.append(PortSpec(name="out_ready", direction="input", width=1))

    @classmethod
    def _complete_verification(cls, spec: SpecIR):
        """Fill in verification defaults based on category and interfaces."""
        vc = spec.verification
        if not vc.reference_model:
            vc.reference_model = cls._build_reference_model(spec)

        # Always include reset coverage
        if "reset" not in vc.coverage_bins:
            vc.coverage_bins.append("reset")

        # Category-specific bins
        if spec.category == "comb_alu":
            if "corner_cases" not in vc.coverage_bins:
                vc.coverage_bins.append("corner_cases")
        elif spec.category == "stream_pipeline":
            if "pipeline_full" not in vc.coverage_bins:
                vc.coverage_bins.append("pipeline_full")
            if "backpressure" not in vc.coverage_bins:
                vc.coverage_bins.append("backpressure")

    @classmethod
    def _build_reference_model(cls, spec: SpecIR) -> Optional[str]:
        """Generate a simple Python reference model from the function expression."""
        expr = spec.function.expr.strip()
        if not expr:
            return None

        # Simple translation: RTL/SystemVerilog-like → Python
        ref = expr

        # Replace bit-slice notation a[7:0] with masked version
        ref = re.sub(r'(\w+)\[(\d+):(\d+)\]', r'(\1 >> \3) & ((1 << (\2 - \3 + 1)) - 1)', ref)

        # Replace bitwise &/|/^ that might need masking (for unsigned)
        # Keep as-is for Python since it handles arbitrary precision

        # Replace ** with ** (already Python compatible)
        # Replace multiplication sign variants
        ref = ref.replace("×", "*")

        # Extract port names for lambda args
        port_names = [p.name for p in spec.ports if p.direction == "input"]
        if port_names:
            args = ", ".join(port_names)
            return f"lambda {args}: {ref}"

        return f"lambda **kwargs: {ref}"

    @classmethod
    def _enforce_consistency(cls, spec: SpecIR):
        """Cross-field consistency checks and corrections."""
        # If pipeline is not allowed, max latency must be 1
        if not spec.ppa.allow_pipeline and spec.timing.latency_max is None:
            spec.timing.latency_max = 1

        # If timing_first and no pipeline allowed, flag resource sharing
        if spec.ppa.priority == "timing_first" and not spec.ppa.allow_pipeline:
            # Resource sharing hurts timing — disable if not explicitly set
            if not spec.ppa.allow_resource_sharing:
                spec.ppa.allow_resource_sharing = False

        # If power_first, enable clock gating if not explicitly disabled
        if spec.ppa.priority == "power_first":
            if not spec.ppa.allow_clock_gating:
                spec.ppa.allow_clock_gating = True


# ---------------------------------------------------------------------------
# Spec Extractor — from natural language or structured dict
# ---------------------------------------------------------------------------

class SpecExtractor:
    """Extract SpecIR from natural-language descriptions or structured inputs."""

    # Common operator patterns for parsing expressions
    _OPCODE_PATTERNS = {
        "add": r"\w+\s*\+\s*\w+",
        "sub": r"\w+\s*-\s*\w+",
        "mul": r"\w+\s*\*\s*\w+",
        "and": r"\w+\s*&\s*\w+",
        "or": r"\w*\s*\|\s*\w+",
        "xor": r"\w+\s*\^\s*\w+",
        "shl": r"\w+\s*<<\s*\w+",
        "shr": r"\w+\s*>>\s*\w+",
    }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpecIR:
        """Alias for SpecIR.from_dict (already implemented in spec_ir.py)."""
        return SpecIR.from_dict(data)

    @classmethod
    def from_yaml(cls, yaml_text: str) -> SpecIR:
        """Alias for SpecIR.from_yaml (already implemented in spec_ir.py)."""
        return SpecIR.from_yaml(yaml_text)

    @classmethod
    def from_natural_language(cls, text: str) -> SpecIR:
        """Extract SpecIR from a natural-language description.

        This is a simple rule-based extractor. For full NL understanding,
        integrate with an LLM.
        """
        spec = SpecIR()

        # Extract module name
        name_match = re.search(r'(?:module|design|block)\s+(\w+)', text, re.IGNORECASE)
        if name_match:
            spec.name = name_match.group(1)

        # Detect category from keywords
        lower = text.lower()
        if any(w in lower for w in ["alu", "arithmetic", "combinational"]):
            spec.category = "comb_alu"
        elif any(w in lower for w in ["counter", "accumulate", "register update"]):
            spec.category = "register_update"
        elif any(w in lower for w in ["fsm", "state machine", "controller"]):
            spec.category = "fsm_controller"
        elif any(w in lower for w in ["pipeline", "stream", "ready.valid", "handshake"]):
            spec.category = "stream_pipeline"

        # Extract expression
        expr_match = re.search(r'(\w+\s*=\s*.+?)(?:\.|$)', text)
        if expr_match:
            spec.function.expr = expr_match.group(1).strip()

        # Detect ALU-style opcode
        opcode_match = re.search(r'(?:opcode|operation|op)\s*(?:field\s+)?(\w+)', text, re.IGNORECASE)
        if opcode_match:
            spec.function.opcode_field = opcode_match.group(1)

        # Detect operations list
        ops = {}
        for op_name, pattern in cls._OPCODE_PATTERNS.items():
            if re.search(pattern, text):
                ops[op_name] = pattern
        if ops:
            spec.function.operations = ops

        # Extract port specs
        port_matches = re.findall(r'(\w+)\s*:\s*(?:input|output)\s*(?:(\d+)-?bit)?\s*(signed|unsigned)?', text, re.IGNORECASE)
        for name, width, sign in port_matches:
            spec.ports.append(PortSpec(
                name=name,
                direction="input" if "input" in text.split(name)[1][:10].lower() else "output",
                width=int(width) if width else 1,
                signed=(sign.lower() == "signed"),
            ))

        # Detect timing constraints
        latency_match = re.search(r'(?:latency|max.?latency)\s*(?:of\s+|<=\s+|is\s+)?(\d+)\s*(?:cycles?)?', text, re.IGNORECASE)
        if latency_match:
            spec.timing.latency_max = int(latency_match.group(1))

        freq_match = re.search(r'(?:frequency|target)\s*(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:mhz|MHz)', text, re.IGNORECASE)
        if freq_match:
            spec.timing.target_freq_mhz = float(freq_match.group(1))

        throughput_match = re.search(r'throughput\s*(?:of\s+)?(\d+(?:/\d+)?)', text, re.IGNORECASE)
        if throughput_match:
            spec.timing.throughput = throughput_match.group(1)

        # Detect PPA priority
        if "timing" in lower and ("critical" in lower or "fast" in lower or "high frequency" in lower):
            spec.ppa.priority = "timing_first"
        elif "area" in lower and ("small" in lower or "compact" in lower or "budget" in lower):
            spec.ppa.priority = "area_first"
        elif "power" in lower and ("low power" in lower or "power efficient" in lower):
            spec.ppa.priority = "power_first"

        # Detect pipeline allowance
        if "pipeline" in lower and ("allow" in lower or "support" in lower or "can" in lower):
            spec.ppa.allow_pipeline = True
        elif "no pipeline" in lower or "single cycle" in lower:
            spec.ppa.allow_pipeline = False

        # Detect resource sharing
        if "share" in lower and ("resource" in lower or "operator" in lower or "unit" in lower):
            spec.ppa.allow_resource_sharing = True

        # Detect clock gating
        if "clock gating" in lower or "clock gate" in lower or "power_first" in lower:
            spec.ppa.allow_clock_gating = True

        # Detect reset style
        if "async" in lower and "reset" in lower:
            spec.reset_type = "async"
        if "active low" in lower or "active-low" in lower:
            spec.reset_active = "low"

        # Detect ready-valid interface
        if "ready" in lower and "valid" in lower:
            spec.interfaces = InterfaceSpec(
                input_protocol="ready_valid",
                output_protocol="ready_valid",
            )

        return spec

    @classmethod
    def from_template(cls, template_name: str, **kwargs) -> SpecIR:
        """Create a SpecIR from a named template.

        Supported templates:
        - "mac": Multiply-Accumulate
        - "alu": N-input ALU with opcode
        - "counter": Simple up/down counter
        - "fifo": Ready-valid FIFO wrapper
        - "fsm": State machine controller
        """
        templates: Dict[str, Dict[str, Any]] = {
            "mac": {
                "module": {"name": "MAC", "category": "stream_pipeline"},
                "function": {"expr": "y = a * b + c"},
                "ports": [
                    {"name": "a", "dir": "input", "width": kwargs.get("width", 16)},
                    {"name": "b", "dir": "input", "width": kwargs.get("width", 16)},
                    {"name": "c", "dir": "input", "width": kwargs.get("width", 16) * 2},
                    {"name": "y", "dir": "output", "width": kwargs.get("width", 16) * 2},
                ],
                "timing": {"latency_max": kwargs.get("latency", 2), "throughput": 1},
                "ppa": {"priority": kwargs.get("priority", "balanced"), "allow_pipeline": True},
                "assumptions": {"reset_type": "sync", "reset_active": "high", "reset_name": "rst"},
            },
            "alu": {
                "module": {"name": kwargs.get("name", "ALU"), "category": "comb_alu"},
                "function": {
                    "expr": "result = a op b",
                    "opcode_field": kwargs.get("opcode_name", "op"),
                    "operations": {
                        "000": "a + b",
                        "001": "a - b",
                        "010": "a & b",
                        "011": "a | b",
                        "100": "a ^ b",
                        "101": "a << b[2:0]",
                        "110": "a >> b[2:0]",
                        "111": "a * b",
                    },
                },
                "ports": [
                    {"name": "a", "dir": "input", "width": kwargs.get("width", 8)},
                    {"name": "b", "dir": "input", "width": kwargs.get("width", 8)},
                    {"name": "op", "dir": "input", "width": kwargs.get("opcode_width", 3)},
                    {"name": "result", "dir": "output", "width": kwargs.get("width", 8) * 2},
                ],
                "ppa": {"priority": kwargs.get("priority", "balanced")},
                "assumptions": {"reset_type": "sync", "reset_active": "high", "reset_name": "rst"},
            },
            "counter": {
                "module": {"name": kwargs.get("name", "Counter"), "category": "register_update"},
                "function": {"expr": "count = count + 1"},
                "ports": [
                    {"name": "count", "dir": "output", "width": kwargs.get("width", 8)},
                ],
                "timing": {"latency_max": 1},
                "ppa": {"priority": kwargs.get("priority", "area_first"), "allow_pipeline": False},
                "assumptions": {"reset_type": "sync", "reset_active": kwargs.get("reset_active", "high"), "reset_name": "rst"},
            },
            "fifo": {
                "module": {"name": kwargs.get("name", "StreamFIFO"), "category": "stream_pipeline"},
                "function": {"expr": "y = x"},
                "interfaces": {
                    "input": {"protocol": "ready_valid", "payload": [{"name": "data", "width": kwargs.get("width", 32)}]},
                    "output": {"protocol": "ready_valid", "payload": [{"name": "data", "width": kwargs.get("width", 32)}]},
                },
                "timing": {"throughput": 1},
                "ppa": {"priority": kwargs.get("priority", "balanced"), "allow_pipeline": True},
                "verification": {"protocol_checks": ["backpressure", "no_drop_no_duplicate"]},
                "assumptions": {"reset_type": kwargs.get("reset_type", "sync"), "reset_active": kwargs.get("reset_active", "high"), "reset_name": "rst"},
            },
            "fsm": {
                "module": {"name": kwargs.get("name", "FSMController"), "category": "fsm_controller"},
                "function": {"expr": "next_state = f(current_state, inputs)"},
                "ports": [
                    {"name": "state", "dir": "output", "width": kwargs.get("state_width", 2)},
                ],
                "ppa": {"priority": kwargs.get("priority", "balanced")},
                "assumptions": {"reset_type": "sync", "reset_active": "high", "reset_name": "rst"},
            },
        }

        if template_name not in templates:
            raise ValueError(
                f"Unknown template '{template_name}'. "
                f"Available: {', '.join(templates.keys())}"
            )

        return SpecIR.from_dict(templates[template_name])
