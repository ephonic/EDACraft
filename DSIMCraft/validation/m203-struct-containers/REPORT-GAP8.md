# dsim 20261031T1625 功能完备性测试 + UVM 加载冒烟

- 日期: 2026-10-31
- 二进制: releases/20261031T162541186540Z-5e9008046209（上轮: 20261031T1522）

## 一、缺口清单复查

program block、`let`、specify 时序检查、$assertoff、dist/solve-before/randc、mailbox.peek、covergroup transition bins / with-function sample——**与上轮一致，无新增修复**。

## 二、UVM-2020.3.1 加载冒烟（本轮重点）

源码: evidence/m152-abstract-casts/uvm-reference/accellera-2020.3.1（官方 Accellera 包）
目标: 编译 uvm_pkg + 最小 hello_test（run_test/objection/`uvm_info`）

### 进展
dsim 编译推进到 **base/uvm_queue.svh**（uvm_base.svh 约 2/3 处，拼接后第 16k 行）——
类/静态/参数化类/工厂宏等大部分 UVM 基建语法已被吃下，随后撞上以下阻塞点：

### 阻塞清单（按出现顺序，均已最小化定位）
| # | 构造 | 位置 | 定性 |
|---|------|------|------|
| 1 | **类内 localparam/parameter** | uvm_component.svh:1530 等 9 处 | 小缺口；探针 `/tmp/clp.sv` 三行复现 |
| 2 | **struct 含 string 成员** 作属性/队列元素 | uvm_factory.svh:622（2 个 typedef） | 中等 |
| 3 | **类句柄作关联数组索引**（`bit m_types[uvm_object_wrapper]`） | uvm_factory.svh:619（仅 1 写点，可桩） | 小缺口 |
| 4 | **参数化容器以 string 实例化**（`uvm_queue#(string)` 展开后的 `T queue[$]`） | uvm_queue.svh:58 | **架构性阻塞**——UVM 全库大量使用 |
| 5 | 诊断误导：队列构造报 "associative class property..." | — | 诊断问题 |

补丁实验：#1（localparam→static 成员）与 #2/#3 桩化后编译继续推进至 #4；
#4 出现于 base/uvm_queue，之后 tlm/comps/seq/reg 预计还有更多 string 参数化实例化点。

### 冒烟结论
1. **距离 UVM 编译通过的差距是"参数化容器 + string 负载"一类问题**，而非类/OOP 基建（已过关）
2. 建议优先级：#4（架构）> #1（类内 localparam，工作量小）> #2（string-struct）> #3
3. m152 证据目录表明团队已有 UVM 参考跟踪；本轮清单可直接作为其消缺输入

## 三、标准回归（全绿）

复杂设计 10/10、旧设计 6/6（与 UVM 冒烟互不影响）。

## 四、复现
```
UVM=evidence/m152-abstract-casts/uvm-reference/accellera-2020.3.1/src
bin/dsim --top tb -o smoke +incdir+$UVM +define+UVM_NO_DPI $UVM/uvm_pkg.sv hello.sv
# 阻塞点逐个复现：/tmp/clp.sv（类内 localparam）
```
