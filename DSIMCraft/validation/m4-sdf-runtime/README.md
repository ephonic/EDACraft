# 有限的编译式 SDF IOPATH：实现与验收

新增 `--sdf-annotate`，将已匹配的 specify / SDF 数值表接入实际门级编译器。RTL 与结构门级 parser 保持分开，Liberty 仍提供功能模型。支持无条件 parallel / full path、四态 12 转换、边沿选择、模型基值、ABSOLUTE / INCREMENT 与独立 corner；原始输出 net 保留驱动身份，私有 raw 输出经路径事件交付。输入沿历史、输出前值和待交付状态随检查点恢复。命令与边界见 [运行时说明](../../docs/sdf-runtime.md)。

条件 / ifnone、路径极性、pulse 声明 / 阈值 / RETAIN、INTERCONNECT / PORT / DEVICE 和 timing-check 执行仍明确拒绝。只有主动 `--no-timingchecks` 才可跳过检查声明。完整真实 flattened SDF 尚不能运行，不把 867,982 张表的建立称为实际时序仿真。

验证内容：

- 11 组新 VCS 单独编译，各运行三次，实际 native CLI 也各三次；核对全部 TRACE 和包含 0 时刻的输出位波形。覆盖 12 转换、非对称短脉冲、多输入 latest / 同刻最小、#0、多输出、多个驱动、full path、触发器、反馈和两个 DUT 独立状态。每个编译案例保存零错误/警告注解日志；VCS 后续运行复用注解缓存，不伪造三份注解日志。
- 增加启动诊断：5 个独立输入包含初始 0/Z/X 与两种 #0 反转，一次新 VCS 编译后三次 trace 对三次 native。最初发现边沿过滤在 0 时刻错误，保留失败候选和日志；修正为启动时不按边沿过滤，此后按边沿选择。不是完整 specify / pulse 兼容性证明。
- 54 组既有不可变 VCS 数值参考，全部通过实际 CLI 编译和三次运行；4 个已知部分覆盖成零再增量组合继续明确拒绝。它们不是本轮新运行的 VCS。
- 本地原有 32 项与新增 5 项通过，分组运行；Linux 同一冻结源完整 CTest 37/37。生成路径的错误分支回滚 / 正确分支提交，与相同 run_until 边界的基线比较全部打印和完整 ordered / settled DWF；不滤去中间值或失败分支。
- 本地 9 个实际 ASan/UBSan 二进制：编译器、普通/紧凑内核和六个实际生成程序 / replay。关闭路径的 runtime 在两平台各 8 种宏组合下，空白规范化后的完整预处理结果与旧冻结 header 相同。默认编译器重新构建，三个非 SDF 生成主体逐字相同并核对 golden；实际多输入 SDF CLI 运行通过。

冻结候选源 `0269d3dff9919932dcd8362df05feacad3c5e52741fc8ddc2fb5a29ba79757db`，247 工程、108 parser、3 波形依赖文件；文档另列。未修正启动规则的早期源 `2e4799c19aea586bc5e1da0a5665b494cae96d3da35129c90641d5c0e48b960b` 保留但不采用。原五个数学延时原型、三份波形原型、所有先前归档与命名 sanitizer 构建保持不变。

`source-snapshot.json`、`vcs-evidence.json`、`vcs-extra-evidence.json`、`linux-evidence.json` 固定各归档及逐文件身份；`verify.py` 从原始 trace、波形、计时之外的功能证据、实际 sanitizer 符号、Linux 完整日志及默认生成结果独立核对。`verified-results.json` 保存结果。源码与外部证据归档路径在 JSON 中。

本批没有新的仿真提速结论。另一个直接编码读取试验未过门槛，见 [性能试验](../m5-scalar-read/README.md)。整体 VCS 对齐、自动分区、自动预测与波形扩展继续推进。
