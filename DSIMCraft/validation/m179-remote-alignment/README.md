# M179：103恢复后的功能对齐与发布

服务器恢复后重新读取 `/home/yangfan/vcs/vcs1017.md`，在新目录使用 VCS W-2024.09 对照 M176-M178 原始输入。未修改或中止历史任务。M177/M178 的本地结果是历史记录，不能当成 VCS 对齐结果。

本批修正：

- semaphore 允许键数足够的小请求成功，包括新调用和 `put()` 时已挂起的请求；同样可满足的请求按到达顺序处理。原来严格队首阻塞造成与 VCS 的时序差异。
- mailbox 的内建整型与 packed 向量按位宽、符号、二态/四态判断等价，不再比较 atom 名称。`equivalence.sv` 覆盖 typed/untyped int/packed 和 byte/packed。
- 稳定版构建脚本纳入 IPC 和 GAP3 容器的输入绑定及回归。

新的 `semaphore.sv` 同时检查新调用可取键、多个已挂起请求的唤醒；`cancel.sv` 保证取消的进程确实未获键，单独 `debt.sv` 保留 IEEE 1800-2023 的负初始键数语义。旧输入与第一次 VCS 失败输出保留在远端首轮工作目录，不能将新输入追认成旧输入已通过。

原生 IPC 11模型200波形捕获、27编译拒绝/9运行时诊断通过；serial、time-wheel、threads=2 请求、ordered/settled VCD及同步/异步压缩波形、预测提交/回滚各一次，真实双分区通过。最终VCS汇总见 `vcs-summary.json`：25个模型TRACE一致，两个额外观察器核对并行时间线一致；三个运行差异、四个编译接收差异单列。70个拒绝输入中55个两端拒绝，15个VCS接受而native拒绝；这些输入混合真实功能缺口与接收性差异，不能全算工具错误。

## 已确认的行为差异

- VCS 的负初始 semaphore 键数表现为无符号计数；dsim 按 IEEE 1800-2023 15.3.1 使用可偿还负键数。`debt.sv` 不计为 VCS 一致。
- VCS 的无类型 mailbox 对整数符号差异仍允许接收，类型不符时可能清空 string 输出。dsim 保留等价类型检查，失败不写回。原始 `messages.sv` 因这两点不能到达 VCS 的最后 TRACE，不能算通过。独立探针见 `probes/mailbox-mismatch.sv`。
- 时间模型 `lexical` 的 VCS 诊断探针已收齐：类函数默认参数 `500ps` 实际表现为 `5e-10`，得到 `0.4500000005/0.65000000049999995`；dsim 在定义包的10ns单位下得到0.5/0.7。不是实数比较的末位误差。`precedence` 的物理值相同但写法不同的重复声明被 VCS 拒绝，仍单列差异。
- 新收齐的接收性差异还包括带空格的精度声明、packed匿名enum自增和混合重复赋值模式；VCS拒绝而dsim接受，不计为对齐通过，原始输入未改。
- 低于1fs的precision仍不支持。编译拒绝清单同时包括未实现的合法SV范围，不能将VCS接受它们全归为VCS错误，也不能仅凭VCS编译接受声称运行功能通过。

复现：在103加载 `source /apps/EDAs/syn.bash` 后运行
`python3 validation/m179-remote-alignment/vcs.py . <new-out> ipc gap3_containers time_literals anonymous_enums runtime_array_patterns const_variables`。
`--positive-only` 仅重跑执行模型，拒绝接收性对照保留首轮结果。

完整公开 Accellera UVM 2020.3.1 的原生首错仍为 `uvm_sequence_library.svh:191 randc`，完整UVM未编译运行。本批没有性能测量或速度提升结论。


## 回归与候选版本

Mac首候选 `20261030T044502961745Z-04109ac24df6` 的十组1144捕获、10回滚/9提交及mandatory检查通过，实际入口23模型的CPP及完整异步波形逐字节一致，原始q07输出ok。公开UVM实际入口仍在randc拒绝。

Intel首候选 `20261030T044431993677Z-04109ac24df6` 的时间预测回放失败：测试直接调用icpx时漏了`-fp-model=strict`，正式dsim模型编译路径已有此选项。修正仅涉及 `tests/time_literals/regression.py`，提交 `b9c78de1`，编译器、运行时及SV模型均未变。首候选不激活，不把旧失败改写为通过。

最终候选通过 `refresh-stage.py` 建立新不可变目录：逐项验证1212输入中只变了该测试脚本、runtime及所有模型相同；保留已完成的九组PASS执行证据，替换为完整复验的时间组，重新构建编译器/mandatory并重新发射102个普通后端程序与已执行CPP逐字节绑定，再通过实际入口23模型复验。原首轮收据与失败日志保留，复用结果在最终收据的refresh字段明确列出。


两端写出库分别为macOS Zstd 1.5.7和Linux Zstd 1.5.5（见 `wave-encoding.json`）。跨平台115份CPP逐字节一致；620份波形的独立解码逐信号时间/值一致。其中25份压缩文件编码字节不同，首轮严格字节检查的失败日志保留，未将不同字节误报为相同。平台内的同步/异步字节一致检查和安装入口与候选的字节检查仍严格执行；跨平台结果分别保存文件SHA和解码内容SHA，见 `cross-platform.json`。


最终两端已激活，实现冻结 `b9c78de1`，1212输入的SHA为 `53139d0bff8e…`。Mac为 `20261030T045926558827Z-53139d0bff8e`，103 Intel为 `20261030T050545066581Z-53139d0bff8e`，root/bin一致；各23个实际入口模型CPP/完整异步波形和所选范围复验通过，原始q07均输出ok。收据见 `releases.json`、`progress.json` 和两端 `*-final-activation.json`；首候选和最终候选不混计为新的功能模型。
