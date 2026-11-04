# M183 编译单元级类与 typedef

接通文件级 class 和普通 typedef、按源位置冻结的类型/import 可见视图，以及共享类/特化身份和静态存储。使用私有声明 owner，不改写用户源码到模块或公开 package；RTL 与门级 parser 仍独立。支持范围和明确缺口见 [功能说明](../../docs/compilation-types.md)。

六模型覆盖跨实例类共享/继承/虚派发、全局参数化特化与别名、模块内同名遮蔽和类方法词法上下文、全局类静态字段事件及队列预测回滚、真实双分区、enum/packed struct/数组 typedef 与 96 位字段。VCD/DWF/异步 DWF 的 ordered/settled 独立解码和平台内编码一致性另验；全局类型不自动把独立纯整型过程合并成一个分区。

源顺序另验直接多文件、filelist、include，逆序时拒绝；两种长度的编译器入口别名复验生成 CPP 稳定性。16 个前端拒绝中包括当前明确不支持的合法语言形式，不把它们称为全部非法 SV。VCS 对 parallel 的验证使用未修改源文件加独立观察模块，读取两个输出，观察器源码哈希另记；其余正例直接比对 TRACE。

原版公开 UVM 预处理保持 1888084 字节、166 依赖，SHA256 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。首错已从编译单元 class 语法推进至 `chandle` 语义分析，不表示完整库展开或原生运行成功。

开发初轮并行 fixture 含 `$fatal`，调度器因此保守合为单分区；改为外部独立解码检查输出，重新执行后必须验证实际两个分区。初次生成器脚本因缺少执行位未运行，随后用 sh 显式调用；一次计数字段重命名误改 finalize 方法调用，已恢复并重建。初次编辑 VCS helper 的单处替换断言遇到两个相同命令而停止，修正为只更新正例路径后重新上传。原始失败日志保留，不计最终通过。

正常构建与 ASan/UBSan parser 均包含六轮全局身份、模块克隆、重复初始化、异常与截断语法恢复检查。sanitizer 关闭泄漏检测，外部 Z3 未插桩。已知全量构建的 `sizeof(Ready)==8` 静态断言错误沿用 M182 基线记录，本轮未修改 runtime.hpp，仅声明实际执行的构建目标与选定回归通过。未进行新性能测量。

```sh
python3 tests/compilation_types/regression.py BUILD/dsim OUTPUT BUILD/CMakeCache.txt
python3 validation/m183-compilation-types/sanitize.py ASAN_BUILD/dsim OUTPUT ASAN_OUTPUT
```

生产实现 `32c524c1e1bef93bf93c6a9f58a4f5b6f390dec2` 已推送。冻结 1245 项发布输入，SHA256 `ae00a2dfbfd28dc6eaaf8bf3bbd936bdf5de0b32f58a4474ad17491e27d99cb2`。本地原始产物保存在 `~/vibe-coding/dsim-test/evidence/m183-compilation-types`，生成程序、CPP 和波形不提交主分支。

| 验证范围 | 结果与记录 |
| --- | --- |
| 新功能 | 6 模型、110 捕获、16 前端拒绝、回滚/提交各 1；直接多文件/filelist/include 三次执行、一次逆序拒绝、两种入口长度的 CPP 重复发射；[native.json](native.json) |
| Sanitizer | 6 模型、16 拒绝、1 回放；最终正常/插桩编译器生成 CPP 与冻结发布全部相同；[sanitizer.json](sanitizer.json)、[final-asan-bindings.json](final-asan-bindings.json) |
| VCS | 六个最终源文件通过；parallel 另有独立观察模块，12 个反例共同拒绝/4 项明确能力缺口；[vcs-final.json](vcs-final.json) |
| 既有功能 | 文件级 import 5 模型25捕获，约束 foreach 5模型92捕获；[imports-development.json](imports-development.json)、[foreach-development.json](foreach-development.json) |
| 静态类与前向类 | 开发阶段182/308捕获通过，最终收集顺序调整后 clone 的18捕获重新执行替换；6新+10静态+17前向模型的99份三后端CPP均由最终编译器逐字节复现，复用对应原生程序结果；[final-all-bindings.json](final-all-bindings.json)、[class-static-clone-final.json](class-static-clone-final.json) |
| 原始GAP4 | M183稳定入口复查35个原始源文件，22发射/13拒绝；不计22个全部执行；与当前用户目录35源文件哈希一致；[当前对照](REPORT-GAP4-CURRENT.md)、[源码绑定](report-source-binding.json)、[gap4-native.json](gap4-native.json) |

本地稳定入口已更新为 `20261030T104446796406Z-ae00a2dfbfd2`。冻结源码独立构建、三组选定回归共227份捕获及mandatory全部通过；69份CPP和227份独立解码捕获记录于 [mac-reference.json](mac-reference.json)。六个实际入口模型的CPP/async DWF与验收产物逐字节一致，所选窗口通过；[mac-stage.json](mac-stage.json)、[mac-activation.json](mac-activation.json)。正常、sanitizer和本地实际入口的未修改公开UVM预处理和chandle首错相同。

103 Intel稳定入口已更新为 `20261030T104545587643Z-ae00a2dfbfd2`。三组回归227捕获已完整执行通过；69份CPP、227份独立解码捕获跨端相同，本批压缩字节也全部相同。六个实际入口模型的CPP/async DWF及所选窗口通过；远端公开UVM预处理与chandle首错同其他三种构建/入口一致。见 [linux-stage.json](linux-stage.json)、[cross-platform.json](cross-platform.json)、[linux-activation.json](linux-activation.json)、[public-linux-entry.json](public-linux-entry.json)、[finalization.json](finalization.json)。最终汇总由 [collect.py](collect.py) 核验并生成 [progress.json](progress.json)。

远端首轮publisher在向SSH输出进度时发生Broken pipe，候选收据标为FAIL、稳定入口未切换；原始 [linux-stage-failed.json](linux-stage-failed.json) 和 [finalization-failed.json](finalization-failed.json) 保留。三组独立子任务实际上全部完成PASS，恢复时明确复用本候选这三组已完成结果，未声称重新执行三组。用 [recover-stage.py](recover-stage.py) 重新核验1245输入、运行时头、构建/候选二进制及69份CPP，逐项比对Mac完整组结果，并重新执行help/parser/format/原生DB检查后恢复验收；见 [staging-recovery.json](staging-recovery.json)。收尾任务改用服务器本地持久日志，随后严格跨端比较和六个实际入口复验通过才完成激活。生产源码、输入、原生程序和回归数据均未更改；未覆盖原失败证据。
