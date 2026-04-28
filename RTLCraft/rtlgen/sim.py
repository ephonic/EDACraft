"""
rtlgen.sim — Python AST 仿真后端

直接在 Python 中解释执行 pyRTL 构建的 AST，用于快速单元测试。
支持多时钟域、X/Z 四态逻辑（可选）、时间/延迟模型、子模块递归仿真。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from rtlgen.core import (
    Array,
    ArrayRead,
    ArrayWrite,
    Assign,
    BinOp,
    BitSelect,
    Comment,
    Concat,
    Const,
    Expr,
    ForGenNode,
    GenIfNode,
    GenVar,
    IfNode,
    IndexedAssign,
    Input,
    MemRead,
    MemWrite,
    Module,
    Mux,
    Output,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
    Wire,
    _to_expr,
    _subst_genvar_in_expr,
    _subst_genvar_in_stmt,
)


# -----------------------------------------------------------------
# 4-state Simulation Value
# -----------------------------------------------------------------
class SimValue:
    """四态仿真值（0/1/X/Z）。"""

    def __init__(self, v: int = 0, x_mask: int = 0, z_mask: int = 0, width: int = 32):
        self.width = width
        mask = (1 << width) - 1
        self.v = int(v) & mask
        self.x_mask = int(x_mask) & mask
        self.z_mask = int(z_mask) & mask

    def is_x(self, bit: Optional[int] = None) -> bool:
        if bit is None:
            return self.x_mask != 0
        return ((self.x_mask >> bit) & 1) == 1

    def is_z(self, bit: Optional[int] = None) -> bool:
        if bit is None:
            return self.z_mask != 0
        return ((self.z_mask >> bit) & 1) == 1

    def __int__(self) -> int:
        return self.v

    def __repr__(self):
        return f"SimValue(v={self.v}, x={self.x_mask:#x}, z={self.z_mask:#x})"


def _make_xz(v: Union[int, SimValue], width: int) -> SimValue:
    if isinstance(v, SimValue):
        return SimValue(v.v, v.x_mask, v.z_mask, width)
    return SimValue(v, 0, 0, width)


def _to_int(v: Union[int, SimValue]) -> int:
    return int(v) if isinstance(v, SimValue) else v




# -----------------------------------------------------------------
# Simulator
# -----------------------------------------------------------------
class Simulator:
    """周期精确 AST 解释器，支持子模块递归展开。"""

    def __init__(
        self,
        module: Module,
        trace_signals: Optional[List[str]] = None,
        use_xz: bool = False,
        clock_period_ns: float = 10.0,
        param_overrides: Optional[Dict[str, Any]] = None,
    ):
        self.module = module
        self.use_xz = use_xz
        self.clock_period_ns = clock_period_ns
        self.time_ns: float = 0.0
        self._param_overrides: Dict[str, Any] = dict(param_overrides) if param_overrides else {}

        self.state: Dict[str, Union[int, SimValue]] = {}
        self.next_state: Dict[str, Union[int, SimValue]] = {}
        self.memories: Dict[str, List[Union[int, SimValue]]] = {}
        self.trace: List[Dict[str, Union[int, float]]] = []
        self.trace_signals = trace_signals
        self.trace_max_size: Optional[int] = None  # ring buffer limit
        self._cycle_count: int = 0
        self._delayed_events: List[Tuple[float, Callable[[], None]]] = []
        # (inst_name, child_simulator, port_map)
        self._subsim_info: List[Tuple[str, "Simulator", Dict[str, Expr]]] = []
        self._jit = None
        self._sig_to_hier_name: Dict[int, str] = {}
        # 子模块output信号 -> child_simulator 映射，用于 _eval_expr 直接读取子模块输出
        self._output_signal_map: Dict[int, "Simulator"] = {}
        self._init()
        self._init_jit()

    def _init(self):
        """初始化所有信号，并分配 memory，递归初始化子模块。"""
        for _, sig in list(self.module._inputs.items()) + \
                      list(self.module._outputs.items()) + \
                      list(self.module._wires.items()) + \
                      list(self.module._regs.items()):
            self.state[sig.name] = 0 if not self.use_xz else SimValue(0, width=sig.width)

        if self.use_xz:
            for _, sig in list(self.module._regs.items()):
                self.state[sig.name] = SimValue(0, x_mask=(1 << sig.width) - 1, width=sig.width)

        for name, mem in self.module._memories.items():
            if self.use_xz:
                self.memories[name] = [SimValue(0, x_mask=(1 << mem.width) - 1, width=mem.width) for _ in range(mem.depth)]
            else:
                self.memories[name] = [0] * mem.depth

        for name, arr in self.module._arrays.items():
            if self.use_xz:
                self.state[name] = {i: SimValue(0, x_mask=(1 << arr.width) - 1, width=arr.width) for i in range(arr.depth)}
            else:
                self.state[name] = {i: 0 for i in range(arr.depth)}

        self._init_submodules()
        self._build_sig_map(self.module, "")

    def _build_sig_map(self, mod: Module, prefix: str):
        """Build id(Signal) -> hierarchical_name mapping for peek/poke."""
        for _, sig in list(mod._inputs.items()) + \
                      list(mod._outputs.items()) + \
                      list(mod._wires.items()) + \
                      list(mod._regs.items()):
            self._sig_to_hier_name[id(sig)] = prefix + sig.name

        for name, mem in mod._memories.items():
            self._sig_to_hier_name[id(mem)] = prefix + name

        for inst_name, submod in mod._submodules:
            self._build_sig_map(submod, prefix + inst_name + "_")

        def _scan(stmts):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    self._build_sig_map(stmt.module, prefix + stmt.name + "_")
                elif isinstance(stmt, (IfNode, GenIfNode)):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _scan(body)
                    _scan(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    for i in range(stmt.start, stmt.end):
                        unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                        _scan(unrolled)

        _scan(mod._top_level)
        for body in mod._comb_blocks:
            _scan(body)
        for _, _, _, _, body in mod._seq_blocks:
            _scan(body)

    def _hier_name(self, name):
        """Resolve Signal object to hierarchical name string."""
        if isinstance(name, Signal):
            return self._sig_to_hier_name.get(id(name), name.name)
        return name

    def _init_jit(self):
        """Attempt JIT compilation; fallback silently on failure."""
        if self.use_xz:
            return
        try:
            from rtlgen.sim_jit import JITModule
            self._jit = JITModule(self.module, param_overrides=self._param_overrides)
            # Sync JIT state back to Simulator dict for peek/poke/trace
            self._sync_from_jit()
        except Exception:
            self._jit = None

    def _sync_from_jit(self):
        """Copy JIT flat state into Simulator hierarchical state dict."""
        if self._jit is None:
            return
        for name, idx in self._jit.sig_idx.items():
            self.state[name] = self._jit.state[idx]
        for name, idx in self._jit.mem_idx.items():
            self.memories[name] = list(self._jit.memories[idx])
        for name, idx in self._jit.arr_idx.items():
            self.state[name] = dict(self._jit.arrays[idx])

    def _sync_to_jit(self):
        """Copy Simulator state dict into JIT flat state."""
        if self._jit is None:
            return
        for name, idx in self._jit.sig_idx.items():
            v = self.state.get(name, 0)
            self._jit.state[idx] = int(v) if isinstance(v, SimValue) else v
        for name, idx in self._jit.mem_idx.items():
            v = self.memories.get(name)
            if v is not None:
                self._jit.memories[idx] = list(v)
        for name, idx in self._jit.arr_idx.items():
            v = self.state.get(name)
            if isinstance(v, dict):
                self._jit.arrays[idx] = dict(v)

    def _init_submodules(self):
        """收集并初始化所有显式/隐式子模块实例。"""
        visited: set = set()

        def _collect_from_stmts(stmts: List[Any]):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    if stmt.name not in visited:
                        visited.add(stmt.name)
                        port_map = {k: _to_expr(v) for k, v in stmt.port_map.items()}
                        child = Simulator(
                            stmt.module,
                            trace_signals=None,
                            use_xz=self.use_xz,
                            clock_period_ns=self.clock_period_ns,
                            param_overrides=stmt.params,
                        )
                        self._subsim_info.append((stmt.name, child, port_map))
                elif isinstance(stmt, (IfNode,)):
                    _collect_from_stmts(stmt.then_body)
                    _collect_from_stmts(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _collect_from_stmts(body)
                    _collect_from_stmts(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    for i in range(stmt.start, stmt.end):
                        unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                        _collect_from_stmts(unrolled)

        def _collect_from_module(mod: Module):
            _collect_from_stmts(mod._top_level)
            for body in mod._comb_blocks:
                _collect_from_stmts(body)
            for _, _, _, _, body in mod._seq_blocks:
                _collect_from_stmts(body)
            # 隐式实例化
            for inst_name, submod in mod._submodules:
                if inst_name not in visited:
                    visited.add(inst_name)
                    port_map: Dict[str, Expr] = {}
                    for pname in list(submod._inputs.keys()) + list(submod._outputs.keys()):
                        if hasattr(mod, pname):
                            val = getattr(mod, pname)
                            if isinstance(val, Signal):
                                port_map[pname] = val._expr

                    # 扫描所有Assign语句，自动检测端口连接（递归处理If/Switch/ForGen）
                    def _get_width(name: str) -> int:
                        if name in submod._inputs:
                            return submod._inputs[name].width
                        if name in submod._outputs:
                            return submod._outputs[name].width
                        return 32

                    def _extract_submod_output(expr: Any):
                        """从表达式树中提取属于当前子模块的Output Signal。"""
                        if isinstance(expr, Signal):
                            if expr.name in submod._outputs:
                                return expr
                            return None
                        elif isinstance(expr, Ref):
                            if expr.signal.name in submod._outputs:
                                return expr.signal
                            return None
                        elif isinstance(expr, (BinOp,)):
                            sig = _extract_submod_output(expr.lhs)
                            if sig is not None:
                                return sig
                            return _extract_submod_output(expr.rhs)
                        elif isinstance(expr, (UnaryOp,)):
                            return _extract_submod_output(expr.operand)
                        elif isinstance(expr, (Mux,)):
                            sig = _extract_submod_output(expr.cond)
                            if sig is not None:
                                return sig
                            sig = _extract_submod_output(expr.true_expr)
                            if sig is not None:
                                return sig
                            return _extract_submod_output(expr.false_expr)
                        return None

                    def _scan_port_assigns(stmts: List[Any], pmap: Dict[str, Expr]):
                        for stmt in stmts:
                            if isinstance(stmt, Assign):
                                target_sig = None
                                if isinstance(stmt.target, Signal):
                                    target_sig = stmt.target
                                elif isinstance(stmt.target, Ref):
                                    target_sig = stmt.target.signal

                                value_sig = None
                                if isinstance(stmt.value, Signal):
                                    value_sig = stmt.value
                                elif isinstance(stmt.value, Ref):
                                    value_sig = stmt.value.signal
                                # 注意：不尝试从复杂表达式(Mux/BinOp等)中提取子模块output
                                # 因为子模块output作为RHS表达式的一部分被parent comb读取时，
                                # 不应创建port_map output条目（避免clobber parent target）
                                # _sync_from_child末尾的全量output同步已确保parent state中有该值

                                # input连接: target是子模块input（通过id匹配避免同名冲突）
                                if target_sig is not None:
                                    if target_sig.name in submod._inputs:
                                        if id(target_sig) == id(submod._inputs[target_sig.name]):
                                            pmap[target_sig.name] = stmt.value

                                # output连接: value是子模块output（通过id匹配避免同名冲突）
                                if value_sig is not None:
                                    if value_sig.name in submod._outputs:
                                        if id(value_sig) == id(submod._outputs[value_sig.name]):
                                            if target_sig is not None:
                                                pmap[value_sig.name] = target_sig._expr

                            elif isinstance(stmt, IndexedAssign):
                                # input连接: target是子模块input（bit-select赋值）
                                target_sig = stmt.target_signal
                                if target_sig.name in submod._inputs:
                                    if id(target_sig) == id(submod._inputs[target_sig.name]):
                                        # 记录target_signal本身，_sync_to_child会读取parent state中的完整值
                                        pmap[target_sig.name] = target_sig

                            elif isinstance(stmt, IfNode):
                                then_map = dict(pmap)
                                else_map = dict(pmap)
                                _scan_port_assigns(stmt.then_body, then_map)
                                _scan_port_assigns(stmt.else_body, else_map)
                                all_keys = set(then_map.keys()) | set(else_map.keys())
                                for k in all_keys:
                                    if k not in submod._inputs and k not in submod._outputs:
                                        continue
                                    t = then_map.get(k)
                                    e = else_map.get(k)
                                    if t is not None and e is not None and t is e:
                                        pmap[k] = t
                                    else:
                                        width = _get_width(k)
                                        t_expr = t if t is not None else Const(0, width=width)
                                        e_expr = e if e is not None else Const(0, width=width)
                                        pmap[k] = Mux(stmt.cond, t_expr, e_expr, width)

                            elif isinstance(stmt, SwitchNode):
                                current_map = dict(pmap)
                                _scan_port_assigns(stmt.default_body, current_map)
                                for match_expr, body in reversed(stmt.cases):
                                    case_map = dict(pmap)
                                    _scan_port_assigns(body, case_map)
                                    all_keys = set(case_map.keys()) | set(current_map.keys())
                                    for k in all_keys:
                                        if k not in submod._inputs and k not in submod._outputs:
                                            continue
                                        c = case_map.get(k)
                                        d = current_map.get(k)
                                        if c is not None and d is not None and c is d:
                                            current_map[k] = c
                                        else:
                                            width = _get_width(k)
                                            c_expr = c if c is not None else Const(0, width=width)
                                            d_expr = d if d is not None else Const(0, width=width)
                                            cond = BinOp("==", stmt.expr, match_expr, width=1)
                                            current_map[k] = Mux(cond, c_expr, d_expr, width)
                                for k, v in current_map.items():
                                    if k in submod._inputs or k in submod._outputs:
                                        pmap[k] = v

                            elif isinstance(stmt, GenIfNode):
                                then_map = dict(pmap)
                                else_map = dict(pmap)
                                _scan_port_assigns(stmt.then_body, then_map)
                                _scan_port_assigns(stmt.else_body, else_map)
                                all_keys = set(then_map.keys()) | set(else_map.keys())
                                for k in all_keys:
                                    if k not in submod._inputs and k not in submod._outputs:
                                        continue
                                    t = then_map.get(k)
                                    e = else_map.get(k)
                                    if t is not None and e is not None and t is e:
                                        pmap[k] = t
                                    else:
                                        width = _get_width(k)
                                        t_expr = t if t is not None else Const(0, width=width)
                                        e_expr = e if e is not None else Const(0, width=width)
                                        pmap[k] = Mux(stmt.cond, t_expr, e_expr, width)

                            elif isinstance(stmt, ForGenNode):
                                for i in range(stmt.start, stmt.end):
                                    unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                                    _scan_port_assigns(unrolled, pmap)

                    for body in (mod._top_level, *mod._comb_blocks, *[b for _, _, _, _, b in mod._seq_blocks]):
                        _scan_port_assigns(body, port_map)

                    # 自动参数映射 + 显式参数绑定
                    params: Dict[str, Any] = {}
                    for pname, param in submod._params.items():
                        if hasattr(mod, pname):
                            val = getattr(mod, pname)
                            if isinstance(val, (Signal, int, str)):
                                params[pname] = val
                            elif hasattr(val, "value") and isinstance(getattr(val, "value"), (int, str)):
                                params[pname] = val
                    for pname, val in getattr(submod, "_param_bindings", {}).items():
                        params[pname] = val

                    child = Simulator(
                        submod,
                        trace_signals=None,
                        use_xz=self.use_xz,
                        clock_period_ns=self.clock_period_ns,
                        param_overrides=params,
                    )
                    self._subsim_info.append((inst_name, child, port_map))
                    # 注册子模块output信号映射，供 _eval_expr 直接读取
                    for out_name, out_sig in submod._outputs.items():
                        self._output_signal_map[id(out_sig)] = child

        _collect_from_module(self.module)

    def set(self, name, value: Union[int, SimValue]):
        """设置输入/信号值。"""
        name = self._hier_name(name)
        width = self._width_of(name)
        if self.use_xz:
            self.state[name] = _make_xz(value, width)
        else:
            mask = (1 << width) - 1
            self.state[name] = int(value) & mask
        if self._jit is not None:
            self._jit.set(name, int(value) & mask)

    def get(self, name):
        """读取信号当前值。"""
        name = self._hier_name(name)
        if self._jit is not None:
            try:
                return self._jit.get(name)
            except KeyError:
                pass
        return self.state.get(name, 0 if not self.use_xz else SimValue(0, width=self._width_of(name)))

    def get_int(self, name) -> int:
        """读取信号当前值并转为 int（X/Z 时返回 0）。"""
        name = self._hier_name(name)
        v = self.state.get(name, 0)
        return int(v) if isinstance(v, SimValue) else v

    def _width_of(self, name) -> int:
        if isinstance(name, Signal):
            return name.width
        for d in (self.module._inputs, self.module._outputs, self.module._wires, self.module._regs):
            if name in d:
                return d[name].width
        # search child modules for width info (used when tracing flattened names)
        for _, child, _ in self._subsim_info:
            w = child._width_of(name)
            if w != 32:
                return w
        return 32

    # -----------------------------------------------------------------
    # Time / Delay API
    # -----------------------------------------------------------------
    def now(self) -> float:
        return self.time_ns

    def advance_time(self, ns: float):
        """仅推进仿真时间，不触发时钟边沿（但会触发延迟事件队列中到时的回调）。"""
        target = self.time_ns + ns
        self.time_ns = target
        triggered = [e for e in self._delayed_events if e[0] <= target]
        self._delayed_events = [e for e in self._delayed_events if e[0] > target]
        for _, cb in sorted(triggered, key=lambda x: x[0]):
            cb()

    def schedule_event(self, delay_ns: float, callback: Callable[[], None]):
        """注册一个延迟事件。"""
        self._delayed_events.append((self.time_ns + delay_ns, callback))

    # -----------------------------------------------------------------
    # Public simulation API
    # -----------------------------------------------------------------
    def step(self, clk: Optional[str] = None, do_trace: bool = True):
        """推进一个时钟周期。子模块与父模块在同一 posedge 同步更新。"""
        if self._jit is not None:
            # Fast JIT path
            self._jit.step()
            self._sync_from_jit()
            self.time_ns += self.clock_period_ns
            if do_trace:
                self._do_trace()
            return

        # Fallback AST interpreter path
        # 1. 评估组合逻辑（输入可能已变）
        self._eval_comb()

        # 2. posedge：评估时序逻辑，收集 next_state（先子后父，避免时序泄露）
        for _, child_sim, port_map in self._subsim_info:
            self._sync_to_child(child_sim, port_map)
            child_sim.step(clk=clk, do_trace=False)
        self._eval_seq(clk)

        # 3. commit 寄存器更新（子模块和父模块同时 commit）
        for _, child_sim, _ in self._subsim_info:
            for k, v in list(child_sim.next_state.items()):
                child_sim.state[k] = v
            child_sim.next_state.clear()
        for k, v in list(self.next_state.items()):
            self.state[k] = v
        self.next_state.clear()

        # 4. 再次评估组合逻辑（寄存器输出可能驱动组合逻辑）
        self._eval_comb()

        self.time_ns += self.clock_period_ns
        if do_trace:
            self._do_trace()

    def reset(self, rst: str = "rst", cycles: int = 2):
        """执行复位序列（自动检测 active-high / active-low）。
        当 JIT 启用时，使用快速路径直接清零 state。"""
        active_low = rst.endswith("_n") or rst.endswith("_N")
        if self._jit is not None:
            # Fast path: directly zero all state, then apply reset value
            for i in range(len(self._jit.state)):
                self._jit.state[i] = 0
                self._jit.next_state[i] = 0
            for mem in self._jit.memories:
                for i in range(len(mem)):
                    mem[i] = 0
            for arr in self._jit.arrays:
                for k in list(arr.keys()):
                    arr[k] = 0
            # Hold reset for 'cycles' steps to let seq logic propagate
            if active_low:
                self._jit.set(rst, 0)
            else:
                self._jit.set(rst, 1)
            for _ in range(cycles):
                self._jit.step()
            if active_low:
                self._jit.set(rst, 1)
            else:
                self._jit.set(rst, 0)
            self._sync_from_jit()
            return

        # Fallback AST interpreter path
        if active_low:
            self.set(rst, 0)
        else:
            self.set(rst, 1)
        for _ in range(cycles):
            self.step()
        if active_low:
            self.set(rst, 1)
        else:
            self.set(rst, 0)

    def run(self, cycles: int):
        """连续运行多个时钟周期。"""
        for _ in range(cycles):
            self.step()

    def peek(self, name):
        """读取信号当前值（get 的别名）。支持层级名如 'systolic.state' 或 Signal 对象。"""
        return self.get(name)

    def poke(self, name, value):
        """设置信号值（set 的别名）。支持层级名如 'systolic.state' 或 Signal 对象。"""
        return self.set(name, value)

    def list_signals(self, prefix: str = "") -> List[str]:
        """列出所有匹配前缀的层级信号名。"""
        names = []
        if self._jit is not None:
            for n in self._jit.sig_names:
                if n.startswith(prefix):
                    names.append(n)
            for n in self._jit.mem_names:
                full = f"mem:{n}"
                if full.startswith(prefix):
                    names.append(full)
        else:
            for n in self.state.keys():
                if n.startswith(prefix):
                    names.append(n)
        return sorted(names)

    def assert_eq(self, name: str, expected: int, msg: Optional[str] = None):
        """断言信号值等于期望值，失败时抛出 AssertionError。"""
        actual = self.get_int(name)
        if actual != expected:
            raise AssertionError(
                f"Assertion failed at t={self.time_ns}: {name}={actual} (expected {expected})"
                + (f" | {msg}" if msg else "")
            )

    # -----------------------------------------------------------------
    # Memory dump
    # -----------------------------------------------------------------
    def dump_memory(self, name: str, start: int = 0, end: Optional[int] = None, fmt: str = "hex") -> str:
        """Dump a memory region to a formatted string.

        fmt: "hex" | "bin" | "dec"
        """
        if self._jit is not None:
            mem_idx = self._jit.mem_idx.get(name)
            if mem_idx is not None:
                mem = self._jit.memories[mem_idx]
                end = end if end is not None else len(mem)
                lines = [f"Memory '{name}' [{start}:{end-1}]:"]
                for addr in range(start, min(end, len(mem))):
                    val = mem[addr]
                    if fmt == "hex":
                        lines.append(f"  [{addr:04d}] = {val:04x}")
                    elif fmt == "bin":
                        lines.append(f"  [{addr:04d}] = {val:b}")
                    else:
                        lines.append(f"  [{addr:04d}] = {val}")
                return "\n".join(lines)
        # Fallback: search in AST memories
        mem = self.memories.get(name)
        if mem is not None:
            end = end if end is not None else len(mem)
            lines = [f"Memory '{name}' [{start}:{end-1}]:"]
            for addr in range(start, min(end, len(mem))):
                val = int(mem[addr]) if isinstance(mem[addr], SimValue) else mem[addr]
                if fmt == "hex":
                    lines.append(f"  [{addr:04d}] = {val:04x}")
                elif fmt == "bin":
                    lines.append(f"  [{addr:04d}] = {val:b}")
                else:
                    lines.append(f"  [{addr:04d}] = {val}")
            return "\n".join(lines)
        raise KeyError(f"Memory '{name}' not found")

    def poke_memory(self, name: str, addr: int, value: int):
        """Write a value to a memory location by name."""
        if self._jit is not None:
            mem_idx = self._jit.mem_idx.get(name)
            if mem_idx is not None:
                mem = self._jit.memories[mem_idx]
                if 0 <= addr < len(mem):
                    mem[addr] = int(value) & ((1 << 64) - 1)
                    return
        # Fallback: search in AST memories
        mem = self.memories.get(name)
        if mem is not None:
            if 0 <= addr < len(mem):
                width = mem.width
                mask = (1 << width) - 1
                mem[addr] = int(value) & mask
                return
        raise KeyError(f"Memory '{name}' not found")

    def peek_memory(self, name: str, addr: int) -> int:
        """Read a value from a memory location by name."""
        if self._jit is not None:
            mem_idx = self._jit.mem_idx.get(name)
            if mem_idx is not None:
                mem = self._jit.memories[mem_idx]
                if 0 <= addr < len(mem):
                    return int(mem[addr])
        # Fallback: search in AST memories
        mem = self.memories.get(name)
        if mem is not None:
            if 0 <= addr < len(mem):
                val = mem[addr]
                return int(val) if isinstance(val, SimValue) else val
        raise KeyError(f"Memory '{name}' not found")

    # -----------------------------------------------------------------
    # Breakpoints
    # -----------------------------------------------------------------
    def add_breakpoint(self, condition: Callable[["Simulator"], bool]):
        """Add a breakpoint condition. condition(sim) -> bool."""
        if not hasattr(self, '_breakpoints'):
            self._breakpoints: List[Callable[["Simulator"], bool]] = []
        self._breakpoints.append(condition)

    def run_until_break(self, max_cycles: int = 10000) -> int:
        """Run until a breakpoint fires or max_cycles reached. Returns cycles run."""
        if not hasattr(self, '_breakpoints'):
            self._breakpoints = []
        for c in range(max_cycles):
            self.step()
            for bp in self._breakpoints:
                if bp(self):
                    return c + 1
        return max_cycles

    def run(self, cycles: int):
        """连续运行多个时钟周期。"""
        for _ in range(cycles):
            self.step()

    # -----------------------------------------------------------------
    # Submodule sync helpers
    # -----------------------------------------------------------------
    def _sync_to_child(self, child_sim: "Simulator", port_map: Dict[str, Expr]):
        """将父模块信号值通过 port_map 驱动到子模块输入端口。"""
        for port_name, expr in port_map.items():
            if port_name in child_sim.module._inputs:
                val = self._eval_parent_expr(expr)
                cur = child_sim.state.get(port_name)
                if cur != val:
                    child_sim.set(port_name, val)

    def _sync_from_child(self, child_sim: "Simulator", port_map: Dict[str, Expr]):
        """将子模块输出/线网值通过 port_map 写回父模块信号。"""
        for port_name, expr in port_map.items():
            if port_name in child_sim.module._outputs or port_name in child_sim.module._wires:
                # _eval_comb 使用 AST 解释器更新 state，而非 JIT；直接读 state
                val = child_sim.state.get(port_name, 0)
                self._write_parent_expr(expr, val)
                # 额外：设置同名键供_eval_expr查找
                # 避免对 BitSelect/PartSelect 覆盖父模块向量信号
                from rtlgen.core import Ref
                if isinstance(expr, Ref):
                    self.state[port_name] = val
        # 额外：同步所有子模块Output到parent state（供parent comb评估复杂表达式时使用）
        # 但避免覆盖已在port_map中写回的向量信号
        mapped_outs = set(port_map.keys()) & set(child_sim.module._outputs.keys())
        for out_name, out_sig in child_sim.module._outputs.items():
            if out_name not in mapped_outs:
                val = child_sim.state.get(out_name, 0)
                self.state[out_name] = val

    def _eval_parent_expr(self, expr: Any, loop_vars: Optional[Dict[str, int]] = None) -> Union[int, SimValue]:
        """在父模块 state 中评估一个表达式（用于端口连接）。"""
        if isinstance(expr, int):
            return _make_xz(expr, max(expr.bit_length(), 1)) if self.use_xz else expr
        if isinstance(expr, Const):
            return _make_xz(expr.value, expr.width) if self.use_xz else int(expr.value)
        from rtlgen.core import Signal
        if isinstance(expr, Signal):
            return self._eval_parent_expr(expr._expr, loop_vars)
        if isinstance(expr, Ref):
            # 优先从子模块output直接读取（避免同名信号冲突）
            sig_id = id(expr.signal)
            if sig_id in self._output_signal_map:
                child_sim = self._output_signal_map[sig_id]
                return child_sim.get(expr.signal.name)
            name = expr.signal.name
            if name in self.state:
                return self.state[name]
            return self._get_param_value(name, expr.signal.width)
        if isinstance(expr, BinOp):
            l = self._eval_parent_expr(expr.lhs, loop_vars)
            r = self._eval_parent_expr(expr.rhs, loop_vars)
            return self._binop(expr.op, l, r, expr.width)
        if isinstance(expr, UnaryOp):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            return self._unop(expr.op, v, expr.width)
        if isinstance(expr, PartSelect):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            offset = int(self._eval_parent_expr(expr.offset, loop_vars))
            w = expr.width
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                return SimValue((v.v >> offset) & ((1 << w) - 1), (v.x_mask >> offset) & ((1 << w) - 1), (v.z_mask >> offset) & ((1 << w) - 1), w)
            return (v >> offset) & ((1 << w) - 1)
        if isinstance(expr, Slice):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            w = expr.hi - expr.lo + 1
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                return SimValue((v.v >> expr.lo) & ((1 << w) - 1), (v.x_mask >> expr.lo) & ((1 << w) - 1), (v.z_mask >> expr.lo) & ((1 << w) - 1), w)
            return (v >> expr.lo) & ((1 << w) - 1)
        if isinstance(expr, BitSelect):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            idx = self._eval_parent_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                return SimValue((v.v >> idx_i) & 1, (v.x_mask >> idx_i) & 1, 0, 1)
            return (v >> idx_i) & 1
        if isinstance(expr, Concat):
            if self.use_xz:
                result_v = 0
                result_x = 0
                result_z = 0
                offset = 0
                for op in reversed(expr.operands):
                    op_val = _make_xz(self._eval_parent_expr(op, loop_vars), op.width)
                    result_v |= (op_val.v & ((1 << op.width) - 1)) << offset
                    result_x |= (op_val.x_mask & ((1 << op.width) - 1)) << offset
                    result_z |= (op_val.z_mask & ((1 << op.width) - 1)) << offset
                    offset += op.width
                return SimValue(result_v, result_x, result_z, expr.width)
            result = 0
            offset = 0
            for op in reversed(expr.operands):
                result |= (self._eval_parent_expr(op, loop_vars) & ((1 << op.width) - 1)) << offset
                offset += op.width
            return result
        if isinstance(expr, Mux):
            cond = self._eval_parent_expr(expr.cond, loop_vars)
            if self.use_xz:
                c = _make_xz(cond, 1)
                if c.x_mask & 1:
                    return SimValue(0, x_mask=(1 << expr.width) - 1, width=expr.width)
                return self._eval_parent_expr(expr.true_expr if c.v & 1 else expr.false_expr, loop_vars)
            return self._eval_parent_expr(expr.true_expr if cond else expr.false_expr, loop_vars)
        if isinstance(expr, ArrayRead):
            idx = self._eval_parent_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            arr_state = self.state.get(expr.array_name, {})
            if isinstance(arr_state, dict):
                val = arr_state.get(idx_i, 0)
                if self.use_xz:
                    return _make_xz(val, expr.width)
                return int(val) & ((1 << expr.width) - 1)
            return 0 if not self.use_xz else SimValue(0, width=expr.width)
        if isinstance(expr, GenVar):
            if loop_vars is None or expr.name not in loop_vars:
                raise RuntimeError(f"GenVar '{expr.name}' used outside of ForGen loop in simulation")
            return loop_vars[expr.name]
        raise TypeError(f"Unsupported parent expression type: {type(expr)}")

    def _write_parent_expr(self, expr: Any, value: Union[int, SimValue], loop_vars: Optional[Dict[str, int]] = None):
        """将值写回父模块信号（支持 Ref / BitSelect / Slice）。"""
        if isinstance(expr, Ref):
            name = expr.signal.name
            width = expr.signal.width
            mask = (1 << width) - 1
            self.state[name] = _make_xz(value, width) if self.use_xz else (int(value) & mask)
        elif isinstance(expr, BitSelect):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            idx = self._eval_parent_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            name = expr.operand.signal.name
            width = expr.operand.width
            bit = int(value) & 1
            if self.use_xz:
                current = _make_xz(v, width)
                bit_x = isinstance(value, SimValue) and value.is_x(0)
                if bit_x:
                    new_x = current.x_mask | (1 << idx_i)
                    new_v = current.v
                else:
                    new_x = current.x_mask & ~(1 << idx_i)
                    new_v = current.v | (bit << idx_i) if bit else current.v & ~(1 << idx_i)
                self.state[name] = SimValue(new_v & ((1 << width) - 1), new_x, current.z_mask, width)
            else:
                if bit:
                    new_val = v | (1 << idx_i)
                else:
                    new_val = v & ~(1 << idx_i)
                self.state[name] = new_val & ((1 << width) - 1)
        elif isinstance(expr, PartSelect):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            idx_lo = int(self._eval_parent_expr(expr.offset, loop_vars))
            w = expr.width
            name = expr.operand.signal.name
            width = expr.operand.width
            mask = ((1 << w) - 1) << idx_lo
            if self.use_xz:
                current = _make_xz(v, width)
                val_int = int(value) & ((1 << w) - 1)
                val_x = (value.x_mask if isinstance(value, SimValue) else 0) & ((1 << w) - 1)
                new_v = (current.v & ~mask) | (val_int << idx_lo)
                new_x = (current.x_mask & ~mask) | (val_x << idx_lo)
                self.state[name] = SimValue(new_v & ((1 << width) - 1), new_x, current.z_mask, width)
            else:
                new_val = (v & ~mask) | ((int(value) & ((1 << w) - 1)) << idx_lo)
                self.state[name] = new_val & ((1 << width) - 1)
        elif isinstance(expr, Slice):
            v = self._eval_parent_expr(expr.operand, loop_vars)
            idx_lo = expr.lo
            w = expr.hi - expr.lo + 1
            name = expr.operand.signal.name
            width = expr.operand.width
            mask = ((1 << w) - 1) << idx_lo
            if self.use_xz:
                current = _make_xz(v, width)
                val_int = int(value) & ((1 << w) - 1)
                val_x = (value.x_mask if isinstance(value, SimValue) else 0) & ((1 << w) - 1)
                new_v = (current.v & ~mask) | (val_int << idx_lo)
                new_x = (current.x_mask & ~mask) | (val_x << idx_lo)
                self.state[name] = SimValue(new_v & ((1 << width) - 1), new_x, current.z_mask, width)
            else:
                new_val = (v & ~mask) | ((int(value) & ((1 << w) - 1)) << idx_lo)
                self.state[name] = new_val & ((1 << width) - 1)
        elif isinstance(expr, ArrayRead):
            idx = self._eval_parent_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            name = expr.array_name
            width = expr.width
            if self.use_xz:
                new_val = _make_xz(value, width)
                st = dict(self.state.get(name, {}))
                st[idx_i] = new_val
                self.state[name] = st
            else:
                new_val = int(value) & ((1 << width) - 1)
                st = dict(self.state.get(name, {}))
                st[idx_i] = new_val
                self.state[name] = st
        elif isinstance(expr, Concat):
            # 理论上 output 不会连接到 Concat，但这里简单处理：忽略
            # 因为 SV 中 output 连到 Concat 也是非法的（需要中间 wire）
            pass
        else:
            raise TypeError(f"Cannot write to parent expression type: {type(expr)}")

    # -----------------------------------------------------------------
    # Evaluation engines
    # -----------------------------------------------------------------
    def _eval_comb(self):
        """评估组合逻辑直到收敛（支持跨模块依赖链）。"""
        max_iter = 100
        for _ in range(max_iter):
            changed = False

            # 子模块 comb（同步 -> 评估 -> 写回）
            for _, child_sim, port_map in self._subsim_info:
                self._sync_to_child(child_sim, port_map)
                state_before = {k: _to_int(v) for k, v in child_sim.state.items()}
                child_sim._eval_comb()
                if {k: _to_int(v) for k, v in child_sim.state.items()} != state_before:
                    changed = True
                self._sync_from_child(child_sim, port_map)

            # 父模块 comb
            state_before = {k: _to_int(v) for k, v in self.state.items()}
            for body in self.module._comb_blocks:
                self._exec_stmts(body, mode="comb")
            for stmt in self.module._top_level:
                if isinstance(stmt, Assign):
                    self._exec_assign(stmt, mode="comb")
                elif isinstance(stmt, IndexedAssign):
                    self._exec_indexed_assign(stmt, mode="comb")
                elif isinstance(stmt, IfNode):
                    self._exec_if(stmt, mode="comb")
                elif isinstance(stmt, SwitchNode):
                    self._exec_switch(stmt, mode="comb")
                elif isinstance(stmt, MemWrite):
                    self._exec_mem_write(stmt)
                elif isinstance(stmt, ForGenNode):
                    self._exec_for_gen(stmt, mode="comb")
                elif isinstance(stmt, GenIfNode):
                    self._exec_gen_if(stmt, mode="comb")
                # SubmoduleInst / Comment ignored
            if {k: _to_int(v) for k, v in self.state.items()} != state_before:
                changed = True

            if not changed:
                break

    def _eval_seq(self, clk: Optional[str] = None):
        for clock, rst, reset_async, reset_active_low, body in self.module._seq_blocks:
            if clk is None or clock.name == clk:
                self._exec_stmts(body, mode="seq")

    # -----------------------------------------------------------------
    # Statement execution
    # -----------------------------------------------------------------
    def _exec_stmts(self, stmts: List[Any], mode: str, loop_vars: Optional[Dict[str, int]] = None):
        env = loop_vars or {}
        for stmt in stmts:
            if isinstance(stmt, Assign):
                self._exec_assign(stmt, mode, env)
            elif isinstance(stmt, IndexedAssign):
                self._exec_indexed_assign(stmt, mode, env)
            elif isinstance(stmt, ArrayWrite):
                self._exec_array_write(stmt, mode, env)
            elif isinstance(stmt, IfNode):
                self._exec_if(stmt, mode, env)
            elif isinstance(stmt, SwitchNode):
                self._exec_switch(stmt, mode, env)
            elif isinstance(stmt, MemWrite):
                self._exec_mem_write(stmt, env)
            elif isinstance(stmt, ForGenNode):
                self._exec_for_gen(stmt, mode, env)
            elif isinstance(stmt, GenIfNode):
                self._exec_gen_if(stmt, mode, env)
            elif isinstance(stmt, Comment):
                pass
            elif isinstance(stmt, SubmoduleInst):
                pass  # 子模块在 _eval_comb / step 中统一处理

    def _exec_assign(self, stmt: Assign, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        val = self._eval_expr(stmt.value, loop_vars)
        width = stmt.target.width if hasattr(stmt.target, 'width') else stmt.target.width
        if self.use_xz:
            val = _make_xz(val, width)
        else:
            val = int(val) & ((1 << width) - 1)
        if mode == "seq" and not stmt.blocking:
            if isinstance(stmt.target, Signal):
                self.next_state[stmt.target.name] = val
            else:
                # 需要读取当前 state 并写回
                current = self._eval_parent_expr(stmt.target, loop_vars)
                # 计算新值...
                # 实际上对于 seq 的 PartSelect 赋值，我们需要写回底层信号
                self._write_parent_expr(stmt.target, val, loop_vars)
        else:
            if isinstance(stmt.target, Signal):
                self.state[stmt.target.name] = val
            else:
                self._write_parent_expr(stmt.target, val, loop_vars)

    def _exec_indexed_assign(self, stmt: IndexedAssign, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        idx = self._eval_expr(stmt.index, loop_vars)
        val = self._eval_expr(stmt.value, loop_vars)
        name = stmt.target_signal.name
        width = stmt.target_signal.width
        idx_i = int(idx) if isinstance(idx, SimValue) else idx
        if self.use_xz:
            current = self.state.get(name, SimValue(0, width=width))
            if isinstance(current, int):
                current = SimValue(current, width=width)
            bit_val = int(val) & 1
            bit_x = (isinstance(val, SimValue) and val.is_x(0))
            c_v = current.v if isinstance(current, SimValue) else current
            c_x = current.x_mask if isinstance(current, SimValue) else 0
            if bit_x:
                new_x_mask = c_x | (1 << idx_i)
                new_v_val = c_v
            else:
                new_x_mask = c_x & ~(1 << idx_i)
                if bit_val:
                    new_v_val = c_v | (1 << idx_i)
                else:
                    new_v_val = c_v & ~(1 << idx_i)
            new_val = SimValue(new_v_val, new_x_mask, 0, width)
            if mode == "seq" and not stmt.blocking:
                self.next_state[name] = new_val
            else:
                self.state[name] = new_val
        else:
            current = self.state.get(name, 0)
            bit = int(val) & 1
            mask = 1 << idx_i
            if bit:
                new_val = current | mask
            else:
                new_val = current & ~mask
            new_val &= (1 << width) - 1
            if mode == "seq" and not stmt.blocking:
                self.next_state[name] = new_val
            else:
                self.state[name] = new_val

    def _exec_array_write(self, stmt: ArrayWrite, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        idx = self._eval_expr(stmt.index, loop_vars)
        val = self._eval_expr(stmt.value, loop_vars)
        name = stmt.array_name
        arr = self.module._arrays.get(name)
        width = arr.width if arr else 32
        idx_i = int(idx) if isinstance(idx, SimValue) else idx
        if self.use_xz:
            new_val = _make_xz(val, width)
            if mode == "seq" and not stmt.blocking:
                ns = dict(self.next_state.get(name, self.state.get(name, {})))
                ns[idx_i] = new_val
                self.next_state[name] = ns
            else:
                st = dict(self.state.get(name, {}))
                st[idx_i] = new_val
                self.state[name] = st
        else:
            new_val = int(val) & ((1 << width) - 1)
            if mode == "seq" and not stmt.blocking:
                ns = dict(self.next_state.get(name, self.state.get(name, {})))
                ns[idx_i] = new_val
                self.next_state[name] = ns
            else:
                st = dict(self.state.get(name, {}))
                st[idx_i] = new_val
                self.state[name] = st

    def _exec_gen_if(self, stmt: GenIfNode, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        cond = self._eval_expr(stmt.cond, loop_vars)
        if self.use_xz:
            c = bool(int(cond)) if isinstance(cond, SimValue) else bool(cond)
        else:
            c = bool(cond)
        if c:
            self._exec_stmts(stmt.then_body, mode, loop_vars)
        elif stmt.else_body:
            self._exec_stmts(stmt.else_body, mode, loop_vars)

    def _exec_if(self, stmt: IfNode, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        cond = self._eval_expr(stmt.cond, loop_vars)
        if self.use_xz:
            c = bool(int(cond)) if isinstance(cond, SimValue) else bool(cond)
        else:
            c = bool(cond)
        if c:
            self._exec_stmts(stmt.then_body, mode, loop_vars)
        elif stmt.else_body:
            self._exec_stmts(stmt.else_body, mode, loop_vars)

    def _exec_switch(self, stmt: SwitchNode, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        expr_val = self._eval_expr(stmt.expr, loop_vars)
        matched = False
        expr_i = int(expr_val) if isinstance(expr_val, SimValue) else expr_val
        for val, body in stmt.cases:
            case_val = self._eval_expr(val, loop_vars)
            case_i = int(case_val) if isinstance(case_val, SimValue) else case_val
            if expr_i == case_i:
                self._exec_stmts(body, mode, loop_vars)
                matched = True
                break
        if not matched and stmt.default_body:
            self._exec_stmts(stmt.default_body, mode, loop_vars)

    def _exec_mem_write(self, stmt: MemWrite, loop_vars: Optional[Dict[str, int]] = None):
        addr = self._eval_expr(stmt.addr, loop_vars)
        val = self._eval_expr(stmt.value, loop_vars)
        mem = self.memories.get(stmt.mem_name)
        if mem is not None:
            addr_i = int(addr) if isinstance(addr, SimValue) else addr
            addr_i = addr_i % len(mem)
            if self.use_xz:
                mem[addr_i] = _make_xz(val, self._width_of_mem(stmt.mem_name))
            else:
                mem[addr_i] = int(val)

    def _width_of_mem(self, name: str) -> int:
        mem = self.module._memories.get(name)
        return mem.width if mem else 32

    def _exec_for_gen(self, stmt: ForGenNode, mode: str, loop_vars: Optional[Dict[str, int]] = None):
        env = dict(loop_vars) if loop_vars else {}
        for i in range(stmt.start, stmt.end):
            env[stmt.var_name] = i
            self._exec_stmts(stmt.body, mode, env)

    def _get_param_value(self, name: str, width: int = 1):
        """优先从 param_overrides 取值，否则从 module._params 取值。"""
        if name in self._param_overrides:
            v = self._param_overrides[name]
            return _make_xz(v, max(v.bit_length(), 1)) if self.use_xz else v
        param = self.module._params.get(name)
        if param is not None:
            v = param.value
            return _make_xz(v, max(v.bit_length(), 1)) if self.use_xz else v
        return 0 if not self.use_xz else SimValue(0, width=width)

    # -----------------------------------------------------------------
    # Expression evaluation
    # -----------------------------------------------------------------
    def _eval_expr(self, expr: Any, loop_vars: Optional[Dict[str, int]] = None):
        if isinstance(expr, int):
            return _make_xz(expr, max(expr.bit_length(), 1)) if self.use_xz else expr
        if isinstance(expr, Const):
            if self.use_xz:
                return SimValue(expr.value, width=expr.width)
            return int(expr.value)
        from rtlgen.core import Signal
        if isinstance(expr, Signal):
            return self._eval_expr(expr._expr, loop_vars)
        if isinstance(expr, Ref):
            # 优先从子模块output直接读取（避免同名信号冲突，并反映seq commit后的最新值）
            sig_id = id(expr.signal)
            if sig_id in self._output_signal_map:
                child_sim = self._output_signal_map[sig_id]
                return child_sim.get(expr.signal.name)
            name = expr.signal.name
            if name in self.state:
                return self.state[name]
            return self._get_param_value(name, expr.signal.width)
        if isinstance(expr, BinOp):
            l = self._eval_expr(expr.lhs, loop_vars)
            r = self._eval_expr(expr.rhs, loop_vars)
            return self._binop(expr.op, l, r, expr.width)
        if isinstance(expr, UnaryOp):
            v = self._eval_expr(expr.operand, loop_vars)
            return self._unop(expr.op, v, expr.width)
        if isinstance(expr, PartSelect):
            v = self._eval_expr(expr.operand, loop_vars)
            offset = int(self._eval_expr(expr.offset, loop_vars))
            w = expr.width
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                new_v = (v.v >> offset) & ((1 << w) - 1)
                new_x = (v.x_mask >> offset) & ((1 << w) - 1)
                new_z = (v.z_mask >> offset) & ((1 << w) - 1)
                return SimValue(new_v, new_x, new_z, w)
            return (v >> offset) & ((1 << w) - 1)
        if isinstance(expr, Slice):
            v = self._eval_expr(expr.operand, loop_vars)
            w = expr.hi - expr.lo + 1
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                new_v = (v.v >> expr.lo) & ((1 << w) - 1)
                new_x = (v.x_mask >> expr.lo) & ((1 << w) - 1)
                new_z = (v.z_mask >> expr.lo) & ((1 << w) - 1)
                return SimValue(new_v, new_x, new_z, w)
            return (v >> expr.lo) & ((1 << w) - 1)
        if isinstance(expr, BitSelect):
            v = self._eval_expr(expr.operand, loop_vars)
            idx = self._eval_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            if self.use_xz:
                v = _make_xz(v, expr.operand.width)
                bit_v = (v.v >> idx_i) & 1
                bit_x = (v.x_mask >> idx_i) & 1
                return SimValue(bit_v, bit_x, 0, 1)
            return (v >> idx_i) & 1
        if isinstance(expr, Concat):
            if self.use_xz:
                result_v = 0
                result_x = 0
                result_z = 0
                offset = 0
                for op in reversed(expr.operands):
                    op_val = _make_xz(self._eval_expr(op, loop_vars), op.width)
                    result_v |= (op_val.v & ((1 << op.width) - 1)) << offset
                    result_x |= (op_val.x_mask & ((1 << op.width) - 1)) << offset
                    result_z |= (op_val.z_mask & ((1 << op.width) - 1)) << offset
                    offset += op.width
                return SimValue(result_v, result_x, result_z, expr.width)
            result = 0
            offset = 0
            for op in reversed(expr.operands):
                result |= (self._eval_expr(op, loop_vars) & ((1 << op.width) - 1)) << offset
                offset += op.width
            return result
        if isinstance(expr, Mux):
            cond = self._eval_expr(expr.cond, loop_vars)
            if self.use_xz:
                c = _make_xz(cond, 1)
                if c.x_mask & 1:
                    return SimValue(0, x_mask=(1 << expr.width) - 1, width=expr.width)
                return self._eval_expr(expr.true_expr if c.v & 1 else expr.false_expr, loop_vars)
            return self._eval_expr(expr.true_expr if cond else expr.false_expr, loop_vars)
        if isinstance(expr, MemRead):
            addr = self._eval_expr(expr.addr, loop_vars)
            mem = self.memories.get(expr.mem_name)
            if mem is not None:
                addr_i = int(addr) if isinstance(addr, SimValue) else addr
                addr_i = addr_i % len(mem)
                val = mem[addr_i]
                if self.use_xz:
                    return _make_xz(val, expr.width)
                return int(val)
            return 0 if not self.use_xz else SimValue(0, width=expr.width)
        if isinstance(expr, ArrayRead):
            idx = self._eval_expr(expr.index, loop_vars)
            idx_i = int(idx) if isinstance(idx, SimValue) else idx
            arr_state = self.state.get(expr.array_name, {})
            if isinstance(arr_state, dict):
                val = arr_state.get(idx_i, 0)
                if self.use_xz:
                    return _make_xz(val, expr.width)
                return int(val) & ((1 << expr.width) - 1)
            return 0 if not self.use_xz else SimValue(0, width=expr.width)
        if isinstance(expr, GenVar):
            if loop_vars is None:
                raise RuntimeError("GenVar used outside of ForGen loop in simulation")
            return loop_vars.get(expr.name, 0)
        raise TypeError(f"Unsupported expression type: {type(expr)}")

    def _binop(self, op: str, l, r, width: int):
        if self.use_xz:
            lv = _make_xz(l, width)
            rv = _make_xz(r, width)
            x_mask = lv.x_mask | rv.x_mask | lv.z_mask | rv.z_mask
            result_width = width
            if op == "+":
                v = (lv.v + rv.v) & ((1 << result_width) - 1)
            elif op == "-":
                v = (lv.v - rv.v) & ((1 << result_width) - 1)
            elif op == "*":
                v = (lv.v * rv.v) & ((1 << result_width) - 1)
            elif op == "&":
                v = (lv.v & rv.v) & ((1 << result_width) - 1)
            elif op == "|":
                v = (lv.v | rv.v) & ((1 << result_width) - 1)
            elif op == "^":
                v = (lv.v ^ rv.v) & ((1 << result_width) - 1)
            elif op == "==":
                v = 1 if lv.v == rv.v else 0
            elif op == "!=":
                v = 1 if lv.v != rv.v else 0
            elif op == "<":
                v = 1 if lv.v < rv.v else 0
            elif op == "<=":
                v = 1 if lv.v <= rv.v else 0
            elif op == ">":
                v = 1 if lv.v > rv.v else 0
            elif op == ">=":
                v = 1 if lv.v >= rv.v else 0
            elif op == "<<":
                v = (lv.v << rv.v) & ((1 << result_width) - 1)
            elif op == ">>":
                v = lv.v >> rv.v
            elif op == "%":
                v = (lv.v % rv.v) & ((1 << result_width) - 1) if rv.v != 0 else 0
            else:
                raise ValueError(f"Unknown binary operator: {op}")
            return SimValue(v, x_mask, 0, result_width)
        else:
            l_i = int(l) if isinstance(l, SimValue) else l
            r_i = int(r) if isinstance(r, SimValue) else r
            if op == "+":
                return l_i + r_i
            if op == "-":
                return l_i - r_i
            if op == "*":
                return l_i * r_i
            if op == "&":
                return l_i & r_i
            if op == "|":
                return l_i | r_i
            if op == "^":
                return l_i ^ r_i
            if op == "==":
                return 1 if l_i == r_i else 0
            if op == "!=":
                return 1 if l_i != r_i else 0
            if op == "<":
                return 1 if l_i < r_i else 0
            if op == "<=":
                return 1 if l_i <= r_i else 0
            if op == ">":
                return 1 if l_i > r_i else 0
            if op == ">=":
                return 1 if l_i >= r_i else 0
            if op == "<<":
                return l_i << r_i
            if op == ">>":
                return l_i >> r_i
            if op == "%":
                return l_i % r_i if r_i != 0 else 0
            raise ValueError(f"Unknown binary operator: {op}")

    def _unop(self, op: str, operand, width: int):
        if self.use_xz:
            v = _make_xz(operand, width)
            if op == "~":
                new_v = (~v.v) & ((1 << width) - 1)
                return SimValue(new_v, v.x_mask, v.z_mask, width)
            raise ValueError(f"Unsupported unary op: {op}")
        v_i = int(operand) if isinstance(operand, SimValue) else operand
        if op == "~":
            return (~v_i) & ((1 << width) - 1)
        raise ValueError(f"Unsupported unary op: {op}")

    # -----------------------------------------------------------------
    # Trace
    # -----------------------------------------------------------------
    def _do_trace(self):
        signals = self.trace_signals
        if signals is None:
            # When JIT is active, trace all JIT signals (hierarchical names)
            if self._jit is not None:
                signals = self._jit.sig_names
            else:
                signals = list(self.state.keys())
        snapshot = {"_time": self.time_ns, "_cycle": self._cycle_count}
        self._cycle_count += 1
        for name in signals:
            v = self.get(name)
            snapshot[name] = int(v) if isinstance(v, SimValue) else v
        self.trace.append(snapshot)
        if self.trace_max_size is not None and len(self.trace) > self.trace_max_size:
            self.trace.pop(0)

    def dump_trace(self, fmt: str = "table"):
        """打印仿真 trace。

        fmt: "table" | "vcd"
        """
        if fmt == "table":
            if not self.trace:
                print("No trace data.")
                return
            signals = [k for k in self.trace[0].keys() if k != "_time"]
            header = ["Time", "Cycle"] + signals
            print(" | ".join(f"{h:>10}" for h in header))
            print("-" * (13 * len(header)))
            for cycle, snap in enumerate(self.trace):
                t = snap.get("_time", cycle * self.clock_period_ns)
                row = [f"{t:>10.1f}", f"{cycle:>10}"] + [f"{snap[s]:>10}" for s in signals]
                print(" | ".join(row))
        elif fmt == "vcd":
            print(self.to_vcd())
        else:
            raise ValueError(f"Unknown trace format: {fmt}")

    def to_vcd(self, timescale: str = "1ns") -> str:
        """将 trace 转为简易 VCD 字符串。"""
        if not self.trace:
            return ""
        lines = []
        lines.append(f"$timescale {timescale} $end")
        lines.append("$scope module top $end")
        signals = [k for k in self.trace[0].keys() if k != "_time"]
        ids = {s: chr(33 + i) if i < 90 else f"s{i}" for i, s in enumerate(signals)}
        for s in signals:
            width = self._width_of(s)
            lines.append(f"$var wire {width} {ids[s]} {s} $end")
        lines.append("$upscope $end")
        lines.append("$enddefinitions $end")
        lines.append("$dumpvars")
        for s in signals:
            val = self.trace[0][s]
            val_str = format(val, 'b') if val != 0 else '0'
            lines.append(f"b{val_str} {ids[s]}")
        lines.append("$end")
        for snap in self.trace:
            t = snap.get("_time", 0)
            lines.append(f"#{int(t)}")
            for s in signals:
                val = snap[s]
                val_str = format(val, 'b') if val != 0 else '0'
                lines.append(f"b{val_str} {ids[s]}")
        return "\n".join(lines)
