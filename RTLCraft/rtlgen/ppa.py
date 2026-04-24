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
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
)
from rtlgen.sim import Simulator

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

    def __init__(self, module: Module):
        self.module = module

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
                    drivers[stmt.target.name] = (stmt.value, select_extra)
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
        for _, _, _, _, body in self.module._seq_blocks:
            _collect(body)
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
            d = self._expr_depth(expr) + select_extra
            for ref_name in self._collect_ref_names(expr):
                if ref_name != name:
                    d = max(d, _depth(ref_name) + select_extra)
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
                    # If 语句本身引入一个 Mux 面积（cond width=1）
                    total += replication * _AREA_WEIGHTS.get("Mux", 3.0) * stmt.cond.width
                    _scan_body(stmt.then_body, replication)
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
                    driven.add(stmt.target.name)
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
                    driven.add(stmt.target.name)
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

    @staticmethod
    def _expr_to_str(expr: Any) -> str:
        if isinstance(expr, Const):
            return str(expr.value)
        if isinstance(expr, Ref):
            return expr.signal.name
        return "?"

    def _collect_ref_names(self, expr: Any) -> Set[str]:
        """从表达式中提取所有 Ref 信号名。"""
        names: Set[str] = set()
        if isinstance(expr, Ref):
            names.add(expr.signal.name)
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
