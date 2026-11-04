# 独立门级预处理：已采用

新增门级 `GateSource`、文本所有权接口及实际结构 scope 时间。普通网表快速扫描，不构建 token/逐行表/RTL AST；宏/include 复用公共词法预处理器后继续独立 Network parser。完整功能说明与限制见 [门级预处理](../../docs/gate-preprocessing.md)。runtime、模型求值、并行、波形 header 不变，没有新仿真提速结论。

| 验证 | 结果 |
|---|---|
| 本地 / Linux 同源完整回归 | 各 39 项，162.36 /210.09s |
| 独立结构测试 | 快/慢路径生成代码一致；层级、CRLF、注释、转义名称、实际/未使用 scope 时间 |
| 实际 CLI | 宏/include、时间精度、原始诊断、依赖、直接/硬链接保护、非法指令明确失败；绑定模式接受预处理选项 |
| 新 VCS 时间参考 | 4 组分别编译，各运行三次；native 对应各三次完整 TRACE 相同 |
| 实际 ASan/UBSan | 编译器、独立结构单测、3 组宏/include/时间+IOPATH联合输入的6个生成 native/replay 程序 |
| 预测与波形 | 联合输入整个生成代码与原基准相同；待交付事件的拒绝回放/接受提交，完整 ordered/settled 流和稳定态位通过 |
| 代码保持 | 两平台各11份完整SDF程序与已验收最终Linux版逐字相同；原5份SDF数学原型、3份波形原型未改 |
| 原始 IC 输入 | 原13份带合法时间头的网表到达明确 INTERCONNECT 运行时拒绝，失败不覆盖已有源/IR；未实现 IC 运行时 |
| 实际完整设计 | 300,909 单元、335,872 网、111 模型；既有64位封装保留原始网表字节前缀，独立RTL激励、未改Liberty；旧/新实际编译器整个C++相同 |
| parser 补丁 | 原始ZIP重新应用累计补丁，108个文件全部相同；本项只新增独立gate parser两文件的所有权入口 |
| 默认构建 | build/dsim重建；3个旧程序整文件/golden、宏/include+SDF实际运行、结构新增测试及13例严格拒绝通过 |

单次前端观察：31,597,253 字节结构输入快速扫描约0.252s。旧/新全过程 user+system 25.83/25.88s、wall 25.90/25.95s、峰值RSS 1,973,772/2,061,764 KiB。扫描文本在Liberty读取前准备会增加暂存；这些单次值不能作为配对性能结论，也没有新VCS仿真计时。原始`time -v`在`linux-verified/real-corrected`。支持功能扩大与仿真加速分别验收。

开发失败保留：`initial-ctest-failures.json` 是首轮37/39失败的工具输出摘要，非完整原始日志；随后聚焦和最终完整日志单独保留。初次sanitizer构建与源修改重叠，陈旧对象错误地让未实例化DUT降低精度；`sanitized-front*.log`与初始IR保留，删除对应对象后重编的`sanitized-rebuild.log` / `sanitized-accepted.log`及联合程序均通过。真实输入最初误把结构封装当RTL而触发token上限，原失败在`linux-verified/real`；正确验证沿用既有完整门级封装和独立`real-golden/top.v`，不裁剪网表。

候选归档 `/tmp/dsim-gate-source-candidate-source.tar.gz` SHA `384712bd658635a39d02637097640940c7658265f91e9c6ef2922b139914125b`，256工程/108parser/3原型依赖。`source-snapshot.json`保留当时文档，采用版`production-snapshot.json`只更新状态文档，代码须相同。

Linux证据 `/tmp/dsim-gate-source-linux-evidence.tar.gz` SHA `5c98d4c5ee08f32b5a9a8e64c890e91fd9805e9af0ed1832d819b1506543ad00`，979文件；远端`/tmp/dsim-gate-source-linux-1018-MYUwiy`已结束。VCS证据 `/tmp/dsim-gate-source-time-vcs-evidence.tar.gz` SHA `1b8ada9bdd23dd1d44ce802da8c77d25d463b6a70b0958cf36724d61535bf933`，220文件；远端`/tmp/dsim-gate-source-time-1018-5ZL79a`已结束。实际sanitizer编译器/单测在`sanitized-bin`，六个生成二进制及波形在`integrated`。

`verify.py`核对当前实现、归档、原始trace/输入、生成代码、波形、实际二进制及旧原型，不修改旧冻结证据。最终结果为`verified-results.json`，本批封存表为`verification-manifest.json`。完整VCS功能/性能目标继续；下一功能为有序MIPD合并与私有接收pin，性能继续独立定位和配对筛选。
