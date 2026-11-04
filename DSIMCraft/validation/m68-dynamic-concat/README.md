# M68：动态数组混合拼接赋值目标

动态元素/packed 选择、普通变量和固定数组可混合作为拼接目标。RHS 一次取样，先从左到右捕获全部目标，再从左到右提交，重叠处由右侧项覆盖。非法阻塞项跳过，其他项继续更新；每项仍检查 const-ref、net 和 automatic NBA 限制。即时/延迟/事件 NBA 使用已有整组 Parts 更新，事件目标沿用当前存储解析，普通/延迟目标沿用分配代次。保留单目标快速路径，没有新增队列，RTL/gate parser 保持分离。

| 最终验收 | 结果 |
| --- | --- |
| 本地定向检查 | 19 项不同 CTest 完成；首轮 16 通过，3 条旧 net 诊断预期修正后复测全部通过 |
| 新功能 | 6 共享 + 1 原生扩展模型，三后端、ordered/settled、VCD/DWF，91 捕获、7 次实际失败预测恢复，75.93 秒 |
| 调度与内核 | 重叠顺序、非法项、其他标量继续更新、旧分配目标丢弃、事件目标、检查点及真实两分区通过 |
| 实际 VCS W-2024.09 | 6 份同源模型，608 条全部导出观察位 settled 时间线及 TRACE 一致，无位排除 |
| 只读观察 | VCS 默认不 dump 两个 fixed_words 元素，用两条只读 wrapper 线补齐 16 位，显式映射回原名；其余 592 位直接对应 |
| 独立探针 | 13 条原生检查通过；VCS 12 条可运行/运行诊断检查完成，1 条编译器内部故障独立记录；9 条生命周期结果一致 |
| 编译诊断 | 原生拒绝 4 类；VCS 拒绝 3 类，接受 automatic scalar NBA 编译探针，保留为兼容边界 |
| ASan/UBSan | 8 份实际生成程序的完整 ordered 流/stdout、8 次 sanitized compiler 生成、3 种 NBA 内核通过，leak 关闭 |
| Linux | 最终冻结源干净构建，6 动态内核 + parser 语义单测通过；7 串行 + 1 实际并行程序、16 捕获、4 类诊断通过 |
| 跨平台 | 8 完整 C++、7 串行 + 1 并行完整 ordered 流/stdout 一致，Linux 再核对全部 608 条 VCS 位时间线 |

边界保持明确：

- 本批 packed 动态元素拼接 NBA 探针令 VCS 编译器 `Got SIGSEGV`，标为 `OBSERVED_UNAVAILABLE`，不计功能对齐通过；完整来源、命令和故障日志见 `vcs-probes/packed-nba`。同一 SV 的 `FIXED_REFERENCE` 配置可运行，TRACE 与 dsim 相同；它是固定数组参考，不是动态 NBA VCS 对齐。M67 单目标 packed NBA 的 NYI 仍保留。
- `order` 探针：阻塞两端均记录 `912`，NBA 为 dsim `912`、VCS `11229`，重复索引求值差异延续 M66。
- `growth-after-event` 特定扩容序列中，VCS 保留旧目标写成 `ffff`，dsim 按分配代次丢弃、保留 `5678`；另一个直接 2-to-4 扩容探针两端均丢弃。保留两份完整输入/输出，不推断 VCS 的完整分配规则。这两条差异不计对齐。
- 动态元素仍由同源 scalar/TRACE 观察；608 条不代表所有动态存储位已 dump。M67 负下界裁剪及 signed-negative/ascending 选择边界不变。
- 尚缺元素 scalar-ref、整体数组 timed/NBA、多维容器、数组返回/声明初始化/assignment pattern、完整数组转换和动态元素波形声明；完整 class/约束、队列/关联数组、SVA/覆盖率/UVM 仍未补齐。

首轮临时 control 可执行文件与回归目录重名已清理；三条旧拒绝用例从“拼接不支持”换成 net 目标后，实际更早由 semantic 阶段诊断，预期文本已修正。日志见 `logs/new.log`、`logs/final-ctest.log`、`logs/corrected-ctest.log`。VCS packed 编译故障从最初 NYI 预期改为单列 unavailable，未冒充通过。最终生成 C++ 来自未再修改的实现；再次从最终编译器生成的 8 份主程序与 13 份探针均逐字节匹配实际执行输入，8 份 sanitizer 输入也一致。

1515 个最终冻结输入，源包 SHA256：
`b409857ce73c74034c1f937de456e10262decb8d840bfaa97e5cb966725d5157`。
最终 Linux 使用 `linux/driver.py` 从该源包干净构建；旧观察线配置和旧诊断预期的前置运行不计作最终 Linux 验收。来源见 `source-manifest.json`、`source-changes.json`、`source-archive.json`、`final-identity.json`，汇总见 `results.json`。

复现入口：`tests/dynamic_concat/regression.py`、`run-vcs.py`、`verify.py`、`run-probes.py`、`run-vcs-negatives.py`、`run-linux.py`、`run-sanitizers.py`。本批未新测速、未跑全量 CTest 或 Linux sanitizer，不宣称完整 IEEE/VCS 兼容。
