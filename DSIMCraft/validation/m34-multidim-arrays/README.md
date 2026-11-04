# M34：静态多维数组与 VCS 功能对齐

新增静态多维 unpacked 变量数组，覆盖多维下标读写、packed 选择/成员、foreach、数组查询/inside、signed/两态/enum/宽元素、延迟/NBA、automatic 局部存储、依赖分区和预测失败回滚。RTL parser 修复声明维度列表反转，按源顺序保留各维；门级紧凑 parser 独立且未改。

编译期为各维计算步长和元素信号槽；常量下标直接绑定，动态下标逐项单次取样后检查全部位宽/X/Z及各维上下界，再计算偏移。前一维无效也执行后续下标副作用，越界不允许跨行别名。运行时没有新增 AST 解释器、数组扫描或分配；runtime/parallel 头文件未改。原 M32/M33 的 14 份完整生成 C++ 与冻结验收版本字节一致，见 prior-codegen-identities.json。

六组共同源在 tests/multidim_arrays/。本地串行、时间轮和 --threads 2，分别检查 ordered/settled、VCD/DWF，共 72 次捕获；再于 1ns 的 NBA 待提交或 automatic 任务挂起期间，执行两次实际失败预测/回滚重放，共 74 次。九类明确拒绝回归通过；parallel 用例实际生成两个独立分区。所有静态数组字另与 packed 观察信号检查完整时间线，无未核验数组字。最终新功能 CTest 56.11 秒通过，既有 11 项定向 CTest 207.20 秒全部通过，见 local-new-feature-test.log/local-prior-tests.log。

远端 10.131.254.103，source /apps/EDAs/syn.bash，实际 VCS W-2024.09，六组未经改写的共同输入全部通过 TRACE/自检。同名直接导出的 1544 位完整时间线一致，无名称映射。VCS 默认不导出数组字，全部 660 位静态数组字通过共同源 packed 观察信号逐位核验；该数量单列，不算 VCS 直接导出位。输入、dump wrapper、命令、编译/执行状态和原始波形在 vcs/，比较器 verify.py，映射表 tests/multidim_arrays/observers.json。

probes/indices.sv 的原始 VCS/native TRACE 逐项一致，核对不同声明方向、越界后续下标副作用、宽下标和无跨行写入。initial-observer-delta.log 保留早期用例的预期错误：同一过程写数组后立即打印连续观察信号，两边均显示更新前值；最终共同源增加明确的采样时刻，并重新执行双方。没有把这个用例修正当作事件调度功能修复。

macOS ASan/UBSan parser 单测、六组语料各三轮清理、六个实际生成程序（含真实双线程）及其完整 ordered 波形检查通过，关闭 leak 检测；日志在 sanitizers/。语法文件未改，不增加 Bison 冲突。

759 文件冻结源包信息在 source-archive.json；逐文件哈希在 source-manifest.json。Linux 同源干净构建及六项定向 CTest 219.68 秒通过、退出 0；759 文件逐项哈希和源包 SHA-256 一致，七份完整实际 C++ 跨平台字节一致，Linux 实际波形再次匹配全部 1544 位直接导出和 660 位数组观察时间线。完整结果见 results.json，证据在 linux/、platform-identity.json 和 linux-vcs-results.json。

边界见 docs/multidim-arrays.md：仍不支持动态/关联数组、队列、子数组运行时值/切片、数组端口/形参、整体赋值/初始化、负数组边界及数组 net；readmem 仍限单维。packed 聚合/成员/层次路径作为 foreach 目标仍受原有限制。此次不等于完整 SystemVerilog、UVM 或 VCS 功能覆盖；未运行全量 CTest、Linux sanitizers 或新速度测量。M33 保存的普通 for 隐式计数器波形差异也未在本批修复。
