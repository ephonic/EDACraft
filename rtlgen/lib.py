"""
rtlgen.lib — 标准组件库

提供 FSM、FIFO、Arbiter、Decoder / Encoder 等常用硬件模块。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from rtlgen.core import Input, Module, Output, Parameter, Reg, Signal, Wire
from rtlgen.logic import Const, Else, If, Switch


# ---------------------------------------------------------------------
# FSM
# ---------------------------------------------------------------------

class FSMStateContext:
    """FSM 状态描述上下文。

    在 @fsm.state 装饰的函数中使用，支持：
        ctx.red = 1          -> 设置当前状态下 red 输出的值
        ctx.goto("RUN", when=start) -> 条件状态转移
    """

    def __init__(self, fsm: "FSM"):
        self.fsm = fsm
        self._outputs: Dict[str, Any] = {}
        self._transitions: List[Tuple[Any, str]] = []

    def __setattr__(self, key: str, value: Any):
        if key in ("fsm", "_outputs", "_transitions"):
            object.__setattr__(self, key, value)
        else:
            self._outputs[key] = value

    def goto(self, next_state: str, when: Any = None):
        """注册一个状态转移。多个 goto 按声明顺序具有优先级（先声明优先级高）。"""
        self._transitions.append((when, next_state))


class FSM(Module):
    """模块化状态机生成器。

    示例:
        fsm = FSM("IDLE", name="traffic_fsm")
        fsm.add_output("red", width=1, default=0)
        fsm.add_output("green", width=1, default=0)

        @fsm.state("IDLE")
        def idle(ctx):
            ctx.red = 1
            ctx.green = 0
            ctx.goto("RUN", when=start)

        @fsm.state("RUN")
        def run(ctx):
            ctx.red = 0
            ctx.green = 1
            ctx.goto("IDLE", when=stop)

        fsm.build(clk, rst, parent=self)
    """

    def __init__(self, reset_state: str, name: str = "FSM"):
        self._given_name = name
        super().__init__(name or self.__class__.__name__)
        self.reset_state = reset_state
        self._state_funcs: Dict[str, Callable] = {}
        self._state_names: List[str] = []
        self._state_reg: Optional[Reg] = None
        self._next_state: Optional[Wire] = None
        self._fsm_outputs: Dict[str, int] = {}      # name -> width，避免与 Module._outputs 冲突
        self._output_defaults: Dict[str, Any] = {}
        self._state_outputs: Dict[str, Dict[str, Any]] = {}
        self._state_transitions: Dict[str, List[Tuple[Any, str]]] = {}

    def add_output(self, name: str, width: int = 1, default: Any = 0):
        """声明一个 FSM 输出信号及其默认值。"""
        self._fsm_outputs[name] = width
        self._output_defaults[name] = default
        return self

    def state(self, name: str):
        """装饰器：定义某个状态下的输出与转移行为。"""

        def decorator(func: Callable):
            self._state_funcs[name] = func
            if name not in self._state_names:
                self._state_names.append(name)
            return func

        return decorator

    def build(self, clk: Signal, reset: Optional[Signal] = None, parent: Optional[Module] = None):
        """生成状态寄存器、状态转移逻辑与输出逻辑。

        若传入 parent，则将所有信号与逻辑直接嵌入到 parent 模块中。
        """
        target = parent if parent is not None else self
        n = len(self._state_names)
        w = max(n.bit_length(), 1)
        prefix = f"{self._given_name}_" if (parent is not None and self._given_name) else ""

        self._state_reg = Reg(width=w, name=f"{prefix}state_reg")
        self._next_state = Wire(width=w, name=f"{prefix}next_state")
        target._regs[self._state_reg.name] = self._state_reg
        target._wires[self._next_state.name] = self._next_state
        setattr(target, self._state_reg.name, self._state_reg)
        setattr(target, self._next_state.name, self._next_state)

        # 创建输出信号
        for out_name, width in self._fsm_outputs.items():
            sig_name = f"{prefix}{out_name}"
            if not hasattr(target, sig_name):
                sig = Output(width, sig_name)
                setattr(target, sig_name, sig)          # 注册到 _outputs[sig_name]
            # 绑定便捷名称引用（不触发 Module.__setattr__ 重复注册）
            object.__setattr__(target, out_name, getattr(target, sig_name))

        # 收集各状态行为
        for name, func in self._state_funcs.items():
            ctx = FSMStateContext(self)
            func(ctx)
            self._state_outputs[name] = ctx._outputs
            self._state_transitions[name] = ctx._transitions

        # 生成 next_state 组合逻辑
        @target.comb
        def _next_logic():
            with Switch(self._state_reg) as sw:
                for state_name in self._state_names:
                    with sw.case(self._state_names.index(state_name)):
                        transitions = self._state_transitions.get(state_name, [])
                        current_idx = self._state_names.index(state_name)

                        def chain(idx: int):
                            if idx >= len(transitions):
                                self._next_state <<= Const(current_idx, width=w)
                                return
                            cond, next_s = transitions[idx]
                            next_idx = self._state_names.index(next_s)
                            if cond is not None:
                                with If(cond):
                                    self._next_state <<= Const(next_idx, width=w)
                                with Else():
                                    chain(idx + 1)
                            else:
                                self._next_state <<= Const(next_idx, width=w)

                        if transitions:
                            chain(0)
                        else:
                            self._next_state <<= Const(current_idx, width=w)

        # 生成输出组合逻辑
        @target.comb
        def _output_logic():
            with Switch(self._state_reg) as sw:
                for state_name in self._state_names:
                    with sw.case(self._state_names.index(state_name)):
                        outputs = self._state_outputs.get(state_name, {})
                        for out_name in self._fsm_outputs:
                            val = outputs.get(out_name, self._output_defaults.get(out_name, 0))
                            sig = getattr(target, out_name)
                            sig <<= val

        # 若嵌入到 parent，从 parent 的 _submodules 中移除自身，避免生成空壳实例
        if parent is not None:
            parent._submodules = [(n, m) for n, m in parent._submodules if m is not self]

        # 生成状态寄存器
        @target.seq(clk, reset)
        def _update():
            if reset is not None:
                with If(reset == 1):
                    self._state_reg <<= Const(self._state_names.index(self.reset_state), width=w)
                with Else():
                    self._state_reg <<= self._next_state
            else:
                self._state_reg <<= self._next_state


# ---------------------------------------------------------------------
# FIFO
# ---------------------------------------------------------------------

class SyncFIFO(Module):
    """同步 FIFO。"""

    def __init__(self, width: int, depth: int, name: str = "SyncFIFO"):
        super().__init__(name)
        self.width = width
        self.depth = depth
        addr_w = max(depth.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.din = Input(width, "din")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")

        self.dout = Output(width, "dout")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.count = Output(addr_w + 1, "count")

        self._wr_ptr = Reg(addr_w, "wr_ptr")
        self._rd_ptr = Reg(addr_w, "rd_ptr")
        self._count = Reg(addr_w + 1, "count_reg")

        @self.comb
        def _comb():
            self.full <<= self._count == depth
            self.empty <<= self._count == 0
            self.count <<= self._count

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self._wr_ptr <<= 0
                self._rd_ptr <<= 0
                self._count <<= 0
            with Else():
                wr_inc = Wire(1, "wr_inc")
                rd_inc = Wire(1, "rd_inc")
                wr_inc <<= self.wr_en & ~self.full
                rd_inc <<= self.rd_en & ~self.empty

                with If(wr_inc & ~rd_inc):
                    self._count <<= self._count + 1
                    self._wr_ptr <<= self._wr_ptr + 1
                with Else():
                    with If(~wr_inc & rd_inc):
                        self._count <<= self._count - 1
                        self._rd_ptr <<= self._rd_ptr + 1
                    with Else():
                        with If(wr_inc & rd_inc):
                            self._wr_ptr <<= self._wr_ptr + 1
                            self._rd_ptr <<= self._rd_ptr + 1

        # dout 为组合输出（连接 memory）；在真实实现中应实例化 ram
        # 这里仅做接口占位
        self._mem_depth = Parameter(depth, "DEPTH")


class AsyncFIFO(Module):
    """异步 FIFO（跨时钟域）。

    目前为接口占位，内部 CDC 逻辑（格雷码指针、双口 RAM）可在后续版本补充。
    """

    def __init__(self, width: int, depth: int, name: str = "AsyncFIFO"):
        super().__init__(name)
        addr_w = max(depth.bit_length(), 1)

        self.wr_clk = Input(1, "wr_clk")
        self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst")
        self.rd_rst = Input(1, "rd_rst")

        self.din = Input(width, "din")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")

        self.dout = Output(width, "dout")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")

        self._width = Parameter(width, "WIDTH")
        self._depth = Parameter(depth, "DEPTH")
        self._addr_w = Parameter(addr_w, "ADDR_W")


# ---------------------------------------------------------------------
# Arbiter
# ---------------------------------------------------------------------

class RoundRobinArbiter(Module):
    """轮询调度器。

    目前为接口与状态寄存器占位，核心仲裁逻辑（mask + priority）后续可补充。
    """

    def __init__(self, req_count: int, name: str = "RoundRobinArbiter"):
        super().__init__(name)
        ptr_w = max(req_count.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.reqs = Input(req_count, "reqs")
        self.grants = Output(req_count, "grants")
        self._pointer = Reg(ptr_w, "pointer")

        @self.comb
        def _arb():
            # 占位：简单的 one-hot  granting（仅作接口演示）
            g = Wire(req_count, "grant_vec")
            g <<= self.reqs  # 实际应实现轮询优先级
            self.grants <<= g


# ---------------------------------------------------------------------
# Decoder / Encoder
# ---------------------------------------------------------------------

class Decoder(Module):
    """n-to-2^n 译码器。"""

    def __init__(self, in_width: int, name: str = "Decoder"):
        super().__init__(name)
        out_width = 2 ** in_width
        self.input = Input(in_width, "in")
        self.output = Output(out_width, "out")
        self.en = Input(1, "en")

        @self.comb
        def _decode():
            with Switch(self.input) as sw:
                for i in range(out_width):
                    with sw.case(i):
                        self.output <<= Const(1 << i, width=out_width)
                with sw.default():
                    self.output <<= 0
            with If(~self.en):
                self.output <<= 0


class PriorityEncoder(Module):
    """优先编码器：将最低位的 '1' 编码为二进制索引。"""

    def __init__(self, in_width: int, name: str = "PriorityEncoder"):
        super().__init__(name)
        out_width = max(in_width.bit_length(), 1)
        self.input = Input(in_width, "in")
        self.output = Output(out_width, "out")
        self.valid = Output(1, "valid")

        @self.comb
        def _encode():
            out_wire = Wire(out_width, "out_wire")
            out_wire <<= 0
            for i in range(in_width):
                with If(self.input[i] == 1):
                    out_wire <<= i
            self.output <<= out_wire
            self.valid <<= self.input != 0


# ---------------------------------------------------------------------
# Barrel Shifter
# ---------------------------------------------------------------------

class BarrelShifter(Module):
    """桶形移位器：支持左移、右移、循环左移、循环右移。"""

    def __init__(self, width: int = 32, direction: str = "left", name: str = "BarrelShifter"):
        super().__init__(name)
        self.width = width
        self.direction = direction
        shift_w = max(width.bit_length(), 1)

        self.data_in = Input(width, "data_in")
        self.shift_amount = Input(shift_w, "shift_amount")
        self.data_out = Output(width, "data_out")

        @self.comb
        def _shift():
            result = Wire(width, "result")
            result <<= self.data_in
            for i in range(shift_w):
                with If(self.shift_amount[i] == 1):
                    shift_bits = 1 << i
                    if direction == "left":
                        result <<= result << shift_bits
                    elif direction == "right":
                        result <<= result >> shift_bits
                    elif direction == "left_rotate":
                        result <<= (result << shift_bits) | (result >> (width - shift_bits))
                    elif direction == "right_rotate":
                        result <<= (result >> shift_bits) | (result << (width - shift_bits))
            self.data_out <<= result


# ---------------------------------------------------------------------
# LFSR
# ---------------------------------------------------------------------

class LFSR(Module):
    """线性反馈移位寄存器（Galois LFSR）。

    参数:
        width: 寄存器位宽
        taps: 反馈抽头位置列表（例如 [32, 22, 2, 1] 对应 CRC-32）
        seed: 初始种子值
    """

    def __init__(self, width: int = 16, taps: Optional[List[int]] = None, seed: int = 1, name: str = "LFSR"):
        super().__init__(name)
        self.width = width
        self.taps = taps or [width, 1]
        self.seed = seed

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.enable = Input(1, "enable")
        self.out = Output(width, "out")

        self._state = Reg(width, "lfsr_reg")

        @self.comb
        def _out():
            self.out <<= self._state

        @self.seq(self.clk, self.rst)
        def _update():
            with If(self.rst == 1):
                self._state <<= Const(seed, width=width)
            with Else():
                with If(self.enable):
                    next_val = Wire(width, "next_val")
                    next_val <<= self._state
                    fb = Wire(1, "fb")
                    fb <<= self._state[0]
                    for b in range(width - 1):
                        if (width - b) in self.taps:
                            next_val[b] <<= self._state[b + 1] ^ fb
                        else:
                            next_val[b] <<= self._state[b + 1]
                    next_val[width - 1] <<= fb
                    self._state <<= next_val


# ---------------------------------------------------------------------
# CRC Generator
# ---------------------------------------------------------------------

class CRC(Module):
    """并行 CRC 组合逻辑生成器。

    基于多项式生成 next_crc = f(data, crc_in) 的组合逻辑。
    参数:
        data_width: 输入数据位宽
        poly_width: CRC 位宽
        polynomial: 生成多项式（例如 CRC32 = 0x04C11DB7）
    """

    def __init__(self, data_width: int = 8, poly_width: int = 32, polynomial: int = 0x04C11DB7, name: str = "CRC"):
        super().__init__(name)
        self.data_width = data_width
        self.poly_width = poly_width
        self.polynomial = polynomial

        self.data = Input(data_width, "data")
        self.crc_in = Input(poly_width, "crc_in")
        self.crc_out = Output(poly_width, "crc_out")

        @self.comb
        def _crc_logic():
            # 使用 Python 计算推导出的组合逻辑结构
            # 这里通过逐位运算构建 AST
            crc_val = list(self.crc_in[i] for i in range(poly_width))
            for i in range(data_width - 1, -1, -1):
                bit = self.data[i] ^ crc_val[poly_width - 1]
                new_crc = []
                for j in range(poly_width - 1, -1, -1):
                    if j == poly_width - 1:
                        new_crc.insert(0, bit)
                    else:
                        if (polynomial >> (j + 1)) & 1:
                            new_crc.insert(0, crc_val[j] ^ bit)
                        else:
                            new_crc.insert(0, crc_val[j])
                crc_val = new_crc

            # 拼接为输出
            result = Wire(poly_width, "crc_result")
            for i in range(poly_width):
                result[i] <<= crc_val[i]
            self.crc_out <<= result


# ---------------------------------------------------------------------
# Divider
# ---------------------------------------------------------------------

class Divider(Module):
    """无符号恢复余数除法器（多周期状态机实现）。

    参数:
        dividend_width: 被除数位宽
        divisor_width: 除数位宽
    """

    def __init__(self, dividend_width: int = 32, divisor_width: int = 32, name: str = "Divider"):
        super().__init__(name)
        self.dividend_width = dividend_width
        self.divisor_width = divisor_width
        count_w = max(dividend_width.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.dividend = Input(dividend_width, "dividend")
        self.divisor = Input(divisor_width, "divisor")
        self.quotient = Output(dividend_width, "quotient")
        self.remainder = Output(divisor_width, "remainder")
        self.done = Output(1, "done")
        self.busy = Output(1, "busy")

        self._remainder = Reg(divisor_width, "rem_reg")
        self._quotient = Reg(dividend_width, "quo_reg")
        self._count = Reg(count_w, "count_reg")
        self._state = Reg(2, "state_reg")  # 0=IDLE, 1=RUN, 2=DONE

        @self.comb
        def _out():
            self.quotient <<= self._quotient
            self.remainder <<= self._remainder
            self.done <<= self._state == 2
            self.busy <<= self._state == 1

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self._state <<= 0
                self._count <<= 0
                self._quotient <<= 0
                self._remainder <<= 0
            with Else():
                with If(self._state == 0):
                    with If(self.start):
                        self._state <<= 1
                        self._count <<= dividend_width
                        self._quotient <<= self.dividend
                        self._remainder <<= 0
                with Else():
                    with If(self._state == 1):
                        # 恢复余数算法单周期步进
                        shifted_rem = Wire(divisor_width + 1, "shifted_rem")
                        shifted_rem <<= (self._remainder << 1) | self._quotient[dividend_width - 1]

                        with If(shifted_rem >= self.divisor):
                            self._remainder <<= shifted_rem - self.divisor
                            self._quotient <<= (self._quotient << 1) | Const(1, width=1)
                        with Else():
                            self._remainder <<= shifted_rem
                            self._quotient <<= (self._quotient << 1) | Const(0, width=1)

                        self._count <<= self._count - 1
                        with If(self._count == 1):
                            self._state <<= 2
                    with Else():
                        with If(self._state == 2):
                            with If(self.start):
                                self._state <<= 1
                                self._count <<= dividend_width
                                self._quotient <<= self.dividend
                                self._remainder <<= 0
