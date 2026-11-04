# 单分区串行回退与全局结束快照消减

473文件冻结源 `e91ad65d6407235fe82a50806f45bfeee3cecd96d110bbf4c455c13fd957ddbc`。
先在隔离副本执行再接入工作区；RTL与门级parser保持分离，运行时和并行/波形头文件与472完全相同。

- 实际分区数为1时重新使用原串行 lowering，生成程序仅增加统计参数适配；不会启动线程池或窗口事务。`--threads 1` 同样回退，IR显式报告执行方式。
- 多分区仅在编译程序包含 `$finish` 时启用全局结束事务；无该任务时移除整状态快照，保留窗口输出归并。含任务的多分区生成程序不变。
- 本批没有CPU性能结论，不改变完整SDF内部切分限制，也未实现自动预测器或增量回滚。

`verify_local.py` 独立审计通过：18配置/54实际程序、306捕获、204完整编码比较、333次个别信号有序比较、21份整个串行回退程序身份。覆盖RTL、三类SDF各三后端，以及新增无finish时间格式/输出场景。探针确认两个OS线程重叠执行；注册状态复制0次，强制事务对照18次。12项CLI/不支持组合拒绝通过。

`check_integrated.py` 使用工作区编译器重发射54份完整CPP/语义IR并与隔离构建逐字比较，另实际编译6个无波形RTL/SDF程序，3个事件预算失败程序的退出码、已打印前缀及诊断一致。`gate_source` 正式CTest通过。

`prove_baseline.py` 重发射18类默认关闭程序，与472整个CPP/语义IR相同。另核对三类已执行VCS参考、4个ASan/UBSan和1个TSan程序的整个CPP及完整波形相同，因此复用这些已执行证据，不称本批重新运行。新无finish双线程程序与SDF串行回退程序实际经过macOS ASan/UBSan，16捕获/8完整比较通过，核对实际插桩符号；没有Linux sanitizer。

Linux原任务 `/tmp/dsim-parallel-fallback-linux-1018-rDyjSfGE`，shell PID3344593，启动会话80249。三项受影响CTest为 `gate_source`、`parallel_compiled`、`compiled_regression`，登记112项；另做54份安装输出身份、6无波形/3错误对照和两份原始全SDF的关闭选项GCC预处理身份、开启8线程请求但实际单分区的整个CPP身份。任务进行中，未发布Linux通过或新全量仿真/计时。

原始捕获和命令在 `local/`，2392文件由 `local-manifest.json` 校验；接入证据在 `integrated/`；源身份、隔离初版/最终结果分开保留。Linux终态后使用 `validation/fetch_terminal.py` 下载原任务归档，再运行 `verify_linux.py`。
