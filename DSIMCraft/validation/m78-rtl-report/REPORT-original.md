# dsim 0.13.0 RTL 测试报告

日期: 2026-10-24 | 二进制: releases/20261024T024217767796Z-6a75b0556da2 (dsim 0.13.0)

## 测试设计（6 个，全部仿真结果正确）

| # | 设计 | 覆盖点 | 结果 |
|---|------|--------|------|
| 1 | sync_fifo (16x8) | 存储阵列/指针回绕/满空标志/上下溢保护/almost_full | 6/6 PASS |
| 2 | alu (16bit, 16 op) | 加减乘除模/移位/算术右移/有符号比较/CLZ/ROL/溢出标志 | 1029/1029 PASS（含 1024 随机 golden 对拍）|
| 3 | uart_tx (8N1+偶校验) | 5 状态 FSM/波特率计数/移位寄存器，TB 端软件接收解码 | 10 字节全对 |
| 4 | fir4 (3 级流水) | 流水线 MAC/有符号乘/反压间隙/延迟线 | 201 样本 golden 对拍全对 |
| 5 | cdc_async_fifo + pulse_sync | 双时钟域(100M/66M)/Gray 码指针/2FF 同步器/脉冲同步 | 182 字节跨域有序传输，11/11 脉冲 |
| 6 | sv_features | enum(.next/.prev)/packed struct/always_ff/always_comb/unique case/$countones/立即断言 | PASS |

仿真语义可靠性：非常好。测试期间 4 处 "失败" 全部为测试基准预期写错，dsim 计算结果均为正确（SRA、FIFO 空读、struct 位拼接、X 态 nibble 显示）。零延迟组合环（full↔wnext_gray）被运行时保护正确拦截。

## 发现的缺陷

### A. 崩溃（严重）
1. **task 定义 → 编译器 SIGSEGV (rc=139)**。任何 `task ... endtask`（即使无时序控制）都会使编译器崩溃，无任何诊断输出。最小复现见 cases 记录。

### B. 功能缺失（合法 SV 被拒）
2. `package`/`import` 不支持（语法错误）
3. `property`/`assert property`（并发断言）不支持（语法错误）
4. `$random` / `$urandom` / `$urandom_range` 全部不支持（"unknown err"）
5. **层次化引用**（`dut.internal_sig`）不支持 → 无法在 TB 中观测 DUT 内部信号，验证工作流受影响最大
6. struct 类型作 function 形参不支持（语法错误，级联空错误）
7. 复制个数仅接受裸字面量/参数名：`{(W-1){...}}`、`{2*W{...}}` 等常量表达式被拒（IEEE 1364/1800 合法）
8. `always_ff` 目标变量带声明初始化器（`logic q = 0;`）被拒为 "another writer"（VCS/Questa 接受，严格度分歧）
9. enum `.name()`（字符串返回）不支持；`.next()/.prev()` 正常
10. assert 动作块内非阻塞赋值（`else x <= 1`）不支持；阻塞赋值正常
11. 端口声明 `input var logic` 不支持（SV-2009）

### C. 诊断质量
12. 大量错误消息为空（`error[6115]/[6110]` 空文本）或 "unknown err"（error[6400]/[6702]），定位困难
13. 语法错误后级联报错位置偏移，真实根因（如 struct 形参）不在报错行

### D. 波形
14. `--waveform` 输出为专有 DWF 容器（schema: dsim.wave.prototype.v1，zstd/raw 负载），**非标准文本 VCD**，扩展名 `.vcd` 也仍为 DWF；元数据结构（scope/var）完整

## 已验证可用能力
编译型流程（compile→simv）、`$clog2`、参数覆盖、异步复位、多时钟、`@(negedge)`、`repeat`/`while`/`forever`、`$readmemh`、function（含 automatic）、for 循环内联 int 声明、除法/模/有符号运算、`$countones`、`%0t` 时间格式、X 态显示、零延迟环检测、`--emit-cpp`、DWF 波形（zstd 压缩）

## 复现目录
- rtl-tests/fifo|alu|uart|fir|cdc|svfeatures/  (rtl.sv + tb.sv，各目录可直接编译运行)
- 任务崩溃最小复现：单文件含 `task incr; begin a=a+1; end endtask` 即可触发

## 规避建议（RTL 编码风格）
- 禁用 task，用宏/内联展开替代
- 随机激励用 LFSR 自实现
- DUT 内部观测信号全部引出为端口
- 复制个数用 localparam 中转
- 变量声明置于首次使用之前，且 always_ff 目标变量不写初始化器
