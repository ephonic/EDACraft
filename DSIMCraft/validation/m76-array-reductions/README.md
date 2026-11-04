# M76：数组归约方法

补入固定/动态 unpacked 数组的 `sum/product/and/or/xor` 无 `with` 方法，支持可选空括号、常量前缀子数组、元素位宽/符号、宽四态值、空动态数组，以及固定/open 值参数与动态 const-ref 参数。接通现有自动帧、组合依赖、阻塞/NBA/延迟、并行与预测回滚。RTL/gate parser 继续分离；没有新增运行时或 checkpoint 状态。

- [原生验收](native-results.json)：6 个共享模型和 1 个原生动态敏感性模型，串行/时间轮/双线程，ordered/settled，VCD/DWF，共88次完整流比较、4次失败预测回滚、10个错误输入拒绝；独立 lane 确实分到两个分区。
- [VCS 原始记录](vcs/results.json)：10.131.254.103，`source /apps/EDAs/syn.bash`，W-2024.09_Full64。共享源通过 SHA256 及逐字节核对。[逐位比较](vcs-bit-results.json) 比较全部3,494条公开物理位 settled 时间线，无排除位；27根只读 observer 暴露固定数组字（标量数组字的[0:0] observer 显式映射到标量位身份）。动态堆容器不导出为 VCD 数组字，使用归约输出及 TRACE 检查，不能把未导出的动态元素称作已逐位核验。
- [ASan/UBSan](sanitizer-results.json)：编译器生成及7个实际生成程序执行，完整 C++、stdout、ordered 波形与普通构建一致。[最终编译器检查](final-compiler-sanitized.json) 和 [parser 反复解析/克隆/清理](parser-sanitized.log) 另存；泄漏检测关闭。
- [既有回归](regressions.log) 和 [enum 复核](enum-regression.log)：数组形参、动态数组、open 数组、查询、enum、packed aggregate、旧前端、streaming、门级入口及 parser 内存。初次 enum 检查发现旧诊断已泛化而测试仍要求 enum 专用诊断；恢复专用诊断后重跑。

实测规则见 [功能说明](../../docs/array-reductions.md) 和 [初始探针](probe.sv)：结果自定元素位宽，8 位 ff+2+3 为04；singleton Z 对五方法均保留Z；空动态数组的 product/and 也返回0。130 位跨字、未知值、反向声明、NBA 采样、动态扩容/删除和自动任务挂起都有覆盖。

保留两项 VCS 边界，不计作对齐通过：

- [动态隐式敏感性](probes/dynamic-sensitivity/README.md)：VCS 未因元素写入/resize/delete 重新执行仅依赖动态归约的 always_comb，dsim 会执行。原输入、VCS 编译/执行日志、VCD 独立保存；原生模型保留 dsim 预期，共享时序模型加入明确的标量 refresh 依赖。
- [归约结果数组查询](probes/query-vcs.log)：VCS 拒绝 `$dimensions(a.sum())` 作为查询操作数。dsim 保留元素 packed 类型元数据，[独立检查](query-results.json) scalar/原始 packed 边界/packed 二维（包含 ASan/UBSan 生成器和实际程序执行，可用 verify-queries.py 复现）；共享模型仅检查 `$bits`，不把其它查询计入 VCS 对齐。

仍缺 `with`、定位/排序、queue/关联容器、enum/packed aggregate 元素、多维整体归约及动态子数组前缀。未执行全量 CTest/Linux 原生构建，未新增 VCS 性能测量。复现入口：`python3 tests/array_reductions/regression.py build/dsim build/rtl-array-reductions`，再执行本目录 `verify.py`。

稳定版已发布至 `~/vibe-coding/dsim-test/bin/dsim`：[49项检查](stable-release.json) 含[六组用户问题 case](stable-reported-cases.json)及 gate CLI/SDF；[47个完整 C++、stdout、波形流身份](stable-identity.json) 一致（6新模型对原生验收，41旧模型对 M75 稳定版），另核对类型查询生成代码。实现提交 `3b5f81262b5a8ac13d68c1393a3d592a98bde3ba`；binary SHA256 `6bfb8cc3d68c1279684fa0aa5f96e522fad127c73321b5b4e738c49f62c7e7b1`。8个运行时头文件快照随发布冻结，保留用户未跟踪的 experiments/matvec16。
