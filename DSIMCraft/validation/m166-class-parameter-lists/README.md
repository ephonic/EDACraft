# M166：REPORT-GAP2 与类参数列表

读取用户报告的实际路径 `~/vibe-coding/dsim-test/rtl-tests/complex/REPORT-GAP2.md`，
SHA256 `0a316c371261b0ab962f0a46a7e4818d6df74d70f4c051dc044720b798eba366`。
报告基于较早 M156 二进制，static、string 关联数组、队列和部分 DPI 已由后续批次补充；
本批继续补公开库的实际阻塞，不将旧缺口表直接当作当前功能状态。

补齐连续 class 参数声明的种类/类型继承、首项省略 parameter、命名值类型和必填值参数，
以及逗号后作用域限定类型形参。实现边界见 [类参数列表](../../docs/class-parameter-lists.md)。
八个执行模型和16个拒绝例覆盖参数独立绑定、宽度/符号/二态、默认依赖、克隆、
继承/extern/虚调用、作用域、回滚及用户范围异步波形；前端语法冲突数与基线同为78。
RTL parser 独立修改，gate parser 和 runtime 未修改。

初始测试的71位十六进制文本预期多了一个前导零，已按实际位宽修正；
作用域形参测试最初省略 input 而继承前项 ref，传字面量被正确拒绝，修正了测试。
必填类型的诊断预期改为现有文本。拒绝例还发现非恒定 packed 参数边界被接受，
已增加真实常量检查。这些开发失败日志保留在 dev，不计为最终验收通过。

未修改公开 UVM 的 native 首错从 pool:49 推进，经 resource_pool:206 后到
config_db_implementation:119 的逗号后参数化类形参。仍不能原生编译运行完整 UVM。
原库预处理仍1888084字节、166依赖及相同SHA；没有新的VCS或性能结论。
发布、sanitizer及实际稳定入口验证完成后追加结果；103状态单独记录。

首个4eea9dcd候选四组通过但未激活。最终词法复核发现新规则对form-feed/backspace分隔的表达式操作符检查与WHITE集合不一致，补齐字符集合及parser回归后重新冻结验收；初候选/源码收据保留为initial-*。

最终冻结9bde3e2f，1901源码成员/1060发布输入绑定。Mac四组（class_parameter_lists、parameterized_classes、extern_methods、waveform_selection）742捕获和mandatory完整parser/格式/原生DB检查通过。新八模型146捕获、16编译拒绝、1回滚1提交、实际2分区通过；25份发布生成程序与开发证据逐字节相同。最终完整parser、八前端/16反例、八生成程序及回放ASan/UBSan通过；双分区/独立writer TSan程序与最终发布CPP相同，无LSan或速度结论。

开发完整八模型曾通过，随后scope表达式测试更新单独重跑；最后七个旧serial前端逐字节复验、全部最终serial生成程序和回放经sanitizer重新执行。不能将该开发记录描述为最后一次完整普通回归。最终publisher独立重跑全部四组，结果记录在mac-stage.json。换页符边界首次测试没有放在逗号后而未触发规则，修正测试后明确复现首候选拒绝/最终版接受。

Mac稳定版20261029T082926389035Z-01aea20677c8已激活，二进制SHA256为7ad7e031bf0d2011ae488de7fa74822200de2b3bad183a22891830013b5df6bb。实际入口重新编译七新模型，完整异步波形、rollback所选范围波形及原始r02（省略--top）执行与候选一致；原始输入未改。实际入口及ASan版公开UVM预处理保持原值，native仍在config_db_implementation:119正常拒绝且不留下部分CPP。326参考文件与固定原归档相同。完整UVM、约束随机、IPC/clocking/coverage等目标继续。

报告原19探针复查为9个前端/生成通过、10个拒绝，详见report-probes.json；本批未将9个全部做native执行。103只读SSH返回255服务器不响应，未启动重复构建/修改远端入口，旧Intel超时仍待调查。本批没有VCS对照或跨平台/性能结论。用户experiments/matvec16未修改。

源码、开发及最终Mac证据已归档并逐成员核对，archive-audit.json验证归档载荷与当前完整选择一致；公开库展开源及二进制不作为该证据归档的载荷。原始报告探针另保存在外部report-probes目录。
