"""
rtlgen.dsl_sim — DSL Module Simulation-Based Validation

Validates DSL Module ASTs via Python simulation before RTL emission.
Catches incomplete logic: undriven outputs, static signals, X/Z values,
missing assignments, and unconnected submodule ports.

Usage:
    validator = DSLSimValidator(modules=leaf_targets, output_dir="dsl_sim_reports")
    report = validator.validate_all()
    for mod in report.modules:
        print(f"[{'OK' if mod.simulation_ok else 'FAIL'}] {mod.module_name}")
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from rtlgen.core import (
    Assign,
    ArrayRead,
    ArrayWrite,
    BinOp,
    BitSelect,
    Concat,
    Const,
    ForGenNode,
    GenIfNode,
    GenVar,
    IfNode,
    IndexedAssign,
    Input,
    MemRead,
    MemWrite,
    Module,
    Mux,
    Output,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
    Wire,
)


# -----------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------

@dataclass
class CompletenessIssue:
    severity: str  # "error" | "warning" | "info"
    signal_name: str
    issue_type: str  # "undriven_output" | "latch_risk" | "unused" | "unconnected" | "static_output"
    description: str


@dataclass
class ModuleSimResult:
    module_name: str
    simulation_ok: bool = False
    vectors_run: int = 0
    cycles_run: int = 0
    output_toggles: Dict[str, bool] = field(default_factory=dict)
    x_z_after_reset: List[str] = field(default_factory=list)
    completeness_issues: List[CompletenessIssue] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class DSLSimReport:
    total_modules: int = 0
    passed_modules: int = 0
    total_issues: int = 0
    modules: List[ModuleSimResult] = field(default_factory=list)
    output_dir: str = ""


# -----------------------------------------------------------------
# TestVectorGenerator
# -----------------------------------------------------------------

class TestVectorGenerator:
    """Generates random + directed test vectors for a DSL Module."""

    def __init__(self, module: Module):
        self._module = module

    def generate_all(self, num_random: int = 20, seed: Optional[int] = 42) -> List[Dict[str, int]]:
        vectors = self.generate_directed_vectors()
        vectors.extend(self.generate_random_vectors(num_random, seed))
        return vectors

    def generate_random_vectors(self, num_vectors: int = 20, seed: Optional[int] = 42) -> List[Dict[str, int]]:
        rng = random.Random(seed)
        inputs = list(self._module._inputs.values())
        stimulus_names = self._get_stimulus_names()

        vectors: List[Dict[str, int]] = []
        for _ in range(num_vectors):
            vec: Dict[str, int] = {}
            for sig in inputs:
                if sig.name in stimulus_names:
                    max_val = (1 << min(sig.width, 16)) - 1
                    vec[sig.name] = rng.randint(0, max_val)
            vectors.append(vec)
        return vectors

    def generate_directed_vectors(self) -> List[Dict[str, int]]:
        inputs = list(self._module._inputs.values())
        stimulus_names = self._get_stimulus_names()
        vectors: List[Dict[str, int]] = []

        # 1. All zeros
        vec_zero = {sig.name: 0 for sig in inputs if sig.name not in self._EXCLUDE_NAMES}
        vectors.append(vec_zero)

        # 2. All max
        vec_max = {}
        for sig in inputs:
            if sig.name not in self._EXCLUDE_NAMES:
                vec_max[sig.name] = (1 << min(sig.width, 16)) - 1
        vectors.append(vec_max)

        # 3. Walking 1 for each signal (capped at 8 bits to avoid explosion)
        for sig_name in stimulus_names:
            sig = next((s for s in inputs if s.name == sig_name), None)
            if sig is None:
                continue
            max_bits = min(sig.width, 8)
            for bit in range(max_bits):
                vec = {s.name: 0 for s in inputs if s.name not in self._EXCLUDE_NAMES}
                vec[sig_name] = 1 << bit
                vectors.append(vec)

        # 4. Alternating pattern (0x5555...)
        vec_alt: Dict[str, int] = {}
        for i, sig in enumerate(inputs):
            if sig.name not in self._EXCLUDE_NAMES:
                vec_alt[sig.name] = (0x55555555 >> (i % 32)) & ((1 << min(sig.width, 16)) - 1)
        vectors.append(vec_alt)

        return vectors

    _EXCLUDE_NAMES = frozenset({"clk", "rst", "rst_n", "reset", "reset_n"})

    def _get_stimulus_names(self) -> List[str]:
        return [
            sig.name for sig in self._module._inputs.values()
            if sig.name not in self._EXCLUDE_NAMES
        ]


# -----------------------------------------------------------------
# SignalCompletenessChecker
# -----------------------------------------------------------------

class SignalCompletenessChecker:
    """Static AST analysis to find undriven outputs, missing assignments."""

    def __init__(self, module: Module):
        self._module = module

    def check_all(self) -> List[CompletenessIssue]:
        issues: List[CompletenessIssue] = []

        assigned_targets = self._collect_all_assigned_targets()
        read_refs = self._collect_all_read_refs()

        # 1. Undriven outputs
        for name, sig in self._module._outputs.items():
            if id(sig) not in assigned_targets:
                issues.append(CompletenessIssue(
                    severity="error",
                    signal_name=name,
                    issue_type="undriven_output",
                    description=f"Output '{name}' is never assigned in any logic block",
                ))

        # 2. Unused wires (declared but never read and never written)
        for name, sig in self._module._wires.items():
            written = id(sig) in assigned_targets
            read = id(sig) in read_refs
            if not written and not read:
                issues.append(CompletenessIssue(
                    severity="info",
                    signal_name=name,
                    issue_type="unused",
                    description=f"Wire '{name}' is declared but neither read nor written",
                ))

        # 3. Unconnected submodule ports
        for inst_name, submod in self._module._submodules:
            sub_assigned = set()
            sub_read = set()
            self._collect_from_module(submod, sub_assigned, sub_read)
            for port_name, port_sig in submod._inputs.items():
                if id(port_sig) not in sub_assigned:
                    issues.append(CompletenessIssue(
                        severity="warning",
                        signal_name=f"{inst_name}.{port_name}",
                        issue_type="unconnected",
                        description=f"Submodule '{inst_name}' input '{port_name}' is never driven",
                    ))

        return issues

    def _collect_all_assigned_targets(self) -> Set[int]:
        assigned: Set[int] = set()
        self._collect_assigned(self._module._top_level, assigned)
        for body in self._module._comb_blocks:
            self._collect_assigned(body, assigned)
        for _, _, _, _, body in self._module._seq_blocks:
            self._collect_assigned(body, assigned)
        return assigned

    def _collect_all_read_refs(self) -> Set[int]:
        read: Set[int] = set()
        self._collect_reads(self._module._top_level, read)
        for body in self._module._comb_blocks:
            self._collect_reads(body, read)
        for _, _, _, _, body in self._module._seq_blocks:
            self._collect_reads(body, read)
        return read

    def _collect_from_module(self, mod: Module, assigned: Set[int], read: Set[int]):
        self._collect_assigned(mod._top_level, assigned)
        for body in mod._comb_blocks:
            self._collect_assigned(body, assigned)
        for _, _, _, _, body in mod._seq_blocks:
            self._collect_assigned(body, assigned)
        self._collect_reads(mod._top_level, read)
        for body in mod._comb_blocks:
            self._collect_reads(body, read)
        for _, _, _, _, body in mod._seq_blocks:
            self._collect_reads(body, read)

    def _collect_assigned(self, stmts: List[Any], assigned: Set[int]):
        for stmt in stmts:
            if isinstance(stmt, Assign):
                target = self._get_target_sig(stmt.target)
                if target is not None:
                    assigned.add(id(target))
            elif isinstance(stmt, IndexedAssign):
                assigned.add(id(stmt.target_signal))
            elif isinstance(stmt, ArrayWrite):
                # Array writes don't have a target Signal per se
                pass
            elif isinstance(stmt, IfNode):
                self._collect_assigned(stmt.then_body, assigned)
                self._collect_assigned(stmt.else_body, assigned)
            elif isinstance(stmt, SwitchNode):
                for _, body in stmt.cases:
                    self._collect_assigned(body, assigned)
                self._collect_assigned(stmt.default_body, assigned)
            elif isinstance(stmt, ForGenNode):
                self._collect_assigned(stmt.body, assigned)
            elif isinstance(stmt, GenIfNode):
                self._collect_assigned(stmt.then_body, assigned)
                self._collect_assigned(stmt.else_body, assigned)
            elif isinstance(stmt, SubmoduleInst):
                self._collect_from_module(stmt.module, assigned, set())

    def _collect_reads(self, stmts: List[Any], read: Set[int]):
        for stmt in stmts:
            if isinstance(stmt, Assign):
                self._collect_expr_reads(stmt.value, read)
            elif isinstance(stmt, IndexedAssign):
                self._collect_expr_reads(stmt.index, read)
                self._collect_expr_reads(stmt.value, read)
            elif isinstance(stmt, IfNode):
                self._collect_expr_reads(stmt.cond, read)
                self._collect_reads(stmt.then_body, read)
                self._collect_reads(stmt.else_body, read)
            elif isinstance(stmt, SwitchNode):
                self._collect_expr_reads(stmt.expr, read)
                for match_expr, body in stmt.cases:
                    self._collect_expr_reads(match_expr, read)
                    self._collect_reads(body, read)
                self._collect_reads(stmt.default_body, read)
            elif isinstance(stmt, ForGenNode):
                self._collect_reads(stmt.body, read)
            elif isinstance(stmt, GenIfNode):
                self._collect_expr_reads(stmt.cond, read)
                self._collect_reads(stmt.then_body, read)
                self._collect_reads(stmt.else_body, read)
            elif isinstance(stmt, SubmoduleInst):
                self._collect_from_module(stmt.module, set(), read)

    def _get_target_sig(self, target: Any) -> Optional[Signal]:
        if isinstance(target, Signal):
            return target
        if isinstance(target, Ref):
            return target.signal
        if isinstance(target, (Slice, PartSelect, BitSelect)):
            return self._get_target_sig(target.operand)
        return None

    def _collect_expr_reads(self, expr: Any, read: Set[int]):
        if expr is None:
            return
        if isinstance(expr, Ref):
            read.add(id(expr.signal))
        elif isinstance(expr, Signal):
            read.add(id(expr))
        elif isinstance(expr, BinOp):
            self._collect_expr_reads(expr.lhs, read)
            self._collect_expr_reads(expr.rhs, read)
        elif isinstance(expr, UnaryOp):
            self._collect_expr_reads(expr.operand, read)
        elif isinstance(expr, Mux):
            self._collect_expr_reads(expr.cond, read)
            self._collect_expr_reads(expr.true_expr, read)
            self._collect_expr_reads(expr.false_expr, read)
        elif isinstance(expr, (Slice, PartSelect, BitSelect)):
            self._collect_expr_reads(expr.operand, read)
            if hasattr(expr, 'index') and expr.index is not None:
                self._collect_expr_reads(expr.index, read)
            if hasattr(expr, 'offset') and expr.offset is not None:
                self._collect_expr_reads(expr.offset, read)
        elif isinstance(expr, Concat):
            for op in expr.operands:
                self._collect_expr_reads(op, read)
        elif isinstance(expr, ArrayRead):
            self._collect_expr_reads(expr.index, read)
        elif isinstance(expr, MemRead):
            self._collect_expr_reads(expr.addr, read)
        elif isinstance(expr, Const):
            pass
        elif isinstance(expr, GenVar):
            pass
        elif isinstance(expr, int):
            pass


# -----------------------------------------------------------------
# DSLSimValidator
# -----------------------------------------------------------------

class DSLSimValidator:
    """Validates DSL Module ASTs via Python simulation."""

    def __init__(
        self,
        modules: List[Tuple[str, type]],
        output_dir: str = "dsl_sim_reports",
        default_cycles: int = 50,
        use_xz: bool = True,
    ):
        self._modules = modules
        self._output_dir = output_dir
        self._default_cycles = default_cycles
        self._use_xz = use_xz

    def validate_all(self) -> DSLSimReport:
        report = DSLSimReport(
            total_modules=len(self._modules),
            output_dir=self._output_dir,
        )
        os.makedirs(self._output_dir, exist_ok=True)

        for name, mod_cls in self._modules:
            result = self._validate_single(name, mod_cls)
            report.modules.append(result)
            if result.simulation_ok:
                report.passed_modules += 1
            report.total_issues += len(result.completeness_issues)

        self._write_report(report)
        return report

    def _validate_single(self, name: str, mod_cls: type) -> ModuleSimResult:
        try:
            mod = mod_cls()
        except Exception as e:
            result = ModuleSimResult(module_name=name)
            result.errors.append(f"Instantiation failed: {e}")
            result.simulation_ok = False
            return result

        return self.validate_module_instance(mod, module_name=name)

    def validate_module_instance(
        self,
        mod: Module,
        module_name: Optional[str] = None,
        vectors: Optional[List[Dict[str, Any]]] = None,
    ) -> ModuleSimResult:
        from rtlgen.sim import Simulator, SimValue

        result = ModuleSimResult(module_name=module_name or mod.name)

        # Static completeness check
        checker = SignalCompletenessChecker(mod)
        result.completeness_issues = checker.check_all()

        # Check if simulation is possible
        input_names = [sig.name for sig in mod._inputs.values()
                       if sig.name not in TestVectorGenerator._EXCLUDE_NAMES]
        if not input_names and not mod._seq_blocks:
            result.simulation_ok = True
            result.vectors_run = 0
            return result

        # Generate test vectors
        if vectors is None:
            gen = TestVectorGenerator(mod)
            vectors = gen.generate_all(num_random=20)

        output_names = list(mod._outputs.keys())
        has_clk = "clk" in mod._inputs
        rst_name = self._detect_reset_name(mod)
        has_rst = rst_name is not None

        try:
            sim = Simulator(mod, use_xz=self._use_xz)

            # Reset sequence
            if has_rst:
                sim.reset(rst_name, cycles=2)

            # Check for X/Z immediately after reset
            if self._use_xz:
                for out_name in output_names:
                    val = sim.get(out_name)
                    if isinstance(val, SimValue) and (val.is_x() or val.is_z()):
                        result.x_z_after_reset.append(out_name)

            # Run vectors
            output_toggle_history: Dict[str, set] = {n: set() for n in output_names}
            for i, vec in enumerate(vectors):
                for inp_name, inp_val in vec.items():
                    if inp_name in mod._inputs:
                        sim.set(inp_name, inp_val)

                if has_clk:
                    sim.step(do_trace=False)
                else:
                    sim._eval_comb()

                # Track output values
                for out_name in output_names:
                    val = sim.get_int(out_name)
                    output_toggle_history[out_name].add(val)

            result.vectors_run = len(vectors)
            result.cycles_run = len(vectors)
            result.output_toggles = {n: len(v) > 1 for n, v in output_toggle_history.items()}

            # Flag outputs that never toggled
            for out_name, toggled in result.output_toggles.items():
                if not toggled:
                    result.completeness_issues.append(CompletenessIssue(
                        severity="warning",
                        signal_name=out_name,
                        issue_type="static_output",
                        description=f"Output '{out_name}' never changed value "
                                    f"across {result.vectors_run} test vectors",
                    ))

            result.simulation_ok = True

        except Exception as e:
            import traceback
            result.errors.append(f"Simulation failed: {e}\n{traceback.format_exc()}")
            result.simulation_ok = False

        return result

    @staticmethod
    def _detect_reset_name(mod: Module) -> Optional[str]:
        for candidate in ("rst_n", "reset_n", "rst", "reset", "aresetn"):
            if candidate in mod._inputs:
                return candidate
        for name in mod._inputs:
            lname = name.lower()
            if "rst" in lname or "reset" in lname:
                return name
        return None

    def _write_report(self, report: DSLSimReport):
        # JSON report
        json_path = os.path.join(self._output_dir, "dsl_sim_report.json")
        data = {
            "total_modules": report.total_modules,
            "passed_modules": report.passed_modules,
            "total_issues": report.total_issues,
            "modules": []
        }
        for m in report.modules:
            data["modules"].append({
                "name": m.module_name,
                "simulation_ok": m.simulation_ok,
                "vectors_run": m.vectors_run,
                "cycles_run": m.cycles_run,
                "output_toggles": m.output_toggles,
                "x_z_after_reset": m.x_z_after_reset,
                "completeness_issues": [
                    {"severity": i.severity, "signal": i.signal_name,
                     "type": i.issue_type, "description": i.description}
                    for i in m.completeness_issues
                ],
                "errors": m.errors,
            })
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # Human-readable text report
        txt_path = os.path.join(self._output_dir, "dsl_sim_report.txt")
        sev_marker = {"error": "!!", "warning": "! ", "info": "  "}
        with open(txt_path, "w") as f:
            f.write("DSL Simulation Validation Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Modules: {report.passed_modules}/{report.total_modules} passed\n")
            f.write(f"Total issues: {report.total_issues}\n\n")
            for m in report.modules:
                status = "OK" if m.simulation_ok else "FAIL"
                f.write(f"[{status}] {m.module_name}\n")
                f.write(f"  Vectors: {m.vectors_run}, Cycles: {m.cycles_run}\n")
                if m.x_z_after_reset:
                    f.write(f"  X/Z after reset: {', '.join(m.x_z_after_reset)}\n")
                static_outputs = [n for n, t in m.output_toggles.items() if not t]
                if static_outputs:
                    f.write(f"  Static outputs: {', '.join(static_outputs)}\n")
                for issue in m.completeness_issues:
                    f.write(f"  [{sev_marker.get(issue.severity, '  ')}] "
                            f"{issue.signal_name}: {issue.description}\n")
                if m.errors:
                    for err in m.errors:
                        f.write(f"  [ERR] {err}\n")
                f.write("\n")
