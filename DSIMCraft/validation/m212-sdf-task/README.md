# M212：静态 SDF 系统任务

继续处理 M211 已确认的 `$sdf_annotate(..., dut, ...)` 缺口。RTL AST 只在第二参数放行模块命名空间，保留含空实参的整个参数表；在全局精度选择和过程降级之前，绑定真实结构网表根并构造现有定时表。没有把任务当作空操作，也不修改用户 TB。支持范围和限制见 [说明](../../docs/sdf-task.md)。

已在本地通过八个实际生成模型：直接根实例、原 TB 三参数形式、参数文件名/命名块日志、min、max+scalar/jobs/dictionary/wheel、嵌套层次、generate+请求线程后的串行回退、模型精度细于 TB 的场景。各模型与独立 CLI 注解基线的完整物理波形一致。103 全部重新用 VCS W-2024.09 编译运行，相同 TB/net/model/SDF 原文件字节与哈希核对，八个模型的 TRACE 和完整 top.A/top.Z 时间线一致。消毒器和双端冻结发布状态在最终结果中单列，不能以开发工作区结果代替已发布候选。

明确拒绝与保护检查覆盖延后/#0、条件、always/final、finish 之后、多次注解、错误/默认目标、动态文件名、NUL 字面量、错误 corner、缩放、真实配置、CLI 混用、显式 tick、日志/输出路径冲突、符号链接/硬链接和多 gate 实例，共 28 项。检查保留全部已有编译输出和 SDF 输入。另有 gate_source_cli、完整 11 场景 SDF 路径、路径 checkpoint、SDF CLI、RTL parser 重复清理及 preprocessing 共六项 CTest 通过。

第三参数是 configuration，第四参数才是日志。独立 `probe-vcs.py` 已确认 VCS 接受不存在的第三参数；dsim 对此明确提示默认注解，已有真实配置仍拒绝。首次 VCS 测试对第四参数使用 string localparam 报 IAFSDFA，最终共享测试改为字符串字面值；首次失败日志和原夹具留在外置证据，不计为双方通过。额外 NUL 保护的初始参数夹具经 parser 转换会删除零字节，因此改用实际触发拒绝的 NUL 字面量，未修改 parser 的既有字符串转换语义。

`cases.py`/`regression.py` 在 tests/sdf_task，`vcs.py` 重编参考，`compare.py` 按原文件与完整信号时间线比较，`sanitize.py` 检查实际前端及生成模型。SDF 在编译时静态绑定，日志在仿真语句执行时写出。源任务与 `--sdf-annotate` 共用同一独立门级 IR、timing model、SDF 绑定和执行后端。

103 原 modmult 网表目录仍为空，完整原设计门级/SDF 仿真依旧不能验收；本轮补齐任务入口，不能据此宣称原设计全量 SDF 或 VCS 功能已全部对齐。动态重注解、多实例独立定时表、默认 TB 作用域、缩放与真实配置仍有明确缺口。

最终生产实现为 `34ae44c3`，双端冻结输入共 1506 项，SHA256 `b0b3dc7ad1480d0a7ae19abed5d0df9c3e25464f7cf78ad8cc9f519ac9b479e6`。Mac 稳定版本 `20261101T115151300100Z-b0b3dc7ad148` 与 103 Intel 版本 `20261101T115920520670Z-b0b3dc7ad148` 均已激活。两端发布候选各自通过八模型、28 拒绝和八项 `--emit-preprocessed`/`-E` 逐字检查，实际稳定入口重新编译执行源任务、运行时日志、`-F`/`+libext+` 和完整输出时间线；默认无波形 scalar 模式也各自重新编译执行通过。103 的两个公开入口指向同一发布版本。

跨平台八个源任务模型和八个 CLI 基线的生成 C++ 一致；仅日志模型允许将记录命令中的绝对日志目的路径替换为同一个占位符，其他内容不归一化。16 份完整解码捕获相同。Mac ASan/UBSan 覆盖八次实际前端、四个实际生成模型、28 拒绝和重复 parser 清理；未启用泄漏检测。Linux 既有完整十一场景 SDF 路径、SDF CLI 和 parser 清理回归也通过。详见 `cross-platform.json`、`sanitizer.json`、`default-mode.json` 和双端发布收据。

103 新入口重新生成原 modmult RTL CHKMODE 的 C++，与 M211 逐字相同后，核对 SHA 并复用 M211 已验收原生程序，运行固定 VCS golden，128 笔、0 错误；本项没有重新编译原生程序，`modmult.json` 明确记录复用。完整 SDF 再次解析得到相同的 1,744,700 项；这属于 parser 回归，不代表完整设计的 SDF 仿真。

首次 `99ddf97d2bda` 候选未激活：发布前检查发现延后写出的预处理文件丢失指令，修正后重新冻结并执行全部新增检查。初始 VCS 日志参数夹具和 NUL 参数夹具失败也保留在外置原始证据中，未计为通过。原始命令、C++、波形、输出、发布完整输入清单和初始失败见 `archives.json` 所列两端目录及 manifest；仓库只保留脚本和紧凑结果。
