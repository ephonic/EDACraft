"""
rtlgen_x.dsl.legacy.core — 基础信号、AST 与模块容器

提供 Signal / Input / Output / Wire / Reg、Parameter、Module 以及全局上下文管理。
"""
from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from rtlgen_x.dsl.legacy.entity import IREntity

# Re-export from rtlgen_x.dsl.legacy.logic so DSL files can import everything from core.
# Deferred to avoid circular import (logic.py imports from core.py).
# Mux/Cat/Rep/SRA are not defined in core.py (only Mux as Expr class above),
# so lazy-import pulls in the logic function versions that auto-infer width.
def __getattr__(name: str):
    if name in ("If", "Else", "Elif", "Switch", "Cat", "Rep", "SRA"):
        from rtlgen_x.dsl.legacy.logic import If, Else, Elif, Switch, Cat, Rep, SRA
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(globals().keys()) + [
        "If", "Else", "Elif", "Switch", "Mux", "Cat", "Rep", "SRA",
    ]

# ---------------------------------------------------------------------
# Module Documentation — Structured metadata for Verilog comment injection
# ---------------------------------------------------------------------

@dataclass
class ModuleDoc:
    """Structured documentation metadata for a Module.

    When attached to a Module, the VerilogEmitter uses this to generate
    a rich file header with: file info, purpose, port table, timing diagram,
    and per-always-block descriptions.

    Usage:
        mod._module_doc = ModuleDoc(
            source="C910IFU DSL (Phase 3, Step 1)",
            description="Superscalar instruction fetch unit with branch prediction",
            timing="On each cycle: pc_next selected → BTB lookup → ICache fetch → output",
            always_descriptions=[
                ("Comb", "PC next logic: increment or redirect target"),
                ("Seq", "PC register update, async reset to boot vector"),
            ],
        )
    """
    source: str = ""                          # Where this DSL was generated from
    description: str = ""                      # What this module does
    author: str = ""                           # Who/agent created it
    version: str = ""                          # Version string
    timing: str = ""                           # Key timing/protocol description
    port_description: str = ""                 # Additional port notes
    always_descriptions: List[Tuple[str, str]] = field(default_factory=list)
    """List of (block_type, description) tuples.
    block_type: "Comb" | "Seq" | "Reset" | "Generate"
    description: what this block does in plain language.
    """


@dataclass
class IntentContext:
    """Design intent metadata injected by the agent.

    Helps the emitter produce more meaningful comments by understanding
    what each block is supposed to achieve.
    """
    purpose: str = ""          # High-level purpose (e.g., "instruction fetch pipeline")
    key_signals: List[str] = field(default_factory=list)
    timing_notes: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------

class Expr:
    def __init__(self, width: int = 1):
        self.width = width

    def __ror__(self, other):
        return _make_binop("|", _to_expr(other), self)

    def __rand__(self, other):
        return _make_binop("&", _to_expr(other), self)

    def __rxor__(self, other):
        return _make_binop("^", _to_expr(other), self)

    def __rlshift__(self, other):
        return _make_binop("<<", _to_expr(other), self, width=_to_expr(other).width)


@dataclass
class SourceLoc:
    """Python 源代码位置，用于 AST 节点的溯源映射。"""
    file: str
    line: int


class Const(Expr):
    def __init__(self, value: int, width: int = 1):
        super().__init__(width)
        self.value = value

    def __invert__(self):
        return Const(~self.value & ((1 << self.width) - 1), self.width)

    def __and__(self, other):
        w = max(self.width, getattr(other, "width", self.width))
        if isinstance(other, Const):
            return Const(self.value & other.value, w)
        return _make_binop("&", self, other, w)

    def __or__(self, other):
        w = max(self.width, getattr(other, "width", self.width))
        if isinstance(other, Const):
            return Const(self.value | other.value, w)
        return _make_binop("|", self, other, w)

    def __xor__(self, other):
        w = max(self.width, getattr(other, "width", self.width))
        if isinstance(other, Const):
            return Const(self.value ^ other.value, w)
        return _make_binop("^", self, other, w)


class FunctionCall(Expr):
    """Verilog function / system function call: $clog2(x), my_func(a, b)."""
    def __init__(self, name: str, args: List[Any], width: int = 1, is_system: bool = False):
        super().__init__(width)
        self.name = name
        self.args = [_to_expr(a) for a in args]
        self.is_system = is_system


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


def _width_of(val) -> int:
    """Get width of an Expr, int, or object with .width attribute."""
    if isinstance(val, Expr):
        return val.width
    if isinstance(val, int):
        return max(val.bit_length(), 1)
    return getattr(val, "width", 1)


class Mux(Expr):
    def __init__(self, cond: Expr, true_expr: Expr, false_expr: Expr, width: Optional[int] = None):
        if width is None:
            width = max(_width_of(true_expr), _width_of(false_expr))
        super().__init__(width)
        self.cond = cond
        self.true_expr = true_expr
        self.false_expr = false_expr


class Assign:
    def __init__(self, target: Union["Signal", "Expr"], value: Expr, blocking: bool):
        self.target = target
        self.value = value
        self.blocking = blocking
        self.source_location: Optional[SourceLoc] = Context._capture_location()


class IfNode:
    def __init__(self, cond: Expr):
        self.cond = cond
        self.then_body: List[Any] = []
        self.else_body: List[Any] = []
        # elif support: list of (cond_expr, body) pairs
        self.elif_bodies: List[Tuple[Expr, List[Any]]] = []


class GenIfNode:
    def __init__(self, cond: Expr):
        self.cond = cond
        self.then_body: List[Any] = []
        self.else_body: List[Any] = []
        self.elif_bodies: List[Tuple[Expr, List[Any]]] = []


class SwitchNode:
    def __init__(self, expr: Expr, kind: str = "case"):
        self.expr = expr
        self.kind = kind  # "case", "casez", "casex"
        self.cases: List[Tuple[Expr, List[Any]]] = []
        self.default_body: List[Any] = []


class WhenNode:
    """SpinalHDL-style when/otherwise conditional assignment collector.
    
    Unlike IfNode which emits nested if/else, WhenNode collects
    conditional assignments and emits them as a single priority
    mux chain or if/elif/else block.
    """
    def __init__(self):
        self.branches: List[Tuple[Optional[Expr], List[Any]]] = []
        # Each branch is (condition, body). condition=None means 'otherwise'.


class SubmoduleInst:
    def __init__(self, name: str, module: "Module", params: Dict[str, Any], port_map: Dict[str, Union["Signal", Expr]]):
        self.name = name
        self.module = module
        self.params = params
        self.port_map = port_map


# ---------------------------------------------------------------------
# Interface — protocol-level signal grouping and bulk connection
# ---------------------------------------------------------------------

class Interface:
    """Base class for protocol-level signal grouping.

    Subclasses define a set of ports (name, direction, width) and provide
    bulk connection methods.  An Interface instance holds live Signal
    objects that can be connected to module ports or used in port_map.

    Usage::

        hs = HandshakeInterface(64, "hs")
        self.instantiate(sub, "u_sub", port_map={**hs.connect_port_map(src_hs)})
    """

    def __init__(self, name: str):
        self.name = name
        # Dict[str, Signal] — the actual signal objects
        self.signals: Dict[str, Signal] = {}

    def _add_signal(self, name: str, direction: type, width: int):
        sig = direction(width, f"{self.name}_{name}") if width != 1 else direction(f"{self.name}_{name}")
        self.signals[name] = sig
        return sig

    def all_signals(self) -> Dict[str, Signal]:
        return dict(self.signals)

    def connect_to(self, other: "Interface") -> Dict[str, Tuple[Signal, Signal]]:
        """Return a dict of (my_signal -> other_signal) pairs for matching ports."""
        if type(self) is not type(other):
            raise TypeError(f"Cannot connect {type(self).__name__} to {type(other).__name__}")
        pairs: Dict[str, Tuple[Signal, Signal]] = {}
        for name, sig in self.signals.items():
            if name in other.signals:
                pairs[name] = (sig, other.signals[name])
        return pairs


class HandshakeInterface(Interface):
    """valid / ready / data handshake interface.

    Direction convention: the *producer* drives `valid` and `data`,
    the *consumer* drives `ready`.  For port_map generation, the
    caller decides which side is producer vs consumer.
    """

    def __init__(self, data_width: int, name: str = "hs"):
        super().__init__(name)
        self.data_width = data_width
        self.valid = self._add_signal("valid", Input, 1)
        self.ready = self._add_signal("ready", Input, 1)
        self.data = self._add_signal("data", Input, data_width)

    def connect_port_map(self, other: "HandshakeInterface",
                         direction: str = "src_to_dst") -> Dict[str, Signal]:
        """Generate a port_map dict for self.instantiate().

        Args:
            other: The HandshakeInterface on the other side of the connection.
            direction: "src_to_dst" means self is producer, other is consumer.
                       "dst_to_src" means self is consumer, other is producer.
        """
        if direction == "src_to_dst":
            # self's outputs → other's inputs, self's inputs ← other's outputs
            return {
                "valid": self.valid,    # self drives valid → sub receives valid
                "data": self.data,      # self drives data → sub receives data
                "ready": other.ready,   # other drives ready ← sub provides ready
            }
        else:
            return {
                "valid": other.valid,
                "data": other.data,
                "ready": self.ready,
            }


class CacheInterface(Interface):
    """CPU ↔ L1 cache request/response interface.

    CPU side: drives req, addr, wdata, wen.
    Cache side: drives valid, rdata, ready.
    """

    def __init__(self, addr_width: int = 64, data_width: int = 64, name: str = "cache"):
        super().__init__(name)
        self.addr_width = addr_width
        self.data_width = data_width
        # CPU → Cache
        self.req = self._add_signal("req", Input, 1)
        self.addr = self._add_signal("addr", Input, addr_width)
        self.wdata = self._add_signal("wdata", Input, data_width)
        self.wen = self._add_signal("wen", Input, 1)
        # Cache → CPU
        self.valid = self._add_signal("valid", Input, 1)
        self.rdata = self._add_signal("rdata", Input, data_width)
        self.ready = self._add_signal("ready", Input, 1)

    def connect_port_map(self, other: "CacheInterface",
                         direction: str = "cpu_to_cache") -> Dict[str, Signal]:
        """Generate a port_map dict for self.instantiate()."""
        if direction == "cpu_to_cache":
            return {
                "req": self.req,
                "addr": self.addr,
                "wdata": self.wdata,
                "wen": self.wen,
                "valid": other.valid,
                "rdata": other.rdata,
                "ready": self.ready,
            }
        else:
            return {
                "req": other.req,
                "addr": other.addr,
                "wdata": other.wdata,
                "wen": other.wen,
                "valid": self.valid,
                "rdata": self.rdata,
                "ready": other.ready,
            }


def connect_interfaces(src: Interface, dst: Interface,
                       src_dir: str = "out", dst_dir: str = "in") -> Dict[str, Signal]:
    """Bulk connect two interfaces of the same type.

    Returns a port_map suitable for Module.instantiate().

    Args:
        src: Source interface (signals driven by the caller module).
        dst: Destination interface (signals from the submodule).
        src_dir: "out" means src's signals are outputs from caller's perspective.
        dst_dir: "in" means dst's signals are inputs to caller's perspective.
    """
    if type(src) is not type(dst):
        raise TypeError(f"Cannot connect {type(src).__name__} to {type(dst).__name__}")
    port_map: Dict[str, Signal] = {}
    for name, src_sig in src.signals.items():
        if name in dst.signals:
            port_map[name] = src_sig
    return port_map


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

    def __floordiv__(self, other):
        return _make_binop("/", self, other)

    def __rfloordiv__(self, other):
        return _make_binop("/", other, self)

    def __truediv__(self, other):
        return _make_binop("/", self, other)

    def __rtruediv__(self, other):
        return _make_binop("/", other, self)

    def __neg__(self):
        return _make_unop("-", self)

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

    def __init__(self, width: int, depth: int, name: str = "", init_file: Optional[str] = None, init_zero: bool = False, init_data: Optional[list] = None):
        self.width = width
        self.depth = depth
        self.name = name
        self.init_file = init_file
        self.init_zero = init_zero
        self.init_data = init_data
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
    def __init__(self, var_name: str, start: int, end: int, step: int = 1):
        self.var_name = var_name
        self.start = start
        self.end = end
        self.step = step
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
        return len(a.operands) == len(b.operands) and all(_expr_equal(x, y) for x, y in zip(a.operands, b.operands))
    if isinstance(a, Mux):
        return _expr_equal(a.cond, b.cond) and _expr_equal(a.true_expr, b.true_expr) and _expr_equal(a.false_expr, b.false_expr)
    if isinstance(a, MemRead):
        return a.mem_name == b.mem_name and _expr_equal(a.addr, b.addr)
    if isinstance(a, ArrayRead):
        return a.array_name == b.array_name and _expr_equal(a.index, b.index)
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
    # 情况 3: hi = base + n, lo = base + m (common base, different constants)
    if (isinstance(hi_expr, BinOp) and hi_expr.op == '+' and isinstance(hi_expr.rhs, Const)
            and isinstance(lo_expr, BinOp) and lo_expr.op == '+' and isinstance(lo_expr.rhs, Const)):
        if _expr_equal(hi_expr.lhs, lo_expr.lhs):
            return hi_expr.rhs.value - lo_expr.rhs.value + 1
        if _expr_equal(hi_expr.rhs, lo_expr.lhs) and _expr_equal(hi_expr.lhs, lo_expr.rhs):
            return hi_expr.lhs.value - lo_expr.lhs.value + 1
    # 情况 4: hi = (base + 1) * N - 1, lo = base * N  (e.g. lane*32+31 : lane*32)
    if (isinstance(hi_expr, BinOp) and hi_expr.op == '-'
            and isinstance(hi_expr.rhs, Const) and hi_expr.rhs.value == 1
            and isinstance(hi_expr.lhs, BinOp) and hi_expr.lhs.op == '*'
            and isinstance(hi_expr.lhs.lhs, BinOp) and hi_expr.lhs.lhs.op == '+'
            and isinstance(hi_expr.lhs.lhs.rhs, Const) and hi_expr.lhs.lhs.rhs.value == 1
            and isinstance(lo_expr, BinOp) and lo_expr.op == '*'
            and isinstance(lo_expr.rhs, Const)
            and _expr_equal(hi_expr.lhs.lhs.lhs, lo_expr.lhs)
            and hi_expr.lhs.rhs.value == lo_expr.rhs.value):
        return lo_expr.rhs.value
    return None


# ---------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------

class Signal(IREntity):
    """硬件信号基类，支持位宽推导与运算符重载。"""

    def __init__(self, width: int = 1, name: str = "", signed: bool = False, init_value: Optional[int] = None):
        IREntity.__init__(self, name)
        self.width = width
        self.name = name
        self.signed = signed
        self.init_value = init_value
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

    def __floordiv__(self, other):
        return _make_binop("/", self, other)

    def __rfloordiv__(self, other):
        return _make_binop("/", other, self)

    def __truediv__(self, other):
        return _make_binop("/", self, other)

    def __rtruediv__(self, other):
        return _make_binop("/", other, self)

    def __neg__(self):
        return _make_unop("-", self)

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

    def as_sint(self) -> "Signal":
        """返回此信号的有符号版本（用于算术运算中的符号扩展）。"""
        s = Signal(self.width, self.name)
        s.signed = True
        s._expr = UnaryOp("$signed", self._expr, self.width)
        return s

    def as_uint(self) -> "Signal":
        """返回此信号的无符号版本（显式消除有符号语义）。"""
        s = Signal(self.width, self.name)
        s.signed = False
        s._expr = UnaryOp("$unsigned", self._expr, self.width)
        return s

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
    """时序逻辑寄存器。支持 init_value 以生成 Verilog 初始值声明。"""
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
        return _param_binop("==", self, other, width=1)

    def __ne__(self, other):
        return _param_binop("!=", self, other, width=1)

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
# Intent
# ---------------------------------------------------------------------

class IntentContext:
    """设计约束目标上下文，用于声明 PPA 期望。"""

    def __init__(self):
        self.latency_cycles: Optional[int] = None
        self.throughput: Optional[str] = None       # "1" (每周期一个) | "N" | "variable"
        self.clock_freq: Optional[float] = None     # Hz
        self.area_budget: Optional[int] = None      # estimated gate count budget
        self.power_budget: Optional[float] = None   # mW (optional)


# ---------------------------------------------------------------------
# Context Managers for comb / seq
# ---------------------------------------------------------------------

class _InitContext:
    """Context manager for initial blocks: ``with self.init:``."""
    def __init__(self, module: "Module"):
        self._module = module
    def __enter__(self):
        body: List[Any] = []
        self._module._init_blocks.append(body)
        Context.push(Context(module=self._module, stmt_container=body))
        return self
    def __exit__(self, *args):
        Context.pop()
    def __call__(self, func):
        with self: func()
        return func


class _CombContext:
    """Context manager for combinational/latch logic."""

    def __init__(self, module: "Module", always_latch: bool = False):
        self._module = module
        self._always_latch = always_latch

    def __enter__(self):
        body: List[Any] = []
        if self._always_latch:
            self._module._latch_blocks.append(body)
        else:
            self._module._comb_blocks.append(body)
        Context.push(Context(module=self._module, stmt_container=body))
        return self

    def __exit__(self, *args):
        Context.pop()

    def __call__(self, func: Callable) -> Callable:
        """Decorator compatibility: @self.comb still works."""
        with self:
            func()
        return func


class _SeqContext:
    """Context manager for sequential logic: ``with self.seq(clk, rst):`` or ``@self.seq(clk, rst)``."""

    def __init__(self, module: "Module", clock: Signal, reset: Optional[Signal] = None,
                 reset_async: bool = False, reset_active_low: bool = False):
        self._module = module
        self._clock = clock
        self._reset = reset
        self._reset_async = reset_async
        self._reset_active_low = reset_active_low
        self._body: List[Any] = []

    def __enter__(self):
        self._module._seq_blocks.append(
            (self._clock, self._reset, self._reset_async, self._reset_active_low, self._body)
        )
        Context.push(Context(module=self._module, stmt_container=self._body))
        return self

    def __exit__(self, *args):
        Context.pop()

    def __call__(self, func: Callable) -> Callable:
        """Decorator compatibility: @self.seq(clk, rst) still works."""
        with self:
            func()
        return func


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

    @classmethod
    def _capture_location(cls) -> Optional[SourceLoc]:
        """捕获调用者的 Python 源代码位置（跳过内部框架帧）。"""
        try:
            frame = inspect.currentframe()
            # Walk up until we find a frame NOT from core.py
            while frame is not None:
                fname = frame.f_code.co_filename
                if 'rtlgen/core.py' not in fname and 'rtlgen\\core.py' not in fname:
                    return SourceLoc(file=frame.f_code.co_filename, line=frame.f_lineno)
                frame = frame.f_back
        except Exception:
            pass
        return None


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


class Module(IREntity, metaclass=ModuleMeta):
    """所有硬件模块的基类。"""

    STRICT: bool = False  # 启用严格端口连接检查

    def __init__(self, name: Optional[str] = None, param_bindings: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__
        IREntity.__init__(self, self.name)
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
        self._latch_blocks: List[List[Any]] = []
        self._init_blocks: List[List[Any]] = []
        self._seq_blocks: List[Tuple[Signal, Optional[Signal], List[Any]]] = []
        self._top_level: List[Any] = []
        self._param_bindings: Dict[str, Any] = dict(param_bindings) if param_bindings else {}
        self._module_comments: List[str] = []
        self._module_assertions: List[Tuple[str, str]] = []
        self._module_suggestions: List[str] = []
        self._module_doc: Optional[ModuleDoc] = None
        self._parent: Optional["Module"] = None
        self._design_intent: Optional[IntentContext] = None

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
                    for _, body in stmt.elif_bodies:
                        _collect_stmt_assigns(body, target_dict)
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

        # ================================================================
        # Rule: narrow_const — 窄常量用于宽上下文
        # ================================================================
        if _rule_on("narrow_const"):
            self._lint_narrow_const(violations)

        # ================================================================
        # Rule: redundant_assignment — 同一信号在同一块中被多次赋值（后写覆盖前写）
        # ================================================================
        if _rule_on("redundant_assignment"):
            self._lint_redundant_assignment(violations)

        # ================================================================
        # Rule: missing_case_default — Switch 缺少 default 分支
        # ================================================================
        if _rule_on("missing_case_default"):
            self._lint_missing_case_default(violations)

        # ================================================================
        # Rule: missing_default_assignment — comb 块缺少默认赋值（latch 风险）
        # ================================================================
        if _rule_on("missing_default_assignment"):
            self._lint_missing_default_assignment(violations)

        # ================================================================
        # Rule: narrow_const_comparison — 1 位信号与 1'd1 比较
        # ================================================================
        if _rule_on("narrow_const_comparison"):
            self._lint_narrow_const_comparison(violations)

        # ================================================================
        # Rule: width_truncation — 表达式位宽大于目标信号位宽（隐式截断）
        # ================================================================
        if _rule_on("width_truncation"):
            self._lint_width_truncation(violations)

        # ================================================================
        # Rule: signed_mix — 有符号与无符号信号混合运算
        # ================================================================
        if _rule_on("signed_mix"):
            self._lint_signed_mix(violations)

        return violations

    def _lint_narrow_const(self, violations: List[str]):
        """检查 Const 节点的位宽是否与其使用上下文匹配。

        规则：当 Const 作为赋值目标时，如果 Const.width < target.width，
        说明常量位宽不一致，可能在 Verilog 中产生 1'd0 写入 32 位寄存器。
        """
        def _collect_narrow_consts(stmts, context_widths: Dict):
            for stmt in stmts:
                if isinstance(stmt, Assign):
                    target = None
                    if isinstance(stmt.target, Signal):
                        target = stmt.target
                        tw = target.width
                    elif isinstance(stmt.target, Ref):
                        target = stmt.target.signal
                        tw = target.width
                    elif isinstance(stmt.target, (Slice, BitSelect)):
                        t = stmt.target
                        while isinstance(t, (Slice, BitSelect)) and hasattr(t, "operand"):
                            t = t.operand
                        if isinstance(t, Ref):
                            target = t.signal
                            tw = t.signal.width
                        else:
                            continue
                    else:
                        continue
                    # 检查 Const 在 value 中是否有窄常量
                    self._check_narrow_in_expr(stmt.value, tw, violations, target.name if target else "?")
                elif isinstance(stmt, IfNode):
                    _collect_narrow_consts(stmt.then_body, context_widths)
                    for _, body in stmt.elif_bodies:
                        _collect_narrow_consts(body, context_widths)
                    _collect_narrow_consts(stmt.else_body, context_widths)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _collect_narrow_consts(body, context_widths)
                    _collect_narrow_consts(stmt.default_body, context_widths)

        for body in self._comb_blocks:
            _collect_narrow_consts(body, {})
        for _, _, _, _, body in self._seq_blocks:
            _collect_narrow_consts(body, {})

    def _check_narrow_in_expr(self, expr: Expr, target_width: int, violations: List[str], target_name: str, depth: int = 0):
        """递归检查表达式中是否有位宽远小于上下文的 Const。"""
        if expr is None:
            return
        if isinstance(expr, Const):
            if expr.width == 1 and target_width > 4 and expr.value == 0:
                # Only flag if this Const is a direct assignment value (depth 0)
                if depth == 0:
                    violations.append(
                        f"[NarrowConst] Constant {expr.width}'d{expr.value} assigned to "
                        f"{target_width}-bit signal '{target_name}'. "
                        f"Consider using {target_width}'d{expr.value} for consistency."
                    )
            return
        if isinstance(expr, Mux):
            self._check_narrow_in_expr(expr.true_expr, target_width, violations, target_name, depth + 1)
            self._check_narrow_in_expr(expr.false_expr, target_width, violations, target_name, depth + 1)
            self._check_narrow_in_expr(expr.cond, target_width, violations, target_name, depth + 1)
        if isinstance(expr, BinOp):
            self._check_narrow_in_expr(expr.lhs, target_width, violations, target_name, depth + 1)
            self._check_narrow_in_expr(expr.rhs, target_width, violations, target_name, depth + 1)
        if isinstance(expr, UnaryOp):
            self._check_narrow_in_expr(expr.operand, target_width, violations, target_name, depth + 1)
        if isinstance(expr, Concat):
            for op in expr.operands:
                self._check_narrow_in_expr(op, target_width, violations, target_name, depth + 1)

    def _lint_redundant_assignment(self, violations: List[str]):
        """检查同一 comb 块中是否有顶层顺序赋值覆盖控制流内的赋值。

        典型场景：Switch 之后紧跟 If 写同一信号，导致 Switch 的结果被覆盖。
        Switch/if/else 分支内部对同一信号的多次赋值不算冗余（正常多路径赋值）。
        """
        def _extract_target_name(stmt) -> str | None:
            if isinstance(stmt, Assign):
                if isinstance(stmt.target, Signal):
                    return stmt.target.name
                elif isinstance(stmt.target, Ref):
                    return stmt.target.signal.name
            return None

        def _collect_assigned_sigs_in_stmt(stmt, acc: Set[str]):
            """递归收集语句内部被赋值的所有信号名。"""
            if isinstance(stmt, Assign):
                name = _extract_target_name(stmt)
                if name:
                    acc.add(name)
            elif isinstance(stmt, IfNode):
                for s in stmt.then_body:
                    _collect_assigned_sigs_in_stmt(s, acc)
                for _, body in stmt.elif_bodies:
                    for s in body:
                        _collect_assigned_sigs_in_stmt(s, acc)
                for s in stmt.else_body:
                    _collect_assigned_sigs_in_stmt(s, acc)
            elif isinstance(stmt, SwitchNode):
                for _, case_body in stmt.cases:
                    for s in case_body:
                        _collect_assigned_sigs_in_stmt(s, acc)
                for s in stmt.default_body:
                    _collect_assigned_sigs_in_stmt(s, acc)

        for i, body in enumerate(self._comb_blocks):
            # 场景: SwitchNode 之后紧跟 IfNode 写同一信号
            # 例如：Switch 所有 case 写 out，之后 if(en) out = 0xFF 覆盖
            # 注意：多个 IfNode 串行（如 BarrelShifter）不算冗余，
            # 只有 Switch（有 default，覆盖所有路径）之后的 If 才算覆盖。
            switch_sigs: Set[str] = set()
            for j, stmt in enumerate(body):
                if isinstance(stmt, SwitchNode):
                    _collect_assigned_sigs_in_stmt(stmt, switch_sigs)
                elif isinstance(stmt, IfNode) and switch_sigs:
                    if_sigs: Set[str] = set()
                    _collect_assigned_sigs_in_stmt(stmt, if_sigs)
                    overlap = switch_sigs & if_sigs
                    for sig_name in sorted(overlap):
                        violations.append(
                            f"[RedundantAssign] Signal '{sig_name}' is assigned in a Switch "
                            f"block in @comb #{i}, then overridden by a following If block. "
                            f"The Switch result is dead code. Wrap into if/else chain."
                        )

            # 场景 2: 多个顶层赋值在控制流之前（dead code）
            pre_cf_counts: Dict[str, int] = {}
            for stmt in body:
                if isinstance(stmt, (IfNode, SwitchNode)):
                    break
                name = _extract_target_name(stmt)
                if name:
                    pre_cf_counts[name] = pre_cf_counts.get(name, 0) + 1

            for sig_name, count in pre_cf_counts.items():
                if count > 1:
                    violations.append(
                        f"[RedundantAssign] Signal '{sig_name}' is assigned {count} times "
                        f"before control flow in @comb #{i}. Later assignments override earlier ones."
                    )
        # Note: seq blocks intentionally assign same signal from different branches (reset/normal)
        # so we only check comb blocks where sequential assignments indicate dead code.

    def _lint_missing_case_default(self, violations: List[str]):
        """检查所有 SwitchNode 是否有 default 分支。

        缺少 default 的 case 在组合逻辑中可能推断出 latch。
        """
        def _scan_switches(stmts):
            for stmt in stmts:
                if isinstance(stmt, SwitchNode):
                    if not stmt.default_body:
                        violations.append(
                            f"[MissingCaseDefault] Switch on '{self._expr_name(stmt.expr)}' has no "
                            f"default branch. Add a default to prevent latch inference in comb logic."
                        )
                elif isinstance(stmt, IfNode):
                    _scan_switches(stmt.then_body)
                    for _, body in stmt.elif_bodies:
                        _scan_switches(body)
                    _scan_switches(stmt.else_body)

        for body in self._comb_blocks:
            _scan_switches(body)

    def _expr_name(self, expr) -> str:
        if isinstance(expr, Ref):
            return expr.signal.name
        if isinstance(expr, Const):
            return str(expr.value)
        return "?"

    def _lint_missing_default_assignment(self, violations: List[str]):
        """检查 comb 块中是否有信号在 if/switch 中被赋值但没有默认值。

        专业 RTL 模式：always @(*) 块顶部应有所有被条件赋值的信号的默认赋值。
        """
        def _check_comb_block(body):
            # 收集所有在条件分支中被赋值的信号
            conditional_sigs: Set[str] = set()
            # 收集所有在块顶部的默认赋值（在任何 if/switch 之前）
            default_sigs: Set[str] = set()

            seen_control_flow = False
            for stmt in body:
                if isinstance(stmt, Assign) and not seen_control_flow:
                    name = None
                    if isinstance(stmt.target, Signal):
                        name = stmt.target.name
                    elif isinstance(stmt.target, Ref):
                        name = stmt.target.signal.name
                    if name:
                        default_sigs.add(name)
                elif isinstance(stmt, (IfNode, SwitchNode)):
                    seen_control_flow = True
                    self._collect_assigned_sigs(stmt, conditional_sigs)

            missing = conditional_sigs - default_sigs
            for sig in sorted(missing):
                violations.append(
                    f"[MissingDefaultAssign] Signal '{sig}' is conditionally assigned in comb block "
                    f"but has no default assignment at block top. Add '{sig} = {sig};' to prevent latch."
                )

        for i, body in enumerate(self._comb_blocks):
            _check_comb_block(body)

    def _collect_assigned_sigs(self, stmt, sigs: Set[str]):
        if isinstance(stmt, Assign):
            name = None
            if isinstance(stmt.target, Signal):
                name = stmt.target.name
            elif isinstance(stmt.target, Ref):
                name = stmt.target.signal.name
            if name:
                sigs.add(name)
        elif isinstance(stmt, IfNode):
            for s in stmt.then_body:
                self._collect_assigned_sigs(s, sigs)
            for _, body in stmt.elif_bodies:
                for s in body:
                    self._collect_assigned_sigs(s, sigs)
            for s in stmt.else_body:
                self._collect_assigned_sigs(s, sigs)
        elif isinstance(stmt, SwitchNode):
            for _, b in stmt.cases:
                for s in b:
                    self._collect_assigned_sigs(s, sigs)
            for s in stmt.default_body:
                self._collect_assigned_sigs(s, sigs)

    def _lint_narrow_const_comparison(self, violations: List[str]):
        """检查 1 位信号是否与 1'd1 做 == 比较（冗余）。

        例如：shift_amount[0] == 1'd1 — 1 位信号本身已经是布尔值，
        直接写 shift_amount[0] 即可。
        """
        def _scan_expr(expr, context=""):
            if isinstance(expr, BinOp) and expr.op == "==" and expr.width == 1:
                is_one = (isinstance(expr.lhs, Const) and expr.lhs.value == 1 and expr.lhs.width == 1) or \
                         (isinstance(expr.rhs, Const) and expr.rhs.value == 1 and expr.rhs.width == 1)
                is_zero = (isinstance(expr.lhs, Const) and expr.lhs.value == 0 and expr.lhs.width == 1) or \
                          (isinstance(expr.rhs, Const) and expr.rhs.value == 0 and expr.rhs.width == 1)
                if is_one or is_zero:
                    other = expr.rhs if isinstance(expr.lhs, Const) else expr.lhs
                    if isinstance(other, (Slice, BitSelect)) and other.width == 1:
                        operand_name = self._expr_name(other.operand) if isinstance(other.operand, Ref) else "?"
                        idx = other.hi if isinstance(other, Slice) else (other.index if isinstance(other.index, Const) else "?")
                        violations.append(
                            f"[NarrowConstComparison] Redundant comparison "
                            f"'{operand_name}[{idx}] == 1'd1'. Use '{operand_name}[{idx}]' directly."
                        )
            if isinstance(expr, BinOp):
                _scan_expr(expr.lhs, context)
                _scan_expr(expr.rhs, context)
            if isinstance(expr, Mux):
                _scan_expr(expr.cond, context)
            if isinstance(expr, UnaryOp):
                _scan_expr(expr.operand, context)

        def _scan_stmt(stmt):
            if isinstance(stmt, Assign):
                _scan_expr(stmt.value)
            elif isinstance(stmt, IfNode):
                _scan_expr(stmt.cond)
                for s in stmt.then_body:
                    _scan_stmt(s)
                for cond, body in stmt.elif_bodies:
                    _scan_expr(cond)
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.else_body:
                    _scan_stmt(s)
            elif isinstance(stmt, SwitchNode):
                _scan_expr(stmt.expr)
                for _, body in stmt.cases:
                    for s in body:
                        _scan_stmt(s)

        for body in self._comb_blocks:
            for stmt in body:
                _scan_stmt(stmt)
        for _, _, _, _, body in self._seq_blocks:
            for stmt in body:
                _scan_stmt(stmt)

    def _lint_width_truncation(self, violations: List[str]):
        """检查赋值目标位宽是否小于表达式推导位宽（隐式截断风险）。"""
        def _check_expr(expr, target_width: int, sig_name: str, depth: int = 0):
            if expr is None:
                return
            if isinstance(expr, BinOp):
                inferred = _infer_width(expr.op, expr.lhs, expr.rhs)
                if depth == 0 and inferred > target_width:
                    violations.append(
                        f"[WidthTruncation] Expression '{expr.op}' ({expr.lhs.width}b {expr.op} {expr.rhs.width}b = {inferred}b) "
                        f"assigned to {target_width}-bit signal '{sig_name}'. "
                        f"Upper {inferred - target_width} bit(s) will be truncated. Use .trunc() or extend target if intended."
                    )
                _check_expr(expr.lhs, target_width, sig_name, depth + 1)
                _check_expr(expr.rhs, target_width, sig_name, depth + 1)
            elif isinstance(expr, Mux):
                _check_expr(expr.true_expr, target_width, sig_name, depth + 1)
                _check_expr(expr.false_expr, target_width, sig_name, depth + 1)
            elif isinstance(expr, Concat):
                for op in expr.operands:
                    _check_expr(op, target_width, sig_name, depth + 1)
            elif isinstance(expr, UnaryOp):
                _check_expr(expr.operand, target_width, sig_name, depth + 1)

        def _scan_stmt(stmt):
            if isinstance(stmt, Assign):
                target = None
                tw = 0
                if isinstance(stmt.target, Signal):
                    target = stmt.target
                    tw = target.width
                elif isinstance(stmt.target, Ref):
                    target = stmt.target.signal
                    tw = target.width
                if target and tw > 0:
                    _check_expr(stmt.value, tw, target.name)
            elif isinstance(stmt, IfNode):
                for s in stmt.then_body:
                    _scan_stmt(s)
                for _, body in stmt.elif_bodies:
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.else_body:
                    _scan_stmt(s)
            elif isinstance(stmt, SwitchNode):
                for _, body in stmt.cases:
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.default_body:
                    _scan_stmt(s)

        for body in self._comb_blocks:
            for stmt in body:
                _scan_stmt(stmt)
        for _, _, _, _, body in self._seq_blocks:
            for stmt in body:
                _scan_stmt(stmt)

    def _lint_signed_mix(self, violations: List[str]):
        """检查有符号信号与无符号信号直接混合运算（未显式 cast）。"""
        def _check_mixed(lhs: Expr, rhs: Expr, sig_name: str):
            l_sig = None
            r_sig = None
            if isinstance(lhs, Ref):
                l_sig = lhs.signal
            elif isinstance(lhs, Signal):
                l_sig = lhs
            if isinstance(rhs, Ref):
                r_sig = rhs.signal
            elif isinstance(rhs, Signal):
                r_sig = rhs
            if l_sig and r_sig and getattr(l_sig, "signed", False) != getattr(r_sig, "signed", False):
                violations.append(
                    f"[SignedMix] Signed signal '{l_sig.name}' and unsigned signal '{r_sig.name}' "
                    f"used in the same expression assigned to '{sig_name}'. "
                    f"Use .as_sint() or .as_uint() to clarify intent."
                )

        def _scan_stmt(stmt):
            if isinstance(stmt, Assign):
                target_name = ""
                if isinstance(stmt.target, Signal):
                    target_name = stmt.target.name
                if isinstance(stmt.value, BinOp):
                    _check_mixed(stmt.value.lhs, stmt.value.rhs, target_name)
            elif isinstance(stmt, IfNode):
                for s in stmt.then_body:
                    _scan_stmt(s)
                for _, body in stmt.elif_bodies:
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.else_body:
                    _scan_stmt(s)
            elif isinstance(stmt, SwitchNode):
                for _, body in stmt.cases:
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.default_body:
                    _scan_stmt(s)

        for body in self._comb_blocks:
            for stmt in body:
                _scan_stmt(stmt)
        for _, _, _, _, body in self._seq_blocks:
            for stmt in body:
                _scan_stmt(stmt)

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
            self._memories[value.name] = value
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

    def add_submodule(self, module: "Module", name: Optional[str] = None) -> "Module":
        """Add a sub-module created as a local variable.

        This is the preferred way to register sub-modules that were
        created without a ``self.xxx`` assignment.  It automatically
        generates port bindings by name matching and creates a
        SubmoduleInst in the top-level statement list.

        Usage::

            buf = NoCBuffer()       # local variable
            self.add_submodule(buf) # auto-wired by port name

        Args:
            module: The sub-module instance to add.
            name: Instance name.  Defaults to the module's type name.
        """
        inst_name = name or getattr(module, '_type_name', module.name)
        # Deduplicate: append _1, _2 etc. if name is taken
        existing = {n for n, _ in self._submodules}
        if inst_name in existing:
            i = 1
            while f"{inst_name}_{i}" in existing:
                i += 1
            inst_name = f"{inst_name}_{i}"

        self._submodules.append((inst_name, module))
        object.__setattr__(module, '_parent', self)

        # Auto-generate port bindings by name matching
        port_map: Dict[str, Union[Signal, Expr]] = {}
        for pname in list(module._inputs.keys()) + list(module._outputs.keys()):
            if hasattr(self, pname):
                val = getattr(self, pname)
                if isinstance(val, Signal):
                    port_map[pname] = val
                elif isinstance(val, (int, Const)):
                    port_map[pname] = Const(int(val), 1) if isinstance(val, int) else val

        # Auto-pass parent parameters
        params: Dict[str, Any] = {}
        for pname, param in module._params.items():
            if hasattr(self, pname):
                params[pname] = getattr(self, pname)

        self._top_level.append(SubmoduleInst(inst_name, module, params, port_map))
        return module

    # ---- comb / seq blocks --------------------------------------------
    @property
    def comb(self) -> _CombContext:
        """Combinational logic context manager.

        Usage:
            with self.comb:
                self.y <<= self.a + self.b

        Or as decorator (backward compatible):
            @self.comb
            def my_logic():
                self.y <<= self.a + self.b
        """
        return _CombContext(self)

    @property
    def latch(self) -> _CombContext:
        """Latch logic context manager: generates always_latch block."""
        return _CombContext(self, always_latch=True)

    @property
    def init(self) -> _InitContext:
        """Initial block context manager: generates initial block."""
        return _InitContext(self)

    def seq(self, clock: Signal, reset: Optional[Signal] = None,
            reset_async: bool = False, reset_active_low: bool = False) -> _SeqContext:
        """Sequential logic context manager.

        Usage:
            with self.seq(clk, rst, reset_async=True, reset_active_low=True):
                with If(rst == 0):
                    self.count <<= 0
                with Else():
                    self.count <<= self.count + 1

        Or as decorator (backward compatible):
            @self.seq(clk, rst, reset_async=True)
            def my_seq():
                self.count <<= self.count + 1
        """
        return _SeqContext(self, clock, reset, reset_async, reset_active_low)


    def intent(self, func: Callable) -> Callable:
        """声明设计约束目标的装饰器。

        示例:
            @self.intent
            def constraints(c):
                c.latency_cycles = 3
                c.clock_freq = 500e6
        """
        intent = IntentContext()
        func(intent)
        self._design_intent = intent
        return func

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
        port_map = {k: _to_expr(v) for k, v in port_map.items() if v is not None}
        inst = SubmoduleInst(name, submodule, params, port_map)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(inst)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(inst)
        else:
            self._top_level.append(inst)

    def instantiate_with_ifaces(
        self,
        submodule: "Module",
        name: str,
        params: Optional[Dict[str, Any]] = None,
        parent_ifaces: Optional[Dict[str, Interface]] = None,
        sub_ifaces: Optional[Dict[str, Interface]] = None,
        extra_ports: Optional[Dict[str, Union[Signal, Expr]]] = None,
    ):
        """Instantiate a submodule using Interface-based bulk connection.

        Instead of manually mapping every port, pass interface objects and
        the method auto-generates the port_map by matching interface names.

        Args:
            submodule: The Module to instantiate.
            name: Instance name.
            params: Optional parameter dict.
            parent_ifaces: Dict of interface name -> Interface on this (parent) module.
            sub_ifaces: Dict of interface name -> Interface on the submodule.
                        If None, assumes same names as parent_ifaces.
            extra_ports: Additional port mappings that don't belong to any interface.

        Usage::

            self.instantiate_with_ifaces(
                router, "u_router",
                parent_ifaces={"hs_in": hs_in, "hs_out": hs_out},
                extra_ports={"clk": self.clk, "rst_n": self.rst_n},
            )
        """
        params = params or {}
        sub_ifaces = sub_ifaces or {}
        extra_ports = extra_ports or {}

        port_map: Dict[str, Union[Signal, Expr]] = dict(extra_ports)
        for iface_name, parent_iface in (parent_ifaces or {}).items():
            sub_iface = sub_ifaces.get(iface_name, parent_iface)
            if sub_iface is None:
                continue
            if type(parent_iface) is not type(sub_iface):
                raise TypeError(
                    f"Interface type mismatch on '{iface_name}': "
                    f"{type(parent_iface).__name__} vs {type(sub_iface).__name__}"
                )
            for sig_name, parent_sig in parent_iface.signals.items():
                if sig_name in sub_iface.signals:
                    port_map[sub_iface.signals[sig_name].name] = parent_sig

        port_map = {k: _to_expr(v) for k, v in port_map.items() if v is not None}
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
# Behavioral / Black-box Modules
# ---------------------------------------------------------------------

class BehavioralModule(Module):
    """行为级子模块：用 Python callable 实现功能，可参与系统级仿真。

    在架构探索阶段，子模块可以用行为级模型代替 RTL 实现，
    从而在系统级别验证拆分的合理性。

    示例:
        def mac(a, b, c):
            return {'y': a * b + c}

        mac_mod = BehavioralModule(
            name='mac',
            inputs=[('a', 8), ('b', 8), ('c', 16)],
            outputs=[('y', 16)],
            func=mac,
        )
        # 然后作为子模块实例化到顶层模块中
    """

    def __init__(
        self,
        name: str,
        inputs: List[tuple],       # [(port_name, width), ...]
        outputs: List[tuple],      # [(port_name, width), ...]
        func,                       # Callable[[dict], dict]  inputs -> outputs
    ):
        super().__init__(name)
        self._beh_func = func

        for pname, pw in inputs:
            setattr(self, pname, Input(pw, pname))
            self._inputs[pname] = getattr(self, pname)
        for pname, pw in outputs:
            setattr(self, pname, Output(pw, pname))
            self._outputs[pname] = getattr(self, pname)

    def __repr__(self):
        return f"BehavioralModule({self.name})"


# ---------------------------------------------------------------------
# Behavioral – RTL Correspondence
# ---------------------------------------------------------------------

@dataclass
class ModelVersion:
    """行为级模型或 RTL 设计的版本号，支持语义化版本。"""
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other):
        if not isinstance(other, ModelVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other):
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __hash__(self):
        return hash((self.major, self.minor, self.patch))


@dataclass
class BehavioralRTLPair:
    """行为级模型与 RTL 设计的配对关系。

    维护行为级模型（Python）与 RTL 实现之间的版本对应关系，
    用于确认系统级拆分合理性并验证最终 RTL 满足行为级要求。

    Attributes:
        name:           配对名称（通常等于模块名）
        behavioral:     行为级模块（BehavioralModule 或任何可调用模型）
        rtl:            RTL 模块（Module 子类实例）
        beh_version:    行为级模型版本
        rtl_version:    RTL 实现版本（应与 beh_version 一致才认为"等价"）
        spec_hash:      原始 spec 的哈希，用于追溯
        verified:       是否已通过仿真验证（行为级 == RTL 输出）
        notes:          人工备注，如已知差异、TODO 等
    """
    name: str
    behavioral: Module
    rtl: Module
    beh_version: ModelVersion = field(default_factory=ModelVersion)
    rtl_version: ModelVersion = field(default_factory=ModelVersion)
    spec_hash: str = ""
    verified: bool = False
    notes: str = ""

    def mark_verified(self):
        """标记为已通过仿真验证。"""
        self.verified = True

    def is_consistent(self) -> bool:
        """检查行为级和 RTL 版本是否一致。"""
        return self.beh_version == self.rtl_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "beh_version": str(self.beh_version),
            "rtl_version": str(self.rtl_version),
            "consistent": self.is_consistent(),
            "verified": self.verified,
            "notes": self.notes,
        }


class ModelRegistry:
    """全局行为级模型注册表。

    管理所有模块的行为级模型和 RTL 实现的配对关系，
    支持按名称查找、版本查询、一致性检查。

    用法:
        ModelRegistry.register_pair(pair)
        pair = ModelRegistry.get("MAC16")
        report = ModelRegistry.verification_report()
    """

    _pairs: Dict[str, BehavioralRTLPair] = {}

    @classmethod
    def register_pair(cls, pair: BehavioralRTLPair) -> None:
        """注册一个行为级-RTL 配对。"""
        cls._pairs[pair.name] = pair

    @classmethod
    def get(cls, name: str) -> Optional[BehavioralRTLPair]:
        """按模块名获取配对。"""
        return cls._pairs.get(name)

    @classmethod
    def list_pairs(cls) -> List[str]:
        """列出所有已注册的配对名称。"""
        return list(cls._pairs.keys())

    @classmethod
    def verification_report(cls) -> Dict[str, Any]:
        """生成完整的验证报告。"""
        total = len(cls._pairs)
        verified = sum(1 for p in cls._pairs.values() if p.verified)
        consistent = sum(1 for p in cls._pairs.values() if p.is_consistent())
        return {
            "total_pairs": total,
            "verified": verified,
            "consistent": consistent,
            "unverified": [p.name for p in cls._pairs.values() if not p.verified],
            "inconsistent": [p.name for p in cls._pairs.values() if not p.is_consistent()],
            "pairs": {n: p.to_dict() for n, p in cls._pairs.items()},
        }

    @classmethod
    def reset(cls) -> None:
        """清空注册表（用于测试）。"""
        cls._pairs.clear()


class BlackBoxModule(Module):
    """黑盒子模块：声明端口但不定义内部逻辑。

    用于尚未实现的子模块，生成 Verilog 时为实例化语句。
    仿真时输出 0，不报错。

    示例:
        bb = BlackBoxModule(
            name='future_block',
            inputs=[('din', 8)],
            outputs=[('dout', 8)],
        )
    """

    def __init__(
        self,
        name: str,
        inputs: List[tuple],       # [(port_name, width), ...]
        outputs: List[tuple],      # [(port_name, width), ...]
    ):
        super().__init__(name)
        for pname, pw in inputs:
            setattr(self, pname, Input(pw, pname))
            self._inputs[pname] = getattr(self, pname)
        for pname, pw in outputs:
            setattr(self, pname, Output(pw, pname))
            self._outputs[pname] = getattr(self, pname)

    def __repr__(self):
        return f"BlackBoxModule({self.name})"


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------


def _infer_width(op: str, lhs: Expr, rhs: Expr) -> int:
    """根据操作符和操作数位宽自动推导结果位宽（Verilog 语义）。"""
    if op in ('+', '-'):
        return max(lhs.width, rhs.width) + 1
    if op == '*':
        return lhs.width + rhs.width
    if op in ('&', '|', '^'):
        return max(lhs.width, rhs.width)
    if op == '<<':
        return lhs.width + (rhs.value if isinstance(rhs, Const) else 0)
    if op == '>>':
        return lhs.width
    if op == '>>>':
        return lhs.width
    if op in ('%', '/'):
        return max(lhs.width, rhs.width)
    if op in ('==', '!=', '<', '<=', '>', '>='):
        return 1
    return max(lhs.width, rhs.width)


def _make_binop(op: str, lhs: Any, rhs: Any, width: Optional[int] = None) -> Signal:
    le = _to_expr(lhs)
    re = _to_expr(rhs)
    w = width if width is not None else _infer_width(op, le, re)
    s = Signal(width=w)
    s._expr = BinOp(op, le, re, w)
    return s


def _make_unop(op: str, operand: Any) -> Signal:
    e = _to_expr(operand)
    s = Signal(width=e.width)
    s._expr = UnaryOp(op, e, e.width)
    return s


def _param_binop(op: str, lhs: Any, rhs: Any, width: Optional[int] = None) -> Signal:
    """Parameter 参与算术运算时生成 Expr（行为类似 Signal）。"""
    le = _to_expr(lhs)
    re = _to_expr(rhs)
    w = width if width is not None else max(le.width, re.width) + 1
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
        n.elif_bodies = [(_subst_genvar_in_expr(c, var_name, value),
                          [_subst_genvar_in_stmt(s, var_name, value) for s in b])
                         for c, b in stmt.elif_bodies]
        return n
    if isinstance(stmt, SwitchNode):
        n = SwitchNode(_subst_genvar_in_expr(stmt.expr, var_name, value))
        n.cases = [(_subst_genvar_in_expr(v, var_name, value),
                    [_subst_genvar_in_stmt(s, var_name, value) for s in b]) for v, b in stmt.cases]
        n.default_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.default_body]
        return n
    if isinstance(stmt, ForGenNode):
        n = ForGenNode(stmt.var_name, stmt.start, stmt.end, stmt.step)
        n.body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.body]
        return n
    if isinstance(stmt, GenIfNode):
        n = GenIfNode(_subst_genvar_in_expr(stmt.cond, var_name, value))
        n.then_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.then_body]
        n.else_body = [_subst_genvar_in_stmt(s, var_name, value) for s in stmt.else_body]
        n.elif_bodies = [(_subst_genvar_in_expr(c, var_name, value),
                          [_subst_genvar_in_stmt(s, var_name, value) for s in b])
                         for c, b in stmt.elif_bodies]
        return n
    if isinstance(stmt, WhenNode):
        n = WhenNode()
        n.branches = [(_subst_genvar_in_expr(c, var_name, value) if c is not None else None,
                       [_subst_genvar_in_stmt(s, var_name, value) for s in b])
                      for c, b in stmt.branches]
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
            n.elif_bodies = [(_rename_expr(c, mapping, mem_rename, arr_rename),
                              [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in b])
                             for c, b in stmt.elif_bodies]
            return n
        if isinstance(stmt, SwitchNode):
            n = SwitchNode(_rename_expr(stmt.expr, mapping, mem_rename, arr_rename))
            n.cases = [(_rename_expr(v, mapping, mem_rename, arr_rename), [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in b]) for v, b in stmt.cases]
            n.default_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.default_body]
            return n
        if isinstance(stmt, ForGenNode):
            n = ForGenNode(stmt.var_name, stmt.start, stmt.end, stmt.step)
            n.body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.body]
            return n
        if isinstance(stmt, GenIfNode):
            n = GenIfNode(_rename_expr(stmt.cond, mapping, mem_rename, arr_rename))
            n.then_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.then_body]
            n.else_body = [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in stmt.else_body]
            n.elif_bodies = [(_rename_expr(c, mapping, mem_rename, arr_rename),
                              [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in b])
                             for c, b in stmt.elif_bodies]
            return n
        if isinstance(stmt, WhenNode):
            n = WhenNode()
            n.branches = [(_rename_expr(c, mapping, mem_rename, arr_rename) if c is not None else None,
                           [_rename_stmt(s, mapping, mem_rename, arr_rename) for s in b])
                          for c, b in stmt.branches]
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

        latch = []
        for body in sub_copy._latch_blocks:
            latch.append([_rename_stmt(s, mapping, mem_rename, arr_rename) for s in body])

        for port_name, expr in stmt.port_map.items():
            port_sig = sub_copy._inputs.get(port_name) or sub_copy._outputs.get(port_name) or sub_copy._wires.get(port_name)
            if port_sig is None:
                continue
            new_sig = mapping[port_sig]
            if port_name in sub_copy._inputs:
                top_stmts.append(Assign(new_sig, expr, blocking=True))
            else:
                top_stmts.append(Assign(expr, new_sig, blocking=True))

        return top_stmts, comb, latch, seq

    def _process_stmts(stmts, prefix="", mode="top"):
        """mode: 'top' | 'comb' | 'seq'"""
        top_stmts = []
        new_body = []
        extra_comb = []
        extra_latch = []
        extra_seq = []
        for stmt in stmts:
            if isinstance(stmt, SubmoduleInst):
                ts, cb, lb, sb = _inline_submodule(stmt, f"{prefix}{stmt.name}_")
                top_stmts.extend(ts)
                extra_comb.extend(cb)
                extra_latch.extend(lb)
                extra_seq.extend(sb)
            elif isinstance(stmt, ForGenNode):
                for i in range(stmt.start, stmt.end, stmt.step):
                    unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                    t, b, c, l, s2 = _process_stmts(unrolled, f"{prefix}{stmt.var_name}{i}_", mode=mode)
                    top_stmts.extend(t)
                    new_body.extend(b)
                    extra_comb.extend(c)
                    extra_latch.extend(l)
                    extra_seq.extend(s2)
            elif isinstance(stmt, IfNode):
                n = IfNode(stmt.cond)
                t1, b1, c1, l1, s1 = _process_stmts(stmt.then_body, prefix, mode)
                top_stmts.extend(t1)
                n.then_body = b1
                for cond, body in stmt.elif_bodies:
                    t_e, b_e, c_e, l_e, s_e = _process_stmts(body, prefix, mode)
                    top_stmts.extend(t_e)
                    n.elif_bodies.append((cond, b_e))
                    extra_comb.extend(c_e)
                    extra_latch.extend(l_e)
                    extra_seq.extend(s_e)
                t2, b2, c2, l2, s2 = _process_stmts(stmt.else_body, prefix, mode)
                top_stmts.extend(t2)
                n.else_body = b2
                extra_comb.extend(c1)
                extra_comb.extend(c2)
                extra_latch.extend(l1)
                extra_latch.extend(l2)
                extra_seq.extend(s1)
                extra_seq.extend(s2)
                new_body.append(n)
            elif isinstance(stmt, SwitchNode):
                n = SwitchNode(stmt.expr)
                case_bodies = []
                for v, body in stmt.cases:
                    t, b, c, l, s2 = _process_stmts(body, prefix, mode)
                    top_stmts.extend(t)
                    case_bodies.append((v, b))
                    extra_comb.extend(c)
                    extra_latch.extend(l)
                    extra_seq.extend(s2)
                t, b, c, l, s2 = _process_stmts(stmt.default_body, prefix, mode)
                top_stmts.extend(t)
                n.cases = case_bodies
                n.default_body = b
                extra_comb.extend(c)
                extra_latch.extend(l)
                extra_seq.extend(s2)
                new_body.append(n)
            elif isinstance(stmt, GenIfNode):
                if mode == "top":
                    new_body.append(stmt)
                else:
                    n = IfNode(stmt.cond)
                    t1, b1, c1, l1, s1 = _process_stmts(stmt.then_body, prefix, mode)
                    top_stmts.extend(t1)
                    n.then_body = b1
                    extra_comb.extend(c1)
                    extra_latch.extend(l1)
                    extra_seq.extend(s1)
                    for cond, body in stmt.elif_bodies:
                        t_e, b_e, c_e, l_e, s_e = _process_stmts(body, prefix, mode)
                        top_stmts.extend(t_e)
                        n.elif_bodies.append((cond, b_e))
                        extra_comb.extend(c_e)
                        extra_latch.extend(l_e)
                        extra_seq.extend(s_e)
                    t2, b2, c2, l2, s2 = _process_stmts(stmt.else_body, prefix, mode)
                    top_stmts.extend(t2)
                    n.else_body = b2
                    extra_comb.extend(c2)
                    extra_latch.extend(l2)
                    extra_seq.extend(s2)
                    new_body.append(n)
            else:
                new_body.append(stmt)
        return top_stmts, new_body, extra_comb, extra_latch, extra_seq

    t, b, c, l, s = _process_stmts(module._top_level, mode="top")
    flat._top_level.extend(t)
    flat._top_level.extend(b)
    flat._comb_blocks.extend(c)
    flat._latch_blocks.extend(l)
    flat._seq_blocks.extend(s)

    for body in module._comb_blocks:
        t, b, c, l, s = _process_stmts(body, mode="comb")
        flat._top_level.extend(t)
        if b:
            flat._comb_blocks.append(b)
        flat._comb_blocks.extend(c)
        flat._latch_blocks.extend(l)
        flat._seq_blocks.extend(s)

    for body in module._latch_blocks:
        t, b, c, l, s = _process_stmts(body, mode="latch")
        flat._top_level.extend(t)
        if b:
            flat._latch_blocks.append(b)
        flat._comb_blocks.extend(c)
        flat._latch_blocks.extend(l)
        flat._seq_blocks.extend(s)

    for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
        t, b, c, l, s = _process_stmts(body, mode="seq")
        flat._top_level.extend(t)
        if b:
            flat._seq_blocks.append((clk, rst, reset_async, reset_active_low, b))
        flat._comb_blocks.extend(c)
        flat._latch_blocks.extend(l)
        flat._seq_blocks.extend(s)

    return flat
