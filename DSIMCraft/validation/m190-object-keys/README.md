# M190：对象句柄关联键

新增 class 键的解析、规范类型身份与 64 位键存储，支持 null/别名/上转型、独立复制、类属性、typed foreach、游标、find_index、约束 foreach 与 checkpoint。泛型 KEY 与 typedef 可使用 class/string/32 位整数。纯逻辑表达式也按四态短路；对象容器元素的复合赋值保留一次地址求值。

执行模型在 tests/typed_containers/key_*.sv 和 tests/constraint_foreach/keys.sv；keys_runtime.cpp 检查不同高 32 位、UINT64_MAX、null 排序、复制与快照。parser 测试覆盖 65/129 位克隆身份及失败后重复清理。

边界：任意宽度/enum/aggregate 键、关联数组形参/返回、非整变量游标等尚未补齐；对象身份的顺序仅保证本运行确定，不承诺跨工具分配顺序。公开 UVM 尚未原生编译运行。REPORT-GAP5 的 36 原始探针只做发射检查，23 发射/13 拒绝，不等于 23 执行通过。后续优先 clocking 和 covergroup，另见 plan1017.md。

本批发布、VCS、消毒器及实际入口验证以最终 JSON 收据为准。无性能结论。


REPORT-GAP5 的新复核见 [REPORT-GAP5-CURRENT.md](REPORT-GAP5-CURRENT.md)。VCS 的五个原样新容器模型执行通过；对象键约束 foreach 的 `k.id` 用例被 VCS W-2024.09 以 XMRE 拒绝，dsim 的执行与消毒器检查通过，此边界单列，不能计入同源行为对齐。七个新类型错误用例均需双方拒绝，以最终 vcs.json 为准。

发布候选中，测试代码引用私有嵌套类型以及纯对象模型无可见波形信号的两处测试设施问题已纠正；相应候选保持未激活，日志保留。最终生产 C++ 实现未因这些测试设施修正而改变，稳定发布以 e7c782ab 对应收据为准。

最终双端验收通过：生产提交 e7c782ab，1287 项冻结输入一致，source SHA256 为 `01b0ae0f83c141397fe51192328ffad04ffdf88811020ade80a073e7ca7aeda4`。每端四组 40 模型、712 捕获、73 拒绝、5 回滚/5 提交及 parser/格式 parser/原生 liberty DB 必要检查通过；125 份生成 CPP、712 份解码波形跨端相同。36 份既有 parameterized_classes 波形编码字节差异单列，新模型无编码差异。

Mac 稳定 `20261031T013317256083Z-01b0ae0f83c1` 与 103 Intel 稳定 `20261031T013351619534Z-01b0ae0f83c1` 均已激活；各五个实际入口模型的生成 CPP 和异步波形与候选一致，Linux 根目录兼容入口另验通过。Mac 实际入口另执行合法 peek/randc 报告探针。VCS 五原样正例和七共同拒绝通过，对象键约束成员访问接收差异保留。ASan/UBSan 五模型、一次回放、23 拒绝、parser 重复清理及额外约束模型/64 位键内核通过；未启用 leak 检查。原版公开 UVM 在两端预检及实际入口保持相同展开与 `uvm_report_handler` 首错，完整 UVM 仍未运行。
