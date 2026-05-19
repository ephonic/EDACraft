"""
rtlgen.smt — SAT/SMT 形式化验证支持

将 DSL AST 转换为 Z3 位向量表达式，支持组合等价性检查（CEC）
和有界模型检测（BMC）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from rtlgen.core import (
    ArrayRead,
    Assign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    IfNode,
    MemRead,
    Module,
    Mux,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SwitchNode,
    UnaryOp,
)

# ---------------------------------------------------------------------------
# Lazy import Z3 — fail gracefully if not installed
# ---------------------------------------------------------------------------
try:
    from z3 import (
        BitVec,
        BitVecRef,
        BitVecVal,
        BoolRef,
        Concat as Z3Concat,
        Extract,
        If as Z3If,
        LShR,
        Or,
        Solver,
        UDiv,
        UGE,
        UGT,
        ULE,
        ULT,
        URem,
        is_bv,
        unsat,
    )
    _Z3_AVAILABLE = True
except ImportError:
    _Z3_AVAILABLE = False


class SMTError(Exception):
    """SMT 转换或求解错误。"""


class SMTConverter:
    """将 DSL ``Expr`` 子树转换为 Z3 位向量表达式。

    同一个转换器实例会在内部做表达式缓存，避免重复构建相同的
    Z3 子表达式。
    """

    def __init__(self, prefix: str = ""):
        if not _Z3_AVAILABLE:
            raise SMTError("Z3 solver not installed. Run: pip install z3-solver")
        self.prefix = prefix
        self.vars: Dict[str, BitVecRef] = {}
        self._cache: Dict[int, BitVecRef] = {}

    # ------------------------------------------------------------------
    # Variable management
    # ------------------------------------------------------------------
    def _vname(self, name: str) -> str:
        return f"{self.prefix}{name}" if self.prefix else name

    def get_var(self, name: str, width: int) -> BitVecRef:
        """获取（或创建）名为 *name* 的 Z3 位向量变量。"""
        vn = self._vname(name)
        if vn not in self.vars:
            self.vars[vn] = BitVec(vn, width)
        return self.vars[vn]

    def add_constant(self, name: str, value: int, width: int) -> BitVecRef:
        """将某个信号固定为常量（常用于复位状态）。"""
        vn = self._vname(name)
        c = BitVecVal(value & ((1 << width) - 1), width)
        self.vars[vn] = c
        return c

    # ------------------------------------------------------------------
    # Expr -> Z3
    # ------------------------------------------------------------------
    def convert(self, expr: Expr) -> BitVecRef:
        """将 DSL 表达式转为 Z3 位向量表达式（带缓存）。"""
        eid = id(expr)
        if eid in self._cache:
            return self._cache[eid]
        z3_expr = self._convert_impl(expr)
        self._cache[eid] = z3_expr
        return z3_expr

    def _convert_impl(self, expr: Expr) -> BitVecRef:
        if isinstance(expr, Const):
            mask = (1 << expr.width) - 1 if expr.width < 64 else 0xFFFFFFFFFFFFFFFF
            return BitVecVal(expr.value & mask, expr.width)

        if isinstance(expr, Ref):
            return self.get_var(expr.signal.name, expr.signal.width)

        if isinstance(expr, BinOp):
            l = self.convert(expr.lhs)
            r = self.convert(expr.rhs)
            return self._binop(expr.op, l, r, expr.width)

        if isinstance(expr, UnaryOp):
            o = self.convert(expr.operand)
            if expr.op == "~":
                return ~o
            if expr.op == "-":
                return -o
            if expr.op == "!":
                return Z3If(o == 0, BitVecVal(1, expr.width), BitVecVal(0, expr.width))
            raise SMTError(f"Unsupported unary op: {expr.op}")

        if isinstance(expr, Slice):
            o = self.convert(expr.operand)
            return Extract(expr.hi, expr.lo, o)

        if isinstance(expr, PartSelect):
            o = self.convert(expr.operand)
            off = self.convert(expr.offset)
            if isinstance(expr.offset, Const):
                lo = expr.offset.value
                return Extract(lo + expr.width - 1, lo, o)
            # Variable offset: build ITE chain (unroll all possible offsets)
            # This is exponential in the address width, so we limit to small widths.
            if expr.offset.width > 6:
                raise SMTError(
                    f"Variable PartSelect offset too wide ({expr.offset.width} bits) "
                    "for SMT unrolling. Consider using BMC or structural equivalence."
                )
            total_width = expr.operand.width
            result = BitVecVal(0, expr.width)
            for candidate_lo in range(0, total_width - expr.width + 1):
                candidate = Extract(candidate_lo + expr.width - 1, candidate_lo, o)
                result = Z3If(off == candidate_lo, candidate, result)
            return result

        if isinstance(expr, BitSelect):
            o = self.convert(expr.operand)
            idx = self.convert(expr.index)
            if isinstance(expr.index, Const):
                b = expr.index.value
                return Extract(b, b, o)
            if expr.index.width > 6:
                raise SMTError(
                    f"Variable BitSelect index too wide ({expr.index.width} bits) "
                    "for SMT unrolling."
                )
            result = BitVecVal(0, 1)
            for candidate in range(expr.operand.width):
                bit = Extract(candidate, candidate, o)
                result = Z3If(idx == candidate, bit, result)
            return result

        if isinstance(expr, Concat):
            # Z3 Concat takes MSB-first arguments, but our operands list is
            # already in MSB-first order (logic.py Cat).
            ops = [self.convert(op) for op in expr.operands]
            return Z3Concat(*ops)

        if isinstance(expr, Mux):
            cond = self.convert(expr.cond)
            t = self.convert(expr.true_expr)
            f = self.convert(expr.false_expr)
            return Z3If(cond != 0, t, f)

        if isinstance(expr, MemRead):
            raise SMTError("MemRead not yet supported in SMT conversion")

        if isinstance(expr, ArrayRead):
            raise SMTError("ArrayRead not yet supported in SMT conversion")

        raise SMTError(f"Unsupported expression type: {type(expr).__name__}")

    # ------------------------------------------------------------------
    # Binary operators
    # ------------------------------------------------------------------
    def _binop(self, op: str, l: BitVecRef, r: BitVecRef, width: int) -> BitVecRef:
        # Align operand widths (zero-extend smaller operand)
        wl, wr = l.size(), r.size()
        if wl < wr:
            l = Z3Concat(BitVecVal(0, wr - wl), l)
        elif wr < wl:
            r = Z3Concat(BitVecVal(0, wl - wr), r)

        if op == "+":
            res = l + r
        elif op == "-":
            res = l - r
        elif op == "*":
            res = l * r
        elif op == "&":
            res = l & r
        elif op == "|":
            res = l | r
        elif op == "^":
            res = l ^ r
        elif op == "==":
            res = Z3If(l == r, BitVecVal(1, width), BitVecVal(0, width))
        elif op == "!=":
            res = Z3If(l != r, BitVecVal(1, width), BitVecVal(0, width))
        elif op == "<":
            res = Z3If(ULT(l, r), BitVecVal(1, width), BitVecVal(0, width))
        elif op == ">":
            res = Z3If(UGT(l, r), BitVecVal(1, width), BitVecVal(0, width))
        elif op == "<=":
            res = Z3If(ULE(l, r), BitVecVal(1, width), BitVecVal(0, width))
        elif op == ">=":
            res = Z3If(UGE(l, r), BitVecVal(1, width), BitVecVal(0, width))
        elif op == "<<":
            res = l << r
        elif op == ">>":
            res = LShR(l, r)
        elif op == "/":
            res = UDiv(l, r)
        elif op == "%":
            res = URem(l, r)
        else:
            raise SMTError(f"Unsupported binary operator: {op}")

        # Ensure result matches DSL-declared width (truncate or zero-extend)
        if res.size() > width:
            res = Extract(width - 1, 0, res)
        elif res.size() < width:
            res = Z3Concat(BitVecVal(0, width - res.size()), res)
        return res


# ---------------------------------------------------------------------------
# Driver extraction — compute symbolic expressions for every driven signal
# ---------------------------------------------------------------------------

class DriverExtractor:
    """从 Module AST 提取每个信号的**组合驱动表达式**。

    处理 ``@comb`` 块中的 ``Assign``、``IfNode``、``SwitchNode``，
    用 Z3 ``If``（ITE）合并多路径赋值。
    """

    def __init__(self, module: Module, prefix: str = ""):
        self.module = module
        self.conv = SMTConverter(prefix)
        self._partial: Dict[str, Dict[int, BitVecRef]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self) -> Dict[str, BitVecRef]:
        """提取所有由 ``@comb`` 驱动的信号。

        返回 ``{signal_name: z3_expr}``，其中 *z3_expr* 仅包含输入
        信号和内部 wire 的 Z3 变量。
        """
        drivers: Dict[str, BitVecRef] = {}
        self._partial = {}
        for block in self.module._comb_blocks:
            self._process_stmts(block, drivers)
        self._merge_partials(drivers)
        return drivers

    def extract_with_regs_as_inputs(self) -> Dict[str, BitVecRef]:
        """将 Reg 也视为输入，提取完整的组合驱动关系。

        这对于 CEC 很有用：把 Reg 的当前值当作输入变量，
        输出表达式自然包含 Reg 的影响。
        """
        # Register all Regs as Z3 variables
        for name, reg in self.module._regs.items():
            self.conv.get_var(name, reg.width)
        return self.extract()

    # ------------------------------------------------------------------
    # Statement processing
    # ------------------------------------------------------------------
    def _process_stmts(self, stmts: List[Any], drivers: Dict[str, BitVecRef]):
        for stmt in stmts:
            if isinstance(stmt, Assign):
                self._process_assign(stmt, drivers)

            elif isinstance(stmt, IfNode):
                then_drv = dict(drivers)
                else_drv = dict(drivers)
                then_part = dict(self._partial)
                else_part = dict(self._partial)
                self._process_stmts(stmt.then_body, then_drv)
                self._partial, saved = then_part, self._partial
                self._process_stmts(stmt.else_body, else_drv)
                self._partial = self._merge_partial_ite(saved, self._partial, stmt.cond)
                self._merge_ite(drivers, then_drv, else_drv, stmt.cond)

            elif isinstance(stmt, SwitchNode):
                # Collect driver maps for each case + default
                all_cases = []
                all_partials = []
                for case_expr, case_body in stmt.cases:
                    case_drv = dict(drivers)
                    case_part = dict(self._partial)
                    self._process_stmts(case_body, case_drv)
                    all_cases.append((case_expr, case_drv))
                    all_partials.append(self._partial)
                    self._partial = case_part
                default_drv = dict(drivers)
                default_part = dict(self._partial)
                self._process_stmts(stmt.default_body, default_drv)
                all_partials.append(self._partial)
                self._partial = self._merge_partial_switch(all_partials, stmt.expr)
                self._merge_switch(drivers, all_cases, default_drv, stmt.expr)

    def _process_assign(self, stmt: Assign, drivers: Dict[str, BitVecRef]):
        target = stmt.target
        if isinstance(target, BitSelect):
            base_name = self._base_signal_name(target.operand)
            if base_name:
                idx_expr = target.index
                if isinstance(idx_expr, Const):
                    bit = idx_expr.value
                    val = self.conv.convert(stmt.value) & 1
                    self._partial.setdefault(base_name, {})[bit] = val
                    # Also invalidate any full-signal driver since partial assignments
                    # take precedence over full-signal assignments in most tools.
                    if base_name in drivers:
                        del drivers[base_name]
                else:
                    # Variable index: fall back to whole-signal assignment
                    tname = base_name
                    drivers[tname] = self.conv.convert(stmt.value)
            return

        if isinstance(target, (Slice, PartSelect)):
            # Conservative: treat as whole-signal assignment
            tname = self._base_signal_name(target.operand)
            if tname and tname in self._partial:
                del self._partial[tname]
            if tname:
                drivers[tname] = self.conv.convert(stmt.value)
            return

        tname = self._target_name(target)
        if tname:
            # Full-signal assignment clears any partial assignments
            if tname in self._partial:
                del self._partial[tname]
            drivers[tname] = self.conv.convert(stmt.value)

    def _merge_partials(self, drivers: Dict[str, BitVecRef]):
        """将累积的 bit-level partial assignments 组合成完整信号。"""
        for name, bits in self._partial.items():
            sig = self.module._wires.get(name) or self.module._regs.get(name)
            if sig is None:
                continue
            width = sig.width
            # Build each bit; missing bits use the current register/wire value
            bit_exprs = []
            for i in range(width):
                if i in bits:
                    bit_exprs.append(bits[i])
                else:
                    bit_exprs.append(Extract(i, i, self.conv.get_var(name, width)))
            # Concatenate MSB -> LSB; Z3Concat takes MSB-first arguments
            drivers[name] = Z3Concat(*reversed(bit_exprs))

    def _merge_partial_ite(self, then_part: Dict[str, Dict[int, BitVecRef]],
                           else_part: Dict[str, Dict[int, BitVecRef]],
                           cond_expr: Expr) -> Dict[str, Dict[int, BitVecRef]]:
        cond = self.conv.convert(cond_expr)
        merged: Dict[str, Dict[int, BitVecRef]] = {}
        all_names = set(then_part.keys()) | set(else_part.keys())
        for name in all_names:
            tbits = then_part.get(name, {})
            ebits = else_part.get(name, {})
            mbits: Dict[int, BitVecRef] = {}
            for bit in set(tbits.keys()) | set(ebits.keys()):
                tv = tbits.get(bit)
                ev = ebits.get(bit)
                if tv is not None and ev is not None:
                    mbits[bit] = Z3If(cond != 0, tv, ev)
                elif tv is not None:
                    mbits[bit] = tv
                elif ev is not None:
                    mbits[bit] = ev
            merged[name] = mbits
        return merged

    def _merge_partial_switch(self, partials: List[Dict[str, Dict[int, BitVecRef]]],
                              switch_expr: Expr) -> Dict[str, Dict[int, BitVecRef]]:
        # partials corresponds to [case0, case1, ..., default]
        # We don't have case expressions here, so this is a simplified merge
        # that takes the union. Full ITE-merge would require case expressions.
        merged: Dict[str, Dict[int, BitVecRef]] = {}
        for p in partials:
            for name, bits in p.items():
                if name not in merged:
                    merged[name] = dict(bits)
                else:
                    for bit, expr in bits.items():
                        if bit not in merged[name]:
                            merged[name][bit] = expr
        return merged

    def _merge_ite(self, base: Dict[str, BitVecRef],
                   then_drv: Dict[str, BitVecRef],
                   else_drv: Dict[str, BitVecRef],
                   cond_expr: Expr):
        """将 then/else 两个分支的驱动映射用 ITE 合并回 base。"""
        cond = self.conv.convert(cond_expr)
        changed_keys = set(then_drv.keys()) | set(else_drv.keys())
        for k in changed_keys:
            t = then_drv.get(k)
            e = else_drv.get(k)
            b = base.get(k)
            # Choose the most specific non-None value
            # If both branches changed, build ITE
            if t is not None and e is not None:
                if t is b and e is b:
                    continue
                w = t.size()
                base[k] = Z3If(cond != 0, t, e)
            elif t is not None:
                base[k] = t
            elif e is not None:
                base[k] = e

    def _merge_switch(self, base: Dict[str, BitVecRef],
                      cases: List[Tuple[Expr, Dict[str, BitVecRef]]],
                      default_drv: Dict[str, BitVecRef],
                      switch_expr: Expr):
        """将 Switch 的多个 case 用嵌套 ITE 合并。"""
        sw = self.conv.convert(switch_expr)
        # Start from default, then layer each case on top
        merged = dict(default_drv)
        for case_expr, case_drv in reversed(cases):
            ce = self.conv.convert(case_expr)
            # Align widths for comparison
            sw_cmp, ce_cmp = sw, ce
            if sw_cmp.size() != ce_cmp.size():
                if sw_cmp.size() < ce_cmp.size():
                    sw_cmp = Z3Concat(BitVecVal(0, ce_cmp.size() - sw_cmp.size()), sw_cmp)
                else:
                    ce_cmp = Z3Concat(BitVecVal(0, sw_cmp.size() - ce_cmp.size()), ce_cmp)
            keys = set(case_drv.keys()) | set(merged.keys())
            new_merged: Dict[str, BitVecRef] = {}
            for k in keys:
                cv = case_drv.get(k)
                mv = merged.get(k)
                if cv is not None and mv is not None:
                    cv, mv = _align_widths(cv, mv)
                    new_merged[k] = Z3If(sw_cmp == ce_cmp, cv, mv)
                elif cv is not None:
                    new_merged[k] = cv
                elif mv is not None:
                    new_merged[k] = mv
            merged = new_merged
        base.update(merged)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _target_name(target) -> Optional[str]:
        if isinstance(target, Signal):
            return target.name
        if isinstance(target, (Slice, PartSelect, BitSelect)):
            return DriverExtractor._target_name(target.operand)
        return None

    @staticmethod
    def _base_signal_name(expr: Any) -> Optional[str]:
        from rtlgen.core import Ref, Slice, PartSelect, BitSelect
        if isinstance(expr, Ref):
            return expr.signal.name
        if isinstance(expr, (Slice, PartSelect, BitSelect)):
            return DriverExtractor._base_signal_name(expr.operand)
        return None


# ---------------------------------------------------------------------------
# Combinational Equivalence Checker (CEC)
# ---------------------------------------------------------------------------

def check_combinational_equivalence(
    module_a: Module,
    module_b: Module,
    outputs: Optional[Set[str]] = None,
    timeout_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """组合等价性检查（CEC）。

    将两个模块视为纯组合电路（忽略 ``@seq`` 块，Reg 视为输入），
    证明：在所有可能的输入组合下，两个模块的指定输出完全相同。

    Parameters
    ----------
    module_a, module_b
        待比较的两个 DSL 模块。
    outputs
        指定要比较的信号名集合。默认取两个模块共有的 output。
    timeout_ms
        Z3 求解器超时（毫秒）。

    Returns
    -------
    dict
        ::

            {
                "equivalent": bool,
                "method": "SMT_CEC",
                "outputs_checked": List[str],
                "counterexample": Optional[Dict[str, int]],
                "z3_time_ms": float,
                "solver_stats": str,
            }
    """
    if not _Z3_AVAILABLE:
        raise SMTError("Z3 not available. Install: pip install z3-solver")

    ext_a = DriverExtractor(module_a, prefix="a_")
    ext_b = DriverExtractor(module_b, prefix="b_")

    drv_a = ext_a.extract_with_regs_as_inputs()
    drv_b = ext_b.extract_with_regs_as_inputs()

    # Determine which outputs to compare
    if outputs is None:
        outputs = set(module_a._outputs.keys()) & set(module_b._outputs.keys())
    outputs = sorted(outputs)

    if not outputs:
        return {
            "equivalent": True,
            "method": "SMT_CEC",
            "outputs_checked": [],
            "counterexample": None,
            "reason": "No common outputs specified",
        }

    # Build miter
    solver = Solver()
    if timeout_ms is not None:
        solver.set("timeout", timeout_ms)

    # Constrain common inputs to be equal between the two modules.
    common_inputs = set(module_a._inputs.keys()) & set(module_b._inputs.keys())
    for iname in common_inputs:
        va = ext_a.conv.get_var(iname, module_a._inputs[iname].width)
        vb = ext_b.conv.get_var(iname, module_b._inputs[iname].width)
        solver.add(va == vb)

    # For self-referential wires (e.g. FixedPriorityArbiter's pre_req),
    # we must add constraints var == driver_expr so that Z3 knows the
    # wire is driven by comb logic, not a free input.
    # We also handle wires that are NOT explicitly registered in module._wires
    # (local wires created inside __init__ and only used in comb blocks).
    def _add_wire_constraints(drv, ext, module):
        for name, expr in drv.items():
            if name in module._inputs or name in module._outputs:
                continue
            width = None
            if name in module._wires:
                width = module._wires[name].width
            elif name in module._regs:
                width = module._regs[name].width
            else:
                # Infer width from expression
                width = expr.size()
            var = ext.conv.get_var(name, width)
            solver.add(var == expr)

    _add_wire_constraints(drv_a, ext_a, module_a)
    _add_wire_constraints(drv_b, ext_b, module_b)

    miter_terms: List[BoolRef] = []
    for oname in outputs:
        za = drv_a.get(oname)
        zb = drv_b.get(oname)
        if za is None or zb is None:
            continue
        # Truncate to declared output width (assignments may produce wider exprs)
        out_width_a = module_a._outputs[oname].width if oname in module_a._outputs else za.size()
        out_width_b = module_b._outputs[oname].width if oname in module_b._outputs else zb.size()
        if za.size() > out_width_a:
            za = Extract(out_width_a - 1, 0, za)
        if zb.size() > out_width_b:
            zb = Extract(out_width_b - 1, 0, zb)
        # Align widths
        za, zb = _align_widths(za, zb)
        miter_terms.append(za != zb)

    if not miter_terms:
        return {
            "equivalent": True,
            "method": "SMT_CEC",
            "outputs_checked": outputs,
            "counterexample": None,
            "reason": "No comparable output expressions found",
        }

    miter = Or(miter_terms) if len(miter_terms) > 1 else miter_terms[0]
    solver.add(miter)

    import time
    t0 = time.perf_counter()
    result = solver.check()
    t1 = time.perf_counter()

    if result == unsat:
        return {
            "equivalent": True,
            "method": "SMT_CEC",
            "outputs_checked": outputs,
            "counterexample": None,
            "z3_time_ms": (t1 - t0) * 1000,
            "solver_stats": str(solver.statistics()),
        }

    # SAT — extract counterexample
    model = solver.model()
    cex: Dict[str, int] = {}
    for decl in model.decls():
        val = model[decl]
        if hasattr(val, "as_long"):
            cex[str(decl)] = val.as_long()
        else:
            cex[str(decl)] = str(val)

    return {
        "equivalent": False,
        "method": "SMT_CEC",
        "outputs_checked": outputs,
        "counterexample": cex,
        "z3_time_ms": (t1 - t0) * 1000,
        "solver_stats": str(solver.statistics()),
    }


def _align_widths(a: BitVecRef, b: BitVecRef) -> Tuple[BitVecRef, BitVecRef]:
    """将两个位向量扩展到相同宽度（在 MSB 侧补零）。"""
    wa, wb = a.size(), b.size()
    if wa == wb:
        return a, b
    if wa < wb:
        return Z3Concat(BitVecVal(0, wb - wa), a), b
    return a, Z3Concat(BitVecVal(0, wa - wb), b)


# ---------------------------------------------------------------------------
# Bounded Model Checking (BMC) for sequential equivalence
# ---------------------------------------------------------------------------

def check_bounded_equivalence(
    module_a: Module,
    module_b: Module,
    bound: int = 5,
    outputs: Optional[Set[str]] = None,
    reset_state: Optional[Dict[str, Dict[str, int]]] = None,
    timeout_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """有界时序等价性检查（Bounded Model Checking）。

    将两个模块展开 ``bound`` 个周期，在每个周期施加相同的输入，
    检查两个模块的输出是否始终相同。假设两个模块从相同的初始
    复位状态开始（若未提供则默认所有 Reg 为 0）。

    Parameters
    ----------
    bound
        展开的周期数。
    reset_state
        形如 ``{"a_reg_name": 0, "b_reg_name": 1}`` 的初始状态字典。
        若未提供，所有 Reg 初始化为 0。
    """
    if not _Z3_AVAILABLE:
        raise SMTError("Z3 not available")

    if outputs is None:
        outputs = set(module_a._outputs.keys()) & set(module_b._outputs.keys())
    outputs = sorted(outputs)

    # TODO: full BMC requires extracting next-state functions from @seq blocks.
    # For now, we provide a clear error and a fallback to simulation-based BMC.
    return {
        "equivalent": None,
        "method": "BMC_not_implemented",
        "outputs_checked": outputs,
        "reason": (
            "Full BMC through Z3 for sequential modules requires extracting "
            "next-state functions from @seq blocks. This is planned. "
            "Use check_combinational_equivalence() for combinational modules, "
            "or use simulation-based comparison for sequential modules."
        ),
    }
