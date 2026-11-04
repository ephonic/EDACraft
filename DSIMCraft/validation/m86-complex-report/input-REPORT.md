# dsim 0.13.0 复杂 RTL 测试报告（complex 轮）

- 日期: 2026-10-25
- 二进制: bin/dsim -> releases/20261024T121303184886Z-436e883cea0d（**晚于 REPORT.md v3 的 20261024T1041**）
- 测试目录: rtl-tests/complex/{rv32i,axil,arbiter,muldiv,crc32,svstress,probes}
- 复跑: `./complex/run_all.sh`（新测试）、`./regress.sh`（旧回归）、`cd complex/probes && ./run.sh`（探针）

## 一、复杂设计测试（6/6 PASS）

| 设计 | 规模/要点 | 结果 |
|------|-----------|------|
| **rv32i** 单周期 CPU | RV32I 整数子集全集：ALU 10 op、OP-IMM 8 op、6 种分支、jal/jalr/lui/auipc、lb/lbu/lh/lhu/lw/sb/sh/sw（字节/半字 lane merge）、32×32 寄存器堆、分离 imem/dmem/调试地址空间；python 汇编器（asm.py）生成程序，8 个存储映射调试寄存器自校验 | **PASS**：142 指令全部正确，1 拍/指令；期间发现 unique-case 检查工作正常（对非分支指令的 f3 未覆盖给出警告） |
| **axil** AXI4-Lite 从机 | AW/W/B/AR/R 五通道 FSM、WSTRB 字节合并、RO 门控计数器、RW1C 粘滞标志、未映射地址 SLVERR、SLVERR 后总线恢复；TB 为 task BFM + $urandom 随机背压 + 32 次随机 strb 写 vs 影子模型 | **PASS**（7/7 子项） |
| **arbiter** 轮询仲裁 | 4 客户端 FIFO（深度 8）+ 旋转优先级仲裁 + 每客户端地址计数；随机占空比推入 256 字，校验：严格旋转序（全忙时 last+1）、每客户端顺序/无丢失/无重复、排空完整性 | **PASS**（256/256） |
| **muldiv** 乘除法器 | Booth 基-4 有符号 16×16→32 迭代（含 -32768×-32768=2³⁰ 角点）+ 32/16 恢复余数除法（RISC-V 除零语义 q=-1,r=被除数）；12+11 角点 + 120+120 随机向量 | **PASS**（263/263） |
| **crc32** 流式 CRC | 反射多项式 0xEDB88320，1 字节/拍，SOF/EOF 帧、随机 valid 间隙；KAT "123456789"→CBF43926 + 20 随机帧 vs 独立非反射参考算法（位反转+0x04C11DB7） | **PASS**（22/22） |
| **svstress** SV 集成 | generate-for 实例阵列、if-generate、函数内 for 循环、casez/casex 256 全扫描、$countones/$bits/$clog2 常量运算、enum round-trip | **PASS**（7/7） |

### 仿真正确性结论
本轮 6 个设计共出现 6 处 MISMATCH，逐一定位后 **全部为测试侧 bug**（axil 握手时序竞态、拼接位序写反、tag 初值错、casez/casex 参考模型掩码错、bltu 方向写反、计数器使能位疏忽），dsim 计算零错误——与 v1~v3 三轮结论一致：**仿真语义始终可信**。

## 二、探针结果（17 项）

### 已支持（12 项，其中 4 项为相对 v3 报告的新增能力 ★）
| 特性 | 结果 |
|------|------|
| ★ property / assert property 并发断言 | **可用**：`|=>` 重叠蕴含、`disable iff`、逐拍触发均正确（p01/p16）；限制：else 动作仅单语句，begin/end 块拒绝 |
| ★ interface / modport | **可用**：端口穿越、modport 连接正确（p02） |
| ★ 未打包数组层次引用（u.mem[0]） | **可用**（p03） |
| ★ package 可变变量 | **可用**：含函数内修改（p15） |
| $readmemh | **可用**（p17） |
| 未打包数组作端口 | **可用**（p09） |
| 流式拼接 {<<{}} | **可用**（p07） |
| always_latch | **可用**，锁存/保持语义正确（p11） |
| inside 操作符 | **可用**（p12） |
| 尺寸转换 N'(expr) | **可用**（p13） |
| $urandom/$urandom_range（随机 TB 中大量使用） | 持续正确 |

### 仍不支持（6 项，报错均带行列）
| 特性 | 报错形态 |
|------|---------|
| 函数递归（运行时） | `error[6725]: unknown err.`（不透明） |
| 常量上下文函数调用（localparam = f(x)） | `error[6520]: unknown err.`（不透明） |
| $past/$rose/$stable | 语法错误 |
| force/release | 语法错误 |
| 未打包 struct | 语法错误 |
| $writememh | ✅ 消息清晰："unsupported system task $writememh" |

### 边缘行为
- 参数/genvar 位选（`DEPTH[3:0]`、`g[7:0]`）被拒：`identifier does not name a supported value`——可规避，消息尚可
- 字符串字面量与整数混合运算被拒：消息清晰

## 三、工具缺陷（诊断类，非仿真错误）

1. **[DEBUG] 输出泄漏**：非法标识符重声明（如端口与内部 wire 同名、reg 重复声明）时打印 `[DEBUG] reg_var_symbol redefine check: ...` 后**静默继续编译**，应报告语义错误（svstress/p16 两次触发）。
2. **"unknown err." 残留**：新语义错误路径（递归、常量函数、重声明初始化）仍返回不透明错误，与 v2 修复的 6305 同类，属诊断质量缺口。
3. 零延迟环检测（event/instruction limit）工作正常，但消息未说明是启发式判定（本轮它正确抓住了 TB 死锁）。

## 四、旧设计回归（新二进制，6/6 PASS）

fifo / alu(1029) / uart / fir(201) / cdc / svfeatures 全部 PASS —— 上述新增能力未引入回归。

## 五、结论

1. 复杂度上升到 CPU 级（单周期 RV32I 全整数子集 + 汇编程序自校验）后，dsim 仿真语义依然零错误。
2. 语言覆盖在 v3 之后继续收敛：并发断言、interface、未打包数组层次引用、包变量四个"最大缺口"已全部落地且语义正确。
3. 剩余缺口集中在：函数递归/常量函数（验证 IP 常用）、$past 族（断言配套）、force/release、未打包 struct、$writememh。
4. 最需要修的是两条诊断问题：DEBUG 打印泄漏 + unknown err 残留。
