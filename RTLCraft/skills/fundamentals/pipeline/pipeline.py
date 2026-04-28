"""
rtlgen.pipeline — 流水线引擎

提供 Pipeline / Stage / Handshake，支持自动生成级间寄存器与 valid/ready 握手。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from rtlgen.core import Context, Input, Module, Output, Reg, Signal, Wire
from rtlgen.logic import Else, If, Mux


class Handshake:
    """流水线握手信号组（valid/ready/data）。"""

    def __init__(
        self,
        data_width: int,
        name: str = "",
        data: Optional[Signal] = None,
        valid: Optional[Signal] = None,
        ready: Optional[Signal] = None,
    ):
        self.name = name
        self.data = data if data is not None else Signal(data_width, name=f"{name}_data")
        self.valid = valid if valid is not None else Signal(1, name=f"{name}_valid")
        self.ready = ready if ready is not None else Signal(1, name=f"{name}_ready")

    def fire(self) -> Signal:
        """握手成功条件: valid & ready"""
        return self.valid & self.ready


@dataclass
class _StageDef:
    name: str
    index: int
    func: Callable


class StageContext:
    """传递给 stage 装饰函数的执行上下文。"""

    def __init__(self, stage_name: str, in_hs: Handshake, out_hs: Handshake):
        self.stage_name = stage_name
        self.in_hs = in_hs
        self.out_hs = out_hs

        # 为 stage 内部暴露的本地信号（计算中间结果）
        self.locals: Dict[str, Signal] = {}

    def local(self, name: str, width: int = 1) -> Signal:
        """在 stage 内申请一个本地 Wire。"""
        w = Wire(width, name=f"{self.stage_name}_{name}")
        self.locals[name] = w
        # 显式注册到父模块的 wire 表中
        ctx = Context.current()
        if ctx and ctx.module is not None:
            ctx.module._wires[w.name] = w
        return w


class Pipeline(Module):
    """流水线容器，自动管理级间寄存器与全局握手。

    示例:
        pipe = Pipeline("alu_pipe", data_width=32)
        pipe.clk = Input(1, "clk")
        pipe.rst = Input(1, "rst")

        @pipe.stage(0)
        def fetch(ctx):
            ctx.out_hs.data <<= ctx.in_hs.data + 1
            ctx.out_hs.valid <<= ctx.in_hs.valid

        @pipe.stage(1)
        def exec_(ctx):
            ctx.out_hs.data <<= ctx.in_hs.data * 2
            ctx.out_hs.valid <<= ctx.in_hs.valid

        pipe.build()
    """

    def __init__(self, name: str, data_width: int, has_handshake: bool = True):
        super().__init__(name)
        self.data_width = data_width
        self.has_handshake = has_handshake
        self._stages: List[_StageDef] = []

        # 顶层握手端口 —— 显式声明为 Input/Output 并注册到模块
        if has_handshake:
            in_data = Input(data_width, "in_hs_data")
            in_valid = Input(1, "in_hs_valid")
            in_ready = Output(1, "in_hs_ready")
            self.in_hs_data = in_data
            self.in_hs_valid = in_valid
            self.in_hs_ready = in_ready
            self.in_hs = Handshake(
                data_width, name="in_hs", data=in_data, valid=in_valid, ready=in_ready
            )

            out_data = Output(data_width, "out_hs_data")
            out_valid = Output(1, "out_hs_valid")
            out_ready = Input(1, "out_hs_ready")
            self.out_hs_data = out_data
            self.out_hs_valid = out_valid
            self.out_hs_ready = out_ready
            self.out_hs = Handshake(
                data_width, name="out_hs", data=out_data, valid=out_valid, ready=out_ready
            )

    def stage(self, index: int):
        """装饰器：定义流水线级。"""

        def decorator(func: Callable):
            self._stages.append(_StageDef(name=func.__name__, index=index, func=func))
            return func

        return decorator

    def build(self):
        """自动插入寄存器、连线及握手控制逻辑。"""
        if not self._stages:
            return

        self._stages.sort(key=lambda s: s.index)
        stage_count = len(self._stages)

        # 为每一级创建独立的输入/输出 Handshake（内部 Wire）
        stage_in: List[Handshake] = []
        stage_out: List[Handshake] = []
        for i in range(stage_count):
            sin = self._create_handshake_signals(f"stage{i}_in")
            sout = self._create_handshake_signals(f"stage{i}_out")
            stage_in.append(sin)
            stage_out.append(sout)

        if self.has_handshake:
            # 绑定顶层输入到 stage0_in
            self._bind_top_handshake(stage_in[0], self.in_hs)
            # 绑定最后一级输出到顶层输出
            self._bind_top_handshake(self.out_hs, stage_out[-1])

        # 构建每一级的组合逻辑
        for i in range(stage_count):
            stage = self._stages[i]
            self._build_stage_logic(stage, stage_in[i], stage_out[i])

        # 插入级间寄存器（数据/valid 前向，ready 反向组合）
        for i in range(stage_count - 1):
            self._build_interstage_regs(stage_out[i], stage_in[i + 1])

        if self.has_handshake:
            self._build_handshake_logic(stage_in, stage_out)

    def _create_handshake_signals(self, name: str) -> Handshake:
        """创建一组内部 Wire 用于级间 Handshake，并注册到模块声明表。"""
        data = Wire(self.data_width, name=f"{name}_data")
        valid = Wire(1, name=f"{name}_valid")
        ready = Wire(1, name=f"{name}_ready")
        self._wires[data.name] = data
        self._wires[valid.name] = valid
        self._wires[ready.name] = ready
        return Handshake(self.data_width, name=name, data=data, valid=valid, ready=ready)

    def _bind_top_handshake(self, local_hs: Handshake, top_hs: Handshake):
        @self.comb
        def _bind():
            local_hs.data <<= top_hs.data
            local_hs.valid <<= top_hs.valid
            top_hs.ready <<= local_hs.ready

    def _build_stage_logic(self, stage: _StageDef, in_hs: Handshake, out_hs: Handshake):
        ctx = StageContext(stage.name, in_hs, out_hs)

        @self.comb
        def _logic():
            stage.func(ctx)

    def _build_interstage_regs(self, out_hs: Handshake, next_in: Handshake):
        clk = getattr(self, "clk", None)
        rst = getattr(self, "rst", None)
        if clk is None:
            raise RuntimeError(
                f"Pipeline '{self.name}' needs a 'clk' signal for interstage registers. "
                "Please define self.clk = Input(1) before build()."
            )

        @self.seq(clk, rst)
        def _regs():
            if rst is not None:
                with If(rst == 1):
                    next_in.valid <<= 0
                with Else():
                    with If(out_hs.fire()):
                        next_in.data <<= out_hs.data
                        next_in.valid <<= out_hs.valid
            else:
                with If(out_hs.fire()):
                    next_in.data <<= out_hs.data
                    next_in.valid <<= out_hs.valid

        @self.comb
        def _ready_back():
            # 若下一级寄存器为空（valid=0）或下一级已 ready，则当前级可以接收数据
            out_hs.ready <<= (~next_in.valid) | next_in.ready

    def _build_handshake_logic(self, stage_in: List[Handshake], stage_out: List[Handshake]):
        """生成每一级输入 ready 的反向传播逻辑。"""
        stage_count = len(self._stages)

        for i in range(stage_count):
            curr_in = stage_in[i]
            curr_out = stage_out[i]

            @self.comb
            def _ready(in_hs=curr_in, out_hs=curr_out):
                # 若本级输出无效，或输出已 ready，则输入可以接收新数据
                in_hs.ready <<= (~out_hs.valid) | out_hs.ready


# =====================================================================
# Lower-level pipeline primitives
# =====================================================================

class ShiftReg(Module):
    """Simple shift register with asynchronous active-low reset.

    Parameters
    ----------
    width : int
        Bit width of the data.
    depth : int
        Number of register stages.
    name : str
        Module instance name.
    """

    def __init__(self, width: int, depth: int, name: str = "ShiftReg"):
        super().__init__(name)
        self.width = width
        self.depth = depth
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.din = Input(width, "din")
        self.dout = Output(width, "dout")

        if depth <= 0:
            @self.comb
            def _bypass():
                self.dout <<= self.din
            return

        self.regs = [Reg(width, f"r{i}") for i in range(depth)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _shift():
            with If(self.rst_n == 0):
                for r in self.regs:
                    r <<= 0
            with Else():
                for i in range(depth - 1, 0, -1):
                    self.regs[i] <<= self.regs[i - 1]
                self.regs[0] <<= self.din

        @self.comb
        def _out():
            self.dout <<= self.regs[depth - 1]


class ValidPipe(Module):
    """Single pipeline stage with valid gating.

    Captures ``din`` only when ``valid_in`` is high.  Output holds the
    last captured value.  This is useful for feed-forward pipelines that
    need to propagate data/valid pairs without back-pressure.
    """

    def __init__(self, width: int, name: str = "ValidPipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.din = Input(width, "din")
        self.valid_in = Input(1, "valid_in")
        self.dout = Output(width, "dout")
        self.valid_out = Output(1, "valid_out")

        self.data_reg = Reg(width, "data_reg")
        self.valid_reg = Reg(1, "valid_reg")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _logic():
            with If(self.rst_n == 0):
                self.valid_reg <<= 0
            with Else():
                self.valid_reg <<= self.valid_in
                with If(self.valid_in):
                    self.data_reg <<= self.din

        @self.comb
        def _out():
            self.dout <<= self.data_reg
            self.valid_out <<= self.valid_reg


# =====================================================================
# Simulation debug helpers
# =====================================================================

class DebugProbe:
    """Hierarchical signal probe for rtlgen Simulator objects.

    Example
    -------
    >>> probe = DebugProbe(sim)
    >>> probe.print_all(signals=["valid_in", "q_valid_d", "out_valid"])
    """

    def __init__(self, sim):
        self.sim = sim
        self.subsims = {}
        for item in sim._subsim_info:
            path = item[0]
            subsim = item[1]
            self.subsims[path] = subsim

    def get(self, name: str, path: str = ""):
        """Read a signal by name.  If *path* is given, read from submodule."""
        if path:
            return self.subsims[path].get(name)
        return self.sim.get(name)

    def get_int(self, name: str, path: str = ""):
        """Read a signal and return as Python int."""
        val = self.get(name, path)
        if isinstance(val, int):
            return val
        return int(val)

    def print_all(self, signals, path_prefix="", fmt="hex"):
        """Print signals from all submodules whose path contains *path_prefix*."""
        items = [("top", self.sim)]
        for p, s in self.subsims.items():
            if path_prefix in p:
                items.append((p, s))
        for p, s in items:
            vals = []
            for sig in signals:
                try:
                    v = s.get(sig)
                    if fmt == "hex":
                        vals.append(f"{sig}={hex(v)}")
                    else:
                        vals.append(f"{sig}={v}")
                except Exception as e:
                    vals.append(f"{sig}=ERR({e})")
            print(f"[{p}] " + " ".join(vals))

    def find_subsim(self, name_hint: str):
        """Return the first submodule path that contains *name_hint*."""
        for p in self.subsims:
            if name_hint in p:
                return p, self.subsims[p]
        raise KeyError(f"No submodule matching '{name_hint}'")
