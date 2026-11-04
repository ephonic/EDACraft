# M75：SystemVerilog 流式拼接

补入 `{<<{...}}` / `{>>{...}}`、常量/整数类型 slice size、非整块重排、四态宽 packed 数据、固定 unpacked 数组/子数组打包和静态目标拆包。接通声明初始化、常量/参数、连续 RHS、阻塞/NBA/固定延迟、自动局部变量、函数返回和值参数。RTL/gate parser 继续分离，复用现有值、目标分片、依赖、快照和调度；没有新增 checkpoint 状态。

- [native-results.json](native-results.json)：6 模型 × 3 后端 × ordered/settled × VCD/DWF，加 3 次失败预测回滚，共 75 次完整波形比较；23 个错误/未支持组合拒绝检查；实际双分区。TRACE 固定期望取自真实 VCS。
- [vcs/results.json](vcs/results.json)：`10.131.254.103`，`source /apps/EDAs/syn.bash`，VCS W-2024.09_Full64。6 组共享源逐字节一致，保留编译日志、执行日志和 VCD。[verify.py](verify.py) 比较全部 1,816 条公开物理位的 settled 时间线，无排除位；18 根只读 observer 暴露 VCS 不导出的固定数组元素。
- [sanitizer-results.json](sanitizer-results.json)：6 模型经 ASan/UBSan 编译器生成，并实际编译和运行 instrumented C++ 程序，完整生成 C++、stdout 和 ordered 波形与普通构建一致。[最终编译器复核](final-compiler-sanitized.json) 验证 6 个完整 C++ 身份和全部 23 个拒绝分支。[parser 检查](parser-sanitized.log) 包括重复解析、参数化克隆、generate 和清理，关闭泄漏检测。
- 10 个不同既有检查组通过：assignment patterns、数组复制/形参、固定初始化、packed aggregate、旧前端、generate、事件赋值、gate CLI 和 parser 内存。首次回归发现 Verilog 模式检查范围过宽，已将其限定到流式操作。[首次记录](initial-regressions.log) 保留失败；[修复后记录](regressions.log) 验证旧前端及 parser 内存通过。加新增流式拼接，共 11 个不同检查组。

实现遵循实测尺寸规则：直接打包向右补零；拆包先取源高位，再按目标方向重排。非整块 slice、64 位边界、跨字的 130 位 X/Z、bit 转换、数组声明方向、函数求值次数、延迟采样和真实独立 lane 均有覆盖。窄值用一对 64 位 mask，宽值按源/目标字边界搬运到一个输出 word vector；本批不作 VCS 性能结论，也未运行全量 CTest 或 Linux 原生构建。

边界见 [功能说明](../../docs/streaming-concatenation.md)：动态/关联容器、with 范围、动态数组前缀/目标选择、嵌套流式目标、原始 enum 目标、直接模块连接/端口默认值仍缺。事件控制直接 stream RHS 的 VCS 行为差异保留在 [探针](probes/README.md)，该组合明确拒绝；共享时序模型验证先打包为普通临时变量再做事件 NBA。不能据此宣称完整 SV/VCS 支持。

复现：`python3 tests/streaming/regression.py build/dsim build/rtl-streaming`，再运行 `python3 validation/m75-streaming/verify.py`。稳定发布见 [stable-release.json](stable-release.json) 和 [stable-identity.json](stable-identity.json)：43 项发布检查全部通过，含[六组用户问题 case](stable-reported-cases.json)与门级入口；41 模型完整生成 C++、stdout 和波形流身份一致（6 个新模型对本轮原生验收，35 个旧模型对 M74 稳定版）。入口 `~/vibe-coding/dsim-test/bin/dsim` 已原子更新，冻结 8 个运行时头文件。

实现提交 `83c2ba1c42b69a3b527e5e06f54d39af7fe7f4f4`；binary SHA256 `e1e9cf8606ac85c50636cfa5eb2909833e327fada569f861602e056e01d73509`。工作区仅保留用户未跟踪的 `experiments/matvec16/`，未纳入发布输入或提交。
