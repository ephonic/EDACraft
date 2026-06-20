"""A small rtlgen_x-native DSL surface that builds executable simulator modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)


def _int_width(value: int) -> int:
    if value == 0:
        return 1
    if value > 0:
        return value.bit_length()
    return (-value).bit_length() + 1


@dataclass(frozen=True)
class NativeValue:
    """Width-aware expression wrapper for the native DSL."""

    expr: object
    width: int
    signed: bool = False

    def __post_init__(self) -> None:
        if self.width < 1 or self.width > 64:
            raise ValueError("native DSL values must have width in [1, 64]")

    def mask(self, width: Optional[int] = None) -> "NativeValue":
        return NativeValue(MaskExpr(self.expr, width or self.width), width or self.width, signed=False)

    def as_signed(self) -> "NativeValue":
        return NativeValue(UnaryExpr("$signed", self.expr), self.width, signed=True)

    def as_unsigned(self) -> "NativeValue":
        return NativeValue(UnaryExpr("$unsigned", self.expr), self.width, signed=False)

    def _coerce(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        if isinstance(other, NativeValue):
            return other
        return const(other, width=max(self.width, _int_width(int(other))))

    def _binary(self, op: str, other: Union[int, "NativeValue"], *, width: Optional[int] = None, signed: Optional[bool] = None) -> "NativeValue":
        rhs = self._coerce(other)
        out_width = width if width is not None else max(self.width, rhs.width)
        out_signed = signed if signed is not None else (self.signed or rhs.signed)
        return NativeValue(BinaryExpr(op, self.expr, rhs.expr), out_width, out_signed)

    def __invert__(self) -> "NativeValue":
        return NativeValue(UnaryExpr("~", self.expr), self.width, self.signed)

    def __neg__(self) -> "NativeValue":
        return NativeValue(UnaryExpr("-", self.expr), self.width, self.signed)

    def __add__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        rhs = self._coerce(other)
        return self._binary("+", rhs, width=max(self.width, rhs.width) + 1)

    def __sub__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        rhs = self._coerce(other)
        return self._binary("-", rhs, width=max(self.width, rhs.width) + 1)

    def __mul__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        rhs = self._coerce(other)
        return self._binary("*", rhs, width=min(self.width + rhs.width, 64))

    def __and__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("&", other)

    def __or__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("|", other)

    def __xor__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("^", other)

    def __lshift__(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("<<", other, width=self.width)

    def logical_rshift(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary(">>", other, width=self.width, signed=False)

    def arith_rshift(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary(">>>", other, width=self.width, signed=self.signed)

    def eq(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("==", other, width=1, signed=False)

    def ne(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("!=", other, width=1, signed=False)

    def lt(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("<", other, width=1, signed=False)

    def le(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary("<=", other, width=1, signed=False)

    def gt(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary(">", other, width=1, signed=False)

    def ge(self, other: Union[int, "NativeValue"]) -> "NativeValue":
        return self._binary(">=", other, width=1, signed=False)


@dataclass(frozen=True)
class NativeSignal(NativeValue):
    """Declared signal in the native DSL."""

    name: str = field(default="")
    kind: str = field(default="wire")
    init: int = field(default=0)


@dataclass(frozen=True)
class NativeMemory:
    """Declared memory in the native DSL."""

    name: str
    width: int
    depth: int
    init: Tuple[int, ...] = ()

    def read(self, addr: Union[int, NativeValue]) -> NativeValue:
        addr_value = addr if isinstance(addr, NativeValue) else const(addr, width=max(_int_width(int(addr)), 1))
        return NativeValue(MemoryReadExpr(self.name, addr_value.expr), self.width, signed=False)

    def __getitem__(self, addr: Union[int, NativeValue]) -> NativeValue:
        return self.read(addr)


def const(value: int, *, width: Optional[int] = None, signed: bool = False) -> NativeValue:
    resolved_width = width or _int_width(int(value))
    return NativeValue(ConstExpr(int(value), resolved_width), resolved_width, signed=signed)


def mux(cond: Union[int, NativeValue], when_true: Union[int, NativeValue], when_false: Union[int, NativeValue]) -> NativeValue:
    cond_value = cond if isinstance(cond, NativeValue) else const(cond, width=1)
    true_value = when_true if isinstance(when_true, NativeValue) else const(int(when_true))
    false_value = when_false if isinstance(when_false, NativeValue) else const(int(when_false))
    width = max(true_value.width, false_value.width)
    return NativeValue(MuxExpr(cond_value.expr, true_value.expr, false_value.expr), width, true_value.signed or false_value.signed)


class NativeModuleBuilder:
    """Tiny builder that lowers directly into ``SimModule``."""

    def __init__(self, name: str):
        if not name:
            raise ValueError("module name must not be empty")
        self.name = name
        self._signals: List[Signal] = []
        self._outputs: List[str] = []
        self._assignments: List[Assignment] = []
        self._memories: List[Memory] = []
        self._memory_writes: List[MemoryWrite] = []
        self._signal_names = set()
        self._memory_names = set()

    def _declare_signal(
        self,
        name: str,
        *,
        width: int,
        kind: str,
        signed: bool = False,
        init: int = 0,
    ) -> NativeSignal:
        if name in self._signal_names or name in self._memory_names:
            raise ValueError(f"duplicate declaration '{name}'")
        signal = Signal(name, width=width, kind=kind, signed=signed, init=init)
        self._signals.append(signal)
        self._signal_names.add(name)
        if kind == "output":
            self._outputs.append(name)
        return NativeSignal(SignalRef(name), width=width, signed=signed, name=name, kind=kind, init=init)

    def input(self, name: str, *, width: int, signed: bool = False) -> NativeSignal:
        return self._declare_signal(name, width=width, kind="input", signed=signed)

    def output(self, name: str, *, width: int, signed: bool = False) -> NativeSignal:
        return self._declare_signal(name, width=width, kind="output", signed=signed)

    def wire(self, name: str, *, width: int, signed: bool = False) -> NativeSignal:
        return self._declare_signal(name, width=width, kind="wire", signed=signed)

    def state(self, name: str, *, width: int, init: int = 0, signed: bool = False) -> NativeSignal:
        return self._declare_signal(name, width=width, kind="state", signed=signed, init=init)

    def memory(self, name: str, *, width: int, depth: int, init: Sequence[int] = ()) -> NativeMemory:
        if name in self._memory_names or name in self._signal_names:
            raise ValueError(f"duplicate declaration '{name}'")
        memory = Memory(name=name, width=width, depth=depth, init=tuple(int(value) for value in init))
        self._memories.append(memory)
        self._memory_names.add(name)
        return NativeMemory(name=name, width=width, depth=depth, init=memory.init)

    def assign(self, target: NativeSignal, expr: Union[int, NativeValue], *, phase: str = "comb") -> None:
        if target.kind == "input":
            raise ValueError(f"cannot assign to input '{target.name}'")
        if isinstance(expr, NativeValue):
            native_expr = expr
        else:
            native_expr = const(int(expr), width=target.width, signed=target.signed)
        self._assignments.append(Assignment(target.name, native_expr.expr, phase=phase))

    def comb(self, target: NativeSignal, expr: Union[int, NativeValue]) -> None:
        self.assign(target, expr, phase="comb")

    def seq(self, target: NativeSignal, expr: Union[int, NativeValue]) -> None:
        self.assign(target, expr, phase="seq")

    def write_memory(
        self,
        memory: NativeMemory,
        *,
        addr: Union[int, NativeValue],
        value: Union[int, NativeValue],
        enable: Union[int, NativeValue] = 1,
    ) -> None:
        addr_value = addr if isinstance(addr, NativeValue) else const(int(addr))
        write_value = value if isinstance(value, NativeValue) else const(int(value), width=memory.width)
        enable_value = enable if isinstance(enable, NativeValue) else const(int(enable), width=1)
        self._memory_writes.append(
            MemoryWrite(memory.name, addr_value.expr, write_value.expr, enable=enable_value.expr)
        )

    def build(
        self,
        *,
        reset_signal: Optional[str] = None,
        outputs_post_state: bool = False,
    ) -> SimModule:
        return SimModule(
            name=self.name,
            signals=tuple(self._signals),
            assignments=tuple(self._assignments),
            outputs=tuple(self._outputs),
            memories=tuple(self._memories),
            memory_writes=tuple(self._memory_writes),
            reset_signal=reset_signal,
            outputs_post_state=outputs_post_state,
        )
