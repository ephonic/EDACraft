# M63 无尺寸数组值形参

automatic task/function 的 input/inout `[]` 支持固定 unpacked 数组及子数组、多维 `[][]`、混合固定维度、命名/宽两态元素、默认/命名/经典声明、foreach、形状查询和嵌套传递。无尺寸维度在入口按实际大小重编号为 `[0:size-1]`；编译器按调用点特化形状，parser 保留未绑定维度并推迟查询折叠。形状推导不求值索引表达式，实际入口/返回复制各自只求值一次地址。沿用现有自动帧、事件、取消、分区和回滚。RTL/gate parser 继续分离；门级 parser、runtime 和调度器未修改，Bison 冲突从 47 减为 46。

七个最终同源模型位于 `tests/open_arrays`，覆盖三种后端、两种波形模式、VCD/DWF，共 90 次捕获、6 次真实失败预测恢复、24 次正常/取消调用有界复用、12 类编译拒绝及真实两个并行分区。动态前缀带函数副作用的入口取样和返回重选目标以独立预期检查。每种格式/后端比较完整每信号 ordered 或 settled 流。

实际远端 VCS W-2024.09 七份同源源码及 TRACE 一致，**1692 条物理位 settled 时间线全部一致**，无排除位。32 条只读 wrapper 观察线补齐默认 dump 省略的 1180 位数组，映射见 `observers.json` 和 `vcs-results.json`。`verify.py local` 或 `verify.py linux/models` 可重验保存证据。

事件函数另有明确差异：原 events 模型把无尺寸值参数函数放在事件表达式中，VCS 编译成功但运行 180 秒超时；最小 `probes/event-function.sv` 同样编译成功、运行 10 秒超时，dsim 输出 `TRACE callback 7`。任务等待的独立探针在 VCS 正常退出。原模型、编译日志、超时结果及最小探针均保留，见 `probes/event-comparison.json`；这些探针不计为波形对齐通过。最终主 events 模型使用固定数组值参数函数触发事件，仍以无尺寸任务形参验证局部复制、等待、唤醒与外部修改隔离。

12 类拒绝路径中，VCS 同样拒绝 7 类，另接受动态元素 NBA、output 路径、调整大小赋值、两态/四态转换和默认静态子程序五例；见 `diagnostic-comparison.json` 和原始 `vcs-negatives`。dsim 的本批实现明确限定固定形状、automatic、input/inout，拒绝上述未接通路径。固定数组绑定 ref/const ref `[]` 两端均拒绝。不能据这一批宣称支持完整动态数组或全部诊断对齐。

最终七个实际生成程序通过 ASan/UBSan，含真实 parallel 两分区并比较完整 ordered 流；七份语料各重复三轮 parser 绑定/克隆/清理，完整 parser 语义单测通过，leak 检查关闭。最终代码 hash 见 `final-identity.json` 与 `sanitizers/results.json`。首轮测试误用 Verilog 保留字 small 作为变量名，两端均拒绝，已更名并重验，原始失败日志保留。

本地 11 项不同定向 CTest、Linux 干净构建与交叉核验的具体结果见 `results.json`、`linux` 及原始日志。Linux 包含七串行/一真实双分区程序 16 次捕获，8 份完整生成 C++、7 份完整 ordered 流和 stdout 跨平台一致，并再次核对 VCS 全部物理位。冻结 1354 个源文件，源包 SHA256 见 `source-archive.json`；构建前后检查输入 hash。

仍缺动态数组变量/new[]/resize/delete/空数组、同一调用点的运行期变长、output 动态分配、动态数组 ref/const ref、数组返回、默认静态无尺寸子程序、动态元素 NBA 及更完整元素转换。递归、队列/关联数组、class/约束、完整 SVA/覆盖率和 UVM 仍待补齐；M47/M55、M60/M62 既有边界保留。本批未新增性能测量，未跑全量 CTest 或 Linux sanitizer。
