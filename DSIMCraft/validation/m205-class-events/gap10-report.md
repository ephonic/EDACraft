# dsim 20261101T0309 功能完备性 + UVM 冒烟（重大推进）

- 日期: 2026-11-01
- 二进制: releases/20261101T030946582792Z-b7415868c1e4（上轮 UVM 冒烟: 20261031T1625）

## 一、UVM-2020.3.1 冒烟：从 base/uvm_queue 推进到 reg/uvm_reg_map（≈95% 包体）

上轮阻塞的 `uvm_queue#(string)`（参数化容器 string 特化）**已修复**。本轮逐项桩化后编译到达：

base 全部 → dap → tlm1 → comps → seq → tlm2 全部 → reg 的第 8/16 个文件（uvm_reg_map.svh:121）

### 本轮越过并确认已修复/可编译的 UVM 关键面
- uvm_factory（含 extern 方法、宏工具）、uvm_component（build/connect/run_phase 框架）、uvm_root/phases
- uvm_object 系（field 宏、printer/comparer）、uvm_pool、uvm_registry、uvm_config_db
- uvm_tlm_fifo/analysis（TLM1）、uvm_sequencer/driver/monitor/agent（comps）
- uvm_sequence/seq_item、objection/callback/scoreboard 框架
- uvm_tlm2_generic_payload（桩后）、uvm_reg 前半部（uvm_reg/mem/vreg/block 等）

### 剩余阻塞（全部已最小化定位，按优先级）
| # | 构造 | 出现面 | 定性 |
|---|------|--------|------|
| 1 | **类句柄作关联数组索引** | reg 层大量（m_regs_info[uvm_reg] 等数十处；factory 1 处已桩） | 🔴 **当前终点**，架构性 |
| 2 | **event 作类成员** | uvm_event/objection/barrier/heartbeat/pool/transaction（本轮已全部桩过：bit+wait/直赋值） | 🟠 |
| 3 | rand 修饰非标量/枚举成员 | tlm2 GP、reg（rand enum、rand dyn-array、rand 类句柄数组） | 🟠 |
| 4 | 动态数组作类属性 | tlm2/reg ~20 处（已桩 → 队列） | 🟠 |
| 5 | 类内 localparam（上轮 9 处，已桩 → static） | base | 🟡 |

**桩化补丁共 5 类 ~30 处**，若 #1 修复，剩余 #2~#5 仍需处理才能编译通过原生 UVM。

## 二、常规缺口复查（本轮无变化）

virtual interface、$monitor/$strobe、expect、checker、##[m:n]、defparam、嵌套模块、randcase、sequence 操作符（and/throughout）、程序化 assign/deassign、模块 type 参数、interface class、线网类型/强度、$typename、program、let、specify 时序检查、$assertoff、dist/solve/randc、mailbox.peek、cover transition bins/with-sample——全部仍不支持。

## 三、回归（全绿）

复杂设计 10/10、旧设计 6/6、probes 20/20、probes2 12/12。

## 四、结论与建议

1. 本轮单点修复（参数化容器 string）使 UVM 编译推进 **~95% 包体**；距原生编译仅剩 4 类构造
2. 修复优先级建议：**#1 类句柄关联索引**（一通全通）> #2 event-in-class（UVM 事件/objection 语义必需，bit 桩不保真）> #4 动态数组类属性 > #3 rand-非标量 > #5 类内 localparam
3. #1+#2 修复后建议用**未打桩的原始 UVM** 重新冒烟（当前补丁树在 /tmp/uvm_p，含全部桩清单注释）

## 五、复现
```
cd /tmp/uvmsmoke && /Users/yangfan/vibe-coding/dsim-test/bin/dsim --top tb -o smoke2 \
  +incdir+/tmp/uvm_p +define+UVM_NO_DPI /tmp/uvm_p/uvm_pkg.sv hello.sv
```
