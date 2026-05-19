"""
rtlgen.verification — 行为级模型生成、协议描述、等价性检查与系统集成

基于 SAT/SMT 形式化验证（Z3）和 AST 行为模型提取，提供高层验证与
集成工具。
"""
from __future__ import annotations

import json
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rtlgen.core import Assign, IfNode, Module, Signal, SwitchNode
from rtlgen.sim import Simulator


# =====================================================================
# BehavioralModel — 独立可执行的行为级模型
# =====================================================================

class SignalState:
    """行为模型中的信号状态封装。"""

    __slots__ = ("width", "value")

    def __init__(self, width: int, value: int = 0):
        self.width = width
        self.value = value & ((1 << width) - 1) if width < 64 else value & 0xFFFFFFFFFFFFFFFF

    def set(self, value: int):
        mask = (1 << self.width) - 1 if self.width < 64 else 0xFFFFFFFFFFFFFFFF
        self.value = value & mask


class BehavioralModel:
    """从 DSL AST 生成的独立可执行行为级模型。

    与 ``Simulator`` 的区别：
    - ``Simulator`` 直接在 AST 上解释执行，保留完整的表达式树；
    - ``BehavioralModel`` 将 AST 编译为扁平的 Python 函数列表，
      不保留原始 AST，因此可以序列化、独立运行，且开销更小。

    典型用法：
        model = BehavioralModelGenerator.generate(module)
        model.reset({"rst_n": 0})
        out = model.step({"a": 5, "b": 3})
    """

    def __init__(self, name: str):
        self.name = name
        self.inputs: Dict[str, SignalState] = {}
        self.outputs: Dict[str, SignalState] = {}
        self.regs: Dict[str, SignalState] = {}
        self.wires: Dict[str, SignalState] = {}
        self._comb_funcs: List[Callable[["BehavioralModel"], None]] = []
        self._seq_funcs: List[Callable[["BehavioralModel"], None]] = []
        self._next_regs: Dict[str, int] = {}

    # -----------------------------------------------------------------
    # Registration API (used by generator)
    # -----------------------------------------------------------------
    def add_input(self, name: str, width: int):
        self.inputs[name] = SignalState(width)

    def add_output(self, name: str, width: int):
        self.outputs[name] = SignalState(width)

    def add_reg(self, name: str, width: int, reset_value: int = 0):
        self.regs[name] = SignalState(width, reset_value)

    def add_wire(self, name: str, width: int):
        self.wires[name] = SignalState(width)

    def add_comb_func(self, fn: Callable[["BehavioralModel"], None]):
        self._comb_funcs.append(fn)

    def add_seq_func(self, fn: Callable[["BehavioralModel"], None]):
        self._seq_funcs.append(fn)

    # -----------------------------------------------------------------
    # Execution API
    # -----------------------------------------------------------------
    def reset(self, values: Optional[Dict[str, int]] = None):
        """复位模型状态。

        Args:
            values: 信号名 -> 复位值。未指定的 Reg 保持当前值。
        """
        if values:
            for name, val in values.items():
                if name in self.regs:
                    self.regs[name].set(val)
                if name in self.wires:
                    self.wires[name].set(val)
                if name in self.outputs:
                    self.outputs[name].set(val)

    def set_input(self, name: str, value: int):
        """设置单个输入值。"""
        if name in self.inputs:
            self.inputs[name].set(value)

    def get_output(self, name: str) -> int:
        """读取单个输出值。"""
        return self.outputs.get(name, SignalState(1)).value

    def get_reg(self, name: str) -> int:
        """读取单个寄存器值。"""
        return self.regs.get(name, SignalState(1)).value

    def step(self, inputs: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """单步仿真。

        执行流程：
        1. 应用外部输入
        2. 迭代评估组合逻辑直到收敛
        3. 评估时序逻辑（计算 next_state）
        4. 更新寄存器状态
        5. 返回当前输出快照

        Returns:
            当前周期所有输出信号的 ``{name: value}`` 字典。
        """
        # 1. Apply inputs
        if inputs:
            for name, val in inputs.items():
                if name in self.inputs:
                    self.inputs[name].set(val)

        # 2. Evaluate combinational logic (iterate to convergence)
        #    Build a flat state dict for quick comparison
        def _snapshot():
            snap = {}
            snap.update({k: v.value for k, v in self.wires.items()})
            snap.update({k: v.value for k, v in self.outputs.items()})
            return snap

        for _ in range(100):
            old = _snapshot()
            for fn in self._comb_funcs:
                fn(self)
            if _snapshot() == old:
                break

        # 3. Evaluate sequential logic (computes _next_regs)
        for fn in self._seq_funcs:
            fn(self)

        # 4. Clock edge: update registers
        for name, nxt in self._next_regs.items():
            if name in self.regs:
                self.regs[name].set(nxt)
        self._next_regs.clear()

        # 5. Return output snapshot
        return {name: st.value for name, st in self.outputs.items()}

    def run(self, input_sequence: List[Dict[str, int]]) -> List[Dict[str, int]]:
        """运行输入序列，返回每周期输出。"""
        return [self.step(inp) for inp in input_sequence]


# =====================================================================
# BehavioralModelGenerator — 从 AST 编译行为模型
# =====================================================================

class BehavioralModelGenerator:
    """从 DSL ``Module`` AST 生成独立可执行的 ``BehavioralModel``。

    生成过程通过遍历 AST 的 ``@comb`` / ``@seq`` 块，将每条语句
    编译为操作 ``BehavioralModel`` 状态的 Python 闭包。
    """

    @classmethod
    def generate(cls, module: Module) -> BehavioralModel:
        """从 Module AST 生成 ``BehavioralModel`` 实例。"""
        model = BehavioralModel(module.name)

        # Register ports
        for name, sig in module._inputs.items():
            model.add_input(name, sig.width)
        for name, sig in module._outputs.items():
            model.add_output(name, sig.width)

        # Register internal state
        for name, reg in module._regs.items():
            model.add_reg(name, reg.width, reset_value=0)
        for name, wire in module._wires.items():
            model.add_wire(name, wire.width)

        # Compile comb blocks
        for body in module._comb_blocks:
            fn = cls._compile_stmt_list(body, mode="comb")
            if fn is not None:
                model.add_comb_func(fn)

        # Compile seq blocks
        for _clk, _rst, _reset_async, _reset_active_low, body in module._seq_blocks:
            fn = cls._compile_stmt_list(body, mode="seq")
            if fn is not None:
                model.add_seq_func(fn)

        return model

    # -----------------------------------------------------------------
    # Compilation helpers
    # -----------------------------------------------------------------
    @classmethod
    def _compile_stmt_list(cls, stmts: List[Any], mode: str) -> Optional[Callable]:
        fns = [cls._compile_stmt(s, mode) for s in stmts]
        fns = [f for f in fns if f is not None]
        if not fns:
            return None

        def _run(model: BehavioralModel):
            for fn in fns:
                fn(model)
        return _run

    @classmethod
    def _compile_stmt(cls, stmt: Any, mode: str) -> Optional[Callable]:
        if isinstance(stmt, Assign):
            return cls._compile_assign(stmt, mode)
        if isinstance(stmt, IfNode):
            return cls._compile_if(stmt, mode)
        if isinstance(stmt, SwitchNode):
            return cls._compile_switch(stmt, mode)
        return None

    @classmethod
    def _compile_assign(cls, stmt: Assign, mode: str) -> Callable:
        target = stmt.target
        val_fn = cls._compile_expr(stmt.value)
        write_now = (mode == "comb") or stmt.blocking

        if isinstance(target, Signal):
            name = target.name
            width = target.width
            mask = (1 << width) - 1 if width < 64 else 0xFFFFFFFFFFFFFFFF

            def _write(model: BehavioralModel):
                v = val_fn(model) & mask
                if write_now:
                    if name in model.wires:
                        model.wires[name].set(v)
                    elif name in model.outputs:
                        model.outputs[name].set(v)
                    elif name in model.regs:
                        model.regs[name].set(v)
                else:
                    model._next_regs[name] = v
            return _write

        # Slice / PartSelect / BitSelect — RMW on underlying signal
        if isinstance(target, (Slice,)):
            base_name = cls._base_signal_name(target.operand)
            lo = target.lo
            w = target.hi - lo + 1
            val_mask = (1 << w) - 1
            inv_mask = (~(val_mask << lo)) & 0xFFFFFFFFFFFFFFFF

            def _rmw(model: BehavioralModel):
                v = val_fn(model) & val_mask
                base = cls._read_state(model, base_name)
                new_v = (base & inv_mask) | (v << lo)
                cls._write_state(model, base_name, new_v, write_now)
            return _rmw

        # For PartSelect / BitSelect we skip (rare in behavioral models)
        return None

    @classmethod
    def _compile_if(cls, stmt: IfNode, mode: str) -> Callable:
        cond_fn = cls._compile_expr(stmt.cond)
        then_fn = cls._compile_stmt_list(stmt.then_body, mode)
        else_fn = cls._compile_stmt_list(stmt.else_body, mode)

        def _if(model: BehavioralModel):
            if cond_fn(model):
                if then_fn:
                    then_fn(model)
            else:
                if else_fn:
                    else_fn(model)
        return _if

    @classmethod
    def _compile_switch(cls, stmt: SwitchNode, mode: str) -> Callable:
        sw_fn = cls._compile_expr(stmt.expr)
        cases: List[Tuple[Callable, Callable]] = []
        for ce, cb in stmt.cases:
            cev = cls._compile_expr(ce)
            cb_fn = cls._compile_stmt_list(cb, mode)
            if cb_fn:
                cases.append((cev, cb_fn))
        def_fn = cls._compile_stmt_list(stmt.default_body, mode)

        def _switch(model: BehavioralModel):
            sv = sw_fn(model)
            for cev, cb_fn in cases:
                if sv == cev(model):
                    cb_fn(model)
                    return
            if def_fn:
                def_fn(model)
        return _switch

    # -----------------------------------------------------------------
    # Expression compilation
    # -----------------------------------------------------------------
    @classmethod
    def _compile_expr(cls, expr: Any) -> Callable[[BehavioralModel], int]:
        from rtlgen.core import (
            BinOp, BitSelect, Concat, Const, Mux, PartSelect, Ref,
            Slice, UnaryOp,
        )

        if isinstance(expr, Const):
            v = expr.value & ((1 << expr.width) - 1) if expr.width < 64 else expr.value & 0xFFFFFFFFFFFFFFFF
            return lambda _m: v

        if isinstance(expr, Ref):
            name = expr.signal.name
            return lambda m: cls._read_state(m, name)

        if isinstance(expr, BinOp):
            lfn = cls._compile_expr(expr.lhs)
            rfn = cls._compile_expr(expr.rhs)
            return lambda m: cls._eval_binop(expr.op, lfn(m), rfn(m))

        if isinstance(expr, UnaryOp):
            ofn = cls._compile_expr(expr.operand)
            if expr.op == "~":
                return lambda m: (~ofn(m)) & ((1 << expr.width) - 1)
            if expr.op == "!":
                return lambda m: 1 if ofn(m) == 0 else 0
            if expr.op == "-":
                return lambda m: (-ofn(m)) & ((1 << expr.width) - 1)

        if isinstance(expr, Slice):
            ofn = cls._compile_expr(expr.operand)
            lo = expr.lo
            w = expr.hi - lo + 1
            mask = (1 << w) - 1
            return lambda m: (ofn(m) >> lo) & mask

        if isinstance(expr, Mux):
            cfn = cls._compile_expr(expr.cond)
            tfn = cls._compile_expr(expr.true_expr)
            ffn = cls._compile_expr(expr.false_expr)
            return lambda m: tfn(m) if cfn(m) else ffn(m)

        if isinstance(expr, Concat):
            fns = [cls._compile_expr(op) for op in expr.operands]
            widths = [op.width for op in expr.operands]
            return lambda m, fns=fns, widths=widths: cls._eval_concat(fns, widths, m)

        if isinstance(expr, BitSelect):
            ofn = cls._compile_expr(expr.operand)
            ifn = cls._compile_expr(expr.index)
            return lambda m: (ofn(m) >> ifn(m)) & 1

        # PartSelect with variable offset — build ITE chain at compile time
        if isinstance(expr, PartSelect):
            ofn = cls._compile_expr(expr.operand)
            off_fn = cls._compile_expr(expr.offset)
            w = expr.width
            mask = (1 << w) - 1
            total = expr.operand.width
            if isinstance(expr.offset, Const):
                lo = expr.offset.value
                return lambda m: (ofn(m) >> lo) & mask
            # Variable offset fallback (unroll small range)
            return lambda m: (ofn(m) >> off_fn(m)) & mask

        # Fallback
        return lambda _m: 0

    @staticmethod
    def _eval_binop(op: str, l: int, r: int) -> int:
        if op == "+":
            return l + r
        if op == "-":
            return l - r
        if op == "*":
            return l * r
        if op == "&":
            return l & r
        if op == "|":
            return l | r
        if op == "^":
            return l ^ r
        if op == "==":
            return 1 if l == r else 0
        if op == "!=":
            return 1 if l != r else 0
        if op == "<":
            return 1 if l < r else 0
        if op == ">":
            return 1 if l > r else 0
        if op == "<=":
            return 1 if l <= r else 0
        if op == ">=":
            return 1 if l >= r else 0
        if op == "<<":
            return l << r
        if op == ">>":
            return l >> r
        return 0

    @staticmethod
    def _eval_concat(fns: List[Callable], widths: List[int], model: BehavioralModel) -> int:
        result = 0
        offset = 0
        for fn, w in zip(reversed(fns), reversed(widths)):
            v = fn(model)
            result |= v << offset
            offset += w
        return result

    # -----------------------------------------------------------------
    # State read/write helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _read_state(model: BehavioralModel, name: str) -> int:
        if name in model.inputs:
            return model.inputs[name].value
        if name in model.regs:
            return model.regs[name].value
        if name in model.wires:
            return model.wires[name].value
        if name in model.outputs:
            return model.outputs[name].value
        return 0

    @staticmethod
    def _write_state(model: BehavioralModel, name: str, value: int, now: bool):
        if name in model.wires:
            model.wires[name].set(value)
        elif name in model.outputs:
            model.outputs[name].set(value)
        elif name in model.regs:
            if now:
                model.regs[name].set(value)
            else:
                model._next_regs[name] = value

    @staticmethod
    def _base_signal_name(expr: Any) -> str:
        from rtlgen.core import Ref, Slice, PartSelect, BitSelect
        if isinstance(expr, Ref):
            return expr.signal.name
        if isinstance(expr, (Slice, PartSelect, BitSelect)):
            return BehavioralModelGenerator._base_signal_name(expr.operand)
        return ""


# =====================================================================
# ProtocolDescriptor
# =====================================================================

class HandshakeDesc:
    """握手接口描述。"""

    def __init__(self, direction: str, valid: str, ready: Optional[str], data: Optional[str]):
        self.direction = direction
        self.valid = valid
        self.ready = ready
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "valid": self.valid,
            "ready": self.ready,
            "data": self.data,
        }


class ProtocolDescriptor:
    """描述模块的外部接口协议，自动检测 valid/ready 握手等模式。"""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.clock_ports: List[str] = []
        self.reset_ports: List[str] = []
        self.handshake_interfaces: List[HandshakeDesc] = []
        self.data_ports: List[Tuple[str, int]] = []

    @classmethod
    def analyze(cls, module: Module) -> "ProtocolDescriptor":
        """从 Module AST 自动分析协议。"""
        desc = cls(module.name)

        for name, sig in module._inputs.items():
            lname = name.lower()
            if "clk" in lname:
                desc.clock_ports.append(name)
            elif "rst" in lname or "reset" in lname:
                desc.reset_ports.append(name)

        # Detect valid/ready handshakes on inputs
        valid_ins = [n for n in module._inputs if "valid" in n.lower()]
        ready_outs = [n for n in module._outputs if "ready" in n.lower()]
        data_ins = [n for n in module._inputs
                    if "valid" not in n.lower() and "ready" not in n.lower()
                    and "clk" not in n.lower() and "rst" not in n.lower()]

        for vi in valid_ins:
            prefix = vi.replace("_valid", "").replace("_valid_i", "").replace("_i", "")
            matching_ready = [r for r in ready_outs
                              if prefix in r or r.replace("_ready", "").replace("_ready_o", "") == prefix]
            matching_data = [d for d in data_ins if prefix in d]
            desc.handshake_interfaces.append(HandshakeDesc(
                direction="input",
                valid=vi,
                ready=matching_ready[0] if matching_ready else None,
                data=matching_data[0] if matching_data else None,
            ))

        # Detect valid/ready handshakes on outputs
        valid_outs = [n for n in module._outputs if "valid" in n.lower()]
        ready_ins = [n for n in module._inputs if "ready" in n.lower()]
        data_outs = [n for n in module._outputs
                     if "valid" not in n.lower() and "ready" not in n.lower()]

        for vo in valid_outs:
            prefix = vo.replace("_valid", "").replace("_valid_o", "").replace("_o", "")
            matching_ready = [r for r in ready_ins
                              if prefix in r or r.replace("_ready", "").replace("_ready_i", "") == prefix]
            matching_data = [d for d in data_outs if prefix in d]
            desc.handshake_interfaces.append(HandshakeDesc(
                direction="output",
                valid=vo,
                ready=matching_ready[0] if matching_ready else None,
                data=matching_data[0] if matching_data else None,
            ))

        # Data ports
        for name, sig in list(module._inputs.items()) + list(module._outputs.items()):
            lname = name.lower()
            if "valid" not in lname and "ready" not in lname and "clk" not in lname and "rst" not in lname:
                desc.data_ports.append((name, sig.width))

        return desc

    def to_json(self) -> str:
        return json.dumps({
            "module": self.module_name,
            "clocks": self.clock_ports,
            "resets": self.reset_ports,
            "handshakes": [h.to_dict() for h in self.handshake_interfaces],
            "data_ports": [{"name": n, "width": w} for n, w in self.data_ports],
        }, indent=2)


# =====================================================================
# EquivalenceChecker — SAT/SMT-based formal equivalence checking
# =====================================================================

class EquivalenceChecker:
    """基于 SAT/SMT 的模块等价性检查器。

    提供两种检查策略：
    1. **组合等价性检查 (CEC)**：适用于纯组合模块或时序模块的组合逻辑部分。
       使用 Z3 证明在所有输入下输出相同。
    2. **有界时序等价性检查 (BMC)**：将时序电路展开 ``bound`` 个周期检查。
       （当前为占位，完整实现需提取 next-state 函数。）

    与 review2.md 要求一致：**不使用随机仿真**，而是形式化方法。
    """

    @classmethod
    def check(cls, module_a: Module, module_b: Module,
              method: str = "auto",
              outputs: Optional[Set[str]] = None,
              timeout_ms: Optional[int] = None,
              **kwargs) -> Dict[str, Any]:
        """检查两个模块的等价性。

        Args:
            module_a, module_b: 待比较的 DSL 模块。
            method:
                - ``"auto"``：无时序块 → CEC，有时序块 → 返回说明。
                - ``"combinational"``：强制组合等价性检查。
                - ``"bounded"``：有界时序检查（需额外参数 ``bound``）。
            outputs: 指定比较的信号名集合。默认取共有 output。
            timeout_ms: Z3 求解器超时（毫秒）。

        Returns:
            ::

                {
                    "equivalent": bool | None,
                    "method": str,
                    "outputs_checked": List[str],
                    "counterexample": Dict[str, int] | None,
                    "z3_time_ms": float,
                    "solver_stats": str,
                }
        """
        from rtlgen.smt import check_combinational_equivalence, check_bounded_equivalence

        has_seq = bool(module_a._seq_blocks) or bool(module_b._seq_blocks)

        if method == "auto":
            if has_seq:
                # For sequential modules, bounded checking is the right tool.
                # But if user just wants to compare comb logic, fall back to CEC.
                return check_bounded_equivalence(
                    module_a, module_b,
                    outputs=outputs, timeout_ms=timeout_ms, **kwargs
                )
            return check_combinational_equivalence(
                module_a, module_b, outputs=outputs, timeout_ms=timeout_ms
            )

        if method == "combinational":
            return check_combinational_equivalence(
                module_a, module_b, outputs=outputs, timeout_ms=timeout_ms
            )

        if method == "bounded":
            return check_bounded_equivalence(
                module_a, module_b,
                outputs=outputs, timeout_ms=timeout_ms, **kwargs
            )

        raise ValueError(f"Unknown equivalence check method: {method}")

    @classmethod
    def check_simulation(cls, model_a: Simulator, model_b: Simulator,
                         num_random_tests: int = 1000,
                         seed: Optional[int] = None) -> Dict[str, Any]:
        """基于随机仿真的等价性检查（备选/回归测试用，非形式化验证）。

        当模块包含复杂时序逻辑、Memory、或当前 SMT 转换器不支持的
        特性时，可作为辅助手段使用。
        """
        if seed is not None:
            random.seed(seed)

        inputs_a = list(model_a.module._inputs.keys())
        outputs_a = list(model_a.module._outputs.keys())
        outputs_b = list(model_b.module._outputs.keys())

        model_a.reset(cycles=2)
        model_b.reset(cycles=2)

        mismatches = 0
        failures: List[Dict[str, Any]] = []

        for _ in range(num_random_tests):
            inputs: Dict[str, int] = {}
            for name in inputs_a:
                width = model_a._width_of(name)
                inputs[name] = random.randint(0, (1 << width) - 1)

            for name, val in inputs.items():
                model_a.set(name, val)
                if name in model_b.module._inputs:
                    model_b.set(name, val)

            model_a.step(do_trace=False)
            model_b.step(do_trace=False)

            out_a = {name: model_a.get_int(name) for name in outputs_a}
            out_b = {name: model_b.get_int(name) for name in outputs_b}

            common = set(outputs_a) & set(outputs_b)
            match = all(out_a.get(k) == out_b.get(k) for k in common)
            if not match:
                mismatches += 1
                failures.append({"inputs": inputs.copy(), "out_a": out_a, "out_b": out_b})
                if len(failures) >= 10:
                    break

        return {
            "method": "simulation",
            "equivalent": mismatches == 0,
            "total_tests": num_random_tests,
            "mismatches": mismatches,
            "pass_rate": (num_random_tests - mismatches) / num_random_tests,
            "failures": failures,
        }


# =====================================================================
# SystemBuilder
# =====================================================================

class Connection:
    """模块间端口连接描述。"""

    def __init__(self, src_module: str, src_port: str,
                 dst_module: str, dst_port: str):
        self.src_module = src_module
        self.src_port = src_port
        self.dst_module = dst_module
        self.dst_port = dst_port


class SystemBuilder:
    """从多个 DSL 模块构建完整系统，自动生成顶层端口与连线。"""

    def __init__(self, name: str):
        self.name = name
        self.modules: List[Tuple[str, Module]] = []
        self.connections: List[Connection] = []

    def add_module(self, name: str, module: Module):
        self.modules.append((name, module))

    def connect(self, src_module: str, src_port: str,
                dst_module: str, dst_port: str):
        self.connections.append(Connection(src_module, src_port,
                                           dst_module, dst_port))

    def build(self) -> Module:
        """构建顶层模块，自动连接所有子模块。"""
        top = Module(self.name)

        for name, module in self.modules:
            setattr(top, name, module)

        for conn in self.connections:
            src_mod = getattr(top, conn.src_module)
            dst_mod = getattr(top, conn.dst_module)
            src_sig = getattr(src_mod, conn.src_port)
            dst_sig = getattr(dst_mod, conn.dst_port)

            wire_name = f"{conn.src_module}_{conn.src_port}_to_{conn.dst_module}_{conn.dst_port}"
            w = Signal(src_sig.width, wire_name)
            top._wires[wire_name] = w
            object.__setattr__(top, wire_name, w)

            @top.comb
            def _connect(src=src_sig, wire=w, dst=dst_sig):
                wire <<= src
                dst <<= wire

        return top

    def generate_system_model(self) -> BehavioralModel:
        """生成系统级行为模型（顶层 BehavioralModel）。"""
        top = self.build()
        return BehavioralModelGenerator.generate(top)
