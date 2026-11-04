# M167：参数化类形参与词法前瞻

继续参考 REPORT-GAP/GAP2 并沿未修改 Accellera UVM 2020.3.1 的真实阻塞推进。
修复 config_db_implementation:119 逗号后嵌套参数化类型被归为前一变量列表的问题；
实现见 [参数化类形参](../../docs/parameterized-formals.md)。
前瞻只读当前 parser 输入，在 Flex 缓冲换页后仍映射到正确位置，不用消耗/回填输入，
也不按某个设计或固定嵌套层数匹配。旧常见声明规则保持，新增回退同时支持类型旁的注释。

八模型、八拒绝例验证实际类型绑定/执行：65/71/129位、三层嵌套、默认/null、方向继承、
automatic ref、extern、package克隆、字符串/转义名、事务恢复与双分区。
完整parser直接注入不同位置和66KB注释，以覆盖预处理器通常会消除的路径；
另含畸形括号、未闭合字符串/注释与后续解析恢复。

开发测试最初把模块ref任务/函数留为默认static，被现有生命周期检查正确拒绝；
改为automatic。字符串长度手算少一个字符，$bits的文本预期由146改为154；
八模型最终完整回归通过。拒绝例三个诊断预期按实际既有错误文本修正。
这些属于测试修正，不算新增语言能力。开发日志保留在dev。

公开 UVM 预处理仍1888084字节/166依赖/原SHA；native首错推进到printer:176的real。
这不是公开包语义或运行通过，完整UVM、real值语义、约束随机、IPC、clocking/coverage等目标继续。
RTL lexer 独立修改，gate parser 和 runtime 未改，无新性能结论。
冻结、发布、sanitizer和实际稳定入口复验结果如下。

首候选六组中五组通过；interfaces的八原模型/28捕获及十九个有效拒绝例均通过，
最后一条ordinary_hierarchy_write负例因该能力早已实现而失败。旧稳定入口M166与新候选
对原始负例均成功生成相同CPP，stale-interface.json记录核对；不是本批引入的接受行为变化。
移除陈旧拒绝预期，新增带时间/整变量及切片写入的执行正例，保留接口视图写权限等十九拒绝例。
首候选未激活，初始源码与失败收据保留initial-*；测试修正后重新冻结、重跑六组。

最终冻结1c0e563c（仿真实现与5d8970b5相同，后续修正接口测试），1913源码成员/1072发布输入绑定。
Mac六组parameterized_formals、class_parameter_lists、extern_methods、interfaces、header_imports、waveform_selection
共781捕获及mandatory完整parser/格式/原生DB检查通过。新八模型146捕获/8拒绝/1回滚1提交，
实际2分区通过；25份最终生成程序与开发证据逐字节相同。完整parser、八前端/8反例、
八生成程序与回放ASan/UBSan通过；双分区+独立writer TSan程序与最终CPP相同。无LSan/速度结论。

Mac稳定版20261029T090606578645Z-f2af9481d122已激活，binary SHA256为
066a7f84818ab0526666be8805725125482a8a0a72fdd00883b45105e4d22a21。
实际入口重新编译七新模型，完整异步波形、rollback用户所选范围波形及原始r02（省略--top）
执行与候选一致；原始输入未改。实际入口和ASan版公开库预处理保持1888084字节/166依赖/原SHA，
native仍在printer:176正常拒绝且不留部分CPP。完整UVM/real值语义/约束随机/IPC等目标继续。
103只读SSH返回255服务器不响应，未启动重复构建或修改远端入口，旧Intel超时仍待查。
本批没有VCS/Intel对照或跨平台/性能结论，用户experiments/matvec16未修改。

源码、开发及Mac候选归档共6724个成员逐项SHA256核对通过，归档覆盖当前选定证据。
归档位置、摘要和审计结果见source-freeze.json、development-archive.json、mac-archive.json及archive-audit.json。
