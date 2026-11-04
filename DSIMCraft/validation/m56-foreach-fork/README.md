# M56 foreach 动态循环帧验收

状态：**PASS_SCOPED**。补齐 foreach 隐式自动索引在重叠 fork 中的隔离和逃逸生命周期；本次循环的分支共享索引，循环体 static 局部变量保持共享。自然结束按内到外推进到越界索引，singleton 使用下降方向；break/return 保留退出值，continue 走推进路径。控制转移复用 PC 深度，变量/订阅/共享关系复用 M55 帧与检查点。移除旧 foreach 重叠拒绝，RTL/门级 parser 保持独立，未改 grammar/lexer。

## 验证范围

- 六组共同输入位于 [tests/foreach_fork](../../tests/foreach_fork)：父任务返回、克隆分支静态任务重叠、多维/省略/尾部省略/singleton、嵌套 break/continue/return/命名 disable、取消、直接索引事件等待及实际两分区。
- 本地串行/时间轮/双线程，VCD/DWF ordered/settled 全逐信号流一致，**76 次捕获**；三个挂起期间和一次分配前的实际失败预测共 **4 次回滚**。48 次调用后断言进程不超过 16、信号槽不超过 100。
- 实际 VCS W-2024.09：六份 SV 字节相同，TRACE/自检及 **748 条物理位 settled 时间线一致**，没有位排除。一个既有隐式 foreach 作用域名字差异显式映射：`top.walk.unnamed$$_0.body.calls` → `top.walk.$unm_blk_1.body.calls`，全部 32 位仍比较。命令和原始日志保存在 [vcs](vcs)，比较脚本为 [verify.py](verify.py)。
- macOS 14 项既有定向 CTest 204.61 秒通过；新增 rtl_foreach_fork 72.13 秒通过，合计 **15 项不同检查**。最终 singleton 修正后再次运行 foreach/多维两项，53.81 秒通过。不是全量 CTest。
- ASan/UBSan：六个最终生成程序（含真实双线程）及完整 ordered 流、六语料各三轮 parser 清理、完整 parser 语义单测、kernel/wheel/compact 三内核通过；leak 检查关闭。实际程序哈希见 [sanitizers/results.json](sanitizers/results.json)。
- Linux 从冻结的 **1190 文件**干净构建，3 个 automatic 帧内核、六串行和一个实际双分区程序、14 个波形捕获通过；**7 份完整 C++ 字节相同，六个完整 ordered 流及 stdout 跨平台一致**。Linux 再对相同 VCS 748 条位时间线通过。只跑上述定向范围，未做 Linux sanitizer 或旧门级全量回归。

## 原始探针和边界

[lifetime](probes/lifetime.sv) 与 [singleton](probes/singleton.sv) 原始输入的 native/VCS TRACE 一致；singleton 探针确认 7:7 自然终止为 6。初版曾按上升方向终止，这个真实差异已修复，随后六主模型重新核验。

[multi-overflow](probes/multi-overflow.sv) 含负 unpacked 边界及 INT_MAX 附近 ascending packed 范围：native 因既有非负边界限制拒绝；VCS 编译后未推进到后续时间，自己的 simv PID 2450895 已 SIGTERM 终止。原始日志保留，**不计作对齐或通过**。范围不支持情况没有通过删位或修改共同主输入掩盖。

M55 保存的父任务返回后局部直接事件等待差异仍保留。本批使用尚存活循环帧上的直接索引事件，不把这组通过推广到所有 automatic 事件。递归/process 对象、动态/关联数组和队列、automatic 局部 event、完整 SV 验证/时序能力仍有缺口；无新的仿真测速，不宣称与 VCS 全部功能或性能对齐。

## 证据与复现

入口：`ctest --test-dir build -R '^rtl_foreach_fork$' --output-on-failure`。同源 VCS 运行器 [run-vcs.py](run-vcs.py)、sanitizer 运行器 [run-sanitizers.py](run-sanitizers.py)、Linux 模型运行器 [run-linux.py](run-linux.py)；Linux 构建驱动保存在 [linux/driver.py](linux/driver.py)。

[results.json](results.json) 汇总实际覆盖；[final-identity.json](final-identity.json) 保存七个最终 C++ 哈希；[source-manifest.json](source-manifest.json) 和 [source-changes.json](source-changes.json) 记录源文件，源包 SHA256：`2dd75cf58d5b3013635da54d138329caf06e037d7a9f88cc4bcc7ad480b34b40`。冻结后全部源哈希再次核对一致。原始编译/运行日志按原样保存，包括工具产生的空白。
