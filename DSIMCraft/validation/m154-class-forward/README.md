# M154：类前向声明与启动期对象执行

本批沿 REPORT-GAP 的真实 UVM 编译依赖推进，完整 UVM 目标仍未完成；独立压缩波形线程及用户指定范围持续通过发布检查。

实现冻结 `5b1c968777b5fe7023d88ca3af6438ad9df22795`，1914 个源码文件逐字节匹配 Git blob，归档另含一份清单。实现 `typedef class` 到同词法列表真实定义的类型绑定，涵盖重复前向声明、互相引用句柄、别名/方法签名/ref、未来基类、嵌套遮蔽和 module/generate 克隆。可执行初始化在声明绑定完成后分析；静态 `new` 的 automatic 构造器支持启动期私有 activation、嵌套调用、ref 和异常退栈。常量初值先于构造器读取准备，初始化表达式的完整依赖纳入分区。门级 parser 保持独立。

Mac 与 103 Intel 冻结版本各九组回归、1290 份捕获及 mandatory parser/格式 parser/原生 DB 检查通过。新 class_forward 组各有 17 正例、308 捕获、12 编译拒绝、1 回滚/1 提交，以及实际两个分区、完整四态和范围投影 oracle。跨平台全部 52 份生成 C++、stdout 与 308 份解码捕获一致；不将其表述为全部 1290 份捕获均重新做了跨平台比较。

17 正例与 12 反例的相同 SV 在 VCS W-2024.09 输出/接受性检查通过，源码 SHA 逐项核对。七个模型全部 918 个 native 导出位的 settled 时间线一致，没有遗漏。VCS 将两个 named generate scope 展平成 `$var` 的点号名称，比较脚本明确映射 131 位的声明路径，保留原始 VCD；没有静默取字典交集，也不声称比较了动态堆内部字段。开发阶段 fixture 的非法 initial、保留字、wildcard export、暂态空句柄和 129 位期望长度问题已修正并重跑；先前失败不计通过。

RTL parser 单元、17/12 新前端例、真实公开 UVM 的预处理/失败编译、五份实际生成程序（startup/rollback/clones/generate/parallel）与 startup kernel 通过 ASan/UBSan；两个实际并行程序与独立 DWF 接收线程同时运行通过 TSan。sanitizer 程序的 stdout 和异步 DWF 与正式输入相符。未启用 LSan，未作新 runtime 性能或压缩率主张。

Mac 稳定发布为 `20261028T221545742276Z-08527bc5fc99`，103 Intel 为 `20261028T221853Z-5b1c968`。Mac `~/vibe-coding/dsim-test/bin/dsim` 和 103 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 均已激活；三个真实入口重新编译并运行 rollback SV，生成 C++、stdout、完整异步 DWF 逐字节一致，用户选定 observed/tick 2..3 的结果为 5、7。两个阶段收据保留切换前状态，实际激活另见 activation 收据。

未修改固定 Accellera UVM 2020.3.1（`78c06547a2a0a29b3dc9dcafae62b75b2ff61544`），两端实际 326 文件与公开归档逐 SHA 相符并保留 LICENSE/NOTICE。两端展开均为 1,888,084 字节、166 依赖，SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。native 首错由 uvm_base.svh:42 移至 uvm_object_globals.svh:714 的命名类型队列，正常退出 1、不产生部分 C++；原始包仍未完成语义分析和执行。参数化/编译单元类、对象容器、限定符、约束、IPC、clocking/coverage/DPI 等继续保留，不能把本批 class 验收当作 UVM factory/sequence 已可运行。M152 动态转换、M153 宏字符串和旧 SDF time0 参考差异未计为修复。

波形继续使用自有 DWF1P001：单接收线程拥有编码/Zstd/CRC/写盘/索引，有界批处理与背压、异常传回和关闭排空。同步/异步的管线组每端 72 捕获/36 对字节身份，范围组每端 232 捕获/62 对字节身份通过。用户接口见[波形文档](../../docs/waveform-format.md)，不声明 FSDB 二进制兼容、百万信号规模验收或吞吐收益。

原始证据镜像在本机 `~/vibe-coding/dsim-test/evidence/m154-class-forward/archives` 与 103 `/apps/EDAs/own/dsim/evidence/m154-class-forward/archives`，包括 source/mac/linux/sanitizers/vcs/uvm-reference。六份归档共 13531 个成员，逐 SHA 检查通过，全部为普通文件；VCS 仅导出自有 SV/capture、文本日志和 VCD，vendor 生成 C/C++/csrc/daidir/程序保留远端。源码归档的目录遗漏在构建前修正；证据导出路径错误另在导出时修正。失败包未用于发布。运行 `verify-evidence.py <archives目录>` 与 `audit.py` 可复核。完整 REPORT-GAP/UVM 目标继续，下一编译依赖为命名类型队列及对象容器。
