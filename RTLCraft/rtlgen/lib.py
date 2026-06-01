"""
rtlgen.lib — 标准组件库

提供 FSM、FIFO、Arbiter、Decoder / Encoder 等常用硬件模块。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from rtlgen.core import Input, Memory, Module, Output, Parameter, Reg, Signal, Wire
from rtlgen.logic import Cat, Const, Else, Elif, If, Switch


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
        self.rd_rdy = Output(1, "rd_rdy")

        self._wr_ptr = Reg(addr_w, "wr_ptr")
        self._rd_ptr = Reg(addr_w, "rd_ptr")
        self._count = Reg(addr_w + 1, "count_reg")

        @self.comb
        def _comb():
            self.full <<= self._count == depth
            self.empty <<= self._count == 0
            self.count <<= self._count
            self.rd_rdy <<= ~self.empty

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
    """轮询调度器 (Round-Robin Arbiter)。

    每次从 reqs 中选择一个请求进行授权，授权后指针指向下一个请求，
    保证公平性。grants 为 one-hot 输出。
    """

    def __init__(self, req_count: int = 8, name: str = "RoundRobinArbiter"):
        super().__init__(name)
        ptr_w = max((req_count - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.reqs = Input(req_count, "reqs")
        self.grants = Output(req_count, "grants")

        self.pointer = Reg(ptr_w, "pointer")

        # 组合逻辑中间信号（注册到模块以便 seq 引用及 Verilog 声明生成）
        self._double_reqs = Wire(req_count * 2, "double_reqs")
        self._shifted = Wire(req_count * 2, "shifted")
        self._masked = Wire(req_count, "masked")
        self._grant_vec = Wire(req_count, "grant_vec")
        self._grant_idx = Wire(ptr_w, "grant_idx")
        self._pe_masked = Wire(ptr_w, "pe_masked")
        self._pe_unmasked = Wire(ptr_w, "pe_unmasked")
        self._pe_masked_valid = Wire(1, "pe_masked_valid")

        @self.comb
        def _arb():
            # 将 reqs 拼接两次并右移 pointer 位，构造轮询窗口
            self._double_reqs <<= Cat(self.reqs, self.reqs)
            self._shifted <<= self._double_reqs >> self.pointer
            self._masked <<= self._shifted[req_count - 1:0]

            # masked 优先编码（最低位1）
            self._pe_masked <<= 0
            for i in range(req_count - 1, -1, -1):
                with If(self._masked[i] == 1):
                    self._pe_masked <<= i

            self._pe_masked_valid <<= self._masked != 0

            # unmasked 优先编码（最低位1）
            self._pe_unmasked <<= 0
            for i in range(req_count - 1, -1, -1):
                with If(self.reqs[i] == 1):
                    self._pe_unmasked <<= i

            # 选择 grant 索引
            with If(self._pe_masked_valid == 1):
                self._grant_idx <<= (self._pe_masked + self.pointer) & (req_count - 1)
            with Else():
                self._grant_idx <<= self._pe_unmasked

            # 生成 one-hot grant
            self._grant_vec <<= 0
            for i in range(req_count):
                with If(self._grant_idx == i):
                    self._grant_vec <<= 1 << i

            with If(self.reqs == 0):
                self._grant_vec <<= 0

            self.grants <<= self._grant_vec

        @self.seq(self.clk, self.rst)
        def _update():
            with If(self.rst == 1):
                self.pointer <<= 0
            with Else():
                with If(self.reqs != 0):
                    self.pointer <<= (self._grant_idx + 1) & (req_count - 1)


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


# =====================================================================
# PipelineShift — Multi-cycle pipeline with valid/ready handshake
# =====================================================================

class PipelineShift(Module):
    """Configurable-depth pipeline shift register with valid/ready handshake.
    Useful for inserting latency in any datapath.

    Ports:
        clk, rst, in_valid, out_ready, in_ready, out_valid
        data_in[N-1:0], data_out[N-1:0]

    Latency = depth cycles from in_valid&in_ready to out_valid.
    """

    def __init__(self, width: int = 32, depth: int = 3, name: str = "PipelineShift"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.data_in = Input(width, "data_in")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.data_out = Output(width, "data_out")
        self.out_valid = Output(1, "out_valid"); self.in_ready = Output(1, "in_ready")

        self._pv = [Reg(1, f"pv_{i}") for i in range(depth)]
        self._pd = [Reg(width, f"pd_{i}") for i in range(depth)]

        with self.comb:
            self.in_ready <<= (self._pv[depth - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(depth): self._pv[i] <<= 0; self._pd[i] <<= 0
            with Else():
                # Last stage consumed
                with If(self._pv[depth - 1] & self.out_ready):
                    self._pv[depth - 1] <<= 0
                # Shift stages (reverse order for non-blocking correctness)
                for s in range(depth - 2, -1, -1):
                    nxt_free = (self._pv[s + 1] == 0)
                    with If(self._pv[s] & (nxt_free | self.out_ready)):
                        self._pd[s + 1] <<= self._pd[s]
                        self._pv[s + 1] <<= 1
                        self._pv[s] <<= 0
                # Stage 0: new input
                with If(self.in_valid & self.in_ready):
                    self._pd[0] <<= self.data_in
                    self._pv[0] <<= 1

        with self.comb:
            self.data_out <<= self._pd[depth - 1]
            self.out_valid <<= self._pv[depth - 1]


# =====================================================================
# Counter — Loadable counter with en/load/rst/max
# =====================================================================

class Counter(Module):
    """Configurable-width up-counter with enable, load, max.

    Ports:
        clk, rst, en, load, load_val[N-1:0], count[N-1:0], zero, max_reached
    """

    def __init__(self, width: int = 32, max_val: Optional[int] = None, name: str = "Counter"):
        super().__init__(name)
        max_val = max_val or (1 << width) - 1
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.en = Input(1, "en"); self.load = Input(1, "load")
        self.load_val = Input(width, "load_val")
        self.count = Output(width, "count")
        self.zero = Output(1, "zero")
        self.max_reached = Output(1, "max_reached")

        self._cnt = Reg(width, "cnt")

        with self.comb:
            self.count <<= self._cnt
            self.zero <<= (self._cnt == 0)
            self.max_reached <<= (self._cnt >= max_val)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._cnt <<= 0
            with Else():
                with If(self.load == 1):
                    self._cnt <<= self.load_val
                with Elif(self.en == 1):
                    with If(self._cnt >= max_val):
                        self._cnt <<= 0
                    with Else():
                        self._cnt <<= self._cnt + 1


# =====================================================================
# MultiCycleFSM — IDLE → REQ → WAIT → DONE
# =====================================================================

class MultiCycleFSM(Module):
    """Generic multi-cycle FSM: IDLE=0, REQ=1, WAIT=2, DONE=3.

    Ports:
        clk, rst, start, busy, done
        wait_cycles[N-1:0] — number of WAIT cycles before DONE
    """

    def __init__(self, wait_width: int = 16, name: str = "MultiCycleFSM"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.wait_cycles = Input(wait_width, "wait_cycles")
        self.busy = Output(1, "busy"); self.done = Output(1, "done")

        self._state = Reg(2, "state")
        self._timer = Reg(wait_width, "timer")

        with self.comb:
            self.busy <<= (self._state != 0)
            self.done <<= (self._state == 3)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._state <<= 0; self._timer <<= 0
            with Else():
                with Switch(self._state) as sw:
                    with sw.case(0):  # IDLE
                        with If(self.start):
                            self._state <<= 1
                    with sw.case(1):  # REQ
                        self._state <<= 2
                        self._timer <<= self.wait_cycles
                    with sw.case(2):  # WAIT
                        with If(self._timer > 0):
                            self._timer <<= self._timer - 1
                        with Else():
                            self._state <<= 3
                    with sw.case(3):  # DONE
                        self._state <<= 0


# =====================================================================
# RegisterFile — Multi-port register file with write-enable
# =====================================================================

class RegisterFile(Module):
    """Multi-port register file with separate read/write addresses.

    Ports per read port: rd_addr, rd_data
    Ports per write port: wr_addr, wr_data, wr_en
    """

    def __init__(self, width: int = 32, depth: int = 32,
                 n_read: int = 2, n_write: int = 1,
                 name: str = "RegisterFile"):
        super().__init__(name)
        aw = max((depth - 1).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        self.rd_addr = [Input(aw, f"rd_addr_{i}") for i in range(n_read)]
        self.rd_data = [Output(width, f"rd_data_{i}") for i in range(n_read)]
        self.wr_addr = [Input(aw, f"wr_addr_{i}") for i in range(n_write)]
        self.wr_data = [Input(width, f"wr_data_{i}") for i in range(n_write)]
        self.wr_en = [Input(1, f"wr_en_{i}") for i in range(n_write)]

        self._rf = [Reg(width, f"rf_{i}") for i in range(depth)]

        with self.comb:
            for r in range(n_read):
                self.rd_data[r] <<= 0
                for i in range(depth):
                    with If(self.rd_addr[r] == i):
                        self.rd_data[r] <<= self._rf[i]

        with self.seq(self.clk, self.rst):
            for w in range(n_write):
                with If(self.wr_en[w]):
                    for i in range(depth):
                        with If(self.wr_addr[w] == i):
                            self._rf[i] <<= self.wr_data[w]


# =====================================================================
# DualPortRAM — Dual-port RAM with independent read/write ports
# =====================================================================

class DualPortRAM(Module):
    """Dual-port RAM with independent port A (read/write) and port B (read-only)."""

    def __init__(self, width: int = 32, depth: int = 1024, name: str = "DualPortRAM"):
        super().__init__(name)
        aw = max((depth - 1).bit_length(), 1)
        self.clk = Input(1, "clk")
        self.a_addr = Input(aw, "a_addr"); self.a_wen = Input(1, "a_wen")
        self.a_wdata = Input(width, "a_wdata"); self.a_rdata = Output(width, "a_rdata")
        self.b_addr = Input(aw, "b_addr"); self.b_rdata = Output(width, "b_rdata")

        self._mem = Memory(width, depth, "mem")

        with self.seq(self.clk, None):
            with If(self.a_wen):
                self._mem[self.a_addr] <<= self.a_wdata

        with self.comb:
            self.a_rdata <<= self._mem[self.a_addr]
            self.b_rdata <<= self._mem[self.b_addr]


# =====================================================================
# CAM — Content-Addressable Memory (fully-associative)
# =====================================================================

class CAM(Module):
    """Fully-associative CAM. Write: match_data + wen. Lookup: lookup_data → hit + index.

    Ports:
        clk, rst
        lookup_data[N-1:0], hit, hit_index[log2(depth)-1:0]
        write_data[N-1:0], write_en, write_index[log2(depth)-1:0]
    """

    def __init__(self, width: int = 32, depth: int = 8, name: str = "CAM"):
        super().__init__(name)
        iw = max((depth - 1).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.lookup_data = Input(width, "lookup_data")
        self.hit = Output(1, "hit"); self.hit_index = Output(iw, "hit_index")
        self.write_data = Input(width, "write_data")
        self.write_en = Input(1, "write_en")
        self.write_index = Input(iw, "write_index")

        self._cam_tags = [Reg(width, f"ctag_{i}") for i in range(depth)]
        self._cam_vld = [Reg(1, f"cvld_{i}") for i in range(depth)]

        with self.comb:
            self.hit <<= 0; self.hit_index <<= 0
            for i in range(depth):
                with If(self._cam_vld[i] & (self._cam_tags[i] == self.lookup_data)):
                    self.hit <<= 1; self.hit_index <<= i

        with self.seq(self.clk, self.rst):
            with If(self.write_en):
                for i in range(depth):
                    with If(self.write_index == i):
                        self._cam_tags[i] <<= self.write_data
                        self._cam_vld[i] <<= 1


# =====================================================================
# LUT — Lookup Table ROM (combinational read)
# =====================================================================

class LUT(Module):
    """Combinational lookup table ROM. Initialized with init_data list.

    Ports:
        addr[log2(len(init_data))-1:0], dout[width-1:0]
    """

    def __init__(self, width: int = 32, init_data: Optional[List[int]] = None,
                 depth: Optional[int] = None, name: str = "LUT"):
        super().__init__(name)
        if init_data is not None:
            depth = len(init_data)
        elif depth is None:
            depth = 256
        if init_data is None:
            init_data = [0] * depth
        aw = max((depth - 1).bit_length(), 1)
        self.addr = Input(aw, "addr")
        self.dout = Output(width, "dout")
        self._mem = Memory(width, depth, "lut", init_data=init_data)

        with self.comb:
            self.dout <<= self._mem[self.addr]


# =====================================================================
# MAC — Multiply-Accumulate (signed, pipelined)
# =====================================================================

class MAC(Module):
    """Signed multiply-accumulate: acc = acc + a * b. Pipelined.

    Ports:
        clk, rst, a[N-1:0], b[N-1:0], load_acc, acc_out[2N-1:0]
    """

    def __init__(self, width: int = 16, name: str = "MAC"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.a = Input(width, "a", signed=True)
        self.b = Input(width, "b", signed=True)
        self.load_acc = Input(1, "load_acc")
        self.acc_out = Output(width * 2, "acc_out")
        self.valid = Output(1, "valid")

        self._pipe_a = Reg(width, "pipe_a", signed=True)
        self._pipe_b = Reg(width, "pipe_b", signed=True)
        self._prod = Reg(width * 2, "prod")
        self._acc = Reg(width * 2, "acc")

        with self.comb:
            self.acc_out <<= self._acc
            self.valid <<= 1

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._pipe_a <<= 0; self._pipe_b <<= 0
                self._prod <<= 0; self._acc <<= 0
            with Else():
                self._pipe_a <<= self.a
                self._pipe_b <<= self.b
                self._prod <<= self._pipe_a * self._pipe_b
                with If(self.load_acc):
                    self._acc <<= 0
                with Else():
                    self._acc <<= self._acc + self._prod


# =====================================================================
# SignedMultiplier — Pipelined signed multiplier (configurable stages)
# =====================================================================

class SignedMultiplier(Module):
    """Configurable-latency signed multiplier with valid/ready handshake."""

    def __init__(self, width: int = 16, latency: int = 4, name: str = "SignedMultiplier"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.a = Input(width, "a", signed=True)
        self.b = Input(width, "b", signed=True)
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.product = Output(width * 2, "product"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")

        self._pv = [Reg(1, f"mpv_{i}") for i in range(latency)]
        self._pd = [Reg(width * 2, f"mpd_{i}") for i in range(latency)]

        with self.comb:
            self.in_ready <<= (self._pv[latency - 1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(latency): self._pv[i] <<= 0; self._pd[i] <<= 0
            with Else():
                with If(self._pv[latency - 1] & self.out_ready):
                    self._pv[latency - 1] <<= 0
                for s in range(latency - 2, -1, -1):
                    nxt_free = (self._pv[s + 1] == 0)
                    with If(self._pv[s] & (nxt_free | self.out_ready)):
                        self._pd[s + 1] <<= self._pd[s]
                        self._pv[s + 1] <<= 1; self._pv[s] <<= 0
                with If(self.in_valid & self.in_ready):
                    self._pd[0] <<= self.a * self.b
                    self._pv[0] <<= 1

        with self.comb:
            self.product <<= self._pd[latency - 1]
            self.out_valid <<= self._pv[latency - 1]


# =====================================================================
# DirectMappedCache — Direct-mapped cache with valid/tag/data
# =====================================================================

class DirectMappedCache(Module):
    """Direct-mapped cache with line_size bytes per line.

    Ports:
        clk, rst, addr, req_valid, wen, wdata[line_size*8-1:0]
        fill_valid, fill_data[line_size*8-1:0], fill_index
        hit, rdata[line_size*8-1:0], miss
    """

    def __init__(self, size: int = 4096, line_size: int = 64,
                 data_width: int = 512, name: str = "DirectMappedCache"):
        super().__init__(name)
        n_lines = size // line_size
        aw = max((n_lines - 1).bit_length(), 1)
        tag_w = max(32 - (aw + (line_size.bit_length() - 1)), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.addr = Input(32, "addr"); self.req_valid = Input(1, "req_valid")
        self.wen = Input(1, "wen"); self.wdata = Input(data_width, "wdata")
        self.fill_valid = Input(1, "fill_valid")
        self.fill_data = Input(data_width, "fill_data")
        self.fill_addr = Input(32, "fill_addr")
        self.hit = Output(1, "hit"); self.rdata = Output(data_width, "rdata")
        self.miss = Output(1, "miss")

        self._tag = Memory(tag_w, n_lines, "tag")
        self._data = Memory(data_width, n_lines, "data")
        self._valid = Reg(n_lines, "valid_bits")

        idx = Wire(aw, "cache_idx"); tag = Wire(tag_w, "cache_tag")
        line_bits = line_size.bit_length() - 1
        with self.comb:
            idx <<= (self.addr >> line_bits) % n_lines
            tag <<= self.addr >> (line_bits + aw)

        vld = Wire(1, "vld_bit")
        with self.comb:
            vld <<= (self._valid >> idx) & 1

        with self.comb:
            self.hit <<= vld & (self._tag[idx] == tag)
            self.rdata <<= self._data[idx]
            self.miss <<= self.req_valid & ~(vld & (self._tag[idx] == tag))

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._valid <<= 0
            with Else():
                with If(self.fill_valid):
                    fi = Wire(aw, "fi")
                    fi <<= (self.fill_addr >> line_bits) % n_lines
                    self._data[fi] <<= self.fill_data
                    self._valid <<= self._valid | (1 << fi)
                    ft = Wire(tag_w, "ft")
                    ft <<= self.fill_addr >> (line_bits + aw)
                    self._tag[fi] <<= ft
                with If(self.wen & self.hit):
                    self._data[idx] <<= self.wdata


# =====================================================================
# SetAssocCache — N-way set-associative cache with LRU replacement
# =====================================================================

class SetAssocCache(Module):
    """N-way set-associative cache with LRU replacement.

    Ports:
        clk, rst, addr, req_valid, wen, wdata
        fill_valid, fill_data, fill_addr
        hit, rdata, miss, evict_addr, evict_valid
    """

    def __init__(self, n_ways: int = 4, size: int = 32768, line_size: int = 64,
                 data_width: int = 512, name: str = "SetAssocCache"):
        super().__init__(name)
        n_sets = size // (n_ways * line_size)
        sw = max((n_sets - 1).bit_length(), 1)
        line_bits = line_size.bit_length() - 1
        tag_w = max(32 - (sw + line_bits), 1)

        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.addr = Input(32, "addr"); self.req_valid = Input(1, "req_valid")
        self.wen = Input(1, "wen"); self.wdata = Input(data_width, "wdata")
        self.fill_valid = Input(1, "fill_valid")
        self.fill_data = Input(data_width, "fill_data")
        self.fill_addr = Input(32, "fill_addr")
        self.hit = Output(1, "hit"); self.hit_way = Output(3, "hit_way")
        self.rdata = Output(data_width, "rdata")
        self.miss = Output(1, "miss"); self.miss_addr = Output(32, "miss_addr")
        self.evict_way = Output(3, "evict_way")

        set_idx = Wire(sw, "l2_set"); tag = Wire(tag_w, "l2_tag")
        with self.comb:
            set_idx <<= (self.addr >> line_bits) % n_sets
            tag <<= self.addr >> (sw + line_bits)

        tags = [Memory(tag_w, n_sets, f"tag_{w}") for w in range(n_ways)]
        datas = [Memory(data_width, n_sets, f"data_{w}") for w in range(n_ways)]
        self._sac_vld = [Reg(n_sets, f"svld_{w}") for w in range(n_ways)]
        self._sac_lru = [Reg(3, f"slru_{w}") for w in range(n_ways)]

        with self.comb:
            self.hit <<= 0; self.hit_way <<= 0; self.rdata <<= 0
            for w in range(n_ways):
                v = Wire(1, f"v_{w}")
                v <<= (self._sac_vld[w] >> set_idx) & 1
                with If(v & (tags[w][set_idx] == tag)):
                    self.hit <<= 1; self.hit_way <<= w
                    self.rdata <<= datas[w][set_idx]
            self.miss <<= self.req_valid & ~self.hit
            self.miss_addr <<= self.addr
            self.evict_way <<= 0

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for w in range(n_ways): self._sac_vld[w] <<= 0; self._sac_lru[w] <<= w
            with Else():
                with If(self.fill_valid):
                    f_idx = Wire(sw, "fi")
                    f_idx <<= (self.fill_addr >> line_bits) % n_sets
                    f_tag = Wire(tag_w, "ft")
                    f_tag <<= self.fill_addr >> (sw + line_bits)
                    for w in range(n_ways):
                        with If(self.evict_way == w):
                            datas[w][f_idx] <<= self.fill_data
                            tags[w][f_idx] <<= f_tag
                            self._sac_vld[w] <<= self._sac_vld[w] | (1 << f_idx)


# =====================================================================
# SyncCell — 2-flop CDC synchronizer
# =====================================================================

class SyncCell(Module):
    """2-flop synchronizer for crossing clock domains.
    Ports: clk_dst, rst_dst, data_in, data_out
    """
    def __init__(self, width: int = 1, name: str = "SyncCell"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.data_in = Input(width, "data_in")
        self.data_out = Output(width, "data_out")
        self._ff1 = Reg(width, "sync_ff1"); self._ff2 = Reg(width, "sync_ff2")
        with self.comb:
            self.data_out <<= self._ff2
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._ff1 <<= 0; self._ff2 <<= 0
            with Else():
                self._ff1 <<= self.data_in; self._ff2 <<= self._ff1


# =====================================================================
# PulseSynchronizer — CDC pulse synchronizer
# =====================================================================

class PulseSynchronizer(Module):
    """Pulse-based CDC: toggle → sync → edge detect.
    Ports: clk_src, clk_dst, rst, pulse_in, pulse_out
    """
    def __init__(self, name: str = "PulseSync"):
        super().__init__(name)
        self.clk_src = Input(1, "clk_src"); self.clk_dst = Input(1, "clk_dst")
        self.rst = Input(1, "rst")
        self.pulse_in = Input(1, "pulse_in"); self.pulse_out = Output(1, "pulse_out")
        self._toggle_src = Reg(1, "toggle_src")
        self._sync = [Reg(1, f"sync_{i}") for i in range(3)]
        with self.seq(self.clk_src, self.rst):
            with If(self.rst == 1): self._toggle_src <<= 0
            with Elif(self.pulse_in == 1): self._toggle_src <<= ~self._toggle_src
        with self.seq(self.clk_dst, self.rst):
            with If(self.rst == 1):
                for i in range(3): self._sync[i] <<= 0
            with Else():
                self._sync[0] <<= self._toggle_src
                self._sync[1] <<= self._sync[0]
                self._sync[2] <<= self._sync[1]
        with self.comb:
            self.pulse_out <<= self._sync[1] ^ self._sync[2]


# =====================================================================
# EdgeDetector — Rising/falling edge detector
# =====================================================================

class EdgeDetector(Module):
    """Detect rising/falling edges of a signal."""
    def __init__(self, name: str = "EdgeDetect"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.sig = Input(1, "sig")
        self.rising = Output(1, "rising"); self.falling = Output(1, "falling")
        self._delay = Reg(1, "sig_d")
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1): self._delay <<= 0
            with Else(): self._delay <<= self.sig
        with self.comb:
            self.rising <<= self.sig & ~self._delay
            self.falling <<= ~self.sig & self._delay


# =====================================================================
# ClockGate — Clock gating cell
# =====================================================================

class ClockGate(Module):
    """Clock gating: clk_out = clk_en ? clk_in : 0 (latch-based)."""
    def __init__(self, name: str = "ClockGate"):
        super().__init__(name)
        self.clk_in = Input(1, "clk_in"); self.clk_en = Input(1, "clk_en")
        self.clk_out = Output(1, "clk_out")
        self._latch = Reg(1, "cg_latch")
        with self.seq(~self.clk_in, None):
            with If(self.clk_en == 1): self._latch <<= 1
            with Else(): self._latch <<= 0
        with self.comb:
            self.clk_out <<= self.clk_in & self._latch


# =====================================================================
# AsyncResetRel — Async reset synchronizer (reset release CDC)
# =====================================================================

class AsyncResetRel(Module):
    """Asynchronous reset synchronizer for reset deassertion CDC."""
    def __init__(self, name: str = "AsyncResetRel"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst_async = Input(1, "rst_async")
        self.rst_sync = Output(1, "rst_sync")
        self._ff1 = Reg(1, "ar_ff1"); self._ff2 = Reg(1, "ar_ff2")
        with self.seq(self.clk, self.rst_async, reset_async=True):
            self._ff1 <<= 1; self._ff2 <<= self._ff1
        with self.comb:
            self.rst_sync <<= ~self._ff2


# =====================================================================
# OneHotMux — One-hot encoded multiplexer
# =====================================================================

class OneHotMux(Module):
    """One-hot multiplexer: select[bit] = 1 picks data[i]."""
    def __init__(self, width: int = 32, n_inputs: int = 4, name: str = "OneHotMux"):
        super().__init__(name)
        self.sel = Input(n_inputs, "sel")
        self.data = [Input(width, f"data_{i}") for i in range(n_inputs)]
        self.dout = Output(width, "dout")
        with self.comb:
            result = 0
            for i in range(n_inputs):
                with If(self.sel[i] == 1):
                    result |= self.data[i]
            self.dout <<= result


# =====================================================================
# PipelineInterlock — Stall/hold logic for pipeline control
# =====================================================================

class PipelineInterlock(Module):
    """Pipeline interlock: stall_next when hold condition is met.
    Ports: hold, stall, valid_in, valid_out, ready_in, ready_out
    """
    def __init__(self, name: str = "PipelineInterlock"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.hold = Input(1, "hold")
        self.valid_in = Input(1, "valid_in"); self.ready_out = Output(1, "ready_out")
        self.valid_out = Output(1, "valid_out"); self.ready_in = Input(1, "ready_in")
        self._pipe_v = Reg(1, "pl_v"); self._stall = Reg(1, "pl_stall")
        with self.comb:
            self.ready_out <<= ~self._stall
            self.valid_out <<= self._pipe_v
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._pipe_v <<= 0; self._stall <<= 0
            with Else():
                self._stall <<= self.hold
                with If(self._stall == 0):
                    self._pipe_v <<= self.valid_in


# =====================================================================
# BypassNetwork — Forwarding network for execution units
# =====================================================================

class BypassNetwork(Module):
    """Forwarding network: forward result from EX stage to DS stage inputs.
    Compares rd_addr of producing unit with rs_addr of consuming unit.
    """
    def __init__(self, n_ports: int = 4, width: int = 32, name: str = "BypassNetwork"):
        super().__init__(name)
        self.rd_addr = [Input(8, f"rd_addr_{i}") for i in range(n_ports)]
        self.rd_data = [Input(width, f"rd_data_{i}") for i in range(n_ports)]
        self.rd_valid = [Input(1, f"rd_valid_{i}") for i in range(n_ports)]
        self.rs_addr = Input(8, "rs_addr")
        self.fwd_data = Output(width, "fwd_data"); self.fwd_valid = Output(1, "fwd_valid")
        with self.comb:
            self.fwd_data <<= 0; self.fwd_valid <<= 0
            for i in range(n_ports):
                with If(self.rd_valid[i] & (self.rd_addr[i] == self.rs_addr)):
                    self.fwd_data <<= self.rd_data[i]; self.fwd_valid <<= 1


# =====================================================================
# GrayCounter — Gray code counter (for CDC pointers)
# =====================================================================

class GrayCounter(Module):
    """Gray code counter: count in Gray, bin2gray conversion."""
    def __init__(self, width: int = 8, name: str = "GrayCounter"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.gray = Output(width, "gray"); self.binary = Output(width, "binary")
        self._bin = Reg(width, "gb_bin")
        with self.comb:
            self.gray <<= self._bin ^ (self._bin >> 1)
            self.binary <<= self._bin
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1): self._bin <<= 0
            with Elif(self.en == 1): self._bin <<= self._bin + 1


# =====================================================================
# FIFO with Gray-code CDC pointers (async FIFO)
# =====================================================================

class AsyncFIFO(Module):
    """Async FIFO with Gray-code pointers for CDC.
    Ports: wr_clk, rd_clk, wr_rst, rd_rst, din, wr_en, rd_en, dout, full, empty
    """
    def __init__(self, width: int = 32, depth: int = 8, name: str = "AsyncFIFO"):
        super().__init__(name)
        aw = max((depth - 1).bit_length(), 1)
        self.wr_clk = Input(1, "wr_clk"); self.rd_clk = Input(1, "rd_clk")
        self.wr_rst = Input(1, "wr_rst"); self.rd_rst = Input(1, "rd_rst")
        self.din = Input(width, "din"); self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")
        self.dout = Output(width, "dout"); self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self._mem = Memory(width, depth, "af_mem")
        self._wr_ptr = Reg(aw + 1, "wr_ptr"); self._rd_ptr = Reg(aw + 1, "rd_ptr")
        self._wr_gray = Reg(aw + 1, "wr_gray"); self._rd_gray = Reg(aw + 1, "rd_gray")
        self._wr_sync = [Reg(aw + 1, f"wrs_{i}") for i in range(2)]
        self._rd_sync = [Reg(aw + 1, f"rds_{i}") for i in range(2)]

        ptr_w = aw
        wr_next = Wire(aw + 1, "wr_nxt")
        with self.comb:
            wr_next <<= self._wr_ptr + 1
            self.full <<= ((wr_next[ptr_w:0] == self._wr_sync[1][ptr_w:0]) &
                          (wr_next[aw] != self._wr_sync[1][aw]))

        rd_next = Wire(aw + 1, "rd_nxt")
        with self.comb:
            rd_next <<= self._rd_ptr + 1
            self.empty <<= (rd_next == self._rd_sync[1])

        with self.seq(self.wr_clk, self.wr_rst):
            with If(self.wr_rst == 1):
                self._wr_ptr <<= 0; self._wr_gray <<= 0
            with Else():
                with If(self.wr_en & (self.full == 0)):
                    self._mem[self._wr_ptr[ptr_w - 1:0]] <<= self.din
                    self._wr_ptr <<= wr_next
                    self._wr_gray <<= wr_next ^ (wr_next >> 1)

        with self.seq(self.rd_clk, self.rd_rst):
            with If(self.rd_rst == 1):
                self._rd_ptr <<= 0; self._rd_gray <<= 0
            with Else():
                with If(self.rd_en & (self.empty == 0)):
                    self._rd_ptr <<= rd_next
                    self._rd_gray <<= rd_next ^ (rd_next >> 1)

        with self.seq(self.rd_clk, self.rd_rst):
            with If(self.rd_rst == 1):
                for i in range(2): self._wr_sync[i] <<= 0
            with Else():
                self._wr_sync[0] <<= self._wr_gray
                self._wr_sync[1] <<= self._wr_sync[0]

        with self.seq(self.wr_clk, self.wr_rst):
            with If(self.wr_rst == 1):
                for i in range(2): self._rd_sync[i] <<= 0
            with Else():
                self._rd_sync[0] <<= self._rd_gray
                self._rd_sync[1] <<= self._rd_sync[0]

        with self.comb:
            self.dout <<= self._mem[self._rd_ptr[ptr_w - 1:0]]


# =====================================================================
# MultiCyclePath — Multi-cycle timing path constraint marker
# =====================================================================

class MultiCyclePath(Module):
    """Multi-cycle timing path: holds data for N cycles before sampling.
    Use for paths that need >1 cycle to propagate.
    """
    def __init__(self, width: int = 32, n_cycles: int = 2, name: str = "MultiCyclePath"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.data_in = Input(width, "data_in"); self.en = Input(1, "en")
        self.data_out = Output(width, "data_out")
        self._pipe = [Reg(width, f"mcp_{i}") for i in range(n_cycles)]
        with self.comb:
            self.data_out <<= self._pipe[n_cycles - 1]
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for i in range(n_cycles): self._pipe[i] <<= 0
            with Else():
                self._pipe[0] <<= self.data_in
                for i in range(1, n_cycles):
                    with If(self.en == 1):
                        self._pipe[i] <<= self._pipe[i - 1]
