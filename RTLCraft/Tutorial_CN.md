# rtlgen 教程

这份教程说明发布版 `rtlgen` 的推荐使用方式。重点不是旧的 Skills/Spec2RTL
大流程，而是最佳实践：如何写一个小模块、仿真、生成 RTL、定位问题，并逐步
扩展到更大的 datapath，同时保持语义清晰。

发布包名是 `rtlgen`；所有示例都使用这个名称。

## 1. 心智模型

把 `rtlgen` 理解成一个可执行 RTL 工作台：

```text
reference behavior
  -> DSL module
  -> Python simulation
  -> compiled C++ simulation
  -> emitted SystemVerilog
  -> 本地 RTL simulator smoke / closure
  -> verification 与 PPA report
```

最佳实践是保持短闭环。不要一开始就生成大量 RTL。先从一个模块、一个行为
期望、一条 focused test 开始。

## 2. 写最小有用模块

端口和状态要显式。所有设计可见信号都挂在 `self` 上。

```python
from rtlgen.dsl import Else, If, Input, Module, Output, Reg


class Counter(Module):
    def __init__(self, width=8):
        super().__init__("Counter")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.value = Output(width, "value")

        self.count = Reg(width, "count")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.count <<= 0
            with Else():
                with If(self.en == 1):
                    self.count <<= self.count + 1

        with self.comb:
            self.value <<= self.count
```

关键规则：

1. 使用 `with If(...)`，不要用 Python `if`
2. 使用 `self.count = Reg(...)`，不要写 host-local `count = Reg(...)`
3. 输出连接放在可见的 comb block 中
4. reset 行为要清楚

## 3. 先跑 Python 仿真

```python
from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

dut = Counter()
sim = PythonSimulator(lower_dsl_module_to_sim(dut).module)

print(sim.step({"clk": 0, "rst": 1, "en": 0}))
print(sim.step({"clk": 0, "rst": 0, "en": 1}))
print(sim.step({"clk": 0, "rst": 0, "en": 1}))
```

Python 仿真适合：

1. reset/debug 可观察性
2. 快速迭代控制逻辑
3. 检查 DSL authoring intent 是否能被 lowering 接受
4. 在引入外部工具之前观察 state 和 output trace

如果 lowering 失败，先修 lowering 诊断。lowering diagnostics 本来就是写
DSL 的一部分。

## 4. 加 compiled simulation parity

Python 仿真稳定后，再加 compiled simulation。

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl

cpp_sim = build_compiled_simulator_from_dsl(Counter())
print(cpp_sim.step({"clk": 0, "rst": 1, "en": 0}))
print(cpp_sim.step({"clk": 0, "rst": 0, "en": 1}))
```

最佳实践：

1. Python 和 compiled simulator 使用同一组 test vector
2. Python-vs-C++ mismatch 优先当成 framework/backend 或 signed-width 问题
   排查，除非已经证明不是
3. Python 定位清楚后，再用 compiled simulation 跑更大的 regression

## 5. 生成 SystemVerilog

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Counter())
print(rtl)
```

推荐 backend 顺序：

1. Python simulation：修 DSL 语义
2. compiled C++ simulation：做 parity 和速度提升
3. `iverilog -g2012`：轻量 compile smoke
4. `verilator`：更强的本地 emitted-RTL closure
5. 本地 `vcs`：如果环境提供，并且需要项目级 simulator 行为

发布版文档不依赖网络登录式 simulator flow。有本地 VCS 时，直接使用本地
VCS。

## 6. Signed Datapath 最佳实践

signed fixed-point 逻辑最容易因为隐藏假设出错。要显式。

```python
from rtlgen.dsl import Const, Mux, RoundShiftRight, Wire

self.prod = Wire(32, "prod", signed=True)
self.sum_next = Wire(32, "sum_next", signed=True)
self.scaled = Wire(32, "scaled", signed=True)
self.final = Wire(33, "final", signed=True)
self.clipped = Wire(33, "clipped", signed=True)

with self.comb:
    self.prod <<= self.sample.as_sint() * self.coeff.as_sint()
    self.sum_next <<= self.acc + self.prod
    self.scaled <<= RoundShiftRight(self.sum_next, 14)
    self.final <<= self.scaled.as_sint() + Const(128, 33)
    self.clipped <<= Mux(
        self.final.as_sint() < Const(0, 33).as_sint(),
        Const(0, 33),
        Mux(
            self.final.as_sint() > Const(255, 33).as_sint(),
            Const(255, 33),
            self.final,
        ),
    )
```

检查清单：

1. 表示 signed 值的 storage read，在算术边界使用 `.as_sint()`
2. 使用 `RoundShiftRight(...)`，不要依赖普通 shift 的隐式语义
3. signed 值用 signed compare
4. narrowing 到输出位宽之前先 clip
5. intermediate signal 挂在 module 上，方便 trace 和查看生成 RTL

`jpeg_decoder/` 中的 JPEG IDCT 是发布版中这个模式的主要示例。

## 7. Storage 最佳实践

使用 module-owned `Array` 和 `Memory`。

```python
from rtlgen.dsl import Array, Memory, Wire

self.buf = Array(16, 64, "buf")
self.rom = Memory(16, 64, "rom", init_data=my_table)
self.addr = Wire(6, "addr")
self.data = Wire(16, "data")

with self.comb:
    self.data <<= self.rom[self.addr]
```

规则：

1. `init_data` 和 `init_file` 是设计语义
2. emitted RTL 需要同样内容时，不要把 table 藏在 host-side Python 控制流里
3. address construction 保持在可见 wire/reg 中
4. 不支持的 storage contract 会 fail fast，不要把它当静默综合 hint

当前稳定 storage 子集有意比完整 memory compiler interface 更窄。详见
`rtlgen/DSL_SUPPORT_MATRIX.md` 与 `rtlgen/DSL_SEMANTICS.md`。

## 8. Hierarchy 最佳实践

子模块之间使用显式 parent-owned wire。

```python
self.mid_data = Wire(16, "mid_data")
self.mid_valid = Wire(1, "mid_valid")
self.mid_ready = Wire(1, "mid_ready")

self.instantiate(stage0, "u_stage0", port_map={
    "out_data": self.mid_data,
    "out_valid": self.mid_valid,
    "out_ready": self.mid_ready,
})

self.instantiate(stage1, "u_stage1", port_map={
    "in_data": self.mid_data,
    "in_valid": self.mid_valid,
    "in_ready": self.mid_ready,
})
```

不要在 constructor 里创建临时 local handoff wire 后忘记挂到 `self`。这种写法
会让 lowering 和 emission 难以判断 ownership，authoring-intent checker 会
拒绝它。

## 9. Verification 最佳实践

先从最小 deterministic tests 开始：

1. reset 行为
2. 一个普通 transaction
3. 一个边界 transaction
4. 如果有 ready/valid，补一个 backpressure 或 stall transaction
5. 如果是数值 datapath，补一个 signed 或 overflow case

然后逐步扩大：

1. Python simulator directed tests
2. compiled simulator parity
3. streaming 或 Python-UVM 风格检查
4. emitted RTL smoke
5. executable path 稳定后，再生成 SV/UVM collateral

尽量在不同层复用同一组 transaction。

## 10. PPA Feedback 最佳实践

把 PPA 分析当成早期设计 review 辅助：

1. 查看过宽组合表达式
2. 查看 register/storage 增长
3. 找重复 arithmetic 或 mux 结构
4. critical expression 太深时考虑 pipeline staging
5. 每次 rewrite 后重新跑功能测试

不要把 PPA report 当成最终 signoff。最终 timing/area/power 仍然属于综合和
实现流程。

## 11. 示例：JPEG Datapath

发布版包含一个 JPEG 风格 datapath 示例：

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

它展示了：

1. signed fixed-point IDCT
2. LUT-backed MAC
3. transpose 和 zig-zag reorder buffer
4. parent-owned stage handoff wire
5. Python/compiled simulator parity
6. emitted RTL compile smoke

使用 `jpeg_decoder/README.md` 查看 rerun 顺序，使用
`rtlgen/JPEG_DATAPATH_COOKBOOK.md` 查看可复用 datapath pattern。

## 12. 新设计发布前检查清单

把一个 module 当成 release-ready 之前，请确认：

1. Python simulator tests 通过
2. compiled simulator parity 通过
3. review profile 能生成 emitted RTL
4. 支持子集内的本地 RTL compile smoke 通过
5. signed/storage/hierarchy diagnostics 干净
6. 相关 support-matrix 边界已记录
7. README 或 module notes 说明 focused tests 如何 rerun

这就是实用的 `rtlgen` 闭环：保持设计可执行，保持语义显式，让所有工具消费同
一份 authored structure。
