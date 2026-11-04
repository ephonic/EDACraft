# M65 动态数组形参和引用

2026-10-23。动态实参接入 automatic task/function 的一维 `[]`
input/output/inout/ref/const ref。值传递复制长度和内容，返回可扩缩容；引用绑定数组描述符，
挂起期间实时观察元素、resize/delete。沿用 M64 的 Sim 容器、自动帧、检查点和分区，
本批未修改 runtime/调度器/门级 parser。

## 同源对齐

六最终模型 values/functions/references/lifetime/control/parallel 在实际
10.131.254.103 的 VCS W-2024.09 编译和执行。`run-vcs.py` 保存命令、源 hash、日志和 VCD；
`verify.py` 严格核对所有已导出物理位身份和 settled 时间线及 TRACE。
全部 **576 位**通过，无位排除，本批无需 wrapper 观察映射。
动态元素仍不导出波形声明；内容由共同的 SV scalar 读取和 TRACE 观察，不能称所有动态元素均已 dump。

原生六模型分别执行串行、时间轮、threads=2，以及 ordered/settled VCD/DWF，
72 次基础捕获；values/references/lifetime/control 在任务挂起时执行实际失败预测并恢复，
control/functions 在分配/函数调用前失败预测，合计 **78 捕获、6 次失败预测**。
control 的 12 次取消和 12 次正常调用检查进程/信号数有界；parallel 确认实际两分区，
最终两输出均为 15。不同长度同一调用点、空数组、复制隔离、返回扩容、重叠调用、
嵌套转传、const-ref 事件等待、默认/命名/经典声明、两态和 96 位元素均有覆盖。

14 类原生拒绝逐条核对诊断。VCS 编译同样拒绝 7 类，编译接受其余 7 类：默认静态无尺寸任务、
动态实际数组到固定形参、动态元素 ref/NBA、两态到四态转换、const-ref 转传 output/inout。
后两类沿用 M62 的保守只读策略；这些是功能或兼容欠缺，不能算对齐通过。
见 `diagnostic-comparison.json`，保留两端原始日志。

## 验证范围

本地 14 项不同定向 CTest 全部通过：13 项受影响回归 274.02 秒，最终新功能回归 89.65 秒。
首轮新功能回归 87.56 秒也通过；随后调整预测检查点，使其实际覆盖挂起 ref 帧和分配前函数调用。
六份最终生成程序的 ASan/UBSan、完整 ordered 流、六语料各三轮 parser 清理及完整 parser
语义单测通过，leak 检测关闭。正常 parser 目标重新构建后再检查，1.38 秒通过。最终七份完整生成 C++（六串行加实际并行）重新生成核对；
sanitizer 的六份 C++ 与最终输入一致。

初期取消夹具使用尚不支持的外部命名 fork disable，已改为词法包围的命名块；
证据收集工具的临时路径和冻结清单继承路径已修正。第一次冻结后只调整了回归预测覆盖；
最终冻结源和 Linux 构建单独执行。上述初期尝试不计入最终通过结果。

Linux 最终 1416 文件冻结源干净构建、四项 parser/动态数组内核检查，六串行/一实际并行程序 14 捕获及 14 类诊断通过。七完整 C++、六完整 ordered 流/stdout 跨平台一致，再核对全部 576 条 VCS 位时间线。冻结源包 SHA256：`4ce6555f56ca326e62e43be9eca80a65ca78a880d6fd7810e6f4123863eb7847`。详见 `results.json`、`source-archive.json` 与 `linux/`。
未运行全量 CTest、Linux sanitizer，也未新增性能测量。

## 保留欠缺

固定实际数组仍采用 M63 的调用点形状特化，不能运行期 resize 或调用动态方法；
固定与动态形参互转、静态无尺寸子程序、动态元素 ref/NBA、多维动态容器、数组返回、
声明初始化、assignment pattern、更完整类型转换和动态元素波形导出仍待补齐。
递归、队列/关联数组、class/约束、完整 SVA/覆盖率/UVM 仍非完整支持，
M47/M55/M60/M62/M63 的已知边界保留；本批不宣称完整 VCS 兼容。
