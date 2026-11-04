# SDF 专用传播作业

实验性编译选项 `--gate-sdf-jobs` 要求同时启用 `--gate-scalar-timing` 和 `--sdf-annotate`，默认关闭。

```sh
build/dsim --gate-netlist net.v --gate-top dut --liberty cells.lib \
  --gate-models models.v --sdf-annotate design.sdf \
  --gate-scalar-timing --gate-sdf-jobs tb.v -o simv
```

INTERCONNECT 输入采样和 IOPATH 路径选择改用独立的作业表，不再各自创建通用 `Process` 或 fixed-wait 站点。作业保存共享 handler、实例索引、初始化位置及排队/等待状态；重新等待发生在回调入口。普通门求值、触发器采样和提交、RTL/testbench 进程继续使用原进程协议。IR 的 `gate_design.sdf_jobs` 与生成宏 `DSIM_SDF_JOBS_ENABLED` 记录实际选择。

初始化按注册时记录的进程位置交错调度，保留原 RTL、输入路径、输出路径、门单元及多个门级 scope 的次序。后续作业进入原 Active FIFO，在原位置执行，重复唤醒合并；回调可再次唤醒自身。零延迟交付仍异步排队，定时交付、路径选择时刻、取消代际、检查、波形及每次事件预算不变。批量门求值遇到专用作业必须结束当前批次。

作业表及就绪标志由 `Sim` 拥有，随检查点和事务复制。与 `--time-wheel`、`--gate-batch` 及条件路径共同使用时，继续保留队列边界、输出历史和待交付状态。该实现减少通用进程记录和等待协议开销，尚未减少中间事件数量，也没有提前求值或删除零延迟事件。

八类实际 CLI 定向用例、四后端的192份完整波形和16份回放捕获、五档事件预算边界已通过；四种实际内核的本地ASan/UBSan通过。原始完整SDF的生产代码变换副本在macOS Clang/O1执行全部128笔并匹配，尚不替代新Linux编译器全量重生成。修正条件边沿/ifnone后的432源已通过本地完整92/92及独立核对，实际生成的jobs-wheel检查/预测回放也通过本地ASan/UBSan；Linux完整92项及新VCS对照仍在进行，没有本后端性能结论。源身份与进度见[本批记录](../validation/m5-sdf-jobs/README.md)。


432源Linux原任务正常退出0；3549个原始文件归档18ffbeb1c43ea8d9c562079d7783bf567b7c82b0f46a39e72817b307d81ee860已下载并独立审计PASS：两平台各92项、408跨平台常规捕获及32回放、九条件VCS各三次与选择时刻探针三次、六公共流程581物理位、新编译器实际全量jobs/jobs-wheel各128输出。关闭选项的全CPP与精确Ready换行归一后的GCC预处理、作业六处生成替换及仅排除三个耗时字段的完整IR均已重算验证。见[最终两平台验收](../validation/m5-sdf-jobs/verification.json)。默认仍关闭；性能消融另行记录，不使用本次功能运行的用时作为提速证据。
