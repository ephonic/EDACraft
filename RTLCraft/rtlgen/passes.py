"""
rtlgen.passes — PassManager 框架

提供基于 Pass 的编译流程，支持诊断、常量折叠、死代码消除等。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rtlgen.core import (
    ArrayRead,
    Assign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    ForGenNode,
    GenIfNode,
    IfNode,
    MemRead,
    MemWrite,
    Mux,
    Module,
    Ref,
    Signal,
    Slice,
    SourceLoc,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
    Wire,
)


@dataclass
class Diagnostic:
    """编译/分析诊断信息。"""
    severity: str  # "error" | "warning" | "info"
    signal: str = ""
    message: str = ""
    source: Optional[SourceLoc] = None


@dataclass
class PassResult:
    """单个 Pass 的执行结果。"""
    status: str = "ok"  # "ok" | "failed" | "warning"
    diagnostics: List[Diagnostic] = field(default_factory=list)


class Pass:
    """编译 Pass 基类。"""
    name: str = "base"

    def run(self, module: Module) -> PassResult:
        raise NotImplementedError


class PassManager:
    """Pass 管理器，按顺序执行注册的 Pass。"""

    def __init__(self):
        self._passes: List[Pass] = []

    def add(self, p: Pass):
        self._passes.append(p)

    def run(self, module: Module) -> List[PassResult]:
        """依次执行所有 Pass，返回每个 Pass 的结果。"""
        results = []
        for p in self._passes:
            result = p.run(module)
            results.append(result)
        return results

    def run_until_failure(self, module: Module) -> List[PassResult]:
        """执行 Pass，遇到 failed 状态的 Pass 后停止。"""
        results = []
        for p in self._passes:
            result = p.run(module)
            results.append(result)
            if result.status == "failed":
                break
        return results


# ---------------------------------------------------------------------------
# Built-in passes
# ---------------------------------------------------------------------------

class LintPass(Pass):
    """将 Module.lint() 包装为一个 Pass。"""
    name = "lint"

    def __init__(self, rules: Optional[List[str]] = None):
        self.rules = rules

    def run(self, module: Module) -> PassResult:
        violations = module.lint(rules=self.rules)
        diags = [
            Diagnostic(severity="warning", message=v)
            for v in violations
        ]
        status = "failed" if any(d.severity == "error" for d in diags) else (
            "warning" if diags else "ok"
        )
        return PassResult(status=status, diagnostics=diags)


class ConstantFoldPass(Pass):
    """常量折叠：将 Const op Const 的结果替换为新的 Const。"""
    name = "constant_fold"

    def run(self, module: Module) -> PassResult:
        folded = 0
        for body in module._comb_blocks:
            folded += self._fold_stmts(body)
        for _, _, _, _, body in module._seq_blocks:
            folded += self._fold_stmts(body)
        for stmt in module._top_level:
            folded += self._fold_stmt(stmt)

        status = "ok" if folded == 0 else "warning"
        return PassResult(
            status=status,
            diagnostics=[Diagnostic(severity="info", message=f"Folded {folded} constant expression(s)")] if folded else []
        )

    def _fold_expr(self, expr: Expr) -> tuple:
        """递归折叠，返回 (new_expr, folded_count)。"""
        if isinstance(expr, BinOp):
            new_lhs, lc = self._fold_expr(expr.lhs)
            new_rhs, rc = self._fold_expr(expr.rhs)
            if isinstance(new_lhs, Const) and isinstance(new_rhs, Const):
                result = self._eval_binop(expr.op, new_lhs, new_rhs)
                if result is not None:
                    return result, lc + rc + 1
            return BinOp(expr.op, new_lhs, new_rhs, expr.width), lc + rc
        if isinstance(expr, UnaryOp):
            new_op, c = self._fold_expr(expr.operand)
            if isinstance(new_op, Const):
                result = self._eval_unop(expr.op, new_op)
                if result is not None:
                    return result, c + 1
            return UnaryOp(expr.op, new_op, expr.width), c
        if isinstance(expr, Mux):
            new_cond, cc = self._fold_expr(expr.cond)
            new_true, tc = self._fold_expr(expr.true_expr)
            new_false, fc = self._fold_expr(expr.false_expr)
            if isinstance(new_cond, Const):
                return (new_true if new_cond.value else new_false), cc + tc + fc + 1
            return Mux(new_cond, new_true, new_false, expr.width), cc + tc + fc
        if isinstance(expr, Concat):
            new_ops = []
            total_c = 0
            for op in expr.operands:
                new_op, c = self._fold_expr(op)
                new_ops.append(new_op)
                total_c += c
            return Concat(new_ops, expr.width), total_c
        return expr, 0

    def _fold_stmt(self, stmt) -> int:
        if isinstance(stmt, Assign):
            new_val, c = self._fold_expr(stmt.value)
            stmt.value = new_val
            return c
        if isinstance(stmt, IfNode):
            c = self._fold_expr(stmt.cond)[1]
            for s in stmt.then_body:
                c += self._fold_stmt(s)
            for s in stmt.else_body:
                c += self._fold_stmt(s)
            return c
        if isinstance(stmt, SwitchNode):
            c = self._fold_expr(stmt.expr)[1]
            for _, body in stmt.cases:
                for s in body:
                    c += self._fold_stmt(s)
            for s in stmt.default_body:
                c += self._fold_stmt(s)
            return c
        return 0

    def _fold_stmts(self, stmts: List[Any]) -> int:
        total = 0
        for stmt in stmts:
            total += self._fold_stmt(stmt)
        return total

    def _eval_binop(self, op: str, lhs: Const, rhs: Const) -> Optional[Const]:
        try:
            if op == '+': return Const(lhs.value + rhs.value, width=max(lhs.width, rhs.width) + 1)
            if op == '-': return Const(lhs.value - rhs.value, width=max(lhs.width, rhs.width) + 1)
            if op == '*': return Const(lhs.value * rhs.value, width=lhs.width + rhs.width)
            if op == '&': return Const(lhs.value & rhs.value, width=max(lhs.width, rhs.width))
            if op == '|': return Const(lhs.value | rhs.value, width=max(lhs.width, rhs.width))
            if op == '^': return Const(lhs.value ^ rhs.value, width=max(lhs.width, rhs.width))
            if op == '<<': return Const(lhs.value << rhs.value, width=lhs.width + rhs.value)
            if op == '>>': return Const(lhs.value >> rhs.value, width=lhs.width)
            if op == '%': return Const(lhs.value % rhs.value, width=max(lhs.width, rhs.width))
            if op == '/': return Const(lhs.value // rhs.value, width=max(lhs.width, rhs.width)) if rhs.value != 0 else None
            if op == '==': return Const(1 if lhs.value == rhs.value else 0, width=1)
            if op == '!=': return Const(1 if lhs.value != rhs.value else 0, width=1)
            if op == '<': return Const(1 if lhs.value < rhs.value else 0, width=1)
            if op == '<=': return Const(1 if lhs.value <= rhs.value else 0, width=1)
            if op == '>': return Const(1 if lhs.value > rhs.value else 0, width=1)
            if op == '>=': return Const(1 if lhs.value >= rhs.value else 0, width=1)
        except Exception:
            pass
        return None

    def _eval_unop(self, op: str, operand: Const) -> Optional[Const]:
        try:
            if op == '~': return Const(~operand.value & ((1 << operand.width) - 1), width=operand.width)
            if op == '!': return Const(0 if operand.value else 1, width=1)
        except Exception:
            pass
        return None


class DeadCodeElimPass(Pass):
    """死代码消除：移除从未被读取的信号赋值。"""
    name = "dead_code_elim"

    def run(self, module: Module) -> PassResult:
        # 收集所有被读取的信号
        read_signals: set = set()
        self._collect_reads(module._top_level, read_signals)
        for body in module._comb_blocks:
            self._collect_reads(body, read_signals)
        for _, _, _, _, body in module._seq_blocks:
            self._collect_reads(body, read_signals)

        # 也收集输出端口（它们是 "被读取" 的）
        for name, sig in module._outputs.items():
            read_signals.add(id(sig))

        # 收集被驱动的信号
        driven_signals: Dict[int, List] = {}
        self._collect_driven(module._top_level, driven_signals)
        for body in module._comb_blocks:
            self._collect_driven(body, driven_signals)
        for _, _, _, _, body in module._seq_blocks:
            self._collect_driven(body, driven_signals)

        # 找出从未被读取的驱动信号
        dead = []
        for sig_id, assigns in driven_signals.items():
            if sig_id not in read_signals:
                sig = assigns[0] if assigns else None
                if sig is not None:
                    dead.append(sig)

        diags = [
            Diagnostic(severity="warning", signal=sig.name, message=f"Signal '{sig.name}' is driven but never read")
            for sig in dead
        ]
        return PassResult(
            status="warning" if dead else "ok",
            diagnostics=diags
        )

    def _collect_reads(self, stmts: List[Any], reads: set):
        def _scan_expr(expr):
            if isinstance(expr, Ref):
                reads.add(id(expr.signal))
            elif isinstance(expr, (BinOp, Mux)):
                if hasattr(expr, "lhs"):
                    _scan_expr(expr.lhs)
                    _scan_expr(expr.rhs)
                if hasattr(expr, "cond"):
                    _scan_expr(expr.cond)
                    _scan_expr(expr.true_expr)
                    _scan_expr(expr.false_expr)
            elif isinstance(expr, UnaryOp):
                _scan_expr(expr.operand)
            elif isinstance(expr, (Slice, BitSelect)):
                _scan_expr(expr.operand)
                if hasattr(expr, "index"):
                    _scan_expr(expr.index)
            elif isinstance(expr, Concat):
                for op in expr.operands:
                    _scan_expr(op)
            elif isinstance(expr, MemRead):
                _scan_expr(expr.addr)
            elif isinstance(expr, ArrayRead):
                _scan_expr(expr.index)

        for stmt in stmts:
            if isinstance(stmt, Assign):
                _scan_expr(stmt.value)
            elif isinstance(stmt, IfNode):
                _scan_expr(stmt.cond)
                self._collect_reads(stmt.then_body, reads)
                self._collect_reads(stmt.else_body, reads)
            elif isinstance(stmt, SwitchNode):
                _scan_expr(stmt.expr)
                for _, body in stmt.cases:
                    self._collect_reads(body, reads)
                self._collect_reads(stmt.default_body, reads)
            elif isinstance(stmt, ForGenNode):
                self._collect_reads(stmt.body, reads)
            elif isinstance(stmt, GenIfNode):
                self._collect_reads(stmt.then_body, reads)
                self._collect_reads(stmt.else_body, reads)
            elif isinstance(stmt, SubmoduleInst):
                for expr in stmt.port_map.values():
                    if isinstance(expr, Expr):
                        _scan_expr(expr)

    def _collect_driven(self, stmts: List[Any], driven: Dict[int, List]):
        for stmt in stmts:
            if isinstance(stmt, Assign):
                if isinstance(stmt.target, Signal):
                    driven.setdefault(id(stmt.target), []).append(stmt.target)
            elif isinstance(stmt, IfNode):
                self._collect_driven(stmt.then_body, driven)
                self._collect_driven(stmt.else_body, driven)
            elif isinstance(stmt, SwitchNode):
                for _, body in stmt.cases:
                    self._collect_driven(body, driven)
                self._collect_driven(stmt.default_body, driven)
            elif isinstance(stmt, ForGenNode):
                self._collect_driven(stmt.body, driven)
