# M29：函数输出形参与外部副作用

静态 RTL/SV 函数已支持 output/inout、对词法外部变量的阻塞写入、void 返回类型、函数语句调用和 `void'(f(...));`。输入入口采样，输出在返回时复制；返回值在复制前捕获，目标动态下标在返回时求值。新增空 ANSI 函数/任务形参表，修复单个嵌套函数/条件表达式实参丢失，以及语法恢复经过空 generate block 的空指针崩溃。RTL 与紧凑门级 parser 保持分开；运行时和门级 parser 未改。

范围和代码示例见 [功能说明](../../docs/function-effects.md)，计划见 [plan1017.md](../../plan1017.md)。新增测试位于 [tests/function_effects](../../tests/function_effects/regression.py)。

| 共同输入 | 验证内容 | 与实际 VCS 相同的物理位时间线 |
| --- | --- | ---: |
| copy | 输出地址退出时求值、inout、嵌套调用、void、提前 return、signed/enum/packed/宽两态复制 | 726 |
| effects | 外部全量/部分写、条件短路、阻塞内部 delay、延迟 NBA 单次取样、失败预测回放 | 464 |
| sensitivity | always_comb 跟踪函数体外部读取及 void 写入，传统 @* 只跟踪实参 | 256 |
| parallel | 两独立实例、输出复制和外部状态，实际双分区 | 580 |
| shared | 共享函数状态和模块变量，合并为单分区；空形参函数/任务 | 256 |
| 合计 | 五个同源输入、无返回变量名称映射 | 2282 |

本地串行、时间轮及 `--threads 2`，ordered/settled × VCD/DWF 共 60 次捕获，加 1 次真实失败预测回放，共 **61 次捕获、22 类拒绝**通过。独立预期检查 TRACE、四个动态目标存储器字的完整 settled 时间线、双分区数值和共享状态合并。拒绝覆盖 void 值/查询误用、非法输出目标、enum 不匹配、非法非过程调用、多写进程、automatic/递归和函数时间控制/NBA/任务调用；显式丢弃与默认丢弃的告警数量也检查。

最终本地八项定向 CTest（新功能、子程序、复合动作、命名签名、数组查询、整数类型、编译总回归及 parser 单测）全部通过，131.17 秒；新增语法恢复单测额外通过。macOS ASan/UBSan parser 单测、五组输入各三轮 cleanup 以及五个实际生成程序通过，含实际双线程；关闭 leak 检测。Bison 47 个 shift/reduce，与 M28 相同，无 reduce/reduce。

VCS 来自 `10.131.254.103`，执行前 `source /apps/EDAs/syn.bash`，实际版本 W-2024.09_Full64。使用 `-full64 -sverilog -debug_access+all -top top -top dump`，运行 `simv -no_save`。输入、命令、退出码、完整日志和波形保存在 [vcs](vcs/results.json)；比较脚本同时检查源文件字节、TRACE、全部导出物理位身份和值/时间，见 [vcs-results.json](vcs-results.json)。

明确的对照边界：

- VCS 的 VCD 没有导出 `top.data[0]` 至 `top.data[3]`，显式请求四个字也被 VCS 告警并忽略。比较器只排除这四个明确名字（128 位），它们另有逐字独立预期和 dsim 全后端/格式对照，不计入 2282 位 VCS 一致数。
- 原始敏感集合探针中，传统 `@*` 在声明初始化时的启动响应存在差异，`legacy` 的 3 位时间线不同。完整原始输入、双方波形与逐位差异保存在 [startup-sensitivity](probes/startup-sensitivity/differences.json)。共同输入改为 1 ns 明确驱动输入；没有宣称修复启动调度。
- 保留现有非 void `return;` 扩展。未实现 automatic、递归、ref、默认/命名实参、数组形参、完整并发激活和完整常量函数；package/interface、完整 SVA/UVM 与时序/事件区域仍未补全。本批没有新的性能测量，也未运行全量 CTest 或 Linux sanitizers。

源码冻结为 687 个文件，[manifest](source-manifest.json) 逐项记录 SHA256；源包 SHA256 为 `8cc9cabc787519d7547d44a8d5313af51203179e41c5204905991e8e1c42c08f`。跨平台验收结果记录在 [results.json](results.json)。

最终 Linux 同源干净构建通过，新功能/parser/编译总回归三项 CTest 84.27 秒，退出 0；六份实际生成 C++（五份串行及独立域双线程）跨平台完整字节一致。Linux 实际波形再次匹配同组 VCS 2282 位时间线。源文件逐项身份和完整程序身份见 [final-identity.json](final-identity.json) / [platform-identity.json](platform-identity.json)。
