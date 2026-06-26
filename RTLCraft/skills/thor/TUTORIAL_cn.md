# Thor GPU — 三层设计教程

## 1. 概述

Thor GPU 设计遵循**三层元模型**，从抽象规格到可综合 RTL 逐级精化：

```
第一层 — 功能模型 (functional.py)
    │ 纯 Python 函数，无时序。验证算法正确性。
    ▼
第二层 — 周期精确模型 (cycle_level.py)
    │ CycleContext 闭包，寄存器精确时序。验证流水线。
    ▼
第三层 — RTL DSL 模型 (layer3_dsl/*.py)
    │ Module 子类，可综合 Verilog。比特/周期精确。
    ▼
Verilog (通过 rtlgen.codegen.VerilogEmitter)
```

**跨层一致性**是强制要求：同一测试程序必须在三个层上产生完全一致的结果。由 `test_consistency.py` 保证。

## 2. L1：功能模型

### 规范

```
签名: module_functional(**kwargs) -> Callable
内函数: func(**inputs) -> Dict[str, int]
```

| 属性 | 要求 |
|------|------|
| 时序 | **无**。纯组合逻辑，无时钟、无 cycle 概念 |
| 状态 | **无**。每次调用独立，调用者维护状态 |
| 输入 | 命名的 Python 关键字参数，带默认值和类型注解 |
| 输出 | `Dict[str, int]`，键名与 L3 端口名一致 |
| 配置 | 通过外层工厂函数的 `**kwargs` 传入 |

### 示例

```python
# skills/thor/functional.py
def vector_alu_functional(**kwargs) -> Callable:
    n_lane = kwargs.get('n_lane', 16)
    xlen = kwargs.get('xlen', 32)
    mask = (1 << xlen) - 1
    def func(opcode=0, op1=0, op2=0, pred_mask=0xFFFF) -> Dict:
        result = 0
        for lane in range(n_lane):
            if not ((pred_mask >> lane) & 1): continue
            a = (op1 >> (lane * xlen)) & mask
            b = (op2 >> (lane * xlen)) & mask
            r = (a + b) & mask if opcode == OP_VADD else (a * b) & mask
            result |= r << (lane * xlen)
        return {"result": result, "valid": 1}
    return func
```

### 调用方式

```python
alu_fn = vector_alu_functional(n_lane=16, xlen=32)
r = alu_fn(opcode=OP_VADD, op1=broadcast(5), op2=broadcast(3), pred_mask=0xFFFF)
assert r["result"] == broadcast(8)
```

## 3. L2：周期精确模型

### 规范

```
签名: module_cycle(**kwargs) -> Callable[[CycleContext], None]
内函数: behavior(ctx: CycleContext) -> None
```

| 属性 | 要求 |
|------|------|
| 时序 | **周期精确**。一次 `ArchSimulator.step()` = 一个时钟周期 |
| 状态 | `ctx.state[]` 跨周期保持；`ctx.set_state()` 写 `next_state` |
| 复位 | **强制**。每个 behavior 必须首先检查 `rst` |
| 输入 | `ctx.get_input('信号名', 默认值)` |
| 输出 | `ctx.set_output('信号名', 值)` |
| 注册 | `TemplateRegistry.register('名称', behavior_fn)` |

### 示例

```python
def warp_scheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    n_warps = kwargs.get('n_warps', 4)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['last_warp'] = 0; return
        warp_ready = ctx.get_input('warp_ready_mask', 0)
        warp_stall = ctx.get_input('warp_stall_mask', 0)
        avail = warp_ready & ~warp_stall
        last = ctx.state.get('last_warp', 0)
        sel, valid = last, 0
        if avail:
            for i in range(n_warps):
                idx = (last + 1 + i) % n_warps
                if (avail >> idx) & 1:
                    sel, valid = idx, 1; break
        ctx.state['last_warp'] = sel
        ctx.set_output('selected_warp', sel)
        ctx.set_output('select_valid', valid)
    return behavior
```

## 4. L3：RTL DSL 模型

### 规范

```
继承:    class MyModule(rtlgen.core.Module)
信号:    Input(width, name) / Output(width, name)
         Wire(width, name) / Reg(width, name)
组合:    with self.comb:
时序:    with self.seq(clk, rst):
赋值:    signal <<= expr
```

### 流水线模块模板

```python
class VectorALU(Module):
    def __init__(self, name="vector_alu", latency=3):
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.opcode = Input(5, "opcode")
        self.op1 = Input(512, "op1"); self.op2 = Input(512, "op2")
        self.in_valid = Input(1, "in_valid"); self.out_ready = Input(1, "out_ready")
        self.result = Output(512, "result"); self.out_valid = Output(1, "out_valid")
        self.in_ready = Output(1, "in_ready")

        self._pv = [Reg(1, f"pv_{i}") for i in range(latency)]
        self._pd = [Reg(512, f"pd_{i}") for i in range(latency)]

        with self.comb:
            self.in_ready <<= (self._pv[latency-1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            # 逆序移位，支持流水线 drain
            with If(self._pv[latency-1] & self.out_ready):
                self._pv[latency-1] <<= 0
            for s in range(latency-2, -1, -1):
                nxt_free = (self._pv[s+1] == 0)
                with If(self._pv[s] & (nxt_free | self.out_ready)):
                    self._pd[s+1] <<= self._pd[s]
                    self._pv[s+1] <<= 1; self._pv[s] <<= 0
            with If(self.in_valid & self.in_ready):
                self._pd[0] <<= self.op1 + self.op2
                self._pv[0] <<= 1
```

## 5. 模板库

RTLCraft 内置 22 个参数化微架构模板，位于 `rtlgen/lib.py`。

### 常用模板

| 模板 | 功能 |
|------|------|
| `PipelineShift` | 可配置深度流水线 + valid/ready 握手 |
| `SyncFIFO` | 同步 FIFO |
| `AsyncFIFO` | 异步 FIFO + Gray 码跨时钟域 |
| `RoundRobinArbiter` | 轮询仲裁器 |
| `Counter` | 可加载计数器 |
| `MultiCycleFSM` | IDLE→REQ→WAIT→DONE 通用状态机 |
| `RegisterFile` | 多端口寄存器文件 |
| `CAM` | 全关联内容寻址存储器 |
| `DirectMappedCache` | 直接映射缓存 |
| `SetAssocCache` | N 路组相联缓存 + LRU 替换 |
| `SyncCell` | 2 级触发器 CDC 同步器 |
| `PulseSynchronizer` | 脉冲跨时钟域同步器 |
| `EdgeDetector` | 上升/下降沿检测 |
| `ClockGate` | 锁存器型门控时钟 |
| `AsyncResetRel` | 异步复位同步释放 |
| `BypassNetwork` | 执行单元转发网络 |
| `MAC` | 流水线乘累加 |

## 6. PPA 驱动优化

```python
from rtlgen.ppa import PPAAnalyzer
from rtlgen.lib import MAC

mac = MAC(width=16)
pa = PPAAnalyzer(mac)

# 静态分析（无需仿真）
static = pa.analyze_static()
print(f"等效门数: {static['gate_count']:.0f}")
print(f"寄存器位数: {static['reg_bits']}")
print(f"逻辑深度: {static['logic_depth']}")
print(f"扇出: {static['fanout_report']}")

# 优化建议
for s in pa.suggest_optimizations():
    print(s)

# 完整报告
print(pa.report())
```

### 优化闭环

```
1. 编写/修改 DSL 模块
2. PPAAnalyzer.analyze_static() → 获取 gate_count, logic_depth, fanout
3. 如果 logic_depth > 6：插入 PipelineShift 流水线级
4. 如果 fanout > 8：复制高扇出信号
5. 如果存在 dead_signals：删除未使用逻辑
6. 重新发射 Verilog，重新验证
```

## 7. UVM 验证

### 生成 UVM Testbench

```python
from rtlgen.uvmgen import UVMEmitter
from rtlgen.lib import MAC
uvm = UVMEmitter()
files = uvm.emit_full_testbench(MAC(width=16))
# files = {"MAC_if.sv": ..., "MAC_pkg.sv": ..., "MAC_driver.sv": ..., ...}
```

### Golden Trace 桥接

```python
from rtlgen.uvm_scoreboard import generate_golden_trace
from rtlgen.lib import MAC
sv_code, golden_data = generate_golden_trace(
    MAC(width=16),
    stimuli=[{"a": 5, "b": 3}, {"a": 7, "b": 2}],
    output_signals=["acc_out", "valid"],
)
# sv_code: UVM scoreboard SV 代码
# golden_data: 每周期期望值
```

## 8. 三层对比

| 维度 | L1 功能级 | L2 周期级 | L3 DSL |
|------|-----------|-----------|--------|
| **文件** | `functional.py` | `cycle_level.py` | `layer3_dsl/*.py` |
| **声明方式** | `def fn(**kw)→Dict` | `def fn(ctx)→None` | `class M(Module)` |
| **状态管理** | 调用者手动 | `ctx.state[]` 自动 | `Reg` 信号 |
| **时序** | 无 | 周期级 (step) | 时钟沿级 (posedge) |
| **复位** | 无 | 手动 `if rst:` | `with self.seq(clk, rst):` |
| **输入** | 函数参数 | `ctx.get_input()` | `Input(width, name)` |
| **输出** | `return Dict` | `ctx.set_output()` | `Output <<=` |
| **组合逻辑** | 全部代码 | `ctx.state` 组合使用 | `with self.comb:` |
| **时序逻辑** | ❌ | `ctx.state` 跨周期 | `with self.seq():` |
| **子模块** | 函数组合 | PE 层次 | `self.instantiate()` |
| **控制流** | Python `if/for` | Python `if/for` | `If/Switch/ForGen` |
| **仿真器** | 无（直接调用） | `ArchSimulator` | `Simulator` |
| **速度** | ~1μs/调用 | ~100μs/周期 | ~45μs/步 (JIT) |
| **Verilog** | ❌ | ❌ | ✅ `VerilogEmitter` |
| **最佳用途** | 算法验证 | 架构探索 | RTL 生成 |

## 9. 跨层一致性

### 验证方法

同一程序依次通过 L1 → L2 → L3 执行，输出必须逐比特匹配：

```
程序 (指令序列)
  ├──→ L1 functional.py    → Dict[str, int]
  ├──→ L2 cycle_level.py   → ArchSimulator 信号
  └──→ L3 layer3_dsl/*.py  → Simulator 信号
                              ↓ 比较
                        必须完全相同
```

### 验证覆盖

`test_consistency.py` 覆盖：
- L1 SLOAD 广播：所有 16 通道收到相同立即数
- L1 SIMD VADD/VMUL：逐 32-bit lane 正确计算
- L2 SM 行为：ArchSimulator 运行完整程序
- L3 流水线 Valid 信号：多级流水线握手正常
- Golden 计算内核：`5*3 + 7*2 = 29`
- Golden 多 Warp：4 个 warp 独立 VRF
- 跨层一致：L1 == Golden 逐比特匹配

## 10. API 参考

### CycleContext

```python
ctx.get_input(name, default=0)        # 读输入
ctx.set_output(name, value)            # 写输出
ctx.get_state(name, default=None)      # 读状态
ctx.set_state(name, value)             # 写下一周期状态
```

### Module 信号 API

```python
Input(width, name); Output(width, name)
Wire(width, name);  Reg(width, name, init_value=0)
signal <<= expr         # Reg: 非阻塞; Wire/Output: 连续

# 表达式
a + b, a - b, a * b    # 算术
a & b, a | b, a ^ b    # 位运算
~a                      # 按位取反
a << n, a >> n          # 移位
a == b, a != b          # 比较
a[hi:lo]                # 位片选
a[idx]                  # 位选
Cat(a, b, ...)          # 拼接
Rep(sig, n)             # 复制
Mux(cond, t, f)         # 二选一
REDUCE_AND(a)           # &a (归约 AND)
LOGIC_AND(a, b)         # a && b
clog2(x)                # $clog2(x)

# 控制流
with If(cond): ... with Elif(cond): ... with Else(): ...
with Switch(expr, kind="case") as sw: sw.case(v): ... sw.default(): ...
with ForGen("i", start, end): ...
```

### Simulator API

```python
Simulator(module, use_xz=False, clock_period_ns=10.0)
sim.set(name, value)            # 设置输入
sim.get_int(name) → int         # 读信号值
sim.step()                      # 推进一个时钟周期
sim.reset(rst, cycles=2)        # 复位序列
sim.assert_eq(name, expected)   # 断言信号值
```

### PPAAnalyzer API

```python
PPAAnalyzer(module, tech_node="7nm")
pa.analyze_static()
  → {"logic_depth": {...}, "gate_count": 394.0,
     "reg_bits": 96, "fanout_report": {...}, ...}
pa.analyze_dynamic(sim, n_cycles=100)
  → {"toggle_rates": {...}, "power_hotspots": [...]}
pa.suggest_optimizations()
  → ["[时序] ...", "[面积] ..."]
pa.report(sim=sim)  → str
```
