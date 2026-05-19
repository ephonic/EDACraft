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
    Const,
    Expr,
    IfNode,
    Module,
    Mux,
    Signal,
    SwitchNode,
    Wire,
)
from rtlgen.ppa import PPAAnalyzer
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

    策略仅负责 **分析现状并提出建议**，不执行任何 AST 修改。
    智能体阅读建议后，直接操作 Module 的 AST（_comb_blocks, _wires, _regs 等）
    完成优化，然后通过 PPAOptimizer.inject_optimized() 注入结果。

    注意：本类**没有** apply() 方法。智能体不编写策略的 Python 实现代码，
    而是直接根据建议对 DSL 模块做结构性修改。
    """

    name: str = "base"
    level: int = 1  # 0=arch, 1=AST, 2=RTL, 3=synthesis

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        """Propose candidate optimizations. Returns list of change dicts."""
        return []

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        """Estimate the impact of a change on the PPA report."""
        return {}


# ---------------------------------------------------------------------------
# Strategy: Pipeline Insertion
# ---------------------------------------------------------------------------

class PipelineInsertion(OptimizationStrategy):
    """建议插入流水线寄存器以打断长组合路径。"""

    name = "pipeline_insertion"
    level = 1

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        goal_depth = spec.ppa.max_logic_depth
        if goal_depth is None:
            return proposals

        for name, sig in module._outputs.items():
            proposals.append({
                "type": "pipeline_output",
                "signal": name,
                "stages": 2,
                "description": f"在输出 '{name}' 的路径上插入 {2} 级流水线寄存器，"
                               f"将组合逻辑深度从当前值降至目标 {goal_depth} 以内。",
            })

        for name, wire in module._wires.items():
            if wire.width > 16:
                proposals.append({
                    "type": "pipeline_wire",
                    "signal": name,
                    "stages": 2,
                    "description": f"在宽位内部信号 '{name}' ({wire.width}-bit) 上插入流水线寄存器，"
                                   f"降低关键路径延迟。",
                })

        return proposals

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"logic_depth": -1, "registers": +1, "area": +5}


# ---------------------------------------------------------------------------
# Strategy: Resource Sharing
# ---------------------------------------------------------------------------

class ResourceSharing(OptimizationStrategy):
    """建议共享互斥路径中的算子以减少面积。"""

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
    """建议移除冗余的位宽扩展和掩码。"""

    name = "bitwidth_reduction"
    level = 2

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []

        for name, wire in module._wires.items():
            proposals.append({
                "type": "check_width",
                "signal": name,
                "current_width": wire.width,
                "description": f"检查信号 '{name}' 的位宽 ({wire.width} bit) 是否超出其实际使用需求，"
                               f"考虑截断以减小面积和功耗。",
            })

        return proposals

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"area": -5, "power": -3}


# ---------------------------------------------------------------------------
# Strategy: Operator Selection
# ---------------------------------------------------------------------------

class OperatorSelection(OptimizationStrategy):
    """建议根据 PPA 目标更换算子实现。"""

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
    """建议将不平衡的多路复用器树重新平衡。"""

    name = "mux_balancing"
    level = 2

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []

        for block in module._comb_blocks:
            for stmt in block:
                depth = self._max_if_depth(stmt)
                if depth > 4:
                    proposals.append({
                        "type": "balance_mux_tree",
                        "location": id(stmt),
                        "current_depth": depth,
                        "description": f"发现深度为 {depth} 的嵌套 If/Switch 链，"
                                       f"建议重新平衡 MUX 树以降低关键路径延迟。",
                    })

        return proposals

    def _max_if_depth(self, stmt) -> int:
        if isinstance(stmt, IfNode):
            then_d = max((self._max_if_depth(s) for s in stmt.then_body), default=0)
            else_d = max((self._max_if_depth(s) for s in stmt.else_body), default=0)
            return 1 + max(then_d, else_d)
        return 0

    def estimate_impact(self, report: Dict[str, Any], change: Dict[str, Any]) -> Dict[str, float]:
        return {"logic_depth": -2, "area": 0}


# ---------------------------------------------------------------------------
# Strategy: FSM Encoding Selection
# ---------------------------------------------------------------------------

class FSMEncodingSelect(OptimizationStrategy):
    """建议根据 PPA 目标选择最优 FSM 编码方式。"""

    name = "fsm_encoding_select"
    level = 0

    def propose(self, module: Module, spec: SpecIR) -> List[Dict[str, Any]]:
        proposals = []
        ppa = spec.ppa

        if ppa.priority == "timing_first":
            proposals.append({
                "type": "encoding",
                "style": "one_hot",
                "description": "时序优先：建议 FSM 使用 one-hot 编码，获得最快的次态解码速度。",
            })
        elif ppa.priority == "area_first":
            proposals.append({
                "type": "encoding",
                "style": "binary",
                "description": "面积优先：建议 FSM 使用 binary 编码，用最少的寄存器位数表示状态。",
            })
        elif ppa.priority == "power_first":
            proposals.append({
                "type": "encoding",
                "style": "gray",
                "description": "功耗优先：建议 FSM 使用 Gray 编码，每次状态转换仅翻转一位，降低动态功耗。",
            })

        return proposals

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
    # Legacy API: kept for backward compatibility
    # ------------------------------------------------------------------

    def optimize(self, max_iterations: int = 10) -> OptimizationResult:
        """DEPRECATED: 自动优化循环已废弃。

        框架不再自动执行 AST 修改。请改用 analyze() 获取优化指南，
        由智能体实现优化后通过 inject_optimized() 注入。

        为兼容旧代码，此方法现在仅返回当前模块的 before 分析结果，
        improved=False，strategies_applied=[]。
        """
        import warnings
        warnings.warn(
            "PPAOptimizer.optimize() is deprecated. "
            "Use analyze() to get an OptimizationGuide, then inject_optimized() after agent implementation.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.analyzer.module = self._original_module
        report = self.analyzer.analyze()
        score = PPAScore.compute(report, self.goal)
        return OptimizationResult(
            module=self._original_module,
            iteration=0,
            score_before=score,
            score_after=score,
            strategies_applied=[],
            improved=False,
        )

    def optimize_single(self, strategy_name: str) -> OptimizationResult:
        """DEPRECATED: 单策略自动优化已废弃。

        框架不再自动执行 AST 修改。请改用 analyze() 获取优化指南，
        由智能体实现优化后通过 inject_optimized() 注入。
        """
        import warnings
        warnings.warn(
            "PPAOptimizer.optimize_single() is deprecated. "
            "Use analyze() to get an OptimizationGuide, then inject_optimized() after agent implementation.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.optimize()
