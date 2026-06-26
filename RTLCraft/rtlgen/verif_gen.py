"""
rtlgen.verif_gen — Verification Generator

Generates from SpecIR:
1. Python reference model from function expression
2. Directed tests (zero, max, boundary)
3. Random tests with coverage tracking
4. Protocol assertions (ready-valid rules)
5. Coverage bins
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.spec_ir import PortSpec, SpecIR


# ---------------------------------------------------------------------------
# Reference Model
# ---------------------------------------------------------------------------

class ReferenceModel:
    """Python reference model generated from SpecIR function expression."""

    def __init__(self, spec: SpecIR):
        self.spec = spec
        self._fn: Optional[Callable] = None
        self._build()

    def _build(self):
        expr = self.spec.function.expr.strip()
        if not expr:
            self._fn = None
            return

        # Strip assignment: "y = a * b + c" → "a * b + c"
        if "=" in expr:
            _, expr = expr.split("=", 1)
            expr = expr.strip()

        # Extract port names for lambda args
        input_ports = [p for p in self.spec.ports if p.direction == "input"]
        port_names = [p.name for p in input_ports]

        # Translate expression to Python
        py_expr = self._translate_expr(expr)

        if port_names:
            args_str = ", ".join(port_names)
            try:
                self._fn = eval(f"lambda {args_str}: {py_expr}")
            except Exception:
                self._fn = None
        else:
            self._fn = None

    def _translate_expr(self, expr: str) -> str:
        """Translate RTL-like expression to Python."""
        # Replace bit-slice a[7:0] → (a >> 0) & ((1 << 8) - 1)
        def replace_slice(m):
            var = m.group(1)
            hi = int(m.group(2))
            lo = int(m.group(3))
            width = hi - lo + 1
            return f"(({var} >> {lo}) & ((1 << {width}) - 1))"

        result = re.sub(r'(\w+)\[(\d+):(\d+)\]', replace_slice, expr)

        # Replace bitwise operators (Python uses same symbols, so mostly no-op)
        # Handle multiplication
        result = result.replace("×", "*")

        return result

    def evaluate(self, **inputs: int) -> Optional[int]:
        """Evaluate the reference model with given inputs."""
        if self._fn is None:
            return None
        try:
            # Build kwargs from input port names
            kwargs = {}
            for port in self.spec.ports:
                if port.direction == "input" and port.name in inputs:
                    kwargs[port.name] = inputs[port.name]
            return self._fn(**kwargs)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Test Generator
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    """A single test case with inputs and expected output."""
    inputs: Dict[str, int]
    expected: Optional[int] = None
    expected_outputs: Optional[Dict[str, int]] = None  # for multi-output modules
    name: str = ""
    description: str = ""


@dataclass
class TestResult:
    """Result of running a test."""
    passed: bool
    test_case: TestCase
    actual: Optional[int] = None
    actual_outputs: Optional[Dict[str, int]] = None  # for multi-output modules
    error: str = ""


class TestGenerator:
    """Generate test vectors from SpecIR."""

    def __init__(self, spec: SpecIR):
        self.spec = spec
        self.ref_model = ReferenceModel(spec)

    def generate_directed(self) -> List[TestCase]:
        """Generate directed tests: zero, max, boundary, corner cases."""
        tests: List[TestCase] = []

        input_ports = [p for p in self.spec.ports if p.direction == "input"]

        # Zero test: all inputs = 0
        zero_inputs = {p.name: 0 for p in input_ports}
        zero_expected = self.ref_model.evaluate(**zero_inputs)
        tests.append(TestCase(
            inputs=zero_inputs,
            expected=zero_expected,
            name="all_zeros",
            description="All inputs set to zero",
        ))

        # Max test: all inputs = max value
        max_inputs = {}
        for p in input_ports:
            max_val = (1 << p.width) - 1
            max_inputs[p.name] = max_val
        max_expected = self.ref_model.evaluate(**max_inputs)
        tests.append(TestCase(
            inputs=max_inputs,
            expected=max_expected,
            name="all_max",
            description="All inputs set to maximum value",
        ))

        # Boundary tests: one input at max, rest at zero
        for p in input_ports:
            boundary_inputs = {port.name: 0 for port in input_ports}
            boundary_inputs[p.name] = (1 << p.width) - 1
            boundary_expected = self.ref_model.evaluate(**boundary_inputs)
            tests.append(TestCase(
                inputs=boundary_inputs,
                expected=boundary_expected,
                name=f"max_{p.name}",
                description=f"Only {p.name} at maximum",
            ))

        # Powers of 2
        for p in input_ports:
            for exp in range(p.width):
                pow_inputs = {port.name: 0 for port in input_ports}
                pow_inputs[p.name] = 1 << exp
                pow_expected = self.ref_model.evaluate(**pow_inputs)
                tests.append(TestCase(
                    inputs=pow_inputs,
                    expected=pow_expected,
                    name=f"pow2_{p.name}_{exp}",
                    description=f"{p.name} = 2^{exp}",
                ))

        # ALU-specific: test each opcode
        if self.spec.function.opcode_field and self.spec.function.operations:
            opcode_port = next(
                (p for p in input_ports if p.name == self.spec.function.opcode_field),
                None,
            )
            if opcode_port:
                for opcode_val, expr in self.spec.function.operations.items():
                    opcode_int = int(opcode_val, 2) if isinstance(opcode_val, str) else opcode_val
                    alu_inputs = {p.name: 0xAB for p in input_ports if p.name != self.spec.function.opcode_field}
                    alu_inputs[self.spec.function.opcode_field] = opcode_int
                    alu_expected = self.ref_model.evaluate(**alu_inputs)
                    tests.append(TestCase(
                        inputs=alu_inputs,
                        expected=alu_expected,
                        name=f"opcode_{opcode_val}",
                        description=f"ALU opcode {opcode_val}: {expr}",
                    ))

        return tests

    def generate_random(self, count: int = 100, seed: Optional[int] = None) -> List[TestCase]:
        """Generate random test vectors."""
        if seed is not None:
            random.seed(seed)
        else:
            random.seed()

        tests: List[TestCase] = []
        input_ports = [p for p in self.spec.ports if p.direction == "input"]

        for i in range(count):
            inputs = {}
            for p in input_ports:
                max_val = (1 << p.width) - 1
                inputs[p.name] = random.randint(0, max_val)

            expected = self.ref_model.evaluate(**inputs)
            tests.append(TestCase(
                inputs=inputs,
                expected=expected,
                name=f"random_{i}",
            ))

        return tests

    def generate_protocol_tests(self) -> List[TestCase]:
        """Generate protocol-specific tests for ready-valid interfaces."""
        tests: List[TestCase] = []
        iface = self.spec.interfaces

        if iface is None:
            return tests

        # Ready-valid: test backpressure
        if iface.input_protocol == "ready_valid" or iface.output_protocol == "ready_valid":
            tests.append(TestCase(
                inputs={"in_valid": 1, "out_ready": 0},
                name="backpressure_assert",
                description="Valid asserted but not ready — data should not be consumed",
            ))
            tests.append(TestCase(
                inputs={"in_valid": 1, "out_ready": 1},
                name="normal_transfer",
                description="Valid and ready — data should transfer",
            ))
            tests.append(TestCase(
                inputs={"in_valid": 0, "out_ready": 1},
                name="no_valid",
                description="No valid — no transfer should occur",
            ))

        return tests


# ---------------------------------------------------------------------------
# Coverage Tracker
# ---------------------------------------------------------------------------

@dataclass
class CoverageBin:
    """A coverage bin tracking hits."""
    name: str
    hits: int = 0
    total_samples: int = 0

    @property
    def coverage(self) -> float:
        return self.hits / max(self.total_samples, 1)


class SpecCoverageTracker:
    """Track coverage metrics during verification (SpecIR-based).

    Uses SpecIR verification bins and input port coverage.
    For ProcessingElement-based coverage tracking, use CoverageTracker
    from rtlgen.arch_def instead.
    """

    def __init__(self, spec: SpecIR):
        self.spec = spec
        self.bins: Dict[str, CoverageBin] = {}

        # Initialize bins from spec
        for bin_name in spec.verification.coverage_bins:
            self.bins[bin_name] = CoverageBin(name=bin_name)

        # Add input port coverage bins
        for port in spec.ports:
            if port.direction == "input":
                self.bins[f"input_{port.name}"] = CoverageBin(name=f"input_{port.name}")

    def sample(self, inputs: Dict[str, int]):
        """Record a sample of input values."""
        for name, value in inputs.items():
            bin_key = f"input_{name}"
            if bin_key in self.bins:
                self.bins[bin_key].hits += 1
                self.bins[bin_key].total_samples += 1

    def record_protocol_event(self, event: str):
        """Record a protocol-specific event."""
        if event in self.bins:
            self.bins[event].hits += 1
            self.bins[event].total_samples += 1

    def summary(self) -> Dict[str, Any]:
        """Return coverage summary."""
        total_bins = len(self.bins)
        hit_bins = sum(1 for b in self.bins.values() if b.hits > 0)

        return {
            "total_bins": total_bins,
            "hit_bins": hit_bins,
            "coverage_pct": (hit_bins / max(total_bins, 1)) * 100,
            "bin_details": {
                name: {"hits": b.hits, "total": b.total_samples}
                for name, b in self.bins.items()
            },
        }


# ---------------------------------------------------------------------------
# Verification Runner
# ---------------------------------------------------------------------------

@dataclass
class VerificationReport:
    """Complete verification report."""
    directed_tests: int = 0
    directed_passed: int = 0
    directed_failed: int = 0
    random_tests: int = 0
    random_passed: int = 0
    random_failed: int = 0
    protocol_tests: int = 0
    protocol_passed: int = 0
    protocol_failed: int = 0
    coverage: Dict[str, Any] = field(default_factory=dict)
    failures: List[TestResult] = field(default_factory=list)

    @property
    def total_tests(self) -> int:
        return self.directed_tests + self.random_tests + self.protocol_tests

    @property
    def total_passed(self) -> int:
        return self.directed_passed + self.random_passed + self.protocol_passed

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return (self.total_passed / self.total_tests) * 100

    @property
    def all_passed(self) -> bool:
        return self.total_failed == 0

    @property
    def total_failed(self) -> int:
        return self.directed_failed + self.random_failed + self.protocol_failed


class VerificationRunner:
    """Run verification tests against a DUT (simulator callable)."""

    def __init__(self, spec: SpecIR, dut_callable: Callable):
        """
        Args:
            spec: The SpecIR specification
            dut_callable: Callable that takes a dict of inputs and returns a dict of outputs
        """
        self.spec = spec
        self.dut = dut_callable
        self.test_gen = TestGenerator(spec)
        self.coverage = CoverageTracker(spec)

    def run(self, random_count: int = 0, seed: Optional[int] = 42) -> VerificationReport:
        """Run all verification tests."""
        report = VerificationReport()

        # Directed tests
        directed = self.test_gen.generate_directed()
        report.directed_tests = len(directed)
        for tc in directed:
            result = self._run_test(tc)
            if result.passed:
                report.directed_passed += 1
            else:
                report.directed_failed += 1
                report.failures.append(result)

        # Random tests
        if random_count > 0:
            random_tests = self.test_gen.generate_random(count=random_count, seed=seed)
            report.random_tests = len(random_tests)
            for tc in random_tests:
                result = self._run_test(tc)
                if result.passed:
                    report.random_passed += 1
                    self.coverage.sample(tc.inputs)
                else:
                    report.random_failed += 1
                    report.failures.append(result)

        # Protocol tests
        protocol = self.test_gen.generate_protocol_tests()
        report.protocol_tests = len(protocol)
        for tc in protocol:
            result = self._run_test(tc)
            if result.passed:
                report.protocol_passed += 1
                self.coverage.record_protocol_event(tc.name)
            else:
                report.protocol_failed += 1
                report.failures.append(result)

        # Coverage summary
        report.coverage = self.coverage.summary()

        return report

    def _run_test(self, tc: TestCase) -> TestResult:
        """Run a single test case with multi-output comparison."""
        try:
            outputs: Optional[Dict[str, int]] = self.dut(tc.inputs)
            if outputs is None:
                outputs = {}

            if tc.expected_outputs is not None:
                # Multi-output: compare each named output
                passed = True
                for name, expected_val in tc.expected_outputs.items():
                    actual_val = outputs.get(name)
                    if actual_val != expected_val:
                        passed = False
                        break
                return TestResult(
                    passed=passed,
                    test_case=tc,
                    actual_outputs=outputs,
                )

            # Single-output fallback: if only one output, compare directly
            actual = None
            if outputs:
                actual = list(outputs.values())[0]

            if tc.expected is not None and actual is not None:
                passed = (actual == tc.expected)
            else:
                passed = True  # No expected value to compare

            return TestResult(
                passed=passed,
                test_case=tc,
                actual=actual,
                actual_outputs=outputs,
            )
        except Exception as e:
            return TestResult(
                passed=False,
                test_case=tc,
                error=str(e),
            )
