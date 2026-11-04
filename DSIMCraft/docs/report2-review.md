# Complex REPORT2 复核

原报告使用 M83 稳定入口。冻结原文及输入 SHA256 后，复核原始 probes2、四个新增复杂设计及扩展语义；证据见 `validation/m88-comb-partial`。未将“测试脚本给出 PASS”当作其缺陷分类正确的证明。

1. **P0 三元内算术右移并非 dsim 缺陷。** 远端 VCS W-2024.09_Full64 对原封不动的 `p21_sra_cond.sv` 同样输出 `direct=ffffffff cond=ffffffff tern=003fffff func=ffffffff ifelse=ffffffff`。三元两分支混合 signed/unsigned 会建立 unsigned 上下文，影响分支中 context-determined 的移位左操作数。`$signed` 并不保证整个外层表达式保持 signed；在三元结果外再加 `$signed` 也不能补回已经丢弃的符号位。原探针自己打印的 “bug confirmed” 不是工具诊断。

   当需要 SRA/SRL 选择时，可先把 SRA 结果赋给独立中间线，再做三元选择；或把两分支都显式转换为 signed。新增 `shift_context.sv` 用 `$fatal` 自检负数、31/0 位移、X 条件以及外层 cast，并对照完整共同位波形。仿真器保留已与 VCS 相同的合法语义。

2. **默认随机流的“同源重编译不确定”没有复现。** 相同源字节在不同路径、重复编译及 serial/time-wheel/parallel 入口的完整输出和 ordered 波形一致；显式 `$urandom(seed)` 的后续流可重播，预测失败后也能重播。修改设计增加/删除过程可能改变逻辑过程编号，从而改变默认流，这是现有随机稳定性边界；不宣称完整实例级随机稳定性。具体 `$urandom` 数列与 VCS 不同，随机 AXI/Cache 对照比较各自影子模型的自检结果，不宣称输入激励逐数相同。需要固定单个验证线程时在该线程显式播种。见 [random-functions](random-functions.md)。

3. **SDF 探针需要区分最终值与真实延迟。** 原 `models.v` 未给时标，dsim 的默认 `1s/1s` 会使纳秒路径延迟舍入为零。保留原命令的功能检查；新增 `--timescale 1ns/1ps` 与 VCS `-timescale=1ns/1ps`，以实际 `$sdf_annotate` 对照。`tb.y` 的完整 settled 时间线为 X@0、0@5ns、1@12ns，证明本探针走了非零延迟路径。这不是完整 SDF/timing-check 功能声明。

4. VCD 文本、拒绝覆盖现有波形、incdir/define/文件列表、变索引 NBA、多个 delayed always、SDF 解析与 7/7 路径绑定，均纳入永久回归。四个新增复杂设计和旧六个设计由 `complex_report2` / `complex_report` 两组覆盖。原探针无需改写；不修改用户 DUT 来掩盖失败。

本轮另有两项真实实现修复：报告目录新增阻塞用例的组合过程整字/部分写误拒绝，以及有符号负下标裁剪写入丢失，见 [comb-partial-writes](comb-partial-writes.md)。RTL 与门级 parser 保持独立，DWF 编码不变。
