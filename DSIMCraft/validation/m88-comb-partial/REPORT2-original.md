# dsim 0.13.0 复杂 RTL 测试报告（complex 轮 2：流水线 CPU / AXI4 / Cache / SPI / 门级 SDF）

- 日期: 2026-10-25
- 二进制: bin/dsim -> releases/20261024T121303184886Z-436e883cea0d（同轮 1）
- 新增目录: rtl-tests/complex/{pipecpu,axi4,cache,spi,probes2}
- 复跑: `./complex/run_all.sh`（全部 10 项）、`cd complex/probes2 && ./run.sh`

## 一、新增复杂设计（4/4 PASS，累计 10/10）

| 设计 | 规模/要点 | 结果 |
|------|-----------|------|
| **pipecpu** 5 级流水 RV32I | 冒险 torture 程序：EX/MEM+MEM/WB 前递（含 load 数据 MEM 级组合前递）、load-use 阻塞（含 store-data/分支操作数变体）、EX 段分支解析 + 2 拍冲刷、RF 写前读旁路、jal/jalr 链接与返回；47 条指令，8 项 dbg 断言 | **PASS**：41 指令 / 62 周期（CPI≈1.51，含惩罚） |
| **axi4** 完整 AXI4 突发从机 | INCR/WRAP（2^k 窗口）读写、wstrb 逐拍合并、wlast 位置校验、FIXED→SLVERR、错误注入（早 wlast）、2 深度 AR 队列 + 非延迟读超前完成（**乱序完成验证**）、40 组随机突发 vs 影子模型、最终全存储比对（层次引用未打包数组） | **PASS**（8/8 子项） |
| **cache** 2 路组相联 | 写回 + 写分配、LRU 替换、脏逐出、行填充、**flush 全脏行回写**；冷失效/命中、同组冲突驱逐链、400 次随机读写 vs 平面参考模型、**严格 flush 后 1024 行全比对**、4096 字全读扫描 | **PASS**（hits=3082 misses=1466） |
| **spi** SPI 主机 | 全部 4 种 CPOL/CPHA 模式 × /4 //8 分频 × 5 种帧模式 × 双片选，回环校验 rx==tx、空闲 SCK=CPOL 电平 | **PASS**（40/40 传输） |

## 二、本轮发现的 dsim 缺陷（1 个仿真语义 bug + 若干观察）

### 1. `$signed() >>>` 在三元条件分支内退化为逻辑移位（仿真错误级）
```systemverilog
wire [31:0] r_tern = sel ? ($signed(a) >>> sh) : (a >> sh);   // 错：得 0x003FFFFF
wire [31:0] r_direct = $signed(a) >>> sh;                      // 对：0xFFFFFFFF
```
- 复现: probes2/p21_sra_cond.sv（5 种写法对比，仅三元形式错）
- 影响: pipecpu ALU 的 sra 实现直接踩中（dbg3 差一个符号扩展）
- 规避: if/else 语句或独立赋值/函数形式（probes 已验证三种规避均正确）
- LRM: `>>>` 的算术语义由左操作数**自决**的符号性决定，与所在表达式上下文无关

### 2. 诊断/工具观察（非仿真错误）
- `$urandom` 默认种子在**不同编译产物间不可复现**（同一次运行内确定；改代码重编译后序列改变）——需可复现时应显式种子
- VCD 输出已支持（`--wave-support` + 运行时 `--waveform x.vcd`，文本格式，含 $timescale/$var）——v3 报告中"波形仅 DWF 二进制"的结论已过时
- 波形文件已存在时拒绝覆盖且报错信息可读

## 三、probes2 结果（9 项全过）

| 探针 | 结论 |
|------|------|
| p21 三元分支内 `>>>` | **BUG 确认**（见上） |
| p22 变索引 NBA 写未打包数组（索引同块 NBA 更新） | 正确 |
| p23 多个 `always #delay` 进程 | 正确 |
| p24 文本 VCD 波形 | 可用 |
| p25 `+incdir`/`+define`/`ifdef` | 可用 |
| p25 `-f` 文件列表 | 可用 |
| p26 `--sdf-check` 独立 SDF 解析 | 可用（JSON 摘要：4 cells / 7 IOPATH） |
| p26 `--sdf-bind-check` 绑定（liberty+gate models+netlist） | 可用（7/7 条目绑定，含 TIMESCALE 检查） |
| p26 `--sdf-annotate` 带延迟仿真 | 可用（编译+运行通过，功能正确） |

**门级/SDF 全流程为本次新验证的能力域**（此前报告从未覆盖）：SDF 解析 → 实例/路径绑定 → 注记仿真三级均工作。注意点：SDF 需 `(TIMESCALE 1ns)` 否则报错（可读）；Liberty 函数需用 `!` 而非 `~`；门级网表解析器只接受纯网表文件（含 TB 的文件报语法错）。

## 四、测试侧调试记录（dsim 无辜的误报，供轮次统计）

本轮 4 个设计共出现 ~15 处 MISMATCH，全部定位为测试侧问题，dsim 仿真计算零错误：
- pipecpu: store 地址误用 imm_i、halt 检测未屏蔽 redirect（2 处 RTL/TB 逻辑）
- axi4: BFM 握手边沿记账差一拍（W/AR 双重接受）、监视器未初始化（X==X 恒假）、`wexp` 位宽截断、wrap 长度表达式溢出
- cache: TB 存储行字节序与 DUT 相反、mready 常高致命令丢失、flush 双脏行只回写一路 + **f_w0 复位遗漏（X 传播正确地跳过分支）**
- axi4 DUT 侧被我修掉的: wlast 判据差一拍、wready 死锁、rb_cnt 未复位（该三项为 DUT 设计错误被正确 TB 暴露，dsim 行为均正确）

值得一提：cache 的 f_w0=X 案例中，dsim 的 **X 条件传播语义完全正确**（X 条件跳过分支），正是它让缺陷显形。

## 五、结论

1. 复杂度上探至 5 级流水线（前递/阻塞/冲刷）、完整 AXI4 突发（乱序完成）、写回式缓存（flush 一致性）、SPI 四模式后，dsim **仿真语义仅发现 1 处真实错误**（三元内 `>>>` 符号性丢失），其余全部正确。
2. 门级 + SDF 注记流程首次验证可用，是 RTL 仿真之外的完整能力域。
3. 诊断质量总体良好；遗留：`$urandom` 跨编译不可复现、参数/integer 位选报错语义仍偏晦涩。
4. 建议 bug 修复优先级：**P0 三元 `>>>`**（影响 SRA 之类常用写法的正确性）> P1 `$urandom` 种子 > P2 参数位选报错消息。
