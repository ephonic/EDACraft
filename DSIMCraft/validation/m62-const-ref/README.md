# M62 const ref：实现与对照证据

automatic task/function 的 `const ref` 已接入 RTL parser 和编译器：完整标量/packed/固定数组及动态元素/子数组保持实时别名，支持默认、命名、经典声明和嵌套转传。读写依赖区分只读引用与可写引用；编译期检查普通/部分/成员/数组整体赋值、增量更新及向 writable ref/output/inout 的转传。复用现有激活帧、事件订阅、取消与检查点；runtime、调度器及门级 parser 未修改。Bison 仍为 47 个 shift/reduce 冲突。

同源六个模型位于 `tests/const_ref`。本地回归覆盖 serial/time-wheel/两线程后端、ordered/settled、VCD/DWF，78 次捕获、6 次实际失败预测回滚、24 次正常/取消调用有界复用、23 类编译拒绝、2 类非法动态引用运行诊断，以及实际两个并行分区。四个挂起时回滚模型为 events/arrays/types/control，另有 control/functions 的分配前回滚。完整 ordered 流按每个信号比较，不只检查最终值。

实际远端 VCS W-2024.09 使用未修改的六份 SV；`vcs/results.json` 记录源码 hash/命令/TRACE，`vcs-results.json` 为逐位核对结果：**983 条物理位 settled 时间线及全部 TRACE 一致**，没有排除差异位。六条只读 wrapper 观察线导出 VCS 默认 dump 省略的 192 位数组，映射见 `observers.json`；两端物理位身份集合必须完全相同。`verify.py` 可以重验保存的 local 或 linux/models 证据。

拒绝路径单独与 VCS 编译结果比较，见 `diagnostic-comparison.json`、`vcs-negatives` 和 `diagnostics`：dsim 拒绝 23 类，VCS 拒绝其中 18 类，接受 array_inout/array_output/inout_escape/output_escape/static 五例。独立 `probes/copyout.sv` 在 VCS 运行后实际值从 `1,1,2` 变为 `9,17,18`；dsim 对这种 const ref 回写维持只读拒绝。默认静态 task 的 const ref 也仍由 dsim 保守拒绝。这些是已知兼容差异，不属于对齐通过模型。表达式/字面常量/net 的原始拒绝探针、编译日志亦保留。未知/越界动态引用的 dsim 诊断策略没有宣称与 VCS 相同。

ASan/UBSan 检查六个最终实际生成程序及完整 ordered 流，parallel 使用实际两分区；六份语料分别重复三轮 parser 绑定/克隆/清理，并运行完整 parser 语义单测，leak 检查关闭。`sanitizers/results.json` 和 `final-identity.json` 核对实际生成代码 hash。

Linux 干净构建、受影响定向 CTest 和最终交叉核验结果在 `results.json`、`linux` 及对应原始日志中列明。`source-manifest.json` 冻结 1321 个输入文件，`source-archive.json` 保存源包 SHA256；构建前后均核对 hash。冻结包包含实现、测试和相关文档；源包本身及二进制没有提交。

仍缺开放/动态数组、递归、数组返回、动态容器、class/随机约束、完整 SVA/覆盖率与 UVM。引用函数作为事件表达式回调仍保守拒绝；join_any/join_none 直接访问外层引用的标准限制未完整实现，M47/M55 已知事件差异保留。未新增性能测量、未跑全量 CTest 或 Linux sanitizer，不称完整 VCS 功能或性能对齐。本批优先功能补齐，后续仍先处理开放数组/递归和动态容器等验证阻塞项。
