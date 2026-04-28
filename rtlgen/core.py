"""
rtlgen.core — 基础信号、AST 与模块容器

提供 Signal / Input / Output / Wire / Reg、Parameter、Module 以及全局上下文管理。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ---------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------

class Expr:
    def __init__(self, width: int = 1):
        self.width = width


class Const(Expr):
    def __init__(self, value: int, width: int = 1):
        super().__init__(width)
        self.value = value


class Ref(Expr):
    def __init__(self, signal: "Signal"):
        super().__init__(signal.width)
        self.signal = signal


class BinOp(Expr):
    def __init__(self, op: str, lhs: Expr, rhs: Expr, width: int):
        super().__init__(width)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class UnaryOp(Expr):
    def __init__(self, op: str, operand: Expr, width: int):
        super().__init__(width)
        self.op = op
        self.operand = operand


class Slice(Expr):
    def __init__(self, operand: Expr, hi: int, lo: int):
        super().__init__(hi - lo + 1)
        self.operand = operand
        self.hi = hi
        self.lo = lo


class PartSelect(Expr):
    """动态基址、静态宽度的位选择，如 signal[offset +: width]。

    用于 generate-for 或 always 块中的动态 slice，例如:
        self.state_in[base + 63 : base]   -> PartSelect(state_in, base, 64)
    """

    def __init__(self, operand: Expr, offset: Expr, width: int):
        super().__init__(width)
        self.operand = operand
        self.offset = offset


class BitSelect(Expr):
    """变量索引的单 bit 选择，例如 y[i]。"""

    def __init__(self, operand: Expr, index: Expr):
        super().__init__(1)
        self.operand = operand
        self.index = index


class Concat(Expr):
    def __init__(self, operands: List[Expr], width: int):
        super().__init__(width)
        self.operands = operands


class Mux(Expr):
    def __init__(self, cond: Expr, true_expr: Expr, false_expr: Expr, width: int):
        super().__init__(width)
        self.cond = cond
        self.true_expr = true_expr
        self.false_expr = false_expr


class Assign:
    def __init__(self, target: Union["Signal", "Expr"], value: Expr, blocking: bool):
        self.target = target
        self.value = value
        self.blocking = blocking


class IfNode:
    def __init__(self, cond: Expr):
        self.cond = cond
        self.then_body: List[Any] = []
        self.else_body: List[Any] = []


class GenIfNode:
    def __init__(self, cond: Expr):
        self.cond = cond
        self.then_body: List[Any] = []
        self.else_body: List[Any] = []


class SwitchNode:
    def __init__(self, expr: Expr):
        self.expr = expr
        self.cases: List[Tuple[Expr, List[Any]]] = []
        self.default_body: List[Any] = []


class SubmoduleInst:
    def __init__(self, name: str, module: "Module", params: Dict[str, Any], port_map: Dict[str, Union["Signal", Expr]]):
        self.name = name
        self.module = module
        self.params = params
        self.port_map = port_map


class MemRead(Expr):
    def __init__(self, mem_name: str, addr: Expr, width: int):
        super().__init__(width)
        self.mem_name = mem_name
        self.addr = addr


class MemWrite:
    def __init__(self, mem_name: str, addr: Expr, value: Expr):
        self.mem_name = mem_name
        self.addr = addr
        self.value = value


class ArrayRead(Expr):
    """二维数组元素读取表达式，如 arr[i]（元素位宽 > 1）。"""

    def __init__(self, array_name: str, index: Expr, width: int):
        super().__init__(width)
        self.array_name = array_name
        self.index = index


class ArrayWrite:
    """二维数组元素赋值语句，如 arr[i] = val 或 arr[i] <= val。"""

    def __init__(self, array_name: str, index: Expr, value: Expr, blocking: bool = False):
        self.array_name = array_name
        self.index = index
        self.value = value
        self.blocking = blocking


class ArrayProxy:
    """数组索引代理，支持 arr[i] <<= value 和 arr[i] 作为表达式。"""

    def __init__(self, array_name: str, index: Expr, width: int):
        self.array_name = array_name
        self.index = index
        self.width = width
        self._read_expr = ArrayRead(array_name, index, width)
        self._written = False

    def __ilshift__(self, value: Any):
        stmt = ArrayWrite(self.array_name, self.index, _to_expr(value), blocking=False)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Array write outside of any module or logic block")
        self._written = True
        return self

    def __getitem__(self, key):
        if isinstance(key, slice):
            hi = key.start if key.start is not None else self.width - 1
            lo = key.stop if key.stop is not None else 0
            # 动态 slice 支持
            if isinstance(hi, (Expr, Signal, GenVar)) or isinstance(lo, (Expr, Signal, GenVar)):
                hi_expr = _to_expr(hi)
                lo_expr = _to_expr(lo)
                width = _derive_partselect_width(hi_expr, lo_expr)
                if width is None:
                    raise ValueError(f"Cannot infer width from dynamic slice [{hi_expr} : {lo_expr}]")
                s = Signal(width=width)
                s._expr = PartSelect(_to_expr(self), lo_expr, width)
                return s
            s = Signal(width=hi - lo + 1)
            s._expr = Slice(_to_expr(self), hi, lo)
            return s
        elif isinstance(key, (GenVar, Expr, Signal)):
            s = Signal(width=1)
            s._expr = BitSelect(_to_expr(self), _to_expr(key))
            return s
        else:
            s = Signal(width=1)
            s._expr = Slice(_to_expr(self), key, key)
            return s

    # ---- arithmetic ---------------------------------------------------
    def __add__(self, other):
        return _make_binop("+", self, other)

    def __sub__(self, other):
        return _make_binop("-", self, other)

    def __mul__(self, other):
        aw = self.width
        bw = other.width if isinstance(other, (Signal, Expr, ArrayProxy)) else _to_expr(other).width
        return _make_binop("*", self, other, width=aw + bw)

    def __and__(self, other):
        return _make_binop("&", self, other)

    def __or__(self, other):
        return _make_binop("|", self, other)

    def __xor__(self, other):
        return _make_binop("^", self, other)

    def __lshift__(self, other):
        return _make_binop("<<", self, other, width=self.width)

    def __rshift__(self, other):
        return _make_binop(">>", self, other, width=self.width)

    def __mod__(self, other):
        return _make_binop("%", self, other)

    def __rmod__(self, other):
        return _make_binop("%", other, self)

    def __invert__(self):
        return _make_unop("~", self)

    # ---- comparison ---------------------------------------------------
    def __eq__(self, other):
        return _make_binop("==", self, other, width=1)

    def __ne__(self, other):
        return _make_binop("!=", self, other, width=1)

    def __lt__(self, other):
        return _make_binop("<", self, other, width=1)

    def __le__(self, other):
        return _make_binop("<=", self, other, width=1)

    def __gt__(self, other):
        return _make_binop(">", self, other, width=1)

    def __ge__(self, other):
        return _make_binop(">=", self, other, width=1)

    # ---- reverse ops --------------------------------------------------
    def __radd__(self, other):
        return _make_binop("+", other, self)

    def __rsub__(self, other):
        return _make_binop("-", other, self)

    def __rmul__(self, other):
        bw = self.width
        aw = other.width if isinstance(other, (Signal, Expr, ArrayProxy)) else _to_expr(other).width
        return _make_binop("*", other, self, width=aw + bw)

    def __rand__(self, other):
        return _make_binop("&", other, self)

    def __ror__(self, other):
        return _make_binop("|", other, self)

    def __rxor__(self, other):
        return _make_binop("^", other, self)

    def __rlshift__(self, other):
        return _make_binop("<<", other, self, width=_to_expr(other).width)

    def __rrshift__(self, other):
        return _make_binop(">>", other, self, width=_to_expr(other).width)


class IndexedAssign:
    """向量位选赋值：如 y[i] = a[i] 或 y[i] <= a[i]。"""

    def __init__(self, target_signal: Signal, index: Expr, value: Expr, blocking: bool):
        self.target_signal = target_signal
        self.index = index
        self.value = value
        self.blocking = blocking


class MemProxy:
    """Memory 读写代理对象，支持 mem[addr] 作为表达式以及 mem[addr] <<= value 写入。"""

    def __init__(self, mem_name: str, addr: Expr, width: int):
        self.mem_name = mem_name
        self.addr = addr
        self.width = width
        self._read_expr = MemRead(mem_name, addr, width)
        self._written = False

    def __ilshift__(self, value: Any):
        stmt = MemWrite(self.mem_name, self.addr, _to_expr(value))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Memory write outside of any module or logic block")
        self._written = True
        return self


class Comment:
    """Verilog 注释节点。"""

    def __init__(self, text: str):
        self.text = text


class Memory:
    """硬件存储器（生成 Verilog reg [width-1:0] name [0:depth-1]）。"""

    def __init__(self, width: int, depth: int, name: str = "", init_file: Optional[str] = None):
        self.width = width
        self.depth = depth
        self.name = name
        self.init_file = init_file
        self.addr_width = max(depth.bit_length(), 1)

    def __getitem__(self, addr: Any):
        return MemProxy(self.name, _to_expr(addr), self.width)

    def __setitem__(self, addr: Any, value: Any):
        """处理普通赋值 mem[addr] = value，以及 <<= 回退。"""
        addr_expr = _to_expr(addr)
        # 如果是 augmented assignment (mem[addr] <<= val) 的回退调用，
        # value 会是 MemProxy 且 _written 为 True，此时已写入过，跳过。
        if isinstance(value, MemProxy) and value._written:
            return
        stmt = MemWrite(self.name, addr_expr, _to_expr(value))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Memory write outside of any module or logic block")


class ForGenNode:
    def __init__(self, var_name: str, start: int, end: int):
        self.var_name = var_name
        self.start = start
        self.end = end
        self.body: List[Any] = []


class GenVar(Expr):
    """generate-for 循环变量（在 Verilog 中对应 genvar）。"""

    def __init__(self, name: str):
        super().__init__(1)
        self.name = name

    def __add__(self, other):
        return _genvar_binop("+", self, other)

    def __radd__(self, other):
        return _genvar_binop("+", other, self)

    def __sub__(self, other):
        return _genvar_binop("-", self, other)

    def __rsub__(self, other):
        return _genvar_binop("-", other, self)

    def __mul__(self, other):
        return _genvar_binop("*", self, other)

    def __rmul__(self, other):
        return _genvar_binop("*", other, self)

    def __eq__(self, other):
        return _make_binop("==", self, other, width=1)

    def __ne__(self, other):
        return _make_binop("!=", self, other, width=1)

    def __lt__(self, other):
        return _make_binop("<", self, other, width=1)

    def __le__(self, other):
        return _make_binop("<=", self, other, width=1)

    def __gt__(self, other):
        return _make_binop(">", self, other, width=1)

    def __ge__(self, other):
        return _make_binop(">=", self, other, width=1)

    def __mod__(self, other):
        return _genvar_binop("%", self, other)

    def __rmod__(self, other):
        return _genvar_binop("%", other, self)

    def __floordiv__(self, other):
        return _genvar_binop("/", self, other)

    def __rfloordiv__(self, other):
        return _genvar_binop("/", other, self)

    def __truediv__(self, other):
        return _genvar_binop("/", self, other)

    def __rtruediv__(self, other):
        return _genvar_binop("/", other, self)

    def __lshift__(self, other):
        return _genvar_binop("<<", self, other)

    def __rlshift__(self, other):
        return _genvar_binop("<<", other, self)

    def __rshift__(self, other):
        return _genvar_binop(">>", self, other)

    def __rrshift__(self, other):
        return _genvar_binop(">>", other, self)

    def __and__(self, other):
        return _genvar_binop("&", self, other)

    def __rand__(self, other):
        return _genvar_binop("&", other, self)

    def __or__(self, other):
        return _genvar_binop("|", self, other)

    def __ror__(self, other):
        return _genvar_binop("|", other, self)

    def __xor__(self, other):
        return _genvar_binop("^", self, other)

    def __rxor__(self, other):
        return _genvar_binop("^", other, self)

    def __repr__(self):
        return f"GenVar({self.name})"


def _genvar_binop(op: str, lhs: Any, rhs: Any) -> Signal:
    le = _to_expr(lhs)
    re = _to_expr(rhs)
    # 保守估计位宽，用于索引计算通常足够
    w = max(le.width, re.width) + 1
    s = Signal(width=w)
    s._expr = BinOp(op, le, re, w)
    return s


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _to_expr(val: Any) -> Expr:
    if isinstance(val, MemProxy):
        return val._read_expr
    if isinstance(val, ArrayProxy):
        return val._read_expr
    if isinstance(val, Signal):
        return val._expr
    if isinstance(val, Parameter):
        return val._expr
    if isinstance(val, int):
        width = val.bit_length()
        if width == 0:
            width = 1
        return Const(value=val, width=width)
    if isinstance(val, Expr):
        return val
    raise TypeError(f"Cannot convert {type(val)} to RTL expression")


def _max_width(a: Any, b: Any) -> int:
    aw = a.width if isinstance(a, (Signal, Expr)) else _to_expr(a).width
    bw = b.width if isinstance(b, (Signal, Expr)) else _to_expr(b).width
    return max(aw, bw)


def _expr_equal(a: Expr, b: Expr) -> bool:
    """结构化的表达式等价判断（不深究代数等价，只处理简单模式）。"""
    if type(a) != type(b):
        return False
    if isinstance(a, Const):
        return a.value == b.value and a.width == b.width
    if isinstance(a, Ref):
        return a.signal is b.signal
    if isinstance(a, BinOp):
        return a.op == b.op and _expr_equal(a.lhs, b.lhs) and _expr_equal(a.rhs, b.rhs)
    if isinstance(a, UnaryOp):
        return a.op == b.op and _expr_equal(a.operand, b.operand)
    if isinstance(a, Slice):
        return _expr_equal(a.operand, b.operand) and _expr_equal(a.hi, b.hi) and _expr_equal(a.lo, b.lo)
    if isinstance(a, PartSelect):
        return _expr_equal(a.operand, b.operand) and _expr_equal(a.offset, b.offset)
    if isinstance(a, BitSelect):
        return _expr_equal(a.operand, b.operand) and _expr_equal(a.index, b.index)
    if isinstance(a, Concat):
        return len(a.parts) == len(b.parts) and all(_expr_equal(x, y) for x, y in zip(a.parts, b.parts))
    if isinstance(a, Mux):
        return _expr_equal(a.cond, b.cond) and _expr_equal(a.true_expr, b.true_expr) and _expr_equal(a.false_expr, b.false_expr)
    if isinstance(a, MemRead):
        return a.mem is b.mem and _expr_equal(a.addr, b.addr)
    if isinstance(a, ArrayRead):
        return a.array is b.array and _expr_equal(a.addr, b.addr)
    if isinstance(a, GenVar):
        return a.name == b.name
    return False


def _derive_partselect_width(hi_expr: Expr, lo_expr: Expr) -> Optional[int]:
    """从动态 slice 的上下界推导静态宽度。"""
    # 情况 1: 都是常数
    if isinstance(hi_expr, Const) and isinstance(lo_expr, Const):
        return hi_expr.value - lo_expr.value + 1
    # 情况 2: hi = lo + n
    if isinstance(hi_expr, BinOp) and hi_expr.op == '+':
        if _expr_equal(hi_expr.lhs, lo_expr) and isinstance(hi_expr.rhs, Const):
            return hi_expr.rhs.value + 1
        if _expr_equal(hi_expr.rhs, lo_expr) and isinstance(hi_expr.lhs, Const):
            return hi_expr.lhs.value + 1
    return None


# ---------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------

class Signal:
    """硬件信号基类，支持位宽推导与运算符重载。"""

    def __init__(self, width: int = 1, name: str = "", signed: bool = False):
        self.width = width
        self.name = name
        self.signed = signed
        self._expr = Ref(self)
        self._driven_by: Optional[str] = None  # "comb" | "seq"
        self._parent_module: Optional["Module"] = None  # owning module

    def __hash__(self):
        return id(self)

    # ---- slicing ------------------------------------------------------
    def __getitem__(self, key):
        if isinstance(key, slice):
            hi = key.start if key.start is not None else self.width - 1
            lo = key.stop if key.stop is not None else 0
            # 动态 slice 支持
            if isinstance(hi, (Expr, Signal, GenVar)) or isinstance(lo, (Expr, Signal, GenVar)):
                hi_expr = _to_expr(hi)
                lo_expr = _to_expr(lo)
                width = _derive_partselect_width(hi_expr, lo_expr)
                if width is None:
                    raise ValueError(f"Cannot infer width from dynamic slice [{hi_expr} : {lo_expr}]")
                s = Signal(width=width)
                s._expr = PartSelect(_to_expr(self), lo_expr, width)
                return s
            s = Signal(width=hi - lo + 1)
            s._expr = Slice(_to_expr(self), hi, lo)
            return s
        elif isinstance(key, (GenVar, Expr, Signal)):
            s = Signal(width=1)
            s._expr = BitSelect(_to_expr(self), _to_expr(key))
            return s
        else:
            s = Signal(width=1)
            s._expr = Slice(_to_expr(self), key, key)
            return s

    def __setitem__(self, key, value):
        """支持 generate-for 中的位选赋值回退（如 y[i] <<= ...）。"""
        if isinstance(value, Signal) and getattr(value, '_written_by_ilshift', False):
            return
        if isinstance(key, (GenVar, Expr, int)):
            idx = _to_expr(key) if isinstance(key, (GenVar, Expr)) else key
            blocking = isinstance(self, (Wire, Output))
            stmt = IndexedAssign(self, idx, _to_expr(value), blocking)
            ctx = Context.current()
            if ctx and ctx.stmt_container is not None:
                ctx.stmt_container.append(stmt)
            elif ctx and ctx.module is not None:
                ctx.module._top_level.append(stmt)
            else:
                raise RuntimeError("Indexed assignment outside of any module or logic block")
        else:
            raise TypeError("Unsupported index type for assignment")

    # ---- assignment ---------------------------------------------------
    def __ilshift__(self, other):
        """非阻塞/连续赋值操作符: a <<= b"""
        expr = _to_expr(other)
        if isinstance(self._expr, BitSelect):
            blocking = isinstance(self._expr.operand.signal, (Wire, Output))
            stmt = IndexedAssign(self._expr.operand.signal, self._expr.index, expr, blocking)
            ctx = Context.current()
            if ctx and ctx.stmt_container is not None:
                ctx.stmt_container.append(stmt)
            elif ctx and ctx.module is not None:
                ctx.module._top_level.append(stmt)
            else:
                raise RuntimeError("Assignment outside of any module or logic block")
            self._written_by_ilshift = True
            return self

        if isinstance(self._expr, Slice) and self._expr.hi == self._expr.lo:
            base = self._expr.operand.signal
            idx = Const(self._expr.lo, width=max(self._expr.lo.bit_length(), 1))
            blocking = isinstance(base, (Wire, Output))
            stmt = IndexedAssign(base, idx, expr, blocking)
            ctx = Context.current()
            if ctx and ctx.stmt_container is not None:
                ctx.stmt_container.append(stmt)
            elif ctx and ctx.module is not None:
                ctx.module._top_level.append(stmt)
            else:
                raise RuntimeError("Assignment outside of any module or logic block")
            self._written_by_ilshift = True
            return self

        # PartSelect or general Slice as assignment target
        if isinstance(self._expr, (PartSelect, Slice)):
            blocking = isinstance(self, (Wire, Output))
            stmt = Assign(target=self._expr, value=expr, blocking=blocking)
            ctx = Context.current()
            if ctx and ctx.stmt_container is not None:
                ctx.stmt_container.append(stmt)
            elif ctx and ctx.module is not None:
                ctx.module._top_level.append(stmt)
            else:
                raise RuntimeError("Assignment outside of any module or logic block")
            self._driven_by = "comb" if blocking else "seq"
            self._written_by_ilshift = True
            return self

        blocking = isinstance(self, (Wire, Output))
        stmt = Assign(target=self, value=expr, blocking=blocking)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Assignment outside of any module or logic block")
        self._driven_by = "comb" if blocking else "seq"
        self._written_by_ilshift = True
        return self

    # ---- arithmetic ---------------------------------------------------
    def __add__(self, other):
        return _make_binop("+", self, other)

    def __sub__(self, other):
        return _make_binop("-", self, other)

    def __mul__(self, other):
        # 乘法结果位宽 = 两个操作数位宽之和
        aw = self.width
        bw = other.width if isinstance(other, (Signal, Expr)) else _to_expr(other).width
        return _make_binop("*", self, other, width=aw + bw)

    def __and__(self, other):
        return _make_binop("&", self, other)

    def __or__(self, other):
        return _make_binop("|", self, other)

    def __xor__(self, other):
        return _make_binop("^", self, other)

    def __lshift__(self, other):
        return _make_binop("<<", self, other, width=self.width)

    def __rshift__(self, other):
        return _make_binop(">>", self, other, width=self.width)

    def __mod__(self, other):
        return _make_binop("%", self, other)

    def __rmod__(self, other):
        return _make_binop("%", other, self)

    def __invert__(self):
        return _make_unop("~", self)

    # ---- comparison ---------------------------------------------------
    def __eq__(self, other):
        return _make_binop("==", self, other, width=1)

    def __ne__(self, other):
        return _make_binop("!=", self, other, width=1)

    def __lt__(self, other):
        return _make_binop("<", self, other, width=1)

    def __le__(self, other):
        return _make_binop("<=", self, other, width=1)

    def __gt__(self, other):
        return _make_binop(">", self, other, width=1)

    def __ge__(self, other):
        return _make_binop(">=", self, other, width=1)

    # ---- reverse ops --------------------------------------------------
    def __radd__(self, other):
        return _make_binop("+", other, self)

    def __rsub__(self, other):
        return _make_binop("-", other, self)

    def __rmul__(self, other):
        return _make_binop("*", other, self, width=self.width + _to_expr(other).width)

    def __rand__(self, other):
        return _make_binop("&", other, self)

    def __ror__(self, other):
        return _make_binop("|", other, self)

    def __rxor__(self, other):
        return _make_binop("^", other, self)

    def __rlshift__(self, other):
        return _make_binop("<<", other, self, width=_to_expr(other).width)

    def __rrshift__(self, other):
        return _make_binop(">>", other, self, width=_to_expr(other).width)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.width})<{self.name or 'anonymous'}>"


class Input(Signal):
    """模块输入端口。"""
    pass


class Output(Signal):
    """模块输出端口。"""
    pass


class Wire(Signal):
    """组合逻辑中间信号。"""
    pass


class Reg(Signal):
    """时序逻辑寄存器。"""
    pass



class Vector:
    """一维信号向量，用于减少重复声明。"""

    def __init__(self, width: int, size: int, name: str = "", vtype=None):
        self.width = width
        self.size = size
        self.name = name
        self._vtype = vtype or Wire
        self._signals: List[Signal] = []
        for i in range(size):
            sig = self._vtype(width, f"{name}_{i}")
            sig._vector_parent = self
            sig._vector_index = i
            self._signals.append(sig)

    def __getitem__(self, idx):
        return self._signals[idx]

    def __setitem__(self, idx, val):
        self._signals[idx] = val

    def __iter__(self):
        return iter(self._signals)

    def __len__(self):
        return self.size

    def __reversed__(self):
        return reversed(self._signals)

    def __ilshift__(self, other):
        """批量赋值：支持 Vector <<= Vector 或 Vector <<= list/tuple。"""
        if isinstance(other, Vector):
            if self.size != other.size:
                raise ValueError(f"Vector size mismatch: {self.size} vs {other.size}")
            for i in range(self.size):
                self[i] <<= other[i]
        elif isinstance(other, (list, tuple)):
            if len(other) != self.size:
                raise ValueError(f"Vector size mismatch: {self.size} vs {len(other)}")
            for i, val in enumerate(other):
                self[i] <<= val
        else:
            raise TypeError(f"Cannot <<= {type(other).__name__} into Vector")
        return self

    def __repr__(self):
        return f"Vector({self.width}x{self.size})<{self.name}>"

# ---------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------

class Parameter:
    """硬件参数，用于生成 #(parameter WIDTH = 8) 。"""

    def __init__(self, value: Any, name: str = ""):
        self.value = value
        self.name = name
        self._expr = Ref(Signal(width=1, name=name))

    def __add__(self, other):
        return _param_binop("+", self, other)

    def __sub__(self, other):
        return _param_binop("-", self, other)

    def __mul__(self, other):
        return _param_binop("*", self, other)

    def __radd__(self, other):
        return _param_binop("+", other, self)

    def __rsub__(self, other):
        return _param_binop("-", other, self)

    def __rmul__(self, other):
        return _param_binop("*", other, self)

    def __eq__(self, other):
        return _param_binop("==", self, other)

    def __ne__(self, other):
        return _param_binop("!=", self, other)

    def __lt__(self, other):
        return _param_binop("<", self, other)

    def __le__(self, other):
        return _param_binop("<=", self, other)

    def __gt__(self, other):
        return _param_binop(">", self, other)

    def __ge__(self, other):
        return _param_binop(">=", self, other)

    def __repr__(self):
        return f"Parameter({self.value})"


class LocalParam(Parameter):
    """硬件局部参数，用于生成 localparam WIDTH = 8;"""
    pass


# ---------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------

class Context:
    """全局上下文栈，用于追踪当前正在构建的模块与逻辑块。"""

    _local = threading.local()

    def __init__(
        self,
        module: Optional["Module"] = None,
        stmt_container: Optional[List[Any]] = None,
    ):
        self.module = module
        self.stmt_container = stmt_container

    @classmethod
    def current(cls) -> Optional["Context"]:
        stack = getattr(cls._local, "stack", [])
        return stack[-1] if stack else None

    @classmethod
    def push(cls, ctx: "Context"):
        if not hasattr(cls._local, "stack"):
            cls._local.stack = []
        cls._local.stack.append(ctx)

    @classmethod
    def pop(cls):
        cls._local.stack.pop()


# ---------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------

class ModuleMeta(type):
    """在 Module 子类 __init__ 期间自动 push/pop Context(module=self)，
    避免在父模块的 comb / ForGen 作用域内实例化子模块时，子模块内部语句泄漏到父模块。"""

    def __call__(cls, *args, **kwargs):
        instance = cls.__new__(cls)
        if isinstance(instance, cls):
            Context.push(Context(module=instance))
            try:
                instance.__init__(*args, **kwargs)
            finally:
                Context.pop()
        return instance


class Array:
    """二维信号数组，生成 Verilog unpacked array：logic [width-1:0] name [0:depth-1]。"""

    def __init__(self, width: int, depth: int, name: str = "", vtype=None):
        self.width = width
        self.depth = depth
        self.name = name
        self._vtype = vtype or Wire

    def __getitem__(self, idx):
        idx_expr = _to_expr(idx) if isinstance(idx, int) else _to_expr(idx)
        return ArrayProxy(self.name, idx_expr, self.width)

    def __setitem__(self, idx, value):
        idx_expr = _to_expr(idx) if isinstance(idx, int) else _to_expr(idx)
        if isinstance(value, ArrayProxy) and value._written:
            return
        stmt = ArrayWrite(self.name, idx_expr, _to_expr(value))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Array write outside of any module or logic block")

    def __iter__(self):
        for i in range(self.depth):
            yield self[i]

    def __len__(self):
        return self.depth

    def __repr__(self):
        return f"Array({self.width}x{self.depth})<{self.name}>"


class Module(metaclass=ModuleMeta):
    """所有硬件模块的基类。"""

    STRICT: bool = False  # 启用严格端口连接检查

    def __init__(self, name: Optional[str] = None, param_bindings: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__
        self._type_name = self.__class__.__name__
        self._inputs: Dict[str, Input] = {}
        self._outputs: Dict[str, Output] = {}
        self._wires: Dict[str, Wire] = {}
        self._regs: Dict[str, Reg] = {}
        self._params: Dict[str, Parameter] = {}
        self._memories: Dict[str, Memory] = {}
        self._arrays: Dict[str, Array] = {}
        self._submodules: List[Tuple[str, Module]] = []
        self._comb_blocks: List[List[Any]] = []
        self._seq_blocks: List[Tuple[Signal, Optional[Signal], List[Any]]] = []
        self._top_level: List[Any] = []
        self._param_bindings: Dict[str, Any] = dict(param_bindings) if param_bindings else {}
        self._module_comments: List[str] = []
        self._module_assertions: List[Tuple[str, str]] = []
        self._module_suggestions: List[str] = []
        self._parent: Optional["Module"] = None

    def add_comment(self, text: str):
        """向模块添加顶层注释，生成 Verilog 时会被放在模块头部。"""
        self._module_comments.append(text)

    def add_assertion(self, name: str, expr: str):
        """向模块添加 SVA 断言 (name, expression_string)。"""
        self._module_assertions.append((name, expr))

    def add_suggestions(self, suggestions: List[str]):
        """向模块添加优化建议，生成 Verilog 时会被转为注释。"""
        self._module_suggestions.extend(suggestions)

    def lint(self, rules: Optional[List[str]] = None) -> List[str]:
        """检查设计规则违例（严格端口连接模式 + 流水线/握手协议检查）。

        参数 ``rules`` 可选，限制只检查指定规则。默认检查全部规则。

        返回违例描述列表。空列表表示没有违例。
        """
        violations: List[str] = []
        enabled = set(rules) if rules else None

        def _rule_on(name: str) -> bool:
            return enabled is None or name in enabled

        def _find_refs(expr) -> List[Ref]:
            refs: List[Ref] = []
            if expr is None:
                return refs
            if isinstance(expr, Ref):
                refs.append(expr)
            elif isinstance(expr, (Slice, BitSelect)):
                refs.extend(_find_refs(expr.operand))
            elif hasattr(expr, "operands"):
                for op in expr.operands:
                    refs.extend(_find_refs(op))
            elif hasattr(expr, "lhs"):
                refs.extend(_find_refs(expr.lhs))
                refs.extend(_find_refs(expr.rhs))
            elif hasattr(expr, "operand"):
                refs.extend(_find_refs(expr.operand))
            elif hasattr(expr, "true_expr"):
                refs.extend(_find_refs(expr.true_expr))
                refs.extend(_find_refs(expr.false_expr))
                refs.extend(_find_refs(expr.cond))
            return refs

        def _extract_target_sig(stmt):
            if isinstance(stmt.target, Signal):
                return stmt.target
            if isinstance(stmt.target, Ref):
                return stmt.target.signal
            if isinstance(stmt.target, (Slice, BitSelect)):
                t = stmt.target
                while isinstance(t, (Slice, BitSelect)) and hasattr(t, "operand"):
                    t = t.operand
                if isinstance(t, Ref):
                    return t.signal
            return None

        def _owner_name(mod):
            if mod._parent is not None:
                for inst_name, sm in mod._parent._submodules:
                    if sm is mod:
                        return inst_name
            return mod.name

        def _collect_stmt_assigns(stmts, target_dict: Dict):
            """收集语句中的赋值，按目标信号归类。"""
            for stmt in stmts:
                if isinstance(stmt, Assign):
                    ts = _extract_target_sig(stmt)
                    if ts is not None:
                        target_dict.setdefault(id(ts), []).append(stmt)
                elif isinstance(stmt, IfNode):
                    _collect_stmt_assigns(stmt.then_body, target_dict)
                    _collect_stmt_assigns(stmt.else_body, target_dict)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _collect_stmt_assigns(body, target_dict)
                    _collect_stmt_assigns(stmt.default_body, target_dict)

        all_stmts = list(self._top_level)
        for body in self._comb_blocks:
            all_stmts.extend(body)
        for _, _, _, _, body in self._seq_blocks:
            all_stmts.extend(body)

        for stmt in all_stmts:
            if not isinstance(stmt, Assign):
                continue

            target_sig = _extract_target_sig(stmt)
            if target_sig and target_sig._parent_module is not None and target_sig._parent_module is not self:
                if not isinstance(target_sig, Input):
                    owner = _owner_name(target_sig._parent_module)
                    violations.append(
                        f"[HierarchicalWrite] '{owner}.{target_sig.name}' ({type(target_sig).__name__}) "
                        f"is driven from '{self.name}'. Only submodule INPUT ports may be driven from parent."
                    )

            refs = _find_refs(stmt.value)
            for ref in refs:
                sig = ref.signal
                if sig._parent_module is not None and sig._parent_module is not self:
                    owner = _owner_name(sig._parent_module)
                    if not isinstance(sig, (Input, Output)):
                        violations.append(
                            f"[HierarchicalRead] '{owner}.{sig.name}' ({type(sig).__name__}) is read from '{self.name}'. "
                            f"Only submodule ports (Input/Output) may be accessed from parent."
                        )

        # ================================================================
        # Rule: comb_reg_assign — Reg 信号在 @comb 块中被赋值
        # ================================================================
        if _rule_on("comb_reg_assign") and self._comb_blocks:
            comb_assigns: Dict[int, List[Assign]] = {}
            for body in self._comb_blocks:
                _collect_stmt_assigns(body, comb_assigns)

            for sig_id, assigns in comb_assigns.items():
                # 找到对应的 Reg 信号
                reg_sig = self._regs.get(
                    next((s.name for s in self._regs.values() if id(s) == sig_id), None)
                )
                if reg_sig is not None:
                    violations.append(
                        f"[CombRegAssign] Reg signal '{reg_sig.name}' is assigned in @comb block. "
                        f"It will synthesize as a latch or wire, not a flip-flop. "
                        f"Move the assignment to @seq if a registered output is intended."
                    )

        # ================================================================
        # Rule: seq_output_assign — Output 在 @seq 块中被直接赋值
        # ================================================================
        if _rule_on("seq_output_assign") and self._seq_blocks:
            seq_assigns: Dict[int, List[Assign]] = {}
            for _, _, _, _, body in self._seq_blocks:
                _collect_stmt_assigns(body, seq_assigns)

            for sig_id, assigns in seq_assigns.items():
                out_sig = next(
                    (s for s in self._outputs.values() if id(s) == sig_id), None
                )
                if out_sig is not None:
                    violations.append(
                        f"[SeqOutputAssign] Output '{out_sig.name}' is assigned directly in @seq block. "
                        f"The Python Simulator cannot track Output as sequential state; "
                        f"it will always read 0. Use an internal Reg (e.g., '{out_sig.name}_reg') "
                        f"in @seq and drive the Output via @comb instead."
                    )

        # ================================================================
        # Rule: unregistered_output — 输出端口仅有组合逻辑驱动
        # ================================================================
        if _rule_on("unregistered_output") and (self._comb_blocks or self._seq_blocks):
            # 收集 @seq 块中驱动的信号
            seq_driven: Set[int] = set()
            seq_assigns: Dict[int, List[Assign]] = {}
            for _, _, _, _, body in self._seq_blocks:
                _collect_stmt_assigns(body, seq_assigns)
                for assigns in seq_assigns.values():
                    for a in assigns:
                        ts = _extract_target_sig(a)
                        if ts is not None:
                            seq_driven.add(id(ts))

            # 收集 @comb 块中驱动的信号
            comb_driven: Set[int] = set()
            comb_assigns_map: Dict[int, List[Assign]] = {}
            for body in self._comb_blocks:
                _collect_stmt_assigns(body, comb_assigns_map)
                for assigns in comb_assigns_map.values():
                    for a in assigns:
                        ts = _extract_target_sig(a)
                        if ts is not None:
                            comb_driven.add(id(ts))

            # 构建顶层 assign 的驱动关系: target_id -> value_expr
            top_assigns: Dict[int, Expr] = {}
            for stmt in self._top_level:
                if isinstance(stmt, Assign):
                    ts = _extract_target_sig(stmt)
                    if ts is not None:
                        top_assigns[id(ts)] = stmt.value

            def _sig_is_seq_driven(sig_id: int, visited: Set[int]) -> bool:
                """递归判断一个信号是否（直接或间接）被 @seq 驱动。"""
                if sig_id in visited:
                    return False
                visited.add(sig_id)
                if sig_id in seq_driven:
                    return True
                # 如果该信号被 @comb 块中的 assign 驱动，追踪其驱动源
                if sig_id in comb_assigns_map:
                    for a in comb_assigns_map[sig_id]:
                        src_refs = _find_refs(a.value)
                        for ref in src_refs:
                            if _sig_is_seq_driven(id(ref.signal), visited):
                                return True
                # 如果该信号被顶层 assign 驱动，追踪其驱动源
                if sig_id in top_assigns:
                    src_refs = _find_refs(top_assigns[sig_id])
                    for ref in src_refs:
                        if _sig_is_seq_driven(id(ref.signal), visited):
                            return True
                return False

            def _sig_is_pure_comb(sig_id: int, visited: Set[int]) -> bool:
                """递归判断一个信号是否（仅）被组合逻辑驱动。"""
                if sig_id in visited:
                    return False
                visited.add(sig_id)
                if sig_id in seq_driven:
                    return False
                if sig_id in comb_driven:
                    return True
                if sig_id in top_assigns:
                    src_refs = _find_refs(top_assigns[sig_id])
                    if not src_refs:
                        return True
                    return all(
                        _sig_is_pure_comb(id(ref.signal), visited)
                        for ref in src_refs
                    )
                return False

            # 对每个输出端口，追踪其驱动源
            for out_name, out_sig in self._outputs.items():
                # 跳过 ready 信号（按协议应为组合逻辑）
                if "ready" in out_name.lower():
                    continue
                if _sig_is_seq_driven(id(out_sig), set()):
                    continue
                if _sig_is_pure_comb(id(out_sig), set()):
                    violations.append(
                        f"[UnregisteredOutput] Output '{out_name}' is driven purely by combinational logic. "
                        f"In a clocked module, outputs should normally be registered."
                    )

        # ================================================================
        # Rule: valid_ready_protocol — valid/ready 握手协议违例
        # ================================================================
        if _rule_on("valid_ready_protocol") and (self._comb_blocks or self._seq_blocks):
            self._lint_valid_ready(violations, seq_driven, comb_driven)

        return violations

    def _lint_valid_ready(self, violations: List[str], seq_driven: Set[int], comb_driven: Set[int]):
        """检查 valid/ready 握手协议的正确性。

        规则：
        1. valid 输出信号应被时序逻辑驱动（不应纯组合输出）
        2. ready 输出信号应被组合逻辑驱动（不应被时序逻辑驱动）
        3. 若模块有 valid 输入和时钟，数据输出应被时序逻辑驱动
        """
        def _find_refs(expr) -> List[Ref]:
            refs: List[Ref] = []
            if expr is None:
                return refs
            if isinstance(expr, Ref):
                refs.append(expr)
            elif isinstance(expr, (Slice, BitSelect)):
                refs.extend(_find_refs(expr.operand))
            elif hasattr(expr, "operands"):
                for op in expr.operands:
                    refs.extend(_find_refs(op))
            elif hasattr(expr, "lhs"):
                refs.extend(_find_refs(expr.lhs))
                refs.extend(_find_refs(expr.rhs))
            elif hasattr(expr, "operand"):
                refs.extend(_find_refs(expr.operand))
            elif hasattr(expr, "true_expr"):
                refs.extend(_find_refs(expr.true_expr))
                refs.extend(_find_refs(expr.false_expr))
                refs.extend(_find_refs(expr.cond))
            return refs

        def _extract_target(stmt):
            if isinstance(stmt.target, Signal):
                return stmt.target
            if isinstance(stmt.target, Ref):
                return stmt.target.signal
            if isinstance(stmt.target, (Slice, BitSelect)):
                t = stmt.target
                while isinstance(t, (Slice, BitSelect)) and hasattr(t, "operand"):
                    t = t.operand
                if isinstance(t, Ref):
                    return t.signal
            return None

        # 构建顶层 assign 的驱动关系
        top_assigns: Dict[int, Expr] = {}
        for stmt in self._top_level:
            if isinstance(stmt, Assign):
                ts = _extract_target(stmt)
                if ts is not None:
                    top_assigns[id(ts)] = stmt.value

        def _is_seq_driven(sig_id: int, visited: Set[int]) -> bool:
            if sig_id in visited:
                return False
            visited.add(sig_id)
            if sig_id in seq_driven:
                return True
            if sig_id in top_assigns:
                for ref in _find_refs(top_assigns[sig_id]):
                    if _is_seq_driven(id(ref.signal), visited):
                        return True
            return False

        def _is_pure_comb(sig_id: int, visited: Set[int]) -> bool:
            if sig_id in visited:
                return False
            visited.add(sig_id)
            if sig_id in seq_driven:
                return False
            if sig_id in comb_driven:
                return True
            if sig_id in top_assigns:
                src_refs = _find_refs(top_assigns[sig_id])
                if not src_refs:
                    return True
                return all(_is_pure_comb(id(ref.signal), visited) for ref in src_refs)
            return False

        # 识别 valid/ready 信号
        valid_outputs: List[Signal] = []
        ready_outputs: List[Signal] = []
        valid_inputs: List[Signal] = []
        ready_inputs: List[Signal] = []

        for name, sig in self._outputs.items():
            if "valid" in name.lower():
                valid_outputs.append(sig)
            if "ready" in name.lower():
                ready_outputs.append(sig)

        for name, sig in self._inputs.items():
            if "valid" in name.lower():
                valid_inputs.append(sig)
            if "ready" in name.lower():
                ready_inputs.append(sig)

        # 规则 1: valid 输出应被时序逻辑驱动
        for sig in valid_outputs:
            if _is_pure_comb(id(sig), set()):
                violations.append(
                    f"[ValidReadyProtocol] Output '{sig.name}' (valid) is driven purely by combinational logic. "
                    f"Valid outputs should be registered to avoid glitch propagation."
                )

        # 规则 2: ready 输出应被组合逻辑驱动（反向压力信号）
        for sig in ready_outputs:
            if _is_seq_driven(id(sig), set()) and not _is_pure_comb(id(sig), set()):
                violations.append(
                    f"[ValidReadyProtocol] Output '{sig.name}' (ready) is driven purely by sequential logic. "
                    f"Ready outputs should be combinational for proper back-pressure propagation."
                )

        # 规则 3: 若有 valid 输入和时钟，检查数据输出是否被寄存器驱动
        if valid_inputs and not self._seq_blocks:
            for name, sig in self._outputs.items():
                if "valid" in name.lower() or "ready" in name.lower():
                    continue
                if _is_pure_comb(id(sig), set()):
                    violations.append(
                        f"[ValidReadyProtocol] Module has valid input but output '{sig.name}' "
                        f"is not registered. Data outputs in a clocked pipeline should be registered."
                    )

    def __setattr__(self, key: str, value: Any):
        if isinstance(value, Input):
            value.name = value.name or key
            value._parent_module = self
            object.__setattr__(self, key, value)
            self._inputs[key] = value
        elif isinstance(value, Output):
            value.name = value.name or key
            value._parent_module = self
            object.__setattr__(self, key, value)
            self._outputs[key] = value
        elif isinstance(value, Wire):
            value.name = value.name or key
            value._parent_module = self
            object.__setattr__(self, key, value)
            self._wires[key] = value
        elif isinstance(value, Reg):
            value.name = value.name or key
            value._parent_module = self
            object.__setattr__(self, key, value)
            self._regs[key] = value
        elif isinstance(value, Parameter):
            value.name = value.name or key
            object.__setattr__(self, key, value)
            self._params[key] = value
        elif isinstance(value, LocalParam):
            value.name = value.name or key
            object.__setattr__(self, key, value)
            self._params[key] = value
        elif isinstance(value, Module):
            object.__setattr__(self, key, value)
            self._submodules.append((key, value))
            object.__setattr__(value, '_parent', self)
        elif isinstance(value, Memory):
            value.name = value.name or key
            object.__setattr__(self, key, value)
            self._memories[key] = value
        elif isinstance(value, Vector):
            value.name = value.name or key
            object.__setattr__(self, key, value)
            for sig in value:
                if isinstance(sig, Input):
                    self._inputs[sig.name] = sig
                elif isinstance(sig, Output):
                    self._outputs[sig.name] = sig
                elif isinstance(sig, Wire):
                    self._wires[sig.name] = sig
                elif isinstance(sig, Reg):
                    self._regs[sig.name] = sig
        elif isinstance(value, Array):
            value.name = value.name or key
            object.__setattr__(self, key, value)
            self._arrays[key] = value
        elif isinstance(value, (list, tuple)):
            if value and all(isinstance(v, Signal) for v in value):
                for sig in value:
                    if isinstance(sig, Input):
                        self._inputs[sig.name] = sig
                    elif isinstance(sig, Output):
                        self._outputs[sig.name] = sig
                    elif isinstance(sig, Wire):
                        self._wires[sig.name] = sig
                    elif isinstance(sig, Reg):
                        self._regs[sig.name] = sig
            object.__setattr__(self, key, value)
        else:
            object.__setattr__(self, key, value)

    # ---- decorators ---------------------------------------------------
    def comb(self, func: Callable) -> Callable:
        """组合逻辑块装饰器。

        示例:
            @self.comb
            def my_logic():
                sum_wire <<= a + b
        """
        body: List[Any] = []
        self._comb_blocks.append(body)

        def wrapper(*args, **kwargs):
            Context.push(Context(module=self, stmt_container=body))
            try:
                func(*args, **kwargs)
            finally:
                Context.pop()

        wrapper()
        return wrapper

    def seq(self, clock: Signal, reset: Optional[Signal] = None, reset_async: bool = False, reset_active_low: bool = False):
        """时序逻辑块装饰器。

        示例:
            @self.seq(clk, rst)
            def my_seq():
                counter <= counter + 1
        """

        def decorator(func: Callable) -> Callable:
            body: List[Any] = []
            self._seq_blocks.append((clock, reset, reset_async, reset_active_low, body))

            def wrapper(*args, **kwargs):
                Context.push(Context(module=self, stmt_container=body))
                try:
                    func(*args, **kwargs)
                finally:
                    Context.pop()

            wrapper()
            return wrapper

        return decorator

    def instantiate(
        self,
        submodule: "Module",
        name: str,
        params: Optional[Dict[str, Any]] = None,
        port_map: Optional[Dict[str, Union[Signal, Expr]]] = None,
    ):
        """显式实例化子模块（亦可直接通过 self.sub = SubModule() 隐式实例化）。"""
        params = params or {}
        port_map = port_map or {}
        port_map = {k: _to_expr(v) for k, v in port_map.items()}
        inst = SubmoduleInst(name, submodule, params, port_map)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(inst)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(inst)
        else:
            self._top_level.append(inst)

    def add_memory(self, mem: Memory, name: str = "") -> Memory:
        """注册一个存储器到当前模块。"""
        mem.name = name or mem.name or f"mem_{len(self._memories)}"
        self._memories[mem.name] = mem
        setattr(self, mem.name, mem)
        return mem

    # -----------------------------------------------------------------
    # Convenience constructors
    # -----------------------------------------------------------------
    def input(self, width: int, name: str = ""):
        """创建并注册一个 Input 信号到当前模块。"""
        sig = Input(width, name)
        setattr(self, sig.name, sig)
        return sig

    def output(self, width: int, name: str = ""):
        """创建并注册一个 Output 信号到当前模块。"""
        sig = Output(width, name)
        setattr(self, sig.name, sig)
        return sig

    def reg(self, width: int, name: str = ""):
        """创建并注册一个 Reg 信号到当前模块。"""
        sig = Reg(width, name)
        setattr(self, sig.name, sig)
        return sig

    def wire(self, width: int, name: str = ""):
        """创建并注册一个 Wire 信号到当前模块。"""
        sig = Wire(width, name)
        setattr(self, sig.name, sig)
        return sig

    def parameter(self, value: Any, name: str = ""):
        """创建并注册一个 Parameter 到当前模块。"""
        p = Parameter(value, name)
        setattr(self, p.name, p)
        return p

    def add_param(self, name: str, value: Any):
        """创建并注册一个可配置的 parameter 到当前模块。

        示例:
            self.add_param("WIDTH", 32)
            self.add_param("DEPTH", 16)
        """
        p = Parameter(value, name)
        setattr(self, name, p)
        return p

    def add_localparam(self, name: str, value: Any):
        """创建并注册一个 localparam 到当前模块。

        示例:
            self.add_localparam("ADDR_WIDTH", 8)
        """
        p = LocalParam(value, name)
        setattr(self, name, p)
        return p

    def __repr__(self):
        return f"Module({self.name})"


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _make_binop(op: str, lhs: Any, rhs: Any, width: Optional[int] = None) -> Signal:
    le = _to_expr(lhs)
    re = _to_expr(rhs)
    w = width if width is not None else max(le.width, re.width)
    s = Signal(width=w)
    s._expr = BinOp(op, le, re, w)
    return s


def _make_unop(op: str, operand: Any) -> Signal:
    e = _to_expr(operand)
    s = Signal(width=e.width)
    s._expr = UnaryOp(op, e, e.width)
    return s


def _param_binop(op: str, lhs: Any, rhs: Any) -> Signal:
    """Parameter 参与算术运算时生成 Expr（行为类似 Signal）。"""
    le = _to_expr(lhs)
    re = _to_expr(rhs)
    w = max(le.width, re.width) + 1
    s = Signal(width=w)
    s._expr = BinOp(op, le, re, w)
    return s

# ---------------------------------------------------------------------
# GenVar substitution helpers (used by both simulation and flattening)
# ---------------------------------------------------------------------

def _subst_genvar_in_expr(expr: Any, var_name: str, value: int) -> Any:
    if isinstance(expr, GenVar) and expr.name == var_name:
        return Const(value, width=max(value.bit_length(), 1))
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
        return Assign(_subst_genvar_in_expr(stmt.target, var_name, value),
                      _subst_genvar_in_expr(stmt.value, var_name, value), stmt.blocking)
    if isinstance(stmt, IndexedAssign):
        return IndexedAssign(stmt.target_signal,
                             _subst_genvar_in_expr(stmt.index, var_name, value),
                             _subst_genvar_in_expr(stmt.value, var_name, value), stmt.blocking)
    if isinstance(stmt, ArrayWrite):
        return ArrayWrite(stmt.array_name,
                          _subst_genvar_in_expr(stmt.index, var_name, value),
                          _subst_genvar_in_expr(stmt.value, var_name, value),
                          stmt.blocking)
    if isinstance(stmt, MemWrite):
        return MemWrite(stmt.mem_name,
                        _subst_genvar_in_expr(stmt.addr, var_name, value),
                        _subst_genvar_in_expr(stmt.value, var_name, value))
    if isinstance(stmt, IfNode):
        n = IfNode(_subst_genvar_in_expr(stmt.cond, var_name, value))
        n.then_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.then_body]
        n.else_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.else_body]
        return n
    if isinstance(stmt, SwitchNode):
        n = SwitchNode(_subst_genvar_in_expr(stmt.expr, var_name, value))
        n.cases = [(_subst_genvar_in_expr(v, var_name, value),
                    [_subst_genvar_in_stmt(s, var_name, value) for s in b]) for v, b in stmt.cases]
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
    if isinstance(stmt, SubmoduleInst):
        new_port_map = {}
        for k, v in stmt.port_map.items():
            expr = _to_expr(v) if isinstance(v, Signal) else v
            new_port_map[k] = _subst_genvar_in_expr(expr, var_name, value)
        new_params = {}
        for k, v in stmt.params.items():
            expr = _to_expr(v) if isinstance(v, (Signal, GenVar)) else v
            new_val = _subst_genvar_in_expr(expr, var_name, value)
            if isinstance(new_val, Const):
                new_params[k] = int(new_val.value)
            elif isinstance(new_val, int):
                new_params[k] = new_val
            else:
                new_params[k] = new_val
        new_name = f"{stmt.name}_gen{value}"
        return SubmoduleInst(new_name, stmt.module, new_params, new_port_map)
    if isinstance(stmt, Comment):
        return Comment(stmt.text)
    return stmt


# ---------------------------------------------------------------------
# Module flattening
# ---------------------------------------------------------------------

def flatten_module(module: "Module") -> "Module":
    """Return a flattened copy of *module*.

    - Unrolls all ``ForGenNode`` loops.
    - Recursively inlines all ``SubmoduleInst`` instances.
    - Internal signals of submodules are renamed with an instance prefix.
    - Port connections become plain ``Assign`` statements.
    """
    import copy
    flat = Module(module.name)

    # Copy top-level signals directly (no rename needed)
    for name, sig in module._inputs.items():
        flat._inputs[name] = sig
        object.__setattr__(flat, name, sig)
    for name, sig in module._outputs.items():
        flat._outputs[name] = sig
        object.__setattr__(flat, name, sig)
    for name, sig in module._wires.items():
        flat._wires[name] = sig
        object.__setattr__(flat, name, sig)
    for name, sig in module._regs.items():
        flat._regs[name] = sig
        object.__setattr__(flat, name, sig)
    for name, param in module._params.items():
        flat._params[name] = param
        object.__setattr__(flat, name, param)
    for name, mem in module._memories.items():
        flat._memories[name] = mem
        object.__setattr__(flat, name, mem)
    for name, arr in module._arrays.items():
        flat._arrays[name] = arr
        object.__setattr__(flat, name, arr)

    def _rename_expr(expr, mapping, mem_rename=None, arr_rename=None):
        mem_rename = mem_rename or {}
        arr_rename = arr_rename or {}
        if isinstance(expr, Signal):
            new_sig = mapping.get(expr)
            return new_sig if new_sig is not None else expr
        if isinstance(expr, Ref):
            new_sig = mapping.get(expr.signal)
            if new_sig is not None:
                return Ref(new_sig)
            return expr
        if isinstance(expr, BinOp):
            return BinOp(expr.op, _rename_expr(expr.lhs, mapping, mem_rename, arr_rename), _rename_expr(expr.rhs, mapping, mem_rename, arr_rename), expr.width)
        if isinstance(expr, UnaryOp):
            return UnaryOp(expr.op, _rename_expr(expr.operand, mapping, mem_rename, arr_rename), expr.width)
        if isinstance(expr, Slice):
            return Slice(_rename_expr(expr.operand, mapping, mem_rename, arr_rename), expr.hi, expr.lo)
        if isinstance(expr, PartSelect):
            return PartSelect(_rename_expr(expr.operand, mapping, mem_rename, arr_rename), _rename_expr(expr.offset, mapping, mem_rename, arr_rename), expr.width)
        if isinstance(expr, BitSelect):
            return BitSelect(_rename_expr(expr.operand, mapping, mem_rename, arr_rename), _rename_expr(expr.index, mapping, mem_rename, arr_rename))
        if isinstance(expr, Concat):
            return Concat([_rename_expr(op, mapping, mem_rename, arr_rename) for op in expr.operands], expr.width)
        if isinstance(expr, Mux):
            return Mux(_rename_expr(expr.cond, mapping, mem_rename, arr_rename), _rename_expr(expr.true_expr, mapping, mem_rename, arr_rename), _rename_expr(expr.false_expr, mapping, mem_rename, arr_rename), expr.width)
        if isinstance(expr, MemRead):
            return MemRead(mem_rename.get(expr.mem_name, expr.mem_name), _rename_expr(expr.addr, mapping, mem_rename, arr_rename), expr.width)
        if isinstance(expr, ArrayRead):
            return ArrayRead(arr_rename.get(expr.array_name, expr.array_name), _rename_expr(expr.index, mapping, mem_rename, arr_rename), expr.width)
        return expr

    def _rename_stmt(stmt, mapping, mem_rename, arr_rename):
        if isinstance(stmt, Assign):
            new_target = mapping.get(stmt.target, stmt.target) if isinstance(stmt.target, Signal) else _rename_expr(stmt.target, mapping, mem_rename, arr_rename)
            return Assign(new_target, _rename_expr(stmt.value, mapping, mem_rename, arr_rename), stmt.blocking)
        if isinstance(stmt, IndexedAssign):
            ts = mapping.get(stmt.target_signal, stmt.target_signal)
            return IndexedAssign(ts, _rename_expr(stmt.index, mapping, mem_rename, arr_rename), _rename_expr(stmt.value, mapping, mem_rename, arr_rename), stmt.blocking)
        if isinstance(stmt, ArrayWrite):
            return ArrayWrite(arr_rename.get(stmt.array_name, stmt.array_name), _rename_expr(stmt.index, mapping, mem_rename, arr_rename), _rename_expr(stmt.value, mapping, mem_rename, arr_rename), stmt.blocking)
        if isinstance(stmt, MemWrite):
            return MemWrite(mem_rename.get(stmt.mem_name, stmt.mem_name), _rename_expr(stmt.addr, mapping, mem_rename, arr_rename), _rename_expr(stmt.value, mapping, mem_rename, arr_rename))
        if isinstance(stmt, IfNode):
            n = IfNode(_rename_expr(stmt.cond, mapping, mem_rename, arr_rename))
            n.then_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.then_body]
            n.else_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.else_body]
            return n
        if isinstance(stmt, SwitchNode):
            n = SwitchNode(_rename_expr(stmt.expr, mapping, mem_rename, arr_rename))
            n.cases = [(_rename_expr(v, mapping, mem_rename, arr_rename), [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in b]) for v, b in stmt.cases]
            n.default_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.default_body]
            return n
        if isinstance(stmt, ForGenNode):
            n = ForGenNode(stmt.var_name, stmt.start, stmt.end)
            n.body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.body]
            return n
        if isinstance(stmt, GenIfNode):
            n = GenIfNode(_rename_expr(stmt.cond, mapping, mem_rename, arr_rename))
            n.then_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.then_body]
            n.else_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.else_body]
            return n
        return stmt

    def _inline_submodule(stmt, prefix):
        sub_flat = flatten_module(stmt.module)
        sub_copy = copy.deepcopy(sub_flat)

        mapping = {}
        mem_rename = {}
        arr_rename = {}

        for name, sig in sub_copy._inputs.items():
            new_name = f"{prefix}{name}"
            w = Wire(sig.width, new_name)
            mapping[sig] = w
            flat._wires[new_name] = w
            object.__setattr__(flat, new_name, w)

        for name, sig in sub_copy._outputs.items():
            new_name = f"{prefix}{name}"
            w = Wire(sig.width, new_name)
            mapping[sig] = w
            flat._wires[new_name] = w
            object.__setattr__(flat, new_name, w)

        for name, sig in sub_copy._wires.items():
            new_name = f"{prefix}{name}"
            w = Wire(sig.width, new_name)
            mapping[sig] = w
            flat._wires[new_name] = w
            object.__setattr__(flat, new_name, w)

        for name, sig in sub_copy._regs.items():
            new_name = f"{prefix}{name}"
            r = Reg(sig.width, new_name)
            mapping[sig] = r
            flat._regs[new_name] = r
            object.__setattr__(flat, new_name, r)

        param_stmts = []
        for name, param in sub_copy._params.items():
            new_name = f"{prefix}{name}"
            actual_value = stmt.params.get(name, param.value)
            width = max(actual_value.bit_length(), 1)
            w = Wire(width, new_name)
            mapping[param._expr.signal] = w
            flat._wires[new_name] = w
            object.__setattr__(flat, new_name, w)
            param_stmts.append(Assign(w, Const(actual_value, width), blocking=True))

        for name, mem in sub_copy._memories.items():
            new_name = f"{prefix}{name}"
            new_mem = Memory(mem.width, mem.depth, new_name)
            mem_rename[name] = new_name
            flat._memories[new_name] = new_mem
            object.__setattr__(flat, new_name, new_mem)

        for name, arr in sub_copy._arrays.items():
            new_name = f"{prefix}{name}"
            new_arr = Array(arr.width, arr.depth, new_name, vtype=arr._vtype)
            arr_rename[name] = new_name
            flat._arrays[new_name] = new_arr
            object.__setattr__(flat, new_name, new_arr)

        top_stmts = list(param_stmts)
        for s in sub_copy._top_level:
            top_stmts.append(_rename_stmt(s, mapping, mem_rename, arr_rename))

        comb = []
        for body in sub_copy._comb_blocks:
            comb.append([_rename_stmt(s, mapping, mem_rename, arr_rename) for s in body])

        seq = []
        for clk, rst, reset_async, reset_active_low, body in sub_copy._seq_blocks:
            seq.append((clk, rst, reset_async, reset_active_low, [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in body]))

        for port_name, expr in stmt.port_map.items():
            port_sig = sub_copy._inputs.get(port_name) or sub_copy._outputs.get(port_name) or sub_copy._wires.get(port_name)
            if port_sig is None:
                continue
            new_sig = mapping[port_sig]
            if port_name in sub_copy._inputs:
                top_stmts.append(Assign(new_sig, expr, blocking=True))
            else:
                top_stmts.append(Assign(expr, new_sig, blocking=True))

        return top_stmts, comb, seq

    def _process_stmts(stmts, prefix="", mode="top"):
        """mode: 'top' | 'comb' | 'seq'"""
        top_stmts = []
        new_body = []
        extra_comb = []
        extra_seq = []
        for stmt in stmts:
            if isinstance(stmt, SubmoduleInst):
                ts, cb, sb = _inline_submodule(stmt, f"{prefix}{stmt.name}_")
                top_stmts.extend(ts)
                extra_comb.extend(cb)
                extra_seq.extend(sb)
            elif isinstance(stmt, ForGenNode):
                for i in range(stmt.start, stmt.end):
                    unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                    t, b, c, s2 = _process_stmts(unrolled, f"{prefix}{stmt.var_name}{i}_", mode=mode)
                    top_stmts.extend(t)
                    new_body.extend(b)
                    extra_comb.extend(c)
                    extra_seq.extend(s2)
            elif isinstance(stmt, IfNode):
                n = IfNode(stmt.cond)
                t1, b1, c1, s1 = _process_stmts(stmt.then_body, prefix, mode)
                t2, b2, c2, s2 = _process_stmts(stmt.else_body, prefix, mode)
                top_stmts.extend(t1)
                top_stmts.extend(t2)
                n.then_body = b1
                n.else_body = b2
                extra_comb.extend(c1)
                extra_comb.extend(c2)
                extra_seq.extend(s1)
                extra_seq.extend(s2)
                new_body.append(n)
            elif isinstance(stmt, SwitchNode):
                n = SwitchNode(stmt.expr)
                case_bodies = []
                for v, body in stmt.cases:
                    t, b, c, s2 = _process_stmts(body, prefix, mode)
                    top_stmts.extend(t)
                    case_bodies.append((v, b))
                    extra_comb.extend(c)
                    extra_seq.extend(s2)
                t, b, c, s2 = _process_stmts(stmt.default_body, prefix, mode)
                top_stmts.extend(t)
                n.cases = case_bodies
                n.default_body = b
                extra_comb.extend(c)
                extra_seq.extend(s2)
                new_body.append(n)
            elif isinstance(stmt, GenIfNode):
                if mode == "top":
                    new_body.append(stmt)
                else:
                    n = IfNode(stmt.cond)
                    t1, b1, c1, s1 = _process_stmts(stmt.then_body, prefix, mode)
                    t2, b2, c2, s2 = _process_stmts(stmt.else_body, prefix, mode)
                    top_stmts.extend(t1)
                    top_stmts.extend(t2)
                    n.then_body = b1
                    n.else_body = b2
                    extra_comb.extend(c1)
                    extra_comb.extend(c2)
                    extra_seq.extend(s1)
                    extra_seq.extend(s2)
                    new_body.append(n)
            else:
                new_body.append(stmt)
        return top_stmts, new_body, extra_comb, extra_seq

    t, b, c, s = _process_stmts(module._top_level, mode="top")
    flat._top_level.extend(t)
    flat._top_level.extend(b)
    flat._comb_blocks.extend(c)
    flat._seq_blocks.extend(s)

    for body in module._comb_blocks:
        t, b, c, s = _process_stmts(body, mode="comb")
        flat._top_level.extend(t)
        if b:
            flat._comb_blocks.append(b)
        flat._comb_blocks.extend(c)
        flat._seq_blocks.extend(s)

    for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
        t, b, c, s = _process_stmts(body, mode="seq")
        flat._top_level.extend(t)
        if b:
            flat._seq_blocks.append((clk, rst, reset_async, reset_active_low, b))
        flat._comb_blocks.extend(c)
        flat._seq_blocks.extend(s)

    return flat
