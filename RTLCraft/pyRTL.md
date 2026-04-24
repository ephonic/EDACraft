# pyRTL — Python API for Verilog RTL Generation

> 一套面向对象、装饰器驱动的 Python API，用于描述可综合的 Verilog-2001 数字逻辑。

---

## 1. 快速开始

```bash
cd examples
python counter.py
python pipeline_adder.py
python fsm_traffic.py
python generate_for_inst_demo.py
python protocols_demo.py
```

---

## 2. 核心 API (`rtlgen.core`)

### 2.1 Signal 与派生类

| 类 | 说明 |
|----|------|
| `Signal(width=1, name="", signed=False)` | 信号基类，支持位宽推导与运算符重载。 |
| `Input(width, name)` | 模块输入端口。 |
| `Output(width, name)` | 模块输出端口（在 always 中驱动会自动推导为 `output reg`）。 |
| `Wire(width, name)` | 组合逻辑中间信号。 |
| `Reg(width, name)` | 时序逻辑寄存器。 |
| `Vector(width, size, name, vtype)` | 一维信号向量，减少重复声明。 |

**运算符支持**：`+ - * & | ^ ~ == != < <= > >= << >> []`

```python
from rtlgen import Signal, Input, Output, Wire, Reg

a = Input(8, "a")
b = Input(8, "b")
sum_ = Output(8, "sum")

carry = Wire(1, "carry")
result = Reg(9, "result")

sum_ <<= a + b           # 组合赋值
carry <<= a[7] & b[7]    # 位选
result <<= a + b + carry # 时序赋值（在 @seq 中）

### Vector 信号组

```python
from rtlgen import Vector, Wire, Reg

A = Vector(48, 3, "A", vtype=Wire)   # A_0, A_1, A_2 三个 Wire(48)
B = Vector(48, 3, "B", vtype=Reg)    # B_0, B_1, B_2 三个 Reg(48)

for i in range(3):
    B[i] <<= A[i] + 1
```

**批量赋值**（v0.x+）：

```python
B <<= A                    # Vector <<= Vector，按元素一一对应
B <<= [1, 2, 3]           # Vector <<= list，逐元素赋常数
```

`Vector` 会自动将内部信号注册到父模块的声明表中。

### 2.2 Parameter 与 LocalParam

```python
from rtlgen import Parameter, LocalParam

width = Parameter(32, "WIDTH")
depth = LocalParam(16, "DEPTH")
```

生成：
```verilog
module MyMod #(parameter WIDTH = 32) (
    ...
);
    localparam DEPTH = 16;
    ...
```

**快捷方法**（推荐）：
- `self.add_param(name, value)` → 创建可配置的 `parameter`
- `self.add_localparam(name, value)` → 创建不可重载的 `localparam`

```python
class MyMod(Module):
    def __init__(self):
        super().__init__("MyMod")
        self.add_param("WIDTH", 32)
        self.add_localparam("MASK", (1 << 32) - 1)
```

- `Parameter` 会出现在模块头部的 `#(...)` 中，允许在实例化时被覆盖。
- `LocalParam` 只在模块内部以 `localparam` 形式声明，不会被例化参数覆盖。

### 2.3 Module

所有硬件模块的基类。

```python
from rtlgen import Module, Input, Output, Reg

class Counter(Module):
    def __init__(self, width=8):
        super().__init__("Counter")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.count = Output(width, "count")
        self._cnt = Reg(width, "cnt")

        @self.comb
        def _out():
            self.count <<= self._cnt

        @self.seq(self.clk, self.rst)
        def _logic():
            with If(self.rst == 1):
                self._cnt <<= 0
            with Else():
                self._cnt <<= self._cnt + 1
```

**快捷方法**（自 v0.x 起支持）：
- `self.input(width, name)` → 等价于 `self.xxx = Input(width, name)`
- `self.output(width, name)` → 等价于 `self.xxx = Output(width, name)`
- `self.reg(width, name)` → 等价于 `self.xxx = Reg(width, name)`
- `self.wire(width, name)` → 等价于 `self.xxx = Wire(width, name)`
- `self.parameter(value, name)` → 等价于 `self.xxx = Parameter(value, name)`
- `self.add_param(name, value)` → 创建 `Parameter(name, value)`
- `self.add_localparam(name, value)` → 创建 `LocalParam(name, value)`

例如：
```python
class Adder(Module):
    def __init__(self):
        super().__init__("Adder")
        self.a = self.input(8, "a")
        self.b = self.input(8, "b")
        self.sum = self.output(8, "sum")
        self.carry = self.wire(1, "carry")

        @self.comb
        def _logic():
            self.sum <<= self.a + self.b
            self.carry <<= (self.a + self.b)[8]
```

**装饰器说明**：
- `@self.comb` → 生成 `always @(*)` 或 `assign`
- `@self.seq(clk, rst)` → 生成 `always @(posedge clk or posedge rst)`

**内部信号声明**：
- 所有中间信号（`Wire`、`Reg`）在生成的 SV 中统一声明为 `logic`，兼容 `always @(*)` 与 `assign` 双重驱动场景，避免传统 `wire` 在过程块中赋值导致的编译错误。

### 2.4 Memory

```python
from rtlgen import Memory

mem = Memory(width=32, depth=1024, name="mem", init_file="data.hex")
```

**注册方式**：
- 直接赋值即可自动注册：`self.mem = Memory(32, 1024, "mem")`
- 也可以显式注册：`self.add_memory(mem, "mem")`

**读写语法**：
- 读：`mem[addr]` 作为表达式使用
- 写：`mem[addr] <<= value`（在 `@comb` 或 `@seq` 中）

生成：
```verilog
reg [31:0] mem [0:1023];
initial begin
    $readmemh("data.hex", mem);
end
```

---

## 3. 逻辑控制 (`rtlgen.logic`)

### 3.1 If / Else

```python
from rtlgen.logic import If, Else

with If(a == b):
    c <<= 1
with Else():
    c <<= 0
```

### 3.2 Switch / Case

```python
from rtlgen.logic import Switch

with Switch(opcode) as sw:
    with sw.case(0b001):
        result <<= a + b
    with sw.case(0b010):
        result <<= a - b
    with sw.default():
        result <<= 0
```

### 3.3 ForGen（generate-for）

```python
from rtlgen.logic import ForGen

with ForGen("i", 0, 8) as i:
    self.y[i] <<= self.a[i] & self.b[i]
```

生成：
```verilog
genvar i;
for (i = 0; i < 8; i = i + 1) begin : genblk
    assign y[i] = (a[i] & b[i]);
end
```

**ForGen 中支持子模块实例化**：见第 9 节。

### 3.4 StateTransition — FSM 状态转移收集器

`StateTransition` 解决 `seq` 块中**同一寄存器在多个 `If` 分支被多次赋值**导致的覆盖/歧义问题。它将分散的 `(condition, next_value)` 对收集起来，最终合并为**单一的优先级 Mux 链赋值**。

**问题背景**

在 `@self.seq` 块中，如果写出：

```python
@self.seq(self.clk, self.rst_n)
def _fsm():
    with If(self.state == IDLE):
        self.state <<= WORK
    with If(self.state == WORK):
        self.state <<= READ
    with If(self.state == READ):
        self.state <<= DONE
```

生成的 Verilog 是多个独立 `if` 语句。虽然综合器通常可接受，但：
1. Python 仿真器按顺序求值，若条件有重叠可能产生与 Verilog 不一致的行为；
2. 生成的代码可读性差，不利于综合工具推断完整 case；
3. 深层嵌套 FSM 极易在维护时引入多驱动隐患。

**用法（上下文管理器，推荐）**

```python
from rtlgen import StateTransition

@self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
def _fsm():
    with StateTransition(self.state) as st:
        st.next(WORK, when=self.state == IDLE)
        st.next(READ, when=self.state == WORK)
        st.next(DONE, when=self.state == READ)
    # __exit__ 自动调用 commit()
```

**用法（手动 commit）**

```python
@self.seq(self.clk, self.rst_n)
def _fsm():
    st = StateTransition(self.state)
    st.next(WORK, when=self.state == IDLE)
    st.next(READ, when=self.state == WORK)
    st.next(DONE, when=self.state == READ)
    st.commit()   # 必须在 @seq / @comb 块内调用
```

生成的 Verilog 等价于：

```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        state <= IDLE;
    else
        state <= (state == IDLE) ? WORK :
                 (state == WORK) ? READ :
                 (state == READ) ? DONE : state;  // default_hold=True 保持原值
end
```

**参数说明**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `state_reg` | — | 目标状态寄存器（`Reg` 类型） |
| `default_hold` | `True` | 无任何条件命中时是否保持原值；`False` 时默认回 0 |

**优先级规则**：先注册的 `st.next()` 优先级更高。如果多个条件可能同时满足，排在前面的会生效。

**完整示例：带使能的 3 状态计数器**

```python
class CounterFSM(Module):
    def __init__(self):
        super().__init__("CounterFSM")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.en = Input(1, "en")
        self.state = Reg(2, "state")
        self.flag = Output(1, "flag")

        IDLE = 0; COUNT = 1; DONE = 2

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with StateTransition(self.state) as st:
                st.next(COUNT, when=(self.state == IDLE) & self.en)
                st.next(DONE,  when=(self.state == COUNT) & self.en)
                st.next(IDLE,  when=self.state == DONE)

        @self.comb
        def _out():
            self.flag <<= self.state == DONE
```

### 3.5 表达式辅助函数

| 函数 | 说明 |
|------|------|
| `Mux(cond, true_val, false_val)` | 二选一多路器。 |
| `Cat(a, b, ...)` | 位拼接 `{a, b}`。 |
| `Rep(sig, n)` | 位重复 `{sig, sig, ...}`。 |
| `Const(value, width)` | 常数信号。 |
| `Split(signal, chunk_width)` | 将信号按 chunk_width 分段，返回从低位到高位的列表。 |
| `PadLeft(signal, target_width)` | 左侧补零到 target_width。 |
| `Select(signals, idx)` | 用信号索引从列表/Vector中选择元素（动态索引的替代方案）。 |

**`Select` 示例**：当索引是动态信号时，Python 列表不支持 `list[idx]`。使用 `Select` 替代：

```python
from rtlgen.logic import Select

# 从 8 个寄存器中按 idx 选择
data = Select(self.entry_data, self.selected_idx)

# 也支持 Vector
prs = Select(self.rename.prs1, self.issue_slot)
```

### 3.6 注释传递

```python
from rtlgen.logic import comment

comment("Top level: input registers")

@self.comb
def _logic():
    comment("Start of combination logic")
    self.c <<= self.a & self.b
    comment("End of combination logic")
```

生成：
```verilog
// Top level: input registers
always @(*) begin
    // Start of combination logic
    c = (a & b);
    // End of combination logic
end
```

**说明**：`comment()` 支持在模块顶层、`@comb` / `@seq` 块内、`If` / `Switch` 分支内任意位置插入，多行字符串会自动拆分为多行 `//`。

---

## 4. 流水线引擎 (`rtlgen.pipeline`)

```python
from rtlgen import Pipeline, Input

pipe = Pipeline("AdderPipe", data_width=32)
pipe.clk = Input(1, "clk")
pipe.rst = Input(1, "rst")

@pipe.stage(0)
def fetch(ctx):
    tmp = ctx.local("tmp", 32)
    tmp <<= ctx.in_hs.data + 1
    ctx.out_hs.data <<= tmp
    ctx.out_hs.valid <<= ctx.in_hs.valid

@pipe.stage(1)
def exec_(ctx):
    ctx.out_hs.data <<= ctx.in_hs.data + 2
    ctx.out_hs.valid <<= ctx.in_hs.valid

pipe.build()
```

**自动生成**：
- 级间 `data/valid` 寄存器（仅在 `valid & ready` 时更新）
- `ready` 反向传播：`ready = ~next_valid | next_ready`
- 顶层握手端口：`in_hs_data/valid/ready`、`out_hs_data/valid/ready`

### 4.1 `ShiftReg` — 标准移位寄存器

```python
from rtlgen.pipeline import ShiftReg

self.delay = ShiftReg(128, 16, "delay_u")
self.instantiate(self.delay, "u_delay",
    port_map={
        "clk": self.clk, "rst_n": self.rst_n,
        "din": self.data_in, "dout": self.data_out
    })
```

- `depth=0`：wire-through（`dout <<= din`）
- `depth=1`：单级寄存器，1 拍延迟
- 异步低电平复位

### 4.2 `ValidPipe` — 带 valid 门控的流水寄存器

```python
from rtlgen.pipeline import ValidPipe

stage = ValidPipe(128, "stage_u")
self.instantiate(stage, "u_stage",
    port_map={
        "clk": self.clk, "rst_n": self.rst_n,
        "din": self.in_data, "valid_in": self.in_valid,
        "dout": self.out_data, "valid_out": self.out_valid
    })
```

仅在 `valid_in=1` 时采样 `din`，输出保持上次捕获值。适合 feed-forward 流水线（无反压）.

### 4.3 `DebugProbe` — 层次化信号探针

```python
from rtlgen.pipeline import DebugProbe

probe = DebugProbe(sim)
probe.get("o_valid")                          # 顶层信号
probe.get("qm2", path="u_r0")                # 子模块信号
path, subsim = probe.find_subsim("u_r0")      # 模糊查找子模块
probe.print_all(["valid_in","out_valid"], path_prefix="u_r0")
```

---

## 5. 总线协议 (`rtlgen.protocols`)

### 5.1 Bundle 基类

```python
from rtlgen import Bundle, Input, Output

class MyBundle(Bundle):
    def __init__(self, name=""):
        super().__init__(name)
        self._add("req", Input(1), "in")
        self._add("ack", Output(1), "out")

master = MyBundle("m")
slave = master.flip()          # 方向反转
mapping = master.connect(slave) # Dict[Signal, Signal]
```

### 5.2 标准协议

| 类 | 构造函数示例 |
|----|--------------|
| `AXI4Stream` | `AXI4Stream(data_width=32, user_width=0, has_strb=False)` |
| `APB` | `APB(addr_width=32, data_width=32)` |
| `AXI4Lite` | `AXI4Lite(addr_width=32, data_width=32)` |
| `AXI4` | `AXI4(id_width=4, addr_width=32, data_width=32, user_width=0)` |
| `AHBLite` | `AHBLite(addr_width=32, data_width=32)` |
| `Wishbone` | `Wishbone(addr_width=32, data_width=32)` |

---

## 6. 标准组件库 (`rtlgen.lib`)

### 6.1 FSM（模块化状态机）

```python
from rtlgen import FSM, Module, Input

class TrafficLight(Module):
    def __init__(self):
        super().__init__("TrafficLight")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.timer_done = Input(1, "timer_done")

        fsm = FSM("RED", name="")
        fsm.add_output("red", width=1, default=0)
        fsm.add_output("yellow", width=1, default=0)
        fsm.add_output("green", width=1, default=0)

        @fsm.state("RED")
        def red(ctx):
            ctx.red = 1
            ctx.yellow = 0
            ctx.green = 0
            ctx.goto("GREEN", when=self.timer_done)

        @fsm.state("GREEN")
        def green(ctx):
            ctx.red = 0
            ctx.yellow = 0
            ctx.green = 1
            ctx.goto("YELLOW", when=self.timer_done)

        @fsm.state("YELLOW")
        def yellow(ctx):
            ctx.red = 0
            ctx.yellow = 1
            ctx.green = 0
            ctx.goto("RED", when=self.timer_done)

        fsm.build(self.clk, self.rst, parent=self)
```

**自动生成**：状态寄存器、次态组合逻辑、输出组合逻辑、时序更新块。

### 6.2 FIFO

```python
from rtlgen import SyncFIFO, AsyncFIFO

fifo = SyncFIFO(width=32, depth=16)
fifo.clk = Input(1, "clk")
fifo.rst = Input(1, "rst")
# 端口：din, wr_en, rd_en, dout, full, empty, count
```

### 6.3 Arbiter / Decoder / Encoder

```python
from rtlgen import RoundRobinArbiter, Decoder, PriorityEncoder

arb = RoundRobinArbiter(req_count=4)   # reqs[4] -> grants[4]
dec = Decoder(in_width=3)              # 3-to-8 译码器
enc = PriorityEncoder(in_width=8)      # 8-to-3 优先编码器
```

### 6.4 Barrel Shifter

```python
from rtlgen import BarrelShifter

shifter = BarrelShifter(width=32, direction="left_rotate")
# direction: "left" | "right" | "left_rotate" | "right_rotate"
```

### 6.5 LFSR

```python
from rtlgen import LFSR

lfsr = LFSR(width=16, taps=[16, 14, 13, 11], seed=0xACE1)
```

### 6.6 CRC

```python
from rtlgen import CRC

crc = CRC(data_width=8, poly_width=32, polynomial=0x04C11DB7)
```

### 6.7 Divider

```python
from rtlgen import Divider

div = Divider(dividend_width=32, divisor_width=32)
# 多周期恢复余数除法器，含 start / done / busy 握手信号
```

---

## 7. RAM 封装 (`rtlgen.ram`)

```python
from rtlgen import SinglePortRAM, SimpleDualPortRAM

spram = SinglePortRAM(width=32, depth=1024)
# 端口：clk, addr, din, dout, we, en
# 内部生成 mem[addr] 的 always 读写逻辑

sdpram = SimpleDualPortRAM(width=64, depth=512, init_file="data.hex")
# 端口：clk, wr_addr, rd_addr, din, dout, we, wr_en, rd_en
```

---

## 8. 代码生成 (`rtlgen.codegen`)

```python
from rtlgen import VerilogEmitter

top = Counter(width=8)
emitter = VerilogEmitter()

# 单模块
print(emitter.emit(top))

# 整个设计（含子模块，按依赖顺序）
print(emitter.emit_design(top))

# 输出 SystemVerilog（always_comb / always_ff）
sv_emitter = VerilogEmitter(use_sv_always=True)
print(sv_emitter.emit(top))
```

### 8.1 Verilog Linter 与自动修复 (`emit_with_lint`)

`VerilogEmitter` 支持在生成 Verilog 后自动运行轻量 Linter，并可对常见问题执行 auto-fix：

```python
from rtlgen import VerilogEmitter

top = Counter(width=8)
emitter = VerilogEmitter()

# 生成并 lint，auto_fix=True 会自动修复可修复的问题
text, lint_result = emitter.emit_with_lint(top, auto_fix=True)

for issue in lint_result.issues:
    print(issue.rule, issue.severity, issue.message)
```

**支持规则**：

| 规则 | 说明 | auto_fix 行为 |
|------|------|---------------|
| `default_nettype` | 检查文件顶部是否包含 `` `default_nettype none `` | 在文件首行插入 |
| `implicit_wire` | assign 或子模块端口连线中使用了未声明的 wire | 在模块内部插入 `logic` 声明 |
| `multi_driven` | 同一信号存在多个驱动源（assign + always 等） | 不可自动修复 |
| `unused_signal` | 声明后从未被使用或驱动的信号 | 不可自动修复 |
| `blocking_in_seq` | 时序 always 块中使用了阻塞赋值 `=` | 自动改为 `<=` |
| `latch_risk` | 组合 always 块中 `if` 无 `else`、`case` 无 `default`，或分支赋值不完整 | **在 always 块顶部插入信号的 default 赋值**（如 `sig = 1'b0;` 或 `sig = {WIDTH{1'b0}};`） |
| `width_mismatch` | assign 左右两侧位宽不一致 | 不可自动修复 |

**`latch_risk` 自动修复说明**：
- 当组合 `always @(*)` 中出现 `if` 分支缺少对应 `else` 赋值、或 `if`/`else` 两侧对同一信号赋值不完整时，linter 会在该 always 块的 `begin` 之后插入对应信号的默认初始化赋值。
- 对于 `case` 语句缺少 `default` 的情况，linter 会收集各 case 分支中被赋值的信号，并为没有在 always 顶部做过默认赋值的信号补全初始化。
- 自动修复采用 `1'b0`（1-bit）或 `{N{1'b0}}`（多 bit）作为默认值，从而消除综合器推断出 latch 的风险。

---

## 8.5 Verilog 导入 (`rtlgen.verilog_import`)

pyRTL 支持将已有的 Verilog / SystemVerilog RTL 代码库**逆向转换为 pyRTL Python API**，保持原有模块层次结构。

### 基本用法

```python
from rtlgen.verilog_import import VerilogImporter

importer = VerilogImporter("/path/to/verilog/repo")
importer.scan_repo()                          # 递归扫描 .v / .sv
importer.emit_repo("/output", package_name="imported")
```

输出目录结构：

```
/output/imported/
├── __init__.py
├── top_module.py
├── sub/
│   └── submodule.py
└── ...
```

### 支持的 Verilog 结构

| Verilog 结构 | Python API 映射 |
|-------------|----------------|
| `module` | `class ModuleName(Module)` |
| `input` / `output` | `self.xxx = Input/Output(width, "xxx")` |
| `wire` / `reg` / `logic` | `self.xxx = Wire/Reg(width, "xxx")` |
| `parameter` | `self.add_param("NAME", default)` |
| `localparam` | `self.add_localparam("NAME", value)` |
| `assign` | `self.xxx <<= expr` |
| `always @(*)` | `@self.comb` |
| `always @(posedge clk)` | `@self.seq(self.clk, ...)` |
| `if / else` | `with If(...) / Else()` |
| `case / default` | `with Switch(...) as sw: sw.case() / sw.default()` |
| `generate for` | `with ForGen("i", start, end) as i:` |
| `instance` | `self.instantiate(...)` |
| `memory array` | `Memory(width, depth)` / `Array(width, depth)` |

### 预处理兼容性增强

由于 pyverilog 解析器仅支持 Verilog-2001 子集，导入器内置了多层预处理：

1. **iverilog 预处理**：自动调用 `iverilog -E` 展开 `` `include `` / `` `define `` / `` `ifdef ``
2. **文本级修复**：
   - Windows CRLF (`\r\n`) → Unix LF
   - `for (integer j = ...)` → `for (j = ...)`
   - `'d10` / `'0` / `'1` → `32'd10` / `1'b0` / `1'b1`
   - `i++` / `i--` → `i = i + 1` / `i = i - 1`
3. **容错隔离**：单个文件解析失败不会中断整个目录的扫描

### 已知限制

- `assign {a, b, c} = d`（解构赋值）会生成 TODO 注释，需手动改为 `Split()`
- 参数化 `generate for`（如 `for (i = 0; i < PARAM; i++)`）回退为 Python `for` 循环，非综合但保留语义
- 函数 / 任务（`function` / `task`）生成注释，需手动重写
- 部分 SystemVerilog 高级特性（如 `interface`、`packed` / `unpacked` 结构体）不受支持

---

## 9. UVM Testbench 生成 (`rtlgen.uvmgen`)

`UVMEmitter` 能够基于任意 `Module` 的端口自动生成一套标准 UVM 验证平台骨架，包括：
- `*_if.sv` — SystemVerilog Interface（带 clocking block）
- `*_pkg.sv` — UVM package
- `*_transaction.sv` — `uvm_sequence_item`
- `*_sequencer.sv` / `*_sequence.sv`
- `*_driver.sv` / `*_monitor.sv` / `*_agent.sv`
- `*_scoreboard.sv` / `*_env.sv` / `*_test.sv`
- `tb_top.sv` — 顶层 testbench

### 9.1 基本用法

```python
from rtlgen import UVMEmitter
from counter import Counter

dut = Counter(width=8)
uvm = UVMEmitter()

# 生成完整 testbench 的所有文件
files = uvm.emit_full_testbench(dut)

for fname, content in files.items():
    print(f"// {fname}")
    print(content)
```

### 9.2 生成文件说明

| 文件 | 说明 |
|------|------|
| `Counter_if.sv` | 根据 DUT ports 自动生成 interface 与 clocking block。 |
| `Counter_transaction.sv` | 包含除 `clk/rst` 外的所有 ports 作为 `rand` 字段。 |
| `Counter_driver.sv` | 通过 `vif.cb` 驱动 inputs。 |
| `Counter_monitor.sv` | 通过 `vif.cb` 采样 outputs 并写入 analysis_port。 |
| `Counter_agent.sv` | 组装 sqr / drv / mon。 |
| `Counter_env.sv` | 组装 agent 与 scoreboard，并连接 analysis port。 |
| `Counter_test.sv` | 启动 `Counter_random_sequence` 的 base test。 |
| `tb_top.sv` | 实例化 DUT、interface、时钟生成、调用 `run_test()`。 |

### 9.3 关键约定

- **时钟检测**：默认查找 `clk` / `clock` / `aclk` / `pclk`，作为 interface 的时钟。
- **复位检测**：自动识别 `rst` / `reset` / `rst_n` / `aresetn`，在 `tb_top` 中单独声明为 `logic`。
- **Transaction 字段**：inputs 用于随机激励生成，outputs 用于 scoreboard 检查。

### 9.4 自定义测试序列

生成的 `*_sequence.sv` 中已包含一个 `random_sequence`，你可以直接继承或替换：

```systemverilog
class my_sequence extends Counter_base_sequence;
    `uvm_object_utils(my_sequence)

    virtual task body();
        Counter_transaction txn;
        // 自定义激励逻辑
        ...
    endtask
endclass
```

---

## 10. 子模块例化

### 10.1 显式例化

```python
sub = AndGate()
self.instantiate(
    sub,
    name="u_and",
    port_map={
        "a": self.x,
        "b": self.y,
        "z": self.z,
    },
)
```

### 10.2 隐式例化

```python
self.sub = AndGate()   # 按端口名自动匹配父模块中同名信号
```

**参数自动映射**：若子模块定义了 `Parameter`，且父模块中存在**同名属性**，隐式实例化时会自动生成参数传递。此外，还支持通过 `param_bindings` 传递**派生参数表达式**：

```python
class ParamAdder(Module):
    def __init__(self):
        super().__init__("ParamAdder")
        self.add_param("WIDTH", 8)
        self.add_localparam("OFFSET", 1)
        self.a = Input(self.WIDTH.value, "a")
        self.b = Input(self.WIDTH.value, "b")
        self.y = Output(self.WIDTH.value, "y")
        ...

class Top(Module):
    def __init__(self):
        super().__init__("Top")
        self.add_param("WIDTH", 16)
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.y = Output(16, "y")
        self.adder = ParamAdder()  # 自动生成 #(.WIDTH(WIDTH))
```

生成：
```verilog
ParamAdder #(.WIDTH(WIDTH)) adder (
    .a(a),
    .b(b)
);
```

**复杂表达式绑定**：

```python
class Top(Module):
    def __init__(self):
        super().__init__("Top")
        self.WIDTH = Parameter(16, "WIDTH")
        self.adder = ParamAdder(param_bindings={"WIDTH": self.WIDTH + 4})
```

生成 `#(.WIDTH((WIDTH + 3'd4)))`。

支持 `+`、`-`、`*` 以及 `==`、`!=`、`<`、`<=`、`>`、`>=` 运算符。

### 10.3 generate-for 批量例化

```python
with ForGen("i", 0, 4) as i:
    fa = FullAdder(name="FullAdder")
    self.instantiate(
        fa,
        name="fa",   # 固定字符串，Verilog 自动展开
        port_map={
            "a":    self.a[i],
            "b":    self.b[i],
            "cin":  self.carry[i],
            "sum":  self.sum[i],
            "cout": self.carry[i + 1],
        },
    )
```

**自动模块去重**：`emit_design()` 会自动检测结构（端口+参数）完全相同的模块定义，只输出一次。即使你不小心给每个实例传了不同的 `name="u_mul_0"`、`name="u_mul_1"`，生成器也会把它们合并为单个模块定义，避免 Verilog 文件膨胀。

生成：
```verilog
genvar i;
for (i = 0; i < 4; i = i + 1) begin : genblk
    FullAdder fa (
        .a(a[i]),
        .b(b[i]),
        .cin(carry[i]),
        .sum(sum[i]),
        .cout(carry[(i + 1'b1)])
    );
end
```

### 10.4 Generate-if

```python
from rtlgen.logic import GenIf, GenElse

with GenIf(self.USE_FIFO == 1):
    self.fifo = SyncFIFO(width=32, depth=16)
    with ForGen("i", 0, 4) as i:
        self.data[i] <<= self.fifo.dout[i]
with GenElse():
    with ForGen("i", 0, 4) as i:
        self.data[i] <<= Const(0, width=1)
```

生成：
```verilog
generate
    if ((USE_FIFO == 1'b1)) begin : genif
        genvar i;
        for (i = 0; i < 4; i = i + 1) begin : genblk
            assign data[i] = fifo_dout[i];
        end
    end else begin : genelse
        genvar i;
        for (i = 0; i < 4; i = i + 1) begin : genblk
            assign data[i] = 1'b0;
        end
    end
endgenerate
```

### 10.5 ForGen 在 always 块内

`ForGen` 也可以在 `@comb` 和 `@seq` 块中使用，此时会生成 `for (integer i = ...)` 语句（而非模块顶层的 `genvar`）：

```python
@self.comb
def _logic():
    with ForGen("i", 0, width) as i:
        self.y[i] <<= self.a[i] & self.b[i]

@self.seq(self.clk, self.rst)
def _seq():
    with ForGen("i", 0, width) as i:
        self.q[i] <<= self.d[i]
```

生成：
```verilog
always @(*) begin
    for (integer i = 0; i < 8; i = i + 1) begin
        y[i] = (a[i] & b[i]);
    end
end

always @(posedge clk or posedge rst) begin
    for (integer i = 0; i < 8; i = i + 1) begin
        q[i] <= d[i];
    end
end
```

---

## 11. 完整设计示例

```python
from rtlgen import (
    Module, Input, Output, Reg, Wire,
    Pipeline, AXI4Stream,
    SinglePortRAM, FSM, VerilogEmitter,
)
from rtlgen.logic import If, Else, ForGen

class MyTop(Module):
    def __init__(self):
        super().__init__("MyTop")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.data_in = Input(32, "data_in")
        self.valid_in = Input(1, "valid_in")
        self.data_out = Output(32, "data_out")
        self.valid_out = Output(1, "valid_out")

        # --- 异构流水线：用 Vector + Stage 寄存器手动搭建 ---
        A_w = Vector(48, 3, "s0_A", vtype=Wire)
        A_r = Vector(48, 3, "s1_A", vtype=Reg)

        @self.comb
        def _s0():
            parts = Split(self.data_in, 16)
            for i in range(3):
                A_w[i] <<= PadLeft(parts[i], 48)

        @self.seq(self.clk, self.rst)
        def _s0_reg():
            for i in range(3):
                A_r[i] <<= A_w[i]

        @self.comb
        def _s1():
            self.data_out <<= A_r[0] + A_r[1] + A_r[2]
            self.valid_out <<= self.valid_in

if __name__ == "__main__":
    top = MyTop()
    print(VerilogEmitter().emit(top))
```

---

## 12. UVM RAL 生成 (`rtlgen.regmodel` + `rtlgen.uvmgen`)

```python
from rtlgen import RegField, Register, RegBlock, UVMEmitter

ctrl = Register("ctrl", width=32, fields=[
    RegField("enable", width=1, access="RW", reset=0),
    RegField("mode",   width=3, access="RW", reset=0),
])

data = Register("data", width=32)  # 默认单字段

block = RegBlock("gpio", base_addr=0x4000_0000)
block.add_reg(ctrl, 0x00)
block.add_reg(data, 0x04)

uvm = UVMEmitter()
files = uvm.emit_ral(block, pkg_name="test_pkg")
```

生成内容包含：
- `gpio_ctrl_reg` / `gpio_data_reg`（`uvm_reg` 子类）
- `gpio_reg_block`（`uvm_reg_block` 子类，含 `default_map`）

---

## 13. cocotb 测试集成 (`rtlgen.cocotbgen`)

```python
from rtlgen import CocotbEmitter
from counter import Counter

dut = Counter(width=8)
cocotb = CocotbEmitter()
files = cocotb.emit_full_cocotb(dut, verilog_sources=["Counter.v"])
```

生成文件：
- `test_counter.py` — `@cocotb.test()` 异步函数，含 clock、reset、随机激励。
- `Makefile` — 基于 `cocotb` 的标准 Makefile 模板（默认 `SIM = icarus`）。

---

## 14. APB / AXI4-Lite VIP (`rtlgen.uvmvip`)

```python
from rtlgen import UVMVIPEmitter

vip = UVMVIPEmitter()
apb_files = vip.emit_apb_vip(addr_width=16, data_width=32)
axi_files = vip.emit_axi4lite_vip(addr_width=32, data_width=64)
```

APB VIP 包含：
- `apb_if.sv` — 带 clocking block / modport 的 APB interface。
- `apb_transaction.sv` — `addr`, `data`, `pwrite`, `pprot`, `pstrb`, `pready`, `pslverr`。
- `apb_driver.sv` — 实现 SETUP → ENABLE 状态机。
- `apb_monitor.sv` — 在 `penable & pready` 时采样并写入 `analysis_port`。
- `apb_agent.sv` / `sequencer` / `sequence`

AXI4-Lite VIP 包含：
- `axi4lite_if.sv` — 完整 AW/W/B/AR/R 通道 interface。
- `axi4lite_transaction.sv` — 统一读写事务（`write` 字段区分）。
- `axi4lite_driver.sv` — `do_write()` / `do_read()` 分别处理握手。
- `axi4lite_monitor.sv` — 独立监控写通道与读通道，组装完整事务。
- `axi4lite_agent.sv` / `sequencer` / `sequence`

**快捷入口**：也可直接通过 `UVMEmitter` 调用：

```python
uvm = UVMEmitter()
apb_files = uvm.emit_apb_vip()
axi_files = uvm.emit_axi4lite_vip()
```

---

## 15. SVA 断言生成 (`rtlgen.svagen`)

```python
from rtlgen import SVAEmitter

sva = SVAEmitter()
print(sva.emit_assertions(
    dut,
    custom_assertions=[
        ("handshake_stable", "valid & !ready |=> $stable(data)"),
    ]
))
```

生成内容：
- `bind DUT assertions_module (.*);`
- `module DUT_assertions (...)` 含自动推断的 `clk` / `rst`
- **复位断言**：`$rose(rst) |=> ##[1:10] !rst`
- **Handshake 断言**：自动检测 `valid/ready/data` 端口，生成 data stable / valid hold 属性
- **自定义断言**：用户传入的 `(name, expr)` 列表

---

## 16. Python 仿真后端 (`rtlgen.sim`)

pyRTL 内置了周期精确的 AST 解释器 `Simulator`，无需调用外部 Verilog 仿真器即可在 Python 中快速验证模块行为。

```python
from rtlgen import Simulator
from counter import Counter

dut = Counter(width=4)
sim = Simulator(dut)

sim.reset()           # 自动检测 rst/rst_n 并执行复位序列
sim.set("en", 1)
for i in range(10):
    sim.step()
    print(f"cycle {i}: count = {sim.get('count')}")
```

### 15.1 支持的仿真特性

| 特性 | 说明 |
|------|------|
| 组合逻辑 | `always @(*)` 块在 `step()` 前后自动评估 |
| 时序逻辑 | `always @(posedge clk)` 块在 `step()` 中收集 `next_state`，然后统一 commit |
| If / Else / Switch | 完整支持条件分支与 case 匹配 |
| ForGen | 在仿真器中直接展开为 Python `for` 循环 |
| Memory | `Memory` 对象可直接在 `Simulator` 中读写 |
| 复位 | `reset()` 自动检测高/低有效复位信号 |
| Trace | 内置 `table` / `vcd` 两种 trace 输出格式 |

### 15.2 仿真 API

```python
sim.set(name, value)        # 设置输入/信号值
sim.get(name)               # 读取信号当前值
sim.get_int(name)           # 读取并转为 int（X/Z 时返回 0）
sim.poke(name, value)       # set 的别名（兼容 Verilator/VCS 风格）
sim.peek(name)              # get 的别名
sim.step(do_trace=True)     # 推进一个时钟周期
sim.run(cycles=100)         # 连续运行多个周期
sim.reset(rst="rst")        # 执行复位序列
sim.assert_eq(name, expected, msg="optional")  # 断言信号值
sim.dump_trace(fmt="table") # 打印表格形式 trace
sim.to_vcd(timescale="1ns") # 生成简易 VCD 字符串
```

### 16.3 多时钟域仿真

```python
from rtlgen import Simulator

sim = Simulator(dut, trace_signals=["count_a", "count_b"])
sim.reset()

# 只推进 clk_a 时钟域
sim.step(clk="clk_a")

# 只推进 clk_b 时钟域
sim.step(clk="clk_b")
```

### 16.4 X/Z 四态逻辑

```python
sim = Simulator(dut, use_xz=True)
```

启用后：
- 所有 **寄存器** 初始化值为 **X**（未初始化）
- **Memory** 单元初始化值为 **X**
- 运算遵循 4-state 传播规则（任何操作数含 X 则结果对应位为 X）

### 16.5 时间 / 延迟模型

```python
sim = Simulator(dut, clock_period_ns=10.0)
print(sim.now())          # 0.0
sim.advance_time(5.0)     # 仅推进时间，不触发边沿
print(sim.now())          # 5.0
sim.step()                # 推进 10ns，触发 seq 块
print(sim.now())          # 15.0
```

Trace 输出与 VCD 均使用真实时间戳。

### 16.6 Python ↔ iverilog 协同仿真 (`rtlgen.cosim`)

`CosimRunner` 对同一个 pyRTL Module，同时在 Python `Simulator` 和 `iverilog` 中执行完全相同的测试向量，并逐 cycle 对比输出 trace，确保 Python 仿真器与 Verilog 语义一致。

```python
from rtlgen.cosim import CosimRunner

vectors = [
    {"a": 0b1010, "b": 0b1100},
    {"a": 0b1111, "b": 0b0000},
]
CosimRunner(CondGen(), vectors, mode="comb").run(verbose=True)
```

当前所有 `tests/test_cosim_examples.py` 回归测试均已通过（9/9），覆盖组合逻辑、时序逻辑、generate-if、参数自动映射、Memory 等场景。

### 16.7 Memory 仿真示例

```python
from rtlgen import Simulator, Module, Input, Output, Memory

class SimpleRAM(Module):
    def __init__(self):
        super().__init__("SimpleRAM")
        self.clk = Input(1, "clk")
        self.addr = Input(4, "addr")
        self.din = Input(8, "din")
        self.we = Input(1, "we")
        self.dout = Output(8, "dout")
        self.mem = Memory(8, 16, "ram_mem")
        self.add_memory(self.mem, "ram_mem")
        # ... 读写逻辑 ...

ram = SimpleRAM()
sim = Simulator(ram, trace_signals=["addr", "din", "we", "dout"])
sim.reset()
sim.set("we", 1)
sim.set("addr", 0)
sim.set("din", 0xAB)
sim.step()
sim.set("we", 0)
sim.set("addr", 0)
sim.step()
print(sim.get("dout"))  # 0xAB
sim.dump_trace(fmt="table")
```

---

## 17. pyUVM 原生 Python UVM 框架 (`rtlgen.pyuvm` + `rtlgen.pyuvm_sim` + `rtlgen.pyuvmgen`)

pyRTL 内置了一套**原生 Python UVM 框架**，具备双重能力：

1. **Python 侧实时仿真**：通过 `rtlgen.pyuvm_sim.run_test()` 在 Python 中直接运行完整的 UVM 测试平台（含 component tree、sequence、TLM、phase、objection、virtual interface），底层驱动 `rtlgen.sim.Simulator`。
2. **一键生成 SV/UVM**：通过 `rtlgen.pyuvmgen.UVMEmitter` 将同一套 Python 代码转译为原生 SystemVerilog/UVM，交付给 VCS/Questa/Xcelium。

这意味着你可以**在 Python 里快速调试 UVM 平台逻辑**，确认无误后直接导出 SV，无需手写重复代码。

### 17.1 核心类与辅助宏

```python
from rtlgen.pyuvm import (
    UVMComponent, UVMSequenceItem, UVMSequence, UVMVirtualSequence,
    UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMScoreboard, UVMTest,
    UVMSequencer, UVMConfigDB,
    uvm_fatal, uvm_info, uvm_warning, assert_eq,
    create, repeat, delay, start_item, finish_item,
    randomize, uvm_do, uvm_do_with, Coverage,
    UVMBlockingGetPort, UVMBlockingPutPort,
    UVMNonBlockingGetPort, UVMNonBlockingPutPort,
    UVMBlockingPeekPort, UVMNonBlockingPeekPort,
    UVMAnalysisFIFO,
    UVMRegField, UVMReg, UVMRegBlock, UVMRegPredictor,
)
```

- `UVMComponent` — 基类，含 `build_phase`、`connect_phase`、`run_phase`、`report_phase`
- `UVMSequenceItem` — Transaction 基类，内置 `_fields` 声明与 Python `random` 随机化
- `UVMSequence` / `UVMVirtualSequence` — sequence 与虚拟 sequence（orchestration）
- `UVMDriver` / `UVMMonitor` / `UVMAgent` / `UVMEnv` / `UVMScoreboard` / `UVMTest` — 标准 UVM 组件
- `uvm_do(item)` / `uvm_do_with(item, constraints)` — 一键完成 `start_item` + `randomize` + `finish_item`
- `delay(cycles)` — Python 侧挂起协程，SV 侧映射为 `@vif.cb`
- `assert_eq(actual, expected, msg)` — 轻量级断言，Python 侧记录结果，SV 侧映射为 `assert`
- `Coverage(name)` — 功能覆盖率容器，支持 `define_bins` / `sample` / `get_coverage`
- `UVMConfigDB` — UVM 风格配置数据库，支持类型化存储与层级路径通配符
- `UVMRegField` / `UVMReg` / `UVMRegBlock` / `UVMRegPredictor` — RAL 基础框架

### 17.2 async/await 语法约定

因为 Python 侧需要真正的协程调度，`body()`、`run_phase()` 以及所有涉及时间推进的方法都需要声明为 `async def`：

```python
class CounterSeq(UVMSequence):
    async def body(self):
        for _ in repeat(self.num_transactions):
            txn = create(CounterTxn, "txn")
            await uvm_do(txn)   # 等价于 start_item + randomize + finish_item

class CounterDriver(UVMDriver):
    async def run_phase(self, phase):
        while True:
            self.req = await self.seq_item_port.get_next_item()
            await delay(1)
            self.vif.cb.en <= self.req.en
            self.seq_item_port.item_done()
```

生成 SV 时，生成器会自动去掉 `await` 关键字，并正确映射为 SV task 的阻塞调用。

### 17.3 Transaction 随机化

`UVMSequenceItem.randomize()` 已内置于 Python 侧，基于 `random.getrandbits(width)` 对每个 field 随机化：

```python
class CounterTxn(UVMSequenceItem):
    _fields = [
        ("en", 1),
        ("count", 8),
    ]

txn = create(CounterTxn, "txn")
txn.randomize()        # Python 侧真实随机化
randomize(txn)         # 同上（全局便捷函数）
```

### 17.4 `uvm_do` 与 `uvm_do_with`

```python
# 普通随机化发送
await uvm_do(txn)

# 带约束的随机化发送（Python dict → SV inline constraint）
await uvm_do_with(txn, {"en": 1, "count": "< 10"})
```

Python 侧 `uvm_do_with` 的工作流程：
1. 先调用 `txn.randomize()`
2. 用字典中的值覆盖对应字段（硬约束）
3. `start_item` → `finish_item`

生成的 SV 代码：
```systemverilog
`uvm_do(txn)
`uvm_do_with(txn, {en == 1; count < 10;})
```

### 17.5 Virtual Sequence 与嵌套 Sequence

`UVMVirtualSequence` 不直接发送 item，而是启动子 sequence：

```python
class CounterSubSeq(UVMSequence):
    num_transactions = 3
    async def body(self):
        for _ in repeat(self.num_transactions):
            txn = create(CounterTxn, "txn")
            await uvm_do_with(txn, {"en": 1})

class CounterVirtualSeq(UVMVirtualSequence):
    async def body(self):
        if self.p_sequencer is None:
            uvm_fatal("VSEQ", "p_sequencer is None")
        sub_seq = CounterSubSeq("sub_seq")
        await sub_seq.start(self.p_sequencer, parent_sequence=self)
        seq = CounterSeq("seq")
        await seq.start(self.p_sequencer, parent_sequence=self)
```

- `p_sequencer` 与 `starting_phase` 在 `start()` 时自动传递。
- 子 sequence 的 `pre_body()` / `body()` / `post_body()` 生命周期完整支持。
- Sequence 控制 API：`kill()`、`is_relevant()`、`wait_for_grant()`。

### 17.6 TLM 端口与 AnalysisFIFO

除标准的 `seq_item_port` / `analysis_port` 外，新增完整 TLM 端口族：

```python
from rtlgen.pyuvm import (
    UVMBlockingGetPort, UVMBlockingPutPort,
    UVMNonBlockingGetPort, UVMNonBlockingPutPort,
    UVMBlockingPeekPort, UVMNonBlockingPeekPort,
    UVMAnalysisFIFO,
)
```

**`UVMAnalysisFIFO`** 是带缓冲的 analysis 队列，典型用法：

```python
class CounterScoreboard(UVMScoreboard):
    def __init__(self, name, parent=None):
        super().__init__(name, parent, txn_type=CounterTxn)
        self.afifo = UVMAnalysisFIFO("afifo", maxsize=64)
        self.get_port = UVMBlockingGetPort("get_port")

    def build_phase(self, phase):
        self.afifo.connect_get_port(self.get_port)

    async def run_phase(self, phase):
        while True:
            txn = await self.get_port.get()
            # 处理 transaction ...
```

Environment 连接：
```python
class CounterEnv(UVMEnv):
    def connect_phase(self, phase):
        self.agent.mon.ap.connect(self.sb.afifo)
        self.agent.mon.ap.connect(self.predictor.exp)   # analysis_port 支持多播
```

### 17.7 Driver、Monitor、Agent 示例

```python
class CounterDriver(UVMDriver):
    def __init__(self, name, parent=None):
        super().__init__(name, parent, txn_type=CounterTxn)

    async def run_phase(self, phase):
        while True:
            self.req = await self.seq_item_port.get_next_item()
            await delay(1)
            self.vif.cb.en <= self.req.en
            self.seq_item_port.item_done()

class CounterMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            txn = create(CounterTxn, "txn")
            txn.en = int(self.vif.cb.en)
            txn.count = int(self.vif.cb.count)
            self.ap.write(txn)

class CounterAgent(UVMAgent):
    def build_phase(self, phase):
        self.sqr = UVMSequencer("sqr", self)
        self.drv = CounterDriver("drv", self)
        self.mon = CounterMonitor("mon", self)

    def connect_phase(self, phase):
        self.drv.seq_item_port.connect(self.sqr.seq_item_export)
```

### 17.8 Scoreboard、Env 与 Test

```python
class CounterScoreboard(UVMScoreboard):
    def __init__(self, name, parent=None):
        super().__init__(name, parent, txn_type=CounterTxn)
        self.expect_count = 0
        self.golden_count = 0
        self.cov = Coverage("en_cov")
        self.cov.define_bins([0, 1])

    def write(self, txn):
        self.expect_count += 1
        self.cov.sample(txn.en)
        uvm_info("SCB", f"Txn #{self.expect_count} en={txn.en} count={txn.count}", 0)
        if txn.en:
            self.golden_count += 1
        assert_eq(int(txn.count), self.golden_count, "count mismatch")

    def report_phase(self, phase):
        self.cov.report()

class CounterEnv(UVMEnv):
    def build_phase(self, phase):
        self.agent = CounterAgent("agent", self)
        self.sb = CounterScoreboard("sb", self)

    def connect_phase(self, phase):
        self.agent.mon.ap.connect(self.sb.afifo)

class CounterTest(UVMTest):
    def __init__(self, name, dut):
        super().__init__(name)
        self.dut = dut

    def build_phase(self, phase):
        self.env = CounterEnv("env", self)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        seq = CounterSeq("seq")
        await seq.start(self.env.agent.sqr)
        await delay(10)      # 留足时间让 monitor 处理完剩余事务
        phase.drop_objection(self)
```

- `assert_eq` 在 Python 侧自动记录 pass/fail，仿真结束后打印 `[CHECKER] total=... passed=... failed=...`
- `report_phase` 在所有 component 中递归调用，适合打印覆盖率、统计结果。

### 17.9 Config DB（`UVMConfigDB`）

支持 UVM 风格的类型化配置存储与层级路径通配符匹配：

```python
# 在 Env 或 Test 中设置
self.uvm_config_db_set("vif", sched.vif)
self.uvm_config_db_set("ral", self.ral)

# 在子 component 中获取
self.vif = self.uvm_config_db_get("vif")
self.ral = self.uvm_config_db_get("ral")
```

底层使用全局 `UVMConfigDB.set(cntxt, inst_name, field_name, value, val_type=None)` / `UVMConfigDB.get(...)`，支持 `inst_name="*"` 通配符。

### 17.10 RAL 基础框架

内置轻量级 Register Abstraction Layer：

```python
class CounterRegBlock(UVMRegBlock):
    def __init__(self, name="ral", parent=None):
        super().__init__(name, parent)
        ctrl = UVMReg("ctrl", width=8, reset=0)
        ctrl.add_field(UVMRegField("en", width=1, lsb_pos=0, access="RW", reset=0))
        self.add_reg(ctrl, offset=0x00)
```

- `UVMRegPredictor` 可连接 monitor 的 `analysis_port`，自动根据总线 transaction 更新寄存器 mirror 值。
- 生成的 SV 中，自定义 `UVMRegBlock` 子类会先生成占位 `uvm_component`，确保编译通过（完整 `uvm_reg_block` 生成待后续增强）。

### 17.11 Python 侧运行 UVM 仿真

无需生成 SV，直接在 Python 中执行完整 UVM 测试：

```python
from rtlgen.sim import Simulator
from rtlgen.pyuvm_sim import run_test
from counter import Counter

dut = Counter(width=8)
sim = Simulator(dut)
test = CounterTest("counter_test", dut)

run_test(test, sim, max_cycles=100)
```

`run_test()` 内部执行标准 UVM phase 流程：
1. **默认复位** — `rst=1` 2 cycles → `rst=0` 1 cycle
2. **build_phase** — 递归构建 component 树
3. **vif 绑定** — 通过 `cfg_db_set/get` 分发 virtual interface
4. **connect_phase** — 递归连接 TLM 端口
5. **run_phase** — 启动所有 `async def run_phase`，配合 Scheduler 推进 `Simulator.step()`
6. **report_phase** — 打印覆盖率与 checker 汇总

### 17.12 生成 SV/UVM 代码

同一套 Python 代码，通过 `PyUVMEmitter` 一键生成 SV：

```python
from rtlgen.pyuvmgen import UVMEmitter as PyUVMEmitter
from counter import Counter

test = CounterTest("counter_test", Counter(width=8))
files = PyUVMEmitter().emit(test, pkg_name="counter_test_pkg")

for fname, content in files.items():
    print(f"// {fname}")
    print(content)
```

`emit()` 会自动生成以下文件：
- `{pkg}.sv` — UVM package
- `{Txn}.sv` — transaction 类
- `{base}_agent.sv` / `{base}_driver.sv` / `{base}_monitor.sv` / `{base}_scoreboard.sv`
- `{base}_env.sv` / `{base}_seq.sv` / `{base}_test.sv`
- `{DUT}_if.sv` — 从 DUT 端口推导的 interface（含 clocking block）
- `tb_top.sv` — top module，含 DUT 实例化、interface 连接、时钟生成与 `run_test`

生成器会基于 AST 自动完成：
- `type_id::create` 转换
- `repeat(n)` / `forever` / `delay` / `vif.cb` 映射
- `await` 关键字去除，保留阻塞 task 调用
- `uvm_do` / `uvm_do_with` → `` `uvm_do `` / `` `uvm_do_with `` macro
- `assert_eq` → `assert (...) else `uvm_error(...)`
- `self.xxx` 成员字段推断（含 `UVMAnalysisFIFO`、TLM port、RAL 类）
- 本地变量（如 `txn`、`seq`、`req`、`rsp`）的类型推断与声明
- transaction 类型在 `uvm_driver #(T)` / `uvm_sequence #(T)` / `uvm_analysis_imp` / `write()` 中的自动解析
- 生成的每个 `.sv` 文件自动包含标准头注释

**`vif.cb` 使用注意事项**：
- Driver/Monitor 中通过 `self.vif.cb.xxx` 访问的信号，默认会从 DUT 的 `input`/`output` 端口自动推导。
- 如果在 Python 代码中引用了 DUT 没有的额外信号（如 `self.vif.cb.cmd_valid`），生成器会自动将这些信号补充声明到 interface 中，并加入 clocking block（方向为 `inout`）。
- 为避免不必要的手动映射，建议优先复用 DUT 现有端口名称。

### 17.13 断言与注释集成

pyUVM 生成器已经自动为每个输出文件插入标准头注释。若需要额外 SVA 断言，可继续使用 `SVAEmitter`：

```python
from rtlgen import SVAEmitter

emitter = SVAEmitter()
sva = emitter.emit_assertions(
    dut,
    assertion_name="my_assertions",
    custom_assertions=[
        ("prac_en_low", "(!prac_en) |-> (ck_en_nacu == 1'b0)"),
    ],
)
```

---

## 18. 逻辑综合 (`rtlgen.blifgen` + `rtlgen.synth`)

pyRTL 内置了从 RTL IR 到门级网表的完整综合链路：

1. **BLIF 生成** — `BLIFEmitter` 将 `Module` AST 展开为 Berkeley Logic Interchange Format（单比特网表）
2. **ABC 调用** — `ABCSynthesizer` 自动调用 Berkeley ABC 进行逻辑优化与工艺映射
3. ** Liberty 读取** — 支持标准 `.lib` 工艺库（如 `gf65.lib`）
4. **结果解析** — 自动提取面积、延迟、门数、逻辑深度

### 18.1 生成 BLIF

```python
from rtlgen import BLIFEmitter
from examples.decoder_8b10b_comb import Decoder8b10bComb

dut = Decoder8b10bComb()
blif = BLIFEmitter().emit(dut)

with open("decoder_8b10b_comb.blif", "w") as f:
    f.write(blif)
```

`BLIFEmitter` 支持的功能：
- 所有信号按位展开（bit-blasting）
- 算术运算 `+` / `-` / 比较器 自动展开为加法器/减法器链
- `IfNode` / `SwitchNode` 自动转换为级联 2:1 MUX（`.names` 真值表）
- `Reg` 自动映射为 `.latch`（同步复位通过组合域 MUX 实现）

### 18.2 参数化算子生成

`BLIFEmitter` 支持根据 **时序/面积约束** 自动选择不同的算术算子实现。通过 `SynthConfig` 配置：

```python
from rtlgen import BLIFEmitter, SynthConfig, AdderStyle, MultiplierStyle

cfg = SynthConfig(
    adder=AdderStyle.KOGGE_STONE,        # 或 RCA / CLA / BRENT_KUNG
    multiplier=MultiplierStyle.WALLACE,  # 或 ARRAY / BOOTH
    cla_block_size=4,
)
emitter = BLIFEmitter(config=cfg)
blif = emitter.emit(dut)
```

#### 支持的算子实现

| 算子 | 可选实现 | 特点 |
|------|----------|------|
| **加法器 (`+`)** | `RCA` | Ripple Carry Adder，面积小，延迟 O(n) |
| | `CLA` | Carry Lookahead Adder，4-bit 成组前瞻，面积-延迟折中 |
| | `KOGGE_STONE` | 完全并行前缀树，深度 log₂(n)，高速 |
| | `BRENT_KUNG` | 稀疏前缀树，节点更少，延迟略大 |
| **乘法器 (`*`)** | `ARRAY` | 阵列乘法器，结构规则 |
| | `BOOTH` | Radix-2 Booth 编码，减少部分积 |
| | `WALLACE` | Wallace 树压缩 + 快速加法器，高性能 |
| **除法器 (`/`)** | `RESTORING` | 组合恢复式阵列除法器 |

> **注意**：所有算子都会在 BLIF 中被展开为 `.names` 真值表（AIG  primitives）。进入 ABC 后，`strash` / `rewrite` / `refactor` 会基于 AIG 做结构无关优化，因此不同风格在 ABC 优化后差异会被显著缩小。参数化生成的价值在于**给综合工具提供更优质的初始结构**（例如前缀加法器比 RCA 更容易被保留短路径）。

### 18.3 调用 ABC 进行综合

```python
from rtlgen import ABCSynthesizer, WireLoadModel

synth = ABCSynthesizer(abc_path="~/.local/bin/abc")

result = synth.run(
    input_blif="decoder_8b10b_comb.blif",
    liberty="gf65.lib",          # 工艺库
    output_verilog="mapped.v",   # 映射后的 Verilog
    wlm=WireLoadModel(slope=0.05, intercept=0.01),
)

print(f"Area : {result.area}")    # 2804.18
print(f"Delay: {result.delay}")   # 3460.39
print(f"Gates: {result.gates}")   # 377
print(f"Depth: {result.depth}")   # 36
```

默认 ABC 脚本流程：
```
read_blif → strash → resyn2 → read_lib → map → topo → print_stats → write_verilog
```

如果系统中未找到 ABC 可执行文件，`ABCSynthesizer` 会自动生成 `run_abc.sh` 脚本，方便用户手动执行。

### 18.4 时序逻辑综合示例

**带寄存器的模块同样可以直接综合**。以原始的 `examples/decoder_8b10b.py`（含 22 个 pipeline registers）为例：

```bash
python3 tests/test_synth_decoder_8b10b_seq_demo.py
```

输出示例：
```
.latch count: 22
Area  : 3023.21
Delay : 3571.6
Gates : 407
Depth : 37
```

因为 `gf65.lib` 中**没有可用的触发器/锁存器标准单元**（8 个 cell 里有 1 个 sequential 被 ABC reader 跳过），所以 `.latch` 在 mapped Verilog 中被保留为 `always @(posedge clock)` 形式的 behavioral registers，而组合逻辑部分已经被成功映射到 `gf65.lib` 的 NAND/NOR/AOI 等单元上。

如果你换一个包含 DFF/Latch 的完整工艺库，`.latch` 会被完全映射成具体的触发器实例。

### 18.5 组合逻辑专用示例

如果你只需要分析纯组合逻辑的面积/延迟，可以使用无时序版本：

- **8b10b Decoder（组合版）**
  ```bash
  python3 tests/test_synth_decoder_8b10b_demo.py
  ```
  输出：
  ```
  Area  : 2804.18
  Delay : 3460.39
  Gates : 377
  Depth : 36
  ```

- **SHA3-256 Keccak 单轮（组合版）**
  ```bash
  python3 tests/test_synth_sha3_round_demo.py
  ```
  输出：
  ```
  Area  : 191196.8
  Delay : 1443.02
  Gates : 25937
  Depth : 15
  ```

### 18.6 CPython 3.12 Switch 编译器 Bug 说明

在 CPython 3.12 中存在一个已确认的字节码编译器 bug（[cpython#109093](https://github.com/python/cpython/issues/109093)）：当同一个 `@self.comb` 块中连续出现多个 `with Switch(...) as sw:` 且内部包含 `for` 循环 + `sw.default()` 时，第二个 `Switch` 的 `.default()` 可能被错误绑定到第一个 `Switch` 对象，导致生成的 BLIF 出现组合循环。

**规避方案**：
- 对于纯组合查表逻辑，可直接手动构造 `SwitchNode` AST 节点（如 `decoder_8b10b_comb.py` 所示）
- 或将多个 `Switch` 拆分到不同的 `@self.comb` 块中

---

*Generated for rtlgen project.*

---

## 19. Skills 设计参考目录

`skills/` 目录按硬件设计领域分类，收集可复用的 rtlgen 模块、教程和领域特定设计。

```
skills/
├── skills.md                          # 总索引导航
├── fundamentals/                      # 基础模块 + 教程
│   ├── lib/                           # 标准组件库（FSM、FIFO、Arbiter 等）
│   ├── tutorials/                     # 入门示例
│   └── pipeline/                      # 流水线原语（ShiftReg、ValidPipe、DebugProbe）
├── arithmetic/                        # 算术单元
│   ├── multipliers/                   # KO 树乘法器、Montgomery 模乘
│   ├── sha3/                          # SHA3-256 / Keccak
│   └── fp8/                           # FP8 ALU
├── cryptography/                      # 加解密
│   └── chacha20/                      # ChaCha20 流密码
├── codec/                             # 编解码
│   └── 8b10b/                         # 8b/10b 线码
├── control/                           # 控制逻辑
│   └── fsm/                           # FSM、计数器
├── verification/                      # 验证
│   └── debug/                         # DebugProbe 使用示例
├── synthesis/                         # 综合脚本（ABCSynthesizer）
├── memory-storage/                    # 存储控制（预留）
├── video/                             # Video（预留）
├── image/                             # 图像（预留）
├── gpgpu/                             # GPGPU（预留）
├── cpu/                               # CPU（预留）
├── npu/                               # NPU 神经网络加速器
├── accelerators/                      # 加速器（预留）
└── physical-design/                   # 前后端协同设计（预留）
```

每个子目录包含：
- `SKILL.md` — 该领域的设计规范、关键技术和使用指南
- `.py` 源码文件 — 可直接运行/仿真/综合的参考实现

---

## 附录 A：ChaCha20 全流水线设计示例

以下示例展示了如何使用 `Array`、`Submodule instantiate`、`ForGen`、异步低电平复位以及握手信号，构建一个符合人类工程师风格的 20 轮 ChaCha20 流密码核。

```python
#!/usr/bin/env python3
"""
Fully pipelined ChaCha20 stream cipher core.

Architecture:
- Quarter-round is a pure combinational submodule (human-engineer style).
- Each round is a 2-stage pipeline module (column + diagonal) with handshaking.
- 20 rounds are cascaded.
- Stage 0 (init) builds the initial 512-bit matrix and drives the first round.
- Stage 21 (final) adds init_state and XORs with din.

Target: 12nm @ 1GHz.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import Const, Cat, Mux, Split, If, Else, ForGen

# ---------------------------------------------------------------------------
# Quarter-round: pure combinational block
# ---------------------------------------------------------------------------
class Chacha20QuarterRound(Module):
    """Single ChaCha quarter-round (steps 1-12), combinational."""

    def __init__(self):
        super().__init__("chacha20rng_quarterround")
        self.ai = Input(32, "ai")
        self.bi = Input(32, "bi")
        self.ci = Input(32, "ci")
        self.di = Input(32, "di")
        self.a = Output(32, "a")
        self.b = Output(32, "b")
        self.c = Output(32, "c")
        self.d = Output(32, "d")

        self.step1 = Wire(32, "step1")
        self.step2 = Wire(32, "step2")
        self.step3 = Wire(32, "step3")
        self.step4 = Wire(32, "step4")
        self.step5 = Wire(32, "step5")
        self.step6 = Wire(32, "step6")
        self.step7 = Wire(32, "step7")
        self.step8 = Wire(32, "step8")
        self.step9 = Wire(32, "step9")
        self.step10 = Wire(32, "step10")
        self.step11 = Wire(32, "step11")
        self.step12 = Wire(32, "step12")

        @self.comb
        def _qr_comb():
            s1 = self.step1
            s2 = self.step2
            s3 = self.step3
            s4 = self.step4
            s5 = self.step5
            s6 = self.step6
            s7 = self.step7
            s8 = self.step8
            s9 = self.step9
            s10 = self.step10
            s11 = self.step11
            s12 = self.step12

            s1 <<= self.ai + self.bi
            s2 <<= self.di ^ s1
            s3 <<= Cat(s2[15:0], s2[31:16])
            s4 <<= self.ci + s3
            s5 <<= self.bi ^ s4
            s6 <<= Cat(s5[19:0], s5[31:20])
            s7 <<= s1 + s6
            s8 <<= s3 ^ s7
            s9 <<= Cat(s8[23:0], s8[31:24])
            s10 <<= s9 + s4
            s11 <<= s10 ^ s6
            s12 <<= Cat(s11[24:0], s11[31:25])

            self.a <<= s7
            self.b <<= s12
            self.c <<= s10
            self.d <<= s9


# ---------------------------------------------------------------------------
# Round: 2-stage pipeline with handshaking
# ---------------------------------------------------------------------------
class Chacha20Round(Module):
    """One ChaCha round = column round + diagonal round (2 pipeline stages)."""

    def __init__(self):
        super().__init__("chacha20rng_round")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.xin = Input(512, "xin")
        self.xout = Output(512, "xout")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.init_state_in = Input(512, "init_state_in")
        self.init_state_out = Output(512, "init_state_out")

        # Decompose xin into 16 words
        self.x = Array(32, 16, "x", vtype=Wire)

        # First stage outputs
        self.t_out = Array(32, 16, "t_out", vtype=Wire)
        self.t_out_reg = Array(32, 16, "t_out_reg", vtype=Reg)
        self.stage1_valid = Reg(1, "stage1_valid")
        self.init_state_stage1 = Reg(512, "init_state_stage1")

        # Second stage outputs
        self.xd = Array(32, 16, "xd", vtype=Wire)
        self.xo = Array(32, 16, "xo", vtype=Wire)
        self.xout_t = Reg(512, "xout_t")

        # xin decomposition (unrolled to 16 simple assigns)
        @self.comb
        def _decompose_xin():
            for i in range(16):
                self.x[i] <<= self.xin[i * 32 + 31 : i * 32]

        # xd decomposition (generate for)
        with ForGen("idx", 0, 16) as idx:
            self.xd[idx] <<= self.t_out_reg[idx]

        # Quarter-round instances (stage 1: column) — generate for
        qr = Chacha20QuarterRound()
        with ForGen("idx", 0, 4) as idx:
            self.instantiate(
                qr,
                "u_qr",
                port_map={
                    "ai": self.x[idx],
                    "bi": self.x[idx + 4],
                    "ci": self.x[idx + 8],
                    "di": self.x[idx + 12],
                    "a": self.t_out[idx],
                    "b": self.t_out[idx + 4],
                    "c": self.t_out[idx + 8],
                    "d": self.t_out[idx + 12],
                },
            )

        # Quarter-round instances (stage 2: diagonal)
        for q, (a_idx, b_idx, c_idx, d_idx) in enumerate([(0, 5, 10, 15), (1, 6, 11, 12), (2, 7, 8, 13), (3, 4, 9, 14)]):
            self.instantiate(
                qr,
                f"u_qr_{q+5}",
                port_map={
                    "ai": self.xd[a_idx],
                    "bi": self.xd[b_idx],
                    "ci": self.xd[c_idx],
                    "di": self.xd[d_idx],
                    "a": self.xo[a_idx],
                    "b": self.xo[b_idx],
                    "c": self.xo[c_idx],
                    "d": self.xo[d_idx],
                },
            )

        # Handshake
        @self.comb
        def _round_comb():
            self.i_ready <<= self.o_ready
            self.xout <<= self.xout_t

        # Stage 1 sequential (column round result -> register)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _stage1_seq():
            with If(self.rst_n == 0):
                for i in range(16):
                    self.t_out_reg[i] <<= Const(0, 32)
                self.init_state_stage1 <<= Const(0, 512)
            with Else():
                with If(self.i_valid & self.i_ready):
                    for i in range(16):
                        self.t_out_reg[i] <<= self.t_out[i]
                    self.init_state_stage1 <<= self.init_state_in

        # Stage 2 sequential (diagonal round result -> register)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _stage2_seq():
            with If(self.rst_n == 0):
                self.xout_t <<= Const(0, 512)
                self.init_state_out <<= Const(0, 512)
            with Else():
                with If(self.stage1_valid & self.o_ready):
                    self.xout_t <<= Cat(*reversed([self.xo[i] for i in range(16)]))
                    self.init_state_out <<= self.init_state_stage1

        # Valid pipeline
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _valid_seq1():
            with If(self.rst_n == 0):
                self.stage1_valid <<= Const(0, 1)
            with Else():
                with If(self.o_ready):
                    self.stage1_valid <<= self.i_valid

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _valid_seq2():
            with If(self.rst_n == 0):
                self.o_valid <<= Const(0, 1)
            with Else():
                with If(self.o_ready):
                    self.o_valid <<= self.stage1_valid


# ---------------------------------------------------------------------------
# Core: cascade 20 rounds
# ---------------------------------------------------------------------------
class Chacha20CorePipe(Module):
    """Fully pipelined ChaCha20 core (20 rounds)."""

    def __init__(self, name="Chacha20CorePipe"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.seed = Input(256, "seed")
        self.stream_id = Input(64, "stream_id")
        self.counter = Input(64, "counter")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.o_ready = Input(1, "o_ready")

        self.state = Output(512, "state")
        self.o_valid = Output(1, "o_valid")

        NUM_ROUNDS = 20
        CONSTANTS = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]

        # Build initial state (combinational)
        self.init_state = Wire(512, "init_state")
        self.init_valid = Wire(1, "init_valid")

        @self.comb
        def _init_comb():
            key_words = Split(self.seed, 32)
            counter_words = Split(self.counter, 32)
            nonce_words = Split(self.stream_id, 32)
            words = []
            for i in range(16):
                if i < 4:
                    val = Const(CONSTANTS[i], 32)
                elif i < 12:
                    val = key_words[i - 4]
                elif i == 12:
                    val = counter_words[0]
                elif i == 13:
                    val = counter_words[1]
                elif i == 14:
                    val = nonce_words[0]
                else:
                    val = nonce_words[1]
                words.append(val)
            self.init_state <<= Cat(*reversed(words))
            self.init_valid <<= self.i_valid

        # Pipeline signals
        self.xin = Array(512, NUM_ROUNDS + 1, "xin", vtype=Wire)
        self.xout = Array(512, NUM_ROUNDS, "xout", vtype=Wire)
        self.stage_valid = Array(1, NUM_ROUNDS + 1, "stage_valid", vtype=Wire)
        self.stage_ready = Array(1, NUM_ROUNDS + 1, "stage_ready", vtype=Wire)
        self.init_state_stage = Array(512, NUM_ROUNDS + 1, "init_state_stage", vtype=Wire)

        # Input to first stage
        @self.comb
        def _pipeline_input():
            self.xin[0] <<= self.init_state
            self.stage_valid[0] <<= self.i_valid
            self.init_state_stage[0] <<= self.init_state

        # Instantiate 20 rounds via generate-for
        with ForGen("i", 0, NUM_ROUNDS) as i:
            rd = Chacha20Round()
            self.instantiate(
                rd,
                "inst",
                port_map={
                    "clk": self.clk,
                    "rst_n": self.rst_n,
                    "i_valid": self.stage_valid[i],
                    "i_ready": self.stage_ready[i],
                    "xin": self.xin[i],
                    "xout": self.xout[i],
                    "o_valid": self.stage_valid[i + 1],
                    "o_ready": self.stage_ready[i + 1],
                    "init_state_in": self.init_state_stage[i],
                    "init_state_out": self.init_state_stage[i + 1],
                },
            )
            self.xin[i + 1] <<= self.xout[i]

        # Final stage: add init_state
        self.final_xout = Wire(512, "final_xout")
        self.final_init = Wire(512, "final_init")
        self.final_valid = Wire(1, "final_valid")

        @self.comb
        def _extract_final():
            self.final_xout <<= self.xout[NUM_ROUNDS - 1]
            self.final_init <<= self.init_state_stage[NUM_ROUNDS]
            self.final_valid <<= self.stage_valid[NUM_ROUNDS]

        self.final_state = Wire(512, "final_state")
        @self.comb
        def _final_comb():
            words = []
            for i in range(16):
                st_word = self.final_xout[i * 32 + 31 : i * 32]
                init_word = self.final_init[i * 32 + 31 : i * 32]
                words.append(st_word + init_word)
            self.final_state <<= Cat(*reversed(words))

        # Register outputs
        self.state_reg = Reg(512, "state_reg")
        self.vout_reg = Reg(1, "o_valid_reg")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _output_seq():
            with If(self.rst_n == 0):
                self.state_reg <<= Const(0, 512)
                self.vout_reg <<= Const(0, 1)
            with Else():
                self.state_reg <<= self.final_state
                self.vout_reg <<= self.final_valid

        @self.comb
        def _output_assign():
            self.state <<= self.state_reg
            self.o_valid <<= self.vout_reg
            self.i_ready <<= self.stage_ready[0]
            self.stage_ready[NUM_ROUNDS] <<= self.o_ready


# ---------------------------------------------------------------------------
# Top-level wrapper
# ---------------------------------------------------------------------------
class chacha20rng(Module):
    def __init__(self, name="chacha20rng"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.seed = Input(256, "seed")
        self.counter = Input(64, "counter")
        self.stream_id = Input(64, "stream_id")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.state = Output(512, "state")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")

        u_core = Chacha20CorePipe("u_core")
        self.instantiate(
            u_core,
            "u_core",
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "seed": self.seed,
                "stream_id": self.stream_id,
                "counter": self.counter,
                "i_valid": self.i_valid,
                "i_ready": self.i_ready,
                "o_ready": self.o_ready,
                "state": self.state,
                "o_valid": self.o_valid,
            },
        )


# ---------------------------------------------------------------------------
# Generate Verilog when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from rtlgen import VerilogEmitter

    top = chacha20rng()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
```

*Generated for rtlgen project.*

## 附录 B：FP8 (E5M2) 全流水线 ALU

以下示例展示了一个支持加、减、乘、比较、最小/最大值的 3 级流水线 FP8 ALU，包含 `valid/ready` 握手、异步低电平复位以及完整的 NaN/Inf/Zero 异常处理。

```python
#!/usr/bin/env python3
"""
Fully pipelined FP8 (E5M2) ALU.

Supported operations (3-bit op):
  000 = add
  001 = sub
  010 = mul
  011 = min
  100 = max
  101 = cmp_lt
  110 = cmp_eq

Pipeline: 3 stages with valid/ready handshaking.
  Stage 1: Unpack & Align
  Stage 2: Compute (add/sub/mul/cmp)
  Stage 3: Normalize, Round & Pack

Notes:
- Subnormals are handled (exp=0, hidden=0).
- NaN propagation follows simplified rules (any NaN input -> canonical NaN output).
- Rounding is round-half-up for simplicity.
- Overflow -> inf, underflow -> zero.
"""

from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import Const, Cat, Mux, If, Else

BIAS = 15
EXP_WIDTH = 5
MANT_WIDTH = 2
# internal mantissa = hidden + explicit = 3 bits
MAN_FULL_W = 3
# guard bits for add/sub = 3 (GRS)
ADD_GUARD = 3
ADD_PATH_W = MAN_FULL_W + ADD_GUARD  # 6
# add/sub signed width: 6-bit unsigned max 63, signed 8-bit covers [-128,127]
ADD_SIGNED_W = 8


class FP8ALU(Module):
    def __init__(self, name="fp8e5m2_alu"):
        super().__init__(name)

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")

        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.op = Input(3, "op")

        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.result = Output(8, "result")
        self.flags = Output(4, "flags")  # {NV, OF, UF, NX}

        # ------------------------------------------------------------------
        # Stage 1: Unpack wires
        # ------------------------------------------------------------------
        self.a_sign = Wire(1, "a_sign")
        self.a_exp = Wire(EXP_WIDTH, "a_exp")
        self.a_mant = Wire(MANT_WIDTH, "a_mant")
        self.a_hidden = Wire(1, "a_hidden")
        self.a_mant_full = Wire(MAN_FULL_W, "a_mant_full")
        self.a_is_nan = Wire(1, "a_is_nan")
        self.a_is_inf = Wire(1, "a_is_inf")
        self.a_is_zero = Wire(1, "a_is_zero")
        self.a_mag = Wire(EXP_WIDTH + MANT_WIDTH, "a_mag")

        self.b_sign = Wire(1, "b_sign")
        self.b_exp = Wire(EXP_WIDTH, "b_exp")
        self.b_mant = Wire(MANT_WIDTH, "b_mant")
        self.b_hidden = Wire(1, "b_hidden")
        self.b_mant_full = Wire(MAN_FULL_W, "b_mant_full")
        self.b_is_nan = Wire(1, "b_is_nan")
        self.b_is_inf = Wire(1, "b_is_inf")
        self.b_is_zero = Wire(1, "b_is_zero")
        self.b_mag = Wire(EXP_WIDTH + MANT_WIDTH, "b_mag")

        @self.comb
        def _s1_unpack():
            self.a_sign <<= self.a[7]
            self.a_exp <<= self.a[6:2]
            self.a_mant <<= self.a[1:0]
            self.a_hidden <<= Mux(self.a_exp == 0, 0, 1)
            self.a_mant_full <<= Cat(self.a_hidden, self.a_mant)
            self.a_is_nan <<= (self.a_exp == 31) & (self.a_mant != 0)
            self.a_is_inf <<= (self.a_exp == 31) & (self.a_mant == 0)
            self.a_is_zero <<= (self.a_exp == 0) & (self.a_mant == 0)
            self.a_mag <<= Cat(self.a_exp, self.a_mant)

            self.b_sign <<= self.b[7]
            self.b_exp <<= self.b[6:2]
            self.b_mant <<= self.b[1:0]
            self.b_hidden <<= Mux(self.b_exp == 0, 0, 1)
            self.b_mant_full <<= Cat(self.b_hidden, self.b_mant)
            self.b_is_nan <<= (self.b_exp == 31) & (self.b_mant != 0)
            self.b_is_inf <<= (self.b_exp == 31) & (self.b_mant == 0)
            self.b_is_zero <<= (self.b_exp == 0) & (self.b_mant == 0)
            self.b_mag <<= Cat(self.b_exp, self.b_mant)

        # ------------------------------------------------------------------
        # Stage 1 -> Stage 2 registers
        # ------------------------------------------------------------------
        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a_sign = Reg(1, "s1_a_sign")
        self.s1_a_exp = Reg(EXP_WIDTH, "s1_a_exp")
        self.s1_a_mant_full = Reg(MAN_FULL_W, "s1_a_mant_full")
        self.s1_a_is_nan = Reg(1, "s1_a_is_nan")
        self.s1_a_is_inf = Reg(1, "s1_a_is_inf")
        self.s1_a_is_zero = Reg(1, "s1_a_is_zero")
        self.s1_a_mag = Reg(EXP_WIDTH + MANT_WIDTH, "s1_a_mag")

        self.s1_b_sign = Reg(1, "s1_b_sign")
        self.s1_b_exp = Reg(EXP_WIDTH, "s1_b_exp")
        self.s1_b_mant_full = Reg(MAN_FULL_W, "s1_b_mant_full")
        self.s1_b_is_nan = Reg(1, "s1_b_is_nan")
        self.s1_b_is_inf = Reg(1, "s1_b_is_inf")
        self.s1_b_is_zero = Reg(1, "s1_b_is_zero")
        self.s1_b_mag = Reg(EXP_WIDTH + MANT_WIDTH, "s1_b_mag")

        self.s1_op = Reg(3, "s1_op")

        # Pre-declare downstream valid regs for ready calculation
        self.s2_valid = Reg(1, "s2_valid")
        self.o_valid_reg = Reg(1, "o_valid_reg")

        self.s1_ready = Wire(1, "s1_ready")
        self.s2_ready = Wire(1, "s2_ready")
        self.s3_ready = Wire(1, "s3_ready")

        self.s1_ready <<= ~self.s1_valid | self.s2_ready
        self.s2_ready <<= ~self.s2_valid | self.s3_ready
        self.s3_ready <<= ~self.o_valid_reg | self.o_ready
        self.i_ready <<= self.s1_ready

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= Const(0, 1)
            with Else():
                with If(self.s1_ready):
                    self.s1_valid <<= self.i_valid
                    with If(self.i_valid):
                        self.s1_a_sign <<= self.a_sign
                        self.s1_a_exp <<= self.a_exp
                        self.s1_a_mant_full <<= self.a_mant_full
                        self.s1_a_is_nan <<= self.a_is_nan
                        self.s1_a_is_inf <<= self.a_is_inf
                        self.s1_a_is_zero <<= self.a_is_zero
                        self.s1_a_mag <<= self.a_mag

                        self.s1_b_sign <<= self.b_sign
                        self.s1_b_exp <<= self.b_exp
                        self.s1_b_mant_full <<= self.b_mant_full
                        self.s1_b_is_nan <<= self.b_is_nan
                        self.s1_b_is_inf <<= self.b_is_inf
                        self.s1_b_is_zero <<= self.b_is_zero
                        self.s1_b_mag <<= self.b_mag

                        self.s1_op <<= self.op

        # ------------------------------------------------------------------
        # Stage 2: Compute
        # ------------------------------------------------------------------
        self.s2_valid = Reg(1, "s2_valid")

        # Add/Sub intermediate wires
        self.add_eff_b_sign = Wire(1, "add_eff_b_sign")
        self.add_a_is_bigger = Wire(1, "add_a_is_bigger")
        self.add_big_exp = Wire(EXP_WIDTH, "add_big_exp")
        self.add_big_sign = Wire(1, "add_big_sign")
        self.add_big_mant = Wire(MAN_FULL_W, "add_big_mant")
        self.add_small_sign = Wire(1, "add_small_sign")
        self.add_small_mant = Wire(MAN_FULL_W, "add_small_mant")
        self.add_shift = Wire(EXP_WIDTH, "add_shift")
        self.add_small_mant_shifted = Wire(ADD_PATH_W, "add_small_mant_shifted")
        self.add_big_mant_ext = Wire(ADD_SIGNED_W, "add_big_mant_ext")
        self.add_small_mant_ext = Wire(ADD_SIGNED_W, "add_small_mant_ext")
        self.add_signed_big = Wire(ADD_SIGNED_W, "add_signed_big")
        self.add_signed_small = Wire(ADD_SIGNED_W, "add_signed_small")
        self.add_raw_sum = Wire(ADD_SIGNED_W + 1, "add_raw_sum")
        self.add_res_sign = Wire(1, "add_res_sign")
        self.add_res_mag = Wire(ADD_SIGNED_W + 1, "add_res_mag")
        self.add_norm_mant = Wire(MAN_FULL_W, "add_norm_mant")
        self.add_norm_exp = Wire(7, "add_norm_exp")

        # Mul intermediate wires
        self.mul_sign = Wire(1, "mul_sign")
        self.mul_a_eff_exp = Wire(EXP_WIDTH, "mul_a_eff_exp")
        self.mul_b_eff_exp = Wire(EXP_WIDTH, "mul_b_eff_exp")
        self.mul_exp_raw = Wire(7, "mul_exp_raw")
        self.mul_prod = Wire(MAN_FULL_W * 2, "mul_prod")  # 6b
        self.mul_ovf = Wire(1, "mul_ovf")
        self.mul_norm_prod = Wire(MAN_FULL_W * 2, "mul_norm_prod")
        self.mul_guard = Wire(1, "mul_guard")
        self.mul_mant_tmp = Wire(MAN_FULL_W + 1, "mul_mant_tmp")  # 4b
        self.mul_mant_ovf = Wire(1, "mul_mant_ovf")
        self.mul_mant = Wire(MAN_FULL_W, "mul_mant")
        self.mul_exp = Wire(7, "mul_exp")

        # Cmp intermediate wires
        self.cmp_lt = Wire(1, "cmp_lt")
        self.cmp_eq = Wire(1, "cmp_eq")
        self.minmax_sel_a = Wire(1, "minmax_sel_a")

        @self.comb
        def _s2_compute():
            # ---- add/sub --------------------------------------------------
            self.add_eff_b_sign <<= Mux(self.s1_op == 1, self.s1_b_sign ^ 1, self.s1_b_sign)
            self.add_a_is_bigger <<= (self.s1_a_exp > self.s1_b_exp) | (
                (self.s1_a_exp == self.s1_b_exp) & (self.s1_a_mant_full >= self.s1_b_mant_full)
            )
            self.add_big_exp <<= Mux(self.add_a_is_bigger, self.s1_a_exp, self.s1_b_exp)
            self.add_big_sign <<= Mux(self.add_a_is_bigger, self.s1_a_sign, self.add_eff_b_sign)
            self.add_big_mant <<= Mux(self.add_a_is_bigger, self.s1_a_mant_full, self.s1_b_mant_full)
            self.add_small_sign <<= Mux(
                self.add_a_is_bigger, self.add_eff_b_sign, self.s1_a_sign
            )
            self.add_small_mant <<= Mux(self.add_a_is_bigger, self.s1_b_mant_full, self.s1_a_mant_full)
            self.add_shift <<= Mux(
                self.add_a_is_bigger,
                self.s1_a_exp - self.s1_b_exp,
                self.s1_b_exp - self.s1_a_exp,
            )
            # Align small mantissa
            self.add_small_mant_shifted <<= (
                Cat(self.add_small_mant, Const(0, ADD_GUARD)) >> self.add_shift
            )
            self.add_big_mant_ext <<= Cat(Const(0, ADD_SIGNED_W - ADD_PATH_W), self.add_big_mant, Const(0, ADD_GUARD))
            self.add_small_mant_ext <<= Cat(
                Const(0, ADD_SIGNED_W - ADD_PATH_W), self.add_small_mant_shifted
            )
            self.add_signed_big <<= Mux(
                self.add_big_sign,
                Const(0, ADD_SIGNED_W) - self.add_big_mant_ext,
                self.add_big_mant_ext,
            )
            self.add_signed_small <<= Mux(
                self.add_small_sign,
                Const(0, ADD_SIGNED_W) - self.add_small_mant_ext,
                self.add_small_mant_ext,
            )
            self.add_raw_sum <<= Cat(
                self.add_signed_big[ADD_SIGNED_W - 1], self.add_signed_big
            ) + Cat(
                self.add_signed_small[ADD_SIGNED_W - 1], self.add_signed_small
            )
            self.add_res_sign <<= self.add_raw_sum[ADD_SIGNED_W]
            self.add_res_mag <<= Mux(
                self.add_res_sign,
                Const(0, ADD_SIGNED_W + 1) - self.add_raw_sum,
                self.add_raw_sum,
            )

            # Normalize add/sub result (leading zero detection)
            # add_res_mag width = 9. Leading one can be at bit 6 max (64..126)
            with If(self.add_res_mag[6]):
                self.add_norm_mant <<= self.add_res_mag[6:4]
                self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) + 1
            with Else():
                with If(self.add_res_mag[5]):
                    self.add_norm_mant <<= self.add_res_mag[5:3]
                    self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp)
                with Else():
                    with If(self.add_res_mag[4]):
                        self.add_norm_mant <<= self.add_res_mag[4:2]
                        self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 1
                    with Else():
                        with If(self.add_res_mag[3]):
                            self.add_norm_mant <<= self.add_res_mag[3:1]
                            self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 2
                        with Else():
                            with If(self.add_res_mag[2]):
                                self.add_norm_mant <<= self.add_res_mag[2:0]
                                self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 3
                            with Else():
                                with If(self.add_res_mag[1]):
                                    self.add_norm_mant <<= Cat(self.add_res_mag[1:0], Const(0, 1))
                                    self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 4
                                with Else():
                                    with If(self.add_res_mag[0]):
                                        self.add_norm_mant <<= Cat(self.add_res_mag[0], Const(0, 2))
                                        self.add_norm_exp <<= Cat(Const(0, 2), self.add_big_exp) - 5
                                    with Else():
                                        self.add_norm_mant <<= Const(0, MAN_FULL_W)
                                        self.add_norm_exp <<= Const(0, 7)

            # ---- mul ------------------------------------------------------
            self.mul_sign <<= self.s1_a_sign ^ self.s1_b_sign
            self.mul_a_eff_exp <<= Mux(self.s1_a_exp == 0, 1, self.s1_a_exp)
            self.mul_b_eff_exp <<= Mux(self.s1_b_exp == 0, 1, self.s1_b_exp)
            self.mul_exp_raw <<= self.mul_a_eff_exp + self.mul_b_eff_exp - BIAS
            self.mul_prod <<= self.s1_a_mant_full * self.s1_b_mant_full
            self.mul_ovf <<= self.mul_prod[MAN_FULL_W * 2 - 1]
            self.mul_norm_prod <<= Mux(self.mul_ovf, self.mul_prod >> 1, self.mul_prod)
            self.mul_guard <<= Mux(self.mul_ovf, self.mul_prod[0], self.mul_prod[1])
            self.mul_mant_tmp <<= self.mul_norm_prod[MAN_FULL_W * 2 - 2 : MAN_FULL_W * 2 - 4] + self.mul_guard
            self.mul_mant_ovf <<= self.mul_mant_tmp[MAN_FULL_W]
            self.mul_mant <<= Mux(
                self.mul_mant_ovf,
                Const(0b100, MAN_FULL_W),
                self.mul_mant_tmp[MAN_FULL_W - 1 : 0],
            )
            self.mul_exp <<= self.mul_exp_raw + self.mul_ovf + self.mul_mant_ovf

            # ---- cmp ------------------------------------------------------
            with If(self.s1_a_is_nan | self.s1_b_is_nan):
                self.cmp_lt <<= Const(0, 1)
                self.cmp_eq <<= Const(0, 1)
                self.minmax_sel_a <<= Mux(self.s1_b_is_nan, Const(1, 1), Const(0, 1))
            with Else():
                with If(self.s1_a_is_zero & self.s1_b_is_zero):
                    self.cmp_lt <<= Const(0, 1)
                    self.cmp_eq <<= Const(1, 1)
                    self.minmax_sel_a <<= Const(0, 1)
                with Else():
                    with If(self.s1_a_sign != self.s1_b_sign):
                        self.cmp_eq <<= Const(0, 1)
                        with If(self.s1_a_sign == 1):
                            self.cmp_lt <<= Const(1, 1)
                            self.minmax_sel_a <<= Mux(self.s1_op == 3, Const(1, 1), Const(0, 1))
                        with Else():
                            self.cmp_lt <<= Const(0, 1)
                            self.minmax_sel_a <<= Mux(self.s1_op == 3, Const(0, 1), Const(1, 1))
                    with Else():
                        self.cmp_eq <<= self.s1_a_mag == self.s1_b_mag
                        with If(self.s1_a_sign == 0):
                            self.cmp_lt <<= self.s1_a_mag < self.s1_b_mag
                            self.minmax_sel_a <<= Mux(
                                self.s1_op == 3,
                                self.s1_a_mag < self.s1_b_mag,
                                self.s1_a_mag > self.s1_b_mag,
                            )
                        with Else():
                            self.cmp_lt <<= self.s1_a_mag > self.s1_b_mag
                            self.minmax_sel_a <<= Mux(
                                self.s1_op == 3,
                                self.s1_a_mag > self.s1_b_mag,
                                self.s1_a_mag < self.s1_b_mag,
                            )

        # Stage 2 -> Stage 3 comb + registers
        self.s2_res_sign = Reg(1, "s2_res_sign")
        self.s2_res_exp = Reg(7, "s2_res_exp")
        self.s2_res_mant = Reg(MAN_FULL_W, "s2_res_mant")
        self.s2_is_nan = Reg(1, "s2_is_nan")
        self.s2_is_inf = Reg(1, "s2_is_inf")
        self.s2_is_zero = Reg(1, "s2_is_zero")
        self.s2_op = Reg(3, "s2_op")
        self.s2_cmp_lt = Reg(1, "s2_cmp_lt")
        self.s2_cmp_eq = Reg(1, "s2_cmp_eq")
        self.s2_minmax_sel_a = Reg(1, "s2_minmax_sel_a")
        self.s2_minmax_a = Reg(8, "s2_minmax_a")
        self.s2_minmax_b = Reg(8, "s2_minmax_b")

        self.s2_res_sign_in = Wire(1, "s2_res_sign_in")
        self.s2_res_exp_in = Wire(7, "s2_res_exp_in")
        self.s2_res_mant_in = Wire(MAN_FULL_W, "s2_res_mant_in")
        self.s2_is_nan_in = Wire(1, "s2_is_nan_in")
        self.s2_is_inf_in = Wire(1, "s2_is_inf_in")
        self.s2_is_zero_in = Wire(1, "s2_is_zero_in")
        self.s2_cmp_lt_in = Wire(1, "s2_cmp_lt_in")
        self.s2_cmp_eq_in = Wire(1, "s2_cmp_eq_in")
        self.s2_minmax_sel_a_in = Wire(1, "s2_minmax_sel_a_in")

        @self.comb
        def _s2_to_s3_comb():
            is_mul = self.s1_op == 2
            is_addsub = (self.s1_op == 0) | (self.s1_op == 1)

            self.s2_res_sign_in <<= Mux(is_mul, self.mul_sign, self.add_res_sign)
            self.s2_res_exp_in <<= Mux(is_mul, self.mul_exp, self.add_norm_exp)
            self.s2_res_mant_in <<= Mux(is_mul, self.mul_mant, self.add_norm_mant)

            # NaN/Inf/Zero flags for arith ops
            addsub_nan = self.s1_a_is_nan | self.s1_b_is_nan | (
                self.s1_a_is_inf & self.s1_b_is_inf & is_addsub & (self.s1_a_sign != self.add_eff_b_sign)
            )
            mul_nan = self.s1_a_is_nan | self.s1_b_is_nan | (self.s1_a_is_inf & self.s1_b_is_zero) | (self.s1_a_is_zero & self.s1_b_is_inf)
            arith_nan = Mux(is_mul, mul_nan, addsub_nan)

            mul_exp_msb = self.mul_exp[6]
            add_norm_exp_msb = self.add_norm_exp[6]
            addsub_inf = (self.s1_a_is_inf | self.s1_b_is_inf | ((self.add_norm_exp >= 31) & ~add_norm_exp_msb)) & ~arith_nan
            mul_inf = (self.s1_a_is_inf | self.s1_b_is_inf | ((self.mul_exp >= 31) & ~mul_exp_msb)) & ~arith_nan
            arith_inf = Mux(is_mul, mul_inf, addsub_inf)

            addsub_zero = (self.add_res_mag == 0) & is_addsub
            mul_zero = self.s1_a_is_zero | self.s1_b_is_zero
            arith_zero = Mux(is_mul, mul_zero, addsub_zero)

            self.s2_is_nan_in <<= arith_nan
            self.s2_is_inf_in <<= arith_inf
            self.s2_is_zero_in <<= arith_zero & ~arith_nan & ~arith_inf

            self.s2_cmp_lt_in <<= self.cmp_lt
            self.s2_cmp_eq_in <<= self.cmp_eq
            self.s2_minmax_sel_a_in <<= self.minmax_sel_a

        # Pass raw a/b through s1 for minmax
        self.s1_a_raw = Reg(8, "s1_a_raw")
        self.s1_b_raw = Reg(8, "s1_b_raw")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_raw_seq():
            with If(self.rst_n == 0):
                pass
            with Else():
                with If(self.s1_ready & self.i_valid):
                    self.s1_a_raw <<= self.a
                    self.s1_b_raw <<= self.b

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s2_seq():
            with If(self.rst_n == 0):
                self.s2_valid <<= Const(0, 1)
            with Else():
                with If(self.s2_ready):
                    self.s2_valid <<= self.s1_valid
                    with If(self.s1_valid):
                        self.s2_res_sign <<= self.s2_res_sign_in
                        self.s2_res_exp <<= self.s2_res_exp_in
                        self.s2_res_mant <<= self.s2_res_mant_in
                        self.s2_is_nan <<= self.s2_is_nan_in
                        self.s2_is_inf <<= self.s2_is_inf_in
                        self.s2_is_zero <<= self.s2_is_zero_in
                        self.s2_op <<= self.s1_op
                        self.s2_cmp_lt <<= self.s2_cmp_lt_in
                        self.s2_cmp_eq <<= self.s2_cmp_eq_in
                        self.s2_minmax_sel_a <<= self.s2_minmax_sel_a_in
                        self.s2_minmax_a <<= self.s1_a_raw
                        self.s2_minmax_b <<= self.s1_b_raw

        # ------------------------------------------------------------------
        # Stage 3: Pack & Output
        # ------------------------------------------------------------------
        self.arith_result = Wire(8, "arith_result")
        self.cmp_result = Wire(8, "cmp_result")
        self.minmax_result = Wire(8, "minmax_result")
        self.final_result = Wire(8, "final_result")
        self.final_flags = Wire(4, "final_flags")
        self.result_reg = Reg(8, "result_reg")
        self.flags_reg = Reg(4, "flags_reg")

        @self.comb
        def _s3_pack():
            # Arithmetic packing
            with If(self.s2_is_nan):
                self.arith_result <<= Cat(Const(0, 1), Const(31, EXP_WIDTH), Const(0b01, MANT_WIDTH))
            with Else():
                exp_msb = self.s2_res_exp[6]
                with If(self.s2_is_inf | ((self.s2_res_exp >= 31) & ~exp_msb)):
                    self.arith_result <<= Cat(self.s2_res_sign, Const(31, EXP_WIDTH), Const(0, MANT_WIDTH))
                with Else():
                    with If(self.s2_is_zero | exp_msb):
                        self.arith_result <<= Cat(self.s2_res_sign, Const(0, EXP_WIDTH), Const(0, MANT_WIDTH))
                    with Else():
                        self.arith_result <<= Cat(
                            self.s2_res_sign,
                            self.s2_res_exp[EXP_WIDTH - 1 : 0],
                            self.s2_res_mant[MANT_WIDTH - 1 : 0],
                        )

            # Compare result: bit0 = predicate
            cmp_bit = Mux(self.s2_op == 5, self.s2_cmp_lt, self.s2_cmp_eq)
            self.cmp_result <<= Cat(Const(0, 7), cmp_bit)

            # Min/Max result
            self.minmax_result <<= Mux(self.s2_minmax_sel_a, self.s2_minmax_a, self.s2_minmax_b)

            # Final mux
            is_cmp = (self.s2_op == 5) | (self.s2_op == 6)
            is_minmax = (self.s2_op == 3) | (self.s2_op == 4)
            with If(is_cmp):
                self.final_result <<= self.cmp_result
            with Else():
                with If(is_minmax):
                    self.final_result <<= self.minmax_result
                with Else():
                    self.final_result <<= self.arith_result

            # Flags
            is_arith = (self.s2_op == 0) | (self.s2_op == 1) | (self.s2_op == 2)
            nv = self.s2_is_nan & is_arith
            of = self.s2_is_inf & is_arith
            uf = self.s2_is_zero & ~nv & ~of & is_arith
            self.final_flags <<= Cat(nv, of, uf, Const(0, 1))

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s3_seq():
            with If(self.rst_n == 0):
                self.o_valid_reg <<= Const(0, 1)
            with Else():
                with If(self.s3_ready):
                    self.o_valid_reg <<= self.s2_valid
                    with If(self.s2_valid):
                        self.result_reg <<= self.final_result
                        self.flags_reg <<= self.final_flags

        @self.comb
        def _output_assign():
            self.o_valid <<= self.o_valid_reg
            self.result <<= self.result_reg
            self.flags <<= self.flags_reg


# ---------------------------------------------------------------------------
# Generate Verilog when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from rtlgen import VerilogEmitter

    top = FP8ALU()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
```

*Generated for rtlgen project.*

---

### 17.13 最近更新：FP8 ALU 生成器修复（2026-04-14）

针对 `tests/test_fp8_alu_pyuvm.py` 的 FP8 ALU 平台，`rtlgen.pyuvmgen` 已完成以下修复，使生成的 SV/UVM 无需手工修改即可直接编译：

1. **Coverage 成员声明** — `Scoreboard` 中的 `Coverage` 对象（`cov_op`、`cov_a_class` 等）现在会自动推断并在类中声明为成员。
2. **抑制 Python 表达式泄漏** — `define_bins(list(range(7)))`、`sample(...)`、`report()` 等 Coverage 方法调用不再出现在生成的 SV `new()` / `run_phase` / `report_phase` 中。
3. **`seq_item_port` 修正** — Driver 中对 `self.seq_item_port.get_next_item()` / `item_done()` 的翻译不再错误地变成 `seq_item_fifo`。
4. **`txn_type` 推断增强** — Monitor / Scoreboard 中的 `uvm_analysis_port #(FP8ALUTxn)`、`uvm_tlm_analysis_fifo #(FP8ALUTxn)`、`uvm_blocking_get_port #(FP8ALUTxn)` 现在能正确解析为 `FP8ALUTxn` 而非默认的 `uvm_sequence_item`。
5. **本地数组声明** — Python 中的 `classes = ["zero", "subnormal", ...]` 现在会生成 `string classes [N] = '{...};`。
6. **`_check` 占位处理** — Scoreboard 中调用的 Python 内部参考模型（`expected_result`、`fp8_classify` 等）在生成器侧暂不支持自动转译，生成的 SV 中会将其替换为注释占位，保证编译通过。用户可手动替换为 SV 参考模型或 DPI 实现。

生成的文件示例位于 `generated_fp8_alu/` 目录。

---

### 17.14 DPI 桥：让生成的 SV/UVM 直接调用 Python 参考模型（2026-04-14）

`rtlgen` 现在支持通过 **DPI-C** 把 Python 参考模型自动桥接到生成的 SystemVerilog/UVM 中，实现“同一套 Python 参考模型，既能在 pyUVM 侧仿真，也能在 VCS/Questa/Xcelium 侧运行”。

#### 使用方式

1. **在 `rtlgen.dpi_runtime` 中定义参考模型**，并用 `@sv_dpi` 标记：
   ```python
   # rtlgen/dpi_runtime.py
   from rtlgen.pyuvm import sv_dpi
   import hashlib

   @sv_dpi(c_decl='import "DPI-C" function void dpi_sha3_256(input longint block[17], input int len, output longint hash[4]);')
   def dpi_sha3_256(block_arr=None, msg_len=None, hash_arr=None):
       if isinstance(block_arr, bytes):
           return hashlib.sha3_256(block_arr).digest()
       msg = 0
       for i in range(17):
           msg |= block_arr[i] << (i * 64)
       digest = hashlib.sha3_256(msg.to_bytes(17*8, 'little')[:msg_len]).digest()
       for i in range(4):
           hash_arr[i] = int.from_bytes(digest[i*8:(i+1)*8], 'little')
   ```

2. **在 Python pyUVM Scoreboard 中直接调用**：
   ```python
   from rtlgen.dpi_runtime import dpi_sha3_256

   class SHA3Scoreboard(UVMComponent):
       def check(self, exp_txn, act_txn):
           block_arr = [0] * 17
           hash_out  = [0] * 4
           for i in range(17):
               block_arr[i] = (exp_txn.block >> (i * 64)) & 0xFFFFFFFFFFFFFFFF
           dpi_sha3_256(block_arr, exp_txn.msg_len, hash_out)
           expected = 0
           for i in range(4):
               expected |= hash_out[i] << (i * 64)
           ...
   ```

3. **生成 SV/UVM**：`pyuvmgen` 会自动：
   - 在生成的 `sha3_scoreboard.sv` 顶部插入 `import "DPI-C" function void dpi_sha3_256(...);`
   - 将 `check` 方法中的 Python 循环、`[0] * N` 数组初始化、`block_arr[i] = ...`、DPI 调用等翻译为合法的 SystemVerilog。

4. **编译 DPI 共享库**：
   ```bash
   cd generated_sha3_256
   make        # -> libdpi_sha3.dylib (macOS) 或 libdpi_sha3.so (Linux)
   ```

5. **在仿真器中加载**：
   ```bash
   # VCS 示例
   vcs -R -sverilog -ntb_opts uvm-1.1 tb_top.sv -LDFLAGS "-L./ -ldpi_sha3"
   ```

#### 生成器增强点

- **`sv_dpi` 装饰器**：`rtlgen.pyuvm.sv_dpi(c_decl=...)` 会自动把函数注册到 `rtlgen.dpi_runtime`，并携带生成器所需的 SV `import` 声明。
- **DPI import 自动收集**：`_emit_component_class` 会扫描类中所有方法，自动提取 `@sv_dpi` 函数的 `c_decl` 并插入到生成的 `.sv` 文件头部。
- **数组支持**：生成器新增了对 `arr[i] = val`（`ast.Subscript` 赋值）和 `[0] * N`（`ast.BinOp` list 复制）的翻译，使 Scoreboard 中的循环初始化可以直接映射到 SV `longint arr[N] = '{0,0,...};` 和 `for` 循环。

#### 示例工程

完整的端到端示例位于：
- DUT: `examples/sha3_256_pipe.py`
- Python UVM test: `tests/test_sha3_256_pyuvm.py`
- Generated SV + DPI: `generated_sha3_256/`

该示例覆盖空消息、`abc`、`hello world`、最大单块（135 bytes）等定向向量，并通过 DPI 在 Python 侧和 SV 侧共用同一套 `hashlib.sha3_256` 参考模型。

---

### 17.15 最近更新：模块参数化增强（2026-04-14）

`rtlgen` 现在对模块参数（`parameter` / `localparam`）提供了更完整、更符合硬件设计习惯的支持。

#### 新增 API

1. **`LocalParam`** —— 生成不可重载的 `localparam`：
   ```python
   from rtlgen import LocalParam

   self.DEPTH = LocalParam(16, "DEPTH")
   ```

2. **`add_param` / `add_localparam`** —— 推荐的便捷方法：
   ```python
   self.add_param("WIDTH", 32)       # -> parameter WIDTH = 32
   self.add_localparam("MASK", 0xFF) # -> localparam MASK = 255
   ```

#### 代码生成器行为

- `Parameter` 仍出现在模块头部的 `#(...)` 中，可被上层覆盖。
- `LocalParam` 被自动过滤到模块内部，以 `localparam NAME = VALUE;` 形式声明，不会出现在 `#()` 中。

```verilog
module ParamAdder #(parameter WIDTH = 8) (
    input [7:0] a,
    input [7:0] b,
    output [7:0] y
);
    localparam OFFSET = 1;
    assign y = a + b + OFFSET;
endmodule
```

#### 仿真器支持参数覆盖

`Simulator` 现在支持在子模块实例化时传递参数覆盖：

```python
# 显式实例化
adder = ParamAdder()
self.instantiate(adder, "u_adder", params={"WIDTH": 16}, port_map={...})

# 隐式实例化
self.adder = ParamAdder(param_bindings={"WIDTH": self.WIDTH})
```

仿真器会自动将覆盖后的参数值传递给子模块的 `Simulator`，确保 Python 仿真与生成 Verilog 的行为一致。

#### 新增测试

`tests/test_param_localparam.py` 覆盖了：
- `parameter` / `localparam` 的 Verilog 生成检查
- 显式 / 隐式 / 自动参数映射的代码生成
- 参数覆盖在仿真器中的正确性验证

---

### 17.16 最近更新：8b10b Decoder 完整端到端示例（2026-04-14）

新增了一个基于 pyRTL Python API 的 **8b10b Decoder** 设计，覆盖 DUT、Python 功能测试、Python pyUVM 测试平台，以及自动生成的 SV/UVM 代码。

#### DUT 设计 (`examples/decoder_8b10b.py`)

- 单周期 latency 的同步 8b10b 解码器
- 支持 control symbols（24 个 pattern）和 data symbols（5b/6b + 3b/4b 查表）
- 使用 `Switch` 自动生成 Verilog `case` 语句进行组合查表
- 输出通过 `@self.seq` 寄存，实现 1-cycle 延迟

```python
class Decoder8b10b(Module):
    def __init__(self, name="decoder_8b10b"):
        super().__init__(name)
        self.clk_in = Input(1, "clk_in")
        self.reset_in = Input(1, "reset_in")
        self.control_in = Input(1, "control_in")
        self.decoder_in = Input(10, "decoder_in")
        self.decoder_valid_in = Input(1, "decoder_valid_in")
        self.decoder_out = Output(8, "decoder_out")
        self.decoder_valid_out = Output(1, "decoder_valid_out")
        self.control_out = Output(1, "control_out")

        # Pipeline registers + combinational decode wires ...
        @self.seq(self.clk_in, self.reset_in, reset_async=True)
        def _pipeline():
            ...

        @self.comb
        def _decode_control():
            with Switch(self.r_data) as sw:
                for pattern, value in CONTROL_TABLE:
                    with sw.case(pattern):
                        self.control_dec <<= value
                with sw.default():
                    self.control_dec <<= 0
```

#### Python 功能测试 (`tests/test_decoder_8b10b.py`)

覆盖：
- Reset 行为
- 所有 control symbol 的定向查表验证
- 部分 data symbol 的代表性验证
- 全部有效 data 组合的穷举验证（约 400+ entries）
- Valid 信号 1-cycle 延迟传播
- Invalid control pattern fallback

#### Python pyUVM 测试平台 (`tests/test_decoder_8b10b_pyuvm.py`)

- `DecoderTxn`：包含完整的输入/输出字段
- `DecoderDriver` / `DecoderInMonitor` / `DecoderOutMonitor`：标准 UVM 组件
- `DecoderScoreboard`：通过 DPI 调用 `dpi_decoder_8b10b_ref` 获取预期解码结果
- `DecoderDirectedSeq`：覆盖 24 个 control patterns + 6 个 data patterns + 1 个 invalid control
- 31 笔 transactions 全部通过，无 mismatch

#### DPI 参考模型 (`rtlgen/dpi_runtime.py`)

新增了 `dpi_decoder_8b10b_ref`，被 `@sv_dpi` 装饰：
```python
@sv_dpi(c_decl='import "DPI-C" function void dpi_decoder_8b10b_ref(...);')
def dpi_decoder_8b10b_ref(decoder_in=None, control_in=None, ...):
    ...
```

该函数在 Python pyUVM 仿真时直接调用，在生成的 SV/UVM 中则作为 DPI-C import 被 `scoreboard.sv` 调用。

#### 生成的 SV/UVM (`generated_decoder_8b10b/`)

`pyuvmgen` 自动生成了以下文件：
- `decoder_8b10b.v` — DUT Verilog
- `decoder_8b10b_if.sv` — UVM virtual interface
- `decoder_8b10b_pkg.sv`, `DecoderTxn.sv`
- `decoder_agent.sv`, `decoder_driver.sv`, `decoder_in_monitor.sv`, `decoder_out_monitor.sv`
- `decoder_scoreboard.sv` — 包含 DPI import 和 `uvm_config_db::get`
- `decoder_env.sv`, `decoder_test.sv`
- `tb_top.sv` — top-level testbench

#### 生成器同步修复

本次工作同时修复了 `pyuvmgen` 中的两个生成问题：
1. **`cfg_db_get` 翻译修复**：`total = self.cfg_db_get("total_txn_count") or 0` 现在正确生成 `if (!uvm_config_db#(int)::get(this, "", "total_txn_count", total)) total = 0;`，而非之前的 `total = (0)`。
2. **`tb_top.sv` 占位符修复**：修复了 `{rstr}` 未替换为 `{rst_block}` 的生成 bug。

---

### 17.17 最近更新：PPA 分析器（2026-04-14）

新增 `rtlgen.ppa.PPAAnalyzer`，可在不写 Verilog、不跑综合的情况下，基于 AST 静态分析与 Simulator trace 动态分析，快速评估设计的 **Performance、Power、Area** 指标，并给出优化建议。

#### 快速开始

```python
from rtlgen import PPAAnalyzer, Simulator
from examples.decoder_8b10b import Decoder8b10b

dut = Decoder8b10b()
ppa = PPAAnalyzer(dut)

# 静态分析（无需仿真）
static = ppa.analyze_static()
print(f"Max logic depth : {max(static['logic_depth'].values())}")
print(f"Gate estimate   : {static['gate_count']:.1f} NAND2-equiv")
print(f"Register bits   : {static['reg_bits']}")

# 动态分析（基于仿真 trace）
sim = Simulator(dut)
# ... 驱动测试向量 ...
print(ppa.report(sim))
```

#### 分析指标

| 维度 | 指标 | 说明 |
|------|------|------|
| **Performance** | `logic_depth` | 从 Reg/Input 到 Output/Reg 的递归组合逻辑深度，自动考虑 `IfNode` (Mux) 与 `SwitchNode` (查表) 的级联深度 |
| **Area** | `gate_count` | 按 AST 中 `BinOp`/`Mux`/`Concat` 等节点乘以位宽和权重，估算等效 NAND2 门数 |
| **Area** | `reg_bits` | 所有 `Reg` 与 `output reg` 的总位宽 |
| **Area** | `mux_complexity` | `SwitchNode` 的 case 总数与最大条件位宽 |
| **Area** | `dead_signals` | 声明但未被驱动或读取的 Wire/Reg |
| **Power** | `toggle_rates` | 基于 `Simulator.trace` 统计每个信号每 cycle 的翻转率 |
| **Power** | `power_hotspots` | 翻转率超过阈值（默认 80%）的信号列表 |

#### 优化建议引擎

`suggest_optimizations()` 根据规则自动生成中文建议：

- **时序**：逻辑深度 > 6 提示插入 pipeline；> 4 提示关注临界路径。
- **面积**：case 分支 > 32 提示改用 Memory/ROM。
- **布线**：扇出 > 8 提示插入 buffer_reg 或负载均衡。
- **清理**：列出未使用信号建议删除。

#### 8b10b Decoder 的 PPA 报告示例

```
============================================================
PPA Report for Module: decoder_8b10b
============================================================

[Static Analysis]
  Max logic depth : 13
  Gate estimate   : 1698.8 NAND2-equiv
  Register bits   : 22
  Case branches   : 82
  Dead signals    : 0

[Dynamic Analysis]
  Avg toggle rate : 28.41%/cycle
  Hottest signal  : _time (100.00%/cycle)

[Optimization Suggestions]
  • [时序] 信号 'decoder_out' 组合逻辑深度为 13，建议插入 pipeline stage
  • [面积] 设计包含 82 个 case 分支的大规模查表，可考虑替换为 Memory/ROM
```

> **说明**：`decoder_out` 深度 13 是一个**保守 worst-case 估计**，包含了 46-case 的 5b/6b 查表（depth ≈ 7）+ `IfNode` Mux 选择（depth ≈ 3）+ reset 路径嵌套（depth ≈ 3）。实际功能关键路径约为 10，但该估算已足够在设计阶段暴露潜在时序风险。

#### API 导出

```python
from rtlgen import PPAAnalyzer
```

新增测试：`tests/test_ppa.py` 覆盖了逻辑深度、门数估算、寄存器位宽、扇出、死信号、翻转率、报告生成等核心功能。

---

### 17.18 最近更新：RTL IR → BLIF → ABC 逻辑综合流水线（2026-04-14）

`rtlgen` 现在支持将 RTL IR 直接下沉到门级网表（BLIF），并集成 **Berkeley ABC** 进行逻辑优化、AIG 生成、标准单元映射和时序分析。

#### 整体流程

```
Python AST → RTL IR (rtlgen.core) → BLIF (rtlgen.blifgen) → ABC → mapped Verilog
```

1. **BLIFEmitter** 把 `Module` 展开为单比特 BLIF 网表：
   - 组合逻辑：`AND`/`OR`/`XOR`/`NOT` → `.names` LUT
   - 算术逻辑：`+` / `-` / `==` / `!=` / `<` / `<=` / `>` / `>=` → `full_adder` / `full_subtractor` 链（`.subckt`）
   - 数据选择：`IfNode` / `SwitchNode` / `Mux` → 2:1 MUX `.names`（支持 don't care）
   - 时序逻辑：`Reg` → `.latch`（同步复位在组合域中处理）

2. **ABCSynthesizer** 生成并执行 ABC 脚本：
   - `read_blif` → `strash`（转成 AIG）→ `resyn2`（逻辑优化）
   - `read_lib` → `map`（工艺映射）→ `stime -p`（时序报告）
   - 输出 `write_verilog` 和可选的 `write_aiger` AIG 文件

3. **WireLoadModel** 提供简单的线负载模型，用于在 ABC 映射后做互连线延迟估算：
   - `delay = fanout * slope + intercept`

#### 快速示例

```python
from rtlgen import Module, Input, Output, BLIFEmitter
from rtlgen.synth import ABCSynthesizer, WireLoadModel
from rtlgen.liberty import generate_demo_liberty

class Adder(Module):
    def __init__(self):
        super().__init__("Adder")
        self.a = Input(4, "a")
        self.b = Input(4, "b")
        self.y = Output(4, "y")
        @self.comb
        def _logic():
            self.y <<= self.a + self.b

dut = Adder()
blif = BLIFEmitter().emit(dut)
with open("adder.blif", "w") as f:
    f.write(blif)

generate_demo_liberty("demo.lib")

synth = ABCSynthesizer()
result = synth.run(
    input_blif="adder.blif",
    liberty="demo.lib",
    output_verilog="adder_mapped.v",
    output_aig="adder.aag",
    wlm=WireLoadModel(slope=0.05, intercept=0.01),
)
print(f"Area={result.area}, Delay={result.delay}, Gates={result.gates}")
```

#### 生成的 BLIF 片段示例

```blif
.model Adder
.inputs a[0] a[1] a[2] a[3] b[0] b[1] b[2] b[3]
.outputs y[0] y[1] y[2] y[3]
.names gnd
.names vdd
1 1
.subckt half_adder a=a[0] b=b[0] s=y[0] c=c_1
.subckt full_adder a=a[1] b=b[1] cin=c_1 s=y[1] cout=c_2
.subckt full_adder a=a[2] b=b[2] cin=c_2 s=y[2] cout=c_3
.subckt full_adder a=a[3] b=b[3] cin=c_3 s=y[3] cout=c_4
.end
```

#### 集成说明

- 如果环境中未安装 ABC，`ABCSynthesizer.run()` 会抛出 `RuntimeError`，但同时生成 `run_abc.sh` 脚本。用户安装 ABC 后可直接运行：
  ```bash
  brew install abc        # macOS
  # 或从源码编译：https://github.com/berkeley-abc/abc
  ./run_abc.sh
  ```
- Demo Liberty 文件包含 `INVX1`、`NAND2X1`、`NOR2X1`、`DFFX1` 四个基本单元，面积与延迟参数已设定，可用于快速验证映射流程。

#### API 导出

```python
from rtlgen import BLIFEmitter, ABCSynthesizer, WireLoadModel, generate_demo_liberty
```

新增测试：
- `tests/test_blifgen.py` — 验证 BLIF 位级展开、加法器链、MUX、Switch、Reg latch
- `tests/test_synth_pipeline.py` — 验证 ABC 脚本生成、缺失 ABC 的降级处理、Liberty 与 WLM


---

## 附录 C：流水线延迟对齐设计模式

以下设计模式来自 `MontgomeryMult384` 的调试与修复经验，适用于任何包含**长延迟子模块**和**多拍延迟线**的流水线设计。

### C.1 问题：跨模块边界延迟

在 rtlgen AST 仿真器中，**子模块的 `@seq` 比父模块晚 1 拍看到父寄存器的更新**。这导致：

| 场景 | 仿真延迟 | Verilog 延迟 |
|------|---------|-------------|
| 同一模块内 N 级手写寄存器 | N | N |
| `ShiftReg(..., N)` 子模块 | N | N |
| 两个 `ShiftReg` 子模块级联 | 2N | 2N |
| N 级手写寄存器 + 1 个 child `@seq` | **N+1** | N |

**关键结论**：当父模块的寄存器延迟线需要与子模块的 `@seq` 输出对齐时，必须在仿真中额外加 **1 拍** 补偿边界延迟。

### C.2 案例：MontgomeryMult384 的 M 流水线

`RedUnit128` 内部 latency ≈ 13 cycles（`valid_in → valid_out`）。由于它是子模块，父模块实际看到的是 **14 cycles** 延迟（13 + 1 边界）。

**Bug 根因**：`M`（模数）原本只保存在单个寄存器 `s8_M_r` 中。当 `r0_valid` 在 14 cycles 后拉高时，`s8_M_r` 已经是下一个输入的 `M` 了。

**修复方案**：三级 16 级移位寄存器流水线

```
s7_M ──► s8_M_shift[0..15] ──► r0_M_shift[0..15] ──► r1_M_shift[0..15] ──► r2_M_r
          (16 stages)            (16 stages)           (16 stages)
```

- `s8_M_shift`：匹配 `s8_valid → r0_valid` 的 15 拍内部 + 1 拍边界 = 16 拍
- `r0_M_shift`：匹配 `r0_valid_r → r1_valid` 的延迟
- `r1_M_shift`：匹配 `r1_valid_r → r2_valid` 的延迟
- `r2_M_r`：在 `r2_valid` 时捕获 `r1_M_shift[15]`，用于最终条件减法

### C.3 对齐检查清单

设计包含子模块乘法器或约简单元的流水线时：

1. **测量子模块 latency**：单输入从 `valid_in` 到 `valid_out` 的周期数
2. **加 1 拍边界补偿**：如果消费者是子模块 `@seq`，仿真中需要 N+1 级延迟线
3. **延迟所有 sideband 数据**：`M`、`Mp`、控制信号必须与主数据路径同步
4. **用 `DebugProbe` 验证**：
   - 输入 0 的 `M` 应在输入 0 的 `valid_out` 时刻到达消费者
   - 输入 1 的 `M` 不应泄露到输入 0 的计算窗口
5. **测试不同模数的随机向量**：常量-M 测试无法发现 M 覆盖问题

### C.4 推荐做法

- **同一模块内**：使用手写寄存器链（无边界延迟问题）
- **跨模块边界**：要么用 `ShiftReg` 作为独立子模块（每级 +0 额外延迟），要么在父模块内写延迟线并 +1 补偿
- **Back-to-back 测试是必需项**：单输入正确不代表流水线对齐正确

---

## 附录 D：常见陷阱与最佳实践

以下经验来自 `skills/cpu/boom/`（BOOM 风格 OoO RISC-V 处理器）的开发过程。

### D.1 Wire 必须使用 `self` 属性才能在 `comb`/`seq` 中赋值

**错误**：

```python
w = Wire(4, "w")          # 局部变量
@self.comb
def _logic():
    w <<= self.a          # UnboundLocalError！
```

**正确**：

```python
self.w = Wire(4, "w")     # self 属性
@self.comb
def _logic():
    self.w <<= self.a     # OK
```

**原因**：Python 函数内对变量使用 `<<=` 时，解释器会将其视为局部变量赋值。如果变量在函数外定义，就会报 `UnboundLocalError`。`self.w` 作为属性访问不受此限制。

### D.2 Python `list[Signal]` 不支持动态索引

**错误**：

```python
regs = [Reg(8, f"r{i}") for i in range(4)]
@self.comb
def _read():
    self.dout <<= regs[self.idx]   # TypeError！
```

**正确**（使用 `Array`）：

```python
self.regs = Array(8, 4, "regs", vtype=Reg)
@self.comb
def _read():
    self.dout <<= self.regs[self.idx]   # OK
```

**正确**（使用 `Select`）：

```python
from rtlgen.logic import Select
regs = [Reg(8, f"r{i}") for i in range(4)]
@self.comb
def _read():
    self.dout <<= Select(regs, self.idx)   # OK
```

### D.3 `ForGen` 在 `@seq` 块中的使用

`ForGen` 可以在 `@seq` 块中生成 Verilog 的 `for (integer i = ...)` 循环，减少展开后的代码量：

```python
from rtlgen.logic import ForGen

@self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
def _shift():
    with If(self.rst_n == 0):
        with ForGen("i", 0, 4) as i:
            self.regs[i] <<= 0
    with Else():
        with ForGen("i", 1, 4) as i:
            self.regs[i] <<= self.regs[i - 1]
        self.regs[0] <<= self.din
```

生成：

```verilog
always @(posedge clk or negedge rst_n) begin
    if ((rst_n == 0)) begin
        for (integer i = 0; i < 4; i = i + 1) begin
            regs[i] <= 0;
        end
    end else begin
        for (integer i = 1; i < 4; i = i + 1) begin
            regs[i] <= regs[(i - 1)];
        end
        regs[0] <= din;
    end
end
```

### D.4 子模块边界延迟陷阱

在 AST 仿真器中，**父模块 `@seq` → 子模块 `@seq` 有 1 拍额外延迟**。如果设计依赖精确的周期对齐，注意：

- Verilog 仿真 / 综合：无额外延迟
- AST Python 仿真：+1 拍

建议用 `DebugProbe` 或 `sim.assert_eq()` 在关键节点做断言，确保延迟对齐。

### D.5 `Vector <<= Vector` 批量赋值

```python
self.a = Vector(8, 4, "a", vtype=Wire)
self.b = Vector(8, 4, "b", vtype=Wire)

@self.comb
def _connect():
    self.b <<= self.a       # 等价于 b[i] <<= a[i] for i in range(4)
```

---

## 附录 E：BOOM 风格 OoO CPU 设计模式

`skills/cpu/boom/` 目录下包含一套完整的 BOOM 风格乱序 RISC-V 处理器参考实现。以下是其核心设计模式总结。

### E.1 微架构概览

```
Fetch → Decode → Rename → Dispatch → Issue → Register Read → Execute → Writeback → Commit
```

| 阶段 | 模块 | 关键结构 |
|------|------|---------|
| Fetch | `FetchUnit` | PC、fetch buffer、branch predictor 接口 |
| Decode | `DecodeUnit` | 完整 RV32I 解码器，生成控制信号 |
| Rename | `RenameUnit` | RMT（Rename Map Table）、Free List、Busy Table |
| Dispatch | `core.py` | 将重命名后的指令分派到 RS 和 ROB |
| Issue | `ReservationStation` | 统一保留站，wakeup + select |
| RegRead | `PhysicalRegFile` | 6 读口 / 4 写口 |
| Execute | `ALU` / `Multiplier` / `LSU` | ALU、3-cycle MUL、Load/Store Unit |
| Writeback | `core.py` | PRF 写回 + RS wakeup |
| Commit | `ReorderBuffer` | 按序提交，释放旧物理寄存器 |

### E.2 关键设计决策

**1. 统一保留站 vs 分布式 Issue Queue**

真实 BOOM 使用分布式 IQ（ALU / MEM / FP 分离）。本实现使用统一 RS 降低复杂度，但仍然演示了 OoO issue 的核心机制：

- 每条指令进入 RS 时记录 `prs1/prs2/prd` 和 `busy1/busy2`
- Writeback 广播 `prd`，匹配到的 RS entry 清除 busy 标志
- Issue 选择第一个 `valid & !busy1 & !busy2` 的 entry

**2. 多端口物理寄存器堆**

```python
self.prf = PhysicalRegFile(
    num_pregs=64, num_read=6, num_write=4, xlen=32
)
```

6 个读口支持 2 operands × 3 issue lanes（部分共享），4 个写口支持 ALU / MUL / LSU / 备用。

**3. LSU 的 LQ / SQ 分离**

```python
self.lsu = LSU(xlen=32, lq_entries=8, sq_entries=8)
```

- **Load Queue**：追踪 in-flight loads，支持 sign/zero extension
- **Store Queue**：缓冲未提交的 stores，committed stores 优先于 loads 访问内存
- **Store-to-load forwarding**：检测 load 地址与未提交 store 地址匹配

**4. ROB 异常 flush**

```python
@self.seq(...)
def _seq():
    with If(self.exception_valid):
        # 清除所有 entry
        for i in range(num_entries):
            self.entry_valid[i] <<= 0
        self.tail <<= self.exception_rob_idx
```

异常发生时，ROB 从异常指令处截断，前端重定向到异常处理地址。

### E.3 推荐的设计流程

1. **从模块级开始**：先实现独立的 ALU、PRF、RS，各自写单测
2. **用 AST 仿真器验证**：`Simulator.assert_eq()` 检查周期精确行为
3. **逐步集成**：在 `core.py` 中连接各模块，从 Fetch → Decode → Rename 逐步添加
4. **生成 Verilog 后用 iverilog 验证**：`rtlgen.cosim` 或 `iverilog` 编译检查
5. **最后添加复杂控制**：分支预测、异常处理、store queue forwarding


---

## 20. NPU 神经网络加速器 (`skills/cpu/npu/`)

`skills/cpu/npu/` 目录下包含一套完整的神经网络加速器（Neural Processing Unit）设计，支持从 PyTorch 模型到 NPU 指令的端到端编译，以及周期精确的 AST 仿真验证。

### 20.1 架构概览

```
PyTorch Model → FX Graph → NPU IR (Lowering) → Instruction Binary → NPU Core Simulation
```

**NPU Core 硬件模块** (`skills/cpu/npu/core.py`):

| 模块 | 说明 |
|------|------|
| `ProgramCounter` | 程序计数器，支持顺序执行和跳转 |
| `InstructionMemory` | 指令存储器，支持运行时加载 |
| `InstDecode` | 指令译码器，支持 CONFIG/LOAD/STORE/GEMM/VEC_ALU/SFU/CROSSBAR/IM2COL |
| `SystolicArray` | 可配置规模的脉动阵列（GEMM 核心）|
| `VectorALU` | 向量 ALU，支持 ADD/MUL/RELU/MIN/MAX 等操作 |
| `SFU` | 特殊函数单元，支持 SIGMOID/TANH |
| `Crossbar` | 数据交叉开关，连接各执行单元与 SRAM |
| `AXI4DMA` | AXI4 Master DMA 引擎，负责片外 DRAM ↔ SRAM 数据传输 |
| `NeuralAccel` | 顶层模块，集成上述所有组件 |

**编译器链路** (`skills/cpu/npu/compiler/`):

| 文件 | 功能 |
|------|------|
| `lowering.py` | PyTorch FX Graph → NPU IR（支持 Conv2d/Linear/ReLU/Add 等）|
| `codegen.py` | NPU IR → 指令二进制 + 内存分配 |
| `im2col.py` | Conv2d im2col 形状计算与布局辅助 |
| `__init__.py` | `compile_model()` 公共 API |

### 20.2 支持的操作

| PyTorch Op | NPU IR 映射 | 硬件支持 |
|------------|-------------|---------|
| `nn.Conv2d` | im2col + GemmOp + VecALUOp (bias + ReLU) | 软件 im2col + GEMM |
| `nn.Linear` | GemmOp + VecALUOp (bias + ReLU) | GEMM + VEC_ALU |
| `nn.ReLU` / `F.relu` | VecALUOp(RELU) | VEC_ALU |
| `torch.add` | VecALUOp(ADD) | VEC_ALU |
| `nn.BatchNorm2d` | 自动融合到 Conv2d weight/bias | 编译期折叠 |
| `nn.MaxPool2d` | PoolOp(MAX) + POOL 指令 | PoolEngine 硬件 |
| `nn.AvgPool2d` | PoolOp(AVG) + POOL 指令 | PoolEngine 硬件 |
| `nn.AdaptiveAvgPool2d` | PoolOp(AVG) + POOL 指令（1×1 时退化为 identity）| PoolEngine 硬件 |
| `torch.flatten` | 占位（reshape）| 无需指令 |

### 20.3 快速开始

```python
import torch
import torch.nn as nn
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.core import NeuralAccel
from rtlgen.sim import Simulator

# 定义一个小型 CNN
class TinyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1)
        self.relu = nn.ReLU()
        self.fc = nn.Linear(8, 10)
    def forward(self, x):
        x = self.conv1(x)
        x = self.relu(x)
        x = x.mean(dim=(2, 3))  # global average pool
        x = self.fc(x)
        return x

model = TinyCNN()
model.eval()
x = torch.randn(1, 3, 8, 8)

# 编译到 NPU
params = NeuralAccelParams(
    array_size=32,    # 脉动阵列维度
    data_width=16,    # 数据位宽
    acc_width=32,     # 累加器位宽
    sram_depth=65536, # SRAM 深度（16-bit words）
    num_lanes=32,     # 向量 ALU lane 数
)
compiled = compile_model(model, example_input=x, params=params)
print(f"Program length: {compiled.get_program_length()}")
print(compiled.to_asm())

# 运行周期精确仿真
npu = NeuralAccel(params=params)
sim = Simulator(npu)
sim.reset("rst_n")

# 加载程序到指令存储器
for addr, instr in compiled.get_program_load_sequence():
    sim.poke("prog_load_valid", 1)
    sim.poke("prog_load_addr", addr)
    sim.poke("prog_load_data", instr)
    sim.poke("prog_load_we", 1)
    sim.step()
sim.poke("prog_load_valid", 0)
sim.poke("prog_load_we", 0)

# 启动执行
sim.poke("prog_length", compiled.get_program_length())
sim.poke("run", 1)
sim.step()
sim.poke("run", 0)

# 推进仿真（驱动 AXI 从接口）
for i in range(5000):
    sim.poke("m_axi_arready", 1)
    sim.poke("m_axi_awready", 1)
    sim.poke("m_axi_wready", 1)
    sim.poke("m_axi_rvalid", 1)
    sim.poke("m_axi_rlast", 1)
    sim.poke("m_axi_bvalid", 1)
    sim.step()
    if sim.peek("state") == 0:
        print(f"Completed at cycle {i+1}")
        break
```

### 20.4 指令集架构

NPU 使用 64-bit 定长指令，格式如下：

```
[63:56]  opcode
[55:48]  func
[47:40]  rd
[39:32]  rs1
[31:24]  rs2
[23:0]   imm (for CONFIG)
```

| Opcode | 名称 | 说明 |
|--------|------|------|
| 0x0 | CONFIG | 配置 DMA 地址/长度/SRAM 地址，或 IM2COL 参数 |
| 0x1 | LOAD | 从片外 DRAM 加载数据到 SRAM |
| 0x2 | STORE | 从 SRAM 存储数据到片外 DRAM |
| 0x3 | GEMM | 脉动阵列矩阵乘法 |
| 0x4 | VEC_ALU | 向量 ALU 操作 |
| 0x5 | SFU | 特殊函数单元 |
| 0x6 | CROSSBAR | 数据交叉开关 |
| 0x7 | SYNC | 同步屏障 |
| 0x9 | IM2COL | 启动硬件 Im2Col 引擎 |
| 0xA | POOL | 启动硬件 Pool 引擎（MAX/AVG）|

### 20.5 ResNet-like CNN 示例

完整的 ResNet-like 编译/仿真示例位于 `examples/resnet18_npu.py`，包含：

- Conv2d + BN 自动融合
- 残差连接（add）
- ReLU 激活
- 多层堆叠
- 端到端周期精确仿真

运行方式：
```bash
python examples/resnet18_npu.py
```

### 20.6 参数配置

`NeuralAccelParams` 定义了硬件可配置参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `array_size` | 8 | 脉动阵列维度（MxM）|
| `data_width` | 16 | 数据位宽 |
| `acc_width` | 32 | 累加器位宽 |
| `sram_depth` | 256 | 每 bank SRAM 深度（words）|
| `num_lanes` | 8 | 向量 ALU lane 数 |

### 20.7 已知限制

1. **MemoryPlanner 基础 liveness analysis 已实现**：支持按 birth/death 区间分配和 best-fit 内存重用，但仍需自动 tiling 策略处理大网络。
2. **数值正确性**：PoolEngine 已通过与 PyTorch 对齐的 MAX/AVG 功能测试；Conv2d 仿真验证的是程序能否正确执行到完成，不涉及与 PyTorch 的数值对比（因 im2col 中间数据未在仿真中初始化）。

### 20.8 测试覆盖

NPU 相关测试位于 `tests/test_npu_*.py`：

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_npu_axi_dma.py` | DMA 引擎 FSM、AXI4 协议、64-bit 打包/解包 |
| `test_npu_core.py` | NPU 顶层模块、指令执行、状态机 |
| `test_npu_compiler.py` | 编译器 lowering、codegen、内存分配 |
| `test_npu_e2e_compile_run.py` | 端到端编译+仿真（空模型/ReLU/同步）|
| `test_npu_phase1.py` ~ `phase4.py` | 分阶段集成测试 |
| `test_npu_pool_unit.py` | PoolEngine 实例化、Verilog 生成、MAX/AVG 功能测试 |
| `test_npu_resnet18.py` | ResNet18 结构编译、POOL 指令验证、IM2COL dispatch |

全部 86 个 NPU 测试已通过。

### 20.9 PoolEngine 硬件池化引擎

NPU 集成了一块专用的 **PoolEngine** 硬件模块（`skills/cpu/npu/compute/pool_unit.py`），支持 2D MAX / AVG 池化，通过 `OP_POOL = 0xA` 指令启动。

#### 硬件架构

- **FSM 状态机**：`IDLE → WORK → READ → ACC → WRITE → DONE`
  - `WORK`：计算当前 kernel 窗口在输入 feature map 上的坐标，判断是否越界（padding 区跳过 READ）
  - `READ`：向源 SRAM 发起读请求，等待 `resp_valid`
  - `ACC`：根据 `pool_type` 执行 MAX 比较或 AVG 累加；同时推进 kernel 窗口计数器 `kw_r / kh_r`
  - `WRITE`：窗口遍历完成后，将结果写入目的 SRAM；AVG 模式下通过右移 `shift_amt` 实现定点除法
  - `DONE`：所有输出位置处理完毕，置起 `done` 信号

- **MAX 模式**：累加器初值为 `-32768`，每次与读出的 16-bit 有符号数比较取较大值
- **AVG 模式**：累加器初值为 `0`，窗口完成后结果右移 `shift_amt` 位（由编译器根据 kernel 面积计算）

- **SRAM 接口**：复用现有 SRAM 请求/响应总线，通过 crossbar MUX 接入 4 块 SRAM（A/B/C/Scratch），优先级：`DMA > Im2Col > Pool > Crossbar`

#### 编译器支持

Lowering（`skills/cpu/npu/compiler/lowering.py`）：
- `nn.MaxPool2d` → `PoolOp(pool_type=MAX)`
- `nn.AvgPool2d` / `nn.AdaptiveAvgPool2d` → `PoolOp(pool_type=AVG)`
- `AdaptiveAvgPool2d(output_size=(1,1))` 在输入已为 1×1 时退化为 identity，不生成 POOL 指令

Codegen（`skills/cpu/npu/compiler/codegen.py`）：
- `_emit_pool()` 复用 Im2Col 的空间配置寄存器（kh/kw/stride/pad/in_h/in_w/in_c/out_h/out_w）
- 额外发出一条 Pool 专用 CONFIG（`func=0x4`）设置 `pool_type` 与 `div_shift`
- 最后发出 `OP_POOL` 指令，`func[3:2]` 编码目的 buffer，`func[1:0]` 编码源 buffer

#### CONFIG 指令编码（修正后）

`OP_CONFIG` 的 `func[3:2]` 字段决定配置目标：

| `func[3:2]` | 目标 | `func` 范围 | 说明 |
|-------------|------|-------------|------|
| `00` | DMA | `0x0~0x3` | ext_addr[15:0/31:16]、dma_len、sram_addr |
| `01` | Pool | `0x4~0x7` | pool_type/div_shift、pool_src/dst_addr |
| `10/11` | Im2Col | `0x8~0xF` | kh/kw、stride、pad、in_h、in_w、in_c、out_h、out_w |

> **历史修复**：原代码将 `func=0x8~0xB` 错误路由到 Pool 分支，导致 Im2Col 前 4 个配置寄存器无法写入。已修复为 `func[3:2]` 三级译码。

#### 使用示例

```python
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams
import torch.nn as nn

class NetWithPool(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)   # 或 nn.AvgPool2d(2, 2)
        self.fc = nn.Linear(8 * 4 * 4, 10)
    def forward(self, x):
        x = self.conv(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

model = NetWithPool()
params = NeuralAccelParams(array_size=32, sram_depth=65536, num_lanes=32)
compiled = compile_model(model, example_input=torch.randn(1, 3, 8, 8), params=params)
print(compiled.to_asm())   # 可见 CONFIG + POOL 指令序列
```

---

*Updated for RTLCraft project — NPU with Conv2d lowering, IM2COL/POOL hardware engines, liveness-based MemoryPlanner, and ResNet18-scale target support.*
