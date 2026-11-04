# M141：interface 子程序与按名称的 modport import

实现提交 `40a085462a761901b87919b97e2c585d5ee59e9d`。支持实际 interface 实例、typed/modport/generic 端口及转发端口上的 task/function 调用。子程序使用实际 interface 的词法作用域和共享存储，保留实例参数、返回类型、默认/命名参数、automatic/ref、静态局部变量及既有任务延时/NBA 机制。修复预处理器遗漏 interface timescale 的问题，跨时间单位调用按被调用 interface 的时间单位执行。RTL 与门级 parser 保持分开。

七个模型覆盖直接/转发/泛型端口、前向 import、嵌套词法调用、输入/输出/inout/ref、固定数组和字符串、参数/generate、多实例静态存储隔离、符号扩展、enum/packed struct 返回及后续方法/成员访问、组合逻辑敏感性、重叠 automatic 任务和不同时间单位。数值、字符串、时间及失败条件由模型显式检查；无输出的 parallel 模型还独立检查最终值 18/26 及零错误。共享实例的 activation 模型是一分区，独立实例的 parallel 模型为实际两分区。

本地新组通过三种执行配置、完整逐信号有序波形比较、7 次预测提交、7 次回滚、2 次重复 checkpoint 恢复及 21 个拒绝例，共 35 次波形捕获。拒绝例保留原始目标文件，检查编译失败不会破坏已有输出。完整 RTL semantic/cleanup 回归和 14 份实际生成程序的 ASan/UBSan 通过，均关闭 leak detection。另有预处理及时间单位测试。发布候选和最终稳定入口的记录分别保存在 stage、release、activation 与 entry JSON 中。

`source-proof.json` 证明归档的 1794 个源码文件逐字节匹配实现提交及 manifest；归档 SHA256 为 `15b9a75d1d0de3e2bac27b4994e5f26fbe528ea98d4793ec32d282f94b705406`。原始日志、生成的自有模型代码、波形、源码包及 JSON 见 `evidence-index.json`，两端镜像校验见 `mirror-proof.json`。用户的 `experiments/matvec16/` 未更改。

103 恢复后，使用同一份冻结源码完成 VCS W-2024.09_Full64 参考。六个原始模型的 TRACE 及 1,578 个共同声明 bit 的 settled 时间线均与 Mac DSIM 一致。basic、clones、timing、activation 四模型覆盖全部声明；arguments 的两个固定数组元素和 parallel 的两个未命名循环局部变量共 128 bit 未被 VCS `$dumpvars` 导出，加入 `-debug_access+all` 仍相同。这些声明逐个列入未覆盖清单，没有计入已比较位数。sensitivity 原始模型在 interface 返回值的后续成员/方法访问上被 VCS 报 `Error-[NYI]: Xmrs into scopes within interface`，保留完整诊断，标记 `REFERENCE_UNSUPPORTED`；DSIM 的独立检查、跨平台 35 份生成 C++/stdout/完整逐信号有序波形仍通过。详见 `mac-vcs.json`、`vcs-reference.json`、`vcs-coverage-probe.json`、`cross-platform.json`。不是七模型完整 VCS 对齐声明。

Linux Intel 稳定版已激活：`/apps/EDAs/own/dsim/releases/20261028T094130Z-40a0854`。`/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 指向同一二进制，SHA256 `a1b1cc388b39052f26b19ca60c1bbc21df0cfdcde3448feff57c190a5d0f012f`。九组正式回归、mandatory RTL/格式 parser/原生 DB 检查及额外的 preprocessing/time_runtime 均通过。实际安装入口重新编译运行 basic 后，生成 C++、stdout 和完整逐信号有序波形均与正式组一致。编译器为 Intel 2026.1.1 Release，模型使用 `-O2 -xHost`、严格浮点，不启用 IPO；详见 `linux-build-config.json`、`linux-release.json`、`linux-entry.json`。Linux 的 VCS 结果与 Mac 相同，具有上段明确列出的参考覆盖限制。首次 SSH/SFTP 挂起及本次恢复信息保留在 `remote-status.json`；Mac 原始激活记录保留在 `mac-activation.json`。

两端的六个既有 CPU/CRC/muldiv/AXI4/sequence/history 模型，其完整生成 C++ 均与各自 M140 逐字节相同，八个 runtime 头文件也相同，详见 `mac-generation.json`、`linux-generation.json`。没有 runtime 性能测量或加速结论。

限制：只实现按名称 import；prototype-form import、modport export、virtual interface、interface 数组、clocking、普通模块的层次 task/function 调用及完整 SV 验证语言仍未实现。ref 实参继续沿用既有存储/类型限制，不支持任意层次表达式作为 ref 实参。不是完整 VCS 或 UVM 兼容声明。

Mac 稳定版已激活：`20261028T084428760694Z-ee6fad1ddedd`，入口 `~/vibe-coding/dsim-test/bin/dsim`。二进制 SHA256 `6ae7bbcc2c6aa517a4460bf3f54536ad0d10be6ce69e62fb8b1339a1642add95`。实际入口重新编译 basic 模型后，生成 C++ SHA256 `b4bf37e82cd54baa773af01e13a1c93e48ab66848aa5f139168437b8def0f474`、stdout 和完整逐信号有序波形均与候选验收一致。

九组正式 Mac/Linux 发布回归均 PASS；每端合计 622 次捕获、149 个拒绝例，另有 mandatory RTL parser、格式 parser、原生 DB 单元检查：

| 回归组 | 状态 | 捕获 | 拒绝例 |
|---|---|---:|---:|
| interface_subroutines | PASS | 35 | 21 |
| interfaces | PASS | 28 | 20 |
| subroutines | PASS | 62 | 7 |
| call_arguments | PASS | 74 | 24 |
| automatic_subroutines | PASS | 75 | 24 |
| ref_arguments | PASS | 77 | 11 |
| const_ref | PASS | 78 | 23 |
| string_subroutines | PASS | 46 | 11 |
| frontend_compat | PASS | 147 | 8 |

续验没有修改冻结的编译器源码。完整证据为 15 个归档，存于 `~/vibe-coding/dsim-test/evidence/m141-interface-subroutines/` 和 103 的 `/apps/EDAs/own/dsim/evidence/m141-interface-subroutines/`，按最终索引逐个核对字节数和 SHA256。最初八个归档保持原样，其中旧 release/activation 元数据记录的是首次 Mac 激活时远端尚未完成的历史状态；本目录和 `resume-validation.tar.gz` 记录本次续验结果。`index.json`、`mirror-proof.json` 为归档之外的最终校验 sidecar，避免自引用哈希。VCS 生成的 C/C++ 和厂商可执行文件未导出或入库。

103 上使用 `/dev/shm/dsim-m141-tools/vcs.py` 生成原始参考，`publish-linux.py` 构建并回归，`complete-linux.py` 核对源码/二进制/覆盖范围后激活、检查入口并打包；`export-linux-reports.py` 导出派生 JSON。严格比较器要求四模型完整声明相等、另两模型恰好只有已列出的 128 bit 缺失，出现任何新增覆盖差异或值/时间差异都会失败。
