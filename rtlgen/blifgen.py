"""
rtlgen.blifgen — RTL IR → Bit-level BLIF Emitter

将 rtlgen.core.Module 展开为单比特 BLIF 网表，供 ABC/Yosys 做逻辑综合。
支持：
- 组合逻辑：AND/OR/XOR/NOT/MUX/Slice/Concat/BitSelect
- 算术逻辑：+ / - / == / != / < / <= / > / >= （通过 full_adder / full_subtractor 链展开）
- 时序逻辑：Reg 映射为 .latch（同步复位处理）
- 控制流：IfNode / SwitchNode 转成 MUX 树
"""

import math
from enum import Enum
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
    GenVar,
    IfNode,
    IndexedAssign,
    MemRead,
    MemWrite,
    Module,
    Mux,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
)


class BLIFContext:
    """BLIF 生成上下文，维护当前信号到 wire 名的映射。"""

    def __init__(self, emitter: "BLIFEmitter"):
        self.emitter = emitter
        self.bindings: Dict[str, List[str]] = {}

    def copy(self) -> "BLIFContext":
        c = BLIFContext(self.emitter)
        c.bindings = dict(self.bindings)
        return c

    def get(self, name: str, width: int) -> List[str]:
        if name in self.bindings:
            return self.bindings[name]
        # 未绑定信号，使用原始名
        bits = self.emitter._sig_bits(name, width)
        self.bindings[name] = bits
        return bits

    def set(self, name: str, bits: List[str]):
        self.bindings[name] = list(bits)


class AdderStyle(Enum):
    RCA = "rca"
    CLA = "cla"
    KOGGE_STONE = "kogge_stone"
    BRENT_KUNG = "brent_kung"


class MultiplierStyle(Enum):
    ARRAY = "array"
    BOOTH = "booth"
    WALLACE = "wallace"


class DividerStyle(Enum):
    RESTORING = "restoring"


class SynthConfig:
    """逻辑综合配置：根据时序/面积约束选择算子实现。"""

    def __init__(
        self,
        adder: AdderStyle = AdderStyle.RCA,
        multiplier: MultiplierStyle = MultiplierStyle.ARRAY,
        divider: DividerStyle = DividerStyle.RESTORING,
        cla_block_size: int = 4,
    ):
        self.adder = adder
        self.multiplier = multiplier
        self.divider = divider
        self.cla_block_size = cla_block_size


class BLIFEmitter:
    def __init__(self, config: Optional[SynthConfig] = None):
        self.config = config or SynthConfig()
        self.lines: List[str] = []
        self._wire_counter = 0
        self._models: Set[str] = set()
        self._top_inputs: Set[str] = set()
        self._top_outputs: Set[str] = set()
        self._latches: List[Tuple[str, str]] = []  # (next_wire, reg_name)
        self._module: Optional[Module] = None

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit(self, module: Module) -> str:
        self.lines = []
        self._wire_counter = 0
        self._models.clear()
        self._top_inputs.clear()
        self._top_outputs.clear()
        self._latches.clear()
        self._module = module

        ctx = BLIFContext(self)

        # 收集所有 I/O 位名
        inputs_bits: List[str] = []
        for name, sig in module._inputs.items():
            inputs_bits.extend(self._sig_bits(name, sig.width))
        outputs_bits: List[str] = []
        for name, sig in module._outputs.items():
            outputs_bits.extend(self._sig_bits(name, sig.width))

        # 常量节点：gnd 为常数 0（无 truth table 行），vdd 为常数 1（0 输入 -> 输出 1）
        const_decls = [".names gnd", ".names vdd", "1"]

        self.lines.append(f".model {module.name}")
        self.lines.append(f".inputs {' '.join(inputs_bits)}")
        self.lines.append(f".outputs {' '.join(outputs_bits)}")
        for line in const_decls:
            self.lines.append(line)

        # 组合逻辑块
        for body in module._comb_blocks:
            self._emit_body(body, ctx)

        # 顶层实例化与 assign
        for stmt in module._top_level:
            self._emit_stmt(stmt, ctx)

        # 时序逻辑块：生成 next-state 逻辑和 .latch
        seq_ctx = ctx.copy()
        for clk, rst, rst_async, rst_active_low, body in module._seq_blocks:
            # 把时序块body当作组合逻辑处理，但目标信号映射到 _next_ 版本
            self._emit_seq_body(body, seq_ctx, rst, rst_active_low)

        for stmt in module._seq_blocks:
            # stmt 已经展开到 seq_ctx，latch 在 _emit_seq_body 中收集
            pass

        # 子模块隐式实例化
        for inst_name, submod in module._submodules:
            self._emit_implicit_submodule(inst_name, submod, ctx)

        # 输出 latch 声明
        for next_w, reg_name in self._latches:
            self.lines.append(f".latch {next_w} {reg_name} 2")

        self.lines.append(".end")

        # 前置 models
        model_lines: List[str] = []
        if "full_adder" in self._models:
            model_lines.extend(self._model_full_adder())
            model_lines.append("")
        if "half_adder" in self._models:
            model_lines.extend(self._model_half_adder())
            model_lines.append("")
        if "full_subtractor" in self._models:
            model_lines.extend(self._model_full_subtractor())
            model_lines.append("")

        return "\n".join(model_lines + self.lines)

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _fresh_wire(self, prefix: str = "w") -> str:
        self._wire_counter += 1
        return f"{prefix}_{self._wire_counter}"

    def _sig_bits(self, name: str, width: int) -> List[str]:
        if width == 1:
            return [name]
        return [f"{name}[{i}]" for i in range(width)]

    # -----------------------------------------------------------------
    # Statement emission
    # -----------------------------------------------------------------
    def _emit_body(self, body: List[Any], ctx: BLIFContext, emit_changes: bool = True):
        old_bindings = dict(ctx.bindings)
        for stmt in body:
            self._emit_stmt(stmt, ctx)
        if not emit_changes:
            return
        # 将 binding 的变化写入 BLIF lines
        for key, new_bits in ctx.bindings.items():
            old_bits = old_bindings.get(key)
            if old_bits is None:
                # 首次赋值：目标是原始信号名（已由 ctx.get 推导）
                width = len(new_bits)
                target_bits = self._sig_bits(key, width)
                for t, s in zip(target_bits, new_bits):
                    if t != s:
                        self._emit_buf(s, t)
            else:
                for t, s in zip(old_bits, new_bits):
                    if t != s:
                        self._emit_buf(s, t)

    def _emit_stmt(self, stmt: Any, ctx: BLIFContext):
        if isinstance(stmt, Assign):
            bits = self._emit_expr_bits(stmt.value, ctx)
            # 确保赋值位宽与目标信号声明宽度一致
            target_width = stmt.target.width
            if len(bits) < target_width:
                bits = bits + ["gnd"] * (target_width - len(bits))
            elif len(bits) > target_width:
                bits = bits[:target_width]
            ctx.set(stmt.target.name, bits)
        elif isinstance(stmt, IndexedAssign):
            # 数组/向量索引赋值，MVP 下直接忽略或后续扩展
            pass
        elif isinstance(stmt, IfNode):
            self._emit_ifnode(stmt, ctx)
        elif isinstance(stmt, SwitchNode):
            self._emit_switchnode(stmt, ctx)
        elif isinstance(stmt, ForGenNode):
            for i in range(stmt.start, stmt.end):
                unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                self._emit_body(unrolled, ctx)
        elif isinstance(stmt, GenIfNode):
            if self._eval_const(stmt.cond, ctx):
                self._emit_body(stmt.then_body, ctx)
            else:
                self._emit_body(stmt.else_body, ctx)
        elif isinstance(stmt, SubmoduleInst):
            self._emit_submodule_inst(stmt, ctx)
        elif isinstance(stmt, (MemWrite, ArrayWrite)):
            pass

    def _emit_seq_body(self, body: List[Any], ctx: BLIFContext, rst: Optional[Signal], rst_active_low: bool):
        """时序块：所有 Assign target 映射到 _next_ wire，最后生成 .latch"""
        # 先收集时序块中所有被赋值的信号名
        assigned: Set[str] = set()
        def _collect_targets(stmts: List[Any]):
            for s in stmts:
                if isinstance(s, Assign):
                    assigned.add(s.target.name)
                elif isinstance(s, IfNode):
                    _collect_targets(s.then_body)
                    _collect_targets(s.else_body)
                elif isinstance(s, SwitchNode):
                    for _, cb in s.cases:
                        _collect_targets(cb)
                    _collect_targets(s.default_body)
                elif isinstance(s, ForGenNode):
                    _collect_targets(s.body)
                elif isinstance(s, GenIfNode):
                    _collect_targets(s.then_body)
                    _collect_targets(s.else_body)

        _collect_targets(body)

        # 为每个被赋值信号创建 _next_ wire（作为默认 next-state）
        next_map: Dict[str, List[str]] = {}
        for name in assigned:
            width = self._width_of(name)
            next_bits = [self._fresh_wire(f"{name}_next") for _ in range(width)]
            next_map[name] = next_bits

        # 递归处理 body，但重定向 target，且不通过 _emit_body 的 change-detection
        # 输出到原始 reg 名（避免组合门与 .latch 双重驱动 reg）
        seq_ctx = ctx.copy()
        for name in assigned:
            width = self._width_of(name)
            seq_ctx.set(name, next_map[name])

        self._emit_body(body, seq_ctx, emit_changes=False)

        # 应用 reset（同步处理）
        if rst is not None:
            rst_bits = ctx.get(rst.name, rst.width)
            rst_wire = rst_bits[0]
            for name in assigned:
                width = self._width_of(name)
                final_next = seq_ctx.bindings.get(name, next_map[name])
                for i in range(width):
                    mux_out = self._fresh_wire(f"{name}_rst")
                    if rst_active_low:
                        # reset=0 -> 0
                        self._emit_mux2(rst_wire, final_next[i], "gnd", mux_out)
                    else:
                        # reset=1 -> 0
                        self._emit_mux2(rst_wire, "gnd", final_next[i], mux_out)
                    if name not in seq_ctx.bindings:
                        seq_ctx.bindings[name] = list(next_map[name])
                    seq_ctx.bindings[name][i] = mux_out

        # 登记 latch（使用 seq_ctx 中最终确定的 next-state wire）
        for name in assigned:
            width = self._width_of(name)
            orig_bits = self._sig_bits(name, width)
            final_next = seq_ctx.bindings.get(name, next_map[name])
            for i in range(width):
                self._latches.append((final_next[i], orig_bits[i]))

    def _emit_ifnode(self, node: IfNode, ctx: BLIFContext):
        cond_bits = self._emit_expr_bits(node.cond, ctx)
        cond = cond_bits[0]

        then_ctx = ctx.copy()
        self._emit_body(node.then_body, then_ctx, emit_changes=False)

        else_ctx = ctx.copy()
        self._emit_body(node.else_body, else_ctx, emit_changes=False)

        # 合并两边的修改
        all_keys = set(then_ctx.bindings.keys()) | set(else_ctx.bindings.keys())
        for key in all_keys:
            if key not in ctx.bindings and not self._is_valid_signal(key):
                continue
            # 确保 ctx 中有初始绑定
            if key not in ctx.bindings:
                width = self._width_of(key)
                ctx.bindings[key] = self._sig_bits(key, width)
            t_bits = then_ctx.bindings.get(key)
            e_bits = else_ctx.bindings.get(key)
            if t_bits is None and e_bits is None:
                continue
            width = len(ctx.bindings[key])
            if t_bits is None:
                t_bits = ctx.bindings[key]
            if e_bits is None:
                e_bits = ctx.bindings[key]
            merged = []
            for i in range(width):
                if t_bits[i] == e_bits[i]:
                    merged.append(t_bits[i])
                else:
                    out = self._fresh_wire()
                    self._emit_mux2(cond, t_bits[i], e_bits[i], out)
                    merged.append(out)
            ctx.set(key, merged)

    def _emit_switchnode(self, node: SwitchNode, ctx: BLIFContext):
        """SwitchNode -> 级联 If/MUX"""
        expr_bits = self._emit_expr_bits(node.expr, ctx)
        # 简化：如果 expr 是纯常量宽度，我们为每个 case 生成一个比较器树
        # 但更简单的方法是：顺序生成 If-else if 结构
        # 这里我们用递归方式处理：
        # switch(expr) { case v0: body0; ... default: default_body }
        # => tmp = default_body_result; for case in reversed(cases): tmp = (expr==v) ? body : tmp

        # 先处理 default，得到基准环境
        base_ctx = ctx.copy()
        self._emit_body(node.default_body, base_ctx, emit_changes=False)

        # 倒序处理 cases（优先级从低到高，但 Verilog case 没有优先级，这里按出现顺序当作 priority）
        for val_expr, case_body in reversed(node.cases):
            case_ctx = ctx.copy()
            self._emit_body(case_body, case_ctx, emit_changes=False)
            eq_bits = self._emit_eq_bits(node.expr, val_expr, ctx)
            cond = eq_bits[0]
            for key in set(base_ctx.bindings.keys()) | set(case_ctx.bindings.keys()):
                if key not in ctx.bindings and not self._is_valid_signal(key):
                    continue
                if key not in ctx.bindings:
                    width = self._width_of(key)
                    ctx.bindings[key] = self._sig_bits(key, width)
                width = len(ctx.bindings[key])
                b_bits = base_ctx.bindings.get(key, ctx.bindings[key])
                c_bits = case_ctx.bindings.get(key, ctx.bindings[key])
                merged = []
                for i in range(width):
                    if b_bits[i] == c_bits[i]:
                        merged.append(b_bits[i])
                    else:
                        out = self._fresh_wire()
                        self._emit_mux2(cond, c_bits[i], b_bits[i], out)
                        merged.append(out)
                base_ctx.set(key, merged)

        # 把 base_ctx 的修改同步回 ctx
        for key, bits in base_ctx.bindings.items():
            if key in ctx.bindings or self._is_valid_signal(key):
                if key not in ctx.bindings:
                    width = self._width_of(key)
                    ctx.bindings[key] = self._sig_bits(key, width)
                ctx.set(key, bits)

    def _emit_submodule_inst(self, stmt: SubmoduleInst, ctx: BLIFContext):
        # MVP：把子模块端口映射当作连线处理（不展开子模块内部）
        # 更好的做法是递归 emit 子模块，但这里先简单处理
        for pname, expr in stmt.port_map.items():
            if isinstance(expr, Expr):
                src_bits = self._emit_expr_bits(expr, ctx)
                # 目标信号名：inst_name.pname[i]
                width = len(src_bits)
                for i in range(width):
                    dst = f"{stmt.name}_{pname}[{i}]"
                    if src_bits[i] != dst:
                        self._emit_buf(src_bits[i], dst)

    def _emit_implicit_submodule(self, inst_name: str, submod: Module, ctx: BLIFContext):
        port_map: Dict[str, Expr] = {}
        for pname in list(submod._inputs.keys()) + list(submod._outputs.keys()):
            if self._module is not None and hasattr(self._module, pname):
                val = getattr(self._module, pname)
                if isinstance(val, Signal):
                    port_map[pname] = val._expr
        self._emit_submodule_inst(
            type("SM", (), {"name": inst_name, "port_map": port_map, "module": submod, "params": {}})(),
            ctx
        )

    # -----------------------------------------------------------------
    # Expression → bits
    # -----------------------------------------------------------------
    def _emit_expr_bits(self, expr: Any, ctx: BLIFContext) -> List[str]:
        if isinstance(expr, int):
            # Python int literal
            width = max(expr.bit_length(), 1)
            return ["vdd" if ((expr >> i) & 1) else "gnd" for i in range(width)]
        if isinstance(expr, Const):
            return ["vdd" if ((expr.value >> i) & 1) else "gnd" for i in range(expr.width)]
        if isinstance(expr, Ref):
            return ctx.get(expr.signal.name, expr.signal.width)
        if isinstance(expr, Slice):
            operand_bits = self._emit_expr_bits(expr.operand, ctx)
            return operand_bits[expr.lo:expr.hi + 1]
        if isinstance(expr, PartSelect):
            operand_bits = self._emit_expr_bits(expr.operand, ctx)
            try:
                offset = self._eval_const(expr.offset, ctx)
                return operand_bits[offset:offset + expr.width]
            except ValueError:
                offset_bits = self._emit_expr_bits(expr.offset, ctx)
                res = []
                pad_len = 1 << len(offset_bits)
                for i in range(expr.width):
                    candidates = []
                    for j in range(pad_len):
                        idx = j + i
                        candidates.append(operand_bits[idx] if idx < len(operand_bits) else "gnd")
                    res.append(self._emit_mux_tree(offset_bits, candidates))
                return res
        if isinstance(expr, BitSelect):
            operand_bits = self._emit_expr_bits(expr.operand, ctx)
            try:
                idx = self._eval_const(expr.index, ctx)
                return [operand_bits[idx]]
            except ValueError:
                index_bits = self._emit_expr_bits(expr.index, ctx)
                pad_len = 1 << len(index_bits)
                candidates = []
                for j in range(pad_len):
                    candidates.append(operand_bits[j] if j < len(operand_bits) else "gnd")
                return [self._emit_mux_tree(index_bits, candidates)]
        if isinstance(expr, Concat):
            result = []
            for op in expr.operands:
                result.extend(self._emit_expr_bits(op, ctx))
            return result
        if isinstance(expr, BinOp):
            return self._emit_binop_bits(expr, ctx)
        if isinstance(expr, UnaryOp):
            return self._emit_unaryop_bits(expr, ctx)
        if isinstance(expr, Mux):
            cond_bits = self._emit_expr_bits(expr.cond, ctx)
            t_bits = self._emit_expr_bits(expr.true_expr, ctx)
            f_bits = self._emit_expr_bits(expr.false_expr, ctx)
            width = expr.width
            while len(t_bits) < width:
                t_bits.append("gnd")
            while len(f_bits) < width:
                f_bits.append("gnd")
            out = []
            for i in range(width):
                w = self._fresh_wire()
                self._emit_mux2(cond_bits[0], t_bits[i], f_bits[i], w)
                out.append(w)
            return out
        if isinstance(expr, (MemRead, ArrayRead)):
            # MVP：返回临时 wire，不展开 memory 逻辑
            return [self._fresh_wire("mem") for _ in range(expr.width)]
        return []

    def _emit_binop_bits(self, expr: BinOp, ctx: BLIFContext) -> List[str]:
        lhs = self._emit_expr_bits(expr.lhs, ctx)
        rhs = self._emit_expr_bits(expr.rhs, ctx)
        w = expr.width
        op = expr.op

        if op in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "&", "|", "^"):
            out = []
            for i in range(w):
                a = lhs[i] if i < len(lhs) else "gnd"
                b = rhs[i] if i < len(rhs) else "gnd"
                y = self._fresh_wire()
                if op in ("AND", "&"):
                    self._emit_and2(a, b, y)
                elif op in ("OR", "|"):
                    self._emit_or2(a, b, y)
                elif op in ("XOR", "^"):
                    self._emit_xor2(a, b, y)
                elif op == "NAND":
                    self._emit_nand2(a, b, y)
                elif op == "NOR":
                    self._emit_nor2(a, b, y)
                elif op == "XNOR":
                    self._emit_xnor2(a, b, y)
                out.append(y)
            return out

        if op in ("==", "!="):
            # 按位 XNOR，再树形 AND/OR
            min_w = min(len(lhs), len(rhs), w)
            eq_bits = []
            for i in range(min_w):
                a = lhs[i] if i < len(lhs) else "gnd"
                b = rhs[i] if i < len(rhs) else "gnd"
                y = self._fresh_wire()
                self._emit_xnor2(a, b, y)
                eq_bits.append(y)
            # 多余位比较：如果是 ==，多余位必须是 0；如果是 !=，可以忽略
            # 简化：只比较 min_w 位
            result = self._tree_and(eq_bits)
            if op == "==":
                return [result]
            else:
                inv = self._fresh_wire()
                self._emit_not(result, inv)
                return [inv]

        if op == "+":
            return self._emit_adder(lhs, rhs, w)

        if op == "-":
            return self._emit_subtractor_chain(lhs, rhs, w)

        if op in ("<", "<=", ">", ">="):
            return self._emit_unsigned_cmp(lhs, rhs, op)

        if op in ("<<", ">>"):
            return [self._fresh_wire("shift") for _ in range(w)]

        if op == "*":
            return self._emit_multiplier(lhs, rhs, w)

        if op == "/":
            return self._emit_divider(lhs, rhs, w)

        # fallback
        return [self._fresh_wire("op") for _ in range(w)]

    def _emit_unaryop_bits(self, expr: UnaryOp, ctx: BLIFContext) -> List[str]:
        operand = self._emit_expr_bits(expr.operand, ctx)
        if expr.op == "~":
            out = []
            for b in operand:
                y = self._fresh_wire()
                self._emit_not(b, y)
                out.append(y)
            return out
        return list(operand)

    def _emit_eq_bits(self, lhs_expr: Expr, rhs_expr: Expr, ctx: BLIFContext) -> List[str]:
        lhs = self._emit_expr_bits(lhs_expr, ctx)
        rhs = self._emit_expr_bits(rhs_expr, ctx)
        min_w = min(len(lhs), len(rhs))
        eq_bits = []
        for i in range(min_w):
            y = self._fresh_wire()
            self._emit_xnor2(lhs[i], rhs[i], y)
            eq_bits.append(y)
        return [self._tree_and(eq_bits)]

    # -----------------------------------------------------------------
    # Arithmetic building blocks
    # -----------------------------------------------------------------
    def _emit_adder_chain(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        self._models.add("full_adder")
        self._models.add("half_adder")
        out = []
        cin = "gnd"
        for i in range(width):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            s = self._fresh_wire(f"s_{i}")
            cout = self._fresh_wire(f"c_{i}")
            if i == 0 and cin == "gnd":
                self.lines.append(f".subckt half_adder a={a} b={b} s={s} c={cout}")
            else:
                self.lines.append(f".subckt full_adder a={a} b={b} cin={cin} s={s} cout={cout}")
            out.append(s)
            cin = cout
        return out

    def _emit_subtractor_chain(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        self._models.add("full_subtractor")
        out = []
        binin = "gnd"
        for i in range(width):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            d = self._fresh_wire(f"d_{i}")
            bout = self._fresh_wire(f"bout_{i}")
            self.lines.append(f".subckt full_subtractor a={a} b={b} bin={binin} d={d} bout={bout}")
            out.append(d)
            binin = bout
        return out

    def _emit_unsigned_cmp(self, lhs: List[str], rhs: List[str], op: str) -> List[str]:
        """无符号比较，返回 1-bit 结果。"""
        # a < b  =>  subtractor final borrow = 1
        # a <= b =>  (a < b) or (a == b)
        # a > b  =>  !(a <= b)
        # a >= b =>  !(a < b)
        max_w = max(len(lhs), len(rhs))
        self._models.add("full_subtractor")
        binin = "gnd"
        for i in range(max_w):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            d = self._fresh_wire()
            bout = self._fresh_wire()
            self.lines.append(f".subckt full_subtractor a={a} b={b} bin={binin} d={d} bout={bout}")
            binin = bout
        borrow = binin
        if op == "<":
            return [borrow]
        if op == ">=":
            y = self._fresh_wire()
            self._emit_not(borrow, y)
            return [y]
        if op == "<=":
            # a <= b  =  a < b  or  a == b
            eq_bits = []
            for i in range(max_w):
                a = lhs[i] if i < len(lhs) else "gnd"
                b = rhs[i] if i < len(rhs) else "gnd"
                y = self._fresh_wire()
                self._emit_xnor2(a, b, y)
                eq_bits.append(y)
            eq = self._tree_and(eq_bits)
            res = self._fresh_wire()
            self._emit_or2(borrow, eq, res)
            return [res]
        if op == ">":
            # a > b  =  !(a <= b)
            eq_bits = []
            for i in range(max_w):
                a = lhs[i] if i < len(lhs) else "gnd"
                b = rhs[i] if i < len(rhs) else "gnd"
                y = self._fresh_wire()
                self._emit_xnor2(a, b, y)
                eq_bits.append(y)
            eq = self._tree_and(eq_bits)
            le = self._fresh_wire()
            self._emit_or2(borrow, eq, le)
            res = self._fresh_wire()
            self._emit_not(le, res)
            return [res]
        return ["gnd"]

    # -----------------------------------------------------------------
    # Parameterized arithmetic dispatchers
    # -----------------------------------------------------------------
    def _emit_adder(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        style = self.config.adder
        if style == AdderStyle.CLA:
            return self._emit_adder_cla(lhs, rhs, width, self.config.cla_block_size)
        if style == AdderStyle.KOGGE_STONE:
            return self._emit_adder_kogge_stone(lhs, rhs, width)
        if style == AdderStyle.BRENT_KUNG:
            return self._emit_adder_brent_kung(lhs, rhs, width)
        return self._emit_adder_rca(lhs, rhs, width)

    def _emit_multiplier(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        style = self.config.multiplier
        if style == MultiplierStyle.BOOTH:
            return self._emit_multiplier_booth(lhs, rhs, width)
        if style == MultiplierStyle.WALLACE:
            return self._emit_multiplier_wallace(lhs, rhs, width)
        return self._emit_multiplier_array(lhs, rhs, width)

    def _emit_divider(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        style = self.config.divider
        if style == DividerStyle.RESTORING:
            return self._emit_divider_restoring(lhs, rhs, width)
        return [self._fresh_wire("div") for _ in range(width)]

    # -----------------------------------------------------------------
    # Adder implementations
    # -----------------------------------------------------------------
    def _emit_half_adder_aig(self, a: str, b: str, s: str, c: str):
        self._emit_xor2(a, b, s)
        self._emit_and2(a, b, c)

    def _emit_full_adder_aig(self, a: str, b: str, cin: str, s: str, cout: str):
        t1 = self._fresh_wire()
        self._emit_xor2(a, b, t1)
        self._emit_xor2(t1, cin, s)
        t2 = self._fresh_wire()
        t3 = self._fresh_wire()
        self._emit_and2(a, b, t2)
        self._emit_and2(t1, cin, t3)
        self._emit_or2(t2, t3, cout)

    def _emit_full_subtractor_aig(self, a: str, b: str, binin: str, d: str, bout: str):
        t1 = self._fresh_wire()
        self._emit_xor2(a, b, t1)
        self._emit_xor2(t1, binin, d)
        not_a = self._fresh_wire()
        self._emit_not(a, not_a)
        t2 = self._fresh_wire()
        self._emit_and2(not_a, b, t2)
        not_t1 = self._fresh_wire()
        self._emit_not(t1, not_t1)
        t3 = self._fresh_wire()
        self._emit_and2(not_t1, binin, t3)
        self._emit_or2(t2, t3, bout)

    def _emit_adder_rca(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Ripple Carry Adder using pure AIG primitives."""
        out = []
        cin = "gnd"
        for i in range(width):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            s = self._fresh_wire(f"s_{i}")
            cout = self._fresh_wire(f"c_{i}")
            if i == 0 and cin == "gnd":
                self._emit_half_adder_aig(a, b, s, cout)
            else:
                self._emit_full_adder_aig(a, b, cin, s, cout)
            out.append(s)
            cin = cout
        return out

    def _emit_adder_cla(self, lhs: List[str], rhs: List[str], width: int, block_size: int = 4) -> List[str]:
        """Carry Lookahead Adder (block-based)."""
        out = []
        cin = "gnd"
        for base in range(0, width, block_size):
            bw = min(block_size, width - base)
            P = []
            G = []
            for i in range(bw):
                a = lhs[base + i] if base + i < len(lhs) else "gnd"
                b = rhs[base + i] if base + i < len(rhs) else "gnd"
                p = self._fresh_wire()
                g = self._fresh_wire()
                self._emit_xor2(a, b, p)
                self._emit_and2(a, b, g)
                P.append(p)
                G.append(g)

            carries = [cin]
            for i in range(bw):
                # C_{i+1} = G_i | (P_i & G_{i-1}) | (P_i & P_{i-1} & G_{i-2}) | ... | (P_i..P_0 & cin)
                terms = [G[i]]
                prod = P[i]
                for j in range(i - 1, -1, -1):
                    t = self._fresh_wire()
                    self._emit_and2(prod, G[j], t)
                    terms.append(t)
                    new_prod = self._fresh_wire()
                    self._emit_and2(prod, P[j], new_prod)
                    prod = new_prod
                # final term: prod & cin
                t = self._fresh_wire()
                self._emit_and2(prod, cin, t)
                terms.append(t)
                c = self._tree_or(terms)
                carries.append(c)

            for i in range(bw):
                s = self._fresh_wire()
                self._emit_xor2(P[i], carries[i], s)
                out.append(s)
            cin = carries[-1]
        return out

    def _emit_adder_kogge_stone(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Kogge-Stone prefix adder."""
        n = 1
        while n < width:
            n <<= 1
        G = []
        P = []
        for i in range(n):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            g = self._fresh_wire()
            p = self._fresh_wire()
            self._emit_and2(a, b, g)
            self._emit_xor2(a, b, p)
            G.append(g)
            P.append(p)

        depth = int(math.log2(n))
        for d in range(depth):
            step = 1 << d
            new_G = list(G)
            new_P = list(P)
            for i in range(n):
                if i >= step:
                    g_l = G[i - step]
                    p_l = P[i - step]
                    g_r = G[i]
                    p_r = P[i]
                    ng = self._fresh_wire()
                    np = self._fresh_wire()
                    t = self._fresh_wire()
                    self._emit_and2(p_r, g_l, t)
                    self._emit_or2(g_r, t, ng)
                    self._emit_and2(p_r, p_l, np)
                    new_G[i] = ng
                    new_P[i] = np
            G = new_G
            P = new_P

        out = []
        for i in range(width):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            p = self._fresh_wire()
            self._emit_xor2(a, b, p)
            if i == 0:
                out.append(p)
            else:
                s = self._fresh_wire()
                self._emit_xor2(p, G[i - 1], s)
                out.append(s)
        return out

    def _emit_adder_brent_kung(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Brent-Kung prefix adder (sparse tree + fan-out)."""
        n = 1
        while n < width:
            n <<= 1
        G = []
        P = []
        for i in range(n):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            g = self._fresh_wire()
            p = self._fresh_wire()
            self._emit_and2(a, b, g)
            self._emit_xor2(a, b, p)
            G.append(g)
            P.append(p)

        # Up-sweep (reduce tree)
        depth = int(math.log2(n))
        layers = [(list(G), list(P))]
        for d in range(depth):
            step = 1 << d
            prev_G, prev_P = layers[-1]
            new_G = list(prev_G)
            new_P = list(prev_P)
            for i in range(n):
                if (i + 1) % (step * 2) == 0:
                    g_l = prev_G[i - step]
                    p_l = prev_P[i - step]
                    g_r = prev_G[i]
                    p_r = prev_P[i]
                    ng = self._fresh_wire()
                    np = self._fresh_wire()
                    t = self._fresh_wire()
                    self._emit_and2(p_r, g_l, t)
                    self._emit_or2(g_r, t, ng)
                    self._emit_and2(p_r, p_l, np)
                    new_G[i] = ng
                    new_P[i] = np
            layers.append((new_G, new_P))

        # Down-sweep (broadcast)
        for d in reversed(range(depth)):
            step = 1 << d
            cur_G, cur_P = layers[d + 1]
            nxt_G, nxt_P = layers[d]
            for i in range(n):
                if (i + 1) % (step * 2) == step and i >= step:
                    g_l = cur_G[i - step]
                    p_l = cur_P[i - step]
                    g_r = nxt_G[i]
                    p_r = nxt_P[i]
                    ng = self._fresh_wire()
                    np = self._fresh_wire()
                    t = self._fresh_wire()
                    self._emit_and2(p_r, g_l, t)
                    self._emit_or2(g_r, t, ng)
                    self._emit_and2(p_r, p_l, np)
                    nxt_G[i] = ng
                    nxt_P[i] = np

        final_G, final_P = layers[0]
        out = []
        for i in range(width):
            a = lhs[i] if i < len(lhs) else "gnd"
            b = rhs[i] if i < len(rhs) else "gnd"
            p = self._fresh_wire()
            self._emit_xor2(a, b, p)
            if i == 0:
                out.append(p)
            else:
                s = self._fresh_wire()
                self._emit_xor2(p, final_G[i - 1], s)
                out.append(s)
        return out

    # -----------------------------------------------------------------
    # Multiplier implementations
    # -----------------------------------------------------------------
    def _emit_multiplier_array(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Array multiplier: partial products + ripple accumulation."""
        m = len(lhs)
        n = len(rhs)
        rw = m + n
        acc = ["gnd"] * rw
        for j in range(n):
            row = ["gnd"] * j
            bj = rhs[j] if j < len(rhs) else "gnd"
            for i in range(m):
                w = self._fresh_wire()
                self._emit_and2(lhs[i], bj, w)
                row.append(w)
            row = row + ["gnd"] * (rw - len(row))
            row = row[:rw]
            acc = self._emit_adder(acc, row, rw)
        return acc[:width]

    def _emit_multiplier_booth(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Radix-2 Booth multiplier (simplified unsigned version)."""
        m = len(lhs)
        n = len(rhs)
        rw = m + n + 1
        acc = ["gnd"] * rw
        y_prev = "gnd"
        for j in range(n):
            y_curr = rhs[j] if j < len(rhs) else "gnd"
            sel_add = self._fresh_wire()
            sel_sub = self._fresh_wire()
            not_ycurr = self._fresh_wire()
            not_yprev = self._fresh_wire()
            self._emit_not(y_curr, not_ycurr)
            self._emit_not(y_prev, not_yprev)
            self._emit_and2(not_ycurr, y_prev, sel_add)
            self._emit_and2(y_curr, not_yprev, sel_sub)

            row = ["gnd"] * j
            for i in range(m):
                not_a = self._fresh_wire()
                self._emit_not(lhs[i], not_a)
                mux1 = self._fresh_wire()
                self._emit_mux2(sel_sub, not_a, "gnd", mux1)
                mux2 = self._fresh_wire()
                self._emit_mux2(sel_add, lhs[i], mux1, mux2)
                row.append(mux2)
            # sign extension for subtraction
            not_msb = self._fresh_wire()
            self._emit_not(lhs[m - 1], not_msb)
            mux1_msb = self._fresh_wire()
            self._emit_mux2(sel_sub, not_msb, "gnd", mux1_msb)
            mux2_msb = self._fresh_wire()
            self._emit_mux2(sel_add, lhs[m - 1], mux1_msb, mux2_msb)
            row.append(mux2_msb)
            row = row + ["gnd"] * (rw - len(row))
            row = row[:rw]

            # add correction +1 when sel_sub is active (two's complement)
            if j == 0:
                correction_row = [sel_sub] + ["gnd"] * (rw - 1)
                acc = self._emit_adder(correction_row, row, rw)
            else:
                acc = self._emit_adder(acc, row, rw)
            y_prev = y_curr
        return acc[:width]

    def _emit_multiplier_wallace(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Wallace tree multiplier: column compression + fast final adder."""
        m = len(lhs)
        n = len(rhs)
        rw = m + n
        cols = [[] for _ in range(rw)]
        for j in range(n):
            bj = rhs[j] if j < len(rhs) else "gnd"
            for i in range(m):
                w = self._fresh_wire()
                self._emit_and2(lhs[i], bj, w)
                cols[i + j].append(w)

        # Reduce each column to 1 bit (carries go to next column)
        for k in range(rw):
            while len(cols[k]) > 2:
                a = cols[k].pop()
                b = cols[k].pop()
                c = cols[k].pop()
                s = self._fresh_wire()
                cout = self._fresh_wire()
                self._emit_full_adder_aig(a, b, c, s, cout)
                cols[k].append(s)
                if k + 1 < rw:
                    cols[k + 1].append(cout)
            if len(cols[k]) == 2:
                a = cols[k].pop()
                b = cols[k].pop()
                s = self._fresh_wire()
                cout = self._fresh_wire()
                self._emit_half_adder_aig(a, b, s, cout)
                cols[k].append(s)
                if k + 1 < rw:
                    cols[k + 1].append(cout)

        sum_row = [cols[k][0] if len(cols[k]) == 1 else "gnd" for k in range(rw)]
        return sum_row[:width]

    # -----------------------------------------------------------------
    # Divider implementations
    # -----------------------------------------------------------------
    def _emit_divider_restoring(self, lhs: List[str], rhs: List[str], width: int) -> List[str]:
        """Combinational restoring array divider. Returns quotient."""
        n = max(len(lhs), len(rhs))
        rem = ["gnd"] * n
        quotient = []
        for i in reversed(range(n)):
            rem_shifted = rem[1:] + [lhs[i] if i < len(lhs) else "gnd"]
            # subtract
            diff = []
            binin = "gnd"
            for j in range(n):
                a = rem_shifted[j]
                b = rhs[j] if j < len(rhs) else "gnd"
                d = self._fresh_wire()
                bout = self._fresh_wire()
                self._emit_full_subtractor_aig(a, b, binin, d, bout)
                diff.append(d)
                binin = bout
            borrow = binin
            # restore if borrow
            new_rem = []
            for j in range(n):
                m = self._fresh_wire()
                self._emit_mux2(borrow, rem_shifted[j], diff[j], m)
                new_rem.append(m)
            rem = new_rem
            qbit = self._fresh_wire()
            self._emit_not(borrow, qbit)
            quotient.insert(0, qbit)
        if len(quotient) < width:
            quotient = quotient + ["gnd"] * (width - len(quotient))
        return quotient[:width]

    # -----------------------------------------------------------------
    # Primitive BLIF emission
    # -----------------------------------------------------------------
    def _emit_and2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("11 1")

    def _emit_or2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("01 1")
        self.lines.append("10 1")
        self.lines.append("11 1")

    def _emit_nand2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("00 1")
        self.lines.append("01 1")
        self.lines.append("10 1")

    def _emit_nor2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("00 1")

    def _emit_xor2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("01 1")
        self.lines.append("10 1")

    def _emit_xnor2(self, a: str, b: str, y: str):
        self.lines.append(f".names {a} {b} {y}")
        self.lines.append("00 1")
        self.lines.append("11 1")

    def _emit_not(self, a: str, y: str):
        self.lines.append(f".names {a} {y}")
        self.lines.append("0 1")

    def _emit_buf(self, a: str, y: str):
        if a == y:
            return
        self.lines.append(f".names {a} {y}")
        self.lines.append("1 1")

    def _emit_mux2(self, sel: str, t: str, f: str, y: str):
        # y = sel ? t : f
        self.lines.append(f".names {sel} {t} {f} {y}")
        self.lines.append("0-1 1")
        self.lines.append("11- 1")

    def _emit_mux_tree(self, sel_bits: List[str], candidates: List[str]) -> str:
        """Return a net that selects one candidate via a binary tree of 2-to-1 MUXes.

        sel_bits[0] is the LSB and selects between pairs.
        sel=0 picks the lower (even) candidate, sel=1 picks the upper (odd).
        """
        if not candidates:
            return "gnd"
        if not sel_bits:
            return candidates[0]
        pad_len = 1 << len(sel_bits)
        cur = list(candidates)
        while len(cur) < pad_len:
            cur.append("gnd")
        cur = cur[:pad_len]
        for sel in sel_bits:
            nxt = []
            for i in range(0, len(cur), 2):
                a = cur[i]
                b = cur[i + 1] if i + 1 < len(cur) else "gnd"
                out = self._fresh_wire("mux")
                self._emit_mux2(sel, b, a, out)  # sel=0 -> a, sel=1 -> b
                nxt.append(out)
            cur = nxt
        return cur[0]

    def _tree_and(self, bits: List[str]) -> str:
        if not bits:
            return "vdd"
        if len(bits) == 1:
            return bits[0]
        cur = bits
        while len(cur) > 1:
            nxt = []
            for i in range(0, len(cur), 2):
                if i + 1 < len(cur):
                    y = self._fresh_wire()
                    self._emit_and2(cur[i], cur[i + 1], y)
                    nxt.append(y)
                else:
                    nxt.append(cur[i])
            cur = nxt
        return cur[0]

    def _tree_or(self, bits: List[str]) -> str:
        if not bits:
            return "gnd"
        if len(bits) == 1:
            return bits[0]
        cur = bits
        while len(cur) > 1:
            nxt = []
            for i in range(0, len(cur), 2):
                if i + 1 < len(cur):
                    y = self._fresh_wire()
                    self._emit_or2(cur[i], cur[i + 1], y)
                    nxt.append(y)
                else:
                    nxt.append(cur[i])
            cur = nxt
        return cur[0]

    # -----------------------------------------------------------------
    # Model definitions
    # -----------------------------------------------------------------
    def _model_half_adder(self) -> List[str]:
        return [
            ".model half_adder",
            ".inputs a b",
            ".outputs s c",
            ".names a b s",
            "01 1",
            "10 1",
            ".names a b c",
            "11 1",
            ".end",
        ]

    def _model_full_adder(self) -> List[str]:
        return [
            ".model full_adder",
            ".inputs a b cin",
            ".outputs s cout",
            ".names a b cin s",
            "001 1",
            "010 1",
            "100 1",
            "111 1",
            ".names a b cin cout",
            "011 1",
            "101 1",
            "110 1",
            "111 1",
            ".end",
        ]

    def _model_full_subtractor(self) -> List[str]:
        return [
            ".model full_subtractor",
            ".inputs a b bin",
            ".outputs d bout",
            ".names a b bin d",
            "001 1",
            "010 1",
            "100 1",
            "111 1",
            ".names a b bin bout",
            "001 1",
            "010 1",
            "011 1",
            "111 1",
            ".end",
        ]

    # -----------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------
    def _width_of(self, name: str) -> int:
        if self._module is None:
            return 1
        for d in (self._module._inputs, self._module._outputs, self._module._wires, self._module._regs):
            if name in d:
                return d[name].width
        return 1

    def _is_valid_signal(self, name: str) -> bool:
        if self._module is None:
            return False
        for d in (self._module._inputs, self._module._outputs, self._module._wires, self._module._regs):
            if name in d:
                return True
        return False

    def _eval_const(self, expr: Any, ctx: BLIFContext) -> int:
        if isinstance(expr, Const):
            return int(expr.value)
        if isinstance(expr, int):
            return expr
        if isinstance(expr, Ref):
            # 如果信号是 parameter，尝试从 module._params 取值
            param = self.module._params.get(expr.signal.name)
            if param is not None:
                return int(param.value)
        raise ValueError(f"Cannot evaluate {expr} as constant")

    @property
    def module(self) -> Optional[Module]:
        return self._module

# -----------------------------------------------------------------
# GenVar substitution helpers (for unrolling ForGenNode in BLIF)
# -----------------------------------------------------------------

def _subst_genvar_in_expr(expr: Expr, var_name: str, value: int) -> Expr:
    if isinstance(expr, GenVar) and expr.name == var_name:
        return Const(value=value, width=expr.width)
    if isinstance(expr, BinOp):
        return BinOp(expr.op, _subst_genvar_in_expr(expr.lhs, var_name, value),
                     _subst_genvar_in_expr(expr.rhs, var_name, value), expr.width)
    if isinstance(expr, UnaryOp):
        return UnaryOp(expr.op, _subst_genvar_in_expr(expr.operand, var_name, value), expr.width)
    if isinstance(expr, Slice):
        return Slice(_subst_genvar_in_expr(expr.operand, var_name, value), expr.hi, expr.lo)
    if isinstance(expr, PartSelect):
        return PartSelect(_subst_genvar_in_expr(expr.operand, var_name, value),
                          _subst_genvar_in_expr(expr.offset, var_name, value), expr.width)
    if isinstance(expr, BitSelect):
        return BitSelect(_subst_genvar_in_expr(expr.operand, var_name, value),
                         _subst_genvar_in_expr(expr.index, var_name, value))
    if isinstance(expr, Concat):
        return Concat([_subst_genvar_in_expr(op, var_name, value) for op in expr.operands], expr.width)
    if isinstance(expr, Mux):
        return Mux(_subst_genvar_in_expr(expr.cond, var_name, value),
                   _subst_genvar_in_expr(expr.true_expr, var_name, value),
                   _subst_genvar_in_expr(expr.false_expr, var_name, value), expr.width)
    if isinstance(expr, MemRead):
        return MemRead(expr.mem_name, _subst_genvar_in_expr(expr.addr, var_name, value), expr.width)
    if isinstance(expr, ArrayRead):
        return ArrayRead(expr.array_name, _subst_genvar_in_expr(expr.index, var_name, value), expr.width)
    return expr


def _subst_genvar_in_stmt(stmt: Any, var_name: str, value: int) -> Any:
    if isinstance(stmt, Assign):
        return Assign(stmt.target, _subst_genvar_in_expr(stmt.value, var_name, value), stmt.blocking)
    if isinstance(stmt, IndexedAssign):
        return IndexedAssign(stmt.target_signal, _subst_genvar_in_expr(stmt.index, var_name, value),
                             _subst_genvar_in_expr(stmt.value, var_name, value), stmt.blocking)
    if isinstance(stmt, IfNode):
        n = IfNode(_subst_genvar_in_expr(stmt.cond, var_name, value))
        n.then_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.then_body]
        n.else_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.else_body]
        return n
    if isinstance(stmt, SwitchNode):
        n = SwitchNode(_subst_genvar_in_expr(stmt.expr, var_name, value))
        n.cases = [(_subst_genvar_in_expr(v, var_name, value), [_subst_genvar_in_stmt(s, var_name, value) for s in b]) for v, b in stmt.cases]
        n.default_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.default_body]
        return n
    if isinstance(stmt, ForGenNode):
        n = ForGenNode(stmt.var_name, stmt.start, stmt.end)
        n.body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.body]
        return n
    if isinstance(stmt, GenIfNode):
        n = GenIfNode(_subst_genvar_in_expr(stmt.cond, var_name, value))
        n.then_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.then_body]
        n.else_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.else_body]
        return n
    if isinstance(stmt, ArrayWrite):
        return ArrayWrite(stmt.array_name, _subst_genvar_in_expr(stmt.index, var_name, value),
                          _subst_genvar_in_expr(stmt.value, var_name, value), stmt.blocking)
    if isinstance(stmt, MemWrite):
        return MemWrite(stmt.mem_name, _subst_genvar_in_expr(stmt.addr, var_name, value),
                        _subst_genvar_in_expr(stmt.value, var_name, value))
    if isinstance(stmt, SubmoduleInst):
        new_port_map = {k: _subst_genvar_in_expr(v, var_name, value) for k, v in stmt.port_map.items()}
        return SubmoduleInst(stmt.name, stmt.module, stmt.params, new_port_map)
    return stmt
