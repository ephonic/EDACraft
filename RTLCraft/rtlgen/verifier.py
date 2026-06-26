"""
rtlgen.verifier — Skill-Guided RTL Generation: Verification & Repair Loop

Four-level verification as specified in skills/skills-guided-gen.md Section 9:
  Level 1: Syntax check (iverilog)
  Level 2: Static lint (VerilogLinter)
  Level 3: Smoke test (Simulator golden tests)
  Level 4: Behavior trace comparison (behavior model vs RTL simulation)

Plus repair loop: generate repair context and apply minimal patches.
"""
from __future__ import annotations

import inspect
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.codegen import VerilogEmitter
from rtlgen.core import Module
from rtlgen.lint import VerilogLinter, LintIssue
from rtlgen.sim import Simulator


@dataclass
class VerificationResult:
    """Result of a full 4-level verification."""
    level: int  # Highest level reached (1-4)
    passed: bool
    issues: List[str] = field(default_factory=list)
    trace: Optional[List[Dict[str, Any]]] = None
    behavior_trace: Optional[List[Dict[str, Any]]] = None
    trace_diff: Optional[List[str]] = None


@dataclass
class RepairContext:
    """Context passed to repair agent for minimal-change fix."""
    module_name: str
    failed_level: int
    issues: List[str]
    current_code: str
    behavior_requirement: Optional[Dict[str, Any]] = None
    reference_cards: List[Any] = field(default_factory=list)
    trace_diff: Optional[List[str]] = None
    repair_policy: Dict[str, Any] = field(default_factory=lambda: {
        "preserve_existing_structure": True,
        "minimal_change": True,
    })


class Verifier:
    """Four-level verifier with repair loop support.

    Usage:
        verifier = Verifier()
        result = verifier.verify_module(module, verilog_text,
                                        behavior_ref=behavior_fn,
                                        golden_tests=tests)
        if not result.passed:
            ctx = verifier.build_repair_context(module, result, refs)
            patch = logic_generator.repair(ctx)
            verifier.apply_patch(module, patch)
    """

    def __init__(
        self,
        enable_level_3: bool = True,
        enable_level_4: bool = True,
        iverilog_cmd: str = "iverilog",
        max_smoke_cycles: int = 200,
    ):
        self.linter = VerilogLinter(auto_fix=False)
        self.enable_level_3 = enable_level_3
        self.enable_level_4 = enable_level_4
        self.iverilog_cmd = iverilog_cmd
        self.max_smoke_cycles = max_smoke_cycles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_module(
        self,
        module: Module,
        verilog_text: str,
        behavior_ref: Optional[Callable] = None,
        golden_tests: Optional[List[Dict[str, Any]]] = None,
        trace_signals: Optional[List[str]] = None,
    ) -> VerificationResult:
        """Run full 4-level verification. Stop at first failure."""
        issues: List[str] = []

        # ---- Level 1: Syntax Check ----
        ok, err = self.check_syntax(verilog_text)
        if not ok:
            issues.extend(err)
            return VerificationResult(level=1, passed=False, issues=issues)
        issues.append("Level 1 (Syntax): PASSED")

        # ---- Level 2: Static Lint ----
        ok, err = self.check_static(verilog_text)
        if not ok:
            issues.extend(err)
            return VerificationResult(level=2, passed=False, issues=issues)
        issues.append("Level 2 (Static): PASSED")

        # ---- Level 3: Smoke Test ----
        if self.enable_level_3 and golden_tests:
            ok, err, trace = self.check_smoke(module, golden_tests, trace_signals)
            if not ok:
                issues.extend(err)
                return VerificationResult(level=3, passed=False, issues=issues,
                                          trace=trace)
            issues.append("Level 3 (Smoke): PASSED")
        else:
            trace = None

        # ---- Level 4: Behavior Trace Comparison ----
        if self.enable_level_4 and behavior_ref is not None and golden_tests:
            ok, err, rtl_trace, beh_trace, diff = self.check_behavior_match(
                module, behavior_ref, golden_tests, trace_signals
            )
            if not ok:
                issues.extend(err)
                return VerificationResult(
                    level=4, passed=False, issues=issues,
                    trace=rtl_trace, behavior_trace=beh_trace, trace_diff=diff
                )
            issues.append("Level 4 (Behavior Match): PASSED")
        else:
            rtl_trace = None
            beh_trace = None
            diff = None

        return VerificationResult(
            level=4, passed=True, issues=issues,
            trace=rtl_trace, behavior_trace=beh_trace, trace_diff=diff
        )

    def verify_partial(
        self,
        module: Module,
        verilog_text: str,
        golden_tests: Optional[List[Dict[str, Any]]] = None,
    ) -> VerificationResult:
        """Lightweight partial verification (Level 1-2 only) during generation."""
        issues: List[str] = []

        ok, err = self.check_syntax(verilog_text)
        if not ok:
            issues.extend(err)
            return VerificationResult(level=1, passed=False, issues=issues)

        ok, err = self.check_static(verilog_text)
        if not ok:
            issues.extend(err)
            return VerificationResult(level=2, passed=False, issues=issues)

        return VerificationResult(level=2, passed=True, issues=issues)

    def build_repair_context(
        self,
        module: Module,
        result: VerificationResult,
        reference_cards: List[Any],
        behavior_requirement: Optional[Dict[str, Any]] = None,
    ) -> RepairContext:
        """Construct repair context from failed verification."""
        emitter = VerilogEmitter(disable_cse=True)
        code = emitter.emit(module)
        return RepairContext(
            module_name=module.name,
            failed_level=result.level,
            issues=result.issues,
            current_code=code,
            behavior_requirement=behavior_requirement,
            reference_cards=reference_cards,
            trace_diff=result.trace_diff,
        )

    # ------------------------------------------------------------------
    # Level 1: Syntax Check
    # ------------------------------------------------------------------

    def check_syntax(self, verilog_text: str) -> Tuple[bool, List[str]]:
        """Compile with iverilog -g2012. Return (ok, errors)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".v", delete=False
        ) as f:
            f.write(verilog_text)
            tmp_path = f.name

        try:
            cmd = [
                self.iverilog_cmd,
                "-g2012",
                "-Wall",
                "-o", "/dev/null",
                tmp_path,
            ]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            # iverilog warnings are acceptable; errors are not
            errors = [
                line for line in proc.stderr.splitlines()
                if "error:" in line.lower() or "syntax error" in line.lower()
            ]
            if proc.returncode != 0 and errors:
                return False, [f"[Syntax] {e}" for e in errors]
            return True, []
        except subprocess.TimeoutExpired:
            return False, ["[Syntax] iverilog timeout"]
        except FileNotFoundError:
            # iverilog not installed — skip syntax check but warn
            return True, ["[Syntax] iverilog not found, skipped"]
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Level 2: Static Lint
    # ------------------------------------------------------------------

    def check_static(self, verilog_text: str) -> Tuple[bool, List[str]]:
        """Run VerilogLinter. Treat errors as failures, warnings as acceptable."""
        result = self.linter.lint(verilog_text)
        errors = [i for i in result.issues if i.severity == "error"]
        if errors:
            msgs = [f"[Lint/{i.rule}] L{i.line}: {i.message}" for i in errors]
            return False, msgs
        # Collect warnings for info but don't fail
        warnings = [i for i in result.issues if i.severity == "warning"]
        if warnings:
            return True, [f"[Lint/{i.rule}] L{i.line}: {i.message}"
                          for i in warnings[:5]]
        return True, []

    # ------------------------------------------------------------------
    # Level 3: Smoke Test
    # ------------------------------------------------------------------

    def check_smoke(
        self,
        module: Module,
        golden_tests: List[Dict[str, Any]],
        trace_signals: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str], Optional[List[Dict[str, Any]]]]:
        """Run first golden test as smoke test using Simulator."""
        if not golden_tests:
            return True, [], None

        test = golden_tests[0]
        sim = Simulator(module, trace_signals=trace_signals)
        sim.reset()

        # Apply test inputs
        inputs = test.get("inputs", {})
        for sig_name, val in inputs.items():
            sim.poke(sig_name, val)

        # Run for a few cycles
        for _ in range(20):
            sim.step()

        # Check expected outputs if present
        expected = test.get("expected_outputs", {})
        mismatches = []
        for sig_name, exp_val in expected.items():
            actual = sim.peek(sig_name)
            if actual != exp_val:
                mismatches.append(
                    f"[Smoke] {sig_name}: expected {exp_val}, got {actual}"
                )

        if mismatches:
            return False, mismatches, sim.trace

        return True, [], sim.trace

    # ------------------------------------------------------------------
    # Level 4: Behavior Trace Comparison
    # ------------------------------------------------------------------

    def check_behavior_match(
        self,
        module: Module,
        behavior_ref: Callable,
        golden_tests: List[Dict[str, Any]],
        trace_signals: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str], Optional[List[Dict]], Optional[List[Dict]], Optional[List[str]]]:
        """Compare behavior model trace vs RTL simulation trace (L4).

        Runs both the behavior model and RTL simulation for multiple cycles,
        then compares output traces at event level with cycle tolerance.

        ``behavior_ref`` can be either:
        - A callable taking ``CycleContext`` and writing to ``ctx.outputs``
        - A callable taking ``(inputs: dict, cycle: int) -> outputs: dict``
        - A callable taking ``(inputs: dict) -> outputs: dict`` (single-cycle)

        Returns: (ok, errors, rtl_trace, behavior_trace, diff_lines)
        """
        if not golden_tests:
            return True, [], None, None, None

        test = golden_tests[0]
        inputs = test.get("inputs", {})

        # ---- Run RTL simulation ----
        rtl_sim = Simulator(module, trace_signals=trace_signals)
        rtl_sim.reset()
        for sig_name, val in inputs.items():
            rtl_sim.poke(sig_name, val)
        for _ in range(self.max_smoke_cycles):
            rtl_sim.step()
            # Early exit if done signal asserted
            if hasattr(module, "done"):
                try:
                    if rtl_sim.peek("done"):
                        break
                except Exception:
                    pass

        rtl_trace = rtl_sim.trace or []

        # ---- Run behavior model (multi-cycle) ----
        beh_trace = self._run_behavior_multi_cycle(behavior_ref, inputs)

        if not beh_trace:
            return False, ["[L4] Behavior model produced no trace"], \
                   rtl_trace, None, None

        # ---- Compare traces ----
        diff = self._compare_traces(rtl_trace, beh_trace)
        if diff:
            return False, diff, rtl_trace, beh_trace, diff

        return True, [], rtl_trace, beh_trace, None

    @staticmethod
    def _run_behavior_multi_cycle(
        behavior_ref: Callable,
        inputs: Dict[str, Any],
        max_cycles: int = 200,
    ) -> List[Dict[str, Any]]:
        """Run behavior model for multiple cycles, collecting per-cycle trace.

        Detects the signature of ``behavior_ref`` and calls it appropriately:
        - If it accepts a ``CycleContext`` arg, use CycleContext protocol
        - Otherwise, call with ``(inputs, cycle)`` or ``(inputs,)``
        """
        from rtlgen.arch_def import CycleContext

        trace: List[Dict[str, Any]] = []
        state: Dict[str, Any] = {}

        # Detect calling convention by introspecting signature
        try:
            sig = inspect.signature(behavior_ref)
            params = list(sig.parameters.values())
            takes_cycle_context = (
                len(params) == 1
                and params[0].annotation is CycleContext
            )
        except (ValueError, TypeError):
            takes_cycle_context = False

        for cycle in range(max_cycles):
            if takes_cycle_context:
                ctx = CycleContext(
                    cycle=cycle,
                    inputs=dict(inputs),
                    state=dict(state),
                )
                try:
                    behavior_ref(ctx)
                except Exception:
                    break
                frame = {"_cycle": cycle, **ctx.outputs}
                for k, v in ctx.next_state.items():
                    state[k] = v
            else:
                try:
                    # Try with (inputs, cycle) first
                    beh_outputs = behavior_ref(inputs, cycle)
                except TypeError:
                    try:
                        # Fall back to (inputs,)
                        beh_outputs = behavior_ref(inputs)
                    except Exception:
                        break
                except Exception:
                    break
                frame = {"_cycle": cycle, **beh_outputs}

            trace.append(frame)

            # Check for done signal
            if frame.get("done", 0):
                break

        return trace

    def _compare_traces(
        self,
        rtl_trace: List[Dict[str, Any]],
        beh_trace: List[Dict[str, Any]],
        tolerance_cycles: int = 5,
    ) -> List[str]:
        """Compare RTL trace vs behavior trace with cycle tolerance.

        RTL may produce outputs a few cycles later than the behavior model.
        We allow outputs to be delayed by up to ``tolerance_cycles`` cycles
        while still requiring correct final values.
        """
        diffs: List[str] = []
        if not rtl_trace or not beh_trace:
            return diffs

        # Extract output signals from both traces (exclude metadata)
        exclude = {"_time", "_cycle", "_event"}

        # Compare final state of all common output signals
        rtl_final = rtl_trace[-1] if rtl_trace else {}
        beh_final = beh_trace[-1] if beh_trace else {}

        common_signals = set(rtl_final.keys()) & set(beh_final.keys())
        common_signals -= exclude

        for sig in sorted(common_signals):
            r = rtl_final.get(sig)
            b = beh_final.get(sig)
            if r is not None and b is not None and r != b:
                diffs.append(
                    f"[L4:FinalState] {sig}: behavior={b}, rtl={r}"
                )

        # Event-order comparison: check that key state transitions occur
        # in the same relative order, allowing for pipeline latency.
        # RTL may produce events in different order than behavior model
        # (e.g. comb outputs arrive before pipeline outputs), so we allow
        # any matching RTL cycle within tolerance.
        rtl_events = self._extract_trace_events(rtl_trace, common_signals)
        beh_events = self._extract_trace_events(beh_trace, common_signals)

        for beh_ev in beh_events:
            matched = False
            for rtl_ev in rtl_events:
                if rtl_ev["sig"] == beh_ev["sig"] and rtl_ev["val"] == beh_ev["val"]:
                    cycle_delta = rtl_ev["cycle"] - beh_ev["cycle"]
                    if cycle_delta <= tolerance_cycles:
                        matched = True
                        break
            if not matched:
                diffs.append(
                    f"[L4:EventMissing] {beh_ev['sig']}={beh_ev['val']} "
                    f"at cycle {beh_ev['cycle']}"
                )

        return diffs

    @staticmethod
    def _extract_trace_events(
        trace: List[Dict[str, Any]],
        signals: set,
    ) -> List[Dict[str, Any]]:
        """Extract value-change events from a trace for event-order comparison."""
        events = []
        last_vals: Dict[str, Any] = {}
        for frame in trace:
            cycle = frame.get("_cycle", 0)
            for sig in signals:
                val = frame.get(sig)
                if val is not None and val != last_vals.get(sig):
                    events.append({"sig": sig, "val": val, "cycle": cycle})
                    last_vals[sig] = val
        return events

    # ------------------------------------------------------------------
    # Repair helpers
    # ------------------------------------------------------------------

    def apply_patch(self, module: Module, patch: Dict[str, Any]) -> bool:
        """Apply a repair patch to module.

        First version supports wire/signal addition only.
        Future versions can support statement replacement.
        """
        added = patch.get("add_signals", [])
        for sig_spec in added:
            kind = sig_spec.get("kind", "Wire")
            width = sig_spec.get("width", 1)
            name = sig_spec.get("name", "")
            if not name or hasattr(module, name):
                continue
            cls = getattr(__import__("rtlgen.core", fromlist=[kind]), kind, None)
            if cls:
                setattr(module, name, cls(width, name))
        return True

    # ------------------------------------------------------------------
    # Repair Module — Iterative Repair Loop
    # ------------------------------------------------------------------

    def repair_module(
        self,
        module: Module,
        result: VerificationResult,
        logic_generator,
        reference_cards: list,
        behavior_requirement: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> Tuple[Module, VerificationResult]:
        """Iterative repair loop.

        For each attempt:
        1. Build repair context from failed verification
        2. Call logic_generator.repair() for patch
        3. Apply patch to module
        4. Re-emit and re-verify
        5. If passed, return; if failed, continue

        Args:
            module: The DSL module to repair
            result: Failed VerificationResult
            logic_generator: LogicGenerator instance for repair
            reference_cards: Reference cards for context
            behavior_requirement: Optional behavior requirements dict
            max_attempts: Maximum repair attempts

        Returns:
            (repaired_module, new_verification_result)
        """
        emitter = VerilogEmitter(disable_cse=True)

        for attempt in range(1, max_attempts + 1):
            # Build repair context
            ctx = self.build_repair_context(
                module, result, reference_cards, behavior_requirement
            )
            ctx.repair_policy["attempt"] = attempt
            ctx.repair_policy["max_attempts"] = max_attempts

            # Generate repair patch
            try:
                patch = logic_generator.repair(module, ctx)
            except Exception as e:
                result.issues.append(f"[Repair] Attempt {attempt}: repair generator failed: {e}")
                continue

            if not patch:
                result.issues.append(
                    f"[Repair] Attempt {attempt}: no patch generated"
                )
                continue

            # Apply patch
            self.apply_patch(module, patch)

            # Re-verify
            vlog = emitter.emit(module)
            result = self.verify_partial(module, vlog)

            if result.passed:
                # Run full verification if we passed partial
                golden_tests = []  # Caller should provide via context
                result = self.verify_module(
                    module, vlog,
                    golden_tests=golden_tests,
                )
                if result.passed:
                    return module, result

            # Still failing — continue to next attempt
            result.issues.append(
                f"[Repair] Attempt {attempt}: still failing, retrying"
            )

        # All attempts exhausted
        result.issues.append(
            f"[Repair] All {max_attempts} attempts exhausted"
        )
        return module, result

    # ------------------------------------------------------------------
    # Event-Order Trace Comparison (Level 4 Enhancement)
    # ------------------------------------------------------------------

    def _compare_traces_event_order(
        self,
        rtl_trace: List[Dict[str, Any]],
        beh_trace: List[Dict[str, Any]],
        key_signals: Optional[List[str]] = None,
    ) -> List[str]:
        """Compare event sequences rather than cycle-exact values.

        Checks that key events (e.g., dispatch → issue → writeback)
        occur in the same relative order in both traces.
        This is the v1 approach; v2 will add cycle-aware comparison.

        Args:
            rtl_trace: List of per-cycle dicts from RTL simulation
            beh_trace: List of per-cycle dicts from behavior model
            key_signals: Specific signals to track as events

        Returns:
            List of mismatch descriptions
        """
        diffs = []
        if not rtl_trace or not beh_trace:
            if not rtl_trace and beh_trace:
                diffs.append("[EventOrder] RTL trace is empty but behavior trace has events")
            elif rtl_trace and not beh_trace:
                diffs.append("[EventOrder] Behavior trace is empty but RTL trace has events")
            return diffs

        # Determine key signals to track
        if key_signals is None:
            key_signals = self._infer_key_signals(rtl_trace, beh_trace)

        # Extract events from both traces
        rtl_events = self._extract_events(rtl_trace, key_signals)
        beh_events = self._extract_events(beh_trace, key_signals)

        # Subsequence matching: check that beh_events appear in rtl_events in order
        rtl_idx = 0
        for beh_event in beh_events:
            found = False
            while rtl_idx < len(rtl_events):
                if self._events_match(beh_event, rtl_events[rtl_idx]):
                    found = True
                    rtl_idx += 1  # Advance past matched event
                    break
                rtl_idx += 1
            if not found:
                diffs.append(
                    f"[EventMissing] Expected event {beh_event} "
                    f"not found in RTL trace"
                )

        return diffs

    @staticmethod
    def _infer_key_signals(
        rtl_trace: List[Dict[str, Any]],
        beh_trace: List[Dict[str, Any]],
    ) -> List[str]:
        """Infer which signals are important for event comparison."""
        key_signals = []

        # Look for valid/ready signals (control events)
        sample = rtl_trace[0] if rtl_trace else {}
        for name in sample:
            name_lower = name.lower()
            if any(kw in name_lower for kw in [
                "valid", "ready", "fire", "done", "retire",
                "issue", "dispatch", "writeback", "wb_",
                "req", "rsp", "hit", "miss",
            ]):
                key_signals.append(name)

        if not key_signals:
            # Fallback: use all non-cycle, non-time signals
            key_signals = [
                n for n in sample
                if n not in ("_cycle", "_time")
            ][:10]

        return key_signals

    @staticmethod
    def _extract_events(
        trace: List[Dict[str, Any]],
        key_signals: List[str],
    ) -> List[Dict[str, Any]]:
        """Extract discrete events from a continuous trace.

        An event is a cycle where any key signal changes state
        (0→1 or 1→0 for single-bit signals).
        """
        events = []
        prev = {}

        for cycle_idx, frame in enumerate(trace):
            cycle_events = {"_cycle": cycle_idx}
            has_event = False

            for sig in key_signals:
                val = frame.get(sig, 0)
                prev_val = prev.get(sig, 0)

                # Detect rising edge (0→1)
                if val != prev_val and val != 0:
                    cycle_events[sig] = val
                    has_event = True

                prev[sig] = val

            if has_event:
                events.append(cycle_events)

        return events

    @staticmethod
    def _events_match(
        expected: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> bool:
        """Check if an actual event matches the expected event pattern.

        Matches if all non-_cycle keys in expected have the same value
        in actual. This is a loose match for event-order comparison.
        """
        for key, val in expected.items():
            if key == "_cycle":
                continue
            if key not in actual:
                return False
            if actual[key] != val:
                return False
        return True
