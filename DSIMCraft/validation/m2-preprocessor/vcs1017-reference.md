# VCS 仿真策略逆向分析报告（RTL / 门级 / 门级+SDF / 并行）

- 日期：2026-10-17
- 工具：Synopsys VCS / Design Compiler W-2024.09（`source /apps/EDAs/syn.bash`）
- 测试设计：`/home/yangfan/digi/cases/designs/modmult/mul/barr_mult`（barr_modmult，256-bit Barrett 模乘法器，800MHz 综合）
- 分析手段：对 `vcs` 生成的中间产物（csrc/ 生成的 C 源、archive .so、simv ELF）做符号分析 + objdump 反汇编 + callgrind 指令级剖析 + VCS 自带 `-simprofile` 剖析 + gdb 线程/栈采样 + `/proc` 线程观测
- 复现目录：`/home/yangfan/vcs/modmult_sim/{rtl_sim, gate_sim, sdf_sim, lib, perf}`

---

## 1. 被测对象与实验矩阵

| 仿真 | 设计源 | 规模 | 时钟 | 结果 |
|---|---|---|---|---|
| RTL | barr_modmult.v + 14 个子模块（js_zk_mul / approx_msb_mul / lsb_half_mul 等） | 15 个模块 | 1.25ns(800MHz) | **TEST PASS**（生成 golden 向量 128 笔） |
| 门级（无 SDF） | barr_modmult_gate.v（DC compile_ultra 产物） | 529,549 行；**300,909 个 cell 实例**；111 种单元（ND2/OAI21/XOR2/FA1/DFQD1/…） | 1.25ns | **TEST PASS，与 RTL golden 逐位一致 (128/128)** |
| 门级+SDF | 同上 + dc_shell `write_sdf` 产物（sanitize 后） | SDF 165MB：529,684 条 IOPATH + 790,222 条 INTERCONNECT + 43,394 SETUP / 43,248 HOLD / 2,854 RECOVERY | 2.5ns | **TEST PASS (128/128)**；1.25ns 下 127/128（首拍 X，见 §5.4） |

说明：
- 该设计是**近似 Barrett 模乘**（approx_msb 乘法器），输出与精确 `a*b mod p` 全部不同（128/128），
  因此门级验证采用标准 **golden-vector 回放比对** 流（RTL 跑 GOLDMODE 生成向量文件，门级/门级+SDF 跑 CHKMODE 逐笔比对），这本身就是三种仿真共享同一 TB 的关键手段。
- 门级仿真所需标准单元 Verilog 模型在本机没有现成库，用脚本 `lib/gen_libmodels.py` 直接解析 1.2GB 的
  `tcbn12ffcllbwp6t16p96cpdtt1v25c_ccs.lib`：解析 `cell/pin/ff` 组、把 Liberty 布尔函数
  （`& | ^ ! '` 及隐式与、`+` 表或）翻译成 Verilog，并为每个单元生成 `specify` 模块路径
  （`(A => Z) = 0;`、FF 的 `(posedge CP => (Q:1'bx)) = 0;`）与 `$setup/$hold/$recovery/$removal` 占位，
  从而同时支持零延迟门仿和 SDF 反标（共 111 单元：107 组合 + 4 时序，含 DFCNQD1 异步清零）。

---

## 2. VCS 编译流水线（反编译自 csrc/ 产物与链接命令）

对三次编译加 `-k` 保留产物后可见完整流水线：

```
vcs (perl 驱动)
 ├─ Parsing design file ...            # 前端解析
 ├─ elaboration ("elab + .x s to elab")
 ├─ "Starting vcs inline pass..."      # 内联代码生成
 │    ├─ N modules -> LLVM 后端原生代码   （链接行可见 rmar_llvm_0_0.o / rmar_llvm_0_1.o）
 │    ├─ 其余模块 -> csrc/_NNNN_archive_1.so（daidir 内，模块级共享库）
 │    └─ csrc/rmapats.c  ← 明文 C：事件调度模板（见 §4.1）
 └─ g++ -o simv ... -lvcsnew -lsimprofile -luclinative ... -lpthread
```

要点：
1. **VCS 是"编译型"仿真器**：设计被编成原生机器码。函数按 `M_/F_/T_/N_VCSgd_<hash>` 与
   `<10位随机码>edkj` 混淆命名（例 `M_VCSgd_PfvGg`、`rbUfHpnkedkj`），符号表保留但语义名被剥离。
2. 代码分两类载体：设计求值代码在 `daidir/_N_archive_1.so` / `rmar_llvm_*.o`；运行时内核在
   `libvcsnew.so`（导出 `Wmadd/Wmsub/Wmmul/Wconcat/Wvecblt` 等字级向量原语和全套调度函数）。
3. simv 是薄壳 ELF（145 个符号），动态链接 9 个 Synopsys 运行库（libvcsnew/libvirsim/libsimprofile/libuclinative/libsnpsmalloc…）。
4. RTL 编译只重编 5 个模块、其余进 archive —— 增量编译按模块粒度（"recompiling module js_zk_mul_level1 …"）。

---

## 3. RTL 级仿真策略

### 3.1 求值模型：字级编译代码 + 事件驱动
- callgrind（Ir 指令数）显示 RTL 稳态由**设计自身的混淆求值函数**（`*edkj` 系列，位于 libvcsnew 内联的 rmar_llvm 代码）主导，其内部大量调用**字级向量原语**：
  `Wmadd`（加）、`Wmsub`、`Wmmul`（乘）、`Wconcat`、`Wcopy0`、`Wvecblt_lhs0`（向量比较/位选择）、`mdivcore`（本 TB 的 `%` 模除）。
  即 VCS 把 256-bit 的 RTL 表达式树编译成对 32/64-bit 字数组的循环/向量化运算，而不是逐 bit 网表求值 —— **RTL 层保留了运算符语义**。
- `-simprofile time`：VERILOG(Module eval) ≈ 50%，KERNEL Scheduler ≈ 4~5%，UCLI ≈ 20~28%（本设计太小，启动占比高）。
- 性能：190ns 仿真 0.41s CPU；即使 41us/32768 笔也仅 0.75s CPU，数据结构 4.2MB —— RTL 求值是"事件少、每次重"的模式。

### 3.2 调度模型（三种仿真共用，明文证据在 csrc/rmapats.c）
生成的 `schedNewEvent()` 揭示了内核事件队列结构：

```c
I1747 = vcs_clocks + delay;                    // 目标时刻
I1749 = I1747 & ((1<<fHashTableSize)-1);       // ① 时间轮(timing wheel)哈希桶
if (I1747 < vcs_clocks) sched_millenium(...);  // ② 溢出"millenium"远期队列
else if (peblkFutQ1Head && delay==1) { 挂到 FutQ1 尾 } // ③ delay==1 的专用快队列
```

- **哈希时间轮 + FutQ1（下一槽）快速链 + millenium 溢出队列**；
- 事件对象是 EBLK（evaluation block，"recompiling/inline pass"中的最小调度单元），有 `lastEBlk/lastEvtID` 跟踪；
- 内核符号簇佐证两段式调度：`execSchedloopedEvents / ExecuteOneCycle / ProcessLevelizedQueue(Opt) / cleanwheel / fh_set_deltacycle / callOrSchedForRace / ExecuteAccordingToOrder`。
- 事件按 LER（Levelized Event Representation，符号中的 `LeanLerOpt / SemiLer` 变体）分层排序，消 delta 竞争；NBA 更新走 `NBA_Semiler / Sinitnba`（非阻塞赋值队列）。
- 128 核机器上 RTL simv **Threads: 1**（纯单线程内核）。

---

## 4. 门级仿真策略（无 SDF，零延迟）

### 4.1 求值模型：位级展开 + 模块路径(模块路径延迟)机制常开
- 门级把 300,909 个实例展开成 60 个模块的原生代码；门级求值函数（`F_VCSgd_reYIK_*` 等）是**无调用的叶子函数**——纯内联位运算（and/or/xor/test），与 RTL 的字级原语模式完全不同。
- 关键发现：即使所有 specify 延迟为 0，VCS 仍为带 `specify` 的单元走**模块路径延迟(MPD, Module Path Delay)**机制：
  - `-simprofile`：KERNEL 中 **"Module Path Delay Computing" 占 25%**；
  - callgrind Top：`scheduleuna_th_nobuf` 22.0%、**`doMpd32` 19.2%**（32-bit 模块路径延迟求值）、`SchedSemiLerMP1` 9.1%（MP=Module Path 的 semi-LER 调度）、`CauseAllTS32LeanLerOpt` 4.7%（值变化因果传播）、`schedule_delay_event(+_common)` 8.0%（时间轮插队）、`initMPA`（module path array 初始化）、`NBA_Semiler`。
- 结论：**"零延迟门仿"并非把门当纯组合逻辑求值，而是逐 cell 输入→输出的 pin-to-pin 路径事件调度**；
  这解释了门仿比 RTL 慢 15 倍（6.1s vs 0.41s）且内存 48.5MB vs 0.1MB —— 300K 实例每个输入沿都产生路径延迟事件。

### 4.2 一致性
- 与 RTL golden **128/128 逐位一致**（`+delay_mode` 默认惰性(inertia)延迟，0 延迟下无毛刺效应）。

### 4.3 doMpd32 反汇编要点（libvcsnew.so）
```
doMpd32:
  检查 fParallelEBLK / fFgpDynamicToggle (并行求值开关,默认关)
  vcs_simpEBlkStart/End                  (simprofile 埋点)
  遍历模块路径记录(r15): 标志位@+0xa、rise/fall 延迟表、
  经 schedule_delay_event 向时间轮投递输出翻转事件
```
即 MPD 的实现是：输入沿→查 rise/fall 延迟→（惰性过滤，见 §5.3）→投递输出事件。

---

## 5. 门级 + SDF 仿真策略

### 5.1 标注流程
- 编译与门级完全相同（specify 占位延迟 0）；运行时 TB `initial $sdf_annotate(file, dut)`：
  日志 `Doing SDF annotation ...... Done`，由内核内建标注器完成（callgrind 可见 `sdfAnnotateNew`、
  `hsimLoadSdfDelayData/hsimhLoadSdfDelayData`、`processModpaths`、`SinitMPath`、`getMaxMinDelayForAccupath`）。
- 标注内容：529,684 条 IOPATH → 写入对应 specify 模块路径的 rise/fall(min:typ:max 取 typ)；790,222 条 INTERCONNECT → 互连延迟；
  SETUP/HOLD → `$setup/$hold`，RECOVERY → `$recovery`。
- 标注耗时 ≈ 1.2s（SDF 165MB；门仿 6.1s → SDF 7.3s 的差值主体），内存 48.5→61.2MB。
- 工程注意：DC 写出的 SDF 是**状态相关**的（`(COND A2==1'b0 (IOPATH …))`，2,418,216 条 COND）。
  VCS 只把 COND IOPATH 标注到模型中同样 COND 化的模块路径上；简单库模型没有 COND 路径就会被忽略。
  本实验用 `sdf_sanitize.py` 把同端口对的 COND 折叠成一条无条件 IOPATH（首条件值）后再标注——这是无 COND 模型库的常规做法。
  COND 化 TIMINGCHECK（`D_SDFCHK`）同理不标注（0 警告静默忽略）。

### 5.2 求值模型：与门级同一套 MPD 机制，延迟变为真实值
- callgrind Top 与门级同构：`scheduleuna_th_nobuf` 25.4%、`doMpd32` 24.0%、`SchedSemiLerMP1` 7.4%、`CauseAllTS32LeanLerOpt` 3.0%、
  `schedule_delay_event(+_common)` 7.3% + 标注器 `sdfAnnotateNew` 0.33%。
- 差别在于延迟值非 0 后：① 每 25~40ps 一级的组合路径要经历多次真实时间步进（时间轮槽位更密）；② 惰性过滤被激活。

### 5.3 延迟语义（反编译自内核符号簇）
- **惰性延迟/脉冲过滤**：`PulseProp / PulseProp_0_0 / InterPulseProp_(100_100|New|New_Lite) / WDoPulserr_0_(0|100) / printPulsePathInfo / acc_append_pulsere`
  —— 比路径延迟窄的脉冲按拒绝/传播百分比处理（对应运行时 `+pulse_e/+pulse_r/+pulse_int_e`）。
- `+delay_mode_transport` 实测：关闭惰性过滤（本设计结果不变，CPU 7.0s ≈ 7.3s）；
  `+delay_mode_zero/unit` 实测：**先标注后覆盖为 0/单位延迟**，CPU 与普通 SDF 相当（7.0/7.5s）——延迟模式不减少路径事件机制本身。
- 时序检查：模型带 `$setup/$hold/$recovery`（占位 0）→ SDF 的 SETUP/HOLD/RECOVERY 值标注进来；
  `-notimingchecks` 实测首拍 X 现象不变（排除 X 由检查器产生）。

### 5.4 SDF 仿真独有的时序现象（1.25ns 首拍 X）
- 800MHz(1.25ns) 下首笔输出 `res=X`（127/128 通过）；2.5ns 下 128/128 通过。
- 根因（用 `dbg2.sv` 探针 + XMR 追踪 FF 实例 `.Q` 定位）：X 冲刷波在设计无复位寄存器链
  （`full_mul_res_arr` 等）中传播，tx0 的 `r_alpha` 组合锥在捕获沿**之后**才稳定（线负载估计延迟下近关键路径晚到一个周期），
  首拍捕获到 X。零延迟仿真中 delta 排序掩盖了该竞争 —— **这正是门级+SDF 仿真的价值所在：暴露真实延迟下的时序敏感行为**。

---

## 6. 并行仿真策略

### 6.1 编译并行（-j，实测有效）
- `vcs -j8` 触发 `Note-[VCS_PARAL] Parallel code-gen enabled`：**模块级并行代码生成**（60 个模块并行 codegen）。
- 实测：本设计受限于单一巨型顶层模块与固定前端开销，收益有限（门级 42.4s→46.5s 墙钟相当；RTL 12.0→11.1s）；模块数多的设计收益更大。

### 6.2 运行时内核：单线程（实测结论）
- 三种 simv 运行期 `/proc/PID/status` 观测：RTL 1 线程；门级/SDF 2 线程。gdb 采样显示第 2 线程阻塞在 `poll()/recv()`（VCS 交互/守护 IPC 辅助线程），**仿真内核线程唯一，全部 CPU 时间在主线程**。
- 但内核中存在**完整的细粒度并行(FGP, Fine-Grained Parallelism)基础设施但默认关闭**：
  - 符号：`FGP_getSchedulerForThread / fgp_global_(un)lock / fgp_local_(un)lock / fgp_enter_critical / FGP_advanceFutQ / fgpParallelMode / fgpUvmParallelMode / fFgpSingleSocketMode`；
  - `doMpd32/schedule_delay_event` 首指令即检查 `fParallelEBLK / fFgpDynamicToggle` 全局开关（默认 0，走串行快路径）；
  - 驱动串中存在 `-fgp=auto / -fgp=auto_affinity:… / -fgp=conf:` 等语法，但本安装实测 `Ignoring the unknown fgp option`（特性未启用/未授权）。
  - 结论：**事件驱动内核的确定性语义要求全局事件排序，VCS 商用版本把并行留给编译层与回归层**。

### 6.3 回归并行（多进程，实测有效）
- 4 个门级 simv 并发：墙钟 40.5s(串行) → **13.7s(并发)，2.95×**；受限于 license 检查等启动串行化，未到理想 4×。

---

## 7. 三种仿真策略对比总表

| 维度 | RTL | 门级(无SDF) | 门级+SDF |
|---|---|---|---|
| 求值代码 | 字级向量原语(Wmadd/Wmmul…)+表达式树编译 | 位级内联布尔函数(叶子函数,零调用) | 同门级 |
| 事件粒度 | RTL 进程/连续赋值块(EBLK) | 每实例输入沿→pin-to-pin 路径事件 | 同门级 |
| 延迟机制 | `#`/NBA 周期语义 | specify 路径恒走 MPD 机制(0 延迟仍 25% 内核开销) | MPD+真实 rise/fall,惰性脉冲过滤 |
| 内核热点 | 设计求值 ~50% | scheduleuna_th_nobuf 22%, doMpd32 19%, SchedSemiLerMP1 9% | 同门级(+sdfAnnotateNew 0.3% 一次性) |
| 时间轮 | 哈希轮+FutQ1+millenium(rmapats.c) | 同 | 同(槽位更密) |
| CPU(128tx) | 0.41s | 6.1s | 7.3s |
| 内存(数据结构) | 0.1MB | 48.5MB | 61.2MB |
| 线程 | 1 | 2(1 内核+1 IPC) | 2(同左) |
| 独有能力 | 行为语义、近似算法功能 | 结构等价(逐位对 RTL) | 真实延迟竞争/首拍X/毛刺/时序检查 |

---

## 8. 复现命令速查

```bash
source /apps/EDAs/syn.bash
D=/home/yangfan/digi/cases/designs/modmult/mul
W=/home/yangfan/vcs/modmult_sim

# RTL：生成 golden
cd $W/rtl_sim && vcs -full64 -sverilog -timescale=1ns/1ps -f filelist.f +define+GOLDMODE -o simv_rtl -k
./simv_rtl -no_save            # TEST PASS, 写出 golden.txt

# 门级（无 SDF）
cd $W/gate_sim && cp ../rtl_sim/golden.txt .
vcs -full64 -sverilog -timescale=1ns/1ps -f filelist.f +define+CHKMODE -o simv_gate -k
./simv_gate -no_save           # TEST PASS 128/128

# SDF 生成与标注仿真
dc_shell -64 -f $W/sdf_gen/gen_sdf.tcl                      # write_sdf 406MB
python3 $W/sdf_gen/sdf_sanitize.py <sdf>                    # COND 折叠 → 165MB
cd $W/sdf_sim && cp ../rtl_sim/golden.txt .
vcs -full64 -sverilog -timescale=1ns/1ps -f filelist.f +define+CHKMODE \
    +define+SDF_SIM +define+SDF_FILE=\"barr_modmult_flat.sdf\" +define+WARM=2 -o simv_sdf -k
./simv_sdf -no_save            # TEST PASS 128/128 (2.5ns 时钟)

# 剖析
./p_gate -simprofile time                       # VCS 自带：组件/实例级
valgrind --tool=callgrind ./simv_gate -no_save  # 指令级：内核函数排行
gdb -p $(pgrep simv_sdf) -batch -ex "thread apply all bt"   # 线程/栈
```

---

## 9. 结论

1. **RTL 仿真**：编译成原生字级求值代码（LLVM），事件驱动 + LER 分层调度 + 哈希时间轮；开销集中在设计求值本身。
2. **门级仿真（无 SDF）**：位级展开 + 逐实例路径事件；VCS 对带 specify 的单元恒启用模块路径延迟机制，
   即使 0 延迟也有 ~25% 内核时间花在路径延迟计算/调度（`doMpd32`/`SchedSemiLerMP1`），这是门仿慢的根源。
3. **门级+SDF**：同一 MPD 机制上标注真实 rise/fall 延迟 + 惰性脉冲过滤 + 时序检查；
   标注是一次性动作(~1.2s/165MB)；能暴露零延迟仿真不可见的时序竞争（本例 1.25ns 首拍 X）。
4. **并行策略**：编译层模块级并行(-j)与回归层多进程并行是现实手段；运行时内核确定单线程，
   FGP 细粒度并行基础设施在二进制内存在但本安装未启用。
