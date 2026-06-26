"""
rtlgen.ppa_optimizer — PPA 分析与优化指南生成器

设计哲学：框架仅分析现状、提出目标和策略，**所有优化实现由智能体完成**。

职责划分:
  1. 分析 (Analyze)   → PPAAnalyzer 生成当前模块的 PPA 报告
  2. 建议 (Propose)   → 各策略根据 PPA 目标提出优化方向和预期影响
  3. 指南 (Guide)     → 汇总为 OptimizationGuide 文档，交给智能体
  4. 注入 (Inject)    → 智能体完成优化后，通过 inject_optimized() 注入新模块
  5. 对比 (Compare)   → 框架自动计算 before/after 的 PPA 差异

智能体工作流:
  guide = optimizer.analyze()          # 获取优化指南
  print(guide.to_markdown())           # 阅读建议
  # ... 智能体根据指南重写模块 ...
  result = optimizer.inject_optimized(new_module, notes="...")
  print(result.score_before.total, result.score_after.total)
"""
from __future__ import annotations

import copy
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rtlgen.core import (
    Assign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    IfNode,
    Module,
    Mux,
    Ref,
    Reg,
    Signal,
    Slice,
    SwitchNode,
    UnaryOp,
    Wire,
)
from rtlgen.ppa import PPAAnalyzer
from rtlgen.logic import If, Else
from rtlgen.spec_ir import OptimizableOp, SpecIR


# ---------------------------------------------------------------------------
# PPA Score
# ---------------------------------------------------------------------------

@dataclass
class PPAGoal:
    """PPA target specification."""
    max_area: Optional[int] = None
    max_logic_depth: Optional[int] = None
    max_registers: Optional[int] = None
    max_power: Optional[float] = None
    target_freq_mhz: Optional[float] = None


@dataclass
class PPAScore:
    """PPA score relative to goals. Lower is better. 0 = meets all goals."""
    total: float = 0.0
    area_score: float = 0.0
    timing_score: float = 0.0
    register_score: float = 0.0
    power_score: float = 0.0
    violations: List[str] = field(default_factory=list)
    meets_goals: bool = True

    @classmethod
    def compute(cls, report: Dict[str, Any], goal: PPAGoal,
                weights: Optional[Dict[str, float]] = None) -> "PPAScore":
        """Compute PPA score from analysis report vs goals."""
        w = weights or {"area": 1.0, "timing": 1.0, "register": 0.5, "power": 1.0}
        score = cls()

        # Area
        if goal.max_area is not None:
            actual = report.get("cell_area", report.get("gate_count", report.get("area", 0)))
            if isinstance(actual, dict):
                actual = max(actual.values(), default=0)
            if actual > goal.max_area:
                score.area_score = (actual - goal.max_area) / max(goal.max_area, 1) * w["area"]
                score.violations.append(f"Area {actual} exceeds goal {goal.max_area}")
                score.meets_goals = False

        # Timing (logic depth) — may be dict {signal: depth} or scalar
        if goal.max_logic_depth is not None:
            actual = report.get("logic_depth", report.get("max_depth", 0))
            if isinstance(actual, dict):
                actual = max(actual.values(), default=0)
            if actual > goal.max_logic_depth:
                score.timing_score = (actual - goal.max_logic_depth) / max(goal.max_logic_depth, 1) * w["timing"]
                score.violations.append(f"Logic depth {actual} exceeds goal {goal.max_logic_depth}")
                score.meets_goals = False

        # Registers
        if goal.max_registers is not None:
            actual = report.get("register_count", report.get("reg_bits", report.get("registers", 0)))
            if isinstance(actual, dict):
                actual = sum(actual.values(), 0)
            if actual > goal.max_registers:
                score.register_score = (actual - goal.max_registers) / max(goal.max_registers, 1) * w["register"]
                score.violations.append(f"Register count {actual} exceeds goal {goal.max_registers}")
                score.meets_goals = False

        # Power (estimated from activity * capacitance)
        if goal.max_power is not None:
            actual = report.get("estimated_power", 0)
            if isinstance(actual, dict):
                actual = sum(actual.values(), 0)
            if actual > goal.max_power:
                score.power_score = (actual - goal.max_power) / max(goal.max_power, 1e-9) * w["power"]
                score.violations.append(f"Power {actual} exceeds goal {goal.max_power}")
                score.meets_goals = False

        score.total = score.area_score + score.timing_score + score.register_score + score.power_score
        return score


# ---------------------------------------------------------------------------
# Optimization Suggestion — 单条优化建议
# ---------------------------------------------------------------------------

@dataclass
class OptimizationSuggestion:
    """由策略提出的单条优化建议，供智能体参考。

    所有实现由智能体完成；框架仅提供分析、目标和预期影响。
    """
    strategy: str
    change_type: str
    target: str
    description: str
    estimated_impact: Dict[str, float] = field(default_factory=dict)
    priority: str = "medium"  # "high" | "medium" | "low"

    def to_markdown(self) -> str:
        lines = [
            f"### [{self.priority.upper()}] {self.strategy}: {self.change_type}",
            "",
            f"- **Target**: `{self.target}`",
            f"- **Description**: {self.description}",
            "- **Estimated Impact**:",
        ]
        for k, v in self.estimated_impact.items():
            sign = "+" if v > 0 else ""
            lines.append(f"  - {k}: {sign}{v}")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Optimization Guide — 优化指南文档
# ---------------------------------------------------------------------------

@dataclass
class OptimizationGuide:
    """优化指南 — PPAOptimizer 生成，交给智能体执行。

    包含当前模块的完整 PPA 分析、优化目标、逐条建议，以及代码片段。
    """
    module_name: str
    current_ppa: Dict[str, Any] = field(default_factory=dict)
    current_score: PPAScore = field(default_factory=PPAScore)
    goals: PPAGoal = field(default_factory=PPAGoal)
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    code_snippet: str = ""
    agent_interface: str = (
        "智能体工作流：\n"
        "1. 阅读本指南中的 Optimization Suggestions\n"
        "2. 直接操作 Module AST（如 module._comb_blocks, module._wires, module._regs）"
        "   实现优化（插入流水线、共享资源、缩减位宽、重平衡 MUX 等）\n"
        "3. 调用 optimizer.inject_optimized(new_module, notes='...') 注入结果\n"
        "4. 框架自动计算 before/after PPA 对比\n\n"
        "注意：所有分析基于 AST，无需逻辑综合。"
    )

    def to_markdown(self) -> str:
        lines = [
            f"# PPA Optimization Guide: `{self.module_name}`",
            "",
            "## Current PPA Analysis",
            "",
        ]
        for k, v in self.current_ppa.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

        lines.extend([
            "## Goals",
            "",
            f"- Max Area: {self.goals.max_area or 'N/A'}",
            f"- Max Logic Depth: {self.goals.max_logic_depth or 'N/A'}",
            f"- Max Registers: {self.goals.max_registers or 'N/A'}",
            f"- Max Power: {self.goals.max_power or 'N/A'}",
            f"- Target Freq: {self.goals.target_freq_mhz or 'N/A'} MHz",
            "",
            "## Current Score",
            "",
            f"- **Total Score**: {self.current_score.total:.4f}",
            f"- Area Score: {self.current_score.area_score:.4f}",
            f"- Timing Score: {self.current_score.timing_score:.4f}",
            f"- Register Score: {self.current_score.register_score:.4f}",
            f"- Power Score: {self.current_score.power_score:.4f}",
            f"- Meets Goals: {'Yes' if self.current_score.meets_goals else 'No'}",
        ])
        if self.current_score.violations:
            lines.append("- **Violations**:")
            for v in self.current_score.violations:
                lines.append(f"  - {v}")
        lines.append("")

        lines.extend([
            "## Optimization Suggestions",
            "",
        ])
        if not self.suggestions:
            lines.append("No suggestions — current design meets all goals.")
        else:
            for s in self.suggestions:
                lines.append(s.to_markdown())

        lines.extend([
            "## Current Code Snippet",
            "",
            "```verilog",
            self.code_snippet or "*(not available)*",
            "```",
            "",
            "## Agent Interface",
            "",
            self.agent_interface,
            "",
        ])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Optimization Strategy Base Class
# ---------------------------------------------------------------------------

class OptimizationStrategy:
    """Base class for an optimization strategy.

    策略负责 **分析现状、提出建议并执行 AST 修改**。
    optimize() 迭代调用 propose → apply → re-analyze → verify。
    """

    name: str = "base"
    level: int = 1  # 0=arch, 1=AST, 2=RTL, 3=synthesis

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        """Propose candidate optimizations. Returns list of change dicts."""
        return []

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Actually apply the change to the module AST. Returns True if successful."""
        return False

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        """Estimate the impact of a change on the PPA report."""
        return {}


# ---------------------------------------------------------------------------
# Strategy: Pipeline Insertion
# ---------------------------------------------------------------------------

class PipelineInsertion(OptimizationStrategy):
    """插入流水线寄存器以打断长组合路径。

    Improved: batch ALL signals exceeding the depth threshold into a single
    pipeline stage (one `always @(posedge clk)` block), instead of creating
    individual sequential blocks per signal. This produces proper staged
    pipeline registers with intermediate combinational logic preserved.
    """

    name = "pipeline_insertion"
    level = 1

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        goal_depth = spec.ppa.max_logic_depth
        if goal_depth is None:
            return proposals

        analyzer = PPAAnalyzer(module)
        depths = analyzer._critical_path_depth()
        if not depths:
            return proposals

        max_depth = max(depths.values())
        if max_depth > goal_depth:
            # Collect ALL signals exceeding the threshold in one batch
            exceeders = [
                (sig, d) for sig, d in depths.items() if d > goal_depth
            ]
            exceeders.sort(key=lambda x: -x[1])

            # Cap to avoid huge stages; take top signals up to a reasonable limit
            max_signals_per_stage = 12
            batch = exceeders[:max_signals_per_stage]

            proposals.append({
                "type": "pipeline_stage",
                "signals": [s for s, _ in batch],
                "depths": {s: d for s, d in batch},
                "max_depth": max_depth,
                "target_depth": goal_depth,
                "num_signals": len(batch),
                "description": f"Insert pipeline stage for {len(batch)} signals exceeding depth {goal_depth} "
                               f"(max depth={max_depth}). Signals: {[s for s, _ in batch[:5]]}"
                               + (f" +{len(batch)-5} more" if len(batch) > 5 else ""),
            })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Insert a pipeline stage for a batch of signals in a single seq block.

        For each signal:
        1. Remove its combinational assignment (capture the driven value)
        2. Create a pipeline register (`_pipeline_<signal>`)
        3. Replace downstream references with the pipeline register

        All pipeline registers are assigned in ONE `always @(posedge clk)` block,
        producing a clean staged pipeline boundary.
        """
        targets = change.get("signals")
        if not targets:
            # Backward compat: single signal from old proposal format
            sig = change.get("signal")
            if sig:
                targets = [sig]
            else:
                return False

        # Find clock signal
        clk_signal = None
        for name, inp in module._inputs.items():
            if "clk" in name.lower():
                clk_signal = inp
                break
        if clk_signal is None:
            return False

        def _get_assign_target_name(stmt) -> str:
            t = stmt.target
            if hasattr(t, 'name'):
                return t.name
            if isinstance(t, Slice) and hasattr(t.operand, 'name'):
                return t.operand.name
            return ""

        def _find_sig(name: str):
            for d in (module._wires, module._outputs):
                if name in d:
                    return d[name]
            if name in module._regs:
                return module._regs[name]
            # Scan comb block targets for unregistered Wire objects
            for body in module._comb_blocks:
                for stmt in body:
                    if isinstance(stmt, Assign) and _get_assign_target_name(stmt) == name:
                        return stmt.target
            if module._top_level:
                for stmt in module._top_level:
                    if isinstance(stmt, Assign) and _get_assign_target_name(stmt) == name:
                        return stmt.target
            return None

        def _remove_assigns_in_body(body: List[Any], target_name: str) -> Tuple[bool, Any]:
            """Recursively remove ALL assignments to target_name from body.

            Returns (found, first_driven_value) — captures the first value found.
            Handles nested IfNode/SwitchNode bodies.
            """
            found = False
            driven_value = None

            for stmt in body:
                if isinstance(stmt, Assign) and _get_assign_target_name(stmt) == target_name:
                    if driven_value is None:
                        driven_value = stmt.value
                    found = True
                    # Mark for removal (set target to None)
                    stmt._remove = True
                elif isinstance(stmt, IfNode):
                    # Check then_body
                    f, v = _remove_assigns_in_body(stmt.then_body, target_name)
                    if f: found = True
                    if v is not None and driven_value is None:
                        driven_value = v
                    # Check else_body
                    f, v = _remove_assigns_in_body(stmt.else_body, target_name)
                    if f: found = True
                    if v is not None and driven_value is None:
                        driven_value = v
                    # Check elif_bodies
                    for _cond, case_body in stmt.elif_bodies:
                        f, v = _remove_assigns_in_body(case_body, target_name)
                        if f: found = True
                        if v is not None and driven_value is None:
                            driven_value = v
                elif isinstance(stmt, SwitchNode):
                    for _case_val, case_body in stmt.cases:
                        f, v = _remove_assigns_in_body(case_body, target_name)
                        if f: found = True
                        if v is not None and driven_value is None:
                            driven_value = v
                    f, v = _remove_assigns_in_body(stmt.default_body, target_name)
                    if f: found = True
                    if v is not None and driven_value is None:
                        driven_value = v

            return found, driven_value

        def _prune_removed(body: List[Any]) -> List[Any]:
            """Remove statements marked with _remove, recursively prune IfNode/SwitchNode bodies."""
            new_body = []
            for stmt in body:
                if getattr(stmt, '_remove', False):
                    continue
                elif isinstance(stmt, IfNode):
                    stmt.then_body = _prune_removed(stmt.then_body)
                    stmt.else_body = _prune_removed(stmt.else_body)
                    stmt.elif_bodies = [
                        (cond, _prune_removed(case_body))
                        for cond, case_body in stmt.elif_bodies
                    ]
                    new_body.append(stmt)
                elif isinstance(stmt, SwitchNode):
                    stmt.cases = [
                        (case_val, _prune_removed(case_body))
                        for case_val, case_body in stmt.cases
                    ]
                    stmt.default_body = _prune_removed(stmt.default_body)
                    new_body.append(stmt)
                else:
                    new_body.append(stmt)
            return new_body

        # Gather all (signal_obj, driven_value, body_ref) tuples
        pipeline_regs: List[Tuple[str, Reg, Any]] = []  # (old_name, pipe_reg, driven_value)

        for target in targets:
            target_sig = _find_sig(target)
            if target_sig is None:
                continue

            driven_value = None
            # Search comb blocks + top_level for ALL assignments (including nested)
            search_lists: List[List[Any]] = list(module._comb_blocks)
            if module._top_level:
                search_lists = search_lists + [module._top_level]

            for body in search_lists:
                found, dv = _remove_assigns_in_body(body, target)
                if found and dv is not None:
                    driven_value = dv
                    # Prune removed statements
                    body[:] = _prune_removed(body)

            if driven_value is None:
                continue

            # Create pipeline register
            pipe_reg_name = f"_pipeline_{target}"
            pipe_reg = Reg(target_sig.width, pipe_reg_name)
            module._regs[pipe_reg_name] = pipe_reg
            pipeline_regs.append((target, pipe_reg, driven_value))

        if not pipeline_regs:
            return False

        # Emit ALL pipeline register assignments in a SINGLE seq block
        with module.seq(clk_signal):
            for _name, pipe_reg, driven_value in pipeline_regs:
                pipe_reg <<= driven_value

        # Re-drive each pipelined signal from its pipeline register.
        # This ensures output ports and non-pipelined downstream signals
        # that still reference the original name get the pipelined value.
        for old_name, pipe_reg, driven_value in pipeline_regs:
            target_sig = _find_sig(old_name)
            if target_sig is not None:
                # Append a fresh comb assignment: old_name = _pipeline_<old_name>
                module._comb_blocks[-1].append(Assign(target_sig, Ref(pipe_reg), True))

        # Replace downstream references for each signal
        for old_name, pipe_reg, _driven_value in pipeline_regs:
            for block in module._comb_blocks:
                self._replace_refs_in_body(block, old_name, pipe_reg)
            if module._top_level:
                self._replace_refs_in_body(module._top_level, old_name, pipe_reg)

        # Also replace references in the driven_value expressions of other pipeline regs.
        # This handles the case where signal B = signal A, and both are pipelined:
        # _pipeline_B's driven_value originally references A, which must be updated
        # to reference _pipeline_A after A itself is pipelined.
        for old_name, pipe_reg, _driven_value in pipeline_regs:
            for _other_name, _other_reg, other_driven in pipeline_regs:
                if other_driven is not None:
                    self._replace_in_expr(other_driven, old_name, pipe_reg)

        return True

    def _replace_refs_in_body(self, body: List[Any], old_name: str, new_signal: Reg) -> int:
        """Replace Ref(old_name) or direct Signal(old_name) with Ref(new_signal) in body."""
        count = 0
        for stmt in body:
            if isinstance(stmt, Assign):
                if isinstance(stmt.value, Signal) and stmt.value.name == old_name:
                    stmt.value = Ref(new_signal)
                    count += 1
                else:
                    count += self._replace_in_expr(stmt.value, old_name, new_signal)
            elif isinstance(stmt, IfNode):
                count += self._replace_in_expr(stmt.cond, old_name, new_signal)
                count += self._replace_refs_in_body(stmt.then_body, old_name, new_signal)
                count += self._replace_refs_in_body(stmt.else_body, old_name, new_signal)
            elif isinstance(stmt, SwitchNode):
                count += self._replace_in_expr(stmt.expr, old_name, new_signal)
                for _, case_body in stmt.cases:
                    count += self._replace_refs_in_body(case_body, old_name, new_signal)
                count += self._replace_refs_in_body(stmt.default_body, old_name, new_signal)
        return count

    def _replace_in_expr(self, expr: Expr, old_name: str, new_signal: Reg) -> int:
        """Replace Ref(old_name) or direct Signal(old_name) in expression tree with Ref(new_signal)."""
        count = 0
        if isinstance(expr, Ref) and expr.signal.name == old_name:
            expr.signal = new_signal
            count += 1
        elif isinstance(expr, Signal) and expr.name == old_name:
            expr.name = new_signal.name
            expr.width = new_signal.width
            count += 1
        elif isinstance(expr, BinOp):
            count += self._replace_in_expr(expr.lhs, old_name, new_signal)
            count += self._replace_in_expr(expr.rhs, old_name, new_signal)
        elif isinstance(expr, UnaryOp):
            count += self._replace_in_expr(expr.operand, old_name, new_signal)
        elif isinstance(expr, Mux):
            count += self._replace_in_expr(expr.cond, old_name, new_signal)
            count += self._replace_in_expr(expr.true_expr, old_name, new_signal)
            count += self._replace_in_expr(expr.false_expr, old_name, new_signal)
        elif isinstance(expr, Slice):
            count += self._replace_in_expr(expr.operand, old_name, new_signal)
        elif isinstance(expr, BitSelect):
            count += self._replace_in_expr(expr.operand, old_name, new_signal)
            count += self._replace_in_expr(expr.index, old_name, new_signal)
        elif isinstance(expr, Concat):
            for op in expr.operands:
                count += self._replace_in_expr(op, old_name, new_signal)
        return count

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        num = change.get("num_signals", change.get("stages", 1))
        return {"logic_depth": -num, "registers": +num, "area": +num * 3}


# ---------------------------------------------------------------------------
# Strategy: Resource Sharing
# ---------------------------------------------------------------------------

class ResourceSharing(OptimizationStrategy):
    """在互斥路径中共享算子以减少面积。"""

    name = "resource_sharing"
    level = 1

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []

        if not spec.ppa.allow_resource_sharing:
            return proposals

        for block in module._comb_blocks:
            for stmt in block:
                if isinstance(stmt, SwitchNode):
                    ops_per_case = []
                    for case_val, case_body in stmt.cases:
                        for case_stmt in case_body:
                            if isinstance(case_stmt, Assign):
                                ops = self._count_ops(case_stmt.value)
                                ops_per_case.append((case_val, ops))

                    if len(ops_per_case) > 2:
                        proposals.append({
                            "type": "share_switch_arith",
                            "switch_id": id(stmt),
                            "shared_resource": f"shared_alu_{id(stmt)}",
                            "description": f"SwitchNode (id={id(stmt)}) 的 {len(ops_per_case)} 个 case "
                                           f"包含相似算术操作，建议共享一个 ALU 并通过 MUX 选择输入。",
                        })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Resource sharing requires significant AST restructuring; skip for now."""
        return False

    def _count_ops(self, expr: Expr) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        self._walk_ops(expr, counts)
        return counts

    def _walk_ops(self, expr: Expr, counts: Dict[str, int]):
        if isinstance(expr, BinOp):
            counts[expr.op] = counts.get(expr.op, 0) + 1
            self._walk_ops(expr.lhs, counts)
            self._walk_ops(expr.rhs, counts)
        elif isinstance(expr, Mux):
            self._walk_ops(expr.true_expr, counts)
            self._walk_ops(expr.false_expr, counts)
            self._walk_ops(expr.cond, counts)

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"area": -15, "logic_depth": +1, "power": -5}


# ---------------------------------------------------------------------------
# Strategy: Bitwidth Reduction
# ---------------------------------------------------------------------------

class BitwidthReduction(OptimizationStrategy):
    """根据实际使用情况缩减位宽。"""

    name = "bitwidth_reduction"
    level = 2

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        analyzer = PPAAnalyzer(module)
        fanout = analyzer._fanout_analysis()

        for name, wire in module._wires.items():
            if wire.width > 32 and fanout.get(name, 0) <= 1:
                # Low fanout, wide wire — likely can be narrowed
                proposals.append({
                    "type": "narrow_wire",
                    "signal": name,
                    "current_width": wire.width,
                    "fanout": fanout.get(name, 0),
                    "description": f"低扇出宽信号 '{name}' ({wire.width}-bit, fanout={fanout.get(name, 0)}), "
                                   f"建议检查是否可以截断。",
                })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Bitwidth narrowing requires dataflow analysis; not fully automatic."""
        return False

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"area": -5, "power": -3}


# ---------------------------------------------------------------------------
# Strategy: Operator Selection
# ---------------------------------------------------------------------------

class OperatorSelection(OptimizationStrategy):
    """根据 PPA 目标选择算子实现。"""

    name = "operator_selection"
    level = 1

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        ppa = spec.ppa

        if ppa.priority == "timing_first" and not ppa.allow_fast_adder:
            proposals.append({
                "type": "enable_fast_adder",
                "description": "时序优先目标下，建议将关键路径上的加法器替换为进位前瞻加法器 (CLA) "
                               "或进位选择加法器，以降低逻辑深度。",
            })

        if ppa.priority == "area_first":
            proposals.append({
                "type": "force_array_multiplier",
                "description": "面积优先目标下，建议将乘法器替换为阵列乘法器 (Array Multiplier) "
                               "或串行 Booth 乘法器，以牺牲时序换取更小面积。",
            })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Operator selection is handled by the synthesis tool, not at DSL level."""
        return False

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        if change.get("type") == "enable_fast_adder":
            return {"logic_depth": -1, "area": +5}
        if change.get("type") == "force_array_multiplier":
            return {"area": -20, "logic_depth": +2}
        return {}


# ---------------------------------------------------------------------------
# Strategy: Mux Balancing
# ---------------------------------------------------------------------------

class MuxBalancing(OptimizationStrategy):
    """将不平衡的 If/Switch 链转换为平衡的多路复用器树。"""

    name = "mux_balancing"
    level = 2

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []

        for i, block in enumerate(module._comb_blocks):
            for stmt in block:
                depth = self._max_if_depth(stmt)
                if depth > 4:
                    proposals.append({
                        "type": "balance_mux_tree",
                        "block_index": i,
                        "location": id(stmt),
                        "current_depth": depth,
                        "description": f"发现深度为 {depth} 的嵌套 If/Switch 链，"
                                       f"建议重新平衡 MUX 树以降低关键路径延迟。",
                    })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """Flatten deeply nested if-else chains into a single Mux chain."""
        block_index = change.get("block_index")
        if block_index is None or block_index >= len(module._comb_blocks):
            return False
        block = module._comb_blocks[block_index]
        return self._flatten_if_chain(block)

    def _flatten_if_chain(self, block: List[Any]) -> bool:
        """Replace deeply nested IfNode with flat priority mux chain."""
        new_body = []
        changes = 0
        for stmt in block:
            if isinstance(stmt, IfNode):
                depth = self._max_if_depth(stmt)
                if depth > 4:
                    # Flatten: collect all (cond, body) pairs and emit as single mux chain
                    flat = self._flatten_if_node(stmt)
                    new_body.extend(flat)
                    changes += 1
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)
        if changes > 0:
            block[:] = new_body
        return changes > 0

    def _flatten_if_node(self, node: IfNode) -> List[Any]:
        """Recursively flatten IfNode into a list of IfNode with no nesting."""
        results: List[Any] = []
        results.append(IfNode(node.cond))
        results[-1].then_body = list(node.then_body)
        results[-1].else_body = []

        # Flatten elif_bodies
        for cond, body in node.elif_bodies:
            elif_node = IfNode(cond)
            elif_node.then_body = list(body)
            elif_node.else_body = []
            results.append(elif_node)

        # Recurse into else_body if it contains a single IfNode
        if len(node.else_body) == 1 and isinstance(node.else_body[0], IfNode):
            results.extend(self._flatten_if_node(node.else_body[0]))
        elif node.else_body:
            results[-1].else_body = list(node.else_body)

        return results

    def _max_if_depth(self, stmt) -> int:
        if isinstance(stmt, IfNode):
            then_d = max((self._max_if_depth(s) for s in stmt.then_body), default=0)
            else_d = max((self._max_if_depth(s) for s in stmt.else_body), default=0)
            max_nested_else = 0
            if len(stmt.else_body) == 1 and isinstance(stmt.else_body[0], IfNode):
                max_nested_else = self._max_if_depth(stmt.else_body[0])
            return 1 + max(then_d, else_d, max_nested_else)
        return 0

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"logic_depth": -2, "area": 0}


# ---------------------------------------------------------------------------
# Strategy: FSM Encoding Selection
# ---------------------------------------------------------------------------

class FSMEncodingSelect(OptimizationStrategy):
    """根据 PPA 目标选择 FSM 编码方式。"""

    name = "fsm_encoding_select"
    level = 0

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        ppa = spec.ppa

        # Count FSM-related regs (signals with "state" in name)
        fsm_reg_names = [name for name in module._regs if "state" in name.lower()]
        if not fsm_reg_names:
            return proposals

        if ppa.priority == "timing_first":
            proposals.append({
                "type": "encoding",
                "style": "one_hot",
                "reg_names": fsm_reg_names,
                "description": "时序优先：建议 FSM 使用 one-hot 编码，获得最快的次态解码速度。",
            })
        elif ppa.priority == "area_first":
            proposals.append({
                "type": "encoding",
                "style": "binary",
                "reg_names": [r.name for r in fsm_regs],
                "description": "面积优先：建议 FSM 使用 binary 编码，用最少的寄存器位数表示状态。",
            })
        elif ppa.priority == "power_first":
            proposals.append({
                "type": "encoding",
                "style": "gray",
                "reg_names": [r.name for r in fsm_regs],
                "description": "功耗优先：建议 FSM 使用 Gray 编码，每次状态转换仅翻转一位，降低动态功耗。",
            })

        return proposals

    def apply(self, module: Module, change: Dict[str, Any]) -> bool:
        """FSM encoding is handled by synthesis tool; not modifiable at DSL level."""
        return False

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        style = change.get("style", "auto")
        if style == "one_hot":
            return {"logic_depth": -1, "registers": +2, "area": +5}
        elif style == "binary":
            return {"registers": -2, "area": -5, "logic_depth": +1}
        elif style == "gray":
            return {"power": -5, "area": 0}
        return {}


# ---------------------------------------------------------------------------
# Optimization Result — before/after 对比
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """优化前后对比结果。"""
    module: Module
    iteration: int
    score_before: PPAScore
    score_after: PPAScore
    strategies_applied: List[str]
    improved: bool
    agent_notes: str = ""

    def summary(self) -> Dict[str, Any]:
        return {
            "improved": self.improved,
            "score_before": self.score_before.total,
            "score_after": self.score_after.total,
            "delta": self.score_before.total - self.score_after.total,
            "strategies": self.strategies_applied,
            "notes": self.agent_notes,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Optimization Result",
            "",
            f"- **Improved**: {'Yes' if self.improved else 'No'}",
            f"- **Score Before**: {self.score_before.total:.4f}",
            f"- **Score After**: {self.score_after.total:.4f}",
            f"- **Delta**: {self.score_before.total - self.score_after.total:.4f}",
            f"- **Iterations**: {self.iteration}",
        ]
        if self.agent_notes:
            lines.append(f"- **Agent Notes**: {self.agent_notes}")
        if self.strategies_applied:
            lines.append("- **Applied Strategies**:")
            for s in self.strategies_applied:
                lines.append(f"  - {s}")
        if self.score_after.violations:
            lines.append("- **Remaining Violations**:")
            for v in self.score_after.violations:
                lines.append(f"  - {v}")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# PPA Optimizer — Main class
# ---------------------------------------------------------------------------

class PPAOptimizer:
    """PPA 分析与优化指南生成器。

    框架职责：分析 → 建议 → 生成指南 → 接收注入 → 计算对比。
    智能体职责：阅读指南 → 手动实现优化 → 通过 inject_optimized() 注入。
    """

    DEFAULT_STRATEGIES = [
        PipelineInsertion(),
        ResourceSharing(),
        BitwidthReduction(),
        OperatorSelection(),
        MuxBalancing(),
        FSMEncodingSelect(),
    ]

    def __init__(self, module: Module, spec: SpecIR,
                 analyzer: Optional[PPAAnalyzer] = None,
                 strategies: Optional[List[OptimizationStrategy]] = None):
        self._original_module = module
        self.spec = spec
        self.analyzer = analyzer or PPAAnalyzer(module)
        self.strategies = strategies or self.DEFAULT_STRATEGIES
        self.goal = PPAGoal(
            max_area=spec.ppa.max_area,
            max_logic_depth=spec.ppa.max_logic_depth,
            max_registers=spec.ppa.max_registers,
            max_power=spec.ppa.max_power,
            target_freq_mhz=spec.timing.target_freq_mhz,
        )

    # ------------------------------------------------------------------
    # Primary API: Analyze → Guide
    # ------------------------------------------------------------------

    def analyze(self) -> OptimizationGuide:
        """分析当前模块，生成优化指南（不修改任何模块）。"""
        self.analyzer.module = self._original_module
        report = self.analyzer.analyze()
        score = PPAScore.compute(report, self.goal)

        # Collect suggestions from all strategies
        suggestions: List[OptimizationSuggestion] = []
        for strategy in self.strategies:
            proposals = strategy.propose(self._original_module, self.spec)
            for change in proposals:
                impact = strategy.estimate_impact(report, change)
                priority = "high" if impact.get("logic_depth", 0) < -1 or impact.get("area", 0) < -10 else "medium"
                suggestions.append(OptimizationSuggestion(
                    strategy=strategy.name,
                    change_type=change.get("type", "unknown"),
                    target=change.get("signal", change.get("shared_resource",
                          change.get("location", change.get("style", "module")))),
                    description=change.get("description", ""),
                    estimated_impact=impact,
                    priority=priority,
                ))

        # Try to get a code snippet
        code_snippet = ""
        try:
            code_snippet = self._original_module.to_verilog()
        except Exception:
            pass

        return OptimizationGuide(
            module_name=getattr(self._original_module, "name", "unknown"),
            current_ppa=report,
            current_score=score,
            goals=self.goal,
            suggestions=suggestions,
            code_snippet=code_snippet,
        )

    def inject_optimized(self, optimized_module: Module, notes: str = "") -> OptimizationResult:
        """智能体注入优化后的模块，框架自动计算 before/after 对比。

        Args:
            optimized_module: 智能体优化后的 Module 实例
            notes: 智能体填写的优化说明

        Returns:
            OptimizationResult: 包含 score_before / score_after 的对比结果
        """
        # Before score
        self.analyzer.module = self._original_module
        report_before = self.analyzer.analyze()
        score_before = PPAScore.compute(report_before, self.goal)

        # After score
        self.analyzer.module = optimized_module
        report_after = self.analyzer.analyze()
        score_after = PPAScore.compute(report_after, self.goal)

        return OptimizationResult(
            module=optimized_module,
            iteration=1,
            score_before=score_before,
            score_after=score_after,
            strategies_applied=["agent_injected"],
            improved=score_after.total < score_before.total,
            agent_notes=notes,
        )

    # ------------------------------------------------------------------
    # Optimization Loop: analyze → propose → apply → verify
    # ------------------------------------------------------------------

    def optimize(self, max_iterations: int = 5) -> OptimizationResult:
        """Iteratively analyze and apply optimizations until no improvement.

        For each iteration:
        1. Analyze current PPA
        2. Propose changes from all strategies
        3. Apply changes that can improve PPA
        4. Re-analyze and verify improvement
        5. Stop if no improvement or max iterations reached
        """
        # Before: analyze original
        report_before = self.analyzer.analyze()
        score_before = PPAScore.compute(report_before, self.goal)

        applied_strategies = []
        module = self._original_module

        for iteration in range(max_iterations):
            # Collect proposals from all strategies
            all_changes = []
            for strategy in self.strategies:
                changes = strategy.propose(module, self.spec)
                for change in changes:
                    all_changes.append((strategy, change))

            if not all_changes:
                break

            # Try applying high-priority changes first
            improved_this_round = False
            for strategy, change in all_changes:
                impact = strategy.estimate_impact({}, change)
                # Only apply changes that reduce logic_depth or area
                if impact.get("logic_depth", 0) < 0 or impact.get("area", 0) < 0:
                    result = strategy.apply(module, change)
                    if result:
                        applied_strategies.append(f"{strategy.name}:{change.get('type', 'unknown')}")
                        improved_this_round = True

            if not improved_this_round:
                break

        # After: re-analyze
        self.analyzer.module = module
        report_after = self.analyzer.analyze()
        score_after = PPAScore.compute(report_after, self.goal)

        return OptimizationResult(
            module=module,
            iteration=len(applied_strategies),
            score_before=score_before,
            score_after=score_after,
            strategies_applied=applied_strategies,
            improved=score_after.total < score_before.total,
        )

    def optimize_single(self, strategy_name: str) -> OptimizationResult:
        """Run optimization with a single named strategy."""
        strategy_map = {s.name: s for s in self.strategies}
        if strategy_name not in strategy_map:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategy_map.keys())}")

        # Before
        report_before = self.analyzer.analyze()
        score_before = PPAScore.compute(report_before, self.goal)

        strategy = strategy_map[strategy_name]
        changes = strategy.propose(self._original_module, self.spec)
        applied = []

        for change in changes:
            impact = strategy.estimate_impact({}, change)
            if impact.get("logic_depth", 0) < 0 or impact.get("area", 0) < 0:
                if strategy.apply(self._original_module, change):
                    applied.append(change.get("type", "unknown"))

        # After
        self.analyzer.module = self._original_module
        report_after = self.analyzer.analyze()
        score_after = PPAScore.compute(report_after, self.goal)

        return OptimizationResult(
            module=self._original_module,
            iteration=len(applied),
            score_before=score_before,
            score_after=score_after,
            strategies_applied=[f"{strategy_name}:{a}" for a in applied],
            improved=score_after.total < score_before.total,
        )
