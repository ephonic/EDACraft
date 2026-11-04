# M21：SystemVerilog 普通立即断言与 severity 诊断

语言路线以 IEEE 1800-2023 为基线，当前仍是明确列出的子集，见 [功能范围](../../docs/systemverilog-verification.md) 和 [计划](../../plan1017.md)。本批新增普通立即 assert/assume/cover、标签、成功/失败动作、缺省失败诊断和 $fatal/$error/$warning/$info。关键字、AST 身份、参数化/generate 克隆和直接 C++ 代码生成已接通；RTL/SV 行为 parser 与门级紧凑 parser 保持独立，未改 runtime 布局或门级 parser。

条件按四态布尔规则只求值一次；复用已有静态函数/任务、循环、delay/event/NBA、输出事务、检查点及并行依赖。cover 接通条件与用户成功动作，尚无自动命中统计、覆盖数据库或报告。deferred/concurrent SVA、property/sequence、clocking、class/随机化、完整类型系统及完整 IEEE 1800-2023 合规性尚未实现。

五组 actions/defaults/hierarchy/delays/parallel 通过三后端、ordered/settled、VCD/DWF 共 **62 次捕获**、**2 次实际失败预测回放**、**10 类拒绝检查**与 **3 组 fatal 终止**。检查副作用单次求值、X/Z、嵌套动作、显式空 else、缺省诊断位置、静态子程序、generate 克隆和 NBA；回放 stdout 与串行逐字一致，缺省诊断仅输出一次。双线程模型实际两分区、九窗口，两域输出/失败数/命中数有独立时刻和数值预期。见 local-results.json、local-regression.log。

实际 VCS W-2024.09 五组 TRACE 与 **1345 条可观察物理位时间线**一致，逐项核对层次身份、位号和 1ps 时间轴。仅排除两个 VCS 不导出的 inline 循环计数器，无普通信号排除或名称映射；输入 SHA256 和名单见 vcs-results.json，原始输入、编译/执行日志与波形在 vcs/。额外三组 fatal 探针两者均在 TRACE before 后终止且不执行 TRACE after；**该 VCS 运行配置返回 0，dsim 返回 1**，退出码策略有差异，诊断文字也不作逐字一致承诺，详见 probes/results.json。

13 项既有定向 CTest 通过 163.93 秒，含类型参数/整数/两态/signed、generate、子程序、过程控制、always、编译/检查点、门级 CLI 与 parser 单测。parser 单测检查三次解析清理、两个实例克隆、三种断言身份、标签及父节点。Bison 当前 40 个 shift/reduce conflicts（M20 为 39），保留生成日志；不宣称完整 SV grammar。五组输入各三次解析清理、parser 单测，以及四个实际生成程序（actions/defaults/hierarchy 串行、parallel 双线程）通过 macOS ASan/UBSan，关闭 leak 检测；运行波形核对正式基线，见 sanitizer-runtimes.json、sanitizers/ 和 sanitizer-*.log。

585 文件冻结源包 SHA256：`147a4a80dfbe62144b218d902146bab2be5ddf582d9a6f85ff986e14527f3366`，已与工作区逐文件核对。最终本地编译器重新发射五份完整 C++，与正式实跑版本字节相同，见 final-identity.json。Linux `/tmp/dsim-m21-linux-NLpLO5` 同源 manifest 校验、干净构建及十项定向 CTest 通过 215.54 秒，最终退出 0。五份串行及一份双线程完整 C++ 与 macOS 字节相同；Linux 实跑 TRACE/1345 条位时间线也匹配同五组实际 VCS，见 linux/、platform-identity.json 和 linux-vcs-results.json。

```sh
ctest --test-dir build -R '^(rtl_immediate_assertions|rtl_semantic_memory)$' --output-on-failure
python3 validation/m21-immediate-assertions/verify.py
python3 validation/m21-immediate-assertions/run-sanitizers.py
```

本批未运行完整 CTest 集、Linux sanitizer 或新的性能测试，不据此推断相对 VCS 的速度改善。后续类型/接口、并发断言与事件区、覆盖率、动态验证环境的依赖顺序已写入 plan1017.md。
