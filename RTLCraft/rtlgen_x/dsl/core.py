"""
rtlgen_x.dsl.core — 基础信号、AST 与模块容器

提供 Signal / Input / Output / Wire / Reg、Parameter、Module 以及全局上下文管理。
"""
from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from rtlgen_x.dsl.entity import IREntity

# Re-export from rtlgen_x.dsl.logic so DSL files can import everything from core.
# Deferred to avoid circular import (logic.py imports from core.py).
# Mux/Cat/Rep/SRA are not defined in core.py (only Mux as Expr class above),
# so lazy-import pulls in the logic function versions that auto-infer width.
def __getattr__(name: str):
    if name in ("If", "Else", "Elif", "Switch", "Cat", "Rep", "SRA"):
        from rtlgen_x.dsl.logic import If, Else, Elif, Switch, Cat, Rep, SRA
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
        self.enum_value: Optional["EnumValue"] = None

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


@dataclass(frozen=True)
class EnumValue:
    """One named literal belonging to an ``EnumType``."""

    enum_type: "EnumType"
    name: str
    value: int

    @property
    def width(self) -> int:
        return self.enum_type.width

    def as_const(self) -> Const:
        const = Const(self.value, self.width)
        const.enum_value = self
        return const


@dataclass(frozen=True)
class EnumType:
    """A compact hardware enum with stable literal names and encodings."""

    name: str
    members: Tuple[EnumValue, ...]
    width: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("enum name must not be empty")
        if not self.members:
            raise ValueError("enum must contain at least one member")

    @classmethod
    def define(
        cls,
        name: str,
        member_names: List[str] | Tuple[str, ...],
        *,
        width: Optional[int] = None,
        values: Optional[Dict[str, int]] = None,
    ) -> "EnumType":
        """Define one enum type from member names and optional encodings."""

        ordered_names = tuple(str(member_name) for member_name in member_names)
        if not ordered_names:
            raise ValueError("enum must contain at least one member")
        if len(set(ordered_names)) != len(ordered_names):
            raise ValueError("enum member names must be unique")
        value_map: Dict[str, int] = {}
        if values:
            value_map.update({str(k): int(v) for k, v in values.items()})
        next_value = 0
        encoded_values: List[int] = []
        for member_name in ordered_names:
            if member_name in value_map:
                encoded = value_map[member_name]
            else:
                while next_value in encoded_values:
                    next_value += 1
                encoded = next_value
            if encoded < 0:
                raise ValueError("enum values must be >= 0")
            encoded_values.append(encoded)
            next_value = max(next_value, encoded + 1)
        resolved_width = width or max(max(encoded_values).bit_length(), 1)
        if resolved_width < 1:
            raise ValueError("enum width must be >= 1")
        if any(encoded >= (1 << resolved_width) for encoded in encoded_values):
            raise ValueError("enum value does not fit within the declared width")

        placeholder = object.__new__(cls)
        members = tuple(
            EnumValue(enum_type=placeholder, name=member_name, value=encoded)
            for member_name, encoded in zip(ordered_names, encoded_values)
        )
        object.__setattr__(placeholder, "name", name)
        object.__setattr__(placeholder, "members", members)
        object.__setattr__(placeholder, "width", resolved_width)
        rebound_members = tuple(
            EnumValue(enum_type=placeholder, name=member.name, value=member.value)
            for member in members
        )
        object.__setattr__(placeholder, "members", rebound_members)
        return placeholder

    def member(self, name: str) -> EnumValue:
        for member in self.members:
            if member.name == name:
                return member
        raise KeyError(f"unknown enum member '{name}' for enum '{self.name}'")

    def __getattr__(self, name: str) -> EnumValue:
        try:
            return self.member(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from exc

    def values(self) -> Tuple[EnumValue, ...]:
        return self.members


@dataclass(frozen=True)
class PackedStructField:
    """One field inside a packed struct type."""

    struct_type: "PackedStructType"
    name: str
    width: int
    hi: int
    lo: int
    enum_type: Optional[EnumType] = None


@dataclass(frozen=True)
class PackedStructType:
    """A compact packed-struct type with stable field layout."""

    name: str
    fields: Tuple[PackedStructField, ...]
    width: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("struct name must not be empty")
        if not self.fields:
            raise ValueError("struct must contain at least one field")

    @classmethod
    def define(
        cls,
        name: str,
        field_specs: List[Tuple[Any, ...]] | Tuple[Tuple[Any, ...], ...],
    ) -> "PackedStructType":
        """Define one packed struct from ordered MSB-to-LSB field specs.

        Supported field forms:

        - ``("opcode", 4)``
        - ``("state", state_enum)``
        - ``("state", 2, state_enum)``
        """

        ordered_specs = tuple(field_specs)
        if not ordered_specs:
            raise ValueError("struct must contain at least one field")

        parsed_specs: List[Tuple[str, int, Optional[EnumType]]] = []
        seen_names: Set[str] = set()
        for spec in ordered_specs:
            if not isinstance(spec, (list, tuple)) or len(spec) not in (2, 3):
                raise TypeError("struct field specs must be 2- or 3-tuples")
            field_name = str(spec[0])
            if not field_name:
                raise ValueError("struct field name must not be empty")
            if field_name in seen_names:
                raise ValueError("struct field names must be unique")
            seen_names.add(field_name)

            enum_type: Optional[EnumType]
            if len(spec) == 2:
                width_or_enum = spec[1]
                if isinstance(width_or_enum, EnumType):
                    enum_type = width_or_enum
                    field_width = enum_type.width
                else:
                    enum_type = None
                    field_width = int(width_or_enum)
            else:
                field_width = int(spec[1])
                enum_type = spec[2]
                if enum_type is not None and not isinstance(enum_type, EnumType):
                    raise TypeError("struct field enum_type must be an EnumType or None")
                if enum_type is not None and field_width != enum_type.width:
                    raise ValueError("struct field width must match the enum field width")
            if field_width < 1:
                raise ValueError("struct field width must be >= 1")
            parsed_specs.append((field_name, field_width, enum_type))

        total_width = sum(field_width for _, field_width, _ in parsed_specs)
        placeholder = object.__new__(cls)
        remaining = total_width
        fields = []
        for field_name, field_width, enum_type in parsed_specs:
            remaining -= field_width
            lo = remaining
            hi = lo + field_width - 1
            fields.append(
                PackedStructField(
                    struct_type=placeholder,
                    name=field_name,
                    width=field_width,
                    hi=hi,
                    lo=lo,
                    enum_type=enum_type,
                )
            )
        object.__setattr__(placeholder, "name", name)
        object.__setattr__(placeholder, "fields", tuple(fields))
        object.__setattr__(placeholder, "width", total_width)
        rebound_fields = tuple(
            PackedStructField(
                struct_type=placeholder,
                name=field.name,
                width=field.width,
                hi=field.hi,
                lo=field.lo,
                enum_type=field.enum_type,
            )
            for field in fields
        )
        object.__setattr__(placeholder, "fields", rebound_fields)
        return placeholder

    def field(self, name: str) -> PackedStructField:
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError(f"unknown struct field '{name}' for struct '{self.name}'")

    def __getattr__(self, name: str) -> PackedStructField:
        try:
            return self.field(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from exc

    def field_names(self) -> Tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    def pack(self, **field_values: Any) -> "Signal":
        expected = set(self.field_names())
        provided = set(field_values)
        missing = tuple(field.name for field in self.fields if field.name not in field_values)
        extra = tuple(sorted(provided - expected))
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"extra={extra}")
            raise ValueError(
                f"struct pack for '{self.name}' requires exactly the declared fields ({', '.join(details)})"
            )

        packed_exprs: List[Expr] = []
        for field in self.fields:
            value = field_values[field.name]
            if isinstance(value, EnumValue):
                if field.enum_type is not None and value.enum_type is not field.enum_type:
                    raise ValueError(
                        f"struct field '{field.name}' expects enum '{field.enum_type.name}', "
                        f"got '{value.enum_type.name}'"
                    )
            expr = _coerce_expr_width(_to_expr(value), field.width, context=f"{self.name}.{field.name}")
            packed_exprs.append(expr)

        signal = Signal(name=f"{self.name}_packed", struct_type=self)
        signal._expr = Concat(packed_exprs, self.width)
        return signal


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


def _coerce_expr_width(expr: Expr, width: int, *, context: str) -> Expr:
    if expr.width == width:
        return expr
    if expr.width < width:
        if isinstance(expr, Const):
            widened = Const(expr.value, width)
            widened.enum_value = getattr(expr, "enum_value", None)
            return widened
        raise ValueError(f"{context} expects width {width}, got {expr.width}")
    raise ValueError(f"{context} expects width {width}, got {expr.width}")


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


@dataclass(frozen=True)
class ConnectivitySite:
    """Source-mapped statement site for a connectivity fact."""

    kind: str
    phase: str
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class SignalDriver:
    """One structural writer of a DSL signal."""

    signal: str
    target_kind: str
    phase: str
    source_expr_kind: str
    source_signals: Tuple[str, ...]
    source_memories: Tuple[str, ...]
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class StateWriter:
    """A sequential or latch writer for a state element."""

    signal: str
    phase: str
    clock: Optional[str]
    reset: Optional[str]
    reset_async: bool
    reset_active_low: bool
    source_expr_kind: str
    source_signals: Tuple[str, ...]
    source_memories: Tuple[str, ...]
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class MemoryAccess:
    """One read or write touching a declared memory/array."""

    memory: str
    access: str
    phase: str
    target: Optional[str] = None
    clock: Optional[str] = None
    reset: Optional[str] = None
    reset_async: bool = False
    reset_active_low: bool = False
    addr_signals: Tuple[str, ...] = ()
    value_signals: Tuple[str, ...] = ()
    byte_enable_signals: Tuple[str, ...] = ()
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class PortConnection:
    """A parent/submodule port binding."""

    instance: str
    module: str
    port: str
    direction: str
    expr_kind: str
    connected_signals: Tuple[str, ...]
    connected_memories: Tuple[str, ...]


@dataclass(frozen=True)
class ModuleInstancePath:
    """Hierarchy node description for one module instance."""

    path: str
    module_name: str
    type_name: str
    parent_path: Optional[str]
    child_instances: Tuple[str, ...]


@dataclass(frozen=True)
class ModuleConnectivityReport:
    """Structured hierarchy/connectivity summary for a DSL module."""

    hierarchy: Tuple[ModuleInstancePath, ...]
    signal_drivers: Tuple[SignalDriver, ...]
    state_writers: Tuple[StateWriter, ...]
    memory_accesses: Tuple[MemoryAccess, ...]
    port_connections: Tuple[PortConnection, ...]

    def drivers_of(self, signal_name: str) -> Tuple[SignalDriver, ...]:
        return tuple(driver for driver in self.signal_drivers if driver.signal == signal_name)

    def writers_of(self, signal_name: str) -> Tuple[StateWriter, ...]:
        return tuple(writer for writer in self.state_writers if writer.signal == signal_name)

    def accesses_of(self, memory_name: str) -> Tuple[MemoryAccess, ...]:
        return tuple(access for access in self.memory_accesses if access.memory == memory_name)


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
    def __init__(
        self,
        mem_name: str,
        addr: Expr,
        value: Expr,
        *,
        byte_enable: Optional[Expr] = None,
    ):
        self.mem_name = mem_name
        self.addr = addr
        self.value = value
        self.byte_enable = byte_enable
        self.source_location: Optional[SourceLoc] = Context._capture_location()


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
        self.source_location: Optional[SourceLoc] = Context._capture_location()


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
        self.source_location: Optional[SourceLoc] = Context._capture_location()


class MemProxy:
    """Memory 读写代理对象，支持 mem[addr] 作为表达式以及 mem[addr] <<= value 写入。"""

    def __init__(
        self,
        mem_name: str,
        addr: Expr,
        width: int,
        *,
        byte_enable_granularity: Optional[int] = None,
    ):
        self.mem_name = mem_name
        self.addr = addr
        self.width = width
        self.byte_enable_granularity = byte_enable_granularity
        self._read_expr = MemRead(mem_name, addr, width)
        self._written = False

    def _append_write_stmt(self, stmt: MemWrite) -> None:
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError("Memory write outside of any module or logic block")

    def __ilshift__(self, value: Any):
        stmt = MemWrite(self.mem_name, self.addr, _to_expr(value))
        self._append_write_stmt(stmt)
        self._written = True
        return self

    def write(self, value: Any, *, byte_enable: Any):
        if self.byte_enable_granularity is None:
            raise ValueError(
                f"memory '{self.mem_name}' does not declare byte_enable_granularity, "
                "so byte-enable writes are not allowed"
            )
        stmt = MemWrite(
            self.mem_name,
            self.addr,
            _to_expr(value),
            byte_enable=_to_expr(byte_enable),
        )
        self._append_write_stmt(stmt)
        self._written = True
        return self


class Comment:
    """Verilog 注释节点。"""

    def __init__(self, text: str):
        self.text = text


class Memory:
    """硬件存储器（生成 Verilog reg [width-1:0] name [0:depth-1]）。

    ``read_during_write`` captures same-address read/write intent for the
    executable backends. Supported values:

    - ``"write_first"``: same-step read returns the newly written value after
      sequential state update when outputs are recomputed post-state.
    - ``"read_first"``: same-step read continues to observe the pre-write value.

    ``read_ports`` / ``write_ports`` / ``read_style`` / ``read_latency`` capture
    authoring-level storage intent. The current executable subset still only
    closes the simple comb-read / seq-write case, but these fields make the
    intended contract explicit and allow lowering to fail fast on unsupported
    storage shapes.

    ``byte_enable_granularity`` captures partial-write lane intent. For
    example, a 32-bit memory with ``byte_enable_granularity=8`` declares four
    byte-enable lanes. This contract is explicit today, but still only
    partially closed across the full stack.
    """

    _SUPPORTED_READ_DURING_WRITE = {"write_first", "read_first"}
    _SUPPORTED_READ_STYLES = {"async", "sync"}

    def __init__(
        self,
        width: int,
        depth: int,
        name: str = "",
        init_file: Optional[str] = None,
        init_zero: bool = False,
        init_data: Optional[list] = None,
        *,
        read_during_write: str = "write_first",
        read_ports: int = 1,
        write_ports: int = 1,
        read_style: str = "async",
        read_latency: int = 0,
        byte_enable_granularity: Optional[int] = None,
    ):
        if read_during_write not in self._SUPPORTED_READ_DURING_WRITE:
            supported = ", ".join(sorted(self._SUPPORTED_READ_DURING_WRITE))
            raise ValueError(
                f"unsupported read_during_write policy {read_during_write!r}; "
                f"expected one of: {supported}"
            )
        if int(read_ports) < 1:
            raise ValueError("memory read_ports must be >= 1")
        if int(write_ports) < 1:
            raise ValueError("memory write_ports must be >= 1")
        if read_style not in self._SUPPORTED_READ_STYLES:
            supported = ", ".join(sorted(self._SUPPORTED_READ_STYLES))
            raise ValueError(
                f"unsupported read_style {read_style!r}; expected one of: {supported}"
            )
        if int(read_latency) < 0:
            raise ValueError("memory read_latency must be >= 0")
        if byte_enable_granularity is not None:
            if int(byte_enable_granularity) < 1:
                raise ValueError("memory byte_enable_granularity must be >= 1")
            if width % int(byte_enable_granularity) != 0:
                raise ValueError(
                    "memory width must be divisible by byte_enable_granularity"
                )
        self.width = width
        self.depth = depth
        self.name = name
        self.init_file = init_file
        self.init_zero = init_zero
        self.init_data = init_data
        self.read_during_write = read_during_write
        self.read_ports = int(read_ports)
        self.write_ports = int(write_ports)
        self.read_style = read_style
        self.read_latency = int(read_latency)
        self.byte_enable_granularity = (
            int(byte_enable_granularity)
            if byte_enable_granularity is not None
            else None
        )
        self.addr_width = max(depth.bit_length(), 1)

    @property
    def byte_enable_width(self) -> Optional[int]:
        if self.byte_enable_granularity is None:
            return None
        return self.width // self.byte_enable_granularity

    def __getitem__(self, addr: Any):
        return MemProxy(
            self.name,
            _to_expr(addr),
            self.width,
            byte_enable_granularity=self.byte_enable_granularity,
        )

    def write(self, addr: Any, value: Any, *, byte_enable: Any):
        if self.byte_enable_granularity is None:
            raise ValueError(
                f"memory '{self.name}' does not declare byte_enable_granularity, "
                "so byte-enable writes are not allowed"
            )
        proxy = self[addr]
        proxy.write(value, byte_enable=byte_enable)

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


@dataclass(frozen=True)
class ResetDomainSpec:
    """Authoring-level reset-domain declaration.

    This is a DSL-facing object. It captures reset polarity and async/sync
    intent before the design is lowered into the executable simulator model.
    """

    name: str
    signal: Signal
    reset_async: bool = False
    reset_active_low: bool = False

    def __post_init__(self):
        if not self.name:
            raise ValueError("reset domain name must not be empty")
        if not isinstance(self.signal, Signal):
            raise TypeError("reset domain signal must be a DSL Signal")


@dataclass(frozen=True)
class ClockDomainSpec:
    """Authoring-level clock-domain declaration for DSL sequential logic."""

    name: str
    clock: Signal
    reset: Optional[ResetDomainSpec] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("clock domain name must not be empty")
        if not isinstance(self.clock, Signal):
            raise TypeError("clock domain clock must be a DSL Signal")

    @property
    def reset_signal(self) -> Optional[Signal]:
        return self.reset.signal if self.reset is not None else None

    @property
    def reset_async(self) -> bool:
        return self.reset.reset_async if self.reset is not None else False

    @property
    def reset_active_low(self) -> bool:
        return self.reset.reset_active_low if self.reset is not None else False


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
    if isinstance(val, EnumValue):
        return val.as_const()
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

    def __init__(
        self,
        width: int = 1,
        name: str = "",
        signed: bool = False,
        init_value: Optional[int] = None,
        *,
        enum_type: Optional[EnumType] = None,
        struct_type: Optional[PackedStructType] = None,
    ):
        IREntity.__init__(self, name)
        if enum_type is not None and struct_type is not None:
            raise ValueError("signal cannot be both enum-typed and struct-typed")
        resolved_width = width
        if enum_type is not None:
            resolved_width = enum_type.width
        elif struct_type is not None:
            resolved_width = struct_type.width
        self.width = resolved_width
        self.name = name
        self.signed = signed
        self.enum_type = enum_type
        self.struct_type = struct_type
        if init_value is not None and isinstance(init_value, EnumValue):
            if enum_type is not None and init_value.enum_type is not enum_type:
                raise ValueError("enum init_value must belong to the signal enum_type")
            self.init_enum_value = init_value
            init_value = init_value.value
        else:
            self.init_enum_value = None
        self.init_value = init_value
        self._expr = Ref(self)
        self._driven_by: Optional[str] = None  # "comb" | "seq"
        self._parent_module: Optional["Module"] = None  # owning module

    def __hash__(self):
        return id(self)

    def __getattr__(self, key: str):
        try:
            struct_type = object.__getattribute__(self, "struct_type")
        except AttributeError as exc:
            raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {key!r}") from exc
        if struct_type is not None:
            try:
                field = struct_type.field(key)
            except KeyError as exc:
                raise AttributeError(str(exc)) from exc
            field_sig = Signal(width=field.width, enum_type=field.enum_type)
            if field.hi == field.lo:
                field_sig._expr = Slice(_to_expr(self), field.hi, field.lo)
            else:
                field_sig._expr = Slice(_to_expr(self), field.hi, field.lo)
            field_sig._parent_module = self._parent_module
            field_sig._field_parent = self
            field_sig._field_spec = field
            return field_sig
        raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {key!r}")

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


class EnumLocalParam(LocalParam):
    """Named enum literal emitted as a localparam with explicit enum provenance."""

    def __init__(self, enum_value: EnumValue, name: str = ""):
        super().__init__(enum_value.value, name=name)
        self.enum_type = enum_value.enum_type
        self.enum_value = enum_value


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
                normalized = fname.replace("\\", "/")
                if not normalized.endswith("/rtlgen/core.py") and not normalized.endswith("/rtlgen_x/dsl/core.py"):
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
        self._seq_blocks: List[Tuple[Signal, Optional[Signal], bool, bool, List[Any]]] = []
        self._clock_domain_specs: Dict[str, ClockDomainSpec] = {}
        self._reset_domain_specs: Dict[str, ResetDomainSpec] = {}
        self._top_level: List[Any] = []
        self._param_bindings: Dict[str, Any] = dict(param_bindings) if param_bindings else {}
        self._module_comments: List[str] = []
        self._module_assertions: List[Tuple[str, str]] = []
        self._module_suggestions: List[str] = []
        self._module_doc: Optional[ModuleDoc] = None
        self._parent: Optional["Module"] = None
        self._design_intent: Optional[IntentContext] = None
        self._bundles: Dict[str, Any] = {}
        self._enum_types: Dict[str, EnumType] = {}
        self._struct_types: Dict[str, PackedStructType] = {}

    @staticmethod
    def _format_reset_semantics(*, reset_async: bool, reset_active_low: bool) -> str:
        edge = "async" if reset_async else "sync"
        polarity = "active-low" if reset_active_low else "active-high"
        return f"{edge}, {polarity}"

    def _known_reset_domain_names(self) -> str:
        names = tuple(self._reset_domain_specs.keys())
        return ", ".join(names) if names else "none"

    def _known_clock_domain_names(self) -> str:
        names = tuple(self._clock_domain_specs.keys())
        return ", ".join(names) if names else "none"

    def _known_clock_domain_aliases(self) -> str:
        aliases = tuple(
            dict.fromkeys(
                spec.clock.name
                for spec in self._clock_domain_specs.values()
                if getattr(spec.clock, "name", "")
            )
        )
        return ", ".join(aliases) if aliases else "none"

    def _resolve_declared_clock_domain(self, domain: str) -> Optional[ClockDomainSpec]:
        declared = self._clock_domain_specs.get(domain)
        if declared is not None:
            return declared
        alias_matches = [
            spec
            for spec in self._clock_domain_specs.values()
            if getattr(spec.clock, "name", None) == domain
        ]
        if len(alias_matches) == 1:
            return alias_matches[0]
        return None

    def _format_known_clock_domains(self) -> str:
        return (
            f"Known clock domains: {self._known_clock_domain_names()}. "
            f"Known clock aliases: {self._known_clock_domain_aliases()}"
        )

    def _find_matching_reset_domain(
        self,
        reset: Signal,
        *,
        reset_async: bool,
        reset_active_low: bool,
    ) -> Optional[ResetDomainSpec]:
        for spec in self._reset_domain_specs.values():
            if (
                spec.signal.name == reset.name
                and spec.reset_async == reset_async
                and spec.reset_active_low == reset_active_low
            ):
                return spec
        return None

    def add_comment(self, text: str):
        """向模块添加顶层注释，生成 Verilog 时会被放在模块头部。"""
        self._module_comments.append(text)

    def add_assertion(self, name: str, expr: str):
        """向模块添加 SVA 断言 (name, expression_string)。"""
        self._module_assertions.append((name, expr))

    def add_suggestions(self, suggestions: List[str]):
        """向模块添加优化建议，生成 Verilog 时会被转为注释。"""
        self._module_suggestions.extend(suggestions)

    def add_enum_type(self, enum_type: EnumType) -> EnumType:
        """Register one enum type for readable Verilog emission."""

        existing = self._enum_types.get(enum_type.name)
        if existing is not None and existing != enum_type:
            raise ValueError(f"enum type '{enum_type.name}' is already registered with different members")
        self._enum_types[enum_type.name] = enum_type
        for member in enum_type.members:
            localparam_name = f"{enum_type.name.upper()}_{member.name}"
            if localparam_name not in self._params:
                self._params[localparam_name] = EnumLocalParam(member, name=localparam_name)
        return enum_type

    def add_struct_type(self, struct_type: PackedStructType) -> PackedStructType:
        """Register one packed struct type for readable authoring/emission metadata."""

        existing = self._struct_types.get(struct_type.name)
        if existing is not None and existing != struct_type:
            raise ValueError(f"struct type '{struct_type.name}' is already registered with different fields")
        self._struct_types[struct_type.name] = struct_type
        for field in struct_type.fields:
            if field.enum_type is not None:
                self.add_enum_type(field.enum_type)
        return struct_type

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
        elif isinstance(value, EnumType):
            object.__setattr__(self, key, value)
            self.add_enum_type(value)
        elif isinstance(value, PackedStructType):
            object.__setattr__(self, key, value)
            self.add_struct_type(value)
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
        elif hasattr(value, "_signals") and hasattr(value, "_directions"):
            object.__setattr__(self, key, value)
            self._bundles[key] = value
            for field_name, sig in value._signals.items():
                if not sig.name:
                    sig.name = f"{key}_{field_name}"
                sig._parent_module = self
                if isinstance(sig, Input):
                    self._inputs[sig.name] = sig
                elif isinstance(sig, Output):
                    self._outputs[sig.name] = sig
                elif isinstance(sig, Wire):
                    self._wires[sig.name] = sig
                elif isinstance(sig, Reg):
                    self._regs[sig.name] = sig
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

    def bundle(self, key: str, bundle: Any):
        """Register a protocol bundle on this module and return it."""
        setattr(self, key, bundle)
        return bundle

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

    def reset_domain(
        self,
        name: str,
        reset: Signal,
        *,
        reset_async: bool = False,
        reset_active_low: bool = False,
    ) -> ResetDomainSpec:
        """Declare a named reset domain for later reuse in clock domains."""

        spec = ResetDomainSpec(
            name=name,
            signal=reset,
            reset_async=reset_async,
            reset_active_low=reset_active_low,
        )
        existing = self._reset_domain_specs.get(name)
        if existing is not None and existing != spec:
            raise ValueError(
                f"reset domain '{name}' is already declared on module '{self.name}' as "
                f"signal '{existing.signal.name}' "
                f"({self._format_reset_semantics(reset_async=existing.reset_async, reset_active_low=existing.reset_active_low)}); "
                f"cannot redeclare it as signal '{reset.name}' "
                f"({self._format_reset_semantics(reset_async=spec.reset_async, reset_active_low=spec.reset_active_low)})"
            )
        for other_name, other in self._reset_domain_specs.items():
            if other_name == name:
                continue
            if other.signal.name != reset.name:
                continue
            if (
                other.reset_async != spec.reset_async
                or other.reset_active_low != spec.reset_active_low
            ):
                raise ValueError(
                    f"reset signal '{reset.name}' is already declared by reset domain "
                    f"'{other_name}' on module '{self.name}' with "
                    f"{self._format_reset_semantics(reset_async=other.reset_async, reset_active_low=other.reset_active_low)} "
                    f"semantics; cannot redeclare it in reset domain '{name}' as "
                    f"{self._format_reset_semantics(reset_async=spec.reset_async, reset_active_low=spec.reset_active_low)}"
                )
        self._reset_domain_specs[name] = spec
        return spec

    def clock_domain(
        self,
        name: str,
        clock: Signal,
        reset: Optional[Union[Signal, ResetDomainSpec, str]] = None,
        *,
        reset_async: bool = False,
        reset_active_low: bool = False,
    ) -> ClockDomainSpec:
        """Declare a named clock domain for authoring-level sequential logic."""

        reset_spec: Optional[ResetDomainSpec]
        if isinstance(reset, ResetDomainSpec):
            if reset_async or reset_active_low:
                raise ValueError(
                    "reset_async/reset_active_low must not be overridden when reset is a ResetDomainSpec"
                )
            reset_spec = reset
        elif isinstance(reset, str):
            if reset_async or reset_active_low:
                raise ValueError(
                    "reset_async/reset_active_low must not be overridden when reset is a declared reset-domain name"
                )
            reset_spec = self._reset_domain_specs.get(reset)
            if reset_spec is None:
                raise ValueError(
                    f"reset domain '{reset}' must be declared on module '{self.name}' before use. "
                    f"Known reset domains: {self._known_reset_domain_names()}"
                )
        elif reset is None:
            reset_spec = None
        else:
            reset_spec = self._find_matching_reset_domain(
                reset,
                reset_async=reset_async,
                reset_active_low=reset_active_low,
            )
            if reset_spec is None:
                reset_spec = self.reset_domain(
                    f"{name}_reset",
                    reset,
                    reset_async=reset_async,
                    reset_active_low=reset_active_low,
                )
        spec = ClockDomainSpec(name=name, clock=clock, reset=reset_spec)
        existing = self._clock_domain_specs.get(name)
        if existing is not None and existing != spec:
            raise ValueError(
                f"clock domain '{name}' is already declared on module '{self.name}' as "
                f"clock '{existing.clock.name}'"
                + (
                    f", reset '{existing.reset_signal.name}' "
                    f"({self._format_reset_semantics(reset_async=existing.reset_async, reset_active_low=existing.reset_active_low)})"
                    if existing.reset_signal is not None
                    else ", without reset"
                )
                + "; cannot redeclare it as "
                + f"clock '{clock.name}'"
                + (
                    f", reset '{spec.reset_signal.name}' "
                    f"({self._format_reset_semantics(reset_async=spec.reset_async, reset_active_low=spec.reset_active_low)})"
                    if spec.reset_signal is not None
                    else ", without reset"
                )
            )
        for other_name, other in self._clock_domain_specs.items():
            if other_name == name:
                continue
            if other.clock.name == clock.name:
                raise ValueError(
                    f"clock signal '{clock.name}' is already owned by declared clock domain "
                    f"'{other_name}' on module '{self.name}'. Reuse that domain via "
                    f"seq_domain('{other_name}') instead of redeclaring it."
                )
        self._clock_domain_specs[name] = spec
        return spec

    @property
    def declared_reset_domains(self) -> Tuple[ResetDomainSpec, ...]:
        """Return author-declared reset domains in declaration order."""

        return tuple(self._reset_domain_specs.values())

    @property
    def declared_clock_domains(self) -> Tuple[ClockDomainSpec, ...]:
        """Return author-declared clock domains in declaration order."""

        return tuple(self._clock_domain_specs.values())

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

    def seq_domain(self, domain: Union[str, ClockDomainSpec]) -> _SeqContext:
        """Sequential logic context manager bound to a declared clock domain.

        Accepts either a previously returned :class:`ClockDomainSpec` or the
        declared domain name directly. String lookups also accept the declared
        domain's clock-signal alias when it resolves uniquely, which keeps
        multi-clock DSL authoring lighter around existing signal-centric code.
        """

        if isinstance(domain, str):
            declared = self._resolve_declared_clock_domain(domain)
            if declared is None:
                raise ValueError(
                    f"clock domain '{domain}' must be declared on module '{self.name}' before use. "
                    f"{self._format_known_clock_domains()}"
                )
        else:
            declared = self._clock_domain_specs.get(domain.name)
            if declared is None or declared != domain:
                raise ValueError(
                    f"clock domain '{domain.name}' must be declared on module '{self.name}' before use. "
                    f"{self._format_known_clock_domains()}"
                )
        return _SeqContext(
            self,
            declared.clock,
            declared.reset_signal,
            declared.reset_async,
            declared.reset_active_low,
        )


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

    def instantiate_with_bundles(
        self,
        submodule: "Module",
        name: str,
        params: Optional[Dict[str, Any]] = None,
        parent_bundles: Optional[Dict[str, Any]] = None,
        sub_bundles: Optional[Dict[str, Any]] = None,
        extra_ports: Optional[Dict[str, Union[Signal, Expr]]] = None,
        bundle_includes: Optional[Dict[str, tuple[str, ...]]] = None,
        bundle_excludes: Optional[Dict[str, tuple[str, ...]]] = None,
        auto_bundles: bool = True,
    ):
        """Instantiate a submodule using Bundle-based bulk connection.

        This is the Bundle-oriented sibling of ``instantiate_with_ifaces(...)``.
        It is intended for protocol bundles such as ``ReadyValid`` / ``ReqRsp`` /
        ``AXI4Lite`` where the authored connection should stay at the protocol
        object level rather than expanding a hand-written port map.

        The generated mapping uses the peer bundle's actual signal names, so
        prefixed bundle ports on the submodule side work naturally.
        """
        params = params or {}
        parent_bundles = dict(parent_bundles or {})
        sub_bundles = sub_bundles or {}
        extra_ports = extra_ports or {}
        bundle_includes = bundle_includes or {}
        bundle_excludes = bundle_excludes or {}

        resolved_parent_bundles: Dict[str, Any] = dict(parent_bundles)
        if auto_bundles:
            for bundle_name, sub_bundle in getattr(submodule, "_bundles", {}).items():
                if bundle_name in resolved_parent_bundles:
                    continue
                if not hasattr(self, bundle_name):
                    continue
                parent_bundle = getattr(self, bundle_name)
                if not (hasattr(parent_bundle, "_signals") and hasattr(parent_bundle, "instantiate_port_map")):
                    continue
                if type(parent_bundle) is not type(sub_bundle):
                    raise TypeError(
                        f"Auto-discovered bundle type mismatch on '{bundle_name}': "
                        f"{type(parent_bundle).__name__} vs {type(sub_bundle).__name__}"
                    )
                resolved_parent_bundles[bundle_name] = parent_bundle

        known_bundle_names = set(resolved_parent_bundles)
        unknown_includes = set(bundle_includes) - known_bundle_names
        unknown_excludes = set(bundle_excludes) - known_bundle_names
        if unknown_includes or unknown_excludes:
            unknown = tuple(sorted(unknown_includes | unknown_excludes))
            raise ValueError(
                f"bundle include/exclude keys {unknown} do not match the resolved parent bundles "
                f"{tuple(sorted(known_bundle_names))}"
            )

        port_map: Dict[str, Union[Signal, Expr]] = dict(extra_ports)
        for bundle_name, parent_bundle in resolved_parent_bundles.items():
            sub_bundle = sub_bundles.get(bundle_name)
            if sub_bundle is None:
                sub_bundle = getattr(submodule, bundle_name, None)
            if sub_bundle is None:
                raise ValueError(
                    f"submodule bundle '{bundle_name}' was not provided and is not present on "
                    f"module '{submodule.name}'"
                )
            if type(parent_bundle) is not type(sub_bundle):
                raise TypeError(
                    f"Bundle type mismatch on '{bundle_name}': "
                    f"{type(parent_bundle).__name__} vs {type(sub_bundle).__name__}"
                )
            if not hasattr(parent_bundle, "instantiate_port_map"):
                raise TypeError(
                    f"bundle '{bundle_name}' of type {type(parent_bundle).__name__} does not expose "
                    "instantiate_port_map(...)"
                )
            port_map.update(
                parent_bundle.instantiate_port_map(
                    sub_bundle,
                    include=bundle_includes.get(bundle_name),
                    exclude=bundle_excludes.get(bundle_name),
                )
            )

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

    def describe_hierarchy(self) -> Tuple[ModuleInstancePath, ...]:
        """Return a structural hierarchy summary rooted at this module."""

        return _describe_module_hierarchy(self)

    def analyze_connectivity(self) -> ModuleConnectivityReport:
        """Return a structured connectivity summary for this DSL module."""

        return _analyze_module_connectivity(self)


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


def _stmt_site(stmt: Any, *, kind: str, phase: str) -> ConnectivitySite:
    source_location = getattr(stmt, "source_location", None)
    return ConnectivitySite(
        kind=kind,
        phase=phase,
        source_file=getattr(source_location, "file", None),
        source_line=getattr(source_location, "line", None),
    )


def _copy_source_location(dst: Any, src: Any) -> Any:
    source_location = getattr(src, "source_location", None)
    if source_location is not None:
        setattr(dst, "source_location", source_location)
    return dst


def _expr_kind(expr: Any) -> str:
    if isinstance(expr, Signal):
        expr = expr._expr
    if isinstance(expr, Ref):
        return "ref"
    if isinstance(expr, Const):
        return "const"
    if isinstance(expr, BinOp):
        return f"binop:{expr.op}"
    if isinstance(expr, UnaryOp):
        return f"unary:{expr.op}"
    if isinstance(expr, Slice):
        return "slice"
    if isinstance(expr, PartSelect):
        return "partselect"
    if isinstance(expr, BitSelect):
        return "bitselect"
    if isinstance(expr, Concat):
        return "concat"
    if isinstance(expr, Mux):
        return "mux"
    if isinstance(expr, MemRead):
        return "memread"
    if isinstance(expr, ArrayRead):
        return "arrayread"
    if isinstance(expr, FunctionCall):
        return f"call:{expr.name}"
    return type(expr).__name__.lower()


def _expr_signal_names(expr: Any) -> Tuple[str, ...]:
    names: List[str] = []
    seen: Set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, Signal):
            visit(node._expr)
            return
        if isinstance(node, Ref):
            name = node.signal.name
            if name not in seen:
                seen.add(name)
                names.append(name)
            return
        if isinstance(node, BinOp):
            visit(node.lhs)
            visit(node.rhs)
            return
        if isinstance(node, UnaryOp):
            visit(node.operand)
            return
        if isinstance(node, Slice):
            visit(node.operand)
            return
        if isinstance(node, PartSelect):
            visit(node.operand)
            visit(node.offset)
            return
        if isinstance(node, BitSelect):
            visit(node.operand)
            visit(node.index)
            return
        if isinstance(node, Concat):
            for operand in node.operands:
                visit(operand)
            return
        if isinstance(node, Mux):
            visit(node.cond)
            visit(node.true_expr)
            visit(node.false_expr)
            return
        if isinstance(node, MemRead):
            visit(node.addr)
            return
        if isinstance(node, ArrayRead):
            visit(node.index)
            return
        if isinstance(node, FunctionCall):
            for arg in node.args:
                visit(arg)
            return

    visit(expr)
    return tuple(names)


def _expr_memory_names(expr: Any) -> Tuple[str, ...]:
    names: List[str] = []
    seen: Set[str] = set()

    def record(name: str) -> None:
        if name not in seen:
            seen.add(name)
            names.append(name)

    def visit(node: Any) -> None:
        if isinstance(node, Signal):
            visit(node._expr)
            return
        if isinstance(node, BinOp):
            visit(node.lhs)
            visit(node.rhs)
            return
        if isinstance(node, UnaryOp):
            visit(node.operand)
            return
        if isinstance(node, Slice):
            visit(node.operand)
            return
        if isinstance(node, PartSelect):
            visit(node.operand)
            visit(node.offset)
            return
        if isinstance(node, BitSelect):
            visit(node.operand)
            visit(node.index)
            return
        if isinstance(node, Concat):
            for operand in node.operands:
                visit(operand)
            return
        if isinstance(node, Mux):
            visit(node.cond)
            visit(node.true_expr)
            visit(node.false_expr)
            return
        if isinstance(node, MemRead):
            record(node.mem_name)
            visit(node.addr)
            return
        if isinstance(node, ArrayRead):
            record(node.array_name)
            visit(node.index)
            return
        if isinstance(node, FunctionCall):
            for arg in node.args:
                visit(arg)
            return

    visit(expr)
    return tuple(names)


def _assignment_target_info(target: Any) -> Tuple[Optional[str], str]:
    if isinstance(target, Signal):
        return target.name, target.__class__.__name__.lower()
    if isinstance(target, Ref):
        return target.signal.name, target.signal.__class__.__name__.lower()
    if isinstance(target, Slice):
        base = target.operand
        while isinstance(base, (Slice, PartSelect, BitSelect)):
            base = base.operand
        if isinstance(base, Ref):
            return base.signal.name, f"{base.signal.__class__.__name__.lower()}_slice"
        return None, "slice"
    if isinstance(target, PartSelect):
        base = target.operand
        while isinstance(base, (Slice, PartSelect, BitSelect)):
            base = base.operand
        if isinstance(base, Ref):
            return base.signal.name, f"{base.signal.__class__.__name__.lower()}_partselect"
        return None, "partselect"
    if isinstance(target, BitSelect):
        base = target.operand
        while isinstance(base, (Slice, PartSelect, BitSelect)):
            base = base.operand
        if isinstance(base, Ref):
            return base.signal.name, f"{base.signal.__class__.__name__.lower()}_bitselect"
        return None, "bitselect"
    return None, type(target).__name__.lower()


def _walk_stmt_list(
    stmts: List[Any],
    *,
    phase: str,
    clock: Optional[str],
    reset: Optional[str],
    reset_async: bool,
    reset_active_low: bool,
    signal_drivers: List[SignalDriver],
    state_writers: List[StateWriter],
    memory_accesses: List[MemoryAccess],
) -> None:
    for stmt in stmts:
        if isinstance(stmt, Assign):
            target_name, target_kind = _assignment_target_info(stmt.target)
            source_expr_kind = _expr_kind(stmt.value)
            source_signals = _expr_signal_names(stmt.value)
            source_memories = _expr_memory_names(stmt.value)
            site = _stmt_site(stmt, kind="assign", phase=phase)
            if target_name is not None:
                signal_drivers.append(
                    SignalDriver(
                        signal=target_name,
                        target_kind=target_kind,
                        phase=phase,
                        source_expr_kind=source_expr_kind,
                        source_signals=source_signals,
                        source_memories=source_memories,
                        source_file=site.source_file,
                        source_line=site.source_line,
                    )
                )
                if phase in {"seq", "latch"}:
                    state_writers.append(
                        StateWriter(
                            signal=target_name,
                            phase=phase,
                            clock=clock,
                            reset=reset,
                            reset_async=reset_async,
                            reset_active_low=reset_active_low,
                            source_expr_kind=source_expr_kind,
                            source_signals=source_signals,
                            source_memories=source_memories,
                            source_file=site.source_file,
                            source_line=site.source_line,
                        )
                    )
            for memory_name in source_memories:
                memory_accesses.append(
                    MemoryAccess(
                        memory=memory_name,
                        access="read",
                        phase=phase,
                        target=target_name,
                        clock=clock if phase in {"seq", "latch"} else None,
                        reset=reset if phase in {"seq", "latch"} else None,
                        reset_async=reset_async if phase in {"seq", "latch"} else False,
                        reset_active_low=reset_active_low if phase in {"seq", "latch"} else False,
                        addr_signals=(),
                        value_signals=source_signals,
                        source_file=site.source_file,
                        source_line=site.source_line,
                    )
                )
            continue
        if isinstance(stmt, IndexedAssign):
            site = _stmt_site(stmt, kind="indexed_assign", phase=phase)
            source_expr_kind = _expr_kind(stmt.value)
            value_signals = _expr_signal_names(stmt.value)
            value_memories = _expr_memory_names(stmt.value)
            index_signals = _expr_signal_names(stmt.index)
            signal_drivers.append(
                SignalDriver(
                    signal=stmt.target_signal.name,
                    target_kind=f"{stmt.target_signal.__class__.__name__.lower()}_bitselect",
                    phase=phase,
                    source_expr_kind=source_expr_kind,
                    source_signals=tuple(dict.fromkeys(index_signals + value_signals)),
                    source_memories=value_memories,
                    source_file=site.source_file,
                    source_line=site.source_line,
                )
            )
            if phase in {"seq", "latch"}:
                state_writers.append(
                    StateWriter(
                        signal=stmt.target_signal.name,
                        phase=phase,
                        clock=clock,
                        reset=reset,
                        reset_async=reset_async,
                        reset_active_low=reset_active_low,
                        source_expr_kind=source_expr_kind,
                        source_signals=tuple(dict.fromkeys(index_signals + value_signals)),
                        source_memories=value_memories,
                        source_file=site.source_file,
                        source_line=site.source_line,
                    )
                )
            for memory_name in value_memories:
                memory_accesses.append(
                    MemoryAccess(
                        memory=memory_name,
                        access="read",
                        phase=phase,
                        target=stmt.target_signal.name,
                        clock=clock if phase in {"seq", "latch"} else None,
                        reset=reset if phase in {"seq", "latch"} else None,
                        reset_async=reset_async if phase in {"seq", "latch"} else False,
                        reset_active_low=reset_active_low if phase in {"seq", "latch"} else False,
                        addr_signals=(),
                        value_signals=tuple(dict.fromkeys(index_signals + value_signals)),
                        source_file=site.source_file,
                        source_line=site.source_line,
                    )
                )
            continue
        if isinstance(stmt, MemWrite):
            site = _stmt_site(stmt, kind="mem_write", phase=phase)
            memory_accesses.append(
                MemoryAccess(
                    memory=stmt.mem_name,
                    access="write",
                    phase=phase,
                    clock=clock if phase in {"seq", "latch"} else None,
                    reset=reset if phase in {"seq", "latch"} else None,
                    reset_async=reset_async if phase in {"seq", "latch"} else False,
                    reset_active_low=reset_active_low if phase in {"seq", "latch"} else False,
                    addr_signals=_expr_signal_names(stmt.addr),
                    value_signals=_expr_signal_names(stmt.value),
                    byte_enable_signals=_expr_signal_names(stmt.byte_enable) if stmt.byte_enable is not None else (),
                    source_file=site.source_file,
                    source_line=site.source_line,
                )
            )
            continue
        if isinstance(stmt, ArrayWrite):
            site = _stmt_site(stmt, kind="array_write", phase=phase)
            memory_accesses.append(
                MemoryAccess(
                    memory=stmt.array_name,
                    access="write",
                    phase=phase,
                    clock=clock if phase in {"seq", "latch"} else None,
                    reset=reset if phase in {"seq", "latch"} else None,
                    reset_async=reset_async if phase in {"seq", "latch"} else False,
                    reset_active_low=reset_active_low if phase in {"seq", "latch"} else False,
                    addr_signals=_expr_signal_names(stmt.index),
                    value_signals=_expr_signal_names(stmt.value),
                    source_file=site.source_file,
                    source_line=site.source_line,
                )
            )
            continue
        if isinstance(stmt, IfNode):
            _walk_stmt_list(
                stmt.then_body,
                phase=phase,
                clock=clock,
                reset=reset,
                reset_async=reset_async,
                reset_active_low=reset_active_low,
                signal_drivers=signal_drivers,
                state_writers=state_writers,
                memory_accesses=memory_accesses,
            )
            for _, body in stmt.elif_bodies:
                _walk_stmt_list(
                    body,
                    phase=phase,
                    clock=clock,
                    reset=reset,
                    reset_async=reset_async,
                    reset_active_low=reset_active_low,
                    signal_drivers=signal_drivers,
                    state_writers=state_writers,
                    memory_accesses=memory_accesses,
                )
            _walk_stmt_list(
                stmt.else_body,
                phase=phase,
                clock=clock,
                reset=reset,
                reset_async=reset_async,
                reset_active_low=reset_active_low,
                signal_drivers=signal_drivers,
                state_writers=state_writers,
                memory_accesses=memory_accesses,
            )
            continue
        if isinstance(stmt, SwitchNode):
            for _, body in stmt.cases:
                _walk_stmt_list(
                    body,
                    phase=phase,
                    clock=clock,
                    reset=reset,
                    reset_async=reset_async,
                    reset_active_low=reset_active_low,
                    signal_drivers=signal_drivers,
                    state_writers=state_writers,
                    memory_accesses=memory_accesses,
                )
            _walk_stmt_list(
                stmt.default_body,
                phase=phase,
                clock=clock,
                reset=reset,
                reset_async=reset_async,
                reset_active_low=reset_active_low,
                signal_drivers=signal_drivers,
                state_writers=state_writers,
                memory_accesses=memory_accesses,
            )
            continue
        if isinstance(stmt, WhenNode):
            for _, body in stmt.branches:
                _walk_stmt_list(
                    body,
                    phase=phase,
                    clock=clock,
                    reset=reset,
                    reset_async=reset_async,
                    reset_active_low=reset_active_low,
                    signal_drivers=signal_drivers,
                    state_writers=state_writers,
                    memory_accesses=memory_accesses,
                )


def _describe_module_hierarchy(module: Module) -> Tuple[ModuleInstancePath, ...]:
    nodes: List[ModuleInstancePath] = []

    def walk(mod: Module, *, path: str, parent_path: Optional[str]) -> None:
        child_instances = tuple(inst_name for inst_name, _ in mod._submodules)
        nodes.append(
            ModuleInstancePath(
                path=path,
                module_name=mod.name,
                type_name=getattr(mod, "_type_name", mod.__class__.__name__),
                parent_path=parent_path,
                child_instances=child_instances,
            )
        )
        for inst_name, child in mod._submodules:
            child_path = f"{path}.{inst_name}"
            walk(child, path=child_path, parent_path=path)

    walk(module, path=module.name, parent_path=None)
    return tuple(nodes)


def _collect_implicit_port_connections(
    stmts: List[Any],
    *,
    parent_module: Module,
    port_connections: List[PortConnection],
) -> None:
    for stmt in stmts:
        if isinstance(stmt, Assign):
            target = stmt.target
            if isinstance(target, Signal):
                owner = getattr(target, "_parent_module", None)
                if owner is not None and owner is not parent_module and isinstance(target, Input):
                    owner_name = next(
                        (inst_name for inst_name, submod in parent_module._submodules if submod is owner),
                        owner.name,
                    )
                    port_connections.append(
                        PortConnection(
                            instance=owner_name,
                            module=owner.name,
                            port=target.name,
                            direction="input",
                            expr_kind=_expr_kind(stmt.value),
                            connected_signals=_expr_signal_names(stmt.value),
                            connected_memories=_expr_memory_names(stmt.value),
                        )
                    )
            if isinstance(stmt.value, Ref):
                source_signal = stmt.value.signal
                owner = getattr(source_signal, "_parent_module", None)
                if owner is not None and owner is not parent_module and isinstance(source_signal, Output):
                    owner_name = next(
                        (inst_name for inst_name, submod in parent_module._submodules if submod is owner),
                        owner.name,
                    )
                    target_name, _ = _assignment_target_info(stmt.target)
                    connected = (target_name,) if target_name is not None else ()
                    port_connections.append(
                        PortConnection(
                            instance=owner_name,
                            module=owner.name,
                            port=source_signal.name,
                            direction="output",
                            expr_kind="ref",
                            connected_signals=connected,
                            connected_memories=(),
                        )
                    )
            continue
        if isinstance(stmt, IfNode):
            _collect_implicit_port_connections(
                stmt.then_body,
                parent_module=parent_module,
                port_connections=port_connections,
            )
            for _, body in stmt.elif_bodies:
                _collect_implicit_port_connections(
                    body,
                    parent_module=parent_module,
                    port_connections=port_connections,
                )
            _collect_implicit_port_connections(
                stmt.else_body,
                parent_module=parent_module,
                port_connections=port_connections,
            )
            continue
        if isinstance(stmt, SwitchNode):
            for _, body in stmt.cases:
                _collect_implicit_port_connections(
                    body,
                    parent_module=parent_module,
                    port_connections=port_connections,
                )
            _collect_implicit_port_connections(
                stmt.default_body,
                parent_module=parent_module,
                port_connections=port_connections,
            )
            continue
        if isinstance(stmt, WhenNode):
            for _, body in stmt.branches:
                _collect_implicit_port_connections(
                    body,
                    parent_module=parent_module,
                    port_connections=port_connections,
                )


def _analyze_module_connectivity(module: Module) -> ModuleConnectivityReport:
    signal_drivers: List[SignalDriver] = []
    state_writers: List[StateWriter] = []
    memory_accesses: List[MemoryAccess] = []
    port_connections: List[PortConnection] = []

    _walk_stmt_list(
        module._top_level,
        phase="comb",
        clock=None,
        reset=None,
        reset_async=False,
        reset_active_low=False,
        signal_drivers=signal_drivers,
        state_writers=state_writers,
        memory_accesses=memory_accesses,
    )
    for body in module._comb_blocks:
        _walk_stmt_list(
            body,
            phase="comb",
            clock=None,
            reset=None,
            reset_async=False,
            reset_active_low=False,
            signal_drivers=signal_drivers,
            state_writers=state_writers,
            memory_accesses=memory_accesses,
        )
    for body in module._latch_blocks:
        _walk_stmt_list(
            body,
            phase="latch",
            clock=None,
            reset=None,
            reset_async=False,
            reset_active_low=False,
            signal_drivers=signal_drivers,
            state_writers=state_writers,
            memory_accesses=memory_accesses,
        )
    for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
        _walk_stmt_list(
            body,
            phase="seq",
            clock=getattr(clk, "name", None),
            reset=getattr(rst, "name", None) if rst is not None else None,
            reset_async=reset_async,
            reset_active_low=reset_active_low,
            signal_drivers=signal_drivers,
            state_writers=state_writers,
            memory_accesses=memory_accesses,
        )

    for stmt in module._top_level:
        if not isinstance(stmt, SubmoduleInst):
            continue
        submodule = stmt.module
        instance_name = stmt.name
        for port_name, expr in stmt.port_map.items():
            direction = "unknown"
            if port_name in submodule._inputs:
                direction = "input"
            elif port_name in submodule._outputs:
                direction = "output"
            port_connections.append(
                PortConnection(
                    instance=instance_name,
                    module=submodule.name,
                    port=port_name,
                    direction=direction,
                    expr_kind=_expr_kind(expr),
                    connected_signals=_expr_signal_names(expr),
                    connected_memories=_expr_memory_names(expr),
                )
            )
    _collect_implicit_port_connections(
        module._top_level,
        parent_module=module,
        port_connections=port_connections,
    )
    for body in module._comb_blocks:
        _collect_implicit_port_connections(
            body,
            parent_module=module,
            port_connections=port_connections,
        )

    return ModuleConnectivityReport(
        hierarchy=_describe_module_hierarchy(module),
        signal_drivers=tuple(signal_drivers),
        state_writers=tuple(state_writers),
        memory_accesses=tuple(memory_accesses),
        port_connections=tuple(port_connections),
    )

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
        return _copy_source_location(
            Assign(
                _subst_genvar_in_expr(stmt.target, var_name, value),
                _subst_genvar_in_expr(stmt.value, var_name, value),
                stmt.blocking,
            ),
            stmt,
        )
    if isinstance(stmt, IndexedAssign):
        return _copy_source_location(
            IndexedAssign(
                stmt.target_signal,
                _subst_genvar_in_expr(stmt.index, var_name, value),
                _subst_genvar_in_expr(stmt.value, var_name, value),
                stmt.blocking,
            ),
            stmt,
        )
    if isinstance(stmt, ArrayWrite):
        return _copy_source_location(
            ArrayWrite(
                stmt.array_name,
                _subst_genvar_in_expr(stmt.index, var_name, value),
                _subst_genvar_in_expr(stmt.value, var_name, value),
                stmt.blocking,
            ),
            stmt,
        )
    if isinstance(stmt, MemWrite):
        return _copy_source_location(
            MemWrite(
                stmt.mem_name,
                _subst_genvar_in_expr(stmt.addr, var_name, value),
                _subst_genvar_in_expr(stmt.value, var_name, value),
                byte_enable=(
                    _subst_genvar_in_expr(stmt.byte_enable, var_name, value)
                    if stmt.byte_enable is not None
                    else None
                ),
            ),
            stmt,
        )
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
    flat._clock_domain_specs = dict(getattr(module, "_clock_domain_specs", {}))
    flat._reset_domain_specs = dict(getattr(module, "_reset_domain_specs", {}))

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
            return _copy_source_location(
                Assign(new_target, _rename_expr(stmt.value, mapping, mem_rename, arr_rename), stmt.blocking),
                stmt,
            )
        if isinstance(stmt, IndexedAssign):
            ts = mapping.get(stmt.target_signal, stmt.target_signal)
            return _copy_source_location(
                IndexedAssign(
                    ts,
                    _rename_expr(stmt.index, mapping, mem_rename, arr_rename),
                    _rename_expr(stmt.value, mapping, mem_rename, arr_rename),
                    stmt.blocking,
                ),
                stmt,
            )
        if isinstance(stmt, ArrayWrite):
            return _copy_source_location(
                ArrayWrite(
                    arr_rename.get(stmt.array_name, stmt.array_name),
                    _rename_expr(stmt.index, mapping, mem_rename, arr_rename),
                    _rename_expr(stmt.value, mapping, mem_rename, arr_rename),
                    stmt.blocking,
                ),
                stmt,
            )
        if isinstance(stmt, MemWrite):
            return _copy_source_location(
                MemWrite(
                    mem_rename.get(stmt.mem_name, stmt.mem_name),
                    _rename_expr(stmt.addr, mapping, mem_rename, arr_rename),
                    _rename_expr(stmt.value, mapping, mem_rename, arr_rename),
                    byte_enable=(
                        _rename_expr(stmt.byte_enable, mapping, mem_rename, arr_rename)
                        if stmt.byte_enable is not None
                        else None
                    ),
                ),
                stmt,
            )
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
            new_mem = Memory(
                mem.width,
                mem.depth,
                new_name,
                init_file=mem.init_file,
                init_zero=mem.init_zero,
                init_data=list(mem.init_data) if mem.init_data is not None else None,
                read_during_write=getattr(mem, "read_during_write", "write_first"),
                read_ports=getattr(mem, "read_ports", 1),
                write_ports=getattr(mem, "write_ports", 1),
                read_style=getattr(mem, "read_style", "async"),
                read_latency=getattr(mem, "read_latency", 0),
                byte_enable_granularity=getattr(mem, "byte_enable_granularity", None),
            )
            mem_rename[name] = new_name
            flat._memories[new_name] = new_mem
            object.__setattr__(flat, new_name, new_mem)

        for name, arr in sub_copy._arrays.items():
            new_name = f"{prefix}{name}"
            new_arr = Array(arr.width, arr.depth, new_name, vtype=arr._vtype)
            arr_rename[name] = new_name
            if arr.name and arr.name != name:
                arr_rename[arr.name] = new_name
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
