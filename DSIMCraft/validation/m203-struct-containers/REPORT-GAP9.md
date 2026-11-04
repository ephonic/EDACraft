# dsim vs VCS 差距全景补充（probes4：30 项新探针覆盖此前未测域）

- 日期: 2026-10-31 | 二进制: 20261031T1625
- 本轮把历次清单之外的 VCS 能力域实测了一遍（事件/监控/绑定/虚接口/文件 IO/数组方法/OOP 进阶/线网/进程等）

## 一、本轮实测通过（与 VCS/ LRM 一致，此前未验证）

| 域 | 项 |
|----|-----|
| 验证语言 | **bind 语句**（验证 IP 注入）、命名事件 event/`->`/`@(ev)`、**final 块**、`expect` 之外的基本控制 |
| 参数与调用 | **ref 引用参数**（函数+任务）、函数默认参数 |
| TB 基建 | **$value$plusargs/$test$plusargs**、**文件 IO 全套**（$fopen/$fdisplay/$fscanf/$fclose）、$sformatf/$sscanf |
| 数组/字符串 | **数组定位方法全套**（find-with/sort/reverse/sum-with/min/max）、字符串方法（toupper/len/substr/atoi/compare/拼接） |
| OOP 进阶 | **$cast 动态转换**、**抽象类（virtual class + pure virtual）**、rand_mode 冻结 |
| 杂项 | 变量部分选择 `[i +: 8]`、网络延迟 `wire #5`、process::self + wait fork、$onehot/$onehot0/$isunknown、$countones |
| 语义对齐 | t=0 声明初始化触发 `always @(v)`（与 VCS 逐字节一致）、拼接截断保低位（一致）、%h 补零（一致） |

## 二、本轮新发现的不支持项（追加进差距清单）

| # | 项 | 影响 |
|---|-----|------|
| 1 | **virtual interface（类中虚接口属性）** | 🔴 **UVM 驱动/监视器连接的核心机制**——与此前 UVM 冒烟阻塞同级 |
| 2 | $monitor / $strobe | 🟠 传统 TB 观察，常见于旧代码 |
| 3 | interface class（implements） | 🟡 SV-2017，UVM 不依赖 |
| 4 | 程序化连续赋值（过程 assign/deassign） | 🟡 legacy |
| 5 | 模块 type 参数（class 已支持） | 🟡 泛型复用 |
| 6 | wand/wor/tri1 等线网类型与强度 | 🟠 门级/模拟协同场景 |
| 7 | expect 语句 | 🟡 |
| 8 | checker 块 | 🟡 形式验证复用单元 |
| 9 | $sdf_annotate 任务形式 | 🟠 门级流程兼容（CLI --sdf-annotate 已可用，多数流程可切换） |
| 10 | sequence 范围 `##[1:3]` | 🟡 断言表达力 |
| 11 | $typename | 🟢 调试 |
| 12 | 字符串字面量方法接收者（`"42".atoi()`） | 🟢 |

## 三、累计完整差距清单（相对 VCS，截至本构建）

### 仿真正确性
- 无已知缺陷（历轮疑点均经 VCS 交叉证伪）

### 语言（按对 UVM/日常 TB 的影响排序）
1. UVM 阻塞链：参数化容器 string 特化（uvm_queue#(string)）、类内 localparam、string-struct 属性、类句柄关联索引、**virtual interface**
2. 随机化进阶：dist / solve...before / randc
3. 断言进阶：expect、checker、`##[m:n]`、$assertoff、$sampled（未测）、multi-clock/global clocking（未测）
4. 覆盖率进阶：transition bins、with-function sample
5. mailbox.peek、program、let、$monitor/$strobe、$typename
6. 过程 assign/deassign、模块 type 参数、interface class、线网类型/强度
7. specify 时序检查（$setup/$hold）、$sdf_annotate 任务形式

### 工具/流程（VCS 商业特性面）
- 交互式调试（断点/单步/运行时 force CLI）、代码覆盖率（line/toggle/FSM + urg 合并）、UPF 低功耗仿真、FSDB/Verdi 对接、save/restore、PLI/VPI/ACC C 接口（有 DPI-C）、多线程仿真（--threads 实验性）、运行时 min/typ/max 角标切换

## 四、结论

1. **RTL + 手写 TB + SDF 场景**：本轮再验证 18 项此前未测能力全部正确（bind/ref/fileIO/数组方法/$cast/抽象类等），可用面进一步坐实
2. **UVM 场景**：本轮新增确认 **virtual interface** 为并列阻塞项（与 uvm_queue#(string) 同级），建议与"参数化容器 string 特化、类内 localparam"一起列为下一批修复
3. **门级场景**：CLI SDF 已可用；补 $sdf_annotate 任务 + specify 时序检查可提升存量流程兼容性
4. 语义对齐质量持续可信：本轮 3 个疑似 bug（t=0 触发、%h 补零、拼接截断）经 VCS 交叉全部证伪——**第五次"dsim 无辜"**

## 五、复现
`cd rtl-tests/complex/probes4`（30 项探针：u01~u30）
