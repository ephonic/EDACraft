本批参考 `REPORT-GAP8.md`，修复类体 parameter/localparam 的降低和模板作用域常量求值，增加含 string 的 unpacked struct 类属性、动态数组与队列的完整存储路径。

- 新增 8 个结构体/真实 UVM 负载模型，6 个类内常量模型，19 个拒绝用例。
- 比对 TRACE、串行/时间轮/双线程请求、文本及压缩波形、预测回滚；功能测试不构成性能结论。
- 原版公开 UVM 的输入和预处理 SHA 保持；新的首阻塞为 `uvm_resource_base.svh:212` 的 unpacked struct 关联数组。`next-blocker.sv` 是独立、可运行的 VCS 最小复现。
- 不支持项仍包括关联 struct 元素、固定对象数组、结构体容器 NBA、类体 parameter type；不宣称完整 UVM 支持。
- `groups.json` 是冻结发布的九组范围。`progress.json`、各平台 release/entry/ASan/VCS/cross-platform JSON 记录实测状态；原始日志和波形归入 dsim-test/evidence。

REPORT-GAP9 原文和38份原始/中间探针已按SHA复核：20份两端可编译，11份仅VCS可编译，7份两端均拒绝。这里只统计编译能力，未将20份计作运行等价。`gap9-comparison.json`单列VCS自身NYI和语料问题；`next-work.md`记录virtual interface、时间槽末monitor/strobe及UVM关联结构体的实现顺序。

Linux实际入口检查复用冻结阶段已经Intel编译和运行通过的原生模型，逐一要求入口生成的C++完全一致，并复跑TRACE和完整波形；`activate-reuse.py`记录原生文件SHA与路径。原先重复原生编译检查已完成factory/scalar两例后主动中止并恢复旧链接，保留原始记录和策略说明；这次中止不计作产品测试失败。Mac的14例实际入口进行了完整原生编译运行。

最终双端稳定通过：生产3e9525c7，1428冻结输入，九组76模型/1327捕获/126编译拒绝/2运行拒绝/12回滚/9提交及mandatory。Mac与103各14模型实际入口生成C++/运行输出/完整波形验收；跨端232份C++和1327份完整解码捕获一致，16份压缩字节差异单列，完整解码记录一致。Mac稳定20261101T010531513903Z-36847c24fa1c，Linux Intel+Z3稳定20261101T010618129501Z-36847c24fa1c均激活。完整公开UVM仍在关联结构体首错处，GAP9新能力尚未实现。
