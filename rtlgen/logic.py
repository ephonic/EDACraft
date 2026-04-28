"""
rtlgen.logic — 硬件控制流与表达式辅助函数

提供 If / Else / Switch / Case / Default 等上下文管理器，
以及 Mux、Cat、Rep 等常用硬件表达式构造器。
"""
from __future__ import annotations

from typing import Any, List
import inspect

from rtlgen.core import Module

from rtlgen.core import (
    Assign,
    Comment,
    Concat as _ConcatExpr,
    Const as _ConstExpr,
    Context,
    ForGenNode,
    GenVar,
    IfNode,
    Mux as _MuxExpr,
    Ref,
    Signal,
    SwitchNode,
    _to_expr,
)


# ---------------------------------------------------------------------
# Conditional blocks
# ---------------------------------------------------------------------


def _find_module_in_stack() -> Optional[Module]:
    """从调用栈中查找最近的 Module 实例（self）。"""
    frame = inspect.currentframe().f_back.f_back
    while frame:
        local_self = frame.f_locals.get('self')
        if isinstance(local_self, Module):
            return local_self
        frame = frame.f_back
    return None
class If:
    """组合/时序逻辑条件分支。

    示例:
        with If(a == b):
            c <<= 1
        with Else():
            c <<= 0
    """

    def __init__(self, condition: Any):
        self.node = IfNode(cond=_to_expr(condition))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(self.node)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(self.node)
        else:
            mod = _find_module_in_stack()
            if mod is not None:
                mod._top_level.append(self.node)
            else:
                raise RuntimeError("If used outside of any module or logic block")

    def __enter__(self):
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=self.node.then_body))

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()


class Else:
    """If 的 else 分支，必须紧跟在 with If(...) 之后使用。"""

    def __init__(self):
        ctx = Context.current()
        container = ctx.stmt_container if ctx else None
        self.node: Optional[IfNode] = None
        if container is not None:
            for stmt in reversed(container):
                if isinstance(stmt, IfNode):
                    self.node = stmt
                    break
        # 如果当前 container 找不到，搜索 Context 栈中各 module 的 _top_level
        if self.node is None:
            stack = getattr(Context._local, "stack", [])
            for c in reversed(stack):
                mod = c.module
                if mod is not None:
                    for stmt in reversed(mod._top_level):
                        if isinstance(stmt, IfNode):
                            self.node = stmt
                            break
                if self.node is not None:
                    break
        # 最后尝试调用栈中的 module _top_level
        if self.node is None:
            mod = _find_module_in_stack()
            if mod is not None:
                for stmt in reversed(mod._top_level):
                    if isinstance(stmt, IfNode):
                        self.node = stmt
                        break
        if self.node is None:
            raise RuntimeError("Else must follow an If block in the same scope")

    def __enter__(self):
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=self.node.else_body))

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()


# ---------------------------------------------------------------------
# Switch / Case
# ---------------------------------------------------------------------

class _StmtContainerContext:
    """内部辅助上下文管理器，用于将语句收集到指定列表。"""

    def __init__(self, body: List[Any]):
        self.body = body

    def __enter__(self):
        mod = Context.current().module if Context.current() else None
        Context.push(Context(module=mod, stmt_container=self.body))

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()


class Switch:
    """多路分支（生成 Verilog case）。

    示例:
        with Switch(opcode) as sw:
            with sw.case(0b001):
                result <<= a + b
            with sw.case(0b010):
                result <<= a - b
            with sw.default():
                result <<= 0
    """

    def __init__(self, expr: Any):
        self.node = SwitchNode(expr=_to_expr(expr))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(self.node)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(self.node)
        else:
            mod = _find_module_in_stack()
            if mod is not None:
                mod._top_level.append(self.node)
            else:
                raise RuntimeError("Switch used outside of any module or logic block")

    def __enter__(self):
        # 禁止在 with Switch: 内部直接写语句，必须通过 sw.case()
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=None))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()

    def case(self, value: Any):
        """添加一个 case 分支。返回上下文管理器。"""
        body: List[Any] = []
        self.node.cases.append((_to_expr(value), body))
        return _StmtContainerContext(body)

    def default(self):
        """添加 default 分支。返回上下文管理器。"""
        body: List[Any] = []
        self.node.default_body = body
        return _StmtContainerContext(body)


# ---------------------------------------------------------------------
# StateTransition — FSM 状态转移收集器
# ---------------------------------------------------------------------

class StateTransition:
    """将分散在多个 If 分支中的同一目标寄存器赋值合并为单一 Mux 链。

    在 rtlgen 的 ``@seq`` 块中，如果同一寄存器在多个独立 ``with If()`` 分支中被赋值，
    生成的 Verilog 会产生多个独立 ``if`` 语句。虽然在综合工具中通常可接受，但：

    1. 可读性较差；
    2. 当分支条件有重叠（或仿真器按顺序求值）时可能出现歧义；
    3. 不利于 linter / 综合工具推断完整 case。

    ``StateTransition`` 通过显式收集 ``(condition, next_value)`` 对，最终生成一条
    优先级 Mux 链的单一赋值，从根本上消除多赋值覆盖问题。

    用法（手动 commit）：

    .. code-block:: python

        @self.seq(self.clk, self.rst_n)
        def _fsm():
            st = StateTransition(self.state)
            st.next(READ,  when=self.state == IDLE)
            st.next(ACC,   when=self.state == READ)
            st.next(WRITE, when=self.state == ACC)
            st.commit()   # 在当前 stmt_container 中插入一条合并后的赋值

    用法（上下文管理器，自动 commit）：

    .. code-block:: python

        @self.seq(self.clk, self.rst_n)
        def _fsm():
            with StateTransition(self.state) as st:
                st.next(READ,  when=self.state == IDLE)
                st.next(ACC,   when=self.state == READ)
                st.next(WRITE, when=self.state == ACC)

    上述两种写法生成的 Verilog 逻辑等价于：

    .. code-block:: verilog

        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                state <= IDLE;
            else
                state <= (state == IDLE) ? READ :
                         (state == READ) ? ACC  :
                         (state == ACC ) ? WRITE : state;
        end

    参数 ``default_hold=True`` 时，若没有任何条件命中，寄存器保持原值；
    设为 ``False`` 时默认下一值为 0（通常不推荐）。
    """

    def __init__(self, state_reg: Signal, default_hold: bool = True):
        self.state_reg = state_reg
        self.default_hold = default_hold
        self._transitions: List[tuple] = []

    def next(self, value: Any, when: Any = None):
        """注册一条状态转移。

        :param value: 下一状态值（可为常量、Signal、Expr）
        :param when:  触发条件。若为 ``None`` 则视为无条件转移（默认最后优先级）
        """
        cond = _to_expr(when) if when is not None else _ConstExpr(1, 1)
        self._transitions.append((cond, _to_expr(value)))

    def _build_expr(self) -> Any:
        """从已收集的 transitions 构建优先级 Mux 链 Expr。"""
        if not self._transitions:
            return Ref(self.state_reg) if self.default_hold else _ConstExpr(0, self.state_reg.width)

        default = Ref(self.state_reg) if self.default_hold else _ConstExpr(0, self.state_reg.width)
        result = default
        # 从最低优先级向最高优先级折叠，保证先注册的 transition 优先级更高
        for cond, val in reversed(self._transitions):
            w = max(val.width, result.width)
            result = _MuxExpr(cond=cond, true_expr=val, false_expr=result, width=w)
        return result

    def commit(self):
        """将合并后的单一赋值插入到当前的语句容器（stmt_container）。

        必须在 ``@comb`` 或 ``@seq`` 块内调用。
        """
        expr = self._build_expr()
        assign = Assign(target=self.state_reg, value=expr, blocking=False)
        ctx = Context.current()
        container = ctx.stmt_container if ctx else None
        if container is None:
            mod = _find_module_in_stack()
            if mod is not None:
                container = mod._top_level
            else:
                raise RuntimeError(
                    "StateTransition.commit() must be called inside a @comb / @seq block or module"
                )
        container.append(assign)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()


# ---------------------------------------------------------------------
# Expression helpers
# ---------------------------------------------------------------------

def Mux(cond: Any, true_val: Any, false_val: Any) -> Signal:
    """二选一多路器。"""
    ce = _to_expr(cond)
    te = _to_expr(true_val)
    fe = _to_expr(false_val)
    w = max(te.width, fe.width)
    s = Signal(width=w)
    s._expr = _MuxExpr(cond=ce, true_expr=te, false_expr=fe, width=w)
    return s


def Cat(*signals: Any) -> Signal:
    """位拼接（Cat(a, b) -> {a, b}）。"""
    exprs = [_to_expr(s) for s in signals]
    w = sum(e.width for e in exprs)
    s = Signal(width=w)
    s._expr = _ConcatExpr(operands=exprs, width=w)
    return s


def Rep(signal: Any, times: int) -> Signal:
    """位重复（Rep(a, 3) -> {a, a, a}）。"""
    e = _to_expr(signal)
    s = Signal(width=e.width * times)
    s._expr = _ConcatExpr(operands=[e] * times, width=e.width * times)
    return s


def Const(value: int, width: Optional[int] = None) -> Signal:
    """创建常数信号，可指定位宽。"""
    if width is None:
        width = max(value.bit_length(), 1)
    s = Signal(width=width)
    s._expr = _ConstExpr(value=value, width=width)
    return s


def Split(signal: Signal, chunk_width: int) -> List[Signal]:
    """将信号按 chunk_width 分段，返回从低位到高位的列表。

    若总位宽不是 chunk_width 整数倍，最高段会包含剩余的有效位。
    """
    total = signal.width
    n = (total + chunk_width - 1) // chunk_width
    chunks: List[Signal] = []
    for i in range(n):
        lo = i * chunk_width
        hi = min(lo + chunk_width - 1, total - 1)
        chunks.append(signal[hi:lo])
    return chunks


def PadLeft(signal: Signal, target_width: int) -> Signal:
    """左侧补零到 target_width。"""
    if signal.width >= target_width:
        return signal
    return Cat(Const(0, target_width - signal.width), signal)


def Select(signals, idx):
    """用信号索引从列表/Vector中选择元素（返回 Mux 链）。

    当索引是动态信号时，Python 列表不支持 `list[idx]`。使用 Select 替代：

        data = Select(self.entry_data, self.selected_idx)

    参数:
        signals: List[Signal] 或 Vector，从中选择
        idx: Signal / int，索引值
    """
    from rtlgen.core import Vector
    if isinstance(signals, Vector):
        sigs = [signals[i] for i in range(len(signals))]
    else:
        sigs = list(signals)
    if len(sigs) == 0:
        raise ValueError("Select requires at least one signal")
    result = sigs[0]
    for i in range(1, len(sigs)):
        result = Mux(idx == i, sigs[i], result)
    return result


# ---------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------

def comment(text: str):
    """插入 Verilog 注释。

    示例:
        @self.comb
        def _logic():
            comment("Start of combination logic")
            c <<= a & b
    """
    stmt = Comment(text)
    ctx = Context.current()
    if ctx and ctx.stmt_container is not None:
        ctx.stmt_container.append(stmt)
    elif ctx and ctx.module is not None:
        ctx.module._top_level.append(stmt)
    else:
        mod = _find_module_in_stack()
        if mod is not None:
            mod._top_level.append(stmt)
        else:
            raise RuntimeError("Comment used outside of any module or logic block")


# ---------------------------------------------------------------------
# Generate-if / Generate-else
# ---------------------------------------------------------------------

class GenIf:
    """Verilog generate-if 上下文管理器。

    示例:
        with GenIf(USE_FIFO == 1):
            self.fifo = SyncFIFO(...)
    """

    def __init__(self, condition: Any):
        from rtlgen.core import GenIfNode
        self.node = GenIfNode(cond=_to_expr(condition))
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(self.node)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(self.node)
        else:
            mod = _find_module_in_stack()
            if mod is not None:
                mod._top_level.append(self.node)
            else:
                raise RuntimeError("GenIf used outside of any module")

    def __enter__(self):
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=self.node.then_body))

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()


class GenElse:
    """GenIf 的 else 分支，必须紧跟在 with GenIf(...) 之后使用。"""

    def __init__(self):
        from rtlgen.core import GenIfNode
        ctx = Context.current()
        container = ctx.stmt_container if ctx else None
        self.node = None
        if container is not None:
            for stmt in reversed(container):
                if isinstance(stmt, GenIfNode):
                    self.node = stmt
                    break
        # 搜索 Context 栈中各 module 的 _top_level
        if self.node is None:
            stack = getattr(Context._local, "stack", [])
            for c in reversed(stack):
                mod = c.module
                if mod is not None:
                    for stmt in reversed(mod._top_level):
                        if isinstance(stmt, GenIfNode):
                            self.node = stmt
                            break
                if self.node is not None:
                    break
        # 最后尝试调用栈中的 module _top_level
        if self.node is None:
            mod = _find_module_in_stack()
            if mod is not None:
                for stmt in reversed(mod._top_level):
                    if isinstance(stmt, GenIfNode):
                        self.node = stmt
                        break
        if self.node is None:
            raise RuntimeError("GenElse must follow a GenIf block in the same scope")

    def __enter__(self):
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=self.node.else_body))

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()


# ---------------------------------------------------------------------
# Generate-for
# ---------------------------------------------------------------------

class ForGen:
    """Verilog generate-for 循环上下文管理器。

    示例:
        with ForGen("i", 0, 4) as i:
            out[i] <<= in_[i]
    """

    def __init__(self, var_name: str, start: int, end: int):
        self.node = ForGenNode(var_name=var_name, start=start, end=end)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(self.node)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(self.node)
        else:
            mod = _find_module_in_stack()
            if mod is not None:
                mod._top_level.append(self.node)
            else:
                raise RuntimeError("ForGen used outside of any module or logic block")

    def __enter__(self):
        ctx = Context.current()
        mod = ctx.module if ctx else _find_module_in_stack()
        Context.push(Context(module=mod, stmt_container=self.node.body))
        return GenVar(self.node.var_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        Context.pop()