# SDF 原始数值绑定

生产绑定接口新增 `numeric_preview=false`，回调交付单位和 corner 上下文，无提前舍入或 uint64 tick 溢出。默认 CLI 继续原预览路径；实际路径/transition/COND 执行未接入。

本地 4 项 SDF parser/CLI/binding/CLI 回归通过；新增原始模式测试将回调与冻结的精确十进制暂存层连接，验证小数 INCREMENT 最终舍入、大数抵消、跨单位、空 corner 继承、条件/RETAIN 和错误保护。独立 ASan/UBSan 构建的实际 `sdf_binding_test` 通过并检查符号；macOS 未运行 LSAN。具体二进制与输入 SHA 见 `local-results.json` 和源快照。

默认编译器重建，生成的计数器 C++ 与变更前逐字一致；本批没有修改仿真热路径、RTL/gate parser、波形编码或并行内核。Linux 独立干净构建后 4/4 通过（0.49s），160 工程/108 parser/4 原型依赖全部 SHA 核对；日志和二进制 SHA 见 `linux-results.json`。此时仍未施加路径延迟。
