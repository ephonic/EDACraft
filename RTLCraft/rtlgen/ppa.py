"""
rtlgen.ppa — PPA (Power, Performance, Area) Analyzer

基于 AST 静态分析与 Simulator trace 动态分析，快速估算硬件设计的
PPA 指标并给出优化建议。
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from rtlgen.core import (
    ArrayRead,
    ArrayWrite,
    Assign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    ForGenNode,
    GenIfNode,
    IfNode,
    IndexedAssign,
    MemRead,
    MemWrite,
    Module,
    Mux,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
)
from rtlgen.sim import Simulator
from rtlgen.tech_library import TechNode

# ---------------------------------------------------------------------------
# Area weight table (equivalent NAND2 gate units, normalized)
# ---------------------------------------------------------------------------
_AREA_WEIGHTS: Dict[str, float] = {
    "AND": 1.0,
    "OR": 1.0,
    "XOR": 1.5,
    "XNOR": 2.0,
    "NAND": 1.0,
    "NOR": 1.0,
    "~": 0.5,
    "+": 4.0,
    "-": 4.0,
    "*": 8.0,
    "/": 16.0,
    "%": 16.0,
    "<<": 0.5,
    ">>": 0.5,
    "==": 2.0,
    "!=": 2.0,
    "<": 3.0,
    "<=": 3.0,
    ">": 3.0,
    ">=": 3.0,
    "Mux": 3.0,
    "Concat": 0.1,
    "Slice": 0.1,
    "BitSelect": 0.2,
    "MemRead": 2.0,
    "ArrayRead": 1.0,
}


class PPAAnalyzer:
    """PPA 分析器：静态分析时序/面积，动态分析功耗。"""

    def __init__(self, module: Module, tech_node: Optional[str] = None):
        self.module = module
        self._tech_node: Optional[TechNode] = None
        if tech_node:
            try:
                self._tech_node = TechNode(tech_node)
            except ValueError:
                pass

    # =====================================================================
    # Public API
    # =====================================================================
    def analyze(self, sim: Optional[Simulator] = None, n_cycles: Optional[int] = None) -> Dict[str, Any]:
        """Unified PPA analysis entry point.

        If *sim* is provided, performs both static and dynamic analysis and
        merges the results.  Otherwise returns only static metrics.
        """
        result = self.analyze_static()
        if sim is not None:
            result["dynamic"] = self.analyze_dynamic(sim, n_cycles)
        if self._tech_node is not None:
            result["tech_aware"] = self._tech_node_analysis()
        return result

    def analyze_static(self) -> Dict[str, Any]:
        """纯 AST 静态分析，返回时序与面积指标。"""
        return {
            "logic_depth": self._critical_path_depth(),
            "gate_count": self._estimate_gate_count(),
            "reg_bits": self._count_reg_bits(),
            "mux_complexity": self._mux_complexity(),
            "fanout_report": self._fanout_analysis(),
            "dead_signals": self._find_dead_signals(),
            "submodule_summary": self._submodule_summary(),
        }

    def check_intent(self) -> List[Dict[str, Any]]:
        """对照模块声明的 design intent 检查 PPA 是否达标。

        返回检查结果列表，每项包含 intent 字段、目标值、实际值、是否通过。
        """
        intent = getattr(self.module, "_design_intent", None)
        if intent is None:
            return []

        results: List[Dict[str, Any]] = []
        static = self.analyze_static()

        # 检查逻辑深度 vs 延迟约束
        if intent.latency_cycles is not None:
            max_depth = 0
            depths = static.get("logic_depth", {})
            if depths:
                max_depth = max(depths.values()) if depths else 0
            # 粗略估计：每级逻辑深度约需 1 个周期
            passed = max_depth <= intent.latency_cycles
            results.append({
                "field": "latency_cycles",
                "target": intent.latency_cycles,
                "actual": max_depth,
                "pass": passed,
                "message": f"Logic depth {max_depth} vs target {intent.latency_cycles} cycles" if passed
                    else f"Logic depth {max_depth} exceeds target {intent.latency_cycles} cycles — consider pipelining"
            })

        # 检查面积 vs 面积预算
        if intent.area_budget is not None:
            gate_count = static.get("gate_count", 0)
            passed = gate_count <= intent.area_budget
            results.append({
                "field": "area_budget",
                "target": intent.area_budget,
                "actual": gate_count,
                "pass": passed,
                "message": f"Gate count {gate_count} within budget {intent.area_budget}" if passed
                    else f"Gate count {gate_count} exceeds budget {intent.area_budget}"
            })

        # 检查频率可行性（基于最大逻辑深度）
        if intent.clock_freq is not None:
            depths = static.get("logic_depth", {})
            max_depth = max(depths.values()) if depths else 0
            # 粗略估计：每级 NAND2 延迟 ~50ps，目标周期
            target_period_ns = 1e9 / intent.clock_freq
            estimated_delay_ns = max(max_depth * 0.05, 0.05)  # 50ps per level, min 50ps
            max_freq_mhz = 1 / (estimated_delay_ns * 1e-3)  # MHz
            passed = estimated_delay_ns < target_period_ns
            results.append({
                "field": "clock_freq",
                "target": f"{intent.clock_freq/1e6:.0f}MHz",
                "actual": f"~{max_freq_mhz:.0f}MHz max (depth={max_depth})",
                "pass": passed,
                "message": f"Estimated max frequency ok for {intent.clock_freq/1e6:.0f}MHz target" if passed
                    else f"Logic depth {max_depth} may not meet {intent.clock_freq/1e6:.0f}MHz target"
            })

        return results

    def analyze_dynamic(
        self, sim: Simulator, n_cycles: Optional[int] = None
    ) -> Dict[str, Any]:
        """基于 Simulator trace 的动态功耗分析。"""
        return {
            "toggle_rates": self._compute_toggle_rates(sim, n_cycles),
            "power_hotspots": self._identify_power_hotspots(sim, n_cycles),
        }

    def suggest_optimizations(self, static: Optional[Dict[str, Any]] = None) -> List[str]:
        """根据静态分析结果生成优化建议。"""
        if static is None:
            static = self.analyze_static()
        suggestions: List[str] = []

        # 1. 逻辑深度过长
        depths = static.get("logic_depth", {})
        if depths:
            max_depth = max(depths.values())
            max_path = max(depths, key=depths.get)
            if max_depth > 6:
                suggestions.append(
                    f"[时序] 信号 '{max_path}' 组合逻辑深度为 {max_depth}，"
                    f"建议插入 pipeline stage 或拆分逻辑以降低关键路径。"
                )
            elif max_depth > 4:
                suggestions.append(
                    f"[时序] 信号 '{max_path}' 组合逻辑深度为 {max_depth}，"
                    f"在 1GHz 目标下可能处于临界状态，建议关注。"
                )

        # 2. 大面积 SwitchNode
        mux_info = static.get("mux_complexity", {})
        total_cases = mux_info.get("total_cases", 0)
        if total_cases > 32:
            suggestions.append(
                f"[面积] 设计包含 {total_cases} 个 case 分支的大规模查表，"
                f"面积占比可能较高。如频率要求不高，可考虑替换为 Memory/ROM 实现。"
            )

        # 3. 高扇出
        fanout = static.get("fanout_report", {})
        high_fanout = {k: v for k, v in fanout.items() if v > 8}
        if high_fanout:
            sig = max(high_fanout, key=high_fanout.get)
            suggestions.append(
                f"[布线] 信号 '{sig}' 扇出为 {high_fanout[sig]}，"
                f"可能导致较大线延迟。建议插入 buffer_reg 或进行负载均衡。"
            )

        # 4. 未使用信号
        dead = static.get("dead_signals", [])
        if dead:
            suggestions.append(
                f"[面积] 发现 {len(dead)} 个未使用信号: {', '.join(dead[:5])}"
                f"{' ...' if len(dead) > 5 else ''}，建议清理以减面积。"
            )

        # 5. 子模块面积汇总
        sub_summary = static.get("submodule_summary", {})
        if sub_summary:
            total_sub_gates = sum(v["gate_count"] for v in sub_summary.values())
            suggestions.append(
                f"[结构] 设计包含 {len(sub_summary)} 个子模块实例，"
                f"子模块估算等效门数合计约 {total_sub_gates:.0f}。"
            )

        return suggestions

    def report(self, sim: Optional[Simulator] = None, n_cycles: Optional[int] = None) -> str:
        """生成人类可读的 PPA 报告字符串。"""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append(f"PPA Report for Module: {self.module.name}")
        lines.append("=" * 60)

        static = self.analyze_static()
        lines.append("\n[Static Analysis]")
        depths = static["logic_depth"]
        if depths:
            max_d = max(depths.values())
            lines.append(f"  Max logic depth : {max_d}")
            lines.append(f"  Gate estimate   : {static['gate_count']:.1f} NAND2-equiv")
            lines.append(f"  Register bits   : {static['reg_bits']}")
            lines.append(f"  Case branches   : {static['mux_complexity']['total_cases']}")
            lines.append(f"  Dead signals    : {len(static['dead_signals'])}")
        else:
            lines.append("  (no combinational logic found)")

        if static["submodule_summary"]:
            lines.append(f"  Submodules      : {len(static['submodule_summary'])}")

        if sim is not None:
            dyn = self.analyze_dynamic(sim, n_cycles)
            lines.append("\n[Dynamic Analysis]")
            toggles = dyn["toggle_rates"]
            if toggles:
                avg_toggle = sum(toggles.values()) / len(toggles)
                max_sig = max(toggles, key=toggles.get)
                lines.append(f"  Avg toggle rate : {avg_toggle:.2%}/cycle")
                lines.append(f"  Hottest signal  : {max_sig} ({toggles[max_sig]:.2%}/cycle)")
            else:
                lines.append("  (no trace data available)")

        suggestions = self.suggest_optimizations(static)
        if suggestions:
            lines.append("\n[Optimization Suggestions]")
            for s in suggestions:
                lines.append(f"  • {s}")
        else:
            lines.append("\n  No obvious optimization suggestions.")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    # =====================================================================
    # Static Helpers
    # =====================================================================
    def _critical_path_depth(self) -> Dict[str, int]:
        """计算每个被驱动信号的组合逻辑深度（递归包含选择逻辑和子表达式）。"""
        import math

        drivers: Dict[str, Tuple[Any, int]] = {}

        def _collect(body: List[Any], select_extra: int = 0):
            for stmt in body:
                if isinstance(stmt, Assign):
                    if hasattr(stmt.target, 'name'):
                        key = self._assign_target_name(stmt)
                    elif isinstance(stmt.target, Slice):
                        operand = stmt.target.operand
                        if hasattr(operand, 'name'):
                            key = f"{operand.name}[{stmt.target.hi}:{stmt.target.lo}]"
                        elif isinstance(operand, Ref):
                            key = f"{operand.signal.name}[{stmt.target.hi}:{stmt.target.lo}]"
                        else:
                            key = self._expr_to_str(operand)
                    else:
                        key = self._expr_to_str(stmt.target)
                    drivers[key] = (stmt.value, select_extra)
                elif isinstance(stmt, IndexedAssign):
                    key = f"{stmt.target_signal.name}[{self._expr_to_str(stmt.index)}]"
                    drivers[key] = (stmt.value, select_extra)
                elif isinstance(stmt, IfNode):
                    cond_d = self._expr_depth(stmt.cond)
                    _collect(stmt.then_body, select_extra + cond_d + 2)
                    _collect(stmt.else_body, select_extra + cond_d + 2)
                elif isinstance(stmt, SwitchNode):
                    expr_d = self._expr_depth(stmt.expr)
                    n_cases = len(stmt.cases)
                    switch_d = expr_d + int(math.ceil(math.log2(max(n_cases, 2)))) + 1
                    for _, case_body in stmt.cases:
                        _collect(case_body, select_extra + switch_d)
                    _collect(stmt.default_body, select_extra + switch_d)
                elif isinstance(stmt, ForGenNode):
                    _collect(stmt.body, select_extra)
                elif isinstance(stmt, GenIfNode):
                    _collect(stmt.then_body, select_extra)
                    _collect(stmt.else_body, select_extra)
                elif isinstance(stmt, SubmoduleInst):
                    for pname, expr in stmt.port_map.items():
                        if isinstance(expr, Expr):
                            key = f"{stmt.name}.{pname}"
                            drivers[key] = (expr, select_extra)

        for body in self.module._comb_blocks:
            _collect(body)
        # Skip seq blocks: sequential assignments break combinatorial paths.
        # Pipeline registers driven in seq blocks should NOT appear in depth
        # analysis — they terminate the combinatorial chain.
        for stmt in self.module._top_level:
            _collect([stmt])

        memo: Dict[str, int] = {}
        visiting: Set[str] = set()

        def _depth(name: str) -> int:
            if name in memo:
                return memo[name]
            if name not in drivers:
                memo[name] = 0
                return 0
            if name in visiting:
                # Combinational loop protection: break cycle
                return 0
            visiting.add(name)
            expr, select_extra = drivers[name]
            expr_d = self._expr_depth(expr)
            d = expr_d + select_extra
            for ref_name in self._collect_ref_names(expr):
                if ref_name != name:
                    d = max(d, _depth(ref_name) + expr_d + select_extra)
            visiting.discard(name)
            memo[name] = d
            return d

        return {name: _depth(name) for name in drivers}

    def _expr_depth(self, expr: Any) -> int:
        if expr is None or isinstance(expr, (int, bool)):
            return 0
        if isinstance(expr, Const):
            return 0
        if isinstance(expr, Ref):
            return 0
        if isinstance(expr, BinOp):
            # 乘除法通常由多级 booth/阵列实现，深度更高
            mult_penalty = 2 if expr.op in ("*", "/", "%") else 0
            return 1 + mult_penalty + max(self._expr_depth(expr.lhs), self._expr_depth(expr.rhs))
        if isinstance(expr, UnaryOp):
            return 1 + self._expr_depth(expr.operand)
        if isinstance(expr, Mux):
            return 2 + max(self._expr_depth(expr.cond), self._expr_depth(expr.true_expr), self._expr_depth(expr.false_expr))
        if isinstance(expr, Slice):
            return self._expr_depth(expr.operand)
        if isinstance(expr, BitSelect):
            return 1 + max(self._expr_depth(expr.operand), self._expr_depth(expr.index))
        if isinstance(expr, Concat):
            return max((self._expr_depth(op) for op in expr.operands), default=0)
        if isinstance(expr, MemRead):
            return 2 + self._expr_depth(expr.addr)
        if isinstance(expr, ArrayRead):
            return 2 + self._expr_depth(expr.index)
        return 0

    def _estimate_gate_count(self) -> float:
        """估算整个模块的等效门面积。"""
        total = 0.0

        def _scan_body(body: List[Any], replication: int = 1):
            nonlocal total
            for stmt in body:
                if isinstance(stmt, Assign):
                    total += replication * self._expr_area(stmt.value)
                elif isinstance(stmt, IndexedAssign):
                    total += replication * self._expr_area(stmt.value)
                elif isinstance(stmt, IfNode):
                    total += replication * _AREA_WEIGHTS.get("Mux", 3.0) * stmt.cond.width
                    _scan_body(stmt.then_body, replication)
                    for _, eb in stmt.elif_bodies:
                        total += replication * _AREA_WEIGHTS.get("Mux", 3.0)
                        _scan_body(eb, replication)
                    _scan_body(stmt.else_body, replication)
                elif isinstance(stmt, SwitchNode):
                    # Switch 面积估算：N 个 case 相当于 N-1 级 MUX 或 decoder
                    n_cases = len(stmt.cases)
                    if n_cases > 0:
                        total += replication * n_cases * _AREA_WEIGHTS.get("Mux", 3.0) * stmt.expr.width
                    _scan_body(stmt.default_body, replication)
                    for _, case_body in stmt.cases:
                        _scan_body(case_body, replication)
                elif isinstance(stmt, ForGenNode):
                    reps = max(1, stmt.end - stmt.start)
                    _scan_body(stmt.body, replication * reps)
                elif isinstance(stmt, GenIfNode):
                    _scan_body(stmt.then_body, replication)
                    _scan_body(stmt.else_body, replication)
                elif isinstance(stmt, SubmoduleInst):
                    # 只计算端口映射表达式的面积
                    for expr in stmt.port_map.values():
                        if isinstance(expr, Expr):
                            total += replication * self._expr_area(expr)

        for body in self.module._comb_blocks:
            _scan_body(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan_body(body)
        for stmt in self.module._top_level:
            _scan_body([stmt])
        return total

    def _expr_area(self, expr: Any) -> float:
        if expr is None or isinstance(expr, (int, bool)):
            return 0.0
        if isinstance(expr, Const):
            return 0.0
        if isinstance(expr, Ref):
            return 0.0
        if isinstance(expr, BinOp):
            w = expr.width
            base = _AREA_WEIGHTS.get(expr.op, 2.0)
            return (base * w) + self._expr_area(expr.lhs) + self._expr_area(expr.rhs)
        if isinstance(expr, UnaryOp):
            w = expr.width
            base = _AREA_WEIGHTS.get(expr.op, 1.0)
            return (base * w) + self._expr_area(expr.operand)
        if isinstance(expr, Mux):
            w = expr.width
            base = _AREA_WEIGHTS.get("Mux", 3.0)
            return (base * w) + self._expr_area(expr.cond) + self._expr_area(expr.true_expr) + self._expr_area(expr.false_expr)
        if isinstance(expr, Slice):
            return self._expr_area(expr.operand)
        if isinstance(expr, BitSelect):
            return _AREA_WEIGHTS.get("BitSelect", 0.2) * expr.width + self._expr_area(expr.operand) + self._expr_area(expr.index)
        if isinstance(expr, Concat):
            return _AREA_WEIGHTS.get("Concat", 0.1) * expr.width + sum(self._expr_area(op) for op in expr.operands)
        if isinstance(expr, MemRead):
            return _AREA_WEIGHTS.get("MemRead", 2.0) * expr.width + self._expr_area(expr.addr)
        if isinstance(expr, ArrayRead):
            return _AREA_WEIGHTS.get("ArrayRead", 1.0) * expr.width + self._expr_area(expr.index)
        return 0.0

    def _count_reg_bits(self) -> int:
        bits = sum(r.width for r in self.module._regs.values())
        bits += sum(o.width for o in self.module._outputs.values() if o.name in self._reg_outputs())
        return bits

    def _reg_outputs(self) -> Set[str]:
        """推断哪些 output 被声明为 output reg（仅在时序块中被驱动）。"""
        driven: Set[str] = set()

        def _scan(body: List[Any]):
            for stmt in body:
                if isinstance(stmt, Assign):
                    driven.add(self._assign_target_name(stmt))
                elif isinstance(stmt, IfNode):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, cb in stmt.cases:
                        _scan(cb)
                    _scan(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _scan(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)

        # output reg 只在 always 块中被驱动
        for _, _, _, _, body in self.module._seq_blocks:
            _scan(body)
        return driven & set(self.module._outputs.keys())

    def _mux_complexity(self) -> Dict[str, Any]:
        total_cases = 0
        max_case_width = 0

        def _scan(body: List[Any], replication: int = 1):
            nonlocal total_cases, max_case_width
            for stmt in body:
                if isinstance(stmt, IfNode):
                    _scan(stmt.then_body, replication)
                    _scan(stmt.else_body, replication)
                elif isinstance(stmt, SwitchNode):
                    n = len(stmt.cases) * replication
                    total_cases += n
                    max_case_width = max(max_case_width, stmt.expr.width)
                    for _, cb in stmt.cases:
                        _scan(cb, replication)
                    _scan(stmt.default_body, replication)
                elif isinstance(stmt, ForGenNode):
                    _scan(stmt.body, replication * max(1, stmt.end - stmt.start))
                elif isinstance(stmt, GenIfNode):
                    _scan(stmt.then_body, replication)
                    _scan(stmt.else_body, replication)

        for body in self.module._comb_blocks:
            _scan(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan(body)
        return {"total_cases": total_cases, "max_case_width": max_case_width}

    def _fanout_analysis(self) -> Dict[str, int]:
        """统计每个信号的扇出（被 Ref 引用的次数）。"""
        fanout: Dict[str, int] = {}

        def _count_expr(expr: Any):
            if isinstance(expr, Ref):
                name = expr.signal.name
                fanout[name] = fanout.get(name, 0) + 1
            elif isinstance(expr, BinOp):
                _count_expr(expr.lhs)
                _count_expr(expr.rhs)
            elif isinstance(expr, UnaryOp):
                _count_expr(expr.operand)
            elif isinstance(expr, Mux):
                _count_expr(expr.cond)
                _count_expr(expr.true_expr)
                _count_expr(expr.false_expr)
            elif isinstance(expr, Slice):
                _count_expr(expr.operand)
            elif isinstance(expr, BitSelect):
                _count_expr(expr.operand)
                _count_expr(expr.index)
            elif isinstance(expr, Concat):
                for op in expr.operands:
                    _count_expr(op)
            elif isinstance(expr, MemRead):
                _count_expr(expr.addr)
            elif isinstance(expr, ArrayRead):
                _count_expr(expr.index)

        def _scan_body(body: List[Any]):
            for stmt in body:
                if isinstance(stmt, Assign):
                    _count_expr(stmt.value)
                elif isinstance(stmt, IndexedAssign):
                    _count_expr(stmt.value)
                    _count_expr(stmt.index)
                elif isinstance(stmt, IfNode):
                    _count_expr(stmt.cond)
                    _scan_body(stmt.then_body)
                    _scan_body(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    _count_expr(stmt.expr)
                    for _, cb in stmt.cases:
                        _scan_body(cb)
                    _scan_body(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _scan_body(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _count_expr(stmt.cond)
                    _scan_body(stmt.then_body)
                    _scan_body(stmt.else_body)
                elif isinstance(stmt, SubmoduleInst):
                    for expr in stmt.port_map.values():
                        if isinstance(expr, Expr):
                            _count_expr(expr)
                    for expr in stmt.params.values():
                        if isinstance(expr, Expr):
                            _count_expr(expr)
                elif isinstance(stmt, MemWrite):
                    _count_expr(stmt.addr)
                    _count_expr(stmt.value)
                elif isinstance(stmt, ArrayWrite):
                    _count_expr(stmt.index)
                    _count_expr(stmt.value)

        for body in self.module._comb_blocks:
            _scan_body(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan_body(body)
        for stmt in self.module._top_level:
            _scan_body([stmt])
        return fanout

    def _find_dead_signals(self) -> List[str]:
        """找出声明了但从未被驱动或读取的信号。"""
        all_signals = set(self.module._inputs.keys()) | set(self.module._outputs.keys()) | \
                      set(self.module._wires.keys()) | set(self.module._regs.keys())
        referenced = set(self._fanout_analysis().keys())
        driven = set()

        def _scan(body: List[Any]):
            for stmt in body:
                if isinstance(stmt, Assign):
                    driven.add(self._assign_target_name(stmt))
                elif isinstance(stmt, IndexedAssign):
                    driven.add(stmt.target_signal.name)
                elif isinstance(stmt, IfNode):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, cb in stmt.cases:
                        _scan(cb)
                    _scan(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _scan(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, (MemWrite, ArrayWrite)):
                    driven.add(stmt.mem_name if hasattr(stmt, "mem_name") else stmt.array_name)

        for body in self.module._comb_blocks:
            _scan(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan(body)
        for stmt in self.module._top_level:
            _scan([stmt])

        # 输入信号天然被外部驱动，输出信号必须被内部驱动
        dead = []
        for s in self.module._wires:
            if s not in referenced and s not in driven:
                dead.append(s)
        for s in self.module._regs:
            if s not in driven:
                dead.append(s)
        return dead

    def _submodule_summary(self) -> Dict[str, Dict[str, Any]]:
        """递归分析子模块的 PPA（仅一层）。"""
        summary: Dict[str, Dict[str, Any]] = {}
        visited: Set[str] = set()

        def _add_sub(name: str, submod: Module):
            if name in visited:
                return
            visited.add(name)
            sub_ppa = PPAAnalyzer(submod)
            summary[name] = {
                "gate_count": sub_ppa._estimate_gate_count(),
                "reg_bits": sub_ppa._count_reg_bits(),
                "dead_signals": len(sub_ppa._find_dead_signals()),
            }

        for inst_name, submod in self.module._submodules:
            _add_sub(inst_name, submod)

        def _scan_for_inst(body: List[Any]):
            for stmt in body:
                if isinstance(stmt, SubmoduleInst):
                    _add_sub(stmt.name, stmt.module)
                elif isinstance(stmt, IfNode):
                    _scan_for_inst(stmt.then_body)
                    _scan_for_inst(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, cb in stmt.cases:
                        _scan_for_inst(cb)
                    _scan_for_inst(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _scan_for_inst(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _scan_for_inst(stmt.then_body)
                    _scan_for_inst(stmt.else_body)

        for stmt in self.module._top_level:
            _scan_for_inst([stmt])
        for body in self.module._comb_blocks:
            _scan_for_inst(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan_for_inst(body)
        return summary

    # =====================================================================
    # Dynamic Helpers
    # =====================================================================
    def _compute_toggle_rates(
        self, sim: Simulator, n_cycles: Optional[int] = None
    ) -> Dict[str, float]:
        trace = sim.trace
        if not trace:
            return {}
        if n_cycles is not None and len(trace) > n_cycles:
            trace = trace[-n_cycles:]
        if len(trace) < 2:
            return {}

        signals = [k for k in trace[0].keys() if k != "time"]
        toggles: Dict[str, float] = {}
        for sig in signals:
            flips = 0
            for i in range(1, len(trace)):
                if trace[i].get(sig) != trace[i - 1].get(sig):
                    flips += 1
            toggles[sig] = flips / (len(trace) - 1)
        return toggles

    def _identify_power_hotspots(
        self, sim: Simulator, n_cycles: Optional[int] = None, threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        toggles = self._compute_toggle_rates(sim, n_cycles)
        hotspots = []
        for sig, rate in toggles.items():
            if rate >= threshold:
                width = self._signal_width(sig)
                hotspots.append({"signal": sig, "toggle_rate": rate, "width": width})
        hotspots.sort(key=lambda x: x["toggle_rate"], reverse=True)
        return hotspots

    def _signal_width(self, name: str) -> int:
        for d in (self.module._inputs, self.module._outputs, self.module._wires, self.module._regs):
            if name in d:
                return d[name].width
        return 1

    # =====================================================================
    # Technology-Node-Aware Analysis
    # =====================================================================

    def _tech_node_analysis(self) -> Dict[str, Any]:
        """Process node-aware PPA estimation using the tech library.

        Returns timing, area, and power estimates mapped to a specific
        process node (e.g., 28nm, 7nm).
        """
        if self._tech_node is None:
            return {}

        static = self.analyze_static()
        depths = static.get("logic_depth", {})
        max_depth = max(depths.values()) if depths else 0
        gate_count = static.get("gate_count", 0)

        # Estimate RTL constructs from module structure
        rtl_constructs = self._extract_rtl_constructs()
        widths = self._extract_bit_widths()

        # Area estimate
        area_est = self._tech_node.estimate_area_from_rtl(rtl_constructs, widths)

        # Power estimate (with rough cell count from gate_count)
        power_est = self._tech_node.estimate_power({"nand2": int(gate_count)})

        # Logic depth estimate
        critical_path_constructs = self._estimate_critical_path_constructs()
        logic_depth = self._tech_node.estimate_logic_depth(critical_path_constructs, widths)

        # Pipeline recommendation at various frequencies
        pipeline_recs = {}
        for freq in [0.5, 1.0, 2.0, 3.0]:
            stages = self._tech_node.recommend_pipeline(logic_depth, freq)
            pipeline_recs[f"{freq}GHz"] = stages

        # Timing check at default target
        target_freq_ghz = 1.0
        timing_check = self._tech_node.check_critical_path(
            logic_depth * self._tech_node.gate_delay("nand2"),
            target_freq_ghz,
        )

        return {
            "node": self._tech_node.name,
            "min_feature_nm": self._tech_node.min_feature_nm,
            "estimated_area_um2": area_est.total_area_um2,
            "estimated_area_mm2": area_est.die_area_mm2,
            "estimated_power_mw": power_est.total_mw,
            "estimated_dynamic_mw": power_est.dynamic_mw,
            "estimated_leakage_mw": power_est.leakage_mw,
            "estimated_logic_depth": logic_depth,
            "max_depth_at_1ghz": self._tech_node.max_logic_depth(1.0),
            "critical_path_slack_ps": timing_check[1],
            "critical_path_meets_timing": timing_check[0],
            "pipeline_recommendations": pipeline_recs,
            "rtl_constructs": rtl_constructs,
        }

    def set_tech_node(self, node_name: str):
        """Set or change the process node for analysis."""
        self._tech_node = TechNode(node_name)

    def _extract_rtl_constructs(self) -> Dict[str, int]:
        """Extract RTL construct counts from module AST."""
        counts: Dict[str, int] = {}

        def _scan(body):
            for stmt in body:
                if isinstance(stmt, Assign):
                    self._classify_expr(stmt.value, counts)
                elif isinstance(stmt, IfNode):
                    counts["mux2"] = counts.get("mux2", 0) + 1
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    n = len(stmt.cases)
                    if n <= 4:
                        counts["mux4"] = counts.get("mux4", 0) + 1
                    elif n <= 8:
                        counts["mux_tree_8"] = counts.get("mux_tree_8", 0) + 1
                    else:
                        counts["mux_tree_16"] = counts.get("mux_tree_16", 0) + 1
                    for _, cb in stmt.cases:
                        _scan(cb)
                    _scan(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _scan(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SubmoduleInst):
                    for pname in stmt.port_map:
                        if "priority" in pname.lower():
                            counts["priority_enc"] = counts.get("priority_enc", 0) + 1

        for body in self.module._comb_blocks:
            _scan(body)
        for _, _, _, _, body in self.module._seq_blocks:
            _scan(body)
        for stmt in self.module._top_level:
            _scan([stmt])

        # Count registers as "counter" constructs
        reg_count = len(self.module._regs)
        if reg_count > 0:
            counts["counter"] = counts.get("counter", 0) + reg_count

        return counts

    def _extract_bit_widths(self) -> Dict[str, int]:
        """Extract representative bit widths for RTL constructs."""
        widths: Dict[str, int] = {}
        # Use average width of all signals as a rough estimate
        all_widths = [s.width for s in self.module._inputs.values()]
        all_widths += [s.width for s in self.module._outputs.values()]
        all_widths += [s.width for s in self.module._wires.values()]
        all_widths += [s.width for s in self.module._regs.values()]
        if all_widths:
            avg_w = sum(all_widths) // len(all_widths)
            max_w = max(all_widths)
            widths["add"] = max_w
            widths["mul"] = max_w
            widths["mux2"] = max_w
            widths["mux4"] = max_w
        return widths

    def _estimate_critical_path_constructs(self) -> List[str]:
        """Estimate the RTL constructs in the critical path.

        Uses the _critical_path_depth analysis to identify the longest
        signal chain and maps it to RTL constructs.
        """
        depths = self._critical_path_depth()
        if not depths:
            return ["add"]  # default: single adder

        # Find the deepest path
        deepest_sig = max(depths, key=depths.get)
        depth = depths[deepest_sig]

        # Map depth to estimated construct chain
        constructs: List[str] = []
        remaining = depth
        # Simplified: assume worst-case chain of arithmetic + logic
        if remaining > 10:
            constructs.append("mul")
            remaining -= 12
        if remaining > 6:
            constructs.append("add")
            remaining -= 4
        if remaining > 4:
            constructs.append("mux4")
            remaining -= 2
        if remaining > 2:
            constructs.append("mux2")
            remaining -= 1
        if remaining > 0:
            constructs.append("and")

        return constructs if constructs else ["and"]

    def _classify_expr(self, expr: Any, counts: Dict[str, int]):
        """Classify an expression into RTL construct types."""
        from rtlgen.core import BinOp, UnaryOp, Mux, Slice

        if isinstance(expr, BinOp):
            op_map = {
                "+": "add", "-": "sub",
                "*": "mul", "/": "div", "%": "div",
                "&": "and", "|": "or", "^": "xor",
                "<<": "shift_left", ">>": "shift_right",
                "==": "eq", "!=": "ne",
                "<": "lt", "<=": "lte",
                ">": "gt", ">=": "gte",
            }
            construct = op_map.get(expr.op, "and")
            counts[construct] = counts.get(construct, 0) + 1
            self._classify_expr(expr.lhs, counts)
            self._classify_expr(expr.rhs, counts)
        elif isinstance(expr, UnaryOp):
            if expr.op == "~":
                counts["not"] = counts.get("not", 0) + 1
        elif isinstance(expr, Mux):
            counts["mux2"] = counts.get("mux2", 0) + 1
            self._classify_expr(expr.true_expr, counts)
            self._classify_expr(expr.false_expr, counts)
        elif isinstance(expr, Slice):
            self._classify_expr(expr.operand, counts)

    @staticmethod
    def _expr_to_str(expr: Any) -> str:
        if isinstance(expr, Const):
            return str(expr.value)
        if isinstance(expr, Ref):
            return expr.signal.name
        return "?"

    def _assign_target_name(self, stmt: Assign) -> str:
        """Return a string key for an Assign target (handles Signal, Slice, etc.)."""
        target = stmt.target
        if hasattr(target, 'name'):
            return target.name
        if isinstance(target, Slice):
            operand = target.operand
            if hasattr(operand, 'name'):
                return f"{operand.name}[{target.hi}:{target.lo}]"
            if isinstance(operand, Ref):
                return f"{operand.signal.name}[{target.hi}:{target.lo}]"
            return self._expr_to_str(operand)
        return self._expr_to_str(target)

    def _collect_ref_names(self, expr: Any) -> Set[str]:
        """从表达式中提取所有信号名（Ref 和直接 Signal 引用）。"""
        names: Set[str] = set()
        if isinstance(expr, Ref):
            names.add(expr.signal.name)
        elif isinstance(expr, Signal):
            # Direct signal reference (e.g. in BinOp lhs/rhs)
            names.add(expr.name)
        elif isinstance(expr, BinOp):
            names |= self._collect_ref_names(expr.lhs)
            names |= self._collect_ref_names(expr.rhs)
        elif isinstance(expr, UnaryOp):
            names |= self._collect_ref_names(expr.operand)
        elif isinstance(expr, Mux):
            names |= self._collect_ref_names(expr.cond)
            names |= self._collect_ref_names(expr.true_expr)
            names |= self._collect_ref_names(expr.false_expr)
        elif isinstance(expr, Slice):
            names |= self._collect_ref_names(expr.operand)
        elif isinstance(expr, BitSelect):
            names |= self._collect_ref_names(expr.operand)
            names |= self._collect_ref_names(expr.index)
        elif isinstance(expr, Concat):
            for op in expr.operands:
                names |= self._collect_ref_names(op)
        elif isinstance(expr, MemRead):
            names |= self._collect_ref_names(expr.addr)
        elif isinstance(expr, ArrayRead):
            names |= self._collect_ref_names(expr.index)
        return names


# =====================================================================
# PPA-aware component helpers
# =====================================================================

class PPAAwareComponent:
    """PPA 感知组件 Mixin — 为硬件模块提供静态 PPA 估算属性。

    子类应实现 ``_ppa_key()`` 返回数据库查询键。
    """

    PPA_DATABASE: Dict[str, Dict[str, int]] = {
        "FixedPriorityArbiter_4": {"gates": 12, "depth": 2, "ff": 0},
        "RoundRobinArbiter_4": {"gates": 30, "depth": 4, "ff": 4},
        "SyncFIFO_ptr_4x32": {"gates": 150, "depth": 3, "ff": 134},
        "SyncFIFO_ctr_4x32": {"gates": 180, "depth": 4, "ff": 138},
        "SpillRegister_256": {"gates": 520, "depth": 0, "ff": 514},
        "ValidPipe_256": {"gates": 260, "depth": 2, "ff": 258},
    }

    def _ppa_key(self) -> str:
        """返回 PPA 数据库查询键。子类应覆盖此方法。"""
        return self.__class__.__name__

    @property
    def estimated_gates(self) -> int:
        return self.PPA_DATABASE.get(self._ppa_key(), {}).get("gates", 0)

    @property
    def estimated_depth(self) -> int:
        return self.PPA_DATABASE.get(self._ppa_key(), {}).get("depth", 0)

    @property
    def estimated_ff(self) -> int:
        return self.PPA_DATABASE.get(self._ppa_key(), {}).get("ff", 0)

    def satisfies(self, budget: Dict[str, int]) -> bool:
        if "max_gates" in budget and self.estimated_gates > budget["max_gates"]:
            return False
        if "max_depth" in budget and self.estimated_depth > budget["max_depth"]:
            return False
        if "max_ff" in budget and self.estimated_ff > budget["max_ff"]:
            return False
        return True

    def report(self) -> str:
        return (f"{self._ppa_key()}: gates={self.estimated_gates}, "
                f"depth={self.estimated_depth}, ff={self.estimated_ff}")


class OptimizationAdvisor:
    """为 Agent 提供优化建议的静态顾问。"""

    ADVICE = {
        "arbiter_4port": {
            "area": "Use FixedPriorityArbiter (12 gates) instead of RoundRobin (30 gates)",
            "latency": "Both are 1-cycle combinational",
            "power": "FixedPriority has lower toggle rate (fewer gates switching)",
        },
        "fifo_depth_4": {
            "area": "Pointer-based (6 FF) saves 1 FF vs counter-based (7 FF)",
            "latency": "Both 1-cycle read",
            "power": "Pointer-based has fewer toggles (no counter increment)",
        },
        "pipeline_cut": {
            "area": "ValidPipe (256 FF) is smaller than SpillRegister (514 FF)",
            "latency": "ValidPipe has 2-level comb path, SpillRegister has 0",
            "power": "ValidPipe has lower power (fewer FF)",
            "timing": "SpillRegister completely cuts comb path — use for critical paths",
        },
    }

    @classmethod
    def advise(cls, component_type: str, intent: str = "balanced") -> str:
        key = component_type
        if key in cls.ADVICE:
            return cls.ADVICE[key].get(intent, cls.ADVICE[key].get("balanced", ""))
        return "No specific advice available"

    @classmethod
    def suggest_for_module(cls, module: Module) -> List[str]:
        """为给定模块生成一系列优化建议。"""
        from rtlgen.ppa import PPAAnalyzer
        analyzer = PPAAnalyzer(module)
        static = analyzer.analyze_static()
        return analyzer.suggest_optimizations(static)


class DesignRuleChecker:
    """DSL 层设计规则检查器 — 在生成 Verilog 之前发现设计问题。"""

    RULES = {
        "unregistered_output": "所有数据输出应该被寄存器驱动",
        "ready_combinational": "ready 信号应该是组合逻辑",
        "valid_registered": "valid 信号应该在数据之前注册",
        "no_comb_loop": "组合逻辑中不允许自引用（除了特定模式）",
        "credit_no_starvation": "credit counter 不应下溢",
    }

    @classmethod
    def check(cls, module: Module) -> List[str]:
        """检查模块的设计规则，返回违例描述列表。"""
        violations: List[str] = []
        violations.extend(module.lint())
        return violations
